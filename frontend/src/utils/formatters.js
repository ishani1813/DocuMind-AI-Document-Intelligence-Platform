import { formatDistanceToNow, format, isToday, isYesterday } from 'date-fns'

export function formatBytes(bytes) {
  if (!bytes) return '0 B'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function formatRelative(dateStr) {
  const date = new Date(dateStr)
  if (isToday(date)) return `Today at ${format(date, 'h:mm a')}`
  if (isYesterday(date)) return `Yesterday at ${format(date, 'h:mm a')}`
  return formatDistanceToNow(date, { addSuffix: true })
}

export function formatDate(dateStr, fmt = 'MMM d, yyyy') {
  return format(new Date(dateStr), fmt)
}

export function formatScore(score) { return `${(score * 100).toFixed(1)}%` }
export function formatCost(usd) { return usd < 0.001 ? '<$0.001' : `$${usd.toFixed(4)}` }
export function formatMs(ms) { return ms >= 1000 ? `${(ms/1000).toFixed(1)}s` : `${ms}ms` }

export function truncate(str, maxLen = 120) {
  if (!str) return ''
  return str.length <= maxLen ? str : str.slice(0, maxLen).trimEnd() + '…'
}

export function initials(fullName = '') {
  return fullName.split(' ').filter(Boolean).slice(0, 2).map((n) => n[0].toUpperCase()).join('')
}

export function scoreColor(score) {
  if (score >= 0.8) return 'text-emerald-400'
  if (score >= 0.6) return 'text-yellow-400'
  return 'text-surface-200'
}

export function scoreBarColor(score) {
  if (score >= 0.8) return 'bg-emerald-500'
  if (score >= 0.6) return 'bg-yellow-500'
  return 'bg-surface-600'
}

export function toastError(err) {
  const detail = err?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg
  return err?.message || 'Something went wrong'
}
