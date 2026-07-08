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
        # Phase B: tick interval is configurable (BEAT_INTERVAL_SECONDS,
        # default 3600 = hourly, unchanged) so demo-mode minute-level
        # schedules actually fire promptly. send-grace-reminders is left at
        # a fixed 12h — it self-skips minute-mode users (see checkin_tasks.py).
        "dispatch-checkin-emails": {
            "task": "app.worker.tasks.checkin_tasks.dispatch_due_checkins",
            "schedule": float(cfg.beat_interval_seconds),
        },
        "check-grace-periods": {
            "task": "app.worker.tasks.checkin_tasks.check_grace_periods",
            "schedule": float(cfg.beat_interval_seconds),
        },
        "process-pending-triggers": {
            "task": "app.worker.tasks.checkin_tasks.process_pending_triggers",
            "schedule": float(cfg.beat_interval_seconds),
        },
        "send-grace-reminders": {
            "task": "app.worker.tasks.checkin_tasks.send_grace_period_reminders",
            "schedule": 43200.0,  # Every 12h
        },
    },
)
