"""
Celery tasks for check-in email dispatch and grace period monitoring.

Lifecycle (Phase 2, B1-B8):
  dispatch_due_checkins      — hourly; sends check-in emails for due schedules,
                               then clears next_dispatch_at so the schedule is
                               not re-dispatched until confirm/snooze re-arms it.
  check_grace_periods        — hourly; creates ONE release trigger per missed
                               check-in cycle. With an emergency contact the
                               trigger starts as pending_confirmation with a
                               48h window (FR-23/24); otherwise it goes
                               straight to processing.
  process_pending_triggers   — hourly; promotes pending_confirmation triggers
                               whose 48h window elapsed to processing and
                               enqueues delivery.
  send_grace_period_reminders — every 12h; escalating reminders at grace day 3
                               and day 7, at most once per threshold per cycle.
"""

import asyncio
import secrets
from datetime import datetime, timedelta, timezone

from app.worker.celery_app import celery_app

# Hours an emergency contact has to pause delivery before it proceeds (FR-23).
EMERGENCY_CONFIRMATION_WINDOW_HOURS = 48

# Grace-day thresholds for escalating reminders (FR-16).
GRACE_REMINDER_THRESHOLDS = (3, 7)

# Days the grace period is extended per emergency pause (FR-24).
PAUSE_EXTENSION_DAYS = 7


@celery_app.task(name="app.worker.tasks.checkin_tasks.dispatch_due_checkins")
def dispatch_due_checkins():
    asyncio.run(_dispatch_due_checkins())


async def _dispatch_due_checkins():
    from sqlalchemy import select, and_
    from app.db.session import AsyncSessionLocal
    from app.db.models.user import User, UserStatus
    from app.db.models.checkin import CheckInSchedule, CheckInEvent, TokenType, EventStatus
    from app.core.email import send_checkin_email
    from app.core.audit import write_audit
    from app.config import get_settings

    cfg = get_settings()
    now = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as db:
        # B1: only schedules that are armed (next_dispatch_at set).
        # B3: only active, email-verified users ever receive check-in emails.
        result = await db.execute(
            select(CheckInSchedule)
            .join(User, User.id == CheckInSchedule.user_id)
            .where(
                and_(
                    CheckInSchedule.next_dispatch_at.isnot(None),
                    CheckInSchedule.next_dispatch_at <= now,
                    CheckInSchedule.is_paused.is_(False),
                    User.status == UserStatus.active,
                    User.email_verified.is_(True),
                )
            )
        )
        schedules = result.scalars().all()

        for schedule in schedules:
            user = await db.get(User, schedule.user_id)
            if not user:
                continue

            expires_at = now + timedelta(days=7)
            tokens = {
                TokenType.confirm: secrets.token_urlsafe(64),
                TokenType.snooze_7: secrets.token_urlsafe(64),
                TokenType.snooze_14: secrets.token_urlsafe(64),
                TokenType.snooze_30: secrets.token_urlsafe(64),
                TokenType.emergency_pause: secrets.token_urlsafe(64),
            }

            confirm_url = f"{cfg.base_url}/checkin/confirm?token={tokens[TokenType.confirm]}"
            snooze_7_url = f"{cfg.base_url}/checkin/snooze?token={tokens[TokenType.snooze_7]}&days=7"
            snooze_14_url = f"{cfg.base_url}/checkin/snooze?token={tokens[TokenType.snooze_14]}&days=14"
            snooze_30_url = f"{cfg.base_url}/checkin/snooze?token={tokens[TokenType.snooze_30]}&days=30"

            # Send first; only persist tokens/state on success so a failed
            # send leaves next_dispatch_at armed for the next hourly retry
            # (and no session rollback is ever needed mid-loop).
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
                continue

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

            # B1: successful send — disarm until confirm/snooze re-arms,
            # and start a fresh grace cycle.
            schedule.last_dispatched_at = now
            schedule.next_dispatch_at = None
            schedule.grace_reminder_sent_at = None
            schedule.last_grace_reminder_day = None
            await write_audit(db, "checkin_dispatched", user_id=user.id)
            await db.commit()


@celery_app.task(name="app.worker.tasks.checkin_tasks.check_grace_periods")
def check_grace_periods():
    asyncio.run(_check_grace_periods())


def _as_utc(dt):
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


