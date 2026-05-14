"""Tests for the health check endpoint."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check_returns_200(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_check_returns_ok_json(client: AsyncClient):
    response = await client.get("/health")
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_health_check_content_type(client: AsyncClient):
    response = await client.get("/health")
    assert "application/json" in response.headers["content-type"]
