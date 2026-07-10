# Legate Database Models v2.0

Revised to reflect simplified architecture: Supabase PostgreSQL + Supabase Storage, single encryption key model, no shard/node/seeder tables, no subscription tiers.

---

## 1. High-Level Domain Entities

- `users`
- `user_settings`
- `beneficiaries`
- `capsules`
- `capsule_recipients`
- `media_attachments`
- `checkin_schedules`
- `checkin_events`
- `release_triggers`
- `delivery_events`
- `audit_logs`

Removed from v1.0: `subscription_plans`, `nodes`, `shards`, `key_shares` (SSS), `device_sessions` (simplified).

---

## 2. Table Definitions

### 2.1 `users`
| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID, PK | Default `gen_random_uuid()` |
| `email` | VARCHAR(255), UNIQUE | Indexed |
| `password_hash` | VARCHAR(255) | bcrypt |
| `email_verified` | BOOLEAN | Default false |
| `phone` | VARCHAR(32) | Optional |
| `full_name` | VARCHAR(255) | Optional |
| `status` | ENUM(`active`, `suspended`, `memorialized`, `deleted`) | |
| `erasure_requested_at` | TIMESTAMPTZ | GDPR erasure tracking |
| `created_at` | TIMESTAMPTZ | Default now() |
| `updated_at` | TIMESTAMPTZ | |
| `last_login_at` | TIMESTAMPTZ | |

---

### 2.2 `user_settings`
| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID, PK | |
| `user_id` | UUID, FK → users.id | ON DELETE CASCADE |
| `check_in_interval_days` | INTEGER | One of [7, 14, 30, 60] or custom |
| `grace_period_days` | INTEGER | One of [3, 7, 14, 30] |
| `snooze_count_remaining` | INTEGER | Default 2 |
| `preferred_language` | VARCHAR(8) | Default 'en' |
| `needs_onboarding` | BOOLEAN | Default true |
| `last_check_in_at` | TIMESTAMPTZ | |
| `next_check_in_at` | TIMESTAMPTZ | |

---

### 2.3 `encryption_keys`
Stores the user's encrypted Content Encryption Key (CEK). The server never holds the raw CEK — only the encrypted blob and the PBKDF2 derivation parameters needed to re-derive the wrapping key at delivery time.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID, PK | |
| `user_id` | UUID, FK → users.id | ON DELETE CASCADE, UNIQUE |
| `encrypted_cek` | BYTEA | AES-256-GCM encrypted CEK |
| `cek_iv` | BYTEA | IV used to encrypt CEK |
| `pbkdf2_salt` | BYTEA | Random 16-byte salt |
| `pbkdf2_iterations` | INTEGER | Default 100000 |
| `recovery_phrase_hash` | VARCHAR(255) | SHA-256 hash of BIP-39 phrase (for verification only) |
| `created_at` | TIMESTAMPTZ | |
| `updated_at` | TIMESTAMPTZ | |

---

### 2.4 `beneficiaries`
| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID, PK | |
| `user_id` | UUID, FK → users.id | ON DELETE CASCADE |
| `full_name` | VARCHAR(255) | Required |
| `email` | VARCHAR(255) | Required, validated |
| `relationship` | VARCHAR(64) | Optional (e.g. spouse, child, friend) |
| `is_emergency_contact` | BOOLEAN | Default false |
| `status` | ENUM(`active`, `pending`, `removed`) | |
| `invited_at` | TIMESTAMPTZ | |
| `removed_at` | TIMESTAMPTZ | |
| `updated_at` | TIMESTAMPTZ | |

**Constraints:** UNIQUE on `(user_id, email)`.

---

### 2.5 `capsules`
Capsule metadata only — plaintext content never stored in the database.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID, PK | |
| `user_id` | UUID, FK → users.id | ON DELETE CASCADE |
| `title` | VARCHAR(255) | Plaintext — metadata only |
| `status` | ENUM(`draft`, `active`, `pending_deletion`, `deleted`, `delivered`) | |
| `storage_object_path` | TEXT | Supabase Storage path to encrypted content blob |
| `cipher_iv` | BYTEA | IV used for content encryption |
| `content_hash` | VARCHAR(64) | SHA-256 of plaintext (for integrity check, stored encrypted) |
| `scheduled_delivery_date` | DATE | Optional — time-capsule feature (P2) |
| `delivery_order` | INTEGER | Order within a beneficiary's capsule list |
| `auto_saved_at` | TIMESTAMPTZ | |
| `created_at` | TIMESTAMPTZ | |
| `updated_at` | TIMESTAMPTZ | |

