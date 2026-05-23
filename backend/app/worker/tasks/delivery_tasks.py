"""
Celery tasks for triggering and executing the delivery pipeline.
"""

import asyncio
from datetime import datetime, timezone

from app.worker.celery_app import celery_app


@celery_app.task(name="app.worker.tasks.delivery_tasks.execute_delivery", bind=True, max_retries=3)
def execute_delivery(self, trigger_id: str):
    try:
        asyncio.run(_execute_delivery(trigger_id))
    except Exception as exc:
        raise self.retry(exc=exc, countdown=3600)


async def _execute_delivery(trigger_id: str):
    import base64
    import hmac
    import hashlib
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from sqlalchemy import select, and_
    from app.db.session import AsyncSessionLocal
    from app.db.models.user import User, UserStatus, EncryptionKey
    from app.db.models.checkin import ReleaseTrigger, TriggerStatus
    from app.db.models.capsule import Capsule, CapsuleStatus, CapsuleRecipient, MediaAttachment, MediaType
    from app.db.models.beneficiary import Beneficiary
    from app.db.models.delivery import DeliveryEvent, DeliveryStatus
    from app.core.email import send_delivery_email
    from app.core.supabase import get_supabase
    from app.config import get_settings

    cfg = get_settings()
    supabase = get_supabase()
    now = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as db:
        trigger_result = await db.execute(
            select(ReleaseTrigger).where(
                and_(
                    ReleaseTrigger.id == trigger_id,
                    ReleaseTrigger.status == TriggerStatus.processing,
                )
            )
        )
        trigger = trigger_result.scalar_one_or_none()
        if not trigger:
            return

        user = await db.get(User, trigger.user_id)
        if not user:
            return

        enc_result = await db.execute(
            select(EncryptionKey).where(EncryptionKey.user_id == user.id)
        )
        enc_key = enc_result.scalar_one_or_none()
        if not enc_key or not enc_key.delivery_encrypted_cek or not enc_key.delivery_cek_iv:
            trigger.status = TriggerStatus.failed
            await db.commit()
            return

        # Derive wrapping key and decrypt CEK (AES-GCM)
        wrapping_key = bytes.fromhex(
            hmac.new(
                cfg.delivery_secret.encode(),
                str(user.id).encode(),
                hashlib.sha256,
            ).hexdigest()
        )
        wrap_gcm = AESGCM(wrapping_key)
        cek = wrap_gcm.decrypt(enc_key.delivery_cek_iv, enc_key.delivery_encrypted_cek, None)

        # All active capsules for user
        caps_result = await db.execute(
            select(Capsule).where(
                and_(Capsule.user_id == user.id, Capsule.status == CapsuleStatus.active)
            )
        )
        capsules = caps_result.scalars().all()

        for capsule in capsules:
            recip_result = await db.execute(
                select(CapsuleRecipient).where(CapsuleRecipient.capsule_id == capsule.id)
            )
            recipients = recip_result.scalars().all()

            for recipient in recipients:
                beneficiary = await db.get(Beneficiary, recipient.beneficiary_id)
                if not beneficiary:
                    continue

                try:
                    capsules_html = _build_capsule_html(
                        capsule=capsule,
                        cek=cek,
                        supabase=supabase,
                        cfg=cfg,
                    )
                    msg_id = send_delivery_email(
                        to=beneficiary.email,
                        beneficiary_name=beneficiary.full_name,
                        capsules_html=capsules_html,
                        nominator_name=user.full_name or user.email,
                    )
                    db.add(DeliveryEvent(
                        release_trigger_id=trigger.id,
                        capsule_recipient_id=recipient.id,
                        sent_at=now,
                        delivery_status=DeliveryStatus.sent,
                        resend_message_id=msg_id,
                        attempts=1,
                        last_attempt_at=now,
                    ))
                except Exception as exc:
                    db.add(DeliveryEvent(
                        release_trigger_id=trigger.id,
                        capsule_recipient_id=recipient.id,
                        delivery_status=DeliveryStatus.failed,
                        error_detail=str(exc)[:500],
                        attempts=1,
                        last_attempt_at=now,
                    ))

        trigger.status = TriggerStatus.completed
        user.status = UserStatus.memorialized
        await db.commit()

        from app.worker.tasks.cleanup_tasks import purge_user_storage
        purge_user_storage.apply_async(args=[str(user.id)], countdown=259200)


def _build_capsule_html(capsule, cek: bytes, supabase, cfg) -> str:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    parts = [f"<h3>{capsule.title}</h3>"]

    if capsule.storage_object_path and capsule.cipher_iv:
        try:
            encrypted = supabase.storage.from_(cfg.supabase_storage_bucket_content).download(
                capsule.storage_object_path
            )
            if encrypted:
                gcm = AESGCM(cek)
                plaintext = gcm.decrypt(capsule.cipher_iv, encrypted, None)
                text = plaintext.decode("utf-8", errors="replace")
                parts.append(f"<p>{text}</p>")
        except Exception:
            parts.append("<p><em>[Content could not be decrypted]</em></p>")

    return "".join(parts)
