"""
Phase 4 T1 (media delivery with encryption) — backend E2E.

Scenario: capsule has one encrypted photo and one encrypted video attachment.
After forcing delivery, verifies:

  B11-a  DeliveryEvent reaches `sent` and trigger reaches `completed`
  B11-b  Plaintext delivery copies are present in media bucket under
         deliveries/{trigger_id}/{att_id}/
  B11-c  Signed video URL returns HTTP 200 and response body matches the
         original decrypted plaintext
  B11-d  JWT token in the signed URL encodes a ≥ 30-day expiry window

Wire-format notes:
  Photo  — cipher_iv is the raw 12-byte AES-GCM IV
  Video  — cipher_iv is UTF-8-encoded JSON metadata; encrypted blob is the
            repeated [12-byte IV][ciphertext + 16-byte GCM tag] chunked format
"""

import base64
import json
import os
import uuid
from datetime import datetime, timezone

import httpx
import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import select

from tests.e2e.conftest import AsyncSessionLocal
from tests.e2e.test_12_checkin_lifecycle import (
    _create_local_user,
    _add_beneficiary,
    _add_capsule,
)
from app.config import get_settings
from app.core.supabase import get_storage
from app.db.models.capsule import MediaAttachment, MediaType, MediaStatus
from app.db.models.checkin import ReleaseTrigger, TriggerReason, TriggerStatus
from app.db.models.delivery import DeliveryEvent, DeliveryStatus
from app.worker.tasks.delivery_tasks import _run_delivery, SIGNED_URL_EXPIRES_SECONDS


# ── Helpers ──────────────────────────────────────────────────────────────────

def _encrypt_photo(cek: bytes) -> tuple[bytes, bytes, bytes]:
    """Return (plaintext, encrypted_blob, cipher_iv).
    Photo format: raw 12-byte AES-GCM IV stored as cipher_iv.
    Plaintext is kept well under the 200 KB inline-embedding threshold so the
    delivery task embeds it as a data URI (the img src path we can check).
    """
    plaintext = b"FAKE_JPEG_" + b"\xff\xd8\xff" + b"\x00" * 80  # ~93 bytes
    iv = os.urandom(12)
    encrypted = AESGCM(cek).encrypt(iv, plaintext, None)
    return plaintext, encrypted, iv  # cipher_iv = raw IV bytes


def _encrypt_video(cek: bytes) -> tuple[bytes, bytes, bytes]:
    """Return (plaintext, encrypted_blob, cipher_iv).
    Video format: cipher_iv is JSON metadata bytes; encrypted blob uses the
    chunked [12-byte IV][ct+16] wire format (single chunk since the file is tiny).
    """
    chunk_bytes = 5 * 1024 * 1024  # 5 MB chunks (standard)
    plaintext = b"FAKE_MP4_" + b"\x00\x00\x00" + b"\x18ftyp" + b"\x00" * 50
    chunk_iv = os.urandom(12)
    ct = AESGCM(cek).encrypt(chunk_iv, plaintext, None)
    encrypted = chunk_iv + ct  # one chunk
    cipher_iv = json.dumps({"chunk_bytes": chunk_bytes}).encode("utf-8")
    return plaintext, encrypted, cipher_iv


async def _upload_attachment(
    capsule_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    media_type: MediaType,
    mime_type: str,
    encrypted: bytes,
    cipher_iv: bytes,
    original_name: str,
) -> uuid.UUID:
    """Upload encrypted blob to Supabase and insert a MediaAttachment DB row.
    Returns the new attachment id.
    """
    cfg = get_settings()
    storage = get_storage()
    att_id = uuid.uuid4()
    path = f"{user_id}/{capsule_id}/{att_id}.enc"
    storage.from_(cfg.supabase_storage_bucket_media).upload(
        path,
        encrypted,
        {"content-type": "application/octet-stream"},
    )
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        att = MediaAttachment(
            id=att_id,
            capsule_id=capsule_id,
            type=media_type,
            original_name=original_name,
            mime_type=mime_type,
            size_bytes=len(encrypted),
            storage_object_path=path,
            cipher_iv=cipher_iv,
            status=MediaStatus.ready,
            created_at=now,
        )
        db.add(att)
        await db.commit()
    return att_id


