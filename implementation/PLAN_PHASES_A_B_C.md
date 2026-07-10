# Legate — Implementation Plan: Silent Adds, Demo Intervals, Rich Emails

> **Audience:** a Claude LLM agent picking up this work. Read this whole file before editing anything.
> **Repo root:** this file's directory. Backend = FastAPI + SQLAlchemy (async) + Celery + Redis + Supabase Postgres. Frontend = React + Vite + TypeScript + Tailwind. Migrations = Alembic (`backend/alembic/versions/`, applied by dev compose via `alembic upgrade head`).

---

## 0. Context — what this work is and why

Legate is a digital estate ("dead man's switch") app. Users store encrypted capsules for **beneficiaries**. A **check-in schedule** (`interval_days` + `grace_period_days`) emails the user periodically; if they miss the check-in and the grace period lapses, Celery tasks trigger **delivery** of capsules to beneficiaries by email.

Three feature phases were planned. **Phase A is DONE** (see §1 — do not redo it, but understand it). Phases B and C are yours.

### Ground rules (from the project owner — binding)

1. **No stubs, no mockups, no faked tests, no tests written to pass trivially.** Every task must work end-to-end.
2. If a task needs a design decision that deviates from this plan, **stop and consult the user first**.
3. Preserve existing invariants: HTML-escaping via `_esc()` in `backend/app/core/email.py` (security hardening — never remove), FR-comment references in code, the "email failure must never block the main operation" pattern (`try/except: pass` around sends).
4. The sandbox may lack Docker/DB access. Tests that need the stack must be run by the user locally (PowerShell + docker compose). Give them the exact commands; never claim tests passed if you could not run them.

---

## 1. Phase A — Silent beneficiary add (COMPLETED — context only)

**What was built:** an opt-out for the automated "you've been added as a beneficiary" nomination email, plus removal of a dead "Invite pending" UI.

Key decisions an agent must know because Phases B/C touch nearby code:

- `BeneficiaryStatus.pending` is dead. New beneficiaries are created with `status=active`. Nothing anywhere reads `pending` anymore.
- **`invited_at IS NULL` is the single source of truth for "added silently."** No new column was added.
- `POST /beneficiaries/` accepts `notify_beneficiary: bool = true`. When false: no nomination email, `invited_at` stays NULL, audit meta `{"silent": true}`.
- On email-address change (PATCH), the nomination email re-sends **only if** `invited_at IS NOT NULL`; silent stays silent.
- Frontend: `BeneficiaryForm.tsx` has a "Notify by Email" toggle (create mode only — hidden when `initialData` is present). `BeneficiaryCard.tsx` shows an "Added silently" badge (BellOff icon) when `invited_at === null`.
- Silent beneficiaries **still receive delivery emails** when a release triggers. Silence covers only the nomination notice. Do not "fix" this.

**Files changed in Phase A** (for orientation):
`backend/app/schemas/beneficiary.py`, `backend/app/api/beneficiaries.py`, `backend/app/services/beneficiary_service.py`, `backend/tests/test_schemas.py`, `backend/tests/e2e/test_03_beneficiaries.py`, `frontend/src/types/api.ts`, `frontend/src/api/beneficiaries.ts`, `frontend/src/components/beneficiary/BeneficiaryForm.tsx`, `frontend/src/components/beneficiary/BeneficiaryCard.tsx`.

### Phase A testing (user runs in PowerShell at repo root)

```powershell
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
docker compose exec api pytest tests/test_schemas.py tests/test_beneficiaries.py tests/e2e/test_03_beneficiaries.py -v
cd frontend; npm run type-check; npm run test
```

### Phase A success criteria

- [ ] All commands above pass.
- [ ] Adding a beneficiary with toggle ON → email arrives, card has **no** pending UI, no silent badge, API returns `status:"active"`, `invited_at` set.
- [ ] Adding with toggle OFF → **no** email, card shows "Added silently" badge, `invited_at:null`.
- [ ] Editing a silent beneficiary's email → still no email sent.
- [ ] Editing a notified beneficiary's email → nomination email re-sent to the new address.

**Known leftover (optional, ask user):** pre-existing DB rows still have `status='pending'`. Harmless (nothing reads it). A one-line data migration `UPDATE beneficiaries SET status='active' WHERE status='pending'` can be added for consistency.

