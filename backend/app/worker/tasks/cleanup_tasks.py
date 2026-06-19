"""
Celery tasks for scheduled data and storage cleanup.

Phase 2 (B9 + B10):
  - Storage purges build the object list from the DB (per-capsule prefixes)
    plus a recursive listing sweep, remove real object paths in batches, then
    RE-LIST and verify every prefix is empty — raising (Celery retry) if not.
  - purge_user_storage: storage-only purge used after delivery
    (memorialized account keeps its DB rows).
  - purge_user_account: full GDPR erasure (FR-05/FR-41) — storage purge,
    audit-log anonymization, Supabase auth user deletion, then a hard DELETE
    of the users row relying on FK cascades.
"""

import asyncio
import logging
from datetime import datetime, timezone

from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)


# ── Storage helpers ───────────────────────────────────────────────────────────

def _list_prefix(storage, bucket: str, prefix: str) -> list[dict]:
    try:
        return storage.from_(bucket).list(prefix) or []
    except Exception as exc:
        logger.warning("storage list failed for %s/%s: %s", bucket, prefix, exc)
        return []


def _collect_object_paths(storage, bucket: str, prefix: str) -> list[str]:
    """Recursively collect full object paths under a prefix.

    Supabase list() returns immediate children only; folders come back with
    id=None. B9: removing folder paths is a no-op, so we must walk down to
    real object paths.
    """
    paths: list[str] = []
    for item in _list_prefix(storage, bucket, prefix):
        name = item.get("name")
        if not name:
            continue
        full = f"{prefix.rstrip('/')}/{name}" if prefix else name
        if item.get("id"):
            paths.append(full)
        else:
            paths.extend(_collect_object_paths(storage, bucket, full))
    return paths


def _remove_paths(storage, bucket: str, paths: list[str], batch_size: int = 100) -> None:
    for i in range(0, len(paths), batch_size):
        storage.from_(bucket).remove(paths[i:i + batch_size])


def _purge_storage_for_user(user_id: str, capsule_ids: list[str], cfg, storage) -> None:
    """Remove every object for the user across all buckets and verify empty.

    Raises RuntimeError if objects remain after removal (caller retries).
    """
    buckets = (
        cfg.supabase_storage_bucket_content,
        cfg.supabase_storage_bucket_media,
        cfg.supabase_storage_bucket_thumbnails,
    )

    for bucket in buckets:
        # DB-driven: every capsule folder, covering the upload path pattern
        # f"{user_id}/{capsule_id}/content.enc" and media under the same prefix.
        all_paths: set[str] = set()
        for capsule_id in capsule_ids:
            all_paths.update(_collect_object_paths(storage, bucket, f"{user_id}/{capsule_id}"))
        # Sweep: anything else under the user's root prefix (strays).
        all_paths.update(_collect_object_paths(storage, bucket, user_id))

        if all_paths:
            _remove_paths(storage, bucket, sorted(all_paths))

        # Verify: re-list and assert empty.
        remaining = _collect_object_paths(storage, bucket, user_id)
        if remaining:
            logger.error(
                "storage purge incomplete for user %s in bucket %s: %d objects remain (%s…)",
                user_id, bucket, len(remaining), remaining[:5],
            )
            raise RuntimeError(
                f"Storage purge incomplete: {len(remaining)} objects remain in {bucket} for {user_id}"
            )


async def _capsule_ids_for_user(db, user_id: str) -> list[str]:
    from sqlalchemy import select
    from app.db.models.capsule import Capsule
    result = await db.execute(select(Capsule.id).where(Capsule.user_id == user_id))
    return [str(row[0]) for row in result.all()]


# ── Single-capsule purge (user deleted one capsule) ──────────────────────────

@celery_app.task(
    name="app.worker.tasks.cleanup_tasks.purge_capsule_storage",
    bind=True, max_retries=5, default_retry_delay=600,
)
def purge_capsule_storage(self, capsule_id: str):
    try:
        asyncio.run(_purge_capsule_storage(capsule_id))
    except Exception as exc:
        raise self.retry(exc=exc)


