import { ArrowLeft, Plus, Trash2, Edit2, Shield } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

export default function Beneficiaries() {
  const navigate = useNavigate()

  const beneficiaries = [
    { id: 1, name: 'Sarah Johnson', email: 'sarah@example.com', relationship: 'Sister' },
    { id: 2, name: 'Michael Brown', email: 'michael@example.com', relationship: 'Best Friend' },
  ]

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
            <h1 className="text-3xl font-bold text-[#0D1117]">Beneficiaries</h1>
            <p className="text-[#6B7280]">Manage who receives your legacy instructions</p>
          </div>
        </div>

        {/* Security Notice */}
        <div className="bg-blue-50 border border-blue-200 rounded-2xl p-4 mb-8 flex gap-4">
          <Shield className="w-5 h-5 text-[#3D4F6B] flex-shrink-0 mt-1" />
          <div>
            <p className="font-semibold text-[#3D4F6B] text-sm">
              They will only receive instructions, not account access
            </p>
            <p className="text-xs text-[#3D4F6B] opacity-80 mt-1">
              Your beneficiaries cannot access your account or modify your settings
            </p>
          </div>
        </div>

        {/* Add Beneficiary Button */}
        <button
          onClick={() => {}}
          className="w-full py-4 bg-[#3D4F6B] text-white rounded-2xl font-semibold hover:bg-[#2a3851] transition-colors mb-8 flex items-center justify-center gap-2"
        >
          <Plus className="w-5 h-5" />
          Add Beneficiary
        </button>

        {/* Beneficiaries List */}
        <div className="space-y-4">
          {beneficiaries.map((beneficiary) => (
            <div
              key={beneficiary.id}
              className="bg-white rounded-2xl shadow-md p-6 flex items-start justify-between hover:shadow-lg transition-shadow"
            >
              <div className="flex items-center gap-4 flex-1">
                {/* Avatar */}
                <div className="w-12 h-12 bg-gradient-to-br from-blue-400 to-blue-600 rounded-full flex items-center justify-center text-white font-bold text-lg">
                  {beneficiary.name
                    .split(' ')
                    .map((n) => n[0])
                    .join('')}
                </div>
                {/* Info */}
                <div className="flex-1">
                  <h3 className="font-semibold text-[#0D1117] text-lg">
                    {beneficiary.name}
                  </h3>
                  <p className="text-sm text-[#6B7280]">{beneficiary.email}</p>
                  {beneficiary.relationship && (
                    <span className="inline-block mt-2 px-3 py-1 bg-slate-100 text-[#3D4F6B] text-xs font-medium rounded-full">
                      {beneficiary.relationship}
                    </span>
                  )}
                </div>
              </div>

              {/* Actions */}
              <div className="flex items-center gap-2 ml-4">
                <button className="p-2 hover:bg-gray-100 rounded-lg transition-colors">
                  <Edit2 className="w-5 h-5 text-[#3D4F6B]" />
                </button>
                <button className="p-2 hover:bg-red-50 rounded-lg transition-colors">
                  <Trash2 className="w-5 h-5 text-[#C0392B]" />
                </button>
              </div>
            </div>
          ))}
        </div>

        {/* Estate Overview */}
        <div className="bg-white rounded-2xl shadow-md p-6 mt-8">
          <h3 className="font-semibold text-[#0D1117] mb-3">Estate Overview</h3>
          <p className="text-[#6B7280] text-sm mb-4">
            Ensure your successor is also assigned to your main vault. This provides an additional layer of protection and continuity.
          </p>
          <button className="text-[#3D4F6B] font-semibold hover:text-[#2a3851] text-sm">
            Learn More →
          </button>
        </div>
      </div>
    </div>
  )
}
