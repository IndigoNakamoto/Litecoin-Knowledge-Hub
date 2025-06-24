import type { FieldAccess } from 'payload'
import type { User } from '../payload-types'

export const isVerifiedTranslatorField: FieldAccess = ({ req }) => {
  const { user, locale } = req as { user: User; locale: string }
  if (user && user.roles.includes('verified-translator')) {
    // If the user is a verified translator, check if their authorized languages include the current locale
    if (user.authorizedLanguages?.includes(locale as 'en' | 'es' | 'fr')) {
      return true
    }
  }
  // Allow admins and publishers to bypass this check
  if (user && (user.roles.includes('admin') || user.roles.includes('publisher'))) {
    return true
  }
  return false
}
