"""
User account management routes.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.dependencies import get_current_verified_user

router = APIRouter()


@router.get("/me")
async def get_current_user_profile(current_user=Depends(get_current_verified_user)):
    """Return the authenticated user's profile."""
    # TODO: serialize User model to response schema
    raise NotImplementedError


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_verified_user),
):
    """
    Permanently delete user account (GDPR right to erasure).
    User must confirm with DELETE + password in the request body — enforced at service layer.
    Schedules async purge of all Supabase Storage objects within 72 hours.
    """
    # TODO: delegate to AuthService.delete_account
    # TODO: enqueue cleanup_tasks.purge_user_storage
    raise NotImplementedError
