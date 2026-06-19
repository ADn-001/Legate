"""Capsule CRUD, storage upload URL, status transitions."""
import pytest
import uuid
from httpx import AsyncClient


# ── Create ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_capsule_returns_201(auth_client: AsyncClient, test_beneficiary):
    res = await auth_client.post("/capsules/", json={
        "title": "Test Capsule Create",
        "beneficiary_id": test_beneficiary["id"],
        "cipher_iv": "a" * 24,
    })
    assert res.status_code == 201
    body = res.json()
    assert "id" in body
    assert "upload_url" in body
    assert body["upload_url"].startswith("https://")


@pytest.mark.asyncio
async def test_create_capsule_with_invalid_beneficiary_returns_404(auth_client: AsyncClient):
    res = await auth_client.post("/capsules/", json={
        "title": "Bad Capsule",
        "beneficiary_id": str(uuid.uuid4()),
        "cipher_iv": "a" * 24,
    })
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_create_capsule_missing_title_returns_422(auth_client: AsyncClient, test_beneficiary):
    res = await auth_client.post("/capsules/", json={
        "beneficiary_id": test_beneficiary["id"],
        "cipher_iv": "a" * 24,
    })
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_create_capsule_inserts_db_rows(auth_client: AsyncClient, test_beneficiary, created_capsule):
    from tests.e2e.conftest import AsyncSessionLocal
    from app.db.models.capsule import Capsule, CapsuleRecipient
    from sqlalchemy import select
    capsule_id = created_capsule["id"]
    async with AsyncSessionLocal() as db:
        cap = await db.get(Capsule, capsule_id)
        assert cap is not None
        assert cap.title == "Shared Test Capsule"
        assert cap.status.value == "draft"

        recip = await db.execute(
            select(CapsuleRecipient).where(CapsuleRecipient.capsule_id == capsule_id)
        )
        assert recip.scalar_one_or_none() is not None


# ── List ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_capsules(auth_client: AsyncClient, created_capsule):
    res = await auth_client.get("/capsules/")
    assert res.status_code == 200
    body = res.json()
    assert isinstance(body, list)
    assert any(c["id"] == created_capsule["id"] for c in body)


@pytest.mark.asyncio
async def test_list_capsules_includes_pending_deletion_with_badge_status(
    auth_client: AsyncClient, test_beneficiary
):
    """B17 / FR-31: a just-deleted capsule stays listed as pending_deletion
    (the frontend shows a badge); only fully purged capsules disappear."""
    create = await auth_client.post("/capsules/", json={
        "title": "To Delete",
        "beneficiary_id": test_beneficiary["id"],
        "cipher_iv": "b" * 24,
    })
    cap_id = create.json()["id"]
    await auth_client.delete(f"/capsules/{cap_id}")

    res = await auth_client.get("/capsules/")
    by_id = {c["id"]: c for c in res.json()}
    assert cap_id in by_id, "B17 regression: pending_deletion capsule missing from list"
    assert by_id[cap_id]["status"] == "pending_deletion"


@pytest.mark.asyncio
async def test_list_capsules_excludes_fully_deleted(auth_client: AsyncClient, test_beneficiary):
    create = await auth_client.post("/capsules/", json={
        "title": "Fully Deleted",
        "beneficiary_id": test_beneficiary["id"],
        "cipher_iv": "f" * 24,
    })
    cap_id = create.json()["id"]

    from tests.e2e.conftest import AsyncSessionLocal
    from app.db.models.capsule import Capsule, CapsuleStatus
    async with AsyncSessionLocal() as db:
        cap = await db.get(Capsule, cap_id)
        cap.status = CapsuleStatus.deleted
        await db.commit()

    res = await auth_client.get("/capsules/")
    ids = [c["id"] for c in res.json()]
    assert cap_id not in ids


@pytest.mark.asyncio
async def test_list_capsules_exposes_has_recipients(auth_client: AsyncClient, created_capsule):
    """FR-22: the list response carries the zero-recipient flag."""
    res = await auth_client.get("/capsules/")
    cap = next(c for c in res.json() if c["id"] == created_capsule["id"])
    assert cap["has_recipients"] is True


# ── Get Single ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_capsule_by_id(auth_client: AsyncClient, created_capsule):
    cap_id = created_capsule["id"]
    res = await auth_client.get(f"/capsules/{cap_id}")
    assert res.status_code == 200
    assert res.json()["id"] == cap_id


@pytest.mark.asyncio
async def test_get_capsule_not_owned_returns_404(auth_client: AsyncClient):
    res = await auth_client.get(f"/capsules/{uuid.uuid4()}")
    assert res.status_code == 404


# ── Update ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_capsule_title(auth_client: AsyncClient, created_capsule):
    cap_id = created_capsule["id"]
    res = await auth_client.patch(f"/capsules/{cap_id}", json={"title": "Updated Title"})
    assert res.status_code == 200
    assert res.json()["title"] == "Updated Title"


@pytest.mark.asyncio
async def test_patch_storage_path_sets_status_active(auth_client: AsyncClient, test_beneficiary):
    create = await auth_client.post("/capsules/", json={
        "title": "Storage Path Test",
        "beneficiary_id": test_beneficiary["id"],
        "cipher_iv": "c" * 24,
    })
    cap_id = create.json()["id"]
    res = await auth_client.patch(f"/capsules/{cap_id}", json={
        "storage_object_path": f"test-user/{cap_id}/content.enc"
    })
    assert res.status_code == 200
    assert res.json()["status"] == "active"


# ── Delete ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_capsule_sets_pending_deletion(auth_client: AsyncClient, test_beneficiary):
    create = await auth_client.post("/capsules/", json={
        "title": "Delete Me",
        "beneficiary_id": test_beneficiary["id"],
        "cipher_iv": "d" * 24,
    })
    cap_id = create.json()["id"]
    del_res = await auth_client.delete(f"/capsules/{cap_id}")
    assert del_res.status_code == 204

    from tests.e2e.conftest import AsyncSessionLocal
    from app.db.models.capsule import Capsule
    async with AsyncSessionLocal() as db:
        cap = await db.get(Capsule, cap_id)
        assert cap.status.value == "pending_deletion"


# ── Storage Upload URL ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_upload_url_is_valid_supabase_url(auth_client: AsyncClient, test_beneficiary):
    from app.config import get_settings
    cfg = get_settings()
    create = await auth_client.post("/capsules/", json={
        "title": "URL Validity Test",
        "beneficiary_id": test_beneficiary["id"],
        "cipher_iv": "e" * 24,
    })
    upload_url = create.json()["upload_url"]
    assert cfg.supabase_url.replace("https://", "") in upload_url
