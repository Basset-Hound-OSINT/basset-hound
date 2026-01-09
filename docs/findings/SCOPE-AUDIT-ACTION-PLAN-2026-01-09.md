# Scope Audit Action Plan - 2026-01-09

**Status**: 🚨 CRITICAL - Out-of-scope code found
**Audited by**: Claude Sonnet 4.5
**Date**: 2026-01-09

---

## Executive Summary

**Finding**: basset-hound contains **~6,000 lines** of intelligence analysis code that violates the "NO data generation" principle.

**User Clarification**:
> "Intelligence analysis would be considered data generation and Basset Hound is really never supposed to generate data except for the tiny little feature that makes possible suggestions on linking information and entities because of simple pattern matching and even then this feature is supposed to be very simple."

**Core Principle**: basset-hound is **STORAGE ONLY** - it does NOT generate data (except basic suggestions)

---

## Out-of-Scope Services (MUST REMOVE)

### 1. ML Analytics Service ❌
**File**: `/home/devel/basset-hound/api/services/ml_analytics.py` (1,626 lines)

**Violations**:
- ❌ **Generates predictions**: `predict_zero_results()` generates likelihood scores
- ❌ **Generates patterns**: `detect_search_patterns()` generates "trending/seasonal/declining" classifications
- ❌ **Generates clusters**: `cluster_similar_queries()` generates groupings
- ❌ **Generates suggestions**: TF-IDF based query suggestions

**Why it's wrong**: This service GENERATES analytical data from stored data - that's intelligence-analysis territory.

**Action**: **DELETE** - Move to future intelligence-analysis project

---

### 2. Temporal Patterns Service ❌
**File**: `/home/devel/basset-hound/api/services/temporal_patterns.py` (746 lines)

**Violations**:
- ❌ **Generates burst detections**: Identifies activity spikes
- ❌ **Generates trend analyses**: Linear regression trend detection
- ❌ **Generates anomaly scores**: Statistical deviation scoring
- ❌ **Generates behavioral profiles**: Entity temporal profiles

**Why it's wrong**: GENERATES pattern data, trend data, anomaly data - all analytical outputs.

**Action**: **DELETE** - Move to intelligence-analysis project

---

### 3. Community Detection Service ❌
**File**: `/home/devel/basset-hound/api/services/community_detection.py` (1,149 lines)

**Violations**:
- ❌ **Generates community classifications**: Louvain algorithm creates groups
- ❌ **Generates labels**: Label propagation assigns categories
- ❌ **Generates statistics**: Community metrics and analysis

**Why it's wrong**: GENERATES community classifications - that's analytical data generation.

**Action**: **DELETE** - Move to intelligence-analysis project

---

### 4. Influence Service ❌
**File**: `/home/devel/basset-hound/api/services/influence_service.py` (1,151 lines)

**Violations**:
- ❌ **Generates influence scores**: PageRank calculates importance
- ❌ **Generates spread predictions**: Simulates information propagation
- ❌ **Generates key entity lists**: Identifies critical nodes
- ❌ **Generates centrality rankings**: Betweenness, closeness scores

**Why it's wrong**: GENERATES analytical rankings, predictions, importance scores - all data generation.

**Action**: **DELETE** - Move to intelligence-analysis project

---

### 5. Similarity Service (Partial) ⚠️
**File**: `/home/devel/basset-hound/api/services/similarity_service.py` (1,301 lines)

**Violations**:
- ❌ **Generates link predictions**: `find_potential_links()` creates predictions
- ❌ **Generates SimRank scores**: Iterative similarity computation (ML-like)
- ❌ **Generates similarity matrices**: Comprehensive pairwise analysis

**OK to Keep**:
- ✅ Jaccard similarity: Basic set comparison (not generation)
- ✅ Common neighbors: Just counting (not generation)

**Why partial removal**: Link prediction and SimRank GENERATE analytical data, but basic similarity is just comparison.

**Action**: **REFACTOR** - Keep Jaccard/Common Neighbors only, remove prediction features

---

## What Should STAY (Does NOT Generate Data)

