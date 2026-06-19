"""
Celery tasks for triggering and executing the delivery pipeline.

Phase 2 (B6 + B7):
  - ONE email per beneficiary, containing all their capsules ordered by
    delivery_order (FR-39), with media rendered as 30-day signed links.
  - Per-recipient retry: failed sends are retried up to MAX_DELIVERY_ATTEMPTS
    times, RETRY_COUNTDOWN_SECONDS apart, re-sending ONLY failed recipients
    (FR-42). After the final failed attempt the trigger is marked failed, an
    internal alert is emailed to ALERT_EMAIL, and a
    `delivery_failed_permanently` audit row is written.
  - Memorialization + purge scheduling happen when the trigger completes
    (all recipients succeeded) OR the final attempt finished with partial
    delivery — at-least-once delivery per NFR-07 was attempted for every
    recipient, so the account is memorialized anyway.
"""

import asyncio
import html as html_mod
from datetime import datetime, timezone

from app.worker.celery_app import celery_app

MAX_DELIVERY_ATTEMPTS = 3
RETRY_COUNTDOWN_SECONDS = 3600
SIGNED_URL_EXPIRES_SECONDS = 30 * 24 * 3600  # 30 days (FR-39 media links)
PURGE_COUNTDOWN_SECONDS = 259200  # 72h post-delivery content purge


@celery_app.task(name="app.worker.tasks.delivery_tasks.execute_delivery", bind=True, max_retries=3)
def execute_delivery(self, trigger_id: str):
    """First delivery attempt for a release trigger."""
    try:
        asyncio.run(_run_delivery(trigger_id, attempt=1))
    except Exception as exc:
        # Infrastructure-level failure (DB down etc.) — retry the whole task.
        raise self.retry(exc=exc, countdown=RETRY_COUNTDOWN_SECONDS)


@celery_app.task(name="app.worker.tasks.delivery_tasks.retry_failed_deliveries", bind=True, max_retries=3)
def retry_failed_deliveries(self, trigger_id: str, attempt: int):
    """Re-send ONLY recipients whose previous attempts failed (B6/FR-42)."""
    try:
        asyncio.run(_run_delivery(trigger_id, attempt=attempt))
    except Exception as exc:
        raise self.retry(exc=exc, countdown=RETRY_COUNTDOWN_SECONDS)


