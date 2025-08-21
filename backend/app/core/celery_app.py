"""
Celery configuration for background tasks
"""
import os
from celery import Celery
from app.core.config import settings

# Create Celery instance
celery_app = Celery(
    "property_ingestion",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.modules.ingestion.tasks"]
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    # Retry configuration
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Beat schedule for periodic tasks
    beat_schedule={
        "sync-properties-london": {
            "task": "app.modules.ingestion.tasks.sync_properties_for_location",
            "schedule": 3600.0,  # Every hour
            "args": ("London", 10, 100),  # location, radius_km, max_results
        },
        "sync-properties-manchester": {
            "task": "app.modules.ingestion.tasks.sync_properties_for_location",
            "schedule": 3600.0,  # Every hour
            "args": ("Manchester", 10, 100),
        },
        "cleanup-old-properties": {
            "task": "app.modules.ingestion.tasks.cleanup_old_properties",
            "schedule": 24 * 3600.0,  # Daily
            "args": (30,),  # days_old
        },
    },
)

# Configure Redis connection
if hasattr(settings, 'REDIS_URL'):
    celery_app.conf.broker_url = settings.REDIS_URL
    celery_app.conf.result_backend = settings.REDIS_URL
else:
    # Fallback to default Redis configuration
    celery_app.conf.broker_url = "redis://localhost:6379/0"
    celery_app.conf.result_backend = "redis://localhost:6379/0"