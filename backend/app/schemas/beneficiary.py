"""Pydantic schemas for beneficiary endpoints."""

import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr
from app.db.models.beneficiary import BeneficiaryStatus


class BeneficiaryCreate(BaseModel):
    full_name: str
    email: EmailStr
    relationship: str | None = None
    is_emergency_contact: bool = False


class BeneficiaryUpdate(BaseModel):
    full_name: str | None = None
    email: EmailStr | None = None
    relationship: str | None = None
    is_emergency_contact: bool | None = None


class BeneficiaryResponse(BaseModel):
    id: uuid.UUID
    full_name: str
    email: str
    relationship: str | None
    is_emergency_contact: bool
    status: BeneficiaryStatus
    created_at: datetime

    model_config = {"from_attributes": True}
