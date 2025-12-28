"""
Celery Task Module for Basset Hound OSINT Platform.

Provides distributed task processing for:
- Scheduled report generation
- Cache maintenance
- Background data processing

Phase 13: Infrastructure - Celery Workers
"""

import os
import logging

from celery import Celery

logger = logging.getLogger(__name__)

# Create Celery app
celery_app = Celery(
    'basset_hound',
    broker=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0'),
    include=[
        'api.tasks.report_tasks',
        'api.tasks.maintenance_tasks',
    ]
)

# Celery configuration
celery_app.conf.update(
    # Serialization
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',

    # Timezone
    timezone='UTC',
    enable_utc=True,

    # Task execution
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max per task
    task_soft_time_limit=3300,  # Soft limit 55 mins (allows cleanup)

    # Worker settings
    worker_prefetch_multiplier=1,  # One task at a time for long-running tasks
    task_acks_late=True,  # Acknowledge after completion

    # Result settings
    result_expires=86400,  # Results expire after 24 hours

    # Beat schedule for periodic tasks
    beat_schedule={
        'process-due-reports-every-minute': {
            'task': 'api.tasks.report_tasks.process_due_reports',
            'schedule': 60.0,  # Run every minute
        },
        'cleanup-expired-cache-hourly': {
            'task': 'api.tasks.maintenance_tasks.cleanup_expired_cache',
            'schedule': 3600.0,  # Run every hour
        },
    },
)


def get_celery_app() -> Celery:
    """Get the Celery application instance."""
    return celery_app


__all__ = ['celery_app', 'get_celery_app']
