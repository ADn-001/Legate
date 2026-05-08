import { ArrowLeft, Lock, Plus, Users, LogIn, CheckCircle, Clock } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

export default function Activity() {
  const navigate = useNavigate()

  const activities = [
    { id: 1, type: 'checkin_confirmed', label: 'Check-in Confirmed', time: 'Today at 2:45 PM', icon: Lock },
    { id: 2, type: 'capsule_created', label: 'Capsule Created', time: 'Yesterday at 10:20 AM', icon: Plus },
    { id: 3, type: 'beneficiary_added', label: 'Beneficiary Added', time: '2 days ago', icon: Users },
    { id: 4, type: 'login', label: 'Successful Login', time: '3 days ago', icon: LogIn },
    { id: 5, type: 'capsule_updated', label: 'Capsule Updated', time: '5 days ago', icon: CheckCircle },
    { id: 6, type: 'key_accessed', label: 'Encryption Key Accessed', time: '1 week ago', icon: Lock },
  ]

  const getIconBg = (type: string) => {
    const colors: Record<string, string> = {
      checkin_confirmed: 'bg-blue-100',
      capsule_created: 'bg-green-100',
      beneficiary_added: 'bg-purple-100',
      login: 'bg-yellow-100',
      capsule_updated: 'bg-pink-100',
      key_accessed: 'bg-orange-100',
    }
    return colors[type] || 'bg-gray-100'
  }

  const getIconColor = (type: string) => {
    const colors: Record<string, string> = {
      checkin_confirmed: 'text-blue-600',
      capsule_created: 'text-green-600',
      beneficiary_added: 'text-purple-600',
      login: 'text-yellow-600',
      capsule_updated: 'text-pink-600',
      key_accessed: 'text-orange-600',
    }
    return colors[type] || 'text-gray-600'
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
          <div>
            <h1 className="text-3xl font-bold text-[#0D1117]">Activity</h1>
            <p className="text-[#6B7280]">Audit log of all account activities</p>
          </div>
        </div>

        {/* Activity List */}
        <div className="space-y-3">
          {activities.map((activity) => {
            const IconComponent = activity.icon
            return (
              <div
                key={activity.id}
                className="bg-white rounded-2xl shadow-md p-6 hover:shadow-lg transition-shadow"
              >
                <div className="flex items-center gap-4">
                  {/* Icon */}
                  <div className={`w-12 h-12 ${getIconBg(activity.type)} rounded-lg flex items-center justify-center flex-shrink-0`}>
                    <IconComponent className={`w-6 h-6 ${getIconColor(activity.type)}`} />
                  </div>

                  {/* Content */}
                  <div className="flex-1">
                    <h3 className="font-semibold text-[#0D1117]">{activity.label}</h3>
                    <p className="text-sm text-[#6B7280]">{activity.time}</p>
                  </div>

                  {/* Timestamp Icon */}
                  <Clock className="w-4 h-4 text-[#6B7280] opacity-50 flex-shrink-0" />
                </div>
              </div>
            )
          })}
        </div>

        {/* Pagination Info */}
        <div className="mt-8 text-center">
          <button className="px-6 py-3 bg-white rounded-2xl shadow-md hover:shadow-lg transition-shadow text-[#3D4F6B] font-semibold">
            Load More
          </button>
        </div>

        {/* Info Card */}
        <div className="bg-blue-50 border border-blue-200 rounded-2xl p-6 mt-8">
          <h4 className="font-semibold text-[#3D4F6B] mb-2">📋 Activity Log</h4>
          <p className="text-[#3D4F6B] text-sm">
            This log tracks all important activities on your account including check-ins, capsule management, and security events. All entries are timestamped for your records.
          </p>
        </div>
      </div>
    </div>
  )
}
