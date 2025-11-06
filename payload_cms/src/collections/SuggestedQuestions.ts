import type { CollectionConfig } from 'payload'
import { isAdmin, isAdminOrPublisher } from '../access/isAdmin'

export const SuggestedQuestions: CollectionConfig = {
  slug: 'suggested-questions',
  admin: {
    useAsTitle: 'question',
    defaultColumns: ['question', 'order', 'isActive', 'updatedAt'],
    group: 'Content Management',
    description: 'Manage suggested questions displayed to users on the chat interface',
  },
  access: {
    read: () => true, // Public read access for frontend
    create: isAdminOrPublisher,
    update: isAdminOrPublisher,
    delete: isAdmin,
  },
  fields: [
    {
      name: 'question',
      type: 'text',
      required: true,
      admin: {
        description: 'The question text to display to users',
      },
    },
    {
      name: 'order',
      type: 'number',
      required: true,
      defaultValue: 0,
      admin: {
        description: 'Display order (lower numbers appear first)',
      },
    },
    {
      name: 'isActive',
      type: 'checkbox',
      defaultValue: true,
      admin: {
        description: 'Whether this question should be displayed',
      },
    },
  ],
  timestamps: true,
}

