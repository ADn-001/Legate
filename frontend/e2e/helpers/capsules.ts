import { Page, Locator } from '@playwright/test'

/**
 * Several specs share one onboarded user (see helpers/sharedUser.ts), so
 * that account's capsule list accumulates one card per spec that's run
 * before it in the same session. Scope to the specific card by title
 * instead of assuming "the only capsule" / "the first View button".
 *
 * The global-setup cleanup issues DELETE /api/capsules/:id which soft-deletes
 * (sets status=pending_deletion). Those cards remain visible in the list with
 * a "Pending Deletion" badge. Filtering them out keeps each spec scoped to
 * the single active card it created in the current run.
 */
export function capsuleCard(page: Page, title: string): Locator {
  return page.locator('div.rounded-2xl.shadow-md.p-6')
    .filter({ hasText: title })
    .filter({ hasNotText: 'Pending Deletion' })
}
