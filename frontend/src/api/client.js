import axios from 'axios'

// Axios wrapper for the GophKeeper backend.
//
// Paths are relative so the browser talks same-origin: the Vite dev server
// proxies them to the API (see vite.config.js), and in production nginx does.
// The web session token identifies the account and holds no key — it can
// authorize the account (e.g. mint a device invite) but cannot decrypt anything.

const BASE = import.meta.env.VITE_API_BASE ?? ''
const TOKEN_KEY = 'gophkeeper.token'

const client = axios.create({
  baseURL: BASE,
  headers: {
    'Content-Type': 'application/json',
  },
})

export const getToken = () => localStorage.getItem(TOKEN_KEY)
export const setToken = (t) => localStorage.setItem(TOKEN_KEY, t)
export const clearToken = () => localStorage.removeItem(TOKEN_KEY)

function toErrorMessage(error) {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string') {
      return detail
    }
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0]
      if (typeof first?.msg === 'string') {
        return first.msg
      }
    }
    return error.response?.status ? `Request failed (${error.response.status})` : 'Request failed'
  }

  return error instanceof Error ? error.message : 'Request failed'
}

async function request(path, { method = 'GET', body, auth = false, params } = {}) {
  const headers = {}
  if (auth) {
    const token = getToken()
    if (token) {
      headers.Authorization = `Bearer ${token}`
    }
  }

  try {
    const response = await client.request({
      url: path,
      method,
      data: body,
      params,
      headers,
    })

    return response.data
  } catch (error) {
    throw new Error(toErrorMessage(error), { cause: error })
  }
}

export const api = {
  health: () => request('/health', { auth: true }),
  challenge: (publicKey) =>
    request('/auth/challenge', { method: 'POST', body: { public_key: publicKey } }),
  verify: (challengeToken, nonce) =>
    request('/auth/verify', {
      method: 'POST',
      body: { challenge_token: challengeToken, nonce },
    }),
  whoami: () => request('/auth/whoami', { auth: true }),
  register: (email, password, recoveryPubkey = null) =>
    request('/accounts', {
      method: 'POST',
      body: { email, password, recovery_pubkey: recoveryPubkey },
    }),
  login: (email, password) =>
    request('/accounts/login', { method: 'POST', body: { email, password } }),
  me: () => request('/accounts/me', { auth: true }),
  syncPush: (items) =>
    request('/sync/push', {
      method: 'POST',
      body: { items },
      auth: true,
    }),
  syncChanges: (since = 0) => request('/sync/changes', { auth: true, params: { since } }),
  createInvite: () => request('/enroll/invite', { method: 'POST', auth: true }),
  joinInvite: (code, deviceName, publicKey) =>
    request('/enroll/join', {
      method: 'POST',
      body: { code, device_name: deviceName, public_key: publicKey },
    }),
  listDevices: () => request('/devices', { auth: true }),
  getDevice: (deviceId) => request(`/devices/${deviceId}`, { auth: true }),
  statsOverview: () => request('/stats/overview', { auth: true }),
  statsActivity: (period = '7d') => request('/stats/activity', { auth: true, params: { period } }),
  statsSecurity: () => request('/stats/security', { auth: true }),
}
