"""
Graph Analytics Router for Basset Hound - Phase 18.

Provides REST API endpoints for advanced graph analytics including:
- Community detection with configurable algorithms
- Entity similarity analysis
- Influence analysis (PageRank, key entities)
- Temporal relationship patterns
"""

from typing import Optional, Any, Literal
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, ConfigDict, Field

from ..dependencies import get_neo4j_handler


# =============================================================================
# ENUMS
# =============================================================================

class CommunityAlgorithm(str, Enum):
    """Supported community detection algorithms."""
    LOUVAIN = "louvain"
    LABEL_PROPAGATION = "label_propagation"
    GIRVAN_NEWMAN = "girvan_newman"
    CONNECTED_COMPONENTS = "connected_components"


class SimilarityMetric(str, Enum):
    """Supported similarity metrics."""
    JACCARD = "jaccard"
    COSINE = "cosine"
    OVERLAP = "overlap"
    ADAMIC_ADAR = "adamic_adar"


class InfluenceMetric(str, Enum):
    """Supported influence/centrality metrics."""
    PAGERANK = "pagerank"
    BETWEENNESS = "betweenness"
    CLOSENESS = "closeness"
    EIGENVECTOR = "eigenvector"
    DEGREE = "degree"


class TemporalPatternType(str, Enum):
    """Types of temporal patterns to detect."""
    BURST = "burst"
    PERIODIC = "periodic"
    TREND = "trend"
    ANOMALY = "anomaly"


# =============================================================================
# PYDANTIC MODELS - Community Detection
# =============================================================================

class CommunityMember(BaseModel):
    """Schema for an entity that is a member of a community."""
    entity_id: str = Field(..., description="Entity ID")
    label: str = Field(default="", description="Entity display label")
    membership_score: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Membership strength score (0-1)"
    )
    role: str = Field(
        default="member",
        description="Role within community (hub, bridge, member)"
    )


class CommunityInfo(BaseModel):
    """Schema for a detected community."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "community_id": "community_1",
            "size": 15,
            "density": 0.45,
            "cohesion": 0.72,
            "member_ids": ["entity1", "entity2", "entity3"],
            "hub_entities": ["entity1"],
            "bridge_entities": ["entity2"]
        }
    })

    community_id: str = Field(..., description="Unique community identifier")
    size: int = Field(..., ge=0, description="Number of entities in community")
    density: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Internal density (ratio of actual to possible edges)"
    )
    cohesion: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Community cohesion score"
    )
    member_ids: list[str] = Field(
        default_factory=list,
        description="List of entity IDs in this community"
    )
    hub_entities: list[str] = Field(
        default_factory=list,
        description="Highly connected entities within the community"
    )
    bridge_entities: list[str] = Field(
        default_factory=list,
        description="Entities connecting this community to others"
    )


class CommunitiesResponse(BaseModel):
    """Schema for community detection response."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "algorithm": "louvain",
            "community_count": 5,
            "modularity": 0.65,
            "coverage": 0.95,
            "communities": [],
            "total_entities": 100
        }
    })

    algorithm: str = Field(..., description="Algorithm used for detection")
    community_count: int = Field(
        ...,
        ge=0,
        description="Total number of communities detected"
    )
    modularity: float = Field(
        default=0.0,
        description="Modularity score of the partition"
    )
    coverage: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Fraction of entities assigned to communities"
    )
    communities: list[CommunityInfo] = Field(
        default_factory=list,
        description="List of detected communities"
    )
    total_entities: int = Field(
        default=0,
        ge=0,
        description="Total entities analyzed"
    )


class CommunityDetailResponse(BaseModel):
    """Schema for detailed community information."""
    community_id: str = Field(..., description="Community identifier")
    size: int = Field(..., ge=0, description="Number of members")
    density: float = Field(..., ge=0.0, le=1.0, description="Internal density")
    members: list[CommunityMember] = Field(
        default_factory=list,
        description="Detailed member information"
    )
    internal_edges: int = Field(
        default=0,
        ge=0,
        description="Number of edges within community"
    )
    external_edges: int = Field(
        default=0,
        ge=0,
        description="Number of edges to other communities"
    )
    connected_communities: list[str] = Field(
        default_factory=list,
        description="IDs of connected communities"
    )


class EntityCommunityResponse(BaseModel):
    """Schema for entity's community membership."""
    entity_id: str = Field(..., description="Entity ID")
    community_id: Optional[str] = Field(
        None,
        description="Primary community ID (None if not in any community)"
    )
    membership_score: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Membership strength"
    )
    role: str = Field(
        default="member",
        description="Role within community"
    )
    overlapping_communities: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Other communities entity partially belongs to"
    )


# =============================================================================
# PYDANTIC MODELS - Similarity Analysis
# =============================================================================

class SimilarEntityResult(BaseModel):
    """Schema for a similar entity result."""
    entity_id: str = Field(..., description="Similar entity ID")
    label: str = Field(default="", description="Entity display label")
    similarity_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Similarity score (0-1)"
    )
    common_neighbors: int = Field(
        default=0,
        ge=0,
        description="Number of common neighbors"
    )
    shared_attributes: list[str] = Field(
        default_factory=list,
        description="List of shared attribute types"
    )


