"""
Celery tasks for scheduled data and storage cleanup.
"""

from app.worker.celery_app import celery_app


@celery_app.task(name="app.worker.tasks.cleanup_tasks.purge_capsule_storage")
def purge_capsule_storage(capsule_id: str):
    """
    Delete all Supabase Storage objects for a capsule.
    Called 24 hours after capsule deletion is requested.
    TODO: implement Supabase Storage delete calls.
    """
    raise NotImplementedError


@celery_app.task(name="app.worker.tasks.cleanup_tasks.purge_user_storage")
def purge_user_storage(user_id: str):
    """
    Delete all Supabase Storage objects under {user_id}/ prefix.
    Called during GDPR account erasure (72h SLA).
    TODO: implement.
    """
    raise NotImplementedError
