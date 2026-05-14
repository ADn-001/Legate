"""
Tests for check-in token redemption endpoints.
All routes currently raise NotImplementedError → expect HTTP 500.
These routes are intentionally unauthenticated (accessed from email links).
"""

import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# GET /checkin/confirm — STUB
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_confirm_checkin_stub_returns_500(client: AsyncClient):
    response = await client.get("/checkin/confirm", params={"token": "fake-token-abc123"})
    assert response.status_code == 500


@pytest.mark.asyncio
async def test_confirm_checkin_missing_token_returns_422(client: AsyncClient):
    response = await client.get("/checkin/confirm")
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /checkin/snooze — STUB
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_snooze_checkin_stub_returns_500(client: AsyncClient):
    response = await client.get("/checkin/snooze", params={"token": "fake-token-abc123", "days": 7})
    assert response.status_code == 500


@pytest.mark.asyncio
async def test_snooze_checkin_missing_days_returns_422(client: AsyncClient):
    response = await client.get("/checkin/snooze", params={"token": "fake-token"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_snooze_checkin_missing_token_returns_422(client: AsyncClient):
    response = await client.get("/checkin/snooze", params={"days": 7})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /checkin/emergency/pause — STUB
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_emergency_pause_stub_returns_500(client: AsyncClient):
    response = await client.get("/checkin/emergency/pause", params={"token": "fake-emergency-token"})
    assert response.status_code == 500


@pytest.mark.asyncio
async def test_emergency_pause_missing_token_returns_422(client: AsyncClient):
    response = await client.get("/checkin/emergency/pause")
    assert response.status_code == 422
