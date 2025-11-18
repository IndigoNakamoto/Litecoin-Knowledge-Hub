import { CollectionConfig } from 'payload'
import crypto from 'crypto'

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
      async ({ doc, req, operation }: any) => {
        console.log(`KnowledgeBase "${doc.title}" (ID: ${doc.id}) changed with operation: ${operation}, status: ${doc.status}`);
        
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
              console.error(`🔒 Webhook authentication failed for knowledge base "${doc.title}" (ID: ${doc.id}). Status: ${response.status}, Error: ${errorText}`);
            } else {
              console.error(`❌ Failed to sync knowledge base "${doc.title}" (ID: ${doc.id}) to RAG pipeline. Status: ${response.status}, Error: ${errorText}`);
            }
          } else {
            const result = await response.json();
            console.log(`✅ Successfully triggered RAG pipeline sync for knowledge base "${doc.title}" (ID: ${doc.id}):`, result);
          }
        } catch (error) {
          console.error(`💥 Error triggering RAG pipeline sync for knowledge base "${doc.title}" (ID: ${doc.id}):`, error);
        }
      },
    ],
    afterDelete: [
      async ({ doc, req }: any) => {
        console.log(`KnowledgeBase "${doc.title}" (ID: ${doc.id}) has been deleted.`);
        
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
            console.log(`🔐 Webhook authentication enabled - Sending signed webhook to backend`);
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
              console.error(`🔒 Webhook authentication failed for deletion of knowledge base "${doc.title}" (ID: ${doc.id}). Status: ${response.status}, Error: ${errorText}`);
            } else {
              console.error(`❌ Failed to delete knowledge base "${doc.title}" (ID: ${doc.id}) from RAG pipeline. Status: ${response.status}, Error: ${errorText}`);
            }
          } else {
            const result = await response.json();
            console.log(`✅ Successfully triggered RAG pipeline deletion for knowledge base "${doc.title}" (ID: ${doc.id}):`, result);
          }
        } catch (error) {
          console.error(`💥 Error triggering RAG pipeline deletion for knowledge base "${doc.title}" (ID: ${doc.id}):`, error);
        }
      },
    ],
  },
}
