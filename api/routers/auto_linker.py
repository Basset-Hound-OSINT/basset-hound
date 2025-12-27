"""
Auto-Linker API Router for Basset Hound OSINT Platform.

Provides REST API endpoints for automatic entity linking, duplicate detection,
and entity merging based on matching identifiers.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field

from ..dependencies import get_neo4j_handler
from ..services.auto_linker import get_auto_linker, AutoLinker


router = APIRouter(
    prefix="/projects/{project_safe_name}/auto-link",
    tags=["auto-linking"],
    responses={
        404: {"description": "Project or entity not found"},
        500: {"description": "Internal server error"},
    },
)


# ----- Pydantic Models -----

class MatchingIdentifier(BaseModel):
    """Schema for a matching identifier between entities."""
    identifier_type: str = Field(..., description="Type of identifier (e.g., email, phone)")
    path: str = Field(..., description="Full path in profile schema")
    value: str = Field(..., description="The matching value")
    weight: float = Field(1.0, description="Weight for confidence calculation")


class LinkSuggestionResponse(BaseModel):
    """Schema for a suggested link between entities."""
    source_entity_id: str = Field(..., description="Source entity ID")
    target_entity_id: str = Field(..., description="Target entity ID")
    target_entity_name: str = Field(..., description="Display name of target entity")
    matching_identifiers: List[MatchingIdentifier] = Field(
        default_factory=list,
        description="List of matching identifiers"
    )
    confidence_score: float = Field(..., description="Confidence score for the match")
    suggested_relationship_type: str = Field(
        "SHARED_IDENTIFIER",
        description="Suggested relationship type"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "source_entity_id": "abc123",
                "target_entity_id": "def456",
                "target_entity_name": "John Doe",
                "matching_identifiers": [
                    {
                        "identifier_type": "email",
                        "path": "contact.email",
                        "value": "john@example.com",
                        "weight": 3.0
                    }
                ],
                "confidence_score": 3.0,
                "suggested_relationship_type": "SHARED_IDENTIFIER"
            }
        }


class DuplicatesResponse(BaseModel):
    """Schema for duplicates detection response."""
    entity_id: Optional[str] = Field(None, description="Entity ID (if single entity scan)")
    project_id: str = Field(..., description="Project identifier")
    duplicates: List[LinkSuggestionResponse] = Field(
        default_factory=list,
        description="List of potential duplicates"
    )
    count: int = Field(0, description="Number of duplicates found")
    entities_scanned: Optional[int] = Field(
        None,
        description="Total entities scanned (for project-wide scan)"
    )
    scanned_at: Optional[str] = Field(None, description="Scan timestamp")


class SuggestLinksResponse(BaseModel):
    """Schema for link suggestions response."""
    entity_id: str = Field(..., description="Entity ID")
    potential_duplicates: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="High-confidence duplicate matches"
    )
    suggested_links: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Lower-confidence link suggestions"
    )
    total_suggestions: int = Field(0, description="Total number of suggestions")


class MergeRequest(BaseModel):
    """Schema for entity merge request."""
    primary_entity_id: str = Field(..., description="Entity ID to keep and merge into")
    secondary_entity_id: str = Field(..., description="Entity ID to merge from")
    delete_secondary: bool = Field(
        False,
        description="Whether to delete the secondary entity after merge"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "primary_entity_id": "abc123",
                "secondary_entity_id": "def456",
                "delete_secondary": True
            }
        }


class MergeResponse(BaseModel):
    """Schema for entity merge response."""
    success: bool = Field(..., description="Whether merge succeeded")
    primary_entity_id: str = Field(..., description="ID of primary entity")
    secondary_entity_id: str = Field(..., description="ID of secondary entity")
    secondary_deleted: bool = Field(False, description="Whether secondary was deleted")
    merged_entity: Optional[Dict[str, Any]] = Field(
        None,
        description="The merged entity data"
    )
    error: Optional[str] = Field(None, description="Error message if failed")


class AutoLinkProjectResponse(BaseModel):
    """Schema for project-wide auto-link scan response."""
    project: str = Field(..., description="Project identifier")
    entities_scanned: int = Field(0, description="Total entities scanned")
    entities_with_identifiers: int = Field(
        0,
        description="Entities with extractable identifiers"
    )
    potential_duplicates: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="High-confidence duplicate pairs"
    )
    suggested_links: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Lower-confidence link suggestions"
    )
    total_suggestions: int = Field(0, description="Total suggestions found")
    links_created: Optional[int] = Field(
        None,
        description="Links created (if create_links=True)"
    )
    scanned_at: str = Field(..., description="Scan timestamp")


class IdentifierFieldInfo(BaseModel):
    """Schema for identifier field information."""
    path: str = Field(..., description="Full path in schema")
    section_id: str = Field(..., description="Section ID")
    field_id: str = Field(..., description="Field ID")
    component_id: Optional[str] = Field(None, description="Component ID if applicable")
    field_type: str = Field(..., description="Field type")
    multiple: bool = Field(False, description="Whether field allows multiple values")


# ----- Helper Functions -----

def get_linker_with_handler(neo4j_handler) -> AutoLinker:
    """Get AutoLinker instance with the current Neo4j handler."""
    linker = get_auto_linker(neo4j_handler)
    return linker


# ----- Endpoints -----

@router.get(
    "/duplicates",
    response_model=DuplicatesResponse,
    summary="Find potential duplicates in project",
    description="Scan all entities in the project for potential duplicates based on matching identifiers.",
    responses={
        200: {"description": "Duplicates found successfully"},
        404: {"description": "Project not found"},
    }
)
async def find_project_duplicates(
    project_safe_name: str,
    min_confidence: float = Query(
        5.0,
        ge=0.0,
        le=20.0,
        description="Minimum confidence score to consider as duplicate"
    ),
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Find potential duplicate entities across the entire project.

    Scans all entities for matching identifiers and returns pairs
    that exceed the minimum confidence threshold.

    - **project_safe_name**: The URL-safe identifier for the project
    - **min_confidence**: Minimum confidence score (default: 5.0)
    """
    # Verify project exists
    project = neo4j_handler.get_project(project_safe_name)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_safe_name}' not found"
        )

    try:
        linker = get_linker_with_handler(neo4j_handler)
        result = linker.auto_link_all(project_safe_name, create_links=False)

        # Filter to only high-confidence duplicates
        duplicates = [
            d for d in result.get("potential_duplicates", [])
            if d.get("confidence_score", 0) >= min_confidence
        ]

        return {
            "project_id": project_safe_name,
            "duplicates": duplicates,
            "count": len(duplicates),
            "entities_scanned": result.get("entities_scanned", 0),
            "scanned_at": result.get("scanned_at")
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to find duplicates: {str(e)}"
        )


