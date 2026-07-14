import { FileText, Folder, KeyRound, Wallet } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import type { StatsOverview } from '@/api/stats'

interface StatDef {
  key: keyof StatsOverview
  label: string
  icon: LucideIcon
}

const STATS: StatDef[] = [
  { key: 'passwords', label: 'Passwords', icon: KeyRound },
  { key: 'bank_cards', label: 'Bank Cards', icon: Wallet },
  { key: 'notes', label: 'Notes', icon: FileText },
  { key: 'files', label: 'Files', icon: Folder },
]

export function StatCards({
  overview,
  isLoading,
}: {
  overview: StatsOverview | undefined
  isLoading: boolean
}) {
  return (
    <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 xl:grid-cols-4">
      {STATS.map(({ key, label, icon: Icon }) => (
        <Card key={key} className="flex items-center gap-4 p-6">
          <span className="bg-primary/10 text-primary flex size-14 shrink-0 items-center justify-center rounded-full">
            <Icon className="size-6" strokeWidth={1.75} />
          </span>
          <div className="min-w-0">
            <p className="text-muted-foreground text-sm">{label}</p>
            <p
              className={cn(
                'text-foreground text-3xl leading-tight font-bold',
                isLoading && 'text-muted-foreground/40 animate-pulse',
              )}
            >
              {isLoading ? '—' : (overview?.[key] ?? 0)}
            </p>
            <p className="text-muted-foreground text-sm">Total</p>
          </div>
        </Card>
      ))}
    </div>
  )
}
