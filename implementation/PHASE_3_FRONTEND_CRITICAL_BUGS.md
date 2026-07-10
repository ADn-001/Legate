# Phase 3 — Frontend Critical Bugs

**Covers audit items:** F1–F16 (§3 of `AUDIT_REPORT.md`)
**Assumes:** Phases 1–2 are 100% complete — stack deploys, `npm run build` works, backend lifecycle is correct, `CapsuleResponse`/list changes from Phase 2 T11/T13 are live.
**Goal:** Auth actually works (login, verify, session restore), no plaintext password at rest, recovery phrase is a real backup path, capsule edit/view are real, password reset exists.
**Rules:** No stubs/mocks. The final E2E is a real-browser Playwright suite against the full compose stack with live Supabase/Resend.

## Locked decisions

- **Recovery phrase (F4):** standard fix approved — second CEK blob wrapped by a recovery-phrase-derived key; new columns `recovery_encrypted_cek`, `recovery_cek_iv` (+ salt/params as needed) on `encryption_keys`, alembic migration; switch `bip39` → `@scure/bip39` (no Buffer dependency).
- **Token pages (F7):** backend-rendered pages are canonical. The frontend tokenized pages (`pages/tokenized/*`) are **removed** and their routes deleted; emails already point at `BASE_URL` pages. No token-exchange endpoint is built.

---

## T1 (F1) — Fix login/verify order-of-operations

`Login.tsx:22-24`, `VerifyEmail.tsx:35-41`: `authApi.getMe()` is called before the token is stored → 403 → "Invalid email or password" for every login.

1. Refactor `store/auth.ts` API: `setTokens(access, refresh)`, `setUser(user)`, `clear()`; `login()` becomes a thin composition or is removed.
2. Login flow: `POST /auth/login` → `setTokens` → `getMe()` → `setUser` → derive KEK/unwrap CEK (existing crypto store flow) → navigate.
3. VerifyEmail flow: same ordering after OTP verify.

## T2 (F2) — Session restore on reload

`store/auth.ts` keeps the access token in memory only; refresh token sits unused in localStorage; every reload = logout.

1. App boot (`App.tsx`): if `refresh_token` in localStorage → `POST /auth/refresh` → `setTokens` → `getMe()` → `setUser`; set `bootstrapped=true` either way; router waits on `bootstrapped` (splash/spinner, not redirect-to-login flicker).
2. CEK cannot be re-derived without the password: introduce a `locked` crypto-store state. Authenticated-but-locked users can browse metadata; any crypto operation (open/edit capsule content, view recovery phrase) raises an **unlock modal** asking for the password, which re-derives the KEK and unwraps the CEK. Wrong password → inline error, no logout.
3. Refresh failure (expired/revoked) → `clear()` → login page.

## T3 (F3) — Remove plaintext password from sessionStorage

`Signup.tsx:41-44` stores `btoa(password)` in sessionStorage until verify completes.

1. Hold the pending password in a non-persisted zustand store (memory only).
2. If lost (user refreshed between signup and verify): VerifyEmail prompts for the password after successful OTP to complete encryption-key setup (it has to derive the KEK and wrap the CEK). Validate by attempting the setup; wrong password → re-prompt.
3. Grep the codebase for any other `sessionStorage`/`localStorage` writes of secrets; remove.

## T4 (F4) — Make the recovery phrase real (FR-35/FR-10/R-02)

Currently decorative: generated, displayed, never wraps the CEK, never stored; `bip39` v3 needs Node `Buffer` → likely runtime crash in browser.

1. Replace `bip39` with `@scure/bip39` (+ wordlist import); delete the Buffer-dependent code in `crypto/bip39.ts`. Verify phrase generation in an actual browser (not jsdom).
2. Backend: migration adding `recovery_encrypted_cek`, `recovery_cek_iv`, `recovery_salt`, `recovery_phrase_hash` to `encryption_keys` (hash = SHA-256 of normalized mnemonic, for validation only); extend the keys API schemas/endpoints to accept/return the second blob.
3. Frontend `StepRecovery.tsx`: after displaying the phrase and the user confirms — derive a key from the mnemonic (`mnemonicToSeed` → HKDF/PBKDF2 → AES-256-GCM key), encrypt the CEK with it, `PATCH` the second wrapped blob + hash to the server. The phrase itself is never sent.
4. New **recovery flow** page (route `/recover`): user enters email + 24 words → after auth via password reset (T6) or while logged-in-but-locked → validate against `recovery_phrase_hash` → unwrap CEK from recovery blob → re-wrap with the (new) password → PATCH primary blob. This is what makes "forgot password ≠ data loss" true.
5. Settings/Security: "View recovery phrase" requires password confirmation (FR-35 re-access) — display from… the phrase is NOT stored; what's re-shown is the option to *generate a new phrase* (re-wrap CEK with a new mnemonic, invalidating the old). Implement "Regenerate recovery phrase" with explicit warning copy. (Re-displaying the original is cryptographically impossible by design — this satisfies FR-35's intent; noted as deviation in README, Phase 6.)

