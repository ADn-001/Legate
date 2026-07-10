# Phase 3 Handoff Notes

**Updated 2026-06-16.** Supersedes the previous version of this file (written 2026-06-15, pre-implementation audit). Phase 3 (`PHASE_3_FRONTEND_CRITICAL_BUGS.md`, T1–T12) is now **implemented**. This note is for whoever picks up next: either to finish the small T7 cleanup + verification loop, or to build T-test (the Playwright e2e gate).

---

## 1. What's currently happening (read this first)

We are in the **non-e2e verification step**, immediately before T-test. Sequence:

1. T1–T12 implemented end-to-end (details in §2). No stubs/mocks.
2. Full re-read of `Security.tsx` (largest change, T10) confirmed internally consistent.
3. User ran `npm run build` / `npm run lint` / `npm run test` (frontend) and `pytest` (backend) in PowerShell.
   - `tsc` surfaced **two real bugs**, now fixed (§3).
   - Everything else was **environment breakage, not code** (§4): broken `frontend/node_modules` (only Windows `.bin` shims present, actual package contents missing for vitest/eslint/lucide-react/react-router-dom/etc.) and backend deps not installed wherever `pytest` is running.
4. **Outstanding, blocking next steps (on the user):**
   - Delete 3 dead files for T7 (§5) — no delete capability in the assistant's sandbox.
   - `cd frontend; rm -r -fo node_modules; npm install`, then re-run build/lint/test.
   - Install backend deps (`pip install -r backend/requirements.txt` in a venv, or run via `docker compose exec backend pytest`), then re-run pytest.
   - Paste results back.
5. **T-test (Playwright e2e suite) has not been started.** This is the phase gate — do not start it until the user explicitly says go, and until build/lint/test/pytest are all green.

Nothing is running in the background. The ball is in the user's court for the items in step 4.

---

## 2. Task-by-task status (T1–T12)

| Task | Title | Status |
|---|---|---|
| T1 | Fix login/verify order-of-operations | ✅ Done |
| T2 | Session restore on reload + locked crypto state | ✅ Done |
| T3 | Remove plaintext password from sessionStorage | ✅ Done |
| T4 | Make recovery phrase real (incl. T4.5 regenerate) | ✅ Done |
| T5 | Real capsule edit and view | ✅ Done |
| T6 | Password reset, full stack | ✅ Done |
| T7 | Remove frontend tokenized pages | ⚠️ Code/routes done; 3 files need manual deletion |
| T8 | Verify-email resend + state survival | ✅ Done |
| T9 | Draft autosave fixes | ✅ Done |
| T10 | Security page correctness (F11 emergency contact, F12 storage + regen phrase) | ✅ Done |
| T11 | API client interceptor | ✅ Done |
| T12 | Login errors + full name | ✅ Done |
| T-test | Playwright e2e suite (phase gate) | ⏸ Not started |

### Locked decisions honored
- **F4 (recovery phrase, T4/T4.5):** `@scure/bip39` (`frontend/src/crypto/bip39.ts`), second CEK blob (`recovery_encrypted_cek`/`recovery_cek_iv`/`recovery_salt`/`recovery_phrase_hash` on `encryption_keys`), HKDF-SHA256 derivation (`deriveRecoveryKey`), `/recover` page, and a "Regenerate recovery phrase" entry in Security (T4.5) implemented as a 3-step modal (password confirm → new phrase display/copy/checklist → success). Per the phase doc, re-displaying the *original* phrase is cryptographically impossible by design — regeneration is the implemented equivalent of FR-35 re-access. This deviation was pre-approved in the phase doc itself, not a new one.
- **F7 (token pages, T7):** backend-rendered pages canonical, frontend tokenized pages + routes removed, no token-exchange endpoint built. One cleanup step remains — §5.

