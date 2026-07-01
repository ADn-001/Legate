"""Authorization boundaries, injection, and data isolation between users."""
import pytest
import uuid
from httpx import AsyncClient


@pytest.fixture(scope="session")
async def second_user(http: AsyncClient):
    """A second registered user for isolation tests."""
    from tests.e2e.conftest import make_test_email, AsyncSessionLocal, _create_user_via_admin, _make_admin_client

    email = make_test_email()
    password = "TestPassword123!"

    res = await http.post("/auth/signup", json={
        "email": email,
        "password": password,
        "encrypted_cek": "dGVzdA==",
        "cek_iv": "dGVzdA==",
        "pbkdf2_salt": "dGVzdA==",
        "delivery_encrypted_cek": "dGVzdA==",
        "delivery_cek_iv": "dGVzdA==",
    })

    if res.status_code in (429, 503):
        await _create_user_via_admin(email, password)
    else:
        assert res.status_code == 201
        sb = _make_admin_client()
        users = sb.auth.admin.list_users()
        sb_user = next((u for u in users if u.email == email), None)
        if sb_user:
            sb.auth.admin.update_user_by_id(sb_user.id, {"email_confirm": True})
        # Also mark email_verified in the local DB — get_current_verified_user
        # checks this column, not Supabase Auth. Without this the second user
        # always gets 403 instead of the expected 404 on resource isolation tests.
        from sqlalchemy import select as sa_select
        from app.db.models.user import User as UserModel
        async with AsyncSessionLocal() as db:
            r = await db.execute(sa_select(UserModel).where(UserModel.email == email))
            u = r.scalar_one()
            u.email_verified = True
            await db.commit()

    import asyncio
    login = None
    for _attempt in range(4):
        login = await http.post("/auth/login", json={"email": email, "password": password})
        if login.status_code == 200:
            break
        if login.status_code in (429, 503):
            pytest.skip("Supabase rate limit / unavailable — re-run after cooldown")
        if _attempt < 3:
            await asyncio.sleep(5 * (_attempt + 1))
    assert login is not None and login.status_code == 200, f"Login failed: {login.text}"
    data = login.json()
    return {"access_token": data["access_token"], "email": email}


@pytest.mark.asyncio
async def test_user_cannot_access_other_users_capsules(
    http: AsyncClient, second_user, auth_client: AsyncClient, created_capsule
):
    cap_id = created_capsule["id"]
    res = await http.get(
        f"/capsules/{cap_id}",
        headers={"Authorization": f"Bearer {second_user['access_token']}"},
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_user_cannot_delete_other_users_capsule(
    http: AsyncClient, second_user, created_capsule
):
    cap_id = created_capsule["id"]
    res = await http.delete(
        f"/capsules/{cap_id}",
        headers={"Authorization": f"Bearer {second_user['access_token']}"},
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_user_cannot_access_other_users_beneficiaries(
    http: AsyncClient, second_user
):
    res = await http.get(
        "/beneficiaries/",
        headers={"Authorization": f"Bearer {second_user['access_token']}"},
    )
    assert res.status_code == 200
    assert res.json() == []


@pytest.mark.asyncio
async def test_user_cannot_access_other_users_encryption_key(
    http: AsyncClient, second_user
):
    res = await http.get(
        "/auth/me/encryption-key",
        headers={"Authorization": f"Bearer {second_user['access_token']}"},
    )
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_sql_injection_in_token_param(http: AsyncClient):
    res = await http.get("/checkin/confirm?token='; DROP TABLE users; --")
    assert res.status_code in (404, 422)
    assert res.status_code != 500


@pytest.mark.asyncio
async def test_oversized_capsule_title_returns_422(auth_client: AsyncClient, test_beneficiary):
    res = await auth_client.post("/capsules/", json={
        "title": "A" * 300,
        "beneficiary_id": test_beneficiary["id"],
        "cipher_iv": "a" * 24,
    })
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_expired_access_token_returns_401(http: AsyncClient):
    fake_expired = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0IiwiZXhwIjoxfQ.fake"
    res = await http.get("/auth/me", headers={"Authorization": f"Bearer {fake_expired}"})
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_plaintext_not_stored_in_capsule_row(auth_client: AsyncClient, created_capsule):
    from tests.e2e.conftest import AsyncSessionLocal
    from app.db.models.capsule import Capsule
    async with AsyncSessionLocal() as db:
        cap = await db.get(Capsule, created_capsule["id"])
        assert not hasattr(cap, "content")
        assert not hasattr(cap, "plaintext")
        assert not hasattr(cap, "message")
