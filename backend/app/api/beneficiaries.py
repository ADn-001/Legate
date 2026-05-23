"""
Beneficiary management routes.
"""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.dependencies import get_current_verified_user
from app.schemas.beneficiary import BeneficiaryCreate, BeneficiaryUpdate, BeneficiaryResponse
from app.services.beneficiary_service import BeneficiaryService

router = APIRouter()


@router.get("/", response_model=list[BeneficiaryResponse])
async def list_beneficiaries(
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_verified_user),
):
    svc = BeneficiaryService(db)
    return await svc.list_for_user(current_user.id)


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=BeneficiaryResponse)
async def add_beneficiary(
    body: BeneficiaryCreate,
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_verified_user),
):
    svc = BeneficiaryService(db)
    return await svc.create(
        user_id=current_user.id,
        full_name=body.full_name,
        email=body.email,
        relationship=body.relationship,
        is_emergency_contact=body.is_emergency_contact,
        nominator_name=current_user.full_name or current_user.email,
    )


@router.patch("/{beneficiary_id}", response_model=BeneficiaryResponse)
async def update_beneficiary(
    beneficiary_id: uuid.UUID,
    body: BeneficiaryUpdate,
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_verified_user),
):
    svc = BeneficiaryService(db)
    return await svc.update(
        beneficiary_id=beneficiary_id,
        user_id=current_user.id,
        nominator_name=current_user.full_name or current_user.email,
        **body.model_dump(exclude_none=True),
    )


@router.delete("/{beneficiary_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_beneficiary(
    beneficiary_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_verified_user),
):
    svc = BeneficiaryService(db)
    await svc.remove(beneficiary_id=beneficiary_id, user_id=current_user.id)
