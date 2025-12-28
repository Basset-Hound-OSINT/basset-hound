"""
Jobs Router for Basset Hound.

Provides endpoints for managing background job execution including:
- Enqueuing new jobs
- Listing and filtering jobs
- Getting job details and results
- Cancelling jobs
- Running scheduled reports immediately
- Job statistics
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from ..dependencies import get_neo4j_handler
from ..services.job_runner import (
    Job,
    JobResult,
    JobRunner,
    JobStats,
    JobStatus,
    JobType,
    JobPriority,
    WorkerStatus,
    get_job_runner,
)
from ..services.report_scheduler import get_report_scheduler
from ..services.report_export_service import ReportExportService
from ..services.bulk_operations import BulkOperationsService


# Create router
router = APIRouter(
    prefix="/jobs",
    tags=["jobs"],
    responses={
        404: {"description": "Job not found"},
        500: {"description": "Internal server error"},
    },
)

# Create schedule-specific router for running jobs
schedule_jobs_router = APIRouter(
    prefix="/schedules",
    tags=["jobs", "schedules"],
    responses={
        404: {"description": "Schedule not found"},
        500: {"description": "Internal server error"},
    },
)


# ----- Request/Response Models -----

class EnqueueJobRequest(BaseModel):
    """Request schema for enqueuing a new job."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "job_type": "report",
                "payload": {"schedule_id": "abc-123"},
                "priority": "normal",
                "max_retries": 3,
                "timeout_seconds": 300
            }
        }
    )

    job_type: str = Field(
        ...,
        description="Type of job: report, export, bulk_import, or custom"
    )
    payload: Dict[str, Any] = Field(
        default_factory=dict,
        description="Job-specific data and arguments"
    )
    priority: str = Field(
        default="normal",
        description="Priority: low, normal, high, or critical"
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum retry attempts"
    )
    timeout_seconds: int = Field(
        default=300,
        ge=10,
        le=3600,
        description="Job timeout in seconds"
    )
    scheduled_for: Optional[datetime] = Field(
        default=None,
        description="Schedule job for future execution (ISO 8601 format)"
    )


class JobResponse(BaseModel):
    """Response schema for a single job."""
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "job_type": "report",
                "status": "pending",
                "priority": "normal",
                "payload": {"schedule_id": "abc-123"},
                "created_at": "2024-01-15T10:00:00Z",
                "started_at": None,
                "completed_at": None,
                "error": None,
                "retry_count": 0,
                "max_retries": 3
            }
        }
    )

    id: str = Field(..., description="Unique job identifier")
    job_type: str = Field(..., description="Type of job")
    status: str = Field(..., description="Current status")
    priority: str = Field(..., description="Priority level")
    payload: Dict[str, Any] = Field(..., description="Job data")
    created_at: datetime = Field(..., description="Creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Start time")
    completed_at: Optional[datetime] = Field(None, description="Completion time")
    error: Optional[str] = Field(None, description="Error message if failed")
    result: Optional[Any] = Field(None, description="Result if completed")
    retry_count: int = Field(..., description="Current retry count")
    max_retries: int = Field(..., description="Maximum retries")
    timeout_seconds: int = Field(..., description="Timeout in seconds")
    scheduled_for: Optional[datetime] = Field(None, description="Scheduled time")
    created_by: str = Field(..., description="Creator")


