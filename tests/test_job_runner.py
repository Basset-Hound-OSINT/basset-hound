"""
Tests for the Job Runner Service

Comprehensive test coverage for:
- JobStatus, JobType, JobPriority enums
- Job and JobResult Pydantic models
- JobRunner class queue management
- Job execution and status transitions
- Job cancellation
- Retry logic
- Timeout handling
- Integration with scheduler
- Worker lifecycle
- Router endpoints
"""

import asyncio
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, AsyncMock, patch

from api.services.job_runner import (
    JobStatus,
    JobType,
    JobPriority,
    Job,
    JobResult,
    JobStats,
    WorkerStatus,
    JobRunner,
    get_job_runner,
    set_job_runner,
)


# ==================== JobStatus Enum Tests ====================


class TestJobStatus:
    """Tests for JobStatus enum."""

    def test_status_values(self):
        """Test that all expected statuses exist."""
        assert JobStatus.PENDING == "pending"
        assert JobStatus.RUNNING == "running"
        assert JobStatus.COMPLETED == "completed"
        assert JobStatus.FAILED == "failed"
        assert JobStatus.CANCELLED == "cancelled"

    def test_status_is_string_enum(self):
        """Test that JobStatus is a string enum."""
        assert JobStatus.PENDING.value == "pending"
        assert JobStatus.RUNNING.value == "running"
        assert JobStatus.COMPLETED.value == "completed"
        assert JobStatus.FAILED.value == "failed"
        assert JobStatus.CANCELLED.value == "cancelled"

    def test_status_from_string(self):
        """Test creating status from string."""
        assert JobStatus("pending") == JobStatus.PENDING
        assert JobStatus("running") == JobStatus.RUNNING
        assert JobStatus("completed") == JobStatus.COMPLETED
        assert JobStatus("failed") == JobStatus.FAILED
        assert JobStatus("cancelled") == JobStatus.CANCELLED

    def test_invalid_status_raises(self):
        """Test that invalid status raises ValueError."""
        with pytest.raises(ValueError):
            JobStatus("invalid")

    def test_status_count(self):
        """Test that all statuses are accounted for."""
        assert len(JobStatus) == 5


# ==================== JobType Enum Tests ====================


class TestJobType:
    """Tests for JobType enum."""

    def test_type_values(self):
        """Test that all expected types exist."""
        assert JobType.REPORT == "report"
        assert JobType.EXPORT == "export"
        assert JobType.BULK_IMPORT == "bulk_import"
        assert JobType.CUSTOM == "custom"

    def test_type_from_string(self):
        """Test creating type from string."""
        assert JobType("report") == JobType.REPORT
        assert JobType("export") == JobType.EXPORT
        assert JobType("bulk_import") == JobType.BULK_IMPORT
        assert JobType("custom") == JobType.CUSTOM

    def test_invalid_type_raises(self):
        """Test that invalid type raises ValueError."""
        with pytest.raises(ValueError):
            JobType("invalid")

    def test_type_count(self):
        """Test that all types are accounted for."""
        assert len(JobType) == 4


# ==================== JobPriority Enum Tests ====================


class TestJobPriority:
    """Tests for JobPriority enum."""

    def test_priority_values(self):
        """Test that all expected priorities exist."""
        assert JobPriority.LOW == "low"
        assert JobPriority.NORMAL == "normal"
        assert JobPriority.HIGH == "high"
        assert JobPriority.CRITICAL == "critical"

    def test_priority_from_string(self):
        """Test creating priority from string."""
        assert JobPriority("low") == JobPriority.LOW
        assert JobPriority("normal") == JobPriority.NORMAL
        assert JobPriority("high") == JobPriority.HIGH
        assert JobPriority("critical") == JobPriority.CRITICAL

    def test_invalid_priority_raises(self):
        """Test that invalid priority raises ValueError."""
        with pytest.raises(ValueError):
            JobPriority("invalid")

    def test_priority_count(self):
        """Test that all priorities are accounted for."""
        assert len(JobPriority) == 4


# ==================== Job Model Tests ====================


