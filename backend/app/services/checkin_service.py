"""Business logic for check-in token validation and schedule management."""

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.audit import write_audit
from app.db.models.checkin import CheckInEvent, CheckInSchedule, EventStatus, TokenType, ReleaseTrigger, TriggerStatus


class CheckInService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _validate_token(self, token: str) -> CheckInEvent:
        result = await self.db.execute(
            select(CheckInEvent).where(CheckInEvent.token == token)
        )
        event = result.scalar_one_or_none()
        if not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token not found")
        now = datetime.now(timezone.utc)
        if event.expires_at.replace(tzinfo=timezone.utc) < now:
            event.status = EventStatus.expired
            await self.db.commit()
            raise HTTPException(status_code=410, detail="Token expired")
        if event.status == EventStatus.used:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Token already used")
        return event

    async def confirm(self, token: str, ip: str | None, user_agent: str | None) -> dict:
        event = await self._validate_token(token)
        if event.token_type != TokenType.confirm:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token type")

        now = datetime.now(timezone.utc)
        event.status = EventStatus.used
        event.used_at = now
        event.click_ip = ip
        event.click_user_agent = user_agent

        result = await self.db.execute(
            select(CheckInSchedule).where(CheckInSchedule.id == event.schedule_id)
        )
        schedule = result.scalar_one_or_none()
        if schedule:
            schedule.last_confirmed_at = now
            schedule.next_dispatch_at = now + timedelta(days=schedule.interval_days)
            schedule.snooze_count = 0

        await write_audit(self.db, "checkin_confirmed", user_id=event.user_id)
        await self.db.commit()

        next_due = schedule.next_dispatch_at.isoformat() if schedule else None
        return {"status": "confirmed", "next_due": next_due}

    async def snooze(self, token: str, days: int) -> dict:
        event = await self._validate_token(token)

        type_to_days = {
            TokenType.snooze_7: 7,
            TokenType.snooze_14: 14,
            TokenType.snooze_30: 30,
        }
        if event.token_type not in type_to_days:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token type for snooze")
        if type_to_days[event.token_type] != days:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Days mismatch for token type")

        result = await self.db.execute(
            select(CheckInSchedule).where(CheckInSchedule.id == event.schedule_id)
        )
        schedule = result.scalar_one_or_none()
        if not schedule:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")
        if schedule.snooze_count >= schedule.snooze_limit:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Snooze limit reached")

        now = datetime.now(timezone.utc)
        event.status = EventStatus.used
        event.used_at = now

        base = schedule.next_dispatch_at or now
        if base.tzinfo is None:
            base = base.replace(tzinfo=timezone.utc)
        schedule.next_dispatch_at = base + timedelta(days=days)
        schedule.snooze_count += 1

        await write_audit(self.db, "checkin_snoozed", user_id=event.user_id)
        await self.db.commit()
        return {"status": "snoozed", "days": days}

    async def emergency_pause(self, token: str) -> dict:
        event = await self._validate_token(token)
        if event.token_type != TokenType.emergency_pause:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token type")

        result = await self.db.execute(
            select(CheckInSchedule).where(CheckInSchedule.id == event.schedule_id)
        )
        schedule = result.scalar_one_or_none()
        if not schedule:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")
        if schedule.pause_count >= 2:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Pause limit reached (maximum 2)")

        now = datetime.now(timezone.utc)
        event.status = EventStatus.used
        event.used_at = now
        schedule.is_paused = True
        schedule.pause_count += 1

        base = schedule.next_dispatch_at or now
        if base.tzinfo is None:
            base = base.replace(tzinfo=timezone.utc)
        schedule.next_dispatch_at = base + timedelta(days=7)

        # Cancel any active release trigger for this user
        trigger_result = await self.db.execute(
            select(ReleaseTrigger).where(
                and_(
                    ReleaseTrigger.user_id == schedule.user_id,
                    ReleaseTrigger.status == TriggerStatus.processing,
                )
            )
        )
        trigger = trigger_result.scalar_one_or_none()
        if trigger:
            trigger.status = TriggerStatus.cancelled
            trigger.pause_count = (trigger.pause_count or 0) + 1

        await write_audit(self.db, "trigger_cancelled", user_id=event.user_id)
        await self.db.commit()
        return {"status": "paused"}
