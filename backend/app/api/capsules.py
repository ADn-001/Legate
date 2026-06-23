"""
Capsule CRUD routes.
"""

import uuid
from pydantic import BaseModel

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.dependencies import get_current_verified_user
from app.schemas.capsule import (
    CapsuleCreate,
    CapsuleUpdate,
    CapsuleResponse,
    CapsuleContentResponse,
    CapsuleUploadUrlResponse,
    CapsuleUploadContentResponse,
)
from app.services.capsule_service import CapsuleService

router = APIRouter()


class CapsuleCreateResponse(BaseModel):
    id: uuid.UUID
    upload_url: str


@router.get("/", response_model=list[CapsuleResponse])
async def list_capsules(
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_verified_user),
):
    svc = CapsuleService(db)
    return await svc.list_for_user(current_user.id)


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=CapsuleCreateResponse)
async def create_capsule(
    body: CapsuleCreate,
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_verified_user),
):
    svc = CapsuleService(db)
    result = await svc.create(
        user_id=current_user.id,
        title=body.title,
        beneficiary_id=body.beneficiary_id,
        cipher_iv=body.cipher_iv,
        content_hash=body.content_hash,
        content_size_bytes=body.content_size_bytes,
    )
    return CapsuleCreateResponse(**result)


@router.get("/{capsule_id}", response_model=CapsuleResponse)
async def get_capsule(
    capsule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_verified_user),
):
    svc = CapsuleService(db)
    return await svc.get_by_id(capsule_id, current_user.id)


@router.patch("/{capsule_id}", response_model=CapsuleResponse)
async def update_capsule(
    capsule_id: uuid.UUID,
    body: CapsuleUpdate,
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_verified_user),
):
    svc = CapsuleService(db)
    return await svc.update(capsule_id, current_user.id, **body.model_dump(exclude_none=True))


@router.get("/{capsule_id}/content", response_model=CapsuleContentResponse)
async def get_capsule_content(
    capsule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_verified_user),
):
    svc = CapsuleService(db)
    return await svc.get_content_url(capsule_id, current_user.id)


@router.post("/{capsule_id}/content", response_model=CapsuleUploadUrlResponse)
async def get_capsule_upload_url(
    capsule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_verified_user),
):
    svc = CapsuleService(db)
    return await svc.get_upload_url(capsule_id, current_user.id)


@router.put("/{capsule_id}/content", response_model=CapsuleUploadContentResponse)
async def upload_capsule_content(
    capsule_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_verified_user),
):
    """Receive the encrypted blob from the browser and upload it to Supabase
    Storage server-side using the service-role key.  Used by the edit flow so
    that the browser never needs a signed upload URL (which can stall due to
    the signed-URL PUT hanging on the existing-object path)."""
    data = await request.body()
    svc = CapsuleService(db)
    return await svc.upload_content(capsule_id, current_user.id, data)


@router.delete("/{capsule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_capsule(
    capsule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_verified_user),
):
    svc = CapsuleService(db)
    await svc.delete(capsule_id, current_user.id)
