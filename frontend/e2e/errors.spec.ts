import { test, expect } from '@playwright/test'
import { execSync } from 'node:child_process'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { loadSharedUser } from './helpers/sharedUser'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const REPO_ROOT = path.resolve(__dirname, '..', '..')

test('login error messages differentiate bad credentials from a dead server (F14)', async ({ page }) => {
  const { email } = loadSharedUser()

  // Wrong password against a real, existing, verified account -> 401.
  await page.goto('/auth/login')
  await page.getByPlaceholder('you@example.com').fill(email)
  await page.locator('input[type="password"]').fill('DefinitelyWrongPassword999!')
  await page.getByRole('button', { name: 'Sign In' }).click()
  await expect(page.getByText('Invalid email or password')).toBeVisible({ timeout: 10_000 })

  // Real network failure: stop nginx itself (not just the api container —
  // a paused/stopped api alone would still get a real 502 from nginx,
  // which the app correctly classifies as a 5xx server error, not "can't
  // reach the server"). Stopping rather than pausing nginx so the new
  // connection attempt fails fast (ECONNREFUSED) instead of hanging on a
  // half-open socket with no listener to answer it. The already-loaded
  // page survives this; only the new XHR fails to connect.
  //
  // On Windows, Docker runs inside WSL2 — the Windows docker CLI is absent
  // (no //./pipe/dockerDesktopLinuxEngine). Convert REPO_ROOT to a WSL path
  // and shell into WSL to run docker compose from there.
  function dockerCompose(action: string): void {
    if (process.platform === 'win32') {
      const wslRoot = REPO_ROOT
        .replace(/^([A-Za-z]):\\/, (_: string, d: string) => `/mnt/${d.toLowerCase()}/`)
        .replace(/\\/g, '/')
      execSync(`wsl bash -c "cd '${wslRoot}' && docker compose ${action}"`, { stdio: 'pipe' })
    } else {
      execSync(`docker compose ${action}`, { cwd: REPO_ROOT, stdio: 'pipe' })
    }
  }

  dockerCompose('stop nginx')
  try {
    await page.locator('input[type="password"]').fill('AnotherPassword123!')
    await page.getByRole('button', { name: 'Sign In' }).click()
    await expect(page.getByText("Can't reach the server")).toBeVisible({ timeout: 20_000 })
  } finally {
    dockerCompose('start nginx')
  }
})
