import { createContext, useContext } from 'react'
import type { DecryptedSecret } from './session'

export type VaultStatus = 'locked' | 'unlocking' | 'unlocked'

/** State of the approve flow: the browser has enrolled and is waiting for an
 *  existing device to run `goph device approve` and reshare the vault. */
export interface LinkState {
  phase: 'enrolling' | 'awaiting'
  /** How this browser appears in the CLI's approve prompt. */
  deviceName: string
  /** The device id to approve — unambiguous even when names repeat. Null until
   *  enrolled. */
  deviceId: string | null
  /** Key fingerprint to compare against the CLI — null until enrolled. */
  fingerprint: string | null
}

export interface VaultContextValue {
  status: VaultStatus
  secrets: DecryptedSecret[]
  error: string | null
  /** Non-null while linking this browser as a device via the approve flow. */
  link: LinkState | null
  /** Unlock by decrypting the vault with the account recovery key. */
  unlockWithRecoveryKey: (recoveryKey: string) => Promise<void>
  /** Enroll this browser as a device and wait for another device to approve it. */
  linkDevice: () => Promise<void>
  /** Abandon an in-progress approve flow. */
  cancelLink: () => void
  /** Wipe the decryption key and decrypted secrets from memory. */
  lock: () => void
}

export const VaultContext = createContext<VaultContextValue | null>(null)

export function useVault(): VaultContextValue {
  const ctx = useContext(VaultContext)
  if (!ctx) throw new Error('useVault must be used within a VaultProvider')
  return ctx
}
