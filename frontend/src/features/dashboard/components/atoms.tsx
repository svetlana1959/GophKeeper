import { Link } from 'react-router-dom'

export function ViewAllLink({ to }: { to: string }) {
  return (
    <Link to={to} className="text-primary text-sm font-semibold hover:underline">
      View all
    </Link>
  )
}

export function EmptyState({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-muted-foreground flex min-h-24 items-center justify-center text-center text-sm">
      {children}
    </p>
  )
}
