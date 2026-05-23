"""Celery task logic tested by calling task functions directly (not via broker)."""
import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, update

from tests.e2e.conftest import AsyncSessionLocal
from app.db.models.checkin import CheckInSchedule, CheckInEvent
from app.db.models.user import User


@pytest.mark.asyncio
async def test_dispatch_due_checkins_sends_email_for_due_schedules(registered_user):
    """Set next_dispatch_at to past, run dispatch task, verify checkin_events created."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == registered_user["email"]))
        user = result.scalar_one()
        await db.execute(
            update(CheckInSchedule)
            .where(CheckInSchedule.user_id == user.id)
            .values(next_dispatch_at=datetime.now(timezone.utc) - timedelta(hours=1))
        )
        await db.commit()

    from app.worker.tasks import checkin_tasks
    await checkin_tasks._dispatch_due_checkins()

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(CheckInEvent)
            .join(CheckInSchedule)
            .join(User)
            .where(User.email == registered_user["email"])
            .order_by(CheckInEvent.sent_at.desc())
            .limit(5)
        )
        events = result.scalars().all()
        assert len(events) > 0
        token_types = [e.token_type.value for e in events]
        assert "confirm" in token_types
        assert "snooze_7" in token_types


@pytest.mark.asyncio
async def test_check_grace_periods_creates_release_trigger():
    pytest.skip("Requires isolated test user — implement with dedicated fixture")


@pytest.mark.asyncio
async def test_purge_capsule_storage_marks_deleted():
    pytest.skip("Requires real Supabase Storage object — implement post-storage-integration")


@pytest.mark.asyncio
async def test_celery_beat_schedule_registered():
    from app.worker.celery_app import celery_app
    schedule = celery_app.conf.beat_schedule
    assert "dispatch-checkin-emails" in schedule
    assert "check-grace-periods" in schedule
    assert "send-grace-reminders" in schedule
    task_names = [v["task"] for v in schedule.values()]
    assert any("dispatch_due_checkins" in t for t in task_names)
    assert any("check_grace_periods" in t for t in task_names)
    assert any("send_grace_period_reminders" in t for t in task_names)
