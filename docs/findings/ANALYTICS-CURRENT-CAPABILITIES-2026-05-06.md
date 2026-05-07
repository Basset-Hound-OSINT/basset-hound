# Current Analytics Capabilities - Basset Hound

**Date:** 2026-05-06  
**Status:** Research & Documentation  
**Scope:** Inventory of all existing analytics endpoints and implementations

---

## Executive Summary

Basset Hound currently implements **two parallel analytics systems**:

1. **`api/routers/graph_analytics.py`** - Phase 18, inline Python-based graph analytics (24 endpoints, 1861 lines)
2. **`api/routers/analysis.py`** - Lightweight graph analysis (6 endpoints, 507 lines)

The archived `out-of-scope-ml/` folder contains four sophisticated ML services that were deemed out-of-scope for the current platform but are documented for future intelligence-analysis projects. The current implementations provide **lightweight, production-ready analytics without heavy ML dependencies**.

---

## Current Production Analytics

### Router: `api/routers/analysis.py` (Lightweight)

**Purpose:** Basic graph traversal and network analysis  
**Endpoints:** 6  
**Total Lines:** 507  
**Dependencies:** Neo4j only (no external ML libraries)

#### Endpoints & Algorithms

| Endpoint | HTTP | Algorithm | Time Complexity | What It Does |
|----------|------|-----------|-----------------|--------------|
| `/path/{entity1}/{entity2}` | GET | BFS (Breadth-First Search) | O(V+E) | Find shortest path between two entities |
| `/paths/{entity1}/{entity2}` | GET | DFS variant (depth-limited) | O(V+E×max_depth) | Find all paths up to max_depth (default 5) |
| `/centrality/{entity_id}` | GET | Degree centrality calculation | O(E) | Count incoming/outgoing connections per entity |
| `/most-connected` | GET | Degree sort | O(V log V) | Top N entities by total connections |
| `/neighborhood/{entity_id}` | GET | BFS (ego network) | O(2^depth × V) | All entities within N hops |
| `/clusters` | GET | Connected components (BFS/DFS) | O(V+E) | Find isolated subgraphs; separate networks |

#### Computation Method

- **Neo4j Native:** All endpoints use Neo4j driver directly via `neo4j_handler`
- **In-Memory Processing:** Minimal; mostly graph traversal queries
- **Caching:** None (real-time calculation)

#### Missing for Complete OSINT Workflow

- Community structure (which entities form tight groups)
- Centrality metrics beyond degree (PageRank, betweenness, closeness)
- Temporal analysis (when did connections form, activity patterns)
- Link prediction (likely missing relationships)
- Entity importance scoring

---

### Router: `api/routers/graph_analytics.py` (Advanced)

**Purpose:** Advanced graph analytics and intelligence analysis  
**Endpoints:** 24  
**Total Lines:** 1861  
**Dependencies:** Neo4j only (inline Python implementations)  
**Phase:** 18

#### Endpoints by Category

##### Community Detection (3 endpoints)

| Endpoint | Algorithm | Time Complexity | What It Does |
|----------|-----------|-----------------|--------------|
| `/communities` | Connected components + density | O(V+E) | Detect groups of densely connected entities; returns modularity score & community density |
| `/communities/{community_id}` | Cluster lookup + member details | O(C) where C=community size | Get detailed membership & internal/external edge counts for a community |
| `/entity/{entity_id}/community` | Community lookup | O(C) | What community is entity in; also returns overlapping memberships |

**Implementation:** 
- Uses existing `neo4j_handler.find_clusters()` 
- Calculates density: `density = internal_edges / max_possible_edges`
- Estimates modularity as `coverage × 0.5` (simplified heuristic, not true modularity optimization)
- Hub/bridge detection is basic (first entity = hub)

---

##### Similarity Analysis (4 endpoints)

| Endpoint | Metric | Time Complexity | What It Does |
|----------|--------|-----------------|--------------|
| `/entity/{entity_id}/similar` | Jaccard, Cosine, Overlap, Adamic-Adar | O(V²) or O(V×N) worst case | Find structurally similar entities (shared neighbors) |
| `/similarity/{entity1_id}/{entity2_id}` | All metrics combined | O(1) to O(V) | Compare two entities; return Jaccard/Cosine/Overlap scores + path distance |
| `/common-neighbors/{entity1_id}/{entity2_id}` | Intersection + Adamic-Adar | O(deg(e1) × deg(e2)) | Entities connected to both; calculate Adamic-Adar score |

