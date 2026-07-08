"""Pydantic schemas for beneficiary endpoints."""

import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
from app.db.models.beneficiary import BeneficiaryStatus


class BeneficiaryCreate(BaseModel):
    full_name: str
    email: EmailStr
    relationship: str | None = None
    is_emergency_contact: bool = False
    # Silent add: when False, no nomination email is sent and invited_at
    # stays NULL (the frontend renders these as "Added silently").
    notify_beneficiary: bool = True


class BeneficiaryUpdate(BaseModel):
    full_name: str | None = None
    email: EmailStr | None = None
    relationship: str | None = None
    is_emergency_contact: bool | None = None


class BeneficiaryResponse(BaseModel):
    id: uuid.UUID
    full_name: str
    email: str
    # reads from ORM attribute relationship_type; serializes as "relationship"
    relationship: str | None = Field(None, validation_alias="relationship_type")
    is_emergency_contact: bool
    status: BeneficiaryStatus
    # NULL ⇒ the beneficiary was added silently (no notification email).
    invited_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}
