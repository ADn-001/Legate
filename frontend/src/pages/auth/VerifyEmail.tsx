import { useNavigate, useLocation, useSearchParams } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { Mail, ArrowLeft } from 'lucide-react'
import { authApi } from '../../api/auth'
import { keysModule, fromBase64, toBase64 } from '../../crypto/keys'
import { useAuthStore } from '../../store/auth'
import { useCryptoStore } from '../../store/crypto'
import { usePendingAuthStore } from '../../store/pendingAuth'

const RESEND_COOLDOWN_SECONDS = 60

export default function VerifyEmail() {
  const navigate = useNavigate()
  const location = useLocation()
  const [searchParams] = useSearchParams()

  // T8.3: prefer the query param (survives reload), fall back to router
  // state, and otherwise let the user type it in below.
  const [email, setEmail] = useState(searchParams.get('email') || location.state?.email || '')

  const [otp, setOtp] = useState(['', '', '', '', '', ''])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // T3.2: if the pending password (held in memory since signup) was lost
  // because the page reloaded, prompt for it after OTP verification.
  const [step, setStep] = useState<'otp' | 'password'>('otp')
  const [recoveryPassword, setRecoveryPassword] = useState('')

  // T8.1/T8.2: resend OTP with a 60s client-side cooldown.
  const [resendCooldown, setResendCooldown] = useState(0)
  const [resendMessage, setResendMessage] = useState<string | null>(null)
  const [resendError, setResendError] = useState<string | null>(null)

  useEffect(() => {
    if (resendCooldown <= 0) return
    const timer = setTimeout(() => setResendCooldown((c) => c - 1), 1000)
    return () => clearTimeout(timer)
  }, [resendCooldown])

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

  const handleResend = async () => {
    if (!email || resendCooldown > 0) return
    setResendMessage(null)
    setResendError(null)
    try {
      await authApi.resendOtp({ email })
      setResendMessage('A new code has been sent to your email.')
      setResendCooldown(RESEND_COOLDOWN_SECONDS)
    } catch {
      setResendError('Could not resend the code. Please try again shortly.')
    }
  }

  // Derives the wrapping key from `password`, unwraps the CEK, loads it into
  // the crypto store, and re-wraps it for delivery emails. Throws if the
  // password is wrong (AES-GCM auth-tag failure on decrypt).
  const completeEncryptionSetup = async (password: string) => {
    const keyRes = await authApi.getEncryptionKey()
    const { encrypted_cek, cek_iv, pbkdf2_salt } = keyRes.data
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
  }

  const finishOnboarding = () => {
    usePendingAuthStore.getState().clear()
    useAuthStore.getState().setNeedsOnboarding(true)
    navigate('/setup/checkin')
  }

  const handleOtpSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const otpString = otp.join('')
    if (otpString.length !== 6 || !email) return
    setLoading(true)
    setError(null)
    try {
      const { data } = await authApi.verifyEmail({ email, otp: otpString })

      // T1: store tokens before any authenticated call.
      useAuthStore.getState().setTokens(data.access_token, data.refresh_token)
      const { data: meData } = await authApi.getMe()
      useAuthStore.getState().setUser(meData)

      const pending = usePendingAuthStore.getState()
      if (pending.password && pending.email === email) {
        await completeEncryptionSetup(pending.password)
        finishOnboarding()
      } else {
        // Password lost to a reload — ask for it before finishing setup.
        setStep('password')
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Invalid code'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      await completeEncryptionSetup(recoveryPassword)
      finishOnboarding()
    } catch {
      setError('Incorrect password')
      setRecoveryPassword('')
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

            {step === 'otp' ? (
              <>
                <h1 className="text-2xl font-bold text-[#0D1117] text-center mb-2">Check your email</h1>
                <p className="text-[#6B7280] text-center mb-2">We sent a 6-digit code to</p>
                {email && (
                  <p className="text-[#3D4F6B] font-medium text-center mb-6">{email}</p>
                )}

                {error && (
                  <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
                    <p className="text-sm text-red-700">{error}</p>
                  </div>
                )}

                <form onSubmit={handleOtpSubmit} className="space-y-6">
                  {!email && (
                    <div>
                      <label className="block text-sm font-medium text-[#0D1117] mb-2">Email Address</label>
                      <input
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="you@example.com"
                        className="input-field w-full"
                        required
                      />
                    </div>
                  )}

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
                    disabled={otp.join('').length !== 6 || !email || loading}
                    className="w-full py-4 bg-[#3D4F6B] text-white rounded-2xl font-semibold hover:bg-[#2a3851] transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                  >
                    {loading && <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />}
                    Verify Code
                  </button>
                </form>

                {resendMessage && (
                  <div className="bg-green-50 border border-green-200 rounded-lg p-3 mt-4">
                    <p className="text-sm text-green-700">{resendMessage}</p>
                  </div>
                )}
                {resendError && (
                  <div className="bg-red-50 border border-red-200 rounded-lg p-3 mt-4">
                    <p className="text-sm text-red-700">{resendError}</p>
                  </div>
                )}

                <div className="text-center mt-6">
                  <p className="text-[#6B7280] text-sm">
                    Didn't receive the code?{' '}
                    <button
                      type="button"
                      onClick={handleResend}
                      disabled={!email || resendCooldown > 0}
                      className="text-[#3D4F6B] font-semibold hover:text-[#2a3851] disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:text-[#3D4F6B]"
                    >
                      {resendCooldown > 0 ? `Resend (${resendCooldown}s)` : 'Resend'}
                    </button>
                  </p>
                </div>
              </>
            ) : (
              <>
                <h1 className="text-2xl font-bold text-[#0D1117] text-center mb-2">Confirm your password</h1>
                <p className="text-[#6B7280] text-center mb-6">
                  Your session was interrupted before encryption setup finished. Enter your password again to secure your vault.
                </p>

                {error && (
                  <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
                    <p className="text-sm text-red-700">{error}</p>
                  </div>
                )}

                <form onSubmit={handlePasswordSubmit} className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-[#0D1117] mb-2">Password</label>
                    <input
                      type="password"
                      value={recoveryPassword}
                      onChange={(e) => setRecoveryPassword(e.target.value)}
                      placeholder="••••••••••••"
                      className="input-field w-full"
                      autoFocus
                      required
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full py-4 bg-[#3D4F6B] text-white rounded-2xl font-semibold hover:bg-[#2a3851] transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                  >
                    {loading && <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />}
                    Continue
                  </button>
                </form>
              </>
            )}
          </div>
          <p className="text-center text-[#6B7280] text-xs mt-6">Code will expire in 10 minutes</p>
        </div>
      </div>
    </div>
  )
}
