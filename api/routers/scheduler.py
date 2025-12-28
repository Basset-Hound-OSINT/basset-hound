"""
Scheduler Router for Basset Hound OSINT Platform.

Provides endpoints for managing scheduled report generation with support for:
- Project-specific schedule management
- Admin endpoints for viewing all schedules
- Due schedule detection
- Immediate report execution
"""

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from ..dependencies import get_neo4j_handler
from ..services.scheduler_service import (
    ReportScheduler,
    ScheduledReport,
    ScheduleFrequency,
    ReportConfig,
    get_scheduler_service,
)
from ..services.report_export_service import (
    ReportExportService,
    ReportFormat,
)


# ----- Pydantic Request/Response Models -----


class ReportConfigRequest(BaseModel):
    """Request schema for report configuration."""
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
                "template": "default"
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


class CreateScheduleRequest(BaseModel):
    """Request schema for creating a new schedule."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "report_config": {
                    "title": "Daily Project Summary",
                    "format": "html",
                    "report_type": "summary"
                },
                "frequency": "daily",
                "start_time": "2024-01-15T10:00:00Z",
                "cron_expression": None,
                "enabled": True
            }
        }
    )

    report_config: ReportConfigRequest = Field(..., description="Report generation configuration")
    frequency: str = Field(..., description="Schedule frequency: once, hourly, daily, weekly, or monthly")
    start_time: Optional[datetime] = Field(default=None, description="When to first run (ISO 8601, UTC)")
    cron_expression: Optional[str] = Field(default=None, description="Custom cron expression")
    enabled: bool = Field(default=True, description="Enable schedule immediately")


class UpdateScheduleRequest(BaseModel):
    """Request schema for updating a schedule."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "frequency": "weekly",
                "enabled": True
            }
        }
    )

    frequency: Optional[str] = Field(default=None, description="New frequency")
    enabled: Optional[bool] = Field(default=None, description="New enabled state")
    report_config: Optional[ReportConfigRequest] = Field(default=None, description="New report config")
    cron_expression: Optional[str] = Field(default=None, description="New cron expression")


class ScheduledReportResponse(BaseModel):
    """Response schema for a scheduled report."""
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

    id: str = Field(..., description="Schedule unique identifier")
    project_id: str = Field(..., description="Project ID")
    report_config: dict = Field(..., description="Report configuration")
    frequency: str = Field(..., description="Schedule frequency")
    next_run: datetime = Field(..., description="Next scheduled run time")
    last_run: Optional[datetime] = Field(None, description="Last run time")
    created_at: datetime = Field(..., description="Creation timestamp")
    enabled: bool = Field(..., description="Whether schedule is enabled")
    cron_expression: Optional[str] = Field(None, description="Custom cron expression")


class ScheduleListResponse(BaseModel):
    """Response schema for listing schedules."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "schedules": [],
                "total": 0
            }
        }
    )

    schedules: List[ScheduledReportResponse] = Field(..., description="List of schedules")
    total: int = Field(..., description="Total number of schedules")


class RunScheduleResponse(BaseModel):
    """Response schema for running a schedule."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "schedule_id": "550e8400-e29b-41d4-a716-446655440000",
                "success": True,
                "executed_at": "2024-01-15T10:30:00Z",
                "report_size": 15432,
                "next_run": "2024-01-16T10:00:00Z"
            }
        }
    )

    schedule_id: str = Field(..., description="Schedule ID that was executed")
    success: bool = Field(..., description="Whether execution was successful")
    executed_at: datetime = Field(..., description="When the report was generated")
    report_size: Optional[int] = Field(None, description="Size of generated report in bytes")
    next_run: datetime = Field(..., description="Next scheduled run time")
    error: Optional[str] = Field(None, description="Error message if failed")


