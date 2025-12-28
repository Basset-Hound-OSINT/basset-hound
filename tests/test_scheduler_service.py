"""
Tests for the Scheduler Service

Comprehensive test coverage for:
- ScheduleFrequency enum
- ReportConfig model
- ScheduledReport model
- ReportScheduler class methods
- Frequency calculations (next run time)
- Enable/disable functionality
- Due schedule detection
- Report execution integration
- Edge cases (timezone handling, past start times)
- Router endpoints and models
- Cron expression support
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from typing import Dict

from api.services.scheduler_service import (
    ScheduleFrequency,
    ReportConfig,
    ScheduledReport,
    ReportScheduler,
    get_scheduler_service,
    set_scheduler_service,
)
from api.services.report_export_service import (
    ReportFormat,
    ReportOptions,
    ReportSection,
    ReportExportService,
)


# ==================== Fixtures ====================


@pytest.fixture
def scheduler():
    """Create a fresh scheduler for each test."""
    return ReportScheduler()


@pytest.fixture
def sample_report_config():
    """Create sample ReportConfig for testing."""
    return ReportConfig(
        title="Test Report",
        format="html",
        report_type="summary"
    )


@pytest.fixture
def mock_handler():
    """Create a mock Neo4j handler."""
    handler = MagicMock()
    handler.get_project.return_value = {
        "id": "project-123",
        "name": "Test Project",
        "safe_name": "test_project",
        "created_at": "2024-01-15T10:30:00"
    }
    handler.get_all_people.return_value = [
        {
            "id": "entity-1",
            "created_at": "2024-01-15T10:30:00",
            "profile": {
                "core": {"name": [{"first_name": "John", "last_name": "Doe"}]}
            }
        }
    ]
    handler.get_person.return_value = {
        "id": "entity-1",
        "created_at": "2024-01-15T10:30:00",
        "profile": {
            "core": {"name": [{"first_name": "John", "last_name": "Doe"}]}
        }
    }
    return handler


@pytest.fixture
def mock_report_service(mock_handler):
    """Create a mock report service."""
    return ReportExportService(mock_handler)


# ==================== ScheduleFrequency Tests ====================


class TestScheduleFrequency:
    """Tests for ScheduleFrequency enum."""

    def test_frequency_once_value(self):
        """Test ONCE frequency value."""
        assert ScheduleFrequency.ONCE == "once"
        assert ScheduleFrequency.ONCE.value == "once"

    def test_frequency_hourly_value(self):
        """Test HOURLY frequency value."""
        assert ScheduleFrequency.HOURLY == "hourly"
        assert ScheduleFrequency.HOURLY.value == "hourly"

    def test_frequency_daily_value(self):
        """Test DAILY frequency value."""
        assert ScheduleFrequency.DAILY == "daily"
        assert ScheduleFrequency.DAILY.value == "daily"

    def test_frequency_weekly_value(self):
        """Test WEEKLY frequency value."""
        assert ScheduleFrequency.WEEKLY == "weekly"
        assert ScheduleFrequency.WEEKLY.value == "weekly"

    def test_frequency_monthly_value(self):
        """Test MONTHLY frequency value."""
        assert ScheduleFrequency.MONTHLY == "monthly"
        assert ScheduleFrequency.MONTHLY.value == "monthly"

    def test_frequency_from_string(self):
        """Test creating frequency from string."""
        assert ScheduleFrequency("once") == ScheduleFrequency.ONCE
        assert ScheduleFrequency("hourly") == ScheduleFrequency.HOURLY
        assert ScheduleFrequency("daily") == ScheduleFrequency.DAILY
        assert ScheduleFrequency("weekly") == ScheduleFrequency.WEEKLY
        assert ScheduleFrequency("monthly") == ScheduleFrequency.MONTHLY

    def test_invalid_frequency_raises(self):
        """Test that invalid frequency raises ValueError."""
        with pytest.raises(ValueError):
            ScheduleFrequency("invalid")

    def test_frequency_count(self):
        """Test that all frequencies are accounted for."""
        assert len(ScheduleFrequency) == 5

    def test_frequency_is_string_subclass(self):
        """Test that frequency is a string subclass."""
        assert isinstance(ScheduleFrequency.DAILY, str)


# ==================== ReportConfig Tests ====================


class TestReportConfig:
    """Tests for ReportConfig model."""

    def test_report_config_minimal(self):
        """Test creating ReportConfig with minimal fields."""
        config = ReportConfig(title="Test")
        assert config.title == "Test"
        assert config.format == "html"  # default
        assert config.report_type == "summary"  # default

    def test_report_config_all_fields(self):
        """Test creating ReportConfig with all fields."""
        config = ReportConfig(
            title="Full Report",
            format="pdf",
            report_type="custom",
            entity_ids=["id1", "id2"],
            include_graph=False,
            include_timeline=False,
            include_statistics=False,
            template="professional"
        )
        assert config.title == "Full Report"
        assert config.format == "pdf"
        assert config.report_type == "custom"
        assert config.entity_ids == ["id1", "id2"]
        assert config.include_graph is False
        assert config.include_timeline is False
        assert config.include_statistics is False
        assert config.template == "professional"

    def test_report_config_defaults(self):
        """Test ReportConfig default values."""
        config = ReportConfig(title="Test")
        assert config.include_graph is True
        assert config.include_timeline is True
        assert config.include_statistics is True
        assert config.template == "default"
        assert config.entity_ids is None
        assert config.sections is None

    def test_report_config_title_validation(self):
        """Test that empty title is rejected."""
        with pytest.raises(Exception):  # Pydantic validation error
            ReportConfig(title="")


# ==================== ScheduledReport Tests ====================


class TestScheduledReport:
    """Tests for ScheduledReport model."""

    def test_scheduled_report_creation(self, sample_report_config):
        """Test creating a ScheduledReport with all fields."""
        now = datetime.now(timezone.utc)
        report = ScheduledReport(
            id="test-id-123",
            project_id="test_project",
            report_config=sample_report_config,
            frequency=ScheduleFrequency.DAILY,
            next_run=now,
            last_run=None,
            created_at=now,
            enabled=True,
            cron_expression=None
        )

        assert report.id == "test-id-123"
        assert report.project_id == "test_project"
        assert report.frequency == ScheduleFrequency.DAILY
        assert report.enabled is True

    def test_scheduled_report_with_cron(self, sample_report_config):
        """Test creating ScheduledReport with cron expression."""
        now = datetime.now(timezone.utc)
        report = ScheduledReport(
            id="test-id-456",
            project_id="test_project",
            report_config=sample_report_config,
            frequency=ScheduleFrequency.DAILY,
            next_run=now,
            created_at=now,
            cron_expression="0 9 * * *"
        )

        assert report.cron_expression == "0 9 * * *"

    def test_scheduled_report_disabled(self, sample_report_config):
        """Test creating disabled ScheduledReport."""
        now = datetime.now(timezone.utc)
        report = ScheduledReport(
            id="test-id-789",
            project_id="test_project",
            report_config=sample_report_config,
            frequency=ScheduleFrequency.WEEKLY,
            next_run=now,
            created_at=now,
            enabled=False
        )

        assert report.enabled is False


# ==================== ReportScheduler CRUD Tests ====================


class TestReportSchedulerCRUD:
    """Tests for ReportScheduler CRUD operations."""

    def test_schedule_report_creates_schedule(self, scheduler, sample_report_config):
        """Test that schedule_report creates a new schedule."""
        schedule = scheduler.schedule_report(
            project_id="test_project",
            report_config=sample_report_config,
            frequency=ScheduleFrequency.DAILY
        )

        assert schedule is not None
        assert schedule.project_id == "test_project"
        assert schedule.frequency == ScheduleFrequency.DAILY
        assert schedule.enabled is True

    def test_schedule_report_generates_uuid(self, scheduler, sample_report_config):
        """Test that schedule_report generates a valid UUID."""
        schedule = scheduler.schedule_report(
            project_id="test_project",
            report_config=sample_report_config,
            frequency=ScheduleFrequency.DAILY
        )

        # UUID format: 8-4-4-4-12 hex characters
        assert len(schedule.id) == 36
        assert schedule.id.count("-") == 4

    def test_schedule_report_with_start_time(self, scheduler, sample_report_config):
        """Test scheduling with custom start_time."""
        future = datetime.now(timezone.utc) + timedelta(days=7)
        schedule = scheduler.schedule_report(
            project_id="test_project",
            report_config=sample_report_config,
            frequency=ScheduleFrequency.WEEKLY,
            start_time=future
        )

        assert schedule.next_run == future

    def test_schedule_report_disabled(self, scheduler, sample_report_config):
        """Test creating a disabled schedule."""
        schedule = scheduler.schedule_report(
            project_id="test_project",
            report_config=sample_report_config,
            frequency=ScheduleFrequency.DAILY,
            enabled=False
        )

        assert schedule.enabled is False

    def test_schedule_report_empty_project_id_raises(self, scheduler, sample_report_config):
        """Test that empty project_id raises ValueError."""
        with pytest.raises(ValueError, match="project_id is required"):
            scheduler.schedule_report(
                project_id="",
                report_config=sample_report_config,
                frequency=ScheduleFrequency.DAILY
            )

    def test_schedule_report_whitespace_project_id_raises(self, scheduler, sample_report_config):
        """Test that whitespace-only project_id raises ValueError."""
        with pytest.raises(ValueError, match="project_id is required"):
            scheduler.schedule_report(
                project_id="   ",
                report_config=sample_report_config,
                frequency=ScheduleFrequency.DAILY
            )

    def test_get_scheduled_report_returns_schedule(self, scheduler, sample_report_config):
        """Test that get_scheduled_report returns the correct schedule."""
        created = scheduler.schedule_report(
            project_id="test_project",
            report_config=sample_report_config,
            frequency=ScheduleFrequency.DAILY
        )

        retrieved = scheduler.get_scheduled_report(created.id)
        assert retrieved is not None
        assert retrieved.id == created.id

    def test_get_scheduled_report_not_found(self, scheduler):
        """Test that get_scheduled_report returns None for unknown ID."""
        result = scheduler.get_scheduled_report("nonexistent-id")
        assert result is None

    def test_unschedule_report(self, scheduler, sample_report_config):
        """Test removing a schedule."""
        created = scheduler.schedule_report(
            project_id="test_project",
            report_config=sample_report_config,
            frequency=ScheduleFrequency.DAILY
        )

        result = scheduler.unschedule_report(created.id)
        assert result is True
        assert scheduler.get_scheduled_report(created.id) is None

    def test_unschedule_report_not_found(self, scheduler):
        """Test removing nonexistent schedule returns False."""
        result = scheduler.unschedule_report("nonexistent-id")
        assert result is False

    def test_get_scheduled_reports_empty_project(self, scheduler):
        """Test getting schedules for empty project."""
        schedules = scheduler.get_scheduled_reports("empty_project")
        assert schedules == []

    def test_get_scheduled_reports_filters_by_project(self, scheduler, sample_report_config):
        """Test that get_scheduled_reports filters by project."""
        scheduler.schedule_report(
            project_id="project_a",
            report_config=sample_report_config,
            frequency=ScheduleFrequency.DAILY
        )
        scheduler.schedule_report(
            project_id="project_b",
            report_config=sample_report_config,
            frequency=ScheduleFrequency.WEEKLY
        )

        schedules = scheduler.get_scheduled_reports("project_a")
        assert len(schedules) == 1
        assert schedules[0].project_id == "project_a"

    def test_get_scheduled_reports_enabled_only(self, scheduler, sample_report_config):
        """Test filtering only enabled schedules."""
        scheduler.schedule_report(
            project_id="test_project",
            report_config=sample_report_config,
            frequency=ScheduleFrequency.DAILY,
            enabled=True
        )
        scheduler.schedule_report(
            project_id="test_project",
            report_config=sample_report_config,
            frequency=ScheduleFrequency.WEEKLY,
            enabled=False
        )

        schedules = scheduler.get_scheduled_reports("test_project", enabled_only=True)
        assert len(schedules) == 1
        assert schedules[0].enabled is True

    def test_get_scheduled_reports_all_projects(self, scheduler, sample_report_config):
        """Test getting all schedules across projects."""
        scheduler.schedule_report(
            project_id="project_a",
            report_config=sample_report_config,
            frequency=ScheduleFrequency.DAILY
        )
        scheduler.schedule_report(
            project_id="project_b",
            report_config=sample_report_config,
            frequency=ScheduleFrequency.WEEKLY
        )

        schedules = scheduler.get_scheduled_reports()
        assert len(schedules) == 2


# ==================== Update Schedule Tests ====================


class TestUpdateSchedule:
    """Tests for schedule update functionality."""

    def test_update_schedule_frequency(self, scheduler, sample_report_config):
        """Test updating schedule frequency."""
        created = scheduler.schedule_report(
            project_id="test_project",
            report_config=sample_report_config,
            frequency=ScheduleFrequency.DAILY
        )

        updated = scheduler.update_schedule(
            schedule_id=created.id,
            frequency=ScheduleFrequency.WEEKLY
        )

        assert updated is not None
        assert updated.frequency == ScheduleFrequency.WEEKLY

    def test_update_schedule_enabled(self, scheduler, sample_report_config):
        """Test updating schedule enabled state."""
        created = scheduler.schedule_report(
            project_id="test_project",
            report_config=sample_report_config,
            frequency=ScheduleFrequency.DAILY
        )

        updated = scheduler.update_schedule(
            schedule_id=created.id,
            enabled=False
        )

        assert updated is not None
        assert updated.enabled is False

    def test_update_schedule_report_config(self, scheduler, sample_report_config):
        """Test updating report configuration."""
        created = scheduler.schedule_report(
            project_id="test_project",
            report_config=sample_report_config,
            frequency=ScheduleFrequency.DAILY
        )

        new_config = ReportConfig(
            title="Updated Report",
            format="pdf",
            report_type="custom"
        )

        updated = scheduler.update_schedule(
            schedule_id=created.id,
            report_config=new_config
        )

        assert updated is not None
        assert updated.report_config.title == "Updated Report"
        assert updated.report_config.format == "pdf"

    def test_update_schedule_next_run(self, scheduler, sample_report_config):
        """Test updating next_run time."""
        created = scheduler.schedule_report(
            project_id="test_project",
            report_config=sample_report_config,
            frequency=ScheduleFrequency.DAILY
        )

        new_time = datetime.now(timezone.utc) + timedelta(days=30)
        updated = scheduler.update_schedule(
            schedule_id=created.id,
            next_run=new_time
        )

        assert updated is not None
        assert updated.next_run == new_time

    def test_update_schedule_not_found(self, scheduler):
        """Test updating nonexistent schedule returns None."""
        result = scheduler.update_schedule(
            schedule_id="nonexistent-id",
            frequency=ScheduleFrequency.WEEKLY
        )
        assert result is None

    def test_update_schedule_preserves_other_fields(self, scheduler, sample_report_config):
        """Test that update preserves fields not being updated."""
        created = scheduler.schedule_report(
            project_id="test_project",
            report_config=sample_report_config,
            frequency=ScheduleFrequency.DAILY
        )

        original_created_at = created.created_at
        original_project_id = created.project_id

        updated = scheduler.update_schedule(
            schedule_id=created.id,
            frequency=ScheduleFrequency.WEEKLY
        )

        assert updated.created_at == original_created_at
        assert updated.project_id == original_project_id


# ==================== Enable/Disable Tests ====================


class TestEnableDisable:
    """Tests for enable and disable functionality."""

    def test_enable_schedule(self, scheduler, sample_report_config):
        """Test enabling a disabled schedule."""
        created = scheduler.schedule_report(
            project_id="test_project",
            report_config=sample_report_config,
            frequency=ScheduleFrequency.DAILY,
            enabled=False
        )

        enabled = scheduler.enable_schedule(created.id)
        assert enabled is not None
        assert enabled.enabled is True

    def test_disable_schedule(self, scheduler, sample_report_config):
        """Test disabling an enabled schedule."""
        created = scheduler.schedule_report(
            project_id="test_project",
            report_config=sample_report_config,
            frequency=ScheduleFrequency.DAILY,
            enabled=True
        )

        disabled = scheduler.disable_schedule(created.id)
        assert disabled is not None
        assert disabled.enabled is False

    def test_enable_schedule_not_found(self, scheduler):
        """Test enabling nonexistent schedule returns None."""
        result = scheduler.enable_schedule("nonexistent-id")
        assert result is None

    def test_disable_schedule_not_found(self, scheduler):
        """Test disabling nonexistent schedule returns None."""
        result = scheduler.disable_schedule("nonexistent-id")
        assert result is None

    def test_enable_already_enabled(self, scheduler, sample_report_config):
        """Test enabling an already enabled schedule."""
        created = scheduler.schedule_report(
            project_id="test_project",
            report_config=sample_report_config,
            frequency=ScheduleFrequency.DAILY,
            enabled=True
        )

        enabled = scheduler.enable_schedule(created.id)
        assert enabled is not None
        assert enabled.enabled is True


# ==================== Frequency Calculation Tests ====================


class TestFrequencyCalculation:
    """Tests for next run time calculation based on frequency."""

    def test_calculate_next_run_hourly(self, scheduler):
        """Test hourly frequency calculation."""
        now = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        next_run = scheduler.calculate_next_run(ScheduleFrequency.HOURLY, now)

        expected = datetime(2024, 1, 15, 11, 0, 0, tzinfo=timezone.utc)
        assert next_run == expected

    def test_calculate_next_run_daily(self, scheduler):
        """Test daily frequency calculation."""
        now = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        next_run = scheduler.calculate_next_run(ScheduleFrequency.DAILY, now)

        expected = datetime(2024, 1, 16, 10, 0, 0, tzinfo=timezone.utc)
        assert next_run == expected

    def test_calculate_next_run_weekly(self, scheduler):
        """Test weekly frequency calculation."""
        now = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        next_run = scheduler.calculate_next_run(ScheduleFrequency.WEEKLY, now)

        expected = datetime(2024, 1, 22, 10, 0, 0, tzinfo=timezone.utc)
        assert next_run == expected

    def test_calculate_next_run_monthly(self, scheduler):
        """Test monthly frequency calculation."""
        now = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        next_run = scheduler.calculate_next_run(ScheduleFrequency.MONTHLY, now)

        expected = datetime(2024, 2, 15, 10, 0, 0, tzinfo=timezone.utc)
        assert next_run == expected

    def test_calculate_next_run_monthly_day_overflow(self, scheduler):
        """Test monthly frequency with day overflow (Jan 31 -> Feb 28/29)."""
        now = datetime(2024, 1, 31, 10, 0, 0, tzinfo=timezone.utc)
        next_run = scheduler.calculate_next_run(ScheduleFrequency.MONTHLY, now)

        # 2024 is a leap year, so Feb has 29 days
        expected = datetime(2024, 2, 29, 10, 0, 0, tzinfo=timezone.utc)
        assert next_run == expected

    def test_calculate_next_run_monthly_non_leap_year(self, scheduler):
        """Test monthly frequency in non-leap year."""
        now = datetime(2023, 1, 31, 10, 0, 0, tzinfo=timezone.utc)
        next_run = scheduler.calculate_next_run(ScheduleFrequency.MONTHLY, now)

        # 2023 is not a leap year, Feb has 28 days
        expected = datetime(2023, 2, 28, 10, 0, 0, tzinfo=timezone.utc)
        assert next_run == expected

    def test_calculate_next_run_monthly_year_rollover(self, scheduler):
        """Test monthly frequency with year rollover."""
        now = datetime(2024, 12, 15, 10, 0, 0, tzinfo=timezone.utc)
        next_run = scheduler.calculate_next_run(ScheduleFrequency.MONTHLY, now)

        expected = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        assert next_run == expected

    def test_calculate_next_run_once(self, scheduler):
        """Test ONCE frequency returns same time."""
        now = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        next_run = scheduler.calculate_next_run(ScheduleFrequency.ONCE, now)

        assert next_run == now

    def test_calculate_next_run_defaults_to_now(self, scheduler):
        """Test that from_time defaults to now."""
        before = datetime.now(timezone.utc)
        next_run = scheduler.calculate_next_run(ScheduleFrequency.HOURLY)
        after = datetime.now(timezone.utc) + timedelta(hours=1, seconds=1)

        assert before + timedelta(hours=1) <= next_run <= after

    def test_calculate_next_run_naive_datetime(self, scheduler):
        """Test that naive datetime is converted to UTC."""
        now = datetime(2024, 1, 15, 10, 0, 0)  # No timezone
        next_run = scheduler.calculate_next_run(ScheduleFrequency.DAILY, now)

        assert next_run.tzinfo == timezone.utc


# ==================== Due Schedule Detection Tests ====================


class TestDueScheduleDetection:
    """Tests for due schedule detection."""

    def test_get_due_reports_empty(self, scheduler):
        """Test getting due reports when none exist."""
        due = scheduler.get_due_reports()
        assert due == []

    def test_get_due_reports_past_time(self, scheduler, sample_report_config):
        """Test that schedules with past next_run are due."""
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        # Use ONCE frequency so past time is preserved
        schedule = scheduler.schedule_report(
            project_id="test_project",
            report_config=sample_report_config,
            frequency=ScheduleFrequency.ONCE,
            start_time=past
        )

        # Verify next_run is in the past
        assert schedule.next_run == past

        due = scheduler.get_due_reports()
        assert len(due) == 1

    def test_get_due_reports_future_time(self, scheduler, sample_report_config):
        """Test that schedules with future next_run are not due."""
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        scheduler.schedule_report(
            project_id="test_project",
            report_config=sample_report_config,
            frequency=ScheduleFrequency.DAILY,
            start_time=future
        )

        due = scheduler.get_due_reports()
        assert len(due) == 0

    def test_get_due_reports_disabled_excluded(self, scheduler, sample_report_config):
        """Test that disabled schedules are not due."""
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        scheduler.schedule_report(
            project_id="test_project",
            report_config=sample_report_config,
            frequency=ScheduleFrequency.DAILY,
            start_time=past,
            enabled=False
        )

        due = scheduler.get_due_reports()
        assert len(due) == 0

    def test_get_due_reports_filter_by_project(self, scheduler, sample_report_config):
        """Test filtering due schedules by project."""
        past = datetime.now(timezone.utc) - timedelta(hours=1)

        # Use ONCE frequency so past time is preserved
        scheduler.schedule_report(
            project_id="project_a",
            report_config=sample_report_config,
            frequency=ScheduleFrequency.ONCE,
            start_time=past
        )
        scheduler.schedule_report(
            project_id="project_b",
            report_config=sample_report_config,
            frequency=ScheduleFrequency.ONCE,
            start_time=past
        )

        due_a = scheduler.get_due_reports(project_id="project_a")
        due_b = scheduler.get_due_reports(project_id="project_b")

        assert len(due_a) == 1
        assert due_a[0].project_id == "project_a"
        assert len(due_b) == 1
        assert due_b[0].project_id == "project_b"

    def test_get_due_reports_sorted_by_time(self, scheduler, sample_report_config):
        """Test that due schedules are sorted by next_run."""
        now = datetime.now(timezone.utc)
        past_2h = now - timedelta(hours=2)
        past_1h = now - timedelta(hours=1)

        # Use ONCE frequency so past times are preserved
        scheduler.schedule_report(
            project_id="test_project",
            report_config=sample_report_config,
            frequency=ScheduleFrequency.ONCE,
            start_time=past_1h
        )
        scheduler.schedule_report(
            project_id="test_project",
            report_config=sample_report_config,
            frequency=ScheduleFrequency.ONCE,
            start_time=past_2h
        )

        due = scheduler.get_due_reports()
        assert len(due) == 2
        assert due[0].next_run < due[1].next_run

    def test_get_due_reports_with_as_of(self, scheduler, sample_report_config):
        """Test get_due_reports with custom as_of time."""
        future = datetime.now(timezone.utc) + timedelta(hours=2)
        scheduler.schedule_report(
            project_id="test_project",
            report_config=sample_report_config,
            frequency=ScheduleFrequency.DAILY,
            start_time=datetime.now(timezone.utc) + timedelta(hours=1)
        )

        # Not due now
        due_now = scheduler.get_due_reports()
        assert len(due_now) == 0

        # But due in future
        due_future = scheduler.get_due_reports(as_of=future)
        assert len(due_future) == 1


# ==================== Report Execution Tests ====================


class TestReportExecution:
    """Tests for report execution integration."""

    def test_run_scheduled_report_success(self, mock_handler, mock_report_service, sample_report_config):
        """Test successful scheduled report execution."""
        scheduler = ReportScheduler(mock_handler, mock_report_service)

        past = datetime.now(timezone.utc) - timedelta(hours=1)
        schedule = scheduler.schedule_report(
            project_id="test_project",
            report_config=sample_report_config,
            frequency=ScheduleFrequency.DAILY,
            start_time=past
        )

        result = scheduler.run_scheduled_report(schedule.id)

        assert result["success"] is True
        assert "report_bytes" in result
        assert result["report_size"] > 0

    def test_run_scheduled_report_updates_last_run(self, mock_handler, mock_report_service, sample_report_config):
        """Test that running a report updates last_run."""
        scheduler = ReportScheduler(mock_handler, mock_report_service)

        past = datetime.now(timezone.utc) - timedelta(hours=1)
        schedule = scheduler.schedule_report(
            project_id="test_project",
            report_config=sample_report_config,
            frequency=ScheduleFrequency.DAILY,
            start_time=past
        )

        assert schedule.last_run is None

        scheduler.run_scheduled_report(schedule.id)

        updated = scheduler.get_scheduled_report(schedule.id)
        assert updated.last_run is not None

    def test_run_scheduled_report_updates_next_run(self, mock_handler, mock_report_service, sample_report_config):
        """Test that running a report updates next_run."""
        scheduler = ReportScheduler(mock_handler, mock_report_service)

        past = datetime.now(timezone.utc) - timedelta(hours=1)
        schedule = scheduler.schedule_report(
            project_id="test_project",
            report_config=sample_report_config,
            frequency=ScheduleFrequency.DAILY,
            start_time=past
        )

        scheduler.run_scheduled_report(schedule.id)

        updated = scheduler.get_scheduled_report(schedule.id)
        assert updated.next_run > past

    def test_run_scheduled_report_once_disables(self, mock_handler, mock_report_service, sample_report_config):
        """Test that ONCE frequency disables schedule after execution."""
        scheduler = ReportScheduler(mock_handler, mock_report_service)

        past = datetime.now(timezone.utc) - timedelta(hours=1)
        schedule = scheduler.schedule_report(
            project_id="test_project",
            report_config=sample_report_config,
            frequency=ScheduleFrequency.ONCE,
            start_time=past
        )

        assert schedule.enabled is True

        scheduler.run_scheduled_report(schedule.id)

        updated = scheduler.get_scheduled_report(schedule.id)
        assert updated.enabled is False

    def test_run_scheduled_report_not_found(self, mock_handler, mock_report_service):
        """Test running nonexistent schedule raises ValueError."""
        scheduler = ReportScheduler(mock_handler, mock_report_service)

        with pytest.raises(ValueError, match="Schedule not found"):
            scheduler.run_scheduled_report("nonexistent-id")

    def test_run_scheduled_report_no_service_raises(self, sample_report_config):
        """Test that running without report_service raises ValueError."""
        scheduler = ReportScheduler()  # No report service

        past = datetime.now(timezone.utc) - timedelta(hours=1)
        schedule = scheduler.schedule_report(
            project_id="test_project",
            report_config=sample_report_config,
            frequency=ScheduleFrequency.DAILY,
            start_time=past
        )

        with pytest.raises(ValueError, match="report_service is not configured"):
            scheduler.run_scheduled_report(schedule.id)


# ==================== Timezone Handling Tests ====================


class TestTimezoneHandling:
    """Tests for timezone handling edge cases."""

    def test_schedule_with_naive_datetime(self, scheduler, sample_report_config):
        """Test scheduling with naive datetime is converted to UTC."""
        naive_time = datetime(2024, 1, 15, 10, 0, 0)  # No timezone

        schedule = scheduler.schedule_report(
            project_id="test_project",
            report_config=sample_report_config,
            frequency=ScheduleFrequency.DAILY,
            start_time=naive_time
        )

        assert schedule.next_run.tzinfo == timezone.utc

    def test_update_with_naive_datetime(self, scheduler, sample_report_config):
        """Test updating with naive datetime."""
        schedule = scheduler.schedule_report(
            project_id="test_project",
            report_config=sample_report_config,
            frequency=ScheduleFrequency.DAILY
        )

        naive_time = datetime(2024, 6, 15, 10, 0, 0)  # No timezone
        updated = scheduler.update_schedule(schedule.id, next_run=naive_time)

        assert updated.next_run.tzinfo == timezone.utc

    def test_created_at_is_utc(self, scheduler, sample_report_config):
        """Test that created_at is in UTC."""
        schedule = scheduler.schedule_report(
            project_id="test_project",
            report_config=sample_report_config,
            frequency=ScheduleFrequency.DAILY
        )

        assert schedule.created_at.tzinfo == timezone.utc


# ==================== Past Start Time Tests ====================


class TestPastStartTime:
    """Tests for handling past start times."""

    def test_past_start_time_calculates_future(self, scheduler, sample_report_config):
        """Test that past start_time calculates next future occurrence."""
        past = datetime.now(timezone.utc) - timedelta(hours=5)

        schedule = scheduler.schedule_report(
            project_id="test_project",
            report_config=sample_report_config,
            frequency=ScheduleFrequency.HOURLY,
            start_time=past
        )

        # Should have calculated forward to a future time
        assert schedule.next_run > datetime.now(timezone.utc)

    def test_past_start_time_once_frequency(self, scheduler, sample_report_config):
        """Test that past start_time with ONCE keeps the past time."""
        past = datetime.now(timezone.utc) - timedelta(hours=5)

        schedule = scheduler.schedule_report(
            project_id="test_project",
            report_config=sample_report_config,
            frequency=ScheduleFrequency.ONCE,
            start_time=past
        )

        # ONCE frequency should keep the specified time
        assert schedule.next_run == past


# ==================== Singleton Tests ====================


class TestSchedulerSingleton:
    """Tests for scheduler singleton management."""

    def test_get_scheduler_creates_singleton(self):
        """Test that get_scheduler_service creates a singleton."""
        set_scheduler_service(None)

        scheduler1 = get_scheduler_service()
        scheduler2 = get_scheduler_service()

        assert scheduler1 is scheduler2

    def test_set_scheduler(self):
        """Test setting the scheduler singleton."""
        custom_scheduler = ReportScheduler()

        set_scheduler_service(custom_scheduler)
        retrieved = get_scheduler_service()

        assert retrieved is custom_scheduler

    def test_set_scheduler_to_none(self):
        """Test clearing the scheduler singleton."""
        set_scheduler_service(None)
        scheduler = get_scheduler_service()
        assert scheduler is not None  # Creates a new one


# ==================== Utility Method Tests ====================


class TestUtilityMethods:
    """Tests for utility methods."""

    def test_get_all_schedules(self, scheduler, sample_report_config):
        """Test getting all schedules across projects."""
        scheduler.schedule_report(
            project_id="project_a",
            report_config=sample_report_config,
            frequency=ScheduleFrequency.DAILY
        )
        scheduler.schedule_report(
            project_id="project_b",
            report_config=sample_report_config,
            frequency=ScheduleFrequency.WEEKLY
        )

        all_schedules = scheduler.get_all_schedules()
        assert len(all_schedules) == 2

    def test_clear_all_schedules(self, scheduler, sample_report_config):
        """Test clearing all schedules."""
        scheduler.schedule_report(
            project_id="project_a",
            report_config=sample_report_config,
            frequency=ScheduleFrequency.DAILY
        )
        scheduler.schedule_report(
            project_id="project_b",
            report_config=sample_report_config,
            frequency=ScheduleFrequency.WEEKLY
        )

        count = scheduler.clear_all_schedules()
        assert count == 2
        assert len(scheduler.get_all_schedules()) == 0

    def test_get_schedule_count(self, scheduler, sample_report_config):
        """Test getting schedule count."""
        scheduler.schedule_report(
            project_id="project_a",
            report_config=sample_report_config,
            frequency=ScheduleFrequency.DAILY
        )
        scheduler.schedule_report(
            project_id="project_a",
            report_config=sample_report_config,
            frequency=ScheduleFrequency.WEEKLY
        )
        scheduler.schedule_report(
            project_id="project_b",
            report_config=sample_report_config,
            frequency=ScheduleFrequency.DAILY
        )

        assert scheduler.get_schedule_count() == 3
        assert scheduler.get_schedule_count("project_a") == 2
        assert scheduler.get_schedule_count("project_b") == 1


# ==================== Persistence Hooks Tests ====================


class TestPersistenceHooks:
    """Tests for persistence hook functionality."""

    def test_persistence_save_called_on_create(self, sample_report_config):
        """Test that persistence save is called on schedule creation."""
        save_mock = MagicMock()
        scheduler = ReportScheduler(persistence_save=save_mock)

        scheduler.schedule_report(
            project_id="test_project",
            report_config=sample_report_config,
            frequency=ScheduleFrequency.DAILY
        )

        assert save_mock.called

    def test_persistence_save_called_on_delete(self, sample_report_config):
        """Test that persistence save is called on schedule deletion."""
        save_mock = MagicMock()
        scheduler = ReportScheduler(persistence_save=save_mock)

        schedule = scheduler.schedule_report(
            project_id="test_project",
            report_config=sample_report_config,
            frequency=ScheduleFrequency.DAILY
        )

        save_mock.reset_mock()
        scheduler.unschedule_report(schedule.id)

        assert save_mock.called

    def test_persistence_load_on_init(self):
        """Test that persistence load is called on initialization."""
        load_mock = MagicMock(return_value={})
        scheduler = ReportScheduler(persistence_load=load_mock)

        assert load_mock.called


# ==================== Router Import Tests ====================


class TestRouterImports:
    """Tests for router module imports."""

    def test_router_import(self):
        """Test that scheduler router can be imported."""
        from api.routers.scheduler import router
        assert router is not None

    def test_project_router_import(self):
        """Test that project router can be imported."""
        from api.routers.scheduler import project_router
        assert project_router is not None

    def test_admin_router_import(self):
        """Test that admin router can be imported."""
        from api.routers.scheduler import admin_router
        assert admin_router is not None

    def test_request_models_import(self):
        """Test that request models can be imported."""
        from api.routers.scheduler import (
            CreateScheduleRequest,
            UpdateScheduleRequest,
            ReportConfigRequest,
        )
        assert hasattr(CreateScheduleRequest, "model_fields")
        assert hasattr(UpdateScheduleRequest, "model_fields")
        assert hasattr(ReportConfigRequest, "model_fields")

    def test_response_models_import(self):
        """Test that response models can be imported."""
        from api.routers.scheduler import (
            ScheduledReportResponse,
            ScheduleListResponse,
            RunScheduleResponse,
            DueSchedulesResponse,
        )
        assert hasattr(ScheduledReportResponse, "model_fields")
        assert hasattr(ScheduleListResponse, "model_fields")
        assert hasattr(RunScheduleResponse, "model_fields")
        assert hasattr(DueSchedulesResponse, "model_fields")


# ==================== Helper Function Tests ====================


class TestHelperFunctions:
    """Tests for router helper functions."""

    def test_parse_frequency_valid(self):
        """Test _parse_frequency with valid inputs."""
        from api.routers.scheduler import _parse_frequency

        assert _parse_frequency("once") == ScheduleFrequency.ONCE
        assert _parse_frequency("hourly") == ScheduleFrequency.HOURLY
        assert _parse_frequency("daily") == ScheduleFrequency.DAILY
        assert _parse_frequency("weekly") == ScheduleFrequency.WEEKLY
        assert _parse_frequency("monthly") == ScheduleFrequency.MONTHLY

    def test_parse_frequency_case_insensitive(self):
        """Test _parse_frequency is case insensitive."""
        from api.routers.scheduler import _parse_frequency

        assert _parse_frequency("DAILY") == ScheduleFrequency.DAILY
        assert _parse_frequency("Daily") == ScheduleFrequency.DAILY
        assert _parse_frequency("dAiLy") == ScheduleFrequency.DAILY

    def test_parse_frequency_invalid(self):
        """Test that invalid frequency raises HTTPException."""
        from api.routers.scheduler import _parse_frequency
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _parse_frequency("invalid")

        assert exc_info.value.status_code == 400

    def test_build_report_config(self):
        """Test _build_report_config function."""
        from api.routers.scheduler import _build_report_config, ReportConfigRequest

        request = ReportConfigRequest(
            title="Test",
            format="pdf",
            report_type="custom"
        )

        config = _build_report_config(request)

        assert isinstance(config, ReportConfig)
        assert config.title == "Test"
        assert config.format == "pdf"
        assert config.report_type == "custom"
