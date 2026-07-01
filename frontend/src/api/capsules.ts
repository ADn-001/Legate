import client from './client'
import type { MediaKind } from '../types/api'

export interface CapsuleCreatePayload {
  title: string
  beneficiary_id: string
  cipher_iv: string  // lowercase hex string
}

export interface MediaCreatePayload {
  filename: string
  content_type: string
  size_bytes: number
  kind: MediaKind
  cipher_iv: string  // hex (photos) or JSON string (chunked video)
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

  // ── Media attachment API (T1/T2, Phase 4) ────────────────────────────────
  // POST  /capsules/{id}/media            → create row + get upload URL
  createMedia: (id: string, payload: MediaCreatePayload) =>
    client.post(`/capsules/${id}/media`, payload),
  // PUT   /capsules/{id}/media/{mid}/upload  → server-side blob upload
  uploadMediaContent: (id: string, mid: string, data: Uint8Array | Blob, onProgress?: (pct: number) => void) =>
    client.put(`/capsules/${id}/media/${mid}/upload`, data, {
      headers: { 'Content-Type': 'application/octet-stream' },
      onUploadProgress: onProgress
        ? (e) => { if (e.total) onProgress(Math.round((e.loaded / e.total) * 100)) }
        : undefined,
    }),
  // POST  /capsules/{id}/media/{mid}/confirm → mark ready after upload
  confirmMedia: (id: string, mid: string) =>
    client.post(`/capsules/${id}/media/${mid}/confirm`),
  // PUT   /capsules/{id}/media/{mid}/thumbnail → upload encrypted thumbnail
  uploadThumbnail: (id: string, mid: string, data: Uint8Array | Blob) =>
    client.put(`/capsules/${id}/media/${mid}/thumbnail`, data, {
      headers: { 'Content-Type': 'application/octet-stream' },
    }),
  // GET   /capsules/{id}/media/{mid}      → get signed download URL
  getMediaUrl: (id: string, mid: string) =>
    client.get(`/capsules/${id}/media/${mid}`),
  // DELETE /capsules/{id}/media/{mid}     → remove row + storage
  deleteMedia: (id: string, mid: string) =>
    client.delete(`/capsules/${id}/media/${mid}`),
}
