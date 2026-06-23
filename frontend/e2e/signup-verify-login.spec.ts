import { test, expect } from '@playwright/test'
import { freshEmail } from './helpers/env'
import { signupAndOnboard } from './helpers/onboarding'
import { captureBearerToken, getMe, validateRecoveryPhrase } from './helpers/api'
import { hashMnemonicHex } from './helpers/crypto'

async function dumpStorage(page: import('@playwright/test').Page) {
  return page.evaluate(() => {
    const dump = (s: Storage) => {
      const obj: Record<string, string> = {}
      for (let i = 0; i < s.length; i++) {
        const k = s.key(i)!
        obj[k] = s.getItem(k) || ''
      }
      return JSON.stringify(obj)
    }
    return { session: dump(sessionStorage), local: dump(localStorage) }
  })
}

test('signup → OTP verify → onboarding → recovery phrase lands user in the app', async ({ page, baseURL }) => {
  const email = freshEmail('signup')
  const fullName = 'Ada E2E Lovelace'
  const getBearer = captureBearerToken(page)

  const result = await signupAndOnboard(page, email, fullName)
  expect(result.recoveryWords).toHaveLength(24)

  // F3: the pending password must never touch session/localStorage, not
  // even base64-encoded (the original bug stored btoa(password)).
  const storage = await dumpStorage(page)
  const btoaPassword = Buffer.from(result.password).toString('base64')
  expect(storage.session).not.toContain(btoaPassword)
  expect(storage.local).not.toContain(btoaPassword)
  expect(storage.session).not.toContain(result.password)
  expect(storage.local).not.toContain(result.password)

  const bearer = getBearer()
  expect(bearer).toBeTruthy()

  // F16: full_name actually round-trips through signup -> /auth/me.
  const me = await getMe(baseURL!, bearer!)
  expect(me.full_name).toBe(fullName)
  expect(me.email_verified).toBe(true)

  // T4: the recovery blob is genuinely stored server-side — validating the
  // real phrase against the real stored hash must succeed and return it.
  const recoveryHash = hashMnemonicHex(result.recoveryWords.join(' '))
  const validateRes = await validateRecoveryPhrase(baseURL!, bearer!, recoveryHash)
  expect(validateRes.status).toBe(200)
  const blob = await validateRes.json()
  expect(blob.recovery_encrypted_cek).toBeTruthy()
  expect(blob.recovery_cek_iv).toBeTruthy()
  expect(blob.recovery_salt).toBeTruthy()
})
