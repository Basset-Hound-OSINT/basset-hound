"""
Background Job Runner Service for Basset Hound

This module provides async job execution capabilities for scheduled reports and
background tasks using ARQ (async Redis queue) patterns. Supports job queueing,
status tracking, retry logic, timeout handling, and integration with the
report scheduler.

Features:
- Async job execution with ARQ-compatible patterns
- Job status tracking (PENDING, RUNNING, COMPLETED, FAILED, CANCELLED)
- Configurable retry logic with exponential backoff
- Timeout handling for long-running jobs
- In-memory job history (ready for Redis migration)
- Integration with report scheduler
"""

import asyncio
import logging
import threading
from collections import OrderedDict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union
from uuid import uuid4

from pydantic import BaseModel, Field, ConfigDict

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """Status states for background jobs."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(str, Enum):
    """Types of jobs supported by the runner."""
    REPORT = "report"
    EXPORT = "export"
    BULK_IMPORT = "bulk_import"
    CUSTOM = "custom"


class JobPriority(str, Enum):
    """Priority levels for job execution."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class JobResult(BaseModel):
    """
    Result of a job execution.

    Attributes:
        job_id: Unique identifier for the job
        status: Current status of the job
        result: Result data if job completed successfully
        error: Error message if job failed
        started_at: When the job started executing
        completed_at: When the job finished (success or failure)
        duration_ms: Execution duration in milliseconds
        retry_count: Number of retries attempted
        metadata: Additional job metadata
    """
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "completed",
                "result": {"report_size_bytes": 15432},
                "error": None,
                "started_at": "2024-01-15T10:00:00Z",
                "completed_at": "2024-01-15T10:00:05Z",
                "duration_ms": 5000,
                "retry_count": 0,
                "metadata": {}
            }
        }
    )

    job_id: str = Field(..., description="Unique job identifier")
    status: JobStatus = Field(..., description="Current job status")
    result: Optional[Any] = Field(default=None, description="Job result data")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    started_at: Optional[datetime] = Field(default=None, description="Start time")
    completed_at: Optional[datetime] = Field(default=None, description="Completion time")
    duration_ms: Optional[int] = Field(default=None, description="Duration in milliseconds")
    retry_count: int = Field(default=0, description="Number of retries")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Job metadata")


class Job(BaseModel):
    """
    Represents a background job in the queue.

    Attributes:
        id: Unique job identifier
        job_type: Type of job (report, export, bulk_import, custom)
        status: Current job status
        priority: Job priority level
        payload: Job-specific data/arguments
        created_at: When the job was created
        started_at: When the job started executing
        completed_at: When the job finished
        error: Error message if failed
        result: Result data if completed
        retry_count: Current retry count
        max_retries: Maximum retries allowed
        timeout_seconds: Job timeout in seconds
        scheduled_for: Scheduled execution time (optional)
        created_by: User/system that created the job
    """
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "job_type": "report",
                "status": "pending",
                "priority": "normal",
                "payload": {"schedule_id": "abc-123", "project_id": "test_project"},
                "created_at": "2024-01-15T10:00:00Z",
                "max_retries": 3,
                "timeout_seconds": 300
            }
        }
    )

    id: str = Field(default_factory=lambda: str(uuid4()), description="Unique identifier")
    job_type: JobType = Field(..., description="Type of job")
    status: JobStatus = Field(default=JobStatus.PENDING, description="Job status")
    priority: JobPriority = Field(default=JobPriority.NORMAL, description="Priority")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Job data")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = Field(default=None, description="Start time")
    completed_at: Optional[datetime] = Field(default=None, description="Completion time")
    error: Optional[str] = Field(default=None, description="Error message")
    result: Optional[Any] = Field(default=None, description="Result data")
    retry_count: int = Field(default=0, description="Current retry count")
    max_retries: int = Field(default=3, description="Maximum retries")
    timeout_seconds: int = Field(default=300, description="Timeout in seconds")
    scheduled_for: Optional[datetime] = Field(default=None, description="Scheduled time")
    created_by: str = Field(default="system", description="Creator identifier")


