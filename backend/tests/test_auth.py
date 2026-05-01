"""Tests for authentication endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_signup_returns_201(client: AsyncClient):
    # TODO: implement once AuthService.signup is complete
    pass


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient):
    # TODO: implement
    pass
