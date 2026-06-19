export interface User {
  id: string
  email: string
  full_name?: string
  email_verified: boolean
  status: string
  created_at: string
  needs_onboarding: boolean
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
  created_at: string
  updated_at: string
}

export interface CheckinSchedule {
  interval_days: number
  grace_period_days: number
  next_dispatch_at: string | null
  last_confirmed_at: string | null
  snooze_count: number
  snooze_limit: number
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
