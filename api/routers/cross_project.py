"""
Cross-Project Linking API Router for Basset Hound OSINT Platform.

Provides REST API endpoints for cross-project entity linking, allowing
entities from different projects to be linked together. This is useful
for investigations that span multiple projects.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field, ConfigDict

from ..dependencies import get_neo4j_handler
from ..services.cross_project_linker import (
    get_cross_project_linker,
    CrossProjectLinker,
    CrossProjectLink,
)


router = APIRouter(
    prefix="/cross-project",
    tags=["cross-project-linking"],
    responses={
        404: {"description": "Project or entity not found"},
        500: {"description": "Internal server error"},
    },
)

# Entity-level cross-project endpoints
entity_router = APIRouter(
    prefix="/projects/{project_id}/entities/{entity_id}/cross-links",
    tags=["cross-project-linking"],
    responses={
        404: {"description": "Project or entity not found"},
        500: {"description": "Internal server error"},
    },
)


# ----- Pydantic Models -----

class CreateLinkRequest(BaseModel):
    """Schema for creating a cross-project link."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "source_project_id": "project_alpha",
                "source_entity_id": "entity-123",
                "target_project_id": "project_beta",
                "target_entity_id": "entity-456",
                "link_type": "SAME_PERSON",
                "confidence": 0.95,
                "metadata": {"notes": "Matched via email and phone"}
            }
        }
    )

    source_project_id: str = Field(..., description="Source project safe_name")
    source_entity_id: str = Field(..., description="Source entity ID")
    target_project_id: str = Field(..., description="Target project safe_name")
    target_entity_id: str = Field(..., description="Target entity ID")
    link_type: str = Field(
        ...,
        description="Type of link (SAME_PERSON, RELATED, ALIAS, ASSOCIATE, FAMILY, ORGANIZATION)"
    )
    confidence: float = Field(
        1.0,
        ge=0.0,
        le=1.0,
        description="Confidence score for the link (0.0 to 1.0)"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Optional additional metadata"
    )


