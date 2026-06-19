import { useState } from 'react'
import { ArrowLeft, Plus } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useCapsules, useDeleteCapsule } from '../../hooks/useCapsules'
import { useBeneficiaries } from '../../hooks/useBeneficiaries'
import CapsuleCard from '../../components/capsule/CapsuleCard'
import Modal from '../../components/ui/Modal'
import Button from '../../components/ui/Button'
import { Capsule, Beneficiary } from '../../types/api'

export default function CapsuleList() {
  const navigate = useNavigate()
  const { data: capsules, isLoading } = useCapsules()
  const { data: beneficiaries } = useBeneficiaries()
  const deleteMutation = useDeleteCapsule()
  const [deleteTarget, setDeleteTarget] = useState<Capsule | null>(null)

  const getBeneficiaryName = (id: string | null) => {
    if (!id) return undefined
    return beneficiaries?.find((b: Beneficiary) => b.id === id)?.full_name
  }

  const handleDelete = async () => {
    if (!deleteTarget) return
    await deleteMutation.mutateAsync(deleteTarget.id)
    setDeleteTarget(null)
  }

  return (
    <div className="min-h-screen bg-[#F0F2F5] p-4">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center gap-4 mb-8">
          <button onClick={() => navigate('/vault')} className="p-2 hover:bg-white rounded-lg transition-colors">
            <ArrowLeft className="w-5 h-5 text-[#0D1117]" />
          </button>
          <h1 className="text-3xl font-bold text-[#0D1117]">My Capsules</h1>
        </div>

        <Button fullWidth className="mb-8 py-4" onClick={() => navigate('/vault/capsules/new')}>
          <Plus className="w-5 h-5" />
          Create New Capsule
        </Button>

        {isLoading ? (
          <div className="space-y-4">
            {[1, 2, 3].map(i => (
              <div key={i} className="bg-white rounded-2xl shadow-md p-6 animate-pulse">
                <div className="flex items-center gap-3 mb-2">
                  <div className="w-5 h-5 bg-gray-200 rounded" />
                  <div className="h-5 bg-gray-200 rounded w-1/3" />
                </div>
                <div className="h-3 bg-gray-200 rounded w-1/4 mt-2" />
              </div>
            ))}
          </div>
        ) : (
          <div className="space-y-4">
            {capsules?.length === 0 && (
              <p className="text-center text-[#6B7280] py-8">No capsules yet. Create your first one above.</p>
            )}
            {capsules?.map((capsule: Capsule) => (
              <CapsuleCard
                key={capsule.id}
                capsule={capsule}
                beneficiaryName={getBeneficiaryName(capsule.beneficiary_id)}
                onView={() => navigate(`/vault/capsules/${capsule.id}/view`)}
                onEdit={() => navigate(`/vault/capsules/${capsule.id}`)}
                onDelete={() => setDeleteTarget(capsule)}
              />
            ))}
          </div>
        )}

        <div className="bg-blue-50 border border-blue-200 rounded-2xl p-6 mt-8">
          <h4 className="font-semibold text-[#3D4F6B] mb-2">💡 Tip</h4>
          <p className="text-[#3D4F6B] text-sm">
            Create multiple capsules and assign them to different beneficiaries. Each is encrypted independently.
          </p>
        </div>
      </div>

      <Modal
        isOpen={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        title="Delete Capsule"
        footer={
          <div className="flex gap-3">
            <Button variant="secondary" fullWidth onClick={() => setDeleteTarget(null)}>Cancel</Button>
            <Button variant="danger" fullWidth loading={deleteMutation.isPending} onClick={handleDelete}>Delete</Button>
          </div>
        }
      >
        <p className="text-[#6B7280]">
          Are you sure you want to delete <strong>"{deleteTarget?.title}"</strong>? This will mark it for deletion.
        </p>
      </Modal>
    </div>
  )
}
