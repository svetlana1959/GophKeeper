import { useQuery } from '@tanstack/react-query'
import { statsApi } from '@/api/stats'

export function useStatsOverview() {
  return useQuery({ queryKey: ['stats', 'overview'], queryFn: () => statsApi.overview() })
}

export function useStatsSecurity() {
  return useQuery({ queryKey: ['stats', 'security'], queryFn: () => statsApi.security() })
}