class JobListResponse(BaseModel):
    """Response schema for listing jobs."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "jobs": [],
                "total": 0,
                "limit": 100,
                "offset": 0
            }
        }
    )

    jobs: List[JobResponse] = Field(..., description="List of jobs")
    total: int = Field(..., description="Total number of matching jobs")
    limit: int = Field(..., description="Page size limit")
    offset: int = Field(..., description="Page offset")


class JobResultResponse(BaseModel):
    """Response schema for job result."""
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "completed",
                "result": {"report_size_bytes": 15432},
                "error": None,
                "started_at": "2024-01-15T10:00:00Z",
                "completed_at": "2024-01-15T10:00:05Z",
                "duration_ms": 5000,
                "retry_count": 0
            }
        }
    )

    job_id: str = Field(..., description="Job identifier")
    status: str = Field(..., description="Final status")
    result: Optional[Any] = Field(None, description="Result data")
    error: Optional[str] = Field(None, description="Error message")
    started_at: Optional[datetime] = Field(None, description="Start time")
    completed_at: Optional[datetime] = Field(None, description="Completion time")
    duration_ms: Optional[int] = Field(None, description="Duration in milliseconds")
    retry_count: int = Field(..., description="Number of retries")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata")


class JobStatsResponse(BaseModel):
    """Response schema for job statistics."""
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "total_jobs": 100,
                "pending_count": 5,
                "running_count": 2,
                "completed_count": 85,
                "failed_count": 5,
                "cancelled_count": 3,
                "avg_duration_ms": 1500.5,
                "success_rate": 94.4
            }
        }
    )

    total_jobs: int = Field(..., description="Total jobs")
    pending_count: int = Field(..., description="Pending jobs")
    running_count: int = Field(..., description="Running jobs")
    completed_count: int = Field(..., description="Completed jobs")
    failed_count: int = Field(..., description="Failed jobs")
    cancelled_count: int = Field(..., description="Cancelled jobs")
    avg_duration_ms: Optional[float] = Field(None, description="Average duration")
    success_rate: Optional[float] = Field(None, description="Success percentage")


class WorkerStatusResponse(BaseModel):
    """Response schema for worker status."""
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "is_running": True,
                "started_at": "2024-01-15T09:00:00Z",
                "jobs_processed": 42,
                "current_job_id": None,
                "last_heartbeat": "2024-01-15T10:30:00Z"
            }
        }
    )

    is_running: bool = Field(..., description="Whether worker is running")
    started_at: Optional[datetime] = Field(None, description="Worker start time")
    jobs_processed: int = Field(..., description="Total jobs processed")
    current_job_id: Optional[str] = Field(None, description="Current job ID")
    last_heartbeat: Optional[datetime] = Field(None, description="Last heartbeat")


class RunScheduleResponse(BaseModel):
    """Response schema for running a scheduled job."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "schedule_id": "abc-123",
                "status": "pending",
                "message": "Job enqueued successfully"
            }
        }
    )

    job_id: str = Field(..., description="Created job ID")
    schedule_id: str = Field(..., description="Schedule ID")
    status: str = Field(..., description="Job status")
    message: str = Field(..., description="Status message")


class CancelJobResponse(BaseModel):
    """Response schema for job cancellation."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "cancelled": True,
                "message": "Job cancelled successfully"
            }
        }
    )

    job_id: str = Field(..., description="Job ID")
    cancelled: bool = Field(..., description="Whether cancellation succeeded")
    message: str = Field(..., description="Status message")


class RetryJobResponse(BaseModel):
    """Response schema for job retry."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "retried": True,
                "message": "Job queued for retry"
            }
        }
    )

    job_id: str = Field(..., description="Job ID")
    retried: bool = Field(..., description="Whether retry was initiated")
    message: str = Field(..., description="Status message")


# ----- Helper Functions -----

def _job_to_response(job: Job) -> JobResponse:
    """Convert Job model to response schema."""
    return JobResponse(
        id=job.id,
        job_type=job.job_type.value,
        status=job.status.value,
        priority=job.priority.value,
        payload=job.payload,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        error=job.error,
        result=job.result,
        retry_count=job.retry_count,
        max_retries=job.max_retries,
        timeout_seconds=job.timeout_seconds,
        scheduled_for=job.scheduled_for,
        created_by=job.created_by
    )


def _result_to_response(result: JobResult) -> JobResultResponse:
    """Convert JobResult model to response schema."""
    return JobResultResponse(
        job_id=result.job_id,
        status=result.status.value,
        result=result.result,
        error=result.error,
        started_at=result.started_at,
        completed_at=result.completed_at,
        duration_ms=result.duration_ms,
        retry_count=result.retry_count,
        metadata=result.metadata
    )


def _stats_to_response(stats: JobStats) -> JobStatsResponse:
    """Convert JobStats model to response schema."""
    return JobStatsResponse(
        total_jobs=stats.total_jobs,
        pending_count=stats.pending_count,
        running_count=stats.running_count,
        completed_count=stats.completed_count,
        failed_count=stats.failed_count,
        cancelled_count=stats.cancelled_count,
        avg_duration_ms=stats.avg_duration_ms,
        success_rate=stats.success_rate
    )


def _worker_status_to_response(status: WorkerStatus) -> WorkerStatusResponse:
    """Convert WorkerStatus model to response schema."""
    return WorkerStatusResponse(
        is_running=status.is_running,
        started_at=status.started_at,
        jobs_processed=status.jobs_processed,
        current_job_id=status.current_job_id,
        last_heartbeat=status.last_heartbeat
    )


def _get_job_runner_with_services(neo4j_handler) -> JobRunner:
    """Get job runner with all services configured."""
    from ..services.report_scheduler import get_report_scheduler
    from ..services.report_export_service import ReportExportService
    from ..services.bulk_operations import BulkOperationsService

    report_service = ReportExportService(neo4j_handler)
    scheduler = get_report_scheduler()
    scheduler._report_service = report_service
    scheduler._handler = neo4j_handler

    bulk_service = BulkOperationsService(neo4j_handler)

    runner = get_job_runner()
    runner._handler = neo4j_handler
    runner._report_scheduler = scheduler
    runner._report_export_service = report_service
    runner._bulk_operations_service = bulk_service

    return runner