### T10 detail (most recent implementation work — F11 + F12)
- **F11 (single emergency contact, FR-23):** `backend/app/services/beneficiary_service.py` `update()` now bulk-clears `is_emergency_contact` on every other beneficiary for the user in the same transaction when one is set to `true`. `BeneficiaryForm.tsx` shows an amber "This will replace `<name>` as your emergency contact" hint (prop `otherEmergencyContactName`, computed in `Beneficiaries.tsx`). Frontend reflection relies on existing `useUpdateBeneficiary` cache invalidation.
- **F12a (storage usage bar, FR-36/FR-46):** `Security.tsx` queries the existing `GET /settings/storage` endpoint (already complete from Phase 2 T13, returns `total_bytes`/`limit_bytes`/`by_capsule`) via `useQuery<StorageUsage>`. New `StorageUsage` type in `frontend/src/types/api.ts`. Renders a progress bar, amber at ≥75%, red + "nearly out of storage" warning at ≥90%.
- **F12b (regenerate recovery phrase, T4.5/FR-35):** new modal in `Security.tsx`, 3 steps:
  1. `password` — re-derive CEK from current password (`authApi.getEncryptionKey()` + `keysModule.deriveWrappingKey`/`decryptCEK`) as the FR-35 re-access check. CEK held only in `regenCekRef` (`useRef<CryptoKey | null>`), never in component state.
  2. `phrase` — generate new 24-word phrase (`bip39Module.generatePhrase()`), display in a grid, copy-to-clipboard, and a required "I've written it down" checkbox.
  3. `success` — confirms the old phrase no longer works. On confirm: `deriveRecoveryKey` on the new mnemonic → re-wrap CEK → `authApi.setRecoveryKey(...)` overwrites the recovery blob (existing endpoint, supports overwrite by design — no backend change needed).
  - `closeRegenModal()` resets all step state and clears `regenCekRef.current`.

---

## 3. Bugs found and fixed during this verification pass

Caught by `tsc`, not part of the original T1–T12 diffs, but blocked a clean build — both fixed, surgical one-liners:

1. **`frontend/src/pages/security/Security.tsx`** (`handleDeleteAccount`): called `useAuthStore.getState().logout()`. The auth store (`store/auth.ts`) has no `logout` — only `clear()` (resets `user`/`accessToken`/`isAuthenticated`/`needsOnboarding`, removes `refresh_token` from localStorage). Changed `.logout()` → `.clear()`.

2. **`frontend/src/crypto/bip39.ts`** (`deriveRecoveryKey`): `crypto.subtle.deriveKey({ name: 'HKDF', salt, ... })` failed `tsc` — with `@types/node` present, the bare `Uint8Array` parameter type resolves to `Uint8Array<ArrayBufferLike>`, not assignable to DOM's `BufferSource` (`ArrayBuffer | ArrayBufferView<ArrayBuffer>`). Known `@types/node`/DOM-lib generic-typed-array conflict. Fixed with a type-only cast: `salt: salt as unknown as BufferSource` — no runtime behavior change.

---

## 4. Environment issues found (not code)

- **`frontend/node_modules` is broken/incomplete.** `node_modules/.bin` has only Windows `.cmd`/`.ps1` shims; actual package contents for `vitest`, `eslint` (missing `eslint-visitor-keys/dist/eslint-visitor-keys.cjs`), `lucide-react`, `react-router-dom`, `@tanstack/react-query`, `@scure/bip39`, etc. are absent. This produced ~66 of 68 `tsc` errors (`Cannot find module ...`) plus the eslint/vitest crashes.
  - Fix: `cd frontend; rm -r -fo node_modules; npm install`, then re-run build/lint/test.
- **Backend: `ModuleNotFoundError: No module named 'pydantic_settings'`** when running `pytest` — deps from `backend/requirements.txt` (used by the Dockerfile) aren't installed in whatever environment is running pytest, and there's no local venv on disk.
  - Fix: either `docker compose exec backend pytest` (or via `docker-compose.dev.yml`), or create a venv and `pip install -r backend/requirements.txt` before running pytest natively.
- Running `npm run build` from the repo root fails (`ENOENT package.json`) — there's no root `package.json`; commands must run from `frontend/` (or `backend/` for pytest).
- Per memory: docker/git should be run **natively** (PowerShell), not through a WSL `/mnt/d/...` mount, to avoid the known git-index-corruption issue. The frontend `node_modules` mismatch (Windows-only shims) is consistent with npm having been run on the Windows side already — so PowerShell is the right shell for these commands.

---

## 5. T7 — outstanding manual step (no code change needed)

`frontend/src/router.tsx` no longer references the tokenized pages (confirmed via grep) — **the build will not break** without this step. But three dead files remain on disk, contrary to the phase doc's "removed" requirement:

- `frontend/src/pages/tokenized/EmergencyPause.tsx`
- `frontend/src/pages/tokenized/CheckinSnooze.tsx`
- `frontend/src/pages/tokenized/CheckinConfirm.tsx`

