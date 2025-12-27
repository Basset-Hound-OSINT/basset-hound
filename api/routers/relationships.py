"""
Relationships Router for Basset Hound.

Provides endpoints for managing tags and relationships between entities (persons)
within OSINT investigation projects. Supports named relationship types with
properties like confidence, source, notes, and timestamps.
"""

from datetime import datetime
from typing import Optional, List, Dict

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field

from ..dependencies import get_neo4j_handler, get_current_project
from ..models.relationship import (
    RelationshipType,
    ConfidenceLevel,
    RelationshipProperties,
    RelationshipCreate,
    NamedRelationshipCreate,
    RelationshipInfo,
    RelationshipResponse,
    RelationshipListResponse,
    get_all_relationship_types,
    get_relationship_type_categories,
)


router = APIRouter(
    prefix="/projects/{project_safe_name}/entities/{entity_id}/relationships",
    tags=["relationships"],
    responses={
        404: {"description": "Entity or project not found"},
        500: {"description": "Internal server error"},
    },
)


# ----- Pydantic Models -----

class TaggedPeopleUpdate(BaseModel):
    """Schema for updating tagged people on an entity."""
    tagged_ids: list[str] = Field(
        ...,
        description="List of entity IDs to tag/link to this entity"
    )
    transitive_relationships: Optional[list[str]] = Field(
        default_factory=list,
        description="List of transitive relationship entity IDs"
    )
    relationship_types: Optional[Dict[str, str]] = Field(
        default=None,
        description="Mapping of entity IDs to relationship type names"
    )
    relationship_properties: Optional[Dict[str, dict]] = Field(
        default=None,
        description="Mapping of entity IDs to relationship properties"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "tagged_ids": [
                    "550e8400-e29b-41d4-a716-446655440001",
                    "550e8400-e29b-41d4-a716-446655440002"
                ],
                "transitive_relationships": [
                    "550e8400-e29b-41d4-a716-446655440003"
                ],
                "relationship_types": {
                    "550e8400-e29b-41d4-a716-446655440001": "WORKS_WITH",
                    "550e8400-e29b-41d4-a716-446655440002": "FRIEND"
                },
                "relationship_properties": {
                    "550e8400-e29b-41d4-a716-446655440001": {
                        "confidence": "high",
                        "source": "LinkedIn"
                    }
                }
            }
        }


class TaggedPeopleResponse(BaseModel):
    """Schema for tagged people response."""
    tagged_people: list[str] = Field(
        default_factory=list,
        description="List of tagged entity IDs"
    )
    transitive_relationships: list[str] = Field(
        default_factory=list,
        description="List of transitive relationship entity IDs"
    )
    relationship_types: Optional[Dict[str, str]] = Field(
        default=None,
        description="Mapping of entity IDs to relationship type names"
    )
    relationship_properties: Optional[Dict[str, dict]] = Field(
        default=None,
        description="Mapping of entity IDs to relationship properties"
    )


class SuccessResponse(BaseModel):
    """Generic success response."""
    success: bool = True
    message: Optional[str] = None


class RelationshipTypesResponse(BaseModel):
    """Response for available relationship types."""
    types: List[str] = Field(..., description="List of all relationship type names")
    categories: Dict[str, List[str]] = Field(
        ..., description="Relationship types organized by category"
    )


# ----- Endpoints -----

@router.get(
    "/types",
    response_model=RelationshipTypesResponse,
    summary="Get available relationship types",
    description="Retrieve all available relationship types and their categories.",
)
async def get_relationship_types():
    """
    Get all available relationship types.

    Returns a list of all valid relationship type names and their categories.
    """
    return RelationshipTypesResponse(
        types=get_all_relationship_types(),
        categories=get_relationship_type_categories()
    )


