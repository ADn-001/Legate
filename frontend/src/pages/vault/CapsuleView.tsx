import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, Lock, Edit2, Paperclip, AlertTriangle } from 'lucide-react'
import { capsulesApi } from '../../api/capsules'
import { useBeneficiaries } from '../../hooks/useBeneficiaries'
import { requireCek } from '../../store/unlock'
import { capsuleEncryption, hexToBytes } from '../../crypto/capsule'
import { downloadEncryptedBlob } from '../../utils/storage'
import { statusBadgeVariant, statusLabel } from '../../components/capsule/CapsuleCard'
import Badge from '../../components/ui/Badge'
import Button from '../../components/ui/Button'
import { Capsule, Beneficiary } from '../../types/api'

// T5 (F6): read-only decrypt-and-render view of a capsule — the foundation
// FR-30's beneficiary preview builds on in Phase 4.
export default function CapsuleView() {
  const navigate = useNavigate()
  const { id } = useParams()

  const [capsule, setCapsule] = useState<Capsule | null>(null)
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const { data: beneficiaries } = useBeneficiaries()

  useEffect(() => {
    if (!id) return
    let cancelled = false

    const load = async () => {
      setLoading(true)
      setError(null)
      try {
        const { data } = await capsulesApi.get(id)
        if (cancelled) return
        setCapsule(data)

        if (data.storage_object_path && data.cipher_iv && !data.content_unrecoverable) {
          const activeCek = await requireCek()
          const { data: contentData } = await capsulesApi.getContent(id)
          const encrypted = await downloadEncryptedBlob(contentData.url)
          const iv = hexToBytes(data.cipher_iv)
          const decrypted = await capsuleEncryption.decrypt(new Uint8Array(encrypted), activeCek, iv)
          if (!cancelled) setMessage(decrypted)
        }
      } catch (err: unknown) {
        if (!cancelled) {
          const msg = err instanceof Error ? err.message : 'Failed to load capsule'
          setError(msg)
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    load()
    return () => { cancelled = true }
  }, [id])

  const beneficiaryName = capsule?.beneficiary_id
    ? beneficiaries?.find((b: Beneficiary) => b.id === capsule.beneficiary_id)?.full_name
    : undefined

  if (loading) {
    return (
      <div className="min-h-screen bg-[#F0F2F5] p-4 flex items-center justify-center">
        <p className="text-[#6B7280]">Loading capsule…</p>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#F0F2F5] p-4">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <div className="flex items-center gap-4 mb-6">
          <button onClick={() => navigate('/vault/capsules')} className="p-2 hover:bg-white rounded-lg transition-colors">
            <ArrowLeft className="w-5 h-5 text-[#0D1117]" />
          </button>
          <div className="flex-1">
            <h1 className="text-2xl font-bold text-[#0D1117]">View Capsule</h1>
            <p className="text-sm text-[#6B7280]">Read-only preview</p>
          </div>
          {id && (
            <Button variant="secondary" onClick={() => navigate(`/vault/capsules/${id}`)}>
              <Edit2 className="w-4 h-4" />
              Edit
            </Button>
          )}
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        {capsule && (
          <>
            {/* Title & status */}
            <div className="bg-white rounded-2xl shadow-md p-6 mb-4">
              <div className="flex items-center gap-3 mb-3">
                <Lock className="w-5 h-5 text-[#3D4F6B] flex-shrink-0" />
                <h2 className="text-lg font-semibold text-[#0D1117]">{capsule.title}</h2>
              </div>
              <div className="flex items-center gap-2 flex-wrap">
                <Badge variant={statusBadgeVariant(capsule.status)}>
                  {statusLabel(capsule.status)}
                </Badge>
                {!capsule.has_recipients && (
                  <Badge variant="warning">No recipient assigned</Badge>
                )}
                {capsule.content_unrecoverable && (
                  <Badge variant="error">Content unrecoverable</Badge>
                )}
              </div>
              {beneficiaryName && (
                <p className="text-sm text-[#6B7280] mt-3">To: {beneficiaryName}</p>
              )}
            </div>

            {/* Decrypted content */}
            <div className="bg-white rounded-2xl shadow-md p-6 mb-4">
              <h2 className="font-semibold text-[#0D1117] mb-4">MESSAGE</h2>
              {capsule.content_unrecoverable ? (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3">
                  <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-red-700">
                    This capsule's content was encrypted with a vault key that no longer exists, following a
                    password reset. It can no longer be decrypted. You can edit this capsule to write new content.
                  </p>
                </div>
              ) : message ? (
                <p className="text-[#0D1117] whitespace-pre-wrap break-words">{message}</p>
              ) : (
                <p className="text-sm text-[#6B7280]">This capsule has no message content yet.</p>
              )}
            </div>

            {/* Attachments */}
            <div className="bg-white rounded-2xl shadow-md p-6 mb-4">
              <h2 className="font-semibold text-[#0D1117] mb-4 flex items-center gap-2">
                <Paperclip className="w-4 h-4" />
                ATTACHMENTS
              </h2>
              <p className="text-sm text-[#6B7280]">No media attachments.</p>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
