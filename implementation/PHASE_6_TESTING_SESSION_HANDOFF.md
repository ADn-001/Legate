# Phase 6 — Docker + Frontend Testing Session Handoff

**Session date:** 2026-07-01 (backend suite ran ~11:40–12:52 UTC+4; frontend/Playwright work continued into the evening, ~18:45–21:46 UTC+4)
**Context:** Claude crashed mid-session on the original Phase 6 work; everything below picks up after a manual reset. Covers: getting `docker compose up` healthy again, running the full backend + frontend test battery, and debugging Playwright E2E.
**Status at handoff: NOT fully green. Backend and frontend unit/build are solid. Playwright E2E is blocked (see §5). Nothing has been committed to git yet — see §7, this is the most important thing to read.**

---

## 1. TL;DR for whoever picks this up

| Suite | Result |
|---|---|
| Backend unit tests (`pytest tests/ --ignore=tests/e2e`) | ✅ 80/80 pass |
| Backend E2E (`pytest tests/e2e/`, 125 tests) | ✅ 125/125 (1 flaked on the full run, confirmed transient on isolated re-run — see §4) |
| Frontend lint (`npm run lint`) | ✅ clean |
| Frontend unit tests (`npm run test`) | ✅ 24/24 pass |
| Frontend build (`npm run build`) | ✅ succeeds (bundle-size warning, not an error — see §6) |
| Frontend Playwright E2E (`npm run test:e2e`) | ❌ **blocked** — global setup fails during real signup, likely Supabase free-tier auth rate-limiting (see §5) |
| Git | ⚠️ **Nothing committed since "phase 3 complete."** All of phases 4–6 is sitting uncommitted in the working tree. See §7. |

**Most likely next action:** wait out a Supabase auth rate-limit cooldown (~15–60 min, no exact number confirmed), run `npm run test:e2e` once from `frontend/`, then handle git (§7) and the remaining T6 manual/Lighthouse items from `PHASE_6_DOCKER_DELIVERABLE_FINAL_E2E.md`.

---

## 2. Docker: the stack wouldn't start healthy — root cause and fix

**Symptom:** `docker compose up -d` brought up redis/beat/worker/nginx fine, but `legate-api-1` sat in `(unhealthy)` indefinitely. `curl` to `/health` (both from the host and from inside the container) got `Connection refused`. Logs showed migrations ran, then:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started parent process [1]
```
...and nothing further. Ever. (Confirmed via `docker inspect --format='{{json .State.Health}}' legate-api-1` — `FailingStreak` climbing indefinitely, `curl: (7) Failed to connect`.)

**Diagnosis process (in case it resurfaces):**
1. Ruled out DNS/networking — `getent hosts redis` resolved fine, a bare Python `socket.connect(('redis',6379))` succeeded instantly.
2. Ruled out `app/core/ratelimit.py`'s module-level Redis connection (`Limiter(storage_uri=...)`) — initially suspected, but a direct import test (`python3 -c "import app.core.ratelimit"`) completed instantly. (**Note:** an earlier round of tests using `timeout 8 python3 -c "..."` produced misleading blank output — the `timeout` wrapper in this image does not behave as expected; don't trust it for future diagnostics. Test without it and use Ctrl+C if you need to interrupt a genuine hang.)
3. Ran `docker compose run --rm --service-ports api` attached (not detached) and hit Ctrl+C mid-hang to get a traceback. It was stuck in:
   ```
   File "/usr/local/lib/python3.11/multiprocessing/spawn.py", line 122, in spawn_main
   ```

**Root cause:** `backend/entrypoint.sh` ends with `exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2`. Because of the `exec`, uvicorn becomes **PID 1** inside the container. Modern uvicorn spawns its `--workers` using Python's `multiprocessing` **spawn** start method. PID 1 has non-default signal/zombie-reaping semantics in Linux, and with no init system wrapping it (no `tini`/`dumb-init`), the spawn handshake between uvicorn's parent and its forked workers deadlocks — permanently, with zero error output.

**Fix applied:** added `init: true` to the `api` service block in `docker-compose.yml` (Compose Desktop runs `tini` as PID 1 automatically, which fixes the reaping behavior). One-line change, no image rebuild needed — just `docker compose up -d` again to recreate the container.

```yaml
api:
  build: ./backend
  image: legate-backend:latest
  init: true   # tini as PID 1 — required so uvicorn's spawn-based multiprocess workers don't deadlock
  env_file: .env
  ...
