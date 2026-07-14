// In-browser generation of the account's recovery key — an age (X25519) keypair.
//
// The recovery key is a standing recipient every secret is also sealed to, so a
// user who loses all their devices can still recover. Zero-knowledge means the
// private half must never reach the server: we mint the pair with Web Crypto,
// upload only the `age1…` public recipient, and show the `AGE-SECRET-KEY-1…`
// private identity to the user exactly once.
//
// The bech32 mapping is validated against filippo.io/age (see lib/bech32.ts).

import { bech32Encode } from './bech32'

export interface RecoveryKeypair {
  /** The `age1…` public recipient. Safe to upload — this is what the server stores. */
  recipient: string
  /** The `AGE-SECRET-KEY-1…` private identity. Shown once, never sent anywhere. */
  identity: string
}

function base64UrlToBytes(s: string): Uint8Array {
  const b64 = s.replace(/-/g, '+').replace(/_/g, '/')
  const bin = atob(b64)
  const out = new Uint8Array(bin.length)
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i)
  return out
}

/** True if this browser can mint a recovery key (Web Crypto + X25519). */
export async function recoveryKeySupported(): Promise<boolean> {
  if (!globalThis.crypto?.subtle) return false
  try {
    await crypto.subtle.generateKey({ name: 'X25519' }, true, ['deriveBits'])
    return true
  } catch {
    return false
  }
}

/** Generate a fresh age recovery keypair. The private key never leaves the tab. */
export async function generateRecoveryKeypair(): Promise<RecoveryKeypair> {
  const pair = (await crypto.subtle.generateKey({ name: 'X25519' }, true, [
    'deriveBits',
  ])) as CryptoKeyPair
  const pubJwk = await crypto.subtle.exportKey('jwk', pair.publicKey)
  const privJwk = await crypto.subtle.exportKey('jwk', pair.privateKey)
  if (!pubJwk.x || !privJwk.d) throw new Error('key export failed')

  const pub = base64UrlToBytes(pubJwk.x)
  const priv = base64UrlToBytes(privJwk.d)

  // age computes the bech32 checksum over the lowercased HRP, then uppercases the
  // whole identity string — so we encode with a lowercase HRP and uppercase here.
  return {
    recipient: bech32Encode('age', pub),
    identity: bech32Encode('age-secret-key-', priv).toUpperCase(),
  }
}
