"""
Business logic for authentication: signup, login, email verification,
token refresh, and account deletion.
"""

import base64
import hmac
import hashlib
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from fastapi import HTTPException, status as http_status

from app.config import get_settings
from app.core.supabase import get_supabase
from app.core.audit import write_audit
from app.db.models.user import User, UserSettings, EncryptionKey, UserStatus
from app.db.models.checkin import CheckInSchedule


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def signup(
        self,
        email: str,
        password: str,
        encrypted_cek: str,
        cek_iv: str,
        pbkdf2_salt: str,
        delivery_encrypted_cek: str | None = None,
        delivery_cek_iv: str | None = None,
    ) -> dict:
        existing = await self.db.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )
        supabase = get_supabase()
        try:
            response = supabase.auth.sign_up({"email": email, "password": password})
        except Exception as exc:
            err_str = str(exc).lower()
            if "rate" in err_str or "limit" in err_str:
                raise HTTPException(
                    status_code=http_status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Email rate limit exceeded — try again later",
                )
            raise HTTPException(
                status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Auth service unavailable: {exc}",
            )
        if not response.user:
            raise ValueError("Supabase signup failed")

        supabase_uid = response.user.id

        user = User(
            supabase_uid=supabase_uid,
            email=email,
            email_verified=False,
            status=UserStatus.active,
        )
        self.db.add(user)
        await self.db.flush()

        self.db.add(UserSettings(user_id=user.id))

        enc_key = EncryptionKey(
            user_id=user.id,
            encrypted_cek=base64.b64decode(encrypted_cek),
            cek_iv=base64.b64decode(cek_iv),
            pbkdf2_salt=base64.b64decode(pbkdf2_salt),
            pbkdf2_iterations=100000,
            delivery_encrypted_cek=base64.b64decode(delivery_encrypted_cek) if delivery_encrypted_cek else None,
            delivery_cek_iv=base64.b64decode(delivery_cek_iv) if delivery_cek_iv else None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self.db.add(enc_key)

        self.db.add(CheckInSchedule(
            user_id=user.id,
            interval_days=30,
            grace_period_days=7,
            next_dispatch_at=None,
        ))

        await write_audit(self.db, "signup", user_id=user.id, description=f"New account: {email}")
        await self.db.commit()
        return {"message": "Verification email sent"}

    async def verify_email(self, email: str, otp: str) -> dict:
        supabase = get_supabase()
        response = supabase.auth.verify_otp({"email": email, "token": otp, "type": "email"})
        if not response.session:
            raise ValueError("OTP verification failed")

        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError("User not found")

        user.email_verified = True

        result2 = await self.db.execute(
            select(CheckInSchedule).where(CheckInSchedule.user_id == user.id)
        )
        schedule = result2.scalar_one_or_none()
        if schedule:
            schedule.next_dispatch_at = datetime.now(timezone.utc) + timedelta(days=schedule.interval_days)

        await write_audit(self.db, "email_verified", user_id=user.id)
        await self.db.commit()

        session = response.session
        return {
            "access_token": session.access_token,
            "refresh_token": session.refresh_token,
            "token_type": "bearer",
        }

    async def login(self, email: str, password: str) -> dict:
        supabase = get_supabase()
        try:
            response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        except Exception:
            raise HTTPException(status_code=http_status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        if not response.session:
            raise HTTPException(status_code=http_status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user:
            user.last_login_at = datetime.now(timezone.utc)
            await write_audit(self.db, "login", user_id=user.id)
            await self.db.commit()

        session = response.session
        return {
            "access_token": session.access_token,
            "refresh_token": session.refresh_token,
            "token_type": "bearer",
        }

    async def refresh(self, refresh_token: str) -> dict:
        supabase = get_supabase()
        try:
            response = supabase.auth.refresh_session(refresh_token)
        except Exception:
            raise HTTPException(status_code=http_status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
        if not response.session:
            raise HTTPException(status_code=http_status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
        return {
            "access_token": response.session.access_token,
            "refresh_token": response.session.refresh_token,
            "token_type": "bearer",
        }

    async def logout(self) -> None:
        supabase = get_supabase()
        try:
            supabase.auth.sign_out()
        except Exception:
            pass  # session may already be invalid

    async def delete_account(self, user: User, password: str) -> None:
        supabase = get_supabase()
        # Re-authenticate to confirm password
        try:
            response = supabase.auth.sign_in_with_password({"email": user.email, "password": password})
        except Exception:
            raise HTTPException(status_code=http_status.HTTP_401_UNAUTHORIZED, detail="Invalid password")
        if not response.session:
            raise HTTPException(status_code=http_status.HTTP_401_UNAUTHORIZED, detail="Invalid password")

        user.status = UserStatus.deleted
        user.erasure_requested_at = datetime.now(timezone.utc)

        await write_audit(self.db, "account_deleted", user_id=user.id)
        await self.db.commit()

        # Enqueue storage purge (import here to avoid circular imports)
        from app.worker.tasks.cleanup_tasks import purge_user_storage
        purge_user_storage.apply_async(args=[str(user.id)], countdown=0)

        # Delete from Supabase Auth
        supabase.auth.admin.delete_user(user.supabase_uid)

    def get_delivery_wrapping_key(self, user_id: str) -> str:
        cfg = get_settings()
        return hmac.new(
            cfg.delivery_secret.encode(),
            user_id.encode(),
            hashlib.sha256,
        ).hexdigest()
