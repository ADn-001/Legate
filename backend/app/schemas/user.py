"""Pydantic schemas for user profile endpoints."""

import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr
from app.db.models.user import UserStatus


class UserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str | None
    email_verified: bool
    status: UserStatus
    created_at: datetime

    model_config = {"from_attributes": True}