---

## 2. Phase B — Relaxed limits + demo-mode minute-level intervals

### Goal

1. Lower the check-in interval floor from 7 days to **1 day** (permanent, all environments).
2. Add a **demo mode** (env-gated) where interval and grace period can be set in **minutes** (e.g. check-in every 2 min, grace 30 min) so a live demo can show the full lifecycle — check-in email → missed → grace → release → delivery — in minutes instead of weeks.
3. Make Celery beat tick fast enough for minute-level schedules to actually fire.

### Design constraints (do not deviate without asking)

- **Do NOT migrate the day columns to minutes.** `interval_days` / `grace_period_days` stay as-is. Add **nullable override columns** `check_interval_minutes` and `grace_period_minutes` on the check-in schedule table (see `backend/app/db/models/checkin.py`, `CheckInSchedule`, currently lines ~51–52). When a minutes column is non-NULL it takes precedence over the corresponding days column.
- Minutes fields are **only writable when `DEMO_MODE=true`** (server-side enforcement, not just UI hiding). When demo mode is off, PATCH bodies containing minutes fields → 403 with a clear detail message.
- Normal-mode behavior with default env values must be **byte-for-byte identical** to today (beat still ticks 3600s, all math still day-based). Regressions here are the main risk; the whole design exists to avoid them.

### B1. Backend — config

`backend/app/config.py` (`class Settings`, ~line 43). Add:

```python
demo_mode: bool = False
beat_interval_seconds: int = 3600  # dispatch/grace/trigger beat tick
```

Wire both into `docker-compose.yml` **and** `docker-compose.dev.yml`-visible env for `api`, `worker`, and `beat` services (`DEMO_MODE=${DEMO_MODE:-false}`, `BEAT_INTERVAL_SECONDS=${BEAT_INTERVAL_SECONDS:-3600}`). Beat and worker MUST get them too — the tasks read the same Settings.

### B2. Backend — model + migration

- Add to `CheckInSchedule`: `check_interval_minutes: int | None`, `grace_period_minutes: int | None` (nullable Integer columns).
- New Alembic revision in `backend/alembic/versions/` (follow the style of `c1e5d8f2a4b7_phase4_features.py`): `add_column` both, nullable, no default backfill. Downgrade drops them.

### B3. Backend — scheduling helper (the core of the change)

Create `backend/app/core/scheduling.py`:

```python
from datetime import timedelta

def interval_delta(schedule) -> timedelta:
    if schedule.check_interval_minutes:              # demo override
        return timedelta(minutes=schedule.check_interval_minutes)
    return timedelta(days=schedule.interval_days)

def grace_delta(schedule) -> timedelta:
    if schedule.grace_period_minutes:
        return timedelta(minutes=schedule.grace_period_minutes)
    return timedelta(days=schedule.grace_period_days)
```

Replace every schedule-math `timedelta(days=...)` call site with these. Known sites (grep `timedelta(days=` under `backend/app` to catch strays — there WILL be ones not listed here):

