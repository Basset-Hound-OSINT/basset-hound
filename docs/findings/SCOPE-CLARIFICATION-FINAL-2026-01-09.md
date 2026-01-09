# Scope Clarification - Final Report
**Date**: 2026-01-09
**Status**: ✅ COMPLETE - Scope Refined

---

## Executive Summary

After comprehensive discussion and code audit, basset-hound's scope has been refined to distinguish between:

✅ **Data Presentation** (IN SCOPE) - "Here's your data in a useful format"
❌ **Insight Generation** (OUT OF SCOPE) - "Here's what your data means"

---

## The Critical Distinction

### ✅ Data Presentation (Basset-Hound SHOULD Do)

**Definition**: Taking existing data and making it available in useful formats for human operators.

**Examples**:
- Generate entity profile report from template
- Export relationship graph as PNG image
- Create timeline visualization from activity history
- Bulk export entities as ZIP file
- Format data for human consumption (PDF, HTML, Markdown)
- Calculate mathematical metrics (Jaccard similarity, graph density)
- Aggregate data (count connections, sum activity)

**Key Characteristic**: Uses clearly defined algorithmic processes (templates, mathematical formulas, aggregation functions) to present stored data.

**Validation Question**: "Can a human do this with a calculator and the raw data?"
- If **YES** → Data presentation (IN SCOPE)
- If **NO** → Insight generation (OUT OF SCOPE)

---

### ❌ Insight Generation (Basset-Hound Should NOT Do)

**Definition**: Creating NEW information that didn't exist before through analysis, prediction, or pattern detection.

**Examples**:
- Predict what entity will do next
- Detect trending patterns in behavior
- Calculate threat/risk scores
- Identify anomalies in activity
- Recommend actions based on ML models
- Generate insights about relationships

**Key Characteristic**: Generates new data/insights beyond what was stored.

---

## User Clarification (Direct Quote)

> "It's not like Basset Hound doesn't do any analysis it's just that it doesn't do anything other than make data available in ways that are useful to human operators... I don't want to go ahead and remove code that may be involved with useful features like [reports and visualizations] but I definitely want to remove things that are just very much extra where Basset Hound would go out of scope to generate information that is not involved in a very clearly defined algorithmic process that uses an existing template."

---

## What Changes

### Previously Thought Out-of-Scope (Now IN SCOPE):

1. **Template-Based Reports** ✅
   - Entity profile reports
   - Investigation summaries
   - Timeline reports
   - **Why**: Takes stored data and formats it using templates

2. **Graph Visualization Export** ✅
   - Export relationship map as PNG/SVG
   - Graph rendering for Gephi/Cytoscape
   - **Why**: Renders stored relationships visually

3. **Mathematical Similarity Metrics** ✅
   - Jaccard, Cosine, SimRank
   - Common Neighbors
   - **Why**: Mathematical formulas, not ML

4. **Basic Graph Algorithms** ✅
   - Connected components
   - Shortest path (BFS/DFS)
   - Graph density calculation
   - **Why**: Standard graph theory, not ML

5. **Activity Aggregation** ✅
   - Count events per day
   - Sum relationship weights
   - Average confidence scores
   - **Why**: Basic math operations

### Still Out-of-Scope (Remove):

1. **ML-Based Pattern Detection** ❌
   - Trend detection (linear regression)
   - Burst detection (statistical anomalies)
   - Cyclical pattern identification
   - **Why**: Generates NEW insights (predictions)

2. **Predictive Analytics** ❌
   - Zero-result prediction
   - Influence propagation simulation
   - Link prediction
   - **Why**: Predicts future/unknown information

3. **Behavioral Analysis** ❌
   - Entity behavioral profiling
   - Anomaly detection in activity
   - Risk/threat scoring
   - **Why**: Generates interpretations/insights

4. **ML Algorithms** ❌
   - Louvain community detection
   - TF-IDF for query suggestions
   - Neural network embeddings
   - **Why**: Machine learning, not data management

---

## Revised Service Audit

### ml_analytics.py (Partial Keep)

**✅ KEEP**:
- `get_popular_queries()` - Just counts (aggregation)
- `get_recent_searches()` - Just retrieves stored data
- Basic autocomplete from prefix matching (not ML)

**❌ REMOVE**:
- `suggest_queries()` with TF-IDF scoring → ML-based suggestions
- `detect_search_patterns()` → Pattern detection (trending/seasonal)
- `predict_zero_results()` → Predictive analytics
- `cluster_similar_queries()` → ML clustering
- Entity insights generation → Behavioral analysis

**Recommendation**: Extract useful aggregation features, remove ML features

---

### temporal_patterns.py (Partial Keep)

