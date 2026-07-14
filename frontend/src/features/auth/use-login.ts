import { useMutation } from '@tanstack/react-query'
import { accountsApi } from '@/api/accounts'
import { useAuth } from '@/app/auth-context'
import type { LoginValues } from './login-schema'

/** Logs in against `/accounts/login` and stores the session token on success. */
export function useLogin() {
  const { login } = useAuth()
  return useMutation({
    mutationFn: ({ email, password }: LoginValues) => accountsApi.login(email, password),
    onSuccess: (session) => login(session.access_token),
  })
}
