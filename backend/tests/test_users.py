"""
Tests for user account management endpoints.
"""

import pytest
from httpx import AsyncClient

FAKE_TOKEN = "Bearer fake.jwt.token"


@pytest.mark.asyncio
async def test_get_me_invalid_token_returns_401(client: AsyncClient):
    """Invalid JWT returns 401."""
    response = await client.get("/users/me", headers={"Authorization": FAKE_TOKEN})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_no_auth_returns_403(client: AsyncClient):
    """Without Authorization header HTTPBearer raises 403."""
    response = await client.get("/users/me")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_delete_me_invalid_token_returns_401(client: AsyncClient):
    """Invalid JWT returns 401."""
    response = await client.delete("/users/me", headers={"Authorization": FAKE_TOKEN})
    assert response.status_code == 401