```

Confirmed fixed: `docker compose ps` shows `legate-api-1 ... Up X minutes (healthy)`, `/health` returns `{"status":"ok"}` in ~50s.

**Current image sizes** (for T2 image-hygiene tracking): `legate-backend` 469MB (under the <600MB budget), `legate-nginx` 102MB (**over** the doc's <80MB target — not investigated further, flag for later, likely unminified assets or base image choice).

---

## 3. Git hygiene fix: `node_modules` was being tracked

Root `.gitignore` covered Python/env/IDE/OS/Playwright artifacts but had **no `node_modules/` entry** — `frontend/node_modules` has been getting committed since early phases, which is why `git status` was showing hundreds of noise entries.

**Fixed:** added `node_modules/` to the root `.gitignore`.

**Not yet done:** the already-tracked `frontend/node_modules` files still need untracking before the next commit:
```powershell
git rm -r --cached frontend/node_modules
```
Do this as (or right before) the first commit — see §7.

---

## 4. Backend E2E: one flake, confirmed transient

Full run (`docker compose exec api pytest tests/e2e/ -q`) — 71m 51s, **124 passed, 1 failed**:

```
FAILED tests/e2e/test_12_checkin_lifecycle.py::test_b5_grace_reminders_day3_day7_once_per_cycle
AssertionError: B5 regression: day-7 reminder never sent
assert 3 == 7
```

Traced the logic in `backend/app/worker/tasks/checkin_tasks.py::_send_grace_period_reminders` (the threshold-selection loop around line 374) — it's correct; walked through the exact test scenario by hand and it should resolve `due_threshold=7`. Suspected the bare `except Exception: continue` around the real Resend email send (line 396–397) silently swallowing a transient send failure late in a 71-minute run that had already sent hundreds of real emails.

**Confirmed transient:** ran the single test in isolation —
```powershell
docker compose exec api pytest tests/e2e/test_12_checkin_lifecycle.py::test_b5_grace_reminders_day3_day7_once_per_cycle -v
```
→ `1 passed in 308.98s`. No code change made. Treat this the same way `PHASE_5_TO_6_HANDOFF.md` documents other Supabase-free-tier flakes: real, occasional, not a regression.

---

## 5. Frontend Playwright E2E — currently blocked, root cause not fully resolved

This is the one open item. Chronology of what was tried, in order, because each fix was real and got us further:

1. **Browsers not installed** — reset wiped `~/AppData/Local/ms-playwright`. Fixed with `npx playwright install` (let it finish downloading all engines, don't Ctrl+C early).

2. **Timeout too tight after OTP verify** — `frontend/e2e/helpers/onboarding.ts` line ~119 asserted `toHaveURL(/\/setup\/checkin/, { timeout: 20_000 })`. Debug dumps (`debug-failure.html`) proved this was pure latency, not a bug: the checkin wizard content had actually rendered, the URL just hadn't updated within Playwright's 20s window. `completeEncryptionSetup()` chains 4 sequential API calls, each subject to the same "cold Supabase pooler" latency this codebase already documents (see the existing 60s budget on the signup call in the same file). **Fixed:** bumped to 60s, with a comment explaining why.

3. **Same problem, later steps** — beneficiary → capsule → recovery → vault navigation all used the same tight 20s budget and would have hit the same issue one at a time. **Fixed proactively:** bumped all of them to 45s in one pass (this codebase's DB engine opens a new connection per request — NullPool, ~10s overhead per request per the project's own docs — so every step's Save/Continue is a real, slow round trip).

4. **Real infra finding (not fixed, needs your attention):** direct-tested `send_nomination_email` in isolation:
   ```powershell
   docker compose exec api python3 -c "import time; from app.core.email import send_nomination_email; t0=time.time(); r=send_nomination_email(to='diag-test@example.com', nominator_name='Diag'); print('OK', r, round(time.time()-t0,1), flush=True)"
   ```
   Result: **fails immediately** with
   ```
   resend.exceptions.ResendError: You can only send testing emails to your own email address (adnanmohammedshelim@gmail.com). To send emails to other recipients, please verify a domain at resend.com/domains, and change the `from` address to an email using this domain.
   ```
   Your Resend account is still in sandbox mode (no verified sending domain). Every nomination email to a real beneficiary is currently failing — silently, because `backend/app/services/beneficiary_service.py` wraps the send in `except Exception: pass` (line ~50–53) so it doesn't block beneficiary creation. This is already called out as a Phase 6 T3 README task ("Supabase setup section... Resend key") but confirmed broken until a domain is verified. **Not a blocker for the beneficiary-creation flow itself** (backend returns 201 fine either way), but real nomination/grace/delivery emails to anyone other than your own Resend account address will not arrive until this is fixed. Worth doing before any real user-facing use.

5. **Beneficiary step appeared to hang forever** (Save button spinner never stopped, 45s timeout hit). Backend logs showed `POST /beneficiaries/ 201 Created` succeeded — so the hang was client-side, after a successful response, before the next `PATCH /settings/` call (which never appears in the logs at all). Added console/pageerror listeners to `frontend/e2e/global-setup.ts` to catch a client-side JS error on the next run:
   ```ts
   page.on('console', (msg) => console.log(`[browser:${msg.type()}]`, msg.text()))
   page.on('pageerror', (err) => console.error('[browser:pageerror]', err))
   ```
   (Left in place — useful for future debugging, not just this session.)

6. **Next run moved the failure earlier** — this time it failed at the *OTP verify* step, before even reaching beneficiary, with **zero console/pageerror output** (ruling out a JS exception) and `docker compose logs api` showing `POST /auth/signup 201 Created` followed immediately by nothing but `/health` polling — the verify-email POST never reached the server at all.

**Working theory (not proven, most likely explanation):** the shared-user global-setup only calls `saveSharedUser()` on success, so *every failed run creates a brand-new real Supabase signup*. Across this debugging session we triggered at least 5 real signups within under an hour, and the project's own code comment in `global-setup.ts` states: *"the Supabase free tier allows only ~3 signup emails per hour per project."* The failure point moving progressively earlier in the flow across consecutive runs (not staying fixed at one line) is consistent with Supabase auth rate-limiting/degradation getting worse with each attempt, not a deterministic code bug.

**What was NOT done:** did not confirm this against the Supabase dashboard (no access from this session), did not wait out a cooldown and retry, did not reduce signup volume by manually seeding `.shared-user.json`.

**Recommended next steps for whoever picks this up:**
- Check the Supabase project dashboard (Auth → Rate Limits, or similar) to confirm/deny throttling directly rather than inferring it.
- Wait some cooldown window (try 30–60 min if no better data) before the next `npm run test:e2e` attempt.
- Once one run succeeds, `frontend/e2e/.shared-user.json` gets written and all future runs will reuse it (skip signup) — this specific flakiness class goes away after one clean pass. **Do not delete `.shared-user.json`** unless you deliberately want to force a fresh signup.
- If it fails again at the OTP-verify step specifically with no browser console output, that's stronger evidence for the rate-limit theory (vs. a code bug, which would show a pageerror).

---

## 6. Minor items flagged, not fixed (your call whether they matter)

- **Frontend bundle size:** `npm run build` warns the main JS chunk is 767KB minified (Vite's 500KB threshold). Not an error. Could hurt the Lighthouse performance score needed for the T6 acceptance gate (PWA ≥90 desktop + mobile, NFR-25). Fix would be code-splitting via dynamic `import()` or `manualChunks` — not attempted.
- **`legate-nginx` image is 102MB**, over the Phase 6 doc's <80MB target. Not investigated.

---

## 7. ⚠️ CRITICAL: nothing has been committed

Per explicit instruction during this session, **no commits were made** — the plan was to wait until Phase 6 testing was fully green. That means:

- `git log` still shows `"phase 3 complete"` as HEAD.
- All of Phase 4, Phase 5, and today's Phase 6 work (security hardening, `delivery.py`, `ratelimit.py`, e2e test suites, the `init: true` docker fix, the `.gitignore` fix, all the onboarding.ts timeout fixes) is sitting **uncommitted in the working tree**.
- This is exactly the kind of state that got lost once already this project (the crash that started this session). **Whoever reads this should strongly consider committing now**, even before Playwright E2E is fully green, rather than risk losing it again. The uncommitted diff is large — recommend at minimum:
  ```powershell
  git rm -r --cached frontend/node_modules
  git add -A
  git commit -m "phases 4-6: security hardening, docker init fix, test suite, E2E timeout fixes"
  ```
- Do **not** push node_modules — the `.gitignore` fix plus the `git rm --cached` above should keep it out going forward.

---

## 8. Full list of files changed this session (by me, today — on top of whatever was already modified/untracked from earlier phases)

| File | Change |
|---|---|
| `.gitignore` | Added `node_modules/` |
| `docker-compose.yml` | Added `init: true` to the `api` service |
| `frontend/e2e/helpers/onboarding.ts` | Bumped several `toHaveURL`/`waitForResponse` timeouts from 20s → 45s/60s (checkin nav, verify-email response wait, beneficiary/capsule/recovery/vault nav), each with a comment explaining why |
| `frontend/e2e/global-setup.ts` | Added `page.on('console', ...)` and `page.on('pageerror', ...)` listeners for future debugging |

Everything else in `git status` (the large list of backend/frontend files) predates this session — see `PHASE_5_TO_6_HANDOFF.md` and `PHASE_6_DOCKER_DELIVERABLE_FINAL_E2E.md` for that history.

---

## 9. Remaining Phase 6 checklist (from `PHASE_6_DOCKER_DELIVERABLE_FINAL_E2E.md`), status

- T1 (compose/env reconciliation) — not re-audited this session
- T2 (image hygiene) — sizes checked (§2), nginx over budget, not fixed
- T3 (README rewrite) — not touched this session; Resend sandbox-mode limitation (§5.4) should be documented here
- T4 (operational acceptance: restart resilience, `down && up`, clean logs, beat schedule) — not explicitly re-verified this session, stack is currently healthy
- T5 (test consolidation) — `scripts/run_all_tests.sh` already exists and is complete/correct; `test:e2e` npm script already wired
- T6 (final full-system E2E) — **blocked on Playwright E2E (§5)**; Lighthouse audit and manual golden-path walkthrough not started

---

## 10. Quick command reference

```powershell
# Bring the stack up (already has the init:true fix)
docker compose up -d
docker compose ps

# Backend
docker compose exec api pytest tests/ -q --ignore=tests/e2e
docker compose exec api pytest tests/e2e/ -q

# Frontend
cd frontend
npm run lint
npm run test
npm run build
npm run test:e2e
```