## T5 (F5 + F6) — Real capsule edit and view

**Backend half (F6):**
1. Extend `CapsuleResponse` (`schemas/capsule.py`): `beneficiary_id` (primary recipient join), `storage_object_path`, `cipher_iv`, plus Phase 2's `has_recipients`. Update the capsule service to populate them.
2. New `GET /capsules/{id}/content` → returns a short-lived signed download URL for the encrypted blob (Supabase `create_signed_url`), owner-only.

**Frontend half (F5):**
3. `CapsuleEditor.tsx` edit mode (`:id` route): fetch capsule → fetch signed URL → download encrypted blob → decrypt with CEK (unlock modal if locked) → populate editor. Save in edit mode = re-encrypt → upload to the same object path (or new path + PATCH) → `PATCH /capsules/{id}` — never `create` (line 79 bug).
4. Capsule **view screen**: read-only decrypt-and-render of a capsule (title, content, attachments list) from `CapsuleList` — this is the foundation FR-30 preview builds on in Phase 4.
5. `CapsuleList`: show beneficiary names (now available), `pending_deletion` badge (FR-31, data live since Phase 2 T13), and a "no recipients" warning chip using `has_recipients`.

## T6 (F8) — Password reset, full stack (FR-03)

Nothing exists: no route, no page, no link.

