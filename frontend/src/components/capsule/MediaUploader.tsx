/**
 * MediaUploader — T1/T2 (Phase 4)
 *
 * Two modes:
 *  • Edit mode  (capsuleId !== null): upload immediately on file selection.
 *  • Create mode (capsuleId === null): queue files; parent uploads them in handleSave.
 *
 * Thumbnail grid shows:
 *  • Confirmed server-side attachments (fetched, decrypted thumb → object URL).
 *  • Pending local files (create mode) — shown as unencrypted local preview.
 *  • Actively uploading files — progress bar.
 */

import { useRef, useState, useEffect } from 'react'
import { Upload, X, Loader2, Film, Image as ImageIcon } from 'lucide-react'
import { capsulesApi } from '../../api/capsules'
import { decryptThumbnail } from '../../crypto/media'
import { uploadSingleMedia } from '../../utils/media-upload'
import type { MediaAttachment } from '../../types/api'

// ── Type limits per PRD ────────────────────────────────────────────────────
const MAX_PHOTOS = 20
const MAX_PHOTO_BYTES = 10 * 1024 * 1024   // 10 MB
const MAX_VIDEO_BYTES = 500 * 1024 * 1024  // 500 MB
const MAX_VIDEOS = 1

interface UploadingEntry {
  key: string
  filename: string
  progress: number
  error: string | null
}

export interface MediaUploaderProps {
  /** Null in create mode — files are queued and returned via onPendingFilesChange. */
  capsuleId: string | null
  cek: CryptoKey | null
  /** Confirmed server-side attachments (from capsule.media_attachments). */
  attachments: MediaAttachment[]
  onAttachmentAdded: (a: MediaAttachment) => void
  onAttachmentDeleted: (id: string) => void
  /** Create-mode queued files. */
  pendingFiles: File[]
  onPendingFilesChange: (files: File[]) => void
}

// ── ThumbnailCell: fetch + decrypt a server-side thumbnail ─────────────────

