"""Pydantic schemas for capsule endpoints."""

import uuid
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from app.db.models.capsule import CapsuleStatus


class CapsuleCreate(BaseModel):
    title: str = Field(..., max_length=255)
    beneficiary_id: uuid.UUID
    cipher_iv: str  # hex-encoded
    content_hash: str | None = None
    content_size_bytes: int | None = Field(None, ge=0)


class CapsuleUpdate(BaseModel):
    title: str | None = None
    storage_object_path: str | None = None
    # hex-encoded AES-GCM IV for the re-encrypted content blob (T5 edit flow)
    cipher_iv: str | None = None
    # Reassign the primary recipient (T5 edit flow)
    beneficiary_id: uuid.UUID | None = None
    delivery_order: int | None = None
    status: CapsuleStatus | None = None
    # Size of the encrypted content blob, reported at upload time (FR-36).
    content_size_bytes: int | None = Field(None, ge=0)


class CapsuleResponse(BaseModel):
    id: uuid.UUID
    title: str
    status: CapsuleStatus
    delivery_order: int
    # T5 (F6): primary recipient, storage path and content IV so the
    # frontend can fetch + decrypt the content blob for edit/view.
    beneficiary_id: uuid.UUID | None = None
    storage_object_path: str | None = None
    cipher_iv: str | None = None  # hex-encoded
    # FR-22: False when beneficiary removal left this capsule with no
    # recipients — the frontend shows a "needs a recipient" flag.
    has_recipients: bool = True
    # T6.3: true if a password-reset-with-data-loss replaced the CEK that
    # this capsule's content was encrypted under — it can no longer be
    # decrypted.
    content_unrecoverable: bool = False
    content_size_bytes: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("cipher_iv", mode="before")
    @classmethod
    def _hex_encode_cipher_iv(cls, v: object) -> object:
        if isinstance(v, bytes):
            return v.hex()
        return v


class CapsuleContentResponse(BaseModel):
    """Short-lived signed download URL for the encrypted content blob."""
    url: str


class CapsuleUploadUrlResponse(BaseModel):
    """Short-lived signed upload URL for (re-)writing the content blob."""
    upload_url: str
    storage_object_path: str
