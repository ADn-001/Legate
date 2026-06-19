import client from './client'

export interface SignupPayload {
  email: string
  password: string
  full_name: string | null
  encrypted_cek: string
  cek_iv: string
  pbkdf2_salt: string
  delivery_encrypted_cek: string | null
  delivery_cek_iv: string | null
}

export const authApi = {
  signup: (data: SignupPayload) => client.post('/auth/signup', data),
  verifyEmail: (data: { email: string; otp: string }) => client.post('/auth/verify-email', data),
  resendOtp: (data: { email: string }) => client.post('/auth/resend-otp', data),
  login: (data: { email: string; password: string }) => client.post('/auth/login', data),
  refresh: (data: { refresh_token: string }) => client.post('/auth/refresh', data),
  logout: (data: { refresh_token: string }) => client.post('/auth/logout', data),
  getMe: () => client.get('/auth/me'),
  getEncryptionKey: () => client.get('/auth/me/encryption-key'),
  getDeliveryWrappingKey: () => client.get('/auth/me/delivery-wrapping-key'),
  updateDeliveryKey: (data: { delivery_encrypted_cek: string; delivery_cek_iv: string }) =>
    client.patch('/auth/me/encryption-key', data),
  updatePrimaryKey: (data: { encrypted_cek: string; cek_iv: string; pbkdf2_salt: string }) =>
    client.patch('/auth/me/encryption-key/primary', data),
  setRecoveryKey: (data: {
    recovery_encrypted_cek: string
    recovery_cek_iv: string
    recovery_salt: string
    recovery_phrase_hash: string
  }) => client.patch('/auth/me/recovery-key', data),
  validateRecoveryPhrase: (data: { recovery_phrase_hash: string }) =>
    client.post('/auth/me/recovery-key/validate', data),
  forgotPassword: (data: { email: string }) =>
    client.post('/auth/forgot-password', data),
  resetPassword: (data: { new_password: string; encrypted_cek: string; cek_iv: string; pbkdf2_salt: string }) =>
    client.post('/auth/reset-password', data),
  resetPasswordDataLoss: (data: { new_password: string; encrypted_cek: string; cek_iv: string; pbkdf2_salt: string }) =>
    client.post('/auth/reset-password/data-loss', data),
  changePassword: (data: {
    current_password: string
    new_password: string
    encrypted_cek: string
    cek_iv: string
    pbkdf2_salt: string
  }) => client.post('/auth/change-password', data),
}
