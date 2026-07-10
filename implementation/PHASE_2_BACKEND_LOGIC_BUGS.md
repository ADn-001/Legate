# Phase 2 — Backend Critical Logic Bugs (check-in / delivery loop)

**Covers audit items:** B1–B21 (§2 of `AUDIT_REPORT.md`)
**Assumes:** Phase 1 is 100% complete — the compose stack builds and runs, migrations apply on startup, API reachable at `/api` through nginx.
**Goal:** The check-in → grace → delivery → memorial → purge lifecycle is correct: no email spam, no re-triggering, no silent dead vaults, GDPR purge actually purges.
**Rules:** No stubs or mocks. The existing `backend/tests/conftest.py` AsyncMock fixtures must not be used for any new test (see T-test). All lifecycle tests run real Celery task functions against the real database (test Supabase project) and real Redis, manipulating timestamps via real DB writes — never by patching `datetime`.

## Locked decisions

- DB single-use tokens stay (NFR-12 deviation accepted by user). Document in code comment at the token model and in README (Phase 6).
- Emergency-contact pre-trigger pause (B8, FR-23/24) is in scope here even though FR-23/24 are P1, because the token plumbing half-exists and the audit flags it.
- Email links point at backend-rendered pages (`BASE_URL`), per Phase 1 decision.

---

## T1 (B1) — Stop hourly check-in re-dispatch

`checkin_tasks.py:29-82` `_dispatch_due_checkins`: after dispatch, `next_dispatch_at` is never advanced/cleared, so `next_dispatch_at <= now` matches again every hourly beat run → email spam.

1. After a successful send for a schedule, set `schedule.next_dispatch_at = None` and `schedule.last_dispatched_at = now` (verify the latter is already set; keep it).
2. Add `CheckInSchedule.next_dispatch_at.isnot(None)` to the dispatch query.
3. Confirm/snooze (`checkin_service.confirm` / `snooze`) are the only places that re-set `next_dispatch_at` — verify both do (`confirm` sets `now + interval_days`; `snooze` sets `now + snooze_days`).

## T2 (B3) — Filter user status on dispatch

Same function: join `User`, require `User.status == "active"` and `User.email_verified.is_(True)`. Deleted/memorialized/unverified users must never receive check-in emails.

## T3 (B2) — Stop infinite delivery re-trigger

`_check_grace_periods` (`checkin_tasks.py:100-151`) re-creates a delivery trigger every hour for already-delivered users: it only excludes `processing` triggers, and post-delivery `last_confirmed_at < last_dispatched_at` is still true.

1. Skip users where `User.status != "active"` (memorialized users are done).
2. Skip if any `DeliveryTrigger` with `status IN ('processing','completed','pending_confirmation')` exists with `created_at >= schedule.last_dispatched_at` (one trigger per missed-check-in cycle).
3. Keep allowing a new trigger if the previous one for an *older* cycle ended `failed` — but only after T8's retry logic has exhausted (a `failed` trigger from the current cycle must NOT spawn a duplicate; retries are scheduled by the delivery task itself, T8).

## T4 (B4) — Confirm must fully reset pause state

`checkin_service.confirm` (`checkin_service.py:34-58`): after an emergency pause, `is_paused=True` sticks forever → user never dispatched again → silent dead vault.

On successful confirm set: `is_paused = False`, `pause_count = 0`, `grace_reminder_sent_at = None` (plus existing resets). Audit-log the unpause.

## T5 (B5) — Grace reminders per cycle, day 3 and day 7 (FR-16)

`_send_grace_period_reminders` (`checkin_tasks.py:154-231`): `grace_reminder_sent_at.is_(None)` + set-once = one reminder per account lifetime; day-7 never sends; exact-day match misses with 12h cadence.

