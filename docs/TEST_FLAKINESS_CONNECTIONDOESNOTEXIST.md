# E2E Test Flakiness: `asyncpg.exceptions.ConnectionDoesNotExistError`

**Status:** Open — root cause identified, fix not yet implemented (deferred by user decision on 2026-07-04, immediately after Phase B sign-off).
**Owner:** unassigned — this doc exists so a future agent/session can pick it up without re-deriving the diagnosis below.
**Impact:** Non-deterministic test failures in `backend/tests/e2e/`. Does **not** indicate a product bug — every failure observed so far traces to test infrastructure, not application logic.

---

## 1. Symptom

Full-suite runs (`docker compose exec api pytest -v`, ~228 tests, ~25–47 min) intermittently fail a handful of e2e tests with:

```
asyncpg.exceptions.ConnectionDoesNotExistError: connection was closed in the middle of operation
```

surfaced through SQLAlchemy as either:

```
sqlalchemy.exc.DBAPIError: (sqlalchemy.dialects.postgresql.asyncpg.Error) <class 'asyncpg.exceptions.ConnectionDoesNotExistError'>: connection was closed in the middle of operation
```

or, when it happens inside asyncpg's own connection-prepare path before SQLAlchemy wraps it:

```
sqlalchemy.dialects.postgresql.asyncpg.AsyncAdapt_asyncpg_dbapi.Error: <class 'asyncpg.exceptions.ConnectionDoesNotExistError'>: connection was closed in the middle of operation
```

A related teardown-only failure also appears on the last test of a run:

```
RuntimeError: Event loop is closed
```
at `tests/e2e/conftest.py:140` (`_test_engine.dispose()` in the session-scoped `event_loop` fixture), plus a trailing
`RuntimeWarning: coroutine 'AsyncEngine.dispose' was never awaited`.

## 2. Evidence this is infrastructure, not a logic bug

Two full runs of the same "flaky" test set were captured back to back (2026-07-04):

| Run | Failures |
|---|---|
| Run 1 (full suite, 228 tests, 47 min) | `test_04_capsules.py::test_delete_capsule_sets_pending_deletion`, `test_06_checkin_tokens.py::test_confirm_token_single_use_second_call_409`, `test_12_checkin_lifecycle.py::test_b1_dispatch_runs_twice_sends_once`, `::test_b2_grace_expiry_creates_exactly_one_trigger`, `::test_b6_per_recipient_retry_then_permanent_failure`, `::test_b9_b10_full_account_purge`, plus `test_users.py` teardown error |
| Run 2 (isolated re-run of the same files, 41 tests, 24 min) | `test_04_capsules.py::test_list_capsules_exposes_has_recipients`, `test_06_checkin_tokens.py::test_confirm_used_token_returns_409`, `test_12_checkin_lifecycle.py::test_b5_grace_reminders_day3_day7_once_per_cycle`, `::test_b7_single_email_per_beneficiary_ordered_capsules`, plus the same `test_users.py` teardown error |

**Zero overlap** between the two failure sets, run back to back against the same code. Every test in Run 1's failure list passed clean in Run 2, and vice versa. A real logic bug tied to specific business rules would fail the same assertion deterministically; a connection getting killed at a random point in a 25–47 minute run hits whichever query happens to be in flight at that moment, which is exactly what's observed. This rules out Phase B's `interval_delta()`/`grace_delta()` precedence logic (or any other business logic) as the cause — those tests (`test_16_demo_mode.py`, 12/12) have passed clean in every run.

## 3. Root cause

`backend/tests/e2e/conftest.py` already monkey-patches `asyncpg.connect` (lines ~27–70) with a retry-with-backoff wrapper, `_asyncpg_connect_with_retry`. It exists to handle Supabase's free-tier session pooler (PgBouncer) getting saturated:

