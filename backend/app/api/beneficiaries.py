"""
Beneficiary management routes.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.dependencies import get_current_verified_user
from app.schemas.beneficiary import BeneficiaryCreate, BeneficiaryUpdate, BeneficiaryResponse

router = APIRouter()


@router.get("/", response_model=list[BeneficiaryResponse])
async def list_beneficiaries(
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_verified_user),
):
    """List all beneficiaries for the current user."""
    raise NotImplementedError


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=BeneficiaryResponse)
async def add_beneficiary(
    body: BeneficiaryCreate,
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_verified_user),
):
    """Add a new beneficiary and send nomination email."""
    # TODO: delegate to BeneficiaryService.create, send nomination email
    raise NotImplementedError


@router.patch("/{beneficiary_id}", response_model=BeneficiaryResponse)
async def update_beneficiary(
    beneficiary_id: str,
    body: BeneficiaryUpdate,
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_verified_user),
):
    """Update beneficiary details. Re-sends nomination if email changed."""
    raise NotImplementedError


@router.delete("/{beneficiary_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_beneficiary(
    beneficiary_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_verified_user),
):
    """
    Remove a beneficiary.
    Warns if linked capsules will be unassigned.
    Sends removal notification to beneficiary email.
    """
    raise NotImplementedError
