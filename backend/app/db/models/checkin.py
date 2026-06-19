"""
SQLAlchemy ORM models for check-in schedules, events, and release triggers.
"""

import uuid
import enum
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Enum as SAEnum, ForeignKey, Integer, Text
from sqlalchemy.orm import mapped_column, MappedColumn, relationship
from sqlalchemy.dialects.postgresql import JSONB
from app.db.base import Base, TimestampMixin


class TokenType(str, enum.Enum):
    confirm = "confirm"
    snooze_7 = "snooze_7"
    snooze_14 = "snooze_14"
    snooze_30 = "snooze_30"
    emergency_pause = "emergency_pause"


class EventStatus(str, enum.Enum):
    pending = "pending"
    used = "used"
    expired = "expired"


class TriggerReason(str, enum.Enum):
    checkin_missed = "checkin_missed"
    emergency_pause_timeout = "emergency_pause_timeout"
    manual = "manual"


class TriggerStatus(str, enum.Enum):
    # 48h emergency-contact window (FR-23/24): trigger created but delivery
    # deferred until deliver_after; promoted to processing by beat task.
    pending_confirmation = "pending_confirmation"
    processing = "processing"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"
    # Terminal: emergency contact used the pause link during the 48h window.
    paused_cancelled = "paused_cancelled"


class CheckInSchedule(Base, TimestampMixin):
    __tablename__ = "checkin_schedules"

    id: MappedColumn[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: MappedColumn[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    interval_days: MappedColumn[int] = mapped_column(Integer, nullable=False)
    grace_period_days: MappedColumn[int] = mapped_column(Integer, nullable=False)
    next_dispatch_at: MappedColumn[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    last_dispatched_at: MappedColumn[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_confirmed_at: MappedColumn[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    snooze_count: MappedColumn[int] = mapped_column(Integer, default=0)
    snooze_limit: MappedColumn[int] = mapped_column(Integer, default=2)
    is_paused: MappedColumn[bool] = mapped_column(Boolean, default=False)
    pause_count: MappedColumn[int] = mapped_column(Integer, default=0)
    grace_reminder_sent_at: MappedColumn[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Grace-day number (3 or 7) of the last reminder sent THIS cycle (FR-16).
    # Reset to None on confirm/snooze and on new dispatch.
    last_grace_reminder_day: MappedColumn[int | None] = mapped_column(Integer, nullable=True)

    user = relationship("User", back_populates="checkin_schedule")
    events = relationship("CheckInEvent", back_populates="schedule", cascade="all, delete-orphan")


class CheckInEvent(Base):
    __tablename__ = "checkin_events"

    id: MappedColumn[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: MappedColumn[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    schedule_id: MappedColumn[uuid.UUID] = mapped_column(ForeignKey("checkin_schedules.id", ondelete="CASCADE"))
    # NOTE (NFR-12 deviation, accepted): check-in tokens are single-use rows in
    # the database — token state (pending/used/expired) lives here, not in a
    # signed/stateless token. See README for rationale.
    token: MappedColumn[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    token_type: MappedColumn[TokenType] = mapped_column(SAEnum(TokenType), nullable=False)
    status: MappedColumn[EventStatus] = mapped_column(SAEnum(EventStatus), default=EventStatus.pending)
    expires_at: MappedColumn[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sent_at: MappedColumn[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    used_at: MappedColumn[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    click_ip: MappedColumn[str | None] = mapped_column(String(45), nullable=True)
    click_user_agent: MappedColumn[str | None] = mapped_column(Text, nullable=True)

    schedule = relationship("CheckInSchedule", back_populates="events")


class ReleaseTrigger(Base):
    __tablename__ = "release_triggers"

    id: MappedColumn[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: MappedColumn[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    triggered_at: MappedColumn[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reason: MappedColumn[TriggerReason] = mapped_column(SAEnum(TriggerReason), nullable=False)
    status: MappedColumn[TriggerStatus] = mapped_column(SAEnum(TriggerStatus), default=TriggerStatus.processing)
    # Earliest time delivery may run (set to now+48h for pending_confirmation).
    deliver_after: MappedColumn[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pause_count: MappedColumn[int] = mapped_column(Integer, default=0)
    meta: MappedColumn[dict | None] = mapped_column(JSONB, nullable=True)

    delivery_events = relationship("DeliveryEvent", back_populates="release_trigger")
