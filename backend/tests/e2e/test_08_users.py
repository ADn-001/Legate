"""User profile and account deletion."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_me(auth_client: AsyncClient, registered_user):
    res = await auth_client.get("/users/me")
    assert res.status_code == 200
    body = res.json()
    assert body["email"] == registered_user["email"]
    assert body["email_verified"] is True
    assert "status" in body


@pytest.mark.asyncio
async def test_get_me_requires_auth(http: AsyncClient):
    res = await http.get("/users/me")
    assert res.status_code in (401, 403)


@pytest.mark.asyncio
async def test_delete_account_wrong_confirmation_returns_422(auth_client: AsyncClient, registered_user):
    res = await auth_client.request("DELETE", "/users/me", json={
        "confirmation": "WRONG",
        "password": registered_user["password"],
    })
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_delete_account_wrong_password_returns_401(auth_client: AsyncClient, registered_user):
    res = await auth_client.request("DELETE", "/users/me", json={
        "confirmation": "DELETE",
        "password": "WrongPassword999!",
    })
    assert res.status_code == 401
