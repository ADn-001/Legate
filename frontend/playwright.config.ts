import { defineConfig } from '@playwright/test'
import path from 'path'
import { fileURLToPath } from 'url'
import dotenv from 'dotenv'
import { DEFAULT_BASE_URL } from './e2e/helpers/env'

// "type": "module" in package.json means this file runs as native ESM —
// no __dirname/__filename, hence the import.meta.url dance.
const __dirname = path.dirname(fileURLToPath(import.meta.url))

// Pulls SUPABASE_URL / SUPABASE_ANON_KEY / SUPABASE_SERVICE_ROLE_KEY (and
// anything else) from the backend's real .env so scripts/get_test_otp.py —
// spawned as a child process from the specs — inherits them without the
// user having to export them by hand every session.
dotenv.config({ path: path.resolve(__dirname, '../backend/.env') })

// See helpers/env.ts's DEFAULT_BASE_URL for why this isn't plain :80.
const baseURL = process.env.E2E_BASE_URL || DEFAULT_BASE_URL

export default defineConfig({
  testDir: './e2e',
  globalSetup: './e2e/global-setup.ts',
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  // Serial: errors.spec pauses/unpauses the live `api` container, which
  // would break any test running concurrently against the same stack.
  workers: 1,
  retries: 0,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { browserName: 'chromium' },
    },
  ],
})