class JobStats(BaseModel):
    """
    Statistics about job execution.

    Attributes:
        total_jobs: Total number of jobs
        pending_count: Jobs waiting to run
        running_count: Currently running jobs
        completed_count: Successfully completed jobs
        failed_count: Failed jobs
        cancelled_count: Cancelled jobs
        avg_duration_ms: Average job duration
        success_rate: Percentage of successful jobs
    """
    model_config = ConfigDict(extra="forbid")

    total_jobs: int = Field(default=0, description="Total jobs")
    pending_count: int = Field(default=0, description="Pending jobs")
    running_count: int = Field(default=0, description="Running jobs")
    completed_count: int = Field(default=0, description="Completed jobs")
    failed_count: int = Field(default=0, description="Failed jobs")
    cancelled_count: int = Field(default=0, description="Cancelled jobs")
    avg_duration_ms: Optional[float] = Field(default=None, description="Average duration")
    success_rate: Optional[float] = Field(default=None, description="Success percentage")


class WorkerStatus(BaseModel):
    """
    Status of the job worker.

    Attributes:
        is_running: Whether the worker is running
        started_at: When the worker started
        jobs_processed: Total jobs processed
        current_job_id: ID of currently running job
        last_heartbeat: Last heartbeat timestamp
    """
    model_config = ConfigDict(extra="forbid")

    is_running: bool = Field(default=False, description="Worker running state")
    started_at: Optional[datetime] = Field(default=None, description="Start time")
    jobs_processed: int = Field(default=0, description="Jobs processed count")
    current_job_id: Optional[str] = Field(default=None, description="Current job ID")
    last_heartbeat: Optional[datetime] = Field(default=None, description="Last heartbeat")


