"""Celery application configuration for async task processing."""

from celery import Celery
from app.core.config import settings

# Create Celery app instance
celery_app = Celery(
    "moooov_tokenization",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

# Configure Celery
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    # Timezone
    timezone="UTC",
    enable_utc=True,
    # Task settings
    task_track_started=True,
    task_time_limit=300,  # 5 minutes max per task
    task_soft_time_limit=240,  # 4 minutes soft limit
    # Result backend
    result_expires=3600,  # Results expire after 1 hour
    result_backend_transport_options={"master_name": "mymaster"},
    # Worker settings
    worker_prefetch_multiplier=1,  # Disable prefetching for fair distribution
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks
    # Routing
    task_routes={
        "tasks.dictionary_lookup": {"queue": "dictionary"},
        "tasks.llm_process": {"queue": "llm"},
        "tasks.batch_process": {"queue": "batch"},
    },
)

# Auto-discover tasks from app.tasks module
celery_app.autodiscover_tasks(["app.tasks"])
