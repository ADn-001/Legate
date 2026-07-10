import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { AlertTriangle } from 'lucide-react'
import { settingsApi } from '../../api/settings'
import { CheckinSchedule } from '../../types/api'
import Button from '../../components/ui/Button'
import Modal from '../../components/ui/Modal'

const intervalOptions = [7, 14, 30, 60]
const graceOptions = [3, 7, 14, 30]

// B4/FR-11: floor lowered from 7 to 1 day (permanent, all environments).
const MIN_CUSTOM_INTERVAL = 1
const MAX_CUSTOM_INTERVAL = 365
// Warn if the total window (interval + grace) drops below this many days
const SHORT_WINDOW_WARNING_DAYS = 14
// Demo-mode minute overrides (mirrors Security.tsx's "Apply Demo Schedule"
// panel — this was previously the only place the demo controls existed,
// forcing a detour to Settings after finishing onboarding).
const MIN_DEMO_MINUTES = 1
const MAX_DEMO_MINUTES = 1440

export default function StepCheckin() {
  const navigate = useNavigate()
  const [interval, setIntervalVal] = useState(30)
  const [grace, setGrace] = useState(7)
  const [isCustom, setIsCustom] = useState(false)
  const [customInterval, setCustomInterval] = useState(30)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showShortWindowWarning, setShowShortWindowWarning] = useState(false)

  // Demo-mode panel state — only rendered once we know the server has
  // DEMO_MODE enabled (checkinSchedule?.demo_mode). Applying it fires its
  // own request immediately, independent of the day-based Continue flow
  // below, matching how Security.tsx's panel behaves.
  const { data: checkinSchedule } = useQuery<CheckinSchedule>({
    queryKey: ['checkin-schedule'],
    queryFn: () => settingsApi.getCheckinSchedule().then(r => r.data),
  })
  const [demoIntervalMinutes, setDemoIntervalMinutes] = useState(2)
  const [demoGraceMinutes, setDemoGraceMinutes] = useState(2)
  const [demoEmergencyMinutes, setDemoEmergencyMinutes] = useState(2)
  const [demoSaving, setDemoSaving] = useState(false)
  const [demoMsg, setDemoMsg] = useState<string | null>(null)

  const applyDemoSchedule = async () => {
    setDemoSaving(true)
    setDemoMsg(null)
    try {
      await settingsApi.updateCheckinSchedule({
        check_interval_minutes: demoIntervalMinutes,
        grace_period_minutes: demoGraceMinutes,
        emergency_confirm_minutes: demoEmergencyMinutes,
      })
      setDemoMsg('Demo schedule applied.')
    } catch {
      setDemoMsg('Demo mode is disabled on the server, or the request failed.')
    } finally {
      setDemoSaving(false)
    }
  }

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

        {/* Demo scheduling — only rendered when the server has DEMO_MODE
            enabled (server still enforces this with a 403 regardless of
            whether this section is visible). Applying it overrides the
            day-based schedule above with minute-level timing, independent
            of the Continue button below. */}
        {checkinSchedule?.demo_mode && (
          <div className="border-2 border-amber-400 bg-amber-50 rounded-xl p-4 space-y-3 mb-6">
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 bg-amber-400 text-white text-[10px] font-bold rounded uppercase tracking-wide">
                Demo
              </span>
              <p className="text-sm font-semibold text-amber-800">Demo scheduling (minutes)</p>
            </div>
            <p className="text-xs text-amber-700">
              Overrides the day-based schedule above with minute-level timing so a live demo can
              run the full check-in lifecycle in minutes instead of weeks.
            </p>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-amber-800 mb-1">Interval (minutes)</label>
                <input
                  type="number"
                  min={MIN_DEMO_MINUTES}
                  max={MAX_DEMO_MINUTES}
                  value={demoIntervalMinutes}
                  onChange={e => setDemoIntervalMinutes(Math.max(MIN_DEMO_MINUTES, Math.min(MAX_DEMO_MINUTES, Number(e.target.value))))}
                  className="input-field w-full"
                />
              </div>
              <div>
                <label className="block text-xs text-amber-800 mb-1">Grace (minutes)</label>
                <input
                  type="number"
                  min={MIN_DEMO_MINUTES}
                  max={MAX_DEMO_MINUTES}
                  value={demoGraceMinutes}
                  onChange={e => setDemoGraceMinutes(Math.max(MIN_DEMO_MINUTES, Math.min(MAX_DEMO_MINUTES, Number(e.target.value))))}
                  className="input-field w-full"
                />
              </div>
            </div>
            <div>
              <label className="block text-xs text-amber-800 mb-1">
                Emergency confirm window (minutes)
              </label>
              <input
                type="number"
                min={MIN_DEMO_MINUTES}
                max={MAX_DEMO_MINUTES}
                value={demoEmergencyMinutes}
                onChange={e => setDemoEmergencyMinutes(Math.max(MIN_DEMO_MINUTES, Math.min(MAX_DEMO_MINUTES, Number(e.target.value))))}
                className="input-field w-full"
              />
              <p className="text-[11px] text-amber-700 mt-1">
                Only matters once you've added an emergency contact (normally 48 hours) — replaces
                that real-time wait with minutes so the pending-confirmation branch can be demoed too.
              </p>
            </div>
            {demoMsg && (
              <p className={`text-sm ${demoMsg === 'Demo schedule applied.' ? 'text-green-700' : 'text-red-600'}`}>
                {demoMsg}
              </p>
            )}
            <Button loading={demoSaving} onClick={applyDemoSchedule}>
              Apply Demo Schedule
            </Button>
          </div>
        )}

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