---

### 2.6 `capsule_recipients`
| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID, PK | |
| `capsule_id` | UUID, FK → capsules.id | ON DELETE CASCADE |
| `beneficiary_id` | UUID, FK → beneficiaries.id | ON DELETE RESTRICT |
| `is_primary` | BOOLEAN | |
| `delivered_at` | TIMESTAMPTZ | |
| `status` | ENUM(`pending`, `queued`, `sent`, `failed`) | |

---

### 2.7 `media_attachments`
| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID, PK | |
| `capsule_id` | UUID, FK → capsules.id | ON DELETE CASCADE |
| `type` | ENUM(`photo`, `video`) | |
| `original_name` | VARCHAR(255) | |
| `mime_type` | VARCHAR(64) | |
| `size_bytes` | BIGINT | |
| `storage_object_path` | TEXT | Supabase Storage path to encrypted file |
| `cipher_iv` | BYTEA | IV for this file's encryption |
| `thumbnail_storage_path` | TEXT | Supabase Storage path to thumbnail (unencrypted thumbnail OK) |
| `video_duration_seconds` | INTEGER | Nullable |
| `status` | ENUM(`uploading`, `ready`, `failed`, `deleted`) | |
| `created_at` | TIMESTAMPTZ | |

---

### 2.8 `checkin_schedules`
| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID, PK | |
| `user_id` | UUID, FK → users.id | ON DELETE CASCADE, UNIQUE |
| `interval_days` | INTEGER | |
| `grace_period_days` | INTEGER | |
| `next_dispatch_at` | TIMESTAMPTZ | When next check-in email should fire |
| `last_dispatched_at` | TIMESTAMPTZ | |
| `last_confirmed_at` | TIMESTAMPTZ | |
| `snooze_count` | INTEGER | Default 0 |
| `snooze_limit` | INTEGER | Default 2 |
| `is_paused` | BOOLEAN | Emergency contact pause flag |
| `pause_count` | INTEGER | Default 0, max 2 |
| `created_at` | TIMESTAMPTZ | |
| `updated_at` | TIMESTAMPTZ | |

---

### 2.9 `checkin_events`
One row per dispatched check-in email.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID, PK | |
| `user_id` | UUID, FK → users.id | ON DELETE CASCADE |
| `schedule_id` | UUID, FK → checkin_schedules.id | |
| `token` | VARCHAR(128), UNIQUE | Cryptographically random |
| `token_type` | ENUM(`confirm`, `snooze_7`, `snooze_14`, `snooze_30`, `emergency_pause`) | |
| `expires_at` | TIMESTAMPTZ | 7 days after dispatch |
| `used_at` | TIMESTAMPTZ | |
| `status` | ENUM(`pending`, `used`, `expired`) | |
| `sent_at` | TIMESTAMPTZ | |
| `click_ip` | INET | Audit only |
| `click_user_agent` | TEXT | Audit only |

---

### 2.10 `release_triggers`
| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID, PK | |
| `user_id` | UUID, FK → users.id | ON DELETE RESTRICT |
| `triggered_at` | TIMESTAMPTZ | |
| `reason` | ENUM(`checkin_missed`, `emergency_pause_timeout`, `manual`) | |
| `verification_state` | ENUM(`pending`, `confirmed`, `cancelled`) | |
| `status` | ENUM(`processing`, `completed`, `failed`) | |
| `pause_count` | INTEGER | Emergency pauses used |
| `meta` | JSONB | Additional context |

---

### 2.11 `delivery_events`
| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID, PK | |
| `release_trigger_id` | UUID, FK → release_triggers.id | |
| `capsule_recipient_id` | UUID, FK → capsule_recipients.id | |
| `sent_at` | TIMESTAMPTZ | |
| `delivery_status` | ENUM(`pending`, `sent`, `bounced`, `failed`, `opened`) | |
| `resend_message_id` | VARCHAR(255) | Resend API message ID for tracking |
| `attempts` | INTEGER | Default 0 |
| `last_attempt_at` | TIMESTAMPTZ | |
| `error_detail` | TEXT | |

---

