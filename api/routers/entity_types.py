"""
Entity Types Router for Basset Hound OSINT Platform.

Provides REST API endpoints for entity type UI configuration, including:
- Listing all entity types with their configurations
- Getting specific entity type configurations
- Retrieving icons, colors, and form fields for entity types
- Getting valid relationship types between entity types
- Entity type statistics per project
- Validating entity data against type schemas

These endpoints support the frontend UI in rendering entity-type-specific
forms, icons, colors, and relationship options.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from pydantic import BaseModel, Field, ConfigDict

from ..dependencies import get_neo4j_handler
from ..services.entity_type_ui import (
    EntityTypeUIService,
    get_entity_type_ui_service,
)
from ..models.entity_type_ui import (
    EntityTypeUIConfig,
    FieldUIConfig,
    EntityTypeStats,
    ProjectEntityTypeStats,
    CrossTypeRelationships,
    EntityValidationResult,
    EntityTypeIconResponse,
    EntityTypeListResponse,
)
from ..models.entity_types import EntityType


# =============================================================================
# ROUTER CONFIGURATION
# =============================================================================

router = APIRouter(
    prefix="/entity-types",
    tags=["entity-types"],
    responses={
        404: {"description": "Entity type not found"},
        500: {"description": "Internal server error"},
    },
)

# Project-scoped router for statistics
project_entity_types_router = APIRouter(
    prefix="/projects/{project_safe_name}/entity-types",
    tags=["entity-types"],
    responses={
        404: {"description": "Project or entity type not found"},
        500: {"description": "Internal server error"},
    },
)


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class EntityValidationRequest(BaseModel):
    """Request model for entity validation endpoint."""

    profile: Dict[str, Any] = Field(
        ...,
        description="Profile data to validate against the entity type schema"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "profile": {
                    "core": {
                        "name": "John Doe",
                        "email": "john@example.com"
                    }
                }
            }
        }
    )


class ColorResponse(BaseModel):
    """Response model for entity type color endpoint."""

    type: str = Field(..., description="Entity type identifier")
    color: str = Field(..., description="CSS color value")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "person",
                "color": "#3498db"
            }
        }
    )


class FieldsResponse(BaseModel):
    """Response model for entity type fields endpoint."""

    type: str = Field(..., description="Entity type identifier")
    fields: List[FieldUIConfig] = Field(
        default_factory=list,
        description="List of field configurations"
    )
    total: int = Field(default=0, description="Total number of fields")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "person",
                "total": 8,
                "fields": [
                    {
                        "id": "name",
                        "label": "Full Name",
                        "type": "text",
                        "required": True
                    }
                ]
            }
        }
    )


# =============================================================================
# ENTITY TYPE ENDPOINTS
# =============================================================================

@router.get(
    "",
    response_model=EntityTypeListResponse,
    summary="List all entity types",
    description="Retrieve UI configurations for all available entity types.",
    responses={
        200: {
            "description": "List of entity type configurations",
            "content": {
                "application/json": {
                    "example": {
                        "total": 6,
                        "entity_types": [
                            {
                                "type": "person",
                                "icon": "fa-user",
                                "color": "#3498db",
                                "label": "Person",
                                "plural_label": "People"
                            }
                        ]
                    }
                }
            }
        }
    }
)
async def list_entity_types(
    neo4j=Depends(get_neo4j_handler),
    include_fields: bool = Query(
        False,
        description="Include field definitions in response"
    ),
    include_sections: bool = Query(
        False,
        description="Include section definitions in response"
    )
):
    """
    List all available entity types with their UI configurations.

    Returns a list of entity type configurations including icons, colors,
    labels, and optionally field and section definitions.

    This endpoint is useful for:
    - Populating entity type selectors in the UI
    - Getting icon/color mappings for graph visualization
    - Building dynamic forms based on entity type

    Args:
        include_fields: If True, include full field definitions for each type
        include_sections: If True, include section definitions for form layout

    Returns:
        EntityTypeListResponse with all entity type configurations
    """
    try:
        service = get_entity_type_ui_service(neo4j)
        configs = service.get_all_entity_type_configs()

        # Optionally strip fields/sections for lighter response
        if not include_fields:
            for config in configs:
                config.fields = []
        if not include_sections:
            for config in configs:
                config.sections = []

        return EntityTypeListResponse(
            entity_types=configs,
            total=len(configs)
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving entity types: {str(e)}"
        )


@router.get(
    "/{entity_type}",
    response_model=EntityTypeUIConfig,
    summary="Get entity type configuration",
    description="Retrieve the full UI configuration for a specific entity type.",
    responses={
        200: {
            "description": "Entity type configuration",
            "content": {
                "application/json": {
                    "example": {
                        "type": "person",
                        "icon": "fa-user",
                        "color": "#3498db",
                        "label": "Person",
                        "plural_label": "People",
                        "description": "Individual people being investigated"
                    }
                }
            }
        },
        404: {"description": "Entity type not found"}
    }
)
async def get_entity_type(
    entity_type: str,
    neo4j=Depends(get_neo4j_handler)
):
    """
    Get the full UI configuration for a specific entity type.

    Returns complete configuration including:
    - Display metadata (icon, color, labels)
    - Form sections and fields
    - Searchable and list display fields
    - Primary name field configuration

    Args:
        entity_type: Entity type identifier (e.g., 'person', 'organization')

    Returns:
        EntityTypeUIConfig with complete UI configuration

    Raises:
        HTTPException: 404 if entity type is not found
    """
    # Validate entity type
    if not EntityType.is_valid(entity_type):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity type '{entity_type}' not found. Valid types: {EntityType.get_all_values()}"
        )

    try:
        service = get_entity_type_ui_service(neo4j)
        config = service.get_entity_type_config(entity_type)

        if config is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration not found for entity type: {entity_type}"
            )

        return config

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving entity type configuration: {str(e)}"
        )


@router.get(
    "/{entity_type}/icon",
    response_model=EntityTypeIconResponse,
    summary="Get entity type icon",
    description="Retrieve the FontAwesome icon class and color for an entity type.",
    responses={
        200: {
            "description": "Icon and color information",
            "content": {
                "application/json": {
                    "example": {
                        "type": "person",
                        "icon": "fa-user",
                        "color": "#3498db"
                    }
                }
            }
        },
        404: {"description": "Entity type not found"}
    }
)
async def get_entity_type_icon(
    entity_type: str,
    neo4j=Depends(get_neo4j_handler)
):
    """
    Get the icon and color for an entity type.

    Returns the FontAwesome icon class and theme color for use in:
    - Graph node rendering
    - Entity list displays
    - Navigation elements

    Args:
        entity_type: Entity type identifier

    Returns:
        EntityTypeIconResponse with icon class and color

    Raises:
        HTTPException: 404 if entity type is not found
    """
    if not EntityType.is_valid(entity_type):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity type '{entity_type}' not found"
        )

    try:
        service = get_entity_type_ui_service(neo4j)
        icon_response = service.get_entity_type_icon(entity_type)

        if icon_response is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Icon not found for entity type: {entity_type}"
            )

        return icon_response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving entity type icon: {str(e)}"
        )


@router.get(
    "/{entity_type}/color",
    response_model=ColorResponse,
    summary="Get entity type color",
    description="Retrieve the theme color for an entity type.",
    responses={
        200: {
            "description": "Color information",
            "content": {
                "application/json": {
                    "example": {
                        "type": "organization",
                        "color": "#2ecc71"
                    }
                }
            }
        },
        404: {"description": "Entity type not found"}
    }
)
async def get_entity_type_color(
    entity_type: str,
    neo4j=Depends(get_neo4j_handler)
):
    """
    Get the theme color for an entity type.

    Returns the CSS color value used for:
    - Graph node coloring
    - UI accents and highlights
    - Charts and visualizations

    Args:
        entity_type: Entity type identifier

    Returns:
        ColorResponse with type and color

    Raises:
        HTTPException: 404 if entity type is not found
    """
    if not EntityType.is_valid(entity_type):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity type '{entity_type}' not found"
        )

    try:
        service = get_entity_type_ui_service(neo4j)
        color = service.get_entity_type_color(entity_type)

        if color is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Color not found for entity type: {entity_type}"
            )

        return ColorResponse(type=entity_type, color=color)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving entity type color: {str(e)}"
        )


@router.get(
    "/{entity_type}/fields",
    response_model=FieldsResponse,
    summary="Get form fields for entity type",
    description="Retrieve field definitions for building forms for an entity type.",
    responses={
        200: {
            "description": "Field definitions",
            "content": {
                "application/json": {
                    "example": {
                        "type": "person",
                        "total": 8,
                        "fields": [
                            {
                                "id": "name",
                                "label": "Full Name",
                                "type": "text",
                                "required": True,
                                "placeholder": "Enter full name",
                                "order": 1
                            }
                        ]
                    }
                }
            }
        },
        404: {"description": "Entity type not found"}
    }
)
async def get_entity_type_fields(
    entity_type: str,
    neo4j=Depends(get_neo4j_handler),
    required_only: bool = Query(
        False,
        description="Only return required fields"
    )
):
    """
    Get field definitions for an entity type's forms.

    Returns a list of field configurations for building:
    - Entity creation forms
    - Entity edit forms
    - Search filters
    - Import/export mappings

    Each field includes type, validation rules, and display options.

    Args:
        entity_type: Entity type identifier
        required_only: If True, only return required fields

    Returns:
        FieldsResponse with field definitions

    Raises:
        HTTPException: 404 if entity type is not found
    """
    if not EntityType.is_valid(entity_type):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity type '{entity_type}' not found"
        )

    try:
        service = get_entity_type_ui_service(neo4j)
        fields = service.get_entity_type_fields(entity_type)

        if required_only:
            fields = [f for f in fields if f.required]

        return FieldsResponse(
            type=entity_type,
            fields=fields,
            total=len(fields)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving entity type fields: {str(e)}"
        )


@router.get(
    "/{source_type}/relationships/{target_type}",
    response_model=CrossTypeRelationships,
    summary="Get valid relationships between entity types",
    description="Retrieve valid relationship types between a source and target entity type.",
    responses={
        200: {
            "description": "Valid relationship types",
            "content": {
                "application/json": {
                    "example": {
                        "source_type": "person",
                        "target_type": "organization",
                        "bidirectional": True,
                        "relationship_types": [
                            {
                                "relationship_type": "EMPLOYED_BY",
                                "display_label": "Employed By",
                                "inverse_type": "EMPLOYS",
                                "inverse_label": "Employs"
                            }
                        ]
                    }
                }
            }
        },
        404: {"description": "Entity type not found"}
    }
)
async def get_cross_type_relationships(
    source_type: str,
    target_type: str,
    neo4j=Depends(get_neo4j_handler)
):
    """
    Get valid relationship types between two entity types.

    Returns a list of relationship types that can be used to connect
    entities of the source type to entities of the target type.

    Includes:
    - Specific cross-type relationships (e.g., EMPLOYED_BY for Person->Organization)
    - Generic relationships (RELATED_TO, ASSOCIATED_WITH)
    - Inverse relationships where applicable

    Args:
        source_type: Source entity type identifier
        target_type: Target entity type identifier

    Returns:
        CrossTypeRelationships with valid relationship options

    Raises:
        HTTPException: 404 if either entity type is not found
    """
    # Validate entity types
    if not EntityType.is_valid(source_type):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source entity type '{source_type}' not found"
        )

    if not EntityType.is_valid(target_type):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target entity type '{target_type}' not found"
        )

    try:
        service = get_entity_type_ui_service(neo4j)
        relationships = service.get_cross_type_relationship_options(source_type, target_type)

        return relationships

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving relationship options: {str(e)}"
        )


@router.post(
    "/{entity_type}/validate",
    response_model=EntityValidationResult,
    summary="Validate entity data against type schema",
    description="Validate profile data against an entity type's schema.",
    responses={
        200: {
            "description": "Validation result",
            "content": {
                "application/json": {
                    "examples": {
                        "valid": {
                            "summary": "Valid entity data",
                            "value": {
                                "valid": True,
                                "errors": [],
                                "warnings": [],
                                "missing_required": [],
                                "invalid_fields": []
                            }
                        },
                        "invalid": {
                            "summary": "Invalid entity data",
                            "value": {
                                "valid": False,
                                "errors": [
                                    {"field": "email", "message": "Invalid email format"}
                                ],
                                "warnings": [],
                                "missing_required": ["name"],
                                "invalid_fields": ["email"]
                            }
                        }
                    }
                }
            }
        },
        404: {"description": "Entity type not found"}
    }
)
async def validate_entity(
    entity_type: str,
    request: EntityValidationRequest,
    neo4j=Depends(get_neo4j_handler)
):
    """
    Validate profile data against an entity type's schema.

    Performs validation including:
    - Required field checks
    - Type validation (email, URL, number, date formats)
    - Pattern matching (regex validation)
    - Length constraints
    - Numeric range constraints

    Returns detailed error and warning information for each invalid field.

    Args:
        entity_type: Entity type identifier
        request: EntityValidationRequest with profile data to validate

    Returns:
        EntityValidationResult with validation status and details

    Raises:
        HTTPException: 404 if entity type is not found
    """
    if not EntityType.is_valid(entity_type):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity type '{entity_type}' not found"
        )

    try:
        service = get_entity_type_ui_service(neo4j)
        result = service.validate_entity_for_type(entity_type, request.profile)

        return result

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error validating entity: {str(e)}"
        )


# =============================================================================
# PROJECT-SCOPED ENDPOINTS
# =============================================================================

@project_entity_types_router.get(
    "/stats",
    response_model=ProjectEntityTypeStats,
    summary="Get entity type statistics for project",
    description="Retrieve counts and statistics for each entity type in a project.",
    responses={
        200: {
            "description": "Entity type statistics",
            "content": {
                "application/json": {
                    "example": {
                        "project_safe_name": "operation_sunrise",
                        "total_entities": 230,
                        "dominant_type": "person",
                        "type_stats": [
                            {
                                "type": "person",
                                "count": 150,
                                "percentage": 65.2,
                                "last_created": "2024-01-15T10:30:00"
                            },
                            {
                                "type": "organization",
                                "count": 50,
                                "percentage": 21.7
                            }
                        ]
                    }
                }
            }
        }
    }
)
async def get_project_entity_type_stats(
    project_safe_name: str,
    neo4j=Depends(get_neo4j_handler)
):
    """
    Get entity type statistics for a project.

    Returns counts and percentages for each entity type in the project,
    useful for:
    - Dashboard widgets showing entity distribution
    - Project overview statistics
    - Data quality assessments

    Statistics include:
    - Total count per entity type
    - Percentage of total entities
    - Timestamp of most recently created entity
    - Dominant (most common) entity type

    Args:
        project_safe_name: Project identifier

    Returns:
        ProjectEntityTypeStats with per-type statistics
    """
    try:
        service = get_entity_type_ui_service(neo4j)
        stats = service.get_entity_type_statistics(project_safe_name)

        return stats

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving entity type statistics: {str(e)}"
        )
