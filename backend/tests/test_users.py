"""
Tests for user account management endpoints.
All routes currently raise NotImplementedError → expect HTTP 500.
The /users/me routes depend on get_current_user which also raises NotImplementedError,
so any authenticated request that hits the dependency chain returns 500.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_me_stub_returns_500(client: AsyncClient):
    """GET /users/me depends on get_current_user (NotImplementedError) — expect 500."""
    response = await client.get("/users/me", headers={"Authorization": "Bearer fake.jwt.token"})
    assert response.status_code == 500


@pytest.mark.asyncio
async def test_get_me_no_auth_returns_403_or_500(client: AsyncClient):
    """Without Authorization header HTTPBearer raises 403."""
    response = await client.get("/users/me")
    assert response.status_code in (403, 422, 500)


@pytest.mark.asyncio
async def test_delete_me_stub_returns_500(client: AsyncClient):
    """DELETE /users/me depends on get_current_user (NotImplementedError) — expect 500."""
    response = await client.delete("/users/me", headers={"Authorization": "Bearer fake.jwt.token"})
    assert response.status_code == 500
