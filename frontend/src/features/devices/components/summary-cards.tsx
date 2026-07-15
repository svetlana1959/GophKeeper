import { Clock, Laptop, ShieldCheck } from 'lucide-react'
import type { ReactNode } from 'react'
import { Card } from '@/components/ui/card'
import { formatSyncTimestamp } from '@/lib/format'
import type { StatsSecurity } from '@/api/stats'
import { SAMPLE_DEVICES } from '../sample-devices'

function SummaryCard({ icon, value, label }: { icon: ReactNode; value: ReactNode; label: string }) {
  return (
    <Card className="flex items-center gap-5 p-6">
      <span className="bg-primary/10 text-primary flex size-16 shrink-0 items-center justify-center rounded-full">
        {icon}
      </span>
      <div className="min-w-0">
        <p className="text-foreground truncate text-2xl font-bold">{value}</p>
        <p className="text-muted-foreground truncate text-sm">{label}</p>
      </div>
    </Card>
  )
}

export function DevicesSummaryCards({ security }: { security: StatsSecurity | undefined }) {
  const thisDevice = SAMPLE_DEVICES.find((d) => d.thisDevice)
  return (
    <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
      <SummaryCard
        icon={<ShieldCheck className="size-7" strokeWidth={1.75} />}
        value={security?.trusted_devices ?? SAMPLE_DEVICES.length}
        label="Trusted devices"
      />
      <SummaryCard
        icon={<Clock className="size-7" strokeWidth={1.75} />}
        value={security?.last_sync_at ? formatSyncTimestamp(security.last_sync_at) : '—'}
        label="Last synchronization"
      />
      <SummaryCard
        icon={<Laptop className="size-7" strokeWidth={1.75} />}
        value="This device"
        label={thisDevice?.name ?? 'Web session'}
      />
    </div>
  )
}
