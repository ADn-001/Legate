# Phase 1 — Deploy Blockers (Docker)

**Covers audit items:** D1–D11 (§1 of `AUDIT_REPORT.md`)
**Assumes:** Nothing — this is the first phase. Repo state as audited 2026-06-11.
**Goal:** `docker compose up -d --build` produces a working stack: nginx serving the built frontend at `/`, API proxied at `/api/`, worker + beat + redis running, migrations applied.
**Rule:** No stubs, no mock code, no placeholder configs. Every file written here must be production-real and verified by the E2E task (T12) before this phase is marked complete.

## Locked architecture decisions (do not deviate without consulting user)

1. **Routing model:** nginx serves the SPA at `/` and proxies `/api/` → `api:8000` **stripping the `/api` prefix** (trailing-slash `proxy_pass`). Backend routes stay unprefixed. `VITE_API_BASE_URL=/api`.
2. **Check-in email links → backend-rendered pages** (user decision). Emails use `BASE_URL` which in production is the public origin + `/api` (e.g. `https://host/api`), so `{BASE_URL}/checkin/confirm?token=…` resolves through nginx to the API's HTML pages.
3. The existing root `nginx.conf` (proxies everything to api, serves no frontend) is **replaced**, not extended.
4. The `nginx` compose service is built from `frontend/Dockerfile` (multi-stage: node build → nginx with `dist/` + conf). No separate `frontend` service.

---

## T1 (D4) — Fix `npm run build`

`frontend/vite.config.ts` uses a `test:` key with `defineConfig` imported from `vite` → type error, `tsc -b && vite build` fails.

1. Change import to `import { defineConfig } from 'vitest/config'`.
2. Add to `frontend/package.json` scripts: `"test": "vitest run"` (vitest is installed, tests exist in `src/test/`, no script — audit §9).
3. Fix any remaining `tsc -b` errors surfaced by the build (fix properly; do not `// @ts-ignore`).

**Verify:** `npm ci && npm run build` exits 0 and produces `frontend/dist/index.html`. `npm run test` runs the existing suite.

## T2 (D1) — Fix hardcoded `DATABASE_URL` in compose

`docker-compose.yml` lines ~20/39/58 hardcode `postgresql://postgres:postgres@localhost:5432/legate`. There is no postgres service (DB is managed Supabase) and `localhost` inside a container is the container itself.

1. In `api`, `worker`, `beat` services replace with `- DATABASE_URL=${DATABASE_URL}`.
2. Remove the obsolete `version: "3.9"` key.
3. Add `env_file: .env` to api/worker/beat (compose still allows explicit `environment:` overrides; keep the explicit list for documentation value).

**Verify:** `docker compose config` renders the real Supabase URL from `.env`, no `localhost:5432` anywhere in output.

## T3 (D3) — Create `frontend/Dockerfile` (multi-stage)

```dockerfile
# Stage 1 — build
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN npm run build

# Stage 2 — serve
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

Note: stage 2 copies `frontend/nginx.conf` — create it in T4 (the *root* `nginx.conf` is deleted; the canonical conf lives in `frontend/`). Confirm `frontend/src/api/client.ts` reads `import.meta.env.VITE_API_BASE_URL` (it should — fix if it hardcodes `http://localhost:8000`).

## T4 (D2) — Replace nginx config: SPA + `/api` proxy

Create `frontend/nginx.conf`:

```nginx
server {
    listen 80;
    server_name _;
    client_max_body_size 50M;

    root /usr/share/nginx/html;
    index index.html;

    # SPA fallback
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API — trailing slash strips the /api prefix
    location /api/ {
        proxy_pass http://api:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
        proxy_connect_timeout 10s;
    }

    location = /health {
        proxy_pass http://api:8000/health;
        access_log off;
    }

    # Never cache index.html; long-cache hashed assets
    location = /index.html { add_header Cache-Control "no-cache"; }
    location /assets/ { add_header Cache-Control "public, max-age=31536000, immutable"; }
}
```

1. Delete root `nginx.conf` (it proxies `/` to the API and serves no frontend).
2. In `docker-compose.yml`, replace the `nginx` service: `build: { context: ./frontend, args: { VITE_API_BASE_URL: /api } }`, ports `"80:80"`, remove the `./nginx.conf` volume mount, `depends_on: api`.
3. So that Swagger UI works behind the stripped prefix, add `ROOT_PATH` support: in `backend/app/config.py` add `root_path: str = ""`; in `main.py` pass `root_path=cfg.root_path` to `FastAPI(...)`; set `ROOT_PATH=/api` in compose api service. (Routes themselves stay unprefixed.)

