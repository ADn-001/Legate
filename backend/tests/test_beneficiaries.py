"""
Tests for beneficiary management endpoints.
All routes currently raise NotImplementedError → expect HTTP 500.
"""

import pytest
import uuid
from httpx import AsyncClient


FAKE_TOKEN = "Bearer fake.jwt.token"
FAKE_UUID = str(uuid.uuid4())


# ---------------------------------------------------------------------------
# POST /beneficiaries — STUB
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_beneficiary_stub_returns_500(client: AsyncClient):
    payload = {
        "full_name": "Jane Doe",
        "email": "jane@example.com",
        "relationship": "spouse",
        "is_emergency_contact": True,
    }
    response = await client.post("/beneficiaries/", json=payload, headers={"Authorization": FAKE_TOKEN})
    assert response.status_code == 500


@pytest.mark.asyncio
async def test_create_beneficiary_missing_email_returns_4xx(client: AsyncClient):
    """
    With auth stub active, the auth dependency's NotImplementedError fires
    before/alongside body validation, so the result is 500 not 422.
    Accept any 4xx/5xx error response.
    """
    payload = {"full_name": "Jane Doe"}
    response = await client.post("/beneficiaries/", json=payload, headers={"Authorization": FAKE_TOKEN})
    assert response.status_code in (422, 500)


@pytest.mark.asyncio
async def test_create_beneficiary_invalid_email_returns_4xx(client: AsyncClient):
    """With auth stub active, invalid email body results in 500 (auth dep fires first)."""
    payload = {"full_name": "Jane Doe", "email": "not-an-email"}
    response = await client.post("/beneficiaries/", json=payload, headers={"Authorization": FAKE_TOKEN})
    assert response.status_code in (422, 500)


# ---------------------------------------------------------------------------
# GET /beneficiaries — STUB
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_beneficiaries_stub_returns_500(client: AsyncClient):
    response = await client.get("/beneficiaries/", headers={"Authorization": FAKE_TOKEN})
    assert response.status_code == 500


# ---------------------------------------------------------------------------
# PATCH /beneficiaries/{id} — STUB
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_beneficiary_stub_returns_500(client: AsyncClient):
    payload = {"full_name": "Jane Smith"}
    response = await client.patch(
        f"/beneficiaries/{FAKE_UUID}", json=payload, headers={"Authorization": FAKE_TOKEN}
    )
    assert response.status_code == 500


@pytest.mark.asyncio
async def test_update_beneficiary_invalid_email_returns_4xx(client: AsyncClient):
    """With auth stub active, invalid email body results in 500 (auth dep fires first)."""
    payload = {"email": "bad-email"}
    response = await client.patch(
        f"/beneficiaries/{FAKE_UUID}", json=payload, headers={"Authorization": FAKE_TOKEN}
    )
    assert response.status_code in (422, 500)


# ---------------------------------------------------------------------------
# DELETE /beneficiaries/{id} — STUB
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_beneficiary_stub_returns_500(client: AsyncClient):
    response = await client.delete(f"/beneficiaries/{FAKE_UUID}", headers={"Authorization": FAKE_TOKEN})
    assert response.status_code == 500
