import { useCallback, useMemo, useState, type ReactNode } from 'react'
import { EnrollmentContext } from './enrollment-context'
import { AddDeviceModal } from './add-device-modal'

/** Hosts the single add-device modal and exposes `openAddDevice()` to the whole
 *  app shell, so any "Add device" trigger opens the same flow. */
export function EnrollmentProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false)
  const openAddDevice = useCallback(() => setOpen(true), [])
  const value = useMemo(() => ({ openAddDevice }), [openAddDevice])

  return (
    <EnrollmentContext.Provider value={value}>
      {children}
      <AddDeviceModal open={open} onOpenChange={setOpen} />
    </EnrollmentContext.Provider>
  )
}
