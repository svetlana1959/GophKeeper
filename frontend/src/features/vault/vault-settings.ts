// User-configurable vault preferences for this browser: how long a linked device
// asks to live, and whether to stay signed in across reloads. localStorage-backed
// and origin-scoped; not a security boundary (the device key lives in device-store).

import { DEFAULT_DEVICE_TTL_SECONDS } from './session'

const KEY = 'gophkeeper.vault.settings'

export interface VaultSettings {
  /** Whether a linked browser persists its key across reloads (PIN-guarded). */
  persist: boolean
  /** Self-declared device lifetime, in seconds, sent at enroll/heartbeat. */
  ttlSeconds: number
}

const DEFAULTS: VaultSettings = { persist: true, ttlSeconds: DEFAULT_DEVICE_TTL_SECONDS }

/** TTL presets offered in Settings. Mandatory — there is no "never" for a browser. */
export const TTL_OPTIONS: { label: string; seconds: number }[] = [
  { label: '1 hour', seconds: 60 * 60 },
  { label: '8 hours', seconds: 8 * 60 * 60 },
  { label: '1 day', seconds: 24 * 60 * 60 },
  { label: '1 week', seconds: 7 * 24 * 60 * 60 },
  { label: '30 days', seconds: 30 * 24 * 60 * 60 },
]

export function loadVaultSettings(): VaultSettings {
  try {
    const raw = localStorage.getItem(KEY)
    if (!raw) return { ...DEFAULTS }
    const parsed = JSON.parse(raw) as Partial<VaultSettings>
    return {
      persist: typeof parsed.persist === 'boolean' ? parsed.persist : DEFAULTS.persist,
      ttlSeconds:
        typeof parsed.ttlSeconds === 'number' && parsed.ttlSeconds > 0
          ? parsed.ttlSeconds
          : DEFAULTS.ttlSeconds,
    }
  } catch {
    return { ...DEFAULTS }
  }
}

export function saveVaultSettings(next: VaultSettings): void {
  localStorage.setItem(KEY, JSON.stringify(next))
}
