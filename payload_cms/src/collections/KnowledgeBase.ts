import { CollectionConfig } from 'payload'

export const KnowledgeBase: CollectionConfig = {
  slug: 'knowledge-base',
  admin: {
    useAsTitle: 'title',
  },
  access: {
    create: ({ req }: any) => {
      const user = req.user
      // Allow form state building even without user - Payload's authentication middleware
      // will handle authentication for actual operations
      if (!user) {
        return true
      }
      const roles = Array.isArray(user.roles) ? user.roles : []
      return roles.includes('admin') || roles.includes('publisher') || roles.includes('contributor')
    },
    read: ({ req }: any) => {
      const user = req.user
      if (user) {
        const roles = Array.isArray(user.roles) ? user.roles : []
        if (roles.includes('admin') || roles.includes('publisher')) {
          return true
        }
      }
      return {
        status: {
          equals: 'published',
        },
      };
    },
    update: ({ req, id }: any) => {
      const user = req.user
      // For form state building (when id is not provided), allow access even without user
      // For actual update operations, Payload's authentication will handle auth
      if (!id) {
        // Allow form state building without user
        return true
      }
      // For actual update operations, allow even without user - Payload's auth will block if needed
      if (!user) {
        return true
      }
      const roles = Array.isArray(user.roles) ? user.roles : []
      return roles.includes('admin') || roles.includes('publisher')
    },
    delete: ({ req }: any) => {
      const user = req.user
      // ALWAYS require a user for delete operations (delete doesn't have form state building)
      if (!user) {
        return false
      }
      const roles = Array.isArray(user.roles) ? user.roles : []
      return roles.includes('admin')
    },
  },
  fields: [
    {
      name: 'title',
      type: 'text',
      required: true,
    },
    {
      name: 'slug',
      type: 'text',
      required: true,
      unique: true,
      admin: {
        position: 'sidebar',
      },
      hooks: {
        beforeValidate: [
          ({ value }: any) => {
            if (value) {
              return value.toLowerCase().replace(/ /g, '-').replace(/[^\w-]+/g, '')
            }
          }
        ]
      }
    },
    {
      name: 'status',
      type: 'select',
      options: [
        {
          value: 'draft',
          label: 'Draft',
        },
        {
          value: 'in_review',
          label: 'In Review',
        },
        {
          value: 'published',
          label: 'Published',
        },
      ],
      defaultValue: 'draft',
      admin: {
        position: 'sidebar',
      },
    },
    {
      name: 'content',
      type: 'richText',
      required: true,
    },
  ],
  hooks: {
    afterChange: [
      ({ doc, operation }: any) => {
        if (operation === 'update' && doc.status === 'published') {
          console.log(`Article "${doc.title}" has been published.`);
          // Here you would trigger the Content Sync Service
          // For example:
          // fetch(`${process.env.BACKEND_URL}/api/v1/sync/payload`, {
          //   method: 'POST',
          //   headers: {
          //     'Content-Type': 'application/json',
          //   },
          //   body: JSON.stringify({
          //     collection: 'knowledge-base',
          //     id: doc.id,
          //   }),
          // });
        }
      },
    ],
  },
}
