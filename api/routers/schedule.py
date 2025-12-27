"""
Schedule Router for Basset Hound.

Provides endpoints for managing scheduled report generation.
"""

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from ..dependencies import get_neo4j_handler
from ..services.report_scheduler import (
    ReportScheduler,
    ReportSchedule,
    ScheduleFrequency,
    get_report_scheduler,
)
from ..services.report_export_service import (
    ReportExportService,
    ReportFormat,
    ReportOptions,
    ReportSection,
)


# Create router
router = APIRouter(
    prefix="/projects/{project_safe_name}/schedules",
    tags=["schedules"],
    responses={
        404: {"description": "Schedule or project not found"},
        500: {"description": "Internal server error"},
    },
)


# ----- Pydantic Models -----

class ReportSectionRequest(BaseModel):
    """Request schema for a report section."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Key Findings",
                "content": "This section summarizes the key findings.",
                "entities": ["uuid-1", "uuid-2"],
                "include_relationships": True,
                "include_timeline": False
            }
        }
    )

    title: str = Field(..., description="Section title")
    content: str = Field(..., description="Markdown content for the section")
    entities: List[str] = Field(
        default_factory=list,
        description="Entity IDs to include in this section"
    )
    include_relationships: bool = Field(
        default=True,
        description="Include relationship data for entities"
    )
    include_timeline: bool = Field(
        default=False,
        description="Include timeline events for entities"
    )


class ReportOptionsRequest(BaseModel):
    """Request schema for report options."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Weekly Investigation Report",
                "format": "html",
                "entity_ids": None,
                "sections": None,
                "include_graph": True,
                "include_timeline": True,
                "include_statistics": True,
                "template": "default"
            }
        }
    )

    title: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Report title"
    )
    format: str = Field(
        default="html",
        description="Output format: pdf, html, or markdown"
    )
    entity_ids: Optional[List[str]] = Field(
        default=None,
        description="Specific entity IDs to include (None = all entities)"
    )
    sections: Optional[List[ReportSectionRequest]] = Field(
        default=None,
        description="Custom sections for the report"
    )
    include_graph: bool = Field(
        default=True,
        description="Include relationship graph visualization"
    )
    include_timeline: bool = Field(
        default=True,
        description="Include project timeline"
    )
    include_statistics: bool = Field(
        default=True,
        description="Include project statistics"
    )
    template: str = Field(
        default="default",
        description="Template name for styling"
    )


class CreateScheduleRequest(BaseModel):
    """Request schema for creating a new schedule."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "report_type": "summary",
                "frequency": "daily",
                "options": {
                    "title": "Daily Project Summary",
                    "format": "html",
                    "include_statistics": True
                },
                "next_run": "2024-01-15T10:00:00Z",
                "enabled": True
            }
        }
    )

    report_type: str = Field(
        ...,
        min_length=1,
        description="Type of report: summary, custom, or entity"
    )
    frequency: str = Field(
        ...,
        description="Schedule frequency: once, hourly, daily, weekly, or monthly"
    )
    options: ReportOptionsRequest = Field(
        ...,
        description="Report generation options"
    )
    next_run: Optional[datetime] = Field(
        default=None,
        description="When to first run the report (ISO 8601 format, UTC)"
    )
    enabled: bool = Field(
        default=True,
        description="Whether the schedule should be enabled immediately"
    )


class UpdateScheduleRequest(BaseModel):
    """Request schema for updating a schedule."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "frequency": "weekly",
                "next_run": "2024-01-20T10:00:00Z"
            }
        }
    )

    report_type: Optional[str] = Field(
        default=None,
        description="New report type"
    )
    frequency: Optional[str] = Field(
        default=None,
        description="New schedule frequency"
    )
    options: Optional[ReportOptionsRequest] = Field(
        default=None,
        description="New report options"
    )
    next_run: Optional[datetime] = Field(
        default=None,
        description="New next run time"
    )
    enabled: Optional[bool] = Field(
        default=None,
        description="New enabled state"
    )


