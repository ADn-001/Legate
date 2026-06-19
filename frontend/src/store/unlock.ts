/**
 * Unlock Modal Store (Zustand)
 *
 * Coordinates the global "unlock vault" modal (see
 * components/auth/UnlockModal.tsx). Any code that needs the CEK should call
 * `requireCek()`, which resolves immediately if the CEK is already available
 * and not locked, or otherwise opens the unlock modal and resolves once the
 * user enters their correct password (or rejects if they cancel).
 */

import { create } from 'zustand'
import { useCryptoStore } from './crypto'

interface PendingUnlock {
  resolve: (cek: CryptoKey) => void
  reject: (err: Error) => void
}

interface UnlockState {
  isOpen: boolean
  pending: PendingUnlock | null
  _open: (pending: PendingUnlock) => void
  _close: () => void
}

export const useUnlockStore = create<UnlockState>((set) => ({
  isOpen: false,
  pending: null,
  _open: (pending) => set({ isOpen: true, pending }),
  _close: () => set({ isOpen: false, pending: null }),
}))

export function requireCek(): Promise<CryptoKey> {
  const { cek, locked } = useCryptoStore.getState()
  if (cek && !locked) return Promise.resolve(cek)
  return new Promise<CryptoKey>((resolve, reject) => {
    useUnlockStore.getState()._open({ resolve, reject })
  })
}
