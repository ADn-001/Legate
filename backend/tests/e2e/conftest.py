"""
E2E test configuration — real Supabase, real Redis, real DB.
All test users prefixed with e2etest_ for easy cleanup.
"""

import asyncio
import base64
import os
import uuid
from datetime import datetime, timezone, timedelta

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool

from app.main import app
from app.config import get_settings
from app.db.models.user import User, UserSettings, EncryptionKey, UserStatus
from app.db.models.checkin import CheckInSchedule

TEST_PASSWORD = "TestPassword123!"
TEST_EMAIL_PREFIX = "e2etest_"

# ── Patch asyncpg.connect with EAUTHTIMEOUT retry ────────────────────────────
# asyncpg has a hardcoded ~10 s auth-challenge timeout inside its C protocol
# layer (separate from the Python-level `timeout=` parameter). When Supabase's
# PgBouncer is saturated — typically because uvicorn workers and the Celery
# worker are all holding connections — it accepts the TCP handshake but delays
# the auth challenge beyond 10 s, raising ConnectionFailureError(EAUTHTIMEOUT).
# Patching asyncpg.connect with retry+backoff gives PgBouncer time to drain
# its queue without crashing the test run.
import asyncpg as _asyncpg
_orig_asyncpg_connect = _asyncpg.connect


async def _asyncpg_connect_with_retry(*args, **kwargs):
    from asyncpg.exceptions import (
        ConnectionFailureError as _CFE,
        InternalServerError as _ISE,
    )
    # ConnectionAbortedError is raised by asyncpg when the SSL handshake
    # times out (60 s asyncio limit) — distinct from EAUTHTIMEOUT but
    # caused by the same root problem: PgBouncer saturation on the free tier.
    # InternalServerError(EMAXCONNSESSION) is raised when the PgBouncer
    # session-mode pool is full (15-slot free-tier limit). Stale connections
    # from container restarts can saturate the pool transiently; retrying with
    # backoff gives Supabase time to reclaim the slots.
    last_exc = None
    for _attempt in range(4):
        try:
            return await _orig_asyncpg_connect(*args, **kwargs)
        except (_CFE, ConnectionAbortedError, ConnectionResetError, OSError) as _exc:
            last_exc = _exc
            if _attempt < 3:
                await asyncio.sleep(10 * (_attempt + 1))   # 10 s, 20 s, 30 s
        except _ISE as _exc:
            _msg = str(_exc)
            if "EMAXCONNSESSION" in _msg or "max clients" in _msg.lower():
                last_exc = _exc
                if _attempt < 3:
                    await asyncio.sleep(15 * (_attempt + 1))  # 15 s, 30 s, 45 s
            else:
                raise
    raise last_exc


_asyncpg.connect = _asyncpg_connect_with_retry

# ── Test engine (NullPool) ───────────────────────────────────────────────────

_cfg = get_settings()
_test_engine = create_async_engine(
    _cfg.database_url.replace("postgresql://", "postgresql+asyncpg://"),
    poolclass=NullPool,    # NullPool: fresh asyncpg connection per checkout, discarded on return.
                           # AsyncAdaptedQueuePool causes "Future attached to a different loop":
                           # its cached connections bind their internal Futures to whatever loop
                           # was running at creation time (e.g. test_01 health test), but
                           # Starlette's BaseHTTPMiddleware call_next TaskGroup runs the handler
                           # as a new asyncio Task whose loop asyncpg sees as "different".
                           # NullPool avoids all of that — no persistent async state across reqs.
                           # EAUTHTIMEOUT from PgBouncer saturation is handled by the
                           # asyncpg.connect monkey-patch above (4 retries, 10/20/30 s backoff).
    echo=False,
    connect_args={"timeout": 120},
)
AsyncSessionLocal = async_sessionmaker(_test_engine, expire_on_commit=False, class_=AsyncSession)


# ── Patch app.db.session for worker-task code paths ──────────────────────────
# Worker task functions (checkin_tasks/delivery_tasks/cleanup_tasks) import
# AsyncSessionLocal from app.db.session. Override it to use the test engine so
# all DB operations in the test process share the same pool and event loop.
import app.db.session as _db_session_module  # noqa: E402

_db_session_module.engine = _test_engine
_db_session_module.AsyncSessionLocal = AsyncSessionLocal