@router.get(
    "/",
    response_model=TaggedPeopleResponse,
    summary="Get entity relationships",
    description="Retrieve all tags and relationships for an entity.",
    responses={
        200: {"description": "Relationships retrieved successfully"},
        404: {"description": "Entity or project not found"},
    }
)
async def get_relationships(
    project_safe_name: str,
    entity_id: str,
    include_details: bool = Query(
        False,
        description="Include full relationship details (types and properties)"
    ),
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Get relationships for an entity.

    Returns the list of tagged people and transitive relationships
    associated with the specified entity.

    - **project_safe_name**: The URL-safe identifier for the project
    - **entity_id**: The unique identifier for the entity
    - **include_details**: Whether to include relationship types and properties
    """
    person = neo4j_handler.get_person(project_safe_name, entity_id)

    if not person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity '{entity_id}' not found in project '{project_safe_name}'"
        )

    # Extract tagged people from profile
    profile = person.get("profile", {})
    tagged_section = profile.get("Tagged People", {})

    response = TaggedPeopleResponse(
        tagged_people=tagged_section.get("tagged_people", []) or [],
        transitive_relationships=tagged_section.get("transitive_relationships", []) or []
    )

    if include_details:
        response.relationship_types = tagged_section.get("relationship_types", {})
        response.relationship_properties = tagged_section.get("relationship_properties", {})

    return response


@router.put(
    "/",
    response_model=SuccessResponse,
    summary="Update entity relationships",
    description="Update the tags and relationships for an entity.",
    responses={
        200: {"description": "Relationships updated successfully"},
        400: {"description": "Invalid relationship data"},
        404: {"description": "Entity or project not found"},
    }
)
async def update_relationships(
    project_safe_name: str,
    entity_id: str,
    data: TaggedPeopleUpdate,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Update relationships for an entity.

    Updates the tagged people and transitive relationships
    for the specified entity.

    - **project_safe_name**: The URL-safe identifier for the project
    - **entity_id**: The unique identifier for the entity
    - **tagged_ids**: List of entity IDs to tag
    - **transitive_relationships**: Optional list of transitive relationships
    - **relationship_types**: Optional mapping of entity IDs to relationship types
    - **relationship_properties**: Optional mapping of entity IDs to properties
    """
    # Verify entity exists
    person = neo4j_handler.get_person(project_safe_name, entity_id)

    if not person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity '{entity_id}' not found in project '{project_safe_name}'"
        )

    try:
        # Build the update data
        update_data = {
            "tagged_people": data.tagged_ids,
            "transitive_relationships": data.transitive_relationships or []
        }

        # Add relationship types if provided
        if data.relationship_types:
            update_data["relationship_types"] = data.relationship_types

        # Add relationship properties if provided
        if data.relationship_properties:
            update_data["relationship_properties"] = data.relationship_properties

        # Update person with tagged people data
        updated_person = neo4j_handler.update_person(
            project_safe_name,
            entity_id,
            {
                "profile": {
                    "Tagged People": update_data
                }
            }
        )

        if not updated_person:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update relationships"
            )

        return SuccessResponse(
            success=True,
            message="Relationships updated successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update relationships: {str(e)}"
        )


