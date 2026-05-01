"""
SQLAlchemy ORM model for the append-only audit log.
"""

import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Text
from sqlalchemy.orm import mapped_column, MappedColumn
from sqlalchemy.dialects.postgresql import JSONB
from app.db.base import Base


class AuditLog(Base):
    """
    Append-only audit trail. No UPDATE or DELETE operations permitted on this table.
    user_id is nullable to support system-level events.
    """
    __tablename__ = "audit_logs"

    id: MappedColumn[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: MappedColumn[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    actor_id: MappedColumn[uuid.UUID | None] = mapped_column(nullable=True)
    event_type: MappedColumn[str] = mapped_column(String(64), nullable=False)
    resource_type: MappedColumn[str | None] = mapped_column(String(64), nullable=True)
    resource_id: MappedColumn[uuid.UUID | None] = mapped_column(nullable=True)
    description: MappedColumn[str | None] = mapped_column(Text, nullable=True)
    ip_address: MappedColumn[str | None] = mapped_column(String(45), nullable=True)
    created_at: MappedColumn[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    meta: MappedColumn[dict | None] = mapped_column(JSONB, nullable=True)
