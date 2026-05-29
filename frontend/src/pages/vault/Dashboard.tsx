import { useNavigate } from 'react-router-dom'
import { Lock, Users, Shield, Clock, Plus, Eye } from 'lucide-react'
import { useAuthStore } from '../../store/auth'
import { useCheckinSchedule } from '../../hooks/useCheckinSchedule'
import { useCapsules } from '../../hooks/useCapsules'
import { useBeneficiaries } from '../../hooks/useBeneficiaries'
import { useAuditLogs } from '../../hooks/useAuditLogs'
import { formatDate, formatRelativeTime } from '../../utils/dates'
import { getEventLabel } from '../../utils/audit'
import { ActivityEntry, CheckinSchedule } from '../../types/api'

function deriveVaultStatus(schedule: CheckinSchedule | undefined) {
  if (!schedule?.next_dispatch_at) return { color: 'bg-[#22C55E]', label: 'VAULT STATUS: ACTIVE' }
  const diff = new Date(schedule.next_dispatch_at).getTime() - Date.now()
  if (diff < 0) return { color: 'bg-red-500', label: 'VAULT STATUS: OVERDUE' }
  if (diff < 3 * 86400000) return { color: 'bg-amber-400', label: 'VAULT STATUS: DUE SOON' }
  return { color: 'bg-[#22C55E]', label: 'VAULT STATUS: ACTIVE' }
}

export default function Dashboard() {
  const navigate = useNavigate()
  const user = useAuthStore(s => s.user)
  const { data: schedule, isLoading: scheduleLoading } = useCheckinSchedule()
  const { data: capsules } = useCapsules()
  const { data: beneficiaries } = useBeneficiaries()
  const { data: activity } = useAuditLogs(1)

  const displayName = user?.full_name?.split(' ')[0] || user?.email?.split('@')[0] || 'there'
  const vaultStatus = deriveVaultStatus(schedule)
  const recentActivity: ActivityEntry[] = Array.isArray(activity) ? activity.slice(0, 3) : []

  return (
    <div className="min-h-screen bg-[#F0F2F5] p-4">
      <div className="max-w-4xl mx-auto">
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-[#0D1117] mb-2">Hello, {displayName}</h1>
          <p className="text-[#6B7280]">Your digital legacy is secured and up to date.</p>
        </div>

        {/* Vault Status Card */}
        <div className="bg-white rounded-2xl shadow-md p-8 mb-8">
          <div className="flex items-start justify-between mb-6">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <div className={`w-3 h-3 ${vaultStatus.color} rounded-full`} />
                <span className="font-semibold text-[#0D1117]">{vaultStatus.label}</span>
              </div>
              <p className="text-[#6B7280] text-sm mb-4">Your vault is active and protected</p>
            </div>
            <Lock className="w-8 h-8 text-[#3D4F6B]" />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="bg-slate-50 rounded-lg p-4">
              <p className="text-[#6B7280] text-xs font-medium mb-1">LAST CHECK-IN</p>
              {scheduleLoading ? (
                <div className="h-6 bg-gray-200 rounded animate-pulse" />
              ) : (
                <p className="text-lg font-bold text-[#0D1117]">
                  {schedule?.last_confirmed_at ? formatRelativeTime(schedule.last_confirmed_at) : 'Never'}
                </p>
              )}
            </div>
            <div className="bg-slate-50 rounded-lg p-4">
              <p className="text-[#6B7280] text-xs font-medium mb-1">NEXT CHECK-IN</p>
              {scheduleLoading ? (
                <div className="h-6 bg-gray-200 rounded animate-pulse" />
              ) : (
                <p className="text-lg font-bold text-[#0D1117]">
                  {schedule?.next_dispatch_at ? formatDate(schedule.next_dispatch_at) : '—'}
                </p>
              )}
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
          <div
            onClick={() => navigate('/vault/capsules')}
            className="bg-white rounded-2xl shadow-md p-6 cursor-pointer hover:shadow-lg transition-shadow"
          >
            <div className="flex items-start justify-between mb-4">
              <div>
                <h3 className="font-semibold text-[#0D1117] mb-1">My Capsules</h3>
                <p className="text-sm text-[#6B7280]">{capsules?.length ?? 0} secured {capsules?.length === 1 ? 'vault' : 'vaults'}</p>
              </div>
              <Eye className="w-5 h-5 text-[#3D4F6B]" />
            </div>
          </div>

          <div
            onClick={() => navigate('/people')}
            className="bg-white rounded-2xl shadow-md p-6 cursor-pointer hover:shadow-lg transition-shadow"
          >
            <div className="flex items-start justify-between mb-4">
              <div>
                <h3 className="font-semibold text-[#0D1117] mb-1">Beneficiaries</h3>
                <p className="text-sm text-[#6B7280]">{beneficiaries?.length ?? 0} {beneficiaries?.length === 1 ? 'person' : 'people'} managed</p>
              </div>
              <Users className="w-5 h-5 text-[#3D4F6B]" />
            </div>
          </div>
        </div>

        {/* Security & Activity */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div onClick={() => navigate('/security')} className="bg-white rounded-2xl shadow-md p-6 cursor-pointer hover:shadow-lg transition-shadow">
            <div className="flex items-start justify-between mb-4">
              <div>
                <h3 className="font-semibold text-[#0D1117] mb-1">Security</h3>
                <p className="text-sm text-[#6B7280]">End-to-End Encrypted</p>
              </div>
              <Shield className="w-5 h-5 text-[#3D4F6B]" />
            </div>
          </div>

          <div onClick={() => navigate('/activity')} className="bg-white rounded-2xl shadow-md p-6 cursor-pointer hover:shadow-lg transition-shadow">
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
            <button onClick={() => navigate('/activity')} className="text-sm text-[#3D4F6B] hover:text-[#2a3851] font-medium">
              VIEW ALL
            </button>
          </div>

          {recentActivity.length === 0 ? (
            <p className="text-sm text-[#6B7280] text-center py-4">No activity yet</p>
          ) : (
            <div className="space-y-4">
              {recentActivity.map((item, idx) => (
                <div key={item.id} className={`flex items-center gap-4 ${idx < recentActivity.length - 1 ? 'pb-4 border-b border-gray-100' : ''}`}>
                  <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                    <Lock className="w-5 h-5 text-[#3D4F6B]" />
                  </div>
                  <div className="flex-1">
                    <p className="font-medium text-[#0D1117]">{getEventLabel(item.event_type)}</p>
                    <p className="text-sm text-[#6B7280]">{formatRelativeTime(item.created_at)}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
