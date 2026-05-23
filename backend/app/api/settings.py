"""
User settings and storage configuration routes.
"""

import uuid
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.session import get_db_session
from app.dependencies import get_current_verified_user
from app.db.models.checkin import CheckInSchedule
from app.db.models.capsule import MediaAttachment, Capsule
from app.schemas.checkin import CheckInSettingsUpdate, CheckInSettingsResponse

router = APIRouter()


class StorageCapsuleBreakdown(BaseModel):
    capsule_id: uuid.UUID
    title: str
    bytes: int


class StorageUsageResponse(BaseModel):
    total_bytes: int
    by_capsule: list[StorageCapsuleBreakdown]


@router.get("/checkin", response_model=CheckInSettingsResponse)
async def get_checkin_settings(
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_verified_user),
):
    result = await db.execute(
        select(CheckInSchedule).where(CheckInSchedule.user_id == current_user.id)
    )
    schedule = result.scalar_one_or_none()
    if not schedule:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Schedule not found")
    return schedule


@router.patch("/checkin", response_model=CheckInSettingsResponse)
async def update_checkin_settings(
    body: CheckInSettingsUpdate,
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_verified_user),
):
    result = await db.execute(
        select(CheckInSchedule).where(CheckInSchedule.user_id == current_user.id)
    )
    schedule = result.scalar_one_or_none()
    if not schedule:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Schedule not found")

    if body.interval_days is not None:
        old_interval = schedule.interval_days
        schedule.interval_days = body.interval_days
        if body.interval_days != old_interval and schedule.last_confirmed_at:
            base = schedule.last_confirmed_at
            if base.tzinfo is None:
                base = base.replace(tzinfo=timezone.utc)
            schedule.next_dispatch_at = base + timedelta(days=body.interval_days)

    if body.grace_period_days is not None:
        schedule.grace_period_days = body.grace_period_days

    await db.commit()
    return schedule


@router.get("/storage", response_model=StorageUsageResponse)
async def get_storage_usage(
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_verified_user),
):
    # Get all user capsules
    capsule_result = await db.execute(
        select(Capsule).where(Capsule.user_id == current_user.id)
    )
    capsules = {c.id: c for c in capsule_result.scalars().all()}

    # Aggregate size_bytes by capsule_id
    agg_result = await db.execute(
        select(MediaAttachment.capsule_id, func.sum(MediaAttachment.size_bytes))
        .where(MediaAttachment.capsule_id.in_(list(capsules.keys())))
        .group_by(MediaAttachment.capsule_id)
    )
    rows = agg_result.all()

    by_capsule = []
    total = 0
    for capsule_id, size in rows:
        total += size or 0
        cap = capsules.get(capsule_id)
        by_capsule.append(StorageCapsuleBreakdown(
            capsule_id=capsule_id,
            title=cap.title if cap else "",
            bytes=size or 0,
        ))

    return StorageUsageResponse(total_bytes=total, by_capsule=by_capsule)
