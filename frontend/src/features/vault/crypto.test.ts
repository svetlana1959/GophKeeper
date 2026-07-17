import { describe, expect, it } from 'vitest'
import { decryptContent, generateDeviceIdentity, recipientOf, sealContent } from './crypto'

function base64ToBytes(b64: string): Uint8Array {
  const bin = atob(b64)
  const out = new Uint8Array(bin.length)
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i)
  return out
}

// A real secret produced by the Go CLI stack (filippo.io/age over the CLI's
// `content` JSON, whose []byte Value is base64 in JSON). Decrypting this in the
// app's build proves the browser can read actual CLI-sealed secrets — not just
// its own round-trips. Regenerate with the Go fixture if the format ever changes.
const CLI_IDENTITY = 'AGE-SECRET-KEY-18FP4YL6RKQ6S3GK9Y2HQW2T07QY4JN37A2J8SWFEA8XS9NEQ88JQ4809GF'
const CLI_CIPHERTEXT = base64ToBytes(
  'YWdlLWVuY3J5cHRpb24ub3JnL3YxCi0+IFgyNTUxOSBZQnZCYkV3ajFwNXZkSWJxNWppN1lEVTFoRFF3Q1FsKzN3eUp5THk4bG1rCjF0b3dMaHZMYzIvSTdLUjgreUVib1dqenZka0NHMFFNbVR1YjlSSTN5WEUKLS0tIGREMmllTzlrSDNUQ08rcmJlQ3JycDgrOWpGMCtNanN5alBQWVNBVmhUUVEKAfHCz390pRs62N7WOndY9BoQN7OAwdMntstf9hAjvrUdoCRKD9woTcM7ZUTz8oTWadkCQMZukz2zSA0SHOp7O+15SPec5GstLasIgz2uob0ExBzlhlAZ/kXiwX8+fMxsbj3n+U8+DuWgBLxq7V2h7p12YjOsaf0bjun/iSdo7olpKQs=',
)

describe('vault crypto', () => {
  it('decrypts a real CLI-produced secret (content JSON + base64 value)', async () => {
    const content = await decryptContent(CLI_CIPHERTEXT, CLI_IDENTITY)
    expect(content.name).toBe('github')
    expect(content.folder).toBe('work')
    expect(content.description).toBe('work token')
    expect(new TextDecoder().decode(content.value)).toBe('ghp_secret_token_123')
  })

  it('round-trips a secret sealed to a browser-generated device key', async () => {
    const device = await generateDeviceIdentity()
    expect(device.recipient).toMatch(/^age1[0-9a-z]+$/)
    expect(device.identity).toMatch(/^AGE-SECRET-KEY-1/)

    const ciphertext = await sealContent(
      { name: 'gmail', value: new TextEncoder().encode('hunter2'), folder: 'personal' },
      [device.recipient],
    )
    const content = await decryptContent(ciphertext, device.identity)
    expect(content.name).toBe('gmail')
    expect(content.folder).toBe('personal')
    expect(new TextDecoder().decode(content.value)).toBe('hunter2')
  })

  it('recipientOf recovers the public half (recovery-key validation)', async () => {
    const device = await generateDeviceIdentity()
    expect(await recipientOf(device.identity)).toBe(device.recipient)
  })
})
