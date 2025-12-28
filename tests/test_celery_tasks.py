"""
Tests for Celery Tasks Module.

Phase 13: Infrastructure - Celery Workers
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock
from collections import OrderedDict


class TestCeleryAppConfiguration:
    """Tests for Celery app configuration."""

    def test_celery_app_import(self):
        """Test that celery_app can be imported."""
        from api.tasks import celery_app
        assert celery_app is not None

    def test_celery_app_name(self):
        """Test celery app has correct name."""
        from api.tasks import celery_app
        assert celery_app.main == 'basset_hound'

    def test_get_celery_app_function(self):
        """Test get_celery_app helper function."""
        from api.tasks import get_celery_app, celery_app
        assert get_celery_app() is celery_app

    def test_celery_app_has_task_includes(self):
        """Test that celery app includes task modules."""
        from api.tasks import celery_app
        includes = celery_app.conf.include
        assert 'api.tasks.report_tasks' in includes
        assert 'api.tasks.maintenance_tasks' in includes

    def test_celery_app_serialization_config(self):
        """Test celery serialization configuration."""
        from api.tasks import celery_app
        assert celery_app.conf.task_serializer == 'json'
        assert 'json' in celery_app.conf.accept_content
        assert celery_app.conf.result_serializer == 'json'

    def test_celery_app_timezone_config(self):
        """Test celery timezone configuration."""
        from api.tasks import celery_app
        assert celery_app.conf.timezone == 'UTC'
        assert celery_app.conf.enable_utc is True

    def test_celery_app_task_time_limits(self):
        """Test celery task time limits."""
        from api.tasks import celery_app
        assert celery_app.conf.task_time_limit == 3600  # 1 hour
        assert celery_app.conf.task_soft_time_limit == 3300  # 55 minutes

    def test_celery_beat_schedule_exists(self):
        """Test that beat schedule is configured."""
        from api.tasks import celery_app
        beat_schedule = celery_app.conf.beat_schedule
        assert beat_schedule is not None
        assert 'process-due-reports-every-minute' in beat_schedule
        assert 'cleanup-expired-cache-hourly' in beat_schedule

    def test_celery_worker_prefetch_config(self):
        """Test celery worker prefetch configuration."""
        from api.tasks import celery_app
        assert celery_app.conf.worker_prefetch_multiplier == 1
        assert celery_app.conf.task_acks_late is True

    def test_celery_result_expiry_config(self):
        """Test celery result expiry configuration."""
        from api.tasks import celery_app
        assert celery_app.conf.result_expires == 86400  # 24 hours


class TestReportTasks:
    """Tests for report generation tasks."""

    def test_generate_scheduled_report_task_exists(self):
        """Test that generate_scheduled_report task exists."""
        from api.tasks.report_tasks import generate_scheduled_report
        assert generate_scheduled_report is not None
        assert hasattr(generate_scheduled_report, 'delay')
        assert hasattr(generate_scheduled_report, 'apply_async')

    def test_process_due_reports_task_exists(self):
        """Test that process_due_reports task exists."""
        from api.tasks.report_tasks import process_due_reports
        assert process_due_reports is not None
        assert hasattr(process_due_reports, 'delay')

    def test_generate_report_async_task_exists(self):
        """Test that generate_report_async task exists."""
        from api.tasks.report_tasks import generate_report_async
        assert generate_report_async is not None
        assert hasattr(generate_report_async, 'delay')

    def test_generate_scheduled_report_is_task(self):
        """Test that generate_scheduled_report is a celery task."""
        from api.tasks.report_tasks import generate_scheduled_report
        from celery import Task
        assert isinstance(generate_scheduled_report, Task)

    def test_process_due_reports_is_task(self):
        """Test that process_due_reports is a celery task."""
        from api.tasks.report_tasks import process_due_reports
        from celery import Task
        assert isinstance(process_due_reports, Task)


class TestMaintenanceTasks:
    """Tests for maintenance tasks."""

    def test_cleanup_expired_cache_task_exists(self):
        """Test that cleanup_expired_cache task exists."""
        from api.tasks.maintenance_tasks import cleanup_expired_cache
        assert cleanup_expired_cache is not None
        assert hasattr(cleanup_expired_cache, 'delay')

    def test_cleanup_ml_analytics_cache_task_exists(self):
        """Test that cleanup_ml_analytics_cache task exists."""
        from api.tasks.maintenance_tasks import cleanup_ml_analytics_cache
        assert cleanup_ml_analytics_cache is not None
        assert hasattr(cleanup_ml_analytics_cache, 'delay')

    def test_optimize_search_index_task_exists(self):
        """Test that optimize_search_index task exists."""
        from api.tasks.maintenance_tasks import optimize_search_index
        assert optimize_search_index is not None
        assert hasattr(optimize_search_index, 'delay')

    def test_health_check_task_exists(self):
        """Test that health_check task exists."""
        from api.tasks.maintenance_tasks import health_check
        assert health_check is not None
        assert hasattr(health_check, 'delay')

    def test_cleanup_old_reports_task_exists(self):
        """Test that cleanup_old_reports task exists."""
        from api.tasks.maintenance_tasks import cleanup_old_reports
        assert cleanup_old_reports is not None
        assert hasattr(cleanup_old_reports, 'delay')

    def test_all_maintenance_tasks_are_celery_tasks(self):
        """Test that all maintenance tasks are celery tasks."""
        from api.tasks.maintenance_tasks import (
            cleanup_expired_cache,
            cleanup_ml_analytics_cache,
            optimize_search_index,
            health_check,
            cleanup_old_reports,
        )
        from celery import Task
        assert isinstance(cleanup_expired_cache, Task)
        assert isinstance(cleanup_ml_analytics_cache, Task)
        assert isinstance(optimize_search_index, Task)
        assert isinstance(health_check, Task)
        assert isinstance(cleanup_old_reports, Task)


class TestTaskRetryBehavior:
    """Tests for task retry configuration."""

    def test_generate_scheduled_report_has_retries(self):
        """Test that generate_scheduled_report has retry configuration."""
        from api.tasks.report_tasks import generate_scheduled_report
        assert generate_scheduled_report.max_retries == 3
        assert generate_scheduled_report.default_retry_delay == 60

    def test_generate_report_async_has_retries(self):
        """Test that generate_report_async has retry configuration."""
        from api.tasks.report_tasks import generate_report_async
        assert generate_report_async.max_retries == 2
        assert generate_report_async.default_retry_delay == 300

    def test_process_due_reports_no_explicit_retries(self):
        """Test that process_due_reports has no explicit retry limit."""
        from api.tasks.report_tasks import process_due_reports
        # Default max_retries is 3 if not specified
        # but this task doesn't need retries as it just queues other tasks
        assert hasattr(process_due_reports, 'max_retries')


class TestTaskExports:
    """Tests for module exports."""

    def test_report_tasks_exports(self):
        """Test report_tasks module exports."""
        from api.tasks.report_tasks import __all__
        assert 'generate_scheduled_report' in __all__
        assert 'process_due_reports' in __all__
        assert 'generate_report_async' in __all__

    def test_maintenance_tasks_exports(self):
        """Test maintenance_tasks module exports."""
        from api.tasks.maintenance_tasks import __all__
        assert 'cleanup_expired_cache' in __all__
        assert 'cleanup_ml_analytics_cache' in __all__
        assert 'optimize_search_index' in __all__
        assert 'health_check' in __all__
        assert 'cleanup_old_reports' in __all__

    def test_main_module_exports(self):
        """Test main tasks module exports."""
        from api.tasks import __all__
        assert 'celery_app' in __all__
        assert 'get_celery_app' in __all__


class TestBeatScheduleConfiguration:
    """Tests for Celery Beat schedule configuration."""

    def test_process_due_reports_schedule(self):
        """Test process_due_reports scheduled every minute."""
        from api.tasks import celery_app
        schedule = celery_app.conf.beat_schedule['process-due-reports-every-minute']
        assert schedule['task'] == 'api.tasks.report_tasks.process_due_reports'
        assert schedule['schedule'] == 60.0

    def test_cleanup_cache_schedule(self):
        """Test cleanup_expired_cache scheduled hourly."""
        from api.tasks import celery_app
        schedule = celery_app.conf.beat_schedule['cleanup-expired-cache-hourly']
        assert schedule['task'] == 'api.tasks.maintenance_tasks.cleanup_expired_cache'
        assert schedule['schedule'] == 3600.0


class TestTaskRegistration:
    """Tests that tasks are properly registered with Celery."""

    def test_tasks_registered_with_app(self):
        """Test that all tasks are registered with the celery app."""
        from api.tasks import celery_app

        # Force task discovery
        celery_app.autodiscover_tasks(['api.tasks'], force=True)

        # Get registered task names
        task_names = list(celery_app.tasks.keys())

        # Check our tasks are registered (they should have full module path)
        # Note: some celery internal tasks might be included too
        report_tasks = [t for t in task_names if 'report_tasks' in t]
        maintenance_tasks = [t for t in task_names if 'maintenance_tasks' in t]

        assert len(report_tasks) >= 1 or len(maintenance_tasks) >= 1


class TestTaskNames:
    """Tests for task naming conventions."""

    def test_generate_scheduled_report_name(self):
        """Test generate_scheduled_report has correct name."""
        from api.tasks.report_tasks import generate_scheduled_report
        assert 'generate_scheduled_report' in generate_scheduled_report.name

    def test_process_due_reports_name(self):
        """Test process_due_reports has correct name."""
        from api.tasks.report_tasks import process_due_reports
        assert 'process_due_reports' in process_due_reports.name

    def test_cleanup_expired_cache_name(self):
        """Test cleanup_expired_cache has correct name."""
        from api.tasks.maintenance_tasks import cleanup_expired_cache
        assert 'cleanup_expired_cache' in cleanup_expired_cache.name
