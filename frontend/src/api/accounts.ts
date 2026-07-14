import { z } from 'zod'
import { http } from './http'

// Runtime-validated shapes for the account endpoints. Types are inferred from the
// zod schemas, and the OpenAPI-generated `schema.d.ts` is the compile-time source
// of truth the schemas are kept in sync with.

export const accountSessionSchema = z.object({
  access_token: z.string(),
  token_type: z.string().optional(),
  expires_in: z.number(),
})
export type AccountSession = z.infer<typeof accountSessionSchema>

export const accountSchema = z.object({
  id: z.string(),
  recovery_pubkey: z.string().nullable(),
})
export type Account = z.infer<typeof accountSchema>

export const accountsApi = {
  async login(email: string, password: string): Promise<AccountSession> {
    const { data } = await http.post('/accounts/login', { email, password })
    return accountSessionSchema.parse(data)
  },

  async register(
    email: string,
    password: string,
    recoveryPubkey: string | null = null,
  ): Promise<AccountSession> {
    const { data } = await http.post('/accounts', {
      email,
      password,
      recovery_pubkey: recoveryPubkey,
    })
    return accountSessionSchema.parse(data)
  },

  async me(): Promise<Account> {
    const { data } = await http.get('/accounts/me')
    return accountSchema.parse(data)
  },
}
