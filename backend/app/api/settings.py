"""
User settings and storage configuration routes.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.config import get_settings
from app.db.session import get_db_session
from app.dependencies import get_current_verified_user, require_active_user
from app.db.models.checkin import CheckInSchedule
from app.db.models.capsule import MediaAttachment, Capsule
from app.db.models.user import UserSettings
from app.schemas.checkin import CheckInSettingsUpdate, CheckInSettingsResponse

router = APIRouter()


class UserSettingsPatch(BaseModel):
    """T5 (Phase 4): patch general user settings — wizard step, onboarding flag."""
    setup_step: Optional[int] = Field(None, ge=1, le=4)
    needs_onboarding: Optional[bool] = None


class UserSettingsResponse(BaseModel):
    setup_step: Optional[int] = None
    needs_onboarding: bool

    model_config = {"from_attributes": True}


@router.get("/", response_model=UserSettingsResponse)
async def get_user_settings(
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_verified_user),
):
    settings_row = current_user.settings
    if not settings_row:
        return UserSettingsResponse(setup_step=None, needs_onboarding=True)
    return UserSettingsResponse.model_validate(settings_row)


@router.patch("/", response_model=UserSettingsResponse)
async def patch_user_settings(
    body: UserSettingsPatch,
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(require_active_user),
):
    """T5 (Phase 4): persist wizard step + onboarding flag."""
    settings_row: UserSettings | None = current_user.settings
    if not settings_row:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Settings not found")

    if body.setup_step is not None:
        settings_row.setup_step = body.setup_step
    if body.needs_onboarding is not None:
        settings_row.needs_onboarding = body.needs_onboarding

    await db.commit()
    return UserSettingsResponse.model_validate(settings_row)


class StorageCapsuleBreakdown(BaseModel):
    capsule_id: uuid.UUID
    title: str
    bytes: int


class StorageUsageResponse(BaseModel):
    total_bytes: int
    # FR-36: quota for the progress bar.
    limit_bytes: int
    by_capsule: list[StorageCapsuleBreakdown]


def _with_demo_flag(schedule: CheckInSchedule) -> CheckInSettingsResponse:
    """Build the response model and stamp the server's global demo_mode flag
    onto it — demo_mode isn't a column on the schedule, it's process config."""
    response = CheckInSettingsResponse.model_validate(schedule)
    response.demo_mode = get_settings().demo_mode
    return response


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
        raise HTTPException(status_code=404, detail="Schedule not found")
    return _with_demo_flag(schedule)


@router.patch("/checkin", response_model=CheckInSettingsResponse)
async def update_checkin_settings(
    body: CheckInSettingsUpdate,
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(require_active_user),
):
    cfg = get_settings()

    result = await db.execute(
        select(CheckInSchedule).where(CheckInSchedule.user_id == current_user.id)
    )
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # B4: minute overrides (and clearing them) are demo-mode-only, enforced
    # server-side — not just hidden in the UI. Checked before any mutation
    # so a rejected request never partially applies.
    wants_minutes = (
        body.check_interval_minutes is not None
        or body.grace_period_minutes is not None
        or body.emergency_confirm_minutes is not None
        or body.clear_minute_overrides
    )
    if wants_minutes and not cfg.demo_mode:
        raise HTTPException(status_code=403, detail="Demo mode is disabled")

    if body.clear_minute_overrides:
        schedule.check_interval_minutes = None
        schedule.grace_period_minutes = None
        schedule.emergency_confirm_minutes = None
        # Back to day-based scheduling: recompute next_dispatch_at from
        # interval_days using the same anchor logic as the days branch below.
        if schedule.last_confirmed_at:
            base = schedule.last_confirmed_at
            if base.tzinfo is None:
                base = base.replace(tzinfo=timezone.utc)
            schedule.next_dispatch_at = base + timedelta(days=schedule.interval_days)
        else:
            schedule.next_dispatch_at = datetime.now(timezone.utc) + timedelta(days=schedule.interval_days)

    if body.interval_days is not None:
        old_interval = schedule.interval_days
        schedule.interval_days = body.interval_days
        # Only recompute from days when there's no active minute override —
        # a minute override always takes precedence (scheduling.interval_delta),
        # so changing interval_days shouldn't disturb an in-flight demo cycle.
        if body.interval_days != old_interval and not schedule.check_interval_minutes:
            if schedule.last_confirmed_at:
                base = schedule.last_confirmed_at
                if base.tzinfo is None:
                    base = base.replace(tzinfo=timezone.utc)
                schedule.next_dispatch_at = base + timedelta(days=body.interval_days)
            else:
                # B15: never confirmed yet — anchor the new interval to now,
                # not to a missing last_confirmed_at.
                schedule.next_dispatch_at = datetime.now(timezone.utc) + timedelta(days=body.interval_days)

    if body.grace_period_days is not None:
        schedule.grace_period_days = body.grace_period_days

    if body.check_interval_minutes is not None:
        schedule.check_interval_minutes = body.check_interval_minutes
        # Same anchor logic as the days branch above, but in minutes — this
        # is what actually arms the demo cycle.
        if schedule.last_confirmed_at:
            base = schedule.last_confirmed_at
            if base.tzinfo is None:
                base = base.replace(tzinfo=timezone.utc)
            schedule.next_dispatch_at = base + timedelta(minutes=body.check_interval_minutes)
        else:
            schedule.next_dispatch_at = datetime.now(timezone.utc) + timedelta(minutes=body.check_interval_minutes)

    if body.grace_period_minutes is not None:
        schedule.grace_period_minutes = body.grace_period_minutes

    if body.emergency_confirm_minutes is not None:
        # No next_dispatch_at recompute needed — this only affects a future
        # pending_confirmation trigger's deliver_after, not dispatch timing.
        schedule.emergency_confirm_minutes = body.emergency_confirm_minutes

    await db.commit()
    return _with_demo_flag(schedule)


@router.get("/storage", response_model=StorageUsageResponse)
async def get_storage_usage(
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_verified_user),
):
    cfg = get_settings()

    # Get all user capsules
    capsule_result = await db.execute(
        select(Capsule).where(Capsule.user_id == current_user.id)
    )
    capsules = {c.id: c for c in capsule_result.scalars().all()}

    # Aggregate media size_bytes by capsule_id
    media_sizes: dict = {}
    if capsules:
        agg_result = await db.execute(
            select(MediaAttachment.capsule_id, func.sum(MediaAttachment.size_bytes))
            .where(MediaAttachment.capsule_id.in_(list(capsules.keys())))
            .group_by(MediaAttachment.capsule_id)
        )
        media_sizes = {capsule_id: size or 0 for capsule_id, size in agg_result.all()}

    # B16: include the encrypted text-content blob sizes, not just media.
    by_capsule = []
    total = 0
    for capsule_id, cap in capsules.items():
        size = media_sizes.get(capsule_id, 0) + (cap.content_size_bytes or 0)
        if size == 0:
            continue
        total += size
        by_capsule.append(StorageCapsuleBreakdown(
            capsule_id=capsule_id,
            title=cap.title,
            bytes=size,
        ))

    return StorageUsageResponse(
        total_bytes=total,
        limit_bytes=cfg.storage_quota_bytes,
        by_capsule=by_capsule,
    )
