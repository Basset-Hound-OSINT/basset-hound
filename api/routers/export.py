"""
Export Router for Basset Hound.

Provides endpoints for generating and exporting investigation reports
in various formats (PDF, HTML, Markdown).
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field

from ..dependencies import get_neo4j_handler
from ..services.report_export_service import (
    ReportExportService,
    ReportFormat,
    ReportOptions,
    ReportSection,
    TEMPLATES,
)


# Create routers
router = APIRouter(
    prefix="/projects/{project_safe_name}/export",
    tags=["export"],
    responses={
        404: {"description": "Project or entity not found"},
        500: {"description": "Internal server error"},
    },
)

templates_router = APIRouter(
    prefix="/export",
    tags=["export"],
    responses={
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
                "content": "This section summarizes the key findings from the investigation.",
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


class GenerateReportRequest(BaseModel):
    """Request schema for generating a custom report."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Investigation Report - Operation Alpha",
                "format": "html",
                "entity_ids": None,
                "sections": [
                    {
                        "title": "Executive Summary",
                        "content": "Overview of the investigation findings.",
                        "entities": [],
                        "include_relationships": True,
                        "include_timeline": False
                    }
                ],
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
        description="Template name for styling (default, professional, minimal)"
    )


class TemplateInfo(BaseModel):
    """Information about an available template."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "default",
                "description": "Modern, clean design with gradient headers"
            }
        }
    )

    name: str = Field(..., description="Template name")
    description: str = Field(..., description="Template description")


class TemplateListResponse(BaseModel):
    """Response schema for listing available templates."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "templates": [
                    {"name": "default", "description": "Modern, clean design with gradient headers"},
                    {"name": "professional", "description": "Formal, serif-based design for official reports"},
                    {"name": "minimal", "description": "Simple, minimal design with clean typography"}
                ]
            }
        }
    )

    templates: List[TemplateInfo] = Field(
        ...,
        description="List of available templates"
    )


# Template descriptions
TEMPLATE_DESCRIPTIONS = {
    "default": "Modern, clean design with gradient headers and card-based layout",
    "professional": "Formal, serif-based design suitable for official reports",
    "minimal": "Simple, minimal design with clean typography and subtle styling",
}


# ----- Helper Functions -----

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


def _get_content_type(format: ReportFormat) -> str:
    """Get content type for a report format."""
    content_types = {
        ReportFormat.PDF: "application/pdf",
        ReportFormat.HTML: "text/html; charset=utf-8",
        ReportFormat.MARKDOWN: "text/markdown; charset=utf-8",
    }
    return content_types.get(format, "application/octet-stream")


def _get_file_extension(format: ReportFormat) -> str:
    """Get file extension for a report format."""
    extensions = {
        ReportFormat.PDF: "pdf",
        ReportFormat.HTML: "html",
        ReportFormat.MARKDOWN: "md",
    }
    return extensions.get(format, "bin")


# ----- Endpoints -----

