"""
Report Storage Router for Basset Hound.

Provides API endpoints for storing and managing generated reports with version history.
Supports CRUD operations, version management, version diffing, and cleanup.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status, Query, Body
from pydantic import BaseModel, ConfigDict, Field

from ..services.report_storage import (
    ReportStorageService,
    ReportFormat,
    ReportVersion,
    StoredReport,
    ReportNotFoundError,
    VersionNotFoundError,
    DuplicateContentError,
    get_report_storage_service,
)


router = APIRouter(
    prefix="/reports/stored",
    tags=["report-storage"],
    responses={
        404: {"description": "Report or version not found"},
        500: {"description": "Internal server error"},
    },
)


# ==================== Pydantic Models ====================


class StoreReportRequest(BaseModel):
    """Schema for storing a new report."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "name": "Entity Investigation Report",
            "content": "<html><body><h1>Report</h1></body></html>",
            "format": "html",
            "project_id": "my-project",
            "entity_id": "entity-123",
            "template_id": "default-entity-report",
            "context": {"title": "Investigation Report"},
            "report_id": None,
            "skip_duplicate_check": False
        }
    })

    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Display name for the report"
    )
    content: str = Field(
        ...,
        description="Report content"
    )
    format: str = Field(
        default="html",
        description="Output format (pdf, html, markdown, json, text)"
    )
    project_id: str = Field(
        ...,
        min_length=1,
        description="Associated project ID"
    )
    entity_id: Optional[str] = Field(
        default=None,
        description="Associated entity ID (optional)"
    )
    template_id: Optional[str] = Field(
        default=None,
        description="Template ID used for generation"
    )
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Context data used for generation"
    )
    report_id: Optional[str] = Field(
        default=None,
        description="Existing report ID to add version to"
    )
    skip_duplicate_check: bool = Field(
        default=False,
        description="Skip duplicate content check"
    )


class ReportVersionResponse(BaseModel):
    """Schema for report version response."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "version_id": "v-550e8400-e29b-41d4-a716-446655440000",
                "report_id": "r-550e8400-e29b-41d4-a716-446655440001",
                "version_number": 1,
                "content": "<html><body><h1>Report</h1></body></html>",
                "format": "html",
                "generated_at": "2024-01-15T10:30:00",
                "template_id": "default-entity-report",
                "context_hash": "a1b2c3d4e5f6"
            }
        }
    )

    version_id: str
    report_id: str
    version_number: int
    content: str
    format: str
    generated_at: str
    template_id: Optional[str]
    context_hash: str


class ReportVersionSummary(BaseModel):
    """Condensed version info without content."""
    version_id: str
    version_number: int
    format: str
    generated_at: str
    template_id: Optional[str]
    context_hash: str


class StoredReportResponse(BaseModel):
    """Schema for stored report response."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "report_id": "r-550e8400-e29b-41d4-a716-446655440001",
                "name": "Entity Investigation Report",
                "project_id": "my-project",
                "entity_id": "entity-123",
                "created_at": "2024-01-15T10:30:00",
                "updated_at": "2024-01-15T11:00:00",
                "current_version": 2,
                "version_count": 2,
                "versions": [
                    {
                        "version_id": "v1",
                        "version_number": 1,
                        "format": "html",
                        "generated_at": "2024-01-15T10:30:00",
                        "template_id": None,
                        "context_hash": ""
                    }
                ]
            }
        }
    )

    report_id: str
    name: str
    project_id: str
    entity_id: Optional[str]
    created_at: str
    updated_at: str
    current_version: int
    version_count: int
    versions: List[ReportVersionSummary]


class StoredReportListItem(BaseModel):
    """Condensed report info for list view."""
    report_id: str
    name: str
    project_id: str
    entity_id: Optional[str]
    created_at: str
    updated_at: str
    current_version: int
    version_count: int
    current_format: Optional[str]


class ReportListResponse(BaseModel):
    """Schema for report list response."""
    reports: List[StoredReportListItem]
    count: int


