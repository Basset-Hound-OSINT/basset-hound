"""
Graph Visualization Service for Basset Hound OSINT Platform.

This module provides advanced graph visualization capabilities including:
- Multiple layout algorithms (force-directed, hierarchical, circular)
- Export formats (D3.js, Cytoscape.js, GraphML, DOT)
- Subgraph extraction with filtering
- Visual metadata computation (colors, sizes, weights)

All layout computations are done server-side, returning node positions
that can be rendered by any frontend library.
"""

import json
import logging
import math
import random
import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from pydantic import BaseModel, Field, ConfigDict, field_validator

from api.models.entity_types import EntityType
from api.models.relationship import (
    RelationshipType,
    ConfidenceLevel,
    get_relationship_type_categories,
)

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS AND CONSTANTS
# =============================================================================

class LayoutAlgorithm(str, Enum):
    """Available graph layout algorithms."""
    FORCE_DIRECTED = "force_directed"
    HIERARCHICAL = "hierarchical"
    CIRCULAR = "circular"
    RADIAL = "radial"
    GRID = "grid"


class ExportFormat(str, Enum):
    """Supported graph export formats."""
    D3_JSON = "d3_json"
    CYTOSCAPE_JSON = "cytoscape_json"
    GRAPHML = "graphml"
    DOT = "dot"


class NodePriority(str, Enum):
    """Node prioritization strategies for limiting graph size."""
    CENTRALITY = "centrality"
    RECENCY = "recency"
    CONNECTION_COUNT = "connection_count"
    CUSTOM_WEIGHT = "custom_weight"


# Default color schemes
ENTITY_TYPE_COLORS: Dict[str, str] = {
    EntityType.PERSON.value: "#3498db",      # Blue
    EntityType.ORGANIZATION.value: "#2ecc71", # Green
    EntityType.DEVICE.value: "#e74c3c",       # Red
    EntityType.LOCATION.value: "#9b59b6",     # Purple
    EntityType.EVENT.value: "#f39c12",        # Orange
    EntityType.DOCUMENT.value: "#1abc9c",     # Teal
    "Person": "#3498db",  # Backwards compatibility
    "default": "#95a5a6",  # Gray
}

RELATIONSHIP_TYPE_COLORS: Dict[str, str] = {
    # Professional
    "WORKS_WITH": "#27ae60",
    "BUSINESS_PARTNER": "#2ecc71",
    "REPORTS_TO": "#16a085",
    "MANAGES": "#1abc9c",
    "COLLEAGUE": "#3498db",
    # Family
    "FAMILY": "#e74c3c",
    "MARRIED_TO": "#c0392b",
    "PARENT_OF": "#d35400",
    "CHILD_OF": "#e67e22",
    "SIBLING_OF": "#f39c12",
    "SPOUSE": "#c0392b",
    # Social
    "FRIEND": "#9b59b6",
    "ACQUAINTANCE": "#8e44ad",
    "NEIGHBOR": "#2980b9",
    # Investigative
    "ASSOCIATED_WITH": "#7f8c8d",
    "SUSPECTED_ASSOCIATE": "#c0392b",
    "ALIAS_OF": "#e74c3c",
    # Generic
    "RELATED_TO": "#95a5a6",
    "KNOWS": "#bdc3c7",
    "default": "#95a5a6",
}

CONFIDENCE_COLORS: Dict[str, str] = {
    ConfidenceLevel.CONFIRMED.value: "#27ae60",
    ConfidenceLevel.HIGH.value: "#2ecc71",
    ConfidenceLevel.MEDIUM.value: "#f39c12",
    ConfidenceLevel.LOW.value: "#e67e22",
    ConfidenceLevel.UNVERIFIED.value: "#95a5a6",
    "default": "#95a5a6",
}


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class Position(BaseModel):
    """2D position for a node."""
    x: float = Field(..., description="X coordinate")
    y: float = Field(..., description="Y coordinate")

    model_config = ConfigDict(frozen=True)


class NodeVisualProperties(BaseModel):
    """Visual properties for a graph node."""
    color: str = Field(default="#95a5a6", description="Node fill color")
    size: float = Field(default=20.0, ge=5.0, le=100.0, description="Node radius/size")
    border_color: Optional[str] = Field(default=None, description="Node border color")
    border_width: float = Field(default=1.0, ge=0.0, description="Node border width")
    opacity: float = Field(default=1.0, ge=0.0, le=1.0, description="Node opacity")
    shape: str = Field(default="circle", description="Node shape (circle, square, etc.)")


class EdgeVisualProperties(BaseModel):
    """Visual properties for a graph edge."""
    color: str = Field(default="#95a5a6", description="Edge stroke color")
    width: float = Field(default=1.0, ge=0.5, le=10.0, description="Edge stroke width")
    opacity: float = Field(default=0.8, ge=0.0, le=1.0, description="Edge opacity")
    style: str = Field(default="solid", description="Edge style (solid, dashed, dotted)")
    arrow: bool = Field(default=True, description="Whether to show arrow")


class VisualizationNode(BaseModel):
    """A node in the visualization graph."""
    id: str = Field(..., description="Unique node identifier")
    label: str = Field(..., description="Display label")
    entity_type: str = Field(default="Person", description="Entity type")
    position: Position = Field(..., description="Node position")
    visual: NodeVisualProperties = Field(
        default_factory=NodeVisualProperties,
        description="Visual properties"
    )
    properties: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional node properties"
    )
    centrality: float = Field(default=0.0, ge=0.0, le=1.0, description="Node centrality score")
    degree: int = Field(default=0, ge=0, description="Node degree (connection count)")


class VisualizationEdge(BaseModel):
    """An edge in the visualization graph."""
    id: str = Field(..., description="Unique edge identifier")
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    relationship_type: str = Field(default="RELATED_TO", description="Relationship type")
    visual: EdgeVisualProperties = Field(
        default_factory=EdgeVisualProperties,
        description="Visual properties"
    )
    properties: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional edge properties"
    )
    weight: float = Field(default=1.0, ge=0.0, description="Edge weight (e.g., confidence)")


class VisualizationGraph(BaseModel):
    """Complete visualization graph with nodes, edges, and metadata."""
    nodes: List[VisualizationNode] = Field(default_factory=list, description="Graph nodes")
    edges: List[VisualizationEdge] = Field(default_factory=list, description="Graph edges")
    layout: LayoutAlgorithm = Field(
        default=LayoutAlgorithm.FORCE_DIRECTED,
        description="Layout algorithm used"
    )
    bounds: Dict[str, float] = Field(
        default_factory=lambda: {"min_x": 0, "max_x": 1000, "min_y": 0, "max_y": 1000},
        description="Graph bounding box"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional graph metadata"
    )


