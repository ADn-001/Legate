# Phase 5 — Security Hardening

**Covers audit items:** S1–S6 (§5 of `AUDIT_REPORT.md`)
**Assumes:** Phases 1–4 are 100% complete — in particular the rewritten delivery renderer (Phase 2 T9), rich-text + bleach sanitizer (Phase 4 T9), and rate limiting (Phase 4 T7) already exist.
**Goal:** No known-secret defaults, no HTML injection anywhere, documented deviations, security regression tests.
**Rules:** No mocks. Injection tests verify the **actual sent email body** via the Resend API, not a rendered string in memory.

---

## T1 (S1) — Secrets must be required, no known defaults

`config.py:41-42`: `supabase_jwt_secret`/`delivery_secret` default to `"fake-..."` strings — if env is unset the app silently runs with derivable secrets (the delivery CEK wrapping key!).

1. Remove both defaults — make the fields required (`str` with no default) so pydantic-settings fails startup loudly.
2. Add a startup validator rejecting obviously weak values: length < 32, or containing `fake`/`changeme`/`secret` → raise with a clear message ("generate with `openssl rand -base64 48`").
3. Same treatment for `secret_key` (already required — verify) and `database_url`.
4. Update both `.env.example` files with generation instructions. Verify compose passes them (Phase 1 already does).

## T2 (S2) — Delivery-wrapping-key endpoint hardening

`GET /auth/me/delivery-wrapping-key` (`api/auth.py:103-115`) returns the HMAC wrapping key to any authenticated user — by design (client wraps CEK for delivery), but it must not be casual.

1. Change to `POST` (no caching, no prefetch, not in browser history).
2. Write an `audit_logs` row on every access (user, timestamp, IP).
3. Apply a strict rate limit (5/min/user — slowapi bucket from Phase 4 T7).
4. Add a docstring + `docs/SECURITY.md` section explaining the design: key is per-deployment HMAC over user id with `delivery_secret`; secrecy depends on S1; rotating `delivery_secret` invalidates all delivery blobs (documented operational warning).

## T3 (S3) — Sanitize all user content in outbound email + pages

`delivery_tasks.py:137-148` + `core/email.py`: decrypted capsule text interpolated into HTML unescaped; beneficiary/nominator names unescaped → HTML injection into delivery emails.

1. Capsule rich-text HTML: run through the `bleach` allowlist sanitizer (Phase 4 T9 — `b,strong,i,em,ul,li,p,br`, no attributes) at **render time** in the delivery worker and the preview template endpoint. Never trust the stored HTML even though the editor sanitizes.
2. ALL other user-supplied strings in any email template (names, capsule titles, beneficiary names, emails shown in copy) → `html.escape()`. Audit every template in `core/email.py` and the check-in/grace/nomination/removal/pause emails from Phases 2–4; fix each.
3. Subject lines: strip CR/LF from user-supplied fragments (header injection).

## T4 (S5) — Escape backend HTML error pages

`api/checkin.py` token pages echo exception `detail` into HTML unescaped. `html.escape(message)` in every `_render`/format call (confirm/snooze/pause/expired/error variants). Today the messages are internal, but a future refactor could pass user input — close it now.

## T5 (S4 + S6) — Documented deviations (no code change)

1. S4: DB single-use tokens instead of Redis blacklist (NFR-12) — user-approved. Add `docs/SECURITY.md` entry: tokens are 64-byte urlsafe, single-use enforced by status mutation in the same transaction, expiry 7 days; equivalent guarantees to a blacklist.
2. S6: snooze/confirm links are GETs that mutate state — required for email-client clicks, standard pattern; documented with CSRF analysis (tokens are unguessable bearer secrets; no cookie auth on those pages).
3. Create `docs/SECURITY.md` consolidating: encryption architecture summary, S2 design note, S4/S6 deviations, secret-generation instructions, threat-model notes from PRD §8 (R-03 worker isolation: confirm delivery worker never logs plaintext — grep all `logger` calls in `delivery_tasks.py` and `core/email.py`, NFR-09; remove/redact any that include content or decrypted values).

## T6 — Plaintext-logging sweep (NFR-09, supports R-03)

Systematic pass (this is the verification half of T5.3):
1. Grep `backend/` for `print(`, `logger.*(` in the delivery/cleanup path; assert no decrypted content, CEK bytes, wrapped keys, or recovery material is ever logged. Fix violations by logging ids/lengths only.
2. Frontend: ensure no `console.log` of CEK, password, phrase, or decrypted content (grep `src/crypto/`, stores, editor). Remove.
3. Add an ESLint `no-console` (error, allow `console.error` without sensitive args) and a backend ruff/flake8 rule or CI grep guard so regressions fail lint.

## T-test — Phase 5 E2E (final task — phase gate)

New `backend/tests/e2e/test_15_security.py` + Playwright additions, against the live compose stack:

1. **S1:** start an api container with `DELIVERY_SECRET` unset (compose run with env override) → process exits non-zero with the clear error; with a weak value (`fake-x`) → same. Stack with real values → healthy.
2. **S2:** `GET` on delivery-wrapping-key → 405; `POST` → 200 + new audit_logs row exists; 6th call in a minute → 429.
3. **S3 injection (the critical one):** create a capsule whose rich text includes `<script>alert(1)</script>`, `<img src=x onerror=alert(1)>`, and a beneficiary named `<b>Bob</b><script>x</script>`; force delivery to `delivered@resend.dev`; retrieve the sent email via Resend API (`GET /emails/{id}`) and assert: no `<script>` tag present, `onerror` absent, allowed tags (`<b>` from rich text) preserved, the beneficiary name's `<b>` is escaped (names get full escape, not allowlist).
4. **S4 regression:** confirm token reuse → 409; expired (timestamp manipulation) → 410; tokens in emails are ≥64 urlsafe bytes.
5. **S5:** request a checkin page with a token crafted to produce each error branch; response HTML contains no unescaped `<` from the message path (assert escaping by injecting a marker through the only controllable input — the token string itself rendered in any error page, if rendered).
6. **NFR-09:** run a full forced delivery, then `docker compose logs worker` — assert the known plaintext marker string from the test capsule does NOT appear in logs.
7. Lint guards from T6 are active: `npm run lint` and backend lint pass, and a deliberate `console.log("cek")` test commit fails lint (verify locally, then revert).

**Run:**
```
docker compose up -d --build
docker compose exec api pytest tests/e2e/test_15_security.py -x -q
cd frontend && npm run lint && npm run test:e2e -- --grep security
```
All green = Phase 5 complete. Record output in `## Phase 5 E2E result`.