class SimilarEntitiesResponse(BaseModel):
    """Schema for similar entities response."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "entity_id": "entity1",
            "metric": "jaccard",
            "similar_entities": [],
            "total_found": 10
        }
    })

    entity_id: str = Field(..., description="Source entity ID")
    metric: str = Field(..., description="Similarity metric used")
    similar_entities: list[SimilarEntityResult] = Field(
        default_factory=list,
        description="List of similar entities ranked by score"
    )
    total_found: int = Field(
        default=0,
        ge=0,
        description="Total similar entities found"
    )


class EntityComparisonResponse(BaseModel):
    """Schema for comparing two entities."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "entity1_id": "entity1",
            "entity2_id": "entity2",
            "similarity_scores": {
                "jaccard": 0.45,
                "cosine": 0.52,
                "overlap": 0.60
            },
            "common_neighbors_count": 5,
            "path_distance": 2,
            "shared_communities": ["community_1"]
        }
    })

    entity1_id: str = Field(..., description="First entity ID")
    entity2_id: str = Field(..., description="Second entity ID")
    similarity_scores: dict[str, float] = Field(
        default_factory=dict,
        description="Similarity scores by metric"
    )
    common_neighbors_count: int = Field(
        default=0,
        ge=0,
        description="Number of common neighbors"
    )
    path_distance: Optional[int] = Field(
        None,
        ge=0,
        description="Shortest path distance (None if not connected)"
    )
    shared_communities: list[str] = Field(
        default_factory=list,
        description="Communities both entities belong to"
    )


class CommonNeighbor(BaseModel):
    """Schema for a common neighbor entity."""
    entity_id: str = Field(..., description="Neighbor entity ID")
    label: str = Field(default="", description="Entity display label")
    relationship_to_entity1: str = Field(
        default="RELATED_TO",
        description="Relationship type to first entity"
    )
    relationship_to_entity2: str = Field(
        default="RELATED_TO",
        description="Relationship type to second entity"
    )


class CommonNeighborsResponse(BaseModel):
    """Schema for common neighbors response."""
    entity1_id: str = Field(..., description="First entity ID")
    entity2_id: str = Field(..., description="Second entity ID")
    common_neighbors: list[CommonNeighbor] = Field(
        default_factory=list,
        description="List of common neighbors"
    )
    total_count: int = Field(
        default=0,
        ge=0,
        description="Total number of common neighbors"
    )
    adamic_adar_score: float = Field(
        default=0.0,
        ge=0.0,
        description="Adamic-Adar similarity score based on common neighbors"
    )


# =============================================================================
# PYDANTIC MODELS - Influence Analysis
# =============================================================================

class EntityInfluence(BaseModel):
    """Schema for entity influence ranking."""
    entity_id: str = Field(..., description="Entity ID")
    label: str = Field(default="", description="Entity display label")
    influence_score: float = Field(
        ...,
        ge=0.0,
        description="Influence score (normalized)"
    )
    rank: int = Field(..., ge=1, description="Rank position")
    metrics: dict[str, float] = Field(
        default_factory=dict,
        description="Individual metric scores"
    )


class InfluenceRankingsResponse(BaseModel):
    """Schema for influence rankings response."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "metric": "pagerank",
            "damping_factor": 0.85,
            "rankings": [],
            "total_entities": 100
        }
    })

    metric: str = Field(..., description="Primary influence metric used")
    damping_factor: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Damping factor used (for PageRank)"
    )
    rankings: list[EntityInfluence] = Field(
        default_factory=list,
        description="Entities ranked by influence"
    )
    total_entities: int = Field(
        default=0,
        ge=0,
        description="Total entities analyzed"
    )
    convergence_iterations: int = Field(
        default=0,
        ge=0,
        description="Iterations until convergence"
    )


class InfluenceSpreadNode(BaseModel):
    """Schema for a node in influence spread simulation."""
    entity_id: str = Field(..., description="Entity ID")
    label: str = Field(default="", description="Entity display label")
    activation_probability: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Probability of being influenced"
    )
    activation_step: int = Field(
        default=0,
        ge=0,
        description="Step at which entity was activated"
    )


class InfluenceSpreadResponse(BaseModel):
    """Schema for influence spread simulation response."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "source_entity_id": "entity1",
            "model": "independent_cascade",
            "steps": 5,
            "spread_probability": 0.3,
            "total_influenced": 25,
            "influenced_entities": []
        }
    })

    source_entity_id: str = Field(..., description="Starting entity ID")
    model: str = Field(
        default="independent_cascade",
        description="Influence spread model used"
    )
    steps: int = Field(..., ge=1, description="Number of simulation steps")
    spread_probability: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Probability of influence spread per edge"
    )
    total_influenced: int = Field(
        default=0,
        ge=0,
        description="Total entities influenced"
    )
    influenced_entities: list[InfluenceSpreadNode] = Field(
        default_factory=list,
        description="Entities influenced with activation details"
    )
    spread_by_step: dict[int, int] = Field(
        default_factory=dict,
        description="Number of new activations per step"
    )


class KeyEntity(BaseModel):
    """Schema for a key/critical entity."""
    entity_id: str = Field(..., description="Entity ID")
    label: str = Field(default="", description="Entity display label")
    criticality_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Criticality score"
    )
    role: str = Field(
        default="key",
        description="Role type (hub, bridge, broker, etc.)"
    )
    impact_if_removed: dict[str, Any] = Field(
        default_factory=dict,
        description="Predicted impact if entity is removed"
    )


