"""
LLM Export Router for Basset Hound OSINT Platform.

Provides RESTful API endpoints for exporting OSINT data in LLM-optimized formats
(Markdown, JSON, YAML, Plain Text, XML) with intelligent token management and
configurable context building.

Endpoints:
- POST /projects/{project_id}/llm-export/entity/{entity_id} - Export single entity for LLM
- POST /projects/{project_id}/llm-export/summary - Export project summary for LLM
- POST /projects/{project_id}/llm-export/entity/{entity_id}/context - Export entity with context
- POST /projects/{project_id}/llm-export/investigation-brief - Export investigation brief
- POST /llm-export/estimate-tokens - Estimate tokens for content
- GET /llm-export/formats - List available export formats
"""

from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, ConfigDict

from ..dependencies import get_neo4j_handler
from ..services.llm_export import (
    LLMExportFormat,
    LLMExportConfig,
    ExportContext,
    LLMExportResult,
    TokenEstimator,
    get_llm_export_service,
)


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class EntityExportRequest(BaseModel):
    """Request model for exporting a single entity."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "format": "markdown",
                "max_tokens": 4000,
                "context": {
                    "include_entities": True,
                    "include_relationships": True,
                    "include_timeline": False,
                    "include_orphan_data": False,
                    "include_statistics": True,
                    "include_metadata": True
                },
                "prioritize_fields": ["core", "profile", "contact", "social"],
                "max_field_length": 500,
                "max_relationships": 50,
                "include_raw_data": False
            }
        }
    )

    format: LLMExportFormat = Field(
        default=LLMExportFormat.MARKDOWN,
        description="Output format for the export"
    )
    max_tokens: Optional[int] = Field(
        default=None,
        ge=100,
        description="Maximum tokens (None = unlimited)"
    )
    context: ExportContext = Field(
        default_factory=ExportContext,
        description="Configuration for what context to include"
    )
    prioritize_fields: List[str] = Field(
        default_factory=lambda: ["core", "profile", "contact", "social"],
        description="Fields to prioritize in output"
    )
    max_field_length: int = Field(
        default=500,
        ge=50,
        description="Maximum length for field values"
    )
    max_relationships: int = Field(
        default=50,
        ge=1,
        description="Maximum relationships to include"
    )
    include_raw_data: bool = Field(
        default=False,
        description="Include raw data in response"
    )


class ProjectSummaryRequest(BaseModel):
    """Request model for exporting a project summary."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "format": "json",
                "max_tokens": 8000,
                "context": {
                    "include_entities": True,
                    "include_relationships": True,
                    "include_statistics": True
                },
                "include_raw_data": False
            }
        }
    )

    format: LLMExportFormat = Field(
        default=LLMExportFormat.MARKDOWN,
        description="Output format for the export"
    )
    max_tokens: Optional[int] = Field(
        default=None,
        ge=100,
        description="Maximum tokens (None = unlimited)"
    )
    context: ExportContext = Field(
        default_factory=ExportContext,
        description="Configuration for what context to include"
    )
    include_raw_data: bool = Field(
        default=False,
        description="Include raw data in response"
    )


class EntityContextRequest(BaseModel):
    """Request model for exporting entity with relationship context."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "depth": 2,
                "format": "markdown",
                "max_tokens": 6000,
                "context": {
                    "include_relationships": True,
                    "include_statistics": True
                },
                "max_relationships": 50,
                "include_raw_data": False
            }
        }
    )

    depth: int = Field(
        default=2,
        ge=1,
        le=5,
        description="Number of relationship hops to include (1-5)"
    )
    format: LLMExportFormat = Field(
        default=LLMExportFormat.MARKDOWN,
        description="Output format for the export"
    )
    max_tokens: Optional[int] = Field(
        default=None,
        ge=100,
        description="Maximum tokens (None = unlimited)"
    )
    context: ExportContext = Field(
        default_factory=ExportContext,
        description="Configuration for what context to include"
    )
    max_relationships: int = Field(
        default=50,
        ge=1,
        description="Maximum relationships to include"
    )
    include_raw_data: bool = Field(
        default=False,
        description="Include raw data in response"
    )


class InvestigationBriefRequest(BaseModel):
    """Request model for exporting an investigation brief."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "focus_entities": [
                    "entity-550e8400-e29b-41d4-a716-446655440000",
                    "entity-550e8400-e29b-41d4-a716-446655440001"
                ],
                "format": "markdown",
                "max_tokens": 10000,
                "context": {
                    "include_relationships": True,
                    "include_statistics": True
                },
                "max_field_length": 500,
                "max_relationships": 100,
                "include_raw_data": False
            }
        }
    )

    focus_entities: List[str] = Field(
        ...,
        min_length=1,
        description="Entity IDs to focus the investigation on"
    )
    format: LLMExportFormat = Field(
        default=LLMExportFormat.MARKDOWN,
        description="Output format for the export"
    )
    max_tokens: Optional[int] = Field(
        default=None,
        ge=100,
        description="Maximum tokens (None = unlimited)"
    )
    context: ExportContext = Field(
        default_factory=ExportContext,
        description="Configuration for what context to include"
    )
    max_field_length: int = Field(
        default=500,
        ge=50,
        description="Maximum length for field values"
    )
    max_relationships: int = Field(
        default=100,
        ge=1,
        description="Maximum relationships to include"
    )
    include_raw_data: bool = Field(
        default=False,
        description="Include raw data in response"
    )