class DeleteLinkRequest(BaseModel):
    """Schema for removing a cross-project link."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "source_project_id": "project_alpha",
                "source_entity_id": "entity-123",
                "target_project_id": "project_beta",
                "target_entity_id": "entity-456"
            }
        }
    )

    source_project_id: str = Field(..., description="Source project safe_name")
    source_entity_id: str = Field(..., description="Source entity ID")
    target_project_id: str = Field(..., description="Target project safe_name")
    target_entity_id: str = Field(..., description="Target entity ID")


class CrossProjectLinkResponse(BaseModel):
    """Schema for a cross-project link response."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "source_project_id": "project_alpha",
                "source_entity_id": "entity-123",
                "target_project_id": "project_beta",
                "target_entity_id": "entity-456",
                "link_type": "SAME_PERSON",
                "confidence": 0.95,
                "created_at": "2024-01-15T10:30:00",
                "metadata": {"notes": "Matched via email"}
            }
        }
    )

    source_project_id: str = Field(..., description="Source project safe_name")
    source_entity_id: str = Field(..., description="Source entity ID")
    target_project_id: str = Field(..., description="Target project safe_name")
    target_entity_id: str = Field(..., description="Target entity ID")
    link_type: str = Field(..., description="Type of link")
    confidence: float = Field(..., description="Confidence score")
    created_at: str = Field(..., description="Creation timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class CrossProjectLinksListResponse(BaseModel):
    """Schema for listing cross-project links."""
    project_id: str = Field(..., description="Project safe_name")
    entity_id: str = Field(..., description="Entity ID")
    links: List[CrossProjectLinkResponse] = Field(
        default_factory=list,
        description="List of cross-project links"
    )
    count: int = Field(0, description="Number of links")


class PotentialMatchResponse(BaseModel):
    """Schema for a potential cross-project match."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "source_project_id": "project_alpha",
                "source_entity_id": "entity-123",
                "target_project_id": "project_beta",
                "target_entity_id": "entity-789",
                "link_type": "SAME_PERSON",
                "confidence": 0.8,
                "matching_identifiers": [
                    {"path": "core.email", "matching_values": ["john@example.com"]}
                ]
            }
        }
    )

    source_project_id: str = Field(..., description="Source project safe_name")
    source_entity_id: str = Field(..., description="Source entity ID")
    target_project_id: str = Field(..., description="Target project safe_name")
    target_entity_id: str = Field(..., description="Target entity ID")
    link_type: str = Field(..., description="Suggested link type")
    confidence: float = Field(..., description="Match confidence score")
    matching_identifiers: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Identifiers that matched"
    )


class PotentialMatchesListResponse(BaseModel):
    """Schema for listing potential matches."""
    project_id: str = Field(..., description="Source project safe_name")
    entity_id: str = Field(..., description="Source entity ID")
    matches: List[PotentialMatchResponse] = Field(
        default_factory=list,
        description="List of potential matches"
    )
    count: int = Field(0, description="Number of potential matches")


class LinkedEntityResponse(BaseModel):
    """Schema for a linked entity across projects."""
    project_id: str = Field(..., description="Project safe_name")
    entity_id: str = Field(..., description="Entity ID")
    entity_data: Dict[str, Any] = Field(..., description="Entity profile data")
    link_type: str = Field(..., description="Type of link")
    confidence: float = Field(..., description="Link confidence")
    link_direction: str = Field(..., description="Direction of link (outgoing/incoming)")


class LinkedEntitiesListResponse(BaseModel):
    """Schema for listing all linked entities."""
    source_project_id: str = Field(..., description="Source project safe_name")
    source_entity_id: str = Field(..., description="Source entity ID")
    linked_entities: List[LinkedEntityResponse] = Field(
        default_factory=list,
        description="List of linked entities"
    )
    count: int = Field(0, description="Number of linked entities")


class LinkOperationResponse(BaseModel):
    """Schema for link operation results."""
    success: bool = Field(..., description="Whether operation succeeded")
    message: str = Field(..., description="Operation result message")
    link: Optional[CrossProjectLinkResponse] = Field(
        None,
        description="The created/affected link (if applicable)"
    )


# ----- Helper Functions -----

def get_linker_with_handler(neo4j_handler) -> CrossProjectLinker:
    """Get CrossProjectLinker instance with the current Neo4j handler."""
    return get_cross_project_linker(neo4j_handler)


def link_to_response(link: CrossProjectLink) -> CrossProjectLinkResponse:
    """Convert a CrossProjectLink to a response model."""
    return CrossProjectLinkResponse(
        source_project_id=link.source_project_id,
        source_entity_id=link.source_entity_id,
        target_project_id=link.target_project_id,
        target_entity_id=link.target_entity_id,
        link_type=link.link_type,
        confidence=link.confidence,
        created_at=link.created_at.isoformat() if hasattr(link.created_at, 'isoformat') else str(link.created_at),
        metadata=link.metadata
    )


# ----- Cross-Project Link Endpoints -----

@router.post(
    "/link",
    response_model=LinkOperationResponse,
    summary="Create a cross-project link",
    description="Create a link between two entities in different projects.",
    responses={
        200: {"description": "Link created successfully"},
        400: {"description": "Invalid request (bad link type, self-linking, etc.)"},
        404: {"description": "Project or entity not found"},
    }
)
async def create_cross_project_link(
    request: CreateLinkRequest,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Create a cross-project link between two entities.

    Links entities across different projects with a specified relationship type
    and confidence score. Valid link types include:
    - SAME_PERSON: High confidence same individual
    - RELATED: General relationship
    - ALIAS: Alternate identity
    - ASSOCIATE: Business/social associate
    - FAMILY: Family relationship
    - ORGANIZATION: Organizational relationship
    """
    try:
        linker = get_linker_with_handler(neo4j_handler)

        link = await linker.link_entities(
            source_project=request.source_project_id,
            source_entity=request.source_entity_id,
            target_project=request.target_project_id,
            target_entity=request.target_entity_id,
            link_type=request.link_type,
            confidence=request.confidence,
            metadata=request.metadata
        )

        return LinkOperationResponse(
            success=True,
            message=f"Cross-project link created between {request.source_entity_id} and {request.target_entity_id}",
            link=link_to_response(link)
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create cross-project link: {str(e)}"
        )


@router.delete(
    "/link",
    response_model=LinkOperationResponse,
    summary="Remove a cross-project link",
    description="Remove an existing cross-project link between two entities.",
    responses={
        200: {"description": "Link removed successfully"},
        404: {"description": "Link not found"},
    }
)
async def remove_cross_project_link(
    request: DeleteLinkRequest,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Remove a cross-project link between two entities.

    Deletes the link relationship from the graph database.
    """
    try:
        linker = get_linker_with_handler(neo4j_handler)

        success = await linker.unlink_entities(
            source_project=request.source_project_id,
            source_entity=request.source_entity_id,
            target_project=request.target_project_id,
            target_entity=request.target_entity_id
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cross-project link not found"
            )

        return LinkOperationResponse(
            success=True,
            message=f"Cross-project link removed between {request.source_entity_id} and {request.target_entity_id}"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove cross-project link: {str(e)}"
        )


@router.get(
    "/find-matches/{project_id}/{entity_id}",
    response_model=PotentialMatchesListResponse,
    summary="Find potential matches in other projects",
    description="Find entities in other projects that might be the same person based on shared identifiers.",
    responses={
        200: {"description": "Potential matches found"},
        404: {"description": "Project or entity not found"},
    }
)
async def find_potential_matches(
    project_id: str,
    entity_id: str,
    target_projects: Optional[str] = Query(
        None,
        description="Comma-separated list of target project safe_names to search (searches all if not specified)"
    ),
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Find potential cross-project matches for an entity.

    Searches other projects for entities with matching identifiers
    (email, phone, usernames, etc.) and returns potential matches
    ranked by confidence.
    """
    # Verify entity exists
    entity = await neo4j_handler.get_person(project_id, entity_id)
    if not entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity '{entity_id}' not found in project '{project_id}'"
        )

    try:
        linker = get_linker_with_handler(neo4j_handler)

        # Parse target projects if specified
        target_project_list = None
        if target_projects:
            target_project_list = [p.strip() for p in target_projects.split(",")]

        matches = await linker.find_potential_matches(
            project_id=project_id,
            entity_id=entity_id,
            target_projects=target_project_list
        )

        match_responses = []
        for match in matches:
            matching_identifiers = match.metadata.get("matching_identifiers", [])
            match_responses.append(PotentialMatchResponse(
                source_project_id=match.source_project_id,
                source_entity_id=match.source_entity_id,
                target_project_id=match.target_project_id,
                target_entity_id=match.target_entity_id,
                link_type=match.link_type,
                confidence=match.confidence,
                matching_identifiers=matching_identifiers
            ))

        return PotentialMatchesListResponse(
            project_id=project_id,
            entity_id=entity_id,
            matches=match_responses,
            count=len(match_responses)
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to find potential matches: {str(e)}"
        )


# ----- Entity-Level Cross-Project Endpoints -----

@entity_router.get(
    "",
    response_model=CrossProjectLinksListResponse,
    summary="Get cross-project links for an entity",
    description="Get all cross-project links associated with a specific entity.",
    responses={
        200: {"description": "Links retrieved successfully"},
        404: {"description": "Project or entity not found"},
    }
)
async def get_entity_cross_project_links(
    project_id: str,
    entity_id: str,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Get all cross-project links for a specific entity.

    Returns both outgoing links (where this entity is the source)
    and incoming links (where this entity is the target).
    """
    # Verify entity exists
    entity = await neo4j_handler.get_person(project_id, entity_id)
    if not entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity '{entity_id}' not found in project '{project_id}'"
        )

    try:
        linker = get_linker_with_handler(neo4j_handler)

        links = await linker.get_cross_project_links(
            project_id=project_id,
            entity_id=entity_id
        )

        link_responses = [link_to_response(link) for link in links]

        return CrossProjectLinksListResponse(
            project_id=project_id,
            entity_id=entity_id,
            links=link_responses,
            count=len(link_responses)
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cross-project links: {str(e)}"
        )


@entity_router.get(
    "/all-linked",
    response_model=LinkedEntitiesListResponse,
    summary="Get all linked entities across projects",
    description="Get all entities linked to this entity across all projects.",
    responses={
        200: {"description": "Linked entities retrieved successfully"},
        404: {"description": "Project or entity not found"},
    }
)
async def get_all_linked_entities(
    project_id: str,
    entity_id: str,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Get all entities linked to this entity across all projects.

    Returns full entity data for each linked entity along with
    link metadata.
    """
    # Verify entity exists
    entity = await neo4j_handler.get_person(project_id, entity_id)
    if not entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity '{entity_id}' not found in project '{project_id}'"
        )

    try:
        linker = get_linker_with_handler(neo4j_handler)

        linked_entities = await linker.get_all_linked_entities(
            project_id=project_id,
            entity_id=entity_id
        )

        entity_responses = [
            LinkedEntityResponse(
                project_id=e["project_id"],
                entity_id=e["entity_id"],
                entity_data=e["entity_data"],
                link_type=e["link_type"],
                confidence=e["confidence"],
                link_direction=e["link_direction"]
            )
            for e in linked_entities
        ]

        return LinkedEntitiesListResponse(
            source_project_id=project_id,
            source_entity_id=entity_id,
            linked_entities=entity_responses,
            count=len(entity_responses)
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get linked entities: {str(e)}"
        )
