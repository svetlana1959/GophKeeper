import { useCallback, useEffect, useRef, useState } from 'react'
import { Check, Copy } from 'lucide-react'
import { cn } from '@/lib/utils'

/** Copy-to-clipboard button that flips to a check for a moment after copying. */
export function CopyButton({
  value,
  label = 'Copy',
  className,
}: {
  value: string
  label?: string
  className?: string
}) {
  const [copied, setCopied] = useState(false)
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)

  useEffect(() => () => clearTimeout(timer.current), [])

  const copy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(value)
      setCopied(true)
      clearTimeout(timer.current)
      timer.current = setTimeout(() => setCopied(false), 1500)
    } catch {
      // Clipboard blocked (insecure context / denied) — leave the button as-is.
    }
  }, [value])

  return (
    <button
      type="button"
      onClick={copy}
      aria-label={label}
      className={cn(
        'text-muted-foreground hover:text-foreground inline-flex items-center gap-1.5 text-sm font-medium transition-colors',
        className,
      )}
    >
      {copied ? (
        <Check className="text-primary size-4" strokeWidth={2.5} />
      ) : (
        <Copy className="size-4" />
      )}
      {copied ? 'Copied' : label}
    </button>
  )
}
