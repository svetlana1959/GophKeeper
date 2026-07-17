import { useState } from 'react'
import { MoreVertical, Plus, Trash2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { Device } from '@/api/devices'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { DeviceIcon } from '@/features/dashboard/components/device-icon'
import { SectionCard } from '@/features/dashboard/components/section-card'
import { EmptyState } from '@/features/dashboard/components/atoms'
import { useDevices } from '@/features/dashboard/use-devices'
import { useEnrollment } from '@/features/enrollment/enrollment-context'
import { isOnline, lastActiveLabel } from '../device-display'
import { RemoveDeviceDialog } from './remove-device-dialog'

function DeviceRow({ device }: { device: Device }) {
  const online = isOnline(device)
  const [removing, setRemoving] = useState(false)

  return (
    <div className="flex items-center gap-4 py-4">
      <DeviceIcon name={device.device_name} />
      <div className="min-w-0 flex-1">
        <p className="text-foreground truncate font-semibold">{device.device_name}</p>
        <p className="text-muted-foreground truncate text-sm">
          <span className="capitalize">{device.status}</span> • Last active:{' '}
          {lastActiveLabel(device)}
        </p>
      </div>
      <span
        className={cn(
          'flex items-center gap-2 text-sm',
          online ? 'text-primary' : 'text-muted-foreground',
        )}
      >
        <span
          className={cn('size-1.5 rounded-full', online ? 'bg-primary' : 'bg-muted-foreground')}
        />
        {online ? 'Online' : 'Offline'}
      </span>
      <DropdownMenu>
        <DropdownMenuTrigger
          aria-label="Device options"
          className="text-muted-foreground hover:text-foreground rounded-md p-1 transition-colors outline-none data-[state=open]:text-foreground"
        >
          <MoreVertical className="size-4" />
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem data-variant="destructive" onSelect={() => setRemoving(true)}>
            <Trash2 className="size-4" />
            Remove device
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
      <RemoveDeviceDialog device={device} open={removing} onOpenChange={setRemoving} />
    </div>
  )
}

export function TrustedDevicesList() {
  const { openAddDevice } = useEnrollment()
  const devices = useDevices()
  const trusted = (devices.data ?? []).filter((d) => d.status === 'active')

  return (
    <SectionCard title="Trusted Devices">
      {trusted.length > 0 ? (
        <div className="divide-border/60 divide-y">
          {trusted.map((device) => (
            <DeviceRow key={device.id} device={device} />
          ))}
        </div>
      ) : (
        <EmptyState>No trusted devices yet.</EmptyState>
      )}
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
