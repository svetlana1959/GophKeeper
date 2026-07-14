import { Loader2, Terminal } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { apiErrorMessage } from '@/api/http'
import { CopyButton } from './components/copy-button'
import type { PendingInvite } from './use-add-device'

/** Second half of the flow: show the pairing code and the CLI command, then wait
 *  for the new device to redeem it. Presentational — the modal owns the polling. */
export function InviteStep({
  invite,
  isCreating,
  error,
  onRetry,
}: {
  invite: PendingInvite | null
  isCreating: boolean
  error: unknown
  onRetry: () => void
}) {
  if (error) {
    return (
      <div className="mt-5 flex flex-col gap-4">
        <p className="text-destructive text-sm">{apiErrorMessage(error)}</p>
        <Button onClick={onRetry}>Try again</Button>
      </div>
    )
  }

  if (isCreating || !invite) {
    return (
      <div className="text-muted-foreground mt-8 flex items-center justify-center gap-2 py-8 text-sm">
        <Loader2 className="size-4 animate-spin" />
        Creating a pairing code…
      </div>
    )
  }

  const command = `goph link ${invite.code}`

  return (
    <div className="mt-5 flex flex-col gap-5">
      <ol className="text-muted-foreground list-decimal space-y-1.5 pl-5 text-sm">
        <li>
          Install the GophKeeper CLI on the new device and run <code>goph login</code>.
        </li>
        <li>Run the command below with the pairing code.</li>
      </ol>

      <div>
        <div className="mb-2 flex items-center justify-between">
          <span className="text-muted-foreground flex items-center gap-1.5 text-xs font-medium">
            <Terminal className="size-3.5" />
            Run on the new device
          </span>
          <CopyButton value={command} label="Copy command" />
        </div>
        <code className="text-foreground bg-muted/60 border-border/60 block rounded-lg border px-3 py-3 font-mono text-xs break-all">
          <span className="text-muted-foreground select-none">$ </span>
          {command}
        </code>
      </div>

      <div className="border-border/60 flex items-center gap-3 rounded-xl border border-dashed px-4 py-3.5">
        <Loader2 className="text-primary size-4 shrink-0 animate-spin" />
        <p className="text-muted-foreground text-sm">
          Waiting for the device to connect… Keep this window open.
        </p>
      </div>
    </div>
  )
}
