import { useCallback, useState } from 'react'
import { AlertTriangle, Download, KeyRound, ShieldCheck } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { apiErrorMessage } from '@/api/http'
import { generateRecoveryKeypair, type RecoveryKeypair } from '@/lib/recovery-key'
import { useSetRecoveryKey } from './use-add-device'
import { CopyButton } from './components/copy-button'

function downloadIdentity(identity: string) {
  const blob = new Blob([`${identity}\n`], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'gophkeeper-recovery-key.txt'
  a.click()
  URL.revokeObjectURL(url)
}

/** First half of the first-device flow: mint an age recovery key in the browser,
 *  show its private half exactly once, and upload only the public half. */
export function RecoveryStep({ onDone }: { onDone: () => void }) {
  const [keypair, setKeypair] = useState<RecoveryKeypair | null>(null)
  const [generating, setGenerating] = useState(false)
  const [genError, setGenError] = useState<string | null>(null)
  const [confirmed, setConfirmed] = useState(false)
  const save = useSetRecoveryKey()

  const generate = useCallback(async () => {
    setGenError(null)
    setGenerating(true)
    try {
      setKeypair(await generateRecoveryKeypair())
    } catch {
      setGenError('Your browser could not generate a recovery key. Try a current browser.')
    } finally {
      setGenerating(false)
    }
  }, [])

  const persist = useCallback(() => {
    if (keypair) save.mutate(keypair.recipient, { onSuccess: onDone })
  }, [keypair, save, onDone])

  if (!keypair) {
    return (
      <div className="mt-5 flex flex-col gap-5">
        <div className="bg-primary/[0.07] flex items-start gap-3 rounded-xl p-4">
          <ShieldCheck className="text-primary mt-0.5 size-5 shrink-0" strokeWidth={2} />
          <p className="text-muted-foreground text-sm">
            Your recovery key is a spare key to your vault. Every secret is also sealed to it, so
            you can get back in even if you lose all your devices. It's generated here in your
            browser — we only ever store its public half.
          </p>
        </div>
        {genError ? <p className="text-destructive text-sm">{genError}</p> : null}
        <Button onClick={generate} disabled={generating}>
          <KeyRound className="size-4" strokeWidth={2} />
          {generating ? 'Generating…' : 'Generate recovery key'}
        </Button>
      </div>
    )
  }

  return (
    <div className="mt-5 flex flex-col gap-5">
      <div>
        <div className="mb-2 flex items-center justify-between">
          <span className="text-foreground text-sm font-semibold">Your recovery key</span>
          <div className="flex items-center gap-4">
            <CopyButton value={keypair.identity} />
            <button
              type="button"
              onClick={() => downloadIdentity(keypair.identity)}
              className="text-muted-foreground hover:text-foreground inline-flex items-center gap-1.5 text-sm font-medium transition-colors"
            >
              <Download className="size-4" />
              Download
            </button>
          </div>
        </div>
        <code className="text-foreground bg-muted/60 border-border/60 block rounded-lg border px-3 py-3 font-mono text-xs break-all">
          {keypair.identity}
        </code>
      </div>

      <div className="bg-destructive/[0.07] flex items-start gap-3 rounded-xl p-4">
        <AlertTriangle className="text-destructive mt-0.5 size-5 shrink-0" strokeWidth={2} />
        <p className="text-muted-foreground text-sm">
          This is the only time we'll show it. Save it in a password manager or somewhere safe — if
          you lose it and all your devices, your secrets can't be recovered.
        </p>
      </div>

      <label className="flex cursor-pointer items-center gap-3 text-sm select-none">
        <input
          type="checkbox"
          checked={confirmed}
          onChange={(e) => setConfirmed(e.target.checked)}
          className="border-input text-primary focus-visible:ring-primary/40 size-4 rounded"
        />
        <span className="text-foreground">I've saved my recovery key somewhere safe.</span>
      </label>

      {save.error ? <p className="text-destructive text-sm">{apiErrorMessage(save.error)}</p> : null}

      <Button onClick={persist} disabled={!confirmed || save.isPending}>
        {save.isPending ? 'Saving…' : 'Continue'}
      </Button>
    </div>
  )
}
