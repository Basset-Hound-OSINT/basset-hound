"""
Influence Propagation Service for Basset Hound OSINT Platform.

This service tracks how information and connections spread through the graph,
identifying influential entities and simulating influence propagation.

Features:
- PageRank algorithm for identifying influential entities
- Influence spread simulation (Independent Cascade and Linear Threshold models)
- Influence path tracking between entities
- Key entity identification (articulation points, bridges)
- Works with Neo4j through the existing neo4j_handler

References:
- PageRank: Page, L., et al. "The PageRank citation ranking"
- Influence models: Kempe, D., et al. "Maximizing the spread of influence"
"""

import logging
import random
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from pydantic import BaseModel, Field


logger = logging.getLogger("basset_hound.influence_service")


# =============================================================================
# MODELS
# =============================================================================


class InfluenceScore(BaseModel):
    """Represents an entity's influence score and ranking."""

    entity_id: str = Field(..., description="Unique identifier of the entity")
    score: float = Field(..., ge=0.0, description="Influence score (0.0 to 1.0 for PageRank)")
    rank: int = Field(..., ge=1, description="Rank among all entities (1 = most influential)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "entity_id": "550e8400-e29b-41d4-a716-446655440000",
                "score": 0.15,
                "rank": 1
            }
        }
    }


class AffectedEntity(BaseModel):
    """Entity affected during influence spread simulation."""

    entity_id: str = Field(..., description="Entity ID")
    step: int = Field(..., ge=0, description="Step at which entity was affected")
    activated_by: Optional[str] = Field(None, description="Entity that activated this one")
    activation_probability: Optional[float] = Field(None, description="Probability of activation")


class InfluenceSpreadResult(BaseModel):
    """Result of an influence spread simulation."""

    seed_entity_id: str = Field(..., description="Starting entity for the spread")
    affected_entities: List[AffectedEntity] = Field(
        default_factory=list,
        description="Entities affected at each step"
    )
    steps: int = Field(..., ge=0, description="Total number of propagation steps")
    reach_percentage: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Percentage of total graph reached"
    )
    total_entities: int = Field(..., description="Total entities in the graph")
    affected_count: int = Field(..., description="Number of entities affected")

    model_config = {
        "json_schema_extra": {
            "example": {
                "seed_entity_id": "550e8400-e29b-41d4-a716-446655440000",
                "affected_entities": [],
                "steps": 3,
                "reach_percentage": 45.5,
                "total_entities": 100,
                "affected_count": 45
            }
        }
    }


class KeyEntityReason(str, Enum):
    """Reason why an entity is considered key/critical."""

    ARTICULATION_POINT = "articulation_point"  # Removal disconnects the graph
    BRIDGE_ENDPOINT = "bridge_endpoint"  # Endpoint of a bridge edge
    HIGH_BETWEENNESS = "high_betweenness"  # High betweenness centrality
    HIGH_DEGREE = "high_degree"  # Many connections
    GATEWAY = "gateway"  # Connects otherwise separate clusters


class KeyEntityResult(BaseModel):
    """Entity identified as key/critical to network structure."""

    entity_id: str = Field(..., description="Entity ID")
    importance_score: float = Field(
        ...,
        ge=0.0,
        description="Importance score (higher = more critical)"
    )
    reason: KeyEntityReason = Field(..., description="Why this entity is considered key")
    components_if_removed: Optional[int] = Field(
        None,
        description="Number of components if this entity is removed"
    )
    affected_entities_count: Optional[int] = Field(
        None,
        description="Number of entities affected if removed"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "entity_id": "550e8400-e29b-41d4-a716-446655440000",
                "importance_score": 0.85,
                "reason": "articulation_point",
                "components_if_removed": 3,
                "affected_entities_count": 25
            }
        }
    }


class InfluencePathStep(BaseModel):
    """A single step in an influence path."""

    entity_id: str = Field(..., description="Entity at this step")
    relationship_type: Optional[str] = Field(None, description="Relationship to next entity")
    distance_from_source: int = Field(..., description="Number of hops from source")


