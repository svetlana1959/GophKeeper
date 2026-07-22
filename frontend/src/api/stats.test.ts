import { describe, expect, it } from 'vitest'
import { statsOverviewSchema, statsSecuritySchema } from './stats'

// The security response is the one the UI degrades silently on: every field is
// read through `security.data?.…` with a fallback, so a failed parse doesn't throw
// in a component — it just renders "0 trusted devices" for an account that has
// them. These pin the shapes the backend actually returns.
describe('statsSecuritySchema', () => {
  const base = {
    status: 'good',
    trusted_devices: 2,
    revoked_devices: 0,
    alerts: 0,
  }

  it('accepts a null last_sync_at (no sync events persisted yet)', () => {
    const parsed = statsSecuritySchema.parse({ ...base, last_sync_at: null })
    expect(parsed.last_sync_at).toBeNull()
    expect(parsed.trusted_devices).toBe(2)
  })

  it('accepts a timestamp once sync events exist', () => {
    const parsed = statsSecuritySchema.parse({ ...base, last_sync_at: '2026-07-13T21:30:00Z' })
    expect(parsed.last_sync_at).toBe('2026-07-13T21:30:00Z')
  })

  it('accepts status "warning" alongside the new pending_devices field', () => {
    const parsed = statsSecuritySchema.parse({
      ...base,
      status: 'warning',
      pending_devices: 0,
      last_sync_at: null,
    })
    expect(parsed.status).toBe('warning')
  })
})

describe('statsOverviewSchema', () => {
  it('accepts zeroed category counts and the new pending_devices field', () => {
    const parsed = statsOverviewSchema.parse({
      passwords: 0,
      bank_cards: 0,
      notes: 0,
      files: 0,
      trusted_devices: 1,
      revoked_devices: 0,
      pending_devices: 0,
    })
    expect(parsed.trusted_devices).toBe(1)
  })
})