@router.post(
    "/tag/{target_entity_id}",
    response_model=SuccessResponse,
    summary="Tag another entity with relationship type",
    description="Add a tag/relationship to another entity with optional type and properties.",
    responses={
        200: {"description": "Entity tagged successfully"},
        404: {"description": "Source or target entity not found"},
    }
)
async def tag_entity(
    project_safe_name: str,
    entity_id: str,
    target_entity_id: str,
    relationship_type: str = Query(
        "RELATED_TO",
        description="Type of relationship (e.g., WORKS_WITH, FRIEND, FAMILY)"
    ),
    confidence: Optional[str] = Query(
        None,
        description="Confidence level (confirmed, high, medium, low, unverified)"
    ),
    source: Optional[str] = Query(
        None,
        description="Source of the relationship information"
    ),
    notes: Optional[str] = Query(
        None,
        description="Additional notes about the relationship"
    ),
    bidirectional: bool = Query(
        False,
        description="Create inverse relationship on target entity"
    ),
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Tag another entity with a named relationship.

    Adds the target entity to this entity's tagged people list with
    the specified relationship type and properties.

    - **project_safe_name**: The URL-safe identifier for the project
    - **entity_id**: The source entity ID
    - **target_entity_id**: The entity ID to tag
    - **relationship_type**: Type of relationship (default: RELATED_TO)
    - **confidence**: Optional confidence level
    - **source**: Optional source of the relationship info
    - **notes**: Optional notes about the relationship
    - **bidirectional**: Whether to create inverse relationship on target
    """
    # Verify both entities exist
    source_entity = neo4j_handler.get_person(project_safe_name, entity_id)
    if not source_entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source entity '{entity_id}' not found"
        )

    target = neo4j_handler.get_person(project_safe_name, target_entity_id)
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target entity '{target_entity_id}' not found"
        )

    try:
        # Build properties
        properties = {
            "timestamp": datetime.now().isoformat()
        }
        if confidence:
            properties["confidence"] = confidence
        if source:
            properties["source"] = source
        if notes:
            properties["notes"] = notes

        # Create the relationship
        if bidirectional:
            result = neo4j_handler.create_bidirectional_relationship(
                project_safe_name,
                entity_id,
                target_entity_id,
                relationship_type,
                properties
            )
        else:
            result = neo4j_handler.create_relationship(
                project_safe_name,
                entity_id,
                target_entity_id,
                relationship_type,
                properties
            )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create relationship"
            )

        msg = f"Entity '{target_entity_id}' tagged as {relationship_type}"
        if bidirectional:
            msg += " (bidirectional)"

        return SuccessResponse(
            success=True,
            message=msg
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to tag entity: {str(e)}"
        )


@router.patch(
    "/tag/{target_entity_id}",
    response_model=SuccessResponse,
    summary="Update relationship with entity",
    description="Update the relationship type or properties for an existing relationship.",
    responses={
        200: {"description": "Relationship updated successfully"},
        404: {"description": "Entity or relationship not found"},
    }
)
async def update_entity_relationship(
    project_safe_name: str,
    entity_id: str,
    target_entity_id: str,
    relationship_type: Optional[str] = Query(
        None,
        description="New relationship type"
    ),
    confidence: Optional[str] = Query(
        None,
        description="New confidence level"
    ),
    source: Optional[str] = Query(
        None,
        description="New source information"
    ),
    notes: Optional[str] = Query(
        None,
        description="New notes"
    ),
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Update an existing relationship.

    Updates the relationship type and/or properties for an existing
    relationship between two entities.

    - **project_safe_name**: The URL-safe identifier for the project
    - **entity_id**: The source entity ID
    - **target_entity_id**: The target entity ID
    - **relationship_type**: New relationship type (optional)
    - **confidence**: New confidence level (optional)
    - **source**: New source information (optional)
    - **notes**: New notes (optional)
    """
    try:
        # Build properties update
        properties = {}
        if confidence is not None:
            properties["confidence"] = confidence
        if source is not None:
            properties["source"] = source
        if notes is not None:
            properties["notes"] = notes

        result = neo4j_handler.update_relationship(
            project_safe_name,
            entity_id,
            target_entity_id,
            relationship_type,
            properties if properties else None
        )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Relationship between '{entity_id}' and '{target_entity_id}' not found"
            )

        return SuccessResponse(
            success=True,
            message="Relationship updated successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update relationship: {str(e)}"
        )


@router.get(
    "/tag/{target_entity_id}",
    response_model=dict,
    summary="Get relationship details",
    description="Get detailed information about a specific relationship.",
    responses={
        200: {"description": "Relationship details retrieved successfully"},
        404: {"description": "Relationship not found"},
    }
)
async def get_entity_relationship(
    project_safe_name: str,
    entity_id: str,
    target_entity_id: str,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Get details of a specific relationship.

    Returns the relationship type and properties for the relationship
    between the source and target entities.
    """
    result = neo4j_handler.get_relationship(
        project_safe_name,
        entity_id,
        target_entity_id
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Relationship between '{entity_id}' and '{target_entity_id}' not found"
        )

    return result


@router.delete(
    "/tag/{target_entity_id}",
    response_model=SuccessResponse,
    summary="Remove tag from entity",
    description="Remove a tag/relationship to another entity.",
    responses={
        200: {"description": "Tag removed successfully"},
        404: {"description": "Entity not found"},
    }
)
async def untag_entity(
    project_safe_name: str,
    entity_id: str,
    target_entity_id: str,
    bidirectional: bool = Query(
        False,
        description="Also remove the reverse relationship from target entity"
    ),
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Remove tag from entity.

    Removes the target entity from this entity's tagged people list.

    - **project_safe_name**: The URL-safe identifier for the project
    - **entity_id**: The source entity ID
    - **target_entity_id**: The entity ID to untag
    - **bidirectional**: Also remove reverse relationship from target
    """
    # Verify source entity exists
    source = neo4j_handler.get_person(project_safe_name, entity_id)
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity '{entity_id}' not found"
        )

    try:
        # Delete the relationship
        result = neo4j_handler.delete_relationship(
            project_safe_name,
            entity_id,
            target_entity_id
        )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Relationship to '{target_entity_id}' not found"
            )

        # Optionally delete reverse relationship
        if bidirectional:
            neo4j_handler.delete_relationship(
                project_safe_name,
                target_entity_id,
                entity_id
            )

        msg = f"Tag to '{target_entity_id}' removed successfully"
        if bidirectional:
            msg += " (including reverse relationship)"

        return SuccessResponse(
            success=True,
            message=msg
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove tag: {str(e)}"
        )


