import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Shield, CheckCircle, AlertCircle, Clock } from 'lucide-react'
import client from '../../api/client'

const snoozeOptions = [
  { days: 7, label: 'Snooze for 7 days' },
  { days: 14, label: 'Snooze for 14 days' },
  { days: 30, label: 'Snooze for 30 days' },
]

type SnoozeStatus = 'idle' | 'loading' | 'success' | 'limit_reached' | 'error'

export default function CheckinSnooze() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token')
  const [status, setStatus] = useState<SnoozeStatus>('idle')
  const [selectedDays, setSelectedDays] = useState<number | null>(null)

  const handleSnooze = async (days: number) => {
    if (!token) { setStatus('error'); return }
    setSelectedDays(days)
    setStatus('loading')
    try {
      await client.get(`/checkin/snooze?token=${token}&days=${days}`)
      setStatus('success')
    } catch (err: unknown) {
      const code = (err as { response?: { status?: number } }).response?.status
      setStatus(code === 409 ? 'limit_reached' : 'error')
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex flex-col items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <div className="bg-white rounded-2xl shadow-lg p-8 text-center">
          <div className="flex justify-center mb-6">
            <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center">
              {status === 'success' ? (
                <CheckCircle className="w-8 h-8 text-green-600" />
              ) : status === 'error' || status === 'limit_reached' ? (
                <AlertCircle className="w-8 h-8 text-red-600" />
              ) : (
                <Clock className="w-8 h-8 text-[#3D4F6B]" />
              )}
            </div>
          </div>

          {status === 'idle' && (
            <>
              <div className="flex justify-center mb-4">
                <Shield className="w-6 h-6 text-[#3D4F6B]" />
              </div>
              <h1 className="text-2xl font-bold text-[#0D1117] mb-2">Snooze Check-in</h1>
              <p className="text-[#6B7280] mb-6">How long should we wait before checking in again?</p>
              <div className="space-y-3">
                {snoozeOptions.map(({ days, label }) => (
                  <button
                    key={days}
                    onClick={() => handleSnooze(days)}
                    className="w-full py-3 border-2 border-gray-200 rounded-xl text-[#0D1117] font-medium hover:border-[#3D4F6B] hover:bg-blue-50 transition-colors"
                  >
                    {label}
                  </button>
                ))}
              </div>
            </>
          )}

          {status === 'loading' && (
            <div className="py-8">
              <div className="w-12 h-12 border-4 border-[#3D4F6B] border-t-transparent rounded-full animate-spin mx-auto" />
              <p className="text-[#6B7280] mt-4">Snoozing for {selectedDays} days...</p>
            </div>
          )}

          {status === 'success' && (
            <>
              <h1 className="text-2xl font-bold text-[#0D1117] mb-2">Snoozed!</h1>
              <p className="text-[#6B7280]">We'll check in again in {selectedDays} days.</p>
            </>
          )}

          {status === 'limit_reached' && (
            <>
              <h1 className="text-xl font-bold text-[#0D1117] mb-2">Snooze limit reached</h1>
              <p className="text-[#6B7280]">You have reached your snooze limit for this period.</p>
            </>
          )}

          {status === 'error' && (
            <>
              <h1 className="text-xl font-bold text-[#0D1117] mb-2">Error</h1>
              <p className="text-[#6B7280]">This snooze link is invalid or has expired.</p>
            </>
          )}
        </div>
        <p className="text-center text-[#6B7280] text-xs mt-6">🔒 End-to-End Encrypted</p>
      </div>
    </div>
  )
}
