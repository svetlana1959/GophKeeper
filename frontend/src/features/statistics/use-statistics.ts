import { useQuery } from '@tanstack/react-query'
import { statsApi, type StatsActivity } from '@/api/stats'

export type ActivityPeriod = StatsActivity['period']

export function useStatsActivity(period: ActivityPeriod) {
  return useQuery({
    queryKey: ['stats', 'activity', period],
    queryFn: () => statsApi.activity(period),
  })
}
