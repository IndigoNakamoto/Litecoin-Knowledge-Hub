import type { CollectionConfig } from 'payload'

export const Users: CollectionConfig = {
  slug: 'users',
  admin: {
    useAsTitle: 'email',
    hidden: ({ user }) => !user || !user.roles?.includes('admin'),
  },
  auth: true,
  access: {
    create: ({ req }) => {
      const user = req.user
      if (!user) {
        console.log('[Users access] No user found in request')
        return false
      }
      // Ensure roles is an array and check for admin role
      const roles = Array.isArray(user.roles) ? user.roles : []
      const hasAdmin = roles.includes('admin')
      console.log('[Users access] Create check - User:', user.email, 'Roles:', JSON.stringify(roles), 'Has admin:', hasAdmin, 'User object:', JSON.stringify(Object.keys(user)))
      return hasAdmin
    },
    read: () => true,
    update: ({ req: { user }, id }) => {
      if (!user) return false
      // Ensure roles is an array and check for admin role
      const roles = Array.isArray(user.roles) ? user.roles : []
      if (roles.includes('admin')) {
        return true
      }
      return user.id === id
    },
    delete: ({ req: { user } }) => {
      if (!user) return false
      // Ensure roles is an array and check for admin role
      const roles = Array.isArray(user.roles) ? user.roles : []
      return roles.includes('admin')
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
          // Ensure roles is an array and check for admin role
          const roles = Array.isArray(user.roles) ? user.roles : []
          return roles.includes('admin')
        },
      },
    },
    {
      name: 'authorizedLanguages',
      type: 'select',
      hasMany: true,
      options: ['en', 'es', 'fr'], // Assuming these are your languages
      admin: {
        condition: (data, siblingData) => {
          // Only show for verified-translator role
          const roles = siblingData?.roles || data?.roles || [];
          return Array.isArray(roles) && roles.includes('verified-translator');
        },
      },
    },
    {
      name: 'authorizedCategories',
      type: 'relationship',
      relationTo: 'categories',
      hasMany: true,
      admin: {
        condition: (data, siblingData) => {
          // Only show for contributor role
          const roles = siblingData?.roles || data?.roles || [];
          return Array.isArray(roles) && roles.includes('contributor');
        },
      },
    },
  ],
}
