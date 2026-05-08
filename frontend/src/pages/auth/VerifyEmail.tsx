import { useNavigate } from 'react-router-dom'
import { useState } from 'react'
import { Mail, ArrowLeft } from 'lucide-react'

export default function VerifyEmail() {
  const navigate = useNavigate()
  const [otp, setOtp] = useState(['', '', '', '', '', ''])

  const handleOtpChange = (index: number, value: string) => {
    if (value.length > 1) return
    const newOtp = [...otp]
    newOtp[index] = value
    setOtp(newOtp)

    // Auto-focus next input
    if (value && index < 5) {
      const nextInput = document.querySelector(`input[data-index="${index + 1}"]`) as HTMLInputElement
      if (nextInput) nextInput.focus()
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (otp.join('').length === 6) {
      navigate('/setup/checkin')
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex flex-col">
      {/* Back Button */}
      <button
        onClick={() => navigate('/auth/login')}
        className="absolute top-4 left-4 p-2 hover:bg-white rounded-lg transition-colors"
      >
        <ArrowLeft className="w-5 h-5 text-[#0D1117]" />
      </button>

      {/* Main Content */}
      <div className="flex-1 flex items-center justify-center p-4">
        <div className="w-full max-w-md">
          {/* Card */}
          <div className="bg-white rounded-2xl shadow-lg p-8">
            {/* Icon */}
            <div className="flex justify-center mb-6">
              <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center">
                <Mail className="w-8 h-8 text-[#3D4F6B]" />
              </div>
            </div>

            {/* Heading */}
            <h1 className="text-2xl font-bold text-[#0D1117] text-center mb-2">
              Check your email
            </h1>
            <p className="text-[#6B7280] text-center mb-8">
              We sent a 6-digit code to your email address
            </p>

            {/* Form */}
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* OTP Input */}
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
                    className="w-12 h-12 text-center text-2xl font-bold border-2 border-gray-200 rounded-lg focus:outline-none focus:border-[#3D4F6B] focus:ring-2 focus:ring-[#3D4F6B] focus:ring-opacity-20"
                  />
                ))}
              </div>

              {/* Verify Button */}
              <button
                type="submit"
                disabled={otp.join('').length !== 6}
                className="w-full py-4 bg-[#3D4F6B] text-white rounded-2xl font-semibold hover:bg-[#2a3851] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Verify Code
              </button>
            </form>

            {/* Resend Link */}
            <div className="text-center mt-6">
              <p className="text-[#6B7280] text-sm">
                Didn't receive the code?{' '}
                <button className="text-[#3D4F6B] font-semibold hover:text-[#2a3851]">
                  Resend
                </button>
              </p>
            </div>
          </div>

          {/* Footer */}
          <p className="text-center text-[#6B7280] text-xs mt-6">
            Code will expire in 10 minutes
          </p>
        </div>
      </div>
    </div>
  )
}
