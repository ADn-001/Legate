import { ArrowLeft, Plus, Edit2, Trash2, Lock } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

export default function CapsuleList() {
  const navigate = useNavigate()

  const capsules = [
    {
      id: 1,
      title: 'Instructions for Sarah',
      beneficiaries: ['Sarah Johnson'],
      status: 'active' as const,
    },
    {
      id: 2,
      title: 'Financial Documents',
      beneficiaries: ['Michael Brown', 'Sarah Johnson'],
      status: 'active' as const,
    },
    {
      id: 3,
      title: 'Personal Messages',
      beneficiaries: ['Sarah Johnson'],
      status: 'draft' as const,
    },
  ]

  const statusColors = {
    active: { bg: 'bg-green-100', text: 'text-green-800', label: 'Active' },
    draft: { bg: 'bg-gray-100', text: 'text-gray-800', label: 'Draft' },
    delivered: { bg: 'bg-blue-100', text: 'text-blue-800', label: 'Delivered' },
  }

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
          <h1 className="text-3xl font-bold text-[#0D1117]">My Capsules</h1>
        </div>

        {/* Create Button */}
        <button
          onClick={() => navigate('/vault/capsules/new')}
          className="w-full py-4 bg-[#3D4F6B] text-white rounded-2xl font-semibold hover:bg-[#2a3851] transition-colors mb-8 flex items-center justify-center gap-2"
        >
          <Plus className="w-5 h-5" />
          Create New Capsule
        </button>

        {/* Capsules List */}
        <div className="space-y-4">
          {capsules.map((capsule) => {
            const statusColor = statusColors[capsule.status]
            return (
              <div
                key={capsule.id}
                className="bg-white rounded-2xl shadow-md p-6 hover:shadow-lg transition-shadow"
              >
                <div className="flex items-start justify-between gap-4">
                  {/* Content */}
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <Lock className="w-5 h-5 text-[#3D4F6B]" />
                      <h3 className="text-lg font-semibold text-[#0D1117]">
                        {capsule.title}
                      </h3>
                    </div>
                    <p className="text-sm text-[#6B7280] mb-3">
                      To: {capsule.beneficiaries.join(', ')}
                    </p>
                    <div className="flex items-center gap-2">
                      <span
                        className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold ${statusColor.bg} ${statusColor.text}`}
                      >
                        {statusColor.label}
                      </span>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => navigate(`/vault/capsules/${capsule.id}`)}
                      className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                    >
                      <Edit2 className="w-5 h-5 text-[#3D4F6B]" />
                    </button>
                    <button className="p-2 hover:bg-red-50 rounded-lg transition-colors">
                      <Trash2 className="w-5 h-5 text-[#C0392B]" />
                    </button>
                  </div>
                </div>
              </div>
            )
          })}
        </div>

        {/* Info Card */}
        <div className="bg-blue-50 border border-blue-200 rounded-2xl p-6 mt-8">
          <h4 className="font-semibold text-[#3D4F6B] mb-2">💡 Tip</h4>
          <p className="text-[#3D4F6B] text-sm">
            You can create multiple capsules and assign them to different beneficiaries. Each capsule is encrypted independently and will only be delivered when your account becomes inactive.
          </p>
        </div>
      </div>
    </div>
  )
}