class TestJobModel:
    """Tests for Job Pydantic model."""

    def test_job_creation_minimal(self):
        """Test creating a job with minimal fields."""
        job = Job(job_type=JobType.REPORT)

        assert job.id is not None
        assert len(job.id) == 36  # UUID format
        assert job.job_type == JobType.REPORT
        assert job.status == JobStatus.PENDING
        assert job.priority == JobPriority.NORMAL
        assert job.payload == {}
        assert job.max_retries == 3
        assert job.timeout_seconds == 300

    def test_job_creation_full(self):
        """Test creating a job with all fields."""
        now = datetime.now(timezone.utc)
        job = Job(
            id="test-id-123",
            job_type=JobType.EXPORT,
            status=JobStatus.RUNNING,
            priority=JobPriority.HIGH,
            payload={"project_id": "test"},
            created_at=now,
            started_at=now,
            max_retries=5,
            timeout_seconds=600,
            created_by="user123"
        )

        assert job.id == "test-id-123"
        assert job.job_type == JobType.EXPORT
        assert job.status == JobStatus.RUNNING
        assert job.priority == JobPriority.HIGH
        assert job.payload == {"project_id": "test"}
        assert job.max_retries == 5
        assert job.timeout_seconds == 600
        assert job.created_by == "user123"

    def test_job_scheduled_for(self):
        """Test job with scheduled_for field."""
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        job = Job(
            job_type=JobType.REPORT,
            scheduled_for=future
        )

        assert job.scheduled_for == future

    def test_job_with_result(self):
        """Test job with result field."""
        job = Job(
            job_type=JobType.REPORT,
            status=JobStatus.COMPLETED,
            result={"report_size": 1234}
        )

        assert job.result == {"report_size": 1234}

    def test_job_with_error(self):
        """Test job with error field."""
        job = Job(
            job_type=JobType.REPORT,
            status=JobStatus.FAILED,
            error="Something went wrong"
        )

        assert job.error == "Something went wrong"


# ==================== JobResult Model Tests ====================


class TestJobResultModel:
    """Tests for JobResult Pydantic model."""

    def test_result_creation(self):
        """Test creating a job result."""
        now = datetime.now(timezone.utc)
        result = JobResult(
            job_id="test-123",
            status=JobStatus.COMPLETED,
            result={"data": "value"},
            started_at=now - timedelta(seconds=5),
            completed_at=now,
            duration_ms=5000
        )

        assert result.job_id == "test-123"
        assert result.status == JobStatus.COMPLETED
        assert result.result == {"data": "value"}
        assert result.duration_ms == 5000
        assert result.error is None

    def test_result_with_error(self):
        """Test creating a failed job result."""
        result = JobResult(
            job_id="test-456",
            status=JobStatus.FAILED,
            error="Timeout exceeded"
        )

        assert result.status == JobStatus.FAILED
        assert result.error == "Timeout exceeded"
        assert result.result is None


# ==================== JobStats Model Tests ====================


class TestJobStatsModel:
    """Tests for JobStats Pydantic model."""

    def test_stats_defaults(self):
        """Test default stats values."""
        stats = JobStats()

        assert stats.total_jobs == 0
        assert stats.pending_count == 0
        assert stats.running_count == 0
        assert stats.completed_count == 0
        assert stats.failed_count == 0
        assert stats.cancelled_count == 0
        assert stats.avg_duration_ms is None
        assert stats.success_rate is None

    def test_stats_with_values(self):
        """Test stats with values."""
        stats = JobStats(
            total_jobs=100,
            pending_count=10,
            running_count=5,
            completed_count=75,
            failed_count=5,
            cancelled_count=5,
            avg_duration_ms=1500.5,
            success_rate=93.75
        )

        assert stats.total_jobs == 100
        assert stats.success_rate == 93.75


# ==================== WorkerStatus Model Tests ====================


class TestWorkerStatusModel:
    """Tests for WorkerStatus Pydantic model."""

    def test_worker_status_defaults(self):
        """Test default worker status values."""
        status = WorkerStatus()

        assert status.is_running is False
        assert status.started_at is None
        assert status.jobs_processed == 0
        assert status.current_job_id is None

    def test_worker_status_running(self):
        """Test running worker status."""
        now = datetime.now(timezone.utc)
        status = WorkerStatus(
            is_running=True,
            started_at=now,
            jobs_processed=42,
            current_job_id="job-123"
        )

        assert status.is_running is True
        assert status.jobs_processed == 42
        assert status.current_job_id == "job-123"


# ==================== JobRunner Queue Management Tests ====================


