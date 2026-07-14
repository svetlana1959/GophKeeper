import { createBrowserRouter } from 'react-router-dom'
import { AppShell } from '@/components/layout/app-shell'
import { ProtectedRoute } from './protected-route'

// Auth routes are standalone; everything else renders inside the app shell behind
// the auth guard. Feature routes are lazy so each is its own chunk.
export const router = createBrowserRouter([
  {
    path: '/login',
    lazy: async () => ({ Component: (await import('@/features/auth/login-page')).LoginPage }),
  },
  {
    path: '/register',
    lazy: async () => ({
      Component: (await import('@/features/auth/register-page')).RegisterPage,
    }),
  },
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <AppShell />,
        children: [
          {
            path: '/',
            lazy: async () => ({
              Component: (await import('@/features/dashboard/dashboard-page')).DashboardPage,
            }),
          },
          {
            path: '/secrets',
            lazy: async () => ({
              Component: (await import('@/features/placeholder/coming-soon')).SecretsPage,
            }),
          },
          {
            path: '/devices',
            lazy: async () => ({
              Component: (await import('@/features/placeholder/coming-soon')).DevicesPage,
            }),
          },
          {
            path: '/statistics',
            lazy: async () => ({
              Component: (await import('@/features/placeholder/coming-soon')).StatisticsPage,
            }),
          },
          {
            path: '/settings',
            lazy: async () => ({
              Component: (await import('@/features/placeholder/coming-soon')).SettingsPage,
            }),
          },
        ],
      },
    ],
  },
  {
    path: '*',
    lazy: async () => ({ Component: (await import('@/features/auth/login-page')).LoginPage }),
  },
])
