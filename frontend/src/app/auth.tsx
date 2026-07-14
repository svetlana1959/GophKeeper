import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { identityStore, setUnauthorizedHandler, tokenStore } from '@/api/http'
import { AuthContext } from './auth-context'
import { queryClient } from './query-client'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => tokenStore.get())
  const [identity, setIdentity] = useState<string | null>(() => identityStore.get())

  // A 401 anywhere clears the session; ProtectedRoute then redirects to /login.
  useEffect(() => {
    setUnauthorizedHandler(() => {
      setToken(null)
      queryClient.clear()
    })
    return () => setUnauthorizedHandler(null)
  }, [])

  const login = useCallback((next: string, nextIdentity?: string) => {
    tokenStore.set(next)
    setToken(next)
    if (nextIdentity) {
      identityStore.set(nextIdentity)
      setIdentity(nextIdentity)
    }
  }, [])

  const logout = useCallback(() => {
    tokenStore.clear()
    identityStore.clear()
    setToken(null)
    setIdentity(null)
    queryClient.clear()
  }, [])

  const value = useMemo(
    () => ({ isAuthed: Boolean(token), identity, login, logout }),
    [token, identity, login, logout],
  )
  return <AuthContext value={value}>{children}</AuthContext>
}
