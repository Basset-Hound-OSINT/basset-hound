"""
Similarity Scoring Service for Basset Hound OSINT Platform.

This module provides entity similarity analysis capabilities including:
- Structural Similarity (Jaccard index on neighbor sets)
- Cosine Similarity on relationship vectors
- Common Neighbors Analysis
- Role Similarity (SimRank-like iterative algorithm)

All computations are done in pure Python for efficiency with medium-sized graphs
(1000-10000 entities).
"""

import logging
import math
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from pydantic import BaseModel, Field, ConfigDict

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS AND CONSTANTS
# =============================================================================

class SimilarityMethod(str, Enum):
    """Available similarity computation methods."""
    JACCARD = "jaccard"
    COSINE = "cosine"
    COMMON_NEIGHBORS = "common_neighbors"
    SIMRANK = "simrank"
    COMBINED = "combined"  # Weighted combination of multiple methods


# Default weights for combined similarity
DEFAULT_WEIGHTS = {
    SimilarityMethod.JACCARD: 0.3,
    SimilarityMethod.COSINE: 0.3,
    SimilarityMethod.COMMON_NEIGHBORS: 0.2,
    SimilarityMethod.SIMRANK: 0.2,
}


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class SimilarityResult(BaseModel):
    """Result of similarity comparison between two entities."""
    entity1_id: str = Field(..., description="First entity ID")
    entity2_id: str = Field(..., description="Second entity ID")
    score: float = Field(..., ge=0.0, le=1.0, description="Similarity score (0.0 to 1.0)")
    method: SimilarityMethod = Field(..., description="Similarity method used")
    common_neighbors: List[str] = Field(
        default_factory=list,
        description="List of common neighbor entity IDs"
    )
    details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional method-specific details"
    )

    model_config = ConfigDict(frozen=False)


class EntitySimilarityReport(BaseModel):
    """Similarity report for a single entity."""
    entity_id: str = Field(..., description="The entity being analyzed")
    similar_entities: List[SimilarityResult] = Field(
        default_factory=list,
        description="List of similar entities sorted by score"
    )
    top_n: int = Field(default=10, description="Number of results requested")
    method: SimilarityMethod = Field(..., description="Similarity method used")
    total_candidates: int = Field(
        default=0,
        description="Total number of entities considered"
    )

    model_config = ConfigDict(frozen=False)


class SimilarityConfig(BaseModel):
    """Configuration for similarity computation."""
    method: SimilarityMethod = Field(
        default=SimilarityMethod.JACCARD,
        description="Similarity method to use"
    )
    threshold: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score to include in results"
    )
    include_common_neighbors: bool = Field(
        default=True,
        description="Whether to include common neighbor IDs in results"
    )
    top_n: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of similar entities to return"
    )
    # SimRank-specific options
    simrank_iterations: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of iterations for SimRank algorithm"
    )
    simrank_decay: float = Field(
        default=0.8,
        gt=0.0,
        lt=1.0,
        description="Decay factor for SimRank (typically 0.8)"
    )
    # Combined method weights
    weights: Optional[Dict[str, float]] = Field(
        default=None,
        description="Custom weights for combined similarity method"
    )

    model_config = ConfigDict(frozen=False)


class PotentialLink(BaseModel):
    """A potential missing link between entities."""
    entity1_id: str = Field(..., description="First entity ID")
    entity2_id: str = Field(..., description="Second entity ID")
    score: float = Field(..., ge=0.0, le=1.0, description="Link prediction score")
    common_neighbor_count: int = Field(
        default=0,
        description="Number of shared connections"
    )
    common_neighbors: List[str] = Field(
        default_factory=list,
        description="IDs of common neighbors"
    )
    evidence: Dict[str, Any] = Field(
        default_factory=dict,
        description="Supporting evidence for the predicted link"
    )

    model_config = ConfigDict(frozen=False)


# =============================================================================
# SIMILARITY ALGORITHMS
# =============================================================================