Each only imports `client` (`api/client`), `react-router-dom`, and `lucide-react` — all still valid — so they won't cause type errors either; they're purely orphaned. Delete the three files and the now-empty `tokenized/` folder. The assistant has no file-delete capability in this environment (sandbox unavailable for `rm`), so this is a manual step.

---

## 6. Next steps (in order)

1. Delete the 3 files in §5 (T7 cleanup).
2. `cd frontend; rm -r -fo node_modules; npm install`, then `npm run build`, `npm run lint`, `npm run test`. Report any remaining errors.
3. Get backend deps installed (Docker exec or local venv + `pip install -r backend/requirements.txt`), re-run `pytest`. Report any remaining errors.
4. Once build/lint/test/pytest are all green, the user gives the go-ahead to start **T-test**:
   - Add Playwright (`@playwright/test`) to the frontend, `npx playwright install chromium`, add a `test:e2e` script.
   - Write the 7 specs from the phase doc (`signup-verify-login`, `session-restore`, `capsule-edit`, `capsule-view`, `password-reset`, `draft`, `errors`) against the compose stack (`http://localhost`) with live Supabase/Resend.
   - Build the test-OTP helper `scripts/get_test_otp.py` reusing the `_make_admin_client()` pattern from `backend/tests/e2e/test_02_auth.py`/`conftest.py` — fresh admin client per call, excluded from the Docker image via `.dockerignore`.
   - Run via `docker compose up -d --build` then `cd frontend && npx playwright install chromium && npm run test:e2e`. Record results in `## Phase 3 E2E result` in `PHASE_3_FRONTEND_CRITICAL_BUGS.md`. All specs green = Phase 3 complete.

---

## 7. Files touched in the most recent (T10) implementation segment

- `backend/app/services/beneficiary_service.py` — F11 single-emergency-contact transaction logic.
- `frontend/src/components/beneficiary/BeneficiaryForm.tsx` — `otherEmergencyContactName` prop + hint.
- `frontend/src/pages/people/Beneficiaries.tsx` — computes `otherEmergencyContactName`, passes to form.
- `frontend/src/types/api.ts` — added `StorageUsage` interface.
- `frontend/src/pages/security/Security.tsx` — storage usage card, regenerate-recovery-phrase modal, `logout()` → `clear()` fix.
- `frontend/src/crypto/bip39.ts` — `BufferSource` type-cast fix in `deriveRecoveryKey`.

(Earlier T1–T9, T11, T12 changes span `store/auth.ts`, `store/crypto.ts`, `store/unlock.ts`, `store/pendingAuth.ts`, `api/client.ts`, `api/auth.ts`, `crypto/keys.ts`, `crypto/bip39.ts`, `crypto/capsule.ts`, `pages/auth/*`, `pages/vault/CapsuleEditor.tsx`/`CapsuleView.tsx`/`CapsuleList.tsx`, `pages/security/Recover.tsx`, `pages/setup/StepRecovery.tsx`, `router.tsx`, plus backend `schemas/capsule.py`, `services/capsule_service.py`, `api/capsules.py`, `services/auth_service.py`, `api/auth.py`, and an Alembic migration for the recovery-blob columns — see git history for the full diff per task.)

---

## 8. Update 2026-06-22 — verification loop closed, T-test built, four real bugs found via live testing, E2E run still pending

**Read this whole section before doing anything** — it's the full state as of context running out mid-session. The short version: code is in good shape, several real bugs were found and fixed by actually running things against the live stack, and the very last action (fix baseURL + a crypto bug) has **not yet been confirmed working** — that's the next thing to do.

### 8.1 Verification loop (§4/§5/§6 above) — closed

