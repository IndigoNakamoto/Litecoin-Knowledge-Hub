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
import crypto from 'crypto'

type AccessResult = boolean | Record<string, unknown>

const userHasRole = (user: User | null | undefined, roles: string[]): boolean =>
  Boolean(user?.roles?.some((role) => roles.includes(role)))

const articleCreateAccess = ({ req }: { req: { user?: User } }): AccessResult => {
  const user = req.user as User | undefined
  
  // Allow form state building even without user - Payload's authentication middleware
  // will handle authentication for actual operations. During SSR, user session might
  // not be available even for authenticated users, so we allow access control to pass
  // and rely on Payload's authentication to block unauthenticated operations.
  if (!user) {
    console.log('[Article access] Create check - No user found (may be form state building), allowing for form structure')
    return true
  }
  
  const roles = Array.isArray(user.roles) ? user.roles : []
  const hasAccess = userHasRole(user, ['admin', 'publisher', 'contributor'])
  console.log('[Article access] Create check - User:', user.email, 'Roles:', JSON.stringify(roles), 'Has access:', hasAccess)
  return hasAccess
}

const articleReadAccess = ({ req }: { req: { user?: User } }): AccessResult => {
  const user = req.user as User | undefined
  if (!user) {
    console.log('[Article access] Read check - No user, allowing published articles only')
    return {
      status: {
        equals: 'published',
      },
    }
  }

  const roles = Array.isArray(user.roles) ? user.roles : []
  const hasAdminOrPublisher = userHasRole(user, ['admin', 'publisher'])
  console.log('[Article access] Read check - User:', user.email, 'Roles:', JSON.stringify(roles), 'Has admin/publisher:', hasAdminOrPublisher)

  if (hasAdminOrPublisher) {
    console.log('[Article access] Read check - Allowing all articles for admin/publisher')
    return true
  }

  console.log('[Article access] Read check - Allowing published articles or user\'s own articles')
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
  
  // For form state building (when id is not provided), allow access even without user
  // Payload's authentication middleware will handle authentication for actual operations
  if (!id) {
    if (user) {
      const roles = Array.isArray(user.roles) ? user.roles : []
      console.log('[Article access] Update check - Form state building, User:', user.email, 'Roles:', JSON.stringify(roles))
      return true
    } else {
      // Allow form state building without user - Payload will handle auth for actual operations
      console.log('[Article access] Update check - Form state building, no user (allowing for form structure)')
      return true
    }
  }

  // For actual update operations (when id is provided), require a user
  if (!user) {
    console.log('[Article access] Update check - No user found for update operation, denying access')
    return false
  }

  const roles = Array.isArray(user.roles) ? user.roles : []
  console.log('[Article access] Update check - User:', user.email, 'Roles:', JSON.stringify(roles), 'Article ID:', id)

  const hasAdminPublisherOrTranslator = userHasRole(user, ['admin', 'publisher', 'verified-translator'])
  if (hasAdminPublisherOrTranslator) {
    console.log('[Article access] Update check - Allowing update for admin/publisher/translator')
    return true
  }

  const hasContributor = userHasRole(user, ['contributor'])
  if (hasContributor) {
    if (id) {
      console.log('[Article access] Update check - Contributor trying to update article:', id)
      try {
        const doc = await req.payload.findByID({
          collection: 'articles',
          id,
          depth: 0,
        })

        if (doc) {
          const authorId = typeof doc.author === 'string' ? doc.author : (doc.author as any)?.id || doc.author
          const isAuthor = authorId === user.id
          const isDraft = doc.status === 'draft'
          console.log('[Article access] Update check - Contributor update result:', {
            isAuthor,
            isDraft,
            authorId,
            userId: user.id,
            status: doc.status
          })
          return isAuthor && isDraft
        }

        console.log('[Article access] Update check - Article not found')
        return false
      } catch (error) {
        console.error('[Article access] Update check - Error fetching article:', error)
        return false
      }
    }

    console.log('[Article access] Update check - Contributor creating/updating own draft articles')
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

  console.log('[Article access] Update check - User does not have required role, denying access')
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
          // Allow form state building even without user - Payload's authentication middleware
          // will handle authentication for actual operations. During SSR, user session might
          // not be available even for authenticated users, so we allow access control to pass
          // and rely on Payload's authentication to block unauthenticated operations.
          if (!user) {
            console.log('[Article status field] Create check - No user found (may be form state building), allowing for form structure')
            return true
          }
          const roles = Array.isArray(user.roles) ? user.roles : []
          const canCreate = roles.includes('admin') || roles.includes('publisher')
          console.log('[Article status field] Create check - User:', user.email, 'Roles:', JSON.stringify(roles), 'Can create:', canCreate)
          return canCreate
        },
        read: () => true,
        update: ({ req: { user } }: any) => {
          // Allow form state building even without user - Payload's authentication middleware
          // will handle authentication for actual operations. During SSR, user session might
          // not be available even for authenticated users, so we allow access control to pass
          // and rely on Payload's authentication to block unauthenticated operations.
          if (!user) {
            console.log('[Article status field] Update check - No user found (may be form state building), allowing for form structure')
            return true
          }
          const roles = Array.isArray(user.roles) ? user.roles : []
          const canUpdate = roles.includes('admin') || roles.includes('publisher')
          console.log('[Article status field] Update check - User:', user.email, 'Roles:', JSON.stringify(roles), 'Can update:', canUpdate)
          return canUpdate
        },
      },
    },
  ],
  hooks: {
    afterChange: [
      async ({ doc, req, operation }: any) => {
        console.log(`Article "${doc.title}" (ID: ${doc.id}) changed with operation: ${operation}, status: ${doc.status}`);
        
        const backendUrl = process.env.BACKEND_URL;
        if (!backendUrl) {
          console.error('❌ BACKEND_URL environment variable is not set. Cannot trigger RAG pipeline sync.');
          return;
        }

        try {
          // Prepare webhook payload
          const payload = JSON.stringify({
            operation: operation,
            doc: doc,
          });
          
          // Generate HMAC signature if WEBHOOK_SECRET is configured
          const webhookSecret = process.env.WEBHOOK_SECRET;
          const headers: Record<string, string> = {
            'Content-Type': 'application/json',
          };
          
          if (webhookSecret) {
            // Generate HMAC-SHA256 signature
            const signature = crypto
              .createHmac('sha256', webhookSecret)
              .update(payload)
              .digest('hex');
            
            // Add signature and timestamp headers
            headers['X-Webhook-Signature'] = signature;
            headers['X-Webhook-Timestamp'] = Math.floor(Date.now() / 1000).toString();
            console.log(`🔐 Webhook authentication enabled - Sending signed webhook to backend`);
          } else {
            console.warn('⚠️  WEBHOOK_SECRET not configured - Webhook will be sent without authentication');
          }
          
          // Always trigger sync to handle publishing, unpublishing, and updates
          const response = await fetch(`${backendUrl}/api/v1/sync/payload`, {
            method: 'POST',
            headers: headers,
            body: payload,
          });

          if (!response.ok) {
            const errorText = await response.text();
            if (response.status === 401) {
              console.error(`🔒 Webhook authentication failed for article "${doc.title}" (ID: ${doc.id}). Status: ${response.status}, Error: ${errorText}`);
            } else {
              console.error(`❌ Failed to sync article "${doc.title}" (ID: ${doc.id}) to RAG pipeline. Status: ${response.status}, Error: ${errorText}`);
            }
          } else {
            const result = await response.json();
            console.log(`✅ Successfully triggered RAG pipeline sync for article "${doc.title}" (ID: ${doc.id}):`, result);
          }
        } catch (error) {
          console.error(`💥 Error triggering RAG pipeline sync for article "${doc.title}" (ID: ${doc.id}):`, error);
        }
      },
    ],
    afterDelete: [
      async ({ doc, req }: any) => {
        console.log(`Article "${doc.title}" (ID: ${doc.id}) has been deleted.`);
        
        const backendUrl = process.env.BACKEND_URL;
        if (!backendUrl) {
          console.error('❌ BACKEND_URL environment variable is not set. Cannot trigger RAG pipeline deletion.');
          return;
        }

        try {
          // Prepare webhook payload
          const payload = JSON.stringify({
            operation: 'delete',
            doc: doc,
          });
          
          // Generate HMAC signature if WEBHOOK_SECRET is configured
          const webhookSecret = process.env.WEBHOOK_SECRET;
          const headers: Record<string, string> = {
            'Content-Type': 'application/json',
          };
          
          if (webhookSecret) {
            // Generate HMAC-SHA256 signature
            const signature = crypto
              .createHmac('sha256', webhookSecret)
              .update(payload)
              .digest('hex');
            
            // Add signature and timestamp headers
            headers['X-Webhook-Signature'] = signature;
            headers['X-Webhook-Timestamp'] = Math.floor(Date.now() / 1000).toString();
            console.log(`🔐 Webhook authentication enabled - Sending signed webhook for deletion`);
          } else {
            console.warn('⚠️  WEBHOOK_SECRET not configured - Webhook will be sent without authentication');
          }
          
          // Trigger removal from vector store
          const response = await fetch(`${backendUrl}/api/v1/sync/payload`, {
            method: 'POST',
            headers: headers,
            body: payload,
          });

          if (!response.ok) {
            const errorText = await response.text();
            if (response.status === 401) {
              console.error(`🔒 Webhook authentication failed for deletion of article "${doc.title}" (ID: ${doc.id}). Status: ${response.status}, Error: ${errorText}`);
            } else {
              console.error(`❌ Failed to delete article "${doc.title}" (ID: ${doc.id}) from RAG pipeline. Status: ${response.status}, Error: ${errorText}`);
            }
          } else {
            const result = await response.json();
            console.log(`✅ Successfully triggered RAG pipeline deletion for article "${doc.title}" (ID: ${doc.id}):`, result);
          }
        } catch (error) {
          console.error(`💥 Error triggering RAG pipeline deletion for article "${doc.title}" (ID: ${doc.id}):`, error);
        }
      },
    ],
  },
}
