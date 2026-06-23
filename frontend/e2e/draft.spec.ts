import { test, expect } from '@playwright/test'
import { loginUI } from './helpers/onboarding'
import { loadSharedUser } from './helpers/sharedUser'

test('draft autosave is encrypted at rest and restores after unlock', async ({ page }) => {
  const { email, password } = loadSharedUser()
  await loginUI(page, email, password)

  // Client-side navigation keeps the in-memory CEK alive. page.goto('/vault/capsules/new')
  // is a hard nav: it wipes JS state and bootstrap sets locked=true. With locked=true,
  // persistDraft() bails immediately (`if (!cek || locked) return`) — nothing ever
  // gets saved to localStorage and the 40s poll below times out. Using the Dashboard
  // button keeps CEK in memory so autosave can actually encrypt and persist the draft.
  await page.getByRole('button', { name: 'Create Capsule' }).click()
  await expect(page).toHaveURL(/\/vault\/capsules\/new/, { timeout: 10_000 })
  const secretSentence = 'This sentence must never appear in plaintext in localStorage.'
  const secretTitle = 'Draft Test Capsule'
  await page.locator('input[placeholder="e.g. Instructions for Sarah"]').fill(secretTitle)
  await page.locator('textarea[placeholder="Write your message here..."]').fill(secretSentence)

  // Autosave runs on a 30s interval (CapsuleEditor.tsx) — poll rather than
  // sleep blindly, but it genuinely takes about that long.
  await expect
    .poll(() => page.evaluate(() => localStorage.getItem('draft_capsule_new')), { timeout: 40_000 })
    .not.toBeNull()

  const draftRaw = await page.evaluate(() => localStorage.getItem('draft_capsule_new'))
  expect(draftRaw).not.toContain(secretSentence)
  expect(draftRaw).not.toContain(secretTitle)
  // T9: on-disk shape is `{ iv: hex, data: base64 }` — opaque without the CEK.
  const parsed = JSON.parse(draftRaw!)
  expect(parsed.iv).toBeTruthy()
  expect(parsed.data).toBeTruthy()

  // Reload clears the in-memory CEK. Re-opening the new-capsule editor
  // must prompt to unlock before it can decrypt the saved draft.
  await page.reload()
  await expect(page.getByText('Unlock your vault')).toBeVisible({ timeout: 10_000 })
  await page.locator('input[type="password"]').fill(password)
  await page.getByRole('button', { name: 'Unlock' }).click()

  await expect(page.locator('input[placeholder="e.g. Instructions for Sarah"]')).toHaveValue(secretTitle, {
    timeout: 10_000,
  })
  await expect(page.locator('textarea[placeholder="Write your message here..."]')).toHaveValue(secretSentence)
})
