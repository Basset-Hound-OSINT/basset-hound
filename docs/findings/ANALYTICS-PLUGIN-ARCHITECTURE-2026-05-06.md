# Analytics Plugin Architecture Design

**Date:** 2026-05-06  
**Status:** Proposed Architecture (Research & Design)  
**Purpose:** Enable modular, optional analytics extensions without coupling to core OSINT platform

---

## Vision

Basset Hound's core strength is fast OSINT data collection and organization. Analytics should be **optional, pluggable, and scalable** so investigators can:

1. **Start simple:** Use only what they need (basic path finding)
2. **Grow gradually:** Add community detection, centrality measures as needed
3. **Stay flexible:** Swap implementations (Python → NetworkX → GDS) without breaking API
4. **Scale efficiently:** Deploy ML workloads separately if needed
5. **Maintain security:** Keep heavy dependencies optional, avoid supply chain risks

---

## Architecture Overview

### Three-Tier Analytics Stack

```
┌─────────────────────────────────────────────────────┐
│  REST API Layer (api/routers/*)                     │
│  - Standard endpoints (no changes)                  │
│  - All current functionality                        │
└────────────┬────────────────────────────────────────┘
             │
┌────────────▼────────────────────────────────────────┐
│  Analytics Plugin Layer (new)                       │
│                                                     │
│  ┌─────────────────────────────────────────────┐  │
│  │ Core (Always On)                            │  │
│  │ - Path finding, clusters, basic centrality  │  │
│  │ - No external dependencies                  │  │
│  └─────────────────────────────────────────────┘  │
│                                                     │
│  ┌─────────────────────────────────────────────┐  │
│  │ Analytics Light (Feature Flag)              │  │
│  │ - Community detection (Louvain, LPA)        │  │
│  │ - Centrality (PageRank, betweenness)        │  │
│  │ - Similarity metrics, influence simulation  │  │
│  │ - Requires: networkx, numpy                 │  │
│  └─────────────────────────────────────────────┘  │
│                                                     │
│  ┌─────────────────────────────────────────────┐  │
│  │ Analytics GDS (Feature Flag, Enterprise)    │  │
│  │ - Neo4j GDS integration                     │  │
│  │ - Automatic fallback to NetworkX            │  │
│  │ - Requires: Neo4j Enterprise Edition        │  │
│  └─────────────────────────────────────────────┘  │
│                                                     │
│  ┌─────────────────────────────────────────────┐  │
│  │ Analytics ML (Separate Service, Optional)   │  │
│  │ - ML-based clustering, entity linking       │  │
│  │ - Query suggestions, semantic similarity    │  │
│  │ - Zero-result prediction                    │  │
│  │ - Requires: sklearn, scipy, pandas, torch   │  │
│  └─────────────────────────────────────────────┘  │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## Layer 1: Core Analytics (Always On)

**File:** `api/analytics/core.py` (existing or new)  
**Dependencies:** None beyond Neo4j  
**Endpoints:** Current `analysis.py` endpoints

**What's Included:**
- Shortest path finding (BFS)
- All paths finding (DFS)
- Connected components (clusters)
- Degree centrality
- Neighborhood exploration

**Guaranteed Performance:**
- <1K entities: <100ms response time
- <10K entities: <1s response time

**Stability:** Production-ready, no changes planned

---

## Layer 2: Analytics Light (NetworkX-Based)

### Overview

**File:** `api/analytics/light.py` (new)  
**Feature Flag:** `ENABLE_ANALYTICS_LIGHT=true/false` (default: true)  
**Dependencies:** `networkx>=3.0` (optional, ~4MB)  
**Requires:** Python 3.9+

**When to Enable:**
- Growing investigations (100-10K entities)
- Need advanced centrality measures
- Want community detection
- Can accept 1-5s response times

**When to Disable:**
- Minimal resource constraints
- Only basic path finding needed
- Dependency management critical

### Algorithms Implemented

#### Community Detection

```python
# api/analytics/light.py::detect_communities()

