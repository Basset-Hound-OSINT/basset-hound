"""
Export Router for Basset Hound.

Provides endpoints for generating and exporting investigation reports
in various formats (PDF, HTML, Markdown, DOCX) and data in multiple formats
(GraphML, CSV, JSON, GeoJSON, Database dumps).
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
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
from ..services.export_service import (
    ExportService,
    ExportFilter,
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


# ----- Additional Pydantic Models for new export formats -----

class EntityExportFilterRequest(BaseModel):
    """Request schema for filtering entities during export."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "entity_types": ["Person", "Organization"],
                "tags": ["verified", "high-priority"],
                "limit": 100,
                "offset": 0,
                "search_query": "John"
            }
        }
    )

    entity_types: Optional[List[str]] = Field(
        default=None,
        description="Filter by entity types"
    )
    tags: Optional[List[str]] = Field(
        default=None,
        description="Filter by tags"
    )
    limit: Optional[int] = Field(
        default=None,
        description="Maximum number of entities to export"
    )
    offset: int = Field(
        default=0,
        description="Number of entities to skip (pagination)"
    )
    search_query: Optional[str] = Field(
        default=None,
        description="Full-text search query"
    )


class ReportExportFormatRequest(BaseModel):
    """Request schema for exporting reports in various formats."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Investigation Report",
                "format": "docx",
                "sections": [
                    {
                        "title": "Summary",
                        "content": "Investigation summary..."
                    }
                ],
                "include_author": True,
                "author": "Analyst"
            }
        }
    )

    title: str = Field(
        ...,
        description="Report title"
    )
    format: str = Field(
        default="html",
        description="Output format: docx, html, or markdown"
    )
    sections: List[dict] = Field(
        default_factory=list,
        description="Report sections with title and content"
    )
    include_author: bool = Field(
        default=False,
        description="Include author metadata"
    )
    author: Optional[str] = Field(
        default=None,
        description="Author name"
    )


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


# ----- New Export Format Endpoints -----

@router.get(
    "/graphml",
    summary="Export graph to GraphML",
    description="Export the project graph in GraphML format for Gephi/Cytoscape.",
    responses={
        200: {
            "description": "GraphML export successful",
            "content": {"application/xml": {}}
        },
        404: {"description": "Project not found"},
    }
)
async def export_graphml(
    project_safe_name: str,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Export project graph to GraphML format.

    Compatible with Gephi and Cytoscape for graph visualization and analysis.
    Includes node properties and edge weights.

    - **project_safe_name**: The URL-safe identifier for the project
    """
    try:
        service = ExportService(neo4j_handler)
        graphml_data = service.export_graph_graphml(project_safe_name)

        return Response(
            content=graphml_data,
            media_type="application/xml",
            headers={
                "Content-Disposition": f'attachment; filename="{project_safe_name}_graph.graphml"'
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"GraphML export failed: {str(e)}"
        )


@router.get(
    "/entities/csv",
    summary="Export entities as CSV",
    description="Export entities from the project in CSV format with optional filtering.",
    responses={
        200: {
            "description": "CSV export successful",
            "content": {"text/csv": {}}
        },
        404: {"description": "Project not found"},
    }
)
async def export_entities_csv(
    project_safe_name: str,
    entity_types: Optional[str] = Query(None, description="Comma-separated entity types to filter"),
    limit: Optional[int] = Query(None, description="Maximum number of entities to export"),
    offset: int = Query(0, description="Number of entities to skip (pagination)"),
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Export entities to CSV format.

    Supports filtering by entity type and pagination for large datasets.

    - **project_safe_name**: The URL-safe identifier for the project
    - **entity_types**: Comma-separated list of entity types to filter (optional)
    - **limit**: Maximum number of entities to export
    - **offset**: Number of entities to skip (for pagination)
    """
    try:
        entity_type_list = None
        if entity_types:
            entity_type_list = [t.strip() for t in entity_types.split(',')]

        filters = ExportFilter(
            entity_types=entity_type_list,
            limit=limit,
            offset=offset
        )

        service = ExportService(neo4j_handler)
        csv_data = service.export_entities_csv(project_safe_name, filters)

        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{project_safe_name}_entities.csv"'
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"CSV export failed: {str(e)}"
        )


@router.get(
    "/entities/json",
    summary="Export entities as JSON",
    description="Export entities from the project in JSON format with optional filtering.",
    responses={
        200: {
            "description": "JSON export successful",
            "content": {"application/json": {}}
        },
        404: {"description": "Project not found"},
    }
)
async def export_entities_json(
    project_safe_name: str,
    entity_types: Optional[str] = Query(None, description="Comma-separated entity types to filter"),
    limit: Optional[int] = Query(None, description="Maximum number of entities to export"),
    offset: int = Query(0, description="Number of entities to skip (pagination)"),
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Export entities to JSON format.

    Supports filtering by entity type and pagination for large datasets.

    - **project_safe_name**: The URL-safe identifier for the project
    - **entity_types**: Comma-separated list of entity types to filter (optional)
    - **limit**: Maximum number of entities to export
    - **offset**: Number of entities to skip (for pagination)
    """
    try:
        entity_type_list = None
        if entity_types:
            entity_type_list = [t.strip() for t in entity_types.split(',')]

        filters = ExportFilter(
            entity_types=entity_type_list,
            limit=limit,
            offset=offset
        )

        service = ExportService(neo4j_handler)
        json_data = service.export_entities_json(project_safe_name, filters)

        return Response(
            content=json_data,
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="{project_safe_name}_entities.json"'
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"JSON export failed: {str(e)}"
        )


@router.get(
    "/locations/geojson",
    summary="Export locations as GeoJSON",
    description="Export location-based entities in GeoJSON format for mapping tools.",
    responses={
        200: {
            "description": "GeoJSON export successful",
            "content": {"application/json": {}}
        },
        404: {"description": "Project not found"},
    }
)
async def export_geojson(
    project_safe_name: str,
    limit: Optional[int] = Query(None, description="Maximum number of locations to export"),
    offset: int = Query(0, description="Number of locations to skip"),
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Export location-based entities to GeoJSON format.

    Compatible with mapping tools like Leaflet, Mapbox, and others.
    Only includes entities with latitude and longitude coordinates.

    - **project_safe_name**: The URL-safe identifier for the project
    - **limit**: Maximum number of locations to export
    - **offset**: Number of locations to skip (for pagination)
    """
    try:
        filters = ExportFilter(limit=limit, offset=offset)

        service = ExportService(neo4j_handler)
        geojson_data = service.export_geojson(project_safe_name, filters)

        return Response(
            content=geojson_data,
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="{project_safe_name}_locations.geojson"'
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"GeoJSON export failed: {str(e)}"
        )


@router.post(
    "/report-formats",
    summary="Export report in multiple formats",
    description="Export a report in DOCX, HTML, or Markdown format.",
    responses={
        200: {
            "description": "Report export successful",
            "content": {
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {},
                "text/html": {},
                "text/markdown": {}
            }
        },
        400: {"description": "Invalid format or request"},
    }
)
async def export_report_formats(
    project_safe_name: str,
    request: ReportExportFormatRequest,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Export a report in DOCX (Word), HTML, or Markdown format.

    - **project_safe_name**: The URL-safe identifier for the project
    - **title**: Report title
    - **format**: Output format (docx, html, or markdown)
    - **sections**: List of report sections with title and content
    - **include_author**: Whether to include author metadata
    - **author**: Author name (if include_author is true)
    """
    try:
        format_lower = request.format.lower()

        # Build metadata
        metadata = {}
        if request.include_author:
            metadata['author'] = request.author or 'Unknown'
        metadata['date'] = datetime.utcnow().isoformat()

        service = ExportService(neo4j_handler)

        if format_lower == 'docx':
            report_data = service.export_report_docx(
                request.title,
                request.sections,
                metadata
            )
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ext = "docx"
        elif format_lower == 'html':
            report_data = service.export_report_html(
                request.title,
                request.sections,
                metadata
            )
            media_type = "text/html; charset=utf-8"
            ext = "html"
        elif format_lower == 'markdown':
            report_data = service.export_report_markdown(
                request.title,
                request.sections,
                metadata
            )
            media_type = "text/markdown; charset=utf-8"
            ext = "md"
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid format '{request.format}'. Must be: docx, html, or markdown"
            )

        # Convert string to bytes if needed
        if isinstance(report_data, str):
            report_data = report_data.encode('utf-8')

        safe_title = "".join(c if c.isalnum() or c in "-_" else "_" for c in request.title)

        return Response(
            content=report_data,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{safe_title}.{ext}"'
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Report export failed: {str(e)}"
        )


@router.get(
    "/database-dump",
    summary="Export full database dump",
    description="Export complete Neo4j database dump including all nodes, relationships, and schema.",
    responses={
        200: {
            "description": "Database dump export successful",
            "content": {"application/zip": {}}
        },
    }
)
async def export_database_dump(
    include_schema: bool = Query(True, description="Include schema definition"),
    include_config: bool = Query(True, description="Include configuration"),
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Export a complete database dump.

    Creates a compressed ZIP file containing:
    - All nodes (nodes.json)
    - All relationships (relationships.json)
    - Schema definition (schema.json, if requested)
    - Export metadata (metadata.json)

    - **include_schema**: Include schema information (default: true)
    - **include_config**: Include configuration (default: true)
    """
    try:
        service = ExportService(neo4j_handler)
        dump_data = service.export_database_dump(
            compress=True,
            include_schema=include_schema,
            include_config=include_config
        )

        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = f"basset_hound_dump_{timestamp}.zip"

        return Response(
            content=dump_data,
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database dump export failed: {str(e)}"
        )
