import { ShieldCheck } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { DeviceIcon } from '@/features/dashboard/components/device-icon'
import { SECRET_TYPE, type SecretMeta } from '../sample-secrets'
import { SecretTypeIcon } from './secret-type-icon'

function MetaRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4 py-2.5">
      <span className="text-muted-foreground text-sm">{label}</span>
      <span className="text-foreground text-sm font-medium">{value}</span>
    </div>
  )
}

export function SecretDetail({ secret }: { secret: SecretMeta | null }) {
  if (!secret) {
    return (
      <Card className="text-muted-foreground flex min-h-64 items-center justify-center p-6 text-center text-sm">
        Select a secret to see its details.
      </Card>
    )
  }

  return (
    <Card className="flex flex-col gap-6 p-6">
      <div className="flex items-center gap-4">
        <SecretTypeIcon type={secret.type} />
        <div className="min-w-0">
          <h2 className="text-foreground truncate text-lg font-bold">{secret.name}</h2>
          <p className="text-muted-foreground text-sm">{SECRET_TYPE[secret.type].label}</p>
        </div>
      </div>

      <div className="border-border/60 divide-border/60 divide-y border-t border-b">
        <MetaRow label="Type" value={SECRET_TYPE[secret.type].label} />
        <MetaRow label="Created" value={secret.created} />
        <MetaRow label="Last Modified" value={secret.updated} />
      </div>

      <div>
        <h3 className="text-foreground text-sm font-semibold">Devices with access</h3>
        <ul className="mt-3 space-y-3">
          {secret.devices.map((d) => (
            <li key={d.name} className="flex items-center gap-3">
              <DeviceIcon name={d.name} />
              <span className="text-foreground min-w-0 flex-1 truncate text-sm">{d.name}</span>
              <span
                className={
                  d.online
                    ? 'text-primary flex items-center gap-1.5 text-sm'
                    : 'text-muted-foreground flex items-center gap-1.5 text-sm'
                }
              >
                <span
                  className={`size-1.5 rounded-full ${d.online ? 'bg-primary' : 'bg-muted-foreground'}`}
                />
                {d.online ? 'Online' : 'Offline'}
              </span>
            </li>
          ))}
        </ul>
      </div>

      <div className="bg-muted/40 text-muted-foreground flex items-start gap-3 rounded-xl p-4 text-sm">
        <ShieldCheck className="text-primary mt-0.5 size-5 shrink-0" strokeWidth={2} />
        <p>
          Secret values are end-to-end encrypted and never leave your devices. Open them in the CLI
          or desktop app to view or edit.
        </p>
      </div>
    </Card>
  )
}
