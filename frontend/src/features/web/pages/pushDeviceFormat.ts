import type { PushDevice } from '../../../api/types'

/** "Firefox · Linux" — the secondary technical detail under a device's friendly name. */
export function deviceDetail(device: PushDevice): string {
  return [device.browser, device.platform].filter(Boolean).join(' · ')
}

/**
 * "today" / "yesterday" / "3 days ago" / a date once it stops being useful as a relative span.
 * Compared by calendar day rather than elapsed hours, so 11pm last night reads as "yesterday".
 */
export function lastSeenLabel(iso: string): string {
  const seen = new Date(iso)
  if (Number.isNaN(seen.getTime())) return 'unknown'
  const startOfDay = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime()
  const days = Math.round((startOfDay(new Date()) - startOfDay(seen)) / 86_400_000)
  if (days <= 0) return 'today'
  if (days === 1) return 'yesterday'
  if (days < 7) return `${days} days ago`
  return seen.toLocaleDateString()
}
