"""Business logic for capsule CRUD operations."""

import uuid
import secrets

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.config import get_settings
from app.core.audit import write_audit
from app.core.supabase import get_storage
from app.db.models.beneficiary import Beneficiary
from app.db.models.capsule import Capsule, CapsuleStatus, CapsuleRecipient, RecipientStatus

# Short-lived: these signed URLs are used immediately by the owner's browser
# for in-app edit/view, unlike the 30-day delivery links sent to beneficiaries.
CONTENT_SIGNED_URL_EXPIRES_SECONDS = 3600


class CapsuleService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _annotate_recipients(self, capsules: list[Capsule]) -> None:
        """Attach has_recipients (FR-22) and the primary beneficiary_id (T5/F6)
        to each capsule."""
        if not capsules:
            return
        result = await self.db.execute(
            select(CapsuleRecipient.capsule_id, CapsuleRecipient.beneficiary_id, CapsuleRecipient.is_primary)
            .where(CapsuleRecipient.capsule_id.in_([c.id for c in capsules]))
        )
        counts: dict[uuid.UUID, int] = {}
        primary: dict[uuid.UUID, uuid.UUID] = {}
        for capsule_id, beneficiary_id, is_primary in result.all():
            counts[capsule_id] = counts.get(capsule_id, 0) + 1
            if is_primary:
                primary[capsule_id] = beneficiary_id
        for capsule in capsules:
            capsule.has_recipients = counts.get(capsule.id, 0) > 0
            capsule.beneficiary_id = primary.get(capsule.id)

    async def list_for_user(self, user_id: uuid.UUID) -> list[Capsule]:
        # B17: pending_deletion capsules stay visible (FR-31 badge);
        # only fully deleted ones are hidden.
        result = await self.db.execute(
            select(Capsule)
            .where(
                and_(
                    Capsule.user_id == user_id,
                    Capsule.status != CapsuleStatus.deleted,
                )
            )
            .order_by(Capsule.delivery_order)
        )
        capsules = list(result.scalars().all())
        await self._annotate_recipients(capsules)
        return capsules

    async def create(
        self,
        user_id: uuid.UUID,
        title: str,
        beneficiary_id: uuid.UUID,
        cipher_iv: str,
        content_hash: str | None,
        content_size_bytes: int | None = None,
    ) -> dict:
        # Verify beneficiary belongs to user
        bene_result = await self.db.execute(
            select(Beneficiary).where(
                and_(Beneficiary.id == beneficiary_id, Beneficiary.user_id == user_id)
            )
        )
        if not bene_result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Beneficiary not found")

        # B18: delivery_order = max(existing) + 1 — count+1 collides after
        # deletions or manual reordering.
        max_result = await self.db.execute(
            select(func.max(Capsule.delivery_order)).where(Capsule.user_id == user_id)
        )
        delivery_order = (max_result.scalar() or 0) + 1

        capsule = Capsule(
            user_id=user_id,
            title=title,
            status=CapsuleStatus.draft,
            cipher_iv=bytes.fromhex(cipher_iv) if cipher_iv else None,
            content_hash=content_hash,
            content_size_bytes=content_size_bytes,
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

        # Generate signed upload URL using isolated storage client (service role key,
        # not contaminated by user SIGNED_IN events from auth operations)
        cfg = get_settings()
        storage_path = f"{user_id}/{capsule.id}/content.enc"
        try:
            storage = get_storage()
            upload_response = storage.from_(cfg.supabase_storage_bucket_content).create_signed_upload_url(storage_path)
            upload_url = upload_response.get("signedURL") or upload_response.get("signed_url", "")
        except Exception as _e:
            import logging
            logging.getLogger(__name__).error("upload_url generation failed: %s", _e)
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
        await self._annotate_recipients([capsule])
        return capsule

    async def update(self, capsule_id: uuid.UUID, user_id: uuid.UUID, **kwargs) -> Capsule:
        capsule = await self.get_by_id(capsule_id, user_id)

        beneficiary_id = kwargs.pop("beneficiary_id", None)
        if beneficiary_id is not None:
            bene_result = await self.db.execute(
                select(Beneficiary).where(
                    and_(Beneficiary.id == beneficiary_id, Beneficiary.user_id == user_id)
                )
            )
            if not bene_result.scalar_one_or_none():
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Beneficiary not found")

            recipient_result = await self.db.execute(
                select(CapsuleRecipient).where(
                    and_(CapsuleRecipient.capsule_id == capsule_id, CapsuleRecipient.is_primary.is_(True))
                )
            )
            primary_recipient = recipient_result.scalar_one_or_none()
            if primary_recipient:
                primary_recipient.beneficiary_id = beneficiary_id
            else:
                self.db.add(CapsuleRecipient(
                    capsule_id=capsule_id, beneficiary_id=beneficiary_id,
                    is_primary=True, status=RecipientStatus.pending,
                ))
            capsule.beneficiary_id = beneficiary_id
            # A primary recipient now exists (FR-22).
            capsule.has_recipients = True

        allowed = {"title", "storage_object_path", "delivery_order", "status", "content_size_bytes", "cipher_iv"}
        for key, value in kwargs.items():
            if key not in allowed or value is None:
                continue
            if key == "cipher_iv":
                value = bytes.fromhex(value)
            setattr(capsule, key, value)

        if kwargs.get("storage_object_path") and capsule.status == CapsuleStatus.draft:
            capsule.status = CapsuleStatus.active

        # T6.3: re-uploading content re-encrypts it under the current CEK,
        # so a previously-unrecoverable capsule is recoverable again.
        if kwargs.get("storage_object_path"):
            capsule.content_unrecoverable = False

        await write_audit(self.db, "capsule_updated", user_id=user_id, resource_id=capsule_id)
        await self.db.commit()
        return capsule

    async def get_content_url(self, capsule_id: uuid.UUID, user_id: uuid.UUID) -> dict:
        capsule = await self.get_by_id(capsule_id, user_id)
        if not capsule.storage_object_path:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Capsule has no content")

        cfg = get_settings()
        try:
            storage = get_storage()
            response = storage.from_(cfg.supabase_storage_bucket_content).create_signed_url(
                capsule.storage_object_path, CONTENT_SIGNED_URL_EXPIRES_SECONDS
            )
            url = response.get("signedURL") or response.get("signed_url", "")
        except Exception as exc:
            import logging
            logging.getLogger(__name__).error("get_content_url failed: %s", exc)
            url = ""

        if not url:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Could not generate download URL")
        return {"url": url}

    async def get_upload_url(self, capsule_id: uuid.UUID, user_id: uuid.UUID) -> dict:
        capsule = await self.get_by_id(capsule_id, user_id)

        cfg = get_settings()
        # Each edit gets a unique path so create_signed_upload_url (which
        # defaults to upsert=False) never collides with the previous upload.
        # Old content files are orphaned and cleaned up when the capsule is
        # purged. The capsule record is updated with the new path by the
        # PATCH that follows the upload.
        storage_path = f"{user_id}/{capsule.id}/content_{secrets.token_hex(8)}.enc"
        try:
            storage = get_storage()
            response = storage.from_(cfg.supabase_storage_bucket_content).create_signed_upload_url(storage_path)
            upload_url = response.get("signedURL") or response.get("signed_url", "")
        except Exception as exc:
            import logging
            logging.getLogger(__name__).error("get_upload_url failed: %s", exc)
            upload_url = ""

        if not upload_url:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Could not generate upload URL")
        return {"upload_url": upload_url, "storage_object_path": storage_path}

    async def upload_content(self, capsule_id: uuid.UUID, user_id: uuid.UUID, data: bytes) -> dict:
        """Server-side upload of encrypted content blob (edit flow).

        Avoids the browser→Supabase signed-URL PUT which can stall due to
        upsert conflicts. Uses the service-role key directly with a unique
        storage path, so no object conflict is possible.
        """
        await self.get_by_id(capsule_id, user_id)  # ownership check
        cfg = get_settings()
        storage_path = f"{user_id}/{capsule_id}/content_{secrets.token_hex(8)}.enc"
        try:
            storage = get_storage()
            storage.from_(cfg.supabase_storage_bucket_content).upload(
                path=storage_path,
                file=data,
                file_options={"contentType": "application/octet-stream"},
            )
        except Exception as exc:
            import logging
            logging.getLogger(__name__).error("upload_content failed: %s", exc)
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Content upload failed")
        return {"storage_object_path": storage_path}

    async def delete(self, capsule_id: uuid.UUID, user_id: uuid.UUID) -> None:
        capsule = await self.get_by_id(capsule_id, user_id)
        capsule.status = CapsuleStatus.pending_deletion

        await write_audit(self.db, "capsule_deleted", user_id=user_id, resource_id=capsule_id)
        await self.db.commit()

        from app.worker.tasks.cleanup_tasks import purge_capsule_storage
        purge_capsule_storage.apply_async(args=[str(capsule_id)], countdown=86400)