class TestJobRunnerQueueManagement:
    """Tests for JobRunner queue management."""

    @pytest.fixture
    def runner(self):
        """Create a fresh job runner for each test."""
        return JobRunner()

    def test_enqueue_job_creates_job(self, runner):
        """Test that enqueue_job creates a new job."""
        job = runner.enqueue_job(
            job_type=JobType.REPORT,
            payload={"schedule_id": "abc-123"}
        )

        assert job is not None
        assert job.job_type == JobType.REPORT
        assert job.status == JobStatus.PENDING
        assert job.payload == {"schedule_id": "abc-123"}

    def test_enqueue_job_generates_uuid(self, runner):
        """Test that enqueue_job generates a valid UUID."""
        job = runner.enqueue_job(
            job_type=JobType.REPORT,
            payload={}
        )

        assert len(job.id) == 36
        assert job.id.count("-") == 4

    def test_enqueue_job_with_priority(self, runner):
        """Test enqueuing job with priority."""
        job = runner.enqueue_job(
            job_type=JobType.REPORT,
            payload={},
            priority=JobPriority.HIGH
        )

        assert job.priority == JobPriority.HIGH

    def test_enqueue_job_with_custom_retries(self, runner):
        """Test enqueuing job with custom max_retries."""
        job = runner.enqueue_job(
            job_type=JobType.REPORT,
            payload={},
            max_retries=5
        )

        assert job.max_retries == 5

    def test_enqueue_job_with_timeout(self, runner):
        """Test enqueuing job with custom timeout."""
        job = runner.enqueue_job(
            job_type=JobType.REPORT,
            payload={},
            timeout_seconds=600
        )

        assert job.timeout_seconds == 600

    def test_enqueue_job_with_scheduled_for(self, runner):
        """Test enqueuing job with scheduled_for time."""
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        job = runner.enqueue_job(
            job_type=JobType.REPORT,
            payload={},
            scheduled_for=future
        )

        assert job.scheduled_for == future

    def test_enqueue_job_invalid_type_raises(self, runner):
        """Test that invalid job_type raises ValueError."""
        with pytest.raises(ValueError, match="Invalid job_type"):
            runner.enqueue_job(
                job_type="invalid_type",
                payload={}
            )

    def test_get_job_returns_job(self, runner):
        """Test that get_job returns the correct job."""
        created = runner.enqueue_job(
            job_type=JobType.REPORT,
            payload={}
        )

        retrieved = runner.get_job(created.id)
        assert retrieved is not None
        assert retrieved.id == created.id

    def test_get_job_not_found(self, runner):
        """Test that get_job returns None for unknown ID."""
        result = runner.get_job("nonexistent-id")
        assert result is None

    def test_get_job_status_returns_status(self, runner):
        """Test that get_job_status returns correct status."""
        job = runner.enqueue_job(
            job_type=JobType.REPORT,
            payload={}
        )

        status = runner.get_job_status(job.id)
        assert status == JobStatus.PENDING

    def test_get_job_status_not_found(self, runner):
        """Test that get_job_status returns None for unknown ID."""
        result = runner.get_job_status("nonexistent-id")
        assert result is None

    def test_list_jobs_empty(self, runner):
        """Test listing jobs when none exist."""
        jobs = runner.list_jobs()
        assert jobs == []

    def test_list_jobs_returns_all(self, runner):
        """Test that list_jobs returns all jobs."""
        runner.enqueue_job(job_type=JobType.REPORT, payload={})
        runner.enqueue_job(job_type=JobType.EXPORT, payload={})

        jobs = runner.list_jobs()
        assert len(jobs) == 2

    def test_list_jobs_filter_by_status(self, runner):
        """Test filtering jobs by status."""
        job1 = runner.enqueue_job(job_type=JobType.REPORT, payload={})
        job2 = runner.enqueue_job(job_type=JobType.EXPORT, payload={})

        # Manually set one to completed
        job2.status = JobStatus.COMPLETED

        pending_jobs = runner.list_jobs(status=JobStatus.PENDING)
        assert len(pending_jobs) == 1
        assert pending_jobs[0].id == job1.id

    def test_list_jobs_filter_by_type(self, runner):
        """Test filtering jobs by type."""
        runner.enqueue_job(job_type=JobType.REPORT, payload={})
        runner.enqueue_job(job_type=JobType.EXPORT, payload={})

        report_jobs = runner.list_jobs(job_type=JobType.REPORT)
        assert len(report_jobs) == 1
        assert report_jobs[0].job_type == JobType.REPORT

    def test_list_jobs_pagination(self, runner):
        """Test job list pagination."""
        for _ in range(5):
            runner.enqueue_job(job_type=JobType.REPORT, payload={})

        page1 = runner.list_jobs(limit=2, offset=0)
        page2 = runner.list_jobs(limit=2, offset=2)

        assert len(page1) == 2
        assert len(page2) == 2
        assert page1[0].id != page2[0].id

    def test_list_jobs_sorted_by_priority(self, runner):
        """Test that jobs are sorted by priority."""
        low = runner.enqueue_job(
            job_type=JobType.REPORT,
            payload={},
            priority=JobPriority.LOW
        )
        high = runner.enqueue_job(
            job_type=JobType.REPORT,
            payload={},
            priority=JobPriority.HIGH
        )
        critical = runner.enqueue_job(
            job_type=JobType.REPORT,
            payload={},
            priority=JobPriority.CRITICAL
        )

        jobs = runner.list_jobs()
        assert jobs[0].id == critical.id
        assert jobs[1].id == high.id
        assert jobs[2].id == low.id

    def test_get_pending_jobs(self, runner):
        """Test getting pending jobs."""
        job1 = runner.enqueue_job(job_type=JobType.REPORT, payload={})
        job2 = runner.enqueue_job(job_type=JobType.EXPORT, payload={})
        job2.status = JobStatus.RUNNING

        pending = runner.get_pending_jobs()
        assert len(pending) == 1
        assert pending[0].id == job1.id

    def test_get_running_jobs(self, runner):
        """Test getting running jobs."""
        job1 = runner.enqueue_job(job_type=JobType.REPORT, payload={})
        job2 = runner.enqueue_job(job_type=JobType.EXPORT, payload={})
        job1.status = JobStatus.RUNNING

        running = runner.get_running_jobs()
        assert len(running) == 1
        assert running[0].id == job1.id


