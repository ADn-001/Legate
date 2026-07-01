/**
 * DeliveryPreviewModal — T3/FR-30 (Phase 4)
 *
 * Fetches the delivery email template from GET /delivery/template,
 * fills in placeholders client-side with the current (decrypted) capsule
 * content, and renders it in a sandboxed iframe with a "PREVIEW" banner.
 *
 * Placeholder substitution:
 *   {{CAPSULE_TITLE}} → HTML-escaped title
 *   {{CAPSULE_BODY}}  → rich HTML (tiptap) passed through as-is, or plain
 *                       text with newlines → <br>
 *   {{MEDIA_HTML}}    → attachment count summary (thumbnails are encrypted,
 *                       so we can't inline them in the preview)
 *   {{SENDER_NAME}}   → HTML-escaped sender name
 */

import { useEffect, useState } from 'react'
import { X, Loader2, AlertTriangle } from 'lucide-react'
import { deliveryApi } from '../../api/delivery'
import type { MediaAttachment } from '../../types/api'

interface Props {
  isOpen: boolean
  onClose: () => void
  title: string
  message: string
  senderName: string
  attachments: MediaAttachment[]
  pendingFiles: File[]
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function buildBodyHtml(message: string): string {
  const trimmed = message.trim()
  if (!trimmed) return '<p><em>(no message)</em></p>'
  // tiptap output starts with HTML tags; plain text doesn't
  if (trimmed.startsWith('<')) return trimmed
  return escapeHtml(trimmed).replace(/\n/g, '<br>')
}

function buildMediaHtml(attachments: MediaAttachment[], pendingFiles: File[]): string {
  const confirmed = attachments.filter(a => a.status === 'ready')
  const pending = pendingFiles.length
  const total = confirmed.length + pending
  if (total === 0) return ''
  const parts: string[] = ['<div class="media">']
  if (confirmed.length > 0) {
    parts.push(`<p>📎 ${confirmed.length} encrypted attachment${confirmed.length > 1 ? 's' : ''} — accessible once delivered to beneficiary</p>`)
  }
  if (pending > 0) {
    parts.push(`<p>📎 ${pending} pending upload${pending > 1 ? 's' : ''}</p>`)
  }
  parts.push('</div>')
  return parts.join('')
}

function fillTemplate(
  template: string,
  title: string,
  message: string,
  senderName: string,
  attachments: MediaAttachment[],
  pendingFiles: File[],
): string {
  return template
    .replace(/\{\{CAPSULE_TITLE\}\}/g, escapeHtml(title || 'Untitled'))
    .replace(/\{\{CAPSULE_BODY\}\}/g, buildBodyHtml(message))
    .replace(/\{\{MEDIA_HTML\}\}/g, buildMediaHtml(attachments, pendingFiles))
    .replace(/\{\{SENDER_NAME\}\}/g, escapeHtml(senderName || 'Your contact'))
}

export default function DeliveryPreviewModal({
  isOpen, onClose, title, message, senderName, attachments, pendingFiles,
}: Props) {
  const [templateHtml, setTemplateHtml] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!isOpen) return
    setLoading(true)
    setError(null)
    deliveryApi.getTemplate()
      .then(res => setTemplateHtml(String(res.data)))
      .catch(() => setError('Could not load preview template. Please try again.'))
      .finally(() => setLoading(false))
  }, [isOpen])

  useEffect(() => {
    if (!isOpen) return
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [isOpen, onClose])

  if (!isOpen) return null

  const filled = templateHtml
    ? fillTemplate(templateHtml, title, message, senderName, attachments, pendingFiles)
    : null

  return (
    <div
      className="fixed inset-0 bg-black/60 z-50 flex flex-col"
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      {/* Preview banner */}
      <div className="flex items-center justify-between px-6 py-3 bg-amber-500 text-white flex-shrink-0">
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-4 h-4" />
          <span className="font-semibold text-sm">DELIVERY PREVIEW — this is how your email will appear to the beneficiary</span>
        </div>
        <button onClick={onClose} className="p-1 hover:bg-amber-600 rounded transition-colors" aria-label="Close preview">
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Preview body */}
      <div className="flex-1 overflow-hidden">
        {loading && (
          <div className="h-full flex items-center justify-center bg-white">
            <Loader2 className="w-8 h-8 text-[#3D4F6B] animate-spin" />
          </div>
        )}
        {error && (
          <div className="h-full flex items-center justify-center bg-white">
            <p className="text-red-600 text-sm">{error}</p>
          </div>
        )}
        {filled && !loading && (
          <iframe
            srcDoc={filled}
            className="w-full h-full border-0"
            title="Delivery preview"
            sandbox="allow-same-origin"
          />
        )}
      </div>
    </div>
  )
}
