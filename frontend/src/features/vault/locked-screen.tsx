import { useState } from 'react'
import { KeyRound, Loader2, Lock } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useVault } from './vault-context'

export function VaultLockedScreen() {
  const { unlockWithRecoveryKey, status, error } = useVault()
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
          This browser decrypts your vault locally — the server never can. Unlock with your recovery
          key to read your secrets in this browser.
        </p>
      </div>

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
            className="border-input text-foreground placeholder:text-muted-foreground focus-visible:border-primary focus-visible:ring-primary/25 mt-1.5 h-11 w-full rounded-lg border bg-transparent px-3 font-mono text-sm focus-visible:ring-2 focus-visible:outline-none"
          />
        </label>
        {error ? <p className="text-destructive text-left text-sm">{error}</p> : null}
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
      </form>

      <p className="text-muted-foreground border-border/60 w-full border-t pt-4 text-xs">
        Your recovery key never leaves this browser. If you lose it and all your devices, your
        secrets can't be recovered — keep it somewhere safe.
      </p>
    </Card>
  )
}
