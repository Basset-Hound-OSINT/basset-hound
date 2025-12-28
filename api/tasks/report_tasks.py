"""
Report Generation Tasks for Celery.

Provides background task processing for scheduled report generation.

Phase 13: Infrastructure - Celery Workers
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from . import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def generate_scheduled_report(self, schedule_id: str) -> Dict[str, Any]:
    """
    Generate a report for a specific schedule.

    This task is called when a scheduled report is due for execution.
    It retrieves the schedule, generates the report, and updates the
    schedule's last_run and next_run times.

    Args:
        schedule_id: The unique identifier of the schedule to execute

    Returns:
        Dict containing execution results:
        - success: Whether the report was generated successfully
        - schedule_id: The schedule ID
        - executed_at: When the report was generated
        - next_run: When the next report is scheduled
        - error: Error message if failed (optional)

    Raises:
        Retry: If the task should be retried due to transient errors
    """
    from api.services.scheduler_service import get_scheduler_service, ReportScheduler
    from api.services.report_export_service import ReportExportService
    from api.neo4j_handler import get_neo4j_handler

    logger.info(f"Starting report generation for schedule: {schedule_id}")

    try:
        # Get the scheduler service
        scheduler = get_scheduler_service()

        # Get the schedule
        schedule = scheduler.get_scheduled_report(schedule_id)
        if schedule is None:
            logger.error(f"Schedule not found: {schedule_id}")
            return {
                "success": False,
                "schedule_id": schedule_id,
                "error": f"Schedule not found: {schedule_id}",
            }

        if not schedule.enabled:
            logger.info(f"Schedule {schedule_id} is disabled, skipping")
            return {
                "success": False,
                "schedule_id": schedule_id,
                "error": "Schedule is disabled",
            }

        # Initialize services if needed
        if scheduler._report_service is None:
            try:
                neo4j_handler = get_neo4j_handler()
                scheduler._report_service = ReportExportService(neo4j_handler)
                scheduler._handler = neo4j_handler
            except Exception as e:
                logger.error(f"Failed to initialize report service: {e}")
                raise self.retry(exc=e)

        # Run the scheduled report
        result = scheduler.run_scheduled_report(schedule_id)

        logger.info(f"Report generation completed for schedule {schedule_id}: {result}")
        return result

    except Exception as e:
        logger.error(f"Error generating report for schedule {schedule_id}: {e}")

        # Retry for transient errors
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying task (attempt {self.request.retries + 1}/{self.max_retries})")
            raise self.retry(exc=e)

        return {
            "success": False,
            "schedule_id": schedule_id,
            "executed_at": datetime.now(timezone.utc).isoformat(),
            "error": str(e),
        }


@celery_app.task(bind=True)
def process_due_reports(self) -> Dict[str, Any]:
    """
    Find and process all reports that are due for execution.

    This task is called periodically by Celery Beat to check for
    and process any scheduled reports that are past their next_run time.

    Returns:
        Dict containing:
        - processed: Number of reports processed
        - successful: Number of successful report generations
        - failed: Number of failed report generations
        - schedule_ids: List of schedule IDs that were processed
    """
    from api.services.scheduler_service import get_scheduler_service

    logger.info("Processing due reports")

    try:
        scheduler = get_scheduler_service()
        now = datetime.now(timezone.utc)

        # Get all due schedules
        due_schedules = scheduler.get_due_reports(as_of=now)

        if not due_schedules:
            logger.debug("No due reports found")
            return {
                "processed": 0,
                "successful": 0,
                "failed": 0,
                "schedule_ids": [],
            }

        logger.info(f"Found {len(due_schedules)} due reports")

        processed = 0
        successful = 0
        failed = 0
        schedule_ids = []

        for schedule in due_schedules:
            try:
                # Queue the report generation as a separate task
                generate_scheduled_report.delay(schedule.id)
                processed += 1
                successful += 1
                schedule_ids.append(schedule.id)
                logger.info(f"Queued report generation for schedule: {schedule.id}")
            except Exception as e:
                failed += 1
                logger.error(f"Failed to queue report for schedule {schedule.id}: {e}")

        return {
            "processed": processed,
            "successful": successful,
            "failed": failed,
            "schedule_ids": schedule_ids,
        }

    except Exception as e:
        logger.error(f"Error processing due reports: {e}")
        return {
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "schedule_ids": [],
            "error": str(e),
        }


@celery_app.task(bind=True, max_retries=2, default_retry_delay=300)
def generate_report_async(
    self,
    project_id: str,
    report_type: str = "summary",
    title: Optional[str] = None,
    format: str = "html",
    entity_ids: Optional[list] = None,
) -> Dict[str, Any]:
    """
    Generate a report asynchronously (on-demand, not scheduled).

    This task allows users to request a report generation that runs
    in the background, useful for large reports that would timeout
    in a synchronous API call.

    Args:
        project_id: The project to generate the report for
        report_type: Type of report (summary, entity, custom)
        title: Optional report title
        format: Output format (html, pdf, markdown)
        entity_ids: Optional list of entity IDs to include

    Returns:
        Dict containing:
        - success: Whether the report was generated
        - project_id: The project ID
        - report_path: Path to the generated report (if successful)
        - error: Error message (if failed)
    """
    from api.services.report_export_service import (
        ReportExportService,
        ReportFormat,
        ReportOptions,
    )
    from api.neo4j_handler import get_neo4j_handler

    logger.info(f"Starting async report generation for project: {project_id}")

    try:
        # Initialize services
        neo4j_handler = get_neo4j_handler()
        report_service = ReportExportService(neo4j_handler)

        # Parse format
        format_map = {
            "pdf": ReportFormat.PDF,
            "html": ReportFormat.HTML,
            "markdown": ReportFormat.MARKDOWN,
            "md": ReportFormat.MARKDOWN,
        }
        report_format = format_map.get(format.lower(), ReportFormat.HTML)

        # Build options
        options = ReportOptions(
            title=title or f"{project_id} Report",
            format=report_format,
            project_id=project_id,
            entity_ids=entity_ids,
        )

        # Generate report based on type
        if report_type == "summary":
            result = report_service.generate_summary_report(project_id, options)
        elif report_type == "entity" and entity_ids:
            result = report_service.generate_entity_report(
                project_id, entity_ids[0], options
            )
        else:
            result = report_service.generate_summary_report(project_id, options)

        logger.info(f"Report generated successfully for project {project_id}")

        return {
            "success": True,
            "project_id": project_id,
            "report_type": report_type,
            "format": format,
            "report_size": len(result) if result else 0,
        }

    except Exception as e:
        logger.error(f"Error generating async report for project {project_id}: {e}")

        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)

        return {
            "success": False,
            "project_id": project_id,
            "error": str(e),
        }


__all__ = [
    'generate_scheduled_report',
    'process_due_reports',
    'generate_report_async',
]
