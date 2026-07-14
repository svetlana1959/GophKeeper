import { Card } from '@/components/ui/card'
import type { StatsOverview } from '@/api/stats'

// Fixed categorical order + CVD-validated palette (passes light & dark).
const TYPES = [
  { key: 'passwords', label: 'Passwords', color: '#1a9e34' },
  { key: 'notes', label: 'Notes', color: '#2f7fd4' },
  { key: 'bank_cards', label: 'Bank Cards', color: '#cf4d8f' },
  { key: 'files', label: 'Files', color: '#c8811a' },
] as const

const R = 60
const STROKE = 22
const C = 2 * Math.PI * R

export function SecretsByType({ overview }: { overview: StatsOverview | undefined }) {
  const counts = TYPES.map((t) => ({ ...t, count: overview?.[t.key] ?? 0 }))
  const total = counts.reduce((s, c) => s + c.count, 0)

  // Cumulative dash offset per segment, computed without render-time mutation.
  const segments = counts.reduce<
    Array<(typeof counts)[number] & { frac: number; dash: number; offset: number }>
  >((acc, c) => {
    const frac = total > 0 ? c.count / total : 0
    const offset = acc.reduce((s, x) => s + x.dash, 0)
    return [...acc, { ...c, frac, dash: frac * C, offset }]
  }, [])

  return (
    <Card className="flex flex-col p-6">
      <h2 className="text-foreground mb-4 text-xl font-bold">Secrets By Type</h2>
      <div className="flex flex-1 flex-col items-center gap-8 sm:flex-row sm:justify-around">
        <svg
          viewBox="0 0 160 160"
          className="size-40 shrink-0"
          role="img"
          aria-label="Secrets by type"
        >
          <g transform="rotate(-90 80 80)">
            <circle
              cx={80}
              cy={80}
              r={R}
              fill="none"
              className="stroke-muted"
              strokeWidth={STROKE}
            />
            {total > 0
              ? segments.map((s) => (
                  <circle
                    key={s.key}
                    cx={80}
                    cy={80}
                    r={R}
                    fill="none"
                    stroke={s.color}
                    strokeWidth={STROKE}
                    strokeDasharray={`${s.dash} ${C - s.dash}`}
                    strokeDashoffset={-s.offset}
                  />
                ))
              : null}
          </g>
          <text x={80} y={76} textAnchor="middle" className="fill-foreground text-[22px] font-bold">
            {total}
          </text>
          <text x={80} y={94} textAnchor="middle" className="fill-muted-foreground text-[10px]">
            secrets
          </text>
        </svg>

        <ul className="w-full max-w-[220px] space-y-3">
          {segments.map((s) => (
            <li key={s.key} className="flex items-center gap-3 text-sm">
              <span
                className="size-2.5 shrink-0 rounded-full"
                style={{ backgroundColor: s.color }}
              />
              <span className="text-foreground flex-1">{s.label}</span>
              <span className="text-muted-foreground tabular-nums">
                {Math.round(s.frac * 100)}%
              </span>
            </li>
          ))}
        </ul>
      </div>
    </Card>
  )
}
