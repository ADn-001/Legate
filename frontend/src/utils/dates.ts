/**
 * Date formatting utilities
 */

export const formatDate = (date: Date | string): string => {
  // TODO: Format date as readable string
  return new Date(date).toLocaleDateString()
}

export const formatRelativeTime = (date: Date | string): string => {
  // TODO: Format date as relative time (e.g., "2h ago", "yesterday")
  return 'just now'
}

export const formatISO = (date: Date): string => {
  return date.toISOString()
}
