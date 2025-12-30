# Phase 25: Entity Deduplication & Data Quality Engine

## Summary

Phase 25 adds comprehensive data quality assessment and entity deduplication capabilities to Basset Hound. This enables investigators to:
- Score entity data quality across multiple dimensions
- Detect duplicate entities with various matching strategies
- Merge duplicate entities while preserving all relevant data
- Generate quality reports for entire projects

## Components Implemented

### 1. Data Quality Service

**File**: `api/services/data_quality.py`

A comprehensive service for assessing entity data quality across six dimensions.

#### Quality Dimensions

| Dimension | Weight | Description |
|-----------|--------|-------------|
| Completeness | 30% | How many fields are filled vs expected |
| Freshness | 20% | How recently the data was updated |
| Accuracy | 20% | Validation of field formats (email, phone, etc.) |
| Consistency | 15% | Internal data consistency |
| Uniqueness | 10% | Unique identifiers and data points |
| Validity | 5% | Schema compliance and format validation |

#### Data Sources with Reliability Ratings

| Source | Reliability | Description |
|--------|-------------|-------------|
| `manual_entry` | 0.90 | User-entered data |
| `maltego` | 0.85 | Maltego OSINT tool |
| `spiderfoot` | 0.80 | SpiderFoot scanner |
| `theharvester` | 0.75 | theHarvester recon tool |
| `shodan` | 0.85 | Shodan IoT search |
| `hibp` | 0.90 | Have I Been Pwned |
| `csv_import` | 0.70 | CSV file imports |
| `json_import` | 0.70 | JSON file imports |
| `api_enrichment` | 0.80 | API enrichment data |
| `osint_tool` | 0.75 | Generic OSINT tools |
| `unknown` | 0.50 | Unknown source |

#### Grade Scale

| Grade | Score Range | Description |
|-------|-------------|-------------|
| A | 90-100 | Excellent quality |
| B | 75-89 | Good quality |
| C | 60-74 | Acceptable quality |
| D | 40-59 | Poor quality |
| F | 0-39 | Very poor quality |

#### Usage Example

```python
from api.services.data_quality import (
    DataQualityService,
    get_data_quality_service,
)

service = get_data_quality_service()

# Score a single entity
score = await service.score_entity(
    project_id="project-123",
    entity_id="entity-456",
    entity_data={
        "name": "John Doe",
        "email": "john@example.com",
        "phone": "+1-555-123-4567"
    },
    metadata={"source": "manual_entry", "updated_at": "2024-01-15T10:00:00Z"}
)

print(f"Score: {score.overall_score}/100 (Grade: {score.grade})")

# Get project quality report
report = await service.get_project_quality_report(
    project_id="project-123",
    entity_scores=[score]
)
print(f"Average Score: {report.average_score}")
```

### 2. Deduplication Service

**File**: `api/services/deduplication.py`

A comprehensive service for detecting and resolving duplicate entities.

#### Match Types

| Match Type | Description |
|------------|-------------|
| `exact` | Exact string match |
| `case_insensitive` | Case-insensitive match |
| `fuzzy` | Levenshtein distance similarity |
| `phonetic` | Phonetic matching (Soundex-like) |
| `normalized` | Normalized text comparison (accents, special chars) |
| `partial` | Partial/substring matching |
| `token_set` | Token set similarity (word overlap) |

#### Merge Strategies

| Strategy | Description |
|----------|-------------|
| `keep_primary` | Keep primary entity's values for conflicts |
| `keep_duplicate` | Keep duplicate entity's values for conflicts |
| `keep_newest` | Keep most recently updated values |
| `keep_oldest` | Keep oldest values |
| `keep_longest` | Keep longest field values |
| `keep_all` | Merge all unique values (lists/sets) |
| `manual` | Require manual resolution for conflicts |

#### Usage Example

