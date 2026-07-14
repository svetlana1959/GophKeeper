import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { setUnauthorizedHandler, tokenStore } from '@/api/http'
import { AuthContext } from './auth-context'
import { queryClient } from './query-client'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => tokenStore.get())

  // A 401 anywhere clears the session; ProtectedRoute then redirects to /auth.
  useEffect(() => {
    setUnauthorizedHandler(() => {
      setToken(null)
      queryClient.clear()
    })
    return () => setUnauthorizedHandler(null)
  }, [])

  const login = useCallback((next: string) => {
    tokenStore.set(next)
    setToken(next)
  }, [])

  const logout = useCallback(() => {
    tokenStore.clear()
    setToken(null)
    queryClient.clear()
  }, [])

  const value = useMemo(() => ({ isAuthed: Boolean(token), login, logout }), [token, login, logout])
  return <AuthContext value={value}>{children}</AuthContext>
}
