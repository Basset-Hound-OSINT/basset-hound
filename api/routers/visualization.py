"""
Graph Visualization Router for Basset Hound.

Provides endpoints for graph visualization including full project graphs,
entity neighborhood subgraphs, layout algorithms, graph exports, statistics,
and cluster visualization data.
"""

from typing import Optional, Any, Literal
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field

from ..dependencies import get_neo4j_handler


class LayoutType(str, Enum):
    """Supported graph layout algorithms."""
    FORCE_DIRECTED = "force_directed"
    HIERARCHICAL = "hierarchical"
    CIRCULAR = "circular"
    GRID = "grid"
    RADIAL = "radial"
    SPECTRAL = "spectral"


class ExportFormat(str, Enum):
    """Supported graph export formats."""
    D3 = "d3"
    CYTOSCAPE = "cytoscape"
    GRAPHML = "graphml"
    DOT = "dot"


router = APIRouter(
    prefix="/projects/{project_safe_name}/visualization",
    tags=["visualization"],
    responses={
        404: {"description": "Project or entity not found"},
        500: {"description": "Internal server error"},
    },
)


# ----- Pydantic Models -----

class VisualizationNode(BaseModel):
    """Schema for a visualization node."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "label": "John Doe",
            "type": "Person",
            "x": 100.5,
            "y": 200.3,
            "size": 10,
            "color": "#4a90d9",
            "properties": {"email": "john@example.com"}
        }
    })

    id: str = Field(..., description="Unique node identifier")
    label: str = Field(..., description="Display label for the node")
    type: str = Field(default="Entity", description="Node type (e.g., Person, Organization)")
    x: Optional[float] = Field(None, description="X coordinate for layout")
    y: Optional[float] = Field(None, description="Y coordinate for layout")
    size: Optional[float] = Field(None, description="Node size for rendering")
    color: Optional[str] = Field(None, description="Node color (hex or named)")
    properties: dict[str, Any] = Field(default_factory=dict, description="Additional node properties")


class VisualizationEdge(BaseModel):
    """Schema for a visualization edge."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "id": "edge_1",
            "source": "550e8400-e29b-41d4-a716-446655440000",
            "target": "550e8400-e29b-41d4-a716-446655440001",
            "type": "TAGGED",
            "label": "colleague",
            "weight": 1.0,
            "properties": {"confidence": "high"}
        }
    })

    id: str = Field(..., description="Unique edge identifier")
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    type: str = Field(default="RELATIONSHIP", description="Edge type")
    label: Optional[str] = Field(None, description="Edge label for display")
    weight: Optional[float] = Field(None, description="Edge weight")
    properties: dict[str, Any] = Field(default_factory=dict, description="Additional edge properties")


class GraphResponse(BaseModel):
    """Schema for complete graph response."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "nodes": [
                {
                    "id": "entity1",
                    "label": "John Doe",
                    "type": "Person",
                    "properties": {}
                }
            ],
            "edges": [
                {
                    "id": "edge_0",
                    "source": "entity1",
                    "target": "entity2",
                    "type": "TAGGED",
                    "label": "colleague"
                }
            ],
            "metadata": {
                "node_count": 1,
                "edge_count": 1,
                "project_safe_name": "my-project"
            }
        }
    })

    nodes: list[VisualizationNode] = Field(default_factory=list, description="Graph nodes")
    edges: list[VisualizationEdge] = Field(default_factory=list, description="Graph edges")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Graph metadata")


class NeighborhoodResponse(BaseModel):
    """Schema for neighborhood subgraph response."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "center_entity_id": "entity1",
            "depth": 2,
            "nodes": [],
            "edges": [],
            "depth_map": {"entity1": 0, "entity2": 1, "entity3": 2}
        }
    })

    center_entity_id: str = Field(..., description="The center entity of the neighborhood")
    depth: int = Field(..., description="Maximum depth explored")
    nodes: list[VisualizationNode] = Field(default_factory=list, description="Nodes in neighborhood")
    edges: list[VisualizationEdge] = Field(default_factory=list, description="Edges in neighborhood")
    depth_map: dict[str, int] = Field(
        default_factory=dict,
        description="Map of entity IDs to their depth from center"
    )


