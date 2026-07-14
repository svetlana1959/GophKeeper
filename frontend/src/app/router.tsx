import { createBrowserRouter } from 'react-router-dom'
import { ProtectedRoute } from './protected-route'

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
        path: '/',
        lazy: async () => ({
          Component: (await import('@/features/dashboard/dashboard-page')).DashboardPage,
        }),
      },
    ],
  },
  {
    path: '*',
    lazy: async () => ({ Component: (await import('@/features/auth/login-page')).LoginPage }),
  },
])