def _parse_job_type(job_type_str: str) -> JobType:
    """Parse job type string to enum."""
    try:
        return JobType(job_type_str.lower())
    except ValueError:
        valid_types = ", ".join([t.value for t in JobType])
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid job_type '{job_type_str}'. Must be one of: {valid_types}"
        )


def _parse_priority(priority_str: str) -> JobPriority:
    """Parse priority string to enum."""
    try:
        return JobPriority(priority_str.lower())
    except ValueError:
        valid = ", ".join([p.value for p in JobPriority])
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid priority '{priority_str}'. Must be one of: {valid}"
        )


def _parse_status(status_str: Optional[str]) -> Optional[JobStatus]:
    """Parse status string to enum."""
    if status_str is None:
        return None
    try:
        return JobStatus(status_str.lower())
    except ValueError:
        valid = ", ".join([s.value for s in JobStatus])
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status '{status_str}'. Must be one of: {valid}"
        )


# ----- Job Endpoints -----

@router.post(
    "",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Enqueue a new job",
    description="Create and enqueue a new background job for execution.",
    responses={
        201: {"description": "Job enqueued successfully"},
        400: {"description": "Invalid request parameters"},
    }
)
async def enqueue_job(
    request: EnqueueJobRequest,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Enqueue a new background job.

    - **job_type**: Type of job (report, export, bulk_import, custom)
    - **payload**: Job-specific data and arguments
    - **priority**: Execution priority (low, normal, high, critical)
    - **max_retries**: Maximum retry attempts (0-10)
    - **timeout_seconds**: Job timeout (10-3600 seconds)
    - **scheduled_for**: Optional scheduled execution time
    """
    try:
        job_type = _parse_job_type(request.job_type)
        priority = _parse_priority(request.priority)

        runner = _get_job_runner_with_services(neo4j_handler)

        job = runner.enqueue_job(
            job_type=job_type,
            payload=request.payload,
            priority=priority,
            max_retries=request.max_retries,
            timeout_seconds=request.timeout_seconds,
            scheduled_for=request.scheduled_for,
            created_by="api_user"  # TODO: Get from auth context
        )

        return _job_to_response(job)

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enqueue job: {str(e)}"
        )


@router.get(
    "",
    response_model=JobListResponse,
    summary="List jobs",
    description="List all jobs with optional filtering.",
    responses={
        200: {"description": "Jobs retrieved successfully"},
    }
)
async def list_jobs(
    status_filter: Optional[str] = Query(
        None,
        alias="status",
        description="Filter by status: pending, running, completed, failed, cancelled"
    ),
    job_type: Optional[str] = Query(
        None,
        description="Filter by job type: report, export, bulk_import, custom"
    ),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Skip first N results"),
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    List jobs with optional filtering.

    - **status**: Filter by job status
    - **job_type**: Filter by job type
    - **limit**: Maximum number of results
    - **offset**: Skip first N results
    """
    try:
        runner = _get_job_runner_with_services(neo4j_handler)

        # Parse filters
        status_enum = _parse_status(status_filter)
        job_type_enum = None
        if job_type:
            job_type_enum = _parse_job_type(job_type)

        jobs = runner.list_jobs(
            status=status_enum,
            job_type=job_type_enum,
            limit=limit,
            offset=offset
        )

        return JobListResponse(
            jobs=[_job_to_response(j) for j in jobs],
            total=len(runner._jobs),  # Total unfiltered count
            limit=limit,
            offset=offset
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list jobs: {str(e)}"
        )


@router.get(
    "/stats",
    response_model=JobStatsResponse,
    summary="Get job statistics",
    description="Get aggregated statistics about job execution.",
    responses={
        200: {"description": "Statistics retrieved successfully"},
    }
)
async def get_job_stats(
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Get job execution statistics.

    Returns counts by status, average duration, and success rate.
    """
    try:
        runner = _get_job_runner_with_services(neo4j_handler)
        stats = runner.get_job_stats()
        return _stats_to_response(stats)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job stats: {str(e)}"
        )


@router.get(
    "/worker",
    response_model=WorkerStatusResponse,
    summary="Get worker status",
    description="Get the current status of the background job worker.",
    responses={
        200: {"description": "Worker status retrieved successfully"},
    }
)
async def get_worker_status(
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Get background worker status.

    Returns whether the worker is running, jobs processed, and current job.
    """
    try:
        runner = _get_job_runner_with_services(neo4j_handler)
        worker_status = runner.get_worker_status()
        return _worker_status_to_response(worker_status)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get worker status: {str(e)}"
        )


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    summary="Get job details",
    description="Get details for a specific job by ID.",
    responses={
        200: {"description": "Job retrieved successfully"},
        404: {"description": "Job not found"},
    }
)
async def get_job(
    job_id: str,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Get job details by ID.

    - **job_id**: The unique job identifier
    """
    try:
        runner = _get_job_runner_with_services(neo4j_handler)
        job = runner.get_job(job_id)

        if job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job not found: {job_id}"
            )

        return _job_to_response(job)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job: {str(e)}"
        )


@router.get(
    "/{job_id}/result",
    response_model=JobResultResponse,
    summary="Get job result",
    description="Get the result of a completed job.",
    responses={
        200: {"description": "Result retrieved successfully"},
        404: {"description": "Job or result not found"},
    }
)
async def get_job_result(
    job_id: str,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Get job result by ID.

    Returns the result data for a completed job.

    - **job_id**: The unique job identifier
    """
    try:
        runner = _get_job_runner_with_services(neo4j_handler)
        result = runner.get_job_result(job_id)

        if result is None:
            # Check if job exists
            job = runner.get_job(job_id)
            if job is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Job not found: {job_id}"
                )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Result not available for job: {job_id}"
            )

        return _result_to_response(result)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job result: {str(e)}"
        )


