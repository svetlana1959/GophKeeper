import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { LogOut, Monitor, Moon, ShieldCheck, Sun, Trash2 } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { accountsApi } from '@/api/accounts'
import { useAuth } from '@/app/auth-context'
import { useTheme, type Theme } from '@/app/theme-context'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { GITHUB_URL } from '@/features/landing/constants'
import { useVault } from '@/features/vault/vault-context'
import {
  loadVaultSettings,
  saveVaultSettings,
  TTL_OPTIONS,
  type VaultSettings,
} from '@/features/vault/vault-settings'

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

function VaultAccessCard() {
  const { persisted, canPersist, saveDevice, forgetDevice } = useVault()
  const [settings, setSettings] = useState<VaultSettings>(loadVaultSettings)
  const [pin, setPin] = useState('')
  const [saved, setSaved] = useState(false)

  const update = (next: VaultSettings) => {
    setSettings(next)
    saveVaultSettings(next)
  }

  const save = async () => {
    await saveDevice(pin.trim() || undefined)
    setPin('')
    setSaved(true)
    setTimeout(() => setSaved(false), 1500)
  }

  return (
    <SettingsCard
      title="Vault access"
      description="How this browser unlocks your secrets and how long it stays linked."
    >
      <div className="flex flex-col gap-6">
        <label className="flex flex-col gap-1.5">
          <span className="text-foreground text-sm font-medium">This browser expires after</span>
          <span className="text-muted-foreground text-xs">
            A linked browser asks the server to reap it after this idle period, so abandoned
            sessions don't linger. It renews while you use it.
          </span>
          <select
            value={settings.ttlSeconds}
            onChange={(e) => update({ ...settings, ttlSeconds: Number(e.target.value) })}
            className="border-input text-foreground focus-visible:border-primary focus-visible:ring-primary/25 mt-1 h-11 w-full max-w-xs rounded-lg border bg-transparent px-3 text-sm focus-visible:ring-2 focus-visible:outline-none"
          >
            {TTL_OPTIONS.map((o) => (
              <option key={o.seconds} value={o.seconds} className="bg-background">
                {o.label}
              </option>
            ))}
          </select>
        </label>

        <label className="border-border/60 flex items-start justify-between gap-4 border-t pt-5">
          <span className="flex flex-col gap-1">
            <span className="text-foreground text-sm font-medium">Stay signed in on this browser</span>
            <span className="text-muted-foreground text-xs">
              Save the device key here so reloads don't need re-linking. Protect it with a PIN.
            </span>
          </span>
          <input
            type="checkbox"
            checked={settings.persist}
            onChange={(e) => update({ ...settings, persist: e.target.checked })}
            className="accent-primary mt-1 size-4 shrink-0"
          />
        </label>

        <div className="border-border/60 flex flex-col gap-4 border-t pt-5">
          {persisted ? (
            <p className="text-foreground flex items-center gap-2 text-sm font-medium">
              <ShieldCheck
                className={persisted.protected ? 'text-primary size-4' : 'text-muted-foreground size-4'}
                strokeWidth={2}
              />
              This browser is saved
              <span className="text-muted-foreground font-normal">
                · {persisted.protected ? 'PIN-protected' : 'no PIN — unprotected'}
              </span>
            </p>
          ) : null}

          {canPersist ? (
            <div className="flex flex-col gap-2">
              <p className="text-foreground text-sm font-medium">
                {persisted ? 'Protect with a PIN' : 'Save this browser'}
              </p>
              {!persisted ? (
                <p className="text-muted-foreground text-xs">
                  Skip re-linking next time. Set a PIN to encrypt the saved key (recommended).
                </p>
              ) : null}
              <div className="flex flex-wrap items-end gap-3">
                <label className="flex flex-col gap-1">
                  <span className="text-muted-foreground text-xs">
                    PIN {persisted ? '' : '(optional)'}
                  </span>
                  <input
                    type="password"
                    inputMode="numeric"
                    value={pin}
                    onChange={(e) => setPin(e.target.value)}
                    placeholder="••••"
                    autoComplete="off"
                    className="border-input text-foreground placeholder:text-muted-foreground focus-visible:border-primary focus-visible:ring-primary/25 h-11 w-32 rounded-lg border bg-transparent px-3 font-mono text-sm focus-visible:ring-2 focus-visible:outline-none"
                  />
                </label>
                <Button
                  onClick={() => void save()}
                  disabled={Boolean(persisted) && !pin.trim()}
                  className="shrink-0"
                >
                  {saved ? 'Saved' : persisted ? 'Set PIN' : 'Save this browser'}
                </Button>
              </div>
            </div>
          ) : !persisted ? (
            <p className="text-muted-foreground text-sm">
              Unlock this browser as a device (link and approve it) to save it here.
            </p>
          ) : null}

          {persisted ? (
            <Button variant="outline" onClick={forgetDevice} className="w-fit">
              <Trash2 className="size-4" />
              Forget this browser
            </Button>
          ) : null}
        </div>
      </div>
    </SettingsCard>
  )
}

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

        <VaultAccessCard />

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
