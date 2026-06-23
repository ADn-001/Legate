/**
 * Direct-to-backend assertions that can't be made from the DOM alone (e.g.
 * "the recovery blob exists server-side"). Reuses the real bearer token the
 * app itself attached to a real request — captured off the wire, not
 * reconstructed — so these calls are exactly what the app is authorized to
 * do, no shortcuts.
 */
import { Page } from '@playwright/test'
import { apiBase } from './env'

export function captureBearerToken(page: Page): () => string | null {
  let token: string | null = null
  page.on('request', (req) => {
    const auth = req.headers()['authorization']
    if (auth) token = auth
  })
  return () => token
}

export async function getMe(baseURL: string, bearer: string) {
  const res = await fetch(`${apiBase(baseURL)}/auth/me`, {
    headers: { Authorization: bearer },
  })
  if (!res.ok) throw new Error(`GET /auth/me failed: ${res.status} ${await res.text()}`)
  return res.json()
}

export async function validateRecoveryPhrase(baseURL: string, bearer: string, recoveryPhraseHash: string) {
  const res = await fetch(`${apiBase(baseURL)}/auth/me/recovery-key/validate`, {
    method: 'POST',
    headers: { Authorization: bearer, 'Content-Type': 'application/json' },
    body: JSON.stringify({ recovery_phrase_hash: recoveryPhraseHash }),
  })
  return res
}
