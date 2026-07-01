import { test, expect } from '@playwright/test'
import { loginUI } from './helpers/onboarding'
import { loadSharedUser } from './helpers/sharedUser'
import { capsuleCard } from './helpers/capsules'

test('editing a capsule decrypts existing content and re-save never duplicates it', async ({ page }) => {
  const { email, password } = loadSharedUser()
  await loginUI(page, email, password)

  // Client-side navigation (React Router) instead of page.goto to keep the
  // in-memory CEK alive. page.goto is a hard navigation that wipes JS state
  // and sets locked=true after bootstrap, requiring an unlock modal on every
  // subsequent save. The Dashboard "Create Capsule" button calls navigate(),
  // so Zustand store state (CEK) is preserved across the route change.
  const title = 'Edit Test Capsule'
  await page.getByRole('button', { name: 'Create Capsule' }).click()
  await expect(page).toHaveURL(/\/vault\/capsules\/new/, { timeout: 10_000 })
  // useBeneficiaries() is an async React Query fetch. The auto-select effect fires
  // only after it resolves. If Save is clicked before that, beneficiaryId is still ''
  // and handleSave() bails with "Please select a beneficiary" without reaching the API.
  await expect(page.locator('select')).not.toHaveValue('', { timeout: 10_000 })
  await page.locator('input[placeholder="e.g. Instructions for Sarah"]').fill(title)
  // T9/Phase 4: editor is tiptap (contenteditable div), not a textarea
  const editor = page.locator('[contenteditable="true"]')
  await editor.click()
  await editor.pressSequentially('Original content.')
  await page.getByRole('button', { name: 'Save Capsule' }).click()
  await expect(page).toHaveURL(/\/vault\/capsules$/, { timeout: 20_000 })

  const card = capsuleCard(page, title)
  // Wait for React Query to fetch and render the capsule list before asserting
  // count — card.count() is not a waiting call and returns 0 if the list fetch
  // hasn't resolved yet.
  await expect(card).toHaveCount(1, { timeout: 10_000 })

  // F5: edit route fetches the capsule, downloads the signed blob, and
  // decrypts it with the CEK into the tiptap editor — not blank.
  await card.getByRole('button', { name: 'Edit capsule' }).click()
  await expect(page).toHaveURL(/\/vault\/capsules\/[^/]+$/, { timeout: 10_000 })
  await expect(page.locator('[contenteditable="true"]')).toContainText(
    'Original content.',
    { timeout: 10_000 }
  )

  await page.locator('[contenteditable="true"]').selectText()
  await page.keyboard.type('Updated content after edit.')
  await page.getByRole('button', { name: 'Update Capsule' }).click()
  await expect(page).toHaveURL(/\/vault\/capsules$/, { timeout: 20_000 })

  // The Phase 3 bug (line-79) was CapsuleEditor calling `create` instead of
  // `update` in edit mode, silently duplicating the capsule.
  const countAfter = await capsuleCard(page, title).count()
  expect(countAfter).toBe(1)

  await capsuleCard(page, title).getByRole('button', { name: 'View capsule' }).click()
  await expect(page.getByText('Updated content after edit.')).toBeVisible({ timeout: 10_000 })
  await expect(page.getByText('Original content.')).not.toBeVisible()
})
