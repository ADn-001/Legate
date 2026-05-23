"""
Authentication routes: signup, login, logout, token refresh, email verification.
"""

import base64

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db_session
from app.db.models.user import EncryptionKey
from app.dependencies import get_current_user, get_current_verified_user
from app.schemas.auth import (
    SignupRequest, LoginRequest, TokenResponse,
    VerifyEmailRequest, RefreshRequest,
    EncryptionKeyResponse, DeliveryWrappingKeyResponse,
)
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService

router = APIRouter()


@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(body: SignupRequest, db: AsyncSession = Depends(get_db_session)):
    svc = AuthService(db)
    result = await svc.signup(
        email=body.email,
        password=body.password,
        encrypted_cek=body.encrypted_cek,
        cek_iv=body.cek_iv,
        pbkdf2_salt=body.pbkdf2_salt,
        delivery_encrypted_cek=body.delivery_encrypted_cek,
        delivery_cek_iv=body.delivery_cek_iv,
    )
    return result


@router.post("/verify-email", status_code=status.HTTP_200_OK, response_model=TokenResponse)
async def verify_email(body: VerifyEmailRequest, db: AsyncSession = Depends(get_db_session)):
    svc = AuthService(db)
    return await svc.verify_email(body.email, body.otp)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db_session)):
    svc = AuthService(db)
    return await svc.login(body.email, body.password)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest, db: AsyncSession = Depends(get_db_session)):
    svc = AuthService(db)
    return await svc.refresh(body.refresh_token)


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(body: RefreshRequest, db: AsyncSession = Depends(get_db_session)):
    svc = AuthService(db)
    await svc.logout()
    return {"message": "Logged out"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user=Depends(get_current_verified_user)):
    return current_user


@router.get("/me/encryption-key", response_model=EncryptionKeyResponse)
async def get_encryption_key(
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_verified_user),
):
    result = await db.execute(select(EncryptionKey).where(EncryptionKey.user_id == current_user.id))
    key = result.scalar_one_or_none()
    if not key:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Encryption key not found")
    return EncryptionKeyResponse(
        encrypted_cek=base64.b64encode(key.encrypted_cek).decode(),
        cek_iv=base64.b64encode(key.cek_iv).decode(),
        pbkdf2_salt=base64.b64encode(key.pbkdf2_salt).decode(),
        pbkdf2_iterations=key.pbkdf2_iterations,
    )


@router.get("/me/delivery-wrapping-key", response_model=DeliveryWrappingKeyResponse)
async def get_delivery_wrapping_key(
    current_user=Depends(get_current_verified_user),
):
    import hmac, hashlib
    from app.config import get_settings
    cfg = get_settings()
    key = hmac.new(
        cfg.delivery_secret.encode(),
        str(current_user.id).encode(),
        hashlib.sha256,
    ).hexdigest()
    return DeliveryWrappingKeyResponse(wrapping_key=key)
