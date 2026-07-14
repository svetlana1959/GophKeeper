import { SectionCard } from './section-card'
import { EmptyState, ViewAllLink } from './atoms'

// The backend exposes only aggregated activity counts (`/stats/activity`), not a
// discrete event feed, so this renders an empty state until such an endpoint exists.
export function RecentActivityCard() {
  return (
    <SectionCard title="Recent Activity" action={<ViewAllLink to="/statistics" />}>
      <EmptyState>No recent activity to show.</EmptyState>
    </SectionCard>
  )
}
