import type { Access } from 'payload'

export const isAdmin: Access = ({ req: { user } }) => {
  // Require authentication - fail securely if no user
  if (!user) {
    return false
  }
  const roles = Array.isArray(user.roles) ? user.roles : []
  return roles.includes('admin')
}

export const isAdminOrPublisher: Access = ({ req: { user } }) => {
  // Require authentication - fail securely if no user
  if (!user) {
    return false
  }
  const roles = Array.isArray(user.roles) ? user.roles : []
  return roles.includes('admin') || roles.includes('publisher')
}
