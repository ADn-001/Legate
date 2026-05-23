"""
Tests for authentication endpoints.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# POST /auth/signup — schema validation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_signup_missing_required_fields_returns_422(client: AsyncClient):
    response = await client.post("/auth/signup", json={"email": "test@example.com"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_signup_invalid_email_returns_422(client: AsyncClient):
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
# POST /auth/login — schema validation
# ---------------------------------------------------------------------------

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
# POST /auth/verify-email — schema validation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_verify_email_missing_otp_returns_422(client: AsyncClient):
    response = await client.post("/auth/verify-email", json={"email": "test@example.com"})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST /auth/refresh — schema validation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_refresh_missing_token_returns_422(client: AsyncClient):
    response = await client.post("/auth/refresh", json={})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /auth/me/encryption-key — requires auth (no token → 403)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_encryption_key_no_auth_returns_403(client: AsyncClient):
    response = await client.get("/auth/me/encryption-key")
    assert response.status_code == 403
