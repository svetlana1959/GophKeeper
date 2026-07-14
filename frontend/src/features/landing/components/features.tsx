import { Check, Lock, RefreshCw, ShieldCheck, Terminal } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

interface Feature {
  icon: LucideIcon
  title: string
  body: string
  tag: string
}

const FEATURES: Feature[] = [
  {
    icon: Lock,
    title: 'Zero-Knowledge Encryption',
    body: 'Secrets are encrypted on your device before they leave it. Only you can decrypt them.',
    tag: 'Your secrets stay yours',
  },
  {
    icon: Terminal,
    title: 'CLI First',
    body: 'Built for developers who live in the terminal. A fast CLI for everyday secret management.',
    tag: 'Fast, developer-friendly',
  },
  {
    icon: RefreshCw,
    title: 'Distributed Sync',
    body: 'Access the same secrets securely across all of your trusted devices, always in sync.',
    tag: 'Sync anywhere, securely',
  },
  {
    icon: ShieldCheck,
    title: 'Trusted Devices',
    body: 'You decide which devices can access your secrets through a verifiable trust chain.',
    tag: 'Full access control',
  },
]

const TRUST_PILLS = ['Secure', 'Privacy by default', 'End-to-end encryption']

export function Features() {
  return (
    <section id="features" className="mx-auto max-w-7xl scroll-mt-20 px-6 py-20 lg:py-28">
      <div className="mx-auto max-w-2xl text-center">
        <h2 className="text-4xl font-bold tracking-tight sm:text-5xl">
          <span className="text-white">Why </span>
          <span className="text-primary">GophKeeper</span>
        </h2>
        <p className="mt-4 text-lg text-white/50">
          Powerful encryption and seamless control over your secrets, so you can build with total
          confidence.
        </p>
      </div>

      <div className="mt-14 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {FEATURES.map(({ icon: Icon, title, body, tag }) => (
          <div
            key={title}
            className="group border-primary/15 from-primary/[0.07] hover:border-primary/40 flex flex-col rounded-2xl border bg-gradient-to-b to-transparent p-6 transition-colors"
          >
            <span className="bg-primary text-primary-foreground flex size-12 items-center justify-center rounded-xl">
              <Icon className="size-6" strokeWidth={2} />
            </span>
            <h3 className="mt-5 text-xl font-semibold text-white">{title}</h3>
            <p className="mt-3 flex-1 text-sm leading-relaxed text-white/50">{body}</p>
            <div className="mt-6 border-t border-white/10 pt-4">
              <p className="text-primary flex items-center gap-2 text-sm font-medium">
                <Check className="size-4" strokeWidth={2.5} />
                {tag}
              </p>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-12 flex justify-center">
        <div className="border-primary/20 bg-primary/[0.06] flex flex-wrap items-center justify-center gap-x-6 gap-y-2 rounded-full border px-8 py-3">
          {TRUST_PILLS.map((pill, i) => (
            <div key={pill} className="flex items-center gap-6">
              {i > 0 ? <span className="bg-primary size-1 rounded-full" aria-hidden /> : null}
              <span className="text-sm text-white/70">{pill}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