class ScheduleResponse(BaseModel):
    """Response schema for a single schedule."""
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "project_id": "test_project",
                "report_type": "summary",
                "frequency": "daily",
                "next_run": "2024-01-16T10:00:00Z",
                "last_run": "2024-01-15T10:00:00Z",
                "enabled": True,
                "created_at": "2024-01-01T00:00:00Z",
                "created_by": "user123"
            }
        }
    )

    id: str = Field(..., description="Schedule unique identifier")
    project_id: str = Field(..., description="Project ID")
    report_type: str = Field(..., description="Report type")
    frequency: str = Field(..., description="Schedule frequency")
    next_run: datetime = Field(..., description="Next scheduled run time")
    last_run: Optional[datetime] = Field(None, description="Last run time")
    enabled: bool = Field(..., description="Whether schedule is enabled")
    created_at: datetime = Field(..., description="Creation timestamp")
    created_by: str = Field(..., description="Creator identifier")


class ScheduleListResponse(BaseModel):
    """Response schema for listing schedules."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "schedules": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "project_id": "test_project",
                        "report_type": "summary",
                        "frequency": "daily",
                        "next_run": "2024-01-16T10:00:00Z",
                        "last_run": None,
                        "enabled": True,
                        "created_at": "2024-01-01T00:00:00Z",
                        "created_by": "user123"
                    }
                ],
                "total": 1
            }
        }
    )

    schedules: List[ScheduleResponse] = Field(
        ...,
        description="List of schedules"
    )
    total: int = Field(..., description="Total number of schedules")


class RunNowResponse(BaseModel):
    """Response schema for immediate schedule execution."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "schedule_id": "550e8400-e29b-41d4-a716-446655440000",
                "executed_at": "2024-01-15T10:30:00Z",
                "report_size_bytes": 15432,
                "next_run": "2024-01-16T10:00:00Z"
            }
        }
    )

    schedule_id: str = Field(..., description="Schedule ID that was executed")
    executed_at: datetime = Field(..., description="When the report was generated")
    report_size_bytes: int = Field(..., description="Size of generated report in bytes")
    next_run: datetime = Field(..., description="Next scheduled run time")


# ----- Helper Functions -----

def _parse_frequency(frequency_str: str) -> ScheduleFrequency:
    """Parse frequency string to ScheduleFrequency enum."""
    frequency_lower = frequency_str.lower()
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
    format_lower = format_str.lower()
    try:
        return ReportFormat(format_lower)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid format '{format_str}'. Must be one of: pdf, html, markdown"
        )


def _build_report_options(
    project_id: str,
    options_request: ReportOptionsRequest
) -> ReportOptions:
    """Build ReportOptions from request."""
    # Parse format
    report_format = _parse_format(options_request.format)

    # Build sections if provided
    sections = None
    if options_request.sections:
        sections = [
            ReportSection(
                title=s.title,
                content=s.content,
                entities=s.entities,
                include_relationships=s.include_relationships,
                include_timeline=s.include_timeline
            )
            for s in options_request.sections
        ]

    return ReportOptions(
        title=options_request.title,
        format=report_format,
        project_id=project_id,
        entity_ids=options_request.entity_ids,
        sections=sections,
        include_graph=options_request.include_graph,
        include_timeline=options_request.include_timeline,
        include_statistics=options_request.include_statistics,
        template=options_request.template
    )


def _schedule_to_response(schedule: ReportSchedule) -> ScheduleResponse:
    """Convert ReportSchedule to ScheduleResponse."""
    return ScheduleResponse(
        id=schedule.id,
        project_id=schedule.project_id,
        report_type=schedule.report_type,
        frequency=schedule.frequency.value,
        next_run=schedule.next_run,
        last_run=schedule.last_run,
        enabled=schedule.enabled,
        created_at=schedule.created_at,
        created_by=schedule.created_by
    )


def _get_scheduler_with_service(neo4j_handler) -> ReportScheduler:
    """Get scheduler with report service configured."""
    report_service = ReportExportService(neo4j_handler)
    scheduler = get_report_scheduler()
    # Update the report service reference
    scheduler._report_service = report_service
    scheduler._handler = neo4j_handler
    return scheduler


# ----- Endpoints -----

