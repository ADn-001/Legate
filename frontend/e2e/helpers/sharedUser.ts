/**
 * One real signup is shared across the specs that just need *an*
 * onboarded, logged-in user (session-restore, capsule-edit, capsule-view,
 * draft, errors) — created once in global-setup.ts. Doing 7 independent
 * real Supabase signups per run tripped Supabase's signup/email rate
 * limit on the first attempt (the same one backend/tests/e2e/test_02_auth.py
 * explicitly skips on). signup-verify-login.spec and password-reset.spec
 * still perform their own independent real signup — the first because it's
 * testing signup itself, the second because it permanently changes its
 * user's password and can't share state with anything that runs after it.
 */
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
export const SHARED_USER_FILE = path.resolve(__dirname, '../.shared-user.json')

export interface SharedUser {
  email: string
  password: string
  fullName: string
  recoveryWords: string[]
}

export function loadSharedUser(): SharedUser {
  if (!fs.existsSync(SHARED_USER_FILE)) {
    throw new Error(
      `${SHARED_USER_FILE} doesn't exist — global-setup.ts should have created it before any spec ran. ` +
        `Did global-setup fail? Check the test run's startup output above the per-spec results.`
    )
  }
  return JSON.parse(fs.readFileSync(SHARED_USER_FILE, 'utf-8'))
}

export function saveSharedUser(user: SharedUser): void {
  fs.writeFileSync(SHARED_USER_FILE, JSON.stringify(user, null, 2))
}
