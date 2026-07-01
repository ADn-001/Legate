import axios from 'axios'
import { useAuthStore } from '../store/auth'
import { useCryptoStore } from '../store/crypto'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

// Endpoints that legitimately return 401/403 as part of normal flow (bad
// credentials, expired OTP, etc.) and must never trigger a token-refresh
// retry or a forced logout/redirect.
const AUTH_ENDPOINTS = [
  '/auth/login',
  '/auth/signup',
  '/auth/verify-email',
  '/auth/refresh',
  '/auth/logout',
  '/auth/resend-otp',
  '/auth/forgot-password',
  '/auth/reset-password',
]

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

client.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

client.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config
    const responseStatus = error.response?.status
    const isAuthEndpoint = AUTH_ENDPOINTS.some((path) => original?.url?.includes(path))

    // T11: backend's HTTPBearer raises 403 on a missing/invalid
    // Authorization header (in addition to 401 from get_current_user), so
    // both must trigger the refresh flow. A single retry per request
    // (via _retry) prevents infinite loops.
    if ((responseStatus === 401 || responseStatus === 403) && !isAuthEndpoint && !original._retry) {
      original._retry = true
      const refreshToken = localStorage.getItem('refresh_token')
      if (refreshToken) {
        try {
          const { data } = await axios.post(`${API_BASE_URL}/auth/refresh`, { refresh_token: refreshToken })
          useAuthStore.getState().setTokens(data.access_token, data.refresh_token)
          original.headers.Authorization = `Bearer ${data.access_token}`
          return client(original)
        } catch {
          useAuthStore.getState().clear()
          useCryptoStore.getState().clearCek()
          window.location.href = '/auth/login'
          return new Promise(() => {}) // navigation is occurring; never resolve
        }
      } else {
        useAuthStore.getState().clear()
        useCryptoStore.getState().clearCek()
        window.location.href = '/auth/login'
        return new Promise(() => {})
      }
    }
    // T7: surface 429 rate-limit errors with a user-facing toast
    if (responseStatus === 429) {
      const retryAfter = error.response?.headers?.['retry-after']
      const msg = retryAfter
        ? `Too many attempts. Please wait ${retryAfter} seconds and try again.`
        : 'Too many attempts. Please wait a moment and try again.'
      // Dispatch a custom event that AppShell listens to in order to show a toast
      window.dispatchEvent(new CustomEvent('legate:ratelimit', { detail: { message: msg } }))
    }
    return Promise.reject(error)
  }
)

export default client
