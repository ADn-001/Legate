import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Shield, CheckCircle } from 'lucide-react'
import { authApi } from '../../api/auth'

// T6.2: "Forgot password?" entry point. Always shows the same success
// message regardless of whether the email is registered, matching the
// backend's anti-enumeration behavior (FR-03).
export default function ForgotPassword() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [sent, setSent] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      await authApi.forgotPassword({ email })
      setSent(true)
    } catch {
      setError("Can't reach the server. Please try again.")
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

          {sent ? (
            <div className="text-center">
              <CheckCircle className="w-12 h-12 text-green-600 mx-auto mb-4" />
              <h1 className="text-2xl font-bold text-[#0D1117] mb-2">Check your email</h1>
              <p className="text-[#6B7280] mb-6">
                If an account exists for <strong>{email}</strong>, we've sent a link to reset your password.
                The link expires in 30 minutes.
              </p>
              <button onClick={() => navigate('/auth/login')} className="text-[#3D4F6B] font-semibold hover:text-[#2a3851]">
                Back to sign in
              </button>
            </div>
          ) : (
            <>
              <h1 className="text-2xl font-bold text-[#0D1117] text-center mb-2">Forgot your password?</h1>
              <p className="text-[#6B7280] text-center mb-8">
                Enter your account email and we'll send you a link to reset it.
              </p>

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

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full py-4 bg-[#3D4F6B] text-white rounded-2xl font-semibold hover:bg-[#2a3851] transition-colors mt-6 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {loading && <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />}
                  Send reset link
                </button>
              </form>

              <p className="text-center text-[#6B7280] mt-6">
                <button onClick={() => navigate('/auth/login')} className="text-[#3D4F6B] font-semibold hover:text-[#2a3851]">
                  Back to sign in
                </button>
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
