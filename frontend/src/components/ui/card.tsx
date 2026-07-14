import * as React from 'react'
import { cn } from '@/lib/utils'

/** Surface container matching the dashboard cards: subtle border, soft shadow in
 *  light, flat in dark. Compose padding/spacing via `className`. */
export function Card({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      className={cn(
        'bg-card rounded-2xl border border-black/[0.06] p-6 shadow-[0_1px_3px_rgba(0,0,0,0.04)] dark:border-white/[0.04] dark:shadow-none',
        className,
      )}
      {...props}
    />
  )
}