class CommunityDetectionInput(BaseModel):
    project_id: str
    algorithm: Literal["louvain", "label_propagation", "connected_components"]
    resolution: float = 1.0  # For Louvain

class CommunityInfo(BaseModel):
    id: str
    member_ids: List[str]
    size: int
    density: float
    modularity: Optional[float]  # For Louvain

async def detect_communities(
    project_id: str,
    algorithm: str = "louvain",
    resolution: float = 1.0,
) -> List[CommunityInfo]:
    """
    Detect communities using NetworkX.
    Falls back to current implementation if NetworkX unavailable.
    """
    try:
        import networkx as nx
        from networkx.algorithms import community
    except ImportError:
        logger.warning("NetworkX not available, using fallback")
        return fallback_detect_communities(project_id)
    
    # Fetch graph
    G = await fetch_graph_from_neo4j(project_id)
    
    if algorithm == "louvain":
        communities_list = list(community.greedy_modularity_communities(
            G, weight=None, resolution=resolution
        ))
        # Calculate modularity
        modularity = community.modularity(G, communities_list)
    elif algorithm == "label_propagation":
        communities_list = list(community.label_propagation_communities(G))
        modularity = None
    else:  # connected_components
        communities_list = list(nx.connected_components(G))
        modularity = None
    
    # Convert to response
    results = []
    for i, members in enumerate(communities_list):
        subgraph = G.subgraph(members)
        density = nx.density(subgraph)
        results.append(CommunityInfo(
            id=f"community_{i}",
            member_ids=list(members),
            size=len(members),
            density=density,
            modularity=modularity / len(communities_list) if modularity else None
        ))
    
    return sorted(results, key=lambda x: x.size, reverse=True)
```

#### Centrality Measures

```python
# api/analytics/light.py::calculate_centrality()

class CentralityInput(BaseModel):
    project_id: str
    metric: Literal[
        "pagerank", 
        "betweenness", 
        "closeness", 
        "eigenvector",
        "degree"
    ]
    top_n: int = 20

class CentralityResult(BaseModel):
    entity_id: str
    score: float
    rank: int

async def calculate_centrality(
    project_id: str,
    metric: str = "pagerank",
    top_n: int = 20,
) -> List[CentralityResult]:
    """
    Calculate centrality metrics using NetworkX.
    Falls back to current implementation if NetworkX unavailable.
    """
    try:
        import networkx as nx
    except ImportError:
        logger.warning("NetworkX not available, using fallback")
        return fallback_calculate_centrality(project_id, metric, top_n)
    
    G = await fetch_graph_from_neo4j(project_id)
    
    if metric == "pagerank":
        scores = nx.pagerank(G, alpha=0.85)
    elif metric == "betweenness":
        scores = nx.betweenness_centrality(G)
    elif metric == "closeness":
        scores = nx.closeness_centrality(G)
    elif metric == "eigenvector":
        try:
            scores = nx.eigenvector_centrality(G, max_iter=100)
        except nx.NetworkXError:
            # Fallback to degree if eigenvector doesn't converge
            scores = {node: G.degree(node) for node in G}
    else:  # degree
        scores = {node: G.degree(node) for node in G}
    
    # Sort and rank
    sorted_entities = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    
    results = []
    for rank, (entity_id, score) in enumerate(sorted_entities[:top_n], 1):
        results.append(CentralityResult(
            entity_id=entity_id,
            score=score,
            rank=rank
        ))
    
    return results
```

#### Similarity & Link Prediction

```python
# api/analytics/light.py::find_similar_entities()

class SimilarityMetric(str, Enum):
    JACCARD = "jaccard"
    COSINE = "cosine"
    RESOURCE_ALLOCATION = "resource_allocation"
    ADAMIC_ADAR = "adamic_adar"