class DiffRequest(BaseModel):
    """Schema for version diff request."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "version1": 1,
            "version2": 2
        }
    })

    version1: int = Field(..., ge=1, description="First version number")
    version2: int = Field(..., ge=1, description="Second version number")


class DiffResponse(BaseModel):
    """Schema for version diff response."""
    version1: int
    version2: int
    version1_generated_at: str
    version2_generated_at: str
    diff: str
    lines_added: int
    lines_removed: int
    is_identical: bool


class CleanupRequest(BaseModel):
    """Schema for cleanup request."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "keep_count": 5
        }
    })

    keep_count: int = Field(
        default=5,
        ge=1,
        description="Number of recent versions to keep"
    )


class CleanupResponse(BaseModel):
    """Schema for cleanup response."""
    report_id: str
    versions_deleted: int
    versions_remaining: int


class ExportResponse(BaseModel):
    """Schema for export response."""
    report: Dict[str, Any]
    exported_at: str
    export_version: str


class ImportRequest(BaseModel):
    """Schema for import request."""
    report: Dict[str, Any] = Field(..., description="Report data to import")
    overwrite: bool = Field(default=False, description="Overwrite if exists")


class StatsResponse(BaseModel):
    """Schema for stats response."""
    total_reports: int
    total_versions: int


# ==================== Helper Functions ====================


def _parse_format(format_str: str) -> ReportFormat:
    """Parse format string to ReportFormat enum."""
    try:
        return ReportFormat(format_str.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid format: {format_str}. Must be one of: pdf, html, markdown, json, text"
        )


def _version_to_response(version: ReportVersion) -> ReportVersionResponse:
    """Convert ReportVersion to response model."""
    return ReportVersionResponse(
        version_id=version.version_id,
        report_id=version.report_id,
        version_number=version.version_number,
        content=version.content,
        format=version.format.value,
        generated_at=version.generated_at.isoformat(),
        template_id=version.template_id,
        context_hash=version.context_hash,
    )


def _version_to_summary(version: ReportVersion) -> ReportVersionSummary:
    """Convert ReportVersion to summary model (without content)."""
    return ReportVersionSummary(
        version_id=version.version_id,
        version_number=version.version_number,
        format=version.format.value,
        generated_at=version.generated_at.isoformat(),
        template_id=version.template_id,
        context_hash=version.context_hash,
    )


def _report_to_response(report: StoredReport) -> StoredReportResponse:
    """Convert StoredReport to response model."""
    return StoredReportResponse(
        report_id=report.report_id,
        name=report.name,
        project_id=report.project_id,
        entity_id=report.entity_id,
        created_at=report.created_at.isoformat(),
        updated_at=report.updated_at.isoformat(),
        current_version=report.current_version,
        version_count=report.get_version_count(),
        versions=[_version_to_summary(v) for v in report.versions],
    )


def _report_to_list_item(report: StoredReport) -> StoredReportListItem:
    """Convert StoredReport to list item model."""
    current_version = report.get_current_version_content()
    current_format = current_version.format.value if current_version else None

    return StoredReportListItem(
        report_id=report.report_id,
        name=report.name,
        project_id=report.project_id,
        entity_id=report.entity_id,
        created_at=report.created_at.isoformat(),
        updated_at=report.updated_at.isoformat(),
        current_version=report.current_version,
        version_count=report.get_version_count(),
        current_format=current_format,
    )


# ==================== Endpoints ====================


@router.post(
    "",
    response_model=StoredReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Store a new report",
    description="Store a new report or add a new version to an existing report.",
    responses={
        201: {"description": "Report stored successfully"},
        400: {"description": "Invalid request or duplicate content"},
        409: {"description": "Duplicate content detected"},
    },
)
async def store_report(
    request: StoreReportRequest,
) -> StoredReportResponse:
    """
    Store a new report or add a version to an existing report.

    If report_id is provided and exists, a new version is added.
    Otherwise, a new report is created.

    - **name**: Display name for the report
    - **content**: Report content (HTML, Markdown, text, etc.)
    - **format**: Output format (pdf, html, markdown, json, text)
    - **project_id**: Associated project ID
    - **entity_id**: Associated entity ID (optional)
    - **template_id**: Template ID used for generation (optional)
    - **context**: Context data used for generation (optional)
    - **report_id**: Existing report ID to add version to (optional)
    - **skip_duplicate_check**: Skip duplicate content check (default: false)
    """
    service = get_report_storage_service()

    try:
        report_format = _parse_format(request.format)

        report = service.store_report(
            name=request.name,
            content=request.content,
            format=report_format,
            project_id=request.project_id,
            entity_id=request.entity_id,
            template_id=request.template_id,
            context=request.context,
            report_id=request.report_id,
            skip_duplicate_check=request.skip_duplicate_check,
        )

        return _report_to_response(report)

    except DuplicateContentError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )


