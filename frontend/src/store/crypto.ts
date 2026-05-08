/**
 * Crypto Store (Zustand)
 * - CEK (Content Encryption Key) - in-memory only, never persisted
 * - Methods to set/clear CEK
 *
 * CRITICAL: CEK must NEVER be written to localStorage, sessionStorage, IndexedDB, etc.
 * It lives in-memory only. On logout or page refresh, user must re-derive it from password.
 */

import { create } from 'zustand'

interface CryptoState {
  cek: CryptoKey | null
  setCek: (key: CryptoKey) => void
  clearCek: () => void
}

export const useCryptoStore = create<CryptoState>((set) => ({
  cek: null,
  setCek: (key) => set({ cek: key }),
  clearCek: () => set({ cek: null }),
}))