async def _run_delivery(trigger_id: str, attempt: int):
    import hmac
    import hashlib
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from sqlalchemy import select, and_
    from app.db.session import AsyncSessionLocal
    from app.db.models.user import User, UserStatus, EncryptionKey
    from app.db.models.checkin import ReleaseTrigger, TriggerStatus
    from app.db.models.capsule import Capsule, CapsuleStatus, CapsuleRecipient, RecipientStatus
    from app.db.models.beneficiary import Beneficiary
    from app.db.models.delivery import DeliveryEvent, DeliveryStatus
    from app.core.email import send_delivery_email, send_alert_email
    from app.core.audit import write_audit
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
            return  # cancelled / paused / already finalized

        user = await db.get(User, trigger.user_id)
        if not user:
            return

        enc_result = await db.execute(
            select(EncryptionKey).where(EncryptionKey.user_id == user.id)
        )
        enc_key = enc_result.scalar_one_or_none()
        if not enc_key or not enc_key.delivery_encrypted_cek or not enc_key.delivery_cek_iv:
            trigger.status = TriggerStatus.failed
            await write_audit(
                db, "delivery_failed_permanently", user_id=user.id,
                resource_id=trigger.id,
                description="No delivery encryption key material",
            )
            await db.commit()
            if cfg.alert_email:
                try:
                    send_alert_email(
                        to=cfg.alert_email,
                        subject=f"Delivery failed — missing key material (trigger {trigger_id})",
                        body_text=f"Trigger: {trigger_id}\nUser: {user.id}\nReason: no delivery_encrypted_cek/delivery_cek_iv",
                    )
                except Exception:
                    pass
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

        # ── B7: group deliverable capsules by beneficiary, ordered ───────────
        caps_result = await db.execute(
            select(Capsule)
            .where(and_(Capsule.user_id == user.id, Capsule.status == CapsuleStatus.active))
            .order_by(Capsule.delivery_order)
        )
        capsules = caps_result.scalars().all()

        # beneficiary_id -> list[(capsule, recipient_row)] in delivery_order
        groups: dict = {}
        beneficiaries: dict = {}
        for capsule in capsules:
            recip_result = await db.execute(
                select(CapsuleRecipient).where(CapsuleRecipient.capsule_id == capsule.id)
            )
            for recipient in recip_result.scalars().all():
                beneficiary = beneficiaries.get(recipient.beneficiary_id)
                if beneficiary is None:
                    beneficiary = await db.get(Beneficiary, recipient.beneficiary_id)
                    if not beneficiary:
                        continue
                    beneficiaries[recipient.beneficiary_id] = beneficiary
                groups.setdefault(recipient.beneficiary_id, []).append((capsule, recipient))

        # ── Determine which recipient rows already succeeded ─────────────────
        sent_result = await db.execute(
            select(DeliveryEvent.capsule_recipient_id).where(
                and_(
                    DeliveryEvent.release_trigger_id == trigger.id,
                    DeliveryEvent.delivery_status == DeliveryStatus.sent,
                )
            )
        )
        already_sent_ids = {row[0] for row in sent_result.all()}

        failed_beneficiaries: list[str] = []

        for beneficiary_id, capsule_pairs in groups.items():
            beneficiary = beneficiaries[beneficiary_id]
            pending_pairs = [
                (capsule, recipient) for capsule, recipient in capsule_pairs
                if recipient.id not in already_sent_ids
            ]
            if not pending_pairs:
                continue  # this beneficiary fully delivered in a prior attempt

            # ONE email per beneficiary: all their capsules, in order (FR-39).
            # The full set is re-rendered (not just pending capsules) so a
            # retried beneficiary still receives a complete, ordered email.
            try:
                sections = []
                for capsule, _recipient in capsule_pairs:
                    sections.append(_build_capsule_html(
                        capsule=capsule,
                        cek=cek,
                        supabase=supabase,
                        cfg=cfg,
                        media_html=await _render_capsule_media(db, capsule, cfg),
                    ))
                capsules_html = "".join(sections)

                msg_id = send_delivery_email(
                    to=beneficiary.email,
                    beneficiary_name=beneficiary.full_name,
                    capsules_html=capsules_html,
                    nominator_name=user.full_name or user.email,
                )
                for _capsule, recipient in capsule_pairs:
                    if recipient.id in already_sent_ids:
                        continue
                    recipient.status = RecipientStatus.sent
                    recipient.delivered_at = now
                    db.add(DeliveryEvent(
                        release_trigger_id=trigger.id,
                        capsule_recipient_id=recipient.id,
                        sent_at=now,
                        delivery_status=DeliveryStatus.sent,
                        resend_message_id=msg_id,
                        attempts=attempt,
                        last_attempt_at=now,
                    ))
            except Exception as exc:
                failed_beneficiaries.append(beneficiary.email)
                for _capsule, recipient in pending_pairs:
                    recipient.status = RecipientStatus.failed
                    db.add(DeliveryEvent(
                        release_trigger_id=trigger.id,
                        capsule_recipient_id=recipient.id,
                        delivery_status=DeliveryStatus.failed,
                        error_detail=str(exc)[:500],
                        attempts=attempt,
                        last_attempt_at=now,
                    ))

        # ── Finalization (B6) ────────────────────────────────────────────────
        if not failed_beneficiaries:
            trigger.status = TriggerStatus.completed
            user.status = UserStatus.memorialized
            await write_audit(db, "delivery_completed", user_id=user.id, resource_id=trigger.id)
            await db.commit()
            _schedule_post_delivery_purge(str(user.id))
        elif attempt < MAX_DELIVERY_ATTEMPTS:
            # Do NOT mark completed; schedule a retry for failed recipients only.
            await db.commit()
            retry_failed_deliveries.apply_async(
                args=[str(trigger.id), attempt + 1],
                countdown=RETRY_COUNTDOWN_SECONDS,
            )
        else:
            # Final attempt exhausted with failures: partial delivery.
            # Memorialize anyway — at-least-once delivery (NFR-07) was
            # attempted MAX_DELIVERY_ATTEMPTS times for every recipient.
            trigger.status = TriggerStatus.failed
            user.status = UserStatus.memorialized
            await write_audit(
                db, "delivery_failed_permanently", user_id=user.id,
                resource_id=trigger.id,
                description=f"Failed recipients after {attempt} attempts: {', '.join(failed_beneficiaries)}"[:1000],
                meta={"failed_recipients": failed_beneficiaries, "attempts": attempt},
            )
            await db.commit()
            if cfg.alert_email:
                try:
                    send_alert_email(
                        to=cfg.alert_email,
                        subject=f"Delivery permanently failed (trigger {trigger_id})",
                        body_text=(
                            f"Trigger: {trigger_id}\n"
                            f"User: {user.id}\n"
                            f"Attempts: {attempt}\n"
                            f"Failed recipients: {', '.join(failed_beneficiaries)}"
                        ),
                    )
                except Exception:
                    pass
            _schedule_post_delivery_purge(str(user.id))


