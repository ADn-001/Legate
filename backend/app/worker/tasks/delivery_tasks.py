"""
Celery tasks for triggering and executing the delivery pipeline.
"""

from app.worker.celery_app import celery_app


@celery_app.task(name="app.worker.tasks.delivery_tasks.execute_delivery", bind=True, max_retries=3)
def execute_delivery(self, trigger_id: str):
    """
    Execute full delivery pipeline for a given release trigger ID.
    Retries up to 3 times with exponential backoff on failure.
    TODO: delegate to DeliveryService.execute_delivery.
    """
    try:
        raise NotImplementedError
    except Exception as exc:
        raise self.retry(exc=exc, countdown=3600)
