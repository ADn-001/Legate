"""Pydantic schemas for capsule endpoints."""

import uuid
from datetime import datetime
from pydantic import BaseModel
from app.db.models.capsule import CapsuleStatus


class CapsuleCreate(BaseModel):
    title: str
    beneficiary_id: uuid.UUID
    cipher_iv: str  # base64-encoded
    content_hash: str | None = None


class CapsuleUpdate(BaseModel):
    title: str | None = None
    storage_object_path: str | None = None
    delivery_order: int | None = None
    status: CapsuleStatus | None = None


class CapsuleResponse(BaseModel):
    id: uuid.UUID
    title: str
    status: CapsuleStatus
    delivery_order: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
