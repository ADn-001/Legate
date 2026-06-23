/**
 * Bridges to backend/scripts/get_test_otp.py, which mints real Supabase
 * OTPs/tokens via the admin API (see that file's docstring for why a
 * Python script and not a JS call to Supabase admin REST directly — it
 * mirrors the same supabase-py version already pinned in
 * backend/requirements.txt).
 *
 * Requires Python with `supabase==2.4.3` installed on whatever machine
 * runs `npm run test:e2e`, and SUPABASE_URL / SUPABASE_ANON_KEY /
 * SUPABASE_SERVICE_ROLE_KEY in the environment (playwright.config.ts loads
 * these from backend/.env automatically).
 */
import { execFileSync } from 'node:child_process'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const SCRIPT_PATH = path.resolve(__dirname, '../../../backend/scripts/get_test_otp.py')
const PYTHON_BIN = process.env.E2E_PYTHON || (process.platform === 'win32' ? 'python' : 'python3')

function run(args: string[]): unknown {
  let out: string
  try {
    out = execFileSync(PYTHON_BIN, [SCRIPT_PATH, ...args], {
      encoding: 'utf-8',
      env: process.env,
    })
  } catch (err) {
    const stderr = (err as { stderr?: Buffer | string })?.stderr
    throw new Error(
      `get_test_otp.py ${args[0]} failed: ${stderr?.toString() || (err as Error).message}\n` +
        `(Is Python + 'supabase' installed, and SUPABASE_URL/SUPABASE_ANON_KEY/SUPABASE_SERVICE_ROLE_KEY set?)`
    )
  }
  const lastLine = out.trim().split('\n').pop() || '{}'
  return JSON.parse(lastLine)
}

export function getSignupOtp(email: string, password: string): string {
  const result = run(['signup-otp', email, password]) as { otp: string }
  return result.otp
}

export function getRecoveryTokens(email: string): { access_token: string; refresh_token: string } {
  return run(['recovery-tokens', email]) as { access_token: string; refresh_token: string }
}
