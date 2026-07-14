import { createBrowserRouter } from 'react-router-dom'
import { ProtectedRoute } from './protected-route'

// Routes are lazy so each feature is its own chunk. Real screens land per phase;
// these placeholders exist to prove routing + the auth guard end-to-end.
export const router = createBrowserRouter([
  {
    path: '/auth',
    lazy: async () => ({ Component: (await import('@/features/auth/login-page')).LoginPage }),
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
