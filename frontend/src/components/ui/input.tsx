import * as React from 'react'
import { cn } from '@/lib/utils'

function Input({ className, type, ...props }: React.ComponentProps<'input'>) {
  return (
    <input
      type={type}
      data-slot="input"
      className={cn(
        'border-input text-foreground flex h-11 w-full rounded-[7px] border bg-transparent px-3 py-2 text-sm shadow-xs transition-colors',
        'placeholder:text-muted-foreground',
        'focus-visible:border-primary focus-visible:ring-primary/25 focus-visible:ring-2 focus-visible:outline-none',
        'aria-invalid:border-destructive aria-invalid:ring-destructive/20',
        'disabled:cursor-not-allowed disabled:opacity-50',
        className,
      )}
      {...props}
    />
  )
}

export { Input }
