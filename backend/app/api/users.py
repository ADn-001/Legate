"""
User account management routes.
"""

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.dependencies import get_current_verified_user
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService

router = APIRouter()


class DeleteAccountRequest(BaseModel):
    confirmation: str
    password: str

    @field_validator("confirmation")
    @classmethod
    def must_be_delete(cls, v: str) -> str:
        if v != "DELETE":
            raise ValueError('Confirmation must be "DELETE"')
        return v


class UpdateUserRequest(BaseModel):
    needs_onboarding: bool | None = None


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(current_user=Depends(get_current_verified_user)):
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        email_verified=current_user.email_verified,
        status=current_user.status,
        created_at=current_user.created_at,
        needs_onboarding=current_user.settings.needs_onboarding if current_user.settings else True,
    )


@router.patch("/me", response_model=UserResponse)
async def update_user_profile(
    body: UpdateUserRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_verified_user),
):
    if body.needs_onboarding is not None and current_user.settings:
        current_user.settings.needs_onboarding = body.needs_onboarding
        await db.commit()
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        email_verified=current_user.email_verified,
        status=current_user.status,
        created_at=current_user.created_at,
        needs_onboarding=current_user.settings.needs_onboarding if current_user.settings else True,
    )


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    body: DeleteAccountRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_verified_user),
):
    svc = AuthService(db)
    await svc.delete_account(current_user, body.password)
