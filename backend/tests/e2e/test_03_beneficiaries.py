"""Beneficiary CRUD, nomination email, emergency contact."""
import pytest
import uuid
from httpx import AsyncClient

VALID_BENEFICIARY = {
    "full_name": "Jane Doe",
    "relationship": "Spouse",
    "is_emergency_contact": False,
}


@pytest.fixture(scope="module")
async def created_beneficiary(auth_client: AsyncClient):
    """Beneficiary created once per module for CRUD tests."""
    res = await auth_client.post("/beneficiaries/", json={
        **VALID_BENEFICIARY,
        "email": f"jane_{uuid.uuid4().hex[:6]}@testlegate.dev",
    })
    assert res.status_code == 201, f"created_beneficiary fixture failed: {res.text}"
    return res.json()

# ── Create ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_beneficiary_returns_201(auth_client: AsyncClient):
    res = await auth_client.post("/beneficiaries/", json={
        **VALID_BENEFICIARY,
        "email": f"bene201_{uuid.uuid4().hex[:6]}@testlegate.dev",
    })
    assert res.status_code == 201
    body = res.json()
    assert body["full_name"] == VALID_BENEFICIARY["full_name"]
    assert "id" in body
    assert body["status"] == "pending"


@pytest.mark.asyncio
async def test_create_beneficiary_duplicate_email_returns_409(auth_client: AsyncClient, created_beneficiary):
    res = await auth_client.post("/beneficiaries/", json={
        **VALID_BENEFICIARY,
        "email": created_beneficiary["email"],
    })
    assert res.status_code == 409


@pytest.mark.asyncio
async def test_create_beneficiary_invalid_email_returns_422(auth_client: AsyncClient):
    res = await auth_client.post("/beneficiaries/", json={**VALID_BENEFICIARY, "email": "not-valid"})
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_create_beneficiary_missing_name_returns_422(auth_client: AsyncClient):
    res = await auth_client.post("/beneficiaries/", json={
        "email": "valid@testlegate.dev",
        "relationship": "Friend",
        "is_emergency_contact": False,
    })
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_create_beneficiary_inserts_db_row(auth_client: AsyncClient):
    from app.db.session import AsyncSessionLocal
    from app.db.models.beneficiary import Beneficiary
    from sqlalchemy import select
    email = f"dbcheck_{uuid.uuid4().hex[:6]}@testlegate.dev"
    await auth_client.post("/beneficiaries/", json={**VALID_BENEFICIARY, "email": email})
    from tests.e2e.conftest import AsyncSessionLocal as TestSession
    async with TestSession() as db:
        result = await db.execute(select(Beneficiary).where(Beneficiary.email == email))
        row = result.scalar_one_or_none()
        assert row is not None
        assert row.invited_at is not None


# ── List ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_beneficiaries_returns_array(auth_client: AsyncClient, created_beneficiary):
    res = await auth_client.get("/beneficiaries/")
    assert res.status_code == 200
    body = res.json()
    assert isinstance(body, list)
    assert any(b["id"] == created_beneficiary["id"] for b in body)


@pytest.mark.asyncio
async def test_list_beneficiaries_requires_auth(http: AsyncClient):
    res = await http.get("/beneficiaries/")
    assert res.status_code in (401, 403)


# ── Update ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_beneficiary_name(auth_client: AsyncClient, created_beneficiary):
    bene_id = created_beneficiary["id"]
    res = await auth_client.patch(f"/beneficiaries/{bene_id}", json={"full_name": "Jane Smith"})
    assert res.status_code == 200
    assert res.json()["full_name"] == "Jane Smith"


@pytest.mark.asyncio
async def test_update_beneficiary_invalid_email_returns_422(auth_client: AsyncClient, created_beneficiary):
    bene_id = created_beneficiary["id"]
    res = await auth_client.patch(f"/beneficiaries/{bene_id}", json={"email": "bad-email"})
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_update_beneficiary_not_owned_returns_404(auth_client: AsyncClient):
    fake_id = str(uuid.uuid4())
    res = await auth_client.patch(f"/beneficiaries/{fake_id}", json={"full_name": "Hacker"})
    assert res.status_code == 404


# ── Emergency Contact ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_set_emergency_contact(auth_client: AsyncClient, created_beneficiary):
    bene_id = created_beneficiary["id"]
    res = await auth_client.patch(f"/beneficiaries/{bene_id}", json={"is_emergency_contact": True})
    assert res.status_code == 200
    assert res.json()["is_emergency_contact"] is True


# ── Delete ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_beneficiary(auth_client: AsyncClient):
    create_res = await auth_client.post("/beneficiaries/", json={
        **VALID_BENEFICIARY,
        "email": f"todelete_{uuid.uuid4().hex[:6]}@testlegate.dev",
    })
    bene_id = create_res.json()["id"]
    del_res = await auth_client.delete(f"/beneficiaries/{bene_id}")
    assert del_res.status_code == 204

    from tests.e2e.conftest import AsyncSessionLocal
    from app.db.models.beneficiary import Beneficiary
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            __import__("sqlalchemy", fromlist=["select"]).select(Beneficiary).where(
                Beneficiary.id == bene_id
            )
        )
        row = result.scalar_one_or_none()
        assert row is not None
        assert row.status.value == "removed"
        assert row.removed_at is not None
