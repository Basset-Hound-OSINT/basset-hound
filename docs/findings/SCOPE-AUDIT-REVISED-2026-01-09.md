# Revised Scope Audit: Data Presentation vs. Insight Generation

**Date:** 2026-01-09
**Purpose:** Re-audit out-of-scope services with refined understanding of data presentation (OK) vs. insight generation (NOT OK)

---

## Key Distinction

**✅ IN SCOPE - Data Presentation & Export:**
- Generate reports from templates with stored data
- Export relationship graphs as images
- Bulk export features (ZIP, API)
- Data visualization (graph rendering, timeline rendering)
- Format data for human consumption
- **Philosophy**: "Here's your data in a useful format"

**❌ OUT OF SCOPE - Insight Generation:**
- Generate NEW insights (predictions, patterns, risk scores)
- ML-based analysis
- Behavioral pattern detection
- Predictive analytics
- **Philosophy**: "Here's what your data means"

---

## Service-by-Service Analysis

### 1. ml_analytics.py

**Location:** `/home/devel/basset-hound/api/services/ml_analytics.py`

**What it does:**
- Query suggestions based on search history
- TF-IDF vectorization for semantic similarity
- Search pattern detection (trending topics)
- Entity insights with relationship suggestions
- Query similarity calculation
- Zero-result prediction

**Analysis:**

#### ✅ KEEP (Data Presentation):
```python
# Line 450-520: Basic query suggestions from history
def suggest_queries(partial_query, user_history):
    """Generate query suggestions based on partial input."""
    # Uses PREFIX MATCHING from stored query history
    # This is like browser autocomplete - showing what you've searched before
```
**Reason**: Prefix matching against stored history is simple data retrieval, not ML prediction.

#### ❌ REMOVE (Insight Generation):
```python
# Line 622-673: Pattern detection
def detect_search_patterns(time_range, project_id):
    """Detect trending patterns, seasonal patterns."""
    # Detects TRENDING topics (line 675-710)
    # Generates NEW INSIGHTS about what's "rising" or "declining"
```
**Reason**: Identifying trends and generating insights like "15% increase in crypto searches" is creating new analytical data.

```python
# Line 1251-1316: Zero-result prediction
def predict_zero_results(query):
    """Predict likelihood of zero results."""
    # Uses TF-IDF similarity to PREDICT future outcomes
    # Returns probability: "This query will likely fail"
```
**Reason**: Predicting future outcomes is insight generation, not data presentation.

```python
# Line 799-881: Entity insights
def get_entity_insights(entity_id, project_id):
    """Generate insights about an entity."""
    # Generates insights like:
    # - "Frequently searched together with X"
    # - "High search activity (entity may be of high interest)"
```
**Reason**: Generating recommendations and interpretations is insight generation.

**Verdict**: **MOSTLY REMOVE** (Keep basic autocomplete, remove ML features)

---

### 2. temporal_patterns.py

**Location:** `/home/devel/basset-hound/api/services/temporal_patterns.py`

**What it does:**
- Burst detection (sudden spikes)
- Trend detection (gradual changes)
- Cyclical pattern detection
- Anomaly detection
- Entity temporal profiles

**Analysis:**

#### ✅ KEEP (Data Presentation):
```python
# Line 544-624: Entity temporal profile
def get_entity_temporal_profile(project_id, entity_id, events):
    """Build a temporal profile for an entity."""
    # Aggregates activity history:
    # - First/last activity timestamps
    # - Total events count
    # - Most active hour/day
```
**Reason**: This is AGGREGATING stored data (counting, finding min/max). No new insights.

```python
# Line 263-320: Activity bucketing
def _get_activity_buckets(events, window, start_time, end_time):
    """Aggregate events into time buckets."""
    # Groups events by time period (hour/day/week)
    # Counts events per bucket
```
**Reason**: This is data aggregation for timeline visualization. Like creating a bar chart.

#### ❌ REMOVE (Insight Generation):
```python
# Line 322-394: Burst detection
def detect_bursts(buckets, threshold):
    """Detect activity bursts using statistical threshold."""
    # Calculates mean and standard deviation
    # Flags periods > mean + threshold * std
    # Generates NEW INSIGHT: "This is a burst!"
```
**Reason**: Detecting anomalies and labeling them as "bursts" is pattern detection, not data presentation.

