"""Token lifecycle: generate via DB, then redeem via confirm/snooze/pause routes."""
import pytest
import secrets
import uuid
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from sqlalchemy import select

from tests.e2e.conftest import AsyncSessionLocal
from app.db.models.checkin import CheckInSchedule, CheckInEvent, TokenType, EventStatus


async def _insert_test_token(
    user_id: str,
    schedule_id: str,
    token_type: TokenType,
    expired: bool = False,
    used: bool = False,
) -> str:
    """Directly insert a checkin_event row for testing token redemption."""
    token = secrets.token_urlsafe(48)
    expires_at = datetime.now(timezone.utc) + (
        timedelta(days=-1) if expired else timedelta(days=7)
    )
    async with AsyncSessionLocal() as db:
        event = CheckInEvent(
            id=uuid.uuid4(),
            user_id=uuid.UUID(user_id),
            schedule_id=uuid.UUID(schedule_id),
            token=token,
            token_type=token_type,
            status=EventStatus.used if used else EventStatus.pending,
            expires_at=expires_at,
            sent_at=datetime.now(timezone.utc),
        )
        db.add(event)
        await db.commit()
    return token


async def _get_user_schedule(user_id: str) -> CheckInSchedule:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(CheckInSchedule).where(CheckInSchedule.user_id == uuid.UUID(user_id))
        )
        return result.scalar_one()


@pytest.fixture(scope="module")
async def user_ids(registered_user):
    from app.db.models.user import User
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.email == registered_user["email"])
        )
        user = result.scalar_one()
        schedule = await _get_user_schedule(str(user.id))
        return {"user_id": str(user.id), "schedule_id": str(schedule.id)}


# ── Confirm ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_confirm_valid_token(http: AsyncClient, user_ids):
    token = await _insert_test_token(user_ids["user_id"], user_ids["schedule_id"], TokenType.confirm)
    res = await http.get(f"/checkin/confirm?token={token}")
    assert res.status_code == 200
    assert "text/html" in res.headers.get("content-type", "")
    assert "confirmed" in res.text.lower()


@pytest.mark.asyncio
async def test_confirm_marks_token_used(http: AsyncClient, user_ids):
    token = await _insert_test_token(user_ids["user_id"], user_ids["schedule_id"], TokenType.confirm)
    await http.get(f"/checkin/confirm?token={token}")
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(CheckInEvent).where(CheckInEvent.token == token))
        event = result.scalar_one()
        assert event.status.value == "used"
        assert event.used_at is not None


@pytest.mark.asyncio
async def test_confirm_resets_schedule_timer(http: AsyncClient, user_ids):
    schedule_before = await _get_user_schedule(user_ids["user_id"])
    token = await _insert_test_token(user_ids["user_id"], user_ids["schedule_id"], TokenType.confirm)
    await http.get(f"/checkin/confirm?token={token}")
    schedule_after = await _get_user_schedule(user_ids["user_id"])
    if schedule_before.last_confirmed_at:
        assert schedule_after.last_confirmed_at > schedule_before.last_confirmed_at
    assert schedule_after.snooze_count == 0


@pytest.mark.asyncio
async def test_confirm_expired_token_returns_410(http: AsyncClient, user_ids):
    # [FIXED #1] Route catches exception → HTMLResponse with correct status code
    token = await _insert_test_token(
        user_ids["user_id"], user_ids["schedule_id"], TokenType.confirm, expired=True
    )
    res = await http.get(f"/checkin/confirm?token={token}")
    assert res.status_code == 410
    assert "text/html" in res.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_confirm_used_token_returns_409(http: AsyncClient, user_ids):
    # [FIXED #1]
    token = await _insert_test_token(
        user_ids["user_id"], user_ids["schedule_id"], TokenType.confirm, used=True
    )
    res = await http.get(f"/checkin/confirm?token={token}")
    assert res.status_code == 409
    assert "text/html" in res.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_confirm_token_single_use_second_call_409(http: AsyncClient, user_ids):
    """T-test 3 (NFR-12 regression): redeem the SAME confirm token twice —
    first succeeds (200), second is rejected with 409."""
    token = await _insert_test_token(user_ids["user_id"], user_ids["schedule_id"], TokenType.confirm)
    first = await http.get(f"/checkin/confirm?token={token}")
    assert first.status_code == 200
    second = await http.get(f"/checkin/confirm?token={token}")
    assert second.status_code == 409
    assert "text/html" in second.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_confirm_nonexistent_token_returns_404(http: AsyncClient):
    # [FIXED #1]
    res = await http.get("/checkin/confirm?token=totallyFakeToken12345")
    assert res.status_code == 404
    assert "text/html" in res.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_confirm_missing_token_returns_422(http: AsyncClient):
    # FastAPI raises 422 before route handler — not wrapped in HTMLResponse
    res = await http.get("/checkin/confirm")
    assert res.status_code == 422


