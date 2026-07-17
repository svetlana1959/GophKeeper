import { createContext, useContext } from 'react'
import type { DecryptedSecret } from './session'

export type VaultStatus = 'locked' | 'unlocking' | 'unlocked'

export interface VaultContextValue {
  status: VaultStatus
  secrets: DecryptedSecret[]
  error: string | null
  /** Unlock by decrypting the vault with the account recovery key. */
  unlockWithRecoveryKey: (recoveryKey: string) => Promise<void>
  /** Wipe the decryption key and decrypted secrets from memory. */
  lock: () => void
}

export const VaultContext = createContext<VaultContextValue | null>(null)

export function useVault(): VaultContextValue {
  const ctx = useContext(VaultContext)
  if (!ctx) throw new Error('useVault must be used within a VaultProvider')
  return ctx
}
