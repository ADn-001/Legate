import client from './client'

export interface CheckinScheduleUpdate {
  interval_days?: number
  grace_period_days?: number
  // Phase B: demo-mode-only fields — the server rejects these with 403
  // unless DEMO_MODE=true.
  check_interval_minutes?: number
  grace_period_minutes?: number
  emergency_confirm_minutes?: number
  clear_minute_overrides?: boolean
}

export const settingsApi = {
  getCheckinSchedule: () => client.get('/settings/checkin'),
  updateCheckinSchedule: (data: CheckinScheduleUpdate) =>
    client.patch('/settings/checkin', data),
  getStorageUsage: () => client.get('/settings/storage'),
  // T5 (Phase 4): general user settings — wizard step and onboarding flag
  getSettings: () => client.get('/settings/'),
  patchSettings: (data: { setup_step?: number; needs_onboarding?: boolean }) =>
    client.patch('/settings/', data),
}
