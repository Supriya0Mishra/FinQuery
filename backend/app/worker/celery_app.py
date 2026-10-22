from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "finquery",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.worker.tasks"],
)

celery_app.conf.update(
    task_acks_late=True,  # a job is only removed from the queue once it finishes
    worker_prefetch_multiplier=1,
    task_track_started=True,
    broker_connection_retry_on_startup=True,
)
