import { DeviceIcon } from '@/features/dashboard/components/device-icon'
import { SectionCard } from '@/features/dashboard/components/section-card'
import { EmptyState } from '@/features/dashboard/components/atoms'
import { useDevices } from '@/features/dashboard/use-devices'
import { lastActiveLabel } from '../device-display'

// Devices awaiting approval (status "pending"). Approve/Reject wiring lands with
// the device-approval flow; for now this surfaces the real pending set.
export function PendingRequests() {
  const devices = useDevices()
  const pending = (devices.data ?? []).filter((d) => d.status === 'pending')

  return (
    <SectionCard title="Pending Access Requests">
      {pending.length > 0 ? (
        <div className="divide-border/60 divide-y">
          {pending.map((device) => (
            <div key={device.id} className="flex items-start gap-4 py-3">
              <DeviceIcon name={device.device_name} />
              <div className="min-w-0 flex-1">
                <p className="text-foreground truncate font-semibold">{device.device_name}</p>
                <p className="text-muted-foreground truncate text-sm">
                  Requested: {lastActiveLabel(device)}
                </p>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <EmptyState>No pending access requests.</EmptyState>
      )}
    </SectionCard>
  )
}