```python
# Line 396-446: Trend detection
def detect_trend(buckets):
    """Detect overall trend using linear regression."""
    # Uses LINEAR REGRESSION to predict trend direction
    # Returns "INCREASING", "DECREASING", "STABLE"
```
**Reason**: Applying statistical models to identify trends is predictive analysis.

```python
# Line 448-500: Cyclical pattern detection
def detect_cyclical_patterns(buckets, window):
    """Detect cyclical patterns (weekly, monthly)."""
    # Analyzes variance across days of week
    # Reports "weekly pattern" if variation significant
```
**Reason**: Pattern detection algorithm generates new insights about cycles.

```python
# Line 502-542: Anomaly detection
def detect_anomalies(buckets, threshold):
    """Detect anomalous activity periods."""
    # Statistical threshold: |value - mean| > threshold * std_dev
    # Generates "anomaly score" for unusual events
```
**Reason**: Detecting and scoring anomalies is insight generation.

**Verdict**: **PARTIALLY KEEP** (Keep aggregation/timeline, remove pattern detection)

---

### 3. community_detection.py

**Location:** `/home/devel/basset-hound/api/services/community_detection.py`

**What it does:**
- Louvain community detection (modularity-based)
- Label propagation (fast clustering)
- Connected components analysis
- Community statistics

**Analysis:**

#### ✅ KEEP (Data Presentation):
```python
# Line 438-490: Connected components finder
def find_weakly_connected(nodes, edges):
    """Find connected components (ignoring direction)."""
    # Uses BFS to find connected subgraphs
    # This is BASIC GRAPH QUERY (who's connected to whom?)
```
**Reason**: Finding connected components is a graph database query, not ML. It's like "show me all entities in this cluster."

```python
# Line 1046-1071: Calculate community density
def _calculate_community_density(members, edges):
    """Calculate edge density within a community."""
    # Density = actual_edges / possible_edges
    # Simple mathematical calculation on stored data
```
**Reason**: Computing density is a mathematical formula, not insight generation.

#### ❌ REMOVE (Insight Generation):
```python
# Line 158-297: Louvain algorithm
class LouvainAlgorithm:
    """Louvain community detection using modularity optimization."""
    # Iterative algorithm that DISCOVERS communities
    # Uses modularity formula to optimize partitions
    # Generates NEW INSIGHT: "These entities form a community"
```
**Reason**: Louvain is a RESEARCH ALGORITHM that discovers hidden community structure. This is advanced analysis, not data presentation.

```python
# Line 356-435: Label propagation
class LabelPropagation:
    """Label propagation for community detection."""
    # Each node adopts most common label among neighbors
    # Iterative algorithm that DISCOVERS communities
```
**Reason**: Another research algorithm for community detection. Generates new clustering insights.

**Verdict**: **PARTIALLY KEEP** (Keep connected components, remove Louvain/Label Propagation)

---

### 4. influence_service.py

**Location:** `/home/devel/basset-hound/api/services/influence_service.py`

**What it does:**
- PageRank algorithm for influence scoring
- Influence spread simulation (Independent Cascade, Linear Threshold)
- Influence path tracking
- Key entity identification (articulation points, bridges)
- Betweenness centrality

**Analysis:**

#### ✅ KEEP (Data Presentation):
```python
# Line 653-743: Find influence path
def find_influence_path(project_id, source_id, target_id, max_depth):
    """Find shortest path between entities using BFS."""
    # Uses breadth-first search to find path
    # This is GRAPH TRAVERSAL QUERY (basic Neo4j feature)
```
**Reason**: BFS path finding is a standard graph query. Like "show me how A connects to B."

```python
# Line 894-942: Find articulation points
def _find_articulation_points(adjacency, all_nodes):
    """Find articulation points using Tarjan's algorithm."""
    # Graph algorithm to find critical nodes
    # These are STRUCTURAL PROPERTIES of the graph
```
**Reason**: While this is an algorithm, it's finding OBJECTIVE structural properties (which nodes are bridges). This is like "show me critical connection points" - data presentation for visualization.

#### ⚠️ DEBATABLE (Could go either way):
```python
# Line 349-451: PageRank calculation
def calculate_pagerank(project_id, damping_factor, max_iterations):
    """Calculate PageRank scores for entities."""
    # Iterative algorithm that computes importance scores
    # Used for VISUALIZATION (node sizing in graphs)
```
**Reason**: PageRank IS an algorithm, but if used ONLY for graph visualization (sizing nodes), it's data presentation. If used to say "this entity is important," it's insight generation.

