import { describe, expect, it } from 'vitest'
import { generateRecoveryKeypair } from './recovery-key'

// Runs against Node's Web Crypto (jsdom test env), which supports X25519 — the
// same primitive the browser uses. Asserts the age key shapes; correctness of the
// bech32 mapping against filippo.io/age is covered by bech32.test.ts's pinned
// vectors and out-of-band validation.
describe('generateRecoveryKeypair', () => {
  it('produces a well-formed age recipient and identity', async () => {
    const { recipient, identity } = await generateRecoveryKeypair()

    expect(recipient).toMatch(/^age1[0-9a-z]{58}$/)
    expect(identity).toMatch(/^AGE-SECRET-KEY-1[0-9A-Z]{58}$/)
  })

  it('produces a distinct key each call', async () => {
    const a = await generateRecoveryKeypair()
    const b = await generateRecoveryKeypair()
    expect(a.recipient).not.toBe(b.recipient)
    expect(a.identity).not.toBe(b.identity)
  })
})
