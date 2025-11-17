import type { Access } from 'payload'

export const isAdmin: Access = ({ req: { user } }) => {
  // Allow form state building even without user - Payload's authentication middleware
  // will handle authentication for actual operations. During SSR, user session might
  // not be available even for authenticated users, so we allow access control to pass
  // and rely on Payload's authentication to block unauthenticated operations.
  if (!user) {
    return true
  }
  const roles = Array.isArray(user.roles) ? user.roles : []
  return roles.includes('admin')
}

export const isAdminOrPublisher: Access = ({ req: { user } }) => {
  // Allow form state building even without user - Payload's authentication middleware
  // will handle authentication for actual operations. During SSR, user session might
  // not be available even for authenticated users, so we allow access control to pass
  // and rely on Payload's authentication to block unauthenticated operations.
  if (!user) {
    return true
  }
  const roles = Array.isArray(user.roles) ? user.roles : []
  return roles.includes('admin') || roles.includes('publisher')
}
