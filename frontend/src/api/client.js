// Tiny axios wrapper for the backend described by the provided OpenAPI.
//
// Paths are relative so the browser talks same-origin: the Vite dev server
// proxies them to the API (see vite.config.js), and in production nginx does.
// The web session token identifies the account and holds no key — it can
// authorize the account (e.g. mint a device invite) but cannot decrypt anything.

import axios from 'axios'

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

async function request(path, { method = 'GET', body, auth = false, headers: extraHeaders = {} } = {}) {
  const headers = {}
  if (auth) {
    const token = getToken()
    if (token) {
      headers.Authorization = `Bearer ${token}`
    }
  }
  Object.assign(headers, extraHeaders)
  try {
    const res = await client.request({
      url: path,
      method,
      headers,
      data: body,
    })
    return res.data
  } catch (error) {
    const detail = error.response?.data?.detail
    throw new Error(detail || error.message || 'Request failed', { cause: error })
  }
}

export const api = {
  register: (username, password) =>
    request('/auth/', {
      method: 'POST',
      body: { username, password },
    }),
  login: (username, password) =>
    request('/auth/token', {
      method: 'POST',
      body: new URLSearchParams({ username, password }),
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    }),
  me: () => request('/users/', { auth: true }),
  createInvite: () => request('/enroll/invite', { method: 'POST', auth: true }),
}
