-- Legate RLS Policies
-- Run these in the Supabase SQL editor (Dashboard → SQL Editor).
-- The backend uses the service_role key which bypasses RLS — these
-- policies protect direct client-side access only.

-- ============================================================
-- Enable RLS on all tables
-- ============================================================
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE encryption_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE beneficiaries ENABLE ROW LEVEL SECURITY;
ALTER TABLE capsules ENABLE ROW LEVEL SECURITY;
ALTER TABLE capsule_recipients ENABLE ROW LEVEL SECURITY;
ALTER TABLE media_attachments ENABLE ROW LEVEL SECURITY;
ALTER TABLE checkin_schedules ENABLE ROW LEVEL SECURITY;
ALTER TABLE checkin_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE release_triggers ENABLE ROW LEVEL SECURITY;
ALTER TABLE delivery_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

-- ============================================================
-- users: own row only (matched by supabase_uid)
-- ============================================================
CREATE POLICY "users_select_own" ON users
    FOR SELECT USING (supabase_uid = auth.uid()::text);

CREATE POLICY "users_update_own" ON users
    FOR UPDATE USING (supabase_uid = auth.uid()::text);

-- ============================================================
-- user_settings: own row
-- ============================================================
CREATE POLICY "user_settings_own" ON user_settings
    FOR ALL USING (
        user_id IN (SELECT id FROM users WHERE supabase_uid = auth.uid()::text)
    );

-- ============================================================
-- encryption_keys: own row (never expose raw bytes to client)
-- ============================================================
CREATE POLICY "encryption_keys_own" ON encryption_keys
    FOR ALL USING (
        user_id IN (SELECT id FROM users WHERE supabase_uid = auth.uid()::text)
    );

-- ============================================================
-- beneficiaries: own rows
-- ============================================================
CREATE POLICY "beneficiaries_own" ON beneficiaries
    FOR ALL USING (
        user_id IN (SELECT id FROM users WHERE supabase_uid = auth.uid()::text)
    );

-- ============================================================
-- capsules: own rows
-- ============================================================
CREATE POLICY "capsules_own" ON capsules
    FOR ALL USING (
        user_id IN (SELECT id FROM users WHERE supabase_uid = auth.uid()::text)
    );

-- ============================================================
-- capsule_recipients: accessible via owned capsules
-- ============================================================
CREATE POLICY "capsule_recipients_own" ON capsule_recipients
    FOR ALL USING (
        capsule_id IN (
            SELECT id FROM capsules
            WHERE user_id IN (SELECT id FROM users WHERE supabase_uid = auth.uid()::text)
        )
    );

-- ============================================================
-- media_attachments: accessible via owned capsules
-- ============================================================
CREATE POLICY "media_attachments_own" ON media_attachments
    FOR ALL USING (
        capsule_id IN (
            SELECT id FROM capsules
            WHERE user_id IN (SELECT id FROM users WHERE supabase_uid = auth.uid()::text)
        )
    );

-- ============================================================
-- checkin_schedules: own row
-- ============================================================
CREATE POLICY "checkin_schedules_own" ON checkin_schedules
    FOR ALL USING (
        user_id IN (SELECT id FROM users WHERE supabase_uid = auth.uid()::text)
    );

-- ============================================================
-- checkin_events: own events
-- ============================================================
CREATE POLICY "checkin_events_own" ON checkin_events
    FOR SELECT USING (
        user_id IN (SELECT id FROM users WHERE supabase_uid = auth.uid()::text)
    );

-- ============================================================
-- audit_logs: read-only, own entries
-- ============================================================
CREATE POLICY "audit_logs_own_read" ON audit_logs
    FOR SELECT USING (
        user_id IN (SELECT id FROM users WHERE supabase_uid = auth.uid()::text)
    );

-- No INSERT/UPDATE/DELETE policies on audit_logs for clients
-- (append-only via server-side service role only)

-- ============================================================
-- Supabase Storage bucket policies
-- Run in: Dashboard → Storage → Policies
-- ============================================================

-- capsule-content: users can only access their own prefix
-- INSERT policy:
--   (storage.foldername(name))[1] = auth.uid()::text
-- SELECT policy:
--   (storage.foldername(name))[1] = auth.uid()::text
-- DELETE policy:
--   (storage.foldername(name))[1] = auth.uid()::text

-- media-attachments: same pattern as capsule-content
-- thumbnails: same pattern as capsule-content
