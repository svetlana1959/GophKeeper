// Minimal Bech32 encoder (BIP-173), matching the variant filippo.io/age uses for
// its keys. The checksum is always computed over the *lowercased* HRP; an
// uppercase key (age identities) is produced by uppercasing the whole result.
// Validated byte-for-byte against filippo.io/age v1.3.1.

const CHARSET = 'qpzry9x8gf2tvdw0s3jn54khce6mua7l'
const GENERATOR = [0x3b6a57b2, 0x26508e6d, 0x1ea119fa, 0x3d4233dd, 0x2a1462b3]

function polymod(values: number[]): number {
  let chk = 1
  for (const v of values) {
    const top = chk >> 25
    chk = ((chk & 0x1ffffff) << 5) ^ v
    for (let i = 0; i < 5; i++) if ((top >> i) & 1) chk ^= GENERATOR[i]!
  }
  return chk
}

function hrpExpand(hrp: string): number[] {
  const out: number[] = []
  for (let i = 0; i < hrp.length; i++) out.push(hrp.charCodeAt(i) >> 5)
  out.push(0)
  for (let i = 0; i < hrp.length; i++) out.push(hrp.charCodeAt(i) & 31)
  return out
}

function createChecksum(hrp: string, data: number[]): number[] {
  const mod = polymod([...hrpExpand(hrp), ...data, 0, 0, 0, 0, 0, 0]) ^ 1
  const out: number[] = []
  for (let i = 0; i < 6; i++) out.push((mod >> (5 * (5 - i))) & 31)
  return out
}

/** Regroup a byte stream into 5-bit groups (the Bech32 data part), padding the
 *  final group with zero bits. */
function convertBits(bytes: Uint8Array): number[] {
  let acc = 0
  let bits = 0
  const out: number[] = []
  for (const value of bytes) {
    acc = (acc << 8) | value
    bits += 8
    while (bits >= 5) {
      bits -= 5
      out.push((acc >> bits) & 31)
    }
  }
  if (bits > 0) out.push((acc << (5 - bits)) & 31)
  return out
}

/** Bech32-encode `bytes` under a lowercase `hrp` (e.g. "age", "age-secret-key-"). */
export function bech32Encode(hrp: string, bytes: Uint8Array): string {
  const data = convertBits(bytes)
  const combined = [...data, ...createChecksum(hrp, data)]
  let out = `${hrp}1`
  for (const d of combined) out += CHARSET[d]!
  return out
}