class SimilarityAlgorithms:
    """
    Pure Python implementations of similarity algorithms.

    Optimized for medium-sized graphs (1000-10000 entities).
    """

    @staticmethod
    def jaccard_similarity(set1: Set[str], set2: Set[str]) -> float:
        """
        Compute Jaccard similarity between two sets.

        Jaccard index = |A intersection B| / |A union B|

        Args:
            set1: First set of neighbor IDs
            set2: Second set of neighbor IDs

        Returns:
            Jaccard similarity score between 0.0 and 1.0
        """
        if not set1 and not set2:
            return 0.0

        intersection = len(set1 & set2)
        union = len(set1 | set2)

        if union == 0:
            return 0.0

        return intersection / union

    @staticmethod
    def cosine_similarity(vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
        """
        Compute cosine similarity between two sparse vectors.

        Cosine = (A . B) / (||A|| * ||B||)

        Args:
            vec1: First vector as {dimension: value} dict
            vec2: Second vector as {dimension: value} dict

        Returns:
            Cosine similarity score between 0.0 and 1.0
        """
        if not vec1 or not vec2:
            return 0.0

        # Compute dot product (only for shared dimensions)
        common_keys = set(vec1.keys()) & set(vec2.keys())
        dot_product = sum(vec1[k] * vec2[k] for k in common_keys)

        # Compute magnitudes
        mag1 = math.sqrt(sum(v * v for v in vec1.values()))
        mag2 = math.sqrt(sum(v * v for v in vec2.values()))

        if mag1 == 0 or mag2 == 0:
            return 0.0

        return dot_product / (mag1 * mag2)

    @staticmethod
    def common_neighbors_score(
        neighbors1: Set[str],
        neighbors2: Set[str],
        total_nodes: int
    ) -> float:
        """
        Compute common neighbors score with normalization.

        Uses Adamic/Adar-inspired normalization where common neighbors
        with fewer connections are weighted higher.

        Args:
            neighbors1: Neighbors of first entity
            neighbors2: Neighbors of second entity
            total_nodes: Total number of nodes in graph

        Returns:
            Normalized common neighbors score between 0.0 and 1.0
        """
        common = neighbors1 & neighbors2

        if not common:
            return 0.0

        # Simple normalized count
        max_possible = min(len(neighbors1), len(neighbors2))
        if max_possible == 0:
            return 0.0

        return len(common) / max_possible


class SimRankCalculator:
    """
    SimRank-like similarity calculator.

    SimRank is based on the idea that two entities are similar if
    their neighbors are similar. Uses iterative computation with
    configurable decay factor and iteration count.
    """

    def __init__(
        self,
        decay: float = 0.8,
        iterations: int = 5
    ):
        """
        Initialize SimRank calculator.

        Args:
            decay: Decay factor (typically 0.8)
            iterations: Number of iterations for convergence
        """
        self.decay = decay
        self.iterations = iterations

    def compute_simrank(
        self,
        adjacency: Dict[str, Set[str]],
        entity_ids: List[str]
    ) -> Dict[Tuple[str, str], float]:
        """
        Compute SimRank scores for all entity pairs.

        Args:
            adjacency: Adjacency dict mapping entity -> set of neighbors
            entity_ids: List of all entity IDs

        Returns:
            Dict mapping (entity1, entity2) tuples to similarity scores
        """
        n = len(entity_ids)
        if n < 2:
            return {}

        # Build reverse adjacency (who points to me)
        in_neighbors: Dict[str, Set[str]] = defaultdict(set)
        for entity, neighbors in adjacency.items():
            for neighbor in neighbors:
                in_neighbors[neighbor].add(entity)

        # Initialize: sim(a, b) = 1 if a == b, else 0
        current_sim: Dict[Tuple[str, str], float] = {}
        for i, a in enumerate(entity_ids):
            for b in entity_ids[i:]:
                if a == b:
                    current_sim[(a, b)] = 1.0
                else:
                    current_sim[(a, b)] = 0.0
                    current_sim[(b, a)] = 0.0

        # Iterative computation
        for iteration in range(self.iterations):
            new_sim: Dict[Tuple[str, str], float] = {}

            for i, a in enumerate(entity_ids):
                for j, b in enumerate(entity_ids):
                    if i > j:
                        continue

                    if a == b:
                        new_sim[(a, b)] = 1.0
                        continue

                    # Get in-neighbors
                    in_a = in_neighbors.get(a, set())
                    in_b = in_neighbors.get(b, set())

                    if not in_a or not in_b:
                        score = 0.0
                    else:
                        # Average similarity of in-neighbor pairs
                        total = 0.0
                        for ia in in_a:
                            for ib in in_b:
                                key = (ia, ib) if ia <= ib else (ib, ia)
                                total += current_sim.get(key, 0.0)

                        score = self.decay * total / (len(in_a) * len(in_b))

                    new_sim[(a, b)] = score
                    new_sim[(b, a)] = score

            current_sim = new_sim

        return current_sim

    def compute_simrank_for_entity(
        self,
        entity_id: str,
        adjacency: Dict[str, Set[str]],
        entity_ids: List[str]
    ) -> Dict[str, float]:
        """
        Compute SimRank scores for a single entity against all others.

        More efficient when only one entity's similarities are needed.

        Args:
            entity_id: Target entity ID
            adjacency: Adjacency dict mapping entity -> set of neighbors
            entity_ids: List of all entity IDs

        Returns:
            Dict mapping other entity IDs to similarity scores
        """
        if entity_id not in entity_ids:
            return {}

        # Build reverse adjacency
        in_neighbors: Dict[str, Set[str]] = defaultdict(set)
        for entity, neighbors in adjacency.items():
            for neighbor in neighbors:
                in_neighbors[neighbor].add(entity)

        # Initialize scores: 1 for self, 0 for others
        current_scores: Dict[str, float] = {eid: 0.0 for eid in entity_ids}
        current_scores[entity_id] = 1.0

        # Full SimRank matrix (needed for iterative computation)
        sim_matrix: Dict[Tuple[str, str], float] = {}
        for a in entity_ids:
            for b in entity_ids:
                sim_matrix[(a, b)] = 1.0 if a == b else 0.0

        # Iterative computation
        for iteration in range(self.iterations):
            new_matrix: Dict[Tuple[str, str], float] = {}

            for a in entity_ids:
                for b in entity_ids:
                    if a == b:
                        new_matrix[(a, b)] = 1.0
                        continue

                    in_a = in_neighbors.get(a, set())
                    in_b = in_neighbors.get(b, set())

                    if not in_a or not in_b:
                        new_matrix[(a, b)] = 0.0
                    else:
                        total = sum(
                            sim_matrix.get((ia, ib), 0.0)
                            for ia in in_a
                            for ib in in_b
                        )
                        new_matrix[(a, b)] = self.decay * total / (len(in_a) * len(in_b))

            sim_matrix = new_matrix

        # Extract scores for target entity
        return {
            eid: sim_matrix.get((entity_id, eid), 0.0)
            for eid in entity_ids
            if eid != entity_id
        }


# =============================================================================
# RELATIONSHIP VECTOR ENCODER
# =============================================================================

class RelationshipVectorEncoder:
    """
    Encodes entity relationships as sparse vectors for cosine similarity.

    Each entity is represented as a vector where dimensions are:
    - Neighbor IDs (binary: 1 if connected, 0 otherwise)
    - Relationship types (count of each type)
    - Optionally: relationship properties like confidence
    """

    def __init__(
        self,
        include_neighbor_ids: bool = True,
        include_rel_types: bool = True,
        include_properties: bool = False
    ):
        """
        Initialize the encoder.

        Args:
            include_neighbor_ids: Include neighbor IDs as dimensions
            include_rel_types: Include relationship type counts
            include_properties: Include relationship properties (e.g., confidence)
        """
        self.include_neighbor_ids = include_neighbor_ids
        self.include_rel_types = include_rel_types
        self.include_properties = include_properties

    def encode_entity(
        self,
        entity_id: str,
        edges: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """
        Encode an entity's relationships as a sparse vector.

        Args:
            entity_id: Entity to encode
            edges: List of all edges in the graph

        Returns:
            Sparse vector as {dimension: value} dict
        """
        vector: Dict[str, float] = {}

        # Find all edges involving this entity
        relevant_edges = [
            e for e in edges
            if e.get("source") == entity_id or e.get("target") == entity_id
        ]

        rel_type_counts: Dict[str, int] = defaultdict(int)

        for edge in relevant_edges:
            source = edge.get("source")
            target = edge.get("target")
            rel_type = edge.get("type", "RELATED_TO")
            props = edge.get("properties", {})

            # Get the neighbor (other end of the edge)
            neighbor = target if source == entity_id else source

            # Add neighbor ID dimension
            if self.include_neighbor_ids:
                vector[f"neighbor:{neighbor}"] = 1.0

            # Count relationship types
            if self.include_rel_types:
                rel_type_counts[rel_type] += 1

            # Add property dimensions
            if self.include_properties:
                confidence = props.get("confidence")
                if confidence:
                    if isinstance(confidence, str):
                        conf_map = {
                            "confirmed": 1.0,
                            "high": 0.8,
                            "medium": 0.6,
                            "low": 0.4,
                            "unverified": 0.2
                        }
                        conf_val = conf_map.get(confidence, 0.5)
                    else:
                        conf_val = float(confidence)
                    vector[f"confidence:{neighbor}"] = conf_val

        # Add relationship type counts
        if self.include_rel_types:
            for rel_type, count in rel_type_counts.items():
                vector[f"rel_type:{rel_type}"] = float(count)

        return vector

    def encode_all_entities(
        self,
        entity_ids: List[str],
        edges: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, float]]:
        """
        Encode all entities as relationship vectors.

        Args:
            entity_ids: List of all entity IDs
            edges: List of all edges

        Returns:
            Dict mapping entity ID to its vector
        """
        return {
            eid: self.encode_entity(eid, edges)
            for eid in entity_ids
        }


# =============================================================================
# MAIN SERVICE CLASS
# =============================================================================

class SimilarityService:
    """
    Similarity Scoring Service for Basset Hound.

    Provides methods to find entities with similar relationship patterns
    using various similarity metrics.
    """

    def __init__(self, neo4j_handler=None):
        """
        Initialize the Similarity Service.

        Args:
            neo4j_handler: Async Neo4j database handler
        """
        self.neo4j_handler = neo4j_handler
        self.algorithms = SimilarityAlgorithms()
        self.encoder = RelationshipVectorEncoder()

    async def _fetch_graph_data(
        self,
        project_safe_name: str
    ) -> Tuple[List[str], List[Dict[str, Any]], Dict[str, Set[str]]]:
        """
        Fetch graph data from Neo4j.

        Args:
            project_safe_name: Project identifier

        Returns:
            Tuple of (entity_ids, edges, adjacency_dict)
        """
        if not self.neo4j_handler:
            return [], [], {}

        async with self.neo4j_handler.session() as session:
            # Get all entities
            entities_result = await session.run("""
                MATCH (project:Project {safe_name: $project_safe_name})
                      -[:HAS_PERSON]->(person:Person)
                RETURN person.id AS id
            """, project_safe_name=project_safe_name)

            entity_data = await entities_result.data()
            entity_ids = [r["id"] for r in entity_data]
            entity_set = set(entity_ids)

            # Get all relationships from profiles
            edges = []
            adjacency: Dict[str, Set[str]] = defaultdict(set)

            # Fetch profile data to extract relationships
            profiles_result = await session.run("""
                MATCH (project:Project {safe_name: $project_safe_name})
                      -[:HAS_PERSON]->(person:Person)
                OPTIONAL MATCH (person)-[:HAS_FIELD_VALUE]->(fv:FieldValue)
                WHERE fv.section_id = 'Tagged People'
                RETURN person.id AS id,
                       collect({field_id: fv.field_id, value: fv.value}) AS field_values
            """, project_safe_name=project_safe_name)

            profiles_data = await profiles_result.data()

            for record in profiles_data:
                entity_id = record["id"]
                field_values = record.get("field_values", [])

                tagged_ids = []
                rel_types = {}
                rel_props = {}

                for fv in field_values:
                    if fv.get("field_id") == "tagged_people":
                        value = fv.get("value")
                        if value:
                            import json
                            try:
                                tagged_ids = json.loads(value) if isinstance(value, str) else value
                            except (json.JSONDecodeError, TypeError):
                                tagged_ids = [value] if value else []
                    elif fv.get("field_id") == "relationship_types":
                        value = fv.get("value")
                        if value:
                            import json
                            try:
                                rel_types = json.loads(value) if isinstance(value, str) else value
                            except (json.JSONDecodeError, TypeError):
                                rel_types = {}
                    elif fv.get("field_id") == "relationship_properties":
                        value = fv.get("value")
                        if value:
                            import json
                            try:
                                rel_props = json.loads(value) if isinstance(value, str) else value
                            except (json.JSONDecodeError, TypeError):
                                rel_props = {}

                if not isinstance(tagged_ids, list):
                    tagged_ids = [tagged_ids] if tagged_ids else []

                for target_id in tagged_ids:
                    if target_id in entity_set:
                        rel_type = rel_types.get(target_id, "RELATED_TO") if isinstance(rel_types, dict) else "RELATED_TO"
                        props = rel_props.get(target_id, {}) if isinstance(rel_props, dict) else {}

                        edges.append({
                            "source": entity_id,
                            "target": target_id,
                            "type": rel_type,
                            "properties": props
                        })

                        adjacency[entity_id].add(target_id)
                        adjacency[target_id].add(entity_id)  # Bidirectional

            return entity_ids, edges, adjacency

    def _build_adjacency_from_edges(
        self,
        edges: List[Dict[str, Any]],
        bidirectional: bool = True
    ) -> Dict[str, Set[str]]:
        """
        Build adjacency dict from edge list.

        Args:
            edges: List of edge dictionaries
            bidirectional: Whether to treat edges as bidirectional

        Returns:
            Dict mapping entity ID to set of neighbor IDs
        """
        adjacency: Dict[str, Set[str]] = defaultdict(set)

        for edge in edges:
            source = edge.get("source")
            target = edge.get("target")

            if source and target:
                adjacency[source].add(target)
                if bidirectional:
                    adjacency[target].add(source)

        return adjacency

    def compute_jaccard_similarity(
        self,
        entity1_id: str,
        entity2_id: str,
        adjacency: Dict[str, Set[str]]
    ) -> SimilarityResult:
        """
        Compute Jaccard similarity between two entities.

        Args:
            entity1_id: First entity ID
            entity2_id: Second entity ID
            adjacency: Adjacency dict

        Returns:
            SimilarityResult with Jaccard score
        """
        neighbors1 = adjacency.get(entity1_id, set())
        neighbors2 = adjacency.get(entity2_id, set())

        # Exclude the entities themselves from neighbor comparison
        neighbors1 = neighbors1 - {entity2_id}
        neighbors2 = neighbors2 - {entity1_id}

        score = self.algorithms.jaccard_similarity(neighbors1, neighbors2)
        common = list(neighbors1 & neighbors2)

        return SimilarityResult(
            entity1_id=entity1_id,
            entity2_id=entity2_id,
            score=score,
            method=SimilarityMethod.JACCARD,
            common_neighbors=common,
            details={
                "neighbors1_count": len(neighbors1),
                "neighbors2_count": len(neighbors2),
                "intersection_count": len(common),
                "union_count": len(neighbors1 | neighbors2)
            }
        )

    def compute_cosine_similarity(
        self,
        entity1_id: str,
        entity2_id: str,
        vectors: Dict[str, Dict[str, float]],
        adjacency: Dict[str, Set[str]]
    ) -> SimilarityResult:
        """
        Compute cosine similarity between entity relationship vectors.

        Args:
            entity1_id: First entity ID
            entity2_id: Second entity ID
            vectors: Pre-computed relationship vectors
            adjacency: Adjacency dict (for common neighbors)

        Returns:
            SimilarityResult with cosine score
        """
        vec1 = vectors.get(entity1_id, {})
        vec2 = vectors.get(entity2_id, {})

        score = self.algorithms.cosine_similarity(vec1, vec2)

        neighbors1 = adjacency.get(entity1_id, set()) - {entity2_id}
        neighbors2 = adjacency.get(entity2_id, set()) - {entity1_id}
        common = list(neighbors1 & neighbors2)

        return SimilarityResult(
            entity1_id=entity1_id,
            entity2_id=entity2_id,
            score=score,
            method=SimilarityMethod.COSINE,
            common_neighbors=common,
            details={
                "vector1_dimensions": len(vec1),
                "vector2_dimensions": len(vec2),
                "shared_dimensions": len(set(vec1.keys()) & set(vec2.keys()))
            }
        )

    def compute_common_neighbors_score(
        self,
        entity1_id: str,
        entity2_id: str,
        adjacency: Dict[str, Set[str]],
        total_nodes: int
    ) -> SimilarityResult:
        """
        Compute common neighbors similarity score.

        Args:
            entity1_id: First entity ID
            entity2_id: Second entity ID
            adjacency: Adjacency dict
            total_nodes: Total number of nodes in graph

        Returns:
            SimilarityResult with common neighbors score
        """
        neighbors1 = adjacency.get(entity1_id, set()) - {entity2_id}
        neighbors2 = adjacency.get(entity2_id, set()) - {entity1_id}

        score = self.algorithms.common_neighbors_score(
            neighbors1, neighbors2, total_nodes
        )
        common = list(neighbors1 & neighbors2)

        return SimilarityResult(
            entity1_id=entity1_id,
            entity2_id=entity2_id,
            score=score,
            method=SimilarityMethod.COMMON_NEIGHBORS,
            common_neighbors=common,
            details={
                "common_count": len(common),
                "neighbors1_count": len(neighbors1),
                "neighbors2_count": len(neighbors2),
                "total_nodes": total_nodes
            }
        )

    async def find_similar_entities(
        self,
        project_safe_name: str,
        entity_id: str,
        config: Optional[SimilarityConfig] = None
    ) -> EntitySimilarityReport:
        """
        Find entities most similar to a given entity.

        Args:
            project_safe_name: Project identifier
            entity_id: Target entity ID
            config: Similarity configuration

        Returns:
            EntitySimilarityReport with ranked similar entities
        """
        if config is None:
            config = SimilarityConfig()

        # Fetch graph data
        entity_ids, edges, adjacency = await self._fetch_graph_data(project_safe_name)

        if entity_id not in entity_ids:
            return EntitySimilarityReport(
                entity_id=entity_id,
                similar_entities=[],
                top_n=config.top_n,
                method=config.method,
                total_candidates=0
            )

        # Compute similarities based on method
        results: List[SimilarityResult] = []

        if config.method == SimilarityMethod.JACCARD:
            for other_id in entity_ids:
                if other_id == entity_id:
                    continue
                result = self.compute_jaccard_similarity(
                    entity_id, other_id, adjacency
                )
                if result.score >= config.threshold:
                    if not config.include_common_neighbors:
                        result.common_neighbors = []
                    results.append(result)

        elif config.method == SimilarityMethod.COSINE:
            vectors = self.encoder.encode_all_entities(entity_ids, edges)
            for other_id in entity_ids:
                if other_id == entity_id:
                    continue
                result = self.compute_cosine_similarity(
                    entity_id, other_id, vectors, adjacency
                )
                if result.score >= config.threshold:
                    if not config.include_common_neighbors:
                        result.common_neighbors = []
                    results.append(result)

        elif config.method == SimilarityMethod.COMMON_NEIGHBORS:
            total_nodes = len(entity_ids)
            for other_id in entity_ids:
                if other_id == entity_id:
                    continue
                result = self.compute_common_neighbors_score(
                    entity_id, other_id, adjacency, total_nodes
                )
                if result.score >= config.threshold:
                    if not config.include_common_neighbors:
                        result.common_neighbors = []
                    results.append(result)

        elif config.method == SimilarityMethod.SIMRANK:
            calculator = SimRankCalculator(
                decay=config.simrank_decay,
                iterations=config.simrank_iterations
            )
            simrank_scores = calculator.compute_simrank_for_entity(
                entity_id, adjacency, entity_ids
            )

            for other_id, score in simrank_scores.items():
                if score >= config.threshold:
                    neighbors1 = adjacency.get(entity_id, set()) - {other_id}
                    neighbors2 = adjacency.get(other_id, set()) - {entity_id}
                    common = list(neighbors1 & neighbors2) if config.include_common_neighbors else []

                    results.append(SimilarityResult(
                        entity1_id=entity_id,
                        entity2_id=other_id,
                        score=score,
                        method=SimilarityMethod.SIMRANK,
                        common_neighbors=common,
                        details={
                            "iterations": config.simrank_iterations,
                            "decay": config.simrank_decay
                        }
                    ))

        elif config.method == SimilarityMethod.COMBINED:
            results = await self._compute_combined_similarity(
                entity_id, entity_ids, edges, adjacency, config
            )

        # Sort by score descending and limit to top_n
        results.sort(key=lambda x: x.score, reverse=True)
        results = results[:config.top_n]

        return EntitySimilarityReport(
            entity_id=entity_id,
            similar_entities=results,
            top_n=config.top_n,
            method=config.method,
            total_candidates=len(entity_ids) - 1
        )

    async def _compute_combined_similarity(
        self,
        entity_id: str,
        entity_ids: List[str],
        edges: List[Dict[str, Any]],
        adjacency: Dict[str, Set[str]],
        config: SimilarityConfig
    ) -> List[SimilarityResult]:
        """
        Compute combined similarity using multiple methods.

        Args:
            entity_id: Target entity ID
            entity_ids: All entity IDs
            edges: All edges
            adjacency: Adjacency dict
            config: Configuration with weights

        Returns:
            List of SimilarityResult with combined scores
        """
        weights = config.weights or DEFAULT_WEIGHTS

        # Normalize weights
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {k: v / total_weight for k, v in weights.items()}

        # Compute all method scores
        vectors = self.encoder.encode_all_entities(entity_ids, edges)
        total_nodes = len(entity_ids)

        calculator = SimRankCalculator(
            decay=config.simrank_decay,
            iterations=config.simrank_iterations
        )
        simrank_scores = calculator.compute_simrank_for_entity(
            entity_id, adjacency, entity_ids
        )

        results: List[SimilarityResult] = []

        for other_id in entity_ids:
            if other_id == entity_id:
                continue

            scores: Dict[SimilarityMethod, float] = {}

            # Jaccard
            jaccard = self.compute_jaccard_similarity(entity_id, other_id, adjacency)
            scores[SimilarityMethod.JACCARD] = jaccard.score

            # Cosine
            cosine = self.compute_cosine_similarity(entity_id, other_id, vectors, adjacency)
            scores[SimilarityMethod.COSINE] = cosine.score

            # Common neighbors
            cn = self.compute_common_neighbors_score(
                entity_id, other_id, adjacency, total_nodes
            )
            scores[SimilarityMethod.COMMON_NEIGHBORS] = cn.score

            # SimRank
            scores[SimilarityMethod.SIMRANK] = simrank_scores.get(other_id, 0.0)

            # Compute weighted average
            combined_score = sum(
                weights.get(method, 0.0) * score
                for method, score in scores.items()
            )

            if combined_score >= config.threshold:
                common = jaccard.common_neighbors if config.include_common_neighbors else []

                results.append(SimilarityResult(
                    entity1_id=entity_id,
                    entity2_id=other_id,
                    score=combined_score,
                    method=SimilarityMethod.COMBINED,
                    common_neighbors=common,
                    details={
                        "component_scores": {m.value: s for m, s in scores.items()},
                        "weights": {m.value: w for m, w in weights.items()}
                    }
                ))

        return results

    async def compute_pairwise_similarity(
        self,
        project_safe_name: str,
        entity1_id: str,
        entity2_id: str,
        config: Optional[SimilarityConfig] = None
    ) -> SimilarityResult:
        """
        Compute similarity between two specific entities.

        Args:
            project_safe_name: Project identifier
            entity1_id: First entity ID
            entity2_id: Second entity ID
            config: Similarity configuration

        Returns:
            SimilarityResult for the pair
        """
        if config is None:
            config = SimilarityConfig()

        entity_ids, edges, adjacency = await self._fetch_graph_data(project_safe_name)

        if entity1_id not in entity_ids or entity2_id not in entity_ids:
            return SimilarityResult(
                entity1_id=entity1_id,
                entity2_id=entity2_id,
                score=0.0,
                method=config.method,
                common_neighbors=[],
                details={"error": "One or both entities not found"}
            )

        if config.method == SimilarityMethod.JACCARD:
            return self.compute_jaccard_similarity(entity1_id, entity2_id, adjacency)

        elif config.method == SimilarityMethod.COSINE:
            vectors = self.encoder.encode_all_entities([entity1_id, entity2_id], edges)
            return self.compute_cosine_similarity(entity1_id, entity2_id, vectors, adjacency)

        elif config.method == SimilarityMethod.COMMON_NEIGHBORS:
            return self.compute_common_neighbors_score(
                entity1_id, entity2_id, adjacency, len(entity_ids)
            )

        elif config.method == SimilarityMethod.SIMRANK:
            calculator = SimRankCalculator(
                decay=config.simrank_decay,
                iterations=config.simrank_iterations
            )
            all_scores = calculator.compute_simrank(adjacency, entity_ids)
            key = (entity1_id, entity2_id) if entity1_id <= entity2_id else (entity2_id, entity1_id)
            score = all_scores.get(key, 0.0)

            neighbors1 = adjacency.get(entity1_id, set()) - {entity2_id}
            neighbors2 = adjacency.get(entity2_id, set()) - {entity1_id}
            common = list(neighbors1 & neighbors2) if config.include_common_neighbors else []

            return SimilarityResult(
                entity1_id=entity1_id,
                entity2_id=entity2_id,
                score=score,
                method=SimilarityMethod.SIMRANK,
                common_neighbors=common,
                details={
                    "iterations": config.simrank_iterations,
                    "decay": config.simrank_decay
                }
            )

        else:  # COMBINED
            results = await self._compute_combined_similarity(
                entity1_id, entity_ids, edges, adjacency, config
            )
            for result in results:
                if result.entity2_id == entity2_id:
                    return result

            # If not found (score below threshold), compute anyway
            return SimilarityResult(
                entity1_id=entity1_id,
                entity2_id=entity2_id,
                score=0.0,
                method=SimilarityMethod.COMBINED,
                common_neighbors=[],
                details={"note": "Score below threshold or no data"}
            )

    async def find_potential_links(
        self,
        project_safe_name: str,
        config: Optional[SimilarityConfig] = None,
        max_results: int = 20
    ) -> List[PotentialLink]:
        """
        Find potential missing links between entities.

        Uses common neighbors analysis to suggest entity pairs that
        might have a relationship but currently don't.

        Args:
            project_safe_name: Project identifier
            config: Similarity configuration
            max_results: Maximum number of potential links to return

        Returns:
            List of PotentialLink suggestions
        """
        if config is None:
            config = SimilarityConfig(method=SimilarityMethod.COMMON_NEIGHBORS)

        entity_ids, edges, adjacency = await self._fetch_graph_data(project_safe_name)

        if len(entity_ids) < 2:
            return []

        # Find existing connections
        existing_connections: Set[Tuple[str, str]] = set()
        for edge in edges:
            source = edge.get("source")
            target = edge.get("target")
            if source and target:
                existing_connections.add((source, target))
                existing_connections.add((target, source))

        # Score potential links (non-connected pairs)
        potential_links: List[PotentialLink] = []

        for i, entity1 in enumerate(entity_ids):
            for entity2 in entity_ids[i + 1:]:
                # Skip if already connected
                if (entity1, entity2) in existing_connections:
                    continue

                neighbors1 = adjacency.get(entity1, set())
                neighbors2 = adjacency.get(entity2, set())
                common = neighbors1 & neighbors2

                if not common:
                    continue

                # Compute score based on common neighbors
                score = self.algorithms.common_neighbors_score(
                    neighbors1, neighbors2, len(entity_ids)
                )

                if score >= config.threshold:
                    potential_links.append(PotentialLink(
                        entity1_id=entity1,
                        entity2_id=entity2,
                        score=score,
                        common_neighbor_count=len(common),
                        common_neighbors=list(common) if config.include_common_neighbors else [],
                        evidence={
                            "entity1_degree": len(neighbors1),
                            "entity2_degree": len(neighbors2),
                            "common_ratio": len(common) / max(min(len(neighbors1), len(neighbors2)), 1)
                        }
                    ))

        # Sort by score and limit
        potential_links.sort(key=lambda x: x.score, reverse=True)
        return potential_links[:max_results]

    async def get_similarity_matrix(
        self,
        project_safe_name: str,
        entity_ids: Optional[List[str]] = None,
        config: Optional[SimilarityConfig] = None
    ) -> Dict[str, Dict[str, float]]:
        """
        Compute full similarity matrix for a set of entities.

        Args:
            project_safe_name: Project identifier
            entity_ids: Specific entities to include (None = all)
            config: Similarity configuration

        Returns:
            Nested dict: matrix[entity1][entity2] = similarity score
        """
        if config is None:
            config = SimilarityConfig()

        all_entity_ids, edges, adjacency = await self._fetch_graph_data(project_safe_name)

        if entity_ids:
            target_ids = [eid for eid in entity_ids if eid in all_entity_ids]
        else:
            target_ids = all_entity_ids

        if len(target_ids) < 2:
            return {}

        # Initialize matrix
        matrix: Dict[str, Dict[str, float]] = {eid: {} for eid in target_ids}

        # Compute based on method
        if config.method == SimilarityMethod.JACCARD:
            for i, e1 in enumerate(target_ids):
                for e2 in target_ids[i:]:
                    if e1 == e2:
                        matrix[e1][e2] = 1.0
                    else:
                        result = self.compute_jaccard_similarity(e1, e2, adjacency)
                        matrix[e1][e2] = result.score
                        matrix[e2][e1] = result.score

        elif config.method == SimilarityMethod.COSINE:
            vectors = self.encoder.encode_all_entities(target_ids, edges)
            for i, e1 in enumerate(target_ids):
                for e2 in target_ids[i:]:
                    if e1 == e2:
                        matrix[e1][e2] = 1.0
                    else:
                        result = self.compute_cosine_similarity(e1, e2, vectors, adjacency)
                        matrix[e1][e2] = result.score
                        matrix[e2][e1] = result.score

        elif config.method == SimilarityMethod.COMMON_NEIGHBORS:
            total = len(all_entity_ids)
            for i, e1 in enumerate(target_ids):
                for e2 in target_ids[i:]:
                    if e1 == e2:
                        matrix[e1][e2] = 1.0
                    else:
                        result = self.compute_common_neighbors_score(e1, e2, adjacency, total)
                        matrix[e1][e2] = result.score
                        matrix[e2][e1] = result.score

        elif config.method == SimilarityMethod.SIMRANK:
            calculator = SimRankCalculator(
                decay=config.simrank_decay,
                iterations=config.simrank_iterations
            )
            simrank_matrix = calculator.compute_simrank(adjacency, target_ids)

            for e1 in target_ids:
                for e2 in target_ids:
                    if e1 == e2:
                        matrix[e1][e2] = 1.0
                    else:
                        key = (e1, e2) if e1 <= e2 else (e2, e1)
                        matrix[e1][e2] = simrank_matrix.get(key, 0.0)

        return matrix


# =============================================================================
# SINGLETON MANAGEMENT
# =============================================================================

_similarity_service: Optional[SimilarityService] = None


def get_similarity_service(
    neo4j_handler=None
) -> SimilarityService:
    """
    Get or create the SimilarityService singleton.

    Args:
        neo4j_handler: Optional async Neo4j handler

    Returns:
        SimilarityService instance
    """
    global _similarity_service

    if _similarity_service is None:
        _similarity_service = SimilarityService(neo4j_handler=neo4j_handler)
    elif neo4j_handler is not None:
        _similarity_service.neo4j_handler = neo4j_handler

    return _similarity_service


def set_similarity_service(service: Optional[SimilarityService]) -> None:
    """Set the similarity service singleton (useful for testing)."""
    global _similarity_service
    _similarity_service = service


def reset_similarity_service() -> None:
    """Reset the similarity service singleton."""
    global _similarity_service
    _similarity_service = None
