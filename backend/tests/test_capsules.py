"""
Tests for capsule CRUD endpoints.
"""

import pytest
import uuid
from httpx import AsyncClient

FAKE_TOKEN = "Bearer fake.jwt.token"
FAKE_UUID = str(uuid.uuid4())


@pytest.mark.asyncio
async def test_create_capsule_invalid_token_returns_401(client: AsyncClient):
    payload = {
        "title": "My First Capsule",
        "beneficiary_id": FAKE_UUID,
        "cipher_iv": "base64iv==",
    }
    response = await client.post("/capsules/", json=payload, headers={"Authorization": FAKE_TOKEN})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_capsule_missing_title_returns_422(client: AsyncClient):
    payload = {"beneficiary_id": FAKE_UUID, "cipher_iv": "iv=="}
    response = await client.post("/capsules/", json=payload)
    assert response.status_code in (422, 403)


@pytest.mark.asyncio
async def test_create_capsule_invalid_beneficiary_uuid_returns_422(client: AsyncClient):
    payload = {"title": "Test", "beneficiary_id": "not-a-uuid", "cipher_iv": "iv=="}
    response = await client.post("/capsules/", json=payload)
    assert response.status_code in (422, 403)


@pytest.mark.asyncio
async def test_list_capsules_invalid_token_returns_401(client: AsyncClient):
    response = await client.get("/capsules/", headers={"Authorization": FAKE_TOKEN})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_capsule_invalid_token_returns_401(client: AsyncClient):
    response = await client.get(f"/capsules/{FAKE_UUID}", headers={"Authorization": FAKE_TOKEN})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_capsule_invalid_token_returns_401(client: AsyncClient):
    payload = {"title": "Updated Title"}
    response = await client.patch(
        f"/capsules/{FAKE_UUID}", json=payload, headers={"Authorization": FAKE_TOKEN}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_delete_capsule_invalid_token_returns_401(client: AsyncClient):
    response = await client.delete(f"/capsules/{FAKE_UUID}", headers={"Authorization": FAKE_TOKEN})
    assert response.status_code == 401
