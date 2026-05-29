import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { capsulesApi } from '../../api/capsules'
import { useBeneficiaries } from '../../hooks/useBeneficiaries'
import { useCryptoStore } from '../../store/crypto'
import { useAuthStore } from '../../store/auth'
import { capsuleEncryption } from '../../crypto/capsule'
import { mediaEncryption } from '../../crypto/media'
import { uploadEncryptedBlob } from '../../utils/storage'
import MediaUploader from '../../components/capsule/MediaUploader'
import SecurityBanner from '../../components/ui/SecurityBanner'
import Button from '../../components/ui/Button'

type AutoSaveStatus = 'saved' | 'saving' | 'unsaved'

export default function CapsuleEditor() {
  const navigate = useNavigate()
  const { id } = useParams()
  const isEdit = !!id

  const [title, setTitle] = useState('')
  const [message, setMessage] = useState('')
  const [beneficiaryId, setBeneficiaryId] = useState('')
  const [files, setFiles] = useState<File[]>([])
  const [saving, setSaving] = useState(false)
  const [autoSaveStatus, setAutoSaveStatus] = useState<AutoSaveStatus>('unsaved')
  const [error, setError] = useState<string | null>(null)

  const cek = useCryptoStore(s => s.cek)
  const user = useAuthStore(s => s.user)
  const { data: beneficiaries } = useBeneficiaries()

  // Load draft on mount
  useEffect(() => {
    const draftKey = `draft_capsule_${id || 'new'}`
    const draft = localStorage.getItem(draftKey)
    if (draft) {
      try {
        const d = JSON.parse(draft)
        setTitle(d.title || '')
        setMessage(d.message || '')
        setBeneficiaryId(d.beneficiaryId || '')
      } catch {
        // ignore corrupt draft
      }
    }
  }, [id])

  // Set first beneficiary as default
  useEffect(() => {
    if (beneficiaries?.length > 0 && !beneficiaryId) {
      setBeneficiaryId(beneficiaries[0].id)
    }
  }, [beneficiaries])

  // Auto-save draft every 30s
  useEffect(() => {
    const timer = setInterval(() => {
      const draft = { title, message, beneficiaryId }
      localStorage.setItem(`draft_capsule_${id || 'new'}`, JSON.stringify(draft))
      setAutoSaveStatus('saved')
      setTimeout(() => setAutoSaveStatus('unsaved'), 2000)
    }, 30000)
    return () => clearInterval(timer)
  }, [title, message, beneficiaryId, id])

  const handleSave = async () => {
    if (!cek) { setError('No encryption key in memory — please log in again'); return }
    if (!title.trim()) { setError('Capsule title is required'); return }
    if (!beneficiaryId) { setError('Please select a beneficiary'); return }

    setSaving(true)
    setError(null)
    try {
      const { ciphertext, iv } = await capsuleEncryption.encrypt(message, cek)
      const cipherIvHex = Array.from(iv).map(b => b.toString(16).padStart(2, '0')).join('')

      const { data } = await capsulesApi.create({
        title,
        beneficiary_id: beneficiaryId,
        cipher_iv: cipherIvHex,
      })
      const { id: capsuleId, upload_url } = data

      await uploadEncryptedBlob(upload_url, new Blob([ciphertext]))
      await capsulesApi.update(capsuleId, { storage_object_path: `${user!.id}/${capsuleId}/content.enc` })

      // Media upload stub — requires B4 backend endpoint
      if (files.length > 0) {
        for (const file of files) {
          // eslint-disable-next-line @typescript-eslint/no-unused-vars
          const { encryptedBlob: _blob, iv: _iv } = await mediaEncryption.encrypt(file, cek)
          // TODO: POST /capsules/{capsuleId}/media → get upload_url → PUT encryptedBlob
          // This requires the B4 backend endpoint to be implemented first.
        }
      }

      localStorage.removeItem(`draft_capsule_${id || 'new'}`)
      navigate('/vault/capsules')
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to save capsule'
      setError(msg)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#F0F2F5] p-4">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <div className="flex items-center gap-4 mb-6">
          <button onClick={() => navigate('/vault/capsules')} className="p-2 hover:bg-white rounded-lg transition-colors">
            <ArrowLeft className="w-5 h-5 text-[#0D1117]" />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-[#0D1117]">
              {isEdit ? 'Edit Capsule' : 'Create Capsule'}
            </h1>
            <p className="text-sm text-[#6B7280]">Secure your digital legacy</p>
          </div>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        {/* Content Section */}
        <div className="bg-white rounded-2xl shadow-md p-6 mb-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-[#0D1117]">CONTENT</h2>
            <span className={`text-xs ${autoSaveStatus === 'saved' ? 'text-green-600' : 'text-gray-400'}`}>
              {autoSaveStatus === 'saved' ? '✓ Draft saved' : autoSaveStatus === 'saving' ? 'Saving...' : ''}
            </span>
          </div>

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
                rows={8}
                maxLength={10000}
                className="input-field w-full resize-none"
              />
              <p className="text-xs text-[#6B7280] text-right mt-1">{message.length}/10000</p>
            </div>
          </div>
        </div>

        {/* Media Section */}
        <div className="bg-white rounded-2xl shadow-md p-6 mb-4">
          <h2 className="font-semibold text-[#0D1117] mb-4">MEDIA ATTACHMENTS</h2>
          <MediaUploader files={files} onFilesChange={setFiles} />
          <p className="text-xs text-amber-600 mt-2">
            Note: Media uploads require a pending backend endpoint. Files will be encrypted but not uploaded until B4 is implemented.
          </p>
        </div>

        {/* Beneficiary Section */}
        <div className="bg-white rounded-2xl shadow-md p-6 mb-4">
          <h2 className="font-semibold text-[#0D1117] mb-4">BENEFICIARY</h2>
          {beneficiaries?.length > 0 ? (
            <select
              value={beneficiaryId}
              onChange={e => setBeneficiaryId(e.target.value)}
              className="input-field w-full"
            >
              <option value="">Select beneficiary...</option>
              {beneficiaries.map((b: { id: string; full_name: string }) => (
                <option key={b.id} value={b.id}>{b.full_name}</option>
              ))}
            </select>
          ) : (
            <p className="text-sm text-[#6B7280]">
              No beneficiaries yet.{' '}
              <button onClick={() => navigate('/people')} className="text-[#3D4F6B] underline">
                Add one first
              </button>
            </p>
          )}
        </div>

        {/* Security Notice */}
        <SecurityBanner className="mb-4">
          Your message is encrypted client-side before leaving this device. Only your beneficiary can decrypt it.
        </SecurityBanner>

        {/* Save Button */}
        <Button fullWidth loading={saving} onClick={handleSave} className="py-4 text-base">
          {isEdit ? 'Update Capsule' : 'Save Capsule'}
        </Button>
      </div>
    </div>
  )
}
