"""
Community Detection Service for Basset Hound OSINT Platform.

This module provides advanced graph analytics focused on community detection:
- Louvain community detection (modularity-based)
- Label propagation (fast, for large graphs)
- Connected components analysis
- Community statistics and metrics

Neo4j GDS is guaranteed to be available via deployment configuration.
Python implementations are used for in-memory analysis without Neo4j.
"""

import logging
import random
import time
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from pydantic import BaseModel, Field, ConfigDict

logger = logging.getLogger(__name__)


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class Community(BaseModel):
    """Represents a detected community in the graph."""

    id: str = Field(..., description="Unique community identifier")
    member_ids: List[str] = Field(
        default_factory=list,
        description="List of entity IDs belonging to this community"
    )
    size: int = Field(default=0, ge=0, description="Number of members in the community")
    density: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Edge density within community (0-1)"
    )

    model_config = ConfigDict(frozen=False)

    def __init__(self, **data):
        super().__init__(**data)
        # Auto-calculate size if not provided
        if self.size == 0 and self.member_ids:
            object.__setattr__(self, 'size', len(self.member_ids))


class CommunityDetectionResult(BaseModel):
    """Result of a community detection algorithm."""

    algorithm: str = Field(..., description="Name of the algorithm used")
    communities: List[Community] = Field(
        default_factory=list,
        description="List of detected communities"
    )
    modularity_score: Optional[float] = Field(
        default=None,
        ge=-1.0,
        le=1.0,
        description="Modularity score of the partition (if applicable)"
    )
    execution_time: float = Field(
        default=0.0,
        ge=0.0,
        description="Algorithm execution time in seconds"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional algorithm-specific metadata"
    )

    model_config = ConfigDict(frozen=False)


class CommunityStats(BaseModel):
    """Statistics about detected communities."""

    total_communities: int = Field(default=0, ge=0, description="Total number of communities")
    avg_size: float = Field(default=0.0, ge=0.0, description="Average community size")
    largest_community: int = Field(default=0, ge=0, description="Size of the largest community")
    smallest_community: int = Field(default=0, ge=0, description="Size of the smallest community")
    isolated_nodes: int = Field(default=0, ge=0, description="Number of isolated nodes")
    size_distribution: Dict[str, int] = Field(
        default_factory=dict,
        description="Distribution of community sizes (size range -> count)"
    )
    inter_community_edges: int = Field(
        default=0,
        ge=0,
        description="Number of edges between different communities"
    )
    intra_community_edges: int = Field(
        default=0,
        ge=0,
        description="Number of edges within communities"
    )
    avg_density: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Average density across all communities"
    )

    model_config = ConfigDict(frozen=False)


class ComponentType(str, Enum):
    """Type of connected component to find."""
    WEAKLY_CONNECTED = "weakly_connected"
    STRONGLY_CONNECTED = "strongly_connected"


class ConnectedComponent(BaseModel):
    """Represents a connected component in the graph."""

    id: str = Field(..., description="Component identifier")
    member_ids: List[str] = Field(
        default_factory=list,
        description="Entity IDs in this component"
    )
    size: int = Field(default=0, ge=0, description="Number of nodes in component")
    is_isolated: bool = Field(
        default=False,
        description="True if component has single node with no edges"
    )

    model_config = ConfigDict(frozen=False)


class ConnectedComponentsResult(BaseModel):
    """Result of connected components analysis."""

    component_type: ComponentType = Field(..., description="Type of components found")
    components: List[ConnectedComponent] = Field(
        default_factory=list,
        description="List of connected components"
    )
    total_components: int = Field(default=0, ge=0, description="Total number of components")
    largest_component_size: int = Field(default=0, ge=0, description="Size of largest component")
    isolated_count: int = Field(default=0, ge=0, description="Number of isolated nodes")
    execution_time: float = Field(default=0.0, ge=0.0, description="Execution time in seconds")

    model_config = ConfigDict(frozen=False)


# =============================================================================
# COMMUNITY DETECTION ALGORITHMS (PYTHON IMPLEMENTATIONS)
# =============================================================================

