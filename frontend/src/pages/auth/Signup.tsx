import { useNavigate } from 'react-router-dom'
import { useState } from 'react'
import { Shield } from 'lucide-react'
import { authApi } from '../../api/auth'
import { keysModule, toBase64 } from '../../crypto/keys'
import { usePendingAuthStore } from '../../store/pendingAuth'

export default function Signup() {
  const navigate = useNavigate()
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      if (!/^(?=.*[0-9])(?=.*[!@#$%^&*()_+\-=\[\]{}|;:,.<>?])/.test(password) || password.length < 12) {
        throw new Error('Password must be at least 12 characters with 1 number and 1 special character')
      }
      if (password !== confirmPassword) throw new Error('Passwords do not match')

      const cek = await keysModule.generateCEK()
      const salt = crypto.getRandomValues(new Uint8Array(16))
      const wrappingKey = await keysModule.deriveWrappingKey(password, salt)
      const { encryptedCek, iv: cekIv } = await keysModule.encryptCEK(cek, wrappingKey)

      await authApi.signup({
        email,
        password,
        full_name: fullName.trim() || null,
        encrypted_cek: toBase64(encryptedCek),
        cek_iv: toBase64(cekIv),
        pbkdf2_salt: toBase64(salt),
        delivery_encrypted_cek: null,
        delivery_cek_iv: null,
      })

      // T3: hold the password in memory only (never sessionStorage/localStorage)
      // so VerifyEmail can derive the wrapping key and wrap the CEK.
      usePendingAuthStore.getState().set(email, password)

      navigate(`/auth/verify-email?email=${encodeURIComponent(email)}`, { state: { email } })
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Signup failed'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="bg-white rounded-2xl shadow-lg p-8">
          <div className="flex items-center justify-center gap-2 mb-8">
            <Shield className="w-8 h-8 text-[#3D4F6B]" />
            <span className="text-2xl font-bold text-[#3D4F6B]">Legate</span>
          </div>

          <h1 className="text-2xl font-bold text-[#0D1117] text-center mb-2">Create Your Account</h1>
          <p className="text-[#6B7280] text-center mb-8">Secure your digital legacy today</p>

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} noValidate className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-[#0D1117] mb-2">Full Name (Optional)</label>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="John Doe"
                className="input-field w-full"
              />
            </div>
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
            <div>
              <label className="block text-sm font-medium text-[#0D1117] mb-2">Password (Min 12 characters)</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="input-field w-full"
                minLength={12}
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-[#0D1117] mb-2">Confirm Password</label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="••••••••••••"
                className="input-field w-full"
                minLength={12}
                required
              />
            </div>

            <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mt-4">
              <p className="text-xs text-[#3D4F6B]">
                🔒 Your password is used to encrypt your capsules. We never store it on our servers.
              </p>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-4 bg-[#3D4F6B] text-white rounded-2xl font-semibold hover:bg-[#2a3851] transition-colors mt-6 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {loading && <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />}
              Create Account
            </button>
          </form>

          <div className="my-6 flex items-center gap-4">
            <div className="flex-1 bg-gray-200 h-px" />
            <span className="text-[#6B7280] text-sm">OR</span>
            <div className="flex-1 bg-gray-200 h-px" />
          </div>

          <p className="text-center text-[#6B7280]">
            Already have an account?{' '}
            <button onClick={() => navigate('/auth/login')} className="text-[#3D4F6B] font-semibold hover:text-[#2a3851]">
              Sign in
            </button>
          </p>
        </div>
        <p className="text-center text-[#6B7280] text-xs mt-6">
          🔒 End-to-end encrypted • No login stored • Recovery phrase protected
        </p>
      </div>
    </div>
  )
}
