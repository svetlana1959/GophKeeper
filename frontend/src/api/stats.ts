import { z } from 'zod'
import { http } from './http'

// Dashboard statistics. `/stats/*` is account-scoped and requires the web session
// token (attached by the http interceptor); the shapes below mirror the OpenAPI
// schema. Counts the server cannot derive without decrypting — the per-category
// totals, `alerts`, `last_sync_at` — come back as 0/null until the client supplies
// privacy-preserving counters and sync events are persisted.

export const statsOverviewSchema = z.object({
  passwords: z.number(),
  bank_cards: z.number(),
  notes: z.number(),
  files: z.number(),
  trusted_devices: z.number(),
  revoked_devices: z.number(),
})
export type StatsOverview = z.infer<typeof statsOverviewSchema>

export const statsSecuritySchema = z.object({
  status: z.string(),
  trusted_devices: z.number(),
  revoked_devices: z.number(),
  alerts: z.number(),
  // Null until the backend persists sync events — not an error, and not optional:
  // the field is always present. A required z.string() here fails the whole parse,
  // which silently empties the security card rather than just the timestamp.
  last_sync_at: z.string().nullable(),
})
export type StatsSecurity = z.infer<typeof statsSecuritySchema>

export const activityPointSchema = z.object({
  date: z.string(),
  created: z.number(),
  updated: z.number(),
  deleted: z.number(),
})
export type ActivityPoint = z.infer<typeof activityPointSchema>

export const statsActivitySchema = z.object({
  period: z.enum(['7d', '30d', '90d']),
  points: z.array(activityPointSchema),
})
export type StatsActivity = z.infer<typeof statsActivitySchema>

export const statsApi = {
  async overview(): Promise<StatsOverview> {
    const { data } = await http.get('/stats/overview')
    return statsOverviewSchema.parse(data)
  },
  async security(): Promise<StatsSecurity> {
    const { data } = await http.get('/stats/security')
    return statsSecuritySchema.parse(data)
  },
  async activity(period: StatsActivity['period'] = '7d'): Promise<StatsActivity> {
    const { data } = await http.get('/stats/activity', { params: { period } })
    return statsActivitySchema.parse(data)
  },
}
