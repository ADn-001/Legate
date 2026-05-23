"""Verify direct Supabase connectivity: Auth, Storage, and DB."""
import pytest


@pytest.mark.asyncio
async def test_supabase_auth_admin_can_list_users():
    from tests.e2e.conftest import _make_admin_client
    sb = _make_admin_client()
    users = sb.auth.admin.list_users()
    assert users is not None
    assert hasattr(users, "__iter__")


@pytest.mark.asyncio
async def test_supabase_storage_buckets_exist():
    from app.core.supabase import get_storage
    storage = get_storage()
    buckets = storage.list_buckets()
    bucket_names = [b.name for b in buckets]
    assert "capsule-content" in bucket_names, f"Missing bucket. Found: {bucket_names}"
    assert "media-attachments" in bucket_names, f"Missing bucket. Found: {bucket_names}"
    assert "thumbnails" in bucket_names, f"Missing bucket. Found: {bucket_names}"


@pytest.mark.asyncio
async def test_supabase_storage_buckets_are_private():
    from app.core.supabase import get_storage
    storage = get_storage()
    buckets = storage.list_buckets()
    for bucket in buckets:
        if bucket.name in ("capsule-content", "media-attachments", "thumbnails"):
            assert bucket.public is False, f"Bucket {bucket.name} should be private"


@pytest.mark.asyncio
async def test_supabase_storage_signed_url_generation():
    from app.core.supabase import get_storage
    import uuid
    storage = get_storage()
    test_path = f"test-user-id/{uuid.uuid4()}/test.enc"
    result = storage.from_("capsule-content").create_signed_upload_url(test_path)
    assert isinstance(result, dict) and ("signedURL" in result or "signed_url" in result)


@pytest.mark.asyncio
async def test_supabase_db_tables_exist():
    from tests.e2e.conftest import AsyncSessionLocal
    from sqlalchemy import text
    expected_tables = [
        "users", "user_settings", "encryption_keys", "beneficiaries",
        "capsules", "capsule_recipients", "media_attachments",
        "checkin_schedules", "checkin_events", "release_triggers",
        "delivery_events", "audit_logs",
    ]
    async with AsyncSessionLocal() as db:
        for table in expected_tables:
            result = await db.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = result.scalar()
            assert count is not None, f"Table {table} is not accessible"


@pytest.mark.asyncio
async def test_supabase_rls_is_enabled():
    from tests.e2e.conftest import AsyncSessionLocal
    from sqlalchemy import text
    expected_tables = [
        "users", "user_settings", "encryption_keys", "beneficiaries",
        "capsules", "capsule_recipients", "media_attachments",
        "checkin_schedules", "checkin_events", "release_triggers",
        "delivery_events", "audit_logs",
    ]
    async with AsyncSessionLocal() as db:
        for table in expected_tables:
            result = await db.execute(text(
                f"SELECT relrowsecurity FROM pg_class WHERE relname = '{table}'"
            ))
            rls_enabled = result.scalar()
            assert rls_enabled is True, f"RLS not enabled on table: {table}"
