import { MonitorSmartphone, RefreshCw, ShieldCheck, Terminal } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

interface Step {
  icon: LucideIcon
  title: string
  body: string
}

const STEPS: Step[] = [
  {
    icon: Terminal,
    title: 'Create a secret',
    body: 'Add a secret with the CLI or the app. It is encrypted on your device before anything leaves.',
  },
  {
    icon: RefreshCw,
    title: 'Sync securely',
    body: 'Your secret syncs to your trust network. We only ever store ciphertext — never your data.',
  },
  {
    icon: MonitorSmartphone,
    title: 'Access anywhere',
    body: 'Reach your secrets from any trusted device in your chain, wherever you are working.',
  },
  {
    icon: ShieldCheck,
    title: "You're in control",
    body: 'Manage devices, permissions, and revoke access at any time — you hold the keys.',
  },
]

export function HowItWorks() {
  return (
    <section id="how-it-works" className="scroll-mt-20 bg-white/[0.02] py-20 lg:py-28">
      <div className="mx-auto max-w-7xl px-6">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-4xl font-bold tracking-tight sm:text-5xl">
            <span className="text-white">How It </span>
            <span className="text-primary">Works</span>
          </h2>
          <p className="mt-4 text-lg text-white/50">Simple. Secure. Distributed.</p>
        </div>

        <ol className="mt-16 grid gap-10 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map(({ icon: Icon, title, body }, i) => (
            <li key={title} className="relative flex flex-col">
              <div className="flex items-center gap-4">
                <span className="bg-primary text-primary-foreground flex size-11 shrink-0 items-center justify-center rounded-full text-lg font-bold">
                  {i + 1}
                </span>
                <span className="text-primary/70">
                  <Icon className="size-6" strokeWidth={1.75} />
                </span>
              </div>
              <h3 className="text-primary mt-5 text-lg font-semibold">{title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-white/50">{body}</p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  )
}