class TokenEstimateRequest(BaseModel):
    """Request model for token estimation."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "content": "Sample text content to estimate tokens for.",
                "format": "markdown"
            }
        }
    )

    content: str = Field(
        ...,
        min_length=1,
        description="Content to estimate tokens for"
    )
    format: LLMExportFormat = Field(
        default=LLMExportFormat.PLAIN_TEXT,
        description="Format of the content (affects token calculation)"
    )


class TokenEstimateResponse(BaseModel):
    """Response model for token estimation."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "token_estimate": 42,
                "format": "markdown",
                "content_length": 150,
                "chars_per_token": 4.0
            }
        }
    )

    token_estimate: int = Field(..., ge=0, description="Estimated token count")
    format: LLMExportFormat = Field(..., description="Format used for estimation")
    content_length: int = Field(..., ge=0, description="Character count of content")
    chars_per_token: float = Field(..., description="Characters per token ratio used")


class FormatInfo(BaseModel):
    """Information about an export format."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "value": "markdown",
                "description": "Markdown format optimized for LLM consumption",
                "overhead_multiplier": 1.1
            }
        }
    )

    value: str = Field(..., description="Format identifier")
    description: str = Field(..., description="Human-readable description")
    overhead_multiplier: float = Field(..., description="Token overhead multiplier for this format")


class FormatsListResponse(BaseModel):
    """Response model listing available export formats."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "formats": [
                    {
                        "value": "markdown",
                        "description": "Markdown format optimized for LLM consumption",
                        "overhead_multiplier": 1.1
                    }
                ],
                "total": 5
            }
        }
    )

    formats: List[FormatInfo] = Field(
        default_factory=list,
        description="Available export formats"
    )
    total: int = Field(..., description="Total number of formats")


# =============================================================================
# ROUTER DEFINITION
# =============================================================================

router = APIRouter(
    tags=["llm-export"],
    responses={
        404: {"description": "Project or entity not found"},
        500: {"description": "Internal server error"},
    },
)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _build_config(request: BaseModel) -> LLMExportConfig:
    """Build LLMExportConfig from request model."""
    config_data = {
        "format": request.format,
        "max_tokens": getattr(request, "max_tokens", None),
        "context": getattr(request, "context", ExportContext()),
        "prioritize_fields": getattr(request, "prioritize_fields", ["core", "profile", "contact", "social"]),
        "max_field_length": getattr(request, "max_field_length", 500),
        "max_relationships": getattr(request, "max_relationships", 50),
        "max_timeline_events": getattr(request, "max_timeline_events", 20),
        "include_raw_data": getattr(request, "include_raw_data", False),
    }
    return LLMExportConfig(**config_data)


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post(
    "/projects/{project_safe_name}/llm-export/entity/{entity_id}",
    response_model=LLMExportResult,
    summary="Export single entity for LLM",
    description="Export a single entity in LLM-optimized format with configurable context.",
    responses={
        200: {"description": "Entity exported successfully"},
        404: {"description": "Project or entity not found"},
        500: {"description": "Export failed"},
    }
)
async def export_entity(
    project_safe_name: str,
    entity_id: str,
    request: EntityExportRequest = EntityExportRequest(),
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Export a single entity in LLM-optimized format.

    Returns the entity profile, relationships, and other context in a format
    optimized for consumption by LLMs and AI agents.

    - **project_safe_name**: The URL-safe identifier for the project
    - **entity_id**: The entity ID to export
    - **request**: Export configuration (format, token limits, context options)
    """
    try:
        service = get_llm_export_service(neo4j_handler)
        config = _build_config(request)

        result = await service.export_entity(entity_id, project_safe_name, config)
        return result

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export entity: {str(e)}"
        )


@router.post(
    "/projects/{project_safe_name}/llm-export/summary",
    response_model=LLMExportResult,
    summary="Export project summary for LLM",
    description="Export a project summary in LLM-optimized format with entities and relationships.",
    responses={
        200: {"description": "Project summary exported successfully"},
        404: {"description": "Project not found"},
        500: {"description": "Export failed"},
    }
)
async def export_project_summary(
    project_safe_name: str,
    request: ProjectSummaryRequest = ProjectSummaryRequest(),
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Export a project summary in LLM-optimized format.

    Returns an overview of the project including entity counts, relationship
    statistics, and entity listings in a format optimized for LLMs.

    - **project_safe_name**: The URL-safe identifier for the project
    - **request**: Export configuration (format, token limits, context options)
    """
    try:
        service = get_llm_export_service(neo4j_handler)
        config = _build_config(request)

        result = await service.export_project_summary(project_safe_name, config)
        return result

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export project summary: {str(e)}"
        )


