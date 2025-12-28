"""
Tests for the Report Scheduler Service

Comprehensive test coverage for:
- ScheduleFrequency enum
- ReportSchedule dataclass
- ReportScheduler class CRUD operations
- Frequency calculations (next run time)
- Pause/resume functionality
- Due schedule detection
- Report execution integration
- Router endpoints and models
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from api.services.report_scheduler import (
    ScheduleFrequency,
    ReportSchedule,
    ReportScheduler,
    get_report_scheduler,
    set_report_scheduler,
)
from api.services.report_export_service import (
    ReportFormat,
    ReportOptions,
    ReportSection,
    ReportExportService,
)


# ==================== ScheduleFrequency Tests ====================


class TestScheduleFrequency:
    """Tests for ScheduleFrequency enum."""

    def test_frequency_values(self):
        """Test that all expected frequencies exist."""
        assert ScheduleFrequency.ONCE == "once"
        assert ScheduleFrequency.HOURLY == "hourly"
        assert ScheduleFrequency.DAILY == "daily"
        assert ScheduleFrequency.WEEKLY == "weekly"
        assert ScheduleFrequency.MONTHLY == "monthly"

    def test_frequency_is_string_enum(self):
        """Test that ScheduleFrequency is a string enum."""
        assert ScheduleFrequency.ONCE.value == "once"
        assert ScheduleFrequency.HOURLY.value == "hourly"
        assert ScheduleFrequency.DAILY.value == "daily"
        assert ScheduleFrequency.WEEKLY.value == "weekly"
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


# ==================== ReportSchedule Tests ====================


class TestReportSchedule:
    """Tests for ReportSchedule dataclass."""

    @pytest.fixture
    def sample_options(self):
        """Create sample ReportOptions for testing."""
        return ReportOptions(
            title="Test Report",
            format=ReportFormat.HTML,
            project_id="test_project"
        )

    def test_schedule_creation(self, sample_options):
        """Test creating a schedule with all fields."""
        now = datetime.now(timezone.utc)
        schedule = ReportSchedule(
            id="test-id-123",
            project_id="test_project",
            report_type="summary",
            frequency=ScheduleFrequency.DAILY,
            next_run=now,
            last_run=None,
            options=sample_options,
            enabled=True,
            created_at=now,
            created_by="user123"
        )

        assert schedule.id == "test-id-123"
        assert schedule.project_id == "test_project"
        assert schedule.report_type == "summary"
        assert schedule.frequency == ScheduleFrequency.DAILY
        assert schedule.next_run == now
        assert schedule.last_run is None
        assert schedule.options == sample_options
        assert schedule.enabled is True
        assert schedule.created_at == now
        assert schedule.created_by == "user123"

    def test_schedule_with_last_run(self, sample_options):
        """Test schedule with last_run set."""
        now = datetime.now(timezone.utc)
        last_run = now - timedelta(hours=1)

        schedule = ReportSchedule(
            id="test-id-456",
            project_id="test_project",
            report_type="custom",
            frequency=ScheduleFrequency.HOURLY,
            next_run=now,
            last_run=last_run,
            options=sample_options,
            enabled=True,
            created_at=now - timedelta(days=1),
            created_by="user456"
        )

        assert schedule.last_run == last_run

    def test_schedule_disabled(self, sample_options):
        """Test creating a disabled schedule."""
        now = datetime.now(timezone.utc)
        schedule = ReportSchedule(
            id="test-id-789",
            project_id="test_project",
            report_type="entity",
            frequency=ScheduleFrequency.WEEKLY,
            next_run=now,
            last_run=None,
            options=sample_options,
            enabled=False,
            created_at=now,
            created_by="user789"
        )

        assert schedule.enabled is False


# ==================== ReportScheduler CRUD Tests ====================


class TestReportSchedulerCRUD:
    """Tests for ReportScheduler CRUD operations."""

    @pytest.fixture
    def scheduler(self):
        """Create a fresh scheduler for each test."""
        return ReportScheduler()

    @pytest.fixture
    def sample_options(self):
        """Create sample ReportOptions for testing."""
        return ReportOptions(
            title="Test Report",
            format=ReportFormat.HTML,
            project_id="test_project"
        )

    def test_schedule_report_creates_schedule(self, scheduler, sample_options):
        """Test that schedule_report creates a new schedule."""
        schedule = scheduler.schedule_report(
            project_id="test_project",
            report_type="summary",
            frequency=ScheduleFrequency.DAILY,
            options=sample_options,
            created_by="user123"
        )

        assert schedule is not None
        assert schedule.project_id == "test_project"
        assert schedule.report_type == "summary"
        assert schedule.frequency == ScheduleFrequency.DAILY
        assert schedule.enabled is True
        assert schedule.created_by == "user123"

    def test_schedule_report_generates_uuid(self, scheduler, sample_options):
        """Test that schedule_report generates a valid UUID."""
        schedule = scheduler.schedule_report(
            project_id="test_project",
            report_type="summary",
            frequency=ScheduleFrequency.DAILY,
            options=sample_options,
            created_by="user123"
        )

        # UUID format: 8-4-4-4-12 hex characters
        assert len(schedule.id) == 36
        assert schedule.id.count("-") == 4

    def test_schedule_report_with_custom_next_run(self, scheduler, sample_options):
        """Test scheduling with custom next_run time."""
        future = datetime.now(timezone.utc) + timedelta(days=7)
        schedule = scheduler.schedule_report(
            project_id="test_project",
            report_type="summary",
            frequency=ScheduleFrequency.WEEKLY,
            options=sample_options,
            created_by="user123",
            next_run=future
        )

        assert schedule.next_run == future

    def test_schedule_report_disabled(self, scheduler, sample_options):
        """Test creating a disabled schedule."""
        schedule = scheduler.schedule_report(
            project_id="test_project",
            report_type="summary",
            frequency=ScheduleFrequency.DAILY,
            options=sample_options,
            created_by="user123",
            enabled=False
        )

        assert schedule.enabled is False

    def test_schedule_report_empty_project_id_raises(self, scheduler, sample_options):
        """Test that empty project_id raises ValueError."""
        with pytest.raises(ValueError, match="project_id is required"):
            scheduler.schedule_report(
                project_id="",
                report_type="summary",
                frequency=ScheduleFrequency.DAILY,
                options=sample_options,
                created_by="user123"
            )

    def test_schedule_report_empty_report_type_raises(self, scheduler, sample_options):
        """Test that empty report_type raises ValueError."""
        with pytest.raises(ValueError, match="report_type is required"):
            scheduler.schedule_report(
                project_id="test_project",
                report_type="",
                frequency=ScheduleFrequency.DAILY,
                options=sample_options,
                created_by="user123"
            )

    def test_schedule_report_empty_created_by_raises(self, scheduler, sample_options):
        """Test that empty created_by raises ValueError."""
        with pytest.raises(ValueError, match="created_by is required"):
            scheduler.schedule_report(
                project_id="test_project",
                report_type="summary",
                frequency=ScheduleFrequency.DAILY,
                options=sample_options,
                created_by=""
            )

    def test_get_schedule_returns_schedule(self, scheduler, sample_options):
        """Test that get_schedule returns the correct schedule."""
        created = scheduler.schedule_report(
            project_id="test_project",
            report_type="summary",
            frequency=ScheduleFrequency.DAILY,
            options=sample_options,
            created_by="user123"
        )

        retrieved = scheduler.get_schedule(created.id)
        assert retrieved is not None
        assert retrieved.id == created.id

    def test_get_schedule_not_found(self, scheduler):
        """Test that get_schedule returns None for unknown ID."""
        result = scheduler.get_schedule("nonexistent-id")
        assert result is None

    def test_list_schedules_empty_project(self, scheduler):
        """Test listing schedules for empty project."""
        schedules = scheduler.list_schedules("empty_project")
        assert schedules == []

    def test_list_schedules_returns_all_for_project(self, scheduler, sample_options):
        """Test that list_schedules returns all schedules for project."""
        scheduler.schedule_report(
            project_id="test_project",
            report_type="summary",
            frequency=ScheduleFrequency.DAILY,
            options=sample_options,
            created_by="user1"
        )
        scheduler.schedule_report(
            project_id="test_project",
            report_type="custom",
            frequency=ScheduleFrequency.WEEKLY,
            options=sample_options,
            created_by="user2"
        )
        scheduler.schedule_report(
            project_id="other_project",
            report_type="summary",
            frequency=ScheduleFrequency.DAILY,
            options=sample_options,
            created_by="user3"
        )

        schedules = scheduler.list_schedules("test_project")
        assert len(schedules) == 2

    def test_list_schedules_enabled_only(self, scheduler, sample_options):
        """Test listing only enabled schedules."""
        scheduler.schedule_report(
            project_id="test_project",
            report_type="summary",
            frequency=ScheduleFrequency.DAILY,
            options=sample_options,
            created_by="user1",
            enabled=True
        )
        scheduler.schedule_report(
            project_id="test_project",
            report_type="custom",
            frequency=ScheduleFrequency.WEEKLY,
            options=sample_options,
            created_by="user2",
            enabled=False
        )

        schedules = scheduler.list_schedules("test_project", enabled_only=True)
        assert len(schedules) == 1
        assert schedules[0].enabled is True

    def test_update_schedule_frequency(self, scheduler, sample_options):
        """Test updating schedule frequency."""
        created = scheduler.schedule_report(
            project_id="test_project",
            report_type="summary",
            frequency=ScheduleFrequency.DAILY,
            options=sample_options,
            created_by="user123"
        )

        updated = scheduler.update_schedule(
            schedule_id=created.id,
            frequency=ScheduleFrequency.WEEKLY
        )

        assert updated is not None
        assert updated.frequency == ScheduleFrequency.WEEKLY

    def test_update_schedule_enabled(self, scheduler, sample_options):
        """Test updating schedule enabled state."""
        created = scheduler.schedule_report(
            project_id="test_project",
            report_type="summary",
            frequency=ScheduleFrequency.DAILY,
            options=sample_options,
            created_by="user123"
        )

        updated = scheduler.update_schedule(
            schedule_id=created.id,
            enabled=False
        )

        assert updated is not None
        assert updated.enabled is False

    def test_update_schedule_next_run(self, scheduler, sample_options):
        """Test updating schedule next_run time."""
        created = scheduler.schedule_report(
            project_id="test_project",
            report_type="summary",
            frequency=ScheduleFrequency.DAILY,
            options=sample_options,
            created_by="user123"
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

    def test_delete_schedule(self, scheduler, sample_options):
        """Test deleting a schedule."""
        created = scheduler.schedule_report(
            project_id="test_project",
            report_type="summary",
            frequency=ScheduleFrequency.DAILY,
            options=sample_options,
            created_by="user123"
        )

        result = scheduler.delete_schedule(created.id)
        assert result is True

        # Verify it's deleted
        assert scheduler.get_schedule(created.id) is None

    def test_delete_schedule_not_found(self, scheduler):
        """Test deleting nonexistent schedule returns False."""
        result = scheduler.delete_schedule("nonexistent-id")
        assert result is False


# ==================== Pause/Resume Tests ====================


class TestPauseResume:
    """Tests for pause and resume functionality."""

    @pytest.fixture
    def scheduler(self):
        """Create a fresh scheduler for each test."""
        return ReportScheduler()

    @pytest.fixture
    def sample_options(self):
        """Create sample ReportOptions for testing."""
        return ReportOptions(
            title="Test Report",
            format=ReportFormat.HTML,
            project_id="test_project"
        )

    def test_pause_schedule(self, scheduler, sample_options):
        """Test pausing a schedule."""
        created = scheduler.schedule_report(
            project_id="test_project",
            report_type="summary",
            frequency=ScheduleFrequency.DAILY,
            options=sample_options,
            created_by="user123",
            enabled=True
        )

        paused = scheduler.pause_schedule(created.id)
        assert paused is not None
        assert paused.enabled is False

    def test_resume_schedule(self, scheduler, sample_options):
        """Test resuming a paused schedule."""
        created = scheduler.schedule_report(
            project_id="test_project",
            report_type="summary",
            frequency=ScheduleFrequency.DAILY,
            options=sample_options,
            created_by="user123",
            enabled=False
        )

        resumed = scheduler.resume_schedule(created.id)
        assert resumed is not None
        assert resumed.enabled is True

    def test_pause_schedule_not_found(self, scheduler):
        """Test pausing nonexistent schedule returns None."""
        result = scheduler.pause_schedule("nonexistent-id")
        assert result is None

    def test_resume_schedule_not_found(self, scheduler):
        """Test resuming nonexistent schedule returns None."""
        result = scheduler.resume_schedule("nonexistent-id")
        assert result is None

    def test_pause_already_paused(self, scheduler, sample_options):
        """Test pausing an already paused schedule."""
        created = scheduler.schedule_report(
            project_id="test_project",
            report_type="summary",
            frequency=ScheduleFrequency.DAILY,
            options=sample_options,
            created_by="user123",
            enabled=False
        )

        paused = scheduler.pause_schedule(created.id)
        assert paused is not None
        assert paused.enabled is False


# ==================== Frequency Calculation Tests ====================


class TestFrequencyCalculation:
    """Tests for next run time calculation based on frequency."""

    @pytest.fixture
    def scheduler(self):
        """Create a fresh scheduler for each test."""
        return ReportScheduler()

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
        """Test monthly frequency with day overflow (Jan 31 -> Feb 28)."""
        now = datetime(2024, 1, 31, 10, 0, 0, tzinfo=timezone.utc)
        next_run = scheduler.calculate_next_run(ScheduleFrequency.MONTHLY, now)

        # 2024 is a leap year, so Feb has 29 days
        expected = datetime(2024, 2, 29, 10, 0, 0, tzinfo=timezone.utc)
        assert next_run == expected

    def test_calculate_next_run_monthly_year_rollover(self, scheduler):
        """Test monthly frequency with year rollover (Dec -> Jan)."""
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

    @pytest.fixture
    def scheduler(self):
        """Create a fresh scheduler for each test."""
        return ReportScheduler()

    @pytest.fixture
    def sample_options(self):
        """Create sample ReportOptions for testing."""
        return ReportOptions(
            title="Test Report",
            format=ReportFormat.HTML,
            project_id="test_project"
        )

    def test_get_due_schedules_empty(self, scheduler):
        """Test getting due schedules when none exist."""
        due = scheduler.get_due_schedules()
        assert due == []

    def test_get_due_schedules_past_time(self, scheduler, sample_options):
        """Test that schedules with past next_run are due."""
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        scheduler.schedule_report(
            project_id="test_project",
            report_type="summary",
            frequency=ScheduleFrequency.DAILY,
            options=sample_options,
            created_by="user123",
            next_run=past
        )

        due = scheduler.get_due_schedules()
        assert len(due) == 1

    def test_get_due_schedules_future_time(self, scheduler, sample_options):
        """Test that schedules with future next_run are not due."""
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        scheduler.schedule_report(
            project_id="test_project",
            report_type="summary",
            frequency=ScheduleFrequency.DAILY,
            options=sample_options,
            created_by="user123",
            next_run=future
        )

        due = scheduler.get_due_schedules()
        assert len(due) == 0

    def test_get_due_schedules_disabled_excluded(self, scheduler, sample_options):
        """Test that disabled schedules are not due."""
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        scheduler.schedule_report(
            project_id="test_project",
            report_type="summary",
            frequency=ScheduleFrequency.DAILY,
            options=sample_options,
            created_by="user123",
            next_run=past,
            enabled=False
        )

        due = scheduler.get_due_schedules()
        assert len(due) == 0

    def test_get_due_schedules_filter_by_project(self, scheduler, sample_options):
        """Test filtering due schedules by project."""
        past = datetime.now(timezone.utc) - timedelta(hours=1)

        scheduler.schedule_report(
            project_id="project_a",
            report_type="summary",
            frequency=ScheduleFrequency.DAILY,
            options=sample_options,
            created_by="user1",
            next_run=past
        )
        scheduler.schedule_report(
            project_id="project_b",
            report_type="summary",
            frequency=ScheduleFrequency.DAILY,
            options=sample_options,
            created_by="user2",
            next_run=past
        )

        due_a = scheduler.get_due_schedules(project_id="project_a")
        due_b = scheduler.get_due_schedules(project_id="project_b")

        assert len(due_a) == 1
        assert due_a[0].project_id == "project_a"
        assert len(due_b) == 1
        assert due_b[0].project_id == "project_b"

    def test_get_due_schedules_sorted_by_time(self, scheduler, sample_options):
        """Test that due schedules are sorted by next_run."""
        now = datetime.now(timezone.utc)
        past_2h = now - timedelta(hours=2)
        past_1h = now - timedelta(hours=1)

        scheduler.schedule_report(
            project_id="test_project",
            report_type="summary",
            frequency=ScheduleFrequency.DAILY,
            options=sample_options,
            created_by="user1",
            next_run=past_1h  # More recent
        )
        scheduler.schedule_report(
            project_id="test_project",
            report_type="custom",
            frequency=ScheduleFrequency.DAILY,
            options=sample_options,
            created_by="user2",
            next_run=past_2h  # Older
        )

        due = scheduler.get_due_schedules()
        assert len(due) == 2
        assert due[0].next_run == past_2h  # Oldest first
        assert due[1].next_run == past_1h


# ==================== Report Execution Tests ====================


class TestReportExecution:
    """Tests for report execution integration."""

    @pytest.fixture
    def mock_handler(self):
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
    def mock_report_service(self, mock_handler):
        """Create a mock report service."""
        service = ReportExportService(mock_handler)
        return service

    @pytest.fixture
    def sample_options(self):
        """Create sample ReportOptions for testing."""
        return ReportOptions(
            title="Test Report",
            format=ReportFormat.HTML,
            project_id="test_project"
        )

    def test_run_scheduled_report_success(self, mock_handler, mock_report_service, sample_options):
        """Test successful scheduled report execution."""
        scheduler = ReportScheduler(mock_handler, mock_report_service)

        past = datetime.now(timezone.utc) - timedelta(hours=1)
        schedule = scheduler.schedule_report(
            project_id="test_project",
            report_type="custom",
            frequency=ScheduleFrequency.DAILY,
            options=sample_options,
            created_by="user123",
            next_run=past
        )

        result = scheduler.run_scheduled_report(schedule.id)

        assert result is not None
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_run_scheduled_report_updates_last_run(self, mock_handler, mock_report_service, sample_options):
        """Test that running a report updates last_run."""
        scheduler = ReportScheduler(mock_handler, mock_report_service)

        past = datetime.now(timezone.utc) - timedelta(hours=1)
        schedule = scheduler.schedule_report(
            project_id="test_project",
            report_type="custom",
            frequency=ScheduleFrequency.DAILY,
            options=sample_options,
            created_by="user123",
            next_run=past
        )

        assert schedule.last_run is None

        scheduler.run_scheduled_report(schedule.id)

        updated = scheduler.get_schedule(schedule.id)
        assert updated.last_run is not None

    def test_run_scheduled_report_updates_next_run(self, mock_handler, mock_report_service, sample_options):
        """Test that running a report updates next_run."""
        scheduler = ReportScheduler(mock_handler, mock_report_service)

        past = datetime.now(timezone.utc) - timedelta(hours=1)
        schedule = scheduler.schedule_report(
            project_id="test_project",
            report_type="custom",
            frequency=ScheduleFrequency.DAILY,
            options=sample_options,
            created_by="user123",
            next_run=past
        )

        scheduler.run_scheduled_report(schedule.id)

        updated = scheduler.get_schedule(schedule.id)
        # next_run should be in the future
        assert updated.next_run > past

    def test_run_scheduled_report_once_disables(self, mock_handler, mock_report_service, sample_options):
        """Test that ONCE frequency disables schedule after execution."""
        scheduler = ReportScheduler(mock_handler, mock_report_service)

        past = datetime.now(timezone.utc) - timedelta(hours=1)
        schedule = scheduler.schedule_report(
            project_id="test_project",
            report_type="custom",
            frequency=ScheduleFrequency.ONCE,
            options=sample_options,
            created_by="user123",
            next_run=past
        )

        assert schedule.enabled is True

        scheduler.run_scheduled_report(schedule.id)

        updated = scheduler.get_schedule(schedule.id)
        assert updated.enabled is False

    def test_run_scheduled_report_not_found(self, mock_handler, mock_report_service):
        """Test running nonexistent schedule returns None."""
        scheduler = ReportScheduler(mock_handler, mock_report_service)
        result = scheduler.run_scheduled_report("nonexistent-id")
        assert result is None

    def test_run_scheduled_report_no_service_raises(self, sample_options):
        """Test that running without report_service raises ValueError."""
        scheduler = ReportScheduler()  # No report service

        past = datetime.now(timezone.utc) - timedelta(hours=1)
        schedule = scheduler.schedule_report(
            project_id="test_project",
            report_type="custom",
            frequency=ScheduleFrequency.DAILY,
            options=sample_options,
            created_by="user123",
            next_run=past
        )

        with pytest.raises(ValueError, match="report_service is not configured"):
            scheduler.run_scheduled_report(schedule.id)

    def test_run_scheduled_report_summary_type(self, mock_handler, mock_report_service, sample_options):
        """Test running a summary report type."""
        scheduler = ReportScheduler(mock_handler, mock_report_service)

        past = datetime.now(timezone.utc) - timedelta(hours=1)
        schedule = scheduler.schedule_report(
            project_id="test_project",
            report_type="summary",
            frequency=ScheduleFrequency.DAILY,
            options=sample_options,
            created_by="user123",
            next_run=past
        )

        result = scheduler.run_scheduled_report(schedule.id)
        assert result is not None

    def test_run_scheduled_report_entity_type(self, mock_handler, mock_report_service):
        """Test running an entity report type."""
        scheduler = ReportScheduler(mock_handler, mock_report_service)

        options = ReportOptions(
            title="Entity Report",
            format=ReportFormat.HTML,
            project_id="test_project",
            entity_ids=["entity-1"]
        )

        past = datetime.now(timezone.utc) - timedelta(hours=1)
        schedule = scheduler.schedule_report(
            project_id="test_project",
            report_type="entity",
            frequency=ScheduleFrequency.DAILY,
            options=options,
            created_by="user123",
            next_run=past
        )

        result = scheduler.run_scheduled_report(schedule.id)
        assert result is not None


# ==================== Singleton Tests ====================


class TestReportSchedulerSingleton:
    """Tests for report scheduler singleton management."""

    def test_get_scheduler_creates_singleton(self):
        """Test that get_report_scheduler creates a singleton."""
        set_report_scheduler(None)

        scheduler1 = get_report_scheduler()
        scheduler2 = get_report_scheduler()

        assert scheduler1 is scheduler2

    def test_set_scheduler(self):
        """Test setting the scheduler singleton."""
        mock_handler = MagicMock()
        scheduler = ReportScheduler(mock_handler)

        set_report_scheduler(scheduler)
        retrieved = get_report_scheduler()

        assert retrieved is scheduler

    def test_set_scheduler_to_none(self):
        """Test clearing the scheduler singleton."""
        set_report_scheduler(None)
        scheduler = get_report_scheduler()
        assert scheduler is not None  # Creates a new one


# ==================== Utility Method Tests ====================


class TestUtilityMethods:
    """Tests for utility methods."""

    @pytest.fixture
    def scheduler(self):
        """Create a fresh scheduler for each test."""
        return ReportScheduler()

    @pytest.fixture
    def sample_options(self):
        """Create sample ReportOptions for testing."""
        return ReportOptions(
            title="Test Report",
            format=ReportFormat.HTML,
            project_id="test_project"
        )

    def test_get_all_schedules(self, scheduler, sample_options):
        """Test getting all schedules across projects."""
        scheduler.schedule_report(
            project_id="project_a",
            report_type="summary",
            frequency=ScheduleFrequency.DAILY,
            options=sample_options,
            created_by="user1"
        )
        scheduler.schedule_report(
            project_id="project_b",
            report_type="summary",
            frequency=ScheduleFrequency.WEEKLY,
            options=sample_options,
            created_by="user2"
        )

        all_schedules = scheduler.get_all_schedules()
        assert len(all_schedules) == 2

    def test_clear_all_schedules(self, scheduler, sample_options):
        """Test clearing all schedules."""
        scheduler.schedule_report(
            project_id="project_a",
            report_type="summary",
            frequency=ScheduleFrequency.DAILY,
            options=sample_options,
            created_by="user1"
        )
        scheduler.schedule_report(
            project_id="project_b",
            report_type="summary",
            frequency=ScheduleFrequency.WEEKLY,
            options=sample_options,
            created_by="user2"
        )

        count = scheduler.clear_all_schedules()
        assert count == 2
        assert len(scheduler.get_all_schedules()) == 0


# ==================== Router Model Tests ====================


class TestScheduleRouter:
    """Tests for schedule router endpoints and models."""

    def test_router_import(self):
        """Test that scheduler router can be imported."""
        from api.routers.scheduler import router
        assert router is not None

    def test_models_import(self):
        """Test that all request/response models can be imported."""
        from api.routers.scheduler import (
            CreateScheduleRequest,
            UpdateScheduleRequest,
            ScheduledReportResponse,
            ScheduleListResponse,
            RunScheduleResponse,
            ReportConfigRequest,
        )

        assert hasattr(CreateScheduleRequest, "model_fields")
        assert hasattr(UpdateScheduleRequest, "model_fields")
        assert hasattr(ScheduledReportResponse, "model_fields")
        assert hasattr(ScheduleListResponse, "model_fields")
        assert hasattr(RunScheduleResponse, "model_fields")
        assert hasattr(ReportConfigRequest, "model_fields")

    def test_parse_frequency_helper(self):
        """Test _parse_frequency helper function."""
        from api.routers.scheduler import _parse_frequency

        assert _parse_frequency("once") == ScheduleFrequency.ONCE
        assert _parse_frequency("hourly") == ScheduleFrequency.HOURLY
        assert _parse_frequency("daily") == ScheduleFrequency.DAILY
        assert _parse_frequency("weekly") == ScheduleFrequency.WEEKLY
        assert _parse_frequency("monthly") == ScheduleFrequency.MONTHLY

    def test_parse_frequency_invalid(self):
        """Test that invalid frequency raises HTTPException."""
        from api.routers.scheduler import _parse_frequency
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _parse_frequency("invalid")

        assert exc_info.value.status_code == 400

    def test_parse_format_helper(self):
        """Test _parse_format helper function."""
        from api.routers.scheduler import _parse_format

        assert _parse_format("pdf") == ReportFormat.PDF
        assert _parse_format("html") == ReportFormat.HTML
        assert _parse_format("markdown") == ReportFormat.MARKDOWN

    def test_parse_format_invalid(self):
        """Test that invalid format raises HTTPException."""
        from api.routers.scheduler import _parse_format
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _parse_format("invalid")

        assert exc_info.value.status_code == 400


# ==================== Edge Cases ====================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.fixture
    def scheduler(self):
        """Create a fresh scheduler for each test."""
        return ReportScheduler()

    @pytest.fixture
    def sample_options(self):
        """Create sample ReportOptions for testing."""
        return ReportOptions(
            title="Test Report",
            format=ReportFormat.HTML,
            project_id="test_project"
        )

    def test_whitespace_project_id_trimmed(self, scheduler, sample_options):
        """Test that whitespace in project_id is trimmed."""
        schedule = scheduler.schedule_report(
            project_id="  test_project  ",
            report_type="summary",
            frequency=ScheduleFrequency.DAILY,
            options=sample_options,
            created_by="user123"
        )

        assert schedule.project_id == "test_project"

    def test_whitespace_only_project_id_raises(self, scheduler, sample_options):
        """Test that whitespace-only project_id raises ValueError."""
        with pytest.raises(ValueError, match="project_id is required"):
            scheduler.schedule_report(
                project_id="   ",
                report_type="summary",
                frequency=ScheduleFrequency.DAILY,
                options=sample_options,
                created_by="user123"
            )

    def test_schedule_with_naive_datetime(self, scheduler, sample_options):
        """Test scheduling with naive datetime is converted to UTC."""
        naive_time = datetime(2024, 1, 15, 10, 0, 0)  # No timezone

        schedule = scheduler.schedule_report(
            project_id="test_project",
            report_type="summary",
            frequency=ScheduleFrequency.DAILY,
            options=sample_options,
            created_by="user123",
            next_run=naive_time
        )

        assert schedule.next_run.tzinfo == timezone.utc

    def test_update_schedule_with_naive_datetime(self, scheduler, sample_options):
        """Test updating schedule with naive datetime."""
        schedule = scheduler.schedule_report(
            project_id="test_project",
            report_type="summary",
            frequency=ScheduleFrequency.DAILY,
            options=sample_options,
            created_by="user123"
        )

        naive_time = datetime(2024, 6, 15, 10, 0, 0)  # No timezone
        updated = scheduler.update_schedule(schedule.id, next_run=naive_time)

        assert updated.next_run.tzinfo == timezone.utc

    def test_monthly_february_non_leap_year(self, scheduler):
        """Test monthly calculation for non-leap year February."""
        # March 31 -> April 30 (30 days in April)
        now = datetime(2023, 1, 31, 10, 0, 0, tzinfo=timezone.utc)  # Non-leap year
        next_run = scheduler.calculate_next_run(ScheduleFrequency.MONTHLY, now)

        # Feb in 2023 has 28 days
        expected = datetime(2023, 2, 28, 10, 0, 0, tzinfo=timezone.utc)
        assert next_run == expected

    def test_update_preserves_other_fields(self, scheduler, sample_options):
        """Test that update preserves fields not being updated."""
        schedule = scheduler.schedule_report(
            project_id="test_project",
            report_type="summary",
            frequency=ScheduleFrequency.DAILY,
            options=sample_options,
            created_by="user123"
        )

        original_created_at = schedule.created_at
        original_project_id = schedule.project_id

        updated = scheduler.update_schedule(schedule.id, frequency=ScheduleFrequency.WEEKLY)

        assert updated.created_at == original_created_at
        assert updated.project_id == original_project_id
        assert updated.created_by == "user123"