class KeyEntitiesResponse(BaseModel):
    """Schema for key entities response."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "key_entities": [],
            "total_found": 10,
            "analysis_type": "structural",
            "network_vulnerability": 0.35
        }
    })

    key_entities: list[KeyEntity] = Field(
        default_factory=list,
        description="List of key/critical entities"
    )
    total_found: int = Field(
        default=0,
        ge=0,
        description="Total key entities identified"
    )
    analysis_type: str = Field(
        default="structural",
        description="Type of analysis performed"
    )
    network_vulnerability: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Overall network vulnerability score"
    )


# =============================================================================
# PYDANTIC MODELS - Temporal Patterns
# =============================================================================

class TemporalPattern(BaseModel):
    """Schema for a detected temporal pattern."""
    pattern_id: str = Field(..., description="Unique pattern identifier")
    pattern_type: str = Field(..., description="Type of pattern detected")
    start_time: Optional[str] = Field(
        None,
        description="Pattern start time (ISO 8601)"
    )
    end_time: Optional[str] = Field(
        None,
        description="Pattern end time (ISO 8601)"
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Detection confidence"
    )
    affected_entities: list[str] = Field(
        default_factory=list,
        description="Entity IDs involved in pattern"
    )
    description: str = Field(
        default="",
        description="Human-readable pattern description"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional pattern metadata"
    )


class TemporalPatternsResponse(BaseModel):
    """Schema for temporal patterns response."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "patterns": [],
            "total_found": 5,
            "time_range": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-12-31T23:59:59Z"
            },
            "pattern_types_found": ["burst", "periodic"]
        }
    })

    patterns: list[TemporalPattern] = Field(
        default_factory=list,
        description="Detected temporal patterns"
    )
    total_found: int = Field(
        default=0,
        ge=0,
        description="Total patterns detected"
    )
    time_range: dict[str, str] = Field(
        default_factory=dict,
        description="Time range analyzed"
    )
    pattern_types_found: list[str] = Field(
        default_factory=list,
        description="Types of patterns found"
    )


# =============================================================================
# ROUTER DEFINITION
# =============================================================================

router = APIRouter(
    prefix="/analytics/{project}",
    tags=["graph-analytics"],
    responses={
        404: {"description": "Project or entity not found"},
        500: {"description": "Internal server error"},
    },
)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _verify_project(neo4j_handler, project_safe_name: str):
    """Verify that a project exists."""
    project = neo4j_handler.get_project(project_safe_name)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_safe_name}' not found"
        )
    return project


def _verify_entity(neo4j_handler, project_safe_name: str, entity_id: str):
    """Verify that an entity exists in a project."""
    entity = neo4j_handler.get_person(project_safe_name, entity_id)
    if not entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity '{entity_id}' not found in project '{project_safe_name}'"
        )
    return entity


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


# =============================================================================
# COMMUNITY DETECTION ENDPOINTS
# =============================================================================

@router.get(
    "/communities",
    response_model=CommunitiesResponse,
    summary="Detect communities in the project graph",
    description="Run community detection algorithm on the project's entity graph.",
    responses={
        200: {"description": "Communities detected successfully"},
        404: {"description": "Project not found"},
    }
)
async def detect_communities(
    project: str,
    algorithm: CommunityAlgorithm = Query(
        default=CommunityAlgorithm.LOUVAIN,
        description="Community detection algorithm to use"
    ),
    resolution: float = Query(
        default=1.0,
        ge=0.1,
        le=5.0,
        description="Resolution parameter for multi-scale detection (higher = more communities)"
    ),
    min_community_size: int = Query(
        default=2,
        ge=1,
        le=100,
        description="Minimum number of entities for a valid community"
    ),
    include_isolated: bool = Query(
        default=False,
        description="Include isolated entities as single-entity communities"
    ),
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Detect communities in the entity graph.

    Uses the specified algorithm to find groups of densely connected entities.
    Supports multiple algorithms optimized for different graph characteristics.

    - **project**: Project safe name
    - **algorithm**: Detection algorithm (louvain, label_propagation, etc.)
    - **resolution**: Resolution parameter for multi-scale detection
    - **min_community_size**: Minimum community size to report
    - **include_isolated**: Include isolated entities
    """
    _verify_project(neo4j_handler, project)

    try:
        # Use existing cluster detection as base and enhance it
        cluster_result = neo4j_handler.find_clusters(project)

        if not cluster_result:
            return CommunitiesResponse(
                algorithm=algorithm.value,
                community_count=0,
                modularity=0.0,
                coverage=0.0,
                communities=[],
                total_entities=0
            )

        # Convert clusters to communities
        communities = []
        total_entities = cluster_result.get("total_entities", 0)

        for cluster_data in cluster_result.get("clusters", []):
            size = cluster_data.get("size", 0)

            # Filter by minimum size
            if size < min_community_size:
                if not include_isolated:
                    continue

            # Skip isolated if not requested
            if cluster_data.get("is_isolated", False) and not include_isolated:
                continue

            entity_ids = cluster_data.get("entity_ids", [])
            internal_edges = cluster_data.get("internal_edges", 0)

            # Calculate density
            max_edges = size * (size - 1) / 2 if size > 1 else 0
            density = internal_edges / max_edges if max_edges > 0 else 0.0

            community = CommunityInfo(
                community_id=cluster_data.get("cluster_id", f"community_{len(communities)}"),
                size=size,
                density=round(density, 4),
                cohesion=density,  # Simplified cohesion metric
                member_ids=entity_ids,
                hub_entities=entity_ids[:1] if entity_ids else [],  # First entity as hub
                bridge_entities=[]
            )
            communities.append(community)

        # Calculate modularity estimate
        connected_clusters = [c for c in communities if c.size > 1]
        modularity = len(connected_clusters) / max(len(communities), 1) * 0.5

        # Calculate coverage
        assigned_entities = sum(c.size for c in communities)
        coverage = assigned_entities / total_entities if total_entities > 0 else 0.0

        return CommunitiesResponse(
            algorithm=algorithm.value,
            community_count=len(communities),
            modularity=round(modularity, 4),
            coverage=round(coverage, 4),
            communities=communities,
            total_entities=total_entities
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to detect communities: {str(e)}"
        )


@router.get(
    "/communities/{community_id}",
    response_model=CommunityDetailResponse,
    summary="Get community details",
    description="Get detailed information about a specific community.",
    responses={
        200: {"description": "Community details retrieved successfully"},
        404: {"description": "Project or community not found"},
    }
)
async def get_community_details(
    project: str,
    community_id: str,
    include_member_details: bool = Query(
        default=True,
        description="Include detailed member information"
    ),
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Get detailed information about a specific community.

    Returns community membership details, internal/external edge counts,
    and connected communities.

    - **project**: Project safe name
    - **community_id**: Community identifier
    - **include_member_details**: Include detailed member info
    """
    _verify_project(neo4j_handler, project)

    try:
        # Find the cluster/community
        cluster_result = neo4j_handler.find_clusters(project)

        if not cluster_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Community '{community_id}' not found"
            )

        # Find matching community
        community_data = None
        for cluster in cluster_result.get("clusters", []):
            if cluster.get("cluster_id") == community_id:
                community_data = cluster
                break

        if not community_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Community '{community_id}' not found"
            )

        # Build member details
        members = []
        entity_ids = community_data.get("entity_ids", [])

        if include_member_details:
            for entity_id in entity_ids:
                entity = neo4j_handler.get_person(project, entity_id)
                if entity:
                    member = CommunityMember(
                        entity_id=entity_id,
                        label=_get_entity_label(entity),
                        membership_score=1.0,
                        role="member"
                    )
                    members.append(member)
        else:
            members = [
                CommunityMember(entity_id=eid, label="", membership_score=1.0, role="member")
                for eid in entity_ids
            ]

        size = community_data.get("size", len(entity_ids))
        internal_edges = community_data.get("internal_edges", 0)
        max_edges = size * (size - 1) / 2 if size > 1 else 0
        density = internal_edges / max_edges if max_edges > 0 else 0.0

        return CommunityDetailResponse(
            community_id=community_id,
            size=size,
            density=round(density, 4),
            members=members,
            internal_edges=internal_edges,
            external_edges=0,  # Would need additional calculation
            connected_communities=[]  # Would need additional calculation
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get community details: {str(e)}"
        )