- `ConnectionFailureError`, `ConnectionAbortedError`, `ConnectionResetError`, `OSError` → retried (handles EAUTHTIMEOUT / SSL handshake timeouts during connection **establishment**)
- `InternalServerError` containing `EMAXCONNSESSION` / "max clients" → retried (handles the 15-slot free-tier pool being full at **connect time**)

This wrapper only guards the moment a connection is opened. It does **not** cover `ConnectionDoesNotExistError`, which is a different failure class entirely: a connection that was already successfully established gets killed by Supabase's pooler *while a query is in flight* (mid-`prepare`, mid-`execute`, or mid-`commit`). There is currently no retry coverage for this at the query-execution level anywhere in the test fixtures — only `_admin_call` (Supabase admin API calls) and the login step in `registered_user` have execution-level retries, and both are narrowly scoped to their own call sites, not general DB query execution.

Given a free-tier Supabase project shared across a long-running suite (uvicorn + Celery worker + Celery beat + the test process itself all holding pooled connections via `NullPool`, meaning every single query opens a fresh connection), it's expected that PgBouncer will occasionally reap a connection mid-query under sustained load. The comment block in `conftest.py` at lines 87–90 already acknowledges `ConnectionDoesNotExistError` as a known category (`statement_cache_size=0` was added specifically because the prepared-statement cache breaks behind the pooler and "can surface as `ConnectionDoesNotExistError` mid-prepare") but a config workaround for the cache issue was applied without adding a matching retry for the connection-drop itself.

The `test_users.py` teardown `RuntimeError: Event loop is closed` is a secondary symptom of the same root cause: if the last test's session got a connection killed, the session-scoped `event_loop` fixture's cleanup (`_test_engine.dispose()`) can race against an already-torn-down loop.

## 4. Recommended fix (not yet implemented)

Add query-level retry, not just connect-level retry. Options, roughly in order of invasiveness:

1. **Narrowest fix** — wrap the specific test-helper functions that do raw `db.execute()`/`db.commit()` calls (e.g. `_insert_test_token`, `_add_capsule`, `_add_beneficiary` in `test_06_checkin_tokens.py` / `test_12_checkin_lifecycle.py`) with a retry-on-`ConnectionDoesNotExistError` decorator, similar in spirit to `_admin_call`.
2. **Broader fix** — add a SQLAlchemy engine-level event listener (`@event.listens_for(_test_engine.sync_engine, "handle_error")`) or a pytest fixture-level retry wrapper around `AsyncSessionLocal()` context managers used across the e2e test modules, so any test using the shared session fixtures gets the retry transparently instead of requiring each test file to opt in individually.
3. **Fix the teardown error alongside it** — guard `_test_engine.dispose()` in the `event_loop` fixture teardown with a check for `loop.is_closed()` before calling `run_until_complete`, or move disposal into an earlier fixture scope that's guaranteed to run before the loop closes.

Whichever approach is chosen, it should **not** touch production code (`app/`) — this is purely a test-harness reliability issue on Supabase's free-tier connection limits, not an application-level connection-handling gap. Before implementing, confirm with the user whether this is still in scope, since it's infrastructure hardening outside `PLAN_PHASES_A_B_C.md`.

## 5. Non-fixes / things ruled out

- Not caused by Phase B (`interval_delta()`/`grace_delta()`, demo-mode gating, migration `d7f1a3c9e5b2`) — none of the failing tests touch that code path, and the failure set changes between identical re-runs.
- Not a missing migration or schema issue — `alembic upgrade head` completed successfully and the new `check_interval_minutes`/`grace_period_minutes` columns are confirmed present (visible in the SELECT statements in the failure tracebacks, which is only possible if the ORM model + DB schema already agree).
- Not fixed by re-running in isolation with fewer concurrent tests — Run 2 still hit it with only 41 tests over 24 minutes, so it's a function of cumulative connection churn over time, not raw parallelism (this suite doesn't use `pytest-xdist`).