@router.post(
    "",
    response_model=ScheduleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create schedule",
    description="Create a new scheduled report for a project.",
    responses={
        201: {"description": "Schedule created successfully"},
        400: {"description": "Invalid request parameters"},
    }
)
async def create_schedule(
    project_safe_name: str,
    request: CreateScheduleRequest,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Create a new scheduled report.

    - **project_safe_name**: The URL-safe identifier for the project
    - **report_type**: Type of report (summary, custom, entity)
    - **frequency**: How often to run (once, hourly, daily, weekly, monthly)
    - **options**: Report generation options
    - **next_run**: When to first run (optional, defaults to now)
    - **enabled**: Whether to enable immediately (default: true)
    """
    try:
        # Parse frequency
        frequency = _parse_frequency(request.frequency)

        # Build report options
        options = _build_report_options(project_safe_name, request.options)

        # Get scheduler
        scheduler = _get_scheduler_with_service(neo4j_handler)

        # Create schedule
        schedule = scheduler.schedule_report(
            project_id=project_safe_name,
            report_type=request.report_type,
            frequency=frequency,
            options=options,
            created_by="api_user",  # TODO: Get from auth context
            next_run=request.next_run,
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


@router.get(
    "",
    response_model=ScheduleListResponse,
    summary="List schedules",
    description="List all schedules for a project.",
    responses={
        200: {"description": "Schedules retrieved successfully"},
    }
)
async def list_schedules(
    project_safe_name: str,
    enabled_only: bool = False,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    List all schedules for a project.

    - **project_safe_name**: The URL-safe identifier for the project
    - **enabled_only**: If true, only return enabled schedules
    """
    try:
        scheduler = _get_scheduler_with_service(neo4j_handler)
        schedules = scheduler.list_schedules(project_safe_name, enabled_only)

        return ScheduleListResponse(
            schedules=[_schedule_to_response(s) for s in schedules],
            total=len(schedules)
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list schedules: {str(e)}"
        )


@router.get(
    "/{schedule_id}",
    response_model=ScheduleResponse,
    summary="Get schedule",
    description="Get a schedule by its ID.",
    responses={
        200: {"description": "Schedule retrieved successfully"},
        404: {"description": "Schedule not found"},
    }
)
async def get_schedule(
    project_safe_name: str,
    schedule_id: str,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Get a schedule by its ID.

    - **project_safe_name**: The URL-safe identifier for the project
    - **schedule_id**: The unique identifier of the schedule
    """
    try:
        scheduler = _get_scheduler_with_service(neo4j_handler)
        schedule = scheduler.get_schedule(schedule_id)

        if schedule is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule not found: {schedule_id}"
            )

        # Verify schedule belongs to project
        if schedule.project_id != project_safe_name:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule not found in project: {project_safe_name}"
            )

        return _schedule_to_response(schedule)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get schedule: {str(e)}"
        )


@router.patch(
    "/{schedule_id}",
    response_model=ScheduleResponse,
    summary="Update schedule",
    description="Update a schedule's settings.",
    responses={
        200: {"description": "Schedule updated successfully"},
        404: {"description": "Schedule not found"},
    }
)
async def update_schedule(
    project_safe_name: str,
    schedule_id: str,
    request: UpdateScheduleRequest,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Update a schedule's settings.

    - **project_safe_name**: The URL-safe identifier for the project
    - **schedule_id**: The unique identifier of the schedule
    - Only provided fields will be updated
    """
    try:
        scheduler = _get_scheduler_with_service(neo4j_handler)

        # Get existing schedule to verify it exists and belongs to project
        existing = scheduler.get_schedule(schedule_id)
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule not found: {schedule_id}"
            )

        if existing.project_id != project_safe_name:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule not found in project: {project_safe_name}"
            )

        # Parse optional frequency
        frequency = None
        if request.frequency is not None:
            frequency = _parse_frequency(request.frequency)

        # Parse optional options
        options = None
        if request.options is not None:
            options = _build_report_options(project_safe_name, request.options)

        # Update schedule
        updated = scheduler.update_schedule(
            schedule_id=schedule_id,
            frequency=frequency,
            options=options,
            next_run=request.next_run,
            enabled=request.enabled,
            report_type=request.report_type
        )

        if updated is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule not found: {schedule_id}"
            )

        return _schedule_to_response(updated)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update schedule: {str(e)}"
        )


