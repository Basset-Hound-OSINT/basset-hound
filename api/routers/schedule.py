"""
Schedule Router for Basset Hound.

DEPRECATED: This module is deprecated. Use scheduler.py instead.

This module now re-exports from scheduler.py for backward compatibility.
All new development should use the scheduler module directly.

The scheduler router provides more comprehensive endpoints including:
- Project-specific schedule management
- Admin endpoints for viewing all schedules
- Due schedule detection
- Immediate report execution
- Cron expression support
"""

import warnings

# Emit deprecation warning when this module is imported
warnings.warn(
    "The schedule router is deprecated. Use scheduler instead. "
    "Import from api.routers.scheduler for the latest scheduling endpoints.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export everything from scheduler for backward compatibility
from .scheduler import (
    router,
    project_router,
    admin_router,
    # Request/Response models
    ReportConfigRequest,
    CreateScheduleRequest,
    UpdateScheduleRequest,
    ScheduledReportResponse,
    ScheduleListResponse,
    RunScheduleResponse,
    DueSchedulesResponse,
    # Helper functions
    _parse_frequency,
)

# Compatibility aliases for old names
ScheduleResponse = ScheduledReportResponse
RunNowResponse = RunScheduleResponse
ReportOptionsRequest = ReportConfigRequest

# Import ReportFormat for _parse_format
from ..services.report_export_service import ReportFormat
from fastapi import HTTPException, status


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


# Placeholder for ReportSectionRequest - use same as export if it exists
try:
    from .export import ReportSectionRequest
except ImportError:
    from pydantic import BaseModel, Field
    from typing import Optional, List, Any

    class ReportSectionRequest(BaseModel):
        """Request schema for report section configuration."""
        section_type: str = Field(..., description="Type of section")
        title: Optional[str] = Field(None, description="Section title")
        content: Optional[str] = Field(None, description="Section content")
        data: Optional[List[Any]] = Field(default=None, description="Section data")


__all__ = [
    "router",
    "project_router",
    "admin_router",
    "ReportConfigRequest",
    "CreateScheduleRequest",
    "UpdateScheduleRequest",
    "ScheduledReportResponse",
    "ScheduleListResponse",
    "RunScheduleResponse",
    "DueSchedulesResponse",
    # Compatibility aliases
    "ScheduleResponse",
    "RunNowResponse",
    "ReportOptionsRequest",
    "ReportSectionRequest",
    # Helper functions
    "_parse_frequency",
    "_parse_format",
]
