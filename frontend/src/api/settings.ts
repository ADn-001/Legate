/**
 * Settings API endpoints
 * - GET /settings/checkin
 * - PATCH /settings/checkin
 * - DELETE /users/me
 */

import client from './client'

export const settingsApi = {
  getCheckinSchedule: () => client.get('/settings/checkin'),
  updateCheckinSchedule: (data: any) => client.patch('/settings/checkin', data),
  deleteAccount: () => client.delete('/users/me'),
}
