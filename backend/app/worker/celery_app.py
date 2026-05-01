"""
Celery application factory.
Broker and result backend are both Redis.
"""

from celery import Celery
from app.config import get_settings

cfg = get_settings()

celery_app = Celery(
    "legate",
    broker=cfg.redis_url,
    backend=cfg.redis_url,
    include=[
        "app.worker.tasks.checkin_tasks",
        "app.worker.tasks.delivery_tasks",
        "app.worker.tasks.cleanup_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "dispatch-checkin-emails": {
            "task": "app.worker.tasks.checkin_tasks.dispatch_due_checkins",
            "schedule": 3600.0,  # Every hour
        },
        "check-grace-periods": {
            "task": "app.worker.tasks.checkin_tasks.check_grace_periods",
            "schedule": 3600.0,  # Every hour
        },
    },
)
