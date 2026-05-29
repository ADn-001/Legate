import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Shield, CheckCircle, AlertCircle, PauseCircle } from 'lucide-react'
import client from '../../api/client'

type PauseStatus = 'idle' | 'loading' | 'success' | 'limit_reached' | 'error'

export default function EmergencyPause() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token')
  const [status, setStatus] = useState<PauseStatus>('idle')

  const handlePause = async () => {
    if (!token) { setStatus('error'); return }
    setStatus('loading')
    try {
      await client.get(`/checkin/emergency/pause?token=${token}`)
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
          <div className="flex items-center justify-center gap-2 mb-8">
            <Shield className="w-7 h-7 text-[#3D4F6B]" />
            <span className="text-xl font-bold text-[#3D4F6B]">Legate</span>
          </div>

          <div className="flex justify-center mb-6">
            <div className={`w-20 h-20 rounded-full flex items-center justify-center ${
              status === 'success' ? 'bg-green-100' :
              status === 'limit_reached' || status === 'error' ? 'bg-red-100' :
              'bg-amber-100'
            }`}>
              {status === 'success' ? (
                <CheckCircle className="w-10 h-10 text-green-600" />
              ) : status === 'limit_reached' || status === 'error' ? (
                <AlertCircle className="w-10 h-10 text-red-600" />
              ) : (
                <PauseCircle className="w-10 h-10 text-amber-600" />
              )}
            </div>
          </div>

          {(status === 'idle' || status === 'loading') && (
            <>
              <h1 className="text-2xl font-bold text-[#0D1117] mb-2">Pause Delivery</h1>
              <p className="text-[#6B7280] mb-4">
                You are listed as an emergency contact. Click below to pause delivery for 7 days while you verify the account holder is okay.
              </p>
              <p className="text-xs text-[#6B7280] bg-blue-50 p-3 rounded-lg mb-6">
                You may do this up to 2 times total.
              </p>
              <button
                onClick={handlePause}
                disabled={status === 'loading'}
                className="w-full py-4 bg-amber-500 text-white rounded-2xl font-semibold hover:bg-amber-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {status === 'loading' && (
                  <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                )}
                Pause Delivery for 7 Days
              </button>
            </>
          )}

          {status === 'success' && (
            <>
              <h1 className="text-2xl font-bold text-[#0D1117] mb-2">Delivery Paused</h1>
              <p className="text-[#6B7280]">Delivery has been paused for 7 days. Please check on the account holder during this time.</p>
            </>
          )}

          {status === 'limit_reached' && (
            <>
              <h1 className="text-xl font-bold text-[#0D1117] mb-2">Pause limit reached</h1>
              <p className="text-[#6B7280]">The pause limit has been reached. Delivery cannot be paused further.</p>
            </>
          )}

          {status === 'error' && (
            <>
              <h1 className="text-xl font-bold text-[#0D1117] mb-2">Invalid link</h1>
              <p className="text-[#6B7280]">This emergency pause link is invalid or has expired.</p>
            </>
          )}
        </div>
        <p className="text-center text-[#6B7280] text-xs mt-6">🔒 End-to-End Encrypted</p>
      </div>
    </div>
  )
}