**Decision**: **KEEP IF** used only for visualization. **REMOVE IF** presented as analytical insights.

#### ❌ REMOVE (Insight Generation):
```python
# Line 457-647: Influence spread simulation
def simulate_influence_spread(project_id, seed_entity_id, model):
    """Simulate how influence spreads from seed entity."""
    # Uses Independent Cascade or Linear Threshold models
    # PREDICTS: "If you start here, influence will reach these entities"
```
**Reason**: Simulating future outcomes is PREDICTIVE MODELING. This generates new insights about what might happen.

```python
# Line 1022-1117: Betweenness centrality
def calculate_betweenness_centrality(project_id, top_n, normalized):
    """Calculate betweenness centrality using Brandes' algorithm."""
    # Computes how often nodes appear on shortest paths
    # Generates INSIGHT: "This entity is a broker/gateway"
```
**Reason**: Betweenness centrality with interpretation is insight generation. (Though the algorithm itself is structural analysis.)

**Verdict**: **PARTIALLY KEEP** (Keep path finding and articulation points for visualization, remove simulations and complex centrality)

---

### 5. similarity_service.py

**Location:** `/home/devel/basset-hound/api/services/similarity_service.py`

**Status:** Previously analyzed as mostly OK

**What it does:**
- Jaccard similarity (neighbor set overlap)
- Cosine similarity (relationship vector comparison)
- Common neighbors analysis
- SimRank (iterative similarity)

**Re-Analysis:**

#### ✅ KEEP (Data Presentation):
```python
# Line 164-186: Jaccard similarity
def jaccard_similarity(set1, set2):
    """Compute Jaccard: |A ∩ B| / |A ∪ B|"""
    # Simple SET COMPARISON
    # Like: "Entity A and B have 60% overlap in connections"
```
**Reason**: Jaccard is a MATHEMATICAL FORMULA applied to stored data. It's a comparison metric, not insight generation. This is data presentation.

```python
# Line 189-216: Cosine similarity
def cosine_similarity(vec1, vec2):
    """Compute cosine: (A · B) / (||A|| * ||B||)"""
    # Mathematical vector comparison
```
**Reason**: Another mathematical formula for comparing stored data.

```python
# Line 218-248: Common neighbors score
def common_neighbors_score(neighbors1, neighbors2, total_nodes):
    """Count common neighbors with normalization."""
    # Counting shared connections
```
**Reason**: Counting and comparing is data aggregation.

#### ⚠️ DEBATABLE:
```python
# Line 251-344: SimRank calculator
class SimRankCalculator:
    """SimRank: entities similar if neighbors similar (iterative)."""
    # Iterative algorithm with decay factor
```
**Reason**: SimRank is an ALGORITHM (research paper), but it's computing similarity scores for comparison purposes. Like Jaccard, it's a similarity metric.

**Decision**: **KEEP** - SimRank is a similarity METRIC (like Jaccard), not predictive. It's computing relationships for comparison.

#### ✅ KEEP:
```python
# Line 1102-1176: Find potential links
async def find_potential_links(project_safe_name, config, max_results):
    """Find potential missing links based on common neighbors."""
    # Uses common neighbor count to suggest connections
```
**Reason**: While this "suggests" links, it's using a SIMPLE RULE (common neighbors count). This is more like "smart search" than insight generation. It's showing existing patterns, not predicting new ones.

**Verdict**: **KEEP** (All similarity metrics are mathematical comparisons, not ML)

---

## Summary

### ✅ KEEP - Data Presentation Features

1. **ml_analytics.py**:
   - Basic autocomplete from search history (prefix matching)
   - Query history statistics (counts, frequencies)

2. **temporal_patterns.py**:
   - Activity aggregation and bucketing
   - Timeline generation
   - Entity temporal profile (first/last activity, counts)

3. **community_detection.py**:
   - Connected components (basic graph query)
   - Community density calculation (mathematical formula)

4. **influence_service.py**:
   - Path finding (BFS/DFS - basic graph queries)
   - Articulation points for visualization
   - PageRank for node sizing in visualizations

