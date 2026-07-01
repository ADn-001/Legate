"""
Phase 4 T7 (rate limiting) — backend E2E.

B12  Login endpoint (5/minute/IP): 6th POST /auth/login within the same
     minute returns 429 with a Retry-After header.

B13  Default authenticated limit (100/minute/IP via SlowAPIMiddleware):
     burst of 101 GET /users/me requests from the same IP hits 429 with
     Retry-After before the 102nd request.

Isolation: each test uses a unique fake IP injected through
ASGITransport(client=(ip, port)) so no test pollutes another's rate-limit
bucket and the shared session fixtures (which use "testclient" IP) are
unaffected.
"""

import asyncio
import uuid
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from tests.e2e.conftest import (
    AsyncSessionLocal,
    TEST_PASSWORD,
    make_test_email,
    _create_user_via_admin,
)


def _unique_ip() -> str:
    """Return a unique IP in the TEST-NET-1 range (RFC 5737, non-routable)."""
    n = uuid.uuid4().int
    return f"192.0.2.{n % 256}"


def _make_client(ip: str, raise_exceptions: bool = True) -> AsyncClient:
    """ASGI test client with a custom remote-address IP."""
    transport = ASGITransport(
        app=app,
        raise_app_exceptions=raise_exceptions,
        client=(ip, 9999),
    )
    return AsyncClient(transport=transport, base_url="http://test", follow_redirects=True)


# ── B12 — login rate limit (5/minute/IP) ──────────────────────────────────────

@pytest.mark.asyncio
async def test_b12_login_rate_limit_5_per_minute():
    """5 login attempts with a non-existent address get 401 (not 429).
    The 6th attempt within the same minute gets 429 + Retry-After.
    """
    ip = _unique_ip()
    body = {"email": "nonexistent_ratelimit@example.com", "password": "WrongPass1!"}

    async with _make_client(ip) as client:
        # First 5 attempts: rate limit not exceeded
        for attempt in range(1, 6):
            resp = await client.post("/auth/login", json=body)
            assert resp.status_code in (400, 401, 422), (
                f"B12: attempt {attempt} returned unexpected {resp.status_code} "
                "(expected 4xx, not 429)"
            )
            assert resp.status_code != 429, (
                f"B12: hit rate limit prematurely on attempt {attempt}"
            )

        # 6th attempt within the same minute: must be 429
        resp = await client.post("/auth/login", json=body)
        assert resp.status_code == 429, (
            f"B12: expected 429 on 6th login attempt, got {resp.status_code}: {resp.text}"
        )
        assert "retry-after" in {h.lower() for h in resp.headers}, (
            "B12: 429 response is missing the Retry-After header"
        )


# ── B13 — authenticated burst (100/minute/IP default limit) ──────────────────

@pytest.mark.asyncio
async def test_b13_authenticated_burst_100_per_minute(registered_user):
    """101+ GET /users/me requests from one IP within a minute hits 429.

    Uses the session-scoped `registered_user` fixture for a valid JWT so
    the endpoint returns 200 for requests under the limit.  The rate-limit
    key is the unique fake IP, so this test is isolated from all others.
    """
    ip = _unique_ip()
    token = registered_user["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Send all 110 requests concurrently so they land within the same
    # rate-limit window. Sequential requests take ~15 s each (NullPool opens a
    # new asyncpg connection per request) and would span multiple 1-minute
    # windows, resetting the bucket before it ever reaches 100.
    async with _make_client(ip, raise_exceptions=False) as client:
        tasks = [client.get("/users/me", headers=headers) for _ in range(110)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

    hit_429 = False
    for resp in responses:
        if isinstance(resp, Exception):
            continue  # connection error during burst — acceptable
        if resp.status_code == 429:
            assert "retry-after" in {h.lower() for h in resp.headers}, (
                "B13: 429 response is missing the Retry-After header"
            )
            hit_429 = True
            break

    assert hit_429, (
        "B13: never received 429 after 100+ concurrent requests — "
        "SlowAPIMiddleware default_limits may not be active"
    )
