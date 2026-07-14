import { Button } from '@/components/ui/button'
import { DeviceIcon } from '@/features/dashboard/components/device-icon'
import { SectionCard } from '@/features/dashboard/components/section-card'
import { EmptyState } from '@/features/dashboard/components/atoms'
import { SAMPLE_PENDING } from '../sample-devices'

export function PendingRequests() {
  return (
    <SectionCard title="Pending Access Requests">
      {SAMPLE_PENDING.length > 0 ? (
        <div className="divide-border/60 divide-y">
          {SAMPLE_PENDING.map((req) => (
            <div key={req.id} className="py-2">
              <div className="flex items-start gap-4">
                <DeviceIcon name={req.name} />
                <div className="min-w-0 flex-1">
                  <p className="text-foreground truncate font-semibold">{req.name}</p>
                  <p className="text-muted-foreground truncate text-sm">{req.os}</p>
                </div>
                <span className="text-muted-foreground shrink-0 text-sm">{req.requestedAgo}</span>
              </div>
              <div className="mt-4 flex gap-3">
                <Button
                  variant="outline"
                  className="text-primary border-primary hover:bg-primary/5 h-10"
                >
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
          ))}
        </div>
      ) : (
        <EmptyState>No pending access requests.</EmptyState>
      )}
    </SectionCard>
  )
}