# ==================== Job Cancellation Tests ====================


class TestJobCancellation:
    """Tests for job cancellation."""

    @pytest.fixture
    def runner(self):
        """Create a fresh job runner for each test."""
        return JobRunner()

    def test_cancel_pending_job(self, runner):
        """Test cancelling a pending job."""
        job = runner.enqueue_job(job_type=JobType.REPORT, payload={})

        result = runner.cancel_job(job.id)
        assert result is True

        updated = runner.get_job(job.id)
        assert updated.status == JobStatus.CANCELLED
        assert updated.error == "Job cancelled by user"

    def test_cancel_job_creates_result(self, runner):
        """Test that cancel_job creates a job result."""
        job = runner.enqueue_job(job_type=JobType.REPORT, payload={})

        runner.cancel_job(job.id)

        result = runner.get_job_result(job.id)
        assert result is not None
        assert result.status == JobStatus.CANCELLED

    def test_cancel_completed_job_fails(self, runner):
        """Test that completed jobs cannot be cancelled."""
        job = runner.enqueue_job(job_type=JobType.REPORT, payload={})
        job.status = JobStatus.COMPLETED

        result = runner.cancel_job(job.id)
        assert result is False

    def test_cancel_failed_job_fails(self, runner):
        """Test that failed jobs cannot be cancelled."""
        job = runner.enqueue_job(job_type=JobType.REPORT, payload={})
        job.status = JobStatus.FAILED

        result = runner.cancel_job(job.id)
        assert result is False

    def test_cancel_already_cancelled_job_fails(self, runner):
        """Test that already cancelled jobs cannot be cancelled again."""
        job = runner.enqueue_job(job_type=JobType.REPORT, payload={})
        job.status = JobStatus.CANCELLED

        result = runner.cancel_job(job.id)
        assert result is False

    def test_cancel_nonexistent_job(self, runner):
        """Test cancelling nonexistent job returns False."""
        result = runner.cancel_job("nonexistent-id")
        assert result is False


# ==================== Job Execution Tests ====================


class TestJobExecution:
    """Tests for job execution."""

    @pytest.fixture
    def runner(self):
        """Create a job runner with mock services."""
        mock_scheduler = MagicMock()
        mock_scheduler.run_scheduled_report.return_value = b"report content"
        mock_scheduler.get_schedule.return_value = MagicMock(id="schedule-123")

        mock_report_service = MagicMock()
        mock_report_service.generate_project_summary.return_value = b"summary"
        mock_report_service.generate_report.return_value = b"custom report"

        mock_bulk_service = MagicMock()
        mock_bulk_service.export_entities.return_value = '{"entities": []}'
        mock_bulk_service.import_entities.return_value = MagicMock(
            total=5,
            successful=4,
            failed=1,
            created_ids=["id1", "id2", "id3", "id4"],
            errors=[{"index": 4, "error": "duplicate"}]
        )

        return JobRunner(
            report_scheduler=mock_scheduler,
            report_export_service=mock_report_service,
            bulk_operations_service=mock_bulk_service
        )

    @pytest.mark.asyncio
    async def test_execute_job_success(self, runner):
        """Test successful job execution."""
        job = runner.enqueue_job(
            job_type=JobType.REPORT,
            payload={"schedule_id": "test-schedule"}
        )

        result = await runner.execute_job(job.id)

        assert result.status == JobStatus.COMPLETED
        assert result.error is None
        assert result.result is not None

    @pytest.mark.asyncio
    async def test_execute_job_updates_status(self, runner):
        """Test that execute_job updates job status."""
        job = runner.enqueue_job(
            job_type=JobType.REPORT,
            payload={"schedule_id": "test-schedule"}
        )

        await runner.execute_job(job.id)

        updated = runner.get_job(job.id)
        assert updated.status == JobStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_execute_job_sets_started_at(self, runner):
        """Test that execute_job sets started_at."""
        job = runner.enqueue_job(
            job_type=JobType.REPORT,
            payload={"schedule_id": "test-schedule"}
        )

        assert job.started_at is None

        await runner.execute_job(job.id)

        updated = runner.get_job(job.id)
        assert updated.started_at is not None

    @pytest.mark.asyncio
    async def test_execute_job_sets_completed_at(self, runner):
        """Test that execute_job sets completed_at."""
        job = runner.enqueue_job(
            job_type=JobType.REPORT,
            payload={"schedule_id": "test-schedule"}
        )

        await runner.execute_job(job.id)

        updated = runner.get_job(job.id)
        assert updated.completed_at is not None

    @pytest.mark.asyncio
    async def test_execute_job_calculates_duration(self, runner):
        """Test that execute_job calculates duration."""
        job = runner.enqueue_job(
            job_type=JobType.REPORT,
            payload={"schedule_id": "test-schedule"}
        )

        result = await runner.execute_job(job.id)

        assert result.duration_ms is not None
        assert result.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_execute_job_not_found_raises(self, runner):
        """Test that executing nonexistent job raises ValueError."""
        with pytest.raises(ValueError, match="Job not found"):
            await runner.execute_job("nonexistent-id")

    @pytest.mark.asyncio
    async def test_execute_already_completed_raises(self, runner):
        """Test that executing completed job raises ValueError."""
        job = runner.enqueue_job(
            job_type=JobType.REPORT,
            payload={}
        )
        job.status = JobStatus.COMPLETED

        with pytest.raises(ValueError, match="already in terminal state"):
            await runner.execute_job(job.id)

    @pytest.mark.asyncio
    async def test_execute_export_job(self, runner):
        """Test executing export job."""
        job = runner.enqueue_job(
            job_type=JobType.EXPORT,
            payload={"project_id": "test-project"}
        )

        result = await runner.execute_job(job.id)

        assert result.status == JobStatus.COMPLETED
        assert "export_size_bytes" in result.result

    @pytest.mark.asyncio
    async def test_execute_bulk_import_job(self, runner):
        """Test executing bulk import job."""
        job = runner.enqueue_job(
            job_type=JobType.BULK_IMPORT,
            payload={
                "project_id": "test-project",
                "entities": [{"profile": {}}]
            }
        )

        result = await runner.execute_job(job.id)

        assert result.status == JobStatus.COMPLETED
        assert result.result["total"] == 5
        assert result.result["successful"] == 4


