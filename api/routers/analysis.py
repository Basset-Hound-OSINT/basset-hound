"""
Graph Analysis Router for Basset Hound.

Provides endpoints for analyzing entity relationships in OSINT investigation projects,
including path finding, centrality analysis, neighborhood exploration, and cluster detection.
"""

from typing import Optional, Any

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, ConfigDict, Field

from ..dependencies import get_neo4j_handler


router = APIRouter(
    prefix="/analysis/{project_safe_name}",
    tags=["analysis"],
    responses={
        404: {"description": "Project or entity not found"},
        500: {"description": "Internal server error"},
    },
)


# ----- Pydantic Models -----

class PathNode(BaseModel):
    """Schema for a node in a path."""
    entity_id: str = Field(..., description="Entity ID")
    entity: Optional[dict[str, Any]] = Field(None, description="Full entity data")


class ShortestPathResponse(BaseModel):
    """Schema for shortest path response."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "found": True,
            "path_length": 3,
            "entity_count": 4,
            "entity_ids": ["entity1", "entity2", "entity3", "entity4"],
            "entities": []
        }
    })

    found: bool = Field(..., description="Whether a path was found")
    path_length: Optional[int] = Field(None, description="Number of hops in the path")
    entity_count: Optional[int] = Field(None, description="Number of entities in path")
    entity_ids: Optional[list[str]] = Field(None, description="Entity IDs in path order")
    entities: Optional[list[dict[str, Any]]] = Field(None, description="Full entity data")
    message: Optional[str] = Field(None, description="Additional message if no path found")


class PathInfo(BaseModel):
    """Schema for a single path in all-paths response."""
    entity_ids: list[str] = Field(..., description="Entity IDs in path order")
    path_length: int = Field(..., description="Number of hops")
    entity_count: int = Field(..., description="Number of entities")


class AllPathsResponse(BaseModel):
    """Schema for all paths response."""
    found: bool = Field(..., description="Whether any paths were found")
    path_count: int = Field(0, description="Number of paths found")
    max_depth_searched: int = Field(..., description="Maximum depth searched")
    paths: list[PathInfo] = Field(default_factory=list, description="List of paths")


class CentralityResponse(BaseModel):
    """Schema for entity centrality response."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "entity_id": "550e8400-e29b-41d4-a716-446655440000",
            "degree_centrality": 5,
            "outgoing_connections": 3,
            "incoming_connections": 2,
            "outgoing_to": ["entity2", "entity3", "entity4"],
            "incoming_from": ["entity5", "entity6"],
            "normalized_centrality": 0.25,
            "total_entities_in_project": 10
        }
    })

    entity_id: str = Field(..., description="Entity ID")
    degree_centrality: int = Field(..., description="Total number of connections")
    outgoing_connections: int = Field(..., description="Number of entities this entity tagged")
    incoming_connections: int = Field(..., description="Number of entities that tagged this entity")
    outgoing_to: list[str] = Field(default_factory=list, description="IDs of tagged entities")
    incoming_from: list[str] = Field(default_factory=list, description="IDs of entities that tagged this")
    normalized_centrality: float = Field(..., description="Normalized centrality score (0-1)")
    total_entities_in_project: int = Field(..., description="Total entities in project")


class EntityConnectionStats(BaseModel):
    """Schema for entity connection statistics."""
    entity_id: str = Field(..., description="Entity ID")
    entity: dict[str, Any] = Field(..., description="Full entity data")
    outgoing_connections: int = Field(..., description="Number of outgoing connections")
    incoming_connections: int = Field(..., description="Number of incoming connections")
    total_connections: int = Field(..., description="Total connections")


class MostConnectedResponse(BaseModel):
    """Schema for most connected entities response."""
    entities: list[EntityConnectionStats] = Field(default_factory=list)
    count: int = Field(0, description="Number of entities returned")
    total_entities_analyzed: int = Field(0, description="Total entities in project")