@router.get(
    "/entities/{entity_id}/duplicates",
    response_model=DuplicatesResponse,
    summary="Find duplicates for a specific entity",
    description="Find entities that might be duplicates of the specified entity.",
    responses={
        200: {"description": "Duplicates found successfully"},
        404: {"description": "Project or entity not found"},
    }
)
async def find_entity_duplicates(
    project_safe_name: str,
    entity_id: str,
    min_confidence: float = Query(
        2.0,
        ge=0.0,
        le=20.0,
        description="Minimum confidence score for matches"
    ),
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Find potential duplicates for a specific entity.

    Analyzes the entity's identifiers and finds other entities
    with matching values.

    - **project_safe_name**: The URL-safe identifier for the project
    - **entity_id**: The entity ID to find duplicates for
    - **min_confidence**: Minimum confidence score (default: 2.0)
    """
    # Verify entity exists
    entity = neo4j_handler.get_person(project_safe_name, entity_id)
    if not entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity '{entity_id}' not found in project '{project_safe_name}'"
        )

    try:
        linker = get_linker_with_handler(neo4j_handler)
        suggestions = linker.find_matching_entities(
            project_safe_name, entity_id, min_confidence=min_confidence
        )

        return {
            "entity_id": entity_id,
            "project_id": project_safe_name,
            "duplicates": [s.to_dict() for s in suggestions],
            "count": len(suggestions)
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to find duplicates: {str(e)}"
        )


@router.get(
    "/entities/{entity_id}/suggested-links",
    response_model=SuggestLinksResponse,
    summary="Get link suggestions for an entity",
    description="Get categorized link suggestions based on shared identifiers.",
    responses={
        200: {"description": "Suggestions retrieved successfully"},
        404: {"description": "Project or entity not found"},
    }
)
async def get_suggested_links(
    project_safe_name: str,
    entity_id: str,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Get link suggestions for a specific entity.

    Returns categorized suggestions:
    - potential_duplicates: High-confidence matches (likely same person)
    - suggested_links: Lower-confidence matches (possibly related)

    - **project_safe_name**: The URL-safe identifier for the project
    - **entity_id**: The entity ID to get suggestions for
    """
    # Verify entity exists
    entity = neo4j_handler.get_person(project_safe_name, entity_id)
    if not entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity '{entity_id}' not found in project '{project_safe_name}'"
        )

    try:
        linker = get_linker_with_handler(neo4j_handler)
        result = linker.suggest_links(project_safe_name, entity_id)
        return result

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get suggestions: {str(e)}"
        )


