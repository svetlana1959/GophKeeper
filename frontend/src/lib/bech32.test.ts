import { describe, expect, it } from 'vitest'
import { bech32Encode } from './bech32'

// Pinned vectors: the all-zero 32-byte key. Both strings parse cleanly in
// filippo.io/age (verified out-of-band), which is the format this must match.
describe('bech32Encode', () => {
  const zeros = new Uint8Array(32)

  it('encodes an age recipient (all-zero key)', () => {
    expect(bech32Encode('age', zeros)).toBe(
      'age1qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq5cu47z',
    )
  })

  it('encodes an age secret key, uppercased (all-zero key)', () => {
    expect(bech32Encode('age-secret-key-', zeros).toUpperCase()).toBe(
      'AGE-SECRET-KEY-1QQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQ8H00W3',
    )
  })

  it('is deterministic', () => {
    const bytes = new Uint8Array(32).fill(7)
    expect(bech32Encode('age', bytes)).toBe(bech32Encode('age', bytes))
  })
})