class DueSchedulesResponse(BaseModel):
    """Response schema for due schedules."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "schedules": [],
                "total": 0,
                "as_of": "2024-01-15T10:00:00Z"
            }
        }
    )

    schedules: List[ScheduledReportResponse] = Field(..., description="List of due schedules")
    total: int = Field(..., description="Total number of due schedules")
    as_of: datetime = Field(..., description="Reference time for due check")


# ----- Helper Functions -----


def _parse_frequency(frequency_str: str) -> ScheduleFrequency:
    """Parse frequency string to ScheduleFrequency enum."""
    frequency_lower = frequency_str.lower().strip()
    try:
        return ScheduleFrequency(frequency_lower)
    except ValueError:
        valid = ", ".join([f.value for f in ScheduleFrequency])
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid frequency '{frequency_str}'. Must be one of: {valid}"
        )


def _parse_format(format_str: str) -> ReportFormat:
    """Parse format string to ReportFormat enum."""
    format_lower = format_str.lower().strip()
    format_map = {
        "pdf": ReportFormat.PDF,
        "html": ReportFormat.HTML,
        "markdown": ReportFormat.MARKDOWN,
        "md": ReportFormat.MARKDOWN,
    }
    if format_lower not in format_map:
        valid = ", ".join(format_map.keys())
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid format '{format_str}'. Must be one of: {valid}"
        )
    return format_map[format_lower]


def _build_report_config(request: ReportConfigRequest) -> ReportConfig:
    """Build ReportConfig from request."""
    return ReportConfig(
        title=request.title,
        format=request.format,
        report_type=request.report_type,
        entity_ids=request.entity_ids,
        include_graph=request.include_graph,
        include_timeline=request.include_timeline,
        include_statistics=request.include_statistics,
        template=request.template
    )


def _schedule_to_response(schedule: ScheduledReport) -> ScheduledReportResponse:
    """Convert ScheduledReport to response model."""
    return ScheduledReportResponse(
        id=schedule.id,
        project_id=schedule.project_id,
        report_config=schedule.report_config.model_dump(),
        frequency=schedule.frequency.value,
        next_run=schedule.next_run,
        last_run=schedule.last_run,
        created_at=schedule.created_at,
        enabled=schedule.enabled,
        cron_expression=schedule.cron_expression
    )


def _get_scheduler_with_service(neo4j_handler) -> ReportScheduler:
    """Get scheduler with report service configured."""
    report_service = ReportExportService(neo4j_handler)
    scheduler = get_scheduler_service()
    scheduler._report_service = report_service
    scheduler._handler = neo4j_handler
    return scheduler


# ----- Project-scoped Schedule Router -----


project_router = APIRouter(
    prefix="/projects/{project_id}/schedules",
    tags=["schedules"],
    responses={
        404: {"description": "Schedule or project not found"},
        500: {"description": "Internal server error"},
    },
)


@project_router.post(
    "",
    response_model=ScheduledReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create schedule",
    description="Create a new scheduled report for a project.",
)
async def create_schedule(
    project_id: str,
    request: CreateScheduleRequest,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Create a new scheduled report for a project.

    - **project_id**: The project identifier
    - **report_config**: Report generation configuration
    - **frequency**: How often to run (once, hourly, daily, weekly, monthly)
    - **start_time**: When to first run (optional, defaults to now)
    - **cron_expression**: Custom cron expression (optional)
    - **enabled**: Whether to enable immediately (default: true)
    """
    try:
        frequency = _parse_frequency(request.frequency)
        report_config = _build_report_config(request.report_config)
        scheduler = _get_scheduler_with_service(neo4j_handler)

        schedule = scheduler.schedule_report(
            project_id=project_id,
            report_config=report_config,
            frequency=frequency,
            start_time=request.start_time,
            cron_expression=request.cron_expression,
            enabled=request.enabled
        )

        return _schedule_to_response(schedule)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create schedule: {str(e)}"
        )


@project_router.get(
    "",
    response_model=ScheduleListResponse,
    summary="List project schedules",
    description="List all schedules for a project.",
)
async def list_project_schedules(
    project_id: str,
    enabled_only: bool = Query(False, description="Only return enabled schedules"),
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    List all schedules for a specific project.

    - **project_id**: The project identifier
    - **enabled_only**: Filter to only enabled schedules
    """
    try:
        scheduler = _get_scheduler_with_service(neo4j_handler)
        schedules = scheduler.get_scheduled_reports(
            project_id=project_id,
            enabled_only=enabled_only
        )

        return ScheduleListResponse(
            schedules=[_schedule_to_response(s) for s in schedules],
            total=len(schedules)
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list schedules: {str(e)}"
        )


# ----- Admin Schedule Router (all schedules) -----


admin_router = APIRouter(
    prefix="/schedules",
    tags=["schedules"],
    responses={
        404: {"description": "Schedule not found"},
        500: {"description": "Internal server error"},
    },
)


@admin_router.get(
    "",
    response_model=ScheduleListResponse,
    summary="List all schedules",
    description="List all schedules across all projects (admin).",
)
async def list_all_schedules(
    enabled_only: bool = Query(False, description="Only return enabled schedules"),
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    List all schedules across all projects.

    This is an admin endpoint for viewing all scheduled reports.

    - **enabled_only**: Filter to only enabled schedules
    """
    try:
        scheduler = _get_scheduler_with_service(neo4j_handler)
        schedules = scheduler.get_scheduled_reports(enabled_only=enabled_only)

        return ScheduleListResponse(
            schedules=[_schedule_to_response(s) for s in schedules],
            total=len(schedules)
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list schedules: {str(e)}"
        )


@admin_router.get(
    "/due",
    response_model=DueSchedulesResponse,
    summary="Get due schedules",
    description="Get all schedules that are past their next_run time.",
)
async def get_due_schedules(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Get all schedules that are due to run.

    A schedule is due if it is enabled and its next_run time is in the past.

    - **project_id**: Optional filter by project ID
    """
    try:
        scheduler = _get_scheduler_with_service(neo4j_handler)
        now = datetime.now(timezone.utc)
        due_schedules = scheduler.get_due_reports(as_of=now, project_id=project_id)

        return DueSchedulesResponse(
            schedules=[_schedule_to_response(s) for s in due_schedules],
            total=len(due_schedules),
            as_of=now
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get due schedules: {str(e)}"
        )


@admin_router.get(
    "/{schedule_id}",
    response_model=ScheduledReportResponse,
    summary="Get schedule details",
    description="Get details of a specific schedule.",
)
async def get_schedule(
    schedule_id: str,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Get details of a specific schedule by ID.

    - **schedule_id**: The schedule unique identifier
    """
    try:
        scheduler = _get_scheduler_with_service(neo4j_handler)
        schedule = scheduler.get_scheduled_report(schedule_id)

        if schedule is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule not found: {schedule_id}"
            )

        return _schedule_to_response(schedule)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get schedule: {str(e)}"
        )


