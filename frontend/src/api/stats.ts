import { z } from 'zod'
import { http } from './http'

// Dashboard statistics. The backend currently serves mock data from unauthenticated
// `/stats/*` endpoints; the shapes below mirror the OpenAPI schema so the UI is
// ready when they become account-scoped.

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
  last_sync_at: z.string(),
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
    const { data } = await http.get('/api/stats/overview')
    return statsOverviewSchema.parse(data)
  },
  async security(): Promise<StatsSecurity> {
    const { data } = await http.get('/api/stats/security')
    return statsSecuritySchema.parse(data)
  },
  async activity(period: StatsActivity['period'] = '7d'): Promise<StatsActivity> {
    const { data } = await http.get('/api/stats/activity', { params: { period } })
    return statsActivitySchema.parse(data)
  },
}
