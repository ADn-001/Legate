import { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, AlertTriangle, Bold, Italic, List, Eye } from 'lucide-react'
import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import CharacterCount from '@tiptap/extension-character-count'
import { capsulesApi } from '../../api/capsules'
import { useBeneficiaries } from '../../hooks/useBeneficiaries'
import { useAuthStore } from '../../store/auth'
import { useCryptoStore } from '../../store/crypto'
import { requireCek } from '../../store/unlock'
import { capsuleEncryption, bytesToHex, hexToBytes } from '../../crypto/capsule'
import { toBase64, fromBase64 } from '../../crypto/keys'
import { uploadEncryptedBlob, downloadEncryptedBlob } from '../../utils/storage'
import { uploadSingleMedia } from '../../utils/media-upload'
import MediaUploader from '../../components/capsule/MediaUploader'
import DeliveryPreviewModal from '../../components/capsule/DeliveryPreviewModal'
import type { MediaAttachment } from '../../types/api'
import SecurityBanner from '../../components/ui/SecurityBanner'
import Button from '../../components/ui/Button'

const MAX_CHARS = 10000

type AutoSaveStatus = 'saved' | 'saving' | 'unsaved'

interface DraftContent {
  title: string
  message: string
  beneficiaryId: string
}

// T9 (F10): drafts are encrypted at rest with the CEK before being written to
// localStorage. The on-disk shape is `{ iv: hex, data: base64 }` — opaque
// without the CEK.
async function encryptDraft(draft: DraftContent, cek: CryptoKey): Promise<string> {
  const { ciphertext, iv } = await capsuleEncryption.encrypt(JSON.stringify(draft), cek)
  return JSON.stringify({ iv: bytesToHex(iv), data: toBase64(ciphertext) })
}

async function decryptDraft(raw: string, cek: CryptoKey): Promise<DraftContent | null> {
  try {
    const { iv, data } = JSON.parse(raw)
    if (!iv || !data) return null
    const json = await capsuleEncryption.decrypt(fromBase64(data), cek, hexToBytes(iv))
    const parsed = JSON.parse(json)
    return {
      title: parsed.title || '',
      message: parsed.message || '',
      beneficiaryId: parsed.beneficiaryId || '',
    }
  } catch {
    return null
  }
}