**Verify:** after T5, `curl localhost/` returns the SPA HTML, `curl localhost/api/docs` returns Swagger, `curl localhost/health` returns `{"status":"ok"}`.

## T5 (D5) — Run migrations on api startup

1. Create `backend/entrypoint.sh`:

```bash
#!/bin/sh
set -e
alembic upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
```

2. In `backend/Dockerfile`: `COPY entrypoint.sh /entrypoint.sh`, `RUN chmod +x /entrypoint.sh`, `CMD ["/entrypoint.sh"]`. Also add `RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*` (needed for T9 healthcheck).
3. Worker and beat keep their explicit `command:` (celery) — they must NOT run migrations.

**Verify:** `docker compose up api` logs show `alembic upgrade head` output before uvicorn starts; re-running is idempotent.

## T6 (D6) — CORS origins from env

`main.py:23-32` allows only `localhost:5173-5179`; production origin would be blocked.

1. `config.py`: add `cors_origins: str = ""` (comma-separated env string) and a property/helper returning `list[str]` — when empty, fall back to the dev localhost list.
2. `main.py`: use the parsed list. Remove the `# TODO: restrict in production`.
3. Add `CORS_ORIGINS=${CORS_ORIGINS:-}` to compose api env and `.env.example` files (T11). Note: with same-origin `/api` proxying, browser CORS rarely triggers in prod, but the API is also exposed on `:8000` and direct use must work.

**Verify:** with `CORS_ORIGINS=https://example.com`, an OPTIONS preflight from that origin gets `access-control-allow-origin: https://example.com`.

## T7 (D7) — Make `docker-compose.dev.yml` a working override

Current file has services with only `build:` keys — unusable, and README tells users to run it standalone.

1. Rewrite as an override: api gets `volumes: [./backend:/app]` and `command: sh -c "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"`; worker/beat get the same volume mount; expose redis port.
2. README (touched fully in Phase 6, but fix the command now): usage is `docker compose -f docker-compose.yml -f docker-compose.dev.yml up`.

**Verify:** dev stack starts; editing a backend file triggers uvicorn reload.

## T8 (D8) — `.dockerignore` + remove committed binary

1. `backend/.dockerignore`: `.venv`, `venv`, `tests/`, `celerybeat-schedule`, `__pycache__/`, `*.pyc`, `.env`, `.pytest_cache`.
2. `frontend/.dockerignore`: `node_modules`, `dist`, `.env`, `*.local`.
3. `git rm --cached backend/celerybeat-schedule`; add `celerybeat-schedule*` to `.gitignore`.

**Verify:** `docker compose build` succeeds; image does not contain `tests/` or `.env` (`docker run --rm <api-image> ls /app`).

## T9 (D9) — Healthchecks and startup ordering

1. api: `healthcheck: test: ["CMD", "curl", "-f", "http://localhost:8000/health"], interval: 15s, timeout: 5s, retries: 5, start_period: 20s`.
2. redis: `healthcheck: test: ["CMD", "redis-cli", "ping"]`.
3. `depends_on` with `condition: service_healthy`: api→redis, worker→redis, beat→redis, nginx→api.
4. Pass through `PBKDF2_ITERATIONS`, bucket-name vars, `ENVIRONMENT`, `ROOT_PATH`, `CORS_ORIGINS` on api/worker/beat (defaults exist; explicit passthrough documents them).

**Verify:** `docker compose ps` shows `healthy` for api and redis; nginx starts only after api is healthy.

## T10 (D10) — Pin direct dependencies

`cryptography` (used directly in `delivery_tasks.py`) and `storage3` (imported in `core/supabase.py`) are only transitive today.

1. Add both to `backend/requirements.txt` with explicit version pins matching what currently resolves (check with `pip freeze` inside the built image).
2. Do **not** remove `python-jose`/`passlib` yet — that is B14, Phase 2 (the dead `core/security.py` module goes with them).

**Verify:** clean `docker compose build` then `docker run --rm <api-image> python -c "import cryptography, storage3"`.

## T11 (D11) — Env examples