**Similarity Metrics Implemented:**
- **Jaccard:** `|A ∩ B| / |A ∪ B|` (intersection over union of neighbors)
- **Cosine:** `|A ∩ B| / sqrt(|A| × |B|)` (normalized)
- **Overlap:** `|A ∩ B| / min(|A|, |B|)` (Szymkiewicz-Simpson)
- **Adamic-Adar:** `Σ(1/log(degree))` over common neighbors (weighted by neighbor degree)

**Implementation:** 
- Builds neighbor sets from entity `tags` field
- Calculates all metrics on-demand (no caching)
- Returns top N results sorted by score
- Missing: learned similarity (embeddings), contextual weights

---

##### Influence Analysis (3 endpoints)

| Endpoint | Algorithm | Time Complexity | What It Does |
|----------|-----------|-----------------|-------------|
| `/influence` | PageRank | O(iterations × E) typical O(100×E) | Rank entities by importance; iterative eigenvector computation |
| `/influence/{entity_id}/spread` | Independent Cascade simulation | O(steps × E) | Simulate how influence spreads from seed entity through network |
| `/key-entities` | Degree-based criticality | O(V) | Find hubs, bridges, brokers; estimate network vulnerability |

**PageRank Implementation:**
- Standard PageRank formula: `PR(A) = (1-d)/N + d × Σ(PR(B)/out_degree(B))`
- Damping factor: 0.85 (default; tunable)
- Convergence: early stop at 1e-6 tolerance
- Handles undirected graphs (symmetric adjacency)
- Time to convergence: typically 10-30 iterations

**Influence Spread Models:**
- **Independent Cascade:** Each activated node has probability `p` to activate each neighbor once
- **Linear Threshold:** Node activates when `fraction_of_active_neighbors ≥ threshold`
- Simulation supports configurable steps (default 5, max 20) and activation probability (default 0.3)

**Key Entities:** 
- Returns top N by connection count
- Estimates impact if removed: fragmentation percentage
- Assigns roles: hub (high degree), broker (in-out balance), key (default)
- Calculates network vulnerability: avg criticality of top 3 entities

---

##### Temporal Patterns (1 endpoint)

| Endpoint | Detection Method | Time Complexity | What It Does |
|----------|------------------|-----------------|--------------|
| `/patterns/temporal` | Burst, trend, periodic | O(n log n) where n=history records | Detect activity spikes, trends, anomalies in creation timestamps |

**Pattern Types Detected:**
1. **Burst:** Daily activity > 2× average (high confidence)
2. **Trend:** Second half avg > 1.5× first half (increasing trend)
3. **Anomaly:** (Not currently implemented; endpoint supports filter)
4. **Periodic:** (Not currently implemented)

**Implementation:** 
- Groups entities by creation date
- Calculates daily averages
- Compares halves (simple linear trend)
- Returns confidence scores and affected entity lists
- Missing: seasonal patterns, wavelets, autocorrelation

---

## Archived ML Services (Out-of-Scope)

**Location:** `/home/devel/basset-hound/archive/out-of-scope-ml/`  
**Status:** Fully documented, ready for intelligence-analysis project migration

### 1. ML Analytics Service (`ml_analytics_service.py` - 1626 lines)

**Purpose:** Query intelligence, patterns, and ML-based entity suggestions

**Key Algorithms:**
- **Query Suggestions:** Prefix matching + pattern-based (n-grams) + TF-IDF semantic similarity
- **Search Patterns:** Trending detection (historical growth), common queries, entity type patterns, declining topics
- **Entity Insights:** Co-search relationships, frequency analysis, zero-result patterns
- **Query Similarity:** Jaccard (tokens) + Edit distance + TF-IDF cosine (weighted 0.3/0.3/0.4)
- **Query Clustering:** Greedy similarity-threshold based clustering
- **Zero-Result Prediction:** Similarity to known failures (0.9), historical rate, token novelty

**ML Techniques:**
- TF-IDF vectorization with LRU cache (max 1000 entries, TTL support)
- IDF change tracking with threshold-based cache invalidation
- N-gram analysis (2-grams, 3-grams) for pattern detection
- Edit distance (Levenshtein, space-optimized)

