import { Outlet, useLocation } from 'react-router-dom'
import { Shield } from 'lucide-react'

const steps = [
  { path: '/setup/checkin', label: 'Check-in' },
  { path: '/setup/beneficiary', label: 'Beneficiary' },
  { path: '/setup/capsule', label: 'Capsule' },
  { path: '/setup/recovery', label: 'Recovery' },
]

export default function SetupLayout() {
  const location = useLocation()
  const currentStep = steps.findIndex(s => location.pathname.startsWith(s.path))
  const stepNumber = currentStep >= 0 ? currentStep + 1 : 1

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      <div className="max-w-md mx-auto px-4 pt-8 pb-4">
        <div className="flex items-center justify-center gap-2 mb-8">
          <Shield className="w-6 h-6 text-[#3D4F6B]" />
          <span className="text-xl font-bold text-[#3D4F6B]">Legate</span>
        </div>

        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-[#3D4F6B]">Step {stepNumber} of {steps.length}</span>
            {currentStep === 2 && (
              <span className="text-xs text-[#6B7280]">Optional step</span>
            )}
          </div>
          <div className="flex gap-1">
            {steps.map((_, i) => (
              <div
                key={i}
                className={`flex-1 h-2 rounded-full transition-colors ${i < stepNumber ? 'bg-[#3D4F6B]' : 'bg-gray-200'}`}
              />
            ))}
          </div>
          <div className="flex justify-between mt-1">
            {steps.map((s, i) => (
              <span key={i} className={`text-xs ${i < stepNumber ? 'text-[#3D4F6B]' : 'text-gray-400'}`}>
                {s.label}
              </span>
            ))}
          </div>
        </div>
      </div>
      <Outlet />
    </div>
  )
}