# ==================== Retry Logic Tests ====================


class TestRetryLogic:
    """Tests for job retry logic."""

    @pytest.fixture
    def runner(self):
        """Create a job runner with a failing handler."""
        runner = JobRunner()

        async def failing_handler(job):
            raise Exception("Simulated failure")

        runner._job_handlers[JobType.CUSTOM] = failing_handler
        return runner

    @pytest.mark.asyncio
    async def test_job_retries_on_failure(self, runner):
        """Test that job retries on failure."""
        job = runner.enqueue_job(
            job_type=JobType.CUSTOM,
            payload={},
            max_retries=3
        )

        result = await runner.execute_job(job.id)

        # Job should be pending for retry
        updated = runner.get_job(job.id)
        assert updated.status == JobStatus.PENDING
        assert updated.retry_count == 1

    @pytest.mark.asyncio
    async def test_job_fails_after_max_retries(self, runner):
        """Test that job fails after max retries."""
        job = runner.enqueue_job(
            job_type=JobType.CUSTOM,
            payload={},
            max_retries=2
        )

        # Execute until max retries exhausted
        await runner.execute_job(job.id)  # retry 1
        await runner.execute_job(job.id)  # retry 2
        result = await runner.execute_job(job.id)  # final failure

        assert result.status == JobStatus.FAILED
        updated = runner.get_job(job.id)
        assert updated.retry_count == 2

    @pytest.mark.asyncio
    async def test_job_no_retry_when_max_zero(self, runner):
        """Test that job doesn't retry when max_retries is 0."""
        job = runner.enqueue_job(
            job_type=JobType.CUSTOM,
            payload={},
            max_retries=0
        )

        result = await runner.execute_job(job.id)

        assert result.status == JobStatus.FAILED
        updated = runner.get_job(job.id)
        assert updated.retry_count == 0

    def test_retry_failed_job_manually(self, runner):
        """Test manually retrying a failed job."""
        job = runner.enqueue_job(
            job_type=JobType.CUSTOM,
            payload={},
            max_retries=0
        )
        job.status = JobStatus.FAILED
        job.retry_count = 5

        result = runner.retry_failed_job(job.id)

        assert result is True
        updated = runner.get_job(job.id)
        assert updated.status == JobStatus.PENDING
        assert updated.retry_count == 0

    def test_retry_non_failed_job_fails(self, runner):
        """Test that retrying non-failed job returns False."""
        job = runner.enqueue_job(
            job_type=JobType.CUSTOM,
            payload={}
        )

        result = runner.retry_failed_job(job.id)
        assert result is False


# ==================== Timeout Handling Tests ====================


