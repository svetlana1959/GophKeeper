import { useState } from 'react'
import { Check, Copy, CreditCard, FileText, KeyRound } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

const TERMINAL: { comment: string; cmd: string }[] = [
  { comment: '# Install GophKeeper', cmd: 'gopher install' },
  { comment: '# Add a secret', cmd: 'gopher secret set database/passwords' },
  { comment: '# View your secrets', cmd: 'gopher secret list' },
  { comment: '# Sync across devices', cmd: 'gopher sync' },
]

// CLI-friendly clipboard payload: just the runnable commands — no `#` comments
// and no `$` prompt — so the block pastes and runs as-is.
const COPY_TEXT = TERMINAL.map(({ cmd }) => cmd).join('\n')

interface SecretRow {
  icon: LucideIcon
  name: string
  type: string
  updated: string
  devices: string
}

const SECRETS: SecretRow[] = [
  {
    icon: KeyRound,
    name: 'GitHub',
    type: 'Password',
    updated: 'Today, 12:45',
    devices: '3 devices',
  },
  {
    icon: KeyRound,
    name: 'Gmail',
    type: 'Password',
    updated: 'Yesterday, 10:13',
    devices: '2 devices',
  },
  { icon: CreditCard, name: 'Mir', type: 'Bank card', updated: '3 days ago', devices: '1 device' },
  {
    icon: FileText,
    name: 'Passport scan.pdf',
    type: 'File',
    updated: '1 week ago',
    devices: '1 device',
  },
]

function Terminal() {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(COPY_TEXT)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // Clipboard unavailable (insecure context / denied) — nothing to recover.
    }
  }

  return (
    <div className="relative rounded-2xl border border-white/10 bg-black/60 p-6 font-mono text-sm">
      <button
        type="button"
        onClick={handleCopy}
        aria-label={copied ? 'Copied' : 'Copy commands'}
        className="focus-visible:ring-primary absolute top-4 right-4 rounded-md border border-white/10 p-2 text-white/50 transition-colors hover:bg-white/5 hover:text-white focus-visible:ring-2 focus-visible:outline-none"
      >
        {copied ? <Check className="text-primary size-4" /> : <Copy className="size-4" />}
      </button>
      <div className="space-y-4">
        {TERMINAL.map(({ comment, cmd }) => (
          <div key={cmd}>
            <p className="text-primary/70">{comment}</p>
            <p className="text-white">
              <span className="text-white/40 select-none">$ </span>
              {cmd}
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}

function SecretsMock() {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-5">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-white">Secrets</h3>
        <span className="bg-primary text-primary-foreground rounded-md px-3 py-1.5 text-xs font-semibold">
          + New Secret
        </span>
      </div>
      <div className="mt-4 divide-y divide-white/5">
        {SECRETS.map(({ icon: Icon, name, type, updated, devices }) => (
          <div key={name} className="flex items-center gap-3 py-3">
            <span className="bg-primary/10 text-primary flex size-9 shrink-0 items-center justify-center rounded-lg">
              <Icon className="size-4" strokeWidth={1.75} />
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-white">{name}</p>
              <p className="text-xs text-white/40">{type}</p>
            </div>
            <div className="hidden text-right sm:block">
              <p className="text-xs text-white/50">{updated}</p>
              <p className="text-xs text-white/30">{devices}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export function DeveloperShowcase() {
  return (
    <section id="developers" className="mx-auto max-w-7xl scroll-mt-20 px-6 py-20 lg:py-28">
      <div className="grid items-center gap-12 lg:grid-cols-2">
        <div>
          <h2 className="text-4xl font-bold tracking-tight sm:text-5xl">
            <span className="text-white">Built for </span>
            <span className="text-primary">developers</span>
          </h2>
          <p className="mt-4 text-lg text-white/50">Everything you need, right in the terminal.</p>
          <div className="mt-8">
            <Terminal />
          </div>
        </div>
        <SecretsMock />
      </div>
    </section>
  )
}
