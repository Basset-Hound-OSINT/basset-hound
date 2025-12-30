# Phase 18: Advanced Graph Analytics

**Completed:** December 2024
**Status:** ✅ Complete

## Overview

Phase 18 implements the core graph analytics capabilities that are central to Basset Hound's value proposition as a graph-powered OSINT platform. These features enable investigators to discover hidden patterns, identify influential entities, and find similar relationship structures across their investigation data.

## Philosophy

Following the project's design principles:
- **Lightweight**: Pure Python implementations (no heavy ML dependencies)
- **Integration-First**: All algorithms return Pydantic models for easy API serialization
- **Local-First**: Algorithms run efficiently on local hardware
- **Graph-Powered**: Leverages Neo4j graph structure for relationship analysis

## Components Implemented

### 1. Community Detection Service

**File:** `api/services/community_detection.py` (~850 lines)

Identifies clusters of closely related entities in the investigation graph.

#### Algorithms:

| Algorithm | Use Case | Complexity |
|-----------|----------|------------|
| **Louvain** | Best quality community detection, modularity-based | O(n log n) |
| **Label Propagation** | Fast detection for large graphs | O(n + m) |
| **Connected Components** | Find isolated subgraphs (weakly/strongly connected) | O(n + m) |

#### Key Models:
```python
Community(id, member_ids, size, density)
CommunityDetectionResult(algorithm, communities, modularity_score, execution_time)
CommunityStats(total_communities, avg_size, largest, smallest, size_distribution)
ConnectedComponent(id, member_ids, size, is_isolated)
```

#### Features:
- Automatic Neo4j GDS integration when available
- Python fallback implementations for all algorithms
- Community density calculation
- Inter/intra-community edge counting
- Size distribution analysis

### 2. Influence Propagation Service

**File:** `api/services/influence_service.py` (~900 lines)

Tracks how influence and information spread through entity networks.

#### Algorithms:

| Algorithm | Purpose | Use Case |
|-----------|---------|----------|
| **PageRank** | Entity influence scoring | Identify most connected/influential entities |
| **Independent Cascade** | Influence spread simulation | Model how information propagates |
| **Linear Threshold** | Influence spread simulation | Model peer influence effects |
| **Betweenness Centrality** | Gateway detection | Find brokers/intermediaries |
| **Articulation Points** | Critical entity detection | Identify network vulnerabilities |

#### Key Models:
```python
InfluenceScore(entity_id, score, rank)
InfluenceSpreadResult(seed_entity_id, affected_entities, steps, reach_percentage)
KeyEntityResult(entity_id, importance_score, reason, components_if_removed)
InfluencePath(source_id, target_id, path, path_length, exists)
InfluenceReport(algorithm, scores, top_n, total_entities, parameters)
```

