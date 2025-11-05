import type { CollectionConfig } from 'payload'
import { isAdmin, isAdminOrPublisher } from '../access/isAdmin'

export const Category: CollectionConfig = {
  slug: 'categories',
  admin: {
    useAsTitle: 'name',
    defaultColumns: ['name', 'parent', 'order', 'audienceLevel'],
    group: 'Content Management',
  },
  access: {
    read: () => true,
    create: isAdminOrPublisher,
    update: isAdminOrPublisher,
    delete: isAdmin,
  },
  fields: [
    {
      name: 'name',
      type: 'text',
      required: true,
      unique: true,
      admin: {
        description: 'Display name for the category',
      },
    },
    {
      name: 'description',
      type: 'textarea',
      admin: {
        description: 'Explain what content belongs in this category for writers',
      },
    },
    {
      name: 'parent',
      type: 'relationship',
      relationTo: 'categories',
      filterOptions: ({ id }) => {
        // Only filter out self-reference if we have an ID (editing existing category)
        if (id) {
          return {
            id: { not_equals: id }
          }
        }
        // For new categories, don't filter anything
        return true
      },
      admin: {
        description: 'Parent category for hierarchical organization (leave blank for main categories)',
      },
    },
    {
      name: 'order',
      type: 'number',
      required: true,
      defaultValue: 0,
      admin: {
        description: 'Sort order within parent category (lower numbers appear first)',
      },
    },
    {
      name: 'audienceLevel',
      type: 'select',
      options: [
        { label: 'Beginner', value: 'beginner' },
        { label: 'Intermediate', value: 'intermediate' },
        { label: 'Advanced', value: 'advanced' },
      ],
      admin: {
        description: 'Target audience level for this category',
      },
    },
    {
      name: 'icon',
      type: 'text',
      admin: {
        description: 'Emoji or icon for visual identification (e.g., 🏛️, 💸)',
      },
    },
  ],
  timestamps: false,
}
