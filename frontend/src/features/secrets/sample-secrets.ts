// Secret *metadata* only. The web never sees secret values — they're end-to-end
// encrypted and only decryptable on an enrolled device (CLI / desktop). The backend
// exposes no metadata-listing endpoint yet, so these mirror the design as samples.

export type SecretType = 'password' | 'note' | 'card' | 'file'

export interface DeviceAccess {
  name: string
  online: boolean
}

export interface SecretMeta {
  id: string
  name: string
  type: SecretType
  updated: string
  created: string
  devices: DeviceAccess[]
}

// Type accent colors reuse the stats categorical palette for cross-page consistency.
export const SECRET_TYPE: Record<SecretType, { label: string; color: string }> = {
  password: { label: 'Password', color: '#1a9e34' },
  note: { label: 'Note', color: '#2f7fd4' },
  card: { label: 'Bank card', color: '#cf4d8f' },
  file: { label: 'File', color: '#c8811a' },
}

const D = {
  mac: { name: 'Macbook Pro', online: true },
  iphone: { name: 'iPhone 17 Pro Max', online: true },
  win: { name: 'Windows PC', online: false },
  ipad: { name: 'iPad Air', online: false },
}

export const SAMPLE_SECRETS: SecretMeta[] = [
  {
    id: 's1',
    name: 'GitHub',
    type: 'password',
    updated: 'Today, 12:45',
    created: '12 June 2026, 10:22',
    devices: [D.mac, D.iphone, D.win],
  },
  {
    id: 's2',
    name: 'Gmail',
    type: 'password',
    updated: 'Yesterday, 10:13',
    created: '2 May 2026, 09:01',
    devices: [D.mac, D.iphone],
  },
  {
    id: 's3',
    name: 'Moodle Innopolis',
    type: 'password',
    updated: '2 days ago',
    created: '20 April 2026, 14:30',
    devices: [D.mac],
  },
  {
    id: 's4',
    name: 'Mir',
    type: 'card',
    updated: '3 days ago',
    created: '11 March 2026, 18:12',
    devices: [D.iphone],
  },
  {
    id: 's5',
    name: 'Project ideas',
    type: 'note',
    updated: 'Yesterday, 22:45',
    created: '1 February 2026, 08:20',
    devices: [D.mac, D.ipad],
  },
  {
    id: 's6',
    name: 'Passport scan.pdf',
    type: 'file',
    updated: '1 week ago',
    created: '15 January 2026, 11:47',
    devices: [D.mac],
  },
]