function ThumbnailCell({
  attachment,
  capsuleId,
  cek,
  onDelete,
}: {
  attachment: MediaAttachment
  capsuleId: string
  cek: CryptoKey
  onDelete: () => void
}) {
  const [src, setSrc] = useState<string | null>(null)
  const [thumbLoading, setThumbLoading] = useState(true)

  useEffect(() => {
    let objectUrl: string | null = null
    let cancelled = false

    ;(async () => {
      if (!attachment.thumbnail_storage_path) { setThumbLoading(false); return }
      try {
        const { data } = await capsulesApi.getMediaUrl(capsuleId, attachment.id)
        if (cancelled || !data.thumb_url) return
        const resp = await fetch(data.thumb_url)
        if (!resp.ok) throw new Error('thumb fetch failed')
        const buf = await resp.arrayBuffer()
        const decrypted = await decryptThumbnail(new Blob([buf]), cek)
        objectUrl = URL.createObjectURL(decrypted)
        if (!cancelled) setSrc(objectUrl)
      } catch {
        // show placeholder
      } finally {
        if (!cancelled) setThumbLoading(false)
      }
    })()

    return () => {
      cancelled = true
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [attachment.id, capsuleId, cek, attachment.thumbnail_storage_path])

  return (
    <div className="relative group">
      <div className="w-full h-24 rounded-lg overflow-hidden bg-gray-100 flex items-center justify-center">
        {thumbLoading ? (
          <Loader2 className="w-5 h-5 text-gray-400 animate-spin" />
        ) : src ? (
          <img src={src} alt={attachment.original_name} className="w-full h-full object-cover" />
        ) : attachment.kind === 'video' ? (
          <Film className="w-8 h-8 text-gray-400" />
        ) : (
          <ImageIcon className="w-8 h-8 text-gray-400" />
        )}
      </div>
      <button
        onClick={(e) => { e.stopPropagation(); onDelete() }}
        className="absolute top-1 right-1 w-5 h-5 bg-red-500 text-white rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
        aria-label="Remove attachment"
      >
        <X className="w-3 h-3" />
      </button>
      <p className="text-xs text-[#6B7280] truncate mt-1">{attachment.original_name}</p>
    </div>
  )
}

// ── PendingFileCell: local preview for create-mode queued files ────────────

function PendingFileCell({
  file,
  onRemove,
}: {
  file: File
  onRemove: () => void
}) {
  const [src] = useState(() =>
    file.type.startsWith('image/') ? URL.createObjectURL(file) : null,
  )

  useEffect(() => {
    return () => { if (src) URL.revokeObjectURL(src) }
  }, [src])

  return (
    <div className="relative group">
      <div className="w-full h-24 rounded-lg overflow-hidden bg-gray-100 flex items-center justify-center">
        {src ? (
          <img src={src} alt={file.name} className="w-full h-full object-cover" />
        ) : (
          <Film className="w-8 h-8 text-gray-400" />
        )}
      </div>
      <button
        onClick={(e) => { e.stopPropagation(); onRemove() }}
        className="absolute top-1 right-1 w-5 h-5 bg-red-500 text-white rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
        aria-label="Remove file"
      >
        <X className="w-3 h-3" />
      </button>
      <p className="text-xs text-[#6B7280] truncate mt-1">{file.name}</p>
    </div>
  )
}

// ── Main component ─────────────────────────────────────────────────────────

export default function MediaUploader({
  capsuleId,
  cek,
  attachments,
  onAttachmentAdded,
  onAttachmentDeleted,
  pendingFiles,
  onPendingFilesChange,
}: MediaUploaderProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragOver, setDragOver] = useState(false)
  const [uploadingEntries, setUploadingEntries] = useState<UploadingEntry[]>([])
  const [validationError, setValidationError] = useState<string | null>(null)

  const existingPhotoCount = attachments.filter(a => a.kind === 'photo').length
  const existingVideoCount = attachments.filter(a => a.kind === 'video').length
  const pendingPhotoCount = pendingFiles.filter(f => f.type.startsWith('image/')).length
  const pendingVideoCount = pendingFiles.filter(f => f.type.startsWith('video/')).length

  /** Validate files against type/size/count limits. Returns valid files + error string. */
  function validateFiles(incoming: File[]): { valid: File[]; error: string | null } {
    const valid: File[] = []
    let error: string | null = null

    const currentPhotos = existingPhotoCount + pendingPhotoCount
    const currentVideos = existingVideoCount + pendingVideoCount
    let addedPhotos = 0
    let addedVideos = 0

    for (const f of incoming) {
      const isVideo = f.type.startsWith('video/')
      const isPhoto = f.type.startsWith('image/')

      if (!isPhoto && !isVideo) {
        error = `"${f.name}" is not a supported file type (JPEG/PNG/HEIC or MP4/MOV)`
        continue
      }
      if (isPhoto) {
        if (f.size > MAX_PHOTO_BYTES) { error = `"${f.name}" exceeds 10 MB photo limit`; continue }
        if (currentPhotos + addedPhotos >= MAX_PHOTOS) { error = `Maximum ${MAX_PHOTOS} photos allowed`; continue }
        addedPhotos++
      }
      if (isVideo) {
        if (f.size > MAX_VIDEO_BYTES) { error = `"${f.name}" exceeds 500 MB video limit`; continue }
        if (currentVideos + addedVideos >= MAX_VIDEOS) { error = 'Only 1 video per capsule is allowed'; continue }
        addedVideos++
      }
      valid.push(f)
    }
    return { valid, error }
  }

  /** In edit mode: immediately upload each valid file. */
  async function uploadImmediately(files: File[]) {
    if (!capsuleId || !cek) return
    for (const file of files) {
      const key = `${file.name}-${file.lastModified}`
      setUploadingEntries(prev => [...prev, { key, filename: file.name, progress: 0, error: null }])
      try {
        const attachment = await uploadSingleMedia(capsuleId, file, cek, (pct) => {
          setUploadingEntries(prev =>
            prev.map(e => (e.key === key ? { ...e, progress: pct } : e)),
          )
        })
        onAttachmentAdded(attachment)
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Upload failed'
        setUploadingEntries(prev =>
          prev.map(e => (e.key === key ? { ...e, error: msg } : e)),
        )
        // Keep errored entry visible for a few seconds then remove
        setTimeout(() => {
          setUploadingEntries(prev => prev.filter(e => e.key !== key))
        }, 4000)
        continue
      }
      setUploadingEntries(prev => prev.filter(e => e.key !== key))
    }
  }

  function handleFiles(incoming: File[]) {
    setValidationError(null)
    const { valid, error } = validateFiles(incoming)
    if (error) setValidationError(error)
    if (!valid.length) return

    if (capsuleId && cek) {
      // Edit mode: upload immediately
      uploadImmediately(valid)
    } else {
      // Create mode: queue
      onPendingFilesChange([...pendingFiles, ...valid])
    }
  }

  function removePending(index: number) {
    onPendingFilesChange(pendingFiles.filter((_, i) => i !== index))
  }

  async function deleteAttachment(id: string) {
    if (!capsuleId) return
    try {
      await capsulesApi.deleteMedia(capsuleId, id)
      onAttachmentDeleted(id)
    } catch {
      // show nothing — attachment stays in list
    }
  }

  const isEmpty =
    attachments.length === 0 && pendingFiles.length === 0 && uploadingEntries.length === 0

  return (
    <div className="space-y-3">
      {/* Drop zone — role="button" so Playwright getByRole('button', { name: /attach/i }) works */}
      <div
        role="button"
        aria-label="Attach photos or files"
        tabIndex={0}
        className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-colors ${
          dragOver ? 'border-[#3D4F6B] bg-blue-50' : 'border-gray-200 hover:border-gray-300'
        }`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => { e.preventDefault(); setDragOver(false); handleFiles(Array.from(e.dataTransfer.files)) }}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); inputRef.current?.click() } }}
      >
        <Upload className="w-8 h-8 text-gray-400 mx-auto mb-2" />
        <p className="text-sm text-[#6B7280]">
          Drag & drop photos/videos or{' '}
          <span className="text-[#3D4F6B] font-medium">browse</span>
        </p>
        <p className="text-xs text-gray-400 mt-1">
          Photos: JPEG/PNG/HEIC up to 10 MB (max {MAX_PHOTOS}). Video: MP4/MOV up to 500 MB (max 1).
        </p>
        <input
          ref={inputRef}
          type="file"
          accept="image/jpeg,image/png,image/heic,video/mp4,video/quicktime"
          multiple
          className="hidden"
          onChange={(e) => { if (e.target.files) handleFiles(Array.from(e.target.files)) }}
        />
      </div>

      {validationError && <p className="text-xs text-red-600">{validationError}</p>}

      {/* Grid: confirmed attachments + uploading + pending */}
      {!isEmpty && (
        <div className="grid grid-cols-3 gap-2">
          {/* Confirmed server-side attachments */}
          {attachments.map(a => (
            capsuleId && cek ? (
              <ThumbnailCell
                key={a.id}
                attachment={a}
                capsuleId={capsuleId}
                cek={cek}
                onDelete={() => deleteAttachment(a.id)}
              />
            ) : null
          ))}

          {/* Uploading entries (edit mode) */}
          {uploadingEntries.map(entry => (
            <div key={entry.key} className="relative">
              <div className="w-full h-24 rounded-lg bg-gray-100 flex flex-col items-center justify-center px-2">
                {entry.error ? (
                  <p className="text-xs text-red-600 text-center">{entry.error}</p>
                ) : (
                  <>
                    <Loader2 className="w-5 h-5 text-[#3D4F6B] animate-spin mb-1" />
                    <div className="w-full bg-gray-200 rounded-full h-1.5">
                      <div
                        className="bg-[#3D4F6B] h-1.5 rounded-full transition-all"
                        style={{ width: `${entry.progress}%` }}
                      />
                    </div>
                    <p className="text-xs text-gray-400 mt-1">{entry.progress}%</p>
                  </>
                )}
              </div>
              <p className="text-xs text-[#6B7280] truncate mt-1">{entry.filename}</p>
            </div>
          ))}

          {/* Pending files (create mode) */}
          {pendingFiles.map((file, i) => (
            <PendingFileCell
              key={`${file.name}-${file.lastModified}`}
              file={file}
              onRemove={() => removePending(i)}
            />
          ))}
        </div>
      )}
    </div>
  )
}
