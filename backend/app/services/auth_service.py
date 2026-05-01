"""
Business logic for authentication: signup, login, email verification,
token refresh, and account deletion.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def signup(self, email: str, password: str, encrypted_cek: str, cek_iv: str, pbkdf2_salt: str):
        """
        Create user, user_settings, encryption_key, checkin_schedule rows.
        Send OTP verification email.
        TODO: implement full signup flow.
        """
        raise NotImplementedError

    async def verify_email(self, email: str, otp: str):
        """
        Validate OTP and mark user email_verified = true.
        TODO: implement OTP storage and validation.
        """
        raise NotImplementedError

    async def login(self, email: str, password: str) -> dict:
        """
        Authenticate user, return access + refresh tokens.
        TODO: implement login flow.
        """
        raise NotImplementedError

    async def refresh(self, refresh_token: str) -> dict:
        """
        Validate refresh token (check Redis blacklist), issue new access token.
        TODO: implement refresh logic.
        """
        raise NotImplementedError

    async def delete_account(self, user_id: str, password: str):
        """
        Set user.status = deleted, cascade soft-delete, enqueue storage purge.
        Record erasure_requested_at for GDPR tracking.
        TODO: implement deletion flow.
        """
        raise NotImplementedError
