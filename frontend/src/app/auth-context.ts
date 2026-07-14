import { createContext, useContext } from 'react'

export interface AuthContextValue {
  isAuthed: boolean
  /** Login identifier (email) for display; null when unknown. */
  identity: string | null
  login: (token: string, identity?: string) => void
  logout: () => void
}

export const AuthContext = createContext<AuthContextValue | null>(null)

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider')
  return ctx
}
