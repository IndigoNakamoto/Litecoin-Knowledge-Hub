import type { Access } from 'payload'

export const isAdmin: Access = ({ req: { user } }) => {
  // Return true or false based on if the user has an admin role
  return Boolean(user?.roles?.includes('admin'))
}

export const isAdminOrPublisher: Access = ({ req: { user } }) => {
    // Return true or false based on if the user has an admin or publisher role
    return Boolean(user?.roles?.includes('admin') || user?.roles?.includes('publisher'))
}