class JobRunner:
    """
    Service for managing background job execution.

    Provides methods for enqueueing jobs, tracking status, handling retries,
    and executing various job types including reports, exports, and bulk imports.
    Uses in-memory storage with interfaces designed for Redis/ARQ migration.
    """

    def __init__(
        self,
        neo4j_handler=None,
        report_scheduler=None,
        report_export_service=None,
        bulk_operations_service=None,
        max_concurrent_jobs: int = 5,
        max_jobs: int = 1000,
        max_job_results: int = 1000,
    ):
        """
        Initialize the job runner.

        Args:
            neo4j_handler: Neo4j database handler instance
            report_scheduler: ReportScheduler instance for scheduled reports
            report_export_service: ReportExportService for generating reports
            bulk_operations_service: BulkOperationsService for imports
            max_concurrent_jobs: Maximum number of concurrent jobs
            max_jobs: Maximum number of jobs to store in memory (LRU eviction)
            max_job_results: Maximum number of job results to store in memory (LRU eviction)
        """
        self._handler = neo4j_handler
        self._report_scheduler = report_scheduler
        self._report_export_service = report_export_service
        self._bulk_operations_service = bulk_operations_service
        self._max_concurrent_jobs = max_concurrent_jobs
        self._max_jobs = max_jobs
        self._max_job_results = max_job_results

        # In-memory storage with thread safety and LRU ordering
        self._lock = threading.RLock()
        self._jobs: OrderedDict[str, Job] = OrderedDict()
        self._job_results: OrderedDict[str, JobResult] = OrderedDict()

        # Worker state
        self._worker_running = False
        self._worker_started_at: Optional[datetime] = None
        self._jobs_processed = 0
        self._current_job_id: Optional[str] = None
        self._worker_task: Optional[asyncio.Task] = None
        self._last_heartbeat: Optional[datetime] = None

        # Registered job handlers
        self._job_handlers: Dict[JobType, Callable] = {
            JobType.REPORT: self.execute_report_job,
            JobType.EXPORT: self.execute_export_job,
            JobType.BULK_IMPORT: self.execute_bulk_import_job,
        }

    # ==================== Memory Management ====================

    def _enforce_jobs_limit(self) -> None:
        """Evict oldest jobs when limit is exceeded (LRU eviction)."""
        while len(self._jobs) > self._max_jobs:
            # Get the oldest job (first in OrderedDict)
            oldest_key = next(iter(self._jobs))
            oldest_job = self._jobs[oldest_key]
            # Only evict completed/failed/cancelled jobs
            if oldest_job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
                del self._jobs[oldest_key]
                logger.debug(f"LRU evicted job: {oldest_key}")
            else:
                # Move to end to avoid infinite loop with active jobs
                self._jobs.move_to_end(oldest_key)
                # If we've cycled through all and none can be evicted, break
                if next(iter(self._jobs)) == oldest_key:
                    break

    def _enforce_results_limit(self) -> None:
        """Evict oldest job results when limit is exceeded (LRU eviction)."""
        while len(self._job_results) > self._max_job_results:
            oldest_key = next(iter(self._job_results))
            del self._job_results[oldest_key]
            logger.debug(f"LRU evicted job result: {oldest_key}")

    def get_jobs_size(self) -> int:
        """Get current number of jobs in storage."""
        with self._lock:
            return len(self._jobs)

    def get_jobs_capacity(self) -> int:
        """Get maximum job storage capacity."""
        return self._max_jobs

    def get_results_size(self) -> int:
        """Get current number of job results in storage."""
        with self._lock:
            return len(self._job_results)

    def get_results_capacity(self) -> int:
        """Get maximum job results storage capacity."""
        return self._max_job_results

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory usage statistics for this service."""
        with self._lock:
            return {
                "jobs_count": len(self._jobs),
                "jobs_capacity": self._max_jobs,
                "jobs_usage_percent": (len(self._jobs) / self._max_jobs * 100) if self._max_jobs > 0 else 0,
                "results_count": len(self._job_results),
                "results_capacity": self._max_job_results,
                "results_usage_percent": (len(self._job_results) / self._max_job_results * 100) if self._max_job_results > 0 else 0,
            }

    # ==================== Queue Management ====================

    def enqueue_job(
        self,
        job_type: JobType,
        payload: Dict[str, Any],
        priority: JobPriority = JobPriority.NORMAL,
        max_retries: int = 3,
        timeout_seconds: int = 300,
        scheduled_for: Optional[datetime] = None,
        created_by: str = "system"
    ) -> Job:
        """
        Enqueue a new job for execution.

        Args:
            job_type: Type of job to execute
            payload: Job-specific data and arguments
            priority: Execution priority
            max_retries: Maximum retry attempts
            timeout_seconds: Job timeout
            scheduled_for: Optional scheduled execution time
            created_by: User/system creating the job

        Returns:
            The created Job object

        Raises:
            ValueError: If job_type is invalid
        """
        if not isinstance(job_type, JobType):
            try:
                job_type = JobType(job_type)
            except ValueError:
                valid_types = ", ".join([t.value for t in JobType])
                raise ValueError(f"Invalid job_type. Must be one of: {valid_types}")

        job_id = str(uuid4())
        now = datetime.now(timezone.utc)

        job = Job(
            id=job_id,
            job_type=job_type,
            status=JobStatus.PENDING,
            priority=priority,
            payload=payload,
            created_at=now,
            max_retries=max_retries,
            timeout_seconds=timeout_seconds,
            scheduled_for=scheduled_for,
            created_by=created_by
        )

        with self._lock:
            self._jobs[job_id] = job
            self._jobs.move_to_end(job_id)  # Mark as most recently used
            self._enforce_jobs_limit()
        logger.info(f"Enqueued job {job_id} of type {job_type.value}")

        return job

    def get_job(self, job_id: str) -> Optional[Job]:
        """
        Get a job by its ID.

        Args:
            job_id: The unique job identifier

        Returns:
            Job if found, None otherwise
        """
        with self._lock:
            job = self._jobs.get(job_id)
            if job is not None:
                self._jobs.move_to_end(job_id)  # Mark as most recently used
            return job

    def get_job_status(self, job_id: str) -> Optional[JobStatus]:
        """
        Get the current status of a job.

        Args:
            job_id: The unique job identifier

        Returns:
            JobStatus if job found, None otherwise
        """
        with self._lock:
            job = self._jobs.get(job_id)
            return job.status if job else None

    def get_job_result(self, job_id: str) -> Optional[JobResult]:
        """
        Get the result of a completed job.

        Args:
            job_id: The unique job identifier

        Returns:
            JobResult if available, None otherwise
        """
        with self._lock:
            result = self._job_results.get(job_id)
            if result is not None:
                self._job_results.move_to_end(job_id)  # Mark as most recently used
            return result

    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a pending or running job.

        Args:
            job_id: The unique job identifier

        Returns:
            True if job was cancelled, False otherwise
        """
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return False

            if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
                return False

            # Update job status
            job.status = JobStatus.CANCELLED
            job.completed_at = datetime.now(timezone.utc)
            job.error = "Job cancelled by user"

            # Create result record
            self._job_results[job_id] = JobResult(
                job_id=job_id,
                status=JobStatus.CANCELLED,
                error="Job cancelled by user",
                completed_at=job.completed_at,
                retry_count=job.retry_count,
                metadata={"cancelled_from_status": job.status.value}
            )
            self._job_results.move_to_end(job_id)
            self._enforce_results_limit()

        logger.info(f"Cancelled job {job_id}")
        return True

    def list_jobs(
        self,
        status: Optional[JobStatus] = None,
        job_type: Optional[JobType] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Job]:
        """
        List jobs with optional filtering.

        Args:
            status: Filter by job status
            job_type: Filter by job type
            limit: Maximum number of results
            offset: Skip first N results

        Returns:
            List of matching Job objects
        """
        with self._lock:
            jobs = list(self._jobs.values())

        # Apply filters
        if status is not None:
            jobs = [j for j in jobs if j.status == status]
        if job_type is not None:
            jobs = [j for j in jobs if j.job_type == job_type]

        # Sort by priority (descending) and created_at (ascending)
        priority_order = {
            JobPriority.CRITICAL: 0,
            JobPriority.HIGH: 1,
            JobPriority.NORMAL: 2,
            JobPriority.LOW: 3
        }
        jobs.sort(key=lambda j: (priority_order.get(j.priority, 2), j.created_at))

        # Apply pagination
        return jobs[offset:offset + limit]

    def get_pending_jobs(self) -> List[Job]:
        """
        Get all pending jobs ordered by priority and creation time.

        Returns:
            List of pending Job objects
        """
        return self.list_jobs(status=JobStatus.PENDING)

    def get_running_jobs(self) -> List[Job]:
        """
        Get all currently running jobs.

        Returns:
            List of running Job objects
        """
        return self.list_jobs(status=JobStatus.RUNNING)

    def get_job_stats(self) -> JobStats:
        """
        Get statistics about job execution.

        Returns:
            JobStats with aggregated metrics
        """
        with self._lock:
            jobs = list(self._jobs.values())
            job_results = list(self._job_results.values())

        total = len(jobs)

        if total == 0:
            return JobStats()

        pending = sum(1 for j in jobs if j.status == JobStatus.PENDING)
        running = sum(1 for j in jobs if j.status == JobStatus.RUNNING)
        completed = sum(1 for j in jobs if j.status == JobStatus.COMPLETED)
        failed = sum(1 for j in jobs if j.status == JobStatus.FAILED)
        cancelled = sum(1 for j in jobs if j.status == JobStatus.CANCELLED)

        # Calculate average duration for completed jobs
        completed_results = [
            r for r in job_results
            if r.status == JobStatus.COMPLETED and r.duration_ms is not None
        ]

        avg_duration = None
        if completed_results:
            avg_duration = sum(r.duration_ms for r in completed_results) / len(completed_results)

        # Calculate success rate
        finished = completed + failed
        success_rate = (completed / finished * 100) if finished > 0 else None

        return JobStats(
            total_jobs=total,
            pending_count=pending,
            running_count=running,
            completed_count=completed,
            failed_count=failed,
            cancelled_count=cancelled,
            avg_duration_ms=avg_duration,
            success_rate=success_rate
        )

    # ==================== Job Execution ====================

    async def execute_job(self, job_id: str) -> JobResult:
        """
        Execute a job immediately.

        Args:
            job_id: The job ID to execute

        Returns:
            JobResult with execution outcome

        Raises:
            ValueError: If job not found or already executed
        """
        # Get job with lock, but release before long-running execution
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise ValueError(f"Job not found: {job_id}")

            if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
                raise ValueError(f"Job already in terminal state: {job.status.value}")

            # Mark job as running
            job.status = JobStatus.RUNNING
            job.started_at = datetime.now(timezone.utc)
            self._current_job_id = job_id

            # Get handler while holding lock
            handler = self._job_handlers.get(job.job_type)
            timeout_seconds = job.timeout_seconds

        result = None
        error = None

        try:
            if handler is None:
                raise ValueError(f"No handler for job type: {job.job_type.value}")

            # Execute with timeout - NO lock held during long operation
            result = await asyncio.wait_for(
                handler(job),
                timeout=timeout_seconds
            )

            with self._lock:
                job.status = JobStatus.COMPLETED
                job.result = result

        except asyncio.TimeoutError:
            error = f"Job timed out after {timeout_seconds} seconds"
            with self._lock:
                job.status = JobStatus.FAILED
                job.error = error
            logger.error(f"Job {job_id} timed out")

        except asyncio.CancelledError:
            error = "Job was cancelled"
            with self._lock:
                job.status = JobStatus.CANCELLED
                job.error = error
            logger.info(f"Job {job_id} was cancelled")

        except Exception as e:
            error = str(e)
            with self._lock:
                job.error = error

                # Check if we should retry
                if job.retry_count < job.max_retries:
                    job.retry_count += 1
                    job.status = JobStatus.PENDING
                    job.started_at = None
                    logger.warning(
                        f"Job {job_id} failed, retry {job.retry_count}/{job.max_retries}: {error}"
                    )
                else:
                    job.status = JobStatus.FAILED
                    logger.error(f"Job {job_id} failed after {job.retry_count} retries: {error}")

        finally:
            with self._lock:
                job.completed_at = datetime.now(timezone.utc)
                self._current_job_id = None

                if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
                    self._jobs_processed += 1

        # Calculate duration
        duration_ms = None
        if job.started_at and job.completed_at:
            duration = (job.completed_at - job.started_at).total_seconds() * 1000
            duration_ms = int(duration)

        # Create and store result
        job_result = JobResult(
            job_id=job_id,
            status=job.status,
            result=result,
            error=error,
            started_at=job.started_at,
            completed_at=job.completed_at,
            duration_ms=duration_ms,
            retry_count=job.retry_count,
            metadata={"job_type": job.job_type.value, "priority": job.priority.value}
        )

        with self._lock:
            self._job_results[job_id] = job_result
            self._job_results.move_to_end(job_id)
            self._enforce_results_limit()
        return job_result

    async def execute_report_job(self, job: Job) -> Dict[str, Any]:
        """
        Execute a report generation job.

        Args:
            job: The job to execute

        Returns:
            Dict with report generation result

        Raises:
            ValueError: If required services not configured
        """
        if self._report_scheduler is None:
            raise ValueError("report_scheduler is not configured")

        schedule_id = job.payload.get("schedule_id")
        if schedule_id:
            # Run from schedule
            report_bytes = self._report_scheduler.run_scheduled_report(schedule_id)
            if report_bytes is None:
                raise ValueError(f"Schedule not found: {schedule_id}")

            return {
                "schedule_id": schedule_id,
                "report_size_bytes": len(report_bytes),
                "generated_at": datetime.now(timezone.utc).isoformat()
            }

        # Direct report generation
        if self._report_export_service is None:
            raise ValueError("report_export_service is not configured")

        project_id = job.payload.get("project_id")
        report_type = job.payload.get("report_type", "summary")

        if report_type == "summary":
            from .report_export_service import ReportFormat
            format_str = job.payload.get("format", "html")
            report_format = ReportFormat(format_str)
            report_bytes = self._report_export_service.generate_project_summary(
                project_id,
                report_format
            )
        else:
            from .report_export_service import ReportOptions, ReportFormat
            format_str = job.payload.get("format", "html")
            options = ReportOptions(
                title=job.payload.get("title", "Report"),
                format=ReportFormat(format_str),
                project_id=project_id,
                entity_ids=job.payload.get("entity_ids"),
                include_graph=job.payload.get("include_graph", True),
                include_timeline=job.payload.get("include_timeline", True),
                include_statistics=job.payload.get("include_statistics", True)
            )
            report_bytes = self._report_export_service.generate_report(options)

        return {
            "project_id": project_id,
            "report_type": report_type,
            "report_size_bytes": len(report_bytes),
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

    async def execute_export_job(self, job: Job) -> Dict[str, Any]:
        """
        Execute an entity export job.

        Args:
            job: The job to execute

        Returns:
            Dict with export result

        Raises:
            ValueError: If bulk_operations_service not configured
        """
        if self._bulk_operations_service is None:
            raise ValueError("bulk_operations_service is not configured")

        project_id = job.payload.get("project_id")
        if not project_id:
            raise ValueError("project_id is required")

        from .bulk_operations import BulkExportOptions

        export_format = job.payload.get("format", "json")
        entity_ids = job.payload.get("entity_ids")
        include_relationships = job.payload.get("include_relationships", True)

        options = BulkExportOptions(
            format=export_format,
            include_relationships=include_relationships,
            entity_ids=entity_ids
        )

        export_data = self._bulk_operations_service.export_entities(project_id, options)

        return {
            "project_id": project_id,
            "format": export_format,
            "export_size_bytes": len(export_data.encode() if isinstance(export_data, str) else export_data),
            "exported_at": datetime.now(timezone.utc).isoformat()
        }

    async def execute_bulk_import_job(self, job: Job) -> Dict[str, Any]:
        """
        Execute a bulk import job.

        Args:
            job: The job to execute

        Returns:
            Dict with import result

        Raises:
            ValueError: If bulk_operations_service not configured
        """
        if self._bulk_operations_service is None:
            raise ValueError("bulk_operations_service is not configured")

        project_id = job.payload.get("project_id")
        if not project_id:
            raise ValueError("project_id is required")

        entities = job.payload.get("entities", [])
        update_existing = job.payload.get("update_existing", False)

        result = self._bulk_operations_service.import_entities(
            project_id,
            entities,
            update_existing
        )

        return {
            "project_id": project_id,
            "total": result.total,
            "successful": result.successful,
            "failed": result.failed,
            "created_ids": result.created_ids,
            "errors": result.errors,
            "imported_at": datetime.now(timezone.utc).isoformat()
        }

    # ==================== Worker Lifecycle ====================

    async def start_worker(self) -> None:
        """
        Start the background worker for processing jobs.

        The worker continuously processes pending jobs in priority order.
        """
        if self._worker_running:
            logger.warning("Worker is already running")
            return

        self._worker_running = True
        self._worker_started_at = datetime.now(timezone.utc)
        self._last_heartbeat = self._worker_started_at

        logger.info("Job worker started")

        self._worker_task = asyncio.create_task(self._worker_loop())

    async def _worker_loop(self) -> None:
        """Internal worker loop that processes jobs."""
        while self._worker_running:
            try:
                self._last_heartbeat = datetime.now(timezone.utc)

                # Get next pending job
                pending_jobs = self.get_pending_jobs()

                # Filter scheduled jobs that aren't due yet
                now = datetime.now(timezone.utc)
                ready_jobs = [
                    j for j in pending_jobs
                    if j.scheduled_for is None or j.scheduled_for <= now
                ]

                if ready_jobs:
                    # Process highest priority job
                    job = ready_jobs[0]
                    try:
                        await self.execute_job(job.id)
                    except Exception as e:
                        logger.error(f"Error executing job {job.id}: {e}")

                # Small delay to prevent tight loop
                await asyncio.sleep(0.1)

            except asyncio.CancelledError:
                logger.info("Worker loop cancelled")
                break
            except Exception as e:
                logger.error(f"Worker loop error: {e}")
                await asyncio.sleep(1)  # Back off on error

    async def stop_worker(self) -> None:
        """
        Stop the background worker gracefully.

        Waits for the current job to complete before stopping.
        """
        if not self._worker_running:
            logger.warning("Worker is not running")
            return

        self._worker_running = False

        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None

        logger.info("Job worker stopped")

    def get_worker_status(self) -> WorkerStatus:
        """
        Get the current status of the worker.

        Returns:
            WorkerStatus with worker state information
        """
        return WorkerStatus(
            is_running=self._worker_running,
            started_at=self._worker_started_at,
            jobs_processed=self._jobs_processed,
            current_job_id=self._current_job_id,
            last_heartbeat=self._last_heartbeat
        )

    # ==================== Integration Hooks ====================

    def enqueue_scheduled_report(
        self,
        schedule_id: str,
        priority: JobPriority = JobPriority.NORMAL
    ) -> Job:
        """
        Enqueue a job to run a scheduled report.

        Args:
            schedule_id: ID of the schedule to run
            priority: Job priority

        Returns:
            The created Job object
        """
        return self.enqueue_job(
            job_type=JobType.REPORT,
            payload={"schedule_id": schedule_id},
            priority=priority,
            created_by="scheduler"
        )

    def enqueue_export(
        self,
        project_id: str,
        export_format: str = "json",
        entity_ids: Optional[List[str]] = None,
        include_relationships: bool = True,
        created_by: str = "user"
    ) -> Job:
        """
        Enqueue an entity export job.

        Args:
            project_id: Project to export from
            export_format: Output format (json, csv, jsonl)
            entity_ids: Specific entities to export (None = all)
            include_relationships: Include relationship data
            created_by: User creating the export

        Returns:
            The created Job object
        """
        return self.enqueue_job(
            job_type=JobType.EXPORT,
            payload={
                "project_id": project_id,
                "format": export_format,
                "entity_ids": entity_ids,
                "include_relationships": include_relationships
            },
            created_by=created_by
        )

    def enqueue_bulk_import(
        self,
        project_id: str,
        entities: List[Dict[str, Any]],
        update_existing: bool = False,
        created_by: str = "user"
    ) -> Job:
        """
        Enqueue a bulk import job.

        Args:
            project_id: Project to import into
            entities: List of entity dictionaries
            update_existing: Whether to update existing entities
            created_by: User creating the import

        Returns:
            The created Job object
        """
        return self.enqueue_job(
            job_type=JobType.BULK_IMPORT,
            payload={
                "project_id": project_id,
                "entities": entities,
                "update_existing": update_existing
            },
            priority=JobPriority.HIGH,  # Imports typically need quick processing
            created_by=created_by
        )

    # ==================== Utility Methods ====================

    def clear_completed_jobs(self, max_age_hours: int = 24) -> int:
        """
        Clear completed jobs older than specified age.

        Args:
            max_age_hours: Maximum age in hours for completed jobs

        Returns:
            Number of jobs cleared
        """
        cutoff = datetime.now(timezone.utc)
        from datetime import timedelta
        cutoff = cutoff - timedelta(hours=max_age_hours)

        with self._lock:
            jobs_to_remove = []
            for job_id, job in self._jobs.items():
                if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
                    if job.completed_at and job.completed_at < cutoff:
                        jobs_to_remove.append(job_id)

            for job_id in jobs_to_remove:
                del self._jobs[job_id]
                if job_id in self._job_results:
                    del self._job_results[job_id]

        logger.info(f"Cleared {len(jobs_to_remove)} old jobs")
        return len(jobs_to_remove)

    def clear_all_jobs(self) -> int:
        """
        Clear all jobs from storage.

        Returns:
            Number of jobs cleared
        """
        with self._lock:
            count = len(self._jobs)
            self._jobs.clear()
            self._job_results.clear()
        logger.info(f"Cleared {count} jobs")
        return count

    def register_job_handler(
        self,
        job_type: JobType,
        handler: Callable
    ) -> None:
        """
        Register a custom job handler.

        Args:
            job_type: Type of job to handle
            handler: Async callable that takes a Job and returns a result
        """
        self._job_handlers[job_type] = handler
        logger.info(f"Registered handler for job type: {job_type.value}")

    def get_jobs_by_status(self, status: JobStatus) -> List[Job]:
        """
        Get all jobs with a specific status.

        Args:
            status: Status to filter by

        Returns:
            List of jobs with that status
        """
        with self._lock:
            return [j for j in self._jobs.values() if j.status == status]

    def retry_failed_job(self, job_id: str) -> bool:
        """
        Manually retry a failed job.

        Args:
            job_id: ID of the failed job

        Returns:
            True if job was reset for retry, False otherwise
        """
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return False

            if job.status != JobStatus.FAILED:
                return False

            # Reset job for retry
            job.status = JobStatus.PENDING
            job.started_at = None
            job.completed_at = None
            job.error = None
            job.retry_count = 0  # Reset retry count for manual retry

        logger.info(f"Job {job_id} reset for manual retry")
        return True


# Singleton instance management
_job_runner: Optional[JobRunner] = None
_job_runner_lock = threading.RLock()


def get_job_runner(
    neo4j_handler=None,
    report_scheduler=None,
    report_export_service=None,
    bulk_operations_service=None
) -> JobRunner:
    """
    Get or create the job runner singleton.

    Args:
        neo4j_handler: Neo4j handler instance (optional)
        report_scheduler: ReportScheduler instance (optional)
        report_export_service: ReportExportService instance (optional)
        bulk_operations_service: BulkOperationsService instance (optional)

    Returns:
        JobRunner instance
    """
    global _job_runner

    if _job_runner is None:
        with _job_runner_lock:
            # Double-check after acquiring lock
            if _job_runner is None:
                _job_runner = JobRunner(
                    neo4j_handler,
                    report_scheduler,
                    report_export_service,
                    bulk_operations_service
                )

    return _job_runner


def set_job_runner(runner: Optional[JobRunner]) -> None:
    """Set the job runner singleton (for testing)."""
    global _job_runner
    with _job_runner_lock:
        _job_runner = runner
