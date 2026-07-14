import { z } from 'zod'

// The design labels the identifier "Username". Our backend authenticates by the
// account's login identifier (the email it was created with), so we forward this
// value as-is and let the server validate it — no strict email check here.
export const loginSchema = z.object({
  username: z.string().min(1, 'Username is required'),
  password: z.string().min(1, 'Password is required'),
})

export type LoginValues = z.infer<typeof loginSchema>