_SIGNUP_CEK = "dGVzdGNlaw=="
_SIGNUP_IV = "dGVzdGl2AA=="
_SIGNUP_SALT = "dGVzdHNhbHQ="
_SIGNUP_DCEK = "dGVzdGRlbGl2ZXJ5Y2VrAA=="
_SIGNUP_DIV = "dGVzdGRlbGl2ZXJ5aXY="


# Supabase validates recipient-domain deliverability at sign_up, so test
# emails must use a REAL mailbox. Plus-addressing keeps each address unique
# while landing in one inbox. Override with E2E_MAILBOX if needed.
E2E_MAILBOX = os.environ.get("E2E_MAILBOX", "995homebase995@gmail.com")


def make_test_email() -> str:
    local, domain = E2E_MAILBOX.split("@", 1)
    return f"{local}+{TEST_EMAIL_PREFIX}{uuid.uuid4().hex[:8]}@{domain}"


# NOTE: the parent tests/conftest.py no longer mocks anything (Phase 2
# T-test); all suites run against real services and the real test database.


# ── Session-scoped event loop (prevents per-module event_loop conflicts) ──────
# pytest-asyncio 0.23.x creates per-module <event_loop> fixtures for module-scoped
# async fixtures defined in conftest.py. Without a session event_loop, the first
# module's <event_loop> gets pinned to all conftest fixtures, causing subsequent
# modules to fail with "fixture '<test_01>::<event_loop>' not found".

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    # Dispose pooled connections before closing the loop so asyncpg can send
    # proper close frames. Without this, asyncpg logs "Future is not running"
    # warnings when the loop closes while connections are still in the pool.
    loop.run_until_complete(_test_engine.dispose())
    loop.close()


# ── Override app DB session to use the test engine ───────────────────────────

async def _override_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@pytest.fixture(scope="session", autouse=True)
def override_db_dependency():
    from app.db.session import get_db_session
    app.dependency_overrides[get_db_session] = _override_db
    yield
    app.dependency_overrides.pop(get_db_session, None)


# ── Shared clients ───────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
async def http():
    """Unauthenticated ASGI client — session-scoped to avoid per-module event_loop conflicts."""
    transport = ASGITransport(app=app, raise_app_exceptions=True)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        follow_redirects=True,
    ) as client:
        yield client


# ── Registered user (admin-confirmed, logged in) ─────────────────────────────

def _make_admin_client():
    """Fresh Supabase client with service role key — not the app singleton.
    The singleton's options.headers gets contaminated with a user JWT on SIGNED_IN
    events, causing admin API calls to return 403. Always create a fresh client
    for admin operations in test fixtures.
    """
    from supabase import create_client
    cfg = get_settings()
    return create_client(cfg.supabase_url, cfg.supabase_service_role_key)


def _admin_call(fn, *args, max_attempts: int = 4, **kwargs):
    """Call a synchronous Supabase admin API function with retry on AuthRetryableError.

    Supabase free-tier admin endpoints (list_users, update_user_by_id, create_user)
    can return a retryable 5xx transiently during high load. Retrying with
    increasing backoff avoids spurious fixture failures.
    """
    import time
    from gotrue.errors import AuthRetryableError
    last_exc = None
    for attempt in range(max_attempts):
        try:
            return fn(*args, **kwargs)
        except AuthRetryableError as exc:
            last_exc = exc
            if attempt < max_attempts - 1:
                time.sleep(10 * (attempt + 1))   # 10 s, 20 s, 30 s
    raise last_exc


async def _create_user_via_admin(email: str, password: str) -> None:
    """
    Rate-limit fallback: create Supabase Auth user + local DB rows directly
    via the admin API, bypassing the signup endpoint and email sending.
    """
    sb = _make_admin_client()
    try:
        admin_resp = _admin_call(sb.auth.admin.create_user, {
            "email": email,
            "password": password,
            "email_confirm": True,
        })
        supabase_uid = admin_resp.user.id
    except Exception as e:
        if "already been registered" not in str(e):
            raise
        # 503 from signup can mean Supabase created the user before timing out.
        # Find the existing UID and fall through to ensure local DB rows exist.
        users_page = _admin_call(sb.auth.admin.list_users)
        existing = next((u for u in users_page if u.email == email), None)
        if not existing:
            raise
        supabase_uid = existing.id
        # If local DB already has this user, nothing more to do.
        async with AsyncSessionLocal() as db:
            from sqlalchemy import select as _select
            already = (await db.execute(
                _select(User).where(User.email == email)
            )).scalar_one_or_none()
            if already:
                return
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        user = User(
            supabase_uid=supabase_uid,
            email=email,
            email_verified=True,
            status=UserStatus.active,
        )
        db.add(user)
        await db.flush()
        db.add(UserSettings(user_id=user.id))
        db.add(EncryptionKey(
            user_id=user.id,
            encrypted_cek=base64.b64decode(_SIGNUP_CEK),
            cek_iv=base64.b64decode(_SIGNUP_IV),
            pbkdf2_salt=base64.b64decode(_SIGNUP_SALT),
            pbkdf2_iterations=100000,
            delivery_encrypted_cek=base64.b64decode(_SIGNUP_DCEK),
            delivery_cek_iv=base64.b64decode(_SIGNUP_DIV),
            created_at=now,
            updated_at=now,
        ))
        db.add(CheckInSchedule(
            user_id=user.id,
            interval_days=30,
            grace_period_days=7,
            next_dispatch_at=now + timedelta(days=30),
        ))
        from app.core.audit import write_audit
        await write_audit(db, "signup", user_id=user.id, description=f"Admin-created test user: {email}")
        await db.commit()


