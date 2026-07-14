import { Bell, Moon, Sun } from 'lucide-react'
import { useTheme } from '@/app/theme-context'

/** Slim header row: theme toggle and notifications, right-aligned. */
export function TopBar() {
  const { resolved, setTheme } = useTheme()
  const isDark = resolved === 'dark'

  return (
    <header className="flex h-20 items-center justify-end gap-5 px-8">
      <button
        type="button"
        onClick={() => setTheme(isDark ? 'light' : 'dark')}
        aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
        title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
        className="text-foreground/80 hover:text-foreground transition-colors"
      >
        {isDark ? (
          <Sun className="size-6" strokeWidth={1.75} />
        ) : (
          <Moon className="size-6" strokeWidth={1.75} />
        )}
      </button>
      <button
        type="button"
        aria-label="Notifications"
        className="text-foreground/80 hover:text-foreground transition-colors"
      >
        <Bell className="size-6" strokeWidth={1.75} />
      </button>
    </header>
  )
}