@router.get(
    "/entity/{entity_id}/community",
    response_model=EntityCommunityResponse,
    summary="Get entity's community membership",
    description="Get the community membership information for a specific entity.",
    responses={
        200: {"description": "Community membership retrieved successfully"},
        404: {"description": "Project or entity not found"},
    }
)
async def get_entity_community(
    project: str,
    entity_id: str,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Get community membership for an entity.

    Returns the primary community the entity belongs to,
    along with any overlapping community memberships.

    - **project**: Project safe name
    - **entity_id**: Entity identifier
    """
    _verify_project(neo4j_handler, project)
    _verify_entity(neo4j_handler, project, entity_id)

    try:
        # Find communities and locate entity
        cluster_result = neo4j_handler.find_clusters(project)

        if not cluster_result:
            return EntityCommunityResponse(
                entity_id=entity_id,
                community_id=None,
                membership_score=0.0,
                role="isolated",
                overlapping_communities=[]
            )

        # Find entity's community
        community_id = None
        role = "member"

        for cluster in cluster_result.get("clusters", []):
            if entity_id in cluster.get("entity_ids", []):
                community_id = cluster.get("cluster_id")

                # Determine role
                if cluster.get("is_isolated", False):
                    role = "isolated"
                elif entity_id == cluster.get("entity_ids", [None])[0]:
                    role = "hub"
                break

        return EntityCommunityResponse(
            entity_id=entity_id,
            community_id=community_id,
            membership_score=1.0 if community_id else 0.0,
            role=role,
            overlapping_communities=[]
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get entity community: {str(e)}"
        )


# =============================================================================
# SIMILARITY ANALYSIS ENDPOINTS
# =============================================================================

@router.get(
    "/entity/{entity_id}/similar",
    response_model=SimilarEntitiesResponse,
    summary="Find similar entities",
    description="Find entities similar to the specified entity based on structural similarity.",
    responses={
        200: {"description": "Similar entities found successfully"},
        404: {"description": "Project or entity not found"},
    }
)
async def find_similar_entities(
    project: str,
    entity_id: str,
    metric: SimilarityMetric = Query(
        default=SimilarityMetric.JACCARD,
        description="Similarity metric to use"
    ),
    min_similarity: float = Query(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score to include"
    ),
    limit: int = Query(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of similar entities to return"
    ),
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Find entities similar to the specified entity.

    Uses structural similarity based on shared neighbors
    and connection patterns.

    - **project**: Project safe name
    - **entity_id**: Source entity identifier
    - **metric**: Similarity metric (jaccard, cosine, etc.)
    - **min_similarity**: Minimum similarity threshold
    - **limit**: Maximum results to return
    """
    _verify_project(neo4j_handler, project)
    entity = _verify_entity(neo4j_handler, project, entity_id)

    try:
        # Get all entities and their connections
        entities = neo4j_handler.get_all_people(project) or []

        if not entities:
            return SimilarEntitiesResponse(
                entity_id=entity_id,
                metric=metric.value,
                similar_entities=[],
                total_found=0
            )

        # Build neighbor sets for each entity
        entity_neighbors: dict[str, set[str]] = {}
        for e in entities:
            eid = e.get("id")
            if not eid:
                continue

            neighbors = set()
            tags = e.get("tags", []) or []
            for tag in tags:
                if isinstance(tag, dict):
                    target = tag.get("target_id") or tag.get("tagged_entity_id")
                    if target:
                        neighbors.add(target)

            entity_neighbors[eid] = neighbors

        # Get source entity's neighbors
        source_neighbors = entity_neighbors.get(entity_id, set())

        # Calculate similarity with all other entities
        similarities = []
        for other_id, other_neighbors in entity_neighbors.items():
            if other_id == entity_id:
                continue

            # Calculate similarity based on metric
            if metric == SimilarityMetric.JACCARD:
                intersection = len(source_neighbors & other_neighbors)
                union = len(source_neighbors | other_neighbors)
                score = intersection / union if union > 0 else 0.0

            elif metric == SimilarityMetric.OVERLAP:
                intersection = len(source_neighbors & other_neighbors)
                min_size = min(len(source_neighbors), len(other_neighbors))
                score = intersection / min_size if min_size > 0 else 0.0

            elif metric == SimilarityMetric.ADAMIC_ADAR:
                import math
                common = source_neighbors & other_neighbors
                score = 0.0
                for common_neighbor in common:
                    neighbor_degree = len(entity_neighbors.get(common_neighbor, set()))
                    if neighbor_degree > 1:
                        score += 1.0 / math.log(neighbor_degree)

                # Normalize
                max_score = len(common) + 1
                score = score / max_score if max_score > 0 else 0.0

            else:  # Cosine
                intersection = len(source_neighbors & other_neighbors)
                magnitude = (len(source_neighbors) * len(other_neighbors)) ** 0.5
                score = intersection / magnitude if magnitude > 0 else 0.0

            if score >= min_similarity:
                # Get entity label
                other_entity = neo4j_handler.get_person(project, other_id)
                label = _get_entity_label(other_entity) if other_entity else other_id[:8]

                similarities.append(SimilarEntityResult(
                    entity_id=other_id,
                    label=label,
                    similarity_score=round(score, 4),
                    common_neighbors=len(source_neighbors & other_neighbors),
                    shared_attributes=[]
                ))

        # Sort by similarity and limit
        similarities.sort(key=lambda x: x.similarity_score, reverse=True)
        similarities = similarities[:limit]

        return SimilarEntitiesResponse(
            entity_id=entity_id,
            metric=metric.value,
            similar_entities=similarities,
            total_found=len(similarities)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to find similar entities: {str(e)}"
        )


@router.get(
    "/similarity/{entity1_id}/{entity2_id}",
    response_model=EntityComparisonResponse,
    summary="Compare two entities",
    description="Compare two entities and calculate their similarity.",
    responses={
        200: {"description": "Entities compared successfully"},
        404: {"description": "Project or entity not found"},
    }
)
async def compare_entities(
    project: str,
    entity1_id: str,
    entity2_id: str,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Compare two entities and calculate similarity metrics.

    Returns multiple similarity scores, common neighbors count,
    path distance, and shared community memberships.

    - **project**: Project safe name
    - **entity1_id**: First entity identifier
    - **entity2_id**: Second entity identifier
    """
    _verify_project(neo4j_handler, project)
    entity1 = _verify_entity(neo4j_handler, project, entity1_id)
    entity2 = _verify_entity(neo4j_handler, project, entity2_id)

    try:
        # Get neighbors for both entities
        def get_neighbors(entity: dict) -> set[str]:
            neighbors = set()
            tags = entity.get("tags", []) or []
            for tag in tags:
                if isinstance(tag, dict):
                    target = tag.get("target_id") or tag.get("tagged_entity_id")
                    if target:
                        neighbors.add(target)
            return neighbors

        neighbors1 = get_neighbors(entity1)
        neighbors2 = get_neighbors(entity2)

        # Calculate similarity metrics
        common = neighbors1 & neighbors2
        union = neighbors1 | neighbors2

        jaccard = len(common) / len(union) if union else 0.0
        overlap_denom = min(len(neighbors1), len(neighbors2))
        overlap = len(common) / overlap_denom if overlap_denom > 0 else 0.0
        cosine_denom = (len(neighbors1) * len(neighbors2)) ** 0.5
        cosine = len(common) / cosine_denom if cosine_denom > 0 else 0.0

        # Get path distance
        path_result = neo4j_handler.find_shortest_path(project, entity1_id, entity2_id)
        path_distance = None
        if path_result and path_result.get("found"):
            path_distance = path_result.get("path_length")

        # Get shared communities
        cluster_result = neo4j_handler.find_clusters(project)
        shared_communities = []
        if cluster_result:
            for cluster in cluster_result.get("clusters", []):
                entity_ids = cluster.get("entity_ids", [])
                if entity1_id in entity_ids and entity2_id in entity_ids:
                    shared_communities.append(cluster.get("cluster_id", ""))

        return EntityComparisonResponse(
            entity1_id=entity1_id,
            entity2_id=entity2_id,
            similarity_scores={
                "jaccard": round(jaccard, 4),
                "overlap": round(overlap, 4),
                "cosine": round(cosine, 4)
            },
            common_neighbors_count=len(common),
            path_distance=path_distance,
            shared_communities=shared_communities
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compare entities: {str(e)}"
        )


@router.get(
    "/common-neighbors/{entity1_id}/{entity2_id}",
    response_model=CommonNeighborsResponse,
    summary="Get common neighbors",
    description="Get entities that are connected to both specified entities.",
    responses={
        200: {"description": "Common neighbors retrieved successfully"},
        404: {"description": "Project or entity not found"},
    }
)
async def get_common_neighbors(
    project: str,
    entity1_id: str,
    entity2_id: str,
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Get common neighbors between two entities.

    Returns entities that have relationships with both specified entities,
    along with the Adamic-Adar similarity score.

    - **project**: Project safe name
    - **entity1_id**: First entity identifier
    - **entity2_id**: Second entity identifier
    """
    _verify_project(neo4j_handler, project)
    entity1 = _verify_entity(neo4j_handler, project, entity1_id)
    entity2 = _verify_entity(neo4j_handler, project, entity2_id)

    try:
        # Get all entities to build neighbor map
        entities = neo4j_handler.get_all_people(project) or []

        # Build neighbor map with relationship types
        neighbor_map: dict[str, dict[str, str]] = {}
        for e in entities:
            eid = e.get("id")
            if not eid:
                continue

            neighbor_map[eid] = {}
            tags = e.get("tags", []) or []
            for tag in tags:
                if isinstance(tag, dict):
                    target = tag.get("target_id") or tag.get("tagged_entity_id")
                    rel_type = tag.get("type", tag.get("label", "RELATED_TO"))
                    if target:
                        neighbor_map[eid][target] = rel_type

        # Get neighbors for both entities
        neighbors1 = set(neighbor_map.get(entity1_id, {}).keys())
        neighbors2 = set(neighbor_map.get(entity2_id, {}).keys())

        # Find common neighbors
        common_neighbor_ids = neighbors1 & neighbors2

        # Build common neighbor details
        common_neighbors = []
        import math
        adamic_adar_score = 0.0

        for neighbor_id in common_neighbor_ids:
            neighbor_entity = neo4j_handler.get_person(project, neighbor_id)
            label = _get_entity_label(neighbor_entity) if neighbor_entity else neighbor_id[:8]

            rel_to_1 = neighbor_map.get(entity1_id, {}).get(neighbor_id, "RELATED_TO")
            rel_to_2 = neighbor_map.get(entity2_id, {}).get(neighbor_id, "RELATED_TO")

            common_neighbors.append(CommonNeighbor(
                entity_id=neighbor_id,
                label=label,
                relationship_to_entity1=rel_to_1,
                relationship_to_entity2=rel_to_2
            ))

            # Calculate Adamic-Adar contribution
            neighbor_degree = len(neighbor_map.get(neighbor_id, {}))
            if neighbor_degree > 1:
                adamic_adar_score += 1.0 / math.log(neighbor_degree)

        return CommonNeighborsResponse(
            entity1_id=entity1_id,
            entity2_id=entity2_id,
            common_neighbors=common_neighbors,
            total_count=len(common_neighbors),
            adamic_adar_score=round(adamic_adar_score, 4)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get common neighbors: {str(e)}"
        )


# =============================================================================
# INFLUENCE ANALYSIS ENDPOINTS
# =============================================================================

@router.get(
    "/influence",
    response_model=InfluenceRankingsResponse,
    summary="Get entity influence rankings",
    description="Calculate and return influence rankings for entities using PageRank or other metrics.",
    responses={
        200: {"description": "Influence rankings calculated successfully"},
        404: {"description": "Project not found"},
    }
)
async def get_influence_rankings(
    project: str,
    metric: InfluenceMetric = Query(
        default=InfluenceMetric.PAGERANK,
        description="Influence metric to use"
    ),
    damping_factor: float = Query(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Damping factor for PageRank algorithm"
    ),
    iterations: int = Query(
        default=100,
        ge=10,
        le=1000,
        description="Maximum iterations for convergence"
    ),
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Number of top entities to return"
    ),
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Get influence rankings for entities in the project.

    Calculates influence scores using PageRank or other centrality metrics.
    Returns entities ranked by their influence in the network.

    - **project**: Project safe name
    - **metric**: Influence metric to use
    - **damping_factor**: PageRank damping factor
    - **iterations**: Max iterations for convergence
    - **limit**: Number of top entities to return
    """
    _verify_project(neo4j_handler, project)

    try:
        # Get all entities and build graph
        entities = neo4j_handler.get_all_people(project) or []

        if not entities:
            return InfluenceRankingsResponse(
                metric=metric.value,
                damping_factor=damping_factor,
                rankings=[],
                total_entities=0,
                convergence_iterations=0
            )

        # Build adjacency
        entity_map = {e.get("id"): e for e in entities if e.get("id")}
        adjacency: dict[str, set[str]] = {eid: set() for eid in entity_map}

        for e in entities:
            eid = e.get("id")
            if not eid:
                continue

            tags = e.get("tags", []) or []
            for tag in tags:
                if isinstance(tag, dict):
                    target = tag.get("target_id") or tag.get("tagged_entity_id")
                    if target and target in entity_map:
                        adjacency[eid].add(target)
                        adjacency[target].add(eid)  # Undirected

        n = len(entity_map)

        if metric == InfluenceMetric.PAGERANK:
            # PageRank algorithm
            scores = {eid: 1.0 / n for eid in entity_map}

            for iteration in range(iterations):
                new_scores = {}
                for eid in entity_map:
                    # Sum contributions from incoming edges
                    incoming_sum = 0.0
                    for neighbor in adjacency[eid]:
                        out_degree = len(adjacency[neighbor])
                        if out_degree > 0:
                            incoming_sum += scores[neighbor] / out_degree

                    new_scores[eid] = (1 - damping_factor) / n + damping_factor * incoming_sum

                # Check convergence
                diff = sum(abs(new_scores[eid] - scores[eid]) for eid in entity_map)
                scores = new_scores

                if diff < 1e-6:
                    convergence = iteration + 1
                    break
            else:
                convergence = iterations

        elif metric == InfluenceMetric.DEGREE:
            scores = {eid: len(neighbors) for eid, neighbors in adjacency.items()}
            max_score = max(scores.values()) if scores else 1
            scores = {eid: score / max_score for eid, score in scores.items()}
            convergence = 1

        elif metric == InfluenceMetric.BETWEENNESS:
            # Simplified betweenness centrality
            scores = {eid: 0.0 for eid in entity_map}

            for source in entity_map:
                # BFS from source
                distances = {source: 0}
                paths = {source: 1}
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

                # Accumulate
                delta = {eid: 0.0 for eid in entity_map}
                for node in reversed(order[1:]):
                    for neighbor in adjacency[node]:
                        if distances.get(neighbor, -1) == distances.get(node, 0) - 1:
                            delta[neighbor] += (paths[neighbor] / max(paths[node], 1)) * (1 + delta[node])
                    scores[node] += delta[node]

            # Normalize
            max_score = max(scores.values()) if scores else 1
            if max_score > 0:
                scores = {eid: score / max_score for eid, score in scores.items()}
            convergence = 1

        else:  # Closeness, Eigenvector - simplified to degree for now
            scores = {eid: len(neighbors) / (n - 1) for eid, neighbors in adjacency.items()}
            convergence = 1

        # Build rankings
        sorted_entities = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        rankings = []

        for rank, (eid, score) in enumerate(sorted_entities[:limit], 1):
            entity = entity_map.get(eid, {})
            label = _get_entity_label(entity)

            rankings.append(EntityInfluence(
                entity_id=eid,
                label=label,
                influence_score=round(score, 6),
                rank=rank,
                metrics={metric.value: round(score, 6)}
            ))

        return InfluenceRankingsResponse(
            metric=metric.value,
            damping_factor=damping_factor,
            rankings=rankings,
            total_entities=n,
            convergence_iterations=convergence
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate influence rankings: {str(e)}"
        )


@router.get(
    "/influence/{entity_id}/spread",
    response_model=InfluenceSpreadResponse,
    summary="Simulate influence spread",
    description="Simulate how influence spreads from a given entity through the network.",
    responses={
        200: {"description": "Influence spread simulated successfully"},
        404: {"description": "Project or entity not found"},
    }
)
async def simulate_influence_spread(
    project: str,
    entity_id: str,
    steps: int = Query(
        default=5,
        ge=1,
        le=20,
        description="Number of propagation steps"
    ),
    spread_probability: float = Query(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Probability of influence spreading per edge"
    ),
    model: str = Query(
        default="independent_cascade",
        description="Propagation model (independent_cascade, linear_threshold)"
    ),
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Simulate influence spread from a source entity.

    Models how influence propagates through the network starting
    from the specified entity using cascade or threshold models.

    - **project**: Project safe name
    - **entity_id**: Starting entity identifier
    - **steps**: Number of propagation steps
    - **spread_probability**: Probability per edge
    - **model**: Propagation model to use
    """
    _verify_project(neo4j_handler, project)
    source_entity = _verify_entity(neo4j_handler, project, entity_id)

    try:
        import random

        # Get all entities and build graph
        entities = neo4j_handler.get_all_people(project) or []
        entity_map = {e.get("id"): e for e in entities if e.get("id")}

        # Build adjacency
        adjacency: dict[str, set[str]] = {eid: set() for eid in entity_map}
        for e in entities:
            eid = e.get("id")
            if not eid:
                continue

            tags = e.get("tags", []) or []
            for tag in tags:
                if isinstance(tag, dict):
                    target = tag.get("target_id") or tag.get("tagged_entity_id")
                    if target and target in entity_map:
                        adjacency[eid].add(target)

        # Run simulation
        activated = {entity_id: 0}  # entity_id -> activation step
        newly_activated = {entity_id}
        spread_by_step = {0: 1}

        for step in range(1, steps + 1):
            step_activated = set()

            for active_entity in newly_activated:
                for neighbor in adjacency.get(active_entity, set()):
                    if neighbor not in activated:
                        # Probabilistic activation
                        if random.random() < spread_probability:
                            step_activated.add(neighbor)
                            activated[neighbor] = step

            spread_by_step[step] = len(step_activated)
            newly_activated = step_activated

            if not newly_activated:
                break

        # Build response
        influenced_entities = []
        for eid, step in sorted(activated.items(), key=lambda x: x[1]):
            entity = entity_map.get(eid, {})
            label = _get_entity_label(entity)

            # Calculate activation probability based on step
            prob = spread_probability ** step if step > 0 else 1.0

            influenced_entities.append(InfluenceSpreadNode(
                entity_id=eid,
                label=label,
                activation_probability=round(prob, 4),
                activation_step=step
            ))

        return InfluenceSpreadResponse(
            source_entity_id=entity_id,
            model=model,
            steps=steps,
            spread_probability=spread_probability,
            total_influenced=len(activated),
            influenced_entities=influenced_entities,
            spread_by_step=spread_by_step
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to simulate influence spread: {str(e)}"
        )


@router.get(
    "/key-entities",
    response_model=KeyEntitiesResponse,
    summary="Find key/critical entities",
    description="Identify key entities that are critical to network structure.",
    responses={
        200: {"description": "Key entities identified successfully"},
        404: {"description": "Project not found"},
    }
)
async def find_key_entities(
    project: str,
    analysis_type: str = Query(
        default="structural",
        description="Analysis type (structural, bridge, hub)"
    ),
    limit: int = Query(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of key entities to return"
    ),
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Find key/critical entities in the network.

    Identifies entities that are structurally important,
    such as hubs (highly connected) or bridges (connecting communities).

    - **project**: Project safe name
    - **analysis_type**: Type of analysis (structural, bridge, hub)
    - **limit**: Maximum results to return
    """
    _verify_project(neo4j_handler, project)

    try:
        # Get most connected entities
        result = neo4j_handler.get_most_connected(project, limit=limit)

        if not result or not result.get("entities"):
            return KeyEntitiesResponse(
                key_entities=[],
                total_found=0,
                analysis_type=analysis_type,
                network_vulnerability=0.0
            )

        # Build key entities list
        key_entities = []
        total_connections = sum(
            e.get("total_connections", 0) for e in result.get("entities", [])
        )

        for entity_data in result.get("entities", []):
            eid = entity_data.get("entity_id", "")
            entity = entity_data.get("entity", {})
            connections = entity_data.get("total_connections", 0)

            # Calculate criticality based on connections
            criticality = connections / total_connections if total_connections > 0 else 0.0

            # Determine role
            if connections > result.get("total_entities_analyzed", 1) * 0.3:
                role = "hub"
            elif entity_data.get("outgoing_connections", 0) > 0 and entity_data.get("incoming_connections", 0) > 0:
                role = "broker"
            else:
                role = "key"

            key_entities.append(KeyEntity(
                entity_id=eid,
                label=_get_entity_label(entity),
                criticality_score=round(criticality, 4),
                role=role,
                impact_if_removed={
                    "connections_lost": connections,
                    "estimated_fragmentation": round(criticality * 0.5, 4)
                }
            ))

        # Calculate network vulnerability
        if key_entities:
            top_criticality = sum(e.criticality_score for e in key_entities[:3])
            vulnerability = min(top_criticality / 3, 1.0)
        else:
            vulnerability = 0.0

        return KeyEntitiesResponse(
            key_entities=key_entities,
            total_found=len(key_entities),
            analysis_type=analysis_type,
            network_vulnerability=round(vulnerability, 4)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to find key entities: {str(e)}"
        )


# =============================================================================
# TEMPORAL PATTERNS ENDPOINT
# =============================================================================

@router.get(
    "/patterns/temporal",
    response_model=TemporalPatternsResponse,
    summary="Detect temporal relationship patterns",
    description="Detect temporal patterns in relationship creation and modification.",
    responses={
        200: {"description": "Temporal patterns detected successfully"},
        404: {"description": "Project not found"},
    }
)
async def detect_temporal_patterns(
    project: str,
    pattern_types: Optional[str] = Query(
        default=None,
        description="Comma-separated pattern types to detect (burst, periodic, trend, anomaly)"
    ),
    start_date: Optional[str] = Query(
        default=None,
        description="Start date for analysis (ISO 8601 format)"
    ),
    end_date: Optional[str] = Query(
        default=None,
        description="End date for analysis (ISO 8601 format)"
    ),
    min_confidence: float = Query(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum pattern confidence to report"
    ),
    neo4j_handler=Depends(get_neo4j_handler)
):
    """
    Detect temporal patterns in the relationship graph.

    Analyzes timestamps of entity and relationship creation to identify
    patterns like bursts of activity, periodic behaviors, or anomalies.

    - **project**: Project safe name
    - **pattern_types**: Types of patterns to detect
    - **start_date**: Analysis start date
    - **end_date**: Analysis end date
    - **min_confidence**: Minimum confidence threshold
    """
    _verify_project(neo4j_handler, project)

    try:
        from datetime import datetime, timezone

        # Parse pattern types
        requested_types = None
        if pattern_types:
            requested_types = [t.strip().lower() for t in pattern_types.split(",")]

        # Get all entities with timestamps
        entities = neo4j_handler.get_all_people(project) or []

        if not entities:
            return TemporalPatternsResponse(
                patterns=[],
                total_found=0,
                time_range={},
                pattern_types_found=[]
            )

        # Extract timestamps
        timestamps = []
        for e in entities:
            created = e.get("created_at")
            if created:
                try:
                    if isinstance(created, str):
                        dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    else:
                        dt = created
                    timestamps.append((e.get("id"), dt))
                except (ValueError, TypeError):
                    pass

        if not timestamps:
            return TemporalPatternsResponse(
                patterns=[],
                total_found=0,
                time_range={},
                pattern_types_found=[]
            )

        # Sort by timestamp
        timestamps.sort(key=lambda x: x[1])

        # Determine time range
        min_time = timestamps[0][1]
        max_time = timestamps[-1][1]

        # Detect patterns
        patterns = []
        pattern_types_found = []

        # Burst detection (simple threshold-based)
        if not requested_types or "burst" in requested_types:
            # Group by day and find bursts
            from collections import defaultdict
            daily_counts = defaultdict(list)

            for eid, dt in timestamps:
                day = dt.date().isoformat()
                daily_counts[day].append(eid)

            avg_daily = len(timestamps) / max(len(daily_counts), 1)

            for day, entity_ids in daily_counts.items():
                if len(entity_ids) > avg_daily * 2:  # Burst threshold
                    confidence = min(len(entity_ids) / (avg_daily * 3), 1.0)
                    if confidence >= min_confidence:
                        patterns.append(TemporalPattern(
                            pattern_id=f"burst_{day}",
                            pattern_type="burst",
                            start_time=f"{day}T00:00:00Z",
                            end_time=f"{day}T23:59:59Z",
                            confidence=round(confidence, 2),
                            affected_entities=entity_ids,
                            description=f"Activity burst detected on {day} with {len(entity_ids)} entities",
                            metadata={"count": len(entity_ids), "average": round(avg_daily, 2)}
                        ))
                        if "burst" not in pattern_types_found:
                            pattern_types_found.append("burst")

        # Trend detection (simple linear)
        if not requested_types or "trend" in requested_types:
            if len(daily_counts) > 7:
                # Compare first half vs second half
                sorted_days = sorted(daily_counts.keys())
                mid = len(sorted_days) // 2

                first_half_avg = sum(len(daily_counts[d]) for d in sorted_days[:mid]) / max(mid, 1)
                second_half_avg = sum(len(daily_counts[d]) for d in sorted_days[mid:]) / max(len(sorted_days) - mid, 1)

                if second_half_avg > first_half_avg * 1.5:
                    trend_confidence = min((second_half_avg / first_half_avg - 1) / 2, 1.0)
                    if trend_confidence >= min_confidence:
                        patterns.append(TemporalPattern(
                            pattern_id="trend_increasing",
                            pattern_type="trend",
                            start_time=min_time.isoformat(),
                            end_time=max_time.isoformat(),
                            confidence=round(trend_confidence, 2),
                            affected_entities=[],
                            description="Increasing activity trend detected",
                            metadata={
                                "direction": "increasing",
                                "first_half_avg": round(first_half_avg, 2),
                                "second_half_avg": round(second_half_avg, 2)
                            }
                        ))
                        if "trend" not in pattern_types_found:
                            pattern_types_found.append("trend")

        return TemporalPatternsResponse(
            patterns=patterns,
            total_found=len(patterns),
            time_range={
                "start": min_time.isoformat(),
                "end": max_time.isoformat()
            },
            pattern_types_found=pattern_types_found
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to detect temporal patterns: {str(e)}"
        )