Redesign:
1. Add column `last_grace_reminder_day: int | None` to `checkin_schedules` (alembic migration) — the grace-day number of the last reminder **this cycle**.
2. Reset it to `None` in `confirm`/`snooze` (T4) and on new dispatch (T1).
3. Reminder logic per overdue schedule: compute `days_into_grace = (now - grace_started_at).days` (use the field the code already derives grace from — `last_dispatched_at + interval` or explicit; keep consistent with `_check_grace_periods`). For each threshold in `(3, 7)`: if `days_into_grace >= threshold` and `(last_grace_reminder_day is None or last_grace_reminder_day < threshold)` → send reminder, set `last_grace_reminder_day = threshold`, `grace_reminder_sent_at = now`. The `>=` comparison makes the 12h cadence safe (fires on first run at-or-after the threshold, once).
4. Skip thresholds ≥ grace period length (a 3-day grace period sends only escalating copy appropriate to its length — day-3 reminder is the trigger day; don't send a reminder and trigger together: skip threshold if `threshold >= grace_period_days`).

## T6 (B8) — Emergency-contact pre-trigger pause email (FR-23/24)

The `emergency_pause` token is generated at dispatch (`checkin_tasks.py:49`) but never emailed; the 48h pre-trigger window doesn't exist.

1. In `_check_grace_periods`, when a grace period expires AND the user has a beneficiary with `is_emergency_contact=True` (and `status != removed`):
   - Create the trigger with new status `pending_confirmation` and `deliver_after = now + 48h` (new columns via the same migration as T5).
   - Email the emergency contact (Resend): plain-language explanation (FR-40 tone), a single-click pause link `{BASE_URL}/checkin/pause?token=…` using a fresh `emergency_pause` token addressed to that contact, and the 48h deadline.
2. Add a beat-driven path (extend `_check_grace_periods` or new task `process_pending_triggers`, hourly): triggers in `pending_confirmation` with `deliver_after <= now` → promote to `processing` and enqueue the delivery task.
3. Pause endpoint behavior (exists at `api/checkin.py` pause route — verify): on valid pause, extend grace by 7 days (`pause_count += 1`, max 2 per trigger event per FR-24), set trigger status `paused_cancelled` (terminal), set `schedule.is_paused = True`. A later confirm (T4) fully resets; if the user still doesn't confirm, a *new* cycle/trigger forms naturally.
4. No emergency contact → trigger goes straight to `processing` (current behavior).
5. Update the trigger-status enum/check constraints + migration accordingly.

## T7 (B9 + B10) — GDPR purge must actually purge (FR-05/FR-41)

**Storage (B9):** `cleanup_tasks.py:104-113` lists only `{user_id}/` immediate children (capsule folders); removing folder paths leaves all nested blobs.
1. Build the object list from the DB: for each of the user's capsules, list `f"{user_id}/{capsule_id}/"` in each bucket (content, media, thumbnails) and collect full object paths; also handle the capsule content blob path pattern used by upload. Batch `remove()` real object paths only.
2. After removal, re-list each prefix and assert empty; log + raise (Celery retry) if not.

**DB rows (B10):** `auth_service.delete_account` (`auth_service.py:171-192`) leaves `users` (email), `beneficiaries` (names/emails), `encryption_keys` rows forever.
3. In the purge task (after storage purge succeeds): anonymize the user's `audit_logs` rows (null/blank actor email, keep event types for compliance), then hard-`DELETE` the `users` row and verify FK cascades remove settings/keys/beneficiaries/capsules/recipients/schedule/tokens/triggers (fix any missing `ondelete="CASCADE"` with a migration).
4. Also delete the Supabase **auth** user via admin API (`auth.admin.delete_user`) — verify `delete_account` does this; if it only flags status, move the full sequence here so everything completes ≤72h (FR-05). The API-level `delete_account` keeps: verify password + "DELETE" text, set status `pending_deletion`, schedule this purge task.

## T8 (B6) — Per-recipient delivery retry (FR-42)

`delivery_tasks.py:84-129`: per-recipient send failures are swallowed into `DeliveryEvent(failed)`, trigger still `completed`, `self.retry` dead.

1. Collect failed recipient sends during the loop.
2. If any failed: do NOT mark trigger `completed`; record `DeliveryEvent(failed)` per recipient with attempt number; schedule `retry_failed_deliveries.apply_async(args=[trigger_id, attempt+1], countdown=3600)` — a new task that re-sends **only** failed recipients. Max 3 attempts, 1h apart.
3. After final failed attempt: mark trigger `failed`, raise an internal alert — concrete implementation: email `ALERT_EMAIL` (new config setting, add to `.env.example`s and compose) with trigger id + failed recipients, and write an `audit_logs` row `delivery_failed_permanently`.
4. Memorialization + purge scheduling happen only when **all** recipients succeeded (trigger `completed`) or the final attempt finished (partial delivery: memorialize anyway — at-least-once per NFR-07 was attempted; document this in a code comment).

## T9 (B7) — One email per beneficiary, capsules in order (FR-39)

Same file: currently one email per capsule per beneficiary; media never delivered.

1. Group the user's deliverable capsules by recipient; order by `delivery_order`.
2. Render ONE email per beneficiary: FR-40 intro (plain-language, non-alarming, includes nominator's name — `User.full_name`, see Phase 3 F16), then each capsule (title + decrypted text) in order.
3. Media: photos embedded/linked + video as 30-day signed link — implement the rendering hooks now (a `render_capsule_media(capsule)` section that pulls `MediaAttachment` rows and generates signed URLs `create_signed_url(path, expires_in=30*24*3600)`); with the media upload pipeline arriving in Phase 4 (G2), attachments may simply not exist yet, but the delivery path must already handle them — real code, not a stub: it renders whatever `media_attachments` rows exist.
4. HTML-escaping of user content is hardened in Phase 5 (S3) — but since this task rewrites the template, apply `html.escape()` to all user-supplied strings NOW; Phase 5 upgrades to sanitization when rich text lands.

## T10 (B11, B12) — Backend check-in pages

1. B11: confirm page (`api/checkin.py:64`) hardcodes "30 days" — use the schedule's real `interval_days` / `next_due` already returned by the service.
2. B12: `_PAUSED_HTML` is passed to `HTMLResponse` without `.format()` → literal `{{ }}` in CSS. Call `.format()` (or store the CSS unescaped and stop double-bracing).

## T11 (B13) — Beneficiary removal correctness (FR-22)

`beneficiary_service.py:105-118`:
1. Send the removal-notification email to the beneficiary (Resend; neutral copy, no content/account details — mirror FR-20 constraints).
2. `list_for_user` (line 69): filter `status != "removed"` by default (add `include_removed: bool = False` param). This also fixes removed people appearing in frontend dropdowns/emergency-contact picker.
3. When removal leaves a capsule with zero recipients, set a flag the frontend can show (capsule list response gains `has_recipients: bool` or similar) — coordinate with Phase 3 F6 schema extension; implement the field here.

## T12 (B14) — Delete dead auth code

`app/core/security.py` (jose JWT + passlib) is dead — auth uses Supabase JWTs via PyJWT in `dependencies.py`. Delete the module; remove `python-jose` and `passlib` from `requirements.txt`; fix any imports (there should be none — grep first).

## T13 (B15, B16, B17, B18) — Settings & capsule API correctness

1. B15: `CheckInSettingsUpdate` schema — pydantic bounds: `interval_days: int = Field(ge=7, le=365)`, `grace_period_days: Literal[3,7,14,30]` (FR-11/12). When `last_confirmed_at is None` and interval changes, set `next_dispatch_at = now + interval` (not from `last_confirmed_at`).
2. B16: storage-usage endpoint — include text-content blob sizes (store `content_size_bytes` on capsule at upload time — migration + set it in capsule create/update path) and add `limit_bytes` (new config setting `storage_quota_bytes`, default e.g. 1 GiB) for the FR-36 progress bar.
3. B17: `capsule_service.list_for_user` must include `pending_deletion` capsules (frontend union type already has the status; FR-31 badge).
4. B18: `delivery_order` assignment: `max(existing delivery_order)+1`, not `count+1`.

## T14 (B19, B20) — Auth edge cases

1. B19: in signup, if the local DB commit fails after Supabase `sign_up` succeeded, call `auth.admin.delete_user` in the except path so no orphan Supabase auth user remains; re-raise.
2. B20: `verify_email` bare `ValueError`s → `HTTPException(status_code=400, detail=...)` so the client gets 400 not 500.
3. B21: no change (documented as fine).

## T-test — Replace mock-based tests, add lifecycle regression suite (final task)

**Setup:** real test env — dedicated Supabase test project (or test schema), real Redis (compose), real Resend key. Use Resend's test addresses for deterministic outcomes: `delivered@resend.dev` (succeeds) and `bounced@resend.dev` (fails) — real API calls, not mocks.

1. Delete the `AsyncMock` session fixtures in `backend/tests/conftest.py`; rewrite the existing unit tests that depended on them to run against a real async test database session (same engine as e2e conftest). Tests that cannot assert anything real get rewritten or deleted — no assert-nothing tests remain.
2. New `backend/tests/e2e/test_12_checkin_lifecycle.py` — drives **real Celery task functions** (call the underlying `_dispatch_due_checkins` etc. synchronously) against the real DB, manipulating time by writing real timestamps:
   - **B1 regression:** user with `next_dispatch_at` in the past → run dispatch twice → exactly one check-in token/email row; `next_dispatch_at` is `None` after first run.
   - **B3 regression:** memorialized + unverified users with due schedules → dispatch → zero sends.
   - **B4 regression:** schedule with `is_paused=True, pause_count=2` → confirm via real token endpoint → all three fields reset; subsequent dispatch works.
   - **B5 regression:** set `last_dispatched_at = now - (interval + 3 days)` → reminders task → day-3 reminder once (run task twice, still once); advance to day 7 → day-7 reminder sends; new cycle resets `last_grace_reminder_day`.
   - **B2 regression:** expire grace → grace task twice → exactly one trigger; after delivery completes (memorial), grace task again → no new trigger.
   - **B8:** user with emergency contact → grace expiry → trigger is `pending_confirmation`, pause token email rendered to the contact's address; pause link extends grace; `deliver_after` elapsed (set timestamp back) → promotion to processing.
   - **B6:** trigger with recipients `delivered@resend.dev` + `bounced@resend.dev` → first run leaves trigger not-completed, retry task scheduled; after 3 attempts → trigger `failed`, alert email + audit row exist.
   - **B7:** beneficiary with 3 capsules (`delivery_order` 2,1,3) → exactly one email; body contains capsules in order 1,2,3.
   - **B9/B10 regression:** create user with 2 capsules + uploaded blobs (real storage upload in test), delete account, run purge → `list()` on every capsule prefix returns empty; `users` row gone; cascades verified; Supabase auth user gone; audit rows anonymized.
3. Token single-use regression (extend `test_06_checkin_tokens.py`): use confirm token twice → 409 second time; expired → 410.

**E2E run (phase gate):** inside the Phase-1 compose stack with live creds:

```
docker compose up -d --build
docker compose exec api pytest tests/ -x -q          # rewritten unit tests
docker compose exec api pytest tests/e2e/ -x -q      # incl. test_12
```

Both suites green = Phase 2 complete. Record output in `## Phase 2 E2E result` section here.

## Phase 2 E2E result

Run 2026-06-15, against the rebuilt compose stack (`NGINX_PORT=8080 docker compose up -d --build`, all 5 services healthy):

```
docker compose exec api pytest tests/ -q --ignore=tests/e2e
................................................................................                                 [100%]
80 passed in 31.08s

docker compose exec api pytest tests/e2e/ -q
......s..s................................................................................................       [100%]
113 passed, 2 skipped in <run time>
```

Both suites green — **Phase 2 (B1–B21) complete**. The 2 skips are the Supabase signup rate-limit fallback path in `test_02_auth.py` (expected/no-op when Supabase doesn't 429 during the run, not failures).

Fixes landed this session beyond the original T1–T14 scope, found while closing out the e2e gate:

- **Cross-event-loop asyncpg pooling bug (test-only):** `backend/tests/e2e/conftest.py` now points `app.db.session.engine`/`AsyncSessionLocal` at the test's `NullPool` engine, so worker-task code (`checkin_tasks`/`delivery_tasks`/`cleanup_tasks`) invoked directly from e2e tests doesn't reuse pooled asyncpg connections across pytest-asyncio's per-test event loops (`Future attached to a different loop`).
- **Supabase admin-client header contamination (production bug):** `get_supabase()`'s shared singleton has its service-role `Authorization` header overwritten by `sign_in_with_password`/`sign_up`/`refresh_session`/`verify_otp` (SIGNED_IN event), causing `auth.admin.delete_user` to fail with 403 `User not allowed`. Added `get_supabase_admin()` (`app/core/supabase.py`, fresh client per call — mirrors the existing `get_storage()` pattern) and switched both `auth.admin.delete_user` call sites (`auth_service.signup`'s B19 rollback, `cleanup_tasks._purge_user_account` step 3) to use it.

T12 (B14) confirmed: `backend/app/core/security.py` deleted; `python-jose`/`passlib` removed from `requirements.txt` (documented via comment).
