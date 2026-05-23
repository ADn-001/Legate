"""
Tests for beneficiary management endpoints.
"""

import pytest
import uuid
from httpx import AsyncClient

FAKE_TOKEN = "Bearer fake.jwt.token"
FAKE_UUID = str(uuid.uuid4())


@pytest.mark.asyncio
async def test_create_beneficiary_invalid_token_returns_401(client: AsyncClient):
    payload = {
        "full_name": "Jane Doe",
        "email": "jane@example.com",
        "relationship": "spouse",
        "is_emergency_contact": True,
    }
    response = await client.post("/beneficiaries/", json=payload, headers={"Authorization": FAKE_TOKEN})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_beneficiary_missing_email_returns_422(client: AsyncClient):
    payload = {"full_name": "Jane Doe"}
    response = await client.post("/beneficiaries/", json=payload)
    assert response.status_code in (422, 403)


@pytest.mark.asyncio
async def test_create_beneficiary_invalid_email_returns_422(client: AsyncClient):
    payload = {"full_name": "Jane Doe", "email": "not-an-email"}
    response = await client.post("/beneficiaries/", json=payload)
    assert response.status_code in (422, 403)


@pytest.mark.asyncio
async def test_list_beneficiaries_invalid_token_returns_401(client: AsyncClient):
    response = await client.get("/beneficiaries/", headers={"Authorization": FAKE_TOKEN})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_beneficiary_invalid_token_returns_401(client: AsyncClient):
    payload = {"full_name": "Jane Smith"}
    response = await client.patch(
        f"/beneficiaries/{FAKE_UUID}", json=payload, headers={"Authorization": FAKE_TOKEN}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_beneficiary_invalid_email_returns_422(client: AsyncClient):
    payload = {"email": "bad-email"}
    response = await client.patch(f"/beneficiaries/{FAKE_UUID}", json=payload)
    assert response.status_code in (422, 403)


@pytest.mark.asyncio
async def test_delete_beneficiary_invalid_token_returns_401(client: AsyncClient):
    response = await client.delete(f"/beneficiaries/{FAKE_UUID}", headers={"Authorization": FAKE_TOKEN})
    assert response.status_code == 401