class LayoutOptions(BaseModel):
    """Options for graph layout computation."""
    algorithm: LayoutAlgorithm = Field(
        default=LayoutAlgorithm.FORCE_DIRECTED,
        description="Layout algorithm to use"
    )
    width: float = Field(default=1000.0, gt=0, description="Canvas width")
    height: float = Field(default=800.0, gt=0, description="Canvas height")
    padding: float = Field(default=50.0, ge=0, description="Padding from edges")
    iterations: int = Field(
        default=100,
        ge=10,
        le=1000,
        description="Number of iterations for iterative algorithms"
    )
    # Force-directed specific
    repulsion_strength: float = Field(
        default=1000.0,
        gt=0,
        description="Node repulsion strength"
    )
    attraction_strength: float = Field(
        default=0.01,
        gt=0,
        description="Edge attraction strength"
    )
    damping: float = Field(
        default=0.9,
        gt=0,
        lt=1,
        description="Velocity damping factor"
    )
    # Hierarchical specific
    level_separation: float = Field(
        default=100.0,
        gt=0,
        description="Vertical spacing between levels"
    )
    node_separation: float = Field(
        default=50.0,
        gt=0,
        description="Horizontal spacing between nodes"
    )
    direction: str = Field(
        default="top_to_bottom",
        description="Hierarchy direction: top_to_bottom, bottom_to_top, left_to_right, right_to_left"
    )
    root_node: Optional[str] = Field(
        default=None,
        description="Root node ID for hierarchical layout"
    )
    # Circular specific
    center_node: Optional[str] = Field(
        default=None,
        description="Center node ID for circular/radial layouts"
    )
    start_angle: float = Field(
        default=0.0,
        description="Starting angle in radians"
    )


class SubgraphExtractionOptions(BaseModel):
    """Options for extracting a subgraph."""
    center_entity_id: str = Field(..., description="Central entity ID")
    max_hops: int = Field(default=2, ge=1, le=10, description="Maximum hops from center")
    max_nodes: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of nodes to include"
    )
    relationship_types: Optional[List[str]] = Field(
        default=None,
        description="Filter by relationship types (None = all)"
    )
    entity_types: Optional[List[str]] = Field(
        default=None,
        description="Filter by entity types (None = all)"
    )
    prioritization: NodePriority = Field(
        default=NodePriority.CENTRALITY,
        description="How to prioritize nodes when limiting"
    )
    include_orphans: bool = Field(
        default=False,
        description="Include nodes with no connections"
    )


class ExportOptions(BaseModel):
    """Options for graph export."""
    format: ExportFormat = Field(..., description="Export format")
    include_positions: bool = Field(
        default=True,
        description="Include computed positions"
    )
    include_visual_properties: bool = Field(
        default=True,
        description="Include visual styling"
    )
    pretty_print: bool = Field(default=True, description="Pretty-print output")


# =============================================================================
# LAYOUT ALGORITHMS
# =============================================================================

