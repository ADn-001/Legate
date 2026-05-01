"""
SQLAlchemy ORM models for capsules, capsule recipients, and media attachments.
"""

import uuid
import enum
from datetime import datetime, date
from sqlalchemy import String, DateTime, Date, Enum as SAEnum, ForeignKey, Integer, LargeBinary, Text
from sqlalchemy.orm import mapped_column, MappedColumn, relationship
from app.db.base import Base, TimestampMixin


class CapsuleStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    pending_deletion = "pending_deletion"
    deleted = "deleted"
    delivered = "delivered"


class RecipientStatus(str, enum.Enum):
    pending = "pending"
    queued = "queued"
    sent = "sent"
    failed = "failed"


class MediaType(str, enum.Enum):
    photo = "photo"
    video = "video"


class MediaStatus(str, enum.Enum):
    uploading = "uploading"
    ready = "ready"
    failed = "failed"
    deleted = "deleted"


class Capsule(Base, TimestampMixin):
    __tablename__ = "capsules"

    id: MappedColumn[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: MappedColumn[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: MappedColumn[str] = mapped_column(String(255), nullable=False)
    status: MappedColumn[CapsuleStatus] = mapped_column(SAEnum(CapsuleStatus), default=CapsuleStatus.draft)
    storage_object_path: MappedColumn[str | None] = mapped_column(Text, nullable=True)
    cipher_iv: MappedColumn[bytes | None] = mapped_column(LargeBinary, nullable=True)
    content_hash: MappedColumn[str | None] = mapped_column(String(64), nullable=True)
    scheduled_delivery_date: MappedColumn[date | None] = mapped_column(Date, nullable=True)
    delivery_order: MappedColumn[int] = mapped_column(Integer, default=0)
    auto_saved_at: MappedColumn[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="capsules")
    recipients = relationship("CapsuleRecipient", back_populates="capsule", cascade="all, delete-orphan")
    media_attachments = relationship("MediaAttachment", back_populates="capsule", cascade="all, delete-orphan")


class CapsuleRecipient(Base):
    __tablename__ = "capsule_recipients"

    id: MappedColumn[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    capsule_id: MappedColumn[uuid.UUID] = mapped_column(ForeignKey("capsules.id", ondelete="CASCADE"))
    beneficiary_id: MappedColumn[uuid.UUID] = mapped_column(ForeignKey("beneficiaries.id", ondelete="RESTRICT"))
    is_primary: MappedColumn[bool] = mapped_column(default=False)
    status: MappedColumn[RecipientStatus] = mapped_column(SAEnum(RecipientStatus), default=RecipientStatus.pending)
    delivered_at: MappedColumn[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    capsule = relationship("Capsule", back_populates="recipients")
    beneficiary = relationship("Beneficiary")
    delivery_events = relationship("DeliveryEvent", back_populates="capsule_recipient")


class MediaAttachment(Base):
    __tablename__ = "media_attachments"

    id: MappedColumn[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    capsule_id: MappedColumn[uuid.UUID] = mapped_column(ForeignKey("capsules.id", ondelete="CASCADE"))
    type: MappedColumn[MediaType] = mapped_column(SAEnum(MediaType), nullable=False)
    original_name: MappedColumn[str] = mapped_column(String(255), nullable=False)
    mime_type: MappedColumn[str] = mapped_column(String(64), nullable=False)
    size_bytes: MappedColumn[int] = mapped_column(nullable=False)
    storage_object_path: MappedColumn[str] = mapped_column(Text, nullable=False)
    cipher_iv: MappedColumn[bytes] = mapped_column(LargeBinary, nullable=False)
    thumbnail_storage_path: MappedColumn[str | None] = mapped_column(Text, nullable=True)
    video_duration_seconds: MappedColumn[int | None] = mapped_column(Integer, nullable=True)
    status: MappedColumn[MediaStatus] = mapped_column(SAEnum(MediaStatus), default=MediaStatus.uploading)
    created_at: MappedColumn[datetime] = mapped_column(DateTime(timezone=True))

    capsule = relationship("Capsule", back_populates="media_attachments")
