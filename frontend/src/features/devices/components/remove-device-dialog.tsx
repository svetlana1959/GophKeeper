import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Loader2, Trash2 } from 'lucide-react'
import { tokenStore } from '@/api/http'
import { devicesApi, type Device } from '@/api/devices'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { isAccountRecoveryKey } from '@/features/vault/session'

/** Remove a device, gated behind the account recovery key. Removing a device is
 *  destructive, so we require proof the caller holds the master key — the same
 *  key that could restore access afterwards. */
export function RemoveDeviceDialog({
  device,
  open,
  onOpenChange,
}: {
  device: Device
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const qc = useQueryClient()
  const [key, setKey] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const close = (next: boolean) => {
    if (busy) return
    if (!next) {
      setKey('')
      setError(null)
    }
    onOpenChange(next)
  }

  const confirm = async () => {
    const accountToken = tokenStore.get()
    if (!accountToken || !key.trim()) return
    setBusy(true)
    setError(null)
    try {
      if (!(await isAccountRecoveryKey({ accountToken, recoveryKey: key.trim() }))) {
        setError("That's not this account's recovery key.")
        return
      }
      await devicesApi.remove(device.id)
      await qc.invalidateQueries({ queryKey: ['devices'] })
      setKey('')
      onOpenChange(false)
    } catch {
      setError('Could not remove the device. Try again.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={close}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Remove {device.device_name}?</DialogTitle>
          <DialogDescription>
            This device will no longer be able to decrypt your secrets. Enter your recovery key to
            confirm — it proves you own this account.
          </DialogDescription>
        </DialogHeader>

        <form
          onSubmit={(e) => {
            e.preventDefault()
            void confirm()
          }}
          className="flex flex-col gap-3"
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
          {error ? <p className="text-destructive text-sm">{error}</p> : null}

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => close(false)} disabled={busy}>
              Cancel
            </Button>
            <Button
              type="submit"
              variant="destructive"
              disabled={busy || !key.trim()}
            >
              {busy ? (
                <>
                  <Loader2 className="size-4 animate-spin" /> Removing…
                </>
              ) : (
                <>
                  <Trash2 className="size-4" /> Remove device
                </>
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
