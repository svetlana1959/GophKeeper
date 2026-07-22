import { useState } from 'react'
import { Check, KeyRound, Laptop, Loader2, Lock, ShieldCheck, Terminal } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { CopyButton } from '@/features/enrollment/components/copy-button'
import { useVault } from './vault-context'

export function VaultLockedScreen() {
  const { link, persisted } = useVault()
  if (link) return <VaultLinkingScreen />
  if (persisted) return <VaultSavedDeviceScreen />
  return <VaultUnlockScreen />
}

const PIN_INPUT_CLASS =
  'border-input text-foreground placeholder:text-muted-foreground focus-visible:border-primary focus-visible:ring-primary/25 mt-1.5 h-11 w-full rounded-lg border bg-transparent px-3 font-mono text-sm focus-visible:ring-2 focus-visible:outline-none'

function VaultSavedDeviceScreen() {
  const { persisted, unlockWithSavedDevice, forgetDevice, status, error } = useVault()
  const [pin, setPin] = useState('')
  const busy = status === 'unlocking'
  const needsPin = persisted?.protected ?? false

  const submit = () => {
    if (busy) return
    if (needsPin && !pin.trim()) return
    void unlockWithSavedDevice(needsPin ? pin.trim() : undefined)
  }

  return (
    <Card className="mx-auto flex max-w-xl flex-col items-center gap-6 p-8 text-center">
      <span className="bg-primary/10 text-primary flex size-14 items-center justify-center rounded-2xl">
        <ShieldCheck className="size-7" strokeWidth={1.75} />
      </span>
      <div>
        <h2 className="text-foreground text-xl font-bold">Unlock this browser</h2>
        <p className="text-muted-foreground mt-2 text-sm">
          This browser is already linked as a device.{' '}
          {needsPin ? 'Enter your PIN to unlock.' : 'Unlock to read your secrets.'}
        </p>
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault()
          submit()
        }}
        className="flex w-full flex-col gap-3"
      >
        {needsPin ? (
          <label className="text-left">
            <span className="text-foreground text-sm font-medium">PIN</span>
            <input
              type="password"
              inputMode="numeric"
              value={pin}
              onChange={(e) => setPin(e.target.value)}
              placeholder="••••"
              autoComplete="off"
              autoFocus
              className={PIN_INPUT_CLASS}
            />
          </label>
        ) : null}
        {error ? <p className="text-destructive text-left text-sm">{error}</p> : null}
        <Button type="submit" disabled={busy || (needsPin && !pin.trim())} className="w-full">
          {busy ? (
            <>
              <Loader2 className="size-4 animate-spin" /> Unlocking…
            </>
          ) : (
            <>
              <KeyRound className="size-4" strokeWidth={2} /> Unlock vault
            </>
          )}
        </Button>
      </form>

      {!needsPin ? (
        <p className="text-muted-foreground text-xs">
          This browser stays signed in without a PIN — anyone using this device can open your vault.
          Add a PIN in Settings.
        </p>
      ) : null}

      <button
        type="button"
        onClick={forgetDevice}
        className="text-muted-foreground hover:text-foreground border-border/60 w-full border-t pt-4 text-xs underline-offset-4 hover:underline"
      >
        Not you? Forget this browser and start over
      </button>
    </Card>
  )
}

