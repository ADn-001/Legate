import { useNavigate } from 'react-router-dom'
import { useState } from 'react'
import { Shield } from 'lucide-react'

export default function Signup() {
  const navigate = useNavigate()
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    // TODO: Implement signup logic with encryption
    navigate('/auth/verify-email')
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Card */}
        <div className="bg-white rounded-2xl shadow-lg p-8">
          {/* Logo */}
          <div className="flex items-center justify-center gap-2 mb-8">
            <Shield className="w-8 h-8 text-[#3D4F6B]" />
            <span className="text-2xl font-bold text-[#3D4F6B]">Legate</span>
          </div>

          {/* Heading */}
          <h1 className="text-2xl font-bold text-[#0D1117] text-center mb-2">
            Create Your Account
          </h1>
          <p className="text-[#6B7280] text-center mb-8">
            Secure your digital legacy today
          </p>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Full Name */}
            <div>
              <label className="block text-sm font-medium text-[#0D1117] mb-2">
                Full Name (Optional)
              </label>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="John Doe"
                className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#3D4F6B] bg-white"
              />
            </div>

            {/* Email */}
            <div>
              <label className="block text-sm font-medium text-[#0D1117] mb-2">
                Email Address
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#3D4F6B] bg-white"
                required
              />
            </div>

            {/* Password */}
            <div>
              <label className="block text-sm font-medium text-[#0D1117] mb-2">
                Password (Min 12 characters)
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#3D4F6B] bg-white"
                minLength={12}
                required
              />
            </div>

            {/* Confirm Password */}
            <div>
              <label className="block text-sm font-medium text-[#0D1117] mb-2">
                Confirm Password
              </label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#3D4F6B] bg-white"
                minLength={12}
                required
              />
            </div>

            {/* Security Notice */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mt-4">
              <p className="text-xs text-[#3D4F6B]">
                🔒 Your password is used to encrypt your capsules. We never store it on our servers.
              </p>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              className="w-full py-4 bg-[#3D4F6B] text-white rounded-2xl font-semibold hover:bg-[#2a3851] transition-colors mt-6"
            >
              Create Account
            </button>
          </form>

          {/* Divider */}
          <div className="my-6 flex items-center gap-4">
            <div className="flex-1 bg-gray-200 h-px"></div>
            <span className="text-[#6B7280] text-sm">OR</span>
            <div className="flex-1 bg-gray-200 h-px"></div>
          </div>

          {/* Login Link */}
          <p className="text-center text-[#6B7280]">
            Already have an account?{' '}
            <button
              onClick={() => navigate('/auth/login')}
              className="text-[#3D4F6B] font-semibold hover:text-[#2a3851]"
            >
              Sign in
            </button>
          </p>
        </div>

        {/* Footer Text */}
        <p className="text-center text-[#6B7280] text-xs mt-6">
          🔒 End-to-end encrypted • No login stored • Recovery phrase protected
        </p>
      </div>
    </div>
  )
}