```python
from api.services.deduplication import (
    DeduplicationService,
    MergeStrategy,
    MatchType,
    get_deduplication_service,
)

service = get_deduplication_service()

# Find duplicates
duplicates = await service.find_duplicates(
    project_id="project-123",
    entity_id="entity-456",
    entity_data={"name": "John Doe", "email": "john@example.com"},
    candidate_entities=[
        {"id": "cand-1", "profile": {"name": "Jon Doe", "email": "john@example.com"}},
        {"id": "cand-2", "profile": {"name": "Jane Smith"}},
    ],
    match_types=[MatchType.FUZZY, MatchType.EXACT],
)

# Preview merge
preview = await service.preview_merge(
    project_id="project-123",
    primary_entity={"id": "entity-456", "profile": {"name": "John Doe"}},
    duplicate_entities=[{"id": "cand-1", "profile": {"phone": "+1-555-1234"}}],
    strategy=MergeStrategy.KEEP_ALL,
)

# Execute merge
result = await service.merge_entities(
    project_id="project-123",
    primary_entity={"id": "entity-456", "profile": {"name": "John Doe"}},
    duplicate_entities=[{"id": "cand-1", "profile": {"phone": "+1-555-1234"}}],
    strategy=MergeStrategy.KEEP_ALL,
)
print(f"Merged: {result.success}")
```

### 3. Data Quality API Router

**File**: `api/routers/data_quality.py`

REST API endpoints for data quality assessment.

#### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/data-quality/score` | Score a single entity |
| POST | `/data-quality/score/batch` | Score multiple entities |
| GET | `/data-quality/config` | Get quality configuration |
| PUT | `/data-quality/config` | Update quality configuration |
| GET | `/data-quality/sources` | List data sources with reliability |
| PUT | `/data-quality/sources/{source}` | Update source reliability |
| POST | `/data-quality/compare` | Compare two entities' quality |
| GET | `/data-quality/stats` | Get service statistics |
| POST | `/data-quality/clear-cache` | Clear score cache |
| GET | `/projects/{project_id}/data-quality/report` | Get project quality report |

#### Usage Examples

**Score Entity:**
```bash
curl -X POST http://localhost:8000/api/v1/data-quality/score \
  -H "Content-Type: application/json" \
  -d '{
    "entity_id": "entity-123",
    "project_id": "project-456",
    "entity_data": {
      "name": "John Doe",
      "email": "john@example.com"
    },
    "metadata": {
      "source": "manual_entry",
      "updated_at": "2024-01-15T10:00:00Z"
    }
  }'
```

**Get Project Report:**
```bash
curl http://localhost:8000/api/v1/projects/project-456/data-quality/report
```

### 4. Deduplication API Router

**File**: `api/routers/deduplication.py`

REST API endpoints for duplicate detection and resolution.

#### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/deduplication/find` | Find duplicates for an entity |
| POST | `/deduplication/find-all` | Find all duplicates in a project |
| POST | `/deduplication/preview` | Preview merge operation |
| POST | `/deduplication/merge` | Execute merge operation |
| POST | `/deduplication/undo/{merge_id}` | Undo a merge |
| GET | `/deduplication/history` | Get merge history |
| GET | `/deduplication/config` | Get deduplication config |
| PUT | `/deduplication/config` | Update deduplication config |
| GET | `/deduplication/stats` | Get service statistics |
| POST | `/deduplication/clear-cache` | Clear candidate cache |
| GET | `/projects/{project_id}/deduplication/report` | Get project report |

#### Usage Examples

**Find Duplicates:**
```bash
curl -X POST http://localhost:8000/api/v1/deduplication/find \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "project-456",
    "entity_id": "entity-123",
    "entity_data": {"name": "John Doe"},
    "candidate_entities": [
      {"id": "cand-1", "profile": {"name": "Jon Doe"}}
    ],
    "match_types": ["fuzzy", "phonetic"]
  }'
```

**Preview Merge:**
```bash
curl -X POST http://localhost:8000/api/v1/deduplication/preview \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "project-456",
    "primary_entity": {"id": "entity-123", "profile": {"name": "John Doe"}},
    "duplicate_entities": [{"id": "dup-1", "profile": {"phone": "+1-555-1234"}}],
    "strategy": "keep_all"
  }'
```

## Test Coverage

**File**: `tests/test_phase25_deduplication_quality.py`

