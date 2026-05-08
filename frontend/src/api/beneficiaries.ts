/**
 * Beneficiary API endpoints
 * - GET /beneficiaries
 * - POST /beneficiaries
 * - PATCH /beneficiaries/:id
 * - DELETE /beneficiaries/:id
 */

import client from './client'

export const beneficiariesApi = {
  list: () => client.get('/beneficiaries'),
  create: (data: any) => client.post('/beneficiaries', data),
  update: (id: string, data: any) => client.patch(`/beneficiaries/${id}`, data),
  delete: (id: string) => client.delete(`/beneficiaries/${id}`),
}
