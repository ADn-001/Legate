"""
FastAPI dependency injection functions.
"""

import jwt as pyjwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import get_settings
from app.db.session import get_db_session
from app.db.models.user import User

bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    token = credentials.credentials
    cfg = get_settings()
    try:
        payload = pyjwt.decode(
            token,
            cfg.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
        supabase_user_id: str = payload["sub"]
    except pyjwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    result = await db.execute(select(User).where(User.supabase_uid == supabase_user_id))
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
