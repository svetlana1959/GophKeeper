import { useQuery } from '@tanstack/react-query'
import { devicesApi } from '@/api/devices'

/** The account's devices, account-scoped. Read by the dashboard and devices pages. */
export function useDevices() {
  return useQuery({
    queryKey: ['devices'],
    queryFn: () => devicesApi.list(),
  })
}
