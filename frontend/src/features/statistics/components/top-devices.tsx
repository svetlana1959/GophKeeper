import { DeviceIcon } from '@/features/dashboard/components/device-icon'
import { SectionCard } from '@/features/dashboard/components/section-card'
import { ViewAllLink } from '@/features/dashboard/components/atoms'
import { SAMPLE_DEVICES } from '@/features/devices/sample-devices'

// Usage share is illustrative — pending an account-scoped devices endpoint.
const SHARE = [45, 28, 18, 9]

export function TopDevices() {
  return (
    <SectionCard title="Top Devices" action={<ViewAllLink to="/devices" />}>
      <div className="space-y-5">
        {SAMPLE_DEVICES.map((device, i) => (
          <div key={device.id} className="flex items-center gap-4">
            <DeviceIcon name={device.name} />
            <div className="min-w-0 flex-1">
              <p className="text-foreground truncate text-sm font-semibold">{device.name}</p>
              <p className="text-muted-foreground truncate text-xs">{device.os}</p>
            </div>
            <div className="hidden w-28 sm:block">
              <div className="bg-muted h-1.5 overflow-hidden rounded-full">
                <div className="bg-primary h-full rounded-full" style={{ width: `${SHARE[i]}%` }} />
              </div>
            </div>
            <span className="text-muted-foreground w-9 text-right text-sm tabular-nums">
              {SHARE[i]}%
            </span>
          </div>
        ))}
      </div>
    </SectionCard>
  )
}
