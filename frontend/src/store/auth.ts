import { create } from 'zustand'

export interface User {
  id: string
  email: string
  full_name?: string
  email_verified: boolean
  status?: 'active' | 'suspended' | 'memorialized' | 'pending_deletion' | 'deleted'
  needs_onboarding?: boolean
}

interface AuthState {
  user: User | null
  accessToken: string | null
  isAuthenticated: boolean
  needsOnboarding: boolean
  bootstrapped: boolean
  setTokens: (accessToken: string, refreshToken: string) => void
  setUser: (user: User) => void
  setNeedsOnboarding: (val: boolean) => void
  setBootstrapped: (val: boolean) => void
  clear: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  accessToken: null,
  isAuthenticated: false,
  needsOnboarding: false,
  bootstrapped: false,
  setTokens: (accessToken, refreshToken) => {
    localStorage.setItem('refresh_token', refreshToken)
    set({ accessToken, isAuthenticated: true })
  },
  setUser: (user) => set({ user }),
  setNeedsOnboarding: (val) => set({ needsOnboarding: val }),
  setBootstrapped: (val) => set({ bootstrapped: val }),
  clear: () => {
    localStorage.removeItem('refresh_token')
    set({ user: null, accessToken: null, isAuthenticated: false, needsOnboarding: false, bootstrapped: false })
  },
}))