**Dependencies:** `collections`, `math`, `threading` only (NO sklearn, numpy, scipy)

**Capabilities Not in Current Graph Analytics:**
- Query understanding and suggestion
- Search pattern mining (trending topics, seasonal patterns)
- Zero-result prediction
- TF-IDF based semantic similarity (beyond structural similarity)

---

### 2. Community Detection Service (`community_detection.py` - 1149 lines)

**Purpose:** Advanced community detection with Neo4j GDS fallback

**Algorithms Implemented (Python):**
1. **Louvain:** Modularity-based greedy optimization (O(E log V) typical)
   - Resolution parameter for multi-scale detection (default 1.0)
   - Iterative refinement until no improvement
   - Returns modularity score and community partition

2. **Label Propagation:** Fast near-linear algorithm (O(E) per iteration)
   - Each node adopts most common label from neighbors
   - Good for large graphs (scales to 1M+ nodes)
   - No modularity optimization

3. **Connected Components:** Union-Find or BFS/DFS (O(V+E))
   - Weakly connected (undirected)
   - Strongly connected (directed, Kosaraju's algorithm)

**Neo4j GDS Integration:**
- Checks availability at runtime (`RETURN gds.version()`)
- Falls back to Python if GDS unavailable (e.g., Community Edition without GDS plugin)
- GDS graph projection using Cypher

**Why Archived:** 
- Requires additional Python dependencies (networkx, scipy if used)
- GDS availability varies by Neo4j edition
- Current graph_analytics uses simpler connected components inline

**Capabilities Not in Current:**
- True modularity optimization (Louvain)
- Label propagation (fast for very large graphs)
- Nested communities (multi-level)
- Community statistics (inter/intra edge counts, size distribution)

---

### 3. Influence Service (`influence_service.py` - 1151 lines)

**Purpose:** Influence propagation and key entity detection

**Algorithms Implemented:**
1. **PageRank:** Same as current graph_analytics but more complete
   - Handles directed graphs properly
   - Pre-computed out-degrees for efficiency
   - Convergence tracking

2. **Influence Spread:**
   - Independent Cascade (p=0.1 default)
   - Linear Threshold (threshold=0.3 default)

3. **Betweenness Centrality:** Brandes' algorithm (O(V×E) time)
   - Single-source shortest paths + accumulation
   - Normalized option for network comparison

4. **Key Entity Detection:**
   - Articulation points (Tarjan's algorithm, O(V+E))
   - Bridges (Tarjan, O(V+E))
   - High-degree hubs
   - Gateway nodes (connect clusters)

5. **Influence Path Tracking:** BFS shortest path + DFS all paths

**Why Archived:**
- Overlaps with current graph_analytics
- Betweenness centrality is expensive (O(V×E)) but currently not offered
- Articulation points/bridges add structural vulnerability analysis

**Capabilities Not in Current:**
- Betweenness centrality (important for broker identification)
- Articulation point detection (critical infrastructure nodes)
- Bridge detection (weak points in network)
- Proper influence path tracking (multiple paths)

---

### 4. Temporal Patterns Service (`temporal_patterns.py` - ~700 lines)

**Purpose:** Advanced temporal analysis of entity/relationship creation

**Pattern Detection (Partially Implemented):**
1. **Burst Detection:** Activity spike > baseline_average × intensity (O(n))
2. **Trend Analysis:** Linear regression (least-squares) over time windows
3. **Cyclical Patterns:** Autocorrelation for weekly/monthly cycles (spectral analysis)
4. **Anomaly Detection:** Z-score or interquartile range based
5. **Stable Periods:** Low variance detection

**Time Windows:** Hour, Day, Week, Month (configurable bucketing)

**Statistics Calculated:**
- Baseline average per window
- Peak timing and intensity
- Trend slope and confidence
- Cycle frequency and phase

**Why Archived:**
- Time series analysis requires careful handling
- Current implementation only detects simple bursts/trends
- Production use needs better validation

**Capabilities Not in Current:**
- Cycle detection (repeating patterns)
- Anomaly scoring (Z-score based)
- Trend confidence estimation
- Advanced time series windowing

---

## Comparison Matrix

| Capability | Current `graph_analytics.py` | Current `analysis.py` | Archived ML | Archived Community | Archived Influence | Archived Temporal |
|------------|------|---------|--------|-------------|---------|-----------|
| **Path Finding** | ✗ | ✓ (BFS, DFS) | ✗ | ✗ | ✓ (BFS, DFS) | ✗ |
| **Degree Centrality** | ✗ | ✓ | ✗ | ✗ | ✓ | ✗ |
| **PageRank** | ✓ | ✗ | ✗ | ✗ | ✓ (more complete) | ✗ |
| **Betweenness** | ✗ | ✗ | ✗ | ✗ | ✓ | ✗ |
| **Community Detection** | ✓ (basic) | ✗ | ✗ | ✓ (advanced: Louvain, Label Prop) | ✗ | ✗ |
| **Similarity Metrics** | ✓ (4 metrics) | ✗ | ✗ | ✗ | ✗ | ✗ |
| **Influence Spread Sim** | ✓ | ✗ | ✗ | ✗ | ✓ | ✗ |
| **Key Entities** | ✓ (basic) | ✗ | ✗ | ✗ | ✓ (articulation, bridges) | ✗ |
| **Temporal Patterns** | ✓ (basic) | ✗ | ✗ | ✗ | ✗ | ✓ (advanced) |
| **Query Suggestions** | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ |
| **Zero-Result Pred** | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ |
| **TF-IDF Vectors** | ✗ | ✗ | ✓ (cached) | ✗ | ✗ | ✗ |

---

## Endpoint Summary

**Total Endpoints:**
- Current: 30 (24 in graph_analytics + 6 in analysis)
- Archived: 43+ (ML analytics router alone has ~9 endpoints)

**Most Complete Categories:**
1. Community & Similarity (graph_analytics)
2. Path Finding & Centrality (analysis + archived influence)
3. Influence Simulation (graph_analytics + archived influence)

**Critical Gaps (for OSINT workflows):**
- No betweenness centrality (expensive but powerful for "gatekeeper" detection)
- No articulation point detection (critical infrastructure)
- No bridge detection (network weak points)
- No ML-based query understanding (Phase 43 Smart Suggestions needs this)
- No temporal anomaly detection (potential indicator of coordinated activity)
- No link prediction (suggest missing relationships)
- No nested/hierarchical communities

---

## Performance Characteristics

### Current Implementations

**Path Finding:** O(V+E)
- Typically <100ms for projects with <5000 entities
- Network size is the limiting factor

**Community Detection:** O(V+E)
- Very fast; dominated by cluster assembly, not algorithm
- Modularity calculation is O(V²) in worst case but filtered

**Similarity:** O(V×neighbors) or O(neighbors²)
- Scalable since uses neighbor sets (not full adjacency)
- Similar entities endpoint: O(V²) but stops early with limits

**PageRank:** O(100×E) typical
- 10-30 iterations to convergence
- Per-entity: O(V log V) for sorting

### Bottlenecks

1. **Scalability:** All algorithms assume <100K entities (in-memory)
2. **Caching:** None in current implementations (always fresh)
3. **Neo4j Calls:** Multiple queries per endpoint (no batching)
4. **Python GIL:** Single-threaded (but mostly I/O bound)

---

## What's Missing for Complete OSINT Intelligence Analysis

### Must-Have (Phase 1)
- Betweenness centrality (find gatekeepers/brokers)
- Eigenvector centrality (find influential connected entities)
- Closeness centrality (find bridges to distant clusters)

### Should-Have (Phase 2)
- Articulation point detection (critical infrastructure)
- Bridge detection (weak points, vulnerabilities)
- Stochastic Block Model (probabilistic communities)
- Link prediction (suggest missing relationships)

### Nice-to-Have (Phase 3)
- Graph embeddings (DeepWalk, Node2Vec)
- Temporal community evolution
- Anomaly scoring (unusual activity detection)
- Influence maximization (find K best seed nodes)

---

## Recommendations

1. **Keep Current:** Both routers work well for their scope; no changes needed
2. **Adopt from Archived:** 
   - Betweenness centrality from `influence_service.py`
   - Advanced Louvain from `community_detection.py`
   - Temporal anomaly detection from `temporal_patterns.py`
3. **Future Intelligence-Analysis Project:** Migrate archived ML services with proper REST API wrapping
4. **Feature Flags:** Use environment variables to enable/disable expensive algorithms at deployment time
5. **Caching Layer:** Add Redis caching for frequently accessed results (PageRank, communities)

