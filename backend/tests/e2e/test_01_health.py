"""Verify server and infrastructure connections are alive."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check_returns_ok(http: AsyncClient):
    res = await http.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_swagger_docs_accessible(http: AsyncClient):
    res = await http.get("/docs")
    assert res.status_code == 200
    assert "swagger" in res.text.lower()


@pytest.mark.asyncio
async def test_openapi_schema_loads(http: AsyncClient):
    res = await http.get("/openapi.json")
    assert res.status_code == 200
    schema = res.json()
    assert "paths" in schema
    paths = schema["paths"]
    assert any("/auth/signup" in p for p in paths)
    assert any("/capsules" in p for p in paths)
    assert any("/beneficiaries" in p for p in paths)
    assert any("/checkin/confirm" in p for p in paths)
    assert any("/activity" in p for p in paths)


@pytest.mark.asyncio
async def test_supabase_connection_via_signup_endpoint(http: AsyncClient):
    import uuid
    res = await http.post("/auth/signup", json={
        "email": f"conntest_{uuid.uuid4().hex[:6]}@testlegate.dev",
        "password": "TestPassword123!",
        "encrypted_cek": "dGVzdA==",
        "cek_iv": "dGVzdA==",
        "pbkdf2_salt": "dGVzdA==",
        "delivery_encrypted_cek": "dGVzdA==",
        "delivery_cek_iv": "dGVzdA==",
    })
    # 429 also proves Supabase is reachable (rate limit response from Supabase)
    assert res.status_code in (201, 409, 429), f"Unexpected status {res.status_code}: {res.text}"


@pytest.mark.asyncio
async def test_redis_connection_via_worker():
    """Verify Redis broker is reachable by Celery."""
    from app.worker.celery_app import celery_app
    inspect = celery_app.control.inspect(timeout=3)
    stats = inspect.stats()
    assert stats is not None, "No Celery workers responded — is the worker running?"
