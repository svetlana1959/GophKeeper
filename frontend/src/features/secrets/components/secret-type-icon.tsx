import { CreditCard, FileText, KeyRound, StickyNote } from 'lucide-react'
import { SECRET_TYPE, type SecretType } from '../sample-secrets'

const ICON_PROPS = { className: 'size-5', strokeWidth: 1.75 } as const

function iconFor(type: SecretType) {
  switch (type) {
    case 'password':
      return <KeyRound {...ICON_PROPS} />
    case 'note':
      return <StickyNote {...ICON_PROPS} />
    case 'card':
      return <CreditCard {...ICON_PROPS} />
    case 'file':
      return <FileText {...ICON_PROPS} />
  }
}

export function SecretTypeIcon({ type }: { type: SecretType }) {
  const { color } = SECRET_TYPE[type]
  return (
    <span
      className="flex size-10 shrink-0 items-center justify-center rounded-lg"
      style={{ color, backgroundColor: `${color}22` }}
    >
      {iconFor(type)}
    </span>
  )
}
