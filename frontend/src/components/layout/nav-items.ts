import { BarChart3, LayoutDashboard, Lock, MonitorSmartphone, Settings } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

export interface NavItem {
  label: string
  to: string
  icon: LucideIcon
  /** Match only the exact path (for the index route) vs. any sub-path. */
  end?: boolean
}

export const NAV_ITEMS: NavItem[] = [
  { label: 'Dashboard', to: '/', icon: LayoutDashboard, end: true },
  { label: 'Secrets', to: '/secrets', icon: Lock },
  { label: 'Devices', to: '/devices', icon: MonitorSmartphone },
  { label: 'Statistics', to: '/statistics', icon: BarChart3 },
  { label: 'Settings', to: '/settings', icon: Settings },
]
