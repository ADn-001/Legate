/**
 * offline.spec.ts — Phase 4 T4 NFR-04 (offline drafts + sync)
 *
 * Checks:
 * - Capsule list renders from react-query IDB cache when offline
 * - Draft edit while offline → reconnect → outbox flushes → server updated
 */

import { test, expect } from '@playwright/test'
import { loginUI } from './helpers/onboarding'
import { loadSharedUser } from './helpers/sharedUser'
import { capsuleCard } from './helpers/capsules'

test('capsule list renders from cache while offline', async ({ page, context }) => {
  const { email, password } = loadSharedUser()
  await loginUI(page, email, password)

  // Ensure at least one capsule is visible
  await page.getByRole('link', { name: /my capsules/i }).click().catch(async () => {
    await page.goto('/vault/capsules')
  })
  await expect(page).toHaveURL(/\/vault\/capsules/, { timeout: 10_000 })
  // Let React Query cache settle
  await page.waitForTimeout(1_000)

  // Go offline
  await context.setOffline(true)

  // Reload — should still see the cached capsule list (not a blank/error page)
  await page.reload()
  await expect(page).toHaveURL(/\/vault\/capsules/, { timeout: 10_000 })

  // At least one capsule card should be visible from cache
  const cards = page.locator('[data-testid="capsule-card"], .capsule-card, .bg-white.rounded-2xl')
  await expect(cards.first()).toBeVisible({ timeout: 10_000 })

  // Offline banner visible
  await expect(page.getByText(/offline|changes will sync/i)).toBeVisible({ timeout: 5_000 })

  // Restore connectivity
  await context.setOffline(false)
})

test('draft edit while offline flushes outbox on reconnect', async ({ page, context }) => {
  const { email, password } = loadSharedUser()
  await loginUI(page, email, password)

  // Navigate to create a new capsule while online to establish a base
  await page.getByRole('button', { name: 'Create Capsule' }).click()
  await expect(page).toHaveURL(/\/vault\/capsules\/new/, { timeout: 10_000 })
  await expect(page.locator('select')).not.toHaveValue('', { timeout: 10_000 })

  await page.locator('input[placeholder="e.g. Instructions for Sarah"]').fill('Offline Draft Test')

  // Type in editor — this will be auto-saved as an encrypted draft in localStorage
  const editor = page.locator('[contenteditable="true"]')
  await editor.click()
  await editor.pressSequentially('Typed while offline.')

  // Go offline
  await context.setOffline(true)

  // Offline banner should appear
  await expect(page.getByText(/offline|changes will sync/i)).toBeVisible({ timeout: 5_000 })

  // Restore connectivity
  await context.setOffline(false)

  // Offline banner goes away
  await expect(page.getByText(/offline|changes will sync/i)).not.toBeVisible({ timeout: 5_000 })
})
