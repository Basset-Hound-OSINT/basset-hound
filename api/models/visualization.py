"""
Pydantic models for Graph Visualization.

Provides data structures for graph layout, node/edge rendering,
and export formats compatible with various visualization libraries.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class LayoutType(str, Enum):
    """Available graph layout algorithms."""
    FORCE_DIRECTED = "force_directed"
    HIERARCHICAL = "hierarchical"
    CIRCULAR = "circular"
    GRID = "grid"
    RADIAL = "radial"
    RANDOM = "random"


class ExportFormat(str, Enum):
    """Supported graph export formats."""
    D3_JSON = "d3"
    CYTOSCAPE_JSON = "cytoscape"
    GRAPHML = "graphml"
    DOT = "dot"
    GEXF = "gexf"


class NodeStyle(BaseModel):
    """Visual styling for a graph node."""
    color: str = Field(
        default="#4a90d9",
        description="Node fill color (hex or CSS color name)"
    )
    border_color: str = Field(
        default="#2d5a8a",
        description="Node border color"
    )
    border_width: float = Field(
        default=2.0,
        ge=0,
        description="Border width in pixels"
    )
    size: float = Field(
        default=30.0,
        ge=5,
        le=200,
        description="Node diameter in pixels"
    )
    shape: str = Field(
        default="circle",
        description="Node shape (circle, square, diamond, triangle)"
    )
    opacity: float = Field(
        default=1.0,
        ge=0,
        le=1,
        description="Node opacity (0-1)"
    )
    label_visible: bool = Field(
        default=True,
        description="Whether to show node label"
    )


class EdgeStyle(BaseModel):
    """Visual styling for a graph edge."""
    color: str = Field(
        default="#999999",
        description="Edge color"
    )
    width: float = Field(
        default=2.0,
        ge=0.5,
        le=20,
        description="Edge width in pixels"
    )
    style: str = Field(
        default="solid",
        description="Edge style (solid, dashed, dotted)"
    )
    opacity: float = Field(
        default=0.8,
        ge=0,
        le=1,
        description="Edge opacity"
    )
    arrow_size: float = Field(
        default=10.0,
        ge=0,
        description="Arrow size for directed edges"
    )
    curved: bool = Field(
        default=False,
        description="Whether edge should be curved"
    )


class Position(BaseModel):
    """2D coordinate position for a node."""
    x: float = Field(..., description="X coordinate")
    y: float = Field(..., description="Y coordinate")


class VisualizationNode(BaseModel):
    """A node in the visualization graph."""
    id: str = Field(..., description="Unique node identifier")
    label: str = Field(..., description="Display label")
    entity_type: str = Field(
        default="person",
        description="Entity type (person, organization, device, etc.)"
    )
    position: Optional[Position] = Field(
        default=None,
        description="Node position (set by layout algorithm)"
    )
    style: NodeStyle = Field(
        default_factory=NodeStyle,
        description="Visual styling"
    )
    data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional node data"
    )
    centrality: Optional[float] = Field(
        default=None,
        ge=0,
        le=1,
        description="Normalized centrality score"
    )
    cluster_id: Optional[str] = Field(
        default=None,
        description="Cluster/community this node belongs to"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "entity-123",
                "label": "John Doe",
                "entity_type": "person",
                "position": {"x": 100.5, "y": 200.3},
                "style": {"color": "#4a90d9", "size": 30},
                "data": {"email": "john@example.com"},
                "centrality": 0.75
            }
        }
    )


class VisualizationEdge(BaseModel):
    """An edge in the visualization graph."""
    id: str = Field(..., description="Unique edge identifier")
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    relationship_type: str = Field(
        default="RELATED_TO",
        description="Type of relationship"
    )
    label: Optional[str] = Field(
        default=None,
        description="Optional edge label"
    )
    style: EdgeStyle = Field(
        default_factory=EdgeStyle,
        description="Visual styling"
    )
    weight: float = Field(
        default=1.0,
        ge=0,
        description="Edge weight (can affect layout)"
    )
    bidirectional: bool = Field(
        default=False,
        description="Whether relationship is bidirectional"
    )
    data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional edge data"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "edge-123",
                "source": "entity-1",
                "target": "entity-2",
                "relationship_type": "KNOWS",
                "weight": 0.8,
                "style": {"color": "#666666", "width": 2}
            }
        }
    )


class GraphData(BaseModel):
    """Complete graph data for visualization."""
    nodes: List[VisualizationNode] = Field(
        default_factory=list,
        description="List of nodes"
    )
    edges: List[VisualizationEdge] = Field(
        default_factory=list,
        description="List of edges"
    )
    layout: Optional[LayoutType] = Field(
        default=None,
        description="Layout algorithm applied"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Graph metadata"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "nodes": [
                    {"id": "entity-1", "label": "Alice", "entity_type": "person"},
                    {"id": "entity-2", "label": "Bob", "entity_type": "person"}
                ],
                "edges": [
                    {"id": "edge-1", "source": "entity-1", "target": "entity-2", "relationship_type": "KNOWS"}
                ],
                "layout": "force_directed",
                "metadata": {"node_count": 2, "edge_count": 1}
            }
        }
    )


class GraphStats(BaseModel):
    """Statistics about a graph."""
    node_count: int = Field(..., ge=0, description="Number of nodes")
    edge_count: int = Field(..., ge=0, description="Number of edges")
    density: float = Field(
        ...,
        ge=0,
        le=1,
        description="Graph density (edges / max possible edges)"
    )
    connected_components: int = Field(
        ...,
        ge=0,
        description="Number of connected components"
    )
    avg_degree: float = Field(
        ...,
        ge=0,
        description="Average node degree"
    )
    max_degree: int = Field(
        ...,
        ge=0,
        description="Maximum node degree"
    )
    entity_type_counts: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of nodes by entity type"
    )
    relationship_type_counts: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of edges by relationship type"
    )


class LayoutRequest(BaseModel):
    """Request to apply a layout algorithm."""
    layout_type: LayoutType = Field(
        default=LayoutType.FORCE_DIRECTED,
        description="Layout algorithm to apply"
    )
    width: float = Field(
        default=1000.0,
        ge=100,
        le=10000,
        description="Canvas width"
    )
    height: float = Field(
        default=800.0,
        ge=100,
        le=10000,
        description="Canvas height"
    )
    iterations: int = Field(
        default=100,
        ge=10,
        le=1000,
        description="Number of layout iterations (force-directed)"
    )
    node_spacing: float = Field(
        default=50.0,
        ge=10,
        le=500,
        description="Minimum spacing between nodes"
    )
    center_x: Optional[float] = Field(
        default=None,
        description="Center X for radial/circular layout"
    )
    center_y: Optional[float] = Field(
        default=None,
        description="Center Y for radial/circular layout"
    )


class SubgraphRequest(BaseModel):
    """Request to extract a subgraph."""
    center_entity_id: str = Field(
        ...,
        description="Center entity for neighborhood extraction"
    )
    max_hops: int = Field(
        default=2,
        ge=1,
        le=5,
        description="Maximum hops from center"
    )
    max_nodes: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum nodes to include"
    )
    relationship_types: Optional[List[str]] = Field(
        default=None,
        description="Filter by relationship types (None = all)"
    )
    entity_types: Optional[List[str]] = Field(
        default=None,
        description="Filter by entity types (None = all)"
    )
    include_metadata: bool = Field(
        default=True,
        description="Include full entity/relationship metadata"
    )


class ExportRequest(BaseModel):
    """Request to export graph data."""
    format: ExportFormat = Field(
        ...,
        description="Export format"
    )
    include_positions: bool = Field(
        default=True,
        description="Include node positions in export"
    )
    include_styles: bool = Field(
        default=True,
        description="Include visual styling in export"
    )
    pretty_print: bool = Field(
        default=False,
        description="Pretty-print JSON output"
    )


class ExportResponse(BaseModel):
    """Response containing exported graph data."""
    format: ExportFormat = Field(..., description="Export format used")
    content_type: str = Field(..., description="MIME content type")
    data: str = Field(..., description="Exported data as string")
    node_count: int = Field(..., ge=0, description="Number of nodes exported")
    edge_count: int = Field(..., ge=0, description="Number of edges exported")


class ClusterInfo(BaseModel):
    """Information about a detected cluster."""
    cluster_id: str = Field(..., description="Cluster identifier")
    node_count: int = Field(..., ge=1, description="Number of nodes in cluster")
    node_ids: List[str] = Field(..., description="IDs of nodes in cluster")
    center_node_id: Optional[str] = Field(
        default=None,
        description="ID of the most central node"
    )
    density: float = Field(
        default=0.0,
        ge=0,
        le=1,
        description="Internal cluster density"
    )


class ClusterResponse(BaseModel):
    """Response containing cluster analysis results."""
    cluster_count: int = Field(..., ge=0, description="Number of clusters found")
    clusters: List[ClusterInfo] = Field(
        default_factory=list,
        description="List of clusters"
    )
    modularity: Optional[float] = Field(
        default=None,
        description="Modularity score of clustering"
    )
    isolated_nodes: int = Field(
        default=0,
        ge=0,
        description="Number of isolated nodes"
    )


# Entity type to color mapping for visualization
ENTITY_TYPE_COLORS = {
    "person": "#4a90d9",       # Blue
    "organization": "#50c878",  # Green
    "device": "#ff7f50",       # Coral
    "location": "#dda0dd",     # Plum
    "event": "#ffd700",        # Gold
    "document": "#d3d3d3",     # Light gray
    "unknown": "#808080",      # Gray
}

# Relationship type to color mapping
RELATIONSHIP_TYPE_COLORS = {
    "RELATED_TO": "#999999",
    "KNOWS": "#4a90d9",
    "WORKS_WITH": "#50c878",
    "FAMILY": "#ff69b4",
    "FRIEND": "#87ceeb",
    "BUSINESS_PARTNER": "#32cd32",
    "ASSOCIATED_WITH": "#ffa500",
    "SUSPECTED_ASSOCIATE": "#ff4500",
    "ALIAS_OF": "#9370db",
}


def get_node_color(entity_type: str) -> str:
    """Get the default color for an entity type."""
    return ENTITY_TYPE_COLORS.get(entity_type.lower(), ENTITY_TYPE_COLORS["unknown"])


def get_edge_color(relationship_type: str) -> str:
    """Get the default color for a relationship type."""
    return RELATIONSHIP_TYPE_COLORS.get(relationship_type.upper(), RELATIONSHIP_TYPE_COLORS["RELATED_TO"])