async def _check_grace_periods():
    from sqlalchemy import select, and_
    from app.db.session import AsyncSessionLocal
    from app.db.models.user import User, UserStatus
    from app.db.models.checkin import (
        CheckInSchedule, CheckInEvent, TokenType, EventStatus,
        ReleaseTrigger, TriggerReason, TriggerStatus,
    )
    from app.db.models.beneficiary import Beneficiary, BeneficiaryStatus
    from app.core.audit import write_audit
    from app.core.email import send_emergency_pause_email
    from app.config import get_settings

    cfg = get_settings()
    now = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as db:
        # B2: memorialized / deleted / pending-deletion users are done — only
        # active users can have a new trigger formed.
        # NOTE: paused schedules are NOT skipped here; an emergency pause
        # extends the grace deadline (PAUSE_EXTENSION_DAYS * pause_count) and a
        # new cycle/trigger forms naturally if the user still doesn't confirm.
        result = await db.execute(
            select(CheckInSchedule)
            .join(User, User.id == CheckInSchedule.user_id)
            .where(
                and_(
                    CheckInSchedule.last_dispatched_at.isnot(None),
                    User.status == UserStatus.active,
                )
            )
        )
        schedules = result.scalars().all()

        for schedule in schedules:
            dispatched_at = _as_utc(schedule.last_dispatched_at)
            if not dispatched_at:
                continue

            grace_deadline = dispatched_at + timedelta(
                days=schedule.grace_period_days + PAUSE_EXTENSION_DAYS * (schedule.pause_count or 0)
            )

            confirmed_at = _as_utc(schedule.last_confirmed_at)
            already_confirmed = confirmed_at and confirmed_at >= dispatched_at
            if already_confirmed or now < grace_deadline:
                continue

            # B2: one trigger per missed-check-in cycle. A trigger (in any
            # non-pause state, including failed — retries are owned by the
            # delivery task, T8/B6) created during the current cycle blocks a
            # duplicate. paused_cancelled triggers do NOT block: after the
            # pause extension elapses a new trigger forms (FR-24).
            existing = await db.execute(
                select(ReleaseTrigger).where(
                    and_(
                        ReleaseTrigger.user_id == schedule.user_id,
                        ReleaseTrigger.status.in_([
                            TriggerStatus.pending_confirmation,
                            TriggerStatus.processing,
                            TriggerStatus.completed,
                            TriggerStatus.failed,
                        ]),
                        ReleaseTrigger.triggered_at >= dispatched_at,
                    )
                )
            )
            if existing.scalars().first():
                continue

            # B8 / FR-23: with an emergency contact, open a 48h
            # pre-trigger window instead of delivering immediately.
            contact_result = await db.execute(
                select(Beneficiary).where(
                    and_(
                        Beneficiary.user_id == schedule.user_id,
                        Beneficiary.is_emergency_contact.is_(True),
                        Beneficiary.status != BeneficiaryStatus.removed,
                    )
                )
            )
            emergency_contact = contact_result.scalars().first()

            if emergency_contact:
                deliver_after = now + timedelta(hours=EMERGENCY_CONFIRMATION_WINDOW_HOURS)
                trigger = ReleaseTrigger(
                    user_id=schedule.user_id,
                    triggered_at=now,
                    reason=TriggerReason.checkin_missed,
                    status=TriggerStatus.pending_confirmation,
                    deliver_after=deliver_after,
                )
                db.add(trigger)
                await db.flush()

                # Fresh single-use pause token addressed to the contact.
                pause_token = secrets.token_urlsafe(64)
                db.add(CheckInEvent(
                    user_id=schedule.user_id,
                    schedule_id=schedule.id,
                    token=pause_token,
                    token_type=TokenType.emergency_pause,
                    status=EventStatus.pending,
                    expires_at=deliver_after,
                    sent_at=now,
                ))

                user = await db.get(User, schedule.user_id)
                pause_url = f"{cfg.base_url}/checkin/emergency/pause?token={pause_token}"
                try:
                    send_emergency_pause_email(
                        to=emergency_contact.email,
                        contact_name=emergency_contact.full_name,
                        user_name=(user.full_name or user.email) if user else "the account holder",
                        pause_url=pause_url,
                        deadline=deliver_after,
                    )
                except Exception:
                    # Email failure must not lose the 48h window; the trigger
                    # still promotes after deliver_after (at-least-once, NFR-07).
                    pass

                await write_audit(
                    db, "delivery_pending_confirmation",
                    user_id=schedule.user_id, resource_id=trigger.id,
                )
                await db.commit()
            else:
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


