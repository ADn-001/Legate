"""Phase 5 security hardening E2E tests (T-test).

Covers:
  S1  — startup validation: weak/missing secrets raise at boot
  S2  — delivery-wrapping-key: GET→405, POST→200+audit, rate-limited at 5/min
  S3  — HTML injection in delivery email (bleach sanitizer + html.escape)
  S4  — checkin token: reuse→409, expiry→410, length≥64 urlsafe bytes
  S5  — checkin error pages: no unescaped XSS from token parameter
  NFR-09 — delivery worker logs no plaintext capsule content

Lint guards (T6) are verified outside this file:
  Backend:  docker compose exec api ruff check .
  Frontend: cd frontend && npm run lint
A deliberate console.log("cek") in frontend code must fail lint.
"""

import logging
import os
import secrets
import uuid
from datetime import datetime, timezone, timedelta

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select, desc

from tests.e2e.conftest import AsyncSessionLocal
from app.config import get_settings
from app.db.models.checkin import (
    CheckInEvent,
    EventStatus,
    TokenType,
    ReleaseTrigger,
    TriggerReason,
    TriggerStatus,
)
from app.db.models.delivery import DeliveryEvent
from app.db.models.audit import AuditLog
from app.worker.tasks.delivery_tasks import _run_delivery, _sanitize_html
from app.main import app

# Re-use helpers from test_12 — avoids duplicating fixture code.
from tests.e2e.test_12_checkin_lifecycle import (
    _create_local_user,
    _add_beneficiary,
    _add_capsule,
    _test_inbox,
)

NOW = lambda: datetime.now(timezone.utc)  # noqa: E731


# ── Private helpers ───────────────────────────────────────────────────────────

def _unique_ip() -> str:
    """Unique non-routable IP (TEST-NET-1, RFC 5737) so rate-limit buckets
    are isolated between tests and from the shared session fixtures."""
    n = uuid.uuid4().int
    return f"192.0.2.{n % 256}"


def _make_authed_client(ip: str, token: str) -> AsyncClient:
    """Authenticated ASGI test client with a custom remote-address IP."""
    transport = ASGITransport(app=app, client=(ip, 9999))
    return AsyncClient(
        transport=transport,
        base_url="http://test",
        follow_redirects=True,
        headers={"Authorization": f"Bearer {token}"},
    )


# ═════════════════════════════════════════════════════════════════════════════
# S1 — Startup secrets validation
# ═════════════════════════════════════════════════════════════════════════════

def test_s1_short_secret_rejected():
    """_validate_secret raises ValueError for values under 32 characters."""
    from app.config import _validate_secret

    with pytest.raises(ValueError, match="too short"):
        _validate_secret("TEST_SECRET", "short")


def test_s1_known_weak_fragments_rejected():
    """_validate_secret raises ValueError when the value contains a known-weak word."""
    from app.config import _validate_secret

    weak_values = [
        "fake-" + "x" * 40,
        "changeme-" + "x" * 40,
        "secret-key-" + "x" * 40,
        "example-secret-" + "x" * 40,
        "replace-me-now-" + "x" * 40,
    ]
    for val in weak_values:
        with pytest.raises(ValueError, match="known-weak placeholder"):
            _validate_secret("TEST_SECRET", val)


def test_s1_strong_secret_accepted():
    """_validate_secret accepts a properly generated secret (no raises)."""
    from app.config import _validate_secret

    strong = secrets.token_hex(24)  # 48 hex chars — well above 32, no weak words
    result = _validate_secret("TEST_SECRET", strong)
    assert result == strong


# ═════════════════════════════════════════════════════════════════════════════
# S2 — Delivery-wrapping-key hardening
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_s2_get_delivery_key_returns_405(auth_client: AsyncClient):
    """GET /auth/me/delivery-wrapping-key must return 405 (no caching, no browser history)."""
    res = await auth_client.get("/auth/me/delivery-wrapping-key")
    assert res.status_code == 405, (
        f"S2: GET should return 405 (method not allowed), got {res.status_code}"
    )