class LouvainAlgorithm:
    """
    Python implementation of the Louvain community detection algorithm.

    The Louvain method is a greedy optimization method that maximizes
    modularity - a measure of the density of links inside communities
    compared to links between communities.
    """

    def __init__(self, resolution: float = 1.0, random_seed: int = 42):
        """
        Initialize the Louvain algorithm.

        Args:
            resolution: Resolution parameter (higher = more/smaller communities)
            random_seed: Random seed for reproducibility
        """
        self.resolution = resolution
        self._random = random.Random(random_seed)

    def detect(
        self,
        nodes: List[str],
        edges: List[Tuple[str, str]],
        max_iterations: int = 100
    ) -> Tuple[Dict[str, int], float]:
        """
        Detect communities using the Louvain algorithm.

        Args:
            nodes: List of node IDs
            edges: List of (source, target) tuples
            max_iterations: Maximum iterations per phase

        Returns:
            Tuple of (node_to_community mapping, modularity score)
        """
        if not nodes:
            return {}, 0.0

        # Build adjacency list with weights
        adjacency: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        for source, target in edges:
            adjacency[source][target] += 1.0
            adjacency[target][source] += 1.0  # Undirected

        # Calculate total edge weight (2m in modularity formula)
        total_weight = sum(
            sum(neighbors.values()) for neighbors in adjacency.values()
        )
        if total_weight == 0:
            # No edges - each node is its own community
            return {node: i for i, node in enumerate(nodes)}, 0.0

        # Initialize: each node is its own community
        node_to_community = {node: i for i, node in enumerate(nodes)}
        community_to_nodes: Dict[int, Set[str]] = {
            i: {node} for i, node in enumerate(nodes)
        }

        # Calculate initial node degrees (sum of edge weights)
        node_degrees: Dict[str, float] = {
            node: sum(adjacency[node].values()) for node in nodes
        }

        # Calculate community total weights
        community_weights: Dict[int, float] = {
            i: node_degrees[node] for i, node in enumerate(nodes)
        }

        # Phase 1: Local optimization (move nodes to best community)
        improved = True
        iteration = 0

        while improved and iteration < max_iterations:
            improved = False
            iteration += 1

            # Randomize node order for better convergence
            shuffled_nodes = list(nodes)
            self._random.shuffle(shuffled_nodes)

            for node in shuffled_nodes:
                current_community = node_to_community[node]

                # Calculate modularity change for moving to each neighbor's community
                best_community = current_community
                best_delta = 0.0

                # Get unique communities of neighbors
                neighbor_communities = set()
                for neighbor in adjacency[node]:
                    neighbor_communities.add(node_to_community[neighbor])
                neighbor_communities.add(current_community)  # Include current

                # Remove node from current community temporarily
                community_to_nodes[current_community].remove(node)
                community_weights[current_community] -= node_degrees[node]

                for target_community in neighbor_communities:
                    delta = self._calculate_modularity_delta(
                        node,
                        target_community,
                        adjacency,
                        node_degrees,
                        community_to_nodes,
                        community_weights,
                        total_weight
                    )

                    if delta > best_delta:
                        best_delta = delta
                        best_community = target_community

                # Move node to best community
                node_to_community[node] = best_community
                community_to_nodes[best_community].add(node)
                community_weights[best_community] += node_degrees[node]

                if best_community != current_community:
                    improved = True

        # Clean up empty communities and renumber
        final_communities: Dict[str, int] = {}
        community_id = 0
        community_mapping: Dict[int, int] = {}

        for node in nodes:
            old_community = node_to_community[node]
            if old_community not in community_mapping:
                community_mapping[old_community] = community_id
                community_id += 1
            final_communities[node] = community_mapping[old_community]

        # Calculate final modularity
        modularity = self._calculate_modularity(
            final_communities, adjacency, node_degrees, total_weight
        )

        return final_communities, modularity

    def _calculate_modularity_delta(
        self,
        node: str,
        target_community: int,
        adjacency: Dict[str, Dict[str, float]],
        node_degrees: Dict[str, float],
        community_to_nodes: Dict[int, Set[str]],
        community_weights: Dict[int, float],
        total_weight: float
    ) -> float:
        """Calculate change in modularity from moving node to target community."""
        # Sum of edge weights from node to target community
        k_i_in = sum(
            adjacency[node].get(member, 0.0)
            for member in community_to_nodes[target_community]
        )

        # Node degree and community total weight
        k_i = node_degrees[node]
        sigma_tot = community_weights[target_community]

        # Modularity gain formula
        delta = (
            k_i_in / total_weight
            - self.resolution * (k_i * sigma_tot) / (total_weight * total_weight / 2)
        )

        return delta

    def _calculate_modularity(
        self,
        communities: Dict[str, int],
        adjacency: Dict[str, Dict[str, float]],
        node_degrees: Dict[str, float],
        total_weight: float
    ) -> float:
        """Calculate modularity of a partition."""
        if total_weight == 0:
            return 0.0

        modularity = 0.0

        for node1, community1 in communities.items():
            for node2, community2 in communities.items():
                if community1 == community2:
                    # Edge weight (0 if no edge)
                    a_ij = adjacency[node1].get(node2, 0.0)
                    # Expected edges based on degree product
                    k_i_k_j = node_degrees[node1] * node_degrees[node2]
                    expected = k_i_k_j / total_weight

                    modularity += a_ij - self.resolution * expected

        modularity /= total_weight
        return modularity


