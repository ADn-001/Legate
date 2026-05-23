"""
Tests for check-in token redemption endpoints.
These routes are unauthenticated (accessed from email links).
With a fake/missing token, the service raises 404 which is caught
and returned as an HTML error page (200 with error content, or 404).
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_confirm_checkin_unknown_token_returns_html(client: AsyncClient):
    """Unknown token → 404 from service, caught → HTML error page returned as 200 or 4xx."""
    response = await client.get("/checkin/confirm", params={"token": "fake-token-abc123"})
    # Route catches the exception and returns HTML — status 404 from service
    assert response.status_code in (200, 400, 404)
    assert "text/html" in response.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_confirm_checkin_missing_token_returns_422(client: AsyncClient):
    response = await client.get("/checkin/confirm")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_snooze_checkin_unknown_token_returns_html(client: AsyncClient):
    response = await client.get("/checkin/snooze", params={"token": "fake-token-abc123", "days": 7})
    assert response.status_code in (200, 400, 404)
    assert "text/html" in response.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_snooze_checkin_missing_days_returns_422(client: AsyncClient):
    response = await client.get("/checkin/snooze", params={"token": "fake-token"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_snooze_checkin_missing_token_returns_422(client: AsyncClient):
    response = await client.get("/checkin/snooze", params={"days": 7})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_emergency_pause_unknown_token_returns_html(client: AsyncClient):
    response = await client.get("/checkin/emergency/pause", params={"token": "fake-emergency-token"})
    assert response.status_code in (200, 400, 404)
    assert "text/html" in response.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_emergency_pause_missing_token_returns_422(client: AsyncClient):
    response = await client.get("/checkin/emergency/pause")
    assert response.status_code == 422