#### Features:
- Configurable PageRank damping factor
- Multiple propagation models (cascade vs threshold)
- Path finding between entities (shortest path, all paths)
- Articulation point detection (Tarjan's algorithm)
- Bridge edge identification

### 3. Similarity Scoring Service

**File:** `api/services/similarity_service.py` (~700 lines)

Finds entities with similar relationship patterns.

#### Similarity Methods:

| Method | Description | Best For |
|--------|-------------|----------|
| **Jaccard** | Set overlap of neighbors | General similarity |
| **Cosine** | Vector similarity of relationship types | Relationship pattern matching |
| **Common Neighbors** | Count of shared connections | Link prediction |
| **SimRank** | Recursive structural similarity | Deep pattern matching |

#### Key Models:
```python
SimilarityResult(entity1_id, entity2_id, score, method, common_neighbors)
EntitySimilarityReport(entity_id, similar_entities, method_used)
PotentialLink(entity1_id, entity2_id, score, evidence)
SimilarityConfig(methods, threshold, max_results)
```

#### Features:
- Multiple similarity metrics
- Configurable thresholds
- Link prediction for missing connections
- Relationship vector encoding

### 4. Temporal Patterns Service

**File:** `api/services/temporal_patterns.py` (~550 lines)

Detects patterns in entity activity over time.

#### Pattern Types:

| Pattern | Detection Method | Use Case |
|---------|-----------------|----------|
| **Burst** | Statistical threshold detection | Unusual activity spikes |
| **Trend** | Linear regression | Long-term activity changes |
| **Cyclical** | Day-of-week analysis | Regular patterns |
| **Anomaly** | Z-score based | Unexpected events |

#### Key Models:
```python
BurstDetection(start_time, end_time, intensity, event_count, baseline_average)
TrendAnalysis(direction, slope, start_value, end_value, confidence)
CyclicalPattern(period_days, period_description, peak_day, trough_day)
TemporalAnomaly(timestamp, anomaly_score, expected_value, actual_value, deviation)
EntityTemporalProfile(entity_id, first_activity, last_activity, total_events, bursts, trend, anomalies)
```

#### Features:
- Configurable time windows (hour/day/week/month)
- Burst intensity scoring
- Trend direction detection (increasing/decreasing/stable)
- Weekly pattern analysis
- Entity temporal profiling

### 5. Graph Analytics Router

**File:** `api/routers/graph_analytics.py` (~600 lines)

REST API endpoints for all graph analytics features.

#### Endpoints:

| Method | Path | Description |
|--------|------|-------------|
| GET | `/analytics/{project}/communities` | Detect communities |
| GET | `/analytics/{project}/communities/louvain` | Louvain algorithm |
| GET | `/analytics/{project}/communities/label-propagation` | Label propagation |
| GET | `/analytics/{project}/components` | Connected components |
| GET | `/analytics/{project}/influence/pagerank` | PageRank scores |
| POST | `/analytics/{project}/influence/spread` | Influence spread simulation |
| GET | `/analytics/{project}/influence/path/{source}/{target}` | Influence path |
| GET | `/analytics/{project}/influence/key-entities` | Key entity detection |
| GET | `/analytics/{project}/similarity/{entity_id}` | Similar entities |
| GET | `/analytics/{project}/similarity/predict-links` | Link prediction |
| GET | `/analytics/{project}/temporal/{entity_id}/profile` | Entity temporal profile |
| GET | `/analytics/{project}/temporal/patterns` | Project temporal patterns |

## Test Coverage

**File:** `tests/test_phase18_graph_analytics.py` (~750 lines)

56 comprehensive tests covering:
- Community Detection Models (5 tests)
- Louvain Algorithm (5 tests)
- Label Propagation (3 tests)
- Connected Components (4 tests)
- Influence Models (6 tests)
- Propagation Model Enums (2 tests)
- Similarity Models (2 tests)
- Similarity Algorithms (5 tests)
- Temporal Patterns Models (6 tests)
- Graph Analytics Router (4 tests)
- Service Factories (4 tests)
- Service Exports (4 tests)
- Router Exports (1 test)

**All 56 tests pass.**

## Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `api/services/community_detection.py` | ~850 | Community detection algorithms |
| `api/services/influence_service.py` | ~900 | Influence propagation & key entity detection |
| `api/services/similarity_service.py` | ~700 | Entity similarity scoring |
| `api/services/temporal_patterns.py` | ~550 | Temporal pattern detection |
| `api/routers/graph_analytics.py` | ~600 | REST API endpoints |
| `tests/test_phase18_graph_analytics.py` | ~750 | Comprehensive test suite |

## Files Modified

- `api/services/__init__.py` - Added Phase 18 service exports
- `api/routers/__init__.py` - Added graph analytics router

## Algorithm Details

### Louvain Community Detection

The Louvain method is a greedy modularity optimization algorithm:

1. **Phase 1**: Each node starts as its own community
2. **Phase 2**: Iterate through nodes, moving each to the community that maximizes modularity gain
3. **Phase 3**: Aggregate communities into super-nodes and repeat

Modularity formula:
```
Q = (1/2m) Σ [A_ij - (k_i * k_j)/(2m)] δ(c_i, c_j)
```

### PageRank

The PageRank algorithm measures entity importance based on incoming connections:

```
PR(u) = (1-d)/N + d * Σ PR(v)/L(v)
```

Where:
- d = damping factor (default 0.85)
- N = total nodes
- L(v) = out-degree of node v

### Tarjan's Articulation Points

Uses DFS to find articulation points (vertices whose removal disconnects the graph):
- Track discovery time and lowest reachable node for each vertex
- A vertex is an articulation point if:
  - It's the root with 2+ children, OR
  - It's not the root and has a child with no back edge to an ancestor

## Performance Considerations

- All algorithms are O(n log n) or O(n + m) complexity
- Python implementations work well for graphs up to ~10,000 nodes
- Neo4j GDS integration available for larger graphs
- Configurable max iterations for convergence control
- Async-compatible for integration with FastAPI

## Integration with Other Phases

- **Phase 15 (Orphan Data)**: Community detection can identify orphan data clusters
- **Phase 16 (Data Import)**: Imported entities are immediately available for analysis
- **Phase 17 (Frontend Integration)**: Graph analytics results feed visualization components

## Future Enhancements

1. **Graph Neural Networks**: Deep learning for entity classification
2. **Link Prediction**: More sophisticated methods (node2vec, GraphSAGE)
3. **Streaming Analytics**: Real-time pattern detection
4. **Query Optimization**: Caching for frequently-run analyses
5. **Export Formats**: Analysis results in various formats (CSV, JSON, GraphML)

## Conclusion

Phase 18 successfully implements the core graph analytics capabilities that differentiate Basset Hound as a graph-powered OSINT platform. These algorithms enable investigators to discover hidden patterns and relationships that would be invisible in traditional database systems, while remaining lightweight enough to run on local hardware.
