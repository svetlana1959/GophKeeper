import type { ReactNode } from 'react'
import { Card } from '@/components/ui/card'
import { cn } from '@/lib/utils'

/** Dashboard panel with a titled header (and optional "View all" action) above a
 *  divider, then content. */
export function SectionCard({
  title,
  action,
  children,
  className,
  bodyClassName,
}: {
  title: string
  action?: ReactNode
  children: ReactNode
  className?: string
  bodyClassName?: string
}) {
  return (
    <Card className={cn('flex flex-col p-0', className)}>
      <div className="flex items-center justify-between px-6 pt-6 pb-4">
        <h2 className="text-foreground text-xl font-bold">{title}</h2>
        {action}
      </div>
      <div className="border-border/60 border-t" />
      <div className={cn('flex-1 px-6 py-4', bodyClassName)}>{children}</div>
    </Card>
  )
}
