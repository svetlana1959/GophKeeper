import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from './auth-context'

/** Renders child routes only when authenticated; otherwise redirects to /login. */
export function ProtectedRoute() {
  const { isAuthed } = useAuth()
  return isAuthed ? <Outlet /> : <Navigate to="/login" replace />
}
