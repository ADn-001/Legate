# Phase 4 — Missing PRD Features

**Covers audit items:** G1–G11 (§4 of `AUDIT_REPORT.md`) **plus, per user decision:** FR-28 (video), FR-30 (preview), NFR-04 (offline drafts + sync). Other P1s (FR-04 biometrics, FR-17 push, FR-29 drag-reorder) remain out of scope.
**Assumes:** Phases 1–3 are 100% complete — deployable stack, correct backend lifecycle, working auth/edit/view/recovery, encrypted drafts (Phase 3 T9), delivery email renders `media_attachments` (Phase 2 T9).
**Goal:** All PRD P0 features exist end-to-end; the app is a real installable PWA.
**Rules:** No stubs/mocks. The "B4 endpoint" stub comment in `CapsuleEditor.tsx:89-97` must be gone by end of phase.

---

## T1 (G2 + FR-27) — Photo attachments, end-to-end

Backend:
1. `POST /capsules/{id}/media` — request: filename, content_type, size_bytes, kind=`photo`. Validate: ≤20 photos/capsule (count existing rows), JPEG/PNG/HEIC, ≤10MB (FR-27). Create `MediaAttachment` row (`status='pending'`) + return a Supabase **signed upload URL** for `{user_id}/{capsule_id}/{attachment_id}` in the media bucket.
2. `POST /capsules/{id}/media/{mid}/confirm` — client calls after upload completes; backend verifies the object exists (head/list) and size matches → `status='ready'`.
3. `DELETE /capsules/{id}/media/{mid}` — remove row + storage object.
4. Include attachments (id, kind, status, size, thumbnail path) in `CapsuleResponse`.

