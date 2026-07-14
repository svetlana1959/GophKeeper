import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'
import { BrandLogo } from '@/components/brand/logo'

/** Split auth shell: a dark brand panel on the left, centered content on the right. */
export function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="bg-background grid min-h-screen lg:grid-cols-[385px_1fr]">
      <aside className="relative hidden flex-col justify-center overflow-hidden bg-black px-10 lg:flex">
        <BrandLogo />
        <p className="mt-6 max-w-[228px] text-base leading-relaxed text-white/40">
          Secure your secrets.
          <br />
          Anywhere. Anytime.
        </p>
      </aside>
      <main className="flex items-center justify-center p-6">{children}</main>
    </div>
  )
}

/** The rounded auth card: icon, title, subtitle, then form content. */
export function AuthCard({
  icon,
  title,
  subtitle,
  children,
  className,
}: {
  icon: ReactNode
  title: string
  subtitle: string
  children: ReactNode
  className?: string
}) {
  return (
    <div
      className={cn(
        'bg-card border-border w-full max-w-[666px] rounded-[20px] border px-8 py-12 shadow-[1px_1px_30px_1px_rgba(0,0,0,0.07)] sm:px-[4.5rem]',
        className,
      )}
    >
      <div className="mx-auto flex w-full max-w-[524px] flex-col">
        <div className="text-primary mb-3 flex justify-center">{icon}</div>
        <h1 className="text-foreground text-center text-[2rem] leading-tight font-bold">{title}</h1>
        <p className="text-muted-foreground mt-2 text-center text-base">{subtitle}</p>
        <div className="mt-8">{children}</div>
      </div>
    </div>
  )
}