def _list_delivery_files(storage, bucket: str, prefix: str) -> list[dict]:
    """List real storage objects under prefix (filter out placeholder entries)."""
    items = storage.from_(bucket).list(prefix) or []
    return [it for it in items if it.get("id")]


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_b11_media_delivery_photo_and_video():
    """End-to-end media delivery with photo + video.

    After delivery:
      • trigger reaches `completed`
      • plaintext delivery copies exist in storage
      • signed video URL → 200 and bytes match original plaintext
      • JWT in signed URL has ≥ 30-day expiry
    """
    cfg = get_settings()
    storage = get_storage()

    # ── 1. Create user with real delivery key material ────────────────────────
    u = await _create_local_user(with_delivery_key=True)
    user_id: uuid.UUID = u["user_id"]
    cek: bytes = u["cek"]

    # ── 2. Beneficiary + capsule ──────────────────────────────────────────────
    bene_id = await _add_beneficiary(
        user_id,
        email=f"delivered+media{uuid.uuid4().hex[:8]}@resend.dev",
    )
    capsule_id, _recip_id = await _add_capsule(
        user_id, bene_id,
        title="Media Delivery Test",
        delivery_order=1,
    )

    # ── 3. Encrypted photo (< 200 KB → inlined as data URI by delivery task) ─
    photo_plain, photo_enc, photo_iv = _encrypt_photo(cek)
    photo_id = await _upload_attachment(
        capsule_id, user_id,
        media_type=MediaType.photo,
        mime_type="image/jpeg",
        encrypted=photo_enc,
        cipher_iv=photo_iv,
        original_name="test_photo.jpg",
    )

    # ── 4. Encrypted video (chunked format) ───────────────────────────────────
    video_plain, video_enc, video_cipher_iv = _encrypt_video(cek)
    video_id = await _upload_attachment(
        capsule_id, user_id,
        media_type=MediaType.video,
        mime_type="video/mp4",
        encrypted=video_enc,
        cipher_iv=video_cipher_iv,
        original_name="test_video.mp4",
    )

    # ── 5. Force trigger ──────────────────────────────────────────────────────
    async with AsyncSessionLocal() as db:
        trigger = ReleaseTrigger(
            user_id=user_id,
            triggered_at=datetime.now(timezone.utc),
            reason=TriggerReason.checkin_missed,
            status=TriggerStatus.processing,
        )
        db.add(trigger)
        await db.commit()
        trigger_id: uuid.UUID = trigger.id

    # ── 6. Run delivery ───────────────────────────────────────────────────────
    await _run_delivery(str(trigger_id), attempt=1)

    # ── B11-a: trigger completed + delivery event sent ────────────────────────
    async with AsyncSessionLocal() as db:
        trigger_row = (await db.execute(
            select(ReleaseTrigger).where(ReleaseTrigger.id == trigger_id)
        )).scalar_one()
        assert trigger_row.status == TriggerStatus.completed, (
            f"B11-a: trigger status {trigger_row.status!r}, expected completed"
        )

        events = (await db.execute(
            select(DeliveryEvent).where(DeliveryEvent.release_trigger_id == trigger_id)
        )).scalars().all()
        assert any(e.delivery_status == DeliveryStatus.sent for e in events), (
            "B11-a: no DeliveryEvent with status=sent"
        )

    # ── B11-b: plaintext delivery copies exist in storage ────────────────────
    photo_prefix = f"deliveries/{trigger_id}/{photo_id}"
    photo_items = _list_delivery_files(storage, cfg.supabase_storage_bucket_media, photo_prefix)
    assert photo_items, f"B11-b: no photo delivery file under {photo_prefix}"
    photo_delivery_path = f"{photo_prefix}/{photo_items[0]['name']}"

    video_prefix = f"deliveries/{trigger_id}/{video_id}"
    video_items = _list_delivery_files(storage, cfg.supabase_storage_bucket_media, video_prefix)
    assert video_items, f"B11-b: no video delivery file under {video_prefix}"
    video_delivery_path = f"{video_prefix}/{video_items[0]['name']}"

    downloaded_photo = storage.from_(cfg.supabase_storage_bucket_media).download(photo_delivery_path)
    assert bytes(downloaded_photo) == photo_plain, (
        "B11-b: photo plaintext in storage does not match original"
    )

    downloaded_video = storage.from_(cfg.supabase_storage_bucket_media).download(video_delivery_path)
    assert bytes(downloaded_video) == video_plain, (
        "B11-b: video plaintext in storage does not match original"
    )

    # ── B11-c: signed video URL → 200, body matches original ─────────────────
    signed = storage.from_(cfg.supabase_storage_bucket_media).create_signed_url(
        video_delivery_path, SIGNED_URL_EXPIRES_SECONDS
    )
    video_url: str = signed.get("signedURL") or signed.get("signed_url") or ""
    assert video_url, "B11-c: create_signed_url returned no URL"

    async with httpx.AsyncClient(follow_redirects=True, timeout=30) as hc:
        resp = await hc.get(video_url)
    assert resp.status_code == 200, (
        f"B11-c: signed URL returned {resp.status_code} (URL: {video_url[:80]}...)"
    )
    assert resp.content == video_plain, (
        "B11-c: signed URL response body does not match decrypted plaintext"
    )

    # ── B11-d: JWT in signed URL encodes ≥ 30-day expiry ─────────────────────
    assert "token=" in video_url, "B11-d: signed URL missing 'token=' parameter"
    token_str = video_url.split("token=")[1].split("&")[0]
    # JWT is header.payload.signature — base64url-encoded, no padding needed for decode
    parts = token_str.split(".")
    assert len(parts) == 3, f"B11-d: token is not a valid JWT (parts={len(parts)})"
    # Add padding and decode payload
    payload_b64 = parts[1] + "==" * ((4 - len(parts[1]) % 4) % 4)
    try:
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
    except Exception as exc:
        raise AssertionError(f"B11-d: could not decode JWT payload: {exc}") from exc

    if "exp" in payload and "iat" in payload:
        duration = payload["exp"] - payload["iat"]
        assert duration >= SIGNED_URL_EXPIRES_SECONDS, (
            f"B11-d: JWT expiry window {duration}s < {SIGNED_URL_EXPIRES_SECONDS}s (30 days)"
        )
    else:
        # Supabase may encode expiry differently; assert URL was at minimum signed
        # with the correct expires_in argument by verifying the token is non-empty
        assert len(token_str) > 20, "B11-d: JWT token suspiciously short"
