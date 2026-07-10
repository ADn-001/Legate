# Legate

Digital estate planning — compose messages for the people you love, delivered when it matters most.

---

## Quick start

**Prerequisites:** Docker Desktop, a [Supabase](https://supabase.com) project, a [Resend](https://resend.com) API key.

```bash
cp .env.example .env
# Fill in the values — see the Environment variables table below

# Build the frontend first — the nginx image copies the pre-built dist/
# (requires Node 20+; VITE_API_BASE_URL=/api is set via frontend/.env.production)
cd frontend && npm ci && npm run build && cd ..

docker compose up -d --build
```

Open **http://localhost** (or `http://localhost:<NGINX_PORT>` if you changed the port).

The first `up --build` takes a few minutes. Subsequent starts without `--build` are fast.

> **Windows / WSL note:** if port 80 is already bound, set `NGINX_PORT=8080` in `.env` before running.

---

## Supabase setup

Complete these steps once in your Supabase project before starting the stack.

### 1. Create three storage buckets

All three must be **private**.

| Bucket name | Purpose |
|---|---|
| `capsule-content` | Encrypted capsule blobs |
| `media-attachments` | Photo and video uploads |
| `thumbnails` | Auto-generated image thumbnails |

### 2. Row Level Security (not needed for this architecture)

> **Note:** the backend accesses the database and storage exclusively with the
> service-role key (or the `postgres` role for direct Postgres connections),
> and the frontend has no direct path to Supabase at all — every request goes
> through the FastAPI backend. RLS protects architectures where a client
> connects to Supabase directly with a scoped JWT; that access pattern doesn't
> exist here, so enabling RLS policies wouldn't add a real security boundary
> on top of the existing FastAPI-layer authorization. This was reassessed
> (not just carried over from an earlier plan) — see
> `implementation/Legate_PRD_v3_0.md` §4.2/§11.3 for the full reasoning. Skip
> this step; nothing else in setup depends on it.

### 3. Enable email OTP auth

In the Supabase Dashboard → **Authentication → Providers → Email**, enable:
- **Enable email sign-ups** ✅
- **Confirm email** ✅ (OTP / magic link)

### 4. Set the password-reset redirect URL

Dashboard → **Authentication → URL Configuration → Redirect URLs**, add:

```
https://<your-host>/auth/reset-password
```

(Locally: `http://localhost/auth/reset-password` or `http://localhost:8080/auth/reset-password`.)

---

## Environment variables

Copy `.env.example` to `.env` and fill in every value. The app refuses to start if any secret is shorter than 32 characters or matches a known placeholder.

| Variable | Required | Description | Where to find it |
|---|---|---|---|
| `DATABASE_URL` | ✅ | Supabase Postgres connection string | Dashboard → Settings → Database → Connection string (URI, port 5432) |
| `SUPABASE_URL` | ✅ | `https://<project-ref>.supabase.co` | Dashboard → Settings → API |
| `SUPABASE_ANON_KEY` | ✅ | Public anon key | Dashboard → Settings → API |
| `SUPABASE_SERVICE_ROLE_KEY` | ✅ | Service-role key — **keep secret** | Dashboard → Settings → API |
| `SUPABASE_JWT_SECRET` | ✅ | JWT signing secret | Dashboard → Settings → API → JWT Secret |
| `RESEND_API_KEY` | ✅ | Resend transactional email key | [resend.com/api-keys](https://resend.com/api-keys) |
| `EMAIL_FROM` | ✅ | Sender address (`noreply@yourdomain.com`) | Must match a verified Resend domain |
| `SECRET_KEY` | ✅ | App signing secret. Generate: `openssl rand -base64 48` | — |
| `DELIVERY_SECRET` | ✅ | CEK wrapping secret. Generate: `openssl rand -base64 48`. **Rotating invalidates all delivery blobs.** | — |
| `BASE_URL` | ✅ | Public URL of the API, as seen by email link recipients. In compose: `http://localhost/api` or `https://your-host/api` | — |
| `FRONTEND_URL` | — | Public URL of the frontend SPA. Used as the Supabase password-reset redirect base. Default: `http://localhost` | — |
| `CORS_ORIGINS` | — | Comma-separated allowed CORS origins. Empty → dev localhost defaults | — |
| `ENVIRONMENT` | — | `development` or `production`. Default: `development` | — |
| `PBKDF2_ITERATIONS` | — | PBKDF2-SHA256 iteration count for key derivation. Default: `100000` | — |
| `SUPABASE_STORAGE_BUCKET_CONTENT` | — | Capsule content bucket name. Default: `capsule-content` | — |
| `SUPABASE_STORAGE_BUCKET_MEDIA` | — | Media attachments bucket name. Default: `media-attachments` | — |
| `SUPABASE_STORAGE_BUCKET_THUMBNAILS` | — | Thumbnails bucket name. Default: `thumbnails` | — |
| `STORAGE_QUOTA_BYTES` | — | Per-user storage quota (bytes). Default: `1073741824` (1 GiB) | — |
| `ALERT_EMAIL` | — | Ops alert address for permanent delivery failures. Empty disables alert emails; audit rows are always written | — |
| `NGINX_PORT` | — | Host port nginx publishes on. Default: `80` | — |
| `DEMO_MODE` | — | When `true`, `PATCH /settings/checkin` accepts minute-level interval/grace/emergency-confirm overrides so a live demo can run the full check-in lifecycle in minutes instead of weeks. Server-enforced (403 when off), not just hidden in the UI. Default: `false` — leave off outside of an active demo | — |
| `BEAT_INTERVAL_SECONDS` | — | Celery beat tick (seconds) for the dispatch/grace/trigger-promotion tasks. Default: `3600` (hourly). Only lower this (e.g. `60`) while `DEMO_MODE` is on — left low permanently, it ticks the grace-period check against every user every minute forever, which is a real cost, not just a demo convenience | — |

---

## Architecture

```
Browser / PWA
     │
     ▼
  nginx (:80)
  ├── /         → serves the React SPA from dist/
  └── /api/*    → proxies (prefix-stripped) to api:8000

api (FastAPI + Uvicorn, 2 workers)
     │
     ├── Supabase (auth, storage)
     ├── PostgreSQL via SQLAlchemy + asyncpg
     └── Redis (task queue / rate-limit)

worker (Celery)       ← consumes tasks from Redis
beat   (Celery beat)  ← enqueues periodic tasks
redis  (Redis 7)      ← broker + result backend
```

`api`, `worker`, and `beat` share the same Docker image (`legate-backend:latest`) built from `backend/Dockerfile`, with different startup commands — no separate builds. `redis` runs the official `redis:7-alpine` image.

### Periodic tasks (beat schedule)

| Task | Interval | Purpose |
|---|---|---|
| `dispatch_due_checkins` | `BEAT_INTERVAL_SECONDS` (default 1 h) | Send check-in emails to users whose `next_dispatch_at` is past |
| `check_grace_periods` | `BEAT_INTERVAL_SECONDS` (default 1 h) | Create release triggers for users whose grace period has expired |
| `process_pending_triggers` | `BEAT_INTERVAL_SECONDS` (default 1 h) | Promote pending-confirmation triggers once the 48 h window elapses |
| `send_grace_period_reminders` | Fixed 12 h (not affected by `BEAT_INTERVAL_SECONDS`) | Send day-3 and day-7 grace-period reminder emails |

The first three all share the same configurable tick (`BEAT_INTERVAL_SECONDS`) — lowering it is what makes demo-mode minute-level schedules actually fire promptly.

### Migrations

`alembic upgrade head` runs automatically in the `api` entrypoint before Uvicorn starts. It is idempotent — safe to re-run on restart or `docker compose down && up`.

> **State across restarts:** the database is managed by Supabase and persists across `docker compose down`. Redis queue state is lost on `down -v`, but beat re-enqueues all periodic tasks within one schedule interval.

---

## Dev workflow

### Docker Compose (recommended)

```bash
# Production-like compose (same image as deployment):
docker compose up -d --build

# Development compose (hot reload for API + worker):
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

The dev override mounts `./backend` into the containers and swaps the API command to `uvicorn --reload`.

### Local (no Docker)

**Backend:**
```bash
cd backend
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill values
alembic upgrade head
uvicorn app.main:app --port 8000 --reload
```

**Frontend:**
```bash
cd frontend
npm install
VITE_API_BASE_URL=http://localhost:8000 npm run dev
```

**API docs:** http://localhost:8000/docs (Swagger UI, available in development mode).

---

## Manual testing guide (legate.one)

For reviewers testing the live deployment rather than running the stack locally. Full detail, including a complete feature-by-feature walkthrough and known limitations, is in `implementation/Legate_Testers_Guide.md` — this is the condensed version.

**The live site currently runs with demo scheduling on** and will stay that way for the assessment period, so check-in intervals/grace periods/emergency-contact windows can be set in minutes instead of real days, letting you watch a full signup → check-in → missed check-in → delivery cycle complete in one sitting.

### Read this before you sign up

Legate creates your account record the moment you submit the signup form, **before** email verification. If you don't finish verification (expired code, closed the tab, etc.), that email is permanently stuck — there's no cleanup job, and any later signup with the same email fails with "Email already registered."

- Stuck on the code screen with an expired/wrong code? Use **Resend** on that same screen — safe, doesn't create a new account.
- Need a fresh account, or already navigated away? Use a **plus-alias** — most providers treat `you+anything@domain.com` as your real inbox, but Legate treats it as a distinct account:
  - `jane.doe@gmail.com` → `jane.doe+test1@gmail.com`, `jane.doe+test2@gmail.com`, etc.
  - You'll want at least two working addresses/aliases: one to test as yourself, one to add as a beneficiary so you can see what a recipient actually receives.

### Core things to test

1. **Signup + verification** — weak-password rejection, OTP entry, resend, and (expected, not a bug) the duplicate-email 409 above.
2. **Onboarding wizard** — check-in interval/grace period, the amber "Demo scheduling (minutes)" panel + Apply Demo Schedule, adding a beneficiary (try both the Emergency Contact and Notify by Email toggles), creating a first capsule with a photo/video attachment and using Preview, and the 24-word recovery phrase (save it — there's no way to view the original again later).
3. **Dashboard** — vault status pill, check-in dates, capsule/beneficiary counts.
4. **Capsules** — create/edit/delete from `/vault/capsules`, media attachments, autosave draft indicator.
5. **Beneficiaries** — add/edit/remove, emergency-contact reassignment warning, silently-added badge.
6. **Full check-in lifecycle** — confirm via the emailed link (confirmation page should report the interval in **minutes** during demo mode), let a cycle lapse into grace, test the emergency-contact pause link, and confirm delivery actually lands in the beneficiary's inbox and the sender's account becomes memorialized/read-only afterward.
7. **Security settings** — password change, recovery-phrase regenerate (replaces, doesn't reveal, the old one), forgot-password flow, logout, and delete account (immediate lockout, full erasure within 72 hours — not instant, by design).
8. **Activity log** and **PWA install** (Android: **⋮ menu → Install app**, not the address bar).

### Known limitations (documented, not bugs)

No native mobile app (PWA only, by design), recovery phrase is regenerate-only, no database-level Row Level Security (all authorization is in the app layer — deliberate, since the browser never talks to the database directly), no independent pen-test or formal accessibility audit, no CI/CD (manual deploys), single-server hosting, Cloudflare-edge-IP rate-limit bucketing, no email-change or capsule-reorder UI, delivered media links expire after 3 days. Full rationale for each is in `implementation/Legate_Testers_Guide.md` and `implementation/Legate_PRD_v3_0.md`.

---

## Testing

### Backend unit tests

```bash
docker compose exec api pytest tests/ -q --ignore=tests/e2e
```

### Backend E2E tests (real Supabase + Resend, ~70 min on free tier)

```bash
docker compose exec api pytest tests/e2e/ -q
```

Runs suites 01–16 covering health, auth, beneficiaries, capsules, check-in settings/tokens/lifecycle, activity, users, Celery tasks, security hardening, Supabase integration, media delivery, rate limiting, and demo mode. Requires real credentials in `.env`.

### Frontend unit tests

```bash
cd frontend && npm run test
```

### Frontend Playwright E2E

Requires a running compose stack and real Supabase credentials loaded from `backend/.env`.

```bash
cd frontend
npm run test:e2e
# Override the base URL if nginx is on a non-standard port:
E2E_BASE_URL=http://localhost:8080 npm run test:e2e
```

### Run everything (CI / pre-ship)

There is no single CI script in this repo (no CI/CD pipeline exists — deploys are manual). Run the suites above in this order:

```bash
docker compose up -d --build
docker compose exec api pytest tests/ -q --ignore=tests/e2e
docker compose exec api pytest tests/e2e/ -q
cd frontend && npm run test && npm run test:e2e && cd ..
```

### Lighthouse (NFR-25 — PWA ≥ 90)

```bash
# Install once:
npm install -g @lhci/cli

# Run against the live stack:
lhci autorun --collect.url=http://localhost --collect.numberOfRuns=1
```

Target: PWA score ≥ 90 on both desktop and mobile emulation.

---

## §9 Regression test coverage

| Requirement | Test file | Test function |
|---|---|---|
| B1 — no double-dispatch per cycle | `backend/tests/e2e/test_12_checkin_lifecycle.py` | `test_b1_dispatch_runs_twice_sends_once` |
| B2 — exactly one trigger per missed cycle | `backend/tests/e2e/test_12_checkin_lifecycle.py` | `test_b2_grace_expiry_creates_exactly_one_trigger` |
| B4 — confirm fully resets pause state | `backend/tests/e2e/test_12_checkin_lifecycle.py` | `test_b4_confirm_resets_pause_state_and_dispatch_resumes` |
| F1 — signup → verify → login flow | `frontend/e2e/signup-verify-login.spec.ts` | (full spec) |
| S4 — check-in token single-use + expiry | `backend/tests/e2e/test_15_security.py` | S4 block |
| B9/B10 — purge deletes nested storage objects | `backend/tests/e2e/test_12_checkin_lifecycle.py` | `test_b9_b10_full_account_purge` |

---

## Documented deviations from PRD / ideal practice

Full rationale for each deviation is in `docs/SECURITY.md`.

### DB single-use tokens (deviation from NFR-12 Redis blacklist)

NFR-12 calls for a Redis blacklist to prevent token replay. Legate uses DB-backed single-use tokens instead: each token's `status` column is mutated to `used` in the same transaction as the action it authorises. This is race-safe (no TOCTOU window) and does not require Redis to be up for token invalidation to work. Tokens are 64-byte URL-safe random strings with a 7-day `expires_at`.

### Recovery-phrase re-display = regenerate, not reveal (FR-35)

FR-35 asks for re-display of the existing recovery phrase. That's not actually possible: the 24-word phrase itself is never stored anywhere, by design — only a one-way derived blob used to validate a submitted phrase, and a copy of the CEK wrapped under a key derived from the phrase. Neither of those can be reversed back into the original words. So "view my recovery phrase again" in Security settings is implemented as **regenerate**, not reveal: after confirming your password, it generates a brand-new 24-word phrase (`bip39Module.generatePhrase()`), re-wraps your existing CEK under it, and immediately invalidates the old phrase — the UI is explicit about this ("Your old recovery phrase stops working as soon as you confirm"). This is a deliberate, cryptographically-necessary deviation from a literal reading of FR-35, not a partial implementation of phrase re-display.

### Backend-rendered check-in pages (GET mutations)

`GET /checkin/confirm`, `GET /checkin/snooze`, and `GET /checkin/emergency/pause` mutate state via GET because email clients cannot trigger POST requests from hyperlinks. CSRF risk is negligible: these endpoints authenticate by possession of the 64-byte opaque token (≥ 512 bits of entropy) and tokens are single-use, so a CSRF attack would require the attacker to already possess the token value.

---

## Operational notes

### DELIVERY_SECRET rotation

**Rotating `DELIVERY_SECRET` is destructive.** All existing `delivery_encrypted_cek` blobs were wrapped under the old key. After rotation the delivery worker cannot decrypt them and all pending deliveries will fail permanently. Re-wrap existing blobs before rotating.

### docker compose down and up

`docker compose down` stops all containers. `docker compose up -d` restarts them. Database state persists (Supabase is managed). Redis queue state is cleared on `down -v`; Celery beat re-enqueues all periodic tasks within one schedule interval. This behaviour is acceptable and documented.

### Recreating `api` without nginx serving stale 502s

`nginx.conf` proxies to the `api` container by hostname (`proxy_pass http://api:8000/`), which nginx resolves to a container IP **once, at its own startup** — it does not re-resolve afterward. `docker-compose.yml`'s `depends_on: api: restart: true` is meant to auto-restart nginx whenever `api` is recreated, but this only fires reliably on a full `docker compose up`. If you manually recreate a subset of services, e.g.:

```bash
docker compose up -d --force-recreate api worker beat
```

`api` gets a **new** container IP on the docker network, nginx keeps the old one, and every request 502s ("connection refused") until nginx is restarted. Always include `nginx` in the same command:

```bash
docker compose up -d --force-recreate api worker beat nginx
```

or, if you forget and it's already broken: `docker compose restart nginx`.

### Logs

```bash
docker compose logs -f api
docker compose logs -f worker
docker compose logs -f beat
```

No sensitive data (CEK bytes, plaintext capsule content, wrapping keys) is written to any log stream. See `docs/SECURITY.md §6` for the full NFR-09 audit.
