import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { WifiOff, X } from 'lucide-react'
import TopBar from './TopBar'
import BottomNav from './BottomNav'
import UnlockModal from '../auth/UnlockModal'
import { flushOutbox } from '../../utils/outbox'
import { useAuthStore } from '../../store/auth'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const hideNavPaths = ['/auth/', '/setup/', '/checkin/', '/emergency/']

interface Toast {
  id: number
  message: string
}

let toastId = 0

export default function AppShell({ children }: { children: React.ReactNode }) {
  const location = useLocation()
  const hideNav = hideNavPaths.some(p => location.pathname.startsWith(p))
    || location.pathname === '/'

  const [isOnline, setIsOnline] = useState(navigator.onLine)
  const [toasts, setToasts] = useState<Toast[]>([])
  const accessToken = useAuthStore(s => s.accessToken)

  function addToast(message: string) {
    const id = ++toastId
    setToasts(prev => [...prev, { id, message }])
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 5000)
  }

  function dismissToast(id: number) {
    setToasts(prev => prev.filter(t => t.id !== id))
  }

  // Online/offline tracking
  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true)
      // Flush offline outbox when connectivity is restored
      flushOutbox(accessToken, API_BASE_URL).catch(() => {})
    }
    const handleOffline = () => setIsOnline(false)
    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)
    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [accessToken])

  // Rate-limit toast (dispatched by api/client.ts on 429 responses)
  useEffect(() => {
    const handler = (e: Event) => {
      const msg = (e as CustomEvent<{ message: string }>).detail?.message
      if (msg) addToast(msg)
    }
    window.addEventListener('legate:ratelimit', handler)
    return () => window.removeEventListener('legate:ratelimit', handler)
  }, [])

  return (
    <div className="min-h-screen bg-[#F0F2F5] flex flex-col">
      {!hideNav && <TopBar />}

      {/* Offline banner */}
      {!isOnline && (
        <div className="bg-amber-500 text-white text-center text-sm py-2 px-4 flex items-center justify-center gap-2">
          <WifiOff className="w-4 h-4" />
          You're offline. Changes may not be saved until you reconnect.
        </div>
      )}

      <main className={`flex-1 ${!hideNav ? 'pb-20' : ''}`}>
        {children}
      </main>

      {!hideNav && <BottomNav />}
      <UnlockModal />

      {/* Toast stack (rate-limit + other notifications) */}
      {toasts.length > 0 && (
        <div className="fixed bottom-24 right-4 z-50 flex flex-col gap-2 max-w-xs">
          {toasts.map(t => (
            <div key={t.id} className="bg-[#0D1117] text-white text-sm rounded-xl px-4 py-3 shadow-lg flex items-start gap-2">
              <span className="flex-1">{t.message}</span>
              <button onClick={() => dismissToast(t.id)} className="flex-shrink-0 p-0.5 hover:opacity-70">
                <X className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
