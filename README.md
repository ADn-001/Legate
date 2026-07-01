# Legate

Digital estate planning — compose messages for the people you love, delivered when it matters most.

---

## Quick start

**Prerequisites:** Docker Desktop, a [Supabase](https://supabase.com) project, a [Resend](https://resend.com) API key.

```bash
cp .env.example .env
# Fill in the values — see the Environment variables table below
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

### 2. Apply RLS policies

```bash
# From the project root — requires psql on PATH, or paste the file into
# the Supabase SQL editor (Dashboard → SQL Editor → New query).
psql "$DATABASE_URL" -f supabase/rls_policies.sql
```

### 3. Enable email OTP auth

In the Supabase Dashboard → **Authentication → Providers → Email**, enable:
- **Enable email sign-ups** ✅
- **Confirm email** ✅ (OTP / magic link)

### 4. Set the password-reset redirect URL

Dashboard → **Authentication → URL Configuration → Redirect URLs**, add:

```
https://<your-host>/reset-password
```

(Locally: `http://localhost/reset-password` or `http://localhost:8080/reset-password`.)

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
     ├── Supabase (auth, RLS, storage)
     ├── PostgreSQL via SQLAlchemy + asyncpg
     └── Redis (task queue / rate-limit)

worker (Celery)       ← consumes tasks from Redis
beat   (Celery beat)  ← enqueues periodic tasks
redis  (Redis 7)      ← broker + result backend
```

All four backend services (`api`, `worker`, `beat`, `redis`) share the same Docker image (`legate-backend:latest`) built from `backend/Dockerfile`. Only `redis` uses a separate image.

### Periodic tasks (beat schedule)

| Task | Interval | Purpose |
|---|---|---|
| `dispatch_due_checkins` | 1 h | Send check-in emails to users whose `next_dispatch_at` is past |
| `check_grace_periods` | 1 h | Create release triggers for users whose grace period has expired |
| `process_pending_triggers` | 1 h | Promote pending-confirmation triggers once the 48 h window elapses |
| `send_grace_period_reminders` | 12 h | Send day-3 and day-7 grace-period reminder emails |

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

## Testing

### Backend unit tests

```bash
docker compose exec api pytest tests/ -q --ignore=tests/e2e
```

### Backend E2E tests (real Supabase + Resend, ~70 min on free tier)

```bash
docker compose exec api pytest tests/e2e/ -q
```

Runs suites 01–15 covering auth, beneficiaries, capsules, check-in lifecycle, media delivery, rate limiting, and security hardening. Requires real credentials in `.env`.

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

```bash
bash scripts/run_all_tests.sh
```

Builds the stack from scratch, runs all suites in order, fails fast on the first error. See `scripts/run_all_tests.sh` for the full sequence.

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

### Recovery-phrase re-display = regenerate (FR-35)

FR-35 asks for re-display of the existing recovery phrase. The recovery phrase is derived from the CEK, which is zero-knowledge (never stored server-side in plaintext). The backend cannot reconstruct it. Displaying it again requires the user to be authenticated and their CEK to be in browser memory. The implemented flow is: re-derive phrase from in-memory CEK → show phrase → user may download PDF. This is functionally equivalent; it does not produce a new phrase.

### Backend-rendered check-in pages (GET mutations)

`GET /checkin/confirm`, `GET /checkin/snooze`, and `GET /checkin/emergency/pause` mutate state via GET because email clients cannot trigger POST requests from hyperlinks. CSRF risk is negligible: these endpoints authenticate by possession of the 64-byte opaque token (≥ 512 bits of entropy) and tokens are single-use, so a CSRF attack would require the attacker to already possess the token value.

---

## Operational notes

### DELIVERY_SECRET rotation

**Rotating `DELIVERY_SECRET` is destructive.** All existing `delivery_encrypted_cek` blobs were wrapped under the old key. After rotation the delivery worker cannot decrypt them and all pending deliveries will fail permanently. Re-wrap existing blobs before rotating.

### docker compose down and up

`docker compose down` stops all containers. `docker compose up -d` restarts them. Database state persists (Supabase is managed). Redis queue state is cleared on `down -v`; Celery beat re-enqueues all periodic tasks within one schedule interval. This behaviour is acceptable and documented.

### Logs

```bash
docker compose logs -f api
docker compose logs -f worker
docker compose logs -f beat
```

No sensitive data (CEK bytes, plaintext capsule content, wrapping keys) is written to any log stream. See `docs/SECURITY.md §6` for the full NFR-09 audit.