async def find_similar_entities(
    project_id: str,
    entity_id: str,
    metric: str = "jaccard",
    limit: int = 10,
) -> List[dict]:
    """
    Find similar entities using NetworkX link prediction algorithms.
    """
    try:
        import networkx as nx
        from networkx.algorithms import link_prediction
    except ImportError:
        return fallback_find_similar_entities(project_id, entity_id, metric, limit)
    
    G = await fetch_graph_from_neo4j(project_id)
    
    if metric == "jaccard":
        similarities = list(link_prediction.jaccard_coefficient(
            G, 
            [(entity_id, node) for node in G.neighbors(entity_id)]
        ))
    elif metric == "cosine":
        similarities = list(link_prediction.cosine_similarity(
            G,
            [(entity_id, node) for node in G.neighbors(entity_id)]
        ))
    elif metric == "resource_allocation":
        similarities = list(link_prediction.resource_allocation_index(
            G,
            [(entity_id, node) for node in G.neighbors(entity_id)]
        ))
    else:  # adamic_adar
        similarities = list(link_prediction.adamic_adar_index(
            G,
            [(entity_id, node) for node in G.neighbors(entity_id)]
        ))
    
    # Sort and limit
    similarities.sort(key=lambda x: x[2], reverse=True)
    
    return [
        {"entity_id": target, "similarity_score": score}
        for _, target, score in similarities[:limit]
    ]
```

#### Key Entity Detection

```python
# api/analytics/light.py::find_key_entities()

class KeyEntityType(str, Enum):
    ARTICULATION_POINT = "articulation_point"
    BRIDGE_ENDPOINT = "bridge_endpoint"
    HIGH_DEGREE = "high_degree"
    GATEWAY = "gateway"

class KeyEntity(BaseModel):
    entity_id: str
    entity_type: KeyEntityType
    score: float
    description: str

async def find_key_entities(
    project_id: str,
    limit: int = 10,
) -> List[KeyEntity]:
    """
    Find key/critical entities (articulation points, bridges, hubs).
    """
    try:
        import networkx as nx
    except ImportError:
        return fallback_find_key_entities(project_id, limit)
    
    G = await fetch_graph_from_neo4j(project_id)
    
    key_entities: Dict[str, KeyEntity] = {}
    
    # Articulation points (removal disconnects graph)
    for node in nx.articulation_points(G):
        key_entities[node] = KeyEntity(
            entity_id=node,
            entity_type=KeyEntityType.ARTICULATION_POINT,
            score=0.95,  # Highest importance
            description="Removing this entity would disconnect the graph"
        )
    
    # Bridges (removal increases components)
    for u, v in nx.bridges(G):
        for node in [u, v]:
            if node not in key_entities:
                key_entities[node] = KeyEntity(
                    entity_id=node,
                    entity_type=KeyEntityType.BRIDGE_ENDPOINT,
                    score=0.85,
                    description="Part of a bridge connection (weak point)"
                )
    
    # High-degree hubs
    degrees = [(node, G.degree(node)) for node in G]
    avg_degree = sum(d for _, d in degrees) / len(degrees)
    
    for node, degree in degrees:
        if node not in key_entities and degree > avg_degree * 2:
            normalized_score = min(0.8, degree / max(d for _, d in degrees))
            key_entities[node] = KeyEntity(
                entity_id=node,
                entity_type=KeyEntityType.HIGH_DEGREE,
                score=normalized_score,
                description=f"Hub with {degree} connections (avg {avg_degree:.0f})"
            )
    
    # Sort by score and limit
    sorted_entities = sorted(
        key_entities.values(),
        key=lambda x: x.score,
        reverse=True
    )
    
    return sorted_entities[:limit]
```

### Graceful Degradation Strategy

**Design Principle:** If NetworkX not installed, seamlessly fall back to current implementations.

```python
# api/analytics/light.py::__init__.py

NETWORKX_AVAILABLE = False
try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    logger.warning("NetworkX not installed; using fallback implementations")

async def detect_communities(project_id, algorithm="louvain", **kwargs):
    """Smart router: use NetworkX if available, else fallback"""
    if NETWORKX_AVAILABLE:
        return await _detect_communities_networkx(project_id, algorithm, **kwargs)
    else:
        return await _detect_communities_fallback(project_id)