class LabelPropagation:
    """
    Label Propagation algorithm for community detection.

    A fast, near-linear time algorithm where each node adopts the label
    most common among its neighbors.
    """

    def __init__(self, random_seed: int = 42):
        """Initialize with random seed for tie-breaking."""
        self._random = random.Random(random_seed)

    def detect(
        self,
        nodes: List[str],
        edges: List[Tuple[str, str]],
        max_iterations: int = 100
    ) -> Dict[str, int]:
        """
        Detect communities using label propagation.

        Args:
            nodes: List of node IDs
            edges: List of (source, target) tuples
            max_iterations: Maximum iterations before stopping

        Returns:
            Dictionary mapping node IDs to community IDs
        """
        if not nodes:
            return {}

        # Build adjacency list
        adjacency: Dict[str, Set[str]] = defaultdict(set)
        for source, target in edges:
            adjacency[source].add(target)
            adjacency[target].add(source)

        # Initialize: each node has unique label
        labels = {node: i for i, node in enumerate(nodes)}

        # Iterate until convergence or max iterations
        for iteration in range(max_iterations):
            changed = False

            # Process nodes in random order
            shuffled_nodes = list(nodes)
            self._random.shuffle(shuffled_nodes)

            for node in shuffled_nodes:
                neighbors = adjacency.get(node, set())
                if not neighbors:
                    continue

                # Count neighbor labels
                label_counts: Dict[int, int] = defaultdict(int)
                for neighbor in neighbors:
                    label_counts[labels[neighbor]] += 1

                # Find most common label(s)
                max_count = max(label_counts.values())
                max_labels = [
                    label for label, count in label_counts.items()
                    if count == max_count
                ]

                # Break ties randomly
                new_label = self._random.choice(max_labels)

                if labels[node] != new_label:
                    labels[node] = new_label
                    changed = True

            if not changed:
                break

        # Renumber labels to be consecutive integers
        unique_labels = set(labels.values())
        label_map = {old: new for new, old in enumerate(sorted(unique_labels))}
        return {node: label_map[label] for node, label in labels.items()}