### 2.12 `audit_logs`
Append-only. No deletes or updates.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID, PK | |
| `user_id` | UUID, FK → users.id, NULLABLE | Null for system events |
| `actor_id` | UUID, NULLABLE | For admin-initiated actions |
| `event_type` | VARCHAR(64) | See event type registry below |
| `resource_type` | VARCHAR(64) | e.g. 'capsule', 'beneficiary' |
| `resource_id` | UUID, NULLABLE | |
| `description` | TEXT | |
| `ip_address` | INET | |
| `created_at` | TIMESTAMPTZ | |
| `meta` | JSONB | |

**Event type registry:**
`login`, `logout`, `signup`, `email_verified`, `password_reset`, `capsule_created`, `capsule_updated`, `capsule_deleted`, `beneficiary_added`, `beneficiary_updated`, `beneficiary_removed`, `checkin_sent`, `checkin_confirmed`, `checkin_snoozed`, `checkin_expired`, `trigger_created`, `trigger_cancelled`, `delivery_sent`, `delivery_failed`, `account_deleted`, `key_accessed`

---

## 3. Supabase Storage Buckets

| Bucket | Contents | Access Policy |
|--------|----------|--------------|
| `capsule-content` | Encrypted content blobs (.enc files) | Private — authenticated user only via RLS |
| `media-attachments` | Encrypted photo and video files | Private — authenticated user only via RLS |
| `thumbnails` | Video thumbnails (not encrypted) | Private — authenticated user only |

All storage object paths follow the pattern: `{user_id}/{capsule_id}/{filename}`

---

## 4. Row Level Security (RLS) Policies

All tables enforce Supabase RLS. Key policies:

- `users`: Users can SELECT/UPDATE their own row only. No direct DELETE (handled by API).
- `user_settings`, `encryption_keys`, `checkin_schedules`: Users can SELECT/UPDATE their own row. INSERT on signup via service role only.
- `beneficiaries`, `capsules`, `media_attachments`: Users can SELECT/INSERT/UPDATE/DELETE rows where `user_id = auth.uid()`.
- `checkin_events`: Users can SELECT their own events. INSERT/UPDATE via service role (Celery worker) only.
- `release_triggers`, `delivery_events`: Read-only for users. Write via service role only.
- `audit_logs`: SELECT only for own rows. INSERT via service role only. No UPDATE or DELETE ever.

---

## 5. Indexes

```sql
CREATE UNIQUE INDEX idx_users_email ON users(email);
CREATE UNIQUE INDEX idx_user_settings_user ON user_settings(user_id);
CREATE UNIQUE INDEX idx_encryption_keys_user ON encryption_keys(user_id);
CREATE UNIQUE INDEX idx_checkin_schedules_user ON checkin_schedules(user_id);
CREATE UNIQUE INDEX idx_beneficiaries_user_email ON beneficiaries(user_id, email);
CREATE INDEX idx_capsules_user ON capsules(user_id);
CREATE INDEX idx_capsules_status ON capsules(status);
CREATE INDEX idx_checkin_events_token ON checkin_events(token);
CREATE INDEX idx_checkin_events_schedule ON checkin_events(schedule_id);
CREATE INDEX idx_checkin_schedules_next_dispatch ON checkin_schedules(next_dispatch_at);
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id, created_at DESC);
CREATE INDEX idx_delivery_events_trigger ON delivery_events(release_trigger_id);
```

---

## 6. GDPR & Privacy Notes

- `users.erasure_requested_at` tracks the timestamp of a right-to-erasure request.
- On deletion: `users.status` set to `deleted`, cascade purges all associated rows in user-owned tables.
- Supabase Storage objects under `{user_id}/` prefix purged asynchronously within 72 hours via Celery task.
- `audit_logs` rows for the user are anonymised (user_id set to null, description redacted) rather than deleted — required for security audit trail integrity.
- `checkin_events.click_ip` and `click_user_agent` are audit fields — included in data access responses under GDPR right of access.

---

## 7. Optional Future Tables

- `legal_acceptance` — (user_id, tos_version, accepted_at) — for versioned ToS acceptance tracking
- `password_reset_tokens` — if moving away from Supabase Auth magic links
- `push_tokens` — (user_id, platform, token, created_at) — for Capacitor push notifications
- `scheduled_capsules` — for P2 time-capsule feature (date-triggered delivery independent of death trigger)
