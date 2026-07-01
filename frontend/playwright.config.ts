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

// Playwright 1.46+ defaults to chrome-headless-shell for headless mode (separate
// binary from the full Chromium). On machines where only the full Chrome is
// installed, set PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH to its path so Playwright
// uses it instead of failing with "Executable doesn't exist".
const chromiumExecutable = process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH || undefined

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
    // NOTE: do NOT add serviceWorkers: 'block' here. Blocking the SW causes
    // registerSW.js to throw on navigator.serviceWorker.register(), which
    // triggers repeated React re-renders that make the submit button
    // "unstable" for Playwright's actionability checks (bounding-box changes
    // during the ~50 ms stability window). The SW POST→GET caching issue is
    // fixed at the source: vite.config.ts runtimeCaching has method: 'GET'
    // so the SW only intercepts GET requests.
    launchOptions: {
      executablePath: chromiumExecutable,
    },
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
