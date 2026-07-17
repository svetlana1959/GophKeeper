import { DeviceIcon } from '@/features/dashboard/components/device-icon'
import { SectionCard } from '@/features/dashboard/components/section-card'
import { EmptyState, ViewAllLink } from '@/features/dashboard/components/atoms'
import { useDevices } from '@/features/dashboard/use-devices'
import { isOnline, lastActiveLabel } from '@/features/devices/device-display'

// Real devices, most-recently-active first. There is no per-device usage share
// to chart (the server never sees which device read what), so this ranks by
// recency instead of a fabricated percentage.
export function TopDevices() {
  const devices = useDevices()
  const recent = [...(devices.data ?? [])]
    .filter((d) => d.status !== 'revoked')
    .sort((a, b) => (b.last_seen_at ?? '').localeCompare(a.last_seen_at ?? ''))
    .slice(0, 5)

  return (
    <SectionCard title="Devices" action={<ViewAllLink to="/devices" />}>
      {recent.length > 0 ? (
        <div className="space-y-5">
          {recent.map((device) => (
            <div key={device.id} className="flex items-center gap-4">
              <DeviceIcon name={device.device_name} />
              <div className="min-w-0 flex-1">
                <p className="text-foreground truncate text-sm font-semibold">
                  {device.device_name}
                </p>
                <p className="text-muted-foreground truncate text-xs">{lastActiveLabel(device)}</p>
              </div>
              <span
                className={
                  isOnline(device)
                    ? 'text-primary shrink-0 text-xs font-medium'
                    : 'text-muted-foreground shrink-0 text-xs'
                }
              >
                {isOnline(device) ? 'Online' : 'Offline'}
              </span>
            </div>
          ))}
        </div>
      ) : (
        <EmptyState>No devices yet.</EmptyState>
      )}
    </SectionCard>
  )
}
