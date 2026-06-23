import { chromium } from '@playwright/test'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { freshEmail, DEFAULT_BASE_URL } from './helpers/env'
import { signupAndOnboard } from './helpers/onboarding'
import { saveSharedUser, SHARED_USER_FILE } from './helpers/sharedUser'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

/**
 * Runs once before the whole suite: one real signup + onboarding, shared
 * by every spec that just needs an already-onboarded user (see
 * helpers/sharedUser.ts for why this exists).
 *
 * If .shared-user.json already exists from a previous run it is reused —
 * the Supabase free tier allows only ~3 signup emails per hour per project,
 * so recreating the shared user on every `npm run test:e2e` call exhausts
 * the limit after 3 runs. Delete .shared-user.json manually to force a
 * fresh signup (e.g. when switching Supabase projects or resetting the DB).
 */
export default async function globalSetup(): Promise<void> {
  // Wait for the backend to be healthy before any spec runs.
  // Without this, spec 1's loginUI fires while uvicorn is still initialising
  // (healthcheck start_period: 20s), the POST /auth/login request hangs, and
  // the Sign In button stays disabled for the full 20 s timeout.
  const baseURL = process.env.E2E_BASE_URL || DEFAULT_BASE_URL
  console.log('[global-setup] Waiting for backend…')
  for (let i = 0; i < 60; i++) {
    try {
      const res = await fetch(`${baseURL}/health`)
      if (res.ok) { console.log('[global-setup] Backend healthy.'); break }
    } catch { /* not ready yet */ }
    if (i === 59) throw new Error('[global-setup] Backend health check timed out after 60 s')
    await new Promise(r => setTimeout(r, 1000))
  }

  if (fs.existsSync(SHARED_USER_FILE)) {
    // Warm up the backend's full auth+DB+JWKS pipeline before any spec fires.
    // The first sign_in_with_password call after a container restart is a sync
    // blocking call in uvicorn that takes >20 s (cold TCP/TLS to Supabase GoTrue).
    // Paying that cost here prevents spec 1's loginUI from timing out.
    // The GET /auth/me call warms up the PyJWKClient JWKS cache so JWT
    // validation works immediately for all subsequent specs.
    const { email, password } = JSON.parse(fs.readFileSync(SHARED_USER_FILE, 'utf-8'))
    const apiBase = `${baseURL.replace(/\/$/, '')}/api`
    console.log('[global-setup] Warming up backend auth+JWT pipeline…')
    let accessToken: string | null = null
    for (let i = 0; i < 30; i++) {
      try {
        const loginRes = await fetch(`${apiBase}/auth/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password }),
        })
        if (loginRes.ok) {
          const { access_token } = await loginRes.json()
          // Warm up JWT validation — fetches and caches the JWKS on first call.
          const meRes = await fetch(`${apiBase}/auth/me`, {
            headers: { Authorization: `Bearer ${access_token}` },
          })
          if (meRes.ok) {
            accessToken = access_token
            console.log('[global-setup] Backend fully warmed up.')
            break
          }
        }
      } catch { /* still warming up, retry */ }
      await new Promise(r => setTimeout(r, 2000))
    }

    // Delete capsules left over from previous runs so each spec sees exactly
    // the capsules it created in the current run (prevents strict-mode
    // violations from duplicate title matches on the vault list page).
    if (accessToken) {
      try {
        const listRes = await fetch(`${apiBase}/capsules/`, {
          headers: { Authorization: `Bearer ${accessToken}` },
        })
        if (listRes.ok) {
          const capsules: { id: string }[] = await listRes.json()
          for (const c of capsules) {
            await fetch(`${apiBase}/capsules/${c.id}`, {
              method: 'DELETE',
              headers: { Authorization: `Bearer ${accessToken}` },
            })
          }
          if (capsules.length) {
            console.log(`[global-setup] Cleaned up ${capsules.length} capsule(s) from previous run.`)
          }
        }
      } catch (err) {
        console.warn('[global-setup] Capsule cleanup failed (non-fatal):', err)
      }
    }

    console.log(`[global-setup] Reusing existing shared user — delete ${SHARED_USER_FILE} to force a new signup.`)
    return
  }

  // baseURL already set above
  const browser = await chromium.launch()
  try {
    const context = await browser.newContext({ baseURL })
    const page = await context.newPage()
    const email = freshEmail('shared')
    try {
      const result = await signupAndOnboard(page, email, 'Shared E2E User')
      saveSharedUser(result)
    } catch (err) {
      // globalSetup gets none of Playwright's automatic screenshot/trace
      // capture (that's tied to the test() fixtures) — dump our own so a
      // failure here is debuggable instead of just "timed out".
      const shotPath = path.resolve(__dirname, 'debug-failure.png')
      const htmlPath = path.resolve(__dirname, 'debug-failure.html')
      await page.screenshot({ path: shotPath, fullPage: true }).catch(() => null)
      const html = await page.content().catch(() => '<could not read page.content()>')
      await import('node:fs').then((fs) => fs.writeFileSync(htmlPath, html))
      console.error(`global-setup failed at URL ${page.url()}. Dumped ${shotPath} and ${htmlPath}.`)
      throw err
    }
    await context.close()
  } finally {
    await browser.close()
  }
}
