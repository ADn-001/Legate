/**
 * Auth API endpoints
 * - POST /auth/signup
 * - POST /auth/verify-email
 * - POST /auth/login
 * - GET /auth/me
 * - GET /auth/me/encryption-key
 * - POST /auth/refresh
 * - POST /auth/logout
 */

import client from './client'

export const authApi = {
  signup: (data: any) => client.post('/auth/signup', data),
  verifyEmail: (data: any) => client.post('/auth/verify-email', data),
  login: (data: any) => client.post('/auth/login', data),
  getMe: () => client.get('/auth/me'),
  getEncryptionKey: () => client.get('/auth/me/encryption-key'),
  refresh: (data: any) => client.post('/auth/refresh', data),
  logout: () => client.post('/auth/logout'),
}