function VaultUnlockScreen() {
  const { unlockWithRecoveryKey, linkDevice, status, error } = useVault()
  const [showRecovery, setShowRecovery] = useState(false)
  const [key, setKey] = useState('')
  const busy = status === 'unlocking'

  const submitRecovery = () => {
    if (key.trim() && !busy) void unlockWithRecoveryKey(key.trim())
  }

  return (
    <Card className="mx-auto flex max-w-xl flex-col items-center gap-6 p-8 text-center">
      <span className="bg-primary/10 text-primary flex size-14 items-center justify-center rounded-2xl">
        <Lock className="size-7" strokeWidth={1.75} />
      </span>
      <div>
        <h2 className="text-foreground text-xl font-bold">Your secrets are locked</h2>
        <p className="text-muted-foreground mt-2 text-sm">
          This browser decrypts your vault locally — the server never can. Link it as a device and
          approve it from a device you already have.
        </p>
      </div>

      <div className="flex w-full flex-col gap-3">
        <Button onClick={() => void linkDevice()} className="w-full">
          <Laptop className="size-4" strokeWidth={2} /> Link this browser
        </Button>
        {!showRecovery ? (
          <Button
            variant="outline"
            onClick={() => setShowRecovery(true)}
            className="w-full"
          >
            <KeyRound className="size-4" strokeWidth={2} /> Unlock with recovery key
          </Button>
        ) : (
          <form
            onSubmit={(e) => {
              e.preventDefault()
              submitRecovery()
            }}
            className="border-border/60 flex flex-col gap-3 border-t pt-4"
          >
            <label className="text-left">
              <span className="text-foreground text-sm font-medium">Recovery key</span>
              <input
                type="password"
                value={key}
                onChange={(e) => setKey(e.target.value)}
                placeholder="AGE-SECRET-KEY-1…"
                autoComplete="off"
                spellCheck={false}
                autoFocus
                className={PIN_INPUT_CLASS}
              />
            </label>
            <Button type="submit" disabled={!key.trim() || busy} className="w-full">
              {busy ? (
                <>
                  <Loader2 className="size-4 animate-spin" /> Unlocking…
                </>
              ) : (
                <>
                  <KeyRound className="size-4" strokeWidth={2} /> Unlock vault
                </>
              )}
            </Button>
            <p className="text-muted-foreground text-left text-xs">
              Your most powerful key — anyone with it can read everything. It never leaves this
              browser. Prefer approving from another device when you can.
            </p>
          </form>
        )}
      </div>

      <p className="text-muted-foreground border-border/60 w-full border-t pt-4 text-xs">
        Once linked, this browser stays signed in. Add a PIN in Settings to protect the key it saves
        here.
      </p>

      {error ? <p className="text-destructive text-sm">{error}</p> : null}
    </Card>
  )
}

function VaultLinkingScreen() {
  const { link, cancelLink } = useVault()
  if (!link) return null

  // Approve by id, not name — a browser's name ("Firefox on Linux") repeats
  // across re-links, so the CLI can't resolve it unambiguously.
  const command = link.deviceId ? `goph device approve ${link.deviceId}` : 'goph device approve …'

  return (
    <Card className="mx-auto flex max-w-xl flex-col items-center gap-6 p-8 text-center">
      <span className="bg-primary/10 text-primary flex size-14 items-center justify-center rounded-2xl">
        <Loader2 className="size-7 animate-spin" strokeWidth={1.75} />
      </span>
      <div>
        <h2 className="text-foreground text-xl font-bold">
          {link.phase === 'enrolling' ? 'Linking this browser…' : 'Waiting for approval'}
        </h2>
        <p className="text-muted-foreground mt-2 text-sm">
          This browser is <span className="text-foreground font-medium">{link.deviceName}</span>. On
          a device you already have, run this and confirm the fingerprint matches:
        </p>
      </div>

      <div className="border-border bg-muted/40 flex w-full items-center gap-2 rounded-lg border px-3 py-2.5 text-left font-mono text-sm">
        <Terminal className="text-muted-foreground size-4 shrink-0" strokeWidth={2} />
        <code className="text-foreground grow truncate">{command}</code>
        {link.deviceId ? <CopyButton value={command} className="shrink-0" /> : null}
      </div>

      <div className="text-left">
        <span className="text-muted-foreground text-xs">Fingerprint</span>
        <p className="text-foreground font-mono text-2xl font-semibold tracking-wide">
          {link.fingerprint ?? '········'}
        </p>
        <p className="text-muted-foreground mt-1 text-xs">
          It must match the fingerprint the CLI shows before you approve.
        </p>
      </div>

      <div className="text-muted-foreground flex items-center gap-2 text-sm">
        <Check className="text-primary size-4" strokeWidth={2} />
        This browser unlocks automatically once approved.
      </div>

      <Button variant="outline" onClick={cancelLink} className="w-full">
        Cancel
      </Button>
    </Card>
  )
}