class TestTimeoutHandling:
    """Tests for job timeout handling."""

    @pytest.fixture
    def runner(self):
        """Create a job runner with a slow handler."""
        runner = JobRunner()

        async def slow_handler(job):
            await asyncio.sleep(10)  # Longer than typical test timeout
            return {"result": "done"}

        runner._job_handlers[JobType.CUSTOM] = slow_handler
        return runner

    @pytest.mark.asyncio
    async def test_job_times_out(self, runner):
        """Test that job times out after timeout_seconds."""
        job = runner.enqueue_job(
            job_type=JobType.CUSTOM,
            payload={},
            timeout_seconds=1  # 1 second timeout
        )

        result = await runner.execute_job(job.id)

        assert result.status == JobStatus.FAILED
        assert "timed out" in result.error


# ==================== Job Stats Tests ====================


class TestJobStats:
    """Tests for job statistics."""

    @pytest.fixture
    def runner(self):
        """Create a fresh job runner."""
        return JobRunner()

    def test_stats_empty(self, runner):
        """Test stats when no jobs exist."""
        stats = runner.get_job_stats()

        assert stats.total_jobs == 0
        assert stats.pending_count == 0
        assert stats.success_rate is None

    def test_stats_counts(self, runner):
        """Test stats counting."""
        # Create jobs in different states
        pending = runner.enqueue_job(job_type=JobType.REPORT, payload={})
        running = runner.enqueue_job(job_type=JobType.EXPORT, payload={})
        completed = runner.enqueue_job(job_type=JobType.BULK_IMPORT, payload={})
        failed = runner.enqueue_job(job_type=JobType.CUSTOM, payload={})

        running.status = JobStatus.RUNNING
        completed.status = JobStatus.COMPLETED
        failed.status = JobStatus.FAILED

        stats = runner.get_job_stats()

        assert stats.total_jobs == 4
        assert stats.pending_count == 1
        assert stats.running_count == 1
        assert stats.completed_count == 1
        assert stats.failed_count == 1

    def test_stats_success_rate(self, runner):
        """Test success rate calculation."""
        completed = runner.enqueue_job(job_type=JobType.REPORT, payload={})
        failed = runner.enqueue_job(job_type=JobType.EXPORT, payload={})

        completed.status = JobStatus.COMPLETED
        failed.status = JobStatus.FAILED

        stats = runner.get_job_stats()

        assert stats.success_rate == 50.0


# ==================== Worker Lifecycle Tests ====================


class TestWorkerLifecycle:
    """Tests for worker lifecycle management."""

    @pytest.fixture
    def runner(self):
        """Create a fresh job runner."""
        return JobRunner()

    def test_worker_initial_status(self, runner):
        """Test initial worker status."""
        status = runner.get_worker_status()

        assert status.is_running is False
        assert status.started_at is None
        assert status.jobs_processed == 0

    @pytest.mark.asyncio
    async def test_start_worker(self, runner):
        """Test starting the worker."""
        await runner.start_worker()

        try:
            status = runner.get_worker_status()
            assert status.is_running is True
            assert status.started_at is not None
        finally:
            await runner.stop_worker()

    @pytest.mark.asyncio
    async def test_stop_worker(self, runner):
        """Test stopping the worker."""
        await runner.start_worker()
        await runner.stop_worker()

        status = runner.get_worker_status()
        assert status.is_running is False

    @pytest.mark.asyncio
    async def test_start_already_running_worker(self, runner):
        """Test starting an already running worker."""
        await runner.start_worker()

        try:
            # Should not raise, just log warning
            await runner.start_worker()
        finally:
            await runner.stop_worker()

    @pytest.mark.asyncio
    async def test_stop_not_running_worker(self, runner):
        """Test stopping a worker that isn't running."""
        # Should not raise, just log warning
        await runner.stop_worker()


# ==================== Integration Hook Tests ====================


class TestIntegrationHooks:
    """Tests for scheduler integration hooks."""

    @pytest.fixture
    def runner(self):
        """Create a fresh job runner."""
        return JobRunner()

    def test_enqueue_scheduled_report(self, runner):
        """Test enqueueing a scheduled report job."""
        job = runner.enqueue_scheduled_report(
            schedule_id="schedule-123",
            priority=JobPriority.HIGH
        )

        assert job.job_type == JobType.REPORT
        assert job.payload["schedule_id"] == "schedule-123"
        assert job.priority == JobPriority.HIGH
        assert job.created_by == "scheduler"

    def test_enqueue_export(self, runner):
        """Test enqueueing an export job."""
        job = runner.enqueue_export(
            project_id="test-project",
            export_format="json",
            entity_ids=["entity-1", "entity-2"],
            include_relationships=True,
            created_by="user123"
        )

        assert job.job_type == JobType.EXPORT
        assert job.payload["project_id"] == "test-project"
        assert job.payload["format"] == "json"
        assert job.payload["entity_ids"] == ["entity-1", "entity-2"]
        assert job.created_by == "user123"

    def test_enqueue_bulk_import(self, runner):
        """Test enqueueing a bulk import job."""
        entities = [{"profile": {"name": "Test"}}]
        job = runner.enqueue_bulk_import(
            project_id="test-project",
            entities=entities,
            update_existing=True,
            created_by="user456"
        )

        assert job.job_type == JobType.BULK_IMPORT
        assert job.payload["project_id"] == "test-project"
        assert job.payload["entities"] == entities
        assert job.payload["update_existing"] is True
        assert job.priority == JobPriority.HIGH