@pytest.fixture(scope="session")
async def registered_user(http):
    email = make_test_email()
    password = TEST_PASSWORD

    res = await http.post("/auth/signup", json={
        "email": email,
        "password": password,
        "encrypted_cek": _SIGNUP_CEK,
        "cek_iv": _SIGNUP_IV,
        "pbkdf2_salt": _SIGNUP_SALT,
        "delivery_encrypted_cek": _SIGNUP_DCEK,
        "delivery_cek_iv": _SIGNUP_DIV,
    })

    if res.status_code in (429, 503):
        # Rate-limited or Supabase auth timeout: create via admin API (no email send).
        await _create_user_via_admin(email, password)
    else:
        assert res.status_code == 201, f"Signup failed: {res.text}"
        sb = _make_admin_client()
        sb_users = _admin_call(sb.auth.admin.list_users)
        sb_user = next((u for u in sb_users if u.email == email), None)
        assert sb_user, f"User {email} not found in Supabase Auth"
        _admin_call(sb.auth.admin.update_user_by_id, sb_user.id, {"email_confirm": True})
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(User).where(User.email == email))
            user = result.scalar_one()
            user.email_verified = True
            sched = await db.execute(
                select(CheckInSchedule).where(CheckInSchedule.user_id == user.id)
            )
            schedule = sched.scalar_one_or_none()
            if schedule:
                schedule.next_dispatch_at = datetime.now(timezone.utc) + timedelta(days=30)
            await db.commit()

    # Retry login with backoff — Supabase takes a moment to propagate email
    # confirmation (or admin user creation) before sign_in_with_password works.
    login_res = None
    for _attempt in range(5):
        login_res = await http.post("/auth/login", json={"email": email, "password": password})
        if login_res.status_code == 200:
            break
        if _attempt < 4:
            await asyncio.sleep(5 * (_attempt + 1))  # 5 s, 10 s, 15 s, 20 s
    assert login_res is not None and login_res.status_code == 200, (
        f"Login failed after retries: {login_res.text if login_res else 'no response'}"
    )
    data = login_res.json()

    return {
        "email": email,
        "password": password,
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
        "user_id": data.get("user_id"),
    }


@pytest.fixture(scope="session")
async def auth_client(registered_user):
    """Authenticated ASGI client."""
    transport = ASGITransport(app=app, raise_app_exceptions=True)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        follow_redirects=True,
        headers={"Authorization": f"Bearer {registered_user['access_token']}"},
    ) as client:
        yield client


# ── Shared cross-module fixtures (used by security module 10) ────────────────

@pytest.fixture(scope="session")
async def test_beneficiary(auth_client):
    """One beneficiary for the session user."""
    res = await auth_client.post("/beneficiaries/", json={
        "full_name": "Shared Test Beneficiary",
        "email": f"sharedbene_{uuid.uuid4().hex[:6]}@testlegate.dev",
        "relationship": "Friend",
        "is_emergency_contact": False,
    })
    assert res.status_code == 201
    return res.json()


@pytest.fixture(scope="session")
async def created_capsule(auth_client, test_beneficiary):
    """One capsule for the session user."""
    res = await auth_client.post("/capsules/", json={
        "title": "Shared Test Capsule",
        "beneficiary_id": test_beneficiary["id"],
        "cipher_iv": "0" * 24,
    })
    assert res.status_code == 201
    return res.json()
