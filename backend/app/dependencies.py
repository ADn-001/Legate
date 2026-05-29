"""
FastAPI dependency injection functions.
"""

import jwt as pyjwt
from jwt import PyJWKClient
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.db.session import get_db_session
from app.db.models.user import User

bearer_scheme = HTTPBearer()

# Cached JWKS client — fetches & caches public keys from Supabase
_jwks_client: PyJWKClient | None = None


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        cfg = get_settings()
        _jwks_client = PyJWKClient(f"{cfg.supabase_url}/auth/v1/.well-known/jwks.json")
    return _jwks_client


def _decode_supabase_jwt(token: str) -> dict:
    """
    Verify a Supabase JWT. Tries HS256 first (legacy projects), then falls back
    to ES256 via JWKS (current default for new Supabase projects).
    """
    cfg = get_settings()
    try:
        return pyjwt.decode(
            token,
            cfg.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except pyjwt.InvalidAlgorithmError:
        pass
    except pyjwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    # ES256 path: verify via JWKS
    try:
        signing_key = _get_jwks_client().get_signing_key_from_jwt(token)
        return pyjwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256"],
            audience="authenticated",
        )
    except pyjwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    token = credentials.credentials
    try:
        payload = _decode_supabase_jwt(token)
        supabase_user_id: str = payload["sub"]
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    result = await db.execute(
        select(User).options(selectinload(User.settings)).where(User.supabase_uid == supabase_user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


async def get_current_verified_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email address not verified.",
        )
    return current_user
