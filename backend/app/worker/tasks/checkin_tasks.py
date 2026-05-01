"""
Celery tasks for check-in email dispatch and grace period monitoring.
"""

from app.worker.celery_app import celery_app


@celery_app.task(name="app.worker.tasks.checkin_tasks.dispatch_due_checkins")
def dispatch_due_checkins():
    """
    Find all checkin_schedules where next_dispatch_at <= NOW() and is_paused = false.
    For each: generate tokens, insert checkin_events, send check-in email via Resend.
    Update last_dispatched_at.
    TODO: implement with async DB session.
    """
    raise NotImplementedError


@celery_app.task(name="app.worker.tasks.checkin_tasks.check_grace_periods")
def check_grace_periods():
    """
    Find schedules where last_dispatched_at + grace_period_days < NOW()
    and no confirmation has been received.
    For each: create release_trigger, enqueue delivery_tasks.execute_delivery.
    TODO: implement.
    """
    raise NotImplementedError
