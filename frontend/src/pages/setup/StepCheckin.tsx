import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AlertTriangle } from 'lucide-react'
import { settingsApi } from '../../api/settings'
import Button from '../../components/ui/Button'
import Modal from '../../components/ui/Modal'

const intervalOptions = [7, 14, 30, 60]
const graceOptions = [3, 7, 14, 30]

const MIN_CUSTOM_INTERVAL = 7
const MAX_CUSTOM_INTERVAL = 365
// Warn if the total window (interval + grace) drops below this many days
const SHORT_WINDOW_WARNING_DAYS = 14

export default function StepCheckin() {
  const navigate = useNavigate()
  const [interval, setIntervalVal] = useState(30)
  const [grace, setGrace] = useState(7)
  const [isCustom, setIsCustom] = useState(false)
  const [customInterval, setCustomInterval] = useState(30)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showShortWindowWarning, setShowShortWindowWarning] = useState(false)

  const effectiveInterval = isCustom ? customInterval : interval
  const totalWindow = effectiveInterval + grace

  function selectInterval(d: number) {
    setIsCustom(false)
    setIntervalVal(d)
  }

  function selectCustom() {
    setIsCustom(true)
    setCustomInterval(30)
  }

  async function persist() {
    setLoading(true)
    setError(null)
    try {
      await settingsApi.updateCheckinSchedule({
        interval_days: effectiveInterval,
        grace_period_days: grace,
      })
      // T5: persist wizard step so the user can resume if they leave
      await settingsApi.patchSettings({ setup_step: 2 })
      navigate('/setup/beneficiary')
    } catch {
      setError('Failed to save check-in settings. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleContinue = async () => {
    if (isCustom) {
      const val = Math.round(customInterval)
      if (val < MIN_CUSTOM_INTERVAL || val > MAX_CUSTOM_INTERVAL) {
        setError(`Custom interval must be between ${MIN_CUSTOM_INTERVAL} and ${MAX_CUSTOM_INTERVAL} days.`)
        return
      }
    }
    // Warn if the delivery window is very short
    if (totalWindow < SHORT_WINDOW_WARNING_DAYS) {
      setShowShortWindowWarning(true)
      return
    }
    await persist()
  }

  const handleSkip = async () => {
    try {
      await settingsApi.patchSettings({ needs_onboarding: false })
    } catch { /* non-blocking */ }
    navigate('/vault')
  }

  return (
    <div className="max-w-md mx-auto px-4 pb-8">
      <div className="bg-white rounded-2xl shadow-lg p-8">
        <h1 className="text-2xl font-bold text-[#0D1117] mb-2">How often should we check in?</h1>
        <p className="text-[#6B7280] mb-8">
          We'll send you a check-in email on this schedule. If we don't hear back within the grace period,
          your capsules will be delivered.
        </p>

        <div className="mb-6">
          <p className="text-sm font-semibold text-[#0D1117] mb-3">Check-in Interval</p>
          <div className="grid grid-cols-3 gap-2 mb-2">
            {intervalOptions.map(d => (
              <button
                key={d}
                onClick={() => selectInterval(d)}
                className={`py-3 rounded-xl text-sm font-semibold border-2 transition-colors ${
                  !isCustom && interval === d
                    ? 'border-[#3D4F6B] bg-[#3D4F6B] text-white'
                    : 'border-gray-200 text-[#6B7280] hover:border-gray-300'
                }`}
              >
                {d}d
              </button>
            ))}
            <button
              onClick={selectCustom}
              className={`py-3 rounded-xl text-sm font-semibold border-2 transition-colors ${
                isCustom
                  ? 'border-[#3D4F6B] bg-[#3D4F6B] text-white'
                  : 'border-gray-200 text-[#6B7280] hover:border-gray-300'
              }`}
            >
              Custom
            </button>
          </div>
          {isCustom && (
            <div className="mt-3">
              <label className="block text-xs text-[#6B7280] mb-1">
                Days ({MIN_CUSTOM_INTERVAL}–{MAX_CUSTOM_INTERVAL})
              </label>
              <input
                type="number"
                min={MIN_CUSTOM_INTERVAL}
                max={MAX_CUSTOM_INTERVAL}
                value={customInterval}
                onChange={e => setCustomInterval(Math.max(MIN_CUSTOM_INTERVAL, Math.min(MAX_CUSTOM_INTERVAL, Number(e.target.value))))}
                className="input-field w-full"
              />
            </div>
          )}
        </div>

        <div className="mb-8">
          <p className="text-sm font-semibold text-[#0D1117] mb-3">Grace Period</p>
          <div className="grid grid-cols-4 gap-2">
            {graceOptions.map(d => (
              <button
                key={d}
                onClick={() => setGrace(d)}
                className={`py-3 rounded-xl text-sm font-semibold border-2 transition-colors ${
                  grace === d
                    ? 'border-[#3D4F6B] bg-[#3D4F6B] text-white'
                    : 'border-gray-200 text-[#6B7280] hover:border-gray-300'
                }`}
              >
                {d}d
              </button>
            ))}
          </div>
        </div>

        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
          <p className="text-sm text-[#3D4F6B]">
            If we don't hear from you within <strong>{totalWindow} days</strong> ({effectiveInterval}d interval + {grace}d grace),
            your capsules will be delivered to your beneficiaries.
          </p>
        </div>

        {error && <p className="text-sm text-red-600 mb-4">{error}</p>}

        <Button fullWidth loading={loading} onClick={handleContinue}>
          Continue
        </Button>

        <button
          onClick={handleSkip}
          className="w-full mt-3 text-sm text-[#6B7280] hover:text-[#3D4F6B] transition-colors py-2"
        >
          Skip setup
        </button>
      </div>

      {/* Short-window warning modal */}
      <Modal
        isOpen={showShortWindowWarning}
        onClose={() => setShowShortWindowWarning(false)}
        title="Very Short Delivery Window"
        footer={
          <div className="flex gap-3">
            <Button variant="secondary" fullWidth onClick={() => setShowShortWindowWarning(false)}>
              Go Back
            </Button>
            <Button fullWidth loading={loading} onClick={() => { setShowShortWindowWarning(false); persist() }}>
              Proceed Anyway
            </Button>
          </div>
        }
      >
        <div className="flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
          <div className="space-y-2">
            <p className="text-sm text-[#0D1117]">
              Your total delivery window is only <strong>{totalWindow} days</strong>. A missed check-in
              email (spam folder, travel, etc.) could trigger delivery sooner than intended.
            </p>
            <p className="text-sm text-[#6B7280]">We recommend at least 14 days total for most users.</p>
          </div>
        </div>
      </Modal>
    </div>
  )
}