class ConnectedComponentsFinder:
    """Find connected components in a graph using DFS/BFS."""

    def find_weakly_connected(
        self,
        nodes: List[str],
        edges: List[Tuple[str, str]]
    ) -> List[Set[str]]:
        """
        Find weakly connected components (ignoring edge direction).

        Args:
            nodes: List of node IDs
            edges: List of (source, target) tuples

        Returns:
            List of sets, each set contains node IDs in a component
        """
        if not nodes:
            return []

        # Build undirected adjacency
        adjacency: Dict[str, Set[str]] = defaultdict(set)
        for source, target in edges:
            adjacency[source].add(target)
            adjacency[target].add(source)

        visited: Set[str] = set()
        components: List[Set[str]] = []

        for start_node in nodes:
            if start_node in visited:
                continue

            # BFS from start_node
            component: Set[str] = set()
            queue = [start_node]

            while queue:
                node = queue.pop(0)
                if node in visited:
                    continue

                visited.add(node)
                component.add(node)

                for neighbor in adjacency[node]:
                    if neighbor not in visited:
                        queue.append(neighbor)

            components.append(component)

        return components

    def find_strongly_connected(
        self,
        nodes: List[str],
        edges: List[Tuple[str, str]]
    ) -> List[Set[str]]:
        """
        Find strongly connected components using Kosaraju's algorithm.

        Args:
            nodes: List of node IDs
            edges: List of (source, target) directed tuples

        Returns:
            List of sets, each set contains node IDs in a strongly connected component
        """
        if not nodes:
            return []

        # Build directed adjacency and reverse adjacency
        adjacency: Dict[str, Set[str]] = defaultdict(set)
        reverse_adjacency: Dict[str, Set[str]] = defaultdict(set)

        for source, target in edges:
            adjacency[source].add(target)
            reverse_adjacency[target].add(source)

        # First DFS pass: get finish order
        visited: Set[str] = set()
        finish_order: List[str] = []

        def dfs_first(node: str):
            stack = [(node, False)]
            while stack:
                current, processed = stack.pop()
                if processed:
                    finish_order.append(current)
                    continue
                if current in visited:
                    continue
                visited.add(current)
                stack.append((current, True))
                for neighbor in adjacency[current]:
                    if neighbor not in visited:
                        stack.append((neighbor, False))

        for node in nodes:
            if node not in visited:
                dfs_first(node)

        # Second DFS pass: find SCCs in reverse order
        visited.clear()
        components: List[Set[str]] = []

        def dfs_second(start: str) -> Set[str]:
            component: Set[str] = set()
            stack = [start]
            while stack:
                node = stack.pop()
                if node in visited:
                    continue
                visited.add(node)
                component.add(node)
                for neighbor in reverse_adjacency[node]:
                    if neighbor not in visited:
                        stack.append(neighbor)
            return component

        for node in reversed(finish_order):
            if node not in visited:
                scc = dfs_second(node)
                components.append(scc)

        return components


# =============================================================================
# MAIN SERVICE CLASS
# =============================================================================