class LayoutEngine:
    """Engine for computing graph layouts."""

    def __init__(self):
        self._random = random.Random(42)  # Deterministic for testing

    def _to_dict(self, obj: Any) -> Dict[str, Any]:
        """Convert object to dict if it's a Pydantic model, otherwise return as-is."""
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        elif hasattr(obj, "dict"):
            return obj.dict()
        elif isinstance(obj, dict):
            return obj
        else:
            # Try to access attributes directly for duck typing
            return {"id": getattr(obj, "id", None), "source": getattr(obj, "source", None), "target": getattr(obj, "target", None)}

    def _get_id(self, node: Any) -> str:
        """Get node ID from either dict or Pydantic model."""
        if isinstance(node, dict):
            return node["id"]
        return node.id

    def _get_edge_endpoints(self, edge: Any) -> tuple:
        """Get source and target from either dict or Pydantic model."""
        if isinstance(edge, dict):
            return edge["source"], edge["target"]
        return edge.source, edge.target

    def compute_layout(
        self,
        nodes: List[Any],
        edges: List[Any],
        options: LayoutOptions
    ) -> List[Any]:
        """
        Compute positions for all nodes based on the selected algorithm.

        Args:
            nodes: List of node objects (dicts or Pydantic models) with 'id' attribute
            edges: List of edge objects (dicts or Pydantic models) with 'source' and 'target' attributes
            options: Layout configuration options

        Returns:
            List of nodes with updated positions
        """
        if not nodes:
            return []

        # Convert inputs to dicts for internal processing
        node_dicts = [self._to_dict(n) for n in nodes]
        edge_dicts = [self._to_dict(e) for e in edges]

        # Get the appropriate layout algorithm
        algorithm = options.algorithm
        if algorithm == LayoutAlgorithm.FORCE_DIRECTED:
            positions = self._force_directed_layout_internal(node_dicts, edge_dicts, options)
        elif algorithm == LayoutAlgorithm.HIERARCHICAL:
            positions = self._hierarchical_layout(node_dicts, edge_dicts, options)
        elif algorithm == LayoutAlgorithm.CIRCULAR:
            positions = self._circular_layout(node_dicts, edge_dicts, options)
        elif algorithm == LayoutAlgorithm.RADIAL:
            positions = self._radial_layout(node_dicts, edge_dicts, options)
        elif algorithm == LayoutAlgorithm.GRID:
            positions = self._grid_layout(node_dicts, edge_dicts, options)
        else:
            positions = self._force_directed_layout_internal(node_dicts, edge_dicts, options)

        # Update original nodes with computed positions
        result = []
        for node in nodes:
            node_id = self._get_id(node)
            pos = positions.get(node_id, Position(x=0, y=0))
            if hasattr(node, "model_copy"):
                # Pydantic v2
                updated = node.model_copy(update={"position": pos})
            elif hasattr(node, "copy"):
                # Pydantic v1
                updated = node.copy(update={"position": pos})
            elif isinstance(node, dict):
                node["position"] = pos
                updated = node
            else:
                # Fallback - try to set attribute
                node.position = pos
                updated = node
            result.append(updated)
        return result

    def _force_directed_layout_internal(
        self,
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]],
        options: LayoutOptions
    ) -> Dict[str, Position]:
        """
        Compute force-directed layout using Fruchterman-Reingold algorithm.

        This algorithm treats edges as springs that pull connected nodes together
        and applies repulsive forces between all nodes to prevent overlap.

        Returns dict mapping node IDs to Position objects.
        """
        if not nodes:
            return {}

        # Initialize random positions
        positions: Dict[str, Tuple[float, float]] = {}
        velocities: Dict[str, Tuple[float, float]] = {}

        width = options.width - 2 * options.padding
        height = options.height - 2 * options.padding
        center_x = options.width / 2
        center_y = options.height / 2

        for node in nodes:
            node_id = node["id"]
            # Random initial position in the center area
            x = center_x + (self._random.random() - 0.5) * width * 0.8
            y = center_y + (self._random.random() - 0.5) * height * 0.8
            positions[node_id] = (x, y)
            velocities[node_id] = (0.0, 0.0)

        # Build adjacency for quick lookup
        adjacency: Dict[str, Set[str]] = defaultdict(set)
        for edge in edges:
            source = edge["source"]
            target = edge["target"]
            adjacency[source].add(target)
            adjacency[target].add(source)

        # Optimal distance (Fruchterman-Reingold)
        area = width * height
        k = math.sqrt(area / max(len(nodes), 1))

        # Iterative optimization
        temperature = width / 10
        cooling_rate = temperature / options.iterations

        for iteration in range(options.iterations):
            # Calculate repulsive forces between all node pairs
            forces: Dict[str, Tuple[float, float]] = {n["id"]: (0.0, 0.0) for n in nodes}

            for i, node1 in enumerate(nodes):
                for node2 in nodes[i + 1:]:
                    id1, id2 = node1["id"], node2["id"]
                    x1, y1 = positions[id1]
                    x2, y2 = positions[id2]

                    dx = x1 - x2
                    dy = y1 - y2
                    dist = math.sqrt(dx * dx + dy * dy) + 0.01

                    # Repulsive force (Coulomb's law style)
                    repulsion = (options.repulsion_strength * k * k) / dist

                    fx = (dx / dist) * repulsion
                    fy = (dy / dist) * repulsion

                    forces[id1] = (forces[id1][0] + fx, forces[id1][1] + fy)
                    forces[id2] = (forces[id2][0] - fx, forces[id2][1] - fy)

            # Calculate attractive forces along edges
            for edge in edges:
                source, target = edge["source"], edge["target"]
                if source not in positions or target not in positions:
                    continue

                x1, y1 = positions[source]
                x2, y2 = positions[target]

                dx = x2 - x1
                dy = y2 - y1
                dist = math.sqrt(dx * dx + dy * dy) + 0.01

                # Attractive force (Hooke's law style)
                attraction = options.attraction_strength * dist * dist / k

                fx = (dx / dist) * attraction
                fy = (dy / dist) * attraction

                forces[source] = (forces[source][0] + fx, forces[source][1] + fy)
                forces[target] = (forces[target][0] - fx, forces[target][1] - fy)

            # Update positions with velocity damping
            for node in nodes:
                node_id = node["id"]
                fx, fy = forces[node_id]
                vx, vy = velocities[node_id]

                # Update velocity with force and damping
                vx = (vx + fx) * options.damping
                vy = (vy + fy) * options.damping

                # Limit velocity by temperature
                speed = math.sqrt(vx * vx + vy * vy)
                if speed > temperature:
                    vx = (vx / speed) * temperature
                    vy = (vy / speed) * temperature

                velocities[node_id] = (vx, vy)

                # Update position
                x, y = positions[node_id]
                x = max(options.padding, min(options.width - options.padding, x + vx))
                y = max(options.padding, min(options.height - options.padding, y + vy))
                positions[node_id] = (x, y)

            # Cool down
            temperature = max(temperature - cooling_rate, 1.0)

        return {node_id: Position(x=x, y=y) for node_id, (x, y) in positions.items()}

    def _hierarchical_layout(
        self,
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]],
        options: LayoutOptions
    ) -> Dict[str, Position]:
        """
        Compute hierarchical layout for tree-like structures.

        Assigns nodes to levels based on distance from root node,
        then arranges nodes horizontally within each level.
        """
        if not nodes:
            return {}

        node_ids = {n["id"] for n in nodes}

        # Build adjacency
        children: Dict[str, List[str]] = defaultdict(list)
        parents: Dict[str, Set[str]] = defaultdict(set)

        for edge in edges:
            source, target = edge["source"], edge["target"]
            if source in node_ids and target in node_ids:
                children[source].append(target)
                parents[target].add(source)

        # Find root node (specified or node with no parents)
        root = options.root_node
        if not root or root not in node_ids:
            # Find nodes with no parents (potential roots)
            candidates = [n["id"] for n in nodes if not parents[n["id"]]]
            if candidates:
                root = candidates[0]
            else:
                root = nodes[0]["id"]

        # Assign levels using BFS from root
        levels: Dict[str, int] = {root: 0}
        queue = [root]
        while queue:
            current = queue.pop(0)
            current_level = levels[current]
            for child in children[current]:
                if child not in levels:
                    levels[child] = current_level + 1
                    queue.append(child)

        # Handle disconnected nodes
        for node in nodes:
            if node["id"] not in levels:
                levels[node["id"]] = max(levels.values(), default=0) + 1

        # Group nodes by level
        level_nodes: Dict[int, List[str]] = defaultdict(list)
        for node_id, level in levels.items():
            level_nodes[level].append(node_id)

        # Calculate positions
        positions: Dict[str, Position] = {}
        max_level = max(level_nodes.keys(), default=0)

        for level, node_list in level_nodes.items():
            num_nodes = len(node_list)
            total_width = options.width - 2 * options.padding

            # Position based on direction
            if options.direction in ("top_to_bottom", "bottom_to_top"):
                y = options.padding + level * options.level_separation
                if options.direction == "bottom_to_top":
                    y = options.height - y

                for i, node_id in enumerate(node_list):
                    if num_nodes == 1:
                        x = options.width / 2
                    else:
                        x = options.padding + (i + 0.5) * total_width / num_nodes
                    positions[node_id] = Position(x=x, y=y)

            else:  # left_to_right or right_to_left
                x = options.padding + level * options.level_separation
                if options.direction == "right_to_left":
                    x = options.width - x

                total_height = options.height - 2 * options.padding
                for i, node_id in enumerate(node_list):
                    if num_nodes == 1:
                        y = options.height / 2
                    else:
                        y = options.padding + (i + 0.5) * total_height / num_nodes
                    positions[node_id] = Position(x=x, y=y)

        return positions

    def _circular_layout(
        self,
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]],
        options: LayoutOptions
    ) -> Dict[str, Position]:
        """
        Arrange nodes in a circle with optional central node.

        If a center_node is specified, it is placed at the center
        and other nodes are arranged around it.
        """
        if not nodes:
            return {}

        center_x = options.width / 2
        center_y = options.height / 2
        radius = min(
            options.width - 2 * options.padding,
            options.height - 2 * options.padding
        ) / 2 * 0.9

        positions: Dict[str, Position] = {}

        # Handle center node if specified
        center_node = options.center_node
        circle_nodes = [n for n in nodes if n["id"] != center_node]

        if center_node and any(n["id"] == center_node for n in nodes):
            positions[center_node] = Position(x=center_x, y=center_y)

        # Arrange remaining nodes in a circle
        num_nodes = len(circle_nodes)
        if num_nodes == 0:
            return positions

        angle_step = 2 * math.pi / num_nodes
        start_angle = options.start_angle

        for i, node in enumerate(circle_nodes):
            angle = start_angle + i * angle_step
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            positions[node["id"]] = Position(x=x, y=y)

        return positions

    def _radial_layout(
        self,
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]],
        options: LayoutOptions
    ) -> Dict[str, Position]:
        """
        Arrange nodes in concentric circles based on distance from center node.

        Similar to hierarchical but uses radial arrangement instead of levels.
        """
        if not nodes:
            return {}

        node_ids = {n["id"] for n in nodes}
        center_x = options.width / 2
        center_y = options.height / 2

        # Build adjacency
        adjacency: Dict[str, Set[str]] = defaultdict(set)
        for edge in edges:
            source, target = edge["source"], edge["target"]
            if source in node_ids and target in node_ids:
                adjacency[source].add(target)
                adjacency[target].add(source)

        # Find center node
        center_node = options.center_node
        if not center_node or center_node not in node_ids:
            # Use node with highest degree as center
            degrees = {n["id"]: len(adjacency[n["id"]]) for n in nodes}
            center_node = max(degrees, key=degrees.get) if degrees else nodes[0]["id"]

        # Calculate distances from center (BFS)
        distances: Dict[str, int] = {center_node: 0}
        queue = [center_node]
        while queue:
            current = queue.pop(0)
            for neighbor in adjacency[current]:
                if neighbor not in distances:
                    distances[neighbor] = distances[current] + 1
                    queue.append(neighbor)

        # Handle disconnected nodes
        max_dist = max(distances.values(), default=0)
        for node in nodes:
            if node["id"] not in distances:
                distances[node["id"]] = max_dist + 1
                max_dist += 1

        # Group by distance
        rings: Dict[int, List[str]] = defaultdict(list)
        for node_id, dist in distances.items():
            rings[dist].append(node_id)

        # Calculate positions
        positions: Dict[str, Position] = {}
        max_radius = min(
            options.width - 2 * options.padding,
            options.height - 2 * options.padding
        ) / 2 * 0.9

        positions[center_node] = Position(x=center_x, y=center_y)

        for ring_num in range(1, max(rings.keys(), default=0) + 1):
            ring_nodes = rings[ring_num]
            if not ring_nodes:
                continue

            radius = ring_num * max_radius / max(distances.values(), default=1)
            angle_step = 2 * math.pi / len(ring_nodes)

            for i, node_id in enumerate(ring_nodes):
                angle = options.start_angle + i * angle_step
                x = center_x + radius * math.cos(angle)
                y = center_y + radius * math.sin(angle)
                positions[node_id] = Position(x=x, y=y)

        return positions

    def _grid_layout(
        self,
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]],
        options: LayoutOptions
    ) -> Dict[str, Position]:
        """
        Arrange nodes in a simple grid pattern.

        Useful for quick visualization or when relationship structure
        is not the primary concern.
        """
        if not nodes:
            return {}

        num_nodes = len(nodes)
        cols = math.ceil(math.sqrt(num_nodes))
        rows = math.ceil(num_nodes / cols)

        cell_width = (options.width - 2 * options.padding) / max(cols, 1)
        cell_height = (options.height - 2 * options.padding) / max(rows, 1)

        positions: Dict[str, Position] = {}

        for i, node in enumerate(nodes):
            row = i // cols
            col = i % cols
            x = options.padding + col * cell_width + cell_width / 2
            y = options.padding + row * cell_height + cell_height / 2
            positions[node["id"]] = Position(x=x, y=y)

        return positions


