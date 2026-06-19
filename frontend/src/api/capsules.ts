import client from './client'

export interface CapsuleCreatePayload {
  title: string
  beneficiary_id: string
  cipher_iv: string  // lowercase hex string
}

export const capsulesApi = {
  list: () => client.get('/capsules/'),
  get: (id: string) => client.get(`/capsules/${id}`),
  create: (data: CapsuleCreatePayload) => client.post('/capsules/', data),
  update: (id: string, data: Record<string, unknown>) => client.patch(`/capsules/${id}`, data),
  delete: (id: string) => client.delete(`/capsules/${id}`),
  getContent: (id: string) => client.get(`/capsules/${id}/content`),
  getUploadUrl: (id: string) => client.post(`/capsules/${id}/content`),
}