@pytest.mark.asyncio
async def test_s2_post_delivery_key_creates_audit_log(http: AsyncClient, registered_user):
    """POST /auth/me/delivery-wrapping-key returns 200 and writes an audit_logs row.

    Uses a fresh login rather than the session-scoped auth_client token — the
    suite runs for 60+ minutes and Supabase JWTs expire after 1 hour, so the
    session token is stale by the time this test runs.
    """
    import asyncio
    login = None
    for _attempt in range(4):
        login = await http.post("/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        })
        if login.status_code == 200:
            break
        if login.status_code in (429, 503):
            pytest.skip("Supabase rate limit / unavailable — re-run after cooldown")
        if _attempt < 3:
            await asyncio.sleep(5 * (_attempt + 1))
    assert login is not None and login.status_code == 200, f"Login failed: {login.text}"
    fresh_token = login.json()["access_token"]

    res = await http.post(
        "/auth/me/delivery-wrapping-key",
        headers={"Authorization": f"Bearer {fresh_token}"},
    )
    assert res.status_code == 200, f"S2: POST returned {res.status_code}: {res.text}"
    body = res.json()
    assert "wrapping_key" in body, "S2: response missing wrapping_key field"
    assert len(body["wrapping_key"]) == 64, (
        f"S2: wrapping_key length {len(body['wrapping_key'])} != 64"
    )
    assert all(c in "0123456789abcdef" for c in body["wrapping_key"]), (
        "S2: wrapping_key is not a lowercase hex string"
    )

    # Audit log row must have been written.
    async with AsyncSessionLocal() as db:
        log = (await db.execute(
            select(AuditLog)
            .where(AuditLog.event_type == "delivery_wrapping_key_accessed")
            .order_by(desc(AuditLog.created_at))
            .limit(1)
        )).scalar_one_or_none()
    assert log is not None, (
        "S2: no audit_log row with event_type='delivery_wrapping_key_accessed'"
    )


@pytest.mark.asyncio
async def test_s2_delivery_key_rate_limited_at_5_per_minute(http: AsyncClient, registered_user):
    """6th POST on delivery-wrapping-key from the same IP returns 429.

    Uses a fresh login — the session-scoped token expires after 1 hour and this
    test runs late in the suite.

    Sends all 8 requests concurrently — sequential NullPool requests take ~10 s
    each (new asyncpg connection per call), so 5 sequential calls span >1 minute
    and the rate-limit window resets before the 6th lands. Concurrent requests
    all arrive within the same 1-minute bucket, guaranteed to trigger the limit.
    """
    import asyncio
    login = None
    for _attempt in range(4):
        login = await http.post("/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        })
        if login.status_code == 200:
            break
        if login.status_code in (429, 503):
            pytest.skip("Supabase rate limit / unavailable — re-run after cooldown")
        if _attempt < 3:
            await asyncio.sleep(5 * (_attempt + 1))
    assert login is not None and login.status_code == 200, f"Login failed: {login.text}"
    fresh_token = login.json()["access_token"]

    ip = _unique_ip()
    async with _make_authed_client(ip, fresh_token) as client:
        # 8 concurrent requests — at least the last 3 must be rate-limited (limit is 5).
        tasks = [client.post("/auth/me/delivery-wrapping-key") for _ in range(8)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

    valid = [r for r in responses if not isinstance(r, Exception)]
    hit_429 = any(r.status_code == 429 for r in valid)
    assert hit_429, (
        f"S2: rate limit (5/min) never triggered after 8 concurrent calls. "
        f"Status codes: {[r.status_code for r in valid]}"
    )


# ═════════════════════════════════════════════════════════════════════════════
# S3 — HTML injection sanitization
# ═════════════════════════════════════════════════════════════════════════════

def test_s3_sanitize_html_strips_script_and_event_handlers():
    """_sanitize_html removes <script> tags and event handler attributes from rich HTML.

    bleach HTML-escapes disallowed tags rather than stripping them entirely, so
    <img onerror=alert(1)> becomes &lt;img ... onerror=alert(1)&gt; — the word
    "onerror" is still present as inert text, not as an executable attribute.
    The correct check: no unescaped HTML tag (<...>) contains onerror.
    """
    import re
    xss_rich = (
        '<script>alert(1)</script>'
        '<img src=x onerror=alert(1)>'
        '<b>safe bold</b>'
        '<p>safe paragraph</p>'
    )
    result = _sanitize_html(xss_rich)
    # No unescaped <script> tag — bleach must have escaped or removed it.
    assert '<script>' not in result, "S3: <script> tag survived bleach sanitization as executable HTML"
    # onerror must not appear inside an actual (unescaped) HTML tag.
    assert not re.search(r'<[^>]*onerror', result), (
        "S3: onerror attribute survived sanitization inside an executable HTML tag"
    )
    # bleach's allowlist preserves <b> and <p>
    assert '<b>' in result, "S3: allowed <b> tag was wrongly removed"
    assert 'safe bold' in result, "S3: safe text content was removed by sanitizer"


def test_s3_beneficiary_name_html_escaping():
    """_esc (html.escape) converts special chars so XSS in names is impossible."""
    from app.core.email import _esc

    xss_name = '<b>Bob</b><script>x</script>'
    escaped = _esc(xss_name)
    assert '<b>' not in escaped, "S3: <b> in name not escaped"
    assert '<script>' not in escaped, "S3: <script> in name not escaped"
    assert '&lt;b&gt;' in escaped, "S3: html.escape not applied to name"
    assert '&lt;script&gt;' in escaped, "S3: html.escape not applied to name"


def test_s3_strip_header_removes_crlf():
    """_strip_header removes CR/LF from subject-line fragments (header injection)."""
    from app.core.email import _strip_header

    injected = "Normal Name\r\nBcc: attacker@evil.com"
    result = _strip_header(injected)
    assert '\r' not in result, "S3: CR not stripped from email header"
    assert '\n' not in result, "S3: LF not stripped from email header"
    assert 'Normal Name' in result, "S3: legitimate content stripped from header"


@pytest.mark.asyncio
async def test_s3_full_delivery_xss_sanitized():
    """Full E2E: capsule with XSS rich-text content → delivery → no <script>/onerror
    in the rendered email body.

    Steps:
      1. Create user with real delivery key material.
      2. Create beneficiary with XSS HTML in the name.
      3. Encrypt XSS content with the user's CEK, upload to Supabase storage.
      4. Force delivery via _run_delivery.
      5. Get the email body (Resend API → fallback renderer).
      6. Assert <script> and onerror absent; allowed <b> content present.
    """
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from app.core.supabase import get_storage
    from app.db.models.beneficiary import Beneficiary, BeneficiaryStatus
    from app.db.models.capsule import Capsule
    from app.worker.tasks.delivery_tasks import _build_capsule_html

    cfg = get_settings()
    storage = get_storage()

    # 1. User with real delivery key material
    u = await _create_local_user(with_delivery_key=True)
    user_id: uuid.UUID = u["user_id"]
    cek: bytes = u["cek"]

    # 2. Beneficiary with XSS in the name
    xss_bene_name = '<b>Bob</b><script>x</script>'
    bene_email = f"delivered+s3{uuid.uuid4().hex[:8]}@resend.dev"
    async with AsyncSessionLocal() as db:
        bene = Beneficiary(
            user_id=user_id,
            full_name=xss_bene_name,
            email=bene_email,
            is_emergency_contact=False,
            status=BeneficiaryStatus.active,
        )
        db.add(bene)
        await db.commit()
        bene_id = bene.id

    # 3. Capsule with XSS rich-text content, encrypted
    xss_content = '<script>alert(1)</script><img src=x onerror=alert(1)><b>safe bold</b>'
    iv = os.urandom(12)
    encrypted = AESGCM(cek).encrypt(iv, xss_content.encode("utf-8"), None)

    capsule_id, _ = await _add_capsule(
        user_id, bene_id,
        title="S3 XSS Test Capsule",
        delivery_order=1,
    )
    storage_path = f"{user_id}/{capsule_id}/content.enc"
    storage.from_(cfg.supabase_storage_bucket_content).upload(
        storage_path,
        bytes(encrypted),
        {"content-type": "application/octet-stream"},
    )
    async with AsyncSessionLocal() as db:
        cap = await db.get(Capsule, capsule_id)
        cap.storage_object_path = storage_path
        cap.cipher_iv = iv
        await db.commit()

    # 4. Force delivery via trigger
    async with AsyncSessionLocal() as db:
        trigger = ReleaseTrigger(
            user_id=user_id,
            triggered_at=NOW(),
            reason=TriggerReason.checkin_missed,
            status=TriggerStatus.processing,
        )
        db.add(trigger)
        await db.commit()
        trigger_id = trigger.id

    await _run_delivery(str(trigger_id), attempt=1)

    # 5. Get email body: try Resend API first, fall back to in-process renderer
    async with AsyncSessionLocal() as db:
        events = (await db.execute(
            select(DeliveryEvent).where(DeliveryEvent.release_trigger_id == trigger_id)
        )).scalars().all()

    message_id = next((e.resend_message_id for e in events if e.resend_message_id), None)

    html_body = ""
    if message_id:
        try:
            import resend
            from resend.exceptions import ResendError
            resend.api_key = cfg.resend_api_key
            email_obj = resend.Emails.get(email_id=message_id)
            html_body = (
                email_obj.get("html")
                if isinstance(email_obj, dict)
                else getattr(email_obj, "html", "")
            ) or ""
        except Exception as exc:
            if "restricted" not in str(exc).lower():
                raise

    if not html_body:
        # Fallback: re-render through the production capsule renderer
        from app.core.supabase import get_supabase
        async with AsyncSessionLocal() as db:
            cap = await db.get(Capsule, capsule_id)
        sb = get_supabase()
        html_body = _build_capsule_html(capsule=cap, cek=cek, supabase=sb, cfg=cfg)

    import re as _re
    assert html_body, "S3: could not obtain delivery email body for injection verification"
    assert '<script>' not in html_body, (
        "S3: <script> tag survived sanitization in delivery email body"
    )
    # bleach escapes disallowed tags, so "onerror" may appear as harmless text
    # inside &lt;img...&gt;. The real check: no unescaped tag contains onerror.
    assert not _re.search(r'<[^>]*onerror', html_body), (
        "S3: onerror attribute survived sanitization inside an executable HTML tag in delivery body"
    )
    assert 'safe bold' in html_body, (
        "S3: bleach over-sanitized allowed content (<b>safe bold</b>) from delivery body"
    )


# ═════════════════════════════════════════════════════════════════════════════
# S4 — Checkin token: reuse, expiry, minimum length
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_s4_token_reuse_returns_409(http: AsyncClient):
    """Redeeming a confirm token twice returns 409 Conflict on the second attempt."""
    u = await _create_local_user()
    token = secrets.token_urlsafe(64)
    async with AsyncSessionLocal() as db:
        db.add(CheckInEvent(
            user_id=u["user_id"],
            schedule_id=u["schedule_id"],
            token=token,
            token_type=TokenType.confirm,
            expires_at=NOW() + timedelta(days=7),
            status=EventStatus.pending,
        ))
        await db.commit()

    # First redemption: success
    res1 = await http.get(f"/checkin/confirm?token={token}")
    assert res1.status_code == 200, f"S4: first confirm returned {res1.status_code}"

    # Second redemption: conflict
    res2 = await http.get(f"/checkin/confirm?token={token}")
    assert res2.status_code == 409, (
        f"S4: expected 409 on token reuse, got {res2.status_code}: {res2.text[:200]}"
    )


@pytest.mark.asyncio
async def test_s4_expired_token_returns_410(http: AsyncClient):
    """A confirm token whose expires_at is in the past returns 410 Gone."""
    u = await _create_local_user()
    token = secrets.token_urlsafe(64)
    async with AsyncSessionLocal() as db:
        db.add(CheckInEvent(
            user_id=u["user_id"],
            schedule_id=u["schedule_id"],
            token=token,
            token_type=TokenType.confirm,
            expires_at=NOW() - timedelta(days=1),   # already expired
            status=EventStatus.pending,
        ))
        await db.commit()

    res = await http.get(f"/checkin/confirm?token={token}")
    assert res.status_code == 410, (
        f"S4: expected 410 for expired token, got {res.status_code}: {res.text[:200]}"
    )


@pytest.mark.asyncio
async def test_s4_dispatched_tokens_are_64_urlsafe_bytes():
    """Tokens produced by _dispatch_due_checkins are ≥ 64 urlsafe base64 characters (NFR-12)."""
    import re
    from app.worker.tasks.checkin_tasks import _dispatch_due_checkins

    u = await _create_local_user(next_dispatch_at=NOW() - timedelta(hours=2))
    await _dispatch_due_checkins()

    async with AsyncSessionLocal() as db:
        events = (await db.execute(
            select(CheckInEvent).where(CheckInEvent.user_id == u["user_id"])
        )).scalars().all()

    assert events, "S4: _dispatch_due_checkins produced no tokens"
    for event in events:
        assert len(event.token) >= 64, (
            f"S4: token length {len(event.token)} < 64 for type={event.token_type}"
        )
        assert re.fullmatch(r"[A-Za-z0-9_\-]+", event.token), (
            f"S4: token contains non-urlsafe characters: {event.token[:20]}…"
        )


# ═════════════════════════════════════════════════════════════════════════════
# S5 — Checkin error pages: no XSS from token parameter
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_s5_xss_token_not_reflected_in_error_page(http: AsyncClient):
    """A token containing an XSS payload is never echoed unescaped in the HTML error page."""
    # The token is not echoed by the service — it returns a static "Token not found"
    # error. This test verifies that even if a parser were ever to echo the token,
    # the result would not contain an executable <script> tag.
    xss_token = "<script>alert('xss')</script>"
    res = await http.get(f"/checkin/confirm?token={xss_token}")

    assert res.status_code in (400, 404, 410, 422), (
        f"S5: unexpected status code {res.status_code}"
    )
    # The raw XSS payload must not appear in the response body
    assert "<script>alert" not in res.text, (
        "S5: XSS token payload is reflected unescaped in checkin error page"
    )


@pytest.mark.asyncio
async def test_s5_checkin_error_messages_are_html_escaped(http: AsyncClient):
    """Error messages from the checkin service are rendered inside html.escape() — no raw HTML."""
    u = await _create_local_user()
    token = secrets.token_urlsafe(64)
    async with AsyncSessionLocal() as db:
        db.add(CheckInEvent(
            user_id=u["user_id"],
            schedule_id=u["schedule_id"],
            token=token,
            token_type=TokenType.confirm,
            expires_at=NOW() - timedelta(days=1),   # expired → 410 path
            status=EventStatus.pending,
        ))
        await db.commit()

    res = await http.get(f"/checkin/confirm?token={token}")
    assert res.status_code == 410, f"S5: expected 410, got {res.status_code}"

    # The service detail "Token expired" must appear somewhere in the page.
    assert "expired" in res.text.lower(), (
        "S5: error detail 'Token expired' not present in 410 response"
    )
    # No raw <script> tag should be in any error response.
    assert "<script>" not in res.text.lower(), (
        "S5: <script> tag found in checkin error page"
    )


# ═════════════════════════════════════════════════════════════════════════════
# NFR-09 — Delivery worker logs no plaintext capsule content
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_nfr09_delivery_worker_logs_no_plaintext(caplog):
    """_run_delivery must not log any plaintext capsule content.

    A known marker string is embedded in the capsule content. After delivery,
    the marker must not appear in any captured log record from any logger at
    any level.
    """
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from app.core.supabase import get_storage
    from app.db.models.capsule import Capsule

    cfg = get_settings()
    storage = get_storage()

    MARKER = f"nfr09-plaintext-{uuid.uuid4().hex}"

    u = await _create_local_user(with_delivery_key=True)
    user_id = u["user_id"]
    cek = u["cek"]

    bene_id = await _add_beneficiary(
        user_id, email=f"delivered+nfr09{uuid.uuid4().hex[:8]}@resend.dev"
    )
    capsule_id, _ = await _add_capsule(
        user_id, bene_id,
        title="NFR-09 Log Audit Capsule",
        delivery_order=1,
    )

    # Encrypt the marker and upload to storage.
    iv = os.urandom(12)
    encrypted = AESGCM(cek).encrypt(iv, MARKER.encode("utf-8"), None)
    storage_path = f"{user_id}/{capsule_id}/content.enc"
    storage.from_(cfg.supabase_storage_bucket_content).upload(
        storage_path,
        bytes(encrypted),
        {"content-type": "application/octet-stream"},
    )
    async with AsyncSessionLocal() as db:
        cap = await db.get(Capsule, capsule_id)
        cap.storage_object_path = storage_path
        cap.cipher_iv = iv
        await db.commit()

    async with AsyncSessionLocal() as db:
        trigger = ReleaseTrigger(
            user_id=user_id,
            triggered_at=NOW(),
            reason=TriggerReason.checkin_missed,
            status=TriggerStatus.processing,
        )
        db.add(trigger)
        await db.commit()
        trigger_id = trigger.id

    # Capture ALL log output at DEBUG level during delivery.
    with caplog.at_level(logging.DEBUG):
        await _run_delivery(str(trigger_id), attempt=1)

    assert MARKER not in caplog.text, (
        f"NFR-09 VIOLATION: plaintext capsule content found in delivery worker logs. "
        f"Marker prefix: {MARKER[:30]}…"
    )
