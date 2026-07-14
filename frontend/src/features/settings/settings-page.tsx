import { useQuery } from '@tanstack/react-query'
import { LogOut, Monitor, Moon, Sun } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { accountsApi } from '@/api/accounts'
import { useAuth } from '@/app/auth-context'
import { useTheme, type Theme } from '@/app/theme-context'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { GITHUB_URL } from '@/features/landing/constants'

function SettingsCard({
  title,
  description,
  children,
}: {
  title: string
  description: string
  children: React.ReactNode
}) {
  return (
    <Card className="p-6">
      <h2 className="text-foreground text-xl font-bold">{title}</h2>
      <p className="text-muted-foreground mt-1 text-sm">{description}</p>
      <div className="mt-6">{children}</div>
    </Card>
  )
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="border-border/60 flex flex-col gap-1 border-b py-3 last:border-0 sm:flex-row sm:items-center sm:justify-between">
      <span className="text-muted-foreground text-sm">{label}</span>
      <span className="text-foreground truncate font-medium">{value}</span>
    </div>
  )
}

const THEMES: { value: Theme; label: string; icon: LucideIcon }[] = [
  { value: 'light', label: 'Light', icon: Sun },
  { value: 'dark', label: 'Dark', icon: Moon },
  { value: 'system', label: 'System', icon: Monitor },
]

export function SettingsPage() {
  const { identity, logout } = useAuth()
  const { theme, setTheme } = useTheme()
  const me = useQuery({ queryKey: ['account', 'me'], queryFn: () => accountsApi.me() })

  return (
    <div className="mx-auto max-w-[900px]">
      <header>
        <h1 className="text-foreground text-4xl font-bold">Settings</h1>
        <p className="text-muted-foreground mt-2 text-lg">Manage your account and preferences.</p>
      </header>

      <div className="mt-8 flex flex-col gap-6">
        <SettingsCard title="Account" description="Your account details.">
          <div className="flex flex-col">
            <Field label="Email" value={identity ?? '—'} />
            <Field label="Account ID" value={me.data?.id ?? (me.isLoading ? 'Loading…' : '—')} />
            <Field
              label="Recovery key"
              value={me.data?.recovery_pubkey ? 'Configured' : 'Not set'}
            />
          </div>
        </SettingsCard>

        <SettingsCard title="Appearance" description="Choose how GophKeeper looks.">
          <div className="grid grid-cols-3 gap-3" role="radiogroup" aria-label="Theme">
            {THEMES.map(({ value, label, icon: Icon }) => {
              const active = theme === value
              return (
                <button
                  key={value}
                  type="button"
                  role="radio"
                  aria-checked={active}
                  onClick={() => setTheme(value)}
                  className={cn(
                    'focus-visible:ring-primary flex flex-col items-center gap-2 rounded-xl border p-4 text-sm font-medium transition-colors focus-visible:ring-2 focus-visible:outline-none',
                    active
                      ? 'border-primary bg-primary/5 text-foreground'
                      : 'border-border text-muted-foreground hover:text-foreground hover:border-foreground/20',
                  )}
                >
                  <Icon className="size-5" strokeWidth={1.75} />
                  {label}
                </button>
              )
            })}
          </div>
        </SettingsCard>

        <SettingsCard title="Security" description="Manage your web session.">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-muted-foreground text-sm">
              You're signed in on this browser. Signing out clears the session token stored here.
            </p>
            <Button variant="outline" onClick={logout} className="shrink-0">
              <LogOut className="size-4" />
              Log out
            </Button>
          </div>
        </SettingsCard>

        <SettingsCard title="About" description="GophKeeper — zero-knowledge secret management.">
          <a
            href={GITHUB_URL}
            target="_blank"
            rel="noreferrer"
            className="text-primary text-sm font-medium hover:underline"
          >
            View the project on GitHub
          </a>
        </SettingsCard>
      </div>
    </div>
  )
}
