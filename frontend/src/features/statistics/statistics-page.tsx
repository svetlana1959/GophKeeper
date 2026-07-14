import { useState } from 'react'
import { useStatsOverview } from '@/features/dashboard/use-stats'
import { RecentActivityCard } from '@/features/dashboard/components/recent-activity-card'
import { StatsSummaryCards } from './components/summary-cards'
import { SecretsOverTime } from './components/secrets-over-time'
import { SecretsByType } from './components/secrets-by-type'
import { StorageUsage } from './components/storage-usage'
import { TopDevices } from './components/top-devices'
import { useStatsActivity, type ActivityPeriod } from './use-statistics'

export function StatisticsPage() {
  const [period, setPeriod] = useState<ActivityPeriod>('30d')
  const overview = useStatsOverview()
  const activity = useStatsActivity(period)

  return (
    <div className="mx-auto max-w-[1400px]">
      <header>
        <h1 className="text-foreground text-4xl font-bold">Account Statistics</h1>
        <p className="text-muted-foreground mt-2 text-lg">
          Overview of your account activity and data usage.
        </p>
      </header>

      <div className="mt-8">
        <StatsSummaryCards overview={overview.data} />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-[1.6fr_1fr]">
        <SecretsOverTime
          points={activity.data?.points ?? []}
          period={period}
          onPeriodChange={setPeriod}
          isLoading={activity.isLoading}
        />
        <SecretsByType overview={overview.data} />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
        <StorageUsage />
        <RecentActivityCard />
        <TopDevices />
      </div>
    </div>
  )
}
