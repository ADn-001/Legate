import { useNavigate } from 'react-router-dom'
import { useState } from 'react'
import { Shield } from 'lucide-react'
import { authApi } from '../../api/auth'
import { keysModule, fromBase64 } from '../../crypto/keys'
import { useAuthStore } from '../../store/auth'
import { useCryptoStore } from '../../store/crypto'

export default function Login() {
  const navigate = useNavigate()
  const authStore = useAuthStore()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const { data } = await authApi.login({ email, password })
      const { data: meData } = await authApi.getMe()
      authStore.login(meData, data.access_token, data.refresh_token)

      const keyRes = await authApi.getEncryptionKey()
      const { encrypted_cek, cek_iv, pbkdf2_salt } = keyRes.data
      const salt = fromBase64(pbkdf2_salt)
      const wrappingKey = await keysModule.deriveWrappingKey(password, salt)
      const cek = await keysModule.decryptCEK(fromBase64(encrypted_cek), wrappingKey, fromBase64(cek_iv))
      useCryptoStore.getState().setCek(cek)

      if (meData.needs_onboarding) {
        navigate('/setup/checkin')
      } else {
        navigate('/vault')
      }
    } catch {
      setError('Invalid email or password')
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

          <h1 className="text-2xl font-bold text-[#0D1117] text-center mb-2">Welcome Back</h1>
          <p className="text-[#6B7280] text-center mb-8">Sign in to your account</p>

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
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
              <label className="block text-sm font-medium text-[#0D1117] mb-2">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="input-field w-full"
                required
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-4 bg-[#3D4F6B] text-white rounded-2xl font-semibold hover:bg-[#2a3851] transition-colors mt-6 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {loading && <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />}
              Sign In
            </button>
          </form>

          <div className="my-6 flex items-center gap-4">
            <div className="flex-1 bg-gray-200 h-px" />
            <span className="text-[#6B7280] text-sm">OR</span>
            <div className="flex-1 bg-gray-200 h-px" />
          </div>

          <p className="text-center text-[#6B7280]">
            Don't have an account?{' '}
            <button onClick={() => navigate('/auth/signup')} className="text-[#3D4F6B] font-semibold hover:text-[#2a3851]">
              Create one
            </button>
          </p>
        </div>
        <p className="text-center text-[#6B7280] text-xs mt-6">🔒 Your data is encrypted end-to-end</p>
      </div>
    </div>
  )
}