class InfluencePath(BaseModel):
    """Path of influence from source to target."""

    source_id: str = Field(..., description="Source entity ID")
    target_id: str = Field(..., description="Target entity ID")
    path: List[InfluencePathStep] = Field(
        default_factory=list,
        description="Entities in the path"
    )
    path_length: int = Field(..., description="Number of hops")
    exists: bool = Field(..., description="Whether a path exists")


class InfluenceReport(BaseModel):
    """Complete influence analysis report."""

    algorithm: str = Field(..., description="Algorithm used (e.g., 'pagerank')")
    scores: List[InfluenceScore] = Field(default_factory=list, description="Scored entities")
    top_n: int = Field(..., description="Number of top entities returned")
    total_entities: int = Field(..., description="Total entities analyzed")
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Algorithm parameters used"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "algorithm": "pagerank",
                "scores": [],
                "top_n": 10,
                "total_entities": 100,
                "parameters": {"damping_factor": 0.85, "iterations": 100}
            }
        }
    }


class PropagationModel(str, Enum):
    """Influence propagation model types."""

    INDEPENDENT_CASCADE = "independent_cascade"
    LINEAR_THRESHOLD = "linear_threshold"


# =============================================================================
# SERVICE IMPLEMENTATION
# =============================================================================


class InfluenceService:
    """
    Service for analyzing influence propagation in entity graphs.

    This service provides algorithms to:
    - Identify the most influential entities using PageRank
    - Simulate how influence spreads from seed entities
    - Track influence paths between entities
    - Identify key entities whose removal would fragment the network

    Usage:
        service = InfluenceService(neo4j_handler)

        # Get top influential entities
        report = service.calculate_pagerank("project-123", top_n=10)

        # Simulate influence spread
        result = service.simulate_influence_spread(
            "project-123",
            seed_entity_id="entity-456",
            model=PropagationModel.INDEPENDENT_CASCADE
        )

        # Find key entities
        key_entities = service.find_key_entities("project-123")
    """

    # Default algorithm parameters
    DEFAULT_DAMPING_FACTOR = 0.85
    DEFAULT_ITERATIONS = 100
    DEFAULT_TOLERANCE = 1e-6
    DEFAULT_PROPAGATION_PROBABILITY = 0.1
    DEFAULT_THRESHOLD = 0.3
    DEFAULT_MAX_STEPS = 10

    def __init__(self, neo4j_handler):
        """
        Initialize the influence service.

        Args:
            neo4j_handler: Neo4j database handler instance
        """
        self.neo4j = neo4j_handler

    # =========================================================================
    # GRAPH DATA EXTRACTION
    # =========================================================================

    def _get_graph_data(
        self,
        project_id: str
    ) -> Tuple[Dict[str, Set[str]], Dict[str, Set[str]], Set[str]]:
        """
        Extract graph data from Neo4j for analysis.

        Args:
            project_id: Project ID or safe_name

        Returns:
            Tuple of (outgoing_edges, incoming_edges, all_node_ids)
            - outgoing_edges: Dict mapping node_id to set of connected node_ids
            - incoming_edges: Dict mapping node_id to set of nodes pointing to it
            - all_node_ids: Set of all node IDs in the graph
        """
        # Get project entities
        project = self._get_project_by_id(project_id)
        if not project:
            logger.warning(f"Project {project_id} not found")
            return {}, {}, set()

        project_safe_name = project.get("safe_name", project_id)

        # Get all entities
        entities = self.neo4j.get_all_people(project_safe_name)
        if not entities:
            return {}, {}, set()

        all_node_ids = {e.get("id") for e in entities if e.get("id")}
        outgoing_edges: Dict[str, Set[str]] = defaultdict(set)
        incoming_edges: Dict[str, Set[str]] = defaultdict(set)

        # Build adjacency from tagged relationships
        for entity in entities:
            entity_id = entity.get("id")
            if not entity_id:
                continue

            profile = entity.get("profile", {})
            tagged_section = profile.get("Tagged People", {})
            tagged_ids = tagged_section.get("tagged_people", []) or []

            if not isinstance(tagged_ids, list):
                tagged_ids = [tagged_ids] if tagged_ids else []

            for target_id in tagged_ids:
                if target_id in all_node_ids:
                    outgoing_edges[entity_id].add(target_id)
                    incoming_edges[target_id].add(entity_id)

        return dict(outgoing_edges), dict(incoming_edges), all_node_ids

    def _get_undirected_adjacency(
        self,
        project_id: str
    ) -> Tuple[Dict[str, Set[str]], Set[str]]:
        """
        Get undirected adjacency list for the graph.

        Args:
            project_id: Project ID or safe_name

        Returns:
            Tuple of (adjacency_dict, all_node_ids)
        """
        outgoing, incoming, all_nodes = self._get_graph_data(project_id)

        adjacency: Dict[str, Set[str]] = defaultdict(set)

        for node_id in all_nodes:
            # Add outgoing edges
            if node_id in outgoing:
                adjacency[node_id].update(outgoing[node_id])
            # Add incoming edges (treat as bidirectional for undirected)
            if node_id in incoming:
                adjacency[node_id].update(incoming[node_id])

        # Ensure all nodes are in adjacency dict
        for node_id in all_nodes:
            if node_id not in adjacency:
                adjacency[node_id] = set()

        # Make symmetric (undirected)
        for node_id, neighbors in list(adjacency.items()):
            for neighbor in neighbors:
                adjacency[neighbor].add(node_id)

        return dict(adjacency), all_nodes

    def _get_project_by_id(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get project by ID or safe_name."""
        try:
            projects = self.neo4j.get_all_projects()
            for project in projects:
                if project.get("id") == project_id or project.get("safe_name") == project_id:
                    return project
            return None
        except Exception:
            return None

    # =========================================================================
    # PAGERANK ALGORITHM
    # =========================================================================

    def calculate_pagerank(
        self,
        project_id: str,
        damping_factor: float = DEFAULT_DAMPING_FACTOR,
        max_iterations: int = DEFAULT_ITERATIONS,
        tolerance: float = DEFAULT_TOLERANCE,
        top_n: int = 10
    ) -> InfluenceReport:
        """
        Calculate PageRank scores for all entities in a project.

        PageRank measures the importance of entities based on the structure
        of their connections. Entities with many incoming connections from
        other important entities will have higher scores.

        Args:
            project_id: Project ID or safe_name
            damping_factor: Probability of following a link (0.85 typical)
            max_iterations: Maximum iterations before stopping
            tolerance: Convergence tolerance
            top_n: Number of top-ranked entities to return

        Returns:
            InfluenceReport with PageRank scores and rankings
        """
        logger.info(f"Calculating PageRank for project {project_id}")

        outgoing_edges, incoming_edges, all_nodes = self._get_graph_data(project_id)

        if not all_nodes:
            return InfluenceReport(
                algorithm="pagerank",
                scores=[],
                top_n=top_n,
                total_entities=0,
                parameters={
                    "damping_factor": damping_factor,
                    "iterations": 0,
                    "tolerance": tolerance
                }
            )

        n = len(all_nodes)
        node_list = list(all_nodes)
        node_to_idx = {node: i for i, node in enumerate(node_list)}

        # Initialize PageRank scores uniformly
        scores = {node: 1.0 / n for node in all_nodes}

        # Precompute out-degrees
        out_degrees = {node: len(outgoing_edges.get(node, set())) for node in all_nodes}

        # Iterative PageRank computation
        iteration = 0
        for iteration in range(max_iterations):
            new_scores = {}
            max_diff = 0.0

            for node in all_nodes:
                # Sum contributions from incoming nodes
                incoming_sum = 0.0
                for source in incoming_edges.get(node, set()):
                    out_degree = out_degrees.get(source, 0)
                    if out_degree > 0:
                        incoming_sum += scores[source] / out_degree

                # PageRank formula
                new_score = (1 - damping_factor) / n + damping_factor * incoming_sum
                new_scores[node] = new_score

                max_diff = max(max_diff, abs(new_score - scores[node]))

            scores = new_scores

            # Check for convergence
            if max_diff < tolerance:
                logger.info(f"PageRank converged after {iteration + 1} iterations")
                break

        # Sort by score and create ranking
        sorted_nodes = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        # Create InfluenceScore objects
        influence_scores = []
        for rank, (node_id, score) in enumerate(sorted_nodes[:top_n], start=1):
            influence_scores.append(InfluenceScore(
                entity_id=node_id,
                score=score,
                rank=rank
            ))

        return InfluenceReport(
            algorithm="pagerank",
            scores=influence_scores,
            top_n=top_n,
            total_entities=n,
            parameters={
                "damping_factor": damping_factor,
                "iterations": iteration + 1,
                "tolerance": tolerance,
                "converged": iteration < max_iterations - 1
            }
        )

    # =========================================================================
    # INFLUENCE SPREAD SIMULATION
    # =========================================================================

    def simulate_influence_spread(
        self,
        project_id: str,
        seed_entity_id: str,
        model: PropagationModel = PropagationModel.INDEPENDENT_CASCADE,
        propagation_probability: float = DEFAULT_PROPAGATION_PROBABILITY,
        threshold: float = DEFAULT_THRESHOLD,
        max_steps: int = DEFAULT_MAX_STEPS,
        random_seed: Optional[int] = None
    ) -> InfluenceSpreadResult:
        """
        Simulate how influence spreads from a seed entity through the network.

        Two models are supported:

        1. Independent Cascade: Each active node has one chance to activate
           each inactive neighbor with probability p.

        2. Linear Threshold: Each node has a threshold. A node becomes active
           when the sum of influence from active neighbors exceeds the threshold.

        Args:
            project_id: Project ID or safe_name
            seed_entity_id: Entity to start the spread from
            model: Propagation model to use
            propagation_probability: Probability for Independent Cascade model
            threshold: Threshold for Linear Threshold model
            max_steps: Maximum propagation steps
            random_seed: Random seed for reproducibility

        Returns:
            InfluenceSpreadResult with affected entities and statistics
        """
        logger.info(f"Simulating {model.value} spread from {seed_entity_id}")

        if random_seed is not None:
            random.seed(random_seed)

        adjacency, all_nodes = self._get_undirected_adjacency(project_id)

        if not all_nodes:
            return InfluenceSpreadResult(
                seed_entity_id=seed_entity_id,
                affected_entities=[],
                steps=0,
                reach_percentage=0.0,
                total_entities=0,
                affected_count=0
            )

        if seed_entity_id not in all_nodes:
            logger.warning(f"Seed entity {seed_entity_id} not found in project")
            return InfluenceSpreadResult(
                seed_entity_id=seed_entity_id,
                affected_entities=[],
                steps=0,
                reach_percentage=0.0,
                total_entities=len(all_nodes),
                affected_count=0
            )

        if model == PropagationModel.INDEPENDENT_CASCADE:
            affected = self._independent_cascade(
                adjacency,
                seed_entity_id,
                propagation_probability,
                max_steps
            )
        else:
            affected = self._linear_threshold(
                adjacency,
                seed_entity_id,
                threshold,
                max_steps
            )

        # Calculate statistics
        total_entities = len(all_nodes)
        affected_count = len(affected)
        reach_percentage = (affected_count / total_entities * 100) if total_entities > 0 else 0.0
        max_step = max((ae.step for ae in affected), default=0)

        return InfluenceSpreadResult(
            seed_entity_id=seed_entity_id,
            affected_entities=affected,
            steps=max_step,
            reach_percentage=round(reach_percentage, 2),
            total_entities=total_entities,
            affected_count=affected_count
        )

    def _independent_cascade(
        self,
        adjacency: Dict[str, Set[str]],
        seed_id: str,
        probability: float,
        max_steps: int
    ) -> List[AffectedEntity]:
        """
        Independent Cascade model implementation.

        Each newly activated node has exactly one chance to activate each
        of its inactive neighbors with the given probability.
        """
        affected = [AffectedEntity(
            entity_id=seed_id,
            step=0,
            activated_by=None,
            activation_probability=1.0
        )]
        active_set = {seed_id}
        newly_active = {seed_id}

        for step in range(1, max_steps + 1):
            if not newly_active:
                break

            next_active = set()

            for node in newly_active:
                neighbors = adjacency.get(node, set())
                for neighbor in neighbors:
                    if neighbor not in active_set:
                        # Try to activate with given probability
                        if random.random() < probability:
                            next_active.add(neighbor)
                            active_set.add(neighbor)
                            affected.append(AffectedEntity(
                                entity_id=neighbor,
                                step=step,
                                activated_by=node,
                                activation_probability=probability
                            ))

            newly_active = next_active

        return affected

    def _linear_threshold(
        self,
        adjacency: Dict[str, Set[str]],
        seed_id: str,
        threshold: float,
        max_steps: int
    ) -> List[AffectedEntity]:
        """
        Linear Threshold model implementation.

        Each node becomes active when the fraction of its active neighbors
        exceeds its threshold.
        """
        affected = [AffectedEntity(
            entity_id=seed_id,
            step=0,
            activated_by=None,
            activation_probability=1.0
        )]
        active_set = {seed_id}

        for step in range(1, max_steps + 1):
            new_activations = []

            for node in adjacency:
                if node in active_set:
                    continue

                neighbors = adjacency.get(node, set())
                if not neighbors:
                    continue

                # Calculate fraction of active neighbors
                active_neighbors = len(neighbors & active_set)
                fraction_active = active_neighbors / len(neighbors)

                if fraction_active >= threshold:
                    new_activations.append(node)
                    # Find which active neighbor triggered this (arbitrary choice)
                    activator = next(iter(neighbors & active_set), None)
                    affected.append(AffectedEntity(
                        entity_id=node,
                        step=step,
                        activated_by=activator,
                        activation_probability=fraction_active
                    ))

            if not new_activations:
                break

            active_set.update(new_activations)

        return affected

    # =========================================================================
    # INFLUENCE PATH TRACKING
    # =========================================================================

    def find_influence_path(
        self,
        project_id: str,
        source_id: str,
        target_id: str,
        max_depth: int = 10
    ) -> InfluencePath:
        """
        Find the shortest path of influence from source to target entity.

        Uses BFS to find the shortest path between two entities,
        tracing how influence could propagate.

        Args:
            project_id: Project ID or safe_name
            source_id: Starting entity ID
            target_id: Destination entity ID
            max_depth: Maximum path length to search

        Returns:
            InfluencePath with the path details
        """
        logger.info(f"Finding influence path from {source_id} to {target_id}")

        adjacency, all_nodes = self._get_undirected_adjacency(project_id)

        if source_id not in all_nodes or target_id not in all_nodes:
            return InfluencePath(
                source_id=source_id,
                target_id=target_id,
                path=[],
                path_length=0,
                exists=False
            )

        if source_id == target_id:
            return InfluencePath(
                source_id=source_id,
                target_id=target_id,
                path=[InfluencePathStep(
                    entity_id=source_id,
                    relationship_type=None,
                    distance_from_source=0
                )],
                path_length=0,
                exists=True
            )

        # BFS to find shortest path
        visited = {source_id}
        queue = deque([(source_id, [source_id])])

        while queue:
            current, path = queue.popleft()

            if len(path) > max_depth:
                continue

            for neighbor in adjacency.get(current, set()):
                if neighbor == target_id:
                    # Found the target
                    full_path = path + [neighbor]
                    path_steps = []
                    for i, node_id in enumerate(full_path):
                        rel_type = "RELATED_TO" if i < len(full_path) - 1 else None
                        path_steps.append(InfluencePathStep(
                            entity_id=node_id,
                            relationship_type=rel_type,
                            distance_from_source=i
                        ))

                    return InfluencePath(
                        source_id=source_id,
                        target_id=target_id,
                        path=path_steps,
                        path_length=len(full_path) - 1,
                        exists=True
                    )

                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))

        # No path found
        return InfluencePath(
            source_id=source_id,
            target_id=target_id,
            path=[],
            path_length=0,
            exists=False
        )

    def find_all_paths(
        self,
        project_id: str,
        source_id: str,
        target_id: str,
        max_depth: int = 5,
        max_paths: int = 10
    ) -> List[InfluencePath]:
        """
        Find multiple paths between source and target entities.

        Args:
            project_id: Project ID or safe_name
            source_id: Starting entity ID
            target_id: Destination entity ID
            max_depth: Maximum path length
            max_paths: Maximum number of paths to return

        Returns:
            List of InfluencePath objects
        """
        adjacency, all_nodes = self._get_undirected_adjacency(project_id)

        if source_id not in all_nodes or target_id not in all_nodes:
            return []

        paths = []

        def dfs(current: str, path: List[str], visited: Set[str]):
            if len(paths) >= max_paths:
                return
            if len(path) > max_depth + 1:
                return

            if current == target_id:
                path_steps = []
                for i, node_id in enumerate(path):
                    rel_type = "RELATED_TO" if i < len(path) - 1 else None
                    path_steps.append(InfluencePathStep(
                        entity_id=node_id,
                        relationship_type=rel_type,
                        distance_from_source=i
                    ))
                paths.append(InfluencePath(
                    source_id=source_id,
                    target_id=target_id,
                    path=path_steps,
                    path_length=len(path) - 1,
                    exists=True
                ))
                return

            for neighbor in adjacency.get(current, set()):
                if neighbor not in visited:
                    visited.add(neighbor)
                    dfs(neighbor, path + [neighbor], visited)
                    visited.remove(neighbor)

        dfs(source_id, [source_id], {source_id})

        # Sort by path length
        paths.sort(key=lambda p: p.path_length)

        return paths[:max_paths]

    # =========================================================================
    # KEY ENTITY IDENTIFICATION
    # =========================================================================

    def find_key_entities(
        self,
        project_id: str,
        top_n: int = 10
    ) -> List[KeyEntityResult]:
        """
        Find entities that are critical to network connectivity.

        Identifies:
        - Articulation points: Entities whose removal disconnects the graph
        - Bridge endpoints: Entities connected by bridge edges
        - High-degree hubs: Entities with many connections

        Args:
            project_id: Project ID or safe_name
            top_n: Maximum number of key entities to return

        Returns:
            List of KeyEntityResult objects sorted by importance
        """
        logger.info(f"Finding key entities in project {project_id}")

        adjacency, all_nodes = self._get_undirected_adjacency(project_id)

        if not all_nodes:
            return []

        key_entities: Dict[str, KeyEntityResult] = {}

        # Find articulation points
        articulation_points = self._find_articulation_points(adjacency, all_nodes)
        for node_id in articulation_points:
            components = self._count_components_without_node(adjacency, all_nodes, node_id)
            key_entities[node_id] = KeyEntityResult(
                entity_id=node_id,
                importance_score=1.0,  # Articulation points are highly important
                reason=KeyEntityReason.ARTICULATION_POINT,
                components_if_removed=components,
                affected_entities_count=len(all_nodes) - 1
            )

        # Find bridge endpoints
        bridges = self._find_bridges(adjacency, all_nodes)
        for node1, node2 in bridges:
            for node_id in [node1, node2]:
                if node_id not in key_entities:
                    key_entities[node_id] = KeyEntityResult(
                        entity_id=node_id,
                        importance_score=0.8,
                        reason=KeyEntityReason.BRIDGE_ENDPOINT,
                        components_if_removed=None,
                        affected_entities_count=None
                    )

        # Find high-degree nodes (hubs)
        degrees = [(node, len(adjacency.get(node, set()))) for node in all_nodes]
        degrees.sort(key=lambda x: x[1], reverse=True)

        # Calculate average degree for comparison
        avg_degree = sum(d for _, d in degrees) / len(degrees) if degrees else 0

        for node_id, degree in degrees:
            if node_id not in key_entities and degree > avg_degree * 2:
                key_entities[node_id] = KeyEntityResult(
                    entity_id=node_id,
                    importance_score=min(0.7, degree / (max(d for _, d in degrees) or 1)),
                    reason=KeyEntityReason.HIGH_DEGREE,
                    components_if_removed=None,
                    affected_entities_count=degree
                )

        # Sort by importance and return top_n
        sorted_entities = sorted(
            key_entities.values(),
            key=lambda x: x.importance_score,
            reverse=True
        )

        return sorted_entities[:top_n]

    def _find_articulation_points(
        self,
        adjacency: Dict[str, Set[str]],
        all_nodes: Set[str]
    ) -> Set[str]:
        """
        Find articulation points using Tarjan's algorithm.

        An articulation point is a vertex whose removal increases the
        number of connected components.
        """
        if not all_nodes:
            return set()

        articulation_points = set()
        visited = set()
        discovery_time = {}
        low = {}
        parent = {}
        time_counter = [0]

        def dfs(node: str):
            visited.add(node)
            discovery_time[node] = low[node] = time_counter[0]
            time_counter[0] += 1
            children = 0

            for neighbor in adjacency.get(node, set()):
                if neighbor not in visited:
                    children += 1
                    parent[neighbor] = node
                    dfs(neighbor)
                    low[node] = min(low[node], low[neighbor])

                    # Check articulation point conditions
                    if parent.get(node) is None and children > 1:
                        articulation_points.add(node)
                    if parent.get(node) is not None and low[neighbor] >= discovery_time[node]:
                        articulation_points.add(node)
                elif neighbor != parent.get(node):
                    low[node] = min(low[node], discovery_time[neighbor])

        # Run DFS from each unvisited node (handles disconnected graphs)
        for node in all_nodes:
            if node not in visited:
                parent[node] = None
                dfs(node)

        return articulation_points

    def _find_bridges(
        self,
        adjacency: Dict[str, Set[str]],
        all_nodes: Set[str]
    ) -> List[Tuple[str, str]]:
        """
        Find bridge edges using Tarjan's algorithm.

        A bridge is an edge whose removal increases the number of
        connected components.
        """
        if not all_nodes:
            return []

        bridges = []
        visited = set()
        discovery_time = {}
        low = {}
        parent = {}
        time_counter = [0]

        def dfs(node: str):
            visited.add(node)
            discovery_time[node] = low[node] = time_counter[0]
            time_counter[0] += 1

            for neighbor in adjacency.get(node, set()):
                if neighbor not in visited:
                    parent[neighbor] = node
                    dfs(neighbor)
                    low[node] = min(low[node], low[neighbor])

                    # Check bridge condition
                    if low[neighbor] > discovery_time[node]:
                        bridges.append((node, neighbor))
                elif neighbor != parent.get(node):
                    low[node] = min(low[node], discovery_time[neighbor])

        for node in all_nodes:
            if node not in visited:
                parent[node] = None
                dfs(node)

        return bridges

    def _count_components_without_node(
        self,
        adjacency: Dict[str, Set[str]],
        all_nodes: Set[str],
        exclude_node: str
    ) -> int:
        """
        Count connected components if a node is removed.
        """
        remaining_nodes = all_nodes - {exclude_node}
        if not remaining_nodes:
            return 0

        visited = set()
        components = 0

        def dfs(node: str):
            visited.add(node)
            for neighbor in adjacency.get(node, set()):
                if neighbor != exclude_node and neighbor not in visited:
                    dfs(neighbor)

        for node in remaining_nodes:
            if node not in visited:
                dfs(node)
                components += 1

        return components

    # =========================================================================
    # BETWEENNESS CENTRALITY
    # =========================================================================

    def calculate_betweenness_centrality(
        self,
        project_id: str,
        top_n: int = 10,
        normalized: bool = True
    ) -> InfluenceReport:
        """
        Calculate betweenness centrality for all entities.

        Betweenness centrality measures how often a node appears on
        shortest paths between other nodes. High betweenness indicates
        the entity is a broker or gateway in the network.

        Args:
            project_id: Project ID or safe_name
            top_n: Number of top entities to return
            normalized: Whether to normalize scores

        Returns:
            InfluenceReport with betweenness centrality scores
        """
        logger.info(f"Calculating betweenness centrality for project {project_id}")

        adjacency, all_nodes = self._get_undirected_adjacency(project_id)

        if not all_nodes:
            return InfluenceReport(
                algorithm="betweenness_centrality",
                scores=[],
                top_n=top_n,
                total_entities=0,
                parameters={"normalized": normalized}
            )

        n = len(all_nodes)
        betweenness = {node: 0.0 for node in all_nodes}

        # Brandes' algorithm for betweenness centrality
        for source in all_nodes:
            # Single-source shortest paths
            stack = []
            predecessors = {node: [] for node in all_nodes}
            sigma = {node: 0 for node in all_nodes}
            sigma[source] = 1
            distance = {node: -1 for node in all_nodes}
            distance[source] = 0

            queue = deque([source])

            while queue:
                current = queue.popleft()
                stack.append(current)

                for neighbor in adjacency.get(current, set()):
                    # First visit
                    if distance[neighbor] < 0:
                        distance[neighbor] = distance[current] + 1
                        queue.append(neighbor)

                    # Shortest path to neighbor via current
                    if distance[neighbor] == distance[current] + 1:
                        sigma[neighbor] += sigma[current]
                        predecessors[neighbor].append(current)

            # Accumulation
            delta = {node: 0.0 for node in all_nodes}
            while stack:
                current = stack.pop()
                for pred in predecessors[current]:
                    delta[pred] += (sigma[pred] / sigma[current]) * (1 + delta[current])
                if current != source:
                    betweenness[current] += delta[current]

        # Normalize if requested
        if normalized and n > 2:
            norm_factor = 2.0 / ((n - 1) * (n - 2))
            betweenness = {node: score * norm_factor for node, score in betweenness.items()}

        # Sort and create ranking
        sorted_nodes = sorted(betweenness.items(), key=lambda x: x[1], reverse=True)

        influence_scores = []
        for rank, (node_id, score) in enumerate(sorted_nodes[:top_n], start=1):
            influence_scores.append(InfluenceScore(
                entity_id=node_id,
                score=round(score, 6),
                rank=rank
            ))

        return InfluenceReport(
            algorithm="betweenness_centrality",
            scores=influence_scores,
            top_n=top_n,
            total_entities=n,
            parameters={"normalized": normalized}
        )


# =============================================================================
# MODULE-LEVEL FUNCTIONS
# =============================================================================


# Singleton instance
_influence_service_instance: Optional[InfluenceService] = None


def get_influence_service(neo4j_handler) -> InfluenceService:
    """
    Factory function to get or create an InfluenceService instance.

    Args:
        neo4j_handler: Neo4j database handler

    Returns:
        InfluenceService instance
    """
    global _influence_service_instance

    if _influence_service_instance is None:
        _influence_service_instance = InfluenceService(neo4j_handler)

    return _influence_service_instance


def reset_influence_service() -> None:
    """Reset the singleton instance (useful for testing)."""
    global _influence_service_instance
    _influence_service_instance = None
