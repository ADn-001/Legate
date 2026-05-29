import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { settingsApi } from '../../api/settings'
import Button from '../../components/ui/Button'

const intervalOptions = [7, 14, 30, 60]
const graceOptions = [3, 7, 14, 30]

export default function StepCheckin() {
  const navigate = useNavigate()
  const [interval, setInterval] = useState(30)
  const [grace, setGrace] = useState(7)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleContinue = async () => {
    setLoading(true)
    setError(null)
    try {
      await settingsApi.updateCheckinSchedule({ interval_days: interval, grace_period_days: grace })
      navigate('/setup/beneficiary')
    } catch {
      setError('Failed to save check-in settings. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-md mx-auto px-4 pb-8">
      <div className="bg-white rounded-2xl shadow-lg p-8">
        <h1 className="text-2xl font-bold text-[#0D1117] mb-2">How often should we check in?</h1>
        <p className="text-[#6B7280] mb-8">
          We'll send you a check-in email on this schedule. If we don't hear back within the grace period, your capsules will be delivered.
        </p>

        <div className="mb-6">
          <p className="text-sm font-semibold text-[#0D1117] mb-3">Check-in Interval</p>
          <div className="grid grid-cols-4 gap-2">
            {intervalOptions.map(d => (
              <button
                key={d}
                onClick={() => setInterval(d)}
                className={`py-3 rounded-xl text-sm font-semibold border-2 transition-colors ${interval === d ? 'border-[#3D4F6B] bg-[#3D4F6B] text-white' : 'border-gray-200 text-[#6B7280] hover:border-gray-300'}`}
              >
                {d}d
              </button>
            ))}
          </div>
        </div>

        <div className="mb-8">
          <p className="text-sm font-semibold text-[#0D1117] mb-3">Grace Period</p>
          <div className="grid grid-cols-4 gap-2">
            {graceOptions.map(d => (
              <button
                key={d}
                onClick={() => setGrace(d)}
                className={`py-3 rounded-xl text-sm font-semibold border-2 transition-colors ${grace === d ? 'border-[#3D4F6B] bg-[#3D4F6B] text-white' : 'border-gray-200 text-[#6B7280] hover:border-gray-300'}`}
              >
                {d}d
              </button>
            ))}
          </div>
        </div>

        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
          <p className="text-sm text-[#3D4F6B]">
            If we don't hear from you within <strong>{interval + grace} days</strong> ({interval}d interval + {grace}d grace), your capsules will be delivered to your beneficiaries.
          </p>
        </div>

        {error && <p className="text-sm text-red-600 mb-4">{error}</p>}

        <Button fullWidth loading={loading} onClick={handleContinue}>
          Continue
        </Button>
      </div>
    </div>
  )
}
