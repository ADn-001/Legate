/**
 * Shared constants for the Phase 3 E2E suite. Real Supabase, real Resend,
 * real backend — no mocks anywhere in this directory.
 */

// Same mailbox the backend's own e2e conftest uses (see
// backend/tests/e2e/conftest.py E2E_MAILBOX) — plus-addressing keeps every
// signup unique while landing in one real inbox.
export const MAILBOX = process.env.E2E_MAILBOX || '995homebase995@gmail.com'

export const TEST_PASSWORD = 'TestPassword123!'

// This machine has a permanent, unrelated process already bound to port 80
// (see legate-environment-quirks notes) — the documented workaround is
// NGINX_PORT=8080, so that's the default base URL here too, NOT plain
// :80/http://localhost (which silently hits that other process and 404s).
// `$env:E2E_BASE_URL` doesn't persist across new shell sessions, so this
// must be the single source of truth rather than relying on it being set.
export const DEFAULT_BASE_URL = 'http://localhost:8080'

export function freshEmail(tag: string): string {
  const [local, domain] = MAILBOX.split('@')
  const unique = `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
  return `${local}+e2e_${tag}_${unique}@${domain}`
}

// Frontend's axios baseURL is VITE_API_BASE_URL, built as `/api` against
// the compose stack (nginx proxies /api/* to the backend) — see
// frontend/Dockerfile and src/api/client.ts.
export function apiBase(baseURL: string): string {
  return `${baseURL.replace(/\/$/, '')}/api`
}
