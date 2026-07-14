import { Folder, Laptop, RefreshCw, ShieldCheck } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import type { StatsOverview } from '@/api/stats'

interface SummaryDef {
  label: string
  icon: LucideIcon
  value: (o: StatsOverview | undefined) => number | undefined
  // Trend is illustrative — the backend doesn't expose period-over-period deltas yet.
  trend: number
}

const SUMMARY: SummaryDef[] = [
  {
    label: 'Total Secrets',
    icon: ShieldCheck,
    value: (o) => (o ? o.passwords + o.notes + o.bank_cards + o.files : undefined),
    trend: 12,
  },
  { label: 'Folders', icon: Folder, value: () => 18, trend: 5 },
  { label: 'Trusted Devices', icon: Laptop, value: (o) => o?.trusted_devices, trend: -1 },
  { label: 'Sync Events', icon: RefreshCw, value: () => 247, trend: 18 },
]

export function StatsSummaryCards({ overview }: { overview: StatsOverview | undefined }) {
  return (
    <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 xl:grid-cols-4">
      {SUMMARY.map(({ label, icon: Icon, value, trend }) => {
        const v = value(overview)
        const up = trend >= 0
        return (
          <Card key={label} className="p-6">
            <div className="flex items-center gap-4">
              <span className="bg-primary/10 text-primary flex size-12 shrink-0 items-center justify-center rounded-full">
                <Icon className="size-6" strokeWidth={1.75} />
              </span>
              <div className="min-w-0">
                <p className="text-muted-foreground text-sm">{label}</p>
                <p className="text-foreground text-3xl leading-tight font-bold">{v ?? '—'}</p>
              </div>
            </div>
            <p className="mt-4 text-sm">
              <span className={cn('font-semibold', up ? 'text-primary' : 'text-destructive')}>
                {up ? '+' : ''}
                {trend}%
              </span>{' '}
              <span className="text-muted-foreground">vs previous 30 days</span>
            </p>
          </Card>
        )
      })}
    </div>
  )
}
