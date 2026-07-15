import { useQuery } from '@tanstack/react-query'
import { devicesApi } from '@/api/devices'

/** Devices for the account. Retry is disabled: from the web this reliably 401s
 *  (the endpoint wants a device token), so retrying just delays the empty state. */
export function useDevices() {
  return useQuery({
    queryKey: ['devices'],
    queryFn: () => devicesApi.list(),
    retry: false,
  })
}
