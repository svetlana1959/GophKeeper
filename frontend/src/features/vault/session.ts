// The vault session: turning the browser into a device and unlocking secrets.
//
// This uses fetch (not the app's axios instance) for two reasons: the device
// token must be set explicitly per call (the account-session interceptor would
// otherwise override it), and keeping it dependency-light makes the whole flow
// runnable outside the browser for end-to-end verification. `baseUrl` defaults to
// the same `/api` the rest of the app talks to.

import { generatePairingCode } from '@/lib/pairing-code'
import {
  base64ToBytes,
  bytesToBase64,
  decryptContent,
  decryptRaw,
  generateDeviceIdentity,
  recipientOf,
} from './crypto'

const DEFAULT_BASE = '/api'

// How long a freshly linked browser device asks to live. It heartbeats to extend
// this while in use; if the tab is abandoned (key wiped on lock/close, no more
// heartbeats) the server reaps the device once this elapses — so orphaned browser
// devices don't pile up. Settings will make this configurable (Phase 5).
export const DEFAULT_DEVICE_TTL_SECONDS = 24 * 60 * 60

async function api<T>(
  baseUrl: string,
  path: string,
  init: { method?: string; token?: string; body?: unknown } = {},
): Promise<T> {
  const headers: Record<string, string> = {}
  if (init.body !== undefined) headers['Content-Type'] = 'application/json'
  if (init.token) headers.Authorization = `Bearer ${init.token}`
  const res = await fetch(`${baseUrl}${path}`, {
    method: init.method ?? 'GET',
    headers,
    body: init.body !== undefined ? JSON.stringify(init.body) : undefined,
  })
  if (!res.ok) {
    const detail = await res.text().catch(() => '')
    throw new Error(`${init.method ?? 'GET'} ${path} -> ${res.status} ${detail}`)
  }
  return res.json() as Promise<T>
}

export interface BrowserDevice {
  deviceId: string
  identity: string
  recipient: string
  deviceToken: string
}

/** A friendly name for this browser, e.g. "Firefox on Linux" — shown in the
 *  device list and next to the approval prompt so the user recognises it. */
export function browserLabel(): string {
  const ua = typeof navigator === 'undefined' ? '' : navigator.userAgent
  const browser = /Edg\//.test(ua)
    ? 'Edge'
    : /Firefox\//.test(ua)
      ? 'Firefox'
      : /Chrome\//.test(ua)
        ? 'Chrome'
        : /Safari\//.test(ua)
          ? 'Safari'
          : 'Browser'
  const os = /Windows/.test(ua)
    ? 'Windows'
    : /Mac OS X|Macintosh/.test(ua)
      ? 'Mac'
      : /Android/.test(ua)
        ? 'Android'
        : /iPhone|iPad/.test(ua)
          ? 'iOS'
          : /Linux/.test(ua)
            ? 'Linux'
            : 'this device'
  return `${browser} on ${os}`
}

/** Make this browser a device: mint an invite (account session), join with a
 *  freshly generated keypair, then authenticate via the age challenge to get a
 *  device token. The private key never leaves the tab. */
export async function enrollBrowserDevice(opts: {
  accountToken: string
  deviceName: string
  ttlSeconds?: number
  baseUrl?: string
}): Promise<BrowserDevice> {
  const baseUrl = opts.baseUrl ?? DEFAULT_BASE
  const { identity, recipient } = await generateDeviceIdentity()

  const { code, codeHash } = await generatePairingCode()
  await api(baseUrl, '/enroll/invite', {
    method: 'POST',
    token: opts.accountToken,
    body: { code_hash: codeHash, roster: [] },
  })
  const join = await api<{ device: { id: string } }>(baseUrl, '/enroll/join', {
    method: 'POST',
    body: {
      code_hash: codeHash,
      device_name: opts.deviceName,
      public_key: recipient,
      sign_public_key: '',
      // A self-enrolled browser is its own inviter; no one verifies the mac.
      join_mac: code.slice(0, 8),
      // The browser declares its own lifetime; the server caps and reaps it.
      ttl_seconds: opts.ttlSeconds ?? DEFAULT_DEVICE_TTL_SECONDS,
    },
  })

  // Prove possession of the private key: decrypt the age challenge, return the nonce.
  const challenge = await api<{ challenge: string; challenge_token: string }>(
    baseUrl,
    '/auth/challenge',
    { method: 'POST', body: { public_key: recipient } },
  )
  const nonce = await decryptRaw(base64ToBytes(challenge.challenge), identity)
  const verify = await api<{ access_token: string }>(baseUrl, '/auth/verify', {
    method: 'POST',
    body: { challenge_token: challenge.challenge_token, nonce: bytesToBase64(nonce) },
  })

  return { deviceId: join.device.id, identity, recipient, deviceToken: verify.access_token }
}

