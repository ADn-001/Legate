import { Shield } from 'lucide-react'

interface SecurityBannerProps {
  children: React.ReactNode
  className?: string
}

export default function SecurityBanner({ children, className = '' }: SecurityBannerProps) {
  return (
    <div className={`security-banner ${className}`}>
      <Shield className="w-5 h-5 text-[#3D4F6B] flex-shrink-0 mt-0.5" />
      <div className="text-sm text-[#3D4F6B]">{children}</div>
    </div>
  )
}