class NeighborhoodResponse(BaseModel):
    """Schema for entity neighborhood response."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "center_entity_id": "entity1",
            "max_depth": 2,
            "total_entities": 5,
            "neighborhood": {
                "depth_0": [{"id": "entity1"}],
                "depth_1": [{"id": "entity2"}, {"id": "entity3"}],
                "depth_2": [{"id": "entity4"}, {"id": "entity5"}]
            },
            "edges": [
                {"source": "entity1", "target": "entity2"},
                {"source": "entity1", "target": "entity3"}
            ]
        }
    })

    center_entity_id: str = Field(..., description="The center entity ID")
    max_depth: int = Field(..., description="Maximum depth searched")
    total_entities: int = Field(..., description="Total entities in neighborhood")
    neighborhood: dict[str, list[dict[str, Any]]] = Field(
        ...,
        description="Entities organized by depth (depth_0, depth_1, etc.)"
    )
    edges: list[dict[str, str]] = Field(
        default_factory=list,
        description="Edges within the neighborhood"
    )


class ClusterInfo(BaseModel):
    """Schema for cluster information."""
    cluster_id: str = Field(..., description="Cluster identifier (root entity ID)")
    size: int = Field(..., description="Number of entities in cluster")
    entity_ids: list[str] = Field(..., description="IDs of entities in cluster")
    entities: list[dict[str, Any]] = Field(default_factory=list, description="Full entity data")
    internal_edges: int = Field(..., description="Number of edges within cluster")
    is_isolated: bool = Field(..., description="Whether this is a single isolated entity")


class ClustersResponse(BaseModel):
    """Schema for clusters response."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "cluster_count": 3,
            "isolated_count": 1,
            "connected_clusters": 2,
            "total_entities": 10,
            "clusters": []
        }
    })

    cluster_count: int = Field(..., description="Total number of clusters")
    isolated_count: int = Field(..., description="Number of isolated entities")
    connected_clusters: int = Field(..., description="Number of clusters with 2+ entities")
    total_entities: int = Field(..., description="Total entities in project")
    clusters: list[ClusterInfo] = Field(default_factory=list, description="List of clusters")


class ErrorResponse(BaseModel):
    """Schema for error response."""
    error: str = Field(..., description="Error message")


# ----- Endpoints -----

@router.get(
    "/path/{entity1}/{entity2}",
    response_model=ShortestPathResponse,
    summary="Find shortest path between entities",
    description="Find the shortest path between two entities through their relationships.",
    responses={
        200: {"description": "Path information retrieved successfully"},
        404: {"description": "Project or entity not found"},
    }
)
async def find_shortest_path(
    project_safe_name: str,
    entity1: str,
    entity2: str,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Find the shortest path between two entities.

    Uses graph traversal to find the most direct connection between
    two entities through their tagged relationships.

    - **project_safe_name**: The URL-safe identifier for the project
    - **entity1**: The starting entity ID
    - **entity2**: The target entity ID
    """
    # Verify project exists
    project = neo4j_handler.get_project(project_safe_name)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_safe_name}' not found"
        )

    # Verify entities exist
    e1 = neo4j_handler.get_person(project_safe_name, entity1)
    e2 = neo4j_handler.get_person(project_safe_name, entity2)

    if not e1:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity '{entity1}' not found"
        )
    if not e2:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity '{entity2}' not found"
        )

    try:
        result = neo4j_handler.find_shortest_path(project_safe_name, entity1, entity2)

        if result is None:
            return ShortestPathResponse(
                found=False,
                message="Unable to find path between entities"
            )

        return result

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to find path: {str(e)}"
        )


@router.get(
    "/paths/{entity1}/{entity2}",
    response_model=AllPathsResponse,
    summary="Find all paths between entities",
    description="Find all paths between two entities up to a maximum depth.",
    responses={
        200: {"description": "Paths retrieved successfully"},
        404: {"description": "Project or entity not found"},
    }
)
async def find_all_paths(
    project_safe_name: str,
    entity1: str,
    entity2: str,
    max_depth: int = Query(default=5, ge=1, le=10, description="Maximum path depth"),
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Find all paths between two entities.

    Returns all possible paths between two entities up to the specified
    maximum depth. Useful for understanding all connections between entities.

    - **project_safe_name**: The URL-safe identifier for the project
    - **entity1**: The starting entity ID
    - **entity2**: The target entity ID
    - **max_depth**: Maximum path length to search (1-10, default: 5)
    """
    # Verify project exists
    project = neo4j_handler.get_project(project_safe_name)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_safe_name}' not found"
        )

    # Verify entities exist
    e1 = neo4j_handler.get_person(project_safe_name, entity1)
    e2 = neo4j_handler.get_person(project_safe_name, entity2)

    if not e1:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity '{entity1}' not found"
        )
    if not e2:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity '{entity2}' not found"
        )

    try:
        result = neo4j_handler.find_all_paths(project_safe_name, entity1, entity2, max_depth)
        return result

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to find paths: {str(e)}"
        )


