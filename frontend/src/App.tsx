import { useEffect } from 'react'
import { AppRouter } from './router'
import { authApi } from './api/auth'
import { useAuthStore } from './store/auth'
import { useCryptoStore } from './store/crypto'

export default function App() {
  const bootstrapped = useAuthStore((s) => s.bootstrapped)

  useEffect(() => {
    const bootstrap = async () => {
      const refreshToken = localStorage.getItem('refresh_token')
      if (refreshToken) {
        try {
          const { data } = await authApi.refresh({ refresh_token: refreshToken })
          useAuthStore.getState().setTokens(data.access_token, data.refresh_token)

          const { data: meData } = await authApi.getMe()
          useAuthStore.getState().setUser(meData)
          useAuthStore.getState().setNeedsOnboarding(!!meData.needs_onboarding)

          // The CEK cannot be re-derived without the password — any crypto
          // operation must go through the unlock modal (store/unlock.ts).
          useCryptoStore.getState().setLocked(true)
        } catch {
          useAuthStore.getState().clear()
        }
      }
      useAuthStore.getState().setBootstrapped(true)
    }
    bootstrap()
  }, [])

  if (!bootstrapped) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center">
        <div className="w-12 h-12 border-4 border-[#3D4F6B] border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  return <AppRouter />
}