@router.get(
    "",
    response_model=ReportListResponse,
    summary="List stored reports",
    description="Retrieve a list of stored reports with optional filters.",
    responses={
        200: {"description": "List of reports"},
    },
)
async def list_reports(
    project_id: Optional[str] = Query(
        default=None,
        description="Filter by project ID"
    ),
    entity_id: Optional[str] = Query(
        default=None,
        description="Filter by entity ID"
    ),
    format: Optional[str] = Query(
        default=None,
        description="Filter by format (pdf, html, markdown, json, text)"
    ),
) -> ReportListResponse:
    """
    List all stored reports with optional filtering.

    - **project_id**: Filter by project ID
    - **entity_id**: Filter by entity ID
    - **format**: Filter by report format
    """
    service = get_report_storage_service()

    format_filter = None
    if format:
        format_filter = _parse_format(format)

    reports = service.list_reports(
        project_id=project_id,
        entity_id=entity_id,
        format_filter=format_filter,
    )

    items = [_report_to_list_item(r) for r in reports]

    return ReportListResponse(
        reports=items,
        count=len(items),
    )


@router.get(
    "/stats",
    response_model=StatsResponse,
    summary="Get storage statistics",
    description="Get statistics about stored reports.",
    responses={
        200: {"description": "Storage statistics"},
    },
)
async def get_stats() -> StatsResponse:
    """
    Get statistics about stored reports.

    Returns the total number of reports and versions.
    """
    service = get_report_storage_service()

    return StatsResponse(
        total_reports=service.get_report_count(),
        total_versions=service.get_total_version_count(),
    )


@router.get(
    "/{report_id}",
    response_model=StoredReportResponse,
    summary="Get report by ID",
    description="Retrieve a stored report with all version summaries.",
    responses={
        200: {"description": "Report found"},
        404: {"description": "Report not found"},
    },
)
async def get_report(
    report_id: str,
) -> StoredReportResponse:
    """
    Get a stored report by ID.

    Returns the report with summaries of all versions (content not included).
    Use the version endpoint to get full content.

    - **report_id**: The report ID
    """
    service = get_report_storage_service()

    try:
        report = service.get_report(report_id)
        return _report_to_response(report)

    except ReportNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report not found: {report_id}"
        )


@router.get(
    "/{report_id}/versions/{version_number}",
    response_model=ReportVersionResponse,
    summary="Get specific version",
    description="Retrieve a specific version of a report with full content.",
    responses={
        200: {"description": "Version found"},
        404: {"description": "Report or version not found"},
    },
)
async def get_report_version(
    report_id: str,
    version_number: int,
) -> ReportVersionResponse:
    """
    Get a specific version of a report.

    Returns the full version including content.

    - **report_id**: The report ID
    - **version_number**: The version number (1, 2, 3, ...)
    """
    service = get_report_storage_service()

    try:
        version = service.get_report_version(report_id, version_number)
        return _version_to_response(version)

    except ReportNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report not found: {report_id}"
        )
    except VersionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version {version_number} not found for report {report_id}"
        )


@router.get(
    "/{report_id}/versions/current",
    response_model=ReportVersionResponse,
    summary="Get current version",
    description="Retrieve the current (latest) version of a report.",
    responses={
        200: {"description": "Current version"},
        404: {"description": "Report not found or no versions"},
    },
)
async def get_current_version(
    report_id: str,
) -> ReportVersionResponse:
    """
    Get the current (latest) version of a report.

    - **report_id**: The report ID
    """
    service = get_report_storage_service()

    try:
        report = service.get_report(report_id)
        version = report.get_current_version_content()

        if version is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No versions found for report {report_id}"
            )

        return _version_to_response(version)

    except ReportNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report not found: {report_id}"
        )