| File | Approx. line | What it computes |
|---|---|---|
| `backend/app/api/settings.py` | 119, 123 | `next_dispatch_at` on interval change |
| `backend/app/services/auth_service.py` | 179 | `next_dispatch_at` on first activation |
| `backend/app/services/checkin_service.py` | 50 | `next_dispatch_at` on confirm |
| `backend/app/worker/tasks/checkin_tasks.py` | ~177 | grace deadline incl. `PAUSE_EXTENSION_DAYS * pause_count` — keep the pause extension in **days** (it's an emergency-contact feature, not demo-relevant); only the base grace becomes `grace_delta(schedule)` |
| `backend/app/worker/tasks/checkin_tasks.py` | ~363 | grace deadline for reminder emails |

**Grace reminders** (`send_grace_period_reminders`, day-threshold logic ~lines 318–400): when `grace_period_minutes` is set, **skip the user** (`continue`) — day-based reminder thresholds are meaningless in a minutes-long demo. Add a comment saying so.

### B4. Backend — schemas + API

`backend/app/schemas/checkin.py`:

- `interval_days`: `Field(None, ge=7, le=365)` → `ge=1`.
- `grace_period_days`: `Literal[3, 7, 14, 30]` → `int` with `ge=1, le=30`. (Frontend keeps its 3/7/14/30 presets; the API just stops rejecting other values. Check `test_schemas.py` for Literal-based tests and update them.)
- Add to `CheckInSettingsUpdate`: `check_interval_minutes: int | None = Field(None, ge=1, le=1440)`, `grace_period_minutes: int | None = Field(None, ge=1, le=1440)`, plus `clear_minute_overrides: bool = False` to reset back to day mode.
- Add both minutes fields (+ `demo_mode` if convenient) to `CheckInSettingsResponse`.

`backend/app/api/settings.py` `update_checkin_settings` (~line 97):

- If any minutes field (or `clear_minute_overrides`) present and `get_settings().demo_mode` is false → `HTTPException(403, "Demo mode is disabled")`.
- Setting `check_interval_minutes` recomputes `next_dispatch_at` using the same anchor logic as the existing days branch (lines 111–123) but with `timedelta(minutes=...)`.
- `clear_minute_overrides=True` → NULL both columns, recompute `next_dispatch_at` from `interval_days`.

Expose demo mode to the frontend: add `demo_mode: cfg.demo_mode` to the `GET /settings/checkin` response (simplest; it's already the page that needs it).

### B5. Backend — Celery beat

`backend/app/worker/celery_app.py` (~lines 28–45): replace the hardcoded `3600.0` for `dispatch-checkin-emails`, `check-grace-periods`, `process-pending-triggers` with `float(cfg.beat_interval_seconds)`. Leave `send-grace-reminders` at 43200 (it self-skips minute-mode users per B3). Note: `tests/e2e/test_09_celery_tasks.py` asserts on the beat schedule — check it still passes with defaults.

### B6. Frontend

- `frontend/src/types/api.ts` `CheckinSchedule`: add `check_interval_minutes: number | null`, `grace_period_minutes: number | null`, `demo_mode?: boolean`.
- `frontend/src/pages/setup/StepCheckin.tsx`: `MIN_CUSTOM_INTERVAL = 7` → `1`. Keep the existing short-window warning modal.
- `frontend/src/pages/security/Security.tsx` (check-in edit UI, ~lines 380–480): lower its min to 1; when `demo_mode` is true, render a visually distinct "Demo scheduling" section (amber border, "DEMO" badge) with minute inputs for interval + grace and a "Reset to days" button (`clear_minute_overrides`). When schedule has minute overrides, display them ("Check-in interval: 2 minutes (demo)") instead of the day values.
- `frontend/src/pages/vault/Dashboard.tsx` line ~22: grace-end math currently `dispatched + schedule.grace_period_days * 86400000` — use minutes override when non-null (`grace_period_minutes * 60000`). Grep the frontend for other `86400000` / `interval_days` math and fix the same way.
- `frontend/src/api/settings.ts` + `frontend/src/hooks/useCheckinSchedule.ts`: widen payload types to include the new fields.

### B7. Tests to write (real ones)

- `backend/tests/test_schemas.py`: `interval_days=1` valid; `interval_days=0` invalid; `grace_period_days=5` now valid; minutes bounds (0 → invalid, 1441 → invalid).
- New `backend/tests/e2e/` additions (follow `test_12_checkin_lifecycle.py` patterns — it calls task functions like `_check_grace_periods()` directly, no waiting):
  - unit-style: `interval_delta`/`grace_delta` precedence (minutes set vs NULL).
  - PATCH minutes with `DEMO_MODE=false` → 403 (monkeypatch/env-override the settings cache — note `get_settings()` is likely `lru_cache`d; clear it).
  - PATCH minutes with demo on → columns set, `next_dispatch_at` ≈ now + minutes.
  - Full demo lifecycle: schedule with `check_interval_minutes=1, grace_period_minutes=1`, backdate `next_dispatch_at`/`dispatched_at`, run `_dispatch_due_checkins()` → `_check_grace_periods()` → assert release trigger created (mirror the assertions used in test_12 for the day-based path).
- Regression: run the **entire** existing backend suite; the day-based defaults must pass untouched.

### Phase B testing instructions (user, PowerShell)

```powershell
# 1. normal mode — full regression
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
docker compose exec api alembic upgrade head
docker compose exec api pytest -v

# 2. demo mode — add to .env: DEMO_MODE=true and BEAT_INTERVAL_SECONDS=60, then
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --force-recreate api worker beat
docker compose exec api pytest tests/e2e/ -v -k "demo or checkin"

# 3. live demo rehearsal (manual)
#    UI → Security → set check-in 2 min, grace 2 min → wait ≤1 min for beat tick
docker compose logs worker beat --tail=50 -f
#    expect: dispatch log → (don't confirm) → grace check → release trigger → delivery emails

# 4. frontend
cd frontend; npm run type-check; npm run test
```

### Phase B success criteria

- [ ] With `DEMO_MODE` unset: full existing pytest suite green; beat schedule unchanged (3600s); UI shows no demo section; API rejects minutes fields with 403.
- [ ] `interval_days=1` accepted end-to-end (schema, API, UI custom input).
- [ ] With demo on: minute overrides persist, response includes them, `next_dispatch_at` recomputed in minutes.
- [ ] Live rehearsal (step 3) completes check-in → missed → release → beneficiary delivery email in ≤ interval+grace+2·beat-tick minutes.
- [ ] "Reset to days" clears overrides and restores day-based `next_dispatch_at`.
- [ ] No `timedelta(days=` left in schedule math outside `scheduling.py` (grep proves it), except the intentionally-day-based pause extension.

### Phase B addendum (2026-07-06) — emergency-contact confirmation window now demo-scalable

The original Phase B design left `EMERGENCY_CONFIRMATION_WINDOW_HOURS` (FR-23's 48h
pending_confirmation window) hardcoded, on the theory that it's "an
emergency-contact feature, not demo-relevant" (see the B3 table row above,
which only covers the *pause extension*, `PAUSE_EXTENSION_DAYS`). In
practice this meant a demo account with an emergency contact configured
could never reach actual delivery within a live rehearsal — the trigger
would sit in `pending_confirmation` for a real 48 hours regardless of how
short `check_interval_minutes`/`grace_period_minutes` were set. Confirmed
during a live rehearsal (worker logs showed `delivery_pending_confirmation`
sitting for real elapsed hours with no promotion).

Fix (approved by user): added `emergency_confirm_minutes` as a fourth
demo-mode override column on `checkin_schedules`, following the exact
`check_interval_minutes`/`grace_period_minutes` pattern — nullable, minutes
take precedence over the 48h default via `emergency_confirm_delta()` in
`app/core/scheduling.py`, writable only when `DEMO_MODE=true` (same 403
gating as the other two), and cleared by `clear_minute_overrides` alongside
them. `PAUSE_EXTENSION_DAYS` (the *repeat*-pause extension) is unaffected
and remains intentionally day-based — pausing is something a real emergency
contact does deliberately, not part of the passive missed-checkin timeline
a demo needs to race through.

Changed/added: `backend/alembic/versions/e9b3f6a1c8d4_phase_b_emergency_confirm_minutes.py`,
`app/db/models/checkin.py`, `app/core/scheduling.py`, `app/worker/tasks/checkin_tasks.py`,
`app/schemas/checkin.py`, `app/api/settings.py`, `frontend/src/types/api.ts`,
`frontend/src/api/settings.ts`, `frontend/src/pages/security/Security.tsx`,
plus tests in `backend/tests/test_schemas.py` and `backend/tests/e2e/test_16_demo_mode.py`.

---

## 3. Phase C — Rich HTML email templates

### Goal

Replace the seven plain inline-HTML emails in `backend/app/core/email.py` with a branded, email-client-safe design matching the app aesthetic. No new dependencies, no template engine — keep f-strings, add one shared layout function.

### Current senders (all in `backend/app/core/email.py`)

| Line | Function | Notes |
|---|---|---|
| 35 | `send_checkin_email` | has CTA link (confirm URL) |
| 82 | `send_nomination_email` | Phase A: only sent when notify=true |
| 115 | `send_delivery_email` | receives pre-rendered `capsules_html` — restyle the wrapper AND find where `capsules_html` is built (`worker/tasks/delivery_tasks.py`) and style those blocks too |
| 167 | `send_grace_period_reminder` | urgency variant (amber) |
| 204 | `send_emergency_pause_email` | urgency variant |
| 260 | `send_beneficiary_removal_email` | neutral, no account details (FR-20/FR-22 constraint — keep copy neutral) |
| 296 | `send_alert_email` | internal/ops — minimal styling is fine |

### Design system (from the frontend)

Ink `#0D1117`, slate `#3D4F6B`, muted `#6B7280`, background `#F0F2F5`, card white radius 16px, accent blue gradient `#60A5FA→#2563EB` (avatar gradient `from-blue-400 to-blue-600`), warning amber `#D97706`, danger `#C0392B`.

### C1. Shared layout

Add to `email.py`:

```python
def _base_template(*, title: str, body_html: str, cta_label: str | None = None,
                   cta_url: str | None = None, accent: str = "#2563EB",
                   preheader: str = "") -> str: ...
def _button(label: str, url: str, color: str = "#2563EB") -> str: ...
```

Email-client rules (Gmail/Outlook strip `<style>` and ignore flexbox):

- Table-based layout only (`<table role="presentation">`), **all CSS inline**, max-width 600px centered card on `#F0F2F5` body.
- Header: "Legate" wordmark text (white on `#0D1117` bar or gradient) — no image assets (no hosting for them).
- Hidden preheader span before content.
- Footer: muted one-liner ("Legate — secure digital estate. This is an automated message…").
- Buttons: padded `<a>` inside a table cell with `background-color` + `border-radius` (works in Outlook better than CSS buttons). Always ALSO print the raw URL as fallback text under the button (deliverability + Outlook).

### C2. Rewrite each sender

- Route all seven through `_base_template`. Urgent ones (grace reminder, emergency pause) use amber accent + bolder title; removal stays neutral gray; delivery gets the most care (it's the product's whole point): capsule blocks as bordered sub-cards with title + content.
- **Keep `_esc()` on every interpolated user value — exactly as now.** New layout must not introduce a single unescaped interpolation.
- Add a plain-text part: each sender builds `text = ...` (simple line-based version) and includes `"text": text` in the Resend params dict alongside `"html"`. Verify against the actual send call in `email.py` that the key is passed through.

### C3. Verification tooling (so the user can eyeball without spamming inboxes)

Add `backend/scripts/preview_emails.py`: imports the senders' template-building logic (refactor each sender minimally so HTML construction is a pure `_build_*` function the script can call without sending), renders all seven with sample data to `backend/scripts/email_previews/*.html`. This doubles as proof there are no runtime interpolation errors.

### C4. Tests

- `backend/tests/test_email_templates.py` (new): for each `_build_*`: output contains the escaped sample name; `<script>` in a name arrives escaped (`&lt;script&gt;`); CTA URL present for CTA emails; no `{` `}` f-string leftovers; text part non-empty and contains the CTA URL.
- Existing suites (beneficiary/checkin e2e) must stay green — sender signatures must not change (only internals + added pure builders).

### Phase C testing instructions (user, PowerShell)

```powershell
docker compose exec api pytest tests/test_email_templates.py -v
docker compose exec api pytest -v          # full regression
docker compose exec api python scripts/preview_emails.py
# then open backend\scripts\email_previews\*.html in a browser
# real-world check: trigger one real send (add a beneficiary with notify ON
# to an address you control) and view in Gmail web + mobile.
```

### Phase C success criteria

- [ ] All seven emails render branded (header, card, footer, correct accent) in Gmail web — no raw HTML shown, no broken layout.
- [ ] Every user-supplied value still HTML-escaped (test proves it with a `<script>` payload).
- [ ] Every email has a plain-text alternative part.
- [ ] CTA links work; raw-URL fallback printed under each button.
- [ ] Preview script writes seven HTML files without error.
- [ ] Full backend pytest suite green.

---

## 4. Suggested execution order for the agent

1. Read this file, then read every file named in the phase you're implementing **before** editing (line numbers above are approximate — re-locate by content).
2. Phase B backend (B1→B5, migration first), backend tests, then B6 frontend, then hand the user the Phase B test commands.
3. Wait for the user to confirm Phase B green before starting Phase C (both phases touch worker/email paths; don't stack unverified changes).
4. Phase C, then hand over Phase C test commands.
5. Anything ambiguous (e.g. grace presets in UI, pause-extension units, adding the Phase A data migration) → ask the user, don't guess.