# ── Snooze ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_snooze_7_days(http: AsyncClient, user_ids):
    # Reset snooze count first
    from sqlalchemy import update
    async with AsyncSessionLocal() as db:
        await db.execute(
            update(CheckInSchedule)
            .where(CheckInSchedule.user_id == uuid.UUID(user_ids["user_id"]))
            .values(snooze_count=0)
        )
        await db.commit()

    token = await _insert_test_token(user_ids["user_id"], user_ids["schedule_id"], TokenType.snooze_7)
    schedule_before = await _get_user_schedule(user_ids["user_id"])
    res = await http.get(f"/checkin/snooze?token={token}&days=7")
    assert res.status_code == 200
    schedule_after = await _get_user_schedule(user_ids["user_id"])
    assert schedule_after.snooze_count == schedule_before.snooze_count + 1


@pytest.mark.asyncio
async def test_snooze_increments_snooze_count(http: AsyncClient, user_ids):
    from sqlalchemy import update
    async with AsyncSessionLocal() as db:
        await db.execute(
            update(CheckInSchedule)
            .where(CheckInSchedule.user_id == uuid.UUID(user_ids["user_id"]))
            .values(snooze_count=0)
        )
        await db.commit()

    token = await _insert_test_token(user_ids["user_id"], user_ids["schedule_id"], TokenType.snooze_14)
    await http.get(f"/checkin/snooze?token={token}&days=14")
    schedule = await _get_user_schedule(user_ids["user_id"])
    assert schedule.snooze_count == 1


@pytest.mark.asyncio
async def test_snooze_respects_limit(http: AsyncClient, user_ids):
    # [FIXED #2] Service raises HTTP_409_CONFLICT when snooze_count >= snooze_limit
    from sqlalchemy import update
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(CheckInSchedule).where(
                CheckInSchedule.user_id == uuid.UUID(user_ids["user_id"])
            )
        )
        schedule = result.scalar_one()
        snooze_limit = schedule.snooze_limit
        await db.execute(
            update(CheckInSchedule)
            .where(CheckInSchedule.user_id == uuid.UUID(user_ids["user_id"]))
            .values(snooze_count=snooze_limit)
        )
        await db.commit()

    token = await _insert_test_token(user_ids["user_id"], user_ids["schedule_id"], TokenType.snooze_7)
    res = await http.get(f"/checkin/snooze?token={token}&days=7")
    assert res.status_code == 409


@pytest.mark.asyncio
async def test_snooze_wrong_days_for_token_type_returns_400(http: AsyncClient, user_ids):
    """days=30 with snooze_7 token should fail with 400."""
    from sqlalchemy import update
    async with AsyncSessionLocal() as db:
        await db.execute(
            update(CheckInSchedule)
            .where(CheckInSchedule.user_id == uuid.UUID(user_ids["user_id"]))
            .values(snooze_count=0)
        )
        await db.commit()
    token = await _insert_test_token(user_ids["user_id"], user_ids["schedule_id"], TokenType.snooze_7)
    res = await http.get(f"/checkin/snooze?token={token}&days=30")
    assert res.status_code == 400


# ── Emergency Pause ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_emergency_pause_requires_valid_token(http: AsyncClient):
    # [FIXED #1] Route returns HTMLResponse 404 for unknown token
    res = await http.get("/checkin/emergency/pause?token=faketoken")
    assert res.status_code == 404
    assert "text/html" in res.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_emergency_pause_missing_token_returns_422(http: AsyncClient):
    res = await http.get("/checkin/emergency/pause")
    assert res.status_code == 422
