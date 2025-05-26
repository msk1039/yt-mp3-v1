"""
Celery application configuration for YouTube to MP3 converter.
This module sets up Celery with Redis backend for distributed task processing.
"""

import os
from celery import Celery
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get Redis URL from environment
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

# Create Celery app
celery_app = Celery(
    "yt_mp3_converter",
    broker=redis_url,
    backend=redis_url,
    include=[
        "download_service.worker",
        "conversion_service.worker", 
        "file_service.cleanup"
    ]
)

# Celery configuration
celery_app.conf.update(
    # Task routing
    task_routes={
        "download_service.worker.download_audio_task": {"queue": "download"},
        "conversion_service.worker.convert_to_mp3_task": {"queue": "conversion"},
        "file_service.cleanup.cleanup_task": {"queue": "cleanup"},
    },
    
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task expiration
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    
    # Result backend settings
    result_expires=3600,  # 1 hour
    
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    
    # Task retry settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)

# Optional: Configure task routing for different workers
# This allows scaling specific types of tasks independently
celery_app.conf.task_routes = {
    "download_service.*": {"queue": "download"},
    "conversion_service.*": {"queue": "conversion"},
    "file_service.*": {"queue": "cleanup"},
}

if __name__ == "__main__":
    celery_app.start()
