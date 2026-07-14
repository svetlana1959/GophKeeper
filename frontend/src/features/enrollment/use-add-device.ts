import { useCallback, useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { accountsApi } from '@/api/accounts'
import { enrollApi } from '@/api/enroll'
import { generatePairingCode } from '@/lib/pairing-code'

const POLL_INTERVAL_MS = 2500

/** Upload the public half of a browser-minted recovery key. The keypair is
 *  generated in the component so its private half can be shown before we persist
 *  the public half here. */
export function useSetRecoveryKey() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (recipient: string) => accountsApi.setRecoveryKey(recipient),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['account'] }),
  })
}

export interface PendingInvite {
  code: string
  inviteId: string
  expiresAt: string
}

/** Create a pairing invite (mint code + hash, register the hash) and then poll
 *  until a device redeems it. Returns the code to display and the joined device. */
export function useAddDevice() {
  const qc = useQueryClient()
  const [invite, setInvite] = useState<PendingInvite | null>(null)

  const create = useMutation({
    mutationFn: async (): Promise<PendingInvite> => {
      const { code, codeHash } = await generatePairingCode()
      const { invite_id, expires_at } = await enrollApi.createInvite(codeHash)
      return { code, inviteId: invite_id, expiresAt: expires_at }
    },
    onSuccess: (pending) => setInvite(pending),
  })

  const proof = useQuery({
    queryKey: ['invite-proof', invite?.inviteId],
    queryFn: () => enrollApi.inviteProof(invite!.inviteId),
    enabled: invite !== null,
    refetchInterval: (query) => (query.state.data?.consumed ? false : POLL_INTERVAL_MS),
  })

  const joined = proof.data?.consumed ? (proof.data.device ?? null) : null

  // Once a device redeems the invite, refresh the (device-token-gated) list so
  // it reflects the new device wherever the backend later serves it to the web.
  useEffect(() => {
    if (joined) qc.invalidateQueries({ queryKey: ['devices'] })
  }, [joined, qc])

  const reset = useCallback(() => {
    setInvite(null)
    create.reset()
  }, [create])

  return {
    invite,
    createInvite: create.mutate,
    isCreating: create.isPending,
    createError: create.error,
    joinedDevice: joined,
    reset,
  }
}
