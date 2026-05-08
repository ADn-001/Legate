import { ArrowLeft, Shield, Lock, Bell, Phone } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useState } from 'react'

export default function Security() {
  const navigate = useNavigate()
  const [notifications, setNotifications] = useState(true)
  const [twoFa, setTwoFa] = useState(true)

  return (
    <div className="min-h-screen bg-[#F0F2F5] p-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex items-center gap-4 mb-8">
          <button
            onClick={() => navigate('/vault')}
            className="p-2 hover:bg-white rounded-lg transition-colors"
          >
            <ArrowLeft className="w-5 h-5 text-[#0D1117]" />
          </button>
          <div>
            <h1 className="text-3xl font-bold text-[#0D1117]">Security</h1>
            <p className="text-xs uppercase tracking-widest text-gray-400 mt-1">
              Settings & Protocols
            </p>
          </div>
        </div>

        {/* Vault Status */}
        <div className="bg-white rounded-2xl shadow-md p-6 mb-8">
          <h3 className="font-semibold text-[#0D1117] mb-4">Vault Status</h3>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-[#6B7280] mb-1">Encryption</p>
              <p className="font-semibold text-[#0D1117]">End-to-End Encrypted</p>
            </div>
            <div className="flex items-center gap-2 px-4 py-2 bg-green-100 rounded-full">
              <div className="w-2 h-2 bg-green-600 rounded-full"></div>
              <span className="font-semibold text-green-800 text-sm">ACTIVE</span>
            </div>
          </div>
        </div>

        {/* Access Control */}
        <div className="bg-white rounded-2xl shadow-md p-6 mb-8">
          <h3 className="font-semibold text-[#0D1117] mb-6">Access Control</h3>

          {/* Notifications Toggle */}
          <div className="flex items-center justify-between py-4 border-b border-gray-200 mb-4">
            <div className="flex items-center gap-3">
              <Bell className="w-5 h-5 text-[#3D4F6B]" />
              <div>
                <p className="font-medium text-[#0D1117]">Notifications</p>
                <p className="text-xs text-[#6B7280]">Real-time security alerts</p>
              </div>
            </div>
            <button
              onClick={() => setNotifications(!notifications)}
              className={`relative inline-flex h-8 w-14 items-center rounded-full transition-colors ${
                notifications ? 'bg-[#3D4F6B]' : 'bg-gray-300'
              }`}
            >
              <span
                className={`inline-block h-6 w-6 transform rounded-full bg-white transition-transform ${
                  notifications ? 'translate-x-7' : 'translate-x-1'
                }`}
              />
            </button>
          </div>

          {/* Two-Factor Authentication */}
          <div className="flex items-center justify-between py-4">
            <div className="flex items-center gap-3">
              <Lock className="w-5 h-5 text-[#3D4F6B]" />
              <div>
                <p className="font-medium text-[#0D1117]">Multi-step Verification</p>
                <p className="text-xs text-[#6B7280]">Enhanced identity protocols</p>
              </div>
            </div>
            <button
              onClick={() => setTwoFa(!twoFa)}
              className={`relative inline-flex h-8 w-14 items-center rounded-full transition-colors ${
                twoFa ? 'bg-[#3D4F6B]' : 'bg-gray-300'
              }`}
            >
              <span
                className={`inline-block h-6 w-6 transform rounded-full bg-white transition-transform ${
                  twoFa ? 'translate-x-7' : 'translate-x-1'
                }`}
              />
            </button>
          </div>
        </div>

        {/* Emergency Contact */}
        <div className="bg-white rounded-2xl shadow-md p-6 mb-8">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-2">
              <Phone className="w-5 h-5 text-[#3D4F6B]" />
              <h3 className="font-semibold text-[#0D1117]">Emergency Contact</h3>
            </div>
            <span className="px-3 py-1 bg-blue-100 text-[#3D4F6B] text-xs font-semibold rounded-full">
              LEGACY ACCESS
            </span>
          </div>

          <form className="space-y-4">
            {/* Full Legal Name */}
            <div>
              <label className="block text-sm font-medium text-[#0D1117] mb-2">
                Full Legal Name
              </label>
              <input
                type="text"
                placeholder="Jane Smith"
                className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#3D4F6B]"
              />
            </div>

            {/* Email */}
            <div>
              <label className="block text-sm font-medium text-[#0D1117] mb-2">
                Secure Email Address
              </label>
              <input
                type="email"
                placeholder="emergency@example.com"
                className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#3D4F6B]"
              />
            </div>

            <p className="text-xs text-[#6B7280] bg-blue-50 p-3 rounded-lg">
              💡 Emergency contacts can pause delivery up to 2 times (7 days each) while they verify you are okay.
            </p>

            <button
              type="button"
              className="w-full py-3 bg-[#3D4F6B] text-white rounded-2xl font-semibold hover:bg-[#2a3851] transition-colors"
            >
              Verify & Add Contact
            </button>
          </form>
        </div>

        {/* Footer Info */}
        <div className="bg-white rounded-2xl shadow-md p-6 mb-8">
          <div className="space-y-3">
            <p className="flex items-center gap-2 text-[#0D1117]">
              <Lock className="w-4 h-4" />
              <span>🔒 Encrypted storage enabled</span>
            </p>
            <p className="flex items-center gap-2 text-[#0D1117]">
              <Shield className="w-4 h-4" />
              <span>🗑 Data deletion available anytime</span>
            </p>
          </div>
        </div>

        {/* Legal Disclaimer */}
        <div className="bg-slate-50 border border-gray-200 rounded-2xl p-6">
          <p className="text-xs text-[#6B7280] leading-relaxed">
            <strong>Important:</strong> This is not a legal will. Legate is an instruction-based system for message and document delivery. Please consult with legal professionals for official estate documentation and to ensure compliance with your jurisdiction's laws.
          </p>
        </div>
      </div>
    </div>
  )
}
