"""
Graph Visualization Router for Basset Hound.

Provides endpoints for retrieving graph data in various formats suitable
for frontend visualization libraries like D3.js, vis.js, and Cytoscape.
"""

from typing import Optional, Any, Literal
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, ConfigDict, Field

from ..dependencies import get_neo4j_handler
from ..services.graph_service import get_graph_service


router = APIRouter(
    prefix="/projects/{project_safe_name}/graph",
    tags=["graph"],
    responses={
        404: {"description": "Project, entity, or cluster not found"},
        500: {"description": "Internal server error"},
    },
)


# ----- Pydantic Models -----

class GraphNode(BaseModel):
    """Schema for a graph node."""
    id: str = Field(..., description="Node/entity ID")
    label: str = Field(..., description="Display label for the node")
    type: str = Field(..., description="Node type (e.g., Person)")
    properties: dict[str, Any] = Field(default_factory=dict, description="Node properties")


class GraphEdge(BaseModel):
    """Schema for a graph edge."""
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    type: str = Field(..., description="Relationship type")
    properties: dict[str, Any] = Field(default_factory=dict, description="Edge properties")


class RawGraphResponse(BaseModel):
    """Schema for raw graph data response."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "nodes": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "label": "John Doe",
                    "type": "Person",
                    "properties": {}
                }
            ],
            "edges": [
                {
                    "source": "550e8400-e29b-41d4-a716-446655440000",
                    "target": "550e8400-e29b-41d4-a716-446655440001",
                    "type": "WORKS_WITH",
                    "properties": {"confidence": "high"}
                }
            ]
        }
    })

    nodes: list[GraphNode] = Field(default_factory=list, description="Graph nodes")
    edges: list[GraphEdge] = Field(default_factory=list, description="Graph edges")


class D3GraphResponse(BaseModel):
    """Schema for D3.js formatted graph response."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "nodes": [{"id": "entity1", "label": "John Doe", "type": "Person"}],
            "links": [{"source": "entity1", "target": "entity2", "type": "WORKS_WITH"}]
        }
    })

    nodes: list[dict[str, Any]] = Field(default_factory=list, description="D3 nodes")
    links: list[dict[str, Any]] = Field(default_factory=list, description="D3 links")


class VisGraphResponse(BaseModel):
    """Schema for vis.js formatted graph response."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "nodes": [{"id": "entity1", "label": "John Doe", "group": "Person"}],
            "edges": [{"from": "entity1", "to": "entity2", "label": "Works With", "arrows": "to"}]
        }
    })

    nodes: list[dict[str, Any]] = Field(default_factory=list, description="vis.js nodes")
    edges: list[dict[str, Any]] = Field(default_factory=list, description="vis.js edges")


class CytoscapeGraphResponse(BaseModel):
    """Schema for Cytoscape.js formatted graph response."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "elements": {
                "nodes": [{"data": {"id": "entity1", "label": "John Doe"}}],
                "edges": [{"data": {"id": "edge_0", "source": "entity1", "target": "entity2"}}]
            }
        }
    })

    elements: dict[str, list[dict[str, Any]]] = Field(
        ..., description="Cytoscape elements (nodes and edges)"
    )


# ----- Helper Function -----

def _format_graph_response(graph_data: dict[str, Any], format_type: str) -> dict[str, Any]:
    """
    Format graph data according to the specified format.

    Args:
        graph_data: Raw graph data
        format_type: Target format (d3, vis, cytoscape, raw)

    Returns:
        Formatted graph data
    """
    # Import here to avoid issues with neo4j_handler
    from ..dependencies import get_neo4j_handler

    neo4j = get_neo4j_handler()
    graph_service = get_graph_service(neo4j)

    if format_type == "d3":
        return graph_service.format_for_d3(graph_data)
    elif format_type == "vis":
        return graph_service.format_for_vis(graph_data)
    elif format_type == "cytoscape":
        return graph_service.format_for_cytoscape(graph_data)
    else:  # raw
        return graph_data


# ----- Endpoints -----

