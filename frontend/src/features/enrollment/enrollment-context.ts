import { createContext, useContext } from 'react'

export interface EnrollmentContextValue {
  /** Open the add-device modal. On a first device it also mints the recovery key. */
  openAddDevice: () => void
}

export const EnrollmentContext = createContext<EnrollmentContextValue | null>(null)

export function useEnrollment(): EnrollmentContextValue {
  const ctx = useContext(EnrollmentContext)
  if (!ctx) throw new Error('useEnrollment must be used within an EnrollmentProvider')
  return ctx
}
