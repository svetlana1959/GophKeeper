import { cn } from '@/lib/utils'

/** Round monogram avatar. Fills green with the initial when `filled`, else a
 *  tinted circle with a green initial. */
export function Avatar({
  name,
  className,
  filled = true,
}: {
  name: string | null | undefined
  className?: string
  filled?: boolean
}) {
  const initial = (name?.trim()?.[0] ?? '?').toUpperCase()
  return (
    <span
      className={cn(
        'inline-flex size-10 shrink-0 items-center justify-center rounded-full text-sm font-semibold select-none',
        filled ? 'bg-primary text-primary-foreground' : 'bg-primary/15 text-primary',
        className,
      )}
      aria-hidden
    >
      {initial}
    </span>
  )
}