async def _purge_capsule_storage(capsule_id: str):
    from app.db.session import AsyncSessionLocal
    from app.db.models.capsule import Capsule, CapsuleStatus
    from app.core.supabase import get_storage
    from app.core.audit import write_audit
    from app.config import get_settings

    cfg = get_settings()
    storage = get_storage()

    async with AsyncSessionLocal() as db:
        capsule = await db.get(Capsule, capsule_id)
        if not capsule:
            return

        user_id = str(capsule.user_id)
        prefix = f"{user_id}/{capsule_id}"

        for bucket in (
            cfg.supabase_storage_bucket_content,
            cfg.supabase_storage_bucket_media,
            cfg.supabase_storage_bucket_thumbnails,
        ):
            paths = _collect_object_paths(storage, bucket, prefix)
            if paths:
                _remove_paths(storage, bucket, paths)
            remaining = _collect_object_paths(storage, bucket, prefix)
            if remaining:
                raise RuntimeError(
                    f"Capsule purge incomplete: {len(remaining)} objects remain in {bucket} for {prefix}"
                )

        capsule.status = CapsuleStatus.deleted
        await write_audit(db, "capsule_purged", user_id=capsule.user_id, resource_id=capsule.id)
        await db.commit()


# ── Post-delivery storage purge (account stays, memorialized) ────────────────

@celery_app.task(
    name="app.worker.tasks.cleanup_tasks.purge_user_storage",
    bind=True, max_retries=5, default_retry_delay=600,
)
def purge_user_storage(self, user_id: str):
    try:
        asyncio.run(_purge_user_storage(user_id))
    except Exception as exc:
        raise self.retry(exc=exc)


async def _purge_user_storage(user_id: str):
    from sqlalchemy import select
    from app.db.session import AsyncSessionLocal
    from app.db.models.capsule import Capsule, CapsuleStatus
    from app.core.supabase import get_storage
    from app.core.audit import write_audit
    from app.config import get_settings

    cfg = get_settings()
    storage = get_storage()

    async with AsyncSessionLocal() as db:
        capsule_ids = await _capsule_ids_for_user(db, user_id)

        # Raises (→ Celery retry) if any object survives removal (B9).
        _purge_storage_for_user(user_id, capsule_ids, cfg, storage)

        result = await db.execute(select(Capsule).where(Capsule.user_id == user_id))
        for capsule in result.scalars().all():
            capsule.status = CapsuleStatus.deleted

        await write_audit(db, "user_storage_purged", user_id=None,
                          description="Post-delivery storage purge completed")
        await db.commit()


# ── Full GDPR account purge (FR-05/FR-41, ≤72h) ──────────────────────────────

@celery_app.task(
    name="app.worker.tasks.cleanup_tasks.purge_user_account",
    bind=True, max_retries=5, default_retry_delay=600,
)
def purge_user_account(self, user_id: str):
    try:
        asyncio.run(_purge_user_account(user_id))
    except Exception as exc:
        raise self.retry(exc=exc)


async def _purge_user_account(user_id: str):
    from sqlalchemy import select, delete as sa_delete
    from app.db.session import AsyncSessionLocal
    from app.db.models.user import User
    from app.db.models.audit import AuditLog
    from app.core.supabase import get_supabase_admin, get_storage
    from app.config import get_settings

    cfg = get_settings()
    storage = get_storage()
    now = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as db:
        user = await db.get(User, user_id)
        if not user:
            return  # already purged
        supabase_uid = user.supabase_uid

        capsule_ids = await _capsule_ids_for_user(db, user_id)

        # 1) Storage purge — must fully succeed (verified, raises otherwise)
        #    before any DB rows are touched.
        _purge_storage_for_user(user_id, capsule_ids, cfg, storage)

        # 2) Anonymize the user's audit_logs rows: drop identifying data,
        #    keep event types for compliance (B10).
        logs_result = await db.execute(select(AuditLog).where(AuditLog.user_id == user.id))
        for log in logs_result.scalars().all():
            log.user_id = None
            log.actor_id = None
            log.description = "[redacted]"
            log.ip_address = None
            log.meta = None

        # 3) Delete the Supabase auth user (admin API). Tolerate "already
        #    deleted" so retries are idempotent. Use a dedicated admin client
        #    — get_supabase()'s shared singleton can have its service-role
        #    auth header overwritten by sign_in_with_password/sign_up/refresh
        #    calls elsewhere in this process (see get_supabase_admin()).
        try:
            get_supabase_admin().auth.admin.delete_user(supabase_uid)
        except Exception as exc:
            if "not found" not in str(exc).lower():
                raise

        # 4) Hard-DELETE the users row; FK cascades remove settings, keys,
        #    beneficiaries, capsules, recipients, schedule, tokens, triggers,
        #    and delivery events (ondelete=CASCADE fixed in migration
        #    a4c91f02d7e1).
        await db.execute(sa_delete(User).where(User.id == user.id))

        db.add(AuditLog(
            user_id=None,
            event_type="user_purged",
            description="[redacted]",
            created_at=now,
        ))
        await db.commit()
