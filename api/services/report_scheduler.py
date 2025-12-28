"""
Report Scheduling Service for Basset Hound

This module provides scheduled report generation capabilities for OSINT investigations.
It supports various scheduling frequencies and manages the lifecycle of scheduled reports.

Features:
- Multiple scheduling frequencies (once, hourly, daily, weekly, monthly)
- Schedule management (create, update, delete, pause, resume)
- Due schedule detection
- Automated report execution
- In-memory storage with methods ready for Neo4j migration
"""

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

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


@dataclass
class ReportSchedule:
    """
    Represents a scheduled report configuration.

    Attributes:
        id: Unique identifier for the schedule (UUID)
        project_id: ID of the project this schedule belongs to
        report_type: Type of report to generate (e.g., 'summary', 'custom', 'entity')
        frequency: How often the report should be generated
        next_run: When the report should next be executed (UTC)
        last_run: When the report was last executed (UTC), None if never run
        options: ReportOptions configuration for report generation
        enabled: Whether the schedule is currently active
        created_at: When the schedule was created (UTC)
        created_by: User ID or identifier of who created the schedule
    """
    id: str
    project_id: str
    report_type: str
    frequency: ScheduleFrequency
    next_run: datetime
    last_run: Optional[datetime]
    options: ReportOptions
    enabled: bool
    created_at: datetime
    created_by: str


