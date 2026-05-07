# Analytics Research & Design Documents (2026-05-06)

This directory contains comprehensive research and architecture design for Basset Hound's analytics expansion.

## Documents

### 1. ANALYTICS-CURRENT-CAPABILITIES-2026-05-06.md
**What it is:** Detailed inventory of all existing analytics endpoints and implementations.

**Covers:**
- Current production endpoints (30 total: 24 in graph_analytics + 6 in analysis)
- Algorithms used (BFS, PageRank, Louvain-style clustering, similarity metrics)
- Time complexity and performance characteristics
- What's archived and why (4 services: ML analytics, community detection, influence, temporal patterns)
- What's missing for complete OSINT workflow

**Key Finding:** Current implementations are lightweight (no ML dependencies) and work well for <5K entities. Everything needed for small-to-medium OSINT projects is already in place.

**Size:** ~900 lines

### 2. ANALYTICS-RESEARCH-NEO4J-NETWORKX-2026-05-06.md
**What it is:** Technical research on graph algorithm technologies (Neo4j GDS, NetworkX, custom Python).

**Covers:**
- Neo4j GDS availability by edition (Community doesn't have it; Enterprise does)
- Performance comparisons (10-1000× speedup with GDS when available)
- NetworkX catalog and usage (300+ algorithms, well-documented)
- Decision matrix: when to use each technology
- Cost-benefit analysis
- Licensing details

**Key Finding:** Keep current implementations for now. Add NetworkX optionally for 10× speed improvement. GDS only if Neo4j Enterprise is deployed.

**Size:** ~1000 lines

### 3. ANALYTICS-PLUGIN-ARCHITECTURE-2026-05-06.md
**What it is:** Proposed modular architecture for analytics expansion.

**Covers:**
- Three-tier stack: Core (always on) → Light (NetworkX-based, optional) → GDS (Enterprise, optional) → ML (separate service, optional)
- Plugin interface design (abstract base class pattern)
- Implementation code samples for each tier
- Feature flags (ENABLE_ANALYTICS_LIGHT, ENABLE_ANALYTICS_GDS, etc.)
- Graceful degradation and fallback strategies
- Deployment strategies (minimal → standard → enterprise → full-stack)
- Migration path (zero breaking changes to existing APIs)
- Testing strategy and roadmap

**Key Finding:** Architecture enables optional analytics without forcing dependencies on users. Existing APIs continue to work unchanged while routing through plugin system internally.

**Size:** ~1200 lines

## How to Use These Findings

### For Decision-Making (Stakeholders)
1. Read the Executive Summary in each document
2. Check the decision matrix in ANALYTICS-RESEARCH-NEO4J-NETWORKX-2026-05-06.md
3. Review deployment strategies in ANALYTICS-PLUGIN-ARCHITECTURE-2026-05-06.md

### For Implementation (Engineers)
1. Start with ANALYTICS-CURRENT-CAPABILITIES to understand existing code
2. Reference ANALYTICS-RESEARCH-NEO4J-NETWORKX for algorithm performance
3. Follow ANALYTICS-PLUGIN-ARCHITECTURE for implementation details
4. Copy code samples (plugin interface, smart router, fallback logic)

### For Planning (Product)
1. Review roadmap in ANALYTICS-PLUGIN-ARCHITECTURE (Q2 2026 through Q2 2027+)
2. Check success metrics for adoption targets
3. Plan feature enablement per deployment strategy

## Key Recommendations

### Short-term (Next 2 Months)
- No changes needed to core
- Current implementations are production-ready
- Document what's available to users

### Medium-term (Q3 2026)
- Implement plugin interface (zero breaking changes)
- Add NetworkX support (Analytics Light)
- Enable community detection, betweenness centrality, articulation points

### Long-term (Q4 2026+)
- Optional Neo4j GDS support (if Enterprise deployed)
- Optional ML service for query suggestions and anomaly detection
- Graph embeddings and advanced features

## Files in Scope vs Out-of-Scope

**In Production (In Scope):**
- `api/routers/analysis.py` (6 endpoints, lightweight)
- `api/routers/graph_analytics.py` (24 endpoints, inline Python)

**Archived (Out-of-Scope, Documented for Future):**
- `archive/out-of-scope-ml/ml_analytics_service.py` (query suggestions, patterns)
- `archive/out-of-scope-ml/community_detection.py` (advanced Louvain, label propagation)
- `archive/out-of-scope-ml/influence_service.py` (betweenness, key entities)
- `archive/out-of-scope-ml/temporal_patterns.py` (temporal analysis)

**Recommended Next (Future Intelligence-Analysis Project):**
- Separate Docker service for ML workloads
- REST API integration with Basset Hound
- Optional docker-compose --profile ml deployment

## Summary

Basset Hound's analytics are **purposefully lightweight** and production-ready. The research documents the path for optional enhancement without forcing dependencies on core users. The proposed plugin architecture enables scaling from laptop-based OSINT to enterprise intelligence platforms.

**No changes are recommended to the current codebase.** The architecture is extensible through plugins, allowing future growth without breaking existing functionality.

---

**Date:** 2026-05-06  
**Status:** Research Complete  
**Next Step:** Implement plugin interface (Phase 1, Q2 2026)
