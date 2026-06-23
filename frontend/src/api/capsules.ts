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
  // Edit flow: sends the encrypted blob to the backend which uploads it to
  // Supabase Storage server-side, avoiding the browser→Supabase signed-URL PUT
  // that can hang when the object path already exists.
  uploadContent: (id: string, data: Uint8Array) =>
    client.put(`/capsules/${id}/content`, data, {
      headers: { 'Content-Type': 'application/octet-stream' },
    }),
}