# ----- Additional router for project-level relationship queries -----

project_relationships_router = APIRouter(
    prefix="/projects/{project_safe_name}/relationships",
    tags=["relationships"],
    responses={
        404: {"description": "Project not found"},
        500: {"description": "Internal server error"},
    },
)


@project_relationships_router.get(
    "/types",
    response_model=RelationshipTypesResponse,
    summary="Get available relationship types",
    description="Retrieve all available relationship types and their categories.",
)
async def get_project_relationship_types():
    """
    Get all available relationship types for a project.

    Returns a list of all valid relationship type names and their categories.
    """
    return RelationshipTypesResponse(
        types=get_all_relationship_types(),
        categories=get_relationship_type_categories()
    )


@project_relationships_router.get(
    "/",
    response_model=RelationshipListResponse,
    summary="Get all relationships in project",
    description="Retrieve all tag relationships between entities in a project.",
    responses={
        200: {"description": "Relationships retrieved successfully"},
        404: {"description": "Project not found"},
    }
)
async def get_all_project_relationships(
    project_safe_name: str,
    relationship_type: Optional[str] = Query(
        None,
        description="Filter by relationship type"
    ),
    include_transitive: bool = Query(
        True,
        description="Include transitive relationships"
    ),
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Get all relationships in a project.

    Returns a list of all tag/relationship connections between
    entities in the specified project.

    - **project_safe_name**: The URL-safe identifier for the project
    - **relationship_type**: Optional filter by relationship type
    - **include_transitive**: Include transitive relationships (default: True)
    """
    # Verify project exists
    project = neo4j_handler.get_project(project_safe_name)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_safe_name}' not found"
        )

    try:
        # Get all relationships using the new method
        all_relationships = neo4j_handler.get_all_relationships(
            project_safe_name,
            relationship_type=relationship_type
        )

        # Filter out transitive if requested
        if not include_transitive:
            all_relationships = [
                r for r in all_relationships if not r.get("is_transitive", False)
            ]

        # Convert to RelationshipInfo objects
        relationships = []
        for rel in all_relationships:
            props = rel.get("properties", {})
            relationships.append(RelationshipInfo(
                source_id=rel["source_id"],
                target_id=rel["target_id"],
                relationship_type=rel.get("relationship_type", "RELATED_TO"),
                confidence=props.get("confidence"),
                source=props.get("source"),
                notes=props.get("notes"),
                timestamp=props.get("timestamp"),
                is_transitive=rel.get("is_transitive", False)
            ))

        # Get type counts
        type_counts = neo4j_handler.get_relationship_type_counts(project_safe_name)

        return RelationshipListResponse(
            relationships=relationships,
            count=len(relationships),
            relationship_type_counts=type_counts
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve relationships: {str(e)}"
        )


@project_relationships_router.get(
    "/stats",
    response_model=dict,
    summary="Get relationship statistics",
    description="Retrieve statistics about relationships in a project.",
)
async def get_relationship_stats(
    project_safe_name: str,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Get relationship statistics for a project.

    Returns counts of relationships by type and other statistics.
    """
    # Verify project exists
    project = neo4j_handler.get_project(project_safe_name)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_safe_name}' not found"
        )

    try:
        type_counts = neo4j_handler.get_relationship_type_counts(project_safe_name)
        all_relationships = neo4j_handler.get_all_relationships(project_safe_name)

        # Count unique entity pairs
        unique_pairs = set()
        for rel in all_relationships:
            pair = tuple(sorted([rel["source_id"], rel["target_id"]]))
            unique_pairs.add(pair)

        return {
            "total_relationships": len(all_relationships),
            "unique_entity_pairs": len(unique_pairs),
            "relationship_type_counts": type_counts,
            "available_types": get_all_relationship_types()
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve relationship statistics: {str(e)}"
        )


# Include the project-level router in the module exports
# This should be included in the main router aggregation
