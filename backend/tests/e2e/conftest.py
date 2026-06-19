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

# ── Session-scoped NullPool engine to avoid asyncpg "event loop closed" errors ─

_cfg = get_settings()
_test_engine = create_async_engine(
    _cfg.database_url.replace("postgresql://", "postgresql+asyncpg://"),
    poolclass=NullPool,
    echo=False,
)
AsyncSessionLocal = async_sessionmaker(_test_engine, expire_on_commit=False, class_=AsyncSession)


# ── Patch app.db.session for worker-task code paths ──────────────────────────
# Worker task functions (checkin_tasks/delivery_tasks/cleanup_tasks) do
# `from app.db.session import AsyncSessionLocal` and use the module-level
# `engine`, which is built once at import time with the default pooled
# AsyncAdaptedQueuePool + pool_pre_ping. asyncpg connections are bound to the
# event loop active when they're created; pytest-asyncio gives each test
# function its own loop, so a pooled connection created under one test's loop
# raises "Future attached to a different loop" (and isn't recoverable via
# pre_ping, since that RuntimeError isn't classified as a disconnect) when
# reused under another test's loop. Point worker-task code at this session's
# NullPool engine too — NullPool opens/closes a fresh connection per checkout,
# so there is never a cross-loop reuse.
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
    loop.close()


# ── Override app DB session to use NullPool engine ───────────────────────────

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


async def _create_user_via_admin(email: str, password: str) -> None:
    """
    Rate-limit fallback: create Supabase Auth user + local DB rows directly
    via the admin API, bypassing the signup endpoint and email sending.
    """
    sb = _make_admin_client()
    admin_resp = sb.auth.admin.create_user({
        "email": email,
        "password": password,
        "email_confirm": True,
    })
    supabase_uid = admin_resp.user.id
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

    if res.status_code == 429:
        # Email rate-limited: create user directly via Supabase admin API
        await _create_user_via_admin(email, password)
    else:
        assert res.status_code == 201, f"Signup failed: {res.text}"
        sb = _make_admin_client()
        sb_users = sb.auth.admin.list_users()
        sb_user = next((u for u in sb_users if u.email == email), None)
        assert sb_user, f"User {email} not found in Supabase Auth"
        sb.auth.admin.update_user_by_id(sb_user.id, {"email_confirm": True})
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

    login_res = await http.post("/auth/login", json={"email": email, "password": password})
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
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
