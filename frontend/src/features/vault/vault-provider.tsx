import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { tokenStore } from '@/api/http'
import { deviceFingerprint } from './crypto'
import { VaultContext, type LinkState, type VaultStatus } from './vault-context'
import {
  browserLabel,
  enrollBrowserDevice,
  heartbeatDevice,
  isAccountRecoveryKey,
  pullAndDecrypt,
  type BrowserDevice,
  type DecryptedSecret,
} from './session'

// Auto-lock after inactivity: wipe the decryption key + decrypted secrets from
// memory. MVP holds everything in memory only — a reload locks.
const IDLE_LOCK_MS = 15 * 60 * 1000

// How often to check whether an approving device has reshared the vault to us.
const APPROVE_POLL_MS = 3000

// How often an unlocked browser device tells the server it's still in use, so it
// isn't reaped while open. Well under the declared TTL.
const HEARTBEAT_MS = 5 * 60 * 1000

export function VaultProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<VaultStatus>('locked')
  const [secrets, setSecrets] = useState<DecryptedSecret[]>([])
  const [error, setError] = useState<string | null>(null)
  const [link, setLink] = useState<LinkState | null>(null)

  // The unlock key (recovery key or this browser's device key) stays in a ref,
  // out of React state/devtools. The enrolled device — including its private
  // key — lives here too while the approve flow runs.
  const unlockIdentity = useRef<string | null>(null)
  const device = useRef<BrowserDevice | null>(null)
  const pollAbort = useRef(false)

  const lock = useCallback(() => {
    pollAbort.current = true
    unlockIdentity.current = null
    device.current = null
    setSecrets([])
    setError(null)
    setLink(null)
    setStatus('locked')
  }, [])

  const unlockWithRecoveryKey = useCallback(async (recoveryKey: string) => {
    const accountToken = tokenStore.get()
    if (!accountToken) {
      setError('Your session expired — sign in again.')
      return
    }
    setError(null)
    setStatus('unlocking')
    try {
      if (!(await isAccountRecoveryKey({ accountToken, recoveryKey }))) {
        setError("That's not this account's recovery key.")
        setStatus('locked')
        return
      }
      // The recovery key decrypts everything on its own, so the web doesn't need
      // to become a device to unlock this way — it reads /sync/all with the
      // account token. (Enrolling here would leave a junk device behind on every
      // unlock.) The approve flow is what enrolls a real device.
      const decrypted = await pullAndDecrypt({ token: accountToken, identity: recoveryKey })
      unlockIdentity.current = recoveryKey
      setSecrets(decrypted)
      setStatus('unlocked')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not unlock the vault.')
      setStatus('locked')
    }
  }, [])

  const cancelLink = useCallback(() => {
    pollAbort.current = true
    device.current = null
    setLink(null)
  }, [])

  const linkDevice = useCallback(async () => {
    const accountToken = tokenStore.get()
    if (!accountToken) {
      setError('Your session expired — sign in again.')
      return
    }
    setError(null)
    const deviceName = browserLabel()
    setLink({ phase: 'enrolling', deviceName, deviceId: null, fingerprint: null })
    pollAbort.current = false
    try {
      const enrolled = await enrollBrowserDevice({ accountToken, deviceName })
      if (pollAbort.current) return
      device.current = enrolled
      const fingerprint = await deviceFingerprint(enrolled.recipient)
      setLink({ phase: 'awaiting', deviceName, deviceId: enrolled.deviceId, fingerprint })

      // Wait for an existing device to run `goph device approve`, which vouches
      // for us and reshares the vault. Once anything decrypts under our own key,
      // approval has landed — unlock in memory.
      while (!pollAbort.current) {
        const decrypted = await pullAndDecrypt({
          token: enrolled.deviceToken,
          identity: enrolled.identity,
        })
        if (pollAbort.current) return
        if (decrypted.length > 0) {
          unlockIdentity.current = enrolled.identity
          setSecrets(decrypted)
          setStatus('unlocked')
          setLink(null)
          return
        }
        await new Promise((r) => setTimeout(r, APPROVE_POLL_MS))
      }
    } catch (e) {
      if (pollAbort.current) return
      setError(e instanceof Error ? e.message : 'Could not link this browser.')
      device.current = null
      setLink(null)
    }
  }, [])

  // Keep an unlocked browser device alive while the tab is open. Only devices
  // (approve flow) have a token to beat with; recovery unlock has none.
  useEffect(() => {
    if (status !== 'unlocked' || !device.current) return
    const token = device.current.deviceToken
    const beat = () => void heartbeatDevice({ token }).catch(() => {})
    const timer = setInterval(beat, HEARTBEAT_MS)
    beat()
    return () => clearInterval(timer)
  }, [status])

  // Slide-to-lock on inactivity while unlocked.
  useEffect(() => {
    if (status !== 'unlocked') return
    let timer: ReturnType<typeof setTimeout>
    const reset = () => {
      clearTimeout(timer)
      timer = setTimeout(lock, IDLE_LOCK_MS)
    }
    const events = ['mousemove', 'keydown', 'click', 'scroll', 'visibilitychange']
    events.forEach((e) => window.addEventListener(e, reset))
    reset()
    return () => {
      clearTimeout(timer)
      events.forEach((e) => window.removeEventListener(e, reset))
    }
  }, [status, lock])

  const value = useMemo(
    () => ({ status, secrets, error, link, unlockWithRecoveryKey, linkDevice, cancelLink, lock }),
    [status, secrets, error, link, unlockWithRecoveryKey, linkDevice, cancelLink, lock],
  )
  return <VaultContext.Provider value={value}>{children}</VaultContext.Provider>
}