class ReportScheduler:
    """
    Service for managing scheduled report generation.

    Provides methods for creating, updating, deleting, and executing
    scheduled reports. Stores schedules in memory with interfaces
    designed for future Neo4j storage migration.
    """

    def __init__(self, neo4j_handler=None, report_service: Optional[ReportExportService] = None):
        """
        Initialize the report scheduler.

        Args:
            neo4j_handler: Neo4j database handler instance (optional, for future use)
            report_service: ReportExportService instance for generating reports
        """
        self._handler = neo4j_handler
        self._report_service = report_service
        # In-memory storage for schedules, keyed by schedule ID
        self._lock = threading.RLock()
        self._schedules: Dict[str, ReportSchedule] = {}

    def schedule_report(
        self,
        project_id: str,
        report_type: str,
        frequency: ScheduleFrequency,
        options: ReportOptions,
        created_by: str,
        next_run: Optional[datetime] = None,
        enabled: bool = True
    ) -> ReportSchedule:
        """
        Create a new scheduled report.

        Args:
            project_id: ID of the project for the report
            report_type: Type of report (e.g., 'summary', 'custom', 'entity')
            frequency: How often to generate the report
            options: ReportOptions configuration for the report
            created_by: User ID or identifier of who created the schedule
            next_run: When to first run the report (defaults to now)
            enabled: Whether the schedule should be enabled immediately

        Returns:
            ReportSchedule: The created schedule

        Raises:
            ValueError: If project_id or report_type is empty
        """
        if not project_id or not project_id.strip():
            raise ValueError("project_id is required")
        if not report_type or not report_type.strip():
            raise ValueError("report_type is required")
        if not created_by or not created_by.strip():
            raise ValueError("created_by is required")

        now = datetime.now(timezone.utc)
        schedule_id = str(uuid4())

        # Default next_run to now if not provided
        if next_run is None:
            next_run = now
        # Ensure next_run is timezone-aware (UTC)
        elif next_run.tzinfo is None:
            next_run = next_run.replace(tzinfo=timezone.utc)

        schedule = ReportSchedule(
            id=schedule_id,
            project_id=project_id.strip(),
            report_type=report_type.strip(),
            frequency=frequency,
            next_run=next_run,
            last_run=None,
            options=options,
            enabled=enabled,
            created_at=now,
            created_by=created_by.strip()
        )

        with self._lock:
            self._schedules[schedule_id] = schedule
        logger.info(f"Created schedule {schedule_id} for project {project_id}")

        return schedule

    def get_schedule(self, schedule_id: str) -> Optional[ReportSchedule]:
        """
        Get a schedule by its ID.

        Args:
            schedule_id: The unique identifier of the schedule

        Returns:
            ReportSchedule if found, None otherwise
        """
        with self._lock:
            return self._schedules.get(schedule_id)

    def list_schedules(
        self,
        project_id: str,
        enabled_only: bool = False
    ) -> List[ReportSchedule]:
        """
        List all schedules for a project.

        Args:
            project_id: ID of the project
            enabled_only: If True, only return enabled schedules

        Returns:
            List of ReportSchedule objects for the project
        """
        with self._lock:
            schedules = [
                s for s in self._schedules.values()
                if s.project_id == project_id
            ]

        if enabled_only:
            schedules = [s for s in schedules if s.enabled]

        # Sort by next_run time
        schedules.sort(key=lambda s: s.next_run)

        return schedules

    def update_schedule(
        self,
        schedule_id: str,
        frequency: Optional[ScheduleFrequency] = None,
        options: Optional[ReportOptions] = None,
        next_run: Optional[datetime] = None,
        enabled: Optional[bool] = None,
        report_type: Optional[str] = None
    ) -> Optional[ReportSchedule]:
        """
        Update an existing schedule.

        Args:
            schedule_id: The ID of the schedule to update
            frequency: New frequency (optional)
            options: New report options (optional)
            next_run: New next run time (optional)
            enabled: New enabled state (optional)
            report_type: New report type (optional)

        Returns:
            Updated ReportSchedule if found, None otherwise
        """
        with self._lock:
            schedule = self._schedules.get(schedule_id)
            if schedule is None:
                return None

            # Create a new schedule with updated values
            updated_schedule = ReportSchedule(
                id=schedule.id,
                project_id=schedule.project_id,
                report_type=report_type if report_type is not None else schedule.report_type,
                frequency=frequency if frequency is not None else schedule.frequency,
                next_run=next_run if next_run is not None else schedule.next_run,
                last_run=schedule.last_run,
                options=options if options is not None else schedule.options,
                enabled=enabled if enabled is not None else schedule.enabled,
                created_at=schedule.created_at,
                created_by=schedule.created_by
            )

            # Ensure next_run is timezone-aware
            if updated_schedule.next_run.tzinfo is None:
                updated_schedule = ReportSchedule(
                    id=updated_schedule.id,
                    project_id=updated_schedule.project_id,
                    report_type=updated_schedule.report_type,
                    frequency=updated_schedule.frequency,
                    next_run=updated_schedule.next_run.replace(tzinfo=timezone.utc),
                    last_run=updated_schedule.last_run,
                    options=updated_schedule.options,
                    enabled=updated_schedule.enabled,
                    created_at=updated_schedule.created_at,
                    created_by=updated_schedule.created_by
                )

            self._schedules[schedule_id] = updated_schedule

        logger.info(f"Updated schedule {schedule_id}")

        return updated_schedule

    def delete_schedule(self, schedule_id: str) -> bool:
        """
        Delete a schedule.

        Args:
            schedule_id: The ID of the schedule to delete

        Returns:
            True if the schedule was deleted, False if not found
        """
        with self._lock:
            if schedule_id in self._schedules:
                del self._schedules[schedule_id]
                logger.info(f"Deleted schedule {schedule_id}")
                return True
            return False

    def pause_schedule(self, schedule_id: str) -> Optional[ReportSchedule]:
        """
        Pause a schedule (set enabled to False).

        Args:
            schedule_id: The ID of the schedule to pause

        Returns:
            Updated ReportSchedule if found, None otherwise
        """
        return self.update_schedule(schedule_id, enabled=False)

    def resume_schedule(self, schedule_id: str) -> Optional[ReportSchedule]:
        """
        Resume a paused schedule (set enabled to True).

        Args:
            schedule_id: The ID of the schedule to resume

        Returns:
            Updated ReportSchedule if found, None otherwise
        """
        return self.update_schedule(schedule_id, enabled=True)

    def get_due_schedules(
        self,
        as_of: Optional[datetime] = None,
        project_id: Optional[str] = None
    ) -> List[ReportSchedule]:
        """
        Get all schedules that are due to run.

        A schedule is considered due if:
        - It is enabled
        - Its next_run time is <= the current time (or as_of time)

        Args:
            as_of: The reference time (defaults to now UTC)
            project_id: Filter by project ID (optional)

        Returns:
            List of due ReportSchedule objects
        """
        if as_of is None:
            as_of = datetime.now(timezone.utc)
        elif as_of.tzinfo is None:
            as_of = as_of.replace(tzinfo=timezone.utc)

        with self._lock:
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

    def run_scheduled_report(self, schedule_id: str) -> Optional[bytes]:
        """
        Execute a scheduled report immediately.

        This method:
        1. Generates the report using the configured options
        2. Updates last_run to now
        3. Calculates and sets the next_run time based on frequency
        4. For ONCE frequency, disables the schedule after execution

        Args:
            schedule_id: The ID of the schedule to run

        Returns:
            Report content as bytes if successful, None if schedule not found

        Raises:
            ValueError: If report_service is not configured
            Exception: If report generation fails
        """
        # Get schedule data under lock, then release for long operation
        with self._lock:
            schedule = self._schedules.get(schedule_id)
            if schedule is None:
                return None

            # Copy needed data for report generation
            report_type = schedule.report_type
            options = schedule.options
            frequency = schedule.frequency
            schedule_enabled = schedule.enabled

        if self._report_service is None:
            raise ValueError("report_service is not configured")

        now = datetime.now(timezone.utc)

        # Generate the report based on report_type - NO lock held during long operation
        try:
            if report_type == "summary":
                report_bytes = self._report_service.generate_project_summary(
                    options.project_id,
                    options.format
                )
            elif report_type == "entity":
                # For entity reports, entity_ids should have at least one ID
                if options.entity_ids and len(options.entity_ids) > 0:
                    report_bytes = self._report_service.generate_entity_report(
                        options.project_id,
                        options.entity_ids[0],
                        options.format
                    )
                else:
                    raise ValueError("entity_ids required for entity report type")
            else:
                # Default to custom report
                report_bytes = self._report_service.generate_report(options)

            logger.info(f"Generated report for schedule {schedule_id}")

        except Exception as e:
            logger.error(f"Failed to generate report for schedule {schedule_id}: {e}")
            raise

        # Calculate next run time
        next_run = self.calculate_next_run(frequency, now)

        # Update schedule under lock
        with self._lock:
            # Re-fetch schedule in case it was modified
            schedule = self._schedules.get(schedule_id)
            if schedule is None:
                # Schedule was deleted while we were generating report
                return report_bytes

            new_enabled = schedule.enabled
            if schedule.frequency == ScheduleFrequency.ONCE:
                new_enabled = False

            updated_schedule = ReportSchedule(
                id=schedule.id,
                project_id=schedule.project_id,
                report_type=schedule.report_type,
                frequency=schedule.frequency,
                next_run=next_run,
                last_run=now,
                options=schedule.options,
                enabled=new_enabled,
                created_at=schedule.created_at,
                created_by=schedule.created_by
            )

            self._schedules[schedule_id] = updated_schedule

        return report_bytes

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
        elif from_time.tzinfo is None:
            from_time = from_time.replace(tzinfo=timezone.utc)

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
            # Add approximately one month (30 days for simplicity)
            # For more precise handling, use dateutil.relativedelta
            next_month = from_time.month + 1
            next_year = from_time.year

            if next_month > 12:
                next_month = 1
                next_year += 1

            # Handle day overflow (e.g., Jan 31 -> Feb 28)
            day = from_time.day
            # Find the last day of the next month
            if next_month in (4, 6, 9, 11):
                max_day = 30
            elif next_month == 2:
                # Check for leap year
                if (next_year % 4 == 0 and next_year % 100 != 0) or (next_year % 400 == 0):
                    max_day = 29
                else:
                    max_day = 28
            else:
                max_day = 31

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
            # Default fallback - should not reach here
            return from_time + timedelta(days=1)

    def get_all_schedules(self) -> List[ReportSchedule]:
        """
        Get all schedules (across all projects).

        Returns:
            List of all ReportSchedule objects
        """
        with self._lock:
            return list(self._schedules.values())

    def clear_all_schedules(self) -> int:
        """
        Clear all schedules from storage.

        Returns:
            Number of schedules that were cleared
        """
        with self._lock:
            count = len(self._schedules)
            self._schedules.clear()
        logger.info(f"Cleared {count} schedules")
        return count


# Singleton instance management
_report_scheduler: Optional[ReportScheduler] = None
_report_scheduler_lock = threading.RLock()


def get_report_scheduler(
    neo4j_handler=None,
    report_service: Optional[ReportExportService] = None
) -> ReportScheduler:
    """
    Get or create the report scheduler singleton.

    Args:
        neo4j_handler: Neo4j handler instance (optional)
        report_service: ReportExportService instance (optional)

    Returns:
        ReportScheduler instance
    """
    global _report_scheduler

    if _report_scheduler is None:
        with _report_scheduler_lock:
            # Double-check after acquiring lock
            if _report_scheduler is None:
                _report_scheduler = ReportScheduler(neo4j_handler, report_service)

    return _report_scheduler


def set_report_scheduler(scheduler: Optional[ReportScheduler]) -> None:
    """Set the report scheduler singleton (for testing)."""
    global _report_scheduler
    with _report_scheduler_lock:
        _report_scheduler = scheduler
