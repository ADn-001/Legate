/**
 * API Client - Axios instance with interceptors
 * - Automatic token refresh on 401
 * - Request/response interceptors
 * - Base URL configuration from env
 */

import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://api.legate.app'

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// TODO: Add request interceptor for Authorization header
// TODO: Add response interceptor for token refresh logic

export default client
