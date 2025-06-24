import { CollectionConfig } from 'payload/types'
import { AfterChangeHook } from 'payload/dist/collections/config/types'
import { User } from '../payload-types'

export const KnowledgeBase: CollectionConfig = {
  slug: 'knowledge-base',
  admin: {
    useAsTitle: 'title',
  },
  access: {
    create: ({ req: { user } }: { req: { user: User } }) => {
      if (user) {
        return ['admin', 'editor', 'contributor'].includes(user.role)
      }
      return false
    },
    read: ({ req: { user } }: { req: { user: User } }) => {
      if (user && ['admin', 'editor'].includes(user.role)) {
        return true
      }
      return {
        status: {
          equals: 'published',
        },
      };
    },
    update: ({ req: { user } }: { req: { user: User } }) => {
      if (user) {
        return ['admin', 'editor'].includes(user.role)
      }
      return false
    },
    delete: ({ req: { user } }: { req: { user: User } }) => {
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
          ({ value }: { value: string }) => {
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
      ({ doc, req, operation }: { doc: any, req: any, operation: any }) => {
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
