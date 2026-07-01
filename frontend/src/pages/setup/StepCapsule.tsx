import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { capsulesApi } from '../../api/capsules'
import { settingsApi } from '../../api/settings'
import { useBeneficiaries } from '../../hooks/useBeneficiaries'
import { useCryptoStore } from '../../store/crypto'
import { useAuthStore } from '../../store/auth'
import { capsuleEncryption } from '../../crypto/capsule'
import { uploadEncryptedBlob } from '../../utils/storage'
import Button from '../../components/ui/Button'
import SecurityBanner from '../../components/ui/SecurityBanner'

export default function StepCapsule() {
  const navigate = useNavigate()
  const [title, setTitle] = useState('')
  const [message, setMessage] = useState('')
  const [beneficiaryId, setBeneficiaryId] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const cek = useCryptoStore(s => s.cek)
  const user = useAuthStore(s => s.user)
  const { data: beneficiaries } = useBeneficiaries()

  useEffect(() => {
    if (beneficiaries?.length > 0 && !beneficiaryId) {
      setBeneficiaryId(beneficiaries[0].id)
    }
  }, [beneficiaries])

  const handleSave = async () => {
    if (!cek) { setError('No encryption key in memory — please log in again'); return }
    if (!title.trim()) { setError('Title is required'); return }
    if (!beneficiaryId) { setError('Please select a beneficiary'); return }
    setSaving(true)
    setError(null)
    try {
      const { ciphertext, iv } = await capsuleEncryption.encrypt(message, cek)
      const cipherIvHex = Array.from(iv).map(b => b.toString(16).padStart(2, '0')).join('')
      const { data } = await capsulesApi.create({ title, beneficiary_id: beneficiaryId, cipher_iv: cipherIvHex })
      const { id: capsuleId, upload_url } = data
      await uploadEncryptedBlob(upload_url, new Blob([ciphertext]))
      await capsulesApi.update(capsuleId, { storage_object_path: `${user!.id}/${capsuleId}/content.enc` })
      await settingsApi.patchSettings({ setup_step: 4 }).catch(() => {})
      navigate('/setup/recovery')
    } catch {
      setError('Failed to save capsule. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="max-w-md mx-auto px-4 pb-8">
      <div className="bg-white rounded-2xl shadow-lg p-8">
        <h1 className="text-2xl font-bold text-[#0D1117] mb-2">Create your first capsule</h1>
        <p className="text-[#6B7280] mb-6">Write a message for your beneficiary. You can add more later.</p>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-semibold text-[#0D1117] mb-2">CAPSULE TITLE</label>
            <input
              type="text"
              value={title}
              onChange={e => setTitle(e.target.value)}
              placeholder="e.g. Instructions for Sarah"
              className="input-field w-full"
            />
          </div>

          <div>
            <label className="block text-sm font-semibold text-[#0D1117] mb-2">MESSAGE</label>
            <textarea
              value={message}
              onChange={e => setMessage(e.target.value)}
              placeholder="Write your message here..."
              rows={6}
              maxLength={10000}
              className="input-field w-full resize-none"
            />
            <p className="text-xs text-[#6B7280] text-right mt-1">{message.length}/10000</p>
          </div>

          {beneficiaries && beneficiaries.length > 0 && (
            <div>
              <label className="block text-sm font-semibold text-[#0D1117] mb-2">BENEFICIARY</label>
              <select
                value={beneficiaryId}
                onChange={e => setBeneficiaryId(e.target.value)}
                className="input-field w-full"
              >
                {beneficiaries.map((b: { id: string; full_name: string }) => (
                  <option key={b.id} value={b.id}>{b.full_name}</option>
                ))}
              </select>
            </div>
          )}

          <SecurityBanner>
            Your message is encrypted client-side before leaving this device.
          </SecurityBanner>
        </div>

        <div className="flex gap-3 mt-6">
          <Button
            variant="secondary"
            fullWidth
            onClick={async () => {
              await settingsApi.patchSettings({ setup_step: 4 }).catch(() => {})
              navigate('/setup/recovery')
            }}
            disabled={saving}
          >
            Skip for now
          </Button>
          <Button fullWidth loading={saving} onClick={handleSave}>
            Save Capsule
          </Button>
        </div>
      </div>
    </div>
  )
}