class LayoutResponse(BaseModel):
    """Schema for layout algorithm response."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "layout_type": "force_directed",
            "nodes": [
                {"id": "entity1", "x": 100.5, "y": 200.3}
            ],
            "bounds": {"min_x": 0, "max_x": 500, "min_y": 0, "max_y": 500},
            "parameters": {"iterations": 100, "gravity": 0.1}
        }
    })

    layout_type: str = Field(..., description="Applied layout algorithm")
    nodes: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Nodes with computed x, y positions"
    )
    bounds: dict[str, float] = Field(
        default_factory=dict,
        description="Layout bounding box (min_x, max_x, min_y, max_y)"
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Layout parameters used"
    )


class GraphStatsResponse(BaseModel):
    """Schema for graph statistics response."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "node_count": 50,
            "edge_count": 75,
            "density": 0.06,
            "avg_degree": 3.0,
            "max_degree": 12,
            "min_degree": 0,
            "isolated_nodes": 5,
            "connected_components": 3,
            "clustering_coefficient": 0.45,
            "diameter": 6
        }
    })

    node_count: int = Field(..., description="Total number of nodes")
    edge_count: int = Field(..., description="Total number of edges")
    density: float = Field(..., description="Graph density (edges / possible edges)")
    avg_degree: float = Field(..., description="Average node degree")
    max_degree: int = Field(..., description="Maximum node degree")
    min_degree: int = Field(..., description="Minimum node degree")
    isolated_nodes: int = Field(..., description="Number of nodes with no connections")
    connected_components: int = Field(..., description="Number of connected components")
    clustering_coefficient: Optional[float] = Field(
        None,
        description="Average clustering coefficient"
    )
    diameter: Optional[int] = Field(None, description="Graph diameter (longest shortest path)")


class ClusterVisualization(BaseModel):
    """Schema for a single cluster in visualization."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "cluster_id": "cluster_1",
            "size": 10,
            "centroid": {"x": 150.0, "y": 200.0},
            "color": "#ff6b6b",
            "node_ids": ["entity1", "entity2", "entity3"],
            "internal_edges": 15,
            "external_edges": 3,
            "density": 0.33
        }
    })

    cluster_id: str = Field(..., description="Cluster identifier")
    size: int = Field(..., description="Number of nodes in cluster")
    centroid: Optional[dict[str, float]] = Field(None, description="Cluster centroid position")
    color: Optional[str] = Field(None, description="Assigned cluster color")
    node_ids: list[str] = Field(default_factory=list, description="IDs of nodes in this cluster")
    internal_edges: int = Field(..., description="Number of edges within cluster")
    external_edges: int = Field(..., description="Number of edges to other clusters")
    density: float = Field(..., description="Internal density of the cluster")


class ClustersVisualizationResponse(BaseModel):
    """Schema for cluster visualization response."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "clusters": [],
            "total_clusters": 3,
            "isolated_count": 2,
            "modularity": 0.65,
            "nodes": [],
            "edges": []
        }
    })

    clusters: list[ClusterVisualization] = Field(
        default_factory=list,
        description="List of detected clusters"
    )
    total_clusters: int = Field(..., description="Total number of clusters")
    isolated_count: int = Field(..., description="Number of isolated nodes")
    modularity: Optional[float] = Field(None, description="Modularity score of clustering")
    nodes: list[VisualizationNode] = Field(
        default_factory=list,
        description="All nodes with cluster assignments"
    )
    edges: list[VisualizationEdge] = Field(
        default_factory=list,
        description="All edges"
    )


