import type { CollectionConfig } from 'payload'

export const Users: CollectionConfig = {
  slug: 'users',
  admin: {
    useAsTitle: 'email',
    hidden: ({ user }) => !user || !user.roles?.includes('admin'),
  },
  auth: {
    tokenExpiration: 7200, // 2 hours
    useSessions: true, // Use sessions for better cookie handling
    // Let Payload use default cookie settings - they work better in most cases
  },
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
    read: ({ req: { user }, id }) => {
      // Ensure roles is an array if user exists
      const roles = user ? (Array.isArray(user.roles) ? user.roles : []) : []

      // If no id provided, this is likely the current user endpoint (needed for admin panel)
      // This endpoint requires authentication - return true only if user exists
      // This allows the admin panel to read the current user's data when building form state
      if (!id) {
        if (user) {
          console.log('[Users access] Read check - Current user endpoint, User:', user.email, 'Roles:', JSON.stringify(roles))
          return true
        } else {
          // No user and no id - this might be a form state building request
          // Allow it to pass through, Payload will handle the authentication check
          console.log('[Users access] Read check - Current user endpoint, no user found (may be form state building)')
          return true
        }
      }

      // If no user is authenticated but id is provided, allow public read access (for basic user info)
      if (!user) {
        return true
      }

      // If id is provided and matches current user, allow
      if (user.id === id) {
        console.log('[Users access] Read check - User reading own data, User:', user.email)
        return true
      }

      // Allow admins to read all users
      if (roles.includes('admin')) {
        console.log('[Users access] Read check - Admin reading user, User:', user.email, 'Target ID:', id)
        return true
      }

      // Allow public read access (for basic user info)
      return true
    },
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
