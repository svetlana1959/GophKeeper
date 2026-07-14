import { useAuth } from '@/app/auth-context'
import { displayNameFromIdentity } from '@/lib/format'
import { useAccount } from '@/features/enrollment/use-account'
import { RecoveryKeyCallout } from '@/features/enrollment/recovery-key-callout'
import { LastSync } from './components/last-sync'
import { StatCards } from './components/stat-cards'
import { TrustedDevicesCard } from './components/trusted-devices-card'
import { PendingRequestsCard } from './components/pending-requests-card'
import { SecurityStatusCard } from './components/security-status-card'
import { RecentActivityCard } from './components/recent-activity-card'
import { useStatsOverview, useStatsSecurity } from './use-stats'
import { useDevices } from './use-devices'

export function DashboardPage() {
  const { identity } = useAuth()
  const overview = useStatsOverview()
  const security = useStatsSecurity()
  const devices = useDevices()
  const account = useAccount()
  const needsSetup = account.data?.recovery_pubkey === null

  return (
    <div className="mx-auto max-w-[1400px]">
      <header>
        <h1 className="text-foreground text-4xl font-bold">
          Welcome back, {displayNameFromIdentity(identity)}
        </h1>
        <p className="text-muted-foreground mt-2 text-lg">
          Here's what's happening with your vault.
        </p>
      </header>

      {needsSetup ? (
        <div className="mt-8">
          <RecoveryKeyCallout />
        </div>
      ) : null}

      <div className="mt-8">
        <LastSync lastSyncAt={security.data?.last_sync_at} />
      </div>

      <div className="mt-6">
        <StatCards overview={overview.data} isLoading={overview.isLoading} />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-2">
        <div className="flex flex-col gap-6">
          <TrustedDevicesCard query={devices} />
          <SecurityStatusCard security={security.data} />
        </div>
        <div className="flex flex-col gap-6">
          <PendingRequestsCard query={devices} />
          <RecentActivityCard />
        </div>
      </div>
    </div>
  )
}
