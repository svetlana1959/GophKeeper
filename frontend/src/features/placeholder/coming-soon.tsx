/** Simple placeholder for routes landing in later phases. */
export function ComingSoon({ title }: { title: string }) {
  return (
    <div className="mx-auto max-w-[1400px]">
      <h1 className="text-foreground text-4xl font-bold">{title}</h1>
      <p className="text-muted-foreground mt-2 text-lg">This section is coming soon.</p>
    </div>
  )
}

export const SecretsPage = () => <ComingSoon title="Secrets" />
export const DevicesPage = () => <ComingSoon title="Devices" />
export const StatisticsPage = () => <ComingSoon title="Statistics" />
export const SettingsPage = () => <ComingSoon title="Settings" />
