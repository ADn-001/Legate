"""
Business logic for authentication: signup, login, email verification,
token refresh, and account deletion.
"""

import asyncio
import base64
import hmac
import hashlib
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_

from fastapi import HTTPException, status as http_status

from app.config import get_settings
from app.core.supabase import get_supabase, get_supabase_admin
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
        full_name: str | None = None,
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
            # Run the blocking supabase-py call in a thread so it doesn't
            # stall the uvicorn event loop.  Hard-cap at 30 s: if GoTrue
            # hangs longer than that it is almost always because the free-tier
            # email rate limit was hit and GoTrue is waiting for the email
            # queue to drain.  asyncio.TimeoutError falls through to the
            # admin.create_user() fallback below exactly like an explicit
            # "rate limit" exception.
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    supabase.auth.sign_up, {"email": email, "password": password}
                ),
                timeout=30.0,
            )
        except Exception as exc:
            is_timeout = isinstance(exc, asyncio.TimeoutError)
            err_str = str(exc).lower()
            if is_timeout or "rate" in err_str or "limit" in err_str:
                # Supabase's free-tier email rate limit (3/hour) is exhausted.
                # Fall back to admin.create_user() which creates the auth user
                # without triggering an email send. The E2E test suite obtains
                # the OTP via admin.generate_link() (get_test_otp.py) anyway,
                # so the frontend's /auth/verify-email flow still works.
                try:
                    admin_resp = get_supabase_admin().auth.admin.create_user({
                        "email": email,
                        "password": password,
                        "email_confirm": False,
                    })
                    if not admin_resp.user:
                        raise HTTPException(
                            status_code=http_status.HTTP_429_TOO_MANY_REQUESTS,
                            detail="Email rate limit exceeded — try again later",
                        )
                    response = admin_resp
                except HTTPException:
                    raise
                except Exception:
                    raise HTTPException(
                        status_code=http_status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Email rate limit exceeded — try again later",
                    )
            else:
                raise HTTPException(
                    status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Auth service unavailable: {exc}",
                )
        if not response.user:
            raise ValueError("Supabase signup failed")

        supabase_uid = response.user.id

        # B19: if anything below fails after the Supabase auth user was
        # created, delete that auth user so no orphan remains, then re-raise.
        try:
            user = User(
                supabase_uid=supabase_uid,
                email=email,
                full_name=full_name,
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
        except Exception:
            await self.db.rollback()
            try:
                # Use a dedicated admin client: `supabase` (get_supabase())
                # may have had its service-role auth header overwritten by an
                # earlier sign_in_with_password/sign_up/refresh on this
                # process's shared client (see get_supabase_admin()).
                get_supabase_admin().auth.admin.delete_user(supabase_uid)
            except Exception:
                pass  # best-effort cleanup; original error matters more
            raise
        return {"message": "Verification email sent"}

    async def verify_email(self, email: str, otp: str) -> dict:
        supabase = get_supabase()
        # B20: client errors must surface as 400s, not bare ValueErrors (500).
        try:
            response = supabase.auth.verify_otp({"email": email, "token": otp, "type": "email"})
        except Exception as exc:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"OTP verification failed: {exc}",
            )
        if not response.session:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="OTP verification failed",
            )

        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="User not found",
            )

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

    async def resend_otp(self, email: str) -> dict:
        supabase = get_supabase()
        try:
            supabase.auth.resend({"type": "signup", "email": email})
        except Exception as exc:
            err_str = str(exc).lower()
            if "rate" in err_str or "limit" in err_str:
                raise HTTPException(
                    status_code=http_status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests — try again later",
                )
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Could not resend verification code: {exc}",
            )
        return {"message": "Verification email sent"}

    async def login(self, email: str, password: str) -> dict:
        # Use a fresh anon client per login. The shared get_supabase() singleton
        # accumulates SIGNED_IN event mutations that overwrite options.headers
        # ["Authorization"] with the calling user's JWT. After 70+ minutes of
        # test operations the GoTrueClient's state can cause sign_in_with_password
        # to raise unexpectedly. Fresh client = clean state. Same pattern as
        # delete_account. Uses anon key (not service role) per GoTrue convention.
        from supabase import create_client as _create_client
        _cfg = get_settings()
        _fresh = _create_client(_cfg.supabase_url, _cfg.supabase_anon_key)
        try:
            response = _fresh.auth.sign_in_with_password({"email": email, "password": password})
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
        # Bypass supabase-py entirely. supabase-py's admin client sends
        # Authorization: Bearer <service_role_key> for refresh_session(), which
        # GoTrue rejects when validating a user refresh_token grant. Instead,
        # call GoTrue directly with only the apikey header (no Authorization),
        # which is the correct pattern for client-initiated token refreshes.
        import httpx
        cfg = get_settings()
        url = f"{cfg.supabase_url}/auth/v1/token"
        try:
            async with httpx.AsyncClient() as hx:
                resp = await hx.post(
                    url,
                    params={"grant_type": "refresh_token"},
                    headers={
                        "apikey": cfg.supabase_anon_key,
                        "Content-Type": "application/json",
                    },
                    json={"refresh_token": refresh_token},
                    timeout=30.0,
                )
        except Exception:
            raise HTTPException(status_code=http_status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
        if resp.status_code != 200:
            raise HTTPException(status_code=http_status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
        data = resp.json()
        return {
            "access_token": data["access_token"],
            "refresh_token": data["refresh_token"],
            "token_type": "bearer",
        }

    async def logout(self) -> None:
        supabase = get_supabase()
        try:
            supabase.auth.sign_out()
        except Exception:
            pass  # session may already be invalid

    async def delete_account(self, user: User, password: str) -> None:
        # Use a fresh client for password re-auth. The shared get_supabase()
        # singleton accumulates SIGNED_IN event mutations (options.headers gets
        # overwritten with the latest user JWT) across the lifetime of the
        # process. After many auth operations the GoTrueClient's internal state
        # can cause sign_in_with_password to raise unexpectedly. A fresh client
        # has clean state, same as get_supabase_admin().
        from supabase import create_client
        cfg = get_settings()
        fresh_sb = create_client(cfg.supabase_url, cfg.supabase_service_role_key)
        try:
            response = fresh_sb.auth.sign_in_with_password({"email": user.email, "password": password})
        except Exception:
            raise HTTPException(status_code=http_status.HTTP_401_UNAUTHORIZED, detail="Invalid password")
        if not response.session:
            raise HTTPException(status_code=http_status.HTTP_401_UNAUTHORIZED, detail="Invalid password")

        # B10 / FR-05: flag the account and hand the full erasure sequence to
        # the purge task (storage purge → audit anonymization → Supabase auth
        # deletion → hard DELETE of the users row). Everything completes ≤72h.
        user.status = UserStatus.pending_deletion
        user.erasure_requested_at = datetime.now(timezone.utc)

        await write_audit(self.db, "account_deleted", user_id=user.id)
        await self.db.commit()

        # Enqueue full GDPR purge (import here to avoid circular imports)
        from app.worker.tasks.cleanup_tasks import purge_user_account
        purge_user_account.apply_async(args=[str(user.id)], countdown=0)

    def get_delivery_wrapping_key(self, user_id: str) -> str:
        cfg = get_settings()
        return hmac.new(
            cfg.delivery_secret.encode(),
            user_id.encode(),
            hashlib.sha256,
        ).hexdigest()

    async def forgot_password(self, email: str) -> dict:
        """T6.1: send a Supabase password-reset magic link.

        Always returns the same message regardless of whether the email is
        registered, to avoid leaking account existence.
        """
        supabase = get_supabase()
        cfg = get_settings()
        try:
            supabase.auth.reset_password_for_email(
                email, {"redirect_to": f"{cfg.frontend_url}/auth/reset-password"}
            )
        except Exception:
            pass  # don't leak whether the email exists or Supabase errored
        return {"message": "If an account exists for that email, a password reset link has been sent."}

    async def _update_supabase_password(self, user: User, new_password: str) -> None:
        try:
            get_supabase_admin().auth.admin.update_user_by_id(user.supabase_uid, {"password": new_password})
        except Exception as exc:
            raise HTTPException(
                status_code=http_status.HTTP_502_BAD_GATEWAY,
                detail=f"Could not update password: {exc}",
            )

    async def _get_encryption_key(self, user_id) -> EncryptionKey:
        result = await self.db.execute(select(EncryptionKey).where(EncryptionKey.user_id == user_id))
        key = result.scalar_one_or_none()
        if not key:
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Encryption key not found")
        return key

    async def reset_password(
        self, user: User, new_password: str, encrypted_cek: str, cek_iv: str, pbkdf2_salt: str
    ) -> dict:
        """T6.1/T6.3 (recovery-phrase path): update the Supabase auth
        password and re-wrap the primary CEK blob with the new
        password-derived key. The CEK itself is unchanged, so existing
        capsules remain decryptable."""
        await self._update_supabase_password(user, new_password)

        key = await self._get_encryption_key(user.id)
        key.encrypted_cek = base64.b64decode(encrypted_cek)
        key.cek_iv = base64.b64decode(cek_iv)
        key.pbkdf2_salt = base64.b64decode(pbkdf2_salt)
        key.updated_at = datetime.now(timezone.utc)

        await write_audit(self.db, "password_reset", user_id=user.id)
        await self.db.commit()
        return {"status": "updated"}

    async def reset_password_data_loss(
        self, user: User, new_password: str, encrypted_cek: str, cek_iv: str, pbkdf2_salt: str
    ) -> dict:
        """T6.3 (legacy accounts with no recovery blob): update the Supabase
        auth password and replace the CEK entirely with a brand-new one
        wrapped under the new password. The old CEK is now unrecoverable, so
        every capsule that already has uploaded content is flagged
        content_unrecoverable. Any stale recovery blob (tied to the old CEK)
        is cleared too."""
        await self._update_supabase_password(user, new_password)

        key = await self._get_encryption_key(user.id)
        key.encrypted_cek = base64.b64decode(encrypted_cek)
        key.cek_iv = base64.b64decode(cek_iv)
        key.pbkdf2_salt = base64.b64decode(pbkdf2_salt)
        key.recovery_phrase_hash = None
        key.recovery_encrypted_cek = None
        key.recovery_cek_iv = None
        key.recovery_salt = None
        key.updated_at = datetime.now(timezone.utc)

        from app.db.models.capsule import Capsule
        await self.db.execute(
            update(Capsule)
            .where(and_(Capsule.user_id == user.id, Capsule.storage_object_path.is_not(None)))
            .values(content_unrecoverable=True)
        )

        await write_audit(self.db, "password_reset_data_loss", user_id=user.id)
        await self.db.commit()
        return {"status": "updated"}

    async def change_password(
        self, user: User, current_password: str, new_password: str,
        encrypted_cek: str, cek_iv: str, pbkdf2_salt: str,
    ) -> dict:
        """T6.4: logged-in password change. Confirms the current password by
        re-authenticating with Supabase, then updates the Supabase auth
        password and re-wraps the primary CEK blob with the new
        password-derived key."""
        # Fresh client for re-auth — same singleton contamination risk as login/delete_account.
        from supabase import create_client as _create_client
        _cfg = get_settings()
        _fresh = _create_client(_cfg.supabase_url, _cfg.supabase_anon_key)
        try:
            response = _fresh.auth.sign_in_with_password({"email": user.email, "password": current_password})
        except Exception:
            raise HTTPException(status_code=http_status.HTTP_401_UNAUTHORIZED, detail="Incorrect current password")
        if not response.session:
            raise HTTPException(status_code=http_status.HTTP_401_UNAUTHORIZED, detail="Incorrect current password")

        await self._update_supabase_password(user, new_password)

        key = await self._get_encryption_key(user.id)
        key.encrypted_cek = base64.b64decode(encrypted_cek)
        key.cek_iv = base64.b64decode(cek_iv)
        key.pbkdf2_salt = base64.b64decode(pbkdf2_salt)
        key.updated_at = datetime.now(timezone.utc)

        await write_audit(self.db, "password_changed", user_id=user.id)
        await self.db.commit()
        return {"status": "updated"}
