import { Lock, Users, Shield, Clock } from 'lucide-react'
import { useLocation, useNavigate } from 'react-router-dom'

const tabs = [
  { label: 'Vault', icon: Lock, path: '/vault' },
  { label: 'People', icon: Users, path: '/people' },
  { label: 'Security', icon: Shield, path: '/security' },
  { label: 'Activity', icon: Clock, path: '/activity' },
]

export default function BottomNav() {
  const location = useLocation()
  const navigate = useNavigate()

  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 flex z-40">
      {tabs.map(({ label, icon: Icon, path }) => {
        const active = location.pathname.startsWith(path)
        return (
          <button
            key={path}
            onClick={() => navigate(path)}
            className={`flex-1 flex flex-col items-center py-2 gap-1 transition-colors ${active ? 'text-[#3D4F6B]' : 'text-gray-400'}`}
          >
            <Icon className="w-5 h-5" />
            <span className="text-xs font-medium">{label}</span>
          </button>
        )
      })}
    </nav>
  )
}
