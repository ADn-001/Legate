"""Business logic for capsule CRUD operations."""

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.config import get_settings
from app.core.audit import write_audit
from app.core.supabase import get_supabase
from app.db.models.beneficiary import Beneficiary
from app.db.models.capsule import Capsule, CapsuleStatus, CapsuleRecipient, RecipientStatus


class CapsuleService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_for_user(self, user_id: uuid.UUID) -> list[Capsule]:
        result = await self.db.execute(
            select(Capsule)
            .where(
                and_(
                    Capsule.user_id == user_id,
                    Capsule.status.notin_([CapsuleStatus.deleted]),
                )
            )
            .order_by(Capsule.delivery_order)
        )
        return list(result.scalars().all())

    async def create(
        self,
        user_id: uuid.UUID,
        title: str,
        beneficiary_id: uuid.UUID,
        cipher_iv: str,
        content_hash: str | None,
    ) -> dict:
        # Verify beneficiary belongs to user
        bene_result = await self.db.execute(
            select(Beneficiary).where(
                and_(Beneficiary.id == beneficiary_id, Beneficiary.user_id == user_id)
            )
        )
        if not bene_result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Beneficiary not found")

        # delivery_order = count of existing capsules + 1
        count_result = await self.db.execute(
            select(func.count()).select_from(Capsule).where(Capsule.user_id == user_id)
        )
        delivery_order = (count_result.scalar() or 0) + 1

        capsule = Capsule(
            user_id=user_id,
            title=title,
            status=CapsuleStatus.draft,
            cipher_iv=bytes.fromhex(cipher_iv) if cipher_iv else None,
            content_hash=content_hash,
            delivery_order=delivery_order,
        )
        self.db.add(capsule)
        await self.db.flush()

        recipient = CapsuleRecipient(
            capsule_id=capsule.id,
            beneficiary_id=beneficiary_id,
            is_primary=True,
            status=RecipientStatus.pending,
        )
        self.db.add(recipient)

        # Generate signed upload URL
        cfg = get_settings()
        supabase = get_supabase()
        storage_path = f"{user_id}/{capsule.id}/content.enc"
        try:
            upload_response = supabase.storage.from_(cfg.supabase_storage_bucket_content).create_signed_upload_url(storage_path)
            upload_url = upload_response.get("signedURL") or upload_response.get("signed_url", "")
        except Exception:
            upload_url = ""

        await write_audit(self.db, "capsule_created", user_id=user_id, resource_id=capsule.id)
        await self.db.commit()
        return {"id": capsule.id, "upload_url": upload_url}

    async def get_by_id(self, capsule_id: uuid.UUID, user_id: uuid.UUID) -> Capsule:
        result = await self.db.execute(
            select(Capsule).where(and_(Capsule.id == capsule_id, Capsule.user_id == user_id))
        )
        capsule = result.scalar_one_or_none()
        if not capsule:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Capsule not found")
        return capsule

    async def update(self, capsule_id: uuid.UUID, user_id: uuid.UUID, **kwargs) -> Capsule:
        capsule = await self.get_by_id(capsule_id, user_id)

        allowed = {"title", "storage_object_path", "delivery_order", "status"}
        for key, value in kwargs.items():
            if key in allowed and value is not None:
                setattr(capsule, key, value)

        if kwargs.get("storage_object_path") and capsule.status == CapsuleStatus.draft:
            capsule.status = CapsuleStatus.active

        await write_audit(self.db, "capsule_updated", user_id=user_id, resource_id=capsule_id)
        await self.db.commit()
        return capsule

    async def delete(self, capsule_id: uuid.UUID, user_id: uuid.UUID) -> None:
        capsule = await self.get_by_id(capsule_id, user_id)
        capsule.status = CapsuleStatus.pending_deletion

        await write_audit(self.db, "capsule_deleted", user_id=user_id, resource_id=capsule_id)
        await self.db.commit()

        from app.worker.tasks.cleanup_tasks import purge_capsule_storage
        purge_capsule_storage.apply_async(args=[str(capsule_id)], countdown=86400)