@router.delete(
    "/{job_id}",
    response_model=CancelJobResponse,
    summary="Cancel a job",
    description="Cancel a pending or running job.",
    responses={
        200: {"description": "Job cancelled or already in terminal state"},
        404: {"description": "Job not found"},
    }
)
async def cancel_job(
    job_id: str,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Cancel a job.

    - **job_id**: The unique job identifier

    Note: Only pending and running jobs can be cancelled.
    """
    try:
        runner = _get_job_runner_with_services(neo4j_handler)

        # Check if job exists
        job = runner.get_job(job_id)
        if job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job not found: {job_id}"
            )

        cancelled = runner.cancel_job(job_id)

        if cancelled:
            return CancelJobResponse(
                job_id=job_id,
                cancelled=True,
                message="Job cancelled successfully"
            )
        else:
            return CancelJobResponse(
                job_id=job_id,
                cancelled=False,
                message=f"Job cannot be cancelled (current status: {job.status.value})"
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel job: {str(e)}"
        )


@router.post(
    "/{job_id}/retry",
    response_model=RetryJobResponse,
    summary="Retry a failed job",
    description="Manually retry a failed job.",
    responses={
        200: {"description": "Job queued for retry"},
        404: {"description": "Job not found"},
        400: {"description": "Job cannot be retried"},
    }
)
async def retry_job(
    job_id: str,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Retry a failed job.

    - **job_id**: The unique job identifier

    Note: Only failed jobs can be retried.
    """
    try:
        runner = _get_job_runner_with_services(neo4j_handler)

        job = runner.get_job(job_id)
        if job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job not found: {job_id}"
            )

        retried = runner.retry_failed_job(job_id)

        if retried:
            return RetryJobResponse(
                job_id=job_id,
                retried=True,
                message="Job queued for retry"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Job cannot be retried (current status: {job.status.value})"
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retry job: {str(e)}"
        )


# ----- Schedule Job Endpoints -----

@schedule_jobs_router.post(
    "/{schedule_id}/run",
    response_model=RunScheduleResponse,
    summary="Run scheduled job immediately",
    description="Enqueue a job to run a scheduled report immediately.",
    responses={
        200: {"description": "Job enqueued successfully"},
        404: {"description": "Schedule not found"},
    }
)
async def run_schedule_now(
    schedule_id: str,
    priority: str = Query("normal", description="Job priority"),
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Run a scheduled report immediately.

    Creates a job to execute the scheduled report.

    - **schedule_id**: The unique schedule identifier
    - **priority**: Job priority (low, normal, high, critical)
    """
    try:
        # Validate schedule exists
        scheduler = get_report_scheduler()
        schedule = scheduler.get_schedule(schedule_id)

        if schedule is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule not found: {schedule_id}"
            )

        # Parse priority
        job_priority = _parse_priority(priority)

        # Get runner and enqueue job
        runner = _get_job_runner_with_services(neo4j_handler)
        job = runner.enqueue_scheduled_report(schedule_id, job_priority)

        return RunScheduleResponse(
            job_id=job.id,
            schedule_id=schedule_id,
            status=job.status.value,
            message="Job enqueued successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to run schedule: {str(e)}"
        )


# Export both routers
__all__ = ["router", "schedule_jobs_router"]
