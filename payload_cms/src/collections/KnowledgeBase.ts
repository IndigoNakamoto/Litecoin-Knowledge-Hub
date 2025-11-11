import { CollectionConfig } from 'payload'

export const KnowledgeBase: CollectionConfig = {
  slug: 'knowledge-base',
  admin: {
    useAsTitle: 'title',
  },
  access: {
    create: ({ req }: any) => {
      const user = req.user
      if (user) {
        return ['admin', 'editor', 'contributor'].includes(user.role)
      }
      return false
    },
    read: ({ req }: any) => {
      const user = req.user
      if (user && ['admin', 'editor'].includes(user.role)) {
        return true
      }
      return {
        status: {
          equals: 'published',
        },
      };
    },
    update: ({ req }: any) => {
      const user = req.user
      if (user) {
        return ['admin', 'editor'].includes(user.role)
      }
      return false
    },
    delete: ({ req }: any) => {
      const user = req.user
      if (user) {
        return ['admin', 'editor'].includes(user.role)
      }
      return false
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
