"""
SQLAlchemy ORM model for delivery events.
"""

import uuid
import enum
from datetime import datetime
from sqlalchemy import String, DateTime, Enum as SAEnum, ForeignKey, Integer, Text
from sqlalchemy.orm import mapped_column, MappedColumn, relationship
from app.db.base import Base


class DeliveryStatus(str, enum.Enum):
    pending = "pending"
    sent = "sent"
    bounced = "bounced"
    failed = "failed"
    opened = "opened"


class DeliveryEvent(Base):
    __tablename__ = "delivery_events"

    id: MappedColumn[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    release_trigger_id: MappedColumn[uuid.UUID] = mapped_column(ForeignKey("release_triggers.id"), index=True)
    capsule_recipient_id: MappedColumn[uuid.UUID] = mapped_column(ForeignKey("capsule_recipients.id"))
    sent_at: MappedColumn[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivery_status: MappedColumn[DeliveryStatus] = mapped_column(SAEnum(DeliveryStatus), default=DeliveryStatus.pending)
    resend_message_id: MappedColumn[str | None] = mapped_column(String(255), nullable=True)
    attempts: MappedColumn[int] = mapped_column(Integer, default=0)
    last_attempt_at: MappedColumn[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_detail: MappedColumn[str | None] = mapped_column(Text, nullable=True)

    release_trigger = relationship("ReleaseTrigger", back_populates="delivery_events")
    capsule_recipient = relationship("CapsuleRecipient", back_populates="delivery_events")