@celery_app.task(name="app.worker.tasks.checkin_tasks.process_pending_triggers")
def process_pending_triggers():
    asyncio.run(_process_pending_triggers())


async def _process_pending_triggers():
    """Promote pending_confirmation triggers whose 48h window elapsed (B8.2)."""
    from sqlalchemy import select, and_
    from app.db.session import AsyncSessionLocal
    from app.db.models.checkin import ReleaseTrigger, TriggerStatus
    from app.core.audit import write_audit

    now = datetime.now(timezone.utc)
    promoted: list[str] = []

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ReleaseTrigger).where(
                and_(
                    ReleaseTrigger.status == TriggerStatus.pending_confirmation,
                    ReleaseTrigger.deliver_after.isnot(None),
                    ReleaseTrigger.deliver_after <= now,
                )
            )
        )
        triggers = result.scalars().all()

        for trigger in triggers:
            trigger.status = TriggerStatus.processing
            await write_audit(db, "delivery_triggered", user_id=trigger.user_id, resource_id=trigger.id)
            promoted.append(str(trigger.id))
        await db.commit()

    from app.worker.tasks.delivery_tasks import execute_delivery
    for trigger_id in promoted:
        execute_delivery.apply_async(args=[trigger_id])


@celery_app.task(name="app.worker.tasks.checkin_tasks.send_grace_period_reminders")
def send_grace_period_reminders():
    asyncio.run(_send_grace_period_reminders())


async def _send_grace_period_reminders():
    """
    B5 / FR-16: per-cycle escalating reminders at grace day 3 and day 7.

    The >= comparison makes the 12h cadence safe: each threshold fires on the
    first run at-or-after it, exactly once per cycle (tracked by
    last_grace_reminder_day, which resets on dispatch/confirm/snooze).
    Thresholds >= grace_period_days are skipped — that day belongs to the
    trigger itself, not a reminder.
    """
    from sqlalchemy import select, and_
    from app.db.session import AsyncSessionLocal
    from app.db.models.user import User, UserStatus
    from app.db.models.checkin import CheckInSchedule, CheckInEvent, TokenType, EventStatus
    from app.core.email import send_grace_period_reminder
    from app.config import get_settings

    cfg = get_settings()
    now = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(CheckInSchedule)
            .join(User, User.id == CheckInSchedule.user_id)
            .where(
                and_(
                    CheckInSchedule.last_dispatched_at.isnot(None),
                    CheckInSchedule.is_paused.is_(False),
                    User.status == UserStatus.active,
                    User.email_verified.is_(True),
                )
            )
        )
        schedules = result.scalars().all()

        for schedule in schedules:
            dispatched_at = _as_utc(schedule.last_dispatched_at)
            if not dispatched_at:
                continue

            grace_deadline = dispatched_at + timedelta(days=schedule.grace_period_days)
            days_into_grace = (now - dispatched_at).days

            confirmed_at = _as_utc(schedule.last_confirmed_at)
            if confirmed_at and confirmed_at >= dispatched_at:
                continue
            if now >= grace_deadline:
                continue

            # Highest eligible threshold not yet sent this cycle.
            due_threshold = None
            for threshold in GRACE_REMINDER_THRESHOLDS:
                if threshold >= schedule.grace_period_days:
                    continue
                if days_into_grace >= threshold and (
                    schedule.last_grace_reminder_day is None
                    or schedule.last_grace_reminder_day < threshold
                ):
                    due_threshold = threshold
            if due_threshold is None:
                continue

            days_remaining = max((grace_deadline - now).days, 0)

            user = await db.get(User, schedule.user_id)
            if not user:
                continue

            # Send first; only persist the token/state on success.
            token_value = secrets.token_urlsafe(64)
            confirm_url = f"{cfg.base_url}/checkin/confirm?token={token_value}"
            try:
                send_grace_period_reminder(to=user.email, days_remaining=days_remaining, confirm_url=confirm_url)
            except Exception:
                continue

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

            schedule.last_grace_reminder_day = due_threshold
            schedule.grace_reminder_sent_at = now
            await db.commit()
