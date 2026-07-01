import { test, expect } from '@playwright/test'
import { loginUI } from './helpers/onboarding'
import { loadSharedUser } from './helpers/sharedUser'
import { capsuleCard } from './helpers/capsules'

test('view screen decrypts and renders a capsule; list shows the beneficiary name', async ({ page }) => {
  const { email, password } = loadSharedUser()
  await loginUI(page, email, password)

  // Client-side navigation keeps the in-memory CEK alive (see capsule-edit.spec.ts).
  const title = 'View Test Capsule'
  await page.getByRole('button', { name: 'Create Capsule' }).click()
  await expect(page).toHaveURL(/\/vault\/capsules\/new/, { timeout: 10_000 })
  // Wait for the beneficiary auto-select before saving (see capsule-edit.spec.ts).
  await expect(page.locator('select')).not.toHaveValue('', { timeout: 10_000 })
  await page.locator('input[placeholder="e.g. Instructions for Sarah"]').fill(title)
  // T9/Phase 4: tiptap contenteditable replaces textarea
  const editor = page.locator('[contenteditable="true"]')
  await editor.click()
  await editor.pressSequentially('Viewable content body.')
  await page.getByRole('button', { name: 'Save Capsule' }).click()
  await expect(page).toHaveURL(/\/vault\/capsules$/, { timeout: 20_000 })

  const card = capsuleCard(page, title)

  // F6: beneficiary name (the one created during onboarding) is shown
  // directly in the list, not just an ID.
  await expect(card.getByText(/^To: /)).toBeVisible({ timeout: 10_000 })

  await card.getByRole('button', { name: 'View capsule' }).click()
  await expect(page).toHaveURL(/\/vault\/capsules\/.+\/view$/, { timeout: 10_000 })
  await expect(page.getByText(title)).toBeVisible()
  await expect(page.getByText('Viewable content body.')).toBeVisible({ timeout: 10_000 })
  await expect(page.getByText(/^To: /)).toBeVisible()
})