export default function CapsuleEditor() {
  const navigate = useNavigate()
  const { id } = useParams()
  const isEdit = !!id
  const queryClient = useQueryClient()

  const [title, setTitle] = useState('')
  const [message, setMessage] = useState('')
  const [beneficiaryId, setBeneficiaryId] = useState('')
  const [pendingFiles, setPendingFiles] = useState<File[]>([])
  const [showPreview, setShowPreview] = useState(false)
  // Ref holds content that arrives before the tiptap editor is mounted
  const pendingContentRef = useRef<string | null>(null)
  const [attachments, setAttachments] = useState<MediaAttachment[]>([])
  const [saving, setSaving] = useState(false)
  const [loading, setLoading] = useState(isEdit)
  const [autoSaveStatus, setAutoSaveStatus] = useState<AutoSaveStatus>('unsaved')
  const [error, setError] = useState<string | null>(null)
  const [contentUnrecoverable, setContentUnrecoverable] = useState(false)

  const user = useAuthStore(s => s.user)
  const cek = useCryptoStore(s => s.cek)
  const locked = useCryptoStore(s => s.locked)
  const { data: beneficiaries } = useBeneficiaries()

  // T9/Phase 4: tiptap rich-text editor (StarterKit + CharacterCount)
  // onUpdate keeps `message` state in sync. onCreate applies any content
  // that arrived via setEditorContent before the editor was mounted.
  const editor = useEditor({
    extensions: [
      StarterKit,
      CharacterCount.configure({ limit: MAX_CHARS }),
    ],
    content: '',
    onUpdate: ({ editor }) => {
      setMessage(editor.getHTML())
    },
    onCreate: ({ editor }) => {
      if (pendingContentRef.current !== null) {
        editor.commands.setContent(pendingContentRef.current, false)
        pendingContentRef.current = null
      }
    },
  })

  /** Set editor content from async data loads. If the editor isn't ready yet,
   *  store in pendingContentRef for the onCreate callback. */
  const setEditorContent = useCallback((content: string) => {
    setMessage(content)
    if (editor) {
      editor.commands.setContent(content, false)
    } else {
      pendingContentRef.current = content
    }
  }, [editor])

  // T9 (F10): tracks the last persisted {title, message, beneficiaryId} so
  // the "saved"/"unsaved" indicator reflects real dirty state, not a timer.
  const savedSnapshotRef = useRef<DraftContent>({ title: '', message: '', beneficiaryId: '' })
  const draftRef = useRef<DraftContent>({ title: '', message: '', beneficiaryId: '' })

  // Load draft on mount — only for new capsules. Edit mode loads its content
  // from the server (T5/F5) so a stale local draft can't shadow saved content.
  // The draft is encrypted with the CEK, so an unlock prompt may appear.
  useEffect(() => {
    if (isEdit) return
    const draftKey = `draft_capsule_${id || 'new'}`
    const raw = localStorage.getItem(draftKey)
    if (!raw) return

    ;(async () => {
      try {
        const activeCek = await requireCek()
        const draft = await decryptDraft(raw, activeCek)
        if (draft) {
          setTitle(draft.title)
          setEditorContent(draft.message)
          setBeneficiaryId(draft.beneficiaryId)
          savedSnapshotRef.current = draft
        }
      } catch {
        // user declined to unlock, or the draft is corrupt — start blank
      }
    })()
  }, [id, isEdit])

  // T5 (F5): edit mode — fetch the capsule, download the encrypted content
  // blob via a short-lived signed URL, and decrypt it with the CEK
  // (prompting the unlock modal if the vault is locked).
  useEffect(() => {
    if (!isEdit || !id) return
    let cancelled = false

    const load = async () => {
      setLoading(true)
      setError(null)
      try {
        const { data: capsule } = await capsulesApi.get(id)
        if (cancelled) return
        const loadedTitle = capsule.title || ''
        const loadedBeneficiaryId = capsule.beneficiary_id || ''
        let loadedMessage = ''
        setTitle(loadedTitle)
        setBeneficiaryId(loadedBeneficiaryId)
        setContentUnrecoverable(!!capsule.content_unrecoverable)
        setAttachments(capsule.media_attachments || [])

        if (capsule.storage_object_path && capsule.cipher_iv && !capsule.content_unrecoverable) {
          const activeCek = await requireCek()
          const { data: contentData } = await capsulesApi.getContent(id)
          const encrypted = await downloadEncryptedBlob(contentData.url)
          const iv = hexToBytes(capsule.cipher_iv)
          loadedMessage = await capsuleEncryption.decrypt(new Uint8Array(encrypted), activeCek, iv)
          if (!cancelled) setEditorContent(loadedMessage)
        }

        if (!cancelled) {
          savedSnapshotRef.current = { title: loadedTitle, message: loadedMessage, beneficiaryId: loadedBeneficiaryId }
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
  }, [id, isEdit])

  // Set first beneficiary as default
  useEffect(() => {
    if (beneficiaries?.length > 0 && !beneficiaryId) {
      setBeneficiaryId(beneficiaries[0].id)
    }
  }, [beneficiaries])

  // Keep a ref to the latest editor content for the autosave/unlock effects below.
  useEffect(() => {
    draftRef.current = { title, message, beneficiaryId }
  }, [title, message, beneficiaryId])

  // T9 (F10): the indicator reflects real dirty state — 'unsaved' as soon as
  // content diverges from the last persisted snapshot, 'saved' once it
  // matches again. No timer-driven flicker.
  useEffect(() => {
    const snap = savedSnapshotRef.current
    const isDirty = title !== snap.title || message !== snap.message || beneficiaryId !== snap.beneficiaryId
    setAutoSaveStatus(prev => (isDirty ? 'unsaved' : prev === 'saving' ? prev : 'saved'))
  }, [title, message, beneficiaryId])

  // Encrypt and persist the draft if it's dirty and the vault is unlocked.
  // No-op otherwise — the in-memory editor state is the buffer until the CEK
  // becomes available.
  const persistDraft = useCallback(async () => {
    if (!cek || locked) return
    const current = draftRef.current
    const snap = savedSnapshotRef.current
    const isDirty = current.title !== snap.title || current.message !== snap.message || current.beneficiaryId !== snap.beneficiaryId
    if (!isDirty) return

    setAutoSaveStatus('saving')
    try {
      const encrypted = await encryptDraft(current, cek)
      localStorage.setItem(`draft_capsule_${id || 'new'}`, encrypted)
      savedSnapshotRef.current = current
      setAutoSaveStatus('saved')
    } catch {
      setAutoSaveStatus('unsaved')
    }
  }, [cek, locked, id])

  // Auto-save every 30s while dirty.
  useEffect(() => {
    const timer = setInterval(persistDraft, 30000)
    return () => clearInterval(timer)
  }, [persistDraft])

  // Persist immediately once the vault unlocks (CEK becomes available).
  useEffect(() => {
    persistDraft()
  }, [persistDraft])

  const handleSave = async () => {
    if (!title.trim()) { setError('Capsule title is required'); return }
    if (!beneficiaryId) { setError('Please select a beneficiary'); return }

    setSaving(true)
    setError(null)
    try {
      const activeCek = await requireCek()
      const { ciphertext, iv } = await capsuleEncryption.encrypt(message, activeCek)
      const cipherIvHex = bytesToHex(iv)

      let newCapsuleId: string | null = null

      if (isEdit && id) {
        // T5 (F5): re-encrypt and upload via the backend (server-side PUT to
        // Supabase Storage), then PATCH the capsule — never create a duplicate.
        // Using uploadContent (PUT /capsules/{id}/content) avoids the
        // browser→Supabase signed-URL PUT which can stall on the edit path.
        const { data: uploadData } = await capsulesApi.uploadContent(id, ciphertext)
        await capsulesApi.update(id, {
          title,
          beneficiary_id: beneficiaryId,
          storage_object_path: uploadData.storage_object_path,
          cipher_iv: cipherIvHex,
          content_size_bytes: ciphertext.byteLength,
        })
      } else {
        const { data } = await capsulesApi.create({
          title,
          beneficiary_id: beneficiaryId,
          cipher_iv: cipherIvHex,
        })
        const { id: createdId, upload_url } = data
        newCapsuleId = String(createdId)

        await uploadEncryptedBlob(upload_url, new Blob([ciphertext]))
        await capsulesApi.update(createdId, {
          storage_object_path: `${user!.id}/${createdId}/content.enc`,
          content_size_bytes: ciphertext.byteLength,
        })
      }

      // Upload pending media files (create mode only; edit mode uploads immediately via MediaUploader)
      if (!isEdit && newCapsuleId && pendingFiles.length > 0) {
        for (const file of pendingFiles) {
          try {
            const attachment = await uploadSingleMedia(newCapsuleId, file, activeCek)
            setAttachments(prev => [...prev, attachment])
          } catch {
            // Non-blocking: capsule is saved; individual media failure doesn't abort navigation
          }
        }
      }

      localStorage.removeItem(`draft_capsule_${id || 'new'}`)
      // Invalidate the capsules cache so CapsuleList immediately fetches fresh
      // data rather than showing the stale [] from Dashboard's initial load.
      await queryClient.invalidateQueries({ queryKey: ['capsules'] })
      navigate('/vault/capsules')
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to save capsule'
      setError(msg)
    } finally {
      setSaving(false)
    }
  }

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
          {contentUnrecoverable && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4 flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-red-700">
                The previous content of this capsule was encrypted with a vault key that no longer exists,
                following a password reset, and could not be loaded. Write new content below and save to
                replace it.
              </p>
            </div>
          )}
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-[#0D1117]">CONTENT</h2>
            <div className="flex items-center gap-3">
              <span className={`text-xs ${autoSaveStatus === 'saved' ? 'text-green-600' : 'text-gray-400'}`}>
                {autoSaveStatus === 'saved' ? '✓ Draft saved' : autoSaveStatus === 'saving' ? 'Saving...' : ''}
              </span>
              <button
                onClick={() => setShowPreview(true)}
                className="flex items-center gap-1 text-xs text-[#3D4F6B] hover:text-[#2a3851] font-medium"
              >
                <Eye className="w-3.5 h-3.5" />
                Preview
              </button>
            </div>
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
              {/* T9/Phase 4: tiptap rich text editor */}
              <div className="border border-gray-200 rounded-xl overflow-hidden focus-within:border-[#3D4F6B] transition-colors">
                {/* Toolbar */}
                <div className="flex gap-1 p-2 border-b border-gray-100 bg-gray-50">
                  <button
                    type="button"
                    onClick={() => editor?.chain().focus().toggleBold().run()}
                    className={`p-1.5 rounded text-sm transition-colors ${editor?.isActive('bold') ? 'bg-[#3D4F6B] text-white' : 'text-gray-600 hover:bg-gray-200'}`}
                    title="Bold"
                    aria-label="Bold"
                  >
                    <Bold className="w-4 h-4" />
                  </button>
                  <button
                    type="button"
                    onClick={() => editor?.chain().focus().toggleItalic().run()}
                    className={`p-1.5 rounded text-sm transition-colors ${editor?.isActive('italic') ? 'bg-[#3D4F6B] text-white' : 'text-gray-600 hover:bg-gray-200'}`}
                    title="Italic"
                    aria-label="Italic"
                  >
                    <Italic className="w-4 h-4" />
                  </button>
                  <button
                    type="button"
                    onClick={() => editor?.chain().focus().toggleBulletList().run()}
                    className={`p-1.5 rounded text-sm transition-colors ${editor?.isActive('bulletList') ? 'bg-[#3D4F6B] text-white' : 'text-gray-600 hover:bg-gray-200'}`}
                    title="Bullet list"
                    aria-label="Bullet list"
                  >
                    <List className="w-4 h-4" />
                  </button>
                </div>
                <EditorContent
                  editor={editor}
                  className="prose prose-sm max-w-none p-3 min-h-[200px] text-[#0D1117] focus:outline-none [&_.ProseMirror]:outline-none [&_.ProseMirror]:min-h-[200px] [&_.ProseMirror_p.is-editor-empty:first-child::before]:content-['Write_your_message_here...'] [&_.ProseMirror_p.is-editor-empty:first-child::before]:text-gray-400 [&_.ProseMirror_p.is-editor-empty:first-child::before]:float-left [&_.ProseMirror_p.is-editor-empty:first-child::before]:pointer-events-none"
                />
              </div>
              <p className="text-xs text-[#6B7280] text-right mt-1">
                {editor?.storage.characterCount?.characters() ?? 0}/{MAX_CHARS}
              </p>
            </div>
          </div>
        </div>

        {/* Media Section */}
        <div className="bg-white rounded-2xl shadow-md p-6 mb-4">
          <h2 className="font-semibold text-[#0D1117] mb-4">MEDIA ATTACHMENTS</h2>
          <MediaUploader
            capsuleId={isEdit && id ? id : null}
            cek={cek}
            attachments={attachments}
            onAttachmentAdded={(a) => setAttachments(prev => [...prev, a])}
            onAttachmentDeleted={(aid) => setAttachments(prev => prev.filter(a => a.id !== aid))}
            pendingFiles={pendingFiles}
            onPendingFilesChange={setPendingFiles}
          />
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

      {/* T3: Delivery preview modal */}
      <DeliveryPreviewModal
        isOpen={showPreview}
        onClose={() => setShowPreview(false)}
        title={title}
        message={message}
        senderName={user?.full_name || user?.email || ''}
        attachments={attachments}
        pendingFiles={pendingFiles}
      />
    </div>
  )
}
