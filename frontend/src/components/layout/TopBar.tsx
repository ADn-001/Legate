import { Shield } from 'lucide-react'
import { useAuthStore } from '../../store/auth'

export default function TopBar() {
  const user = useAuthStore(s => s.user)
  const initials = user?.full_name?.split(' ').map(n => n[0]).join('').toUpperCase()
    || user?.email?.[0].toUpperCase()
    || '?'

  return (
    <header className="bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between">
      <div className="flex items-center gap-2">
        <Shield className="w-6 h-6 text-[#3D4F6B]" />
        <span className="text-xl font-bold text-[#3D4F6B]">Legate</span>
      </div>
      <div className="w-9 h-9 bg-[#3D4F6B] rounded-full flex items-center justify-center text-white text-sm font-semibold">
        {initials}
      </div>
    </header>
  )
}