70 comprehensive tests covering:

- DataSource enum (4 tests)
- Source reliability (3 tests)
- QualityDimension enum (2 tests)
- QualityConfig dataclass (3 tests)
- QualityScore dataclass (2 tests)
- DataQualityService core (6 tests)
- DataQualityService config (2 tests)
- Quality comparison (1 test)
- Project quality reports (1 test)
- MatchType enum (2 tests)
- MergeStrategy enum (2 tests)
- DeduplicationConfig (2 tests)
- DuplicateCandidate (1 test)
- DeduplicationService find (4 tests)
- Merge functionality (3 tests)
- Deduplication config (1 test)
- Deduplication reports (1 test)
- Singleton patterns (6 tests)
- Router imports (3 tests)
- Service exports (2 tests)
- Router request/response models (6 tests)
- Integration tests (2 tests)
- Edge cases (6 tests)
- Caching (2 tests)
- Additional methods (3 tests)

```
tests/test_phase25_deduplication_quality.py ... 70 passed in 1.77s
```

## Files Created/Modified

| File | Action | Description |
|------|--------|-------------|
| `api/services/data_quality.py` | Created | Data quality service (~900 lines) |
| `api/services/deduplication.py` | Created | Deduplication service (~900 lines) |
| `api/routers/data_quality.py` | Created | Data quality REST API (~550 lines) |
| `api/routers/deduplication.py` | Created | Deduplication REST API (~500 lines) |
| `api/services/__init__.py` | Modified | Added Phase 25 exports |
| `api/routers/__init__.py` | Modified | Added Phase 25 router registration |
| `tests/test_phase25_deduplication_quality.py` | Created | 70 comprehensive tests |

## Metrics

| Metric | Value |
|--------|-------|
| New tests | 70 |
| All Phase 25 tests passing | Yes |
| New endpoints | 21 |
| Quality dimensions | 6 |
| Match types | 7 |
| Merge strategies | 7 |
| Data sources | 11 |
| Total lines of code | ~2,850 |

## Architecture

### Data Quality Scoring Flow

```
Entity Data → Field Analysis → Dimension Scoring → Weighted Average → Grade
                    ↓
            Schema Validation (optional)
                    ↓
            Source Reliability Adjustment
                    ↓
            Quality Score + Recommendations
```

### Deduplication Flow

```
Entity → Candidate Selection → Match Type Application → Confidence Scoring
                                        ↓
                              Field-by-Field Comparison
                                        ↓
                              Duplicate Candidates List
                                        ↓
                     Preview Merge → Conflict Detection → Execute Merge
```

## Integration Points

### With Existing Services

```python
# Combine quality scoring with import
from api.services.data_quality import get_data_quality_service

async def import_with_quality(entities):
    quality_service = get_data_quality_service()

    for entity in entities:
        score = await quality_service.score_entity(
            project_id=entity["project_id"],
            entity_id=entity["id"],
            entity_data=entity["profile"],
        )

        if score.grade in ["D", "F"]:
            # Flag for review
            entity["needs_review"] = True
            entity["quality_issues"] = score.issues
```

### Webhook Events

The services can trigger webhook events for quality/dedup operations:
- `entity.quality_scored` - When an entity is scored
- `duplicate.detected` - When duplicates are found
- `duplicate.merged` - When entities are merged

## Performance Considerations

- **LRU Caching**: Both services cache results to avoid redundant calculations
- **Batch Operations**: Batch endpoints for scoring multiple entities
- **Configurable Thresholds**: Adjust match thresholds based on use case
- **Async Operations**: All operations are async for non-blocking execution

## Conclusion

Phase 25 adds critical data quality and deduplication capabilities:

- **Data Quality Service**: Multi-dimensional scoring with source reliability
- **Deduplication Service**: Multiple matching strategies with merge capabilities
- **REST APIs**: Full CRUD operations for both services
- **Reports**: Project-level quality and deduplication reports

This enables investigators to:
1. Identify low-quality entity records
2. Find and merge duplicate entities
3. Track data quality trends over time
4. Generate actionable recommendations for data improvement
