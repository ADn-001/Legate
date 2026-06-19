import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Plus } from 'lucide-react'
import { useBeneficiaries, useCreateBeneficiary, useUpdateBeneficiary, useDeleteBeneficiary } from '../../hooks/useBeneficiaries'
import BeneficiaryCard from '../../components/beneficiary/BeneficiaryCard'
import BeneficiaryForm from '../../components/beneficiary/BeneficiaryForm'
import Modal from '../../components/ui/Modal'
import BottomSheet from '../../components/ui/BottomSheet'
import SecurityBanner from '../../components/ui/SecurityBanner'
import Button from '../../components/ui/Button'
import { Beneficiary } from '../../types/api'
import { BeneficiaryCreatePayload } from '../../api/beneficiaries'

export default function Beneficiaries() {
  const navigate = useNavigate()
  const { data: beneficiaries, isLoading } = useBeneficiaries()
  const createMutation = useCreateBeneficiary()
  const updateMutation = useUpdateBeneficiary()
  const deleteMutation = useDeleteBeneficiary()

  const [showForm, setShowForm] = useState(false)
  const [editTarget, setEditTarget] = useState<Beneficiary | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<Beneficiary | null>(null)
  const [formError, setFormError] = useState<string | null>(null)

  const isMobile = window.innerWidth <= 768

  // F11/FR-23: the beneficiary who currently holds the single emergency
  // contact slot, if it's not the one being edited right now.
  const currentEmergencyContact = beneficiaries?.find((b: Beneficiary) => b.is_emergency_contact)
  const otherEmergencyContactName =
    currentEmergencyContact && currentEmergencyContact.id !== editTarget?.id
      ? currentEmergencyContact.full_name
      : undefined

  const handleCreate = async (data: BeneficiaryCreatePayload) => {
    setFormError(null)
    try {
      await createMutation.mutateAsync(data)
      setShowForm(false)
    } catch {
      setFormError('Failed to add beneficiary')
      throw new Error('Failed')
    }
  }

  const handleUpdate = async (data: BeneficiaryCreatePayload) => {
    if (!editTarget) return
    setFormError(null)
    try {
      await updateMutation.mutateAsync({ id: editTarget.id, data })
      setEditTarget(null)
    } catch {
      setFormError('Failed to update beneficiary')
      throw new Error('Failed')
    }
  }

  const handleDelete = async () => {
    if (!deleteTarget) return
    try {
      await deleteMutation.mutateAsync(deleteTarget.id)
      setDeleteTarget(null)
    } catch {
      // ignore
    }
  }

  const formContent = (
    <>
      {formError && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
          <p className="text-sm text-red-700">{formError}</p>
        </div>
      )}
      <BeneficiaryForm
        initialData={editTarget ? {
          full_name: editTarget.full_name,
          email: editTarget.email,
          relationship: editTarget.relationship,
          is_emergency_contact: editTarget.is_emergency_contact,
        } : undefined}
        onSubmit={editTarget ? handleUpdate : handleCreate}
        onCancel={() => { setShowForm(false); setEditTarget(null) }}
        loading={createMutation.isPending || updateMutation.isPending}
        otherEmergencyContactName={otherEmergencyContactName}
      />
    </>
  )

  return (
    <div className="min-h-screen bg-[#F0F2F5] p-4">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center gap-4 mb-8">
          <button onClick={() => navigate('/vault')} className="p-2 hover:bg-white rounded-lg transition-colors">
            <ArrowLeft className="w-5 h-5 text-[#0D1117]" />
          </button>
          <div>
            <h1 className="text-3xl font-bold text-[#0D1117]">Beneficiaries</h1>
            <p className="text-[#6B7280]">Manage who receives your legacy instructions</p>
          </div>
        </div>

        <SecurityBanner className="mb-8">
          They will only receive instructions, not account access. Your beneficiaries cannot modify your settings.
        </SecurityBanner>

        <Button fullWidth className="mb-8 py-4" onClick={() => setShowForm(true)}>
          <Plus className="w-5 h-5" />
          Add Beneficiary
        </Button>

        {isLoading ? (
          <div className="space-y-4">
            {[1, 2].map(i => (
              <div key={i} className="bg-white rounded-2xl shadow-md p-6 animate-pulse">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 bg-gray-200 rounded-full" />
                  <div className="flex-1 space-y-2">
                    <div className="h-4 bg-gray-200 rounded w-1/3" />
                    <div className="h-3 bg-gray-200 rounded w-1/2" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="space-y-4">
            {beneficiaries?.length === 0 && (
              <p className="text-center text-[#6B7280] py-8">No beneficiaries yet. Add your first one above.</p>
            )}
            {beneficiaries?.map((b: Beneficiary) => (
              <BeneficiaryCard
                key={b.id}
                beneficiary={b}
                onEdit={() => setEditTarget(b)}
                onDelete={() => setDeleteTarget(b)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Form — Modal on desktop, BottomSheet on mobile */}
      {isMobile ? (
        <BottomSheet
          isOpen={showForm || !!editTarget}
          onClose={() => { setShowForm(false); setEditTarget(null) }}
          title={editTarget ? 'Edit Beneficiary' : 'Add Beneficiary'}
        >
          {formContent}
        </BottomSheet>
      ) : (
        <Modal
          isOpen={showForm || !!editTarget}
          onClose={() => { setShowForm(false); setEditTarget(null) }}
          title={editTarget ? 'Edit Beneficiary' : 'Add Beneficiary'}
        >
          {formContent}
        </Modal>
      )}

      {/* Delete Confirmation */}
      <Modal
        isOpen={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        title="Delete Beneficiary"
        footer={
          <div className="flex gap-3">
            <Button variant="secondary" fullWidth onClick={() => setDeleteTarget(null)}>Cancel</Button>
            <Button variant="danger" fullWidth loading={deleteMutation.isPending} onClick={handleDelete}>Delete</Button>
          </div>
        }
      >
        <p className="text-[#6B7280]">
          Are you sure you want to remove <strong>{deleteTarget?.full_name}</strong>? Capsules assigned to them will become unassigned.
        </p>
      </Modal>
    </div>
  )
}
