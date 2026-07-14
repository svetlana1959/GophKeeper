import { NavLink } from 'react-router-dom'
import { ChevronDown, LogOut } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAuth } from '@/app/auth-context'
import { BrandLogo } from '@/components/brand/logo'
import { Avatar } from '@/components/ui/avatar'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { displayNameFromIdentity } from '@/lib/format'
import { NAV_ITEMS } from './nav-items'

/** Persistent left navigation. Always dark, in both themes, to match the design. */
export function AppSidebar() {
  const { identity, logout } = useAuth()
  const name = displayNameFromIdentity(identity)

  return (
    <aside className="hidden flex-col bg-black px-6 py-8 text-white lg:flex">
      <div className="px-2">
        <BrandLogo />
      </div>

      <nav className="mt-14 flex flex-1 flex-col gap-1">
        {NAV_ITEMS.map(({ label, to, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 rounded-lg px-3 py-2.5 text-[15px] font-medium transition-colors',
                isActive ? 'text-primary' : 'text-white/60 hover:text-white',
              )
            }
          >
            <Icon className="size-5" strokeWidth={1.75} />
            {label}
          </NavLink>
        ))}
      </nav>

      <DropdownMenu>
        <DropdownMenuTrigger className="flex items-center gap-3 rounded-lg px-2 py-2 text-left transition-colors outline-none hover:bg-white/5 data-[state=open]:bg-white/5">
          <Avatar name={identity} filled={false} className="bg-white/10 text-white" />
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-semibold">{name}</p>
            <p className="text-xs text-white/40">Personal account</p>
          </div>
          <ChevronDown className="size-4 text-white/40" />
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-[var(--radix-dropdown-menu-trigger-width)]">
          <DropdownMenuLabel>
            <p className="text-foreground truncate text-sm font-semibold">{name}</p>
            {identity ? <p className="text-muted-foreground truncate text-xs">{identity}</p> : null}
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem data-variant="destructive" onSelect={logout}>
            <LogOut className="size-4" />
            Log out
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </aside>
  )
}
