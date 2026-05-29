import { create } from 'zustand'

export interface User {
  id: string
  email: string
  full_name?: string
  email_verified: boolean
  needs_onboarding?: boolean
}

interface AuthState {
  user: User | null
  accessToken: string | null
  isAuthenticated: boolean
  needsOnboarding: boolean
  login: (user: User, accessToken: string, refreshToken: string) => void
  logout: () => void
  setUser: (user: User) => void
  setNeedsOnboarding: (val: boolean) => void
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  accessToken: null,
  isAuthenticated: false,
  needsOnboarding: false,
  login: (user, accessToken, refreshToken) => {
    localStorage.setItem('refresh_token', refreshToken)
    set({ user, accessToken, isAuthenticated: true })
  },
  logout: () => {
    localStorage.removeItem('refresh_token')
    set({ user: null, accessToken: null, isAuthenticated: false, needsOnboarding: false })
  },
  setUser: (user) => set({ user }),
  setNeedsOnboarding: (val) => set({ needsOnboarding: val }),
}))
