import { z } from 'zod'
import { http } from './http'

// Device enrollment, from the web's side. The web mints a pairing code (see
// lib/pairing-code.ts), registers only its hash, and then polls the invite until
// a device redeems it via the CLI. The web has no roster to vouch with — that's
// the CLI's job — so it uploads an empty one.

export const createInviteSchema = z.object({
  invite_id: z.string(),
  expires_at: z.string(),
})
export type CreateInvite = z.infer<typeof createInviteSchema>

export const enrolledDeviceSchema = z.object({
  id: z.string(),
  device_name: z.string(),
})

export const inviteProofSchema = z.object({
  consumed: z.boolean(),
  join_mac: z.string(),
  device: enrolledDeviceSchema.nullable().optional(),
})
export type InviteProof = z.infer<typeof inviteProofSchema>

export const enrollApi = {
  /** Register a client-generated invite by its code hash (empty roster for web). */
  async createInvite(codeHash: string): Promise<CreateInvite> {
    const { data } = await http.post('/api/enroll/invite', { code_hash: codeHash, roster: [] })
    return createInviteSchema.parse(data)
  },

  /** Poll an invite to see whether a device has redeemed it yet. */
  async inviteProof(inviteId: string): Promise<InviteProof> {
    const { data } = await http.get(`/api/enroll/invite/${inviteId}`)
    return inviteProofSchema.parse(data)
  },
}
