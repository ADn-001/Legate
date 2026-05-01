"""
Authentication routes: signup, login, logout, token refresh, email verification.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.auth import (
    SignupRequest, LoginRequest, TokenResponse,
    VerifyEmailRequest, RefreshRequest,
)
from app.services.auth_service import AuthService

router = APIRouter()


@router.post("/signup", status_code=status.HTTP_201_CREATED, response_model=TokenResponse)
async def signup(body: SignupRequest, db: AsyncSession = Depends(get_db_session)):
    """
    Create a new user account.
    Expects: email, password, encrypted_cek, cek_iv, pbkdf2_salt.
    Sends OTP verification email.
    """
    # TODO: delegate to AuthService.signup
    raise NotImplementedError


@router.post("/verify-email", status_code=status.HTTP_200_OK)
async def verify_email(body: VerifyEmailRequest, db: AsyncSession = Depends(get_db_session)):
    """Verify email address using 6-digit OTP."""
    # TODO: delegate to AuthService.verify_email
    raise NotImplementedError


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db_session)):
    """
    Authenticate user and return access + refresh tokens.
    """
    # TODO: delegate to AuthService.login
    raise NotImplementedError


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest, db: AsyncSession = Depends(get_db_session)):
    """Rotate refresh token and return new access token."""
    # TODO: delegate to AuthService.refresh
    raise NotImplementedError


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(body: RefreshRequest):
    """Blacklist the refresh token in Redis."""
    # TODO: blacklist token via Redis
    raise NotImplementedError


@router.get("/me/encryption-key")
async def get_encryption_key(db: AsyncSession = Depends(get_db_session)):
    """Return the current user's encrypted CEK blob and derivation params."""
    # TODO: get current user from JWT, fetch encryption_key row
    raise NotImplementedError
