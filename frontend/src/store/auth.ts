/**
 * Authentication Store (Zustand)
 * - User state (logged in user info)
 * - Access and refresh tokens
 * - Login/logout actions
 */

import { create } from 'zustand'

interface User {
  id: string
  email: string
  firstName?: string
  lastName?: string
}

interface AuthState {
  user: User | null
  accessToken: string | null
  isAuthenticated: boolean
  login: (user: User, accessToken: string) => void
  logout: () => void
  setUser: (user: User) => void
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  accessToken: null,
  isAuthenticated: false,
  login: (user, accessToken) => set({ user, accessToken, isAuthenticated: true }),
  logout: () => set({ user: null, accessToken: null, isAuthenticated: false }),
  setUser: (user) => set({ user }),
}))
