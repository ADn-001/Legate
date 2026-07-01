import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { beneficiariesApi } from '../../api/beneficiaries'
import { settingsApi } from '../../api/settings'
import BeneficiaryForm from '../../components/beneficiary/BeneficiaryForm'
import SecurityBanner from '../../components/ui/SecurityBanner'
import { BeneficiaryCreatePayload } from '../../api/beneficiaries'

export default function StepBeneficiary() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (data: BeneficiaryCreatePayload) => {
    setLoading(true)
    setError(null)
    try {
      await beneficiariesApi.create(data)
      await settingsApi.patchSettings({ setup_step: 3 }).catch(() => {})
      navigate('/setup/capsule')
    } catch {
      setError('Failed to add beneficiary. Please try again.')
      throw new Error('Failed')
    } finally {
      setLoading(false)
    }
  }

  const handleSkip = async () => {
    await settingsApi.patchSettings({ needs_onboarding: false }).catch(() => {})
    navigate('/vault')
  }

  return (
    <div className="max-w-md mx-auto px-4 pb-8">
      <div className="bg-white rounded-2xl shadow-lg p-8">
        <h1 className="text-2xl font-bold text-[#0D1117] mb-2">Who should receive your legacy?</h1>
        <p className="text-[#6B7280] mb-6">Add the first person who will receive your capsules.</p>

        <SecurityBanner className="mb-6">
          They will only receive instructions, not account access. Your beneficiaries cannot modify your settings.
        </SecurityBanner>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        <BeneficiaryForm
          onSubmit={handleSubmit}
          onCancel={() => navigate('/setup/checkin')}
          loading={loading}
        />

        <button
          onClick={handleSkip}
          className="w-full mt-4 text-sm text-[#6B7280] hover:text-[#3D4F6B] transition-colors py-2"
        >
          Skip setup
        </button>
      </div>
    </div>
  )
}