```

---

## Layer 3: Analytics GDS (Enterprise Neo4j)

### Overview

**File:** `api/analytics/gds.py` (new, optional)  
**Feature Flag:** `ENABLE_ANALYTICS_GDS=true/false` (default: false)  
**Requirements:** Neo4j Enterprise Edition 5.0+  
**Performance:** 10-100× faster than NetworkX

### Runtime Detection

```python
# api/analytics/gds.py::__init__.py

import logging
from typing import Optional

logger = logging.getLogger(__name__)

GDS_AVAILABLE = False
NEO4J_ENTERPRISE = False

async def check_gds_availability(neo4j_driver) -> bool:
    """Check if Neo4j GDS is available at startup"""
    global GDS_AVAILABLE, NEO4J_ENTERPRISE
    
    try:
        async with neo4j_driver.session() as session:
            result = await session.run("RETURN gds.version() AS version")
            record = await result.single()
            
            if record:
                version = record["version"]
                logger.info(f"Neo4j GDS available: {version}")
                GDS_AVAILABLE = True
                NEO4J_ENTERPRISE = True
                return True
    except Exception as e:
        logger.debug(f"GDS check failed: {e}")
        GDS_AVAILABLE = False
    
    return False

async def initialize_gds(neo4j_driver):
    """Call at startup to detect GDS"""
    await check_gds_availability(neo4j_driver)
    if not GDS_AVAILABLE:
        logger.warning("GDS not available; falling back to NetworkX/Python")
```

### GDS Algorithms

```python
# api/analytics/gds.py::louvain

async def detect_communities_gds(
    neo4j_driver,
    project_id: str,
    resolution: float = 1.0,
) -> List[CommunityInfo]:
    """Run Louvain using Neo4j GDS"""
    
    if not GDS_AVAILABLE:
        raise ValueError("GDS not available; use NetworkX fallback")
    
    async with neo4j_driver.session() as session:
        # Create graph projection
        graph_name = f"basset_louvain_{project_id}"
        
        try:
            # Drop any existing projection
            await session.run(
                f"CALL gds.graph.drop($name, false)",
                name=graph_name
            )
        except:
            pass  # Doesn't exist
        
        # Project graph
        await session.run("""
            CALL gds.graph.project.cypher(
                $graph_name,
                'MATCH (p:Project {safe_name: $project})-[:HAS_PERSON]->(n:Person) 
                 RETURN id(n) AS id',
                'MATCH (p:Project {safe_name: $project})-[:HAS_PERSON]->(n1:Person)-[]->(n2:Person) 
                 RETURN id(n1) AS source, id(n2) AS target'
            )
        """, graph_name=graph_name, project=project_id)
        
        # Run Louvain
        result = await session.run("""
            CALL gds.louvain.stream($graph_name, {
                maxLevels: 10,
                tolerance: 0.0001
            })
            YIELD nodeId, communityId, intermediateCommunityIds
            RETURN gds.util.asNode(nodeId).id AS entityId, communityId
        """, graph_name=graph_name)
        
        records = await result.data()
        
        # Get modularity
        modularity_result = await session.run("""
            CALL gds.louvain.stats($graph_name, {
                maxLevels: 10,
                tolerance: 0.0001
            })
            YIELD modularity
            RETURN modularity
        """, graph_name=graph_name)
        
        modularity_record = await modularity_result.single()
        modularity = modularity_record["modularity"] if modularity_record else None
        
        # Clean up projection
        await session.run(
            f"CALL gds.graph.drop($name, false)",
            name=graph_name
        )
    
    # Convert to response
    communities_dict = {}
    for record in records:
        comm_id = record["communityId"]
        if comm_id not in communities_dict:
            communities_dict[comm_id] = []
        communities_dict[comm_id].append(record["entityId"])
    
    communities = [
        CommunityInfo(
            id=f"community_{i}",
            member_ids=members,
            size=len(members),
            density=0.0,  # Would need subgraph query
            modularity=modularity
        )
        for i, members in enumerate(communities_dict.values())
    ]
    
    return sorted(communities, key=lambda x: x.size, reverse=True)
