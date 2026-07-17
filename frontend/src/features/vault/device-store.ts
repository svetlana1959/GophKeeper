// Persisting the browser's device key across reloads, so the user isn't forced to
// re-link (and re-approve) every visit. The age private key is encrypted at rest
// under a key derived from the user's PIN (PBKDF2 → AES-GCM); with no PIN it is
// stored unprotected — a convenience/security trade the user opts into with an
// explicit warning. Scoped to the origin via localStorage.
//
// NOTE: like any in-tab key material this is reachable by XSS. The CSP/SRI pass
// (Phase 6) is what hardens that; here we only make reloads safe and give the PIN
// as an at-rest lock, not an anti-XSS measure.

import { base64ToBytes, bytesToBase64 } from './crypto'

const STORE_KEY = 'gophkeeper.vault.device'
const PBKDF2_ITERATIONS = 210_000

interface StoredDevice {
  deviceId: string
  recipient: string
  ttlSeconds: number
  protected: boolean
  salt?: string // base64, present iff protected
  iv?: string // base64, present iff protected
  // The identity: AES-GCM ciphertext (base64) when protected, else the raw key.
  identity: string
}

/** What's known about a persisted device without unlocking it. */
export interface PersistedDeviceMeta {
  deviceId: string
  recipient: string
  ttlSeconds: number
  protected: boolean
}

/** A device key recovered from storage, ready to re-authenticate. */
export interface UnlockedDevice {
  deviceId: string
  identity: string
  recipient: string
  ttlSeconds: number
}

/** Thrown when a persisted device can't be decrypted — a wrong or missing PIN. */
export class WrongPinError extends Error {
  constructor() {
    super('That PIN is incorrect.')
    this.name = 'WrongPinError'
  }
}

// Web Crypto wants BufferSource; our Uint8Arrays are ArrayBuffer-backed at
// runtime, but TS's lib types flag the ArrayBufferLike gap. One narrow cast.
const buf = (u: Uint8Array): BufferSource => u as BufferSource

function read(): StoredDevice | null {
  const raw = localStorage.getItem(STORE_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw) as StoredDevice
  } catch {
    return null
  }
}

async function deriveKey(pin: string, salt: Uint8Array): Promise<CryptoKey> {
  const material = await crypto.subtle.importKey(
    'raw',
    new TextEncoder().encode(pin),
    'PBKDF2',
    false,
    ['deriveKey'],
  )
  return crypto.subtle.deriveKey(
    { name: 'PBKDF2', salt: buf(salt), iterations: PBKDF2_ITERATIONS, hash: 'SHA-256' },
    material,
    { name: 'AES-GCM', length: 256 },
    false,
    ['encrypt', 'decrypt'],
  )
}

/** Persist the device key. With a PIN it's encrypted at rest; without one it's
 *  stored in the clear (the caller warns the user). Overwrites any prior device. */
export async function persistDevice(
  device: { deviceId: string; identity: string; recipient: string },
  opts: { pin?: string; ttlSeconds: number },
): Promise<void> {
  const base = { deviceId: device.deviceId, recipient: device.recipient, ttlSeconds: opts.ttlSeconds }
  let stored: StoredDevice
  if (opts.pin) {
    const salt = crypto.getRandomValues(new Uint8Array(16))
    const iv = crypto.getRandomValues(new Uint8Array(12))
    const key = await deriveKey(opts.pin, salt)
    const cipher = new Uint8Array(
      await crypto.subtle.encrypt(
        { name: 'AES-GCM', iv: buf(iv) },
        key,
        buf(new TextEncoder().encode(device.identity)),
      ),
    )
    stored = {
      ...base,
      protected: true,
      salt: bytesToBase64(salt),
      iv: bytesToBase64(iv),
      identity: bytesToBase64(cipher),
    }
  } else {
    stored = { ...base, protected: false, identity: device.identity }
  }
  localStorage.setItem(STORE_KEY, JSON.stringify(stored))
}

/** Metadata about the persisted device, if any — without needing the PIN. */
export function peekPersistedDevice(): PersistedDeviceMeta | null {
  const s = read()
  if (!s) return null
  return { deviceId: s.deviceId, recipient: s.recipient, ttlSeconds: s.ttlSeconds, protected: s.protected }
}

/** Recover the device key. Needs the PIN iff the device is protected; a wrong or
 *  missing PIN throws WrongPinError (AES-GCM authentication catches it). */
export async function unlockPersistedDevice(pin?: string): Promise<UnlockedDevice> {
  const s = read()
  if (!s) throw new Error('No device is saved on this browser.')
  const base = { deviceId: s.deviceId, recipient: s.recipient, ttlSeconds: s.ttlSeconds }
  if (!s.protected) return { ...base, identity: s.identity }
  if (!pin || !s.salt || !s.iv) throw new WrongPinError()
  try {
    const key = await deriveKey(pin, base64ToBytes(s.salt))
    const plain = await crypto.subtle.decrypt(
      { name: 'AES-GCM', iv: buf(base64ToBytes(s.iv)) },
      key,
      buf(base64ToBytes(s.identity)),
    )
    return { ...base, identity: new TextDecoder().decode(plain) }
  } catch {
    throw new WrongPinError()
  }
}

export function clearPersistedDevice(): void {
  localStorage.removeItem(STORE_KEY)
}
