import { ArrowRight, KeyRound } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useEnrollment } from './enrollment-context'

/** Dashboard empty state shown while an account has no recovery key (and so no
 *  devices yet). Points the user at the combined recovery-key + first-device flow. */
export function RecoveryKeyCallout() {
  const { openAddDevice } = useEnrollment()

  return (
    <Card className="border-primary/25 bg-primary/[0.04] flex flex-col items-start gap-5 p-6 sm:flex-row sm:items-center">
      <div className="bg-primary/10 text-primary flex size-12 shrink-0 items-center justify-center rounded-xl">
        <KeyRound className="size-6" strokeWidth={1.75} />
      </div>
      <div className="min-w-0 flex-1">
        <h2 className="text-foreground text-lg font-bold">Set up your vault</h2>
        <p className="text-muted-foreground mt-1 text-sm">
          Create a recovery key and link your first device. The recovery key is a spare key to your
          secrets — minted in your browser, so only you ever hold it.
        </p>
      </div>
      <Button onClick={openAddDevice} className="shrink-0">
        Get started
        <ArrowRight className="size-4" strokeWidth={2} />
      </Button>
    </Card>
  )
}