1. Backend: `POST /auth/forgot-password` → Supabase `reset_password_for_email` (magic link, 30-min expiry — configure redirect to frontend `/reset-password`); `POST /auth/reset-password` completing the change via Supabase token.
2. Frontend: "Forgot password?" link on Login; `/forgot-password` page (email form); `/reset-password` page consuming the magic-link token.
3. **Crypto wiring:** a new password cannot decrypt the old CEK blob. On reset, require the recovery phrase (T4's flow): unwrap CEK from recovery blob → re-wrap with new password → PATCH primary blob. If the user has no recovery blob (legacy account) → show explicit "content unrecoverable" warning and offer reset-with-data-loss (server flags `encryption_keys` row reset; capsules become undecryptable and are marked accordingly). Implement both paths for real.
4. Logged-in password **change** (Security page) gets the same re-wrap treatment using the old password instead of the phrase.

## T7 (F7) — Remove frontend tokenized pages

Per locked decision: delete `pages/tokenized/CheckinConfirm.tsx`, `CheckinSnooze.tsx`, `EmergencyPause.tsx` and their routes/api calls; emails target backend pages. (This also moots F15.) Verify no router references remain; `npm run build` clean.

## T8 (F9) — Verify-email resend + state survival

1. Backend: `POST /auth/resend-otp` → Supabase `auth.resend` (type `signup`). Rate limiting arrives in Phase 4 (G5); still add a simple 60s client-side cooldown on the button.
2. Wire the dead "Resend" button to it; success/error toasts.
3. Email lost on refresh (`location.state`): carry email via query param `?email=` and fall back to a prompt field if absent.

## T9 (F10) — Draft autosave fixes

1. Encrypt drafts at rest: autosave encrypts the draft (title+body) with the CEK before writing `draft_capsule_*` to localStorage; load path decrypts. If the CEK is locked (T2), buffer in memory and persist once unlocked. (User accepted the audit recommendation implicitly via NFR-04 scope; offline sync built in Phase 4 reuses this.)
2. Fix the status flicker: 'saved' indicator must only revert to 'unsaved' on an actual content change (dirty-tracking on the editor state, not a timer).

## T10 (F11 + F12) — Security page correctness

1. F11: backend `beneficiary_service.update` — when setting `is_emergency_contact=True`, clear the flag on the user's other beneficiaries in the same transaction (single emergency contact, FR-23). Frontend reflects single-select UI.
2. F12: Security page shows storage usage via existing `getStorageUsage` (now returns `limit_bytes` from Phase 2 T13) with a progress bar (FR-36/FR-46); "Regenerate recovery phrase" entry from T4.5 with password confirmation.

## T11 (F13) — API client interceptor

1. Replace `login(user!, ...)` misuse with `setTokens` from T1's store API.
2. Handle both 401 and 403 as refresh-triggers (backend HTTPBearer returns 403 on missing/invalid creds); avoid infinite loops: single retry per request, then `clear()` + redirect.

## T12 (F14 + F16) — Login errors + full name

1. F14: differentiate login failures — 400/401/403 → "Invalid email or password"; network error → "Can't reach the server"; 5xx → "Something went wrong, try again".
2. F16: add `full_name` to backend `SignupRequest` + set `User.full_name` in `auth_service.signup`; frontend sends the collected `fullName`. Delivery emails (Phase 2 T9) already consume `full_name` — verify end-to-end that the nominator name renders.

## T-test — Phase 3 E2E (final task — phase gate)

**Tooling:** add Playwright (`@playwright/test`) to the frontend with a `test:e2e` script. Tests run headed-or-headless Chromium against the **compose stack** (`http://localhost`) with live Supabase/Resend.

**OTP handling (no mocks):** tests fetch the OTP via the Supabase admin API from the test conftest pattern used in `backend/tests/e2e/test_02_auth.py` (admin `generate_link` / direct `auth.admin` lookup against the test project). Expose a tiny test-only helper script (`scripts/get_test_otp.py`, reads service-role key from env, NOT shipped in the image — excluded via `.dockerignore`) that Playwright calls. This talks to the real Supabase project.

Playwright specs (each is a real browser run):
1. **signup-verify-login.spec** — signup (name+email+password) → OTP verify → recovery phrase shown → confirm checkbox → land in app. Assert: no `btoa(` password in session/localStorage (inspect storage), recovery blob present via API, `full_name` returned by `/auth/me`.
2. **session-restore.spec** — login → reload page → still authenticated (F2); open a capsule → unlock modal appears → password unlocks → content decrypts.
3. **capsule-edit.spec** — create capsule with text → reopen via edit route → content decrypted into editor (F5) → modify → save → capsule **count unchanged**, content updated (re-fetch + decrypt and assert new text).
4. **capsule-view.spec** — view screen decrypts and renders; beneficiary name visible in list (F6).
5. **password-reset.spec** — forgot password → magic link (retrieve via Supabase admin) → set new password + enter recovery phrase → login with new password → old capsule still decrypts (the re-wrap worked). This is the critical R-02 regression.
6. **draft.spec** — type in editor, wait for autosave → assert localStorage draft value is NOT plaintext (does not contain the typed sentence) → reload → draft restored after unlock.
7. **errors.spec** — wrong password login shows "Invalid email or password"; stopped API (pause container) shows network error message (F14).

Also: `npm run test` (vitest unit suite) and `npm run lint` green; `npm run build` clean.

**Run:**
```
docker compose up -d --build
cd frontend && npx playwright install chromium && npm run test:e2e
```
All specs green = Phase 3 complete. Record output in `## Phase 3 E2E result` here.

## Phase 3 E2E result

**Date:** 2026-06-23  
**Stack:** Docker Compose (NGINX:8080 → FastAPI → Supabase/Redis), Chromium via Playwright, live Supabase project.

```
> legate-frontend@0.0.1 test:e2e
> playwright test

[global-setup] Waiting for backend…
[global-setup] Backend healthy.
[global-setup] Warming up backend auth+JWT pipeline…
[global-setup] Backend fully warmed up.
[global-setup] Cleaned up 22 capsule(s) from previous run.
[global-setup] Reusing existing shared user — delete .shared-user.json to force a new signup.

Running 7 tests using 1 worker
  ok 1 …le decrypts existing content and re-save never duplicates it (53.8s)
  ok 2 …rypts and renders a capsule; list shows the beneficiary name (33.2s)
  ok 3 …raft autosave is encrypted at rest and restores after unlock (46.4s)
  ok 4 …ssages differentiate bad credentials from a dead server (F14) (4.6s)
  ok 5 …via recovery phrase preserves existing capsule content (R-02) (1.7m)
  ok 6 …n survives a reload and a locked vault unlocks via the modal (45.6s)
  ok 7 … verify → onboarding → recovery phrase lands user in the app (43.0s)

  7 passed (7.1m)
```

**Phase 3 — COMPLETE ✅**
