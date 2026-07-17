import { useState } from 'react'
import { Check, KeyRound, Laptop, Loader2, Lock, Terminal } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useVault } from './vault-context'

export function VaultLockedScreen() {
  const { link } = useVault()
  if (link) return <VaultLinkingScreen />
  return <VaultUnlockScreen />
}

function VaultUnlockScreen() {
  const { unlockWithRecoveryKey, linkDevice, status, error } = useVault()
  const [showRecovery, setShowRecovery] = useState(false)
  const [key, setKey] = useState('')
  const busy = status === 'unlocking'

  const submit = () => {
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

      <Button onClick={() => void linkDevice()} className="w-full">
        <Laptop className="size-4" strokeWidth={2} /> Link this browser
      </Button>

      {!showRecovery ? (
        <button
          type="button"
          onClick={() => setShowRecovery(true)}
          className="text-muted-foreground hover:text-foreground text-sm underline-offset-4 hover:underline"
        >
          No other device? Unlock with your recovery key
        </button>
      ) : (
        <form
          onSubmit={(e) => {
            e.preventDefault()
            submit()
          }}
          className="flex w-full flex-col gap-3"
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
              className="border-input text-foreground placeholder:text-muted-foreground focus-visible:border-primary focus-visible:ring-primary/25 mt-1.5 h-11 w-full rounded-lg border bg-transparent px-3 font-mono text-sm focus-visible:ring-2 focus-visible:outline-none"
            />
          </label>
          <Button type="submit" variant="outline" disabled={!key.trim() || busy} className="w-full">
            {busy ? (
              <>
                <Loader2 className="size-4 animate-spin" /> Unlocking…
              </>
            ) : (
              <>
                <KeyRound className="size-4" strokeWidth={2} /> Unlock with recovery key
              </>
            )}
          </Button>
          <p className="text-muted-foreground text-left text-xs">
            The recovery key is your most powerful key — anyone with it can read everything. It never
            leaves this browser. Prefer approving from another device when you can.
          </p>
        </form>
      )}

      {error ? <p className="text-destructive text-sm">{error}</p> : null}
    </Card>
  )
}

function VaultLinkingScreen() {
  const { link, cancelLink } = useVault()
  if (!link) return null

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
          On a device you already have, run this and confirm the fingerprint matches:
        </p>
      </div>

      <div className="border-border bg-muted/40 flex w-full items-center gap-2 rounded-lg border px-3 py-2.5 text-left font-mono text-sm">
        <Terminal className="text-muted-foreground size-4 shrink-0" strokeWidth={2} />
        <code className="text-foreground truncate">goph device approve "{link.deviceName}"</code>
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
