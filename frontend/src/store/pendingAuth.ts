/**
 * Pending Auth Store (Zustand)
 *
 * Holds the password entered at signup time, in memory only, until the
 * verify-email step completes and the CEK has been wrapped/delivered.
 *
 * CRITICAL: never persist this to sessionStorage/localStorage — it holds the
 * user's plaintext password. If the page is refreshed between signup and
 * verification, this store is empty and VerifyEmail must re-prompt for the
 * password (see T3 in PHASE_3_FRONTEND_CRITICAL_BUGS.md).
 */

import { create } from 'zustand'

interface PendingAuthState {
  email: string | null
  password: string | null
  set: (email: string, password: string) => void
  clear: () => void
}

export const usePendingAuthStore = create<PendingAuthState>((set) => ({
  email: null,
  password: null,
  set: (email, password) => set({ email, password }),
  clear: () => set({ email: null, password: null }),
}))
