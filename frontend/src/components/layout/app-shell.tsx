import { Outlet } from 'react-router-dom'
import { EnrollmentProvider } from '@/features/enrollment/enrollment-provider'
import { VaultProvider } from '@/features/vault/vault-provider'
import { AppSidebar } from './app-sidebar'
import { TopBar } from './top-bar'

/** Authenticated app frame: fixed dark sidebar + themed main column with a top bar. */
export function AppShell() {
  return (
    <VaultProvider>
      <EnrollmentProvider>
        <div className="bg-background grid min-h-screen lg:grid-cols-[315px_1fr]">
          <AppSidebar />
          <div className="flex min-h-screen flex-col">
            <TopBar />
            <main className="flex-1 px-8 pb-10">
              <Outlet />
            </main>
          </div>
        </div>
      </EnrollmentProvider>
    </VaultProvider>
  )
}
