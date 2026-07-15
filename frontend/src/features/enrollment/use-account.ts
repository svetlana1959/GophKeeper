import { useQuery } from '@tanstack/react-query'
import { accountsApi } from '@/api/accounts'

/** The current account, incl. whether a recovery key has been set. Drives the
 *  dashboard setup callout and the add-device flow's first-device branch. */
export function useAccount() {
  return useQuery({
    queryKey: ['account'],
    queryFn: () => accountsApi.me(),
  })
}
