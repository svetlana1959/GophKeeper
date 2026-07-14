import { useMutation } from '@tanstack/react-query'
import { accountsApi } from '@/api/accounts'
import { useAuth } from '@/app/auth-context'
import type { RegisterValues } from './register-schema'

/** Creates an account via `/accounts` and stores the returned session token.
 *  The web never handles age keys, so no recovery key is set here. */
export function useRegister() {
  const { login } = useAuth()
  return useMutation({
    mutationFn: ({ email, password }: RegisterValues) => accountsApi.register(email, password),
    onSuccess: (session) => login(session.access_token),
  })
}