@router.delete(
    "/{schedule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete schedule",
    description="Delete a schedule.",
    responses={
        204: {"description": "Schedule deleted successfully"},
        404: {"description": "Schedule not found"},
    }
)
async def delete_schedule(
    project_safe_name: str,
    schedule_id: str,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Delete a schedule.

    - **project_safe_name**: The URL-safe identifier for the project
    - **schedule_id**: The unique identifier of the schedule
    """
    try:
        scheduler = _get_scheduler_with_service(neo4j_handler)

        # Get existing schedule to verify it belongs to project
        existing = scheduler.get_schedule(schedule_id)
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule not found: {schedule_id}"
            )

        if existing.project_id != project_safe_name:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule not found in project: {project_safe_name}"
            )

        deleted = scheduler.delete_schedule(schedule_id)
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


@router.post(
    "/{schedule_id}/pause",
    response_model=ScheduleResponse,
    summary="Pause schedule",
    description="Pause a schedule (set enabled to false).",
    responses={
        200: {"description": "Schedule paused successfully"},
        404: {"description": "Schedule not found"},
    }
)
async def pause_schedule(
    project_safe_name: str,
    schedule_id: str,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Pause a schedule.

    - **project_safe_name**: The URL-safe identifier for the project
    - **schedule_id**: The unique identifier of the schedule
    """
    try:
        scheduler = _get_scheduler_with_service(neo4j_handler)

        # Verify schedule exists and belongs to project
        existing = scheduler.get_schedule(schedule_id)
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule not found: {schedule_id}"
            )

        if existing.project_id != project_safe_name:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule not found in project: {project_safe_name}"
            )

        updated = scheduler.pause_schedule(schedule_id)
        if updated is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule not found: {schedule_id}"
            )

        return _schedule_to_response(updated)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to pause schedule: {str(e)}"
        )


@router.post(
    "/{schedule_id}/resume",
    response_model=ScheduleResponse,
    summary="Resume schedule",
    description="Resume a paused schedule (set enabled to true).",
    responses={
        200: {"description": "Schedule resumed successfully"},
        404: {"description": "Schedule not found"},
    }
)
async def resume_schedule(
    project_safe_name: str,
    schedule_id: str,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Resume a paused schedule.

    - **project_safe_name**: The URL-safe identifier for the project
    - **schedule_id**: The unique identifier of the schedule
    """
    try:
        scheduler = _get_scheduler_with_service(neo4j_handler)

        # Verify schedule exists and belongs to project
        existing = scheduler.get_schedule(schedule_id)
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule not found: {schedule_id}"
            )

        if existing.project_id != project_safe_name:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule not found in project: {project_safe_name}"
            )

        updated = scheduler.resume_schedule(schedule_id)
        if updated is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule not found: {schedule_id}"
            )

        return _schedule_to_response(updated)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resume schedule: {str(e)}"
        )


@router.post(
    "/{schedule_id}/run-now",
    response_model=RunNowResponse,
    summary="Run schedule now",
    description="Trigger immediate execution of a scheduled report.",
    responses={
        200: {"description": "Report generated successfully"},
        404: {"description": "Schedule not found"},
        500: {"description": "Report generation failed"},
    }
)
async def run_schedule_now(
    project_safe_name: str,
    schedule_id: str,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Trigger immediate execution of a scheduled report.

    - **project_safe_name**: The URL-safe identifier for the project
    - **schedule_id**: The unique identifier of the schedule

    Note: This will update last_run and calculate the next_run time.
    For ONCE frequency schedules, this will also disable the schedule.
    """
    try:
        scheduler = _get_scheduler_with_service(neo4j_handler)

        # Verify schedule exists and belongs to project
        existing = scheduler.get_schedule(schedule_id)
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule not found: {schedule_id}"
            )

        if existing.project_id != project_safe_name:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule not found in project: {project_safe_name}"
            )

        # Run the report
        executed_at = datetime.now(timezone.utc)
        report_bytes = scheduler.run_scheduled_report(schedule_id)

        if report_bytes is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule not found: {schedule_id}"
            )

        # Get updated schedule for next_run
        updated = scheduler.get_schedule(schedule_id)

        return RunNowResponse(
            schedule_id=schedule_id,
            executed_at=executed_at,
            report_size_bytes=len(report_bytes),
            next_run=updated.next_run if updated else executed_at
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
