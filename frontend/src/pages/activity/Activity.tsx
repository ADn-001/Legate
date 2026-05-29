import { useState } from 'react'
import { ArrowLeft, Lock, Clock } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useAuditLogs } from '../../hooks/useAuditLogs'
import { getEventLabel } from '../../utils/audit'
import { formatRelativeTime } from '../../utils/dates'
import { ActivityEntry } from '../../types/api'

const eventIconBg: Record<string, string> = {
  login: 'bg-yellow-100',
  capsule_created: 'bg-green-100',
  capsule_updated: 'bg-pink-100',
  beneficiary_added: 'bg-purple-100',
  checkin_confirmed: 'bg-blue-100',
  checkin_snoozed: 'bg-orange-100',
  delivery_sent: 'bg-teal-100',
  key_accessed: 'bg-orange-100',
}

export default function Activity() {
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const [allEntries, setAllEntries] = useState<ActivityEntry[]>([])
  const { data, isLoading } = useAuditLogs(page)

  // Accumulate entries as pages load
  const entries: ActivityEntry[] = page === 1
    ? (Array.isArray(data) ? data : [])
    : [...allEntries, ...(Array.isArray(data) ? data : [])]

  const handleLoadMore = () => {
    if (Array.isArray(data)) setAllEntries(prev => [...prev, ...data])
    setPage(p => p + 1)
  }

  return (
    <div className="min-h-screen bg-[#F0F2F5] p-4">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center gap-4 mb-8">
          <button onClick={() => navigate('/vault')} className="p-2 hover:bg-white rounded-lg transition-colors">
            <ArrowLeft className="w-5 h-5 text-[#0D1117]" />
          </button>
          <div>
            <h1 className="text-3xl font-bold text-[#0D1117]">Activity</h1>
            <p className="text-[#6B7280]">Audit log of all account activities</p>
          </div>
        </div>

        {isLoading && page === 1 ? (
          <div className="space-y-3">
            {[1, 2, 3, 4].map(i => (
              <div key={i} className="bg-white rounded-2xl shadow-md p-6 animate-pulse">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 bg-gray-200 rounded-lg" />
                  <div className="flex-1 space-y-2">
                    <div className="h-4 bg-gray-200 rounded w-1/3" />
                    <div className="h-3 bg-gray-200 rounded w-1/4" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <>
            {entries.length === 0 && (
              <p className="text-center text-[#6B7280] py-8">No activity yet.</p>
            )}
            <div className="space-y-3">
              {entries.map((item: ActivityEntry) => (
                <div key={item.id} className="bg-white rounded-2xl shadow-md p-6 hover:shadow-lg transition-shadow">
                  <div className="flex items-center gap-4">
                    <div className={`w-12 h-12 ${eventIconBg[item.event_type] || 'bg-gray-100'} rounded-lg flex items-center justify-center flex-shrink-0`}>
                      <Lock className="w-6 h-6 text-[#3D4F6B]" />
                    </div>
                    <div className="flex-1">
                      <h3 className="font-semibold text-[#0D1117]">{getEventLabel(item.event_type)}</h3>
                      {item.description && (
                        <p className="text-xs text-[#6B7280]">{item.description}</p>
                      )}
                      <p className="text-sm text-[#6B7280]">{formatRelativeTime(item.created_at)}</p>
                    </div>
                    <Clock className="w-4 h-4 text-[#6B7280] opacity-50 flex-shrink-0" />
                  </div>
                </div>
              ))}
            </div>

            {Array.isArray(data) && data.length === 20 && (
              <div className="mt-8 text-center">
                <button
                  onClick={handleLoadMore}
                  disabled={isLoading}
                  className="px-6 py-3 bg-white rounded-2xl shadow-md hover:shadow-lg transition-shadow text-[#3D4F6B] font-semibold disabled:opacity-50"
                >
                  {isLoading ? 'Loading...' : 'Load More'}
                </button>
              </div>
            )}
          </>
        )}

        <div className="bg-blue-50 border border-blue-200 rounded-2xl p-6 mt-8">
          <h4 className="font-semibold text-[#3D4F6B] mb-2">📋 Activity Log</h4>
          <p className="text-[#3D4F6B] text-sm">
            This log tracks all important activities on your account including check-ins, capsule management, and security events.
          </p>
        </div>
      </div>
    </div>
  )
}
