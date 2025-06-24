import type { CollectionConfig } from 'payload'
import { isAdmin, isAdminOrPublisher } from '../access/isAdmin'

export const Category: CollectionConfig = {
  slug: 'categories',
  admin: {
    useAsTitle: 'name',
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
    },
  ],
  timestamps: false,
}
