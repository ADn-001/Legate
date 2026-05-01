"""
User settings and storage configuration routes.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.dependencies import get_current_verified_user
from app.schemas.checkin import CheckInSettingsUpdate, CheckInSettingsResponse

router = APIRouter()


@router.get("/checkin", response_model=CheckInSettingsResponse)
async def get_checkin_settings(
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_verified_user),
):
    """Return the current user's check-in schedule configuration."""
    raise NotImplementedError


@router.patch("/checkin", response_model=CheckInSettingsResponse)
async def update_checkin_settings(
    body: CheckInSettingsUpdate,
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_verified_user),
):
    """
    Update check-in interval and grace period.
    Reducing grace period shows a confirmation — enforced client-side.
    """
    raise NotImplementedError


@router.get("/storage")
async def get_storage_usage(
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_verified_user),
):
    """Return storage usage breakdown per capsule."""
    # TODO: aggregate media_attachments.size_bytes grouped by capsule
    raise NotImplementedError
