import { Button } from '@/components/ui/button'
import { useAuth } from '@/app/auth-context'

// Placeholder — Phase 2 builds the real dashboard. Reachable only via the auth
// guard, so it doubles as the guard's smoke test.
export function DashboardPage() {
  const { logout } = useAuth()
  return (
    <div className="bg-background flex min-h-screen flex-col items-center justify-center gap-4">
      <h1 className="text-foreground text-2xl font-semibold">Dashboard</h1>
      <p className="text-muted-foreground">Protected route — coming in Phase 2</p>
      <Button variant="outline" onClick={logout}>
        Log out
      </Button>
    </div>
  )
}
