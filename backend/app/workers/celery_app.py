from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "photoai",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "app.workers.tasks.*": {"queue": "default"},
    },
    beat_schedule={
        "periodic-duplicate-scan": {
            "task": "app.workers.tasks.duplicate_detection.run_duplicate_scan",
            "schedule": 3600.0,  # Every hour
        },
        "periodic-face-recluster": {
            "task": "app.workers.tasks.face_detection.recluster_faces",
            "schedule": 7200.0,  # Every 2 hours
        },
    },
)

celery_app.autodiscover_tasks(["app.workers"])

# Explicitly import task modules to ensure they are registered
import app.workers.tasks.image_processing  # noqa: F401, E402
import app.workers.tasks.duplicate_detection  # noqa: F401, E402
import app.workers.tasks.face_detection  # noqa: F401, E402