@router.post(
    "/merge",
    response_model=MergeResponse,
    summary="Merge two entities",
    description="Merge two entities that represent the same person.",
    responses={
        200: {"description": "Entities merged successfully"},
        400: {"description": "Invalid merge request"},
        404: {"description": "Project or entity not found"},
    }
)
async def merge_entities(
    project_safe_name: str,
    merge_request: MergeRequest,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Merge two entities into one.

    The primary entity is kept and updated with data from the secondary.
    Profile data is merged with primary values taking precedence for conflicts.

    - **project_safe_name**: The URL-safe identifier for the project
    - **primary_entity_id**: The entity to keep
    - **secondary_entity_id**: The entity to merge from
    - **delete_secondary**: Whether to delete secondary after merge
    """
    # Verify project exists
    project = neo4j_handler.get_project(project_safe_name)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_safe_name}' not found"
        )

    # Verify both entities exist
    primary = neo4j_handler.get_person(project_safe_name, merge_request.primary_entity_id)
    if not primary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Primary entity '{merge_request.primary_entity_id}' not found"
        )

    secondary = neo4j_handler.get_person(project_safe_name, merge_request.secondary_entity_id)
    if not secondary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Secondary entity '{merge_request.secondary_entity_id}' not found"
        )

    # Cannot merge entity with itself
    if merge_request.primary_entity_id == merge_request.secondary_entity_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot merge entity with itself"
        )

    try:
        linker = get_linker_with_handler(neo4j_handler)
        result = linker.merge_entities(
            project_safe_name,
            merge_request.primary_entity_id,
            merge_request.secondary_entity_id,
            delete_secondary=merge_request.delete_secondary
        )

        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to merge entities: {str(e)}"
        )


@router.post(
    "/scan",
    response_model=AutoLinkProjectResponse,
    summary="Scan project for links",
    description="Scan all entities in project and optionally create links automatically.",
    responses={
        200: {"description": "Scan completed successfully"},
        404: {"description": "Project not found"},
    }
)
async def scan_project_for_links(
    project_safe_name: str,
    create_links: bool = Query(
        False,
        description="Whether to automatically create suggested links"
    ),
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Perform comprehensive auto-link scan on the project.

    Scans all entities for matching identifiers and returns all
    potential duplicates and link suggestions. Optionally creates
    links automatically.

    - **project_safe_name**: The URL-safe identifier for the project
    - **create_links**: Whether to create links automatically (default: False)
    """
    # Verify project exists
    project = neo4j_handler.get_project(project_safe_name)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_safe_name}' not found"
        )

    try:
        linker = get_linker_with_handler(neo4j_handler)
        result = linker.auto_link_all(project_safe_name, create_links=create_links)

        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to scan project: {str(e)}"
        )


@router.get(
    "/identifier-fields",
    response_model=List[IdentifierFieldInfo],
    summary="Get identifier fields",
    description="Get list of all identifier fields from the schema.",
    responses={
        200: {"description": "Identifier fields retrieved successfully"},
    }
)
async def get_identifier_fields(
    project_safe_name: str,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Get all identifier fields defined in the schema.

    Returns the list of fields marked as identifiers that are used
    for duplicate detection and link suggestion.

    - **project_safe_name**: The URL-safe identifier for the project
    """
    # Verify project exists (for consistency)
    project = neo4j_handler.get_project(project_safe_name)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_safe_name}' not found"
        )

    try:
        linker = get_linker_with_handler(neo4j_handler)
        fields = linker.get_identifier_fields()
        return fields

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get identifier fields: {str(e)}"
        )
