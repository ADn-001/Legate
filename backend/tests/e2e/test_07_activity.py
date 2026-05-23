"""Audit log retrieval and pagination."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_activity_returns_list(auth_client: AsyncClient):
    res = await auth_client.get("/activity")
    assert res.status_code == 200
    body = res.json()
    assert isinstance(body, list) or ("items" in body and isinstance(body["items"], list))


@pytest.mark.asyncio
async def test_activity_requires_auth(http: AsyncClient):
    res = await http.get("/activity")
    assert res.status_code in (401, 403)


@pytest.mark.asyncio
async def test_activity_contains_login_events(auth_client: AsyncClient, registered_user):
    # Session user accumulates events across many modules; paginate to find login.
    all_event_types: set[str] = set()
    for page in range(1, 6):
        res = await auth_client.get(f"/activity?page={page}&per_page=100")
        assert res.status_code == 200
        body = res.json()
        items = body if isinstance(body, list) else body.get("items", [])
        if not items:
            break
        all_event_types.update(item["event_type"] for item in items)
        if "login" in all_event_types:
            break
    assert "login" in all_event_types


@pytest.mark.asyncio
async def test_activity_pagination(auth_client: AsyncClient):
    res = await auth_client.get("/activity?page=1&per_page=5")
    assert res.status_code == 200
    body = res.json()
    items = body if isinstance(body, list) else body["items"]
    assert len(items) <= 5


@pytest.mark.asyncio
async def test_activity_does_not_expose_other_users_logs(
    auth_client: AsyncClient,
    registered_user,
):
    """All returned logs belong to the authenticated user (or have null user_id)."""
    from tests.e2e.conftest import AsyncSessionLocal
    from app.db.models.user import User
    from sqlalchemy import select
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == registered_user["email"]))
        user = result.scalar_one()
        user_id = str(user.id)

    res = await auth_client.get("/activity")
    items = res.json() if isinstance(res.json(), list) else res.json()["items"]
    for item in items:
        assert item.get("user_id") == user_id or item.get("user_id") is None