@router.post(
    "/report",
    summary="Generate custom report",
    description="Generate a custom investigation report with configurable sections and options.",
    responses={
        200: {
            "description": "Report generated successfully",
            "content": {
                "application/pdf": {},
                "text/html": {},
                "text/markdown": {}
            }
        },
        400: {"description": "Invalid request parameters"},
        404: {"description": "Project not found"},
    }
)
async def generate_report(
    project_safe_name: str,
    request: GenerateReportRequest,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Generate a custom report for a project.

    Creates a comprehensive investigation report based on the provided options.
    Supports PDF, HTML, and Markdown output formats.

    - **project_safe_name**: The URL-safe identifier for the project
    - **title**: Report title displayed at the top
    - **format**: Output format (pdf, html, markdown)
    - **entity_ids**: Specific entities to include (optional, defaults to all)
    - **sections**: Custom report sections (optional)
    - **include_graph**: Include relationship visualization
    - **include_timeline**: Include event timeline
    - **include_statistics**: Include project statistics
    - **template**: Styling template (default, professional, minimal)
    """
    try:
        # Parse format
        report_format = _parse_format(request.format)

        # Validate template
        if request.template not in TEMPLATES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid template '{request.template}'. Available: {', '.join(TEMPLATES.keys())}"
            )

        # Build sections if provided
        sections = None
        if request.sections:
            sections = [
                ReportSection(
                    title=s.title,
                    content=s.content,
                    entities=s.entities,
                    include_relationships=s.include_relationships,
                    include_timeline=s.include_timeline
                )
                for s in request.sections
            ]

        # Create options
        options = ReportOptions(
            title=request.title,
            format=report_format,
            project_id=project_safe_name,
            entity_ids=request.entity_ids,
            sections=sections,
            include_graph=request.include_graph,
            include_timeline=request.include_timeline,
            include_statistics=request.include_statistics,
            template=request.template
        )

        # Generate report
        service = ReportExportService(neo4j_handler)
        report_bytes = service.generate_report(options)

        # Build filename
        safe_title = "".join(c if c.isalnum() or c in "-_" else "_" for c in request.title)
        filename = f"{safe_title}.{_get_file_extension(report_format)}"

        return Response(
            content=report_bytes,
            media_type=_get_content_type(report_format),
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Report generation failed: {str(e)}"
        )


@router.get(
    "/summary/{format}",
    summary="Generate project summary",
    description="Generate a summary report for the entire project.",
    responses={
        200: {
            "description": "Summary report generated successfully",
            "content": {
                "application/pdf": {},
                "text/html": {},
                "text/markdown": {}
            }
        },
        404: {"description": "Project not found"},
    }
)
async def generate_project_summary(
    project_safe_name: str,
    format: str,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Generate a summary report for a project.

    Creates a comprehensive summary including all entities, statistics,
    and an overview of the project.

    - **project_safe_name**: The URL-safe identifier for the project
    - **format**: Output format (pdf, html, markdown)
    """
    try:
        # Parse format
        report_format = _parse_format(format)

        # Generate summary
        service = ReportExportService(neo4j_handler)
        report_bytes = service.generate_project_summary(project_safe_name, report_format)

        # Build filename
        filename = f"{project_safe_name}_summary.{_get_file_extension(report_format)}"

        return Response(
            content=report_bytes,
            media_type=_get_content_type(report_format),
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Summary generation failed: {str(e)}"
        )


# Entity export endpoint - using a separate route pattern
entity_export_router = APIRouter(
    prefix="/projects/{project_safe_name}/entities/{entity_id}/export",
    tags=["export"],
    responses={
        404: {"description": "Project or entity not found"},
        500: {"description": "Internal server error"},
    },
)


@entity_export_router.get(
    "/{format}",
    summary="Export single entity",
    description="Generate a report for a single entity.",
    responses={
        200: {
            "description": "Entity report generated successfully",
            "content": {
                "application/pdf": {},
                "text/html": {},
                "text/markdown": {}
            }
        },
        404: {"description": "Entity not found"},
    }
)
async def export_entity(
    project_safe_name: str,
    entity_id: str,
    format: str,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Generate a report for a single entity.

    Creates a detailed report for one entity including all profile data,
    relationships, and associated reports.

    - **project_safe_name**: The URL-safe identifier for the project
    - **entity_id**: The unique identifier for the entity
    - **format**: Output format (pdf, html, markdown)
    """
    try:
        # Parse format
        report_format = _parse_format(format)

        # Generate entity report
        service = ReportExportService(neo4j_handler)
        report_bytes = service.generate_entity_report(
            project_safe_name,
            entity_id,
            report_format
        )

        # Build filename
        filename = f"entity_{entity_id[:8]}.{_get_file_extension(report_format)}"

        return Response(
            content=report_bytes,
            media_type=_get_content_type(report_format),
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Entity export failed: {str(e)}"
        )


@templates_router.get(
    "/templates",
    response_model=TemplateListResponse,
    summary="List available templates",
    description="Get a list of all available report templates.",
    responses={
        200: {"description": "Template list retrieved successfully"},
    }
)
async def list_templates():
    """
    List all available report templates.

    Returns information about each available template including name
    and description.
    """
    templates = [
        TemplateInfo(
            name=name,
            description=TEMPLATE_DESCRIPTIONS.get(name, "No description available")
        )
        for name in TEMPLATES.keys()
    ]

    return TemplateListResponse(templates=templates)