@router.post(
    "/{report_id}/diff",
    response_model=DiffResponse,
    summary="Compare versions",
    description="Compare two versions of a report and get a diff.",
    responses={
        200: {"description": "Diff generated"},
        400: {"description": "Invalid version numbers"},
        404: {"description": "Report or version not found"},
    },
)
async def compare_versions(
    report_id: str,
    request: DiffRequest,
) -> DiffResponse:
    """
    Compare two versions of a report.

    Returns a unified diff showing the differences.

    - **report_id**: The report ID
    - **version1**: First version number
    - **version2**: Second version number
    """
    service = get_report_storage_service()

    try:
        diff_result = service.get_report_diff(
            report_id=report_id,
            version1=request.version1,
            version2=request.version2,
        )

        return DiffResponse(**diff_result)

    except ReportNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report not found: {report_id}"
        )
    except VersionNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.delete(
    "/{report_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete report",
    description="Delete a report and all its versions.",
    responses={
        204: {"description": "Report deleted successfully"},
        404: {"description": "Report not found"},
    },
)
async def delete_report(
    report_id: str,
) -> None:
    """
    Delete a report and all its versions.

    - **report_id**: The report ID
    """
    service = get_report_storage_service()

    try:
        service.delete_report(report_id)
        return None

    except ReportNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report not found: {report_id}"
        )


@router.post(
    "/{report_id}/cleanup",
    response_model=CleanupResponse,
    summary="Cleanup old versions",
    description="Remove old versions of a report, keeping the most recent ones.",
    responses={
        200: {"description": "Cleanup completed"},
        400: {"description": "Invalid keep_count"},
        404: {"description": "Report not found"},
    },
)
async def cleanup_versions(
    report_id: str,
    request: CleanupRequest = Body(default=CleanupRequest()),
) -> CleanupResponse:
    """
    Remove old versions of a report.

    Keeps the specified number of most recent versions.

    - **report_id**: The report ID
    - **keep_count**: Number of versions to keep (minimum 1, default 5)
    """
    service = get_report_storage_service()

    try:
        deleted_count = service.cleanup_old_versions(
            report_id=report_id,
            keep_count=request.keep_count,
        )

        report = service.get_report(report_id)

        return CleanupResponse(
            report_id=report_id,
            versions_deleted=deleted_count,
            versions_remaining=report.get_version_count(),
        )

    except ReportNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report not found: {report_id}"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/{report_id}/export",
    response_model=ExportResponse,
    summary="Export report",
    description="Export a report with all versions for backup.",
    responses={
        200: {"description": "Report exported"},
        404: {"description": "Report not found"},
    },
)
async def export_report(
    report_id: str,
) -> ExportResponse:
    """
    Export a report with all versions.

    Returns the complete report data for backup or transfer.

    - **report_id**: The report ID
    """
    service = get_report_storage_service()

    try:
        export_data = service.export_report(report_id)

        return ExportResponse(
            report=export_data["report"],
            exported_at=export_data["exported_at"],
            export_version=export_data["export_version"],
        )

    except ReportNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report not found: {report_id}"
        )


@router.post(
    "/import",
    response_model=StoredReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Import report",
    description="Import a report from exported data.",
    responses={
        201: {"description": "Report imported"},
        400: {"description": "Invalid data or report exists"},
    },
)
async def import_report(
    request: ImportRequest,
) -> StoredReportResponse:
    """
    Import a report from exported data.

    - **report**: Report data to import
    - **overwrite**: Whether to overwrite if report ID exists
    """
    service = get_report_storage_service()

    try:
        report = service.import_report(
            data={"report": request.report},
            overwrite=request.overwrite,
        )

        return _report_to_response(report)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/by-template/{template_id}",
    response_model=ReportListResponse,
    summary="Get reports by template",
    description="Get all reports generated using a specific template.",
    responses={
        200: {"description": "List of reports"},
    },
)
async def get_reports_by_template(
    template_id: str,
) -> ReportListResponse:
    """
    Get all reports that were generated using a specific template.

    - **template_id**: The template ID
    """
    service = get_report_storage_service()

    reports = service.get_reports_by_template(template_id)
    items = [_report_to_list_item(r) for r in reports]

    return ReportListResponse(
        reports=items,
        count=len(items),
    )
