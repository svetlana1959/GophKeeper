import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'
import { BrandLogo } from '@/components/brand/logo'
import brandBg from '@/assets/auth-brand-bg.png'

/** Split auth shell: a black brand panel (with the shield watermark) on the left,
 *  centered card content on the right. Panel is 385px to match the design. */
export function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="bg-background grid min-h-screen lg:grid-cols-[385px_1fr]">
      <aside className="relative hidden overflow-hidden bg-black lg:block">
        <img
          src={brandBg}
          alt=""
          aria-hidden
          className="pointer-events-none absolute max-w-none opacity-[0.12] select-none"
          style={{ width: 804, height: 536, left: -209, top: -39 }}
        />
        {/* Fade the watermark down into solid black. */}
        <div className="absolute inset-0 bg-gradient-to-b from-black/30 via-black/60 to-black" />
        <div className="relative z-10 flex h-full flex-col pt-[16.5rem] pl-11">
          <BrandLogo />
          <p className="mt-4 text-base leading-relaxed text-[#f3f3f4]/50">
            Secure your secrets.
            <br />
            Anywhere. Anytime.
          </p>
        </div>
      </aside>
      <main className="flex items-center justify-center p-6">{children}</main>
    </div>
  )
}

/** The rounded auth card: centered icon, title, subtitle, then form content.
 *  666×~814 in the design; radius 20, generous padding. */
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
        'bg-card w-full max-w-[666px] rounded-[20px] border border-black/[0.06] px-8 py-14 shadow-[1px_1px_30px_1px_rgba(0,0,0,0.07)] sm:px-[4.4rem] dark:border-white/[0.06]',
        className,
      )}
    >
      <div className="text-primary mb-4 flex justify-center">{icon}</div>
      <h1 className="text-foreground text-center text-[2rem] leading-tight font-bold">{title}</h1>
      <p className="text-muted-foreground mt-3 text-center text-base">{subtitle}</p>
      <div className="mt-9">{children}</div>
    </div>
  )
}

/** "or" separator: a centered label between two rules. */
export function AuthDivider({ className }: { className?: string }) {
  return (
    <div className={cn('flex items-center gap-4', className)}>
      <span className="border-input h-px flex-1 border-t" />
      <span className="text-muted-foreground text-xs">or</span>
      <span className="border-input h-px flex-1 border-t" />
    </div>
  )
}
