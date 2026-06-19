/**
 * Crypto Store (Zustand)
 * - CEK (Content Encryption Key) - in-memory only, never persisted
 * - Methods to set/clear CEK
 * - `locked`: true when the user is authenticated but the CEK has not been
 *   (re-)derived for this session (e.g. after a session restore from a
 *   refresh token, where the password is not available). Crypto operations
 *   should check `locked` and, if true, prompt via the unlock modal
 *   (see store/unlock.ts) before proceeding.
 *
 * CRITICAL: CEK must NEVER be written to localStorage, sessionStorage, IndexedDB, etc.
 * It lives in-memory only. On logout or page refresh, user must re-derive it from password.
 */

import { create } from 'zustand'

interface CryptoState {
  cek: CryptoKey | null
  locked: boolean
  setCek: (key: CryptoKey) => void
  clearCek: () => void
  setLocked: (val: boolean) => void
}

export const useCryptoStore = create<CryptoState>((set) => ({
  cek: null,
  locked: false,
  setCek: (key) => set({ cek: key, locked: false }),
  clearCek: () => set({ cek: null, locked: false }),
  setLocked: (val) => set({ locked: val }),
}))
