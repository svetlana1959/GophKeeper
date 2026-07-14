/** The local part of an email, used as a display name when no real name exists. */
export function displayNameFromIdentity(identity: string | null | undefined): string {
  if (!identity) return 'Personal account'
  const local = identity.split('@')[0] ?? identity
  return local.charAt(0).toUpperCase() + local.slice(1)
}

/** e.g. "14 June 2026, 12:43" — matches the dashboard's sync timestamp. */
export function formatSyncTimestamp(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  const day = date.getDate()
  const month = date.toLocaleString('en-US', { month: 'long' })
  const year = date.getFullYear()
  const time = date.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })
  return `${day} ${month} ${year}, ${time}`
}
