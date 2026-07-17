import type { Device } from '@/api/devices'

const ONLINE_WINDOW_MS = 5 * 60 * 1000

/** A device counts as online if it authenticated within the last few minutes. */
export function isOnline(device: Device): boolean {
  if (!device.last_seen_at) return false
  const seen = new Date(device.last_seen_at).getTime()
  return Number.isFinite(seen) && Date.now() - seen < ONLINE_WINDOW_MS
}

/** Coarse "last active" label from last_seen_at (the only activity signal we have). */
export function lastActiveLabel(device: Device): string {
  if (!device.last_seen_at) return 'Never'
  const seen = new Date(device.last_seen_at).getTime()
  if (!Number.isFinite(seen)) return '—'
  const min = Math.floor((Date.now() - seen) / 60_000)
  if (min < 1) return 'Just now'
  if (min < 60) return `${min} min ago`
  const hr = Math.floor(min / 60)
  if (hr < 24) return `${hr} hour${hr === 1 ? '' : 's'} ago`
  const days = Math.floor(hr / 24)
  return `${days} day${days === 1 ? '' : 's'} ago`
}
