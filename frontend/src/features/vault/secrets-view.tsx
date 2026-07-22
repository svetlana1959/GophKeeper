import { useMemo, useState } from 'react'
import { Eye, EyeOff, FolderClosed, KeyRound, Laptop, Loader2, Lock, Search } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { CopyButton } from '@/features/enrollment/components/copy-button'
import { useVault } from './vault-context'
import type { DecryptedSecret } from './session'

function valueText(value: Uint8Array): string {
  return new TextDecoder().decode(value)
}

function SecretsList({
  secrets,
  selectedId,
  onSelect,
}: {
  secrets: DecryptedSecret[]
  selectedId: string | null
  onSelect: (id: string) => void
}) {
  const [query, setQuery] = useState('')
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    return secrets.filter((s) => q === '' || s.name.toLowerCase().includes(q))
  }, [secrets, query])

  return (
    <Card className="flex flex-col p-0">
      <div className="relative p-6 pb-4">
        <Search className="text-muted-foreground pointer-events-none absolute top-1/2 left-9 size-4 -translate-y-1/2" />
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search secrets…"
          aria-label="Search secrets"
          className="border-input text-foreground placeholder:text-muted-foreground focus-visible:border-primary focus-visible:ring-primary/25 h-11 w-full rounded-lg border bg-transparent pr-3 pl-9 text-sm focus-visible:ring-2 focus-visible:outline-none"
        />
      </div>
      {filtered.length === 0 ? (
        <p className="text-muted-foreground px-6 py-10 text-center text-sm">
          {secrets.length === 0 ? 'No secrets yet.' : 'No secrets match.'}
        </p>
      ) : (
        <ul>
          {filtered.map((s) => (
            <li key={s.id}>
              <button
                type="button"
                onClick={() => onSelect(s.id)}
                aria-pressed={selectedId === s.id}
                className={cn(
                  'border-border/40 flex w-full items-center gap-3 border-b px-6 py-3.5 text-left transition-colors last:border-0',
                  selectedId === s.id ? 'bg-primary/[0.06]' : 'hover:bg-muted/50',
                )}
              >
                <span className="bg-muted text-muted-foreground flex size-10 shrink-0 items-center justify-center rounded-lg">
                  <KeyRound className="size-5" strokeWidth={1.75} />
                </span>
                <span className="min-w-0">
                  <span className="text-foreground block truncate font-medium">{s.name}</span>
                  {s.folder ? (
                    <span className="text-muted-foreground flex items-center gap-1 truncate text-xs">
                      <FolderClosed className="size-3" /> {s.folder}
                    </span>
                  ) : null}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </Card>
  )
}

function SecretDetail({ secret }: { secret: DecryptedSecret | null }) {
  const [revealed, setRevealed] = useState(false)

  if (!secret) {
    return (
      <Card className="text-muted-foreground flex min-h-64 items-center justify-center p-6 text-center text-sm">
        Select a secret to view it.
      </Card>
    )
  }

  const text = valueText(secret.value)
  return (
    <Card className="flex flex-col gap-6 p-6">
      <div className="flex items-center gap-4">
        <span className="bg-primary/10 text-primary flex size-11 items-center justify-center rounded-lg">
          <KeyRound className="size-5" strokeWidth={1.75} />
        </span>
        <div className="min-w-0">
          <h2 className="text-foreground truncate text-lg font-bold">{secret.name}</h2>
          {secret.folder ? <p className="text-muted-foreground text-sm">{secret.folder}</p> : null}
        </div>
      </div>

      <div>
        <div className="mb-2 flex items-center justify-between">
          <span className="text-foreground text-sm font-semibold">Value</span>
          <div className="flex items-center gap-4">
            <button
              type="button"
              onClick={() => setRevealed((r) => !r)}
              className="text-muted-foreground hover:text-foreground inline-flex items-center gap-1.5 text-sm font-medium transition-colors"
            >
              {revealed ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
              {revealed ? 'Hide' : 'Reveal'}
            </button>
            <CopyButton value={text} />
          </div>
        </div>
        <code className="text-foreground bg-muted/60 border-border/60 block rounded-lg border px-3 py-3 font-mono text-sm break-all">
          {revealed ? text : '•'.repeat(Math.min(text.length, 24))}
        </code>
      </div>

      {secret.description ? (
        <div>
          <h3 className="text-foreground text-sm font-semibold">Description</h3>
          <p className="text-muted-foreground mt-1 text-sm">{secret.description}</p>
        </div>
      ) : null}
    </Card>
  )
}

function RecoveryRestoreBanner() {
  const { viaRecovery, restoring, restoreAsDevice } = useVault()
  if (!viaRecovery && !restoring) return null

  return (
    <Card className="border-primary/40 bg-primary/5 mb-4 flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex items-start gap-3">
        <Laptop className="text-primary mt-0.5 size-5 shrink-0" strokeWidth={1.75} />
        <div>
          <p className="text-foreground text-sm font-medium">You're unlocked with your recovery key</p>
          <p className="text-muted-foreground text-sm">
            Make this browser a device to unlock with a PIN next time — no recovery key needed.
          </p>
        </div>
      </div>
      {restoring ? (
        <span className="text-muted-foreground flex shrink-0 items-center gap-2 text-sm">
          <Loader2 className="size-4 animate-spin" />
          Resealing {restoring.done}/{restoring.total}…
        </span>
      ) : (
        <Button onClick={() => void restoreAsDevice()} className="shrink-0">
          <Laptop className="size-4" strokeWidth={2} /> Make this a device
        </Button>
      )}
    </Card>
  )
}

export function VaultSecretsView() {
  const { secrets, lock } = useVault()
  const [selectedId, setSelectedId] = useState<string | null>(secrets[0]?.id ?? null)
  const selected = secrets.find((s) => s.id === selectedId) ?? null

  return (
    <div>
      <RecoveryRestoreBanner />
      <div className="mb-4 flex items-center justify-between">
        <p className="text-muted-foreground text-sm">
          Decrypted in this browser · {secrets.length} secret{secrets.length === 1 ? '' : 's'}
        </p>
        <Button variant="outline" onClick={lock} className="h-9">
          <Lock className="size-4" /> Lock
        </Button>
      </div>
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1.5fr_1fr]">
        <SecretsList secrets={secrets} selectedId={selectedId} onSelect={setSelectedId} />
        <SecretDetail secret={selected} />
      </div>
    </div>
  )
}
