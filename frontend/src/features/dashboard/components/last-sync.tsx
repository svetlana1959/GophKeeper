import { RefreshCw } from 'lucide-react'
import { formatSyncTimestamp } from '@/lib/format'

export function LastSync({ lastSyncAt }: { lastSyncAt: string | undefined }) {
  return (
    <div className="text-foreground flex items-center gap-3 text-[15px]">
      <RefreshCw className="text-primary size-5" strokeWidth={2} />
      <span>
        Last synchronization:{' '}
        <span className="text-primary font-medium">
          {lastSyncAt ? formatSyncTimestamp(lastSyncAt) : '—'}
        </span>
      </span>
    </div>
  )
}
