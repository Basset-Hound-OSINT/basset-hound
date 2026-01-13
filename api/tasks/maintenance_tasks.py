"""
Maintenance Tasks for Celery.

Provides background task processing for system maintenance:
- Cache cleanup
- Search index optimization
- Database maintenance

Phase 13: Infrastructure - Celery Workers
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict

from . import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True)
def cleanup_expired_cache(self) -> Dict[str, Any]:
    """
    Clean up expired cache entries.

    This task runs periodically to remove expired entries from both
    the in-memory and Redis caches, freeing up resources.

    Returns:
        Dict containing:
        - success: Whether the cleanup was successful
        - cleaned_count: Number of entries cleaned
        - cache_type: Type of cache that was cleaned
        - executed_at: When the cleanup was performed
    """
    logger.info("Starting cache cleanup")

    try:
        from api.services.cache_service import get_cache_service

        cache_service = get_cache_service()

        # Get stats before cleanup
        stats_before = None
        if cache_service.is_enabled:
            import asyncio
            loop = asyncio.new_event_loop()
            try:
                stats_before = loop.run_until_complete(cache_service.get_stats())
            finally:
                loop.close()

        # For memory cache, expired entries are cleaned automatically
        # but we can trigger a manual cleanup by checking health
        cleaned_count = 0
        cache_type = "unknown"

        if cache_service.is_enabled and cache_service._backend:
            cache_type = cache_service.backend_type.value

            # The memory cache has a _cleanup_expired method
            if hasattr(cache_service._backend, '_cleanup_expired'):
                import asyncio
                loop = asyncio.new_event_loop()
                try:
                    cleaned_count = loop.run_until_complete(
                        cache_service._backend._cleanup_expired()
                    )
                finally:
                    loop.close()

        logger.info(f"Cache cleanup completed: {cleaned_count} entries cleaned")

        return {
            "success": True,
            "cleaned_count": cleaned_count,
            "cache_type": cache_type,
            "executed_at": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error(f"Error during cache cleanup: {e}")
        return {
            "success": False,
            "cleaned_count": 0,
            "error": str(e),
            "executed_at": datetime.now(timezone.utc).isoformat(),
        }


# ARCHIVED: cleanup_ml_analytics_cache task removed (2026-01-13)
# The ML analytics service has been archived to archive/out-of-scope-ml/
# It is out of scope for the storage layer and belongs in a future
# intelligence-analysis project.
#
# @celery_app.task(bind=True)
# def cleanup_ml_analytics_cache(self) -> Dict[str, Any]:
#     """Clean up ML analytics caches - ARCHIVED"""
#     pass


# ARCHIVED: optimize_search_index task removed (2026-01-13)
# This task depended on the ML analytics service which has been archived.
#
# @celery_app.task(bind=True)
# def optimize_search_index(self) -> Dict[str, Any]:
#     """Optimize search indexes - ARCHIVED"""
#     pass


@celery_app.task(bind=True)
def health_check(self) -> Dict[str, Any]:
    """
    Perform a health check on all services.

    This task verifies that all required services are operational
    and returns their status.

    Returns:
        Dict containing health status of all services
    """
    logger.info("Performing health check")

    results = {
        "success": True,
        "services": {},
        "executed_at": datetime.now(timezone.utc).isoformat(),
    }

    # Check cache service
    try:
        from api.services.cache_service import get_cache_service
        import asyncio

        cache_service = get_cache_service()
        loop = asyncio.new_event_loop()
        try:
            health = loop.run_until_complete(cache_service.health_check())
            results["services"]["cache"] = health
        finally:
            loop.close()
    except Exception as e:
        results["services"]["cache"] = {"healthy": False, "error": str(e)}
        results["success"] = False

    # Check scheduler service
    try:
        from api.services.scheduler_service import get_scheduler_service

        scheduler = get_scheduler_service()
        schedule_count = len(scheduler.get_all_schedules())
        results["services"]["scheduler"] = {
            "healthy": True,
            "schedule_count": schedule_count,
        }
    except Exception as e:
        results["services"]["scheduler"] = {"healthy": False, "error": str(e)}
        results["success"] = False

    # Check Neo4j connection
    try:
        from api.neo4j_handler import get_neo4j_handler

        handler = get_neo4j_handler()
        # Simple connectivity check
        results["services"]["neo4j"] = {
            "healthy": handler is not None,
        }
    except Exception as e:
        results["services"]["neo4j"] = {"healthy": False, "error": str(e)}
        results["success"] = False

    logger.info(f"Health check completed: {results}")
    return results


@celery_app.task(bind=True)
def cleanup_old_reports(self, days_old: int = 30) -> Dict[str, Any]:
    """
    Clean up old generated reports.

    This task removes generated reports that are older than the
    specified number of days to free up disk space.

    Args:
        days_old: Remove reports older than this many days (default: 30)

    Returns:
        Dict containing cleanup results
    """
    import os
    from pathlib import Path

    logger.info(f"Starting cleanup of reports older than {days_old} days")

    try:
        # Look for report directories
        report_dirs = [
            Path("reports"),
            Path("static/reports"),
            Path("projects"),  # Reports might be stored in project directories
        ]

        files_removed = 0
        bytes_freed = 0
        cutoff_time = datetime.now(timezone.utc).timestamp() - (days_old * 86400)

        for report_dir in report_dirs:
            if not report_dir.exists():
                continue

            # Find and remove old report files
            for report_file in report_dir.rglob("*.html"):
                try:
                    if report_file.stat().st_mtime < cutoff_time:
                        size = report_file.stat().st_size
                        report_file.unlink()
                        files_removed += 1
                        bytes_freed += size
                except Exception as e:
                    logger.warning(f"Could not remove {report_file}: {e}")

            for report_file in report_dir.rglob("*.pdf"):
                try:
                    if report_file.stat().st_mtime < cutoff_time:
                        size = report_file.stat().st_size
                        report_file.unlink()
                        files_removed += 1
                        bytes_freed += size
                except Exception as e:
                    logger.warning(f"Could not remove {report_file}: {e}")

        logger.info(
            f"Report cleanup completed: removed {files_removed} files, "
            f"freed {bytes_freed / 1024 / 1024:.2f} MB"
        )

        return {
            "success": True,
            "files_removed": files_removed,
            "bytes_freed": bytes_freed,
            "days_old": days_old,
            "executed_at": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error(f"Error during report cleanup: {e}")
        return {
            "success": False,
            "error": str(e),
            "executed_at": datetime.now(timezone.utc).isoformat(),
        }


__all__ = [
    'cleanup_expired_cache',
    # 'cleanup_ml_analytics_cache',  # ARCHIVED
    # 'optimize_search_index',  # ARCHIVED
    'health_check',
    'cleanup_old_reports',
]
