// A pairing code for enrolling a new device. The web mints a high-entropy random
// code and uploads only its SHA-256 hash; the plaintext code is shown to the user
// to type into the CLI on the new device (`goph link <code>`). The server never
// sees the code, so it cannot admit a device on its own.

export interface PairingCode {
  /** The code the user types into the CLI on the new device. */
  code: string
  /** Hex SHA-256 of the code — the only thing sent to the server. */
  codeHash: string
}

function bytesToBase64Url(bytes: Uint8Array): string {
  let bin = ''
  for (const b of bytes) bin += String.fromCharCode(b)
  return btoa(bin).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

function bytesToHex(bytes: Uint8Array): string {
  return Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('')
}

/** Generate a fresh pairing code (~192 bits) and its hash. */
export async function generatePairingCode(): Promise<PairingCode> {
  const raw = crypto.getRandomValues(new Uint8Array(24))
  const code = bytesToBase64Url(raw)
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(code))
  return { code, codeHash: bytesToHex(new Uint8Array(digest)) }
}
