export const formatDate = (date: Date | string): string => {
  return new Date(date).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })
}

export const formatRelativeTime = (date: Date | string): string => {
  const now = Date.now()
  const then = new Date(date).getTime()
  const diff = now - then
  if (diff < 60000) return 'Just now'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`
  if (diff < 604800000) return `${Math.floor(diff / 86400000)}d ago`
  return formatDate(date)
}

export const formatISO = (date: Date): string => date.toISOString()