- T7 cleanup done — the 3 dead `pages/tokenized/*` files were deleted.
- `frontend/src/crypto/bip39.ts` `deriveRecoveryKey`: the real bug behind the `tsc` failure was `seed`/`salt` typed as bare `Uint8Array` (resolves to `Uint8Array<ArrayBufferLike>`, not assignable to WebCrypto's `BufferSource`) — not just a missing cast. Fixed by typing `salt: Uint8Array<ArrayBuffer>` and wrapping `seed` in `new Uint8Array(...)`, matching the convention already used in `keys.ts`/`capsule.ts`/`media.ts`.
- `frontend/eslint.config.js` didn't exist — ESLint 9 needs flat config and was silently running zero rules. Created it. Dropped `--ext ts,tsx` from `package.json`'s `lint` script — invalid under flat config in ESLint v9.
- Environment-only, not code: PowerShell execution policy, Node v18.15.0 → needed ≥20.12 (vitest 4's `rolldown` dependency needs `node:util`'s `styleText` export), a broken `node_modules` needing a clean reinstall (npm/cli#4828), `docker compose exec api` not `backend` (service is named `api`), `NGINX_PORT=8080` for the permanent port-80 conflict on this machine.
- Result at the time: `npm run build` / `npm run lint` / `npm run test` (24/24) / backend `pytest` (184 passed, 2 skipped) all green.

### 8.2 T-test suite — built, structure and files

All real browser, real Supabase/Resend, no mocks:
- `backend/scripts/get_test_otp.py` — mints real Supabase OTPs/recovery tokens via `auth.admin.generate_link` (commands: `signup-otp <email> <password>`, `recovery-tokens <email>`, `debug-link <signup|recovery> <email> [password]` for raw-response debugging). Excluded from the Docker image via `backend/.dockerignore` (`scripts/` added there). Needs Python + `supabase==2.4.3` (matches `backend/requirements.txt`) wherever `npm run test:e2e` runs, and `SUPABASE_URL`/`SUPABASE_ANON_KEY`/`SUPABASE_SERVICE_ROLE_KEY` in env — `playwright.config.ts` auto-loads these from `backend/.env` via `dotenv`.
- `frontend/playwright.config.ts` — `globalSetup: './e2e/global-setup.ts'`, `workers: 1` (serial — `errors.spec` stops/starts the live `nginx` container), `baseURL` from `helpers/env.ts`'s `DEFAULT_BASE_URL`.
- `frontend/e2e/global-setup.ts` — runs once before the suite: one real signup+onboarding via `signupAndOnboard()`, saved to `frontend/e2e/.shared-user.json` (gitignored) via `helpers/sharedUser.ts`. On failure, dumps `frontend/e2e/debug-failure.png` + `.html` — globalSetup gets none of Playwright's automatic per-test screenshot/trace capture, so this was added specifically to make globalSetup failures debuggable.
- `frontend/e2e/helpers/`:
  - `env.ts` — `freshEmail()`, `TEST_PASSWORD`, `DEFAULT_BASE_URL` (see §8.4 below — **this is the single source of truth for the base URL now, do not hardcode `http://localhost` anywhere else**).
  - `otp.ts` — spawns `get_test_otp.py` via `execFileSync`, parses JSON.
  - `crypto.ts` — Node-side mirror of `hashMnemonic`/`normalizeMnemonic` for verifying the server-side recovery hash independently.
  - `api.ts` — `captureBearerToken()` (listens on `page.on('request')` for a real `Authorization` header rather than reconstructing one), `getMe()`, `validateRecoveryPhrase()`.
  - `onboarding.ts` — `signupAndOnboard()` (full real signup → OTP → 4-step wizard → `/vault`) and `loginUI()`. **Has inline diagnostics at each step** (captures the real `/auth/signup` and `/auth/verify-email` HTTP responses, checks for the "Confirm your password" fallback step, reads the on-page error banner) — if a future failure here is just a bare `toHaveURL` timeout with no useful message, that's a sign the diagnostic coverage needs to extend further into the onboarding wizard (beneficiary/capsule/recovery steps don't have this yet, only signup+verify do).
  - `sharedUser.ts` — `loadSharedUser()`/`saveSharedUser()` for the file above.
  - `capsules.ts` — `capsuleCard(page, title)`: scopes capsule-list assertions to one card by title, because the shared user's capsule list accumulates one card per spec that runs against it (see §8.3).
- Specs: `signup-verify-login`, `password-reset` do their **own independent** real signup (can't share state — the latter permanently changes its user's password). `session-restore`, `capsule-edit`, `capsule-view`, `draft` use the **shared** user via `loadSharedUser()` + `loginUI()`. `errors` uses the shared user's email for a wrong-password check but never logs in (it's testing failure paths) and itself stops/starts the `nginx` container around the network-error assertion.
- `frontend/package.json`: added `@playwright/test`, `dotenv` devDeps, `test:e2e` script. `.gitignore`: added `frontend/{test-results,playwright-report,playwright/.cache}/` and `frontend/e2e/.shared-user.json`.

### 8.3 Why only ~3 real signups per run, not 7