/** Re-authenticate an already-enrolled device (e.g. one restored from storage)
 *  for a fresh session token — the age challenge/response, no new enrollment. A
 *  401 here means the device was reaped or revoked; the caller should re-link. */
export async function reauthenticateDevice(opts: {
  identity: string
  baseUrl?: string
}): Promise<string> {
  const baseUrl = opts.baseUrl ?? DEFAULT_BASE
  const recipient = await recipientOf(opts.identity)
  const challenge = await api<{ challenge: string; challenge_token: string }>(
    baseUrl,
    '/auth/challenge',
    { method: 'POST', body: { public_key: recipient } },
  )
  const nonce = await decryptRaw(base64ToBytes(challenge.challenge), opts.identity)
  const verify = await api<{ access_token: string }>(baseUrl, '/auth/verify', {
    method: 'POST',
    body: { challenge_token: challenge.challenge_token, nonce: bytesToBase64(nonce) },
  })
  return verify.access_token
}

/** Extend this device's expiry while it's in active use, so an in-use browser
 *  isn't reaped. Best-effort: a failure (e.g. an expired session token) is left
 *  for the caller to ignore — the worst case is the device expires and re-links. */
export async function heartbeatDevice(opts: {
  token: string
  ttlSeconds?: number
  baseUrl?: string
}): Promise<void> {
  const baseUrl = opts.baseUrl ?? DEFAULT_BASE
  await api(baseUrl, '/devices/heartbeat', {
    method: 'POST',
    token: opts.token,
    body: { ttl_seconds: opts.ttlSeconds ?? DEFAULT_DEVICE_TTL_SECONDS },
  })
}

/** True if `recoveryKey` is the account's recovery key — checked before decrypt so
 *  a wrong key fails instantly and kindly, not after a doomed decrypt. */
export async function isAccountRecoveryKey(opts: {
  accountToken: string
  recoveryKey: string
  baseUrl?: string
}): Promise<boolean> {
  const baseUrl = opts.baseUrl ?? DEFAULT_BASE
  const account = await api<{ recovery_pubkey: string | null }>(baseUrl, '/accounts/me', {
    token: opts.accountToken,
  })
  if (!account.recovery_pubkey) return false
  try {
    return (await recipientOf(opts.recoveryKey)) === account.recovery_pubkey
  } catch {
    return false // not a well-formed age identity
  }
}

export interface DecryptedSecret {
  id: string
  name: string
  folder?: string
  value: Uint8Array
  description?: string
  version: number
}

/** Pull the account's ciphertext and decrypt every live secret with the given
 *  identity — the recovery key today, the device's own key once resharing lands.
 *  Reads /sync/all (account-scoped): the recovery key is a recipient in the
 *  ciphertext but not a device, so the recipient-scoped /changes wouldn't return
 *  anything. Secrets not sealed to this identity are skipped. */
export async function pullAndDecrypt(opts: {
  token: string
  identity: string
  baseUrl?: string
}): Promise<DecryptedSecret[]> {
  const baseUrl = opts.baseUrl ?? DEFAULT_BASE
  const { secrets } = await api<{
    secrets: { id: string; version: number; deleted: boolean; ciphertext_b64: string }[]
  }>(baseUrl, '/sync/all', { token: opts.token })

  const out: DecryptedSecret[] = []
  for (const s of secrets) {
    if (s.deleted) continue
    try {
      const content = await decryptContent(base64ToBytes(s.ciphertext_b64), opts.identity)
      out.push({ id: s.id, version: s.version, ...content })
    } catch {
      // Not sealed to this identity (e.g. created before the recovery key existed).
    }
  }
  return out
}
