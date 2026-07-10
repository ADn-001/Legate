# Phase 6 — Docker Deliverable Finalization + Full-System E2E

**Covers audit items:** §6 of `AUDIT_REPORT.md` (concrete Docker file plan — items not already landed in Phase 1) + §8 step 6 (final verification) + §9 test-suite notes.
**Assumes:** Phases 1–5 are 100% complete. Phase 1 already created `frontend/Dockerfile`, the nginx config, compose fixes, entrypoint migrations, `.dockerignore`s, and env examples. This phase finalizes the deliverable after four phases of changes landed on top, rewrites the README, and runs the whole-product acceptance E2E.
**Goal:** A stranger with the repo + a filled `.env` gets a fully working product with two commands, and every PRD launch gate that is testable pre-launch passes.
**Rules:** No mocks. The final E2E exercises the real deployed stack, real Supabase, real Resend, a real browser.

---

## T1 — Reconcile compose/env with everything Phases 2–5 added

Drift audit — go through every config setting added since Phase 1 and ensure each is in: `config.py` (typed), compose `environment:` blocks where needed, root `.env.example`, `backend/.env.example`:
`ALERT_EMAIL` (P2-T8), `storage_quota_bytes` (P2-T13), recovery-key columns need no env, rate-limit settings if configurable (P4-T7), `ROOT_PATH`, `CORS_ORIGINS`, bucket names, `PBKDF2_ITERATIONS`. Remove any var that no longer exists. `docker compose config` must resolve cleanly with zero warnings.

## T2 — Image hygiene re-check

1. Rebuild from clean (`docker compose build --no-cache`); confirm `.dockerignore`s still exclude `tests/`, `.env`, `scripts/get_test_otp.py` (added Phase 3), `playwright` artifacts, `node_modules`.
2. Confirm `backend/celerybeat-schedule` is not in git (`git ls-files | grep celerybeat` → empty) and gitignored.
3. Verify the frontend image contains the PWA assets (manifest, SW, icons) — `docker run --rm <nginx-image> ls /usr/share/nginx/html` shows `manifest.webmanifest`, `sw.js`, icons.
4. Image sizes sane (api < ~600MB, frontend < ~80MB) — flag anomalies.

## T3 — README rewrite (two-command deploy)

Replace dev-era instructions with the real story:
1. **Quick start:** prerequisites (Docker, a Supabase project, a Resend key) → `cp .env.example .env` (fill values — table of every var with one-line meaning, links to where to find Supabase keys) → `docker compose up -d --build` → open `http://localhost`.
2. Supabase setup section: required buckets (3 names), how to apply `supabase/rls_policies.sql`, auth settings (email OTP enabled, password-reset redirect URL → `https://<host>/reset-password`).
3. Dev workflow: `docker compose -f docker-compose.yml -f docker-compose.dev.yml up`; local non-docker dev (uvicorn + vite) kept as secondary.
4. Testing section: how to run unit, backend e2e, Playwright, Lighthouse — with the env each needs.
5. Architecture sketch (nginx → SPA + `/api` proxy → api/worker/beat/redis; Supabase managed).
6. Documented deviations (from `docs/SECURITY.md`): DB single-use tokens (NFR-12), recovery-phrase re-display = regenerate (FR-35), backend-rendered check-in pages.

## T4 — Operational acceptance per audit §6

Acceptance line from the audit, verified literally: `docker compose up --build` → `/health` 200, frontend loads, signup→verify→capsule→checkin e2e passes against real Supabase creds. Additionally:
1. Restart resilience: `docker compose restart` — all services healthy again, no migration errors on re-run.
2. `docker compose down && up -d` — state survives (DB is managed; redis queue loss acceptable — beat re-enqueues; document).
3. Logs clean: 10 minutes of runtime, no recurring errors/tracebacks in any service.
4. Beat schedule sanity: `docker compose logs beat` shows the three periodic tasks registered at 1h/1h/12h.

## T5 — Test-suite consolidation (§9)

1. Confirm the §9 must-have regression tests all exist and are green: B1 no-double-dispatch, B2 no-re-trigger, B4 unpause-on-confirm, F1 login flow (Playwright spec 1–2), token single-use, purge deletes nested storage objects. Map each to its test file in a table inside this section when done.
2. `frontend/package.json` has `"test": "vitest run"` (Phase 1) and `"test:e2e"` (Phase 3) — both wired into the final run below.
3. Add a top-level `scripts/run_all_tests.sh` that runs every suite in order and fails fast (used by T6).

## T6 — FINAL FULL-SYSTEM E2E (final task — project gate)

Run on a clean machine state (`docker compose down -v`, prune images) with real `.env`:

```bash
scripts/run_all_tests.sh   # implements the following, fail-fast:
```
1. `docker compose build --no-cache && docker compose up -d` → all services healthy ≤ 120s.
2. Backend: `docker compose exec api pytest tests/ -q` (unit, real DB) and `pytest tests/e2e/ -q` (suites 01–15 incl. lifecycle, media-delivery, ratelimit, security).
3. Frontend: `npm run lint && npm run test && npm run build && npm run test:e2e` (full Playwright suite, Phases 3–5 specs).
4. Lighthouse: PWA ≥ 90 desktop AND mobile emulation (NFR-25); record scores.
5. **Manual golden-path walkthrough** (scripted checklist, performed in a real browser, results recorded):
   a. Signup (name/email/password policy enforced, FR-01) → OTP (FR-02) → onboarding carousel (FR-07) → wizard all 4 steps incl. recovery phrase PDF download (FR-08/10).
   b. Add beneficiary → nomination email received (real inbox) with no content/count leakage (FR-19/20). Set as emergency contact.
   c. Create rich-text capsule with 3 photos + 1 video (FR-25/27/28); autosave indicator; reload mid-edit → draft restored encrypted (FR-26).
   d. Edit capsule (Phase 3) → preview (FR-30) → view.
   e. Check-in: shrink interval via settings (custom value + grace warning, FR-11/18); force dispatch (timestamp); receive email; confirm link → confirmation page with real interval (FR-13); dashboard card updates (FR-44).
   f. Snooze path: force dispatch → snooze +7 from email → allowance shown; 3rd snooze rejected (FR-14).
   g. Grace path: force overdue → day-3 + day-7 reminders (timestamps) (FR-16) → emergency contact gets 48h pause email (FR-23) → pause extends (FR-24) → confirm → fully reset (B4).
   h. Delivery: let a second test account trigger fully → ONE email per beneficiary, capsules in order, photos inline/gallery, video 30-day link, FR-40 copy (FR-38–40) → account memorialized, UI read-only (FR-41/G11) → storage purged ≤72h path verified by running the purge task directly and re-listing prefixes.
   i. Recovery: forgot password → magic link → recovery phrase unlocks → content decrypts with new password (FR-03/35, R-02).
   j. GDPR delete: type DELETE + password → rows + storage + auth user gone (FR-05).
   k. PWA: install on Android Chrome or desktop Chrome; offline relaunch shows cached metadata (FR-37/NFR-26).
6. Cross-check: every P0 FR/NFR in the PRD §6–7 mapped to either a passing automated test or a checklist line above; any consciously-deferred item (P1s out of scope, pen-test NFR-11, beta-population gates) listed under "Deferred / out of v1 scope" with a one-line reason.

**Acceptance:** steps 1–5 all green, step 6 table complete with zero unexplained gaps. Record the full run log + Lighthouse scores + the FR coverage table in `## Final E2E result` at the bottom of this file. The project is "100% complete per audit + PRD-P0 (+FR-28/30/NFR-04)" only when this section is filled in with passing results.
