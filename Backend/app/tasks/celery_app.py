from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "analytics",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.ingestion_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=4,
    task_acks_late=True,
)

celery_app.conf.beat_schedule = {
    "drain-ingest-queue": {
        "task": "app.tasks.ingestion_tasks.drain_ingest_queue",
        "schedule": 5.0,
    },
    "cleanup-expired-invitations": {
        "task": "app.tasks.ingestion_tasks.cleanup_expired_invitations",
        "schedule": crontab(hour=2, minute=0),
    },
}
