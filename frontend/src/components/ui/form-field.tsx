import * as React from 'react'
import { cn } from '@/lib/utils'
import { Input } from './input'
import { Label } from './label'

interface FormFieldProps extends React.ComponentProps<'input'> {
  label: string
  icon?: React.ReactNode
  error?: string
}

/** Labeled input with an optional leading icon and an error message. Spread a
 *  react-hook-form `register(...)` onto it for wiring. */
export function FormField({ label, icon, error, id, name, className, ...props }: FormFieldProps) {
  const fieldId = id ?? name
  return (
    <div className="flex flex-col gap-2">
      <Label htmlFor={fieldId}>{label}</Label>
      <div className="relative">
        {icon ? (
          <span className="text-muted-foreground pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 [&_svg]:size-4">
            {icon}
          </span>
        ) : null}
        <Input
          id={fieldId}
          name={name}
          aria-invalid={error ? true : undefined}
          aria-errormessage={error ? `${fieldId}-error` : undefined}
          className={cn(icon && 'pl-9', className)}
          {...props}
        />
      </div>
      {error ? (
        <p id={`${fieldId}-error`} className="text-destructive text-xs">
          {error}
        </p>
      ) : null}
    </div>
  )
}
