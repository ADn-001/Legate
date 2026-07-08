export interface User {
  id: string
  email: string
  full_name?: string
  email_verified: boolean
  status: 'active' | 'suspended' | 'memorialized' | 'pending_deletion' | 'deleted'
  created_at: string
  needs_onboarding: boolean
}

export type MediaKind = 'photo' | 'video'
export type MediaStatus = 'uploading' | 'ready' | 'failed' | 'deleted'

export interface MediaAttachment {
  id: string
  kind: MediaKind
  status: MediaStatus
  original_name: string
  mime_type: string
  size_bytes: number
  thumbnail_storage_path: string | null
  cipher_iv: string  // hex for photos; JSON string for chunked video
  created_at: string
}

export interface Capsule {
  id: string
  user_id: string
  title: string
  beneficiary_id: string | null
  cipher_iv: string
  storage_object_path: string | null
  status: 'draft' | 'active' | 'pending_deletion' | 'deleted' | 'delivered'
  delivery_order: number
  has_recipients: boolean
  content_unrecoverable: boolean
  content_size_bytes: number | null
  media_attachments: MediaAttachment[]
  created_at: string
  updated_at: string
}

export interface Beneficiary {
  id: string
  user_id: string
  full_name: string
  email: string
  relationship?: string
  is_emergency_contact: boolean
  status: 'active' | 'pending' | 'removed'
  /** NULL ⇒ added silently (no notification email was sent) */
  invited_at: string | null
  created_at: string
  updated_at: string
}

export interface CheckinSchedule {
  interval_days: number
  grace_period_days: number
  // Phase B: demo-mode overrides. Non-null means "this cycle is running on
  // minutes, not days" — takes precedence over the day fields above.
  check_interval_minutes: number | null
  grace_period_minutes: number | null
  // Phase B (extension): demo-mode override for the FR-23 emergency-contact
  // 48h confirmation window.
  emergency_confirm_minutes: number | null
  next_dispatch_at: string | null
  last_dispatched_at: string | null
  last_confirmed_at: string | null
  snooze_count: number
  snooze_limit: number
  // Whether the server has DEMO_MODE enabled at all.
  demo_mode?: boolean
}

export interface StorageUsage {
  total_bytes: number
  limit_bytes: number
  by_capsule: { capsule_id: string; title: string; bytes: number }[]
}

export interface ActivityEntry {
  id: string
  event_type: string
  resource_type: string | null
  resource_id: string | null
  description: string | null
  created_at: string
}