Frontend:
5. Wire `MediaUploader.tsx` to the real endpoints: client-side **encrypt each file with the CEK** (existing `crypto/media.ts` — verify it's real; finish it if partial) → upload to the signed URL with progress (NFR-03: visible progress) → confirm. Thumbnail grid from attachment list; delete action.
6. Generate an encrypted thumbnail client-side (canvas downscale → encrypt → upload to thumbnails bucket) so the grid doesn't need full downloads.

Delivery: Phase 2 T9's `render_capsule_media` now has real rows — the delivery worker must **decrypt media server-side** at trigger time (same CEK it already reconstructs) and re-upload plaintext-temporarily? **No.** Decision per PRD 5.3: worker decrypts content in-memory; for photos, attach/embed by generating a delivery copy: decrypt → upload to a short-lived `deliveries/{trigger_id}/` prefix → signed 30-day URL in email → purge with the 72h cleanup (FR-41 covers it; extend purge prefix list). Embed small photos inline (cid attachments) when total < 5MB, otherwise gallery links. Implement both paths.

## T2 (FR-28) — Video attachment (one per capsule)

1. Same media pipeline, kind=`video`: MP4/MOV, ≤500MB, max one per capsule (validate). Upload from device (in-app recording NOT in scope — consult user if wanted; PRD allows upload path).
2. Chunked/resumable upload via Supabase TUS endpoint (`upload to signed URL` supports x-upsert; for 500MB use tus-js-client against Supabase's resumable endpoint) with progress UI.
3. Client-side encryption of a 500MB file must stream (WebCrypto can't stream AES-GCM natively): encrypt in N-MB chunks with per-chunk IVs (store chunk size + IV scheme in attachment metadata) — implement a documented chunked format in `crypto/media.ts`; the delivery worker implements the mirror decryptor.
4. Thumbnail: capture first frame via `<video>` + canvas, encrypt, upload (FR-28 auto-thumbnail).
5. Delivery email: video = secure download link valid 30 days (signed URL on the decrypted delivery copy, T1 pattern).

## T3 (FR-30) — Preview mode

"Preview" on the capsule view screen (Phase 3 T5.4): renders the capsule using the **same template** the delivery email uses. Implement an authenticated backend endpoint `GET /capsules/{id}/preview` that runs the real delivery renderer (Phase 2 T9 code path) against the user's decrypted-on-client content? No — server can't decrypt without trigger. Implementation: extract the delivery email template (intro copy + capsule layout) into a shared template; frontend renders it client-side with decrypted content inside a clearly-marked "Preview" banner (FR-30). Keep the template in one place consumed by both (backend renders with Jinja-style placeholders; frontend fetches the template HTML via `GET /delivery/template` and fills it client-side) so preview cannot drift from reality.

## T4 (G1 + NFR-04 + FR-37) — PWA: manifest, service worker, offline

1. Add `vite-plugin-pwa`: manifest (name "Legate", short_name, theme color, `display: standalone`, icons 192/512 — generate real icons from the app logo; if none exists, design a simple lettermark SVG → PNGs; no placeholder squares), Workbox `generateSW` precaching the shell + hashed assets, runtime caching: `NetworkFirst` for `/api/capsules*`, `/api/beneficiaries*`, `/api/settings*` GETs (metadata offline, FR-37).
2. Replace `vite.svg` favicon; iOS meta tags (`apple-touch-icon`, status-bar style) for Add-to-Home-Screen (NFR-26).
3. react-query persister (`@tanstack/react-query-persist-client` + IDB) so previously loaded capsule metadata renders offline.
4. **Offline drafts + sync (NFR-04):** the encrypted localStorage drafts (Phase 3 T9) become the offline edit store; add an outbox: capsule saves attempted offline queue `{action, payload}` in IndexedDB and flush on `online` event / app focus, with conflict rule last-write-wins + toast. Editing existing capsules offline uses cached metadata + cached encrypted content (runtime-cache the signed-URL blob fetches, `CacheFirst`, keyed by object path).
5. Offline UI state: global banner "You're offline — changes will sync" when `navigator.onLine` is false.

## T5 (G3) — Onboarding carousel + resumable wizard (FR-07/08/09)

1. 3-screen carousel on first launch (before signup or after first login — PRD: first launch; put it pre-wizard, after verify): value prop / how check-ins work / encryption promise. "Skip" always visible (FR-07). Mark seen in user settings (server-side `onboarding_seen` flag — survives devices), localStorage fallback pre-auth.
2. Wizard resumability (FR-09): persist `setup_step` in user settings via `PATCH /settings` after each completed step; on app open, if setup incomplete → resume at `setup_step`. Add Skip on the capsule step (FR-08 "skippable").
3. Keep existing step order (checkin → beneficiary → capsule → recovery) — matches FR-08.

## T6 (G4 + G9) — Static pages: How it works, Privacy, ToS

1. "How Legate works" (FR-45): plain-language flow explanation + collapsible "Technical details" section (encryption architecture, for Persona A). Route + nav entry.
2. Privacy Policy + Terms of Service pages (NFR-15): real, complete drafts covering GDPR rights (NFR-16), data processing (Supabase/Resend), the non-legal-instrument disclaimer (PRD 4.2). Mark as "draft pending legal review" in a comment, not in the visible page. Footer links on Landing + app settings.

## T7 (G5) — Rate limiting (NFR-10)

1. `slowapi` with Redis storage: default `100/minute` keyed by user id for authenticated routes, `10/minute` by IP for unauthenticated. Stricter buckets: `/auth/login`, `/auth/signup`, `/auth/forgot-password`, `/auth/resend-otp` → `5/minute/IP`; `/checkin/*` token pages → `20/minute/IP`.
2. 429 responses with `Retry-After`; frontend interceptor shows a "Too many attempts" toast.
3. Healthcheck `/health` exempt.

## T8 (G6) — Check-in config completeness

1. FR-11 custom interval: `StepCheckin.tsx` + settings UI gain a "Custom" option with numeric input validated 7–365 (backend bounds already enforced, Phase 2 T13).
2. FR-18 reduce-grace warning: confirmation dialog when the new grace period is shorter than current, explaining delivery fires sooner.

## T9 (G7) — Rich text editor (FR-25)

1. Replace the plain textarea with tiptap (StarterKit limited to bold, italic, bullet list — FR-25 scope), 10,000-char limit with counter.
2. Content stored as sanitized HTML **inside the encrypted blob** (encryption path unchanged).
3. Delivery + preview render the HTML through the sanitizer added in Phase 5 S3 (until then, the Phase 2 escape would mangle rich text — so: implement the `bleach` allowlist sanitizer NOW as part of this task, and Phase 5 S3 verifies/extends it; allowlist: `b,strong,i,em,ul,li,p,br`).
4. Editor view/edit/preview/draft paths all updated (decrypt → tiptap content).

## T10 (G8) — Export recovery phrase as PDF (FR-10)

On `StepRecovery` (and post-regeneration, Phase 3 T4.5): "Download PDF" generating client-side (jsPDF or pdf-lib — bundle, no CDN at runtime) — phrase in a numbered 24-slot grid + warning copy. Generated locally; never uploaded. Plus "Copy" action (FR-10) with clipboard API + confirmation toast.

## T11 (G10) — Check-in settings page section

Settings page section (outside the wizard) to edit interval + grace using `PATCH /settings/checkin` (exists), with T8's custom input + warning dialog. Show current schedule state: last confirmed, next due (FR-44 card already on dashboard — verify; fix if stale fields).

## T12 (G11) — Memorial read-only state (FR-41)

1. `/auth/me` exposes `status`; when `memorialized`: render a memorial banner, disable all mutating UI (create/edit/delete capsule, beneficiary changes, settings) — enforce by gating mutations in the api layer (one place), not by hiding buttons only.
2. Backend already blocks via status checks where relevant — verify `dependencies.py` or service guards reject mutations for memorialized users (`403`); add a shared dependency if missing.

## T-test — Phase 4 E2E (final task — phase gate)

Extend the Playwright suite (live compose stack, real Supabase/Resend):

1. **media.spec** — attach 2 photos (real JPEG fixtures) → progress visible → thumbnails render → reload → thumbnails persist; attach a 21st photo → validation error; attach a small real MP4 → upload completes → thumbnail; delete one photo → gone from grid and storage (assert via API).
2. **delivery-with-media (backend e2e)** — new `tests/e2e/test_13_media_delivery.py`: capsule with photo+video → force trigger (timestamp manipulation, Phase 2 pattern) → delivery email to `delivered@resend.dev` contains an inline/gallery image reference and a video link; fetch the signed video URL → 200 and bytes match the original (decrypted); 30-day expiry parameter present.
3. **pwa.spec** — manifest reachable, SW registers, icons 192/512 exist. Then **Lighthouse**: `npx lighthouse http://localhost --preset=desktop --only-categories=pwa` ≥ 90 (NFR-25); run mobile too.
4. **offline.spec** — Playwright `context.setOffline(true)` after loading dashboard: capsule list still renders (cached metadata); edit a draft offline → go online → outbox flushes → server content updated (assert via API).
5. **onboarding.spec** — fresh signup → carousel shows → skip → wizard; abandon wizard at step 2 → reload → resumes step 2 (FR-09); complete → never shown again.
6. **richtext.spec** — bold/italic/list content survives save → edit → preview; preview shows the delivery template with "Preview" banner; raw `<script>alert(1)</script>` pasted into editor is not present in preview DOM as a script node (sanitizer).
7. **ratelimit (backend e2e)** — `test_14_ratelimit.py`: 6th login attempt within a minute → 429 + `Retry-After`; authenticated burst beyond 100/min → 429.
8. **memorial.spec** — memorialized test user (set via DB) → banner shown, capsule create blocked in UI and returns 403 via direct API call.
9. Static pages: `/how-it-works`, `/privacy`, `/terms` return content and are linked.

**Run:** `docker compose up -d --build` → backend `pytest tests/e2e/ -x -q` → `npm run test:e2e` → Lighthouse. All green + Lighthouse PWA ≥90 = Phase 4 complete. Record results in `## Phase 4 E2E result`.