5. **similarity_service.py**:
   - All similarity metrics (Jaccard, Cosine, SimRank, Common Neighbors)
   - Potential link suggestions based on common neighbors

### ❌ REMOVE - Insight Generation Features

1. **ml_analytics.py**:
   - TF-IDF semantic similarity predictions
   - Search pattern detection (trending, declining)
   - Entity insights and recommendations
   - Zero-result prediction
   - Query clustering
   - Related search recommendations based on ML

2. **temporal_patterns.py**:
   - Burst detection (statistical anomaly detection)
   - Trend detection (linear regression)
   - Cyclical pattern detection
   - Anomaly detection with scoring

3. **community_detection.py**:
   - Louvain algorithm (modularity-based clustering)
   - Label propagation algorithm

4. **influence_service.py**:
   - Influence spread simulation (Independent Cascade, Linear Threshold)
   - Betweenness centrality with interpretation
   - Key entity identification with importance scoring

---

## Implementation Recommendations

### Phase 1: Create Simplified Services

**Create:**
- `timeline_service.py` - Activity aggregation and timeline generation
- `graph_query_service.py` - Path finding, connected components
- `similarity_service.py` - Keep as-is (already compliant)

**Remove:**
- `ml_analytics.py` - Replace with simple search history service
- `temporal_patterns.py` - Replace with timeline aggregation
- `community_detection.py` - Keep only connected components
- `influence_service.py` - Keep only path finding

### Phase 2: Migration Strategy

1. **Extract Keep Features:**
   ```python
   # NEW: timeline_service.py
   class TimelineService:
       def aggregate_activity(project_id, time_window):
           """Aggregate activity into time buckets for visualization."""
           # Lines 263-320 from temporal_patterns.py

       def get_entity_timeline(entity_id):
           """Get activity timeline for entity."""
           # Lines 544-624 from temporal_patterns.py
   ```

2. **Extract Graph Queries:**
   ```python
   # NEW: graph_query_service.py
   class GraphQueryService:
       def find_path(source_id, target_id):
           """Find shortest path using BFS."""
           # Lines 653-743 from influence_service.py

       def find_connected_components(project_id):
           """Find connected subgraphs."""
           # Lines 438-490 from community_detection.py
   ```

3. **Remove ML Features:**
   - Delete ML-based pattern detection
   - Delete predictive analytics
   - Delete insight generation algorithms

### Phase 3: Update Documentation

1. Update SCOPE.md:
   - Add "✅ Reports & Data Export" section
   - Clarify distinction between presentation and analysis

2. Update ROADMAP.md:
   - Keep report generation features
   - Keep visualization export features
   - Remove ML/predictive features

---

## File Removal Checklist

### Files to Delete Entirely:
- None (all can be simplified, not deleted)

### Files to Simplify:
- ✅ `ml_analytics.py` → Keep basic search history
- ✅ `temporal_patterns.py` → Keep aggregation functions
- ✅ `community_detection.py` → Keep connected components
- ✅ `influence_service.py` → Keep path finding
- ✅ `similarity_service.py` → Keep as-is

### New Files to Create:
- `timeline_service.py` - Activity aggregation
- `graph_query_service.py` - Basic graph queries
- `search_history_service.py` - Simple autocomplete

---

## Validation Criteria

### ✅ Data Presentation (OK):
- Uses mathematical formulas (Jaccard, Cosine, Density)
- Aggregates stored data (counting, summing, averaging)
- Queries graph structure (paths, components, neighbors)
- Formats data for visualization (timelines, graphs)
- **Question**: "Can a human do this with a calculator and the raw data?"
- **If YES**: Data presentation (OK)

### ❌ Insight Generation (NOT OK):
- Uses machine learning algorithms
- Detects patterns or anomalies
- Predicts future outcomes
- Generates recommendations
- Creates new analytical data
- **Question**: "Does this create new knowledge not explicitly stored?"
- **If YES**: Insight generation (NOT OK)

---

## Conclusion

The revised audit shows that **most services have valuable data presentation features** that should be kept. The key is to:

1. **Extract and preserve** aggregation, visualization, and mathematical comparison features
2. **Remove** ML-based pattern detection, prediction, and recommendation features
3. **Reorganize** code into clear service boundaries (timeline, graph query, similarity)

This maintains basset-hound's value as a **data management and presentation tool** while staying true to the scope of **storage, not analysis**.