@admin_router.patch(
    "/{schedule_id}",
    response_model=ScheduledReportResponse,
    summary="Update schedule",
    description="Update a schedule's settings.",
)
async def update_schedule(
    schedule_id: str,
    request: UpdateScheduleRequest,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Update a schedule's settings.

    Only provided fields will be updated.

    - **schedule_id**: The schedule unique identifier
    - **frequency**: New frequency (optional)
    - **enabled**: New enabled state (optional)
    - **report_config**: New report configuration (optional)
    - **cron_expression**: New cron expression (optional)
    """
    try:
        scheduler = _get_scheduler_with_service(neo4j_handler)

        # Verify schedule exists
        existing = scheduler.get_scheduled_report(schedule_id)
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule not found: {schedule_id}"
            )

        # Parse optional frequency
        frequency = None
        if request.frequency is not None:
            frequency = _parse_frequency(request.frequency)

        # Parse optional report config
        report_config = None
        if request.report_config is not None:
            report_config = _build_report_config(request.report_config)

        # Update schedule
        updated = scheduler.update_schedule(
            schedule_id=schedule_id,
            frequency=frequency,
            enabled=request.enabled,
            report_config=report_config,
            cron_expression=request.cron_expression
        )

        if updated is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule not found: {schedule_id}"
            )

        return _schedule_to_response(updated)

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
            detail=f"Failed to update schedule: {str(e)}"
        )


@admin_router.delete(
    "/{schedule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete schedule",
    description="Delete a schedule.",
)
async def delete_schedule(
    schedule_id: str,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Delete a schedule.

    - **schedule_id**: The schedule unique identifier
    """
    try:
        scheduler = _get_scheduler_with_service(neo4j_handler)

        deleted = scheduler.unschedule_report(schedule_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule not found: {schedule_id}"
            )

        return None

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete schedule: {str(e)}"
        )


@admin_router.post(
    "/{schedule_id}/run",
    response_model=RunScheduleResponse,
    summary="Run schedule now",
    description="Trigger immediate execution of a scheduled report.",
)
async def run_schedule_now(
    schedule_id: str,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Trigger immediate execution of a scheduled report.

    This will:
    - Generate the report immediately
    - Update last_run to now
    - Calculate and set the next_run time
    - For ONCE frequency, disable the schedule after execution

    - **schedule_id**: The schedule unique identifier
    """
    try:
        scheduler = _get_scheduler_with_service(neo4j_handler)

        # Verify schedule exists
        existing = scheduler.get_scheduled_report(schedule_id)
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule not found: {schedule_id}"
            )

        # Run the scheduled report
        result = scheduler.run_scheduled_report(schedule_id)

        return RunScheduleResponse(
            schedule_id=schedule_id,
            success=result.get("success", False),
            executed_at=result.get("executed_at"),
            report_size=result.get("report_size"),
            next_run=result.get("next_run"),
            error=result.get("error")
        )

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
            detail=f"Failed to run scheduled report: {str(e)}"
        )


# Combined router for easy import
router = APIRouter()
router.include_router(project_router)
router.include_router(admin_router)