```

### Fallback Strategy

```python
# api/analytics/light.py::router integration

@router.get("/analytics/communities")
async def get_communities(
    project_id: str,
    algorithm: str = "louvain",
    resolution: float = 1.0,
):
    """Smart community detection: GDS → NetworkX → Python fallback"""
    
    if os.getenv("ENABLE_ANALYTICS_GDS") == "true" and GDS_AVAILABLE:
        try:
            return await gds.detect_communities_gds(
                neo4j_driver, project_id, resolution
            )
        except Exception as e:
            logger.warning(f"GDS failed, falling back to NetworkX: {e}")
            # Fall through to NetworkX
    
    if os.getenv("ENABLE_ANALYTICS_LIGHT") == "true" and NETWORKX_AVAILABLE:
        return await light.detect_communities(project_id, algorithm, resolution)
    
    # Final fallback: current implementation
    return await core.detect_communities(project_id, algorithm, resolution)
```

---

## Layer 4: Analytics ML (Separate Service)

### Overview

**Deployment:** Separate Docker service (docker-compose --profile ml)  
**Feature Flag:** `ENABLE_ANALYTICS_ML=true/false` (default: false)  
**Dependencies:** sklearn, scipy, pandas, torch (optional)  
**Communication:** REST API + optional message queue  
**Purpose:** Heavy ML-based analytics (clustering, NLP, link prediction)

### Architecture

```yaml
# docker-compose.yml (with --profile ml)

services:
  basset_api:
    profiles: ["core"]  # Always runs
    environment:
      ENABLE_ANALYTICS_LIGHT: ${ENABLE_ANALYTICS_LIGHT:-true}
      ENABLE_ANALYTICS_GDS: ${ENABLE_ANALYTICS_GDS:-false}
      ENABLE_ANALYTICS_ML: ${ENABLE_ANALYTICS_ML:-false}
    depends_on:
      - neo4j

  analytics_ml_worker:
    profiles: ["ml"]  # Only with --profile ml
    build:
      context: services/analytics_ml
      dockerfile: Dockerfile
    environment:
      BASSET_API_URL: http://basset_api:8000
      REDIS_URL: redis://redis:6379
    depends_on:
      - basset_api
      - redis
    volumes:
      - ./services/analytics_ml:/app
```

### ML Service Endpoints

```python
# services/analytics_ml/routers/ml_analytics.py

from fastapi import APIRouter, BackgroundTasks

router = APIRouter(prefix="/ml", tags=["ml-analytics"])

@router.post("/suggest")
async def query_suggestions(
    query: str,
    user_history: Optional[List[str]] = None,
    limit: int = 10,
) -> List[QuerySuggestion]:
    """
    ML-based query suggestions using TF-IDF + semantic similarity.
    
    From archived ml_analytics_service.py::suggest_queries()
    """
    pass

@router.get("/patterns")
async def detect_search_patterns(
    project_id: str,
    days: int = 7,
) -> List[SearchPattern]:
    """
    Detect trending/declining search patterns.
    
    From archived ml_analytics_service.py::detect_search_patterns()
    """
    pass

@router.get("/entities/{entity_id}/insights")
async def entity_insights(entity_id: str) -> List[EntityInsight]:
    """
    ML insights about entity (co-search relationships, data quality).
    
    From archived ml_analytics_service.py::get_entity_insights()
    """
    pass

@router.post("/cluster")
async def cluster_queries(
    queries: List[str],
    threshold: float = 0.6,
) -> Dict[str, List[str]]:
    """
    Group similar queries using ML clustering.
    
    From archived ml_analytics_service.py::cluster_similar_queries()
    """
    pass

@router.get("/predict-zero")
async def predict_zero_results(query: str) -> float:
    """
    Predict probability of zero results for a query.
    
    From archived ml_analytics_service.py::predict_zero_results()
    """
    pass
```

### Integration Points

```python
# api/routers/analytics.py (main API)

