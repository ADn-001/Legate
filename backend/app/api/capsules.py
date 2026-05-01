"""
Capsule CRUD routes.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.dependencies import get_current_verified_user
from app.schemas.capsule import CapsuleCreate, CapsuleUpdate, CapsuleResponse

router = APIRouter()


@router.get("/", response_model=list[CapsuleResponse])
async def list_capsules(
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_verified_user),
):
    """List all capsules for the authenticated user."""
    # TODO: delegate to CapsuleService.list_for_user
    raise NotImplementedError


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=CapsuleResponse)
async def create_capsule(
    body: CapsuleCreate,
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_verified_user),
):
    """
    Create capsule metadata record.
    Returns upload URLs for the encrypted content blob.
    """
    # TODO: delegate to CapsuleService.create
    raise NotImplementedError


@router.get("/{capsule_id}", response_model=CapsuleResponse)
async def get_capsule(
    capsule_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_verified_user),
):
    """Get a single capsule by ID."""
    # TODO: delegate to CapsuleService.get_by_id, enforce ownership
    raise NotImplementedError


@router.patch("/{capsule_id}", response_model=CapsuleResponse)
async def update_capsule(
    capsule_id: str,
    body: CapsuleUpdate,
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_verified_user),
):
    """Update capsule metadata (title, storage path, delivery order)."""
    # TODO: delegate to CapsuleService.update
    raise NotImplementedError


@router.delete("/{capsule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_capsule(
    capsule_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_verified_user),
):
    """
    Mark capsule as pending_deletion.
    Enqueues async Supabase Storage purge task (24h).
    """
    # TODO: delegate to CapsuleService.delete, enqueue cleanup_tasks.purge_capsule
    raise NotImplementedError
