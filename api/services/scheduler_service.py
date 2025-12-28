"""
Report Scheduling Service for Basset Hound OSINT Platform

This module provides comprehensive scheduled report generation capabilities.
It supports various scheduling frequencies including custom cron expressions
and manages the lifecycle of scheduled reports.

Features:
- Multiple scheduling frequencies (ONCE, HOURLY, DAILY, WEEKLY, MONTHLY)
- Custom cron expression support via croniter library
- Schedule management (create, update, delete, enable, disable)
- Due schedule detection
- Automated report execution with last_run and next_run tracking
- In-memory storage with persistence hooks for future database migration
- Timezone-aware datetime handling
"""

import logging
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from .report_export_service import (
    ReportExportService,
    ReportFormat,
    ReportOptions,
    ReportSection,
)

logger = logging.getLogger(__name__)


class ScheduleFrequency(str, Enum):
    """Supported scheduling frequencies for report generation."""
    ONCE = "once"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class ReportConfig(BaseModel):
    """Configuration for report generation within a schedule."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Weekly Investigation Summary",
                "format": "html",
                "report_type": "summary",
                "entity_ids": None,
                "include_graph": True,
                "include_timeline": True,
                "include_statistics": True,
                "template": "default",
                "sections": None
            }
        }
    )

    title: str = Field(..., min_length=1, max_length=500, description="Report title")
    format: str = Field(default="html", description="Output format: pdf, html, or markdown")
    report_type: str = Field(default="summary", description="Report type: summary, custom, or entity")
    entity_ids: Optional[List[str]] = Field(default=None, description="Specific entity IDs to include")
    include_graph: bool = Field(default=True, description="Include relationship graph")
    include_timeline: bool = Field(default=True, description="Include timeline")
    include_statistics: bool = Field(default=True, description="Include statistics")
    template: str = Field(default="default", description="Template name for styling")
    sections: Optional[List[Dict[str, Any]]] = Field(default=None, description="Custom sections")


class ScheduledReport(BaseModel):
    """
    Represents a scheduled report configuration.

    This model holds all the information needed to execute a report
    on a schedule, including timing, configuration, and status.
    """
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "project_id": "test_project",
                "report_config": {
                    "title": "Daily Summary",
                    "format": "html",
                    "report_type": "summary"
                },
                "frequency": "daily",
                "next_run": "2024-01-16T10:00:00Z",
                "last_run": None,
                "created_at": "2024-01-15T10:00:00Z",
                "enabled": True,
                "cron_expression": None
            }
        }
    )

    id: str = Field(..., description="Unique identifier for the schedule (UUID)")
    project_id: str = Field(..., description="ID of the project this schedule belongs to")
    report_config: ReportConfig = Field(..., description="Report generation configuration")
    frequency: ScheduleFrequency = Field(..., description="How often the report should be generated")
    next_run: datetime = Field(..., description="When the report should next be executed (UTC)")
    last_run: Optional[datetime] = Field(default=None, description="When the report was last executed (UTC)")
    created_at: datetime = Field(..., description="When the schedule was created (UTC)")
    enabled: bool = Field(default=True, description="Whether the schedule is currently active")
    cron_expression: Optional[str] = Field(
        default=None,
        description="Optional cron expression for custom scheduling (overrides frequency)"
    )


class ReportScheduler:
    """
    Service for managing scheduled report generation.

    Provides methods for creating, updating, deleting, and executing
    scheduled reports. Stores schedules in memory with interfaces
    designed for future database storage migration.
    """

    def __init__(
        self,
        neo4j_handler=None,
        report_service: Optional[ReportExportService] = None,
        persistence_save: Optional[Callable[[Dict[str, ScheduledReport]], None]] = None,
        persistence_load: Optional[Callable[[], Dict[str, ScheduledReport]]] = None
    ):
        """
        Initialize the report scheduler.

        Args:
            neo4j_handler: Neo4j database handler instance (optional)
            report_service: ReportExportService instance for generating reports
            persistence_save: Optional callback for persisting schedules
            persistence_load: Optional callback for loading persisted schedules
        """
        self._handler = neo4j_handler
        self._report_service = report_service
        self._persistence_save = persistence_save
        self._persistence_load = persistence_load

        # In-memory storage for schedules, keyed by schedule ID
        self._schedules: Dict[str, ScheduledReport] = {}

        # Load persisted schedules if available
        if self._persistence_load:
            try:
                self._schedules = self._persistence_load()
                logger.info(f"Loaded {len(self._schedules)} persisted schedules")
            except Exception as e:
                logger.warning(f"Failed to load persisted schedules: {e}")

    def _save_schedules(self) -> None:
        """Persist schedules if persistence hook is configured."""
        if self._persistence_save:
            try:
                self._persistence_save(self._schedules)
            except Exception as e:
                logger.warning(f"Failed to persist schedules: {e}")

    def _ensure_timezone_aware(self, dt: Optional[datetime]) -> Optional[datetime]:
        """Ensure a datetime is timezone-aware (UTC)."""
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    def schedule_report(
        self,
        project_id: str,
        report_config: ReportConfig,
        frequency: ScheduleFrequency,
        start_time: Optional[datetime] = None,
        cron_expression: Optional[str] = None,
        enabled: bool = True
    ) -> ScheduledReport:
        """
        Create a new scheduled report.

        Args:
            project_id: ID of the project for the report
            report_config: ReportConfig with report generation settings
            frequency: How often to generate the report
            start_time: When to first run the report (defaults to now)
            cron_expression: Optional cron expression for custom scheduling
            enabled: Whether the schedule should be enabled immediately

        Returns:
            ScheduledReport: The created schedule

        Raises:
            ValueError: If project_id is empty or invalid cron expression
        """
        if not project_id or not project_id.strip():
            raise ValueError("project_id is required")

        now = datetime.now(timezone.utc)
        schedule_id = str(uuid4())

        # Calculate next_run time
        if start_time is not None:
            next_run = self._ensure_timezone_aware(start_time)
            # If start_time is in the past, calculate the next occurrence
            if next_run < now and frequency != ScheduleFrequency.ONCE:
                next_run = self._calculate_next_from_past(next_run, now, frequency, cron_expression)
        elif cron_expression:
            next_run = self._calculate_next_cron(cron_expression, now)
        else:
            next_run = now

        # Validate cron expression if provided
        if cron_expression:
            self._validate_cron_expression(cron_expression)

        schedule = ScheduledReport(
            id=schedule_id,
            project_id=project_id.strip(),
            report_config=report_config,
            frequency=frequency,
            next_run=next_run,
            last_run=None,
            created_at=now,
            enabled=enabled,
            cron_expression=cron_expression
        )

        self._schedules[schedule_id] = schedule
        self._save_schedules()
        logger.info(f"Created schedule {schedule_id} for project {project_id}")

        return schedule

    def _calculate_next_from_past(
        self,
        past_time: datetime,
        now: datetime,
        frequency: ScheduleFrequency,
        cron_expression: Optional[str] = None
    ) -> datetime:
        """Calculate the next run time when start_time was in the past."""
        if cron_expression:
            return self._calculate_next_cron(cron_expression, now)

        # Keep adding intervals until we're in the future
        next_run = past_time
        while next_run <= now:
            next_run = self.calculate_next_run(frequency, next_run)
            if frequency == ScheduleFrequency.ONCE:
                break  # Don't loop forever for ONCE frequency

        return next_run

    def _validate_cron_expression(self, cron_expression: str) -> None:
        """Validate a cron expression."""
        try:
            from croniter import croniter
            # Try to create a croniter instance to validate the expression
            croniter(cron_expression, datetime.now(timezone.utc))
        except ImportError:
            # croniter not available, skip validation
            logger.warning("croniter library not available, skipping cron validation")
        except Exception as e:
            raise ValueError(f"Invalid cron expression '{cron_expression}': {e}")

    def _calculate_next_cron(self, cron_expression: str, from_time: datetime) -> datetime:
        """Calculate next run time from a cron expression."""
        try:
            from croniter import croniter
            cron = croniter(cron_expression, from_time)
            next_time = cron.get_next(datetime)
            # Ensure timezone awareness
            if next_time.tzinfo is None:
                next_time = next_time.replace(tzinfo=timezone.utc)
            return next_time
        except ImportError:
            logger.warning("croniter library not available, using default interval")
            return from_time + timedelta(days=1)

    def unschedule_report(self, schedule_id: str) -> bool:
        """
        Remove a scheduled report.

        Args:
            schedule_id: The ID of the schedule to remove

        Returns:
            True if the schedule was removed, False if not found
        """
        if schedule_id in self._schedules:
            del self._schedules[schedule_id]
            self._save_schedules()
            logger.info(f"Removed schedule {schedule_id}")
            return True
        return False

    def get_scheduled_reports(
        self,
        project_id: Optional[str] = None,
        enabled_only: bool = False
    ) -> List[ScheduledReport]:
        """
        Get scheduled reports, optionally filtered by project.

        Args:
            project_id: Filter by project ID (None = all projects)
            enabled_only: If True, only return enabled schedules

        Returns:
            List of ScheduledReport objects
        """
        schedules = list(self._schedules.values())

        if project_id is not None:
            schedules = [s for s in schedules if s.project_id == project_id]

        if enabled_only:
            schedules = [s for s in schedules if s.enabled]

        # Sort by next_run time
        schedules.sort(key=lambda s: s.next_run)

        return schedules

    def get_scheduled_report(self, schedule_id: str) -> Optional[ScheduledReport]:
        """
        Get a specific scheduled report by ID.

        Args:
            schedule_id: The unique identifier of the schedule

        Returns:
            ScheduledReport if found, None otherwise
        """
        return self._schedules.get(schedule_id)

    def update_schedule(
        self,
        schedule_id: str,
        frequency: Optional[ScheduleFrequency] = None,
        enabled: Optional[bool] = None,
        report_config: Optional[ReportConfig] = None,
        next_run: Optional[datetime] = None,
        cron_expression: Optional[str] = None
    ) -> Optional[ScheduledReport]:
        """
        Update an existing schedule.

        Args:
            schedule_id: The ID of the schedule to update
            frequency: New frequency (optional)
            enabled: New enabled state (optional)
            report_config: New report configuration (optional)
            next_run: New next run time (optional)
            cron_expression: New cron expression (optional, use empty string to clear)

        Returns:
            Updated ScheduledReport if found, None otherwise
        """
        schedule = self._schedules.get(schedule_id)
        if schedule is None:
            return None

        # Validate cron expression if provided
        if cron_expression is not None and cron_expression != "":
            self._validate_cron_expression(cron_expression)

        # Build updated schedule
        updated_data = schedule.model_dump()

        if frequency is not None:
            updated_data["frequency"] = frequency
        if enabled is not None:
            updated_data["enabled"] = enabled
        if report_config is not None:
            updated_data["report_config"] = report_config
        if next_run is not None:
            updated_data["next_run"] = self._ensure_timezone_aware(next_run)
        if cron_expression is not None:
            updated_data["cron_expression"] = cron_expression if cron_expression else None

        updated_schedule = ScheduledReport(**updated_data)
        self._schedules[schedule_id] = updated_schedule
        self._save_schedules()
        logger.info(f"Updated schedule {schedule_id}")

        return updated_schedule

    def get_due_reports(
        self,
        as_of: Optional[datetime] = None,
        project_id: Optional[str] = None
    ) -> List[ScheduledReport]:
        """
        Get all schedules that are due to run.

        A schedule is considered due if:
        - It is enabled
        - Its next_run time is <= the current time (or as_of time)

        Args:
            as_of: The reference time (defaults to now UTC)
            project_id: Filter by project ID (optional)

        Returns:
            List of due ScheduledReport objects, sorted oldest first
        """
        if as_of is None:
            as_of = datetime.now(timezone.utc)
        else:
            as_of = self._ensure_timezone_aware(as_of)

        due_schedules = []
        for schedule in self._schedules.values():
            if not schedule.enabled:
                continue
            if project_id is not None and schedule.project_id != project_id:
                continue
            if schedule.next_run <= as_of:
                due_schedules.append(schedule)

        # Sort by next_run (oldest first)
        due_schedules.sort(key=lambda s: s.next_run)

        return due_schedules

    def run_scheduled_report(self, schedule_id: str) -> dict:
        """
        Execute a scheduled report immediately.

        This method:
        1. Generates the report using the configured options
        2. Updates last_run to now
        3. Calculates and sets the next_run time based on frequency/cron
        4. For ONCE frequency, disables the schedule after execution

        Args:
            schedule_id: The ID of the schedule to run

        Returns:
            dict with execution results:
                - success: bool
                - report_bytes: bytes (if successful)
                - report_size: int (if successful)
                - executed_at: datetime
                - next_run: datetime
                - error: str (if failed)

        Raises:
            ValueError: If report_service is not configured or schedule not found
        """
        schedule = self._schedules.get(schedule_id)
        if schedule is None:
            raise ValueError(f"Schedule not found: {schedule_id}")

        if self._report_service is None:
            raise ValueError("report_service is not configured")

        now = datetime.now(timezone.utc)
        result = {
            "success": False,
            "executed_at": now,
            "schedule_id": schedule_id
        }

        try:
            # Build ReportOptions from ReportConfig
            report_options = self._build_report_options(schedule)

            # Generate the report based on report_type
            report_config = schedule.report_config
            if report_config.report_type == "summary":
                report_bytes = self._report_service.generate_project_summary(
                    schedule.project_id,
                    ReportFormat(report_config.format)
                )
            elif report_config.report_type == "entity":
                if report_config.entity_ids and len(report_config.entity_ids) > 0:
                    report_bytes = self._report_service.generate_entity_report(
                        schedule.project_id,
                        report_config.entity_ids[0],
                        ReportFormat(report_config.format)
                    )
                else:
                    raise ValueError("entity_ids required for entity report type")
            else:
                # Default to custom report
                report_bytes = self._report_service.generate_report(report_options)

            logger.info(f"Generated report for schedule {schedule_id}")

            result["success"] = True
            result["report_bytes"] = report_bytes
            result["report_size"] = len(report_bytes)

        except Exception as e:
            logger.error(f"Failed to generate report for schedule {schedule_id}: {e}")
            result["error"] = str(e)
            # Still update timing even on failure
            report_bytes = None

        # Calculate next run time
        if schedule.cron_expression:
            next_run = self._calculate_next_cron(schedule.cron_expression, now)
        else:
            next_run = self.calculate_next_run(schedule.frequency, now)

        # Update schedule
        new_enabled = schedule.enabled
        if schedule.frequency == ScheduleFrequency.ONCE:
            new_enabled = False

        updated_data = schedule.model_dump()
        updated_data["last_run"] = now
        updated_data["next_run"] = next_run
        updated_data["enabled"] = new_enabled

        updated_schedule = ScheduledReport(**updated_data)
        self._schedules[schedule_id] = updated_schedule
        self._save_schedules()

        result["next_run"] = next_run

        return result

    def _build_report_options(self, schedule: ScheduledReport) -> ReportOptions:
        """Build ReportOptions from a ScheduledReport."""
        config = schedule.report_config

        # Parse format
        try:
            report_format = ReportFormat(config.format.lower())
        except ValueError:
            report_format = ReportFormat.HTML

        # Build sections if provided
        sections = None
        if config.sections:
            sections = [
                ReportSection(
                    title=s.get("title", ""),
                    content=s.get("content", ""),
                    entities=s.get("entities", []),
                    include_relationships=s.get("include_relationships", True),
                    include_timeline=s.get("include_timeline", False)
                )
                for s in config.sections
            ]

        return ReportOptions(
            title=config.title,
            format=report_format,
            project_id=schedule.project_id,
            entity_ids=config.entity_ids,
            sections=sections,
            include_graph=config.include_graph,
            include_timeline=config.include_timeline,
            include_statistics=config.include_statistics,
            template=config.template
        )

    def calculate_next_run(
        self,
        frequency: ScheduleFrequency,
        from_time: Optional[datetime] = None
    ) -> datetime:
        """
        Calculate the next run time based on frequency.

        Args:
            frequency: The scheduling frequency
            from_time: The reference time (defaults to now UTC)

        Returns:
            The next run time as a timezone-aware datetime (UTC)
        """
        if from_time is None:
            from_time = datetime.now(timezone.utc)
        else:
            from_time = self._ensure_timezone_aware(from_time)

        if frequency == ScheduleFrequency.ONCE:
            # For ONCE, return the same time (no next occurrence)
            return from_time

        elif frequency == ScheduleFrequency.HOURLY:
            return from_time + timedelta(hours=1)

        elif frequency == ScheduleFrequency.DAILY:
            return from_time + timedelta(days=1)

        elif frequency == ScheduleFrequency.WEEKLY:
            return from_time + timedelta(weeks=1)

        elif frequency == ScheduleFrequency.MONTHLY:
            # Handle month transition properly
            next_month = from_time.month + 1
            next_year = from_time.year

            if next_month > 12:
                next_month = 1
                next_year += 1

            # Handle day overflow (e.g., Jan 31 -> Feb 28)
            day = from_time.day
            max_day = self._get_days_in_month(next_year, next_month)
            day = min(day, max_day)

            return datetime(
                year=next_year,
                month=next_month,
                day=day,
                hour=from_time.hour,
                minute=from_time.minute,
                second=from_time.second,
                microsecond=from_time.microsecond,
                tzinfo=timezone.utc
            )

        else:
            # Default fallback
            return from_time + timedelta(days=1)

    def _get_days_in_month(self, year: int, month: int) -> int:
        """Get the number of days in a given month."""
        if month in (4, 6, 9, 11):
            return 30
        elif month == 2:
            # Check for leap year
            if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0):
                return 29
            else:
                return 28
        else:
            return 31

    def enable_schedule(self, schedule_id: str) -> Optional[ScheduledReport]:
        """
        Enable a schedule.

        Args:
            schedule_id: The ID of the schedule to enable

        Returns:
            Updated ScheduledReport if found, None otherwise
        """
        return self.update_schedule(schedule_id, enabled=True)

    def disable_schedule(self, schedule_id: str) -> Optional[ScheduledReport]:
        """
        Disable a schedule.

        Args:
            schedule_id: The ID of the schedule to disable

        Returns:
            Updated ScheduledReport if found, None otherwise
        """
        return self.update_schedule(schedule_id, enabled=False)

    def get_all_schedules(self) -> List[ScheduledReport]:
        """
        Get all schedules across all projects.

        Returns:
            List of all ScheduledReport objects
        """
        return list(self._schedules.values())

    def clear_all_schedules(self) -> int:
        """
        Clear all schedules from storage.

        Returns:
            Number of schedules that were cleared
        """
        count = len(self._schedules)
        self._schedules.clear()
        self._save_schedules()
        logger.info(f"Cleared {count} schedules")
        return count

    def get_schedule_count(self, project_id: Optional[str] = None) -> int:
        """
        Get the count of schedules.

        Args:
            project_id: Filter by project ID (optional)

        Returns:
            Number of schedules
        """
        if project_id is None:
            return len(self._schedules)
        return len([s for s in self._schedules.values() if s.project_id == project_id])


# Singleton instance management
_scheduler_service: Optional[ReportScheduler] = None


def get_scheduler_service(
    neo4j_handler=None,
    report_service: Optional[ReportExportService] = None
) -> ReportScheduler:
    """
    Get or create the scheduler service singleton.

    Args:
        neo4j_handler: Neo4j handler instance (optional)
        report_service: ReportExportService instance (optional)

    Returns:
        ReportScheduler instance
    """
    global _scheduler_service

    if _scheduler_service is None:
        _scheduler_service = ReportScheduler(neo4j_handler, report_service)

    return _scheduler_service


def set_scheduler_service(scheduler: Optional[ReportScheduler]) -> None:
    """Set the scheduler service singleton (for testing)."""
    global _scheduler_service
    _scheduler_service = scheduler
