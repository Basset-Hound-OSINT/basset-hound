# Migration Notes for Intelligence-Analysis Project

**Date:** 2026-01-13
**Source Project:** basset-hound
**Target Project:** intelligence-analysis (future)

## Files to Migrate

### Service Files
| Source Location | Archived Location | Lines | Description |
|-----------------|-------------------|-------|-------------|
| api/services/ml_analytics.py | archive/out-of-scope-ml/ml_analytics_service.py | ~1600 | ML query analytics, suggestions, patterns |
| api/services/community_detection.py | archive/out-of-scope-ml/community_detection.py | ~1000 | Community detection algorithms |
| api/services/influence_service.py | archive/out-of-scope-ml/influence_service.py | ~1000 | Influence propagation, PageRank |
| api/services/temporal_patterns.py | archive/out-of-scope-ml/temporal_patterns.py | ~700 | Temporal pattern detection |

### Router Files
| Source Location | Archived Location | Lines | Description |
|-----------------|-------------------|-------|-------------|
| api/routers/ml_analytics.py | archive/out-of-scope-ml/ml_analytics_router.py | ~808 | REST API for ML analytics |

### Test Files
| Source Location | Archived Location | Lines | Description |
|-----------------|-------------------|-------|-------------|
| tests/test_ml_analytics.py | archive/out-of-scope-ml/tests/test_ml_analytics.py | ~1000 | ML analytics service tests |
| tests/test_phase18_graph_analytics.py | archive/out-of-scope-ml/tests/test_phase18_graph_analytics.py | ~800 | Graph analytics tests |

## Imports Removed

### api/services/__init__.py
```python
# REMOVED:
from .community_detection import (
    CommunityDetectionService,
    Community,
    CommunityDetectionResult,
    CommunityStats,
    ComponentType,
    ConnectedComponent,
    ConnectedComponentsResult,
    get_community_detection_service,
    set_community_detection_service,
    reset_community_detection_service,
)

from .influence_service import (
    InfluenceService,
    InfluenceScore,
    InfluenceSpreadResult,
    AffectedEntity,
    KeyEntityResult,
    KeyEntityReason,
    InfluenceReport,
    InfluencePath,
    InfluencePathStep,
    PropagationModel,
    get_influence_service,
    reset_influence_service,
)

from .temporal_patterns import (
    TemporalPatternsService,
    PatternType,
    TrendDirection,
    TimeWindow,
    ActivityBucket,
    BurstDetection,
    TrendAnalysis,
    CyclicalPattern,
    TemporalAnomaly,
    EntityTemporalProfile,
    RelationshipTemporalPattern,
    TemporalPatternReport,
    get_temporal_patterns_service,
    set_temporal_patterns_service,
)
```

### api/routers/__init__.py
```python
# REMOVED:
from .ml_analytics import router as ml_analytics_router
api_router.include_router(ml_analytics_router)
```

### api/tasks/maintenance_tasks.py
```python
# REMOVED TASKS:
cleanup_ml_analytics_cache()
optimize_search_index()
```

### tests/test_celery_tasks.py
```python
# REMOVED TESTS:
test_cleanup_ml_analytics_cache_task_exists()
test_optimize_search_index_task_exists()
# And removed from test_all_maintenance_tasks_are_celery_tasks()
```

## Migration Instructions

When creating the intelligence-analysis project, follow these steps:

### 1. Copy Service Files
```bash
cp archive/out-of-scope-ml/*.py intelligence-analysis/services/
cp -r archive/out-of-scope-ml/tests/* intelligence-analysis/tests/
```

### 2. Update Imports
The services currently import from basset-hound's internal modules. Update imports to:
- Use the basset-hound API client instead of direct database access
- Remove dependencies on api.config.py settings
- Create new configuration for the intelligence-analysis project

### 3. Key Dependencies to Replace

| Current Import | Replacement |
|---------------|-------------|
| `from api.neo4j_handler import ...` | Use basset-hound REST API |
| `from api.config import get_settings` | New intelligence-analysis config |
| `from api.services.search_service import ...` | Use basset-hound search API |

### 4. Configuration Settings to Migrate
These settings from basset-hound's api/config.py should be recreated:
- `ml_analytics_max_history` (default: 10000)
- `ml_analytics_max_tfidf_cache` (default: 5000)
- `ml_analytics_max_entity_queries` (default: 2000)
- `ml_analytics_max_cooccurrence` (default: 5000)

### 5. API Endpoints to Recreate
The ml_analytics router provided these endpoints:
- `GET /api/v1/ml/suggest` - Query suggestions
- `GET /api/v1/ml/patterns` - Search pattern detection
- `GET /api/v1/ml/entities/{entity_id}/insights` - Entity insights
- `GET /api/v1/ml/related` - Related search suggestions
- `POST /api/v1/ml/cluster` - Query clustering
- `GET /api/v1/ml/predict-zero` - Zero-result prediction
- `GET /api/v1/ml/similarity` - Query similarity
- `GET /api/v1/ml/stats` - ML analytics statistics
- `POST /api/v1/ml/record` - Record query for ML training

### 6. Test Updates
The test files reference basset-hound internal modules. Update to:
- Use mocked basset-hound API responses
- Create fixtures for test data from basset-hound
- Remove direct database dependencies

## Notes

- The graph_analytics router (`api/routers/graph_analytics.py`) was NOT archived because it implements similar functionality inline using Neo4j directly, rather than importing from these services.
- The similarity_service.py was NOT archived as it provides useful link prediction features for the storage layer.
