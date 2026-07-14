import { Button } from '@/components/ui/button'

// Placeholder — Phase 1 builds the real Login (light/dark, loading/error) against
// the design and /accounts/login.
export function LoginPage() {
  return (
    <div className="bg-background flex min-h-screen items-center justify-center">
      <div className="text-center">
        <h1 className="text-foreground text-2xl font-semibold">
          Goph<span className="text-primary">Keeper</span>
        </h1>
        <p className="text-muted-foreground mt-2">Sign in — coming in Phase 1</p>
        <Button className="mt-6">Placeholder</Button>
      </div>
    </div>
  )
}
