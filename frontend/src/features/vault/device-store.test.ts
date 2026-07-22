import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest'
import {
  clearPersistedDevice,
  peekPersistedDevice,
  persistDevice,
  unlockPersistedDevice,
  WrongPinError,
} from './device-store'

// The unit env is Node (no DOM); a Map-backed shim is enough for these tests.
beforeAll(() => {
  const store = new Map<string, string>()
  vi.stubGlobal('localStorage', {
    getItem: (k: string) => store.get(k) ?? null,
    setItem: (k: string, v: string) => void store.set(k, v),
    removeItem: (k: string) => void store.delete(k),
  })
})

const DEVICE = {
  deviceId: 'dev-1',
  identity: 'AGE-SECRET-KEY-1EXAMPLEIDENTITYVALUE0000000000000000000000000000',
  recipient: 'age1examplerecipient',
}

describe('device store', () => {
  afterEach(() => clearPersistedDevice())

  it('round-trips a PIN-protected device and hides the key at rest', async () => {
    await persistDevice(DEVICE, { pin: '1357', ttlSeconds: 3600 })

    const meta = peekPersistedDevice()
    expect(meta).toEqual({
      deviceId: 'dev-1',
      recipient: 'age1examplerecipient',
      ttlSeconds: 3600,
      protected: true,
    })
    // The raw key must not appear in storage when protected.
    expect(localStorage.getItem('gophkeeper.vault.device')).not.toContain(DEVICE.identity)

    const unlocked = await unlockPersistedDevice('1357')
    expect(unlocked.identity).toBe(DEVICE.identity)
    expect(unlocked.ttlSeconds).toBe(3600)
  })

  it('rejects a wrong PIN with WrongPinError', async () => {
    await persistDevice(DEVICE, { pin: '1357', ttlSeconds: 3600 })
    await expect(unlockPersistedDevice('9999')).rejects.toBeInstanceOf(WrongPinError)
    await expect(unlockPersistedDevice()).rejects.toBeInstanceOf(WrongPinError)
  })

  it('stores unprotected when no PIN is given (opt-out)', async () => {
    await persistDevice(DEVICE, { ttlSeconds: 60 })
    expect(peekPersistedDevice()?.protected).toBe(false)
    const unlocked = await unlockPersistedDevice()
    expect(unlocked.identity).toBe(DEVICE.identity)
  })

  it('reports and clears cleanly', async () => {
    expect(peekPersistedDevice()).toBeNull()
    await persistDevice(DEVICE, { pin: '1357', ttlSeconds: 60 })
    expect(peekPersistedDevice()).not.toBeNull()
    clearPersistedDevice()
    expect(peekPersistedDevice()).toBeNull()
  })
})
