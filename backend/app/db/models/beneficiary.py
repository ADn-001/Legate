"""
SQLAlchemy ORM model for beneficiaries.
"""

import uuid
import enum
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Enum as SAEnum, ForeignKey
from sqlalchemy.orm import mapped_column, MappedColumn, relationship
from app.db.base import Base, TimestampMixin


class BeneficiaryStatus(str, enum.Enum):
    active = "active"
    pending = "pending"
    removed = "removed"


class Beneficiary(Base, TimestampMixin):
    __tablename__ = "beneficiaries"

    id: MappedColumn[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: MappedColumn[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    full_name: MappedColumn[str] = mapped_column(String(255), nullable=False)
    email: MappedColumn[str] = mapped_column(String(255), nullable=False)
    relationship_type: MappedColumn[str | None] = mapped_column(String(64), nullable=True, name="relationship")
    is_emergency_contact: MappedColumn[bool] = mapped_column(Boolean, default=False)
    status: MappedColumn[BeneficiaryStatus] = mapped_column(SAEnum(BeneficiaryStatus), default=BeneficiaryStatus.pending)
    invited_at: MappedColumn[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    removed_at: MappedColumn[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="beneficiaries")
