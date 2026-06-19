"""
SQLAlchemy ORM model for users and user settings.
"""

import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Enum as SAEnum, ForeignKey, Integer
from sqlalchemy.orm import mapped_column, MappedColumn, relationship
from app.db.base import Base, TimestampMixin
import enum


class UserStatus(str, enum.Enum):
    active = "active"
    suspended = "suspended"
    memorialized = "memorialized"
    # GDPR erasure requested; full purge task scheduled (FR-05, ≤72h).
    pending_deletion = "pending_deletion"
    deleted = "deleted"


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: MappedColumn[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    supabase_uid: MappedColumn[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    email: MappedColumn[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: MappedColumn[str | None] = mapped_column(String(255), nullable=True)
    email_verified: MappedColumn[bool] = mapped_column(Boolean, default=False)
    full_name: MappedColumn[str | None] = mapped_column(String(255), nullable=True)
    phone: MappedColumn[str | None] = mapped_column(String(32), nullable=True)
    status: MappedColumn[UserStatus] = mapped_column(SAEnum(UserStatus), default=UserStatus.active)
    erasure_requested_at: MappedColumn[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_at: MappedColumn[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    settings = relationship("UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")
    encryption_key = relationship("EncryptionKey", back_populates="user", uselist=False, cascade="all, delete-orphan")
    beneficiaries = relationship("Beneficiary", back_populates="user", cascade="all, delete-orphan")
    capsules = relationship("Capsule", back_populates="user", cascade="all, delete-orphan")
    checkin_schedule = relationship("CheckInSchedule", back_populates="user", uselist=False, cascade="all, delete-orphan")


class UserSettings(Base, TimestampMixin):
    __tablename__ = "user_settings"

    id: MappedColumn[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: MappedColumn[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    check_in_interval_days: MappedColumn[int] = mapped_column(Integer, default=30)
    grace_period_days: MappedColumn[int] = mapped_column(Integer, default=14)
    snooze_count_remaining: MappedColumn[int] = mapped_column(Integer, default=2)
    preferred_language: MappedColumn[str] = mapped_column(String(8), default="en")
    needs_onboarding: MappedColumn[bool] = mapped_column(Boolean, default=True)
    last_check_in_at: MappedColumn[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_check_in_at: MappedColumn[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="settings")


class EncryptionKey(Base):
    __tablename__ = "encryption_keys"

    id: MappedColumn[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: MappedColumn[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    encrypted_cek: MappedColumn[bytes] = mapped_column(nullable=False)
    cek_iv: MappedColumn[bytes] = mapped_column(nullable=False)
    pbkdf2_salt: MappedColumn[bytes] = mapped_column(nullable=False)
    pbkdf2_iterations: MappedColumn[int] = mapped_column(Integer, default=100000)
    delivery_encrypted_cek: MappedColumn[bytes | None] = mapped_column(nullable=True)
    delivery_cek_iv: MappedColumn[bytes | None] = mapped_column(nullable=True)
    recovery_phrase_hash: MappedColumn[str | None] = mapped_column(String(255), nullable=True)
    recovery_encrypted_cek: MappedColumn[bytes | None] = mapped_column(nullable=True)
    recovery_cek_iv: MappedColumn[bytes | None] = mapped_column(nullable=True)
    recovery_salt: MappedColumn[bytes | None] = mapped_column(nullable=True)
    created_at: MappedColumn[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: MappedColumn[datetime] = mapped_column(DateTime(timezone=True))

    user = relationship("User", back_populates="encryption_key")
