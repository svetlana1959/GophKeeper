import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios'

// Single axios instance for the whole app. Paths are relative so the browser
// talks same-origin: the Vite dev proxy forwards them to the API in dev, nginx
// in production. The web session token authorizes the account; it holds no key
// and cannot decrypt anything (the web is metadata/management only).

const TOKEN_KEY = 'gophkeeper.token'

/** Session-token storage. localStorage for now — revisit vs httpOnly cookie. */
export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (token: string) => localStorage.setItem(TOKEN_KEY, token),
  clear: () => localStorage.removeItem(TOKEN_KEY),
}

// The auth layer registers a callback so a 401 anywhere logs the user out and
// redirects, without the api layer importing React.
let onUnauthorized: (() => void) | null = null
export function setUnauthorizedHandler(handler: (() => void) | null) {
  onUnauthorized = handler
}

export const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE ?? '',
  headers: { 'Content-Type': 'application/json' },
})

http.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = tokenStore.get()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

http.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    if (error instanceof AxiosError && error.response?.status === 401) {
      tokenStore.clear()
      onUnauthorized?.()
    }
    return Promise.reject(error)
  },
)

/** Extract a human-readable message from an API error (FastAPI `detail` shapes). */
export function apiErrorMessage(error: unknown): string {
  if (error instanceof AxiosError) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail) && typeof detail[0]?.msg === 'string') return detail[0].msg
    return error.response?.status ? `Request failed (${error.response.status})` : 'Request failed'
  }
  return error instanceof Error ? error.message : 'Request failed'
}