@router.get(
    "/centrality/{entity_id}",
    response_model=CentralityResponse,
    summary="Get entity centrality",
    description="Calculate degree centrality for a specific entity.",
    responses={
        200: {"description": "Centrality metrics retrieved successfully"},
        404: {"description": "Project or entity not found"},
    }
)
async def get_entity_centrality(
    project_safe_name: str,
    entity_id: str,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Get centrality metrics for an entity.

    Calculates degree centrality (number of connections) for the specified
    entity, including both incoming and outgoing relationships.

    - **project_safe_name**: The URL-safe identifier for the project
    - **entity_id**: The entity ID to analyze
    """
    # Verify project exists
    project = neo4j_handler.get_project(project_safe_name)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_safe_name}' not found"
        )

    try:
        result = neo4j_handler.get_entity_centrality(project_safe_name, entity_id)

        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entity '{entity_id}' not found"
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate centrality: {str(e)}"
        )


@router.get(
    "/most-connected",
    response_model=MostConnectedResponse,
    summary="Get most connected entities",
    description="Find the most connected entities in the project.",
    responses={
        200: {"description": "Most connected entities retrieved successfully"},
        404: {"description": "Project not found"},
    }
)
async def get_most_connected(
    project_safe_name: str,
    limit: int = Query(default=10, ge=1, le=100, description="Maximum number of entities to return"),
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Get the most connected entities in a project.

    Returns entities ranked by their total degree centrality
    (sum of incoming and outgoing connections).

    - **project_safe_name**: The URL-safe identifier for the project
    - **limit**: Maximum number of entities to return (1-100, default: 10)
    """
    # Verify project exists
    project = neo4j_handler.get_project(project_safe_name)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_safe_name}' not found"
        )

    try:
        result = neo4j_handler.get_most_connected(project_safe_name, limit=limit)
        return result

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get most connected entities: {str(e)}"
        )


@router.get(
    "/neighborhood/{entity_id}",
    response_model=NeighborhoodResponse,
    summary="Get entity neighborhood",
    description="Get all entities within N hops of a given entity.",
    responses={
        200: {"description": "Neighborhood retrieved successfully"},
        404: {"description": "Project or entity not found"},
    }
)
async def get_entity_neighborhood(
    project_safe_name: str,
    entity_id: str,
    depth: int = Query(default=2, ge=1, le=5, description="Maximum number of hops"),
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Get the neighborhood network around an entity.

    Returns all entities within N hops of the specified entity,
    creating an ego network centered on that entity.

    - **project_safe_name**: The URL-safe identifier for the project
    - **entity_id**: The center entity ID
    - **depth**: Maximum number of hops (1-5, default: 2)
    """
    # Verify project exists
    project = neo4j_handler.get_project(project_safe_name)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_safe_name}' not found"
        )

    try:
        result = neo4j_handler.get_entity_neighborhood(project_safe_name, entity_id, depth)

        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entity '{entity_id}' not found"
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get neighborhood: {str(e)}"
        )


@router.get(
    "/clusters",
    response_model=ClustersResponse,
    summary="Get network clusters",
    description="Detect connected components/clusters in the entity graph.",
    responses={
        200: {"description": "Clusters retrieved successfully"},
        404: {"description": "Project not found"},
    }
)
async def get_clusters(
    project_safe_name: str,
    include_isolated: bool = Query(
        default=True,
        description="Include isolated entities as single-entity clusters"
    ),
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Detect clusters in the entity network.

    Identifies groups of entities that are connected to each other
    but not to entities in other groups. Useful for finding distinct
    networks or communities within a project.

    - **project_safe_name**: The URL-safe identifier for the project
    - **include_isolated**: Whether to include isolated entities (default: True)
    """
    # Verify project exists
    project = neo4j_handler.get_project(project_safe_name)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_safe_name}' not found"
        )

    try:
        result = neo4j_handler.find_clusters(project_safe_name)

        if not include_isolated:
            # Filter out isolated entities
            result["clusters"] = [c for c in result["clusters"] if not c["is_isolated"]]
            result["cluster_count"] = len(result["clusters"])

        return result

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to detect clusters: {str(e)}"
        )
