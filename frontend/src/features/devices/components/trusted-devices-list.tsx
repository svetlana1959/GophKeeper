import { MoreVertical, Plus } from 'lucide-react'
import { cn } from '@/lib/utils'
import { DeviceIcon } from '@/features/dashboard/components/device-icon'
import { SectionCard } from '@/features/dashboard/components/section-card'
import { ViewAllLink } from '@/features/dashboard/components/atoms'
import { useEnrollment } from '@/features/enrollment/enrollment-context'
import type { DeviceView } from '../sample-devices'
import { SAMPLE_DEVICES } from '../sample-devices'

function DeviceRow({ device }: { device: DeviceView }) {
  return (
    <div className="flex items-center gap-4 py-4">
      <DeviceIcon name={device.name} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <p className="text-foreground truncate font-semibold">{device.name}</p>
          {device.thisDevice ? (
            <span className="bg-primary/15 text-primary rounded-full px-2 py-0.5 text-[10px] font-semibold tracking-wide uppercase">
              This device
            </span>
          ) : null}
        </div>
        <p className="text-muted-foreground truncate text-sm">
          {device.os} • {device.client} • Last active: {device.lastActive}
        </p>
      </div>
      <span
        className={cn(
          'flex items-center gap-2 text-sm',
          device.online ? 'text-primary' : 'text-muted-foreground',
        )}
      >
        <span
          className={cn(
            'size-1.5 rounded-full',
            device.online ? 'bg-primary' : 'bg-muted-foreground',
          )}
        />
        {device.online ? 'Online' : 'Offline'}
      </span>
      <button
        type="button"
        aria-label="Device options"
        className="text-muted-foreground hover:text-foreground transition-colors"
      >
        <MoreVertical className="size-4" />
      </button>
    </div>
  )
}

export function TrustedDevicesList() {
  const { openAddDevice } = useEnrollment()

  return (
    <SectionCard title="Trusted Devices" action={<ViewAllLink to="/devices" />}>
      <div className="divide-border/60 divide-y">
        {SAMPLE_DEVICES.map((device) => (
          <DeviceRow key={device.id} device={device} />
        ))}
      </div>
      <button
        type="button"
        onClick={openAddDevice}
        className="border-border text-primary hover:bg-primary/5 mt-4 flex w-full items-center justify-center gap-2 rounded-xl border border-dashed py-4 text-sm font-semibold transition-colors"
      >
        <Plus className="size-4" strokeWidth={2.5} />
        Add New Device
      </button>
    </SectionCard>
  )
}
