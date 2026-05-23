"""
Audit log helper — caller is responsible for committing the session.
"""

from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.audit import AuditLog


async def write_audit(
    db: AsyncSession,
    event_type: str,
    user_id=None,
    resource_type: str | None = None,
    resource_id=None,
    description: str | None = None,
    ip_address: str | None = None,
    meta: dict | None = None,
) -> None:
    log = AuditLog(
        user_id=user_id,
        event_type=event_type,
        resource_type=resource_type,
        resource_id=resource_id,
        description=description,
        ip_address=ip_address,
        created_at=datetime.now(timezone.utc),
        meta=meta,
    )
    db.add(log)
