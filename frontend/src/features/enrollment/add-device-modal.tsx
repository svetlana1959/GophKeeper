import { useCallback, useEffect, useState } from 'react'
import { CheckCircle2, Loader2 } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { useAccount } from './use-account'
import { useAddDevice } from './use-add-device'
import { RecoveryStep } from './recovery-step'
import { InviteStep } from './invite-step'

type Step = 'loading' | 'recovery' | 'invite' | 'done'

const HEADINGS: Record<Step, { title: string; description: string }> = {
  loading: { title: 'Add a device', description: 'Preparing…' },
  recovery: {
    title: 'Set up your recovery key',
    description: "First, create a recovery key — then we'll link your first device.",
  },
  invite: {
    title: 'Add a device',
    description: 'Link a new device to your account with a one-time pairing code.',
  },
  done: {
    title: 'Device linked',
    description: 'Your new device is now trusted and can sync your secrets.',
  },
}

export function AddDeviceModal({
  open,
  onOpenChange,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const account = useAccount()
  const { invite, createInvite, isCreating, createError, joinedDevice, reset } = useAddDevice()
  // The only stored step state: the user's recovery step is done for this session.
  // Everything else is derived, so no setState-in-effect is needed.
  const [recoveryDone, setRecoveryDone] = useState(false)

  const needsRecovery = account.data?.recovery_pubkey === null && !recoveryDone
  const step: Step = !account.data
    ? 'loading'
    : joinedDevice
      ? 'done'
      : needsRecovery
        ? 'recovery'
        : 'invite'

  // Auto-mint the pairing code the moment the invite step is on screen.
  useEffect(() => {
    if (open && step === 'invite' && !invite && !isCreating && !createError) createInvite()
  }, [open, step, invite, isCreating, createError, createInvite])

  // Reset all flow state on close (an event, not an effect) so the next open is
  // clean and no invites are minted for a closed modal.
  const handleOpenChange = useCallback(
    (next: boolean) => {
      if (!next) {
        setRecoveryDone(false)
        reset()
      }
      onOpenChange(next)
    },
    [onOpenChange, reset],
  )

  const heading = HEADINGS[step]

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{heading.title}</DialogTitle>
          <DialogDescription>{heading.description}</DialogDescription>
        </DialogHeader>

        {step === 'loading' ? (
          <div className="text-muted-foreground flex items-center justify-center gap-2 py-10 text-sm">
            <Loader2 className="size-4 animate-spin" />
            Loading…
          </div>
        ) : step === 'recovery' ? (
          <RecoveryStep onDone={() => setRecoveryDone(true)} />
        ) : step === 'invite' ? (
          <InviteStep
            invite={invite}
            isCreating={isCreating}
            error={createError}
            onRetry={reset}
          />
        ) : (
          <div className="mt-5 flex flex-col items-center gap-4 py-4 text-center">
            <CheckCircle2 className="text-primary size-12" strokeWidth={1.75} />
            <p className="text-foreground font-semibold">
              {joinedDevice?.device_name ?? 'Your device'} is connected.
            </p>
            <Button onClick={() => handleOpenChange(false)} className="w-full">
              Done
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