### ✅ MatchingEngine (KEEP)
**File**: `/home/devel/basset-hound/api/services/matching_engine.py`

**Why it's OK**:
- Exact hash matching: Compares hashes (no generation)
- Exact string matching: Compares strings (no generation)
- Fuzzy matching: Returns similarity score 0.0-1.0 (comparison, not generation)

**Principle**: Just compares two values and returns "how similar are they?" - no analytical data generated.

---

### ✅ SuggestionService (KEEP)
**File**: `/home/devel/basset-hound/api/services/suggestion_service.py`

**Why it's OK**:
- Groups suggestions by confidence (HIGH/MEDIUM/LOW)
- Shows "these might match" based on MatchingEngine scores
- Human decides what to do (view/link/dismiss)

**Principle**: Just presents existing comparison results - no new data generated, no predictions.

---

### ✅ DataService (KEEP)
**File**: `/home/devel/basset-hound/api/services/data_service.py`

**Why it's OK**:
- CRUD operations for DataItems
- Links data to entities
- Searches for similar data (using MatchingEngine)

**Principle**: Storage and retrieval only - no generation.

---

### ✅ Basic Graph Queries (KEEP - BUT RENAME)
**File**: Various graph services

**What to Keep**:
- Shortest path between entities
- Get neighbors
- Get relationships
- Count connections

**What to Remove**:
- Centrality calculations (generates importance scores)
- Cluster detection (generates groupings)
- Pattern detection (generates insights)

**Action**: Keep basic retrieval queries, remove analytical queries

---

## Router Impact

### Routers to DELETE:
- `/api/routers/ml_analytics.py` - Exposes ML features
- `/api/routers/graph_analytics.py` - Exposes analysis features (keep basic queries only)

### Routers to KEEP:
- `/api/routers/suggestions.py` - Basic suggestions (Phase 44)
- All CRUD routers (entities, relationships, data)

---

## MCP Tool Impact

### MCP Tools to KEEP:
- `create_data_item`, `get_data_item`, etc. (data management)
- `compute_file_hash`, `verify_file_integrity` (hashing)
- `get_entity_suggestions`, `dismiss_suggestion` (basic suggestions)
- `link_data_items`, `merge_entities` (linking actions)

### MCP Tools to REVIEW:
- `/basset_mcp/tools/analysis.py` - Keep path-finding, remove analysis tools

---

## Phase 43 Status

**Phase 43: Smart Suggestions & Data Matching**

### ✅ IN SCOPE (KEEP):
- Data ID System (Phase 43.1) ✓
- File Hashing (Phase 43.2) ✓
- Matching Engine (Phase 43.3) ✓ - Simple fuzzy matching is OK
- Suggestion System (Phase 43.4) ✓ - Just presents matches
- Linking Actions (Phase 43.5) ✓ - Human-driven linking
- Integration Testing (Phase 43.6) ✓

**Phase 43 is OK** - It's basic data matching, not intelligence analysis.

---

## Removal Plan

### Phase 1: Immediate (This Session)
1. ✅ Update SCOPE.md to clarify "NO data generation"
2. ✅ Update ROADMAP.md to remove ML phases
3. ✅ Document out-of-scope services
4. ✅ Create action plan (this document)

