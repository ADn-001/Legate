"""
FastAPI dependency injection functions.
Used across route handlers for DB sessions, current user, rate limiting, etc.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.core.security import decode_access_token
from app.db.models.user import User

bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    """
    Validate JWT access token and return the authenticated user.
    Raises 401 if token is invalid or expired.
    """
    # TODO: implement token decode + user fetch from DB
    raise NotImplementedError


async def get_current_verified_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Ensure the user has a verified email address."""
    if not current_user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email address not verified.",
        )
    return current_user
