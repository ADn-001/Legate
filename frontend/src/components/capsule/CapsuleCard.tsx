import { Lock, Edit2, Trash2 } from 'lucide-react'
import Badge from '../ui/Badge'
import { Capsule } from '../../types/api'

interface CapsuleCardProps {
  capsule: Capsule
  beneficiaryName?: string
  onEdit: () => void
  onDelete: () => void
}

const statusBadgeVariant = (status: Capsule['status']) => {
  switch (status) {
    case 'active': return 'success' as const
    case 'draft': return 'default' as const
    case 'pending_deletion': return 'warning' as const
    case 'delivered': return 'info' as const
    case 'deleted': return 'error' as const
    default: return 'default' as const
  }
}

const statusLabel = (status: Capsule['status']) => {
  switch (status) {
    case 'active': return 'Active'
    case 'draft': return 'Draft'
    case 'pending_deletion': return 'Pending Deletion'
    case 'delivered': return 'Delivered'
    case 'deleted': return 'Deleted'
    default: return status
  }
}

export default function CapsuleCard({ capsule, beneficiaryName, onEdit, onDelete }: CapsuleCardProps) {
  return (
    <div className="bg-white rounded-2xl shadow-md p-6 hover:shadow-lg transition-shadow">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 mb-2">
            <Lock className="w-5 h-5 text-[#3D4F6B] flex-shrink-0" />
            <h3 className="text-lg font-semibold text-[#0D1117] truncate">{capsule.title}</h3>
          </div>
          {beneficiaryName && (
            <p className="text-sm text-[#6B7280] mb-3">To: {beneficiaryName}</p>
          )}
          <Badge variant={statusBadgeVariant(capsule.status)}>
            {statusLabel(capsule.status)}
          </Badge>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <button
            onClick={onEdit}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            aria-label="Edit capsule"
          >
            <Edit2 className="w-5 h-5 text-[#3D4F6B]" />
          </button>
          <button
            onClick={onDelete}
            className="p-2 hover:bg-red-50 rounded-lg transition-colors"
            aria-label="Delete capsule"
          >
            <Trash2 className="w-5 h-5 text-[#C0392B]" />
          </button>
        </div>
      </div>
    </div>
  )
}
