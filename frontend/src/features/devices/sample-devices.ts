// Placeholder device data, mirroring the design. The backend's `/devices`
// endpoint requires a *device* session token, which the web account session does
// not hold, so — as in the original dashboard PR — these are static samples until
// the backend exposes account-scoped device listing.

export interface DeviceView {
  id: string
  name: string
  os: string
  client: string
  lastActive: string
  online: boolean
  thisDevice?: boolean
}

export interface PendingRequestView {
  id: string
  name: string
  os: string
  requestedAgo: string
}

export const SAMPLE_DEVICES: DeviceView[] = [
  {
    id: 'd1',
    name: 'Macbook Pro',
    os: 'macOS 14.4',
    client: 'Chrome',
    lastActive: 'Just now',
    online: true,
    thisDevice: true,
  },
  {
    id: 'd2',
    name: 'iPhone 17 Pro Max',
    os: 'iOS 26',
    client: 'GophKeeper Mobile',
    lastActive: '2 min ago',
    online: true,
  },
  {
    id: 'd3',
    name: 'Windows PC',
    os: 'Windows 11',
    client: 'Chrome',
    lastActive: '1 hour ago',
    online: false,
  },
  {
    id: 'd4',
    name: 'iPad Air',
    os: 'iPad OS 17.5',
    client: 'GophKeeper Mobile',
    lastActive: '3 days ago',
    online: false,
  },
]

export const SAMPLE_PENDING: PendingRequestView[] = [
  { id: 'p1', name: 'New MacBook Air', os: 'macOS 14.5', requestedAgo: '2 hours ago' },
]