# =============================================================================
# GRAPH METRICS AND ANALYSIS
# =============================================================================

class GraphMetrics:
    """Compute graph metrics for visualization enhancement."""

    @staticmethod
    def compute_degree_centrality(
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """
        Compute degree centrality for each node.

        Degree centrality is the fraction of nodes a given node is connected to.
        """
        if not nodes:
            return {}

        node_ids = {n["id"] for n in nodes}
        degrees: Dict[str, int] = {n["id"]: 0 for n in nodes}

        for edge in edges:
            source, target = edge["source"], edge["target"]
            if source in node_ids:
                degrees[source] = degrees.get(source, 0) + 1
            if target in node_ids:
                degrees[target] = degrees.get(target, 0) + 1

        max_degree = max(degrees.values()) if degrees else 1
        if max_degree == 0:
            max_degree = 1

        return {
            node_id: degree / max_degree
            for node_id, degree in degrees.items()
        }

    @staticmethod
    def compute_betweenness_centrality(
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """
        Compute approximate betweenness centrality.

        Betweenness centrality measures how often a node lies on shortest paths
        between other nodes.
        """
        if len(nodes) < 3:
            return {n["id"]: 0.0 for n in nodes}

        node_ids = {n["id"] for n in nodes}

        # Build adjacency list
        adjacency: Dict[str, Set[str]] = defaultdict(set)
        for edge in edges:
            source, target = edge["source"], edge["target"]
            if source in node_ids and target in node_ids:
                adjacency[source].add(target)
                adjacency[target].add(source)

        betweenness: Dict[str, float] = {n["id"]: 0.0 for n in nodes}

        # For each node, do BFS and count paths
        for source_node in nodes:
            source = source_node["id"]

            # BFS from source
            distances: Dict[str, int] = {source: 0}
            paths: Dict[str, int] = {source: 1}
            queue = [source]
            order = []

            while queue:
                current = queue.pop(0)
                order.append(current)

                for neighbor in adjacency[current]:
                    if neighbor not in distances:
                        distances[neighbor] = distances[current] + 1
                        queue.append(neighbor)
                        paths[neighbor] = 0

                    if distances[neighbor] == distances[current] + 1:
                        paths[neighbor] += paths[current]

            # Accumulate betweenness
            delta: Dict[str, float] = {n["id"]: 0.0 for n in nodes}
            for node in reversed(order[1:]):  # Skip source
                for neighbor in adjacency[node]:
                    if distances.get(neighbor, -1) == distances.get(node, 0) - 1:
                        delta[neighbor] += (paths[neighbor] / max(paths[node], 1)) * (1 + delta[node])
                betweenness[node] += delta[node]

        # Normalize
        max_betweenness = max(betweenness.values()) if betweenness else 1
        if max_betweenness == 0:
            max_betweenness = 1

        return {
            node_id: value / max_betweenness
            for node_id, value in betweenness.items()
        }

    @staticmethod
    def compute_node_degrees(
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """Compute degree (connection count) for each node."""
        degrees: Dict[str, int] = {n["id"]: 0 for n in nodes}

        for edge in edges:
            source, target = edge["source"], edge["target"]
            if source in degrees:
                degrees[source] += 1
            if target in degrees:
                degrees[target] += 1

        return degrees


# =============================================================================
# EXPORT FORMATTERS
# =============================================================================

class GraphExporter:
    """Export graphs to various formats."""

    @staticmethod
    def to_d3_json(
        graph: VisualizationGraph,
        options: ExportOptions
    ) -> Dict[str, Any]:
        """
        Export to D3.js force-simulation compatible JSON.

        Returns:
            Dictionary with 'nodes' and 'links' arrays in D3 format.
        """
        nodes = []
        for node in graph.nodes:
            node_data = {
                "id": node.id,
                "label": node.label,
                "group": node.entity_type,
            }

            if options.include_positions:
                node_data["x"] = node.position.x
                node_data["y"] = node.position.y
                node_data["fx"] = node.position.x  # Fixed position
                node_data["fy"] = node.position.y

            if options.include_visual_properties:
                node_data["color"] = node.visual.color
                node_data["size"] = node.visual.size
                node_data["opacity"] = node.visual.opacity

            node_data["centrality"] = node.centrality
            node_data["degree"] = node.degree
            node_data.update(node.properties)
            nodes.append(node_data)

        links = []
        for edge in graph.edges:
            link_data = {
                "id": edge.id,
                "source": edge.source,
                "target": edge.target,
                "type": edge.relationship_type,
                "value": edge.weight,
            }

            if options.include_visual_properties:
                link_data["color"] = edge.visual.color
                link_data["width"] = edge.visual.width
                link_data["opacity"] = edge.visual.opacity
                link_data["style"] = edge.visual.style

            link_data.update(edge.properties)
            links.append(link_data)

        result = {
            "nodes": nodes,
            "links": links,
            "layout": graph.layout.value,
            "bounds": graph.bounds,
            "metadata": graph.metadata,
        }

        return result

    @staticmethod
    def to_cytoscape_json(
        graph: VisualizationGraph,
        options: ExportOptions
    ) -> Dict[str, Any]:
        """
        Export to Cytoscape.js compatible JSON.

        Returns:
            Dictionary with 'elements' containing 'nodes' and 'edges' arrays.
        """
        elements = {
            "nodes": [],
            "edges": []
        }

        for node in graph.nodes:
            node_data = {
                "data": {
                    "id": node.id,
                    "label": node.label,
                    "type": node.entity_type,
                    "centrality": node.centrality,
                    "degree": node.degree,
                    **node.properties
                }
            }

            if options.include_positions:
                node_data["position"] = {
                    "x": node.position.x,
                    "y": node.position.y
                }

            if options.include_visual_properties:
                node_data["data"]["color"] = node.visual.color
                node_data["data"]["size"] = node.visual.size
                node_data["data"]["borderColor"] = node.visual.border_color
                node_data["data"]["opacity"] = node.visual.opacity
                node_data["data"]["shape"] = node.visual.shape

            elements["nodes"].append(node_data)

        for edge in graph.edges:
            edge_data = {
                "data": {
                    "id": edge.id,
                    "source": edge.source,
                    "target": edge.target,
                    "label": edge.relationship_type,
                    "type": edge.relationship_type,
                    "weight": edge.weight,
                    **edge.properties
                }
            }

            if options.include_visual_properties:
                edge_data["data"]["lineColor"] = edge.visual.color
                edge_data["data"]["width"] = edge.visual.width
                edge_data["data"]["opacity"] = edge.visual.opacity
                edge_data["data"]["lineStyle"] = edge.visual.style

            elements["edges"].append(edge_data)

        return {
            "elements": elements,
            "layout": {"name": "preset"},  # Use precomputed positions
            "bounds": graph.bounds,
            "metadata": graph.metadata
        }

    @staticmethod
    def to_graphml(
        graph: VisualizationGraph,
        options: ExportOptions
    ) -> str:
        """
        Export to GraphML format (XML standard for graphs).

        Returns:
            GraphML XML string.
        """
        # Create root element with namespace
        ns = "http://graphml.graphdrawing.org/xmlns"
        ET.register_namespace('', ns)

        root = ET.Element("{%s}graphml" % ns)
        root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")

        # Define keys for node attributes
        keys = [
            ("d0", "node", "label", "string"),
            ("d1", "node", "type", "string"),
            ("d2", "node", "centrality", "double"),
            ("d3", "node", "degree", "int"),
        ]

        if options.include_positions:
            keys.extend([
                ("d4", "node", "x", "double"),
                ("d5", "node", "y", "double"),
            ])

        if options.include_visual_properties:
            keys.extend([
                ("d6", "node", "color", "string"),
                ("d7", "node", "size", "double"),
            ])

        # Edge attribute keys
        keys.extend([
            ("e0", "edge", "label", "string"),
            ("e1", "edge", "weight", "double"),
            ("e2", "edge", "type", "string"),
        ])

        if options.include_visual_properties:
            keys.extend([
                ("e3", "edge", "color", "string"),
                ("e4", "edge", "width", "double"),
            ])

        for key_id, key_for, attr_name, attr_type in keys:
            key_elem = ET.SubElement(root, "{%s}key" % ns)
            key_elem.set("id", key_id)
            key_elem.set("for", key_for)
            key_elem.set("attr.name", attr_name)
            key_elem.set("attr.type", attr_type)

        # Create graph element
        graph_elem = ET.SubElement(root, "{%s}graph" % ns)
        graph_elem.set("id", "G")
        graph_elem.set("edgedefault", "directed")

        # Add nodes
        for node in graph.nodes:
            node_elem = ET.SubElement(graph_elem, "{%s}node" % ns)
            node_elem.set("id", node.id)

            # Add data elements
            data_elem = ET.SubElement(node_elem, "{%s}data" % ns)
            data_elem.set("key", "d0")
            data_elem.text = node.label

            data_elem = ET.SubElement(node_elem, "{%s}data" % ns)
            data_elem.set("key", "d1")
            data_elem.text = node.entity_type

            data_elem = ET.SubElement(node_elem, "{%s}data" % ns)
            data_elem.set("key", "d2")
            data_elem.text = str(node.centrality)

            data_elem = ET.SubElement(node_elem, "{%s}data" % ns)
            data_elem.set("key", "d3")
            data_elem.text = str(node.degree)

            if options.include_positions:
                data_elem = ET.SubElement(node_elem, "{%s}data" % ns)
                data_elem.set("key", "d4")
                data_elem.text = str(node.position.x)

                data_elem = ET.SubElement(node_elem, "{%s}data" % ns)
                data_elem.set("key", "d5")
                data_elem.text = str(node.position.y)

            if options.include_visual_properties:
                data_elem = ET.SubElement(node_elem, "{%s}data" % ns)
                data_elem.set("key", "d6")
                data_elem.text = node.visual.color

                data_elem = ET.SubElement(node_elem, "{%s}data" % ns)
                data_elem.set("key", "d7")
                data_elem.text = str(node.visual.size)

        # Add edges
        for edge in graph.edges:
            edge_elem = ET.SubElement(graph_elem, "{%s}edge" % ns)
            edge_elem.set("id", edge.id)
            edge_elem.set("source", edge.source)
            edge_elem.set("target", edge.target)

            data_elem = ET.SubElement(edge_elem, "{%s}data" % ns)
            data_elem.set("key", "e0")
            data_elem.text = edge.relationship_type

            data_elem = ET.SubElement(edge_elem, "{%s}data" % ns)
            data_elem.set("key", "e1")
            data_elem.text = str(edge.weight)

            data_elem = ET.SubElement(edge_elem, "{%s}data" % ns)
            data_elem.set("key", "e2")
            data_elem.text = edge.relationship_type

            if options.include_visual_properties:
                data_elem = ET.SubElement(edge_elem, "{%s}data" % ns)
                data_elem.set("key", "e3")
                data_elem.text = edge.visual.color

                data_elem = ET.SubElement(edge_elem, "{%s}data" % ns)
                data_elem.set("key", "e4")
                data_elem.text = str(edge.visual.width)

        # Convert to string
        if options.pretty_print:
            ET.indent(root)

        return ET.tostring(root, encoding='unicode', xml_declaration=True)

    @staticmethod
    def to_dot(
        graph: VisualizationGraph,
        options: ExportOptions
    ) -> str:
        """
        Export to DOT format (Graphviz).

        Returns:
            DOT format string.
        """
        lines = ["digraph G {"]
        lines.append("  // Graph attributes")
        lines.append("  graph [rankdir=TB];")
        lines.append("  node [shape=circle];")
        lines.append("")

        # Node definitions
        lines.append("  // Nodes")
        for node in graph.nodes:
            attrs = [f'label="{node.label}"']

            if options.include_visual_properties:
                attrs.append(f'fillcolor="{node.visual.color}"')
                attrs.append('style="filled"')
                # Scale size for DOT
                width = node.visual.size / 30
                attrs.append(f'width="{width:.2f}"')

            if options.include_positions:
                # DOT uses inches, scale from pixels
                pos_x = node.position.x / 72
                pos_y = node.position.y / 72
                attrs.append(f'pos="{pos_x:.2f},{pos_y:.2f}!"')

            attrs_str = ", ".join(attrs)
            # Escape special characters in node ID
            safe_id = node.id.replace("-", "_").replace(".", "_")
            lines.append(f'  "{safe_id}" [{attrs_str}];')

        lines.append("")

        # Edge definitions
        lines.append("  // Edges")
        for edge in graph.edges:
            safe_source = edge.source.replace("-", "_").replace(".", "_")
            safe_target = edge.target.replace("-", "_").replace(".", "_")

            attrs = [f'label="{edge.relationship_type}"']

            if options.include_visual_properties:
                attrs.append(f'color="{edge.visual.color}"')
                attrs.append(f'penwidth="{edge.visual.width:.1f}"')

                if edge.visual.style == "dashed":
                    attrs.append('style="dashed"')
                elif edge.visual.style == "dotted":
                    attrs.append('style="dotted"')

            attrs_str = ", ".join(attrs)
            lines.append(f'  "{safe_source}" -> "{safe_target}" [{attrs_str}];')

        lines.append("}")

        return "\n".join(lines)


# =============================================================================
# MAIN SERVICE CLASS
# =============================================================================

class GraphVisualizationService:
    """
    Graph Visualization Service for Basset Hound OSINT Platform.

    Provides comprehensive graph visualization capabilities including:
    - Multiple layout algorithms
    - Export to various formats
    - Subgraph extraction with filtering
    - Visual metadata computation
    """

    def __init__(self, neo4j_handler=None, graph_service=None):
        """
        Initialize the Graph Visualization Service.

        Args:
            neo4j_handler: Async Neo4j database handler
            graph_service: Optional GraphService instance for data retrieval
        """
        self.neo4j_handler = neo4j_handler
        self.graph_service = graph_service
        self.layout_engine = LayoutEngine()
        self.metrics = GraphMetrics()
        self.exporter = GraphExporter()

    def _get_entity_type_color(self, entity_type: str) -> str:
        """Get color for an entity type."""
        return ENTITY_TYPE_COLORS.get(entity_type, ENTITY_TYPE_COLORS["default"])

    def _get_relationship_type_color(self, rel_type: str) -> str:
        """Get color for a relationship type."""
        return RELATIONSHIP_TYPE_COLORS.get(rel_type, RELATIONSHIP_TYPE_COLORS["default"])

    def _get_confidence_color(self, confidence: str) -> str:
        """Get color based on confidence level."""
        return CONFIDENCE_COLORS.get(confidence, CONFIDENCE_COLORS["default"])

    def _calculate_node_size(
        self,
        centrality: float,
        min_size: float = 15.0,
        max_size: float = 50.0
    ) -> float:
        """Calculate node size based on centrality."""
        return min_size + centrality * (max_size - min_size)

    def _calculate_edge_width(
        self,
        weight: float,
        min_width: float = 1.0,
        max_width: float = 5.0
    ) -> float:
        """Calculate edge width based on weight/confidence."""
        return min_width + weight * (max_width - min_width)

    def _extract_display_name(self, profile: Dict[str, Any], entity_id: str) -> str:
        """Extract display name from entity profile."""
        if not profile:
            return f"Entity {entity_id[:8]}"

        # Try profile section
        if "profile" in profile:
            profile_section = profile["profile"]

            # Try first_name + last_name
            first_name = profile_section.get("first_name", "")
            last_name = profile_section.get("last_name", "")
            if first_name or last_name:
                return f"{first_name} {last_name}".strip()

            # Try full_name or name
            if "full_name" in profile_section:
                return profile_section["full_name"]
            if "name" in profile_section:
                return profile_section["name"]

        # Try core section
        if "core" in profile:
            core = profile["core"]
            if "name" in core:
                name_data = core["name"]
                if isinstance(name_data, list) and name_data:
                    name_obj = name_data[0]
                    if isinstance(name_obj, dict):
                        first = name_obj.get("first_name", "")
                        last = name_obj.get("last_name", "")
                        if first or last:
                            return f"{first} {last}".strip()

        # Try other common fields
        for section in profile.values():
            if isinstance(section, dict):
                if "username" in section:
                    return f"@{section['username']}"
                if "email" in section:
                    return section["email"].split("@")[0]

        return f"Entity {entity_id[:8]}"

    async def get_project_visualization(
        self,
        project_safe_name: str,
        layout_options: Optional[LayoutOptions] = None,
        include_orphans: bool = True
    ) -> VisualizationGraph:
        """
        Get complete visualization graph for a project.

        Args:
            project_safe_name: Project identifier
            layout_options: Layout configuration (defaults to force-directed)
            include_orphans: Include nodes with no connections

        Returns:
            VisualizationGraph with positions and visual properties
        """
        if layout_options is None:
            layout_options = LayoutOptions()

        # Get raw graph data
        if self.graph_service:
            raw_graph = self.graph_service.get_project_graph(
                project_safe_name,
                include_orphans=include_orphans
            )
        else:
            raw_graph = await self._fetch_project_graph(project_safe_name, include_orphans)

        return await self._build_visualization_graph(
            raw_graph["nodes"],
            raw_graph["edges"],
            layout_options
        )

    async def get_entity_neighborhood(
        self,
        project_safe_name: str,
        extraction_options: SubgraphExtractionOptions,
        layout_options: Optional[LayoutOptions] = None
    ) -> VisualizationGraph:
        """
        Extract and visualize N-hop neighborhood of an entity.

        Args:
            project_safe_name: Project identifier
            extraction_options: Subgraph extraction configuration
            layout_options: Layout configuration

        Returns:
            VisualizationGraph centered on the specified entity
        """
        if layout_options is None:
            layout_options = LayoutOptions(
                algorithm=LayoutAlgorithm.RADIAL,
                center_node=extraction_options.center_entity_id
            )

        # Extract subgraph
        nodes, edges = await self._extract_subgraph(
            project_safe_name,
            extraction_options
        )

        return await self._build_visualization_graph(nodes, edges, layout_options)

    async def _fetch_project_graph(
        self,
        project_safe_name: str,
        include_orphans: bool
    ) -> Dict[str, Any]:
        """Fetch project graph data from Neo4j."""
        if not self.neo4j_handler:
            return {"nodes": [], "edges": []}

        async with self.neo4j_handler.session() as session:
            # Get all entities
            entities_result = await session.run("""
                MATCH (project:Project {safe_name: $project_safe_name})
                      -[:HAS_PERSON]->(person:Person)
                RETURN person.id AS id, person.profile AS profile,
                       person.created_at AS created_at
                ORDER BY person.created_at DESC
            """, project_safe_name=project_safe_name)

            entities_data = await entities_result.data()

            nodes = []
            entity_ids = set()

            for record in entities_data:
                entity_id = record["id"]
                entity_ids.add(entity_id)

                profile = record.get("profile")
                if isinstance(profile, str):
                    try:
                        profile = json.loads(profile)
                    except json.JSONDecodeError:
                        profile = {}
                elif profile is None:
                    profile = {}

                display_name = self._extract_display_name(profile, entity_id)

                nodes.append({
                    "id": entity_id,
                    "label": display_name,
                    "type": "Person",
                    "properties": {
                        "profile": profile,
                        "created_at": record.get("created_at")
                    }
                })

            # Extract edges from Tagged People section
            edges = []
            for node in nodes:
                entity_id = node["id"]
                profile = node["properties"].get("profile", {})
                tagged_section = profile.get("Tagged People", {})

                tagged_ids = tagged_section.get("tagged_people", []) or []
                if not isinstance(tagged_ids, list):
                    tagged_ids = [tagged_ids] if tagged_ids else []

                relationship_types = tagged_section.get("relationship_types", {}) or {}
                relationship_properties = tagged_section.get("relationship_properties", {}) or {}

                for target_id in tagged_ids:
                    if target_id in entity_ids:
                        rel_type = relationship_types.get(target_id, "RELATED_TO")
                        rel_props = relationship_properties.get(target_id, {})

                        edges.append({
                            "source": entity_id,
                            "target": target_id,
                            "type": rel_type,
                            "properties": rel_props
                        })

            # Filter orphans if needed
            if not include_orphans:
                connected_ids = set()
                for edge in edges:
                    connected_ids.add(edge["source"])
                    connected_ids.add(edge["target"])
                nodes = [n for n in nodes if n["id"] in connected_ids]

            return {"nodes": nodes, "edges": edges}

    async def _extract_subgraph(
        self,
        project_safe_name: str,
        options: SubgraphExtractionOptions
    ) -> Tuple[List[Dict], List[Dict]]:
        """Extract subgraph based on extraction options."""
        # Get full graph
        full_graph = await self._fetch_project_graph(project_safe_name, include_orphans=True)
        all_nodes = full_graph["nodes"]
        all_edges = full_graph["edges"]

        # Build node lookup and adjacency
        node_lookup = {n["id"]: n for n in all_nodes}
        adjacency: Dict[str, Set[str]] = defaultdict(set)

        for edge in all_edges:
            source, target = edge["source"], edge["target"]
            rel_type = edge.get("type", "RELATED_TO")

            # Filter by relationship type
            if options.relationship_types:
                if rel_type not in options.relationship_types:
                    continue

            adjacency[source].add(target)
            adjacency[target].add(source)

        # BFS to find nodes within max_hops
        center = options.center_entity_id
        if center not in node_lookup:
            return [], []

        visited = {center: 0}
        queue = [(center, 0)]

        while queue:
            current, depth = queue.pop(0)
            if depth >= options.max_hops:
                continue

            for neighbor in adjacency[current]:
                if neighbor not in visited:
                    visited[neighbor] = depth + 1
                    queue.append((neighbor, depth + 1))

        # Filter nodes by entity type if specified
        candidate_ids = set(visited.keys())
        if options.entity_types:
            candidate_ids = {
                nid for nid in candidate_ids
                if node_lookup.get(nid, {}).get("type", "Person") in options.entity_types
            }

        # Prioritize and limit nodes
        if len(candidate_ids) > options.max_nodes:
            candidate_ids = self._prioritize_nodes(
                list(candidate_ids),
                all_edges,
                options.prioritization,
                options.max_nodes,
                center
            )

        # Filter nodes and edges
        nodes = [n for n in all_nodes if n["id"] in candidate_ids]
        edges = [
            e for e in all_edges
            if e["source"] in candidate_ids and e["target"] in candidate_ids
        ]

        # Apply relationship type filter to edges
        if options.relationship_types:
            edges = [
                e for e in edges
                if e.get("type", "RELATED_TO") in options.relationship_types
            ]

        # Remove orphans if needed
        if not options.include_orphans:
            connected = set()
            for e in edges:
                connected.add(e["source"])
                connected.add(e["target"])
            nodes = [n for n in nodes if n["id"] in connected or n["id"] == center]

        return nodes, edges

    def _prioritize_nodes(
        self,
        node_ids: List[str],
        edges: List[Dict],
        strategy: NodePriority,
        limit: int,
        center_id: str
    ) -> Set[str]:
        """Prioritize nodes based on strategy and return top N."""
        if strategy == NodePriority.CONNECTION_COUNT:
            degrees = defaultdict(int)
            for edge in edges:
                if edge["source"] in node_ids:
                    degrees[edge["source"]] += 1
                if edge["target"] in node_ids:
                    degrees[edge["target"]] += 1

            sorted_ids = sorted(node_ids, key=lambda x: degrees[x], reverse=True)

        elif strategy == NodePriority.CENTRALITY:
            # Use degree centrality as proxy
            degrees = defaultdict(int)
            for edge in edges:
                if edge["source"] in node_ids:
                    degrees[edge["source"]] += 1
                if edge["target"] in node_ids:
                    degrees[edge["target"]] += 1

            sorted_ids = sorted(node_ids, key=lambda x: degrees[x], reverse=True)

        else:
            # Default: keep order
            sorted_ids = node_ids

        # Always include center node
        result = {center_id}
        for nid in sorted_ids:
            if len(result) >= limit:
                break
            result.add(nid)

        return result

    async def _build_visualization_graph(
        self,
        raw_nodes: List[Dict[str, Any]],
        raw_edges: List[Dict[str, Any]],
        layout_options: LayoutOptions
    ) -> VisualizationGraph:
        """Build complete visualization graph with positions and visual properties."""
        if not raw_nodes:
            return VisualizationGraph()

        # Compute layout positions
        positions = self.layout_engine.compute_layout(
            raw_nodes,
            raw_edges,
            layout_options
        )

        # Compute metrics
        centralities = self.metrics.compute_degree_centrality(raw_nodes, raw_edges)
        degrees = self.metrics.compute_node_degrees(raw_nodes, raw_edges)

        # Build visualization nodes
        vis_nodes = []
        for node in raw_nodes:
            node_id = node["id"]
            entity_type = node.get("type", "Person")
            centrality = centralities.get(node_id, 0.0)
            degree = degrees.get(node_id, 0)

            position = positions.get(node_id, Position(x=500, y=400))

            visual = NodeVisualProperties(
                color=self._get_entity_type_color(entity_type),
                size=self._calculate_node_size(centrality),
                border_color=self._get_entity_type_color(entity_type),
                border_width=2.0 if centrality > 0.5 else 1.0,
                opacity=0.9,
                shape="circle"
            )

            vis_node = VisualizationNode(
                id=node_id,
                label=node.get("label", f"Entity {node_id[:8]}"),
                entity_type=entity_type,
                position=position,
                visual=visual,
                properties=node.get("properties", {}),
                centrality=centrality,
                degree=degree
            )
            vis_nodes.append(vis_node)

        # Build visualization edges
        vis_edges = []
        for i, edge in enumerate(raw_edges):
            rel_type = edge.get("type", "RELATED_TO")
            props = edge.get("properties", {})

            # Get confidence for weight
            confidence = props.get("confidence", "unverified")
            if isinstance(confidence, str):
                weight_map = {
                    "confirmed": 1.0,
                    "high": 0.8,
                    "medium": 0.6,
                    "low": 0.4,
                    "unverified": 0.3
                }
                weight = weight_map.get(confidence, 0.5)
            else:
                weight = float(confidence) if confidence else 0.5

            # Determine edge style based on confidence
            if confidence in ("low", "unverified"):
                style = "dashed"
            else:
                style = "solid"

            visual = EdgeVisualProperties(
                color=self._get_relationship_type_color(rel_type),
                width=self._calculate_edge_width(weight),
                opacity=0.5 + weight * 0.4,
                style=style,
                arrow=True
            )

            vis_edge = VisualizationEdge(
                id=f"edge_{i}",
                source=edge["source"],
                target=edge["target"],
                relationship_type=rel_type,
                visual=visual,
                properties=props,
                weight=weight
            )
            vis_edges.append(vis_edge)

        # Compute bounds
        if vis_nodes:
            xs = [n.position.x for n in vis_nodes]
            ys = [n.position.y for n in vis_nodes]
            bounds = {
                "min_x": min(xs),
                "max_x": max(xs),
                "min_y": min(ys),
                "max_y": max(ys)
            }
        else:
            bounds = {"min_x": 0, "max_x": 1000, "min_y": 0, "max_y": 1000}

        return VisualizationGraph(
            nodes=vis_nodes,
            edges=vis_edges,
            layout=layout_options.algorithm,
            bounds=bounds,
            metadata={
                "node_count": len(vis_nodes),
                "edge_count": len(vis_edges),
                "layout_algorithm": layout_options.algorithm.value,
                "layout_iterations": layout_options.iterations
            }
        )

    def export_graph(
        self,
        graph: VisualizationGraph,
        options: ExportOptions
    ) -> Union[Dict[str, Any], str]:
        """
        Export graph to specified format.

        Args:
            graph: VisualizationGraph to export
            options: Export configuration

        Returns:
            Dictionary (for JSON formats) or string (for XML/DOT formats)
        """
        if options.format == ExportFormat.D3_JSON:
            result = self.exporter.to_d3_json(graph, options)
            if options.pretty_print:
                return result
            return result

        elif options.format == ExportFormat.CYTOSCAPE_JSON:
            result = self.exporter.to_cytoscape_json(graph, options)
            if options.pretty_print:
                return result
            return result

        elif options.format == ExportFormat.GRAPHML:
            return self.exporter.to_graphml(graph, options)

        elif options.format == ExportFormat.DOT:
            return self.exporter.to_dot(graph, options)

        else:
            raise ValueError(f"Unsupported export format: {options.format}")

    async def get_cluster_visualization(
        self,
        project_safe_name: str,
        cluster_id: str,
        layout_options: Optional[LayoutOptions] = None
    ) -> VisualizationGraph:
        """
        Get visualization for a specific cluster.

        Args:
            project_safe_name: Project identifier
            cluster_id: Cluster root entity ID
            layout_options: Layout configuration

        Returns:
            VisualizationGraph for the cluster
        """
        if layout_options is None:
            layout_options = LayoutOptions(
                algorithm=LayoutAlgorithm.FORCE_DIRECTED
            )

        if self.graph_service:
            raw_graph = self.graph_service.get_cluster_graph(
                project_safe_name,
                cluster_id
            )
        else:
            # Fallback: treat cluster_id as center for neighborhood extraction
            extraction_opts = SubgraphExtractionOptions(
                center_entity_id=cluster_id,
                max_hops=3,
                max_nodes=50
            )
            nodes, edges = await self._extract_subgraph(
                project_safe_name,
                extraction_opts
            )
            raw_graph = {"nodes": nodes, "edges": edges}

        return await self._build_visualization_graph(
            raw_graph.get("nodes", []),
            raw_graph.get("edges", []),
            layout_options
        )

    def compute_custom_layout(
        self,
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]],
        layout_options: LayoutOptions
    ) -> Dict[str, Position]:
        """
        Compute layout for custom node/edge data.

        Args:
            nodes: List of node dictionaries (must have 'id' key)
            edges: List of edge dictionaries (must have 'source' and 'target')
            layout_options: Layout configuration

        Returns:
            Dictionary mapping node IDs to Position objects
        """
        return self.layout_engine.compute_layout(nodes, edges, layout_options)

    def get_visual_legend(self) -> Dict[str, Any]:
        """
        Get visual legend data for the frontend.

        Returns:
            Dictionary containing color mappings for entity types,
            relationship types, and confidence levels.
        """
        return {
            "entity_types": {
                entity_type: {
                    "color": color,
                    "label": entity_type.replace("_", " ").title()
                }
                for entity_type, color in ENTITY_TYPE_COLORS.items()
                if entity_type != "default"
            },
            "relationship_types": {
                rel_type: {
                    "color": color,
                    "label": rel_type.replace("_", " ").title()
                }
                for rel_type, color in RELATIONSHIP_TYPE_COLORS.items()
                if rel_type != "default"
            },
            "confidence_levels": {
                level: {
                    "color": color,
                    "label": level.title()
                }
                for level, color in CONFIDENCE_COLORS.items()
                if level != "default"
            },
            "relationship_categories": get_relationship_type_categories()
        }


# =============================================================================
# SINGLETON MANAGEMENT
# =============================================================================

_visualization_service: Optional[GraphVisualizationService] = None


def get_graph_visualization_service(
    neo4j_handler=None,
    graph_service=None
) -> GraphVisualizationService:
    """
    Get or create the GraphVisualizationService singleton.

    Args:
        neo4j_handler: Optional async Neo4j handler
        graph_service: Optional GraphService instance

    Returns:
        GraphVisualizationService instance
    """
    global _visualization_service

    if _visualization_service is None:
        _visualization_service = GraphVisualizationService(
            neo4j_handler=neo4j_handler,
            graph_service=graph_service
        )
    elif neo4j_handler is not None:
        _visualization_service.neo4j_handler = neo4j_handler
    elif graph_service is not None:
        _visualization_service.graph_service = graph_service

    return _visualization_service


def set_graph_visualization_service(
    service: Optional[GraphVisualizationService]
) -> None:
    """Set the visualization service singleton (useful for testing)."""
    global _visualization_service
    _visualization_service = service