First full run hit a real Supabase signup-email rate limit (`429 {"detail":"Email rate limit exceeded — try again later"}`) after 2 signups. Restructured per §8.2 to do the minimum: 1 shared (global-setup) + 1 (`signup-verify-login`) + 1 (`password-reset`) = 3. User explicitly decided (2026-06-21) **not** to configure custom SMTP for Supabase Auth via Resend right now and to treat the limit as a known limitation — re-raise only if it keeps blocking runs, or if it matters for real production signup volume (Supabase's default built-in mailer for Auth emails is separate from the Resend integration in `delivery_service.py`, which only sends capsule-delivery emails). **Do not re-run `npm run test:e2e` repeatedly in a tight loop** if a 429 shows up again — space attempts out.

### 8.4 Four real bugs found by actually running this, in order found

1. **Supabase Email OTP length was 8 digits, `VerifyEmail.tsx` is hardcoded for 6** (6 boxes, submit gated on `otp.join('').length !== 6`). Real users could never have completed signup verification. Not a Phase 3 audit item — caught only by testing against the live project. **Fixed by the user** via Supabase Dashboard → Authentication → Settings, set back to 6. Confirmed via `get_test_otp.py debug-link` showing the raw `email_otp` field.
2. Supabase signup-email rate limit — see §8.3. Environmental, not a code bug; worked around by reducing real signups.
3. **`frontend/src/crypto/keys.ts` `decryptCEK` imported the unwrapped CEK with `extractable: false`.** Real, previously-undetected bug, fixed. Every flow that unwraps an existing CEK and then re-wraps it under a *different* key — first-login delivery-key setup in `VerifyEmail.tsx`'s `completeEncryptionSetup`, password reset/change, recovery, regenerate-recovery-phrase — calls `encryptCEK()` on it, which does `crypto.subtle.exportKey('raw', cek)`. A non-extractable key throws `"Failed to execute 'exportKey' on 'SubtleCrypto': key is not extractable"` the instant any of those run. `generateCEK()` already correctly used `extractable: true`; `decryptCEK()` just needed to match it. **This would have broken real user flows in production, not just the test** — found via the onboarding diagnostics in `helpers/onboarding.ts` surfacing the actual on-page error banner text instead of a bare timeout.
4. **`playwright.config.ts` / `global-setup.ts` defaulted `baseURL` to plain `http://localhost` (port 80)**, but this machine has a permanent, unrelated nginx process already bound to port 80 (confirmed: the 404 response it returns is `nginx/1.24.0 (Ubuntu)`, while the actual compose stack's nginx is `1.31.2 (Alpine)` — two different servers). `$env:E2E_BASE_URL` set manually in one PowerShell session doesn't persist to a new session, so it silently fell back to the wrong default and hit the wrong nginx, which 404s on `/auth/signup`. **Fixed**: added `DEFAULT_BASE_URL = 'http://localhost:8080'` to `frontend/e2e/helpers/env.ts` as the single source of truth, imported by both `playwright.config.ts` and `global-setup.ts`, so a fresh shell with no env var set still does the right thing. `E2E_BASE_URL` env var still overrides it if needed elsewhere.

### 8.5 Current status / next steps — START HERE

**No full green `npm run test:e2e` run has happened yet.** The last thing done was the bug-4 fix above; the user was told to re-run but the result was never reported back (context ran out). Next session, in order:

1. Confirm the compose stack is up: `docker compose ps` (in WSL bash, repo root) — all of `api`/`worker`/`beat`/`nginx`/`redis` should show `Up`. If `nginx` shows stopped, a prior interrupted `errors.spec` run may have left it stopped (its `finally` block runs `docker compose start nginx`, but a killed process skips that) — `docker compose start nginx` to recover, or just `up -d` the whole stack.
2. `cd frontend && npm run test:e2e`. No env vars need to be set anymore (bug 4 fix).
3. **If it fails**: read the actual error message first — this session repeatedly found that bare `toHaveURL` timeouts hide the real cause, and added inline diagnostics in `helpers/onboarding.ts` specifically so failures report the real HTTP response/error-banner text instead. If a *new* kind of failure shows a bare timeout with no useful message, extend the same diagnostic pattern (capture the relevant response via `page.waitForResponse()`, or read `.bg-red-50 p` for the on-page error banner) rather than guessing. For failures inside `global-setup.ts` specifically, remember Playwright's automatic screenshot/trace capture does **not** apply there — `debug-failure.png`/`.html` (already wired up) are what you have to go on.
4. Once all 7 specs pass: append `## Phase 3 E2E result` to `PHASE_3_FRONTEND_CRITICAL_BUGS.md` (its own §T-test instruction) with the actual `npm run test:e2e` output. **That's what marks Phase 3 complete** — not before.
