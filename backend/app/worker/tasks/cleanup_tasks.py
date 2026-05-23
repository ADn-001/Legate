"""
Celery tasks for scheduled data and storage cleanup.
"""

import asyncio
from datetime import datetime, timezone

from app.worker.celery_app import celery_app


@celery_app.task(name="app.worker.tasks.cleanup_tasks.purge_capsule_storage")
def purge_capsule_storage(capsule_id: str):
    asyncio.run(_purge_capsule_storage(capsule_id))


async def _purge_capsule_storage(capsule_id: str):
    from sqlalchemy import select
    from app.db.session import AsyncSessionLocal
    from app.db.models.capsule import Capsule, CapsuleStatus
    from app.core.supabase import get_supabase
    from app.core.audit import write_audit
    from app.config import get_settings

    cfg = get_settings()
    supabase = get_supabase()

    async with AsyncSessionLocal() as db:
        capsule = await db.get(Capsule, capsule_id)
        if not capsule:
            return

        user_id = str(capsule.user_id)

        for bucket in (cfg.supabase_storage_bucket_content, cfg.supabase_storage_bucket_media):
            prefix = f"{user_id}/{capsule_id}/"
            try:
                items = supabase.storage.from_(bucket).list(prefix)
                paths = [f"{prefix}{item['name']}" for item in (items or []) if item.get("name")]
                if paths:
                    supabase.storage.from_(bucket).remove(paths)
            except Exception:
                pass

        capsule.status = CapsuleStatus.deleted
        await write_audit(db, "capsule_purged", user_id=capsule.user_id, resource_id=capsule.id)
        await db.commit()


@celery_app.task(name="app.worker.tasks.cleanup_tasks.purge_user_storage")
def purge_user_storage(user_id: str):
    asyncio.run(_purge_user_storage(user_id))


async def _purge_user_storage(user_id: str):
    from sqlalchemy import select, update
    from app.db.session import AsyncSessionLocal
    from app.db.models.capsule import Capsule, CapsuleStatus
    from app.db.models.audit import AuditLog
    from app.core.supabase import get_supabase
    from app.config import get_settings

    cfg = get_settings()
    supabase = get_supabase()

    async with AsyncSessionLocal() as db:
        for bucket in (
            cfg.supabase_storage_bucket_content,
            cfg.supabase_storage_bucket_media,
            cfg.supabase_storage_bucket_thumbnails,
        ):
            prefix = f"{user_id}/"
            try:
                _delete_all_with_prefix(supabase, bucket, prefix)
            except Exception:
                pass

        # Mark all capsules deleted
        capsules_result = await db.execute(
            select(Capsule).where(Capsule.user_id == user_id)
        )
        for capsule in capsules_result.scalars().all():
            capsule.status = CapsuleStatus.deleted

        # Anonymise audit logs
        now = datetime.now(timezone.utc)
        logs_result = await db.execute(
            select(AuditLog).where(AuditLog.user_id == user_id)
        )
        for log in logs_result.scalars().all():
            log.user_id = None
            log.description = "[redacted]"

        # Final audit entry without user_id
        from app.db.models.audit import AuditLog as AuditLogModel
        db.add(AuditLogModel(
            user_id=None,
            event_type="user_purged",
            description="[redacted]",
            created_at=now,
        ))
        await db.commit()


def _delete_all_with_prefix(supabase, bucket: str, prefix: str, batch_size: int = 100) -> None:
    try:
        items = supabase.storage.from_(bucket).list(prefix)
        if not items:
            return
        paths = [f"{prefix}{item['name']}" for item in items if item.get("name")]
        for i in range(0, len(paths), batch_size):
            supabase.storage.from_(bucket).remove(paths[i:i + batch_size])
    except Exception:
        pass