1. Update `backend/.env.example`: add `ENVIRONMENT`, `PBKDF2_ITERATIONS=100000`, the three bucket names, `CORS_ORIGINS`, `ROOT_PATH`, `BASE_URL` (with comment: in production set to public origin + `/api`).
2. Create root `.env.example` listing **every** variable compose consumes (`DATABASE_URL`, `REDIS_URL` is internal, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`, `RESEND_API_KEY`, `EMAIL_FROM`, `SECRET_KEY`, `DELIVERY_SECRET`, `BASE_URL`, `CORS_ORIGINS`, `ENVIRONMENT`, `PBKDF2_ITERATIONS`, bucket names) with one-line comments. No fake-looking real values; use obvious `<placeholder>` markers.

**Verify:** `cp .env.example .env`, fill real values, `docker compose config` resolves everything with no warnings.

## T12 — Phase 1 E2E test (final task — phase is not complete until this passes)

Write `scripts/e2e_phase1.sh` (committed, executable) and run it against **real** Supabase/Resend credentials in `.env`:

```bash
#!/usr/bin/env bash
set -euo pipefail
docker compose down -v --remove-orphans
docker compose build --no-cache
docker compose up -d
# wait for health
for i in $(seq 1 30); do curl -fs localhost/health && break; sleep 2; done

fail() { echo "FAIL: $1"; docker compose logs --tail 50; exit 1; }

curl -fs localhost/health | grep -q '"ok"'            || fail "health"
curl -fs localhost/ | grep -qi '<div id="root">'      || fail "SPA served"
curl -fs localhost/api/openapi.json | grep -q '"Legate API"' || fail "API proxied"
curl -fs localhost/api/docs >/dev/null                 || fail "swagger"
# real signup through the proxy (real Supabase call)
EMAIL="e2e+$(date +%s)@<your-test-domain>"
curl -fs -X POST localhost/api/auth/signup \
  -H 'Content-Type: application/json' \
  -d "{\"email\":\"$EMAIL\",\"password\":\"Phase1-e2e-pass!9\"}" \
  | grep -q user                                       || fail "signup via proxy"
# worker/beat alive
docker compose ps --format json | grep -q '"worker".*running' || fail "worker"
docker compose logs beat --tail 20 | grep -qi 'beat' || fail "beat"
echo "PHASE 1 E2E: PASS"
```

Manual checks in the same run: open `http://localhost/` in a browser — login page renders, no console 404s for assets; `docker compose logs api` shows alembic ran; no restart loops over 5 minutes (`docker compose ps`).

**Acceptance:** script exits 0; all manual checks pass. Record the run output at the bottom of this file in a `## Phase 1 E2E result` section.

## Out of scope for this phase

Login flow itself is still broken in the frontend (F1/F2 — Phase 3); check-in loop bugs (Phase 2). The deploy E2E only proves the stack builds, serves, proxies, migrates, and reaches Supabase.

## Phase 1 E2E result

**Run:** 2026-06-12, user machine (Docker Desktop / WSL2), `NGINX_PORT=8080 E2E_EMAIL="995homebase995+e2e$(date +%s)@gmail.com" bash scripts/e2e_phase1.sh`

**Result: PASS** — script exited 0, final line `PHASE 1 E2E: PASS`.

```
[+] Building 83.0s (38/38) FINISHED
 ✔ Image legate-api    Built
 ✔ Image legate-worker Built
 ✔ Image legate-beat   Built
 ✔ Image legate-nginx  Built
[+] up 6/6
 ✔ Network legate_default    Created
 ✔ Container legate-redis-1  Healthy   (10.9s)
 ✔ Container legate-beat-1   Started   (11.1s)
 ✔ Container legate-api-1    Healthy   (26.5s)
 ✔ Container legate-worker-1 Started   (11.1s)
 ✔ Container legate-nginx-1  Started   (26.7s)
{"status":"ok"}PHASE 1 E2E: PASS
```

Checks proven: health via nginx, SPA served at `/`, `/api/openapi.json` + `/api/docs` proxied with prefix strip, real Supabase signup through the proxy (201), worker + beat running, alembic ran before uvicorn (`Context impl PostgresqlImpl` in api logs).

**Deviations from the doc's T12 snippet (all consulted/necessitated during the run):**
1. nginx host port parameterized as `${NGINX_PORT:-80}` (default unchanged) — user's environment holds port 80; e2e script honors `NGINX_PORT`.
2. Signup payload corrected to the API's actual zero-knowledge contract: `SignupRequest` requires `encrypted_cek`, `cek_iv`, `pbkdf2_salt` (base64) in addition to email/password. The doc's two-field example returned 422 by design.
3. Test email parameterized via `E2E_EMAIL` / `E2E_TEST_DOMAIN` instead of a hard-coded placeholder domain.

**First-run findings (fixed before the passing run):** port-80 bind conflict (host-side), 422 on signup (incomplete doc payload). Stack itself was healthy on first attempt.

**Known non-blocking warnings:** celery worker runs as root (SecurityWarning), `broker_connection_retry` deprecation — both candidates for Phase 5/6.

**Manual checks (2026-06-12): PASS.** `http://localhost:8080/` renders the SPA with no asset 404s and no app console errors (only browser-extension noise present). `docker compose ps` after ~7 minutes: api `Up (healthy)`, redis `Up (healthy)`, nginx/worker/beat `Up`, no restart loops. Phase 1 acceptance criteria met.
