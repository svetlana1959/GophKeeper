import { useMemo, useState } from 'react'
import { StatCards } from '@/features/dashboard/components/stat-cards'
import { useStatsOverview } from '@/features/dashboard/use-stats'
import { SAMPLE_SECRETS, type SecretType } from './sample-secrets'
import { SecretsTable } from './components/secrets-table'
import { SecretDetail } from './components/secret-detail'

export function SecretsPage() {
  const overview = useStatsOverview()
  const [query, setQuery] = useState('')
  const [filter, setFilter] = useState<SecretType | 'all'>('all')
  const [selectedId, setSelectedId] = useState<string | null>(SAMPLE_SECRETS[0]?.id ?? null)

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    return SAMPLE_SECRETS.filter(
      (s) =>
        (filter === 'all' || s.type === filter) && (q === '' || s.name.toLowerCase().includes(q)),
    )
  }, [query, filter])

  const selected = SAMPLE_SECRETS.find((s) => s.id === selectedId) ?? null

  return (
    <div className="mx-auto max-w-[1400px]">
      <header>
        <h1 className="text-foreground text-4xl font-bold">Secrets</h1>
        <p className="text-muted-foreground mt-2 text-lg">
          Browse your secrets by category — values stay encrypted on your devices.
        </p>
      </header>

      <div className="mt-8">
        <StatCards overview={overview.data} isLoading={overview.isLoading} />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-[1.5fr_1fr]">
        <SecretsTable
          secrets={filtered}
          query={query}
          onQueryChange={setQuery}
          filter={filter}
          onFilterChange={setFilter}
          selectedId={selectedId}
          onSelect={setSelectedId}
        />
        <SecretDetail secret={selected} />
      </div>
    </div>
  )
}
