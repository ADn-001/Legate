import { useNavigate } from 'react-router-dom'
import { useState } from 'react'
import { Shield } from 'lucide-react'

export default function Login() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    // TODO: Implement login logic
    navigate('/vault')
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
            Welcome Back
          </h1>
          <p className="text-[#6B7280] text-center mb-8">
            Sign in to your account
          </p>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
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
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#3D4F6B] bg-white"
                required
              />
            </div>

            {/* Forgot Password Link */}
            <div className="text-right">
              <a href="#" className="text-sm text-[#3D4F6B] hover:text-[#2a3851] font-medium">
                Forgot password?
              </a>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              className="w-full py-4 bg-[#3D4F6B] text-white rounded-2xl font-semibold hover:bg-[#2a3851] transition-colors mt-6"
            >
              Sign In
            </button>
          </form>

          {/* Divider */}
          <div className="my-6 flex items-center gap-4">
            <div className="flex-1 bg-gray-200 h-px"></div>
            <span className="text-[#6B7280] text-sm">OR</span>
            <div className="flex-1 bg-gray-200 h-px"></div>
          </div>

          {/* Sign Up Link */}
          <p className="text-center text-[#6B7280]">
            Don't have an account?{' '}
            <button
              onClick={() => navigate('/auth/signup')}
              className="text-[#3D4F6B] font-semibold hover:text-[#2a3851]"
            >
              Create one
            </button>
          </p>
        </div>

        {/* Footer Text */}
        <p className="text-center text-[#6B7280] text-xs mt-6">
          🔒 Your data is encrypted end-to-end
        </p>
      </div>
    </div>
  )
}
