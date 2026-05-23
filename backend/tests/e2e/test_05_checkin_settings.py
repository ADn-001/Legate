"""Check-in schedule CRUD and validation."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_checkin_settings(auth_client: AsyncClient):
    res = await auth_client.get("/settings/checkin")
    assert res.status_code == 200
    body = res.json()
    assert "interval_days" in body
    assert "grace_period_days" in body
    assert "snooze_count" in body
    assert "snooze_limit" in body
    assert body["snooze_limit"] == 2


@pytest.mark.asyncio
async def test_update_checkin_interval(auth_client: AsyncClient):
    res = await auth_client.patch("/settings/checkin", json={"interval_days": 14})
    assert res.status_code == 200
    assert res.json()["interval_days"] == 14


@pytest.mark.asyncio
async def test_update_grace_period(auth_client: AsyncClient):
    res = await auth_client.patch("/settings/checkin", json={"grace_period_days": 3})
    assert res.status_code == 200
    assert res.json()["grace_period_days"] == 3


@pytest.mark.asyncio
async def test_checkin_settings_requires_auth(http: AsyncClient):
    res = await http.get("/settings/checkin")
    assert res.status_code in (401, 403)


@pytest.mark.asyncio
async def test_storage_usage_endpoint(auth_client: AsyncClient):
    res = await auth_client.get("/settings/storage")
    assert res.status_code == 200
    body = res.json()
    assert "total_bytes" in body
    assert "by_capsule" in body
    assert isinstance(body["by_capsule"], list)
