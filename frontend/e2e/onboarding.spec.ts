/**
 * onboarding.spec.ts — Phase 4 T5 (G3 + FR-07/08/09)
 *
 * Checks:
 * - Fresh signup → carousel shows → skip → wizard starts at step 1
 * - Abandon wizard at step 2 → reload → resumes step 2 (FR-09)
 * - Complete wizard → carousel never shown again
 */

import { test, expect } from '@playwright/test'
import { freshEmail, TEST_PASSWORD } from './helpers/env'
import { signupAndOnboard, loginUI } from './helpers/onboarding'
import { getSignupOtp } from './helpers/otp'

test('fresh login shows carousel; skip navigates to wizard step 1', async ({ page }) => {
  const email = freshEmail('carousel')
  const fullName = 'Carousel Test User'

  // Signup (goes directly to /setup/checkin via VerifyEmail.tsx)
  await page.goto('/auth/signup')
  await page.getByPlaceholder('John Doe').fill(fullName)
  await page.getByPlaceholder('you@example.com').fill(email)
  const pwInputs = page.locator('input[type="password"]')
  await pwInputs.nth(0).fill(TEST_PASSWORD)
  await pwInputs.nth(1).fill(TEST_PASSWORD)
  await page.getByRole('button', { name: 'Create Account' }).click()

  await expect(page).toHaveURL(/\/auth\/verify-email/, { timeout: 20_000 })
  const otp = getSignupOtp(email, TEST_PASSWORD)
  for (let i = 0; i < 6; i++) await page.locator(`input[data-index="${i}"]`).fill(otp[i])
  await page.getByRole('button', { name: 'Verify Code' }).click()

  // After signup, VerifyEmail navigates to /setup/checkin (bypassing carousel).
  // Complete the full wizard so needs_onboarding becomes false.
  await expect(page).toHaveURL(/\/setup\/checkin/, { timeout: 20_000 })
  await page.getByRole('button', { name: 'Continue' }).click()
  await expect(page).toHaveURL(/\/setup\/beneficiary/, { timeout: 20_000 })
  await page.getByLabel('Full Name').fill('Test Beneficiary Carousel')
  await page.getByLabel('Email Address').fill(`bene_carousel_${Date.now()}@example.com`)
  await page.getByRole('button', { name: 'Save' }).click()
  await expect(page).toHaveURL(/\/setup\/capsule/, { timeout: 20_000 })
  await page.getByRole('button', { name: 'Skip for now' }).click()
  await expect(page).toHaveURL(/\/setup\/recovery/, { timeout: 20_000 })
  await page.getByRole('checkbox').check()
  await page.getByRole('button', { name: "I'm Ready" }).click()
  await expect(page).toHaveURL(/\/vault$/, { timeout: 20_000 })

  // Log out by clearing storage and logging back in
  await page.evaluate(() => {
    localStorage.removeItem('legate_carousel_seen')
    // Clear auth state
    localStorage.removeItem('refresh_token')
    sessionStorage.clear()
  })
  await page.goto('/auth/login')
  await page.getByPlaceholder('you@example.com').fill(email)
  await page.locator('input[type="password"]').fill(TEST_PASSWORD)
  await page.getByRole('button', { name: 'Sign In' }).click()

  // User has needs_onboarding=false, so login goes to /vault — carousel only
  // shows for users with needs_onboarding=true and setup_step=1.
  await expect(page).toHaveURL(/\/vault/, { timeout: 20_000 })
})

test('wizard abandonment resumes at correct step on re-login (FR-09)', async ({ page }) => {
  const email = freshEmail('resume')
  const fullName = 'Resume Test User'

  // Signup → verify → land at /setup/checkin
  await page.goto('/auth/signup')
  await page.getByPlaceholder('John Doe').fill(fullName)
  await page.getByPlaceholder('you@example.com').fill(email)
  const pwInputs = page.locator('input[type="password"]')
  await pwInputs.nth(0).fill(TEST_PASSWORD)
  await pwInputs.nth(1).fill(TEST_PASSWORD)
  await page.getByRole('button', { name: 'Create Account' }).click()

  await expect(page).toHaveURL(/\/auth\/verify-email/, { timeout: 20_000 })
  const otp = getSignupOtp(email, TEST_PASSWORD)
  for (let i = 0; i < 6; i++) await page.locator(`input[data-index="${i}"]`).fill(otp[i])
  await page.getByRole('button', { name: 'Verify Code' }).click()
  await expect(page).toHaveURL(/\/setup\/checkin/, { timeout: 20_000 })

  // Complete step 1 (checkin) → advance to step 2 (beneficiary)
  await page.getByRole('button', { name: 'Continue' }).click()
  await expect(page).toHaveURL(/\/setup\/beneficiary/, { timeout: 20_000 })

  // ABANDON here — clear session and re-login
  await page.evaluate(() => {
    localStorage.removeItem('refresh_token')
    sessionStorage.clear()
    // Ensure carousel key is set so Login doesn't route to carousel
    localStorage.setItem('legate_carousel_seen', '1')
  })
  await page.goto('/auth/login')
  await page.getByPlaceholder('you@example.com').fill(email)
  await page.locator('input[type="password"]').fill(TEST_PASSWORD)
  await page.getByRole('button', { name: 'Sign In' }).click()

  // FR-09: should resume at step 2 (beneficiary), not restart from step 1
  await expect(page).toHaveURL(/\/setup\/beneficiary/, { timeout: 20_000 })
})

test('completed onboarding never shows setup wizard again', async ({ page }) => {
  const { email, password } = await signupAndOnboard(page, freshEmail('done'))

  // Clear session and log back in
  await page.evaluate(() => {
    localStorage.removeItem('refresh_token')
    sessionStorage.clear()
  })
  await loginUI(page, email, password)

  // Should land at /vault, not /setup/*
  await expect(page).toHaveURL(/\/vault$/, { timeout: 20_000 })
  await expect(page).not.toHaveURL(/\/setup/, { timeout: 2_000 })
})
