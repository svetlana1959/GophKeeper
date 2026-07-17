import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { tokenStore } from '@/api/http'
import { deviceFingerprint } from './crypto'
import {
  clearPendingDevice,
  clearPersistedDevice,
  loadPendingDevice,
  peekPersistedDevice,
  persistDevice,
  savePendingDevice,
  unlockPersistedDevice,
  WrongPinError,
  type PersistedDeviceMeta,
} from './device-store'
import { loadVaultSettings } from './vault-settings'
import { VaultContext, type LinkState, type VaultStatus } from './vault-context'
import {
  browserLabel,
  enrollBrowserDevice,
  heartbeatDevice,
  isAccountRecoveryKey,
  isDeviceApproved,
  isUnauthorized,
  pullAndDecrypt,
  reauthenticateDevice,
  resealVaultToDevice,
  type BrowserDevice,
  type DecryptedSecret,
} from './session'

// Auto-lock after inactivity: wipe the decryption key + decrypted secrets from
// memory. The saved (encrypted) device key survives, so unlocking again is a PIN
// away — no re-link.
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
  const [persisted, setPersisted] = useState<PersistedDeviceMeta | null>(() => peekPersistedDevice())
  const [hasDeviceKey, setHasDeviceKey] = useState(false)
  const [viaRecovery, setViaRecovery] = useState(false)
  const [restoring, setRestoring] = useState<{ done: number; total: number } | null>(null)

  // The unlock key (recovery key or this browser's device key) stays in a ref,
  // out of React state/devtools. The live device — including its private key —
  // lives here too while unlocked or while the approve flow runs.
  const unlockIdentity = useRef<string | null>(null)
  const device = useRef<BrowserDevice | null>(null)
  const pollAbort = useRef(false)

  const lock = useCallback(() => {
    pollAbort.current = true
    unlockIdentity.current = null
    device.current = null
    setHasDeviceKey(false)
    setViaRecovery(false)
    setRestoring(null)
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
      setViaRecovery(true)
      setStatus('unlocked')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not unlock the vault.')
      setStatus('locked')
    }
  }, [])

  const restoreAsDevice = useCallback(async () => {
    const accountToken = tokenStore.get()
    const recoveryKey = unlockIdentity.current
    if (!accountToken || !recoveryKey) return
    setError(null)
    setRestoring({ done: 0, total: 0 })
    try {
      const settings = loadVaultSettings()
      const { device: dev, secrets: resealed } = await resealVaultToDevice({
        accountToken,
        recoveryKey,
        deviceName: browserLabel(),
        ttlSeconds: settings.ttlSeconds,
        onProgress: (p) => setRestoring(p),
      })
      device.current = dev
      unlockIdentity.current = dev.identity
      // reseal already decrypted the vault; use it rather than re-pulling.
      setSecrets(resealed)
      setViaRecovery(false)
      setHasDeviceKey(true) // last, so the heartbeat effect sees device.current set
      if (settings.persist) {
        await persistDevice(dev, { ttlSeconds: settings.ttlSeconds })
        setPersisted(peekPersistedDevice())
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not make this browser a device.')
    } finally {
      setRestoring(null)
    }
  }, [])

  const unlockWithSavedDevice = useCallback(async (pin?: string) => {
    setError(null)
    setStatus('unlocking')
    try {
      const saved = await unlockPersistedDevice(pin) // throws WrongPinError
      const token = await reauthenticateDevice({ identity: saved.identity }) // may 401
      const decrypted = await pullAndDecrypt({ token, identity: saved.identity })
      device.current = {
        deviceId: saved.deviceId,
        identity: saved.identity,
        recipient: saved.recipient,
        deviceToken: token,
      }
      unlockIdentity.current = saved.identity
      setHasDeviceKey(true)
      setSecrets(decrypted)
      setStatus('unlocked')
    } catch (e) {
      if (e instanceof WrongPinError) {
        setError(e.message)
        setStatus('locked')
        return
      }
      if (isUnauthorized(e)) {
        // The device was reaped or revoked server-side; the saved key is dead.
        clearPersistedDevice()
        setPersisted(null)
        setError('This browser is no longer linked — link it again.')
        setStatus('locked')
        return
      }
      setError(e instanceof Error ? e.message : 'Could not unlock the vault.')
      setStatus('locked')
    }
  }, [])

  const cancelLink = useCallback(() => {
    pollAbort.current = true
    device.current = null
    setLink(null)
  }, [])

  const linkDevice = useCallback(async (pin?: string) => {
    const accountToken = tokenStore.get()
    if (!accountToken) {
      setError('Your session expired — sign in again.')
      return
    }
    setError(null)
    const deviceName = browserLabel()
    const settings = loadVaultSettings()
    pollAbort.current = false

    // Reuse this browser's pending device across link attempts so re-linking
    // (cancel, reload, re-click) doesn't spawn a fresh device row each time — one
    // browser stays one device. A browser can't read a MAC or any stable hardware
    // id, so its own persisted keypair *is* its identity.
    const enrollFresh = async () => {
      const d = await enrollBrowserDevice({ accountToken, deviceName, ttlSeconds: settings.ttlSeconds })
      savePendingDevice({ deviceId: d.deviceId, identity: d.identity, recipient: d.recipient })
      return d
    }
    const pending = loadPendingDevice()
    setLink({
      phase: 'enrolling',
      deviceName,
      deviceId: pending?.deviceId ?? null,
      fingerprint: null,
    })
    try {
      let enrolled: BrowserDevice
      if (pending) {
        try {
          const token = await reauthenticateDevice({ identity: pending.identity })
          enrolled = { ...pending, deviceToken: token }
        } catch (e) {
          if (!isUnauthorized(e)) throw e
          // The pending device was reaped server-side; start clean.
          clearPendingDevice()
          enrolled = await enrollFresh()
        }
      } else {
        enrolled = await enrollFresh()
      }
      if (pollAbort.current) return
      device.current = enrolled
      const fingerprint = await deviceFingerprint(enrolled.recipient)
      setLink({ phase: 'awaiting', deviceName, deviceId: enrolled.deviceId, fingerprint })

      // Wait for an existing device to run `goph device approve`, which vouches
      // for us (a trust cert) and reshares the vault. We watch the trust log for
      // that vouch — not for decrypted secrets, since an empty vault has nothing
      // to reshare and would leave us waiting forever.
      while (!pollAbort.current) {
        const approved = await isDeviceApproved({
          token: enrolled.deviceToken,
          deviceId: enrolled.deviceId,
        })
        if (pollAbort.current) return
        if (approved) {
          const decrypted = await pullAndDecrypt({
            token: enrolled.deviceToken,
            identity: enrolled.identity,
          })
          if (pollAbort.current) return
          unlockIdentity.current = enrolled.identity
          setSecrets(decrypted)
          clearPendingDevice() // approved — no longer just "pending"
          if (settings.persist) {
            await persistDevice(enrolled, { pin, ttlSeconds: settings.ttlSeconds })
            setPersisted(peekPersistedDevice())
          }
          setStatus('unlocked')
          setLink(null)
          setHasDeviceKey(true) // last, so the heartbeat effect sees device.current
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

  const saveDevice = useCallback(async (pin?: string) => {
    if (!device.current) throw new Error('No device key to save — link this browser first.')
    const settings = loadVaultSettings()
    await persistDevice(device.current, { pin, ttlSeconds: settings.ttlSeconds })
    setPersisted(peekPersistedDevice())
  }, [])

  const forgetDevice = useCallback(() => {
    clearPersistedDevice()
    setPersisted(null)
  }, [])

  // Keep an unlocked browser device alive while the tab is open. Only devices
  // (link / saved-device / restore) have a token to beat with; recovery unlock
  // has none — hence the hasDeviceKey dependency, which also (re)starts the beat
  // when a recovery unlock is later restored into a device.
  useEffect(() => {
    if (status !== 'unlocked' || !device.current) return
    let cancelled = false
    const beat = async () => {
      const dev = device.current
      if (!dev) return
      try {
        await heartbeatDevice({ token: dev.deviceToken })
      } catch (e) {
        // The device session token expires well before the device TTL; on a 401
        // re-authenticate with the device's own key for a fresh token and retry,
        // so a long-open tab keeps extending its expiry.
        if (cancelled || !isUnauthorized(e) || !device.current) return
        try {
          const token = await reauthenticateDevice({ identity: device.current.identity })
          if (cancelled || !device.current) return
          device.current = { ...device.current, deviceToken: token }
          await heartbeatDevice({ token })
        } catch {
          // Give up this tick; the next interval tries again.
        }
      }
    }
    const timer = setInterval(() => void beat(), HEARTBEAT_MS)
    void beat()
    return () => {
      cancelled = true
      clearInterval(timer)
    }
  }, [status, hasDeviceKey])

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
    () => ({
      status,
      secrets,
      error,
      link,
      persisted,
      // Can save the current device key, or add a PIN to an unprotected one.
      canPersist: hasDeviceKey && (persisted === null || !persisted.protected),
      viaRecovery,
      restoring,
      unlockWithRecoveryKey,
      restoreAsDevice,
      unlockWithSavedDevice,
      linkDevice,
      cancelLink,
      saveDevice,
      forgetDevice,
      lock,
    }),
    [
      status,
      secrets,
      error,
      link,
      persisted,
      hasDeviceKey,
      viaRecovery,
      restoring,
      unlockWithRecoveryKey,
      restoreAsDevice,
      unlockWithSavedDevice,
      linkDevice,
      cancelLink,
      saveDevice,
      forgetDevice,
      lock,
    ],
  )
  return <VaultContext.Provider value={value}>{children}</VaultContext.Provider>
}
