// Client-side vault crypto. This is what makes the browser a real device: it
// generates its own age keypair and decrypts secret payloads locally. The server
// only ever sees ciphertext — decryption happens here, in memory.
//
// Interop with the CLI (filippo.io/age) is via age-encryption, the age author's
// TypeScript implementation (validated round-trip, both directions). A secret's
// age ciphertext wraps a JSON `content` blob produced by the CLI:
//   { name, folder?, value (base64), description? }   (see cli/internal/app/app.go)

import { Decrypter, Encrypter, generateX25519Identity, identityToRecipient } from 'age-encryption'

/** A secret's plaintext, as it lives inside the age ciphertext. */
export interface SecretContent {
  name: string
  folder?: string
  value: Uint8Array
  description?: string
}

/** An age keypair. `identity` (AGE-SECRET-KEY-1…) is held only in memory;
 *  `recipient` (age1…) is what other devices seal to. */
export interface DeviceIdentity {
  identity: string
  recipient: string
}

export function base64ToBytes(b64: string): Uint8Array {
  const bin = atob(b64)
  const out = new Uint8Array(bin.length)
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i)
  return out
}

export function bytesToBase64(bytes: Uint8Array): string {
  let bin = ''
  for (const b of bytes) bin += String.fromCharCode(b)
  return btoa(bin)
}

/** Generate a fresh browser device keypair. The private half never leaves the tab. */
export async function generateDeviceIdentity(): Promise<DeviceIdentity> {
  const identity = await generateX25519Identity()
  const recipient = await identityToRecipient(identity)
  return { identity, recipient }
}

/** Derive the recipient (public half) of an age identity — used to check a pasted
 *  recovery key against the account's stored recovery_pubkey before decrypting. */
export async function recipientOf(identity: string): Promise<string> {
  return identityToRecipient(identity)
}

/** A short, human-readable fingerprint of a device's public key. Must match the
 *  CLI's `fingerprint()` (sha256 of the recipient string, first four bytes as
 *  aabb·ccdd) so the user can compare the two by eye when approving. */
export async function deviceFingerprint(recipient: string): Promise<string> {
  const digest = new Uint8Array(
    await crypto.subtle.digest('SHA-256', new TextEncoder().encode(recipient)),
  )
  const hex = (i: number) => (digest[i] ?? 0).toString(16).padStart(2, '0')
  return `${hex(0)}${hex(1)}·${hex(2)}${hex(3)}`
}

/** Decrypt age ciphertext to raw bytes (e.g. the auth challenge nonce, which is
 *  not a content blob). */
export async function decryptRaw(ciphertext: Uint8Array, identity: string): Promise<Uint8Array> {
  const decrypter = new Decrypter()
  decrypter.addIdentity(identity)
  return decrypter.decrypt(ciphertext)
}

/** Decrypt a secret's age ciphertext with an identity, returning its content. */
export async function decryptContent(
  ciphertext: Uint8Array,
  identity: string,
): Promise<SecretContent> {
  const plain = await decryptRaw(ciphertext, identity)
  const json = JSON.parse(new TextDecoder().decode(plain))
  return {
    name: json.name,
    folder: json.folder || undefined,
    value: base64ToBytes(json.value),
    description: json.description || undefined,
  }
}

/** Seal content to a recipient set — used when resealing the vault to a new
 *  device (approval) or recovering it (bootstrap). Produces binary age. */
export async function sealContent(
  content: SecretContent,
  recipients: string[],
): Promise<Uint8Array> {
  const json = JSON.stringify({
    name: content.name,
    folder: content.folder,
    value: bytesToBase64(content.value),
    description: content.description,
  })
  const encrypter = new Encrypter()
  for (const r of recipients) encrypter.addRecipient(r)
  return encrypter.encrypt(new TextEncoder().encode(json))
}