@router.get(
    "",
    response_model=None,
    summary="Get full project graph",
    description="Retrieve the complete graph for a project in the specified format.",
    responses={
        200: {
            "description": "Graph data in requested format",
            "content": {
                "application/json": {
                    "examples": {
                        "raw": {
                            "summary": "Raw format",
                            "value": {
                                "nodes": [{"id": "entity1", "label": "John Doe"}],
                                "edges": [{"source": "entity1", "target": "entity2"}]
                            }
                        },
                        "d3": {
                            "summary": "D3.js format",
                            "value": {
                                "nodes": [{"id": "entity1", "label": "John Doe"}],
                                "links": [{"source": "entity1", "target": "entity2"}]
                            }
                        }
                    }
                }
            }
        }
    }
)
async def get_project_graph(
    project_safe_name: str,
    neo4j=Depends(get_neo4j_handler),
    format: Literal["d3", "vis", "cytoscape", "raw"] = Query(
        "raw",
        description="Output format for graph data"
    ),
    include_orphans: bool = Query(
        True,
        description="Include entities with no relationships"
    )
):
    """
    Get the complete graph for a project.

    Supports multiple output formats:
    - **d3**: D3.js format with nodes and links
    - **vis**: vis.js format with nodes and edges
    - **cytoscape**: Cytoscape.js format with elements
    - **raw**: Raw format with nodes and edges (default)

    Args:
        project_safe_name: The project's safe name
        format: Output format (d3, vis, cytoscape, raw)
        include_orphans: Whether to include entities with no relationships

    Returns:
        Graph data in the requested format
    """
    try:
        graph_service = get_graph_service(neo4j)
        graph_data = graph_service.get_project_graph(
            project_safe_name=project_safe_name,
            include_orphans=include_orphans
        )

        return _format_graph_response(graph_data, format)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving project graph: {str(e)}"
        )


@router.get(
    "/entity/{entity_id}",
    response_model=None,
    summary="Get entity-centered subgraph",
    description="Retrieve a subgraph centered around a specific entity with N-hop depth.",
    responses={
        200: {"description": "Subgraph data in requested format"},
        404: {"description": "Entity not found"}
    }
)
async def get_entity_subgraph(
    project_safe_name: str,
    entity_id: str,
    neo4j=Depends(get_neo4j_handler),
    format: Literal["d3", "vis", "cytoscape", "raw"] = Query(
        "raw",
        description="Output format for graph data"
    ),
    depth: int = Query(
        2,
        ge=1,
        le=10,
        description="Number of relationship hops to include (1-10)"
    ),
    include_orphans: bool = Query(
        False,
        description="Include entities with no relationships in the subgraph"
    )
):
    """
    Get a subgraph centered around a specific entity.

    Retrieves entities within N relationship hops from the specified entity.
    Useful for exploring local neighborhoods in large graphs.

    Args:
        project_safe_name: The project's safe name
        entity_id: The entity to center the subgraph around
        format: Output format (d3, vis, cytoscape, raw)
        depth: Number of relationship hops to include (1-10)
        include_orphans: Include entities with no relationships

    Returns:
        Subgraph data in the requested format
    """
    try:
        graph_service = get_graph_service(neo4j)
        graph_data = graph_service.get_entity_subgraph(
            project_safe_name=project_safe_name,
            entity_id=entity_id,
            depth=depth,
            include_orphans=include_orphans
        )

        return _format_graph_response(graph_data, format)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving entity subgraph: {str(e)}"
        )


@router.get(
    "/cluster/{cluster_id}",
    response_model=None,
    summary="Get cluster graph",
    description="Retrieve the graph for a specific cluster.",
    responses={
        200: {"description": "Cluster graph data in requested format"},
        404: {"description": "Cluster not found"}
    }
)
async def get_cluster_graph(
    project_safe_name: str,
    cluster_id: str,
    neo4j=Depends(get_neo4j_handler),
    format: Literal["d3", "vis", "cytoscape", "raw"] = Query(
        "raw",
        description="Output format for graph data"
    )
):
    """
    Get the graph for a specific cluster.

    Retrieves all entities and relationships within a detected cluster.
    Cluster ID is typically the root entity ID from cluster detection.

    Args:
        project_safe_name: The project's safe name
        cluster_id: The cluster root entity ID
        format: Output format (d3, vis, cytoscape, raw)

    Returns:
        Cluster graph data in the requested format
    """
    try:
        graph_service = get_graph_service(neo4j)
        graph_data = graph_service.get_cluster_graph(
            project_safe_name=project_safe_name,
            cluster_id=cluster_id
        )

        return _format_graph_response(graph_data, format)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving cluster graph: {str(e)}"
        )
