import client from './client'

export interface SignupPayload {
  email: string
  password: string
  encrypted_cek: string
  cek_iv: string
  pbkdf2_salt: string
  delivery_encrypted_cek: string | null
  delivery_cek_iv: string | null
}

export const authApi = {
  signup: (data: SignupPayload) => client.post('/auth/signup', data),
  verifyEmail: (data: { email: string; otp: string }) => client.post('/auth/verify-email', data),
  login: (data: { email: string; password: string }) => client.post('/auth/login', data),
  refresh: (data: { refresh_token: string }) => client.post('/auth/refresh', data),
  logout: (data: { refresh_token: string }) => client.post('/auth/logout', data),
  getMe: () => client.get('/auth/me'),
  getEncryptionKey: () => client.get('/auth/me/encryption-key'),
  getDeliveryWrappingKey: () => client.get('/auth/me/delivery-wrapping-key'),
  updateDeliveryKey: (data: { delivery_encrypted_cek: string; delivery_cek_iv: string }) =>
    client.patch('/auth/me/encryption-key', data),
}
