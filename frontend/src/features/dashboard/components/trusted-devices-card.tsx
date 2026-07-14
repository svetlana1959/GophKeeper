import { Plus } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { UseQueryResult } from '@tanstack/react-query'
import type { Device } from '@/api/devices'
import { DeviceIcon } from './device-icon'
import { SectionCard } from './section-card'
import { EmptyState, ViewAllLink } from './atoms'

function isOnline(device: Device): boolean {
  if (!device.last_seen_at) return false
  const seen = new Date(device.last_seen_at).getTime()
  return Number.isFinite(seen) && Date.now() - seen < 5 * 60 * 1000
}

function DeviceRow({ device }: { device: Device }) {
  const online = isOnline(device)
  return (
    <div className="flex items-center gap-4 py-3">
      <DeviceIcon name={device.device_name} />
      <div className="min-w-0 flex-1">
        <p className="text-foreground truncate font-semibold">{device.device_name}</p>
        <p className="text-muted-foreground truncate text-sm">{device.status}</p>
      </div>
      <span className={cnStatus(online)}>
        <span
          className={`size-1.5 rounded-full ${online ? 'bg-primary' : 'bg-muted-foreground'}`}
        />
        {online ? 'Online' : 'Offline'}
      </span>
    </div>
  )
}

function cnStatus(online: boolean): string {
  return `flex items-center gap-2 text-sm ${online ? 'text-primary' : 'text-muted-foreground'}`
}

export function TrustedDevicesCard({ query }: { query: UseQueryResult<Device[]> }) {
  const devices = (query.data ?? []).filter((d) => d.status !== 'revoked')

  return (
    <SectionCard title="Trusted Devices" action={<ViewAllLink to="/devices" />}>
      {devices.length > 0 ? (
        <div className="divide-border/60 divide-y">
          {devices.map((device) => (
            <DeviceRow key={device.id} device={device} />
          ))}
        </div>
      ) : (
        <EmptyState>No trusted devices to show yet.</EmptyState>
      )}
      <Link
        to="/devices"
        className="text-primary mt-2 flex items-center gap-2 py-2 text-sm font-semibold hover:underline"
      >
        <Plus className="size-4" strokeWidth={2.5} />
        Add new device
      </Link>
    </SectionCard>
  )
}