### Phase 2: Code Cleanup (Next Session)
1. **Move to archive** (don't delete yet):
   - `api/services/ml_analytics.py`
   - `api/services/temporal_patterns.py`
   - `api/services/community_detection.py`
   - `api/services/influence_service.py`

2. **Refactor**:
   - `api/services/similarity_service.py` - Keep Jaccard only

3. **Remove routers**:
   - `api/routers/ml_analytics.py`
   - Analysis endpoints in `api/routers/graph_analytics.py`

4. **Update MCP tools**:
   - Remove analysis tools from `basset_mcp/tools/analysis.py`

5. **Update tests**: Remove tests for deleted services

### Phase 3: Migration (Future)
1. Create `basset-hound-intelligence` repository
2. Move archived services to new repo
3. Integrate via MCP (intelligence-analysis reads from basset-hound)
4. Update documentation

---

## Impact Assessment

### Lines of Code
- **To Remove**: ~6,000 lines (5 services)
- **To Keep**: ~2,500 lines (Phase 43 implementations)
- **Net Reduction**: ~70% reduction in analytical code

### API Surface
- **Endpoints to Remove**: ~15 analysis endpoints
- **Endpoints to Keep**: 9 suggestion endpoints (Phase 44)

### MCP Tools
- **Tools to Remove**: ~6 analysis tools
- **Tools to Keep**: 119 storage/management tools

### Breaking Changes
- ⚠️ Users relying on ML analytics endpoints will break
- ⚠️ Analysis MCP tools will be removed
- ✅ Phase 43 suggestions are safe (in scope)

---

## Definition: What is "Data Generation"?

### ❌ Data Generation (OUT OF SCOPE for basset-hound):
- **Creating predictions**: "This entity will likely do X"
- **Creating classifications**: "This entity is trending/declining"
- **Creating patterns**: "These entities form a community"
- **Creating scores**: "This entity has influence score 0.85"
- **Creating insights**: "Anomaly detected in activity"
- **Creating reports**: "Risk assessment report"

### ✅ Data Comparison (IN SCOPE for basset-hound):
- **Comparing values**: "String A is 85% similar to String B"
- **Showing suggestions**: "These two items might match (0.95 confidence)"
- **Computing hash**: "File hash is abc123..."
- **Counting**: "Entity has 5 relationships"
- **Retrieving**: "Shortest path is A→B→C"

**Rule of Thumb**: If it creates NEW data that didn't exist before (predictions, patterns, insights), it's intelligence-analysis. If it just compares/retrieves existing data, it's basset-hound.

---

## User Guidance

### For Current Users of Analysis Features:

**If you're using**:
- ML analytics endpoints
- Community detection
- Influence scoring
- Temporal pattern analysis

**You should**:
1. Migrate to future intelligence-analysis project (when available)
2. Use basset-hound MCP tools to read data
3. Implement analysis in your own AI agents (via palletai)

**Timeline**: Analysis features will be deprecated in next major release

---

## Architecture After Cleanup

```
┌─────────────────────────────────────────┐
│   basset-hound (STORAGE ONLY)           │
│   - Stores entities, relationships      │
│   - Basic data matching (fuzzy)         │
│   - Simple suggestions (no generation)  │
│   - CRUD operations                     │
│   - NO ANALYSIS, NO GENERATION          │
└─────────────┬───────────────────────────┘
              │
              │ MCP Tools
              │
              ▼
┌─────────────────────────────────────────┐
│   intelligence-analysis (FUTURE)        │
│   - Reads data from basset-hound        │
│   - GENERATES analysis                  │
│   - GENERATES predictions               │
│   - GENERATES patterns                  │
│   - GENERATES reports                   │
│   - Stores reports back in basset-hound │
└─────────────────────────────────────────┘
```

---

## Success Criteria

After cleanup, basset-hound should:
- ✅ Store entities, relationships, data (CRUD)
- ✅ Provide basic fuzzy matching (comparison only)
- ✅ Show simple suggestions ("these might match")
- ✅ Allow human-driven linking
- ❌ NOT generate predictions
- ❌ NOT detect patterns
- ❌ NOT perform analysis
- ❌ NOT create insights

---

## Next Steps

1. **Review this action plan** with team/user
2. **Get approval** for Phase 2 cleanup
3. **Create migration guide** for users of analysis features
4. **Execute Phase 2** in next development session
5. **Plan intelligence-analysis project** architecture

---

## Conclusion

basset-hound has accumulated significant analytical capabilities that violate the "storage + basic matching" mandate. These features GENERATE new data (predictions, patterns, insights) rather than just storing and comparing existing data.

**Recommendation**: Remove ~6,000 lines of analytical code and move to future intelligence-analysis project, leaving basset-hound as a focused data storage and basic matching tool.

**Key Principle**: **Storage vs. Generation** - basset-hound stores, intelligence-analysis generates.

---

**Report Prepared By**: Claude Sonnet 4.5
**Date**: 2026-01-09
**Status**: READY FOR REVIEW
