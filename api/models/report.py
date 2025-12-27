"""
Pydantic models for Report management.

Reports are markdown documents associated with entities, typically
containing OSINT investigation findings, summaries, and analysis.
Reports are stored in the entity's reports/ directory.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator
import re


class ReportBase(BaseModel):
    """Base model for report data with common fields."""

    content: str = Field(
        default="",
        description="Markdown content of the report",
        examples=["# Investigation Report\n\n## Summary\n\nFindings from the investigation..."]
    )


class ReportCreate(ReportBase):
    """
    Model for creating a new report.

    Reports must have a .md extension and valid filename.
    """

    filename: str = Field(
        ...,
        min_length=1,
        max_length=255,
        pattern=r"^[\w\-. ]+\.md$",
        description="Report filename (must end with .md)",
        examples=["initial_investigation.md", "background_check_report.md"]
    )

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, v: str) -> str:
        """
        Validate report filename.

        Must end with .md, no path traversal, valid characters only.
        """
        v = v.strip()

        if not v.endswith(".md"):
            raise ValueError("Report filename must end with .md")

        # Prevent directory traversal
        if ".." in v or "/" in v or "\\" in v:
            raise ValueError("Invalid filename - path traversal not allowed")

        # Check base name (without .md) has valid characters
        base_name = v[:-3]
        if not re.match(r"^[\w\-. ]+$", base_name):
            raise ValueError("Filename contains invalid characters")

        if not base_name:
            raise ValueError("Filename cannot be just '.md'")

        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "filename": "initial_investigation.md",
                "content": "# Investigation Report\n\n## Subject\n\nJohn Doe\n\n## Findings\n\n- Finding 1\n- Finding 2"
            }
        }
    )


class ReportUpdate(ReportBase):
    """
    Model for updating an existing report.

    Only the content can be updated. To rename, use the rename endpoint.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "content": "# Updated Investigation Report\n\n## Summary\n\nUpdated findings..."
            }
        }
    )


class ReportRename(BaseModel):
    """
    Model for renaming a report.
    """

    new_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        pattern=r"^[\w\-. ]+\.md$",
        description="New filename for the report (must end with .md)",
        examples=["renamed_report.md"]
    )

    @field_validator("new_name")
    @classmethod
    def validate_new_name(cls, v: str) -> str:
        """Validate the new filename."""
        v = v.strip()

        if not v.endswith(".md"):
            raise ValueError("Report filename must end with .md")

        if ".." in v or "/" in v or "\\" in v:
            raise ValueError("Invalid filename - path traversal not allowed")

        base_name = v[:-3]
        # Allow alphanumeric, underscore, hyphen for base name
        if not re.match(r"^[\w\-]+$", base_name.replace(" ", "")):
            raise ValueError("Filename contains invalid characters")

        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "new_name": "final_report.md"
            }
        }
    )


class ReportResponse(BaseModel):
    """
    Model for report data returned by the API.

    Contains report metadata and optionally the content.
    """

    filename: str = Field(
        ...,
        description="Report filename",
        examples=["initial_investigation.md"]
    )
    path: str = Field(
        ...,
        description="Relative path to the report file",
        examples=["reports/initial_investigation.md"]
    )
    url: str = Field(
        ...,
        description="URL to access the report",
        examples=["/projects/uuid/people/uuid/reports/initial_investigation.md"]
    )
    content: Optional[str] = Field(
        default=None,
        description="Markdown content (included when fetching single report)"
    )
    entity_id: str = Field(
        ...,
        description="ID of the entity this report belongs to"
    )
    project_id: str = Field(
        ...,
        description="ID of the project"
    )
    created_at: Optional[datetime] = Field(
        default=None,
        description="When the report was created"
    )
    modified_at: Optional[datetime] = Field(
        default=None,
        description="When the report was last modified"
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "filename": "initial_investigation.md",
                "path": "reports/initial_investigation.md",
                "url": "/projects/uuid-project/people/uuid-person/reports/initial_investigation.md",
                "content": "# Investigation Report\n\n## Summary\n\nFindings...",
                "entity_id": "550e8400-e29b-41d4-a716-446655440000",
                "project_id": "660e8400-e29b-41d4-a716-446655440000",
                "created_at": "2024-01-15T10:30:00",
                "modified_at": "2024-01-16T14:00:00"
            }
        }
    )


class ReportList(BaseModel):
    """
    Model for a list of reports.

    Used when listing all reports for an entity.
    """

    reports: list[ReportResponse] = Field(
        default_factory=list,
        description="List of report records"
    )
    total: int = Field(
        default=0,
        ge=0,
        description="Total number of reports"
    )
    entity_id: str = Field(
        ...,
        description="ID of the entity"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "reports": [
                    {
                        "filename": "initial_investigation.md",
                        "path": "reports/initial_investigation.md",
                        "url": "/projects/uuid/people/uuid/reports/initial_investigation.md",
                        "entity_id": "550e8400-e29b-41d4-a716-446655440000",
                        "project_id": "660e8400-e29b-41d4-a716-446655440000"
                    }
                ],
                "total": 1,
                "entity_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }
    )


class ReportExport(BaseModel):
    """
    Model for exporting entity data as a report package.

    Used when downloading a zip file with the profile report and files.
    """

    markdown_content: str = Field(
        ...,
        description="Markdown content for the profile report"
    )
    include_files: bool = Field(
        default=True,
        description="Whether to include files directory in the export"
    )
    include_reports: bool = Field(
        default=True,
        description="Whether to include reports directory in the export"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "markdown_content": "# Profile Report\n\n## John Doe\n\n...",
                "include_files": True,
                "include_reports": True
            }
        }
    )
