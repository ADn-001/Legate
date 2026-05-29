import client from './client'

export const settingsApi = {
  getCheckinSchedule: () => client.get('/settings/checkin'),
  updateCheckinSchedule: (data: { interval_days?: number; grace_period_days?: number }) =>
    client.patch('/settings/checkin', data),
  getStorageUsage: () => client.get('/settings/storage'),
}
