import { useId, useRef, useState } from 'react'
import { Card } from '@/components/ui/card'
import type { ActivityPoint } from '@/api/stats'
import type { ActivityPeriod } from '../use-statistics'

const PERIODS: { value: ActivityPeriod; label: string }[] = [
  { value: '7d', label: 'Last 7 days' },
  { value: '30d', label: 'Last 30 days' },
  { value: '90d', label: 'Last 90 days' },
]

// Chart geometry (SVG user units; scales responsively via viewBox).
const W = 720
const H = 300
const PAD = { top: 16, right: 16, bottom: 28, left: 40 }
const PLOT_W = W - PAD.left - PAD.right
const PLOT_H = H - PAD.top - PAD.bottom

interface Point {
  label: string
  value: number
}

/** Cumulative net secrets over the period, derived from created/deleted deltas. */
function toCumulative(points: ActivityPoint[]): Point[] {
  let running = 0
  return points.map((p) => {
    running += p.created - p.deleted
    const d = new Date(p.date)
    const label = Number.isNaN(d.getTime())
      ? p.date
      : d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    return { label, value: Math.max(0, running) }
  })
}

function niceMax(max: number): number {
  if (max <= 5) return 5
  const pow = 10 ** Math.floor(Math.log10(max))
  return Math.ceil(max / pow) * pow
}

function LineChart({ points }: { points: Point[] }) {
  const gradId = useId()
  const svgRef = useRef<SVGSVGElement>(null)
  const [hover, setHover] = useState<number | null>(null)

  if (points.length === 0) {
    return (
      <div className="text-muted-foreground flex h-[300px] items-center justify-center text-sm">
        No activity data.
      </div>
    )
  }

  const maxY = niceMax(Math.max(...points.map((p) => p.value), 1))
  const x = (i: number) =>
    PAD.left + (points.length === 1 ? PLOT_W / 2 : (i / (points.length - 1)) * PLOT_W)
  const y = (v: number) => PAD.top + PLOT_H - (v / maxY) * PLOT_H

  const linePath = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${x(i)} ${y(p.value)}`).join(' ')
  const areaPath = `${linePath} L ${x(points.length - 1)} ${PAD.top + PLOT_H} L ${x(0)} ${PAD.top + PLOT_H} Z`

  const yTicks = Array.from({ length: 6 }, (_, i) => Math.round((maxY / 5) * i))
  const xTickIdx = Array.from(
    new Set([
      0,
      Math.round((points.length - 1) / 3),
      Math.round((2 * (points.length - 1)) / 3),
      points.length - 1,
    ]),
  )

  const onMove = (e: React.PointerEvent<SVGSVGElement>) => {
    const rect = svgRef.current?.getBoundingClientRect()
    if (!rect) return
    const relX = ((e.clientX - rect.left) / rect.width) * W
    const ratio = (relX - PAD.left) / PLOT_W
    const idx = Math.round(ratio * (points.length - 1))
    setHover(Math.min(points.length - 1, Math.max(0, idx)))
  }

  const hp = hover != null ? points[hover] : undefined

  return (
    <svg
      ref={svgRef}
      viewBox={`0 0 ${W} ${H}`}
      className="h-[300px] w-full touch-none"
      onPointerMove={onMove}
      onPointerLeave={() => setHover(null)}
      role="img"
      aria-label="Secrets over time"
    >
      <defs>
        <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="var(--primary)" stopOpacity="0.25" />
          <stop offset="100%" stopColor="var(--primary)" stopOpacity="0" />
        </linearGradient>
      </defs>

      {yTicks.map((t) => (
        <g key={t}>
          <line
            x1={PAD.left}
            x2={W - PAD.right}
            y1={y(t)}
            y2={y(t)}
            className="stroke-border/50"
            strokeWidth={1}
          />
          <text
            x={PAD.left - 8}
            y={y(t) + 4}
            textAnchor="end"
            className="fill-muted-foreground text-[11px]"
          >
            {t}
          </text>
        </g>
      ))}

      {xTickIdx.map((i) => {
        const p = points[i]
        if (!p) return null
        return (
          <text
            key={i}
            x={x(i)}
            y={H - 8}
            textAnchor="middle"
            className="fill-muted-foreground text-[11px]"
          >
            {p.label}
          </text>
        )
      })}

      <path d={areaPath} fill={`url(#${gradId})`} />
      <path
        d={linePath}
        fill="none"
        className="stroke-primary"
        strokeWidth={2}
        strokeLinejoin="round"
        strokeLinecap="round"
      />

      {hp ? (
        <g>
          <line
            x1={x(hover!)}
            x2={x(hover!)}
            y1={PAD.top}
            y2={PAD.top + PLOT_H}
            className="stroke-primary/40"
            strokeWidth={1}
          />
          <circle
            cx={x(hover!)}
            cy={y(hp.value)}
            r={5}
            className="fill-primary stroke-card"
            strokeWidth={2}
          />
          <g
            transform={`translate(${Math.min(Math.max(x(hover!), PAD.left + 46), W - PAD.right - 46)}, ${PAD.top + 14})`}
          >
            <rect
              x={-46}
              y={-14}
              width={92}
              height={38}
              rx={6}
              className="fill-popover stroke-border"
              strokeWidth={1}
            />
            <text x={0} y={-1} textAnchor="middle" className="fill-muted-foreground text-[10px]">
              {hp.label}
            </text>
            <text
              x={0}
              y={15}
              textAnchor="middle"
              className="fill-foreground text-[12px] font-semibold"
            >
              {hp.value} secrets
            </text>
          </g>
        </g>
      ) : null}
    </svg>
  )
}

export function SecretsOverTime({
  points,
  period,
  onPeriodChange,
  isLoading,
}: {
  points: ActivityPoint[]
  period: ActivityPeriod
  onPeriodChange: (p: ActivityPeriod) => void
  isLoading: boolean
}) {
  return (
    <Card className="flex flex-col p-6">
      <div className="mb-4 flex items-center justify-between gap-4">
        <h2 className="text-foreground text-xl font-bold">Secrets Over Time</h2>
        <select
          value={period}
          onChange={(e) => onPeriodChange(e.target.value as ActivityPeriod)}
          aria-label="Time range"
          className="border-input text-foreground focus-visible:border-primary focus-visible:ring-primary/25 rounded-lg border bg-transparent px-3 py-1.5 text-sm focus-visible:ring-2 focus-visible:outline-none"
        >
          {PERIODS.map((p) => (
            <option key={p.value} value={p.value} className="text-foreground bg-popover">
              {p.label}
            </option>
          ))}
        </select>
      </div>
      {isLoading ? (
        <div className="text-muted-foreground flex h-[300px] items-center justify-center text-sm">
          Loading…
        </div>
      ) : (
        <LineChart points={toCumulative(points)} />
      )}
    </Card>
  )
}