class ExportRequest(BaseModel):
    """Request schema for graph export."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "include_properties": True,
            "include_layout": True,
            "entity_ids": None
        }
    })

    include_properties: bool = Field(
        default=True,
        description="Include node and edge properties in export"
    )
    include_layout: bool = Field(
        default=False,
        description="Include layout positions in export"
    )
    entity_ids: Optional[list[str]] = Field(
        None,
        description="Specific entity IDs to export (None = all)"
    )


# ----- Helper Functions -----

def _get_entity_label(entity: dict) -> str:
    """Extract a display label from an entity."""
    profile = entity.get("profile", {})
    core = profile.get("core", {})

    # Try to get name
    names = core.get("name", [])
    if names and isinstance(names, list) and len(names) > 0:
        name_obj = names[0]
        if isinstance(name_obj, dict):
            first = name_obj.get("first_name", "")
            last = name_obj.get("last_name", "")
            if first or last:
                return f"{first} {last}".strip()

    # Fallback to email
    emails = core.get("email", [])
    if emails and isinstance(emails, list) and len(emails) > 0:
        return emails[0]

    # Fallback to ID
    return entity.get("id", "Unknown")[:8]


def _build_visualization_node(entity: dict, x: float = None, y: float = None) -> VisualizationNode:
    """Build a visualization node from an entity."""
    return VisualizationNode(
        id=entity.get("id", ""),
        label=_get_entity_label(entity),
        type="Person",
        x=x,
        y=y,
        properties={
            "created_at": entity.get("created_at"),
            "updated_at": entity.get("updated_at"),
        }
    )


def _build_visualization_edge(
    source_id: str,
    target_id: str,
    relationship: dict,
    edge_index: int
) -> VisualizationEdge:
    """Build a visualization edge from a relationship."""
    return VisualizationEdge(
        id=f"edge_{edge_index}",
        source=source_id,
        target=target_id,
        type="TAGGED",
        label=relationship.get("label", relationship.get("type", "")),
        weight=relationship.get("weight", 1.0),
        properties={
            k: v for k, v in relationship.items()
            if k not in ("source", "target", "label", "type", "weight")
        }
    )


def _apply_layout(
    nodes: list[VisualizationNode],
    edges: list[VisualizationEdge],
    layout_type: LayoutType,
    parameters: dict = None
) -> list[dict[str, Any]]:
    """
    Apply a layout algorithm to compute node positions.

    This is a simple implementation. In production, you might use
    networkx or a dedicated graph layout library.
    """
    import math
    import random

    params = parameters or {}
    positioned_nodes = []
    n = len(nodes)

    if n == 0:
        return positioned_nodes

    if layout_type == LayoutType.CIRCULAR:
        # Arrange nodes in a circle
        radius = params.get("radius", 200)
        for i, node in enumerate(nodes):
            angle = (2 * math.pi * i) / n
            x = radius * math.cos(angle) + radius
            y = radius * math.sin(angle) + radius
            positioned_nodes.append({
                "id": node.id,
                "label": node.label,
                "x": x,
                "y": y
            })

    elif layout_type == LayoutType.GRID:
        # Arrange nodes in a grid
        cols = params.get("columns", max(1, int(math.sqrt(n))))
        spacing = params.get("spacing", 100)
        for i, node in enumerate(nodes):
            row = i // cols
            col = i % cols
            positioned_nodes.append({
                "id": node.id,
                "label": node.label,
                "x": col * spacing + spacing / 2,
                "y": row * spacing + spacing / 2
            })

    elif layout_type == LayoutType.HIERARCHICAL:
        # Simple hierarchical layout based on connections
        # Nodes with more connections at the top
        node_degrees = {}
        for node in nodes:
            node_degrees[node.id] = 0
        for edge in edges:
            node_degrees[edge.source] = node_degrees.get(edge.source, 0) + 1
            node_degrees[edge.target] = node_degrees.get(edge.target, 0) + 1

        sorted_nodes = sorted(nodes, key=lambda n: node_degrees.get(n.id, 0), reverse=True)
        levels = {}
        current_level = 0
        current_count = 0
        level_size = params.get("level_size", 5)

        for node in sorted_nodes:
            if current_count >= level_size:
                current_level += 1
                current_count = 0
            levels[node.id] = current_level
            current_count += 1

        level_counts = {}
        spacing_x = params.get("spacing_x", 150)
        spacing_y = params.get("spacing_y", 100)

        for node in nodes:
            level = levels.get(node.id, 0)
            pos_in_level = level_counts.get(level, 0)
            level_counts[level] = pos_in_level + 1
            positioned_nodes.append({
                "id": node.id,
                "label": node.label,
                "x": pos_in_level * spacing_x + spacing_x / 2,
                "y": level * spacing_y + spacing_y / 2
            })

    elif layout_type == LayoutType.RADIAL:
        # Radial layout from center
        center_x = params.get("center_x", 300)
        center_y = params.get("center_y", 300)
        ring_spacing = params.get("ring_spacing", 80)

        # Group by connection count for rings
        node_degrees = {}
        for node in nodes:
            node_degrees[node.id] = 0
        for edge in edges:
            node_degrees[edge.source] = node_degrees.get(edge.source, 0) + 1
            node_degrees[edge.target] = node_degrees.get(edge.target, 0) + 1

        max_degree = max(node_degrees.values()) if node_degrees else 1
        rings = {}

        for node in nodes:
            degree = node_degrees.get(node.id, 0)
            ring = max_degree - degree  # Higher degree = closer to center
            if ring not in rings:
                rings[ring] = []
            rings[ring].append(node)

        for ring_num, ring_nodes in rings.items():
            radius = (ring_num + 1) * ring_spacing
            for i, node in enumerate(ring_nodes):
                angle = (2 * math.pi * i) / len(ring_nodes) if ring_nodes else 0
                x = center_x + radius * math.cos(angle)
                y = center_y + radius * math.sin(angle)
                positioned_nodes.append({
                    "id": node.id,
                    "label": node.label,
                    "x": x,
                    "y": y
                })

    else:  # Force-directed or spectral (simplified random placement)
        # Simple force-directed simulation
        width = params.get("width", 600)
        height = params.get("height", 600)
        iterations = params.get("iterations", 50)
        k = params.get("k", math.sqrt((width * height) / max(n, 1)))

        # Initialize random positions
        positions = {
            node.id: [random.uniform(0, width), random.uniform(0, height)]
            for node in nodes
        }

        # Build adjacency for repulsion/attraction
        adjacency = {node.id: set() for node in nodes}
        for edge in edges:
            if edge.source in adjacency:
                adjacency[edge.source].add(edge.target)
            if edge.target in adjacency:
                adjacency[edge.target].add(edge.source)

        # Simple force simulation
        for _ in range(iterations):
            forces = {node.id: [0.0, 0.0] for node in nodes}

            # Repulsion between all pairs
            node_list = list(positions.keys())
            for i, n1 in enumerate(node_list):
                for n2 in node_list[i + 1:]:
                    dx = positions[n1][0] - positions[n2][0]
                    dy = positions[n1][1] - positions[n2][1]
                    dist = max(math.sqrt(dx * dx + dy * dy), 0.01)
                    force = k * k / dist
                    fx = (dx / dist) * force
                    fy = (dy / dist) * force
                    forces[n1][0] += fx
                    forces[n1][1] += fy
                    forces[n2][0] -= fx
                    forces[n2][1] -= fy

            # Attraction along edges
            for edge in edges:
                if edge.source in positions and edge.target in positions:
                    dx = positions[edge.target][0] - positions[edge.source][0]
                    dy = positions[edge.target][1] - positions[edge.source][1]
                    dist = max(math.sqrt(dx * dx + dy * dy), 0.01)
                    force = dist / k
                    fx = (dx / dist) * force
                    fy = (dy / dist) * force
                    forces[edge.source][0] += fx
                    forces[edge.source][1] += fy
                    forces[edge.target][0] -= fx
                    forces[edge.target][1] -= fy

            # Apply forces with cooling
            cooling = 1.0 - (_ / iterations)
            for node_id in positions:
                positions[node_id][0] += forces[node_id][0] * cooling * 0.1
                positions[node_id][1] += forces[node_id][1] * cooling * 0.1
                # Keep within bounds
                positions[node_id][0] = max(0, min(width, positions[node_id][0]))
                positions[node_id][1] = max(0, min(height, positions[node_id][1]))

        for node in nodes:
            pos = positions.get(node.id, [0, 0])
            positioned_nodes.append({
                "id": node.id,
                "label": node.label,
                "x": pos[0],
                "y": pos[1]
            })

    return positioned_nodes


def _calculate_graph_stats(
    nodes: list[VisualizationNode],
    edges: list[VisualizationEdge]
) -> GraphStatsResponse:
    """Calculate graph statistics."""
    n = len(nodes)
    m = len(edges)

    if n == 0:
        return GraphStatsResponse(
            node_count=0,
            edge_count=0,
            density=0.0,
            avg_degree=0.0,
            max_degree=0,
            min_degree=0,
            isolated_nodes=0,
            connected_components=0
        )

    # Calculate degrees
    degrees = {node.id: 0 for node in nodes}
    for edge in edges:
        degrees[edge.source] = degrees.get(edge.source, 0) + 1
        degrees[edge.target] = degrees.get(edge.target, 0) + 1

    degree_values = list(degrees.values())
    max_degree = max(degree_values) if degree_values else 0
    min_degree = min(degree_values) if degree_values else 0
    avg_degree = sum(degree_values) / n if n > 0 else 0.0
    isolated_nodes = sum(1 for d in degree_values if d == 0)

    # Calculate density
    max_edges = n * (n - 1) / 2 if n > 1 else 1
    density = m / max_edges if max_edges > 0 else 0.0

    # Calculate connected components using simple BFS
    visited = set()
    components = 0
    adjacency = {node.id: set() for node in nodes}
    for edge in edges:
        adjacency[edge.source].add(edge.target)
        adjacency[edge.target].add(edge.source)

    for node in nodes:
        if node.id not in visited:
            components += 1
            # BFS
            queue = [node.id]
            while queue:
                current = queue.pop(0)
                if current not in visited:
                    visited.add(current)
                    for neighbor in adjacency.get(current, []):
                        if neighbor not in visited:
                            queue.append(neighbor)

    return GraphStatsResponse(
        node_count=n,
        edge_count=m,
        density=round(density, 4),
        avg_degree=round(avg_degree, 2),
        max_degree=max_degree,
        min_degree=min_degree,
        isolated_nodes=isolated_nodes,
        connected_components=components
    )


def _export_to_graphml(
    nodes: list[VisualizationNode],
    edges: list[VisualizationEdge],
    include_properties: bool
) -> str:
    """Export graph to GraphML format."""
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">',
        '  <key id="label" for="node" attr.name="label" attr.type="string"/>',
        '  <key id="type" for="node" attr.name="type" attr.type="string"/>',
        '  <key id="edge_label" for="edge" attr.name="label" attr.type="string"/>',
        '  <graph id="G" edgedefault="directed">'
    ]

    for node in nodes:
        lines.append(f'    <node id="{node.id}">')
        lines.append(f'      <data key="label">{node.label}</data>')
        lines.append(f'      <data key="type">{node.type}</data>')
        lines.append('    </node>')

    for edge in edges:
        lines.append(f'    <edge id="{edge.id}" source="{edge.source}" target="{edge.target}">')
        if edge.label:
            lines.append(f'      <data key="edge_label">{edge.label}</data>')
        lines.append('    </edge>')

    lines.append('  </graph>')
    lines.append('</graphml>')

    return '\n'.join(lines)


def _export_to_dot(
    nodes: list[VisualizationNode],
    edges: list[VisualizationEdge],
    include_properties: bool
) -> str:
    """Export graph to DOT (Graphviz) format."""
    lines = ['digraph G {', '  rankdir=LR;', '  node [shape=box];', '']

    for node in nodes:
        label = node.label.replace('"', '\\"')
        lines.append(f'  "{node.id}" [label="{label}"];')

    lines.append('')

    for edge in edges:
        edge_label = f' [label="{edge.label}"]' if edge.label else ''
        lines.append(f'  "{edge.source}" -> "{edge.target}"{edge_label};')

    lines.append('}')

    return '\n'.join(lines)


# ----- Endpoints -----

@router.get(
    "/graph",
    response_model=GraphResponse,
    summary="Get full project graph data",
    description="Retrieve the complete graph data for visualization of a project.",
    responses={
        200: {"description": "Full graph data retrieved successfully"},
        404: {"description": "Project not found"},
    }
)
async def get_project_graph(
    project_safe_name: str,
    include_properties: bool = Query(
        True,
        description="Include entity properties in node data"
    ),
    include_isolated: bool = Query(
        True,
        description="Include nodes with no connections"
    ),
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Get the complete graph data for a project.

    Returns all entities as nodes and all relationships as edges,
    formatted for visualization libraries.

    - **project_safe_name**: The URL-safe identifier for the project
    - **include_properties**: Include detailed properties in nodes
    - **include_isolated**: Include entities with no relationships
    """
    # Verify project exists
    project = neo4j_handler.get_project(project_safe_name)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_safe_name}' not found"
        )

    try:
        # Get all entities
        entities = neo4j_handler.get_all_people(project_safe_name) or []

        # Build nodes
        nodes = []
        entity_ids = set()
        for entity in entities:
            if entity and entity.get("id"):
                entity_ids.add(entity["id"])
                nodes.append(_build_visualization_node(entity))

        # Get all relationships/tags
        edges = []
        edge_index = 0
        connected_ids = set()

        for entity in entities:
            if not entity:
                continue

            entity_id = entity.get("id")
            tags = entity.get("tags", []) or []

            for tag in tags:
                if isinstance(tag, dict):
                    target_id = tag.get("target_id") or tag.get("tagged_entity_id")
                    if target_id and target_id in entity_ids:
                        edges.append(_build_visualization_edge(
                            entity_id, target_id, tag, edge_index
                        ))
                        edge_index += 1
                        connected_ids.add(entity_id)
                        connected_ids.add(target_id)

        # Filter isolated nodes if requested
        if not include_isolated:
            nodes = [n for n in nodes if n.id in connected_ids]

        return GraphResponse(
            nodes=nodes,
            edges=edges,
            metadata={
                "node_count": len(nodes),
                "edge_count": len(edges),
                "project_safe_name": project_safe_name,
                "include_properties": include_properties,
                "include_isolated": include_isolated
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve graph data: {str(e)}"
        )


@router.get(
    "/entity/{entity_id}/neighborhood",
    response_model=NeighborhoodResponse,
    summary="Get N-hop neighborhood subgraph",
    description="Retrieve the neighborhood subgraph around a specific entity.",
    responses={
        200: {"description": "Neighborhood subgraph retrieved successfully"},
        404: {"description": "Project or entity not found"},
    }
)
async def get_entity_neighborhood(
    project_safe_name: str,
    entity_id: str,
    depth: int = Query(
        2,
        ge=1,
        le=5,
        description="Number of hops from center entity (1-5)"
    ),
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Get the N-hop neighborhood around an entity.

    Returns all entities within N relationship hops of the specified
    entity, creating an ego network centered on that entity.

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

    # Verify entity exists
    center_entity = neo4j_handler.get_person(project_safe_name, entity_id)
    if not center_entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity '{entity_id}' not found"
        )

    try:
        # Use the existing neighborhood function if available
        result = neo4j_handler.get_entity_neighborhood(project_safe_name, entity_id, depth)

        if result is None:
            # Fallback: just return the center entity
            nodes = [_build_visualization_node(center_entity)]
            return NeighborhoodResponse(
                center_entity_id=entity_id,
                depth=depth,
                nodes=nodes,
                edges=[],
                depth_map={entity_id: 0}
            )

        # Convert neighborhood result to visualization format
        nodes = []
        depth_map = {}
        entity_map = {}

        for depth_key, entities in result.get("neighborhood", {}).items():
            depth_num = int(depth_key.replace("depth_", ""))
            for entity in entities:
                if entity and entity.get("id"):
                    eid = entity["id"]
                    depth_map[eid] = depth_num
                    entity_map[eid] = entity
                    nodes.append(_build_visualization_node(entity))

        # Build edges from the result
        edges = []
        edge_index = 0
        for edge_data in result.get("edges", []):
            source = edge_data.get("source")
            target = edge_data.get("target")
            if source and target:
                edges.append(VisualizationEdge(
                    id=f"edge_{edge_index}",
                    source=source,
                    target=target,
                    type="TAGGED",
                    label=edge_data.get("label", "")
                ))
                edge_index += 1

        return NeighborhoodResponse(
            center_entity_id=entity_id,
            depth=depth,
            nodes=nodes,
            edges=edges,
            depth_map=depth_map
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve neighborhood: {str(e)}"
        )


@router.get(
    "/layout/{layout_type}",
    response_model=LayoutResponse,
    summary="Apply layout algorithm",
    description="Apply a graph layout algorithm and return positioned nodes.",
    responses={
        200: {"description": "Layout computed successfully"},
        400: {"description": "Invalid layout type"},
        404: {"description": "Project not found"},
    }
)
async def apply_layout(
    project_safe_name: str,
    layout_type: LayoutType,
    entity_ids: Optional[str] = Query(
        None,
        description="Comma-separated entity IDs to layout (None = all)"
    ),
    width: int = Query(800, ge=100, le=5000, description="Layout width"),
    height: int = Query(600, ge=100, le=5000, description="Layout height"),
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Apply a layout algorithm to compute node positions.

    Supported layouts:
    - **force_directed**: Physics-based simulation (default)
    - **hierarchical**: Top-down based on connectivity
    - **circular**: Nodes arranged in a circle
    - **grid**: Regular grid arrangement
    - **radial**: Concentric circles based on connectivity
    - **spectral**: Spectral graph theory based

    - **project_safe_name**: The URL-safe identifier for the project
    - **layout_type**: The layout algorithm to apply
    - **entity_ids**: Specific entities to layout (comma-separated)
    - **width**: Layout canvas width
    - **height**: Layout canvas height
    """
    # Verify project exists
    project = neo4j_handler.get_project(project_safe_name)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_safe_name}' not found"
        )

    try:
        # Get entities
        all_entities = neo4j_handler.get_all_people(project_safe_name) or []

        # Filter if specific IDs requested
        if entity_ids:
            requested_ids = set(eid.strip() for eid in entity_ids.split(","))
            entities = [e for e in all_entities if e and e.get("id") in requested_ids]
        else:
            entities = [e for e in all_entities if e and e.get("id")]

        # Build nodes and edges
        nodes = [_build_visualization_node(e) for e in entities]
        entity_id_set = {n.id for n in nodes}

        edges = []
        edge_index = 0
        for entity in entities:
            tags = entity.get("tags", []) or []
            for tag in tags:
                if isinstance(tag, dict):
                    target_id = tag.get("target_id") or tag.get("tagged_entity_id")
                    if target_id and target_id in entity_id_set:
                        edges.append(_build_visualization_edge(
                            entity["id"], target_id, tag, edge_index
                        ))
                        edge_index += 1

        # Apply layout
        parameters = {"width": width, "height": height}
        positioned_nodes = _apply_layout(nodes, edges, layout_type, parameters)

        # Calculate bounds
        if positioned_nodes:
            xs = [n["x"] for n in positioned_nodes]
            ys = [n["y"] for n in positioned_nodes]
            bounds = {
                "min_x": min(xs),
                "max_x": max(xs),
                "min_y": min(ys),
                "max_y": max(ys)
            }
        else:
            bounds = {"min_x": 0, "max_x": width, "min_y": 0, "max_y": height}

        return LayoutResponse(
            layout_type=layout_type.value,
            nodes=positioned_nodes,
            bounds=bounds,
            parameters=parameters
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to apply layout: {str(e)}"
        )


@router.post(
    "/export/{format}",
    summary="Export graph in specified format",
    description="Export the project graph in various formats for external tools.",
    responses={
        200: {
            "description": "Graph exported successfully",
            "content": {
                "application/json": {},
                "application/xml": {},
                "text/plain": {}
            }
        },
        400: {"description": "Invalid export format"},
        404: {"description": "Project not found"},
    }
)
async def export_graph(
    project_safe_name: str,
    format: ExportFormat,
    request: ExportRequest = None,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Export the project graph in various formats.

    Supported formats:
    - **d3**: JSON format for D3.js (nodes and links)
    - **cytoscape**: JSON format for Cytoscape.js (elements)
    - **graphml**: GraphML XML format
    - **dot**: DOT format for Graphviz

    - **project_safe_name**: The URL-safe identifier for the project
    - **format**: Export format (d3, cytoscape, graphml, dot)
    """
    # Verify project exists
    project = neo4j_handler.get_project(project_safe_name)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_safe_name}' not found"
        )

    if request is None:
        request = ExportRequest()

    try:
        # Get entities
        all_entities = neo4j_handler.get_all_people(project_safe_name) or []

        # Filter if specific IDs requested
        if request.entity_ids:
            requested_ids = set(request.entity_ids)
            entities = [e for e in all_entities if e and e.get("id") in requested_ids]
        else:
            entities = [e for e in all_entities if e and e.get("id")]

        # Build nodes and edges
        nodes = [_build_visualization_node(e) for e in entities]
        entity_id_set = {n.id for n in nodes}

        edges = []
        edge_index = 0
        for entity in entities:
            tags = entity.get("tags", []) or []
            for tag in tags:
                if isinstance(tag, dict):
                    target_id = tag.get("target_id") or tag.get("tagged_entity_id")
                    if target_id and target_id in entity_id_set:
                        edges.append(_build_visualization_edge(
                            entity["id"], target_id, tag, edge_index
                        ))
                        edge_index += 1

        # Export based on format
        if format == ExportFormat.D3:
            content = {
                "nodes": [
                    {
                        "id": n.id,
                        "label": n.label,
                        "type": n.type,
                        **(n.properties if request.include_properties else {})
                    }
                    for n in nodes
                ],
                "links": [
                    {
                        "source": e.source,
                        "target": e.target,
                        "type": e.type,
                        "label": e.label
                    }
                    for e in edges
                ]
            }
            import json
            return Response(
                content=json.dumps(content, indent=2),
                media_type="application/json",
                headers={"Content-Disposition": f'attachment; filename="{project_safe_name}_d3.json"'}
            )

        elif format == ExportFormat.CYTOSCAPE:
            content = {
                "elements": {
                    "nodes": [
                        {
                            "data": {
                                "id": n.id,
                                "label": n.label,
                                "type": n.type,
                                **(n.properties if request.include_properties else {})
                            }
                        }
                        for n in nodes
                    ],
                    "edges": [
                        {
                            "data": {
                                "id": e.id,
                                "source": e.source,
                                "target": e.target,
                                "type": e.type,
                                "label": e.label or ""
                            }
                        }
                        for e in edges
                    ]
                }
            }
            import json
            return Response(
                content=json.dumps(content, indent=2),
                media_type="application/json",
                headers={"Content-Disposition": f'attachment; filename="{project_safe_name}_cytoscape.json"'}
            )

        elif format == ExportFormat.GRAPHML:
            content = _export_to_graphml(nodes, edges, request.include_properties)
            return Response(
                content=content,
                media_type="application/xml",
                headers={"Content-Disposition": f'attachment; filename="{project_safe_name}.graphml"'}
            )

        elif format == ExportFormat.DOT:
            content = _export_to_dot(nodes, edges, request.include_properties)
            return Response(
                content=content,
                media_type="text/plain",
                headers={"Content-Disposition": f'attachment; filename="{project_safe_name}.dot"'}
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export graph: {str(e)}"
        )


