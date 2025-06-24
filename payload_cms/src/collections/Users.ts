import type { CollectionConfig } from 'payload'

export const Users: CollectionConfig = {
  slug: 'users',
  admin: {
    useAsTitle: 'email',
    hidden: ({ user }) => !user || !user.roles.includes('admin'),
  },
  auth: true,
  access: {
    create: ({ req: { user } }) => {
      if (!user) return false
      return user.roles?.includes('admin')
    },
    read: () => true,
    update: ({ req: { user }, id }) => {
      if (!user) return false
      if (user.roles?.includes('admin')) {
        return true
      }
      return user.id === id
    },
    delete: ({ req: { user } }) => {
      if (!user) return false
      return user.roles?.includes('admin')
    },
  },
  fields: [
    {
      name: 'roles',
      type: 'select',
      hasMany: true,
      options: ['admin', 'publisher', 'contributor', 'verified-translator'],
      defaultValue: ['contributor'],
      required: true,
      saveToJWT: true,
      access: {
        update: ({ req: { user } }) => {
          if (!user) return false
          return user.roles?.includes('admin')
        },
      },
    },
    {
      name: 'authorizedLanguages',
      type: 'select',
      hasMany: true,
      options: ['en', 'es', 'fr'], // Assuming these are your languages
      admin: {
        condition: (data, siblingData) => siblingData.roles?.includes('verified-translator'),
      },
    },
    {
      name: 'authorizedCategories',
      type: 'relationship',
      relationTo: 'categories',
      hasMany: true,
      admin: {
        condition: (data, siblingData) => siblingData.roles?.includes('contributor'),
      },
    },
  ],
}
