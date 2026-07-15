import type { UseQueryResult } from '@tanstack/react-query'
import type { Device } from '@/api/devices'
import { Button } from '@/components/ui/button'
import { DeviceIcon } from './device-icon'
import { SectionCard } from './section-card'
import { EmptyState, ViewAllLink } from './atoms'

function RequestRow({ device }: { device: Device }) {
  return (
    <div className="py-2">
      <div className="flex items-start gap-4">
        <DeviceIcon name={device.device_name} />
        <div className="min-w-0 flex-1">
          <p className="text-foreground truncate font-semibold">{device.device_name}</p>
          <p className="text-muted-foreground truncate text-sm">Awaiting approval</p>
        </div>
      </div>
      <div className="mt-4 flex gap-3">
        <Button variant="outline" className="text-primary border-primary hover:bg-primary/5 h-10">
          Approve
        </Button>
        <Button
          variant="outline"
          className="text-destructive border-destructive hover:bg-destructive/5 h-10"
        >
          Reject
        </Button>
      </div>
    </div>
  )
}

export function PendingRequestsCard({ query }: { query: UseQueryResult<Device[]> }) {
  const pending = (query.data ?? []).filter((d) => d.status === 'pending')

  return (
    <SectionCard title="Pending Access Requests" action={<ViewAllLink to="/devices" />}>
      {pending.length > 0 ? (
        <div className="divide-border/60 divide-y">
          {pending.map((device) => (
            <RequestRow key={device.id} device={device} />
          ))}
        </div>
      ) : (
        <EmptyState>No pending access requests.</EmptyState>
      )}
    </SectionCard>
  )
}