@router.post("/analytics/ml/suggest", tags=["ml-analytics"])
async def ml_query_suggestions(request: QuerySuggestionRequest):
    """Proxy to ML service if available"""
    if not os.getenv("ENABLE_ANALYTICS_ML") == "true":
        raise HTTPException(400, "ML analytics not enabled")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{ML_SERVICE_URL}/suggest",
            json=request.dict()
        )
        return response.json()
```

---

## Configuration & Feature Flags

### Environment Variables

```bash
# Core (always on, no flag needed)
# - Path finding, clusters, degree centrality

# Analytics Light (NetworkX-based)
ENABLE_ANALYTICS_LIGHT=true  # Enable community detection, centrality, similarity
ANALYTICS_LIGHT_CACHE_TTL=3600  # Cache results for 1 hour

# Analytics GDS (Neo4j Enterprise)
ENABLE_ANALYTICS_GDS=false  # Enable GDS if Neo4j Enterprise available
GDS_FALLBACK_TO_NETWORKX=true  # Use NetworkX if GDS fails

# Analytics ML (Separate service)
ENABLE_ANALYTICS_ML=false  # Enable ML service
ML_SERVICE_URL=http://localhost:8001  # ML service location
ML_SERVICE_TIMEOUT=60  # Request timeout in seconds

# Caching
CACHE_BACKEND=redis  # redis or memory
CACHE_REDIS_URL=redis://localhost:6379
CACHE_TTL_PAGERANK=86400  # 24 hours
CACHE_TTL_COMMUNITIES=604800  # 7 days
CACHE_TTL_SIMILARITY=3600  # 1 hour
```

### Runtime Configuration

```python
# api/config.py

from enum import Enum

class AnalyticsMode(str, Enum):
    CORE = "core"  # Path finding only
    LIGHT = "light"  # + NetworkX algorithms
    GDS = "gds"  # + Neo4j GDS (requires Enterprise)
    ML = "ml"  # + Separate ML service

class Settings(BaseSettings):
    # Analytics configuration
    analytics_light_enabled: bool = Field(default=True, env="ENABLE_ANALYTICS_LIGHT")
    analytics_gds_enabled: bool = Field(default=False, env="ENABLE_ANALYTICS_GDS")
    analytics_ml_enabled: bool = Field(default=False, env="ENABLE_ANALYTICS_ML")
    
    # Service URLs
    ml_service_url: str = Field(default="http://localhost:8001", env="ML_SERVICE_URL")
    cache_backend: str = Field(default="memory", env="CACHE_BACKEND")
    
    @property
    def analytics_mode(self) -> AnalyticsMode:
        """Determine current analytics mode"""
        if self.analytics_ml_enabled:
            return AnalyticsMode.ML
        elif self.analytics_gds_enabled:
            return AnalyticsMode.GDS
        elif self.analytics_light_enabled:
            return AnalyticsMode.LIGHT
        else:
            return AnalyticsMode.CORE
```

---

## Plugin Interface (Abstract Base Class)

```python
# api/analytics/base.py

from abc import ABC, abstractmethod
from typing import List, Dict, Any

