import { useNavigate } from 'react-router-dom'
import { Lock, Users, Shield, Clock, Plus, Eye } from 'lucide-react'

export default function Dashboard() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-[#F0F2F5] p-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-[#0D1117] mb-2">
            Hello, John
          </h1>
          <p className="text-[#6B7280]">
            Your digital legacy is secured and up to date.
          </p>
        </div>

        {/* Vault Status Card */}
        <div className="bg-white rounded-2xl shadow-md p-8 mb-8">
          <div className="flex items-start justify-between mb-6">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <div className="w-3 h-3 bg-[#22C55E] rounded-full"></div>
                <span className="font-semibold text-[#0D1117]">VAULT STATUS: ACTIVE</span>
              </div>
              <p className="text-[#6B7280] text-sm mb-4">
                Your vault is active and protected
              </p>
            </div>
            <Lock className="w-8 h-8 text-[#3D4F6B]" />
          </div>

          {/* Status Grid */}
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-slate-50 rounded-lg p-4">
              <p className="text-[#6B7280] text-xs font-medium mb-1">LAST CHECK-IN</p>
              <p className="text-lg font-bold text-[#0D1117]">Today</p>
            </div>
            <div className="bg-slate-50 rounded-lg p-4">
              <p className="text-[#6B7280] text-xs font-medium mb-1">NEXT CHECK-IN</p>
              <p className="text-lg font-bold text-[#0D1117]">Apr 7, 2026</p>
            </div>
          </div>
        </div>

        {/* Primary CTA */}
        <button
          onClick={() => navigate('/vault/capsules/new')}
          className="w-full py-4 bg-[#3D4F6B] text-white rounded-2xl font-semibold hover:bg-[#2a3851] transition-colors mb-8 flex items-center justify-center gap-2"
        >
          <Plus className="w-5 h-5" />
          Create Capsule
        </button>

        {/* Quick Links Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          {/* My Capsules */}
          <div
            onClick={() => navigate('/vault/capsules')}
            className="bg-white rounded-2xl shadow-md p-6 cursor-pointer hover:shadow-lg transition-shadow"
          >
            <div className="flex items-start justify-between mb-4">
              <div>
                <h3 className="font-semibold text-[#0D1117] mb-1">My Capsules</h3>
                <p className="text-sm text-[#6B7280]">3 secured vaults</p>
              </div>
              <Eye className="w-5 h-5 text-[#3D4F6B]" />
            </div>
          </div>

          {/* Beneficiaries */}
          <div
            onClick={() => navigate('/people')}
            className="bg-white rounded-2xl shadow-md p-6 cursor-pointer hover:shadow-lg transition-shadow"
          >
            <div className="flex items-start justify-between mb-4">
              <div>
                <h3 className="font-semibold text-[#0D1117] mb-1">Beneficiaries</h3>
                <p className="text-sm text-[#6B7280]">2 people managed</p>
              </div>
              <Users className="w-5 h-5 text-[#3D4F6B]" />
            </div>
          </div>
        </div>

        {/* Security & Activity */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Security */}
          <div
            onClick={() => navigate('/security')}
            className="bg-white rounded-2xl shadow-md p-6 cursor-pointer hover:shadow-lg transition-shadow"
          >
            <div className="flex items-start justify-between mb-4">
              <div>
                <h3 className="font-semibold text-[#0D1117] mb-1">Security</h3>
                <p className="text-sm text-[#6B7280]">2FA Enabled</p>
              </div>
              <Shield className="w-5 h-5 text-[#3D4F6B]" />
            </div>
          </div>

          {/* Activity */}
          <div
            onClick={() => navigate('/activity')}
            className="bg-white rounded-2xl shadow-md p-6 cursor-pointer hover:shadow-lg transition-shadow"
          >
            <div className="flex items-start justify-between mb-4">
              <div>
                <h3 className="font-semibold text-[#0D1117] mb-1">Activity</h3>
                <p className="text-sm text-[#6B7280]">View audit logs</p>
              </div>
              <Clock className="w-5 h-5 text-[#3D4F6B]" />
            </div>
          </div>
        </div>

        {/* Recent Activity */}
        <div className="bg-white rounded-2xl shadow-md p-6 mt-8">
          <div className="flex items-center justify-between mb-6">
            <h3 className="font-semibold text-[#0D1117]">Recent Activity</h3>
            <a href="#" className="text-sm text-[#3D4F6B] hover:text-[#2a3851] font-medium">
              VIEW ALL
            </a>
          </div>

          <div className="space-y-4">
            {/* Activity Item 1 */}
            <div className="flex items-center gap-4 pb-4 border-b border-gray-200">
              <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                <Lock className="w-5 h-5 text-[#3D4F6B]" />
              </div>
              <div className="flex-1">
                <p className="font-medium text-[#0D1117]">Check-in Confirmed</p>
                <p className="text-sm text-[#6B7280]">Today at 2:45 PM</p>
              </div>
            </div>

            {/* Activity Item 2 */}
            <div className="flex items-center gap-4 pb-4 border-b border-gray-200">
              <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
                <Plus className="w-5 h-5 text-[#22C55E]" />
              </div>
              <div className="flex-1">
                <p className="font-medium text-[#0D1117]">Capsule Created</p>
                <p className="text-sm text-[#6B7280]">Yesterday at 10:20 AM</p>
              </div>
            </div>

            {/* Activity Item 3 */}
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                <Users className="w-5 h-5 text-purple-600" />
              </div>
              <div className="flex-1">
                <p className="font-medium text-[#0D1117]">Beneficiary Added</p>
                <p className="text-sm text-[#6B7280]">2 days ago</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
