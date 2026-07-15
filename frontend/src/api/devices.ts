import { z } from 'zod'
import { http } from './http'

// Devices in the caller's account. NOTE: `/devices` currently requires a *device*
// session token (DevicePrincipal) on the backend, which the web account session
// does not hold — so this call fails from the web until the backend accepts an
// account-scoped principal. The UI handles that failure with an empty state.

export const deviceSchema = z.object({
  id: z.string(),
  account_id: z.string(),
  device_name: z.string(),
  public_key: z.string(),
  sign_public_key: z.string(),
  status: z.string(),
  last_seen_at: z.string().nullable(),
  updated_at: z.string(),
})
export type Device = z.infer<typeof deviceSchema>

export const devicesApi = {
  async list(): Promise<Device[]> {
    const { data } = await http.get('/api/devices', { skipAuthLogout: true })
    return z.array(deviceSchema).parse(data)
  },
}
