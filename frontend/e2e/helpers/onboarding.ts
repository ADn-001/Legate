import { Page, expect } from '@playwright/test'
import { getSignupOtp } from './otp'
import { TEST_PASSWORD } from './env'

export interface OnboardResult {
  email: string
  password: string
  fullName: string
  recoveryWords: string[]
}

/**
 * Reads the 24-word recovery phrase straight off the StepRecovery grid
 * (frontend/src/pages/setup/StepRecovery.tsx: each word lives in its own
 * card, second <p> in the card — the first is the 1-24 index label).
 */
export async function readRecoveryPhrase(page: Page): Promise<string[]> {
  const cards = page.locator('div.grid.grid-cols-4 > div')
  const count = await cards.count()
  const words: string[] = []
  for (let i = 0; i < count; i++) {
    const text = await cards.nth(i).locator('p').nth(1).textContent()
    words.push((text || '').trim())
  }
  return words
}

/**
 * Drives the full real signup → OTP verify → 4-step onboarding wizard,
 * exactly as a real user would, landing at /vault. No API shortcuts: every
 * step is filled and submitted through the actual UI so the real
 * client-side crypto (CEK generation, wrapping, recovery-key wrap) runs.
 */
export async function signupAndOnboard(
  page: Page,
  email: string,
  fullName = 'E2E Test User'
): Promise<OnboardResult> {
  await page.goto('/auth/signup')
  await page.getByPlaceholder('John Doe').fill(fullName)
  await page.getByPlaceholder('you@example.com').fill(email)
  const passwordInputs = page.locator('input[type="password"]')
  await passwordInputs.nth(0).fill(TEST_PASSWORD)
  await passwordInputs.nth(1).fill(TEST_PASSWORD)

  // Capture the real /auth/signup response so a failure here reports the
  // actual backend status + body instead of just "didn't navigate" — the
  // generic toHaveURL timeout below gives zero diagnostic info on its own.
  // 60 s timeout: the first Supabase GoTrue call from a cold/idle uvicorn
  // worker triggers a TCP/TLS handshake that can take 20-30 s. The warmup
  // fetch in global-setup should mitigate this, but 60 s is the safety net.
  const signupResponsePromise = page
    .waitForResponse((res) => res.url().includes('/auth/signup') && res.request().method() === 'POST', {
      timeout: 60_000,
    })
    .catch(() => null)

  await page.getByRole('button', { name: 'Create Account' }).click()

  const signupResponse = await signupResponsePromise
  if (signupResponse && !signupResponse.ok()) {
    const body = await signupResponse.text().catch(() => '<unreadable>')
    throw new Error(`POST /auth/signup returned ${signupResponse.status()} for ${email}: ${body}`)
  }
  if (!signupResponse) {
    const errorBanner = await page
      .locator('.bg-red-50 p')
      .first()
      .textContent()
      .catch(() => null)
    throw new Error(
      `No /auth/signup response observed within 60s for ${email}. ` +
        `On-page error banner: ${errorBanner ?? '<none visible>'}`
    )
  }

  await expect(page).toHaveURL(/\/auth\/verify-email/, { timeout: 20_000 })

  const otp = getSignupOtp(email, TEST_PASSWORD)
  if (otp.length !== 6) throw new Error(`Expected a 6-digit OTP, got ${JSON.stringify(otp)}`)
  for (let i = 0; i < 6; i++) {
    await page.locator(`input[data-index="${i}"]`).fill(otp[i])
  }

  // Same reasoning as the signup response capture above: a stuck URL here
  // could mean the OTP was rejected, OR that verify succeeded but the
  // in-memory pending password was lost (VerifyEmail.tsx falls back to a
  // password-confirmation step on the *same* URL in that case) — these
  // need different fixes, so find out which actually happened.
  const verifyResponsePromise = page
    .waitForResponse((res) => res.url().includes('/auth/verify-email') && res.request().method() === 'POST', {
      timeout: 60_000,
    })
    .catch(() => null)

  await page.getByRole('button', { name: 'Verify Code' }).click()

  const verifyResponse = await verifyResponsePromise
  if (verifyResponse && !verifyResponse.ok()) {
    const body = await verifyResponse.text().catch(() => '<unreadable>')
    throw new Error(`POST /auth/verify-email returned ${verifyResponse.status()} for ${email} (otp=${otp}): ${body}`)
  }
  if (!verifyResponse) {
    throw new Error(`No /auth/verify-email response observed within 20s for ${email} (otp=${otp}).`)
  }
  const onPasswordStep = await page
    .getByText('Confirm your password')
    .isVisible()
    .catch(() => false)
  if (onPasswordStep) {
    throw new Error(
      `Verify succeeded but landed on the "Confirm your password" fallback step instead of navigating to ` +
        `/setup/checkin — the in-memory pending password (usePendingAuthStore) was empty or for a different ` +
        `email when VerifyEmail.tsx checked it.`
    )
  }

  try {
    // 60 s, not 20 s: this waits on getMe() plus completeEncryptionSetup()'s
    // four sequential API calls (getEncryptionKey, getDeliveryWrappingKey,
    // updateDeliveryKey + local crypto), each of which can hit the same
    // cold Supabase pooler TCP/TLS handshake documented above for
    // /auth/signup. Confirmed via debug-failure.html dumps: the OTP submit
    // button was still mid-request (disabled, spinner) well past 20 s on a
    // real run, not stuck on an error — this was too tight, not a bug.
    await expect(page).toHaveURL(/\/setup\/checkin/, { timeout: 60_000 })
  } catch (err) {
    // Verify itself returned 200 and we're not on the password-fallback
    // step either — something inside completeEncryptionSetup() (key
    // derivation / decrypt / delivery-key PATCH) threw after verify
    // succeeded, leaving VerifyEmail.tsx's catch block to set an inline
    // error on the same OTP screen.
    const errorBanner = await page
      .locator('.bg-red-50 p')
      .first()
      .textContent()
      .catch(() => null)
    throw new Error(
      `Verify succeeded (200) but never navigated to /setup/checkin. ` +
        `On-page error banner: ${errorBanner ?? '<none visible>'}. Original: ${(err as Error).message}`
    )
  }
  // Capture the PATCH /settings/checkin response so a failure here reports
  // the actual HTTP status + body (not just a bare toHaveURL timeout).
  const checkinResponsePromise = page
    .waitForResponse(
      (res) => res.url().includes('/settings/checkin') && res.request().method() === 'PATCH',
      { timeout: 20_000 },
    )
    .catch(() => null)

  await page.getByRole('button', { name: 'Continue' }).click()

  const checkinResponse = await checkinResponsePromise
  if (checkinResponse && !checkinResponse.ok()) {
    const body = await checkinResponse.text().catch(() => '<unreadable>')
    throw new Error(
      `PATCH /settings/checkin returned ${checkinResponse.status()} during onboarding: ${body}`,
    )
  }
  if (!checkinResponse) {
    const errorBanner = await page
      .locator('.bg-red-50 p, [class*="text-red"] ')
      .first()
      .textContent()
      .catch(() => null)
    throw new Error(
      `No PATCH /settings/checkin response observed within 20s. ` +
        `On-page error: ${errorBanner ?? '<none visible>'}`,
    )
  }

  // 45 s (not 20 s) on the post-submit navigations below: each step's Save/
  // Continue does a real backend round trip (beneficiary create + nomination
  // email, settings PATCH, etc.), and this codebase's DB engine opens a new
  // connection per request (NullPool — see backend/tests/e2e/conftest.py),
  // which the project's own docs measure at ~10s overhead per request on
  // the Supabase free-tier pooler. 20s was too tight; confirmed via
  // debug-failure.html dumps showing in-flight requests, not stuck errors.
  await expect(page).toHaveURL(/\/setup\/beneficiary/, { timeout: 45_000 })
  await page.getByLabel('Full Name').fill('E2E Test Beneficiary')
  await page.getByLabel('Email Address').fill(`beneficiary_${Date.now()}@example.com`)
  await page.getByRole('button', { name: 'Save' }).click()

  await expect(page).toHaveURL(/\/setup\/capsule/, { timeout: 45_000 })
  await page.getByRole('button', { name: 'Skip for now' }).click()

  await expect(page).toHaveURL(/\/setup\/recovery/, { timeout: 45_000 })
  const recoveryWords = await readRecoveryPhrase(page)
  await page.getByRole('checkbox').check()
  await page.getByRole('button', { name: "I'm Ready" }).click()

  await expect(page).toHaveURL(/\/vault$/, { timeout: 45_000 })

  return { email, password: TEST_PASSWORD, fullName, recoveryWords }
}

export async function loginUI(page: Page, email: string, password: string): Promise<void> {
  await page.goto('/auth/login')
  await page.getByPlaceholder('you@example.com').fill(email)
  await page.locator('input[type="password"]').fill(password)
  await page.getByRole('button', { name: 'Sign In' }).click()
  await expect(page).toHaveURL(/\/vault$/, { timeout: 20_000 })
}
