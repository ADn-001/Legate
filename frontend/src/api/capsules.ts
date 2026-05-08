/**
 * Capsule API endpoints
 * - GET /capsules
 * - GET /capsules/:id
 * - POST /capsules
 * - PATCH /capsules/:id
 * - DELETE /capsules/:id
 */

import client from './client'

export const capsulesApi = {
  list: () => client.get('/capsules'),
  get: (id: string) => client.get(`/capsules/${id}`),
  create: (data: any) => client.post('/capsules', data),
  update: (id: string, data: any) => client.patch(`/capsules/${id}`, data),
  delete: (id: string) => client.delete(`/capsules/${id}`),
}
