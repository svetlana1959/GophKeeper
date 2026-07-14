import { Search } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Card } from '@/components/ui/card'
import { SECRET_TYPE, type SecretMeta, type SecretType } from '../sample-secrets'
import { SecretTypeIcon } from './secret-type-icon'

const FILTERS: { value: SecretType | 'all'; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'password', label: 'Passwords' },
  { value: 'note', label: 'Notes' },
  { value: 'card', label: 'Bank Cards' },
  { value: 'file', label: 'Files' },
]

export function SecretsTable({
  secrets,
  query,
  onQueryChange,
  filter,
  onFilterChange,
  selectedId,
  onSelect,
}: {
  secrets: SecretMeta[]
  query: string
  onQueryChange: (v: string) => void
  filter: SecretType | 'all'
  onFilterChange: (v: SecretType | 'all') => void
  selectedId: string | null
  onSelect: (id: string) => void
}) {
  return (
    <Card className="flex flex-col p-0">
      <div className="flex flex-col gap-4 p-6 pb-4">
        <div className="relative">
          <Search className="text-muted-foreground pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2" />
          <input
            type="search"
            value={query}
            onChange={(e) => onQueryChange(e.target.value)}
            placeholder="Search secret..."
            aria-label="Search secrets"
            className="border-input text-foreground placeholder:text-muted-foreground focus-visible:border-primary focus-visible:ring-primary/25 h-11 w-full rounded-lg border bg-transparent pr-3 pl-9 text-sm focus-visible:ring-2 focus-visible:outline-none"
          />
        </div>
        <div className="flex flex-wrap gap-2">
          {FILTERS.map((f) => (
            <button
              key={f.value}
              type="button"
              onClick={() => onFilterChange(f.value)}
              className={cn(
                'rounded-full px-3.5 py-1.5 text-sm font-medium transition-colors',
                filter === f.value
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted text-muted-foreground hover:text-foreground',
              )}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      <div className="text-muted-foreground border-border/60 grid grid-cols-[1fr_auto] gap-4 border-t border-b px-6 py-3 text-xs font-medium sm:grid-cols-[2fr_1.5fr_1fr]">
        <span>Name</span>
        <span className="hidden sm:block">Last Updated</span>
        <span className="text-right sm:text-left">Devices</span>
      </div>

      {secrets.length === 0 ? (
        <p className="text-muted-foreground px-6 py-10 text-center text-sm">No secrets match.</p>
      ) : (
        <ul>
          {secrets.map((s) => (
            <li key={s.id}>
              <button
                type="button"
                onClick={() => onSelect(s.id)}
                aria-pressed={selectedId === s.id}
                className={cn(
                  'border-border/40 grid w-full grid-cols-[1fr_auto] items-center gap-4 border-b px-6 py-3.5 text-left transition-colors last:border-0 sm:grid-cols-[2fr_1.5fr_1fr]',
                  selectedId === s.id ? 'bg-primary/[0.06]' : 'hover:bg-muted/50',
                )}
              >
                <span className="flex min-w-0 items-center gap-3">
                  <SecretTypeIcon type={s.type} />
                  <span className="min-w-0">
                    <span className="text-foreground block truncate font-medium">{s.name}</span>
                    <span className="text-muted-foreground block truncate text-xs">
                      {SECRET_TYPE[s.type].label}
                    </span>
                  </span>
                </span>
                <span className="text-muted-foreground hidden text-sm sm:block">{s.updated}</span>
                <span className="text-muted-foreground text-right text-sm sm:text-left">
                  {s.devices.length} {s.devices.length === 1 ? 'device' : 'devices'}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </Card>
  )
}
