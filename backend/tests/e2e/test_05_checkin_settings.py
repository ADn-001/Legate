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
async def test_update_interval_out_of_bounds_returns_422(auth_client: AsyncClient):
    """B4/FR-11 (Phase B): floor lowered from 7 to 1 day; ceiling still 365."""
    res = await auth_client.patch("/settings/checkin", json={"interval_days": 0})
    assert res.status_code == 422
    res = await auth_client.patch("/settings/checkin", json={"interval_days": 400})
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_update_interval_at_new_floor_accepted(auth_client: AsyncClient):
    """B4/FR-11 (Phase B): 1 day is now valid (used to require >= 7)."""
    res = await auth_client.patch("/settings/checkin", json={"interval_days": 1})
    assert res.status_code == 200
    assert res.json()["interval_days"] == 1
    # restore a normal-mode default so later tests in this module aren't affected
    res = await auth_client.patch("/settings/checkin", json={"interval_days": 30})
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_update_grace_invalid_value_returns_422(auth_client: AsyncClient):
    """B4/FR-12 (Phase B): grace period now accepts any int 1-30, not just 3/7/14/30."""
    res = await auth_client.patch("/settings/checkin", json={"grace_period_days": 0})
    assert res.status_code == 422
    res = await auth_client.patch("/settings/checkin", json={"grace_period_days": 31})
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_update_grace_non_preset_value_accepted(auth_client: AsyncClient):
    """B4/FR-12 (Phase B): 5 is not one of the old 3/7/14/30 presets but is now valid."""
    res = await auth_client.patch("/settings/checkin", json={"grace_period_days": 5})
    assert res.status_code == 200
    assert res.json()["grace_period_days"] == 5
    # restore a normal-mode default so later tests in this module aren't affected
    res = await auth_client.patch("/settings/checkin", json={"grace_period_days": 7})
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_storage_usage_endpoint(auth_client: AsyncClient):
    res = await auth_client.get("/settings/storage")
    assert res.status_code == 200
    body = res.json()
    assert "total_bytes" in body
    assert "by_capsule" in body
    assert isinstance(body["by_capsule"], list)
    # B16 / FR-36: quota for the progress bar.
    assert "limit_bytes" in body
    assert body["limit_bytes"] > 0
