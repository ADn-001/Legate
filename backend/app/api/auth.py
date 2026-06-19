"""
Authentication routes: signup, login, logout, token refresh, email verification.
"""

import base64
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db_session
from app.db.models.user import EncryptionKey
from app.dependencies import get_current_user, get_current_verified_user
from app.schemas.auth import (
    SignupRequest, LoginRequest, TokenResponse,
    VerifyEmailRequest, RefreshRequest, ResendOtpRequest,
    EncryptionKeyResponse, DeliveryWrappingKeyResponse,
    SetPrimaryKeyRequest, SetRecoveryKeyRequest,
    RecoveryKeyResponse, ValidateRecoveryPhraseRequest,
    ForgotPasswordRequest, ResetPasswordRequest,
    ResetPasswordDataLossRequest, ChangePasswordRequest,
)
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService

router = APIRouter()


class UpdateDeliveryKeyRequest(BaseModel):
    delivery_encrypted_cek: str   # base64
    delivery_cek_iv: str          # base64


@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(body: SignupRequest, db: AsyncSession = Depends(get_db_session)):
    svc = AuthService(db)
    result = await svc.signup(
        email=body.email,
        password=body.password,
        encrypted_cek=body.encrypted_cek,
        cek_iv=body.cek_iv,
        pbkdf2_salt=body.pbkdf2_salt,
        full_name=body.full_name,
        delivery_encrypted_cek=body.delivery_encrypted_cek,
        delivery_cek_iv=body.delivery_cek_iv,
    )
    return result


@router.post("/verify-email", status_code=status.HTTP_200_OK, response_model=TokenResponse)
async def verify_email(body: VerifyEmailRequest, db: AsyncSession = Depends(get_db_session)):
    svc = AuthService(db)
    return await svc.verify_email(body.email, body.otp)


@router.post("/resend-otp", status_code=status.HTTP_200_OK)
async def resend_otp(body: ResendOtpRequest, db: AsyncSession = Depends(get_db_session)):
    svc = AuthService(db)
    return await svc.resend_otp(body.email)


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
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        email_verified=current_user.email_verified,
        status=current_user.status,
        created_at=current_user.created_at,
        needs_onboarding=current_user.settings.needs_onboarding if current_user.settings else True,
    )


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


@router.patch("/me/encryption-key", status_code=200)
async def update_delivery_key(
    body: UpdateDeliveryKeyRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_verified_user),
):
    result = await db.execute(select(EncryptionKey).where(EncryptionKey.user_id == current_user.id))
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=404, detail="Encryption key not found")
    key.delivery_encrypted_cek = base64.b64decode(body.delivery_encrypted_cek)
    key.delivery_cek_iv = base64.b64decode(body.delivery_cek_iv)
    key.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return {"status": "updated"}


@router.patch("/me/encryption-key/primary", status_code=200)
async def update_primary_key(
    body: SetPrimaryKeyRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_verified_user),
):
    """Re-wrap the primary CEK blob with a new password-derived key.

    Used by the /recover flow (T4.4) and password reset/change (T6), after
    the client has unwrapped the CEK via the old password or the recovery
    phrase and re-wrapped it with the new password.
    """
    result = await db.execute(select(EncryptionKey).where(EncryptionKey.user_id == current_user.id))
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=404, detail="Encryption key not found")
    key.encrypted_cek = base64.b64decode(body.encrypted_cek)
    key.cek_iv = base64.b64decode(body.cek_iv)
    key.pbkdf2_salt = base64.b64decode(body.pbkdf2_salt)
    key.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return {"status": "updated"}


@router.patch("/me/recovery-key", status_code=200)
async def set_recovery_key(
    body: SetRecoveryKeyRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_verified_user),
):
    """Set or regenerate the recovery-phrase-wrapped CEK blob (T4.3/T4.5)."""
    result = await db.execute(select(EncryptionKey).where(EncryptionKey.user_id == current_user.id))
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=404, detail="Encryption key not found")
    key.recovery_encrypted_cek = base64.b64decode(body.recovery_encrypted_cek)
    key.recovery_cek_iv = base64.b64decode(body.recovery_cek_iv)
    key.recovery_salt = base64.b64decode(body.recovery_salt)
    key.recovery_phrase_hash = body.recovery_phrase_hash
    key.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return {"status": "updated"}


@router.post("/me/recovery-key/validate", response_model=RecoveryKeyResponse)
async def validate_recovery_phrase(
    body: ValidateRecoveryPhraseRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_verified_user),
):
    """Validate a recovery phrase against the stored hash and, if it
    matches, return the recovery-wrapped CEK blob so the client can unwrap
    it (T4.4)."""
    result = await db.execute(select(EncryptionKey).where(EncryptionKey.user_id == current_user.id))
    key = result.scalar_one_or_none()
    if not key or not key.recovery_phrase_hash or not key.recovery_encrypted_cek:
        raise HTTPException(status_code=400, detail="No recovery phrase is set up for this account")
    if body.recovery_phrase_hash != key.recovery_phrase_hash:
        raise HTTPException(status_code=400, detail="Incorrect recovery phrase")
    return RecoveryKeyResponse(
        recovery_encrypted_cek=base64.b64encode(key.recovery_encrypted_cek).decode(),
        recovery_cek_iv=base64.b64encode(key.recovery_cek_iv).decode(),
        recovery_salt=base64.b64encode(key.recovery_salt).decode(),
    )


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
async def forgot_password(body: ForgotPasswordRequest, db: AsyncSession = Depends(get_db_session)):
    """T6.1: send a Supabase password-reset magic link to the given email."""
    svc = AuthService(db)
    return await svc.forgot_password(body.email)


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_verified_user),
):
    """T6.1/T6.3: complete a password reset (recovery-phrase path).

    Authenticated via the Supabase recovery-link access token returned to
    the frontend's /auth/reset-password page.
    """
    svc = AuthService(db)
    return await svc.reset_password(
        current_user, body.new_password, body.encrypted_cek, body.cek_iv, body.pbkdf2_salt
    )


@router.post("/reset-password/data-loss", status_code=status.HTTP_200_OK)
async def reset_password_data_loss(
    body: ResetPasswordDataLossRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_verified_user),
):
    """T6.3: complete a password reset for accounts with no recovery blob.
    Replaces the CEK entirely and flags existing capsule content as
    unrecoverable."""
    svc = AuthService(db)
    return await svc.reset_password_data_loss(
        current_user, body.new_password, body.encrypted_cek, body.cek_iv, body.pbkdf2_salt
    )


@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    body: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_verified_user),
):
    """T6.4: logged-in password change (Security page)."""
    svc = AuthService(db)
    return await svc.change_password(
        current_user, body.current_password, body.new_password,
        body.encrypted_cek, body.cek_iv, body.pbkdf2_salt,
    )
