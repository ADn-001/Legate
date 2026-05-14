"""
Tests for authentication endpoints.
All routes currently raise NotImplementedError → expect HTTP 500.
"""

import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Health check (originally in this file)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# POST /auth/signup — STUB (NotImplementedError)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_signup_stub_returns_500(client: AsyncClient):
    """signup is not implemented yet — expect 500 Internal Server Error."""
    payload = {
        "email": "test@example.com",
        "password": "StrongPassword123!",
        "encrypted_cek": "base64encodedcek==",
        "cek_iv": "base64encodediv==",
        "pbkdf2_salt": "base64encodedsalt==",
    }
    response = await client.post("/auth/signup", json=payload)
    assert response.status_code == 500


@pytest.mark.asyncio
async def test_signup_missing_required_fields_returns_422(client: AsyncClient):
    """Missing required fields should be caught by Pydantic before hitting the stub."""
    response = await client.post("/auth/signup", json={"email": "test@example.com"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_signup_invalid_email_returns_422(client: AsyncClient):
    """Invalid email format should be rejected at schema validation."""
    payload = {
        "email": "not-an-email",
        "password": "password",
        "encrypted_cek": "abc",
        "cek_iv": "abc",
        "pbkdf2_salt": "abc",
    }
    response = await client.post("/auth/signup", json=payload)
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST /auth/login — STUB (NotImplementedError)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_stub_returns_500(client: AsyncClient):
    """login is not implemented yet — expect 500."""
    payload = {"email": "test@example.com", "password": "anypassword"}
    response = await client.post("/auth/login", json=payload)
    assert response.status_code == 500


@pytest.mark.asyncio
async def test_login_missing_password_returns_422(client: AsyncClient):
    response = await client.post("/auth/login", json={"email": "test@example.com"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_invalid_email_returns_422(client: AsyncClient):
    payload = {"email": "not-an-email", "password": "password"}
    response = await client.post("/auth/login", json=payload)
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST /auth/verify-email — STUB (NotImplementedError)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_verify_email_stub_returns_500(client: AsyncClient):
    """verify-email is not implemented yet — expect 500."""
    payload = {"email": "test@example.com", "otp": "123456"}
    response = await client.post("/auth/verify-email", json=payload)
    assert response.status_code == 500


@pytest.mark.asyncio
async def test_verify_email_missing_otp_returns_422(client: AsyncClient):
    response = await client.post("/auth/verify-email", json={"email": "test@example.com"})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST /auth/refresh — STUB (NotImplementedError)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_refresh_stub_returns_500(client: AsyncClient):
    """refresh is not implemented yet — expect 500."""
    response = await client.post("/auth/refresh", json={"refresh_token": "fake.token.value"})
    assert response.status_code == 500


@pytest.mark.asyncio
async def test_refresh_missing_token_returns_422(client: AsyncClient):
    response = await client.post("/auth/refresh", json={})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST /auth/logout — STUB (NotImplementedError)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_logout_stub_returns_500(client: AsyncClient):
    """logout is not implemented yet — expect 500."""
    response = await client.post("/auth/logout", json={"refresh_token": "fake.token.value"})
    assert response.status_code == 500


# ---------------------------------------------------------------------------
# GET /auth/me/encryption-key — STUB (NotImplementedError)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_encryption_key_stub_returns_500(client: AsyncClient):
    """encryption-key endpoint is not implemented yet — expect 500."""
    response = await client.get("/auth/me/encryption-key")
    assert response.status_code == 500
