import { Edit2, Trash2 } from 'lucide-react'
import Badge from '../ui/Badge'
import { Beneficiary } from '../../types/api'

interface BeneficiaryCardProps {
  beneficiary: Beneficiary
  onEdit: () => void
  onDelete: () => void
}

export default function BeneficiaryCard({ beneficiary, onEdit, onDelete }: BeneficiaryCardProps) {
  const initials = beneficiary.full_name
    .split(' ')
    .map(n => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2)

  const isPending = beneficiary.status === 'pending'

  return (
    <div
      className={`bg-white rounded-2xl shadow-md p-6 flex items-start justify-between hover:shadow-lg transition-shadow ${isPending ? 'border-2 border-dashed border-gray-300' : ''}`}
    >
      <div className="flex items-center gap-4 flex-1 min-w-0">
        <div className="w-12 h-12 bg-gradient-to-br from-blue-400 to-blue-600 rounded-full flex items-center justify-center text-white font-bold text-lg flex-shrink-0">
          {initials}
        </div>
        <div className="flex-1 min-w-0">
          <h3 className={`font-semibold text-[#0D1117] text-lg ${isPending ? 'italic' : ''}`}>
            {beneficiary.full_name}
          </h3>
          <p className="text-sm text-[#6B7280] truncate">{beneficiary.email}</p>
          {isPending && (
            <p className="text-xs text-amber-600 mt-1">Invite pending...</p>
          )}
          <div className="flex gap-2 mt-2 flex-wrap">
            {beneficiary.relationship && (
              <Badge variant="default">{beneficiary.relationship}</Badge>
            )}
            {beneficiary.is_emergency_contact && (
              <Badge variant="info">Emergency Contact</Badge>
            )}
            {isPending && <Badge variant="warning">Pending</Badge>}
          </div>
        </div>
      </div>
      <div className="flex items-center gap-2 ml-4 flex-shrink-0">
        <button
          onClick={onEdit}
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          aria-label="Edit beneficiary"
        >
          <Edit2 className="w-5 h-5 text-[#3D4F6B]" />
        </button>
        <button
          onClick={onDelete}
          className="p-2 hover:bg-red-50 rounded-lg transition-colors"
          aria-label="Delete beneficiary"
        >
          <Trash2 className="w-5 h-5 text-[#C0392B]" />
        </button>
      </div>
    </div>
  )
}