@router.post(
    "/projects/{project_safe_name}/llm-export/entity/{entity_id}/context",
    response_model=LLMExportResult,
    summary="Export entity with N-hop context",
    description="Export an entity with its N-hop relationship neighborhood for LLM analysis.",
    responses={
        200: {"description": "Entity context exported successfully"},
        404: {"description": "Project or entity not found"},
        500: {"description": "Export failed"},
    }
)
async def export_entity_context(
    project_safe_name: str,
    entity_id: str,
    request: EntityContextRequest = EntityContextRequest(),
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Export an entity with N-hop relationship context.

    Returns the entity along with all connected entities within N relationship
    hops, creating a contextual neighborhood for LLM analysis.

    - **project_safe_name**: The URL-safe identifier for the project
    - **entity_id**: The center entity ID
    - **request**: Export configuration (depth, format, token limits, context options)
    """
    try:
        service = get_llm_export_service(neo4j_handler)
        config = _build_config(request)

        result = await service.export_entity_context(
            entity_id,
            project_safe_name,
            depth=request.depth,
            config=config
        )
        return result

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export entity context: {str(e)}"
        )


@router.post(
    "/projects/{project_safe_name}/llm-export/investigation-brief",
    response_model=LLMExportResult,
    summary="Export investigation brief",
    description="Export a focused investigation brief on specific entities for LLM analysis.",
    responses={
        200: {"description": "Investigation brief exported successfully"},
        400: {"description": "Invalid request (no entities provided)"},
        404: {"description": "Project not found"},
        500: {"description": "Export failed"},
    }
)
async def export_investigation_brief(
    project_safe_name: str,
    request: InvestigationBriefRequest,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Export a focused investigation brief on specific entities.

    Returns detailed profiles and interconnections for a set of focus entities,
    ideal for targeted investigations and LLM-assisted analysis.

    - **project_safe_name**: The URL-safe identifier for the project
    - **request**: Investigation configuration (focus entities, format, token limits)
    """
    try:
        service = get_llm_export_service(neo4j_handler)
        config = _build_config(request)

        result = await service.export_investigation_brief(
            project_safe_name,
            request.focus_entities,
            config
        )
        return result

    except ValueError as e:
        # Check if it's about no entities found or other validation
        if "No valid entities" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export investigation brief: {str(e)}"
        )


@router.post(
    "/llm-export/estimate-tokens",
    response_model=TokenEstimateResponse,
    summary="Estimate tokens for content",
    description="Estimate the token count for given content in a specific format.",
    responses={
        200: {"description": "Token estimate calculated successfully"},
        400: {"description": "Invalid request"},
    }
)
async def estimate_tokens(request: TokenEstimateRequest):
    """
    Estimate token count for content.

    Uses GPT-family approximation (4 chars per token) with format-specific
    overhead multipliers to estimate token counts.

    - **request**: Content and format for token estimation
    """
    try:
        token_estimate = TokenEstimator.estimate(request.content, request.format)

        return TokenEstimateResponse(
            token_estimate=token_estimate,
            format=request.format,
            content_length=len(request.content),
            chars_per_token=TokenEstimator.CHARS_PER_TOKEN
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to estimate tokens: {str(e)}"
        )


@router.get(
    "/llm-export/formats",
    response_model=FormatsListResponse,
    summary="List available export formats",
    description="Get a list of all available LLM export formats and their characteristics.",
    responses={
        200: {"description": "Formats list retrieved successfully"},
    }
)
async def list_export_formats():
    """
    List available LLM export formats.

    Returns all supported export formats with descriptions and token overhead
    multipliers for each format.
    """
    format_descriptions = {
        LLMExportFormat.MARKDOWN: "Markdown format optimized for LLM consumption with headers and structure",
        LLMExportFormat.JSON: "Structured JSON format for programmatic processing",
        LLMExportFormat.YAML: "YAML format for human-readable structured data",
        LLMExportFormat.PLAIN_TEXT: "Plain text format with minimal formatting",
        LLMExportFormat.XML: "XML format for structured data exchange",
    }

    formats = []
    for fmt in LLMExportFormat:
        formats.append(FormatInfo(
            value=fmt.value,
            description=format_descriptions.get(fmt, f"{fmt.value.title()} format"),
            overhead_multiplier=TokenEstimator.FORMAT_OVERHEAD.get(fmt, 1.0)
        ))

    return FormatsListResponse(
        formats=formats,
        total=len(formats)
    )
