# Archived Out-of-Scope ML Services

**Date Archived:** 2026-01-13

## Why These Were Archived

These services implement **intelligence analysis** functionality, not data storage. The basset-hound project is focused on being an **OSINT data storage and management layer**. Intelligence analysis features such as ML-based pattern detection, community detection, influence propagation, and temporal pattern analysis are beyond the scope of a storage system.

These services should be part of a separate **intelligence-analysis** project that consumes data from basset-hound rather than being embedded within it.

## What These Services Contained

### ml_analytics.py (59KB)
ML-based query analytics service providing:
- Query suggestions with confidence scores using TF-IDF similarity
- Search pattern detection (trending, common, declining, entity-type patterns)
- Entity insights and recommendations
- Related search recommendations
- Query clustering and similarity calculations
- Zero-result predictions
- N-gram language models for query understanding

### community_detection.py (39KB)
Community detection algorithms for graph analysis:
- Louvain algorithm for modularity optimization
- Label propagation algorithm
- Connected components finder
- Community statistics and metrics
- Support for overlapping communities

### influence_service.py (39KB)
Influence propagation and analysis service:
- PageRank implementation for entity influence scoring
- Influence spread simulation (independent cascade model)
- Key entity identification (hubs, bridges, brokers)
- Influence path tracking and reporting

### temporal_patterns.py (28KB)
Temporal pattern detection service:
- Burst detection in entity/relationship creation
- Trend analysis (increasing, decreasing, stable)
- Cyclical pattern detection
- Temporal anomaly detection
- Entity temporal profiles

### ml_analytics_router.py (808 lines)
REST API router providing endpoints for the ML analytics service.

## Where These Should Go

These services should be migrated to a future **intelligence-analysis** project that:

1. Connects to basset-hound as a data source
2. Provides analytical capabilities on top of stored OSINT data
3. Maintains its own caching and state management
4. Can be deployed independently from the storage layer

## Archived Files

### Services
- `ml_analytics_service.py` - ML analytics service
- `community_detection.py` - Community detection algorithms
- `influence_service.py` - Influence propagation service
- `temporal_patterns.py` - Temporal pattern detection

### Routers
- `ml_analytics_router.py` - ML analytics REST API router

### Tests
- `tests/test_ml_analytics.py` - ML analytics service tests
- `tests/test_phase18_graph_analytics.py` - Graph analytics tests (community detection, influence, temporal patterns)

## Dependencies Removed

The following imports and references were removed from the main codebase:

- `api/services/__init__.py` - Removed imports and exports for all 4 services
- `api/routers/__init__.py` - Removed ml_analytics_router import and registration
- `api/tasks/maintenance_tasks.py` - Removed cleanup_ml_analytics_cache and optimize_search_index tasks
- `tests/test_celery_tasks.py` - Removed tests for archived tasks

## Configuration Settings

The following config settings in `api/config.py` were marked as archived but kept for backwards compatibility:

- `ml_analytics_max_history`
- `ml_analytics_max_tfidf_cache`
- `ml_analytics_max_entity_queries`
- `ml_analytics_max_cooccurrence`
