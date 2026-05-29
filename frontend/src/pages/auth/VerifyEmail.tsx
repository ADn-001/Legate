import { useNavigate, useLocation } from 'react-router-dom'
import { useState } from 'react'
import { Mail, ArrowLeft } from 'lucide-react'
import { authApi } from '../../api/auth'
import { keysModule, fromBase64, toBase64 } from '../../crypto/keys'
import { useAuthStore } from '../../store/auth'
import { useCryptoStore } from '../../store/crypto'

export default function VerifyEmail() {
  const navigate = useNavigate()
  const location = useLocation()
  const authStore = useAuthStore()
  const [otp, setOtp] = useState(['', '', '', '', '', ''])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleOtpChange = (index: number, value: string) => {
    if (value.length > 1) return
    const newOtp = [...otp]
    newOtp[index] = value
    setOtp(newOtp)
    if (value && index < 5) {
      const nextInput = document.querySelector(`input[data-index="${index + 1}"]`) as HTMLInputElement
      if (nextInput) nextInput.focus()
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const otpString = otp.join('')
    if (otpString.length !== 6) return
    setLoading(true)
    setError(null)
    try {
      const { data } = await authApi.verifyEmail({
        email: location.state?.email,
        otp: otpString,
      })

      const { data: meData } = await authApi.getMe()
      authStore.login(meData, data.access_token, data.refresh_token)

      const pending = JSON.parse(sessionStorage.getItem('pending_signup') || '{}')
      if (pending.password_hint) {
        const password = atob(pending.password_hint)
        const keyRes = await authApi.getEncryptionKey()
        const { pbkdf2_salt, cek_iv, encrypted_cek } = keyRes.data
        const salt = fromBase64(pbkdf2_salt)
        const wrappingKey = await keysModule.deriveWrappingKey(password, salt)
        const cek = await keysModule.decryptCEK(fromBase64(encrypted_cek), wrappingKey, fromBase64(cek_iv))

        useCryptoStore.getState().setCek(cek)

        const deliveryKeyRes = await authApi.getDeliveryWrappingKey()
        const deliveryWrappingKey = await keysModule.importHexKey(deliveryKeyRes.data.wrapping_key)
        const { encryptedCek: deliveryEncCek, iv: deliveryIv } = await keysModule.encryptCEK(cek, deliveryWrappingKey)
        await authApi.updateDeliveryKey({
          delivery_encrypted_cek: toBase64(deliveryEncCek),
          delivery_cek_iv: toBase64(deliveryIv),
        })

        sessionStorage.removeItem('pending_signup')
      }

      authStore.setNeedsOnboarding(true)
      navigate('/setup/checkin')
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Invalid code'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex flex-col">
      <button
        onClick={() => navigate('/auth/signup')}
        className="absolute top-4 left-4 p-2 hover:bg-white rounded-lg transition-colors"
      >
        <ArrowLeft className="w-5 h-5 text-[#0D1117]" />
      </button>

      <div className="flex-1 flex items-center justify-center p-4">
        <div className="w-full max-w-md">
          <div className="bg-white rounded-2xl shadow-lg p-8">
            <div className="flex justify-center mb-6">
              <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center">
                <Mail className="w-8 h-8 text-[#3D4F6B]" />
              </div>
            </div>

            <h1 className="text-2xl font-bold text-[#0D1117] text-center mb-2">Check your email</h1>
            <p className="text-[#6B7280] text-center mb-2">We sent a 6-digit code to</p>
            {location.state?.email && (
              <p className="text-[#3D4F6B] font-medium text-center mb-6">{location.state.email}</p>
            )}

            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
                <p className="text-sm text-red-700">{error}</p>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="flex justify-center gap-2">
                {otp.map((digit, index) => (
                  <input
                    key={index}
                    data-index={index}
                    type="text"
                    inputMode="numeric"
                    maxLength={1}
                    value={digit}
                    onChange={(e) => handleOtpChange(index, e.target.value)}
                    className="w-12 h-12 text-center text-2xl font-bold border-2 border-gray-200 rounded-lg focus:outline-none focus:border-[#3D4F6B] focus:ring-2 focus:ring-[#3D4F6B]/20"
                  />
                ))}
              </div>

              <button
                type="submit"
                disabled={otp.join('').length !== 6 || loading}
                className="w-full py-4 bg-[#3D4F6B] text-white rounded-2xl font-semibold hover:bg-[#2a3851] transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {loading && <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />}
                Verify Code
              </button>
            </form>

            <div className="text-center mt-6">
              <p className="text-[#6B7280] text-sm">
                Didn't receive the code?{' '}
                <button className="text-[#3D4F6B] font-semibold hover:text-[#2a3851]">Resend</button>
              </p>
            </div>
          </div>
          <p className="text-center text-[#6B7280] text-xs mt-6">Code will expire in 10 minutes</p>
        </div>
      </div>
    </div>
  )
}
