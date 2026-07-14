import { Shield, ShieldCheck } from 'lucide-react'
import type { StatsSecurity } from '@/api/stats'
import { SectionCard } from './section-card'

function StatusRow({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div className="flex items-start gap-3">
      <ShieldCheck className="text-primary mt-0.5 size-5 shrink-0" strokeWidth={2} />
      <div>
        <p className="text-foreground font-semibold">{title}</p>
        <p className="text-muted-foreground text-sm">{subtitle}</p>
      </div>
    </div>
  )
}

export function SecurityStatusCard({ security }: { security: StatsSecurity | undefined }) {
  const trusted = security?.trusted_devices ?? 0
  const alerts = security?.alerts ?? 0

  return (
    <SectionCard title="Security Status" bodyClassName="py-6">
      <div className="flex items-center gap-8">
        <span className="bg-primary/10 text-primary flex size-24 shrink-0 items-center justify-center rounded-full">
          <Shield className="size-11" strokeWidth={1.75} />
        </span>
        <div className="flex flex-col gap-5">
          <StatusRow
            title={`${trusted} trusted ${trusted === 1 ? 'device' : 'devices'}`}
            subtitle="Your devices are secure"
          />
          <StatusRow
            title={alerts === 0 ? 'No security alerts' : `${alerts} security alerts`}
            subtitle={alerts === 0 ? 'Everything looks good' : 'Review your account activity'}
          />
        </div>
      </div>
    </SectionCard>
  )
}
