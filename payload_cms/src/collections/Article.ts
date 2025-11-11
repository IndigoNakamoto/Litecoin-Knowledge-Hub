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
import { CollectionConfig } from 'payload'
import { isVerifiedTranslatorField } from '../access/isVerifiedTranslatorField'
import type { User } from '../payload-types' // It's good practice to import your generated types
import StatusBadge from '../components/StatusBadge'
import CategorySelector from '../components/CategorySelector'

type AccessResult = boolean | Record<string, unknown>

const userHasRole = (user: User | null | undefined, roles: string[]): boolean =>
  Boolean(user?.roles?.some((role) => roles.includes(role)))

const articleCreateAccess = ({ req }: { req: { user?: User } }): AccessResult => {
  const user = req.user as User | undefined
  if (!user) return false
  return userHasRole(user, ['admin', 'publisher', 'contributor'])
}

const articleReadAccess = ({ req }: { req: { user?: User } }): AccessResult => {
  const user = req.user as User | undefined
  if (!user) {
    return {
      status: {
        equals: 'published',
      },
    }
  }

  if (userHasRole(user, ['admin', 'publisher'])) {
    return true
  }

  return {
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
}

const articleUpdateAccess = async ({ req, id }: { req: { user?: User; payload: any }; id?: string }): Promise<AccessResult> => {
  const user = req.user as User | undefined
  if (!user) return false

  if (userHasRole(user, ['admin', 'publisher', 'verified-translator'])) {
    return true
  }

  if (userHasRole(user, ['contributor'])) {
    if (id) {
      const doc = await req.payload.findByID({
        collection: 'articles',
        id,
        depth: 0,
      })

      if (doc) {
        const authorId = typeof doc.author === 'string' ? doc.author : doc.author
        return authorId === user.id && doc.status === 'draft'
      }

      return false
    }

    return {
      and: [
        {
          author: {
            equals: user.id,
          },
        },
        {
          status: {
            equals: 'draft',
          },
        },
      ],
    }
  }

  return false
}

const articleDeleteAccess = ({ req }: { req: { user?: User } }): AccessResult => {
  const user = req.user as User | undefined
  if (!user) return false
  return userHasRole(user, ['admin'])
}

export const Article: CollectionConfig = {
  slug: 'articles',
  admin: {
    useAsTitle: 'title',
    defaultColumns: ['title', 'status', 'updatedAt', 'category', 'author' ],
  },
  access: {
    create: articleCreateAccess as any,
    read: articleReadAccess as any,
    update: articleUpdateAccess as any,
    delete: articleDeleteAccess as any,
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
        description: 'Select categories that best describe your article content',
        components: {
          Field: CategorySelector as any,
        },
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
          Cell: StatusBadge as any,
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
        console.log(`Article "${doc.title}" (ID: ${doc.id}) changed with operation: ${operation}, status: ${doc.status}`);
        // Always trigger sync to handle publishing, unpublishing, and updates
        fetch(`${process.env.BACKEND_URL}/api/v1/sync/payload`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            operation: operation,
            doc: doc,
          }),
        });
      },
    ],
    afterDelete: [
      async ({ doc, req }: any) => {
        console.log(`Article "${doc.title}" (ID: ${doc.id}) has been deleted.`);
        // Trigger removal from vector store
        fetch(`${process.env.BACKEND_URL}/api/v1/sync/payload`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            operation: 'delete',
            doc: doc,
          }),
        });
      },
    ],
  },
}
