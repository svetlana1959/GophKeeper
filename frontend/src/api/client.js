// Tiny fetch wrapper for the GophKeeper backend.
//
// Paths are relative so the browser talks same-origin: the Vite dev server
// proxies them to the API (see vite.config.js), and in production nginx does.
// The web session token identifies the account and holds no key — it can
// authorize the account (e.g. mint a device invite) but cannot decrypt anything.

const BASE = import.meta.env.VITE_API_BASE ?? ''
const TOKEN_KEY = 'gophkeeper.token'

export const getToken = () => localStorage.getItem(TOKEN_KEY)
export const setToken = (t) => localStorage.setItem(TOKEN_KEY, t)
export const clearToken = () => localStorage.removeItem(TOKEN_KEY)

async function request(path, { method = 'GET', body, auth = false } = {}) {
  const headers = { 'Content-Type': 'application/json' }
  if (auth) {
    const token = getToken()
    if (token) headers.Authorization = `Bearer ${token}`
  }
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    throw new Error(data.detail || `Request failed (${res.status})`)
  }
  return data
}

export const api = {
  register: (email, password, recoveryPubkey = null) =>
    request('/accounts', {
      method: 'POST',
      body: { email, password, recovery_pubkey: recoveryPubkey },
    }),
  login: (email, password) =>
    request('/accounts/login', { method: 'POST', body: { email, password } }),
  me: () => request('/accounts/me', { auth: true }),
  createInvite: () => request('/enroll/invite', { method: 'POST', auth: true }),
}