**✅ KEEP**:
- `get_activity_history()` - Retrieves stored events
- `aggregate_by_period()` - Simple grouping (count, sum)
- Timeline generation for visualization → Data presentation
- Activity summary (min/max/count) → Mathematical aggregation

**❌ REMOVE**:
- `detect_bursts()` → Statistical anomaly detection
- `detect_trend()` → Linear regression (predictive)
- `detect_cyclical_patterns()` → Pattern detection
- `detect_anomalies()` → Anomaly scoring
- Temporal profiling with "activity trends" → Behavioral analysis

**Recommendation**: Keep aggregation and timeline features, remove detection features

---

### community_detection.py (Partial Keep)

**✅ KEEP**:
- `ConnectedComponentsFinder` → Basic graph query (DFS/BFS)
- `calculate_density()` → Mathematical formula
- Graph partitioning for visualization → Data presentation

**❌ REMOVE**:
- `LouvainAlgorithm.detect()` → Research ML algorithm
- `LabelPropagation.detect()` → ML-based community detection
- Community statistics with "significance scoring" → Interpretation

**Recommendation**: Keep basic graph queries, remove ML algorithms

---

### influence_service.py (Partial Keep)

**✅ KEEP**:
- `find_shortest_path()` → Basic graph traversal (BFS)
- `find_articulation_points()` → Graph structure query
- Path finding for visualization → Data presentation

**❌ REMOVE**:
- `calculate_pagerank()` with interpretation → Generates importance scores
- `simulate_influence_spread()` → Predictive simulation
- `find_key_entities()` with criticality scoring → Insight generation
- `calculate_betweenness_centrality()` if used for analysis → Generates centrality insights

**Recommendation**: Keep path finding, remove predictive/scoring features

---

### similarity_service.py (Keep All)

**✅ KEEP**:
- All similarity metrics (Jaccard, Cosine, SimRank, Common Neighbors)
- These are mathematical comparisons, not ML
- Used for Phase 43 matching (IN SCOPE)

**Recommendation**: No changes needed

---

## What Reports Should Look Like

### ✅ Template-Based Entity Report (IN SCOPE)

```python
def generate_entity_report(entity_id):
    """Generate report from template - data presentation."""
    # Retrieve stored data
    entity = get_entity(entity_id)
    relationships = get_relationships(entity_id)
    evidence = get_evidence(entity_id)
    timeline = get_activity_timeline(entity_id)

    # Count and aggregate (basic math)
    connection_count = len(relationships)
    evidence_count = len(evidence)

    # Fill template with data (NO NEW INSIGHTS)
    report = {
        "entity": entity,
        "relationships": relationships,
        "evidence": evidence,
        "timeline": timeline,
        "stats": {
            "connections": connection_count,
            "evidence_count": evidence_count
        }
    }

    # Format for human consumption
    return render_template("entity_report.html", **report)
```

**Why IN SCOPE**: Takes stored data, counts it, formats it. No new insights generated.

---

### ❌ Predictive Risk Report (OUT OF SCOPE)

```python
def generate_risk_assessment(entity_id):
    """Generate risk assessment - insight generation."""
    # Retrieve data
    entity = get_entity(entity_id)
    history = get_activity_history(entity_id)
    connections = get_relationships(entity_id)

    # GENERATES NEW INSIGHTS (risk scores, predictions)
    risk_score = ml_model.predict_risk(entity, history)  # ML prediction
    threat_level = calculate_threat_level(connections)    # Scoring algorithm
    predicted_behavior = forecast_activity(history)       # Prediction

    # This is creating NEW DATA that didn't exist
    report = {
        "risk_score": risk_score,          # NEW insight
        "threat_level": threat_level,      # NEW insight
        "predictions": predicted_behavior  # NEW insight
    }

    return report
```

**Why OUT OF SCOPE**: Generates NEW insights (risk scores, threat levels, predictions) that didn't exist in stored data.

---

## Graph Visualization vs. Graph Analysis

### ✅ Graph Export for Visualization (IN SCOPE)

```python
def export_relationship_graph(entity_ids):
    """Export graph as PNG - data presentation."""
    # Retrieve stored relationships
    entities = get_entities(entity_ids)
    relationships = get_relationships_for_entities(entity_ids)

    # Build graph structure (no analysis)
    graph = build_graph(entities, relationships)

    # Calculate layout for visualization (not analysis)
    layout = calculate_force_directed_layout(graph)

    # Render stored data as image
    png = render_graph_to_png(graph, layout)

    return png
```

**Why IN SCOPE**: Takes stored data (entities + relationships) and renders as image. No new insights.

---

### ❌ Community Detection Analysis (OUT OF SCOPE)

