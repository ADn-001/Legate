"""
Activity / audit log endpoint.
"""

import uuid
from datetime import datetime
from pydantic import BaseModel

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db_session
from app.dependencies import get_current_verified_user
from app.db.models.audit import AuditLog

router = APIRouter()


class ActivityEntry(BaseModel):
    id: uuid.UUID
    event_type: str
    resource_type: str | None
    resource_id: uuid.UUID | None
    description: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[ActivityEntry])
async def list_activity(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_verified_user),
):
    offset = (page - 1) * per_page
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.user_id == current_user.id)
        .order_by(AuditLog.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    return list(result.scalars().all())
