"""Celery task logic tested by calling task functions directly (not via broker).

Phase 2: dispatch only persists tokens/state when the email send succeeds, so
this module uses an isolated user with a deterministic Resend test inbox
(delivered+<tag>@resend.dev) instead of the shared session user.
The full lifecycle regressions live in test_12_checkin_lifecycle.py.
"""
import uuid
import pytest
from datetime import datetime, timezone, timedelta

from sqlalchemy import select

from tests.e2e.conftest import AsyncSessionLocal
from app.db.models.user import User, UserSettings, UserStatus
from app.db.models.checkin import CheckInSchedule, CheckInEvent


@pytest.mark.asyncio
async def test_dispatch_due_checkins_sends_email_for_due_schedules():
    """Due schedule + deliverable inbox → token rows created, schedule disarmed."""
    email = f"delivered+{uuid.uuid4().hex[:10]}@resend.dev"
    async with AsyncSessionLocal() as db:
        user = User(
            supabase_uid=f"e2etest-{uuid.uuid4().hex}",
            email=email,
            email_verified=True,
            status=UserStatus.active,
        )
        db.add(user)
        await db.flush()
        db.add(UserSettings(user_id=user.id))
        schedule = CheckInSchedule(
            user_id=user.id,
            interval_days=30,
            grace_period_days=7,
            next_dispatch_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        db.add(schedule)
        await db.commit()
        user_id = user.id
        schedule_id = schedule.id

    from app.worker.tasks import checkin_tasks
    await checkin_tasks._dispatch_due_checkins()

    async with AsyncSessionLocal() as db:
        events = (await db.execute(
            select(CheckInEvent).where(CheckInEvent.user_id == user_id)
        )).scalars().all()
        assert len(events) == 5
        token_types = [e.token_type.value for e in events]
        assert "confirm" in token_types
        assert "snooze_7" in token_types
        assert "emergency_pause" in token_types

        schedule = (await db.execute(
            select(CheckInSchedule).where(CheckInSchedule.id == schedule_id)
        )).scalar_one()
        assert schedule.next_dispatch_at is None  # disarmed until confirm/snooze
        assert schedule.last_dispatched_at is not None


@pytest.mark.asyncio
async def test_celery_beat_schedule_registered():
    from app.worker.celery_app import celery_app
    schedule = celery_app.conf.beat_schedule
    assert "dispatch-checkin-emails" in schedule
    assert "check-grace-periods" in schedule
    assert "send-grace-reminders" in schedule
    assert "process-pending-triggers" in schedule  # B8 promotion path
    task_names = [v["task"] for v in schedule.values()]
    assert any("dispatch_due_checkins" in t for t in task_names)
    assert any("check_grace_periods" in t for t in task_names)
    assert any("send_grace_period_reminders" in t for t in task_names)
    assert any("process_pending_triggers" in t for t in task_names)
