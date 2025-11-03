// payload_cms/src/collections/Article.ts
import {
  BlockquoteFeature,
  BoldFeature,
  HeadingFeature,
  InlineCodeFeature,
  ItalicFeature,
  LinkFeature,
  ParagraphFeature,
  RelationshipFeature,
  UnderlineFeature,
  UploadFeature,
  convertLexicalToMarkdown,
  editorConfigFactory,
  lexicalEditor,
} from '@payloadcms/richtext-lexical'
import type { SerializedEditorState } from '@payloadcms/richtext-lexical/lexical'
import { CollectionConfig } from 'payload/types'
import { isVerifiedTranslatorField } from '../access/isVerifiedTranslatorField'
import type { User } from '../payload-types' // It's good practice to import your generated types
import StatusBadge from '../components/StatusBadge'

export const Article: CollectionConfig = {
  slug: 'articles',
  admin: {
    useAsTitle: 'title',
    defaultColumns: ['title', 'status', 'updatedAt', 'category', 'author' ],
  },
  access: {
    create: ({ req: { user } }: any) => {
      if (!user) return false
      const roles = user.roles || []
      return roles.includes('admin') || roles.includes('publisher') || roles.includes('contributor')
    },
    read: ({ req: { user } }: any) => {
      if (!user) {
        return {
          status: {
            equals: 'published',
          },
        }
      }
      if (user.roles?.includes('admin') || user.roles?.includes('publisher')) {
        return true
      }

      const where = {
        or: [
          {
            status: {
              equals: 'published',
            },
          },
          {
            author: {
              equals: user.id,
            },
          },
        ],
      }
      return where
    },
    update: async ({ req, id }: any) => {
      const { user } = req
      if (!user) return false
      const loggedInUser = user as User

      if (
        loggedInUser.roles?.includes('admin') ||
        loggedInUser.roles?.includes('publisher') ||
        loggedInUser.roles?.includes('verified-translator')
      ) {
        return true
      }


      if (loggedInUser.roles?.includes('contributor')) {
        if (id) {
          const doc = await req.payload.findByID({
            collection: 'articles',
            id,
            depth: 0,
          })
          if (doc) {
            const authorId = typeof doc.author === 'string' ? doc.author : doc.author
            return authorId === loggedInUser.id && doc.status === 'draft'
          }
          return false
        }
        const where = {
          and: [
            {
              author: {
                equals: loggedInUser.id,
              },
            },
            {
              status: {
                equals: 'draft',
              },
            },
          ],
        }
        return where
      }

      return false
    },
    delete: ({ req: { user } }: any) => {
      if (!user) return false
      return user.roles.includes('admin')
    },
  },
  fields: [
    {
      name: 'title',
      type: 'text',
      required: true,
      localized: true,
    },
    {
      name: 'author',
      type: 'relationship',
      relationTo: 'users',
      defaultValue: ({ user }: any) => user?.id,
      admin: {
        position: 'sidebar',
        readOnly: true,
      },
    },
    {
      name: 'publishedDate',
      type: 'date',
      admin: {
        position: 'sidebar',
      },
    },
    {
      name: 'category',
      type: 'relationship',
      relationTo: 'categories',
      hasMany: true,
      admin: {
        position: 'sidebar',
      },
    },
    {
      name: 'content',
      type: 'richText',
      editor: lexicalEditor({
        features: ({ rootFeatures }: any) => [
          ...rootFeatures,
          HeadingFeature({ enabledHeadingSizes: ['h1', 'h2', 'h3', 'h4'] }),
          InlineCodeFeature(),
          BlockquoteFeature(),
          LinkFeature(),
          UploadFeature(),
        ],
      }),
      localized: true,
    },
    {
      name: 'markdown',
      type: 'textarea',
      admin: {
        hidden: true,
      },
      hooks: {
        afterRead: [
          ({ siblingData, siblingFields }: any) => {
            const data: SerializedEditorState = siblingData['content']

            if (!data) {
              return ''
            }

            const markdown = convertLexicalToMarkdown({
              data,
              editorConfig: editorConfigFactory.fromField({
                field: siblingFields.find(
                  (field: any) => 'name' in field && field.name === 'content',
                ),
              }),
            })

            return markdown
          },
        ],
        beforeChange: [
          ({ siblingData }: any) => {
            // Ensure that the markdown field is not saved in the database
            delete siblingData['markdown']
            return null
          },
        ],
      },
    },
    {
      name: 'status',
      type: 'select',
      options: [
        {
          label: 'Draft',
          value: 'draft',
        },
        {
          label: 'Published',
          value: 'published',
        },
      ],
      defaultValue: 'draft',
      admin: {
        position: 'sidebar',
        components: {
          Cell: StatusBadge,
        },
      },
      access: {
        create: ({ req: { user } }: any) => {
          if (!user) return false
          const roles = user.roles || []
          return roles.includes('admin') || roles.includes('publisher')
        },
        read: () => true,
        update: ({ req: { user } }: any) => {
          if (!user) return false
          const roles = user.roles || []
          return roles.includes('admin') || roles.includes('publisher')
        },
      },
    },
  ],
  hooks: {
    afterChange: [
      async ({ doc, req, operation }: any) => {
        if ((operation === 'create' || operation === 'update') && doc.status === 'published') {
          console.log(`Article "${doc.title}" (ID: ${doc.id}) has been published.`);
          // Here you would trigger the Content Sync Service
          fetch(`${process.env.BACKEND_URL}/api/v1/sync/payload`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              doc: doc,
            }),
          });
        }
      },
    ],
  },
}
