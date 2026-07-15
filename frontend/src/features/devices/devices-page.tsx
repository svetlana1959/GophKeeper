import { Card } from '@/components/ui/card'
import { LastSync } from '@/features/dashboard/components/last-sync'
import { SecurityStatusCard } from '@/features/dashboard/components/security-status-card'
import { useStatsSecurity } from '@/features/dashboard/use-stats'
import { DevicesSummaryCards } from './components/summary-cards'
import { TrustedDevicesList } from './components/trusted-devices-list'
import { PendingRequests } from './components/pending-requests'

export function DevicesPage() {
  const security = useStatsSecurity()

  return (
    <div className="mx-auto max-w-[1400px]">
      <header>
        <h1 className="text-foreground text-4xl font-bold">Trusted Devices</h1>
        <p className="text-muted-foreground mt-2 text-lg">These devices can access your secrets.</p>
      </header>

      <div className="mt-8">
        <DevicesSummaryCards security={security.data} />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-[1.4fr_1fr]">
        <TrustedDevicesList />
        <div className="flex flex-col gap-6">
          <PendingRequests />
          <SecurityStatusCard security={security.data} />
          <Card className="p-6">
            <LastSync lastSyncAt={security.data?.last_sync_at} />
          </Card>
        </div>
      </div>
    </div>
  )
}
