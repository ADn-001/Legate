/**
 * Activity/Audit Log API endpoints
 * - GET /activity (paginated)
 */

import client from './client'

export const activityApi = {
  list: (params?: any) => client.get('/activity', { params }),
}