class AnalyticsPlugin(ABC):
    """Base interface for analytics plugins"""
    
    @abstractmethod
    async def is_available(self) -> bool:
        """Check if plugin dependencies are available"""
        pass
    
    @abstractmethod
    async def detect_communities(
        self,
        project_id: str,
        algorithm: str = "louvain",
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Detect communities in entity graph"""
        pass
    
    @abstractmethod
    async def calculate_centrality(
        self,
        project_id: str,
        metric: str = "pagerank",
        **kwargs
    ) -> Dict[str, float]:
        """Calculate centrality metrics"""
        pass
    
    @abstractmethod
    async def find_similar_entities(
        self,
        project_id: str,
        entity_id: str,
        metric: str = "jaccard",
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Find similar entities"""
        pass
    
    @abstractmethod
    async def find_key_entities(
        self,
        project_id: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Find structurally important entities"""
        pass


class CoreAnalyticsPlugin(AnalyticsPlugin):
    """Lightweight core implementation (no external dependencies)"""
    
    async def is_available(self) -> bool:
        return True  # Always available
    
    async def detect_communities(self, project_id: str, **kwargs):
        # Use current graph_analytics.py implementation
        pass

class LightAnalyticsPlugin(AnalyticsPlugin):
    """NetworkX-based implementation"""
    
    async def is_available(self) -> bool:
        try:
            import networkx
            return True
        except ImportError:
            return False
    
    async def detect_communities(self, project_id: str, **kwargs):
        # Use NetworkX implementation
        pass

class GDSAnalyticsPlugin(AnalyticsPlugin):
    """Neo4j GDS implementation"""
    
    async def is_available(self) -> bool:
        return GDS_AVAILABLE and NEO4J_ENTERPRISE
    
    async def detect_communities(self, project_id: str, **kwargs):
        # Use GDS implementation
        pass


class AnalyticsRouter:
    """Smart router: tries plugins in preference order"""
    
    def __init__(self, neo4j_driver):
        self.plugins = [
            GDSAnalyticsPlugin(neo4j_driver),
            LightAnalyticsPlugin(neo4j_driver),
            CoreAnalyticsPlugin(neo4j_driver),
        ]
    
    async def detect_communities(self, project_id: str, **kwargs):
        """Try each plugin until one succeeds"""
        for plugin in self.plugins:
            if await plugin.is_available():
                try:
                    return await plugin.detect_communities(project_id, **kwargs)
                except Exception as e:
                    logger.warning(f"{plugin.__class__.__name__} failed: {e}")
                    continue
        
        raise RuntimeError("No analytics plugin available")
```

---

## Deployment Strategies

### Strategy 1: Minimal (Core Only)
**For:** Small teams, laptop-based OSINT, minimal dependencies  
**Components:** Current basset-hound (no changes)  
**Footprint:** 500MB Docker image  
**Performance:** <1K entities, <100ms response

```bash
docker-compose up
# ENABLE_ANALYTICS_LIGHT=false
# ENABLE_ANALYTICS_GDS=false
# ENABLE_ANALYTICS_ML=false
```

### Strategy 2: Standard (Core + Light)
**For:** Most OSINT operations, growing investigations  
**Components:** Basset Hound + NetworkX  
**Footprint:** 600MB Docker image  
**Performance:** <10K entities, <2s response

```bash
docker-compose up
# ENABLE_ANALYTICS_LIGHT=true
# ENABLE_ANALYTICS_GDS=false
# ENABLE_ANALYTICS_ML=false
```

### Strategy 3: Enterprise (Core + Light + GDS)
**For:** Large OSINT projects, Neo4j Enterprise users  
**Components:** Basset Hound + NetworkX + Neo4j GDS  
**Footprint:** 600MB Docker image  
**Performance:** <100K entities, <10s response

```bash
docker-compose up
ENABLE_ANALYTICS_LIGHT=true
ENABLE_ANALYTICS_GDS=true
ENABLE_ANALYTICS_ML=false
# Requires Neo4j Enterprise Edition
```

### Strategy 4: Full Stack (Core + Light + GDS + ML)
**For:** Intelligence analysis agencies, large-scale operations  
**Components:** Basset Hound + NetworkX + GDS + Separate ML service  
**Footprint:** 1.2GB total (600MB API + 600MB ML service)  
**Performance:** <1M entities (distributed)

```bash
docker-compose --profile ml up
# All features enabled
```

---

## Migration Path (Existing Implementations)

### Current State → Plugin State

**No breaking changes to existing APIs.**

```python
# api/routers/graph_analytics.py (UNCHANGED)

@router.get("/communities")
async def detect_communities(project: str, algorithm: str = "louvain"):
    # Existing implementation continues to work
    # But internally routes through plugin system
    
    # Before (direct):
    # return neo4j_handler.find_clusters(project)
    
    # After (via plugin):
    plugin = get_analytics_plugin()  # Smart router
    return await plugin.detect_communities(project, algorithm=algorithm)
```

**Gradual Migration:**

1. **Phase 1 (Now):** Keep existing code, add plugin layer underneath
2. **Phase 2 (Q2 2026):** Mark current implementations as "Core" plugin
3. **Phase 3 (Q3 2026):** Gradually deprecate direct Neo4j calls, use plugins
4. **Phase 4 (Q4 2026):** All analytics go through plugin interface

---

## Testing Strategy

### Unit Tests
```python
# tests/analytics/test_core_plugin.py
# tests/analytics/test_light_plugin.py
# tests/analytics/test_gds_plugin.py

async def test_community_detection_core():
    plugin = CoreAnalyticsPlugin(mock_neo4j)
    communities = await plugin.detect_communities("test_project")
    assert len(communities) > 0

async def test_community_detection_light():
    pytest.importorskip("networkx")
    plugin = LightAnalyticsPlugin(mock_neo4j)
    communities = await plugin.detect_communities("test_project")
    assert len(communities) > 0

async def test_plugin_fallback():
    router = AnalyticsRouter(mock_neo4j)
    # Should try all plugins
    communities = await router.detect_communities("test_project")
    assert len(communities) > 0
```

### Integration Tests
```python
# tests/analytics/test_analytics_integration.py

async def test_analytics_endpoint_routes_to_best_plugin():
    # Enable multiple plugins
    os.environ["ENABLE_ANALYTICS_LIGHT"] = "true"
    os.environ["ENABLE_ANALYTICS_GDS"] = "false"
    
    response = await client.get("/analytics/project1/communities")
    assert response.status_code == 200
    assert response.json()["communities"]

async def test_gds_fallback_to_networkx():
    # GDS unavailable, should use NetworkX
    os.environ["ENABLE_ANALYTICS_GDS"] = "true"
    # Mock GDS as unavailable
    
    response = await client.get("/analytics/project1/communities")
    assert response.status_code == 200
    # Should still work via NetworkX fallback
```

---

## Roadmap & Timeline

### Q2 2026: Plugin Foundation
- [ ] Implement plugin interface (base.py)
- [ ] Create CoreAnalyticsPlugin (wrap existing code)
- [ ] Add smart router (AnalyticsRouter)
- [ ] Feature flags in config
- [ ] Zero breaking changes to existing APIs

### Q3 2026: NetworkX Integration (Analytics Light)
- [ ] Implement LightAnalyticsPlugin
- [ ] Migrate community detection to NetworkX
- [ ] Add betweenness, articulation point detection
- [ ] Comprehensive testing
- [ ] Docker image optimization

### Q4 2026: Enterprise Support (Analytics GDS)
- [ ] Implement GDSAnalyticsPlugin
- [ ] Runtime GDS availability detection
- [ ] Fallback chain: GDS → NetworkX → Core
- [ ] Performance benchmarks
- [ ] Customer documentation

### Q1 2027: ML Service
- [ ] Migrate archived ML services to separate service
- [ ] REST API for query suggestions, zero-result prediction
- [ ] Optional docker-compose --profile ml
- [ ] Integration tests with basset-hound

### Q2 2027+: Advanced Features
- [ ] Graph embeddings (Node2Vec)
- [ ] Temporal community evolution
- [ ] Influence maximization
- [ ] Anomaly scoring

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **API Compatibility** | 100% backward compatible | Zero breaking changes |
| **Feature Adoption** | 50%+ use Analytics Light | ENV var adoption |
| **Performance** | 10× improvement with Light | Benchmark suite |
| **Scalability** | Support 100K entities | Performance tests |
| **Plugin Coverage** | All core algorithms | Test suite coverage |
| **User Experience** | Seamless fallback | No user-facing errors |

---

## Conclusion

This architecture enables Basset Hound to:
- **Stay lean:** Core platform has zero external ML dependencies
- **Scale gracefully:** Add algorithms without redeploying core
- **Be flexible:** Choose deployment strategy (minimal → full-stack)
- **Future-proof:** Easy to integrate new algorithms (GDS, ML, embeddings)
- **Maintain compatibility:** All existing APIs work unchanged

The plugin system is optional—drop in when needed, not forced on all users.

