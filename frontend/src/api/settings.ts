import client from './client'

export const settingsApi = {
  getCheckinSchedule: () => client.get('/settings/checkin'),
  updateCheckinSchedule: (data: { interval_days?: number; grace_period_days?: number }) =>
    client.patch('/settings/checkin', data),
  getStorageUsage: () => client.get('/settings/storage'),
  // T5 (Phase 4): general user settings — wizard step and onboarding flag
  getSettings: () => client.get('/settings/'),
  patchSettings: (data: { setup_step?: number; needs_onboarding?: boolean }) =>
    client.patch('/settings/', data),
}
