import { test, expect } from '@playwright/test'
import { loginUI } from './helpers/onboarding'
import { loadSharedUser } from './helpers/sharedUser'
import { capsuleCard } from './helpers/capsules'

test('session survives a reload and a locked vault unlocks via the modal', async ({ page }) => {
  const { email, password } = loadSharedUser()
  await loginUI(page, email, password)

  // Client-side navigation keeps the in-memory CEK alive so Save Capsule
  // succeeds without an unlock modal. The page.reload() below tests bootstrap
  // (POST /auth/refresh) separately — that's the F2 requirement, not this goto.
  const title = 'Restore Test Capsule'
  await page.getByRole('button', { name: 'Create Capsule' }).click()
  await expect(page).toHaveURL(/\/vault\/capsules\/new/, { timeout: 10_000 })
  // Wait for the beneficiary auto-select before saving (see capsule-edit.spec.ts).
  await expect(page.locator('select')).not.toHaveValue('', { timeout: 10_000 })
  await page.locator('input[placeholder="e.g. Instructions for Sarah"]').fill(title)
  await page.locator('textarea[placeholder="Write your message here..."]').fill('Content for session-restore spec.')
  await page.getByRole('button', { name: 'Save Capsule' }).click()
  await expect(page).toHaveURL(/\/vault\/capsules$/, { timeout: 20_000 })

  // F2: reload must not log the user out. The access token is in-memory
  // only; this exercises App.tsx's refresh_token bootstrap.
  await page.reload()
  await expect(page).toHaveURL(/\/vault\/capsules$/, { timeout: 20_000 })
  const card = capsuleCard(page, title)
  await expect(card).toBeVisible()

  // The CEK was cleared by the reload (in-memory only, never persisted) —
  // opening the capsule must raise the unlock modal, not fail silently or
  // force a logout.
  await card.getByRole('button', { name: 'View capsule' }).click()
  await expect(page).toHaveURL(/\/vault\/capsules\/.+\/view$/, { timeout: 10_000 })
  await expect(page.getByText('Unlock your vault')).toBeVisible({ timeout: 10_000 })

  // Wrong password first: inline error, no logout, modal stays open.
  await page.locator('input[type="password"]').fill('TotallyWrongPassword999!')
  await page.getByRole('button', { name: 'Unlock' }).click()
  await expect(page.getByText('Incorrect password')).toBeVisible({ timeout: 10_000 })
  await expect(page.getByText('Unlock your vault')).toBeVisible()

  // Correct password unlocks and decrypts.
  await page.locator('input[type="password"]').fill(password)
  await page.getByRole('button', { name: 'Unlock' }).click()
  await expect(page.getByText('Content for session-restore spec.')).toBeVisible({ timeout: 10_000 })
})
