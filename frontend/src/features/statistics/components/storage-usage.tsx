import { Card } from '@/components/ui/card'

// Storage figures are illustrative — the backend doesn't report usage yet.
const USED_GB = 2.3
const TOTAL_GB = 10
const PCT = Math.round((USED_GB / TOTAL_GB) * 100)

const R = 52
const STROKE = 14
const C = 2 * Math.PI * R

export function StorageUsage() {
  return (
    <Card className="flex flex-col p-6">
      <h2 className="text-foreground mb-4 text-xl font-bold">Storage Usage</h2>
      <div className="flex flex-1 items-center gap-6">
        <svg
          viewBox="0 0 130 130"
          className="size-32 shrink-0"
          role="img"
          aria-label="Storage usage"
        >
          <g transform="rotate(-90 65 65)">
            <circle
              cx={65}
              cy={65}
              r={R}
              fill="none"
              className="stroke-muted"
              strokeWidth={STROKE}
            />
            <circle
              cx={65}
              cy={65}
              r={R}
              fill="none"
              className="stroke-primary"
              strokeWidth={STROKE}
              strokeLinecap="round"
              strokeDasharray={`${(PCT / 100) * C} ${C}`}
            />
          </g>
          <text x={65} y={62} textAnchor="middle" className="fill-foreground text-[20px] font-bold">
            {USED_GB}
          </text>
          <text x={65} y={80} textAnchor="middle" className="fill-muted-foreground text-[11px]">
            GB
          </text>
        </svg>
        <div className="min-w-0 flex-1">
          <p className="text-muted-foreground text-sm">of {TOTAL_GB} GB used</p>
          <div className="bg-muted mt-3 h-2 overflow-hidden rounded-full">
            <div className="bg-primary h-full rounded-full" style={{ width: `${PCT}%` }} />
          </div>
          <p className="text-muted-foreground mt-2 text-sm">{PCT}% used</p>
        </div>
      </div>
    </Card>
  )
}
