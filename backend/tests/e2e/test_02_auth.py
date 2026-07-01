"""Full authentication lifecycle: signup, verify, login, refresh, logout."""
import pytest
import uuid
from httpx import AsyncClient

TEST_PASSWORD = "TestPassword123!"


def fresh_email():
    # Must be a deliverable mailbox — Supabase validates the domain at sign_up.
    from tests.e2e.conftest import make_test_email
    return make_test_email()


BASE_SIGNUP = {
    "password": TEST_PASSWORD,
    "encrypted_cek": "dGVzdGNlaw==",
    "cek_iv": "dGVzdGl2AA==",
    "pbkdf2_salt": "dGVzdHNhbHQ=",
    "delivery_encrypted_cek": "dGVzdGRlbGl2ZXJ5Y2VrAA==",
    "delivery_cek_iv": "dGVzdGRlbGl2ZXJ5aXY=",
}

# ── Signup ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_signup_creates_user(http: AsyncClient):
    res = await http.post("/auth/signup", json={**BASE_SIGNUP, "email": fresh_email()})
    if res.status_code in (429, 503):
        pytest.skip("Supabase rate limit / unavailable — re-run after cooldown")
    assert res.status_code == 201
    body = res.json()
    assert "access_token" not in body


@pytest.mark.asyncio
async def test_signup_duplicate_email_returns_409(http: AsyncClient):
    email = fresh_email()
    first = await http.post("/auth/signup", json={**BASE_SIGNUP, "email": email})
    if first.status_code in (429, 503):
        pytest.skip("Supabase rate limit / unavailable — re-run after cooldown")
    assert first.status_code == 201
    res2 = await http.post("/auth/signup", json={**BASE_SIGNUP, "email": email})
    assert res2.status_code == 409


@pytest.mark.asyncio
async def test_signup_invalid_email_returns_422(http: AsyncClient):
    res = await http.post("/auth/signup", json={**BASE_SIGNUP, "email": "not-an-email"})
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_signup_weak_password_returns_422(http: AsyncClient):
    res = await http.post("/auth/signup", json={**BASE_SIGNUP, "email": fresh_email(), "password": "weak"})
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_signup_creates_db_rows(http: AsyncClient):
    from app.db.session import AsyncSessionLocal
    from app.db.models.user import User, UserSettings, EncryptionKey
    from sqlalchemy import select
    email = fresh_email()
    res = await http.post("/auth/signup", json={**BASE_SIGNUP, "email": email})
    if res.status_code in (429, 503):
        pytest.skip("Supabase rate limit / unavailable — re-run after cooldown")
    assert res.status_code == 201
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        assert user is not None
        assert user.email_verified is False

        settings = await db.execute(select(UserSettings).where(UserSettings.user_id == user.id))
        assert settings.scalar_one_or_none() is not None

        enc_key = await db.execute(select(EncryptionKey).where(EncryptionKey.user_id == user.id))
        assert enc_key.scalar_one_or_none() is not None


# ── Login ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_login_with_valid_credentials(registered_user, http: AsyncClient):
    import asyncio
    res = None
    for _attempt in range(4):
        res = await http.post("/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        })
        if res.status_code == 200:
            break
        if res.status_code in (429, 503):
            pytest.skip("Supabase rate limit — re-run after cooldown")
        if _attempt < 3:
            await asyncio.sleep(5 * (_attempt + 1))
    assert res is not None and res.status_code == 200, f"Login failed: {res.text}"
    body = res.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password_returns_401(registered_user, http: AsyncClient):
    res = await http.post("/auth/login", json={
        "email": registered_user["email"],
        "password": "WrongPassword999!",
    })
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_email_returns_401(http: AsyncClient):
    res = await http.post("/auth/login", json={
        "email": "nobody@testlegate.dev",
        "password": TEST_PASSWORD,
    })
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_login_updates_last_login_at(registered_user, http: AsyncClient):
    from app.db.session import AsyncSessionLocal
    from app.db.models.user import User
    from sqlalchemy import select
    await http.post("/auth/login", json={
        "email": registered_user["email"],
        "password": registered_user["password"],
    })
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == registered_user["email"]))
        user = result.scalar_one()
        assert user.last_login_at is not None


# ── Token & Protected Routes ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_me_with_valid_token(auth_client: AsyncClient, registered_user):
    res = await auth_client.get("/auth/me")
    assert res.status_code == 200
    body = res.json()
    assert body["email"] == registered_user["email"]
    assert body["email_verified"] is True


@pytest.mark.asyncio
async def test_get_me_without_token_returns_403(http: AsyncClient):
    res = await http.get("/auth/me")
    assert res.status_code in (401, 403)


@pytest.mark.asyncio
async def test_get_me_with_invalid_token_returns_401(http: AsyncClient):
    res = await http.get("/auth/me", headers={"Authorization": "Bearer fake.invalid.token"})
    assert res.status_code == 401


# ── Encryption Key ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_encryption_key(auth_client: AsyncClient):
    res = await auth_client.get("/auth/me/encryption-key")
    assert res.status_code == 200
    body = res.json()
    assert "encrypted_cek" in body
    assert "cek_iv" in body
    assert "pbkdf2_salt" in body
    assert "pbkdf2_iterations" in body
    assert body["pbkdf2_iterations"] == 100000


@pytest.mark.asyncio
async def test_get_delivery_wrapping_key(auth_client: AsyncClient):
    # S2 (Phase 5): endpoint changed from GET to POST to prevent caching and
    # browser history exposure.  GET must now return 405 Method Not Allowed.
    res_get = await auth_client.get("/auth/me/delivery-wrapping-key")
    assert res_get.status_code == 405, (
        f"S2: GET on delivery-wrapping-key should return 405, got {res_get.status_code}"
    )

    res = await auth_client.post("/auth/me/delivery-wrapping-key")
    assert res.status_code == 200
    body = res.json()
    assert "wrapping_key" in body
    assert len(body["wrapping_key"]) == 64
    assert all(c in "0123456789abcdef" for c in body["wrapping_key"])


# ── Token Refresh ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_token_refresh(registered_user, http: AsyncClient):
    res = await http.post("/auth/refresh", json={"refresh_token": registered_user["refresh_token"]})
    assert res.status_code == 200
    body = res.json()
    assert "access_token" in body


@pytest.mark.asyncio
async def test_token_refresh_with_invalid_token_returns_401(http: AsyncClient):
    res = await http.post("/auth/refresh", json={"refresh_token": "fake.refresh.token"})
    assert res.status_code == 401


# ── Logout ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_logout_succeeds(registered_user, http: AsyncClient):
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
    tokens = login.json()
    res = await http.post(
        "/auth/logout",
        json={"refresh_token": tokens["refresh_token"]},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert res.status_code == 200


# ── Audit Log ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_login_creates_audit_log_entry(registered_user, http: AsyncClient):
    from app.db.session import AsyncSessionLocal
    from app.db.models.audit import AuditLog
    from sqlalchemy import select, desc
    await http.post("/auth/login", json={
        "email": registered_user["email"],
        "password": registered_user["password"],
    })
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(AuditLog)
            .where(AuditLog.event_type == "login")
            .order_by(desc(AuditLog.created_at))
            .limit(1)
        )
        log = result.scalar_one_or_none()
        assert log is not None
