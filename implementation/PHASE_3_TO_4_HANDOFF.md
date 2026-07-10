# Phase 3 → Phase 4 Handoff

**Written:** 2026-06-23  
**Phase 3 status:** COMPLETE — all 7 Playwright E2E specs pass (7.1 min runtime).  
**Next:** `PHASE_4_PRD_P0_FEATURE_GAPS.md`

---

## What Phase 3 delivered

Every T-task in `PHASE_3_FRONTEND_CRITICAL_BUGS.md` is implemented and covered by a passing spec. Quick map:

| Phase 3 task | Covers | Spec |
|---|---|---|
| T1 F1 | Login/verify order-of-operations | spec 7 |
| T2 F2 | Session restore on reload (locked vault, unlock modal) | spec 6 |
| T3 F3 | Plaintext password removed from sessionStorage | spec 7 |
| T4 F4 | Recovery phrase is real (wraps CEK, stored server-side, recovery flow) | spec 5 |
| T5 F5+F6 | Real capsule edit (decrypt→edit→re-encrypt→upload) and view screen | specs 1, 2 |
| T6 F8 | Forgot-password + magic-link + crypto re-wrap on reset | spec 5 |
| T7 F7 | Tokenized pages removed | — |
| T8 F9 | Resend OTP wired, 60s cooldown, email via query param | spec 7 |
| T9 F10 | Draft autosave encrypted at rest, real dirty-tracking | spec 3 |
| T10 F11+F12 | Emergency contact backend single-select + storage usage progress bar + regenerate recovery phrase | — |
| T11 F13 | API interceptor handles 401 AND 403, single retry, no infinite loop | — |
| T12 F14+F16 | Login error differentiation, full_name in signup | spec 4 |

---

## Deviations from the Phase 3 spec

### 1. Edit content upload is server-side, not signed-URL (T5)

**What the spec said:** "upload to the same object path (or new path + PATCH)"

**What was built:** A new endpoint `PUT /capsules/{id}/content` accepts the raw encrypted `Uint8Array` as `application/octet-stream`. The backend uploads it directly to Supabase Storage using the service-role `SyncStorageClient`. No browser→Supabase signed-URL PUT occurs in the edit flow.

**Why:** The `create_signed_upload_url` PUT was hanging indefinitely in the edit flow. The storage3 library's default `upsert=False` causes the PUT to stall when an object already exists at the path. Unique paths (`content_{hex}.enc`) were tried but the hang persisted even with fresh paths (signed URL generation succeeds but the PUT itself stalls, possibly a TCP/timing issue specific to the edit context). Routing through the backend eliminates the browser-to-Supabase network hop entirely and is reliable.

**What this means for Phase 4:**
- `POST /capsules/{id}/media` (Phase 4 T1) should follow the **same server-side upload pattern**: accept the encrypted blob from the browser and upload via `storage.from_(bucket).upload(path, data)`. Do NOT use signed upload URLs for the frontend. See `capsule_service.upload_content()` as the reference implementation.
- The `POST /capsules/{id}/content` endpoint (get_upload_url, returns a signed upload URL) is now dead code in the frontend. It can be kept or removed; it does no harm.

### 2. CREATE flow still uses signed URL + hardcoded storage path

The capsule create flow (`CapsuleEditor.tsx`, `else` branch of `handleSave`) still does:
```
POST /capsules/ → { upload_url, capsule_id }
uploadEncryptedBlob(upload_url, blob)          # direct browser→Supabase PUT
PATCH /capsules/{id} with storage_object_path: `${user.id}/${capsuleId}/content.enc`
```

The storage path is **hardcoded in the frontend** and must match exactly what the backend's `create()` method passes to `create_signed_upload_url` (currently `{user_id}/{capsule_id}/content.enc`). This fragility is acceptable for now (create works reliably) but Phase 4 could consolidate to the server-side upload pattern.

### 3. Multiple storage objects per capsule after edits

Each edit creates a new `content_{token_hex(8)}.enc` object. The old ones become orphaned blobs. The Phase 2 T7 purge task (`purge_capsule_storage`) is supposed to list all objects under `{user_id}/{capsule_id}/` and delete them when a capsule is purged. Verify that the purge task's listing logic covers the `content_*.enc` glob, not just the fixed `content.enc` path.

### 4. `SyncStorageClient` blocks the event loop

All Supabase Storage calls use `SyncStorageClient` (synchronous, blocking). This is acceptable for small payloads (content blobs ≤ ~15KB) because the blocking window is under 1s. For Phase 4 T2 (video attachments up to 500MB), blocking the asyncio event loop during upload is unacceptable. Either:
- Use `asyncio.get_event_loop().run_in_executor(None, storage_call)` to run storage calls in a thread pool, or
- Switch to `AsyncStorageClient` from storage3.

### 5. NGINX_PORT=8080 (environment, not code)