# ==================== Utility Method Tests ====================


class TestUtilityMethods:
    """Tests for utility methods."""

    @pytest.fixture
    def runner(self):
        """Create a fresh job runner."""
        return JobRunner()

    def test_clear_all_jobs(self, runner):
        """Test clearing all jobs."""
        runner.enqueue_job(job_type=JobType.REPORT, payload={})
        runner.enqueue_job(job_type=JobType.EXPORT, payload={})

        count = runner.clear_all_jobs()

        assert count == 2
        assert len(runner._jobs) == 0

    def test_clear_completed_jobs(self, runner):
        """Test clearing old completed jobs."""
        old_job = runner.enqueue_job(job_type=JobType.REPORT, payload={})
        old_job.status = JobStatus.COMPLETED
        old_job.completed_at = datetime.now(timezone.utc) - timedelta(hours=48)

        new_job = runner.enqueue_job(job_type=JobType.EXPORT, payload={})
        new_job.status = JobStatus.COMPLETED
        new_job.completed_at = datetime.now(timezone.utc)

        count = runner.clear_completed_jobs(max_age_hours=24)

        assert count == 1
        assert runner.get_job(old_job.id) is None
        assert runner.get_job(new_job.id) is not None

    def test_register_custom_handler(self, runner):
        """Test registering a custom job handler."""
        async def custom_handler(job):
            return {"custom": "result"}

        runner.register_job_handler(JobType.CUSTOM, custom_handler)

        assert runner._job_handlers[JobType.CUSTOM] == custom_handler

    def test_get_jobs_by_status(self, runner):
        """Test getting jobs by status."""
        pending = runner.enqueue_job(job_type=JobType.REPORT, payload={})
        running = runner.enqueue_job(job_type=JobType.EXPORT, payload={})
        running.status = JobStatus.RUNNING

        pending_jobs = runner.get_jobs_by_status(JobStatus.PENDING)
        running_jobs = runner.get_jobs_by_status(JobStatus.RUNNING)

        assert len(pending_jobs) == 1
        assert pending_jobs[0].id == pending.id
        assert len(running_jobs) == 1
        assert running_jobs[0].id == running.id


# ==================== Singleton Tests ====================


class TestJobRunnerSingleton:
    """Tests for job runner singleton management."""

    def test_get_runner_creates_singleton(self):
        """Test that get_job_runner creates a singleton."""
        set_job_runner(None)

        runner1 = get_job_runner()
        runner2 = get_job_runner()

        assert runner1 is runner2

    def test_set_runner(self):
        """Test setting the runner singleton."""
        custom_runner = JobRunner()

        set_job_runner(custom_runner)
        retrieved = get_job_runner()

        assert retrieved is custom_runner

    def test_set_runner_to_none(self):
        """Test clearing the runner singleton."""
        set_job_runner(None)
        runner = get_job_runner()
        assert runner is not None  # Creates a new one


# ==================== Router Tests ====================


class TestJobsRouter:
    """Tests for jobs router endpoints and models."""

    def test_router_import(self):
        """Test that jobs router can be imported."""
        from api.routers.jobs import router
        assert router is not None

    def test_models_import(self):
        """Test that all request/response models can be imported."""
        from api.routers.jobs import (
            EnqueueJobRequest,
            JobResponse,
            JobListResponse,
            JobResultResponse,
            JobStatsResponse,
            WorkerStatusResponse,
            RunScheduleResponse,
            CancelJobResponse,
            RetryJobResponse,
        )

        assert hasattr(EnqueueJobRequest, "model_fields")
        assert hasattr(JobResponse, "model_fields")
        assert hasattr(JobListResponse, "model_fields")
        assert hasattr(JobResultResponse, "model_fields")
        assert hasattr(JobStatsResponse, "model_fields")

    def test_parse_job_type_helper(self):
        """Test _parse_job_type helper function."""
        from api.routers.jobs import _parse_job_type

        assert _parse_job_type("report") == JobType.REPORT
        assert _parse_job_type("export") == JobType.EXPORT
        assert _parse_job_type("bulk_import") == JobType.BULK_IMPORT
        assert _parse_job_type("custom") == JobType.CUSTOM

    def test_parse_job_type_invalid(self):
        """Test that invalid job_type raises HTTPException."""
        from api.routers.jobs import _parse_job_type
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _parse_job_type("invalid")

        assert exc_info.value.status_code == 400

    def test_parse_priority_helper(self):
        """Test _parse_priority helper function."""
        from api.routers.jobs import _parse_priority

        assert _parse_priority("low") == JobPriority.LOW
        assert _parse_priority("normal") == JobPriority.NORMAL
        assert _parse_priority("high") == JobPriority.HIGH
        assert _parse_priority("critical") == JobPriority.CRITICAL

    def test_parse_priority_invalid(self):
        """Test that invalid priority raises HTTPException."""
        from api.routers.jobs import _parse_priority
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _parse_priority("invalid")

        assert exc_info.value.status_code == 400

    def test_parse_status_helper(self):
        """Test _parse_status helper function."""
        from api.routers.jobs import _parse_status

        assert _parse_status("pending") == JobStatus.PENDING
        assert _parse_status("running") == JobStatus.RUNNING
        assert _parse_status("completed") == JobStatus.COMPLETED
        assert _parse_status("failed") == JobStatus.FAILED
        assert _parse_status("cancelled") == JobStatus.CANCELLED
        assert _parse_status(None) is None


