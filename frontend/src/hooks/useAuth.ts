/**
 * useAuth hook
 * Provides auth operations and state
 */

import { useAuthStore } from '../store/auth'

export const useAuth = () => {
  return useAuthStore()
}