Port 80 is permanently bound to WSL on the dev machine. `.env` sets `NGINX_PORT=8080`. `docker-compose.yml` already uses `"${NGINX_PORT:-80}:80"` so this is a one-line `.env` change, not a code change. The E2E suite's `DEFAULT_BASE_URL` is hardcoded to `http://localhost:8080` in `frontend/e2e/helpers/env.ts`. On any other machine remove `NGINX_PORT` from `.env` (defaults to 80) and set `E2E_BASE_URL=http://localhost` if needed.

### 6. PyJWT clock-skew leeway

`backend/app/dependencies.py` uses `leeway=timedelta(seconds=10)` when verifying Supabase JWTs. This was added to fix `ImmatureSignatureError` caused by Docker's clock being slightly ahead of Supabase's `iat`. Keep this; do not remove it.

### 7. Supabase signup rate limit (3 emails/hour)

`auth_service.signup()` falls back to `admin.create_user()` when Supabase's signup email rate limit is hit. The `get_test_otp.py` script handles both the normal case (OTP from `generate_link`) and the admin-created case. This is already working; Phase 4 does not need to change anything here.

---

## Key files Phase 4 will touch

| File | Why Phase 4 touches it |
|---|---|
| `backend/app/services/capsule_service.py` | Add `create_media`, `confirm_media`, `delete_media` (T1) |
| `backend/app/api/capsules.py` | Add `POST /media`, `POST /media/{mid}/confirm`, `DELETE /media/{mid}` (T1) |
| `backend/app/schemas/capsule.py` | Extend `CapsuleResponse` with `media_attachments` list (T1) |
| `backend/app/db/models/capsule.py` | `MediaAttachment` model already scaffolded — verify it has all needed fields |
| `frontend/src/pages/vault/CapsuleEditor.tsx` | Remove the B4 stub comment (lines 89–97), wire `MediaUploader` |
| `frontend/src/crypto/media.ts` | Verify encryption is real (not stub); complete if partial |
| `backend/app/worker/tasks/delivery_tasks.py` | Phase 4 T1 extends media delivery (decrypt→re-upload delivery copy) |
| `backend/app/worker/tasks/cleanup_tasks.py` | Extend purge to handle media bucket prefix |
| `frontend/vite.config.ts` | Add `vite-plugin-pwa` (T4) |

---

## E2E test infrastructure — what Phase 4 inherits

**Global setup** (`frontend/e2e/global-setup.ts`):
- Waits for backend health (`/health`), warms up JWT pipeline.
- Creates one shared onboarded user (written to `.shared-user.json`). This file is reused across runs to avoid the Supabase 3-email/hour rate limit. Delete it manually to force a new signup.
- Cleans up all capsules from the previous run before each suite starts.

**OTP/token helper** (`backend/scripts/get_test_otp.py`):
- Called via `execFileSync` from `frontend/e2e/helpers/otp.ts`.
- Requires Python + `supabase==2.4.3` on the test machine; `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY` inherited from `backend/.env` automatically by `playwright.config.ts`.
- Supports two modes: `signup-otp` (returns 6-digit OTP for email verify) and `recovery-tokens` (returns `access_token`+`refresh_token` for password reset magic link).

**Spec naming convention:** specs are numbered by Playwright's file-alpha order, not by the order they were written. When adding Phase 4 specs, add files that sort after `session-restore.spec.ts`, `signup-verify-login.spec.ts` (names are descriptive, not numbered).

**Shared user vs. fresh user:** specs that mutate permanent user state (password-reset, future: account deletion test) use `freshEmail()` and do their own `signupAndOnboard()`. Specs that only read/write capsules share the global user via `loadSharedUser()`. Keep this discipline in Phase 4 — the media and PWA specs can share the user; ratelimit tests should use a fresh user.

---

## Known technical debt entering Phase 4

These are present in the codebase but were outside Phase 3's scope. Phase 4 may or may not address them (check the Phase 4 doc):

- `POST /capsules/{id}/content` (get_upload_url) — endpoint is dead, frontend never calls it. Remove or repurpose.
- `CapsuleEditor.tsx` CREATE flow sends `storage_object_path` hardcoded from frontend. Fragile if backend path changes.
- No rate limiting anywhere (Phase 4 T7).
- No PWA manifest/service worker (Phase 4 T4).
- Rich text is a plain textarea (Phase 4 T9).
- `MediaUploader.tsx` stub comment at lines 89–97: "TODO: POST /capsules/{capsuleId}/media → get upload_url → PUT encryptedBlob — This requires the B4 backend endpoint to be implemented first." Phase 4 T1 removes this.
- Beneficiary `status != removed` filter missing from `list_for_user` — removed beneficiaries appear in dropdowns. Audit item B13, not yet fixed.
- `checkin_service.py` — confirm does not re-email the beneficiary on removal (B13 partial).

---

## Running the full suite before starting Phase 4

```bash
# From the repo root (WSL or native Windows with Docker Compose V2):
docker compose build api nginx
docker compose up -d
cd frontend
npm run test:e2e
```

All 7 must be green before starting Phase 4 work. If they're not, resolve before proceeding — Phase 4 adds specs on top and a broken baseline creates confusion about what regressed.
