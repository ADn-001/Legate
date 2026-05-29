import { useState } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { Shield, CheckCircle, AlertCircle } from 'lucide-react'
import client from '../../api/client'

type Status = 'idle' | 'loading' | 'success' | 'expired' | 'error'

export default function CheckinConfirm() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const token = searchParams.get('token')
  const [status, setStatus] = useState<Status>('idle')

  const handleConfirm = async () => {
    if (!token) { setStatus('error'); return }
    setStatus('loading')
    try {
      await client.get(`/checkin/confirm?token=${token}`)
      setStatus('success')
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } }).response?.status
      setStatus(status === 409 ? 'expired' : 'error')
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex flex-col items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <div className="bg-white rounded-2xl shadow-lg p-8 text-center">
          {status === 'idle' && (
            <>
              <div className="flex justify-center mb-6">
                <div className="w-20 h-20 bg-blue-100 rounded-full flex items-center justify-center">
                  <Shield className="w-10 h-10 text-[#3D4F6B]" />
                </div>
              </div>
              <div className="inline-flex items-center gap-2 bg-green-100 text-green-700 px-3 py-1 rounded-full text-xs font-semibold mb-4">
                <span className="w-2 h-2 bg-green-500 rounded-full" />
                SECURITY CHECK-IN
              </div>
              <h1 className="text-2xl font-bold text-[#0D1117] mb-6">Are you okay?</h1>
              <button
                onClick={handleConfirm}
                className="w-full py-4 bg-[#3D4F6B] text-white rounded-2xl font-semibold hover:bg-[#2a3851] transition-colors mb-4 flex items-center justify-center gap-2"
              >
                <CheckCircle className="w-5 h-5" />
                Yes, I'm active
              </button>
              <button
                onClick={() => navigate(`/checkin/snooze?token=${token}`)}
                className="text-sm text-[#6B7280] hover:text-[#3D4F6B] flex items-center justify-center gap-1 mx-auto"
              >
                🕐 Remind me later
              </button>
            </>
          )}

          {status === 'loading' && (
            <div className="py-8">
              <div className="w-12 h-12 border-4 border-[#3D4F6B] border-t-transparent rounded-full animate-spin mx-auto" />
            </div>
          )}

          {status === 'success' && (
            <>
              <div className="flex justify-center mb-6">
                <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center">
                  <CheckCircle className="w-10 h-10 text-green-600" />
                </div>
              </div>
              <h1 className="text-2xl font-bold text-[#0D1117] mb-2">You're confirmed!</h1>
              <p className="text-[#6B7280]">Your timer has been reset. We'll check in again soon.</p>
            </>
          )}

          {status === 'expired' && (
            <>
              <div className="flex justify-center mb-6">
                <div className="w-20 h-20 bg-amber-100 rounded-full flex items-center justify-center">
                  <AlertCircle className="w-10 h-10 text-amber-600" />
                </div>
              </div>
              <h1 className="text-xl font-bold text-[#0D1117] mb-2">Link already used</h1>
              <p className="text-[#6B7280]">This check-in link has already been used.</p>
            </>
          )}

          {status === 'error' && (
            <>
              <div className="flex justify-center mb-6">
                <div className="w-20 h-20 bg-red-100 rounded-full flex items-center justify-center">
                  <AlertCircle className="w-10 h-10 text-red-600" />
                </div>
              </div>
              <h1 className="text-xl font-bold text-[#0D1117] mb-2">Link expired or invalid</h1>
              <p className="text-[#6B7280]">This link has expired or is not valid.</p>
            </>
          )}
        </div>

        <p className="text-center text-[#6B7280] text-xs mt-6">🔒 End-to-End Encrypted</p>
      </div>
    </div>
  )
}
