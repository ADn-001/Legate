"""
Celery tasks for check-in email dispatch and grace period monitoring.
"""

import asyncio
import secrets
from datetime import datetime, timedelta, timezone

from app.worker.celery_app import celery_app


@celery_app.task(name="app.worker.tasks.checkin_tasks.dispatch_due_checkins")
def dispatch_due_checkins():
    asyncio.run(_dispatch_due_checkins())


async def _dispatch_due_checkins():
    from sqlalchemy import select
    from app.db.session import AsyncSessionLocal
    from app.db.models.user import User
    from app.db.models.checkin import CheckInSchedule, CheckInEvent, TokenType, EventStatus
    from app.core.email import send_checkin_email
    from app.core.audit import write_audit
    from app.config import get_settings

    cfg = get_settings()
    now = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(CheckInSchedule)
            .where(CheckInSchedule.next_dispatch_at <= now)
            .where(CheckInSchedule.is_paused.is_(False))
        )
        schedules = result.scalars().all()

        for schedule in schedules:
            user_result = await db.get(User, schedule.user_id)
            if not user_result:
                continue
            user = user_result

            expires_at = now + timedelta(days=7)
            tokens = {
                TokenType.confirm: secrets.token_urlsafe(64),
                TokenType.snooze_7: secrets.token_urlsafe(64),
                TokenType.snooze_14: secrets.token_urlsafe(64),
                TokenType.snooze_30: secrets.token_urlsafe(64),
                TokenType.emergency_pause: secrets.token_urlsafe(64),
            }

            for token_type, token_value in tokens.items():
                db.add(CheckInEvent(
                    user_id=user.id,
                    schedule_id=schedule.id,
                    token=token_value,
                    token_type=token_type,
                    status=EventStatus.pending,
                    expires_at=expires_at,
                    sent_at=now,
                ))

            confirm_url = f"{cfg.base_url}/checkin/confirm?token={tokens[TokenType.confirm]}"
            snooze_7_url = f"{cfg.base_url}/checkin/snooze?token={tokens[TokenType.snooze_7]}&days=7"
            snooze_14_url = f"{cfg.base_url}/checkin/snooze?token={tokens[TokenType.snooze_14]}&days=14"
            snooze_30_url = f"{cfg.base_url}/checkin/snooze?token={tokens[TokenType.snooze_30]}&days=30"

            try:
                send_checkin_email(
                    to=user.email,
                    confirm_url=confirm_url,
                    snooze_7_url=snooze_7_url,
                    snooze_14_url=snooze_14_url,
                    snooze_30_url=snooze_30_url,
                    snoozes_remaining=schedule.snooze_limit - schedule.snooze_count,
                )
            except Exception:
                pass  # log but don't abort — next run will retry

            schedule.last_dispatched_at = now
            await write_audit(db, "checkin_dispatched", user_id=user.id)
            await db.commit()


@celery_app.task(name="app.worker.tasks.checkin_tasks.check_grace_periods")
def check_grace_periods():
    asyncio.run(_check_grace_periods())


async def _check_grace_periods():
    from sqlalchemy import select, and_
    from app.db.session import AsyncSessionLocal
    from app.db.models.user import User
    from app.db.models.checkin import CheckInSchedule, ReleaseTrigger, TriggerReason, TriggerStatus
    from app.db.models.beneficiary import Beneficiary
    from app.core.audit import write_audit

    now = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(CheckInSchedule).where(
                and_(
                    CheckInSchedule.last_dispatched_at.isnot(None),
                    CheckInSchedule.is_paused.is_(False),
                )
            )
        )
        schedules = result.scalars().all()

        for schedule in schedules:
            if not schedule.last_dispatched_at:
                continue
            dispatched_at = schedule.last_dispatched_at
            if dispatched_at.tzinfo is None:
                dispatched_at = dispatched_at.replace(tzinfo=timezone.utc)
            grace_deadline = dispatched_at + timedelta(days=schedule.grace_period_days)

            confirmed_at = schedule.last_confirmed_at
            if confirmed_at and confirmed_at.tzinfo is None:
                confirmed_at = confirmed_at.replace(tzinfo=timezone.utc)

            already_confirmed = confirmed_at and confirmed_at >= dispatched_at
            if already_confirmed or now < grace_deadline:
                continue

            # Check no existing processing trigger for this user
            existing = await db.execute(
                select(ReleaseTrigger).where(
                    and_(
                        ReleaseTrigger.user_id == schedule.user_id,
                        ReleaseTrigger.status == TriggerStatus.processing,
                    )
                )
            )
            if existing.scalar_one_or_none():
                continue

            trigger = ReleaseTrigger(
                user_id=schedule.user_id,
                triggered_at=now,
                reason=TriggerReason.checkin_missed,
                status=TriggerStatus.processing,
            )
            db.add(trigger)
            await db.flush()
            await write_audit(db, "delivery_triggered", user_id=schedule.user_id, resource_id=trigger.id)
            await db.commit()

            from app.worker.tasks.delivery_tasks import execute_delivery
            execute_delivery.apply_async(args=[str(trigger.id)])


@celery_app.task(name="app.worker.tasks.checkin_tasks.send_grace_period_reminders")
def send_grace_period_reminders():
    asyncio.run(_send_grace_period_reminders())


async def _send_grace_period_reminders():
    import secrets
    from sqlalchemy import select, and_
    from app.db.session import AsyncSessionLocal
    from app.db.models.user import User
    from app.db.models.checkin import CheckInSchedule, CheckInEvent, TokenType, EventStatus
    from app.core.email import send_grace_period_reminder
    from app.config import get_settings

    cfg = get_settings()
    now = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(CheckInSchedule).where(
                and_(
                    CheckInSchedule.last_dispatched_at.isnot(None),
                    CheckInSchedule.is_paused.is_(False),
                    CheckInSchedule.grace_reminder_sent_at.is_(None),
                )
            )
        )
        schedules = result.scalars().all()

        for schedule in schedules:
            dispatched_at = schedule.last_dispatched_at
            if not dispatched_at:
                continue
            if dispatched_at.tzinfo is None:
                dispatched_at = dispatched_at.replace(tzinfo=timezone.utc)

            grace_deadline = dispatched_at + timedelta(days=schedule.grace_period_days)
            days_into_grace = (now - dispatched_at).days

            confirmed_at = schedule.last_confirmed_at
            if confirmed_at and confirmed_at.tzinfo is None:
                confirmed_at = confirmed_at.replace(tzinfo=timezone.utc)
            if confirmed_at and confirmed_at >= dispatched_at:
                continue
            if now >= grace_deadline:
                continue

            # Send at day 3 and day 7 of grace period
            if days_into_grace not in (3, 7):
                continue

            days_remaining = (grace_deadline - now).days

            # Generate a fresh confirm token for the reminder
            token_value = secrets.token_urlsafe(64)
            expires_at = now + timedelta(days=max(days_remaining, 1))
            db.add(CheckInEvent(
                user_id=schedule.user_id,
                schedule_id=schedule.id,
                token=token_value,
                token_type=TokenType.confirm,
                status=EventStatus.pending,
                expires_at=expires_at,
                sent_at=now,
            ))

            user = await db.get(User, schedule.user_id)
            if not user:
                continue

            confirm_url = f"{cfg.base_url}/checkin/confirm?token={token_value}"
            try:
                send_grace_period_reminder(to=user.email, days_remaining=days_remaining, confirm_url=confirm_url)
            except Exception:
                continue

            schedule.grace_reminder_sent_at = now
            await db.commit()
