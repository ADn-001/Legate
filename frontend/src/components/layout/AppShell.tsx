import { useLocation } from 'react-router-dom'
import TopBar from './TopBar'
import BottomNav from './BottomNav'

const hideNavPaths = ['/auth/', '/setup/', '/checkin/', '/emergency/']

export default function AppShell({ children }: { children: React.ReactNode }) {
  const location = useLocation()
  const hideNav = hideNavPaths.some(p => location.pathname.startsWith(p))
    || location.pathname === '/'

  return (
    <div className="min-h-screen bg-[#F0F2F5] flex flex-col">
      {!hideNav && <TopBar />}
      <main className={`flex-1 ${!hideNav ? 'pb-20' : ''}`}>
        {children}
      </main>
      {!hideNav && <BottomNav />}
    </div>
  )
}