class CommunityDetectionService:
    """
    Community Detection Service for Basset Hound OSINT Platform.

    Provides various community detection algorithms:
    - Louvain: Modularity-based, good quality results
    - Label Propagation: Fast, good for large graphs
    - Connected Components: Find isolated subgraphs

    Neo4j GDS is guaranteed via deployment. Python implementations
    provide fallback for testing and in-memory analysis.
    """

    def __init__(self, neo4j_handler=None):
        """
        Initialize the Community Detection Service.

        Args:
            neo4j_handler: Async Neo4j database handler (AsyncNeo4jService)
        """
        self.neo4j_handler = neo4j_handler
        self._gds_available: Optional[bool] = None

        # Python algorithm implementations
        self._louvain = LouvainAlgorithm()
        self._label_propagation = LabelPropagation()
        self._components_finder = ConnectedComponentsFinder()

    async def _check_gds_available(self) -> bool:
        """Check if Neo4j GDS library is available."""
        if self._gds_available is not None:
            return self._gds_available

        if not self.neo4j_handler:
            self._gds_available = False
            return False

        try:
            async with self.neo4j_handler.session() as session:
                result = await session.run(
                    "RETURN gds.version() AS version"
                )
                record = await result.single()
                self._gds_available = record is not None
                if self._gds_available:
                    logger.info(f"Neo4j GDS available: version {record['version']}")
        except Exception as e:
            logger.debug(f"Neo4j GDS not available: {e}")
            self._gds_available = False

        return self._gds_available

    async def _fetch_graph_data(
        self,
        project_safe_name: str
    ) -> Tuple[List[str], List[Tuple[str, str]]]:
        """
        Fetch graph data from Neo4j for a project.

        Returns:
            Tuple of (node_ids, edge_tuples)
        """
        if not self.neo4j_handler:
            return [], []

        async with self.neo4j_handler.session() as session:
            # Get all entities in project
            entities_result = await session.run("""
                MATCH (project:Project {safe_name: $project_safe_name})
                      -[:HAS_PERSON]->(person:Person)
                RETURN person.id AS id, person.profile AS profile
            """, project_safe_name=project_safe_name)

            entities = await entities_result.data()

            nodes: List[str] = []
            node_set: Set[str] = set()
            edges: List[Tuple[str, str]] = []

            for record in entities:
                entity_id = record["id"]
                nodes.append(entity_id)
                node_set.add(entity_id)

            # Extract relationships from profiles
            for record in entities:
                entity_id = record["id"]
                profile = record.get("profile") or {}

                if isinstance(profile, str):
                    import json
                    try:
                        profile = json.loads(profile)
                    except (json.JSONDecodeError, TypeError):
                        profile = {}

                tagged_section = profile.get("Tagged People", {})
                tagged_ids = tagged_section.get("tagged_people", []) or []

                if not isinstance(tagged_ids, list):
                    tagged_ids = [tagged_ids] if tagged_ids else []

                for target_id in tagged_ids:
                    if target_id in node_set:
                        edges.append((entity_id, target_id))

            return nodes, edges

    async def detect_louvain(
        self,
        project_safe_name: str,
        resolution: float = 1.0,
        max_iterations: int = 100
    ) -> CommunityDetectionResult:
        """
        Detect communities using the Louvain algorithm.

        Args:
            project_safe_name: Project identifier
            resolution: Resolution parameter (higher = more/smaller communities)
            max_iterations: Maximum iterations

        Returns:
            CommunityDetectionResult with detected communities
        """
        start_time = time.time()

        # Fetch graph data
        nodes, edges = await self._fetch_graph_data(project_safe_name)

        if not nodes:
            return CommunityDetectionResult(
                algorithm="louvain",
                communities=[],
                modularity_score=0.0,
                execution_time=time.time() - start_time,
                metadata={"resolution": resolution}
            )

        # Try GDS first if available
        gds_available = await self._check_gds_available()

        if gds_available and self.neo4j_handler:
            try:
                result = await self._louvain_gds(
                    project_safe_name, resolution, max_iterations
                )
                result.execution_time = time.time() - start_time
                return result
            except Exception as e:
                logger.info(f"Using Python Louvain (GDS unavailable: {e})")

        # Fall back to Python implementation
        louvain = LouvainAlgorithm(resolution=resolution)
        node_to_community, modularity = louvain.detect(nodes, edges, max_iterations)

        # Group nodes by community
        community_members: Dict[int, List[str]] = defaultdict(list)
        for node, community_id in node_to_community.items():
            community_members[community_id].append(node)

        # Build Community objects with density calculation
        communities = []
        for comm_id, members in community_members.items():
            density = self._calculate_community_density(members, edges)
            communities.append(Community(
                id=f"community_{comm_id}",
                member_ids=members,
                size=len(members),
                density=density
            ))

        # Sort by size descending
        communities.sort(key=lambda c: c.size, reverse=True)

        return CommunityDetectionResult(
            algorithm="louvain",
            communities=communities,
            modularity_score=modularity,
            execution_time=time.time() - start_time,
            metadata={
                "resolution": resolution,
                "implementation": "python",
                "iterations": max_iterations
            }
        )

    async def _louvain_gds(
        self,
        project_safe_name: str,
        resolution: float,
        max_iterations: int
    ) -> CommunityDetectionResult:
        """Execute Louvain using Neo4j GDS."""
        async with self.neo4j_handler.session() as session:
            # Create in-memory graph projection
            graph_name = f"community_graph_{project_safe_name}"

            # Drop existing projection if any
            await session.run(f"""
                CALL gds.graph.drop('{graph_name}', false)
            """)

            # Create projection (this is a simplified approach)
            # In production, you'd project the actual relationships
            await session.run("""
                CALL gds.graph.project.cypher(
                    $graph_name,
                    'MATCH (p:Project {safe_name: $project})-[:HAS_PERSON]->(n:Person) RETURN id(n) AS id',
                    'MATCH (p:Project {safe_name: $project})-[:HAS_PERSON]->(n:Person)
                     WHERE n.profile IS NOT NULL
                     UNWIND keys(n.profile) AS section
                     WITH n, n.profile[section] AS sectionData
                     WHERE sectionData.tagged_people IS NOT NULL
                     UNWIND sectionData.tagged_people AS targetId
                     MATCH (t:Person {id: targetId})
                     RETURN id(n) AS source, id(t) AS target',
                    {validateRelationships: false}
                )
            """, graph_name=graph_name, project=project_safe_name)

            # Run Louvain
            result = await session.run("""
                CALL gds.louvain.stream($graph_name, {
                    maxLevels: $max_iterations,
                    tolerance: 0.0001,
                    includeIntermediateCommunities: false
                })
                YIELD nodeId, communityId
                RETURN gds.util.asNode(nodeId).id AS entityId, communityId
            """, graph_name=graph_name, max_iterations=max_iterations)

            records = await result.data()

            # Clean up projection
            await session.run(f"CALL gds.graph.drop('{graph_name}', false)")

            # Process results
            community_members: Dict[int, List[str]] = defaultdict(list)
            for record in records:
                community_members[record["communityId"]].append(record["entityId"])

            communities = [
                Community(
                    id=f"community_{comm_id}",
                    member_ids=members,
                    size=len(members),
                    density=0.0  # Would need additional query for density
                )
                for comm_id, members in community_members.items()
            ]
            communities.sort(key=lambda c: c.size, reverse=True)

            return CommunityDetectionResult(
                algorithm="louvain",
                communities=communities,
                modularity_score=None,  # GDS stream doesn't return modularity
                execution_time=0.0,
                metadata={
                    "resolution": resolution,
                    "implementation": "neo4j_gds"
                }
            )

    async def detect_label_propagation(
        self,
        project_safe_name: str,
        max_iterations: int = 100
    ) -> CommunityDetectionResult:
        """
        Detect communities using Label Propagation algorithm.

        Fast algorithm good for large graphs. Each node adopts the most
        common label among its neighbors iteratively.

        Args:
            project_safe_name: Project identifier
            max_iterations: Maximum iterations

        Returns:
            CommunityDetectionResult with detected communities
        """
        start_time = time.time()

        nodes, edges = await self._fetch_graph_data(project_safe_name)

        if not nodes:
            return CommunityDetectionResult(
                algorithm="label_propagation",
                communities=[],
                modularity_score=None,
                execution_time=time.time() - start_time
            )

        # Use Python implementation
        node_to_community = self._label_propagation.detect(nodes, edges, max_iterations)

        # Group nodes by community
        community_members: Dict[int, List[str]] = defaultdict(list)
        for node, community_id in node_to_community.items():
            community_members[community_id].append(node)

        # Build Community objects
        communities = []
        for comm_id, members in community_members.items():
            density = self._calculate_community_density(members, edges)
            communities.append(Community(
                id=f"community_{comm_id}",
                member_ids=members,
                size=len(members),
                density=density
            ))

        communities.sort(key=lambda c: c.size, reverse=True)

        return CommunityDetectionResult(
            algorithm="label_propagation",
            communities=communities,
            modularity_score=None,  # Label propagation doesn't optimize modularity
            execution_time=time.time() - start_time,
            metadata={
                "max_iterations": max_iterations,
                "implementation": "python"
            }
        )

    async def find_connected_components(
        self,
        project_safe_name: str,
        component_type: ComponentType = ComponentType.WEAKLY_CONNECTED
    ) -> ConnectedComponentsResult:
        """
        Find connected components in the graph.

        Args:
            project_safe_name: Project identifier
            component_type: Type of components to find

        Returns:
            ConnectedComponentsResult with found components
        """
        start_time = time.time()

        nodes, edges = await self._fetch_graph_data(project_safe_name)

        if not nodes:
            return ConnectedComponentsResult(
                component_type=component_type,
                components=[],
                total_components=0,
                largest_component_size=0,
                isolated_count=0,
                execution_time=time.time() - start_time
            )

        # Find components
        if component_type == ComponentType.WEAKLY_CONNECTED:
            raw_components = self._components_finder.find_weakly_connected(nodes, edges)
        else:
            raw_components = self._components_finder.find_strongly_connected(nodes, edges)

        # Build result
        components = []
        isolated_count = 0
        largest_size = 0

        for i, members in enumerate(raw_components):
            size = len(members)
            is_isolated = size == 1

            if is_isolated:
                isolated_count += 1

            if size > largest_size:
                largest_size = size

            components.append(ConnectedComponent(
                id=f"component_{i}",
                member_ids=list(members),
                size=size,
                is_isolated=is_isolated
            ))

        # Sort by size descending
        components.sort(key=lambda c: c.size, reverse=True)

        return ConnectedComponentsResult(
            component_type=component_type,
            components=components,
            total_components=len(components),
            largest_component_size=largest_size,
            isolated_count=isolated_count,
            execution_time=time.time() - start_time
        )

    async def get_community_stats(
        self,
        communities: List[Community],
        project_safe_name: Optional[str] = None
    ) -> CommunityStats:
        """
        Calculate statistics for a set of communities.

        Args:
            communities: List of Community objects
            project_safe_name: Optional project to fetch edge data for inter/intra counts

        Returns:
            CommunityStats with computed statistics
        """
        if not communities:
            return CommunityStats()

        sizes = [c.size for c in communities]
        total = len(communities)

        # Size distribution buckets
        distribution: Dict[str, int] = defaultdict(int)
        for size in sizes:
            if size == 1:
                bucket = "1"
            elif size <= 5:
                bucket = "2-5"
            elif size <= 10:
                bucket = "6-10"
            elif size <= 25:
                bucket = "11-25"
            elif size <= 50:
                bucket = "26-50"
            else:
                bucket = "51+"
            distribution[bucket] += 1

        # Calculate inter/intra edges if project provided
        inter_edges = 0
        intra_edges = 0

        if project_safe_name:
            nodes, edges = await self._fetch_graph_data(project_safe_name)

            # Build node to community mapping
            node_to_community: Dict[str, str] = {}
            for community in communities:
                for member in community.member_ids:
                    node_to_community[member] = community.id

            for source, target in edges:
                source_comm = node_to_community.get(source)
                target_comm = node_to_community.get(target)

                if source_comm and target_comm:
                    if source_comm == target_comm:
                        intra_edges += 1
                    else:
                        inter_edges += 1

        # Calculate average density
        densities = [c.density for c in communities if c.density > 0]
        avg_density = sum(densities) / len(densities) if densities else 0.0

        # Count isolated nodes (communities of size 1)
        isolated = sum(1 for c in communities if c.size == 1)

        return CommunityStats(
            total_communities=total,
            avg_size=sum(sizes) / total if total > 0 else 0.0,
            largest_community=max(sizes) if sizes else 0,
            smallest_community=min(sizes) if sizes else 0,
            isolated_nodes=isolated,
            size_distribution=dict(distribution),
            inter_community_edges=inter_edges,
            intra_community_edges=intra_edges,
            avg_density=avg_density
        )

    def _calculate_community_density(
        self,
        members: List[str],
        edges: List[Tuple[str, str]]
    ) -> float:
        """
        Calculate edge density within a community.

        Density = actual edges / possible edges
        For undirected: possible = n*(n-1)/2
        """
        n = len(members)
        if n < 2:
            return 0.0

        member_set = set(members)
        actual_edges = 0

        for source, target in edges:
            if source in member_set and target in member_set:
                actual_edges += 1

        # For undirected graph, divide by 2 if edges are counted twice
        possible_edges = n * (n - 1) / 2

        return actual_edges / possible_edges if possible_edges > 0 else 0.0

    async def detect_all(
        self,
        project_safe_name: str,
        resolution: float = 1.0
    ) -> Dict[str, Any]:
        """
        Run all community detection algorithms and return comparative results.

        Args:
            project_safe_name: Project identifier
            resolution: Resolution parameter for Louvain

        Returns:
            Dictionary with results from each algorithm
        """
        louvain_result = await self.detect_louvain(project_safe_name, resolution)
        lp_result = await self.detect_label_propagation(project_safe_name)
        components_result = await self.find_connected_components(project_safe_name)

        # Get stats for Louvain (usually best quality)
        stats = await self.get_community_stats(
            louvain_result.communities,
            project_safe_name
        )

        return {
            "louvain": louvain_result,
            "label_propagation": lp_result,
            "connected_components": components_result,
            "stats": stats
        }


# =============================================================================
# SINGLETON MANAGEMENT
# =============================================================================

_community_detection_service: Optional[CommunityDetectionService] = None


def get_community_detection_service(
    neo4j_handler=None
) -> CommunityDetectionService:
    """
    Get or create the CommunityDetectionService singleton.

    Args:
        neo4j_handler: Optional async Neo4j handler

    Returns:
        CommunityDetectionService instance
    """
    global _community_detection_service

    if _community_detection_service is None:
        _community_detection_service = CommunityDetectionService(
            neo4j_handler=neo4j_handler
        )
    elif neo4j_handler is not None:
        _community_detection_service.neo4j_handler = neo4j_handler

    return _community_detection_service


def set_community_detection_service(
    service: Optional[CommunityDetectionService]
) -> None:
    """Set the community detection service singleton (useful for testing)."""
    global _community_detection_service
    _community_detection_service = service


def reset_community_detection_service() -> None:
    """Reset the community detection service singleton."""
    global _community_detection_service
    _community_detection_service = None