```python
def detect_communities(entity_ids):
    """Detect communities - insight generation."""
    # Retrieve data
    graph = get_graph(entity_ids)

    # GENERATES NEW INSIGHTS (community classifications)
    communities = louvain_algorithm(graph)  # ML-based detection

    # Assigns NEW LABELS to entities
    for entity in entities:
        entity.community_id = communities[entity.id]  # NEW data

    return communities
```

**Why OUT OF SCOPE**: Generates NEW classifications (community IDs) that didn't exist. This is analytical insight generation.

---

## Summary Table

| Feature | Type | Status | Reason |
|---------|------|--------|--------|
| Entity profile report | Data Presentation | ✅ KEEP | Template-based, no new insights |
| Timeline visualization | Data Presentation | ✅ KEEP | Renders stored activity |
| Graph export (PNG) | Data Presentation | ✅ KEEP | Visualizes stored relationships |
| Bulk ZIP export | Data Presentation | ✅ KEEP | Packages stored data |
| Jaccard similarity | Data Presentation | ✅ KEEP | Mathematical formula |
| Connected components | Data Presentation | ✅ KEEP | Basic graph query |
| Activity aggregation | Data Presentation | ✅ KEEP | Count/sum/average |
| Shortest path | Data Presentation | ✅ KEEP | Graph traversal (BFS) |
| **Trend detection** | **Insight Generation** | **❌ REMOVE** | **Predicts trends** |
| **Burst detection** | **Insight Generation** | **❌ REMOVE** | **Detects anomalies** |
| **Risk scoring** | **Insight Generation** | **❌ REMOVE** | **Generates scores** |
| **Pattern detection** | **Insight Generation** | **❌ REMOVE** | **Finds patterns** |
| **Louvain clustering** | **Insight Generation** | **❌ REMOVE** | **ML algorithm** |
| **Influence simulation** | **Insight Generation** | **❌ REMOVE** | **Predictive** |
| **Zero-result prediction** | **Insight Generation** | **❌ REMOVE** | **Predictive** |

---

## Validation Rule

**Ask yourself**: "Can a human do this with a calculator and the raw data?"

**Examples**:

| Question | Answer | Status |
|----------|--------|--------|
| Can a human count connections? | YES (use calculator) | ✅ IN SCOPE |
| Can a human render a graph as PNG? | YES (with tool like Gephi) | ✅ IN SCOPE |
| Can a human calculate Jaccard similarity? | YES (formula exists) | ✅ IN SCOPE |
| Can a human find shortest path? | YES (use BFS algorithm) | ✅ IN SCOPE |
| Can a human detect anomalies statistically? | YES, but requires statistical interpretation | ⚠️ BORDERLINE |
| Can a human predict future trends? | NO (requires ML/extrapolation) | ❌ OUT OF SCOPE |
| Can a human calculate risk scores? | NO (subjective interpretation) | ❌ OUT OF SCOPE |
| Can a human detect behavioral patterns? | NO (requires analysis) | ❌ OUT OF SCOPE |

---

## Implementation Plan

### Phase 1: Preserve Useful Features
1. Extract aggregation features from temporal_patterns.py
2. Keep connected components from community_detection.py
3. Keep path finding from influence_service.py
4. Keep basic autocomplete from ml_analytics.py

### Phase 2: Remove Insight Generation
1. Remove ML algorithms (Louvain, Label Propagation)
2. Remove predictive features (trend detection, burst detection)
3. Remove scoring features (risk assessment, influence scores)
4. Remove pattern detection features

### Phase 3: Reorganize
1. Create `timeline_service.py` - Activity aggregation and timeline generation
2. Create `graph_query_service.py` - Path finding, connected components
3. Keep `similarity_service.py` - Already compliant
4. Update documentation

---

## Files Updated

1. **docs/SCOPE.md** - Added "Reports & Data Export" section, refined "Intelligence Analysis" section
2. **docs/ROADMAP.md** - Clarified report generation phases
3. **docs/findings/SCOPE-AUDIT-REVISED-2026-01-09.md** - Complete revised audit
4. **docs/findings/SCOPE-CLARIFICATION-FINAL-2026-01-09.md** - This document

---

## Conclusion

basset-hound is a **data management and presentation tool**, not an intelligence analysis platform.

**It SHOULD**:
- Store and organize intelligence data
- Present data in useful formats (reports, visualizations, exports)
- Use mathematical formulas and algorithms (similarity, aggregation, graph queries)
- Format data for human operators

**It should NOT**:
- Generate predictions about the future
- Detect patterns or anomalies
- Score entities on risk/threat/importance
- Use machine learning for analysis
- Create new insights beyond stored data

**Key Principle**: **Storage + Presentation**, NOT **Analysis + Insight Generation**

---

**Prepared By**: Claude Sonnet 4.5
**Date**: 2026-01-09
**Status**: ✅ SCOPE CLARIFIED