@router.get(
    "/stats",
    response_model=GraphStatsResponse,
    summary="Get graph statistics",
    description="Calculate and return statistics about the project graph.",
    responses={
        200: {"description": "Graph statistics retrieved successfully"},
        404: {"description": "Project not found"},
    }
)
async def get_graph_stats(
    project_safe_name: str,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Get statistics about the project graph.

    Returns metrics including:
    - Node and edge counts
    - Graph density
    - Degree statistics (min, max, average)
    - Number of isolated nodes
    - Number of connected components

    - **project_safe_name**: The URL-safe identifier for the project
    """
    # Verify project exists
    project = neo4j_handler.get_project(project_safe_name)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_safe_name}' not found"
        )

    try:
        # Get all entities
        entities = neo4j_handler.get_all_people(project_safe_name) or []

        # Build nodes
        nodes = []
        entity_ids = set()
        for entity in entities:
            if entity and entity.get("id"):
                entity_ids.add(entity["id"])
                nodes.append(_build_visualization_node(entity))

        # Get edges
        edges = []
        edge_index = 0
        for entity in entities:
            if not entity:
                continue
            tags = entity.get("tags", []) or []
            for tag in tags:
                if isinstance(tag, dict):
                    target_id = tag.get("target_id") or tag.get("tagged_entity_id")
                    if target_id and target_id in entity_ids:
                        edges.append(_build_visualization_edge(
                            entity["id"], target_id, tag, edge_index
                        ))
                        edge_index += 1

        return _calculate_graph_stats(nodes, edges)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate graph statistics: {str(e)}"
        )


@router.get(
    "/clusters",
    response_model=ClustersVisualizationResponse,
    summary="Get cluster visualization data",
    description="Get cluster/community detection data for visualization.",
    responses={
        200: {"description": "Cluster visualization data retrieved successfully"},
        404: {"description": "Project not found"},
    }
)
async def get_clusters_visualization(
    project_safe_name: str,
    include_isolated: bool = Query(
        False,
        description="Include isolated entities as single-node clusters"
    ),
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Get cluster visualization data for a project.

    Returns detected clusters/communities in the graph with visualization
    metadata including cluster IDs, sizes, colors, and node assignments.

    - **project_safe_name**: The URL-safe identifier for the project
    - **include_isolated**: Include isolated nodes as single-node clusters
    """
    # Verify project exists
    project = neo4j_handler.get_project(project_safe_name)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_safe_name}' not found"
        )

    try:
        # Use the existing cluster detection
        cluster_result = neo4j_handler.find_clusters(project_safe_name)

        if not cluster_result:
            return ClustersVisualizationResponse(
                clusters=[],
                total_clusters=0,
                isolated_count=0,
                nodes=[],
                edges=[]
            )

        # Get all entities for node data
        entities = neo4j_handler.get_all_people(project_safe_name) or []
        entity_map = {e["id"]: e for e in entities if e and e.get("id")}
        entity_ids = set(entity_map.keys())

        # Build cluster visualizations
        clusters = []
        cluster_colors = [
            "#ff6b6b", "#4ecdc4", "#45b7d1", "#96ceb4",
            "#ffeaa7", "#dfe6e9", "#fd79a8", "#a29bfe",
            "#00b894", "#e17055", "#74b9ff", "#fdcb6e"
        ]

        node_cluster_map = {}
        for i, cluster_data in enumerate(cluster_result.get("clusters", [])):
            if not include_isolated and cluster_data.get("is_isolated", False):
                continue

            cluster_id = cluster_data.get("cluster_id", f"cluster_{i}")
            node_ids = cluster_data.get("entity_ids", [])
            size = cluster_data.get("size", len(node_ids))
            internal_edges = cluster_data.get("internal_edges", 0)

            # Assign cluster to nodes
            for nid in node_ids:
                node_cluster_map[nid] = {
                    "cluster_id": cluster_id,
                    "color": cluster_colors[i % len(cluster_colors)]
                }

            clusters.append(ClusterVisualization(
                cluster_id=cluster_id,
                size=size,
                color=cluster_colors[i % len(cluster_colors)],
                node_ids=node_ids,
                internal_edges=internal_edges,
                external_edges=0,  # Would need to calculate
                density=internal_edges / (size * (size - 1) / 2) if size > 1 else 0.0
            ))

        # Build nodes with cluster assignments
        nodes = []
        for entity_id, entity in entity_map.items():
            node = _build_visualization_node(entity)
            cluster_info = node_cluster_map.get(entity_id, {})
            node.color = cluster_info.get("color")
            node.properties["cluster_id"] = cluster_info.get("cluster_id")
            nodes.append(node)

        # Build edges
        edges = []
        edge_index = 0
        for entity in entities:
            if not entity:
                continue
            tags = entity.get("tags", []) or []
            for tag in tags:
                if isinstance(tag, dict):
                    target_id = tag.get("target_id") or tag.get("tagged_entity_id")
                    if target_id and target_id in entity_ids:
                        edges.append(_build_visualization_edge(
                            entity["id"], target_id, tag, edge_index
                        ))
                        edge_index += 1

        isolated_count = cluster_result.get("isolated_count", 0)

        return ClustersVisualizationResponse(
            clusters=clusters,
            total_clusters=len(clusters),
            isolated_count=isolated_count,
            modularity=None,  # Would need community detection algorithm
            nodes=nodes,
            edges=edges
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cluster visualization: {str(e)}"
        )
