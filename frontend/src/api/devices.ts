import { z } from 'zod'
import { http } from './http'

// Devices in the caller's account. `GET /devices` accepts the web account session
// (it resolves either an account or a device token to the account), so this is a
// real, account-scoped list.

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
    const { data } = await http.get('/devices')
    return z.array(deviceSchema).parse(data)
  },
  async remove(id: string): Promise<void> {
    await http.delete(`/devices/${id}`)
  },
}
