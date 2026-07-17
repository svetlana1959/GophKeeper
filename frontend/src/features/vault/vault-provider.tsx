import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { tokenStore } from '@/api/http'
import { VaultContext, type VaultStatus } from './vault-context'
import {
  enrollBrowserDevice,
  isAccountRecoveryKey,
  pullAndDecrypt,
  type BrowserDevice,
  type DecryptedSecret,
} from './session'

// Auto-lock after inactivity: wipe the decryption key + decrypted secrets from
// memory. The device enrollment (token) is kept so re-unlock is cheap; only the
// sensitive material goes. MVP holds everything in memory only — a reload locks.
const IDLE_LOCK_MS = 15 * 60 * 1000

function browserLabel(): string {
  const ua = navigator.userAgent
  const browser = /Firefox/.test(ua)
    ? 'Firefox'
    : /Edg/.test(ua)
      ? 'Edge'
      : /Chrome/.test(ua)
        ? 'Chrome'
        : /Safari/.test(ua)
          ? 'Safari'
          : 'Browser'
  const os = /Mac/.test(ua) ? 'Mac' : /Win/.test(ua) ? 'Windows' : /Linux/.test(ua) ? 'Linux' : ''
  return os ? `${browser} on ${os}` : browser
}

export function VaultProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<VaultStatus>('locked')
  const [secrets, setSecrets] = useState<DecryptedSecret[]>([])
  const [error, setError] = useState<string | null>(null)

  // Sensitive material stays in refs, out of React state/devtools.
  const device = useRef<BrowserDevice | null>(null)
  const unlockIdentity = useRef<string | null>(null)

  const lock = useCallback(() => {
    unlockIdentity.current = null
    setSecrets([])
    setError(null)
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
      if (!device.current) {
        device.current = await enrollBrowserDevice({
          accountToken,
          deviceName: browserLabel(),
        })
      }
      const decrypted = await pullAndDecrypt({
        deviceToken: device.current.deviceToken,
        identity: recoveryKey,
      })
      unlockIdentity.current = recoveryKey
      setSecrets(decrypted)
      setStatus('unlocked')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not unlock the vault.')
      setStatus('locked')
    }
  }, [])

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
    () => ({ status, secrets, error, unlockWithRecoveryKey, lock }),
    [status, secrets, error, unlockWithRecoveryKey, lock],
  )
  return <VaultContext.Provider value={value}>{children}</VaultContext.Provider>
}