# ==================== Edge Cases ====================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.fixture
    def runner(self):
        """Create a fresh job runner."""
        return JobRunner()

    def test_enqueue_with_empty_payload(self, runner):
        """Test enqueueing job with empty payload."""
        job = runner.enqueue_job(
            job_type=JobType.REPORT,
            payload={}
        )

        assert job.payload == {}

    def test_enqueue_with_complex_payload(self, runner):
        """Test enqueueing job with complex nested payload."""
        complex_payload = {
            "nested": {
                "deep": {
                    "value": [1, 2, 3]
                }
            },
            "list": ["a", "b", "c"]
        }

        job = runner.enqueue_job(
            job_type=JobType.REPORT,
            payload=complex_payload
        )

        assert job.payload == complex_payload

    def test_multiple_jobs_unique_ids(self, runner):
        """Test that multiple jobs have unique IDs."""
        ids = set()
        for _ in range(100):
            job = runner.enqueue_job(job_type=JobType.REPORT, payload={})
            ids.add(job.id)

        assert len(ids) == 100

    @pytest.mark.asyncio
    async def test_execute_without_scheduler_retries(self, runner):
        """Test that executing report job without scheduler triggers retry."""
        runner._report_scheduler = None

        job = runner.enqueue_job(
            job_type=JobType.REPORT,
            payload={"schedule_id": "test"},
            max_retries=0  # No retries so it fails immediately
        )

        result = await runner.execute_job(job.id)
        assert result.status == JobStatus.FAILED
        assert "report_scheduler is not configured" in result.error

    @pytest.mark.asyncio
    async def test_execute_export_without_service_retries(self, runner):
        """Test that executing export job without service triggers retry."""
        runner._bulk_operations_service = None

        job = runner.enqueue_job(
            job_type=JobType.EXPORT,
            payload={"project_id": "test"},
            max_retries=0  # No retries so it fails immediately
        )

        result = await runner.execute_job(job.id)
        assert result.status == JobStatus.FAILED
        assert "bulk_operations_service is not configured" in result.error

    @pytest.mark.asyncio
    async def test_execute_import_without_service_retries(self, runner):
        """Test that executing import job without service triggers retry."""
        runner._bulk_operations_service = None

        job = runner.enqueue_job(
            job_type=JobType.BULK_IMPORT,
            payload={"project_id": "test", "entities": []},
            max_retries=0  # No retries so it fails immediately
        )

        result = await runner.execute_job(job.id)
        assert result.status == JobStatus.FAILED
        assert "bulk_operations_service is not configured" in result.error

    def test_cancel_job_sets_completed_at(self, runner):
        """Test that cancelling job sets completed_at."""
        job = runner.enqueue_job(job_type=JobType.REPORT, payload={})

        before = datetime.now(timezone.utc)
        runner.cancel_job(job.id)
        after = datetime.now(timezone.utc)

        updated = runner.get_job(job.id)
        assert before <= updated.completed_at <= after

    @pytest.mark.asyncio
    async def test_worker_processes_jobs(self, runner):
        """Test that worker processes pending jobs."""
        mock_scheduler = MagicMock()
        mock_scheduler.run_scheduled_report.return_value = b"report"

        runner._report_scheduler = mock_scheduler

        job = runner.enqueue_job(
            job_type=JobType.REPORT,
            payload={"schedule_id": "test"}
        )

        await runner.start_worker()

        # Give worker time to process
        await asyncio.sleep(0.3)

        await runner.stop_worker()

        updated = runner.get_job(job.id)
        assert updated.status == JobStatus.COMPLETED
