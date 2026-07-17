import { createContext, useContext } from 'react'
import type { DecryptedSecret } from './session'
import type { PersistedDeviceMeta } from './device-store'

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
  /** This browser's saved device, if it was persisted for reload-free unlock. */
  persisted: PersistedDeviceMeta | null
  /** True when there's a device key in memory that can be saved, or a PIN added
   *  to an unprotected saved key. False after a device-free recovery unlock. */
  canPersist: boolean
  /** Unlock by decrypting the vault with the account recovery key. */
  unlockWithRecoveryKey: (recoveryKey: string) => Promise<void>
  /** Unlock using this browser's saved device key. PIN required iff protected. */
  unlockWithSavedDevice: (pin?: string) => Promise<void>
  /** Enroll this browser as a device and wait for another device to approve it.
   *  On success, if persistence is enabled, saves the key (PIN-encrypted if given). */
  linkDevice: (pin?: string) => Promise<void>
  /** Abandon an in-progress approve flow. */
  cancelLink: () => void
  /** Save the current device key on this browser so reloads skip re-linking.
   *  A PIN encrypts it at rest; omit it to store unprotected (opt-out). */
  saveDevice: (pin?: string) => Promise<void>
  /** Forget the saved device on this browser (clears local key material). */
  forgetDevice: () => void
  /** Wipe the decryption key and decrypted secrets from memory. */
  lock: () => void
}

export const VaultContext = createContext<VaultContextValue | null>(null)

export function useVault(): VaultContextValue {
  const ctx = useContext(VaultContext)
  if (!ctx) throw new Error('useVault must be used within a VaultProvider')
  return ctx
}
