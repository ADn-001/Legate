"""
Tests for capsule CRUD endpoints.
All routes currently raise NotImplementedError → expect HTTP 500.
The authenticated routes chain through get_current_user which also raises
NotImplementedError, so any request with a Bearer token returns 500.
"""

import pytest
import uuid
from httpx import AsyncClient


FAKE_TOKEN = "Bearer fake.jwt.token"
FAKE_UUID = str(uuid.uuid4())


# ---------------------------------------------------------------------------
# POST /capsules — STUB
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_capsule_stub_returns_500(client: AsyncClient):
    payload = {
        "title": "My First Capsule",
        "beneficiary_id": FAKE_UUID,
        "cipher_iv": "base64iv==",
    }
    response = await client.post("/capsules/", json=payload, headers={"Authorization": FAKE_TOKEN})
    assert response.status_code == 500


@pytest.mark.asyncio
async def test_create_capsule_missing_title_returns_4xx(client: AsyncClient):
    """With auth stub active, body validation errors result in 500 (auth dep fires first)."""
    payload = {"beneficiary_id": FAKE_UUID, "cipher_iv": "iv=="}
    response = await client.post("/capsules/", json=payload, headers={"Authorization": FAKE_TOKEN})
    assert response.status_code in (422, 500)


@pytest.mark.asyncio
async def test_create_capsule_invalid_beneficiary_uuid_returns_4xx(client: AsyncClient):
    """With auth stub active, invalid UUID body results in 500 (auth dep fires first)."""
    payload = {"title": "Test", "beneficiary_id": "not-a-uuid", "cipher_iv": "iv=="}
    response = await client.post("/capsules/", json=payload, headers={"Authorization": FAKE_TOKEN})
    assert response.status_code in (422, 500)


# ---------------------------------------------------------------------------
# GET /capsules — STUB
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_capsules_stub_returns_500(client: AsyncClient):
    response = await client.get("/capsules/", headers={"Authorization": FAKE_TOKEN})
    assert response.status_code == 500


# ---------------------------------------------------------------------------
# GET /capsules/{id} — STUB
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_capsule_stub_returns_500(client: AsyncClient):
    response = await client.get(f"/capsules/{FAKE_UUID}", headers={"Authorization": FAKE_TOKEN})
    assert response.status_code == 500


# ---------------------------------------------------------------------------
# PATCH /capsules/{id} — STUB
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_capsule_stub_returns_500(client: AsyncClient):
    payload = {"title": "Updated Title"}
    response = await client.patch(
        f"/capsules/{FAKE_UUID}", json=payload, headers={"Authorization": FAKE_TOKEN}
    )
    assert response.status_code == 500


# ---------------------------------------------------------------------------
# DELETE /capsules/{id} — STUB
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_capsule_stub_returns_500(client: AsyncClient):
    response = await client.delete(f"/capsules/{FAKE_UUID}", headers={"Authorization": FAKE_TOKEN})
    assert response.status_code == 500
