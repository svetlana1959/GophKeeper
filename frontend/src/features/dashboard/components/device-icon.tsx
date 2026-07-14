import { Laptop, Monitor, Smartphone } from 'lucide-react'

const ICON_CLASS = 'size-5'
const ICON_PROPS = { className: ICON_CLASS, strokeWidth: 1.75 } as const

/** Best-effort icon element for a device based on its name. */
function iconForName(name: string) {
  const n = name.toLowerCase()
  if (/iphone|android|pixel|phone|ios/.test(n)) return <Smartphone {...ICON_PROPS} />
  if (/macbook|laptop|mac/.test(n)) return <Laptop {...ICON_PROPS} />
  return <Monitor {...ICON_PROPS} />
}

export function DeviceIcon({ name }: { name: string }) {
  return (
    <span className="bg-primary/10 text-primary flex size-11 shrink-0 items-center justify-center rounded-full">
      {iconForName(name)}
    </span>
  )
}