def _schedule_post_delivery_purge(user_id: str):
    from app.worker.tasks.cleanup_tasks import purge_user_storage
    purge_user_storage.apply_async(args=[user_id], countdown=PURGE_COUNTDOWN_SECONDS)


def _build_capsule_html(capsule, cek: bytes, supabase, cfg, media_html: str = "") -> str:
    """Render one capsule section: escaped title + decrypted, escaped text + media."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    parts = [f"<h3>{html_mod.escape(capsule.title or '')}</h3>"]

    if capsule.storage_object_path and capsule.cipher_iv:
        try:
            encrypted = supabase.storage.from_(cfg.supabase_storage_bucket_content).download(
                capsule.storage_object_path
            )
            if encrypted:
                gcm = AESGCM(cek)
                plaintext = gcm.decrypt(capsule.cipher_iv, encrypted, None)
                text = plaintext.decode("utf-8", errors="replace")
                # html.escape now (T9.4); upgraded to sanitization in Phase 5
                # when rich text lands (S3).
                escaped = html_mod.escape(text).replace("\n", "<br>")
                parts.append(f"<p>{escaped}</p>")
        except Exception:
            parts.append("<p><em>[Content could not be decrypted]</em></p>")

    if media_html:
        parts.append(media_html)

    return "".join(parts)


async def _render_capsule_media(db, capsule, cfg) -> str:
    """
    FR-39 media rendering: photos embedded via 30-day signed URLs, videos as
    30-day signed links. Renders whatever media_attachments rows exist — the
    upload pipeline arrives in Phase 4 (G2), so this may legitimately render
    nothing for now.
    """
    from sqlalchemy import select, and_
    from app.db.models.capsule import MediaAttachment, MediaType, MediaStatus
    from app.core.supabase import get_storage

    result = await db.execute(
        select(MediaAttachment).where(
            and_(
                MediaAttachment.capsule_id == capsule.id,
                MediaAttachment.status == MediaStatus.ready,
            )
        ).order_by(MediaAttachment.created_at)
    )
    attachments = result.scalars().all()
    if not attachments:
        return ""

    storage = get_storage()
    parts = ['<div class="media">']
    for att in attachments:
        try:
            signed = storage.from_(cfg.supabase_storage_bucket_media).create_signed_url(
                att.storage_object_path, SIGNED_URL_EXPIRES_SECONDS
            )
            url = signed.get("signedURL") or signed.get("signed_url") or ""
        except Exception:
            url = ""
        if not url:
            continue

        name = html_mod.escape(att.original_name or "attachment")
        if att.type == MediaType.photo:
            parts.append(
                f'<p><img src="{url}" alt="{name}" style="max-width:100%;border-radius:6px">'
                f'<br><a href="{url}">{name}</a> (link valid 30 days)</p>'
            )
        else:
            parts.append(
                f'<p>&#x1F3A5; <a href="{url}">{name}</a> &mdash; video link, valid for 30 days</p>'
            )
    parts.append("</div>")
    return "".join(parts) if len(parts) > 2 else ""
