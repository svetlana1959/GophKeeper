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
  sealContent,
} from './crypto'

const DEFAULT_BASE = '/api'

/** An HTTP error from the vault API, carrying the status so callers can react to
 *  it precisely (e.g. a 401 → the device was reaped) instead of string-matching. */
export class ApiError extends Error {
  readonly status: number
  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

/** True for an authentication failure (device reaped, revoked, or token expired). */
export function isUnauthorized(e: unknown): boolean {
  return e instanceof ApiError && e.status === 401
}

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
    throw new ApiError(res.status, `${init.method ?? 'GET'} ${path} -> ${res.status} ${detail}`)
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

/** Whether this device has been approved — i.e. an existing device published a
 *  vouch cert naming it. This is the approval signal, read from the trust log,
 *  and it does NOT depend on the vault having any secrets to reshare (an empty
 *  vault would otherwise leave the approve poll waiting forever). */
export async function isDeviceApproved(opts: {
  token: string
  deviceId: string
  baseUrl?: string
}): Promise<boolean> {
  const baseUrl = opts.baseUrl ?? DEFAULT_BASE
  const { certs } = await api<{
    certs: { kind: string; subject_id: string }[]
  }>(baseUrl, '/trust/certs', { token: opts.token })
  return certs.some((c) => c.kind === 'vouch' && c.subject_id === opts.deviceId)
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

export interface RestoreProgress {
  done: number
  total: number
}

export interface RestoreResult {
  device: BrowserDevice
  /** The vault, already decrypted during the reseal — the caller shouldn't re-pull. */
  secrets: DecryptedSecret[]
  /** How many secrets couldn't be resealed (a push conflict that survived a retry). */
  failed: number
}

interface PushItem {
  id: string
  ciphertext_b64: string
  base_version: number
  recipients: string[]
}

interface PushResult {
  id: string
  status: string
  version: number
}

async function pushItems(baseUrl: string, token: string, items: PushItem[]): Promise<PushResult[]> {
  const { results } = await api<{ results: PushResult[] }>(baseUrl, '/sync/push', {
    method: 'POST',
    token,
    body: { items },
  })
  return results
}

/** Recovery restore: after unlocking with the recovery key on an account whose
 *  devices have all lapsed, make THIS browser a real device. Enroll it, then
 *  reseal every secret — decrypt with the recovery key, re-seal to the browser's
 *  own key (plus any surviving devices and the recovery key, which stays a
 *  recipient so recovery keeps working) — and push in one batch. Afterwards the
 *  browser decrypts with its own key and can be saved/PIN-protected, so the user
 *  no longer pastes the recovery key each visit. Returns the new device plus the
 *  decrypted vault (so the caller need not re-pull) and how many secrets a push
 *  conflict left un-resealed. */
export async function resealVaultToDevice(opts: {
  accountToken: string
  recoveryKey: string
  deviceName: string
  ttlSeconds?: number
  baseUrl?: string
  onProgress?: (p: RestoreProgress) => void
}): Promise<RestoreResult> {
  const baseUrl = opts.baseUrl ?? DEFAULT_BASE
  const device = await enrollBrowserDevice({
    accountToken: opts.accountToken,
    deviceName: opts.deviceName,
    ttlSeconds: opts.ttlSeconds,
    baseUrl,
  })

  // Reseal to every active device's key (the browser is now among them) plus the
  // recovery key, so recovery still works and no surviving device loses access.
  const recoveryRecipient = await recipientOf(opts.recoveryKey)
  const devices = await api<{ public_key: string; status: string }[]>(baseUrl, '/devices', {
    token: opts.accountToken,
  })
  const recipients = Array.from(
    new Set([
      ...devices.filter((d) => d.status === 'active').map((d) => d.public_key),
      recoveryRecipient,
    ]),
  )

  const { secrets } = await api<{
    secrets: { id: string; version: number; deleted: boolean; ciphertext_b64: string }[]
  }>(baseUrl, '/sync/all', { token: device.deviceToken })
  const live = secrets.filter((s) => !s.deleted)

  // Decrypt and re-seal every secret (skipping any not sealed to the recovery
  // key), collecting the plaintext so the caller doesn't decrypt twice.
  const items: PushItem[] = []
  const decrypted: DecryptedSecret[] = []
  let done = 0
  opts.onProgress?.({ done, total: live.length })
  for (const s of live) {
    try {
      const content = await decryptContent(base64ToBytes(s.ciphertext_b64), opts.recoveryKey)
      items.push({
        id: s.id,
        ciphertext_b64: bytesToBase64(await sealContent(content, recipients)),
        base_version: s.version,
        recipients,
      })
      decrypted.push({ id: s.id, version: s.version, ...content })
    } catch {
      // Not sealed to the recovery key; leave it as-is.
    }
    done += 1
    opts.onProgress?.({ done, total: live.length })
  }

  // One batched push. A conflict (someone edited between our read and write)
  // comes back status:'conflict' with the current version — retry those once at
  // that version rather than silently dropping the secret.
  let failed = 0
  if (items.length > 0) {
    const results = await pushItems(baseUrl, device.deviceToken, items)
    const byId = new Map(items.map((it) => [it.id, it]))
    const retry = results
      .filter((r) => r.status !== 'applied')
      .map((r) => ({ ...byId.get(r.id)!, base_version: r.version }))
    if (retry.length > 0) {
      const retried = await pushItems(baseUrl, device.deviceToken, retry)
      failed = retried.filter((r) => r.status !== 'applied').length
    }
  }
  return { device, secrets: decrypted, failed }
}
