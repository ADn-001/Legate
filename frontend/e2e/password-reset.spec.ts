import { test, expect } from '@playwright/test'
import { freshEmail } from './helpers/env'
import { signupAndOnboard, loginUI } from './helpers/onboarding'
import { getRecoveryTokens } from './helpers/otp'

test('password reset via recovery phrase preserves existing capsule content (R-02)', async ({ page }) => {
  // This spec does: signupAndOnboard + capsule create + forgot-password + Python
  // recovery-tokens script + reset-password flow + fresh login + capsule view.
  // That reliably exceeds the global 60 s default on any non-trivial network.
  test.setTimeout(120_000)

  const email = freshEmail('pwreset')
  const { recoveryWords } = await signupAndOnboard(page, email)

  // Client-side navigation to keep CEK in memory (see capsule-edit.spec.ts comment).
  await page.getByRole('button', { name: 'Create Capsule' }).click()
  await expect(page).toHaveURL(/\/vault\/capsules\/new/, { timeout: 10_000 })
  // Wait for the beneficiary auto-select before saving (see capsule-edit.spec.ts).
  await expect(page.locator('select')).not.toHaveValue('', { timeout: 10_000 })
  await page.locator('input[placeholder="e.g. Instructions for Sarah"]').fill('Pre-Reset Capsule')
  await page
    .locator('textarea[placeholder="Write your message here..."]')
    .fill('Content written before the password reset.')
  await page.getByRole('button', { name: 'Save Capsule' }).click()
  await expect(page).toHaveURL(/\/vault\/capsules$/, { timeout: 20_000 })

  // T6.2: "Forgot password?" entry point, real UI.
  await page.goto('/auth/forgot-password')
  await page.getByPlaceholder('you@example.com').fill(email)
  await page.getByRole('button', { name: 'Send reset link' }).click()
  await expect(page.getByText('Check your email')).toBeVisible({ timeout: 10_000 })

  // Real Supabase recovery tokens, minted via the admin API instead of
  // reading the actual inbox — the same #access_token/#refresh_token shape
  // the real magic link redirects to.
  const tokens = getRecoveryTokens(email)
  await page.goto(`/auth/reset-password#access_token=${tokens.access_token}&refresh_token=${tokens.refresh_token}`)
  await expect(page.getByText('Reset your password')).toBeVisible({ timeout: 10_000 })

  const newPassword = 'BrandNewPassword456!'
  await page.locator('textarea[placeholder="word1 word2 word3 ... word24"]').fill(recoveryWords.join(' '))
  await page.getByLabel('New password', { exact: true }).fill(newPassword)
  await page.getByLabel('Confirm new password').fill(newPassword)
  await page.getByRole('button', { name: 'Reset password' }).click()

  await expect(page.getByText('Your password has been changed and your vault is unlocked')).toBeVisible({
    timeout: 15_000,
  })
  await page.getByRole('button', { name: 'Continue to vault' }).click()
  await expect(page).toHaveURL(/\/vault$/, { timeout: 10_000 });

  // Force a genuinely fresh login with ONLY the new password — proves the
  // re-wrap actually replaced the primary CEK blob server-side, not just
  // that the in-memory session from the reset flow happens to still work.
  await page.evaluate(() => {
    localStorage.clear()
    sessionStorage.clear()
  })
  await loginUI(page, email, newPassword)

  // Client-side nav keeps the new-password CEK in memory so requireCek()
  // in CapsuleView resolves immediately without an unlock prompt.
  await page.getByRole('heading', { name: 'My Capsules' }).click()
  await expect(page).toHaveURL(/\/vault\/capsules$/, { timeout: 10_000 })
  await page.getByRole('button', { name: 'View capsule' }).click()
  // Wait for navigation to the view route before polling for content, the
  // same way capsule-view.spec.ts does. Skipping this collapses the 10 s
  // budget for the whole load (React Query fetch + signed URL + Supabase
  // download + decrypt) into an already-compressed window at the end of a
  // 60-90 s test, which is too tight on slow runs.
  await expect(page).toHaveURL(/\/vault\/capsules\/.*\/view$/, { timeout: 15_000 })
  await expect(page.getByText('Content written before the password reset.')).toBeVisible({ timeout: 20_000 })
})
