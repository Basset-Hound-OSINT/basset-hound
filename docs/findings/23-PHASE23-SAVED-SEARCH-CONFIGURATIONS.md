# Phase 23: Saved Search Configurations

## Summary

Phase 23 adds the ability to save, manage, and execute reusable search configurations. Users can create named searches with custom parameters, organize them with tags and categories, mark favorites, and execute them with optional overrides.

## Components Implemented

### 1. Saved Search Service

**File**: `api/services/saved_search.py`

A comprehensive service for managing saved search configurations.

#### Features

- **CRUD Operations**: Create, read, update, delete saved searches
- **Scoped Searches**: Global, project-scoped, or user-scoped
- **Categories**: Organize searches by category (general, investigation, monitoring, compliance, risk, custom)
- **Tags**: Flexible tagging system for organization
- **Favorites**: Mark frequently-used searches as favorites
- **Search Execution**: Execute saved searches with optional parameter overrides
- **Usage Tracking**: Track execution count and last execution time
- **Duplication**: Clone existing searches for modification
- **Search Discovery**: Find searches by name, tag, category, or text

#### Data Models

| Model | Description |
|-------|-------------|
| `SearchScope` | Enum: GLOBAL, PROJECT, USER |
| `SearchCategory` | Enum: GENERAL, INVESTIGATION, MONITORING, COMPLIANCE, RISK, CUSTOM |
| `SavedSearchConfig` | Configuration for a saved search |
| `SavedSearch` | A saved search with metadata |
| `SearchListFilter` | Filter options for listing searches |
| `SearchExecutionResult` | Result of executing a saved search |

#### Usage Example

```python
from api.services.saved_search import (
    SavedSearchService,
    SavedSearchConfig,
    SearchScope,
    SearchCategory,
    get_saved_search_service,
)

service = get_saved_search_service(search_service)

# Create a saved search
config = SavedSearchConfig(
    name="High-Risk Entities",
    description="Find entities with risk indicators",
    query="tag:high-risk OR tag:suspicious",
    scope=SearchScope.PROJECT,
    project_id="project-123",
    is_advanced=True,
    tags=["risk", "monitoring"],
    category=SearchCategory.RISK,
    is_favorite=True,
)

search_id = await service.create_search(config)

# Execute the saved search
result = await service.execute_search(search_id)
print(f"Found {result.total_count} results in {result.execution_time_ms}ms")

# Execute with overrides
result = await service.execute_search(search_id, {
    "limit": 50,
    "project_id": "different-project"
})

# Get favorites
favorites = await service.get_favorites(project_id="project-123")

# Get by tags
risk_searches = await service.get_by_tags(["risk", "monitoring"])

# Search through saved searches
found = await service.search_saved_searches("high risk")
```

### 2. Saved Search API Router

**File**: `api/routers/saved_search.py`

REST API endpoints for managing and executing saved searches.

#### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/saved-searches` | Create a new saved search |
| GET | `/saved-searches` | List saved searches with filters |
| GET | `/saved-searches/{search_id}` | Get a specific saved search |
| PUT | `/saved-searches/{search_id}` | Update a saved search |
| DELETE | `/saved-searches/{search_id}` | Delete a saved search |
| POST | `/saved-searches/{search_id}/execute` | Execute a saved search |
| POST | `/saved-searches/{search_id}/duplicate` | Duplicate a saved search |
| POST | `/saved-searches/{search_id}/toggle-favorite` | Toggle favorite status |
| GET | `/saved-searches/favorites` | Get favorite searches |
| GET | `/saved-searches/recent` | Get recently executed searches |
| GET | `/saved-searches/popular` | Get most popular searches |
| GET | `/saved-searches/tags` | Get all tags with counts |
| GET | `/saved-searches/by-category/{category}` | Get searches by category |
| GET | `/saved-searches/by-tag/{tag}` | Get searches by tag |
| GET | `/saved-searches/search` | Search through saved searches |
| GET | `/projects/{project_id}/saved-searches` | List project saved searches |
| POST | `/projects/{project_id}/saved-searches` | Create project saved search |

#### Usage Examples

**Create Saved Search:**
```bash
curl -X POST http://localhost:8000/api/v1/saved-searches \
  -H "Content-Type: application/json" \
  -d '{
    "name": "High-Risk Entities",
    "query": "tag:high-risk OR tag:suspicious",
    "scope": "project",
    "project_id": "project-123",
    "is_advanced": true,
    "tags": ["risk", "monitoring"],
    "category": "risk"
  }'
```

**Execute Saved Search:**
```bash
curl -X POST http://localhost:8000/api/v1/saved-searches/{id}/execute \
  -H "Content-Type: application/json" \
  -d '{
    "limit": 50,
    "offset": 0
  }'
```

**List with Filters:**
```bash
curl "http://localhost:8000/api/v1/saved-searches?category=risk&tags=monitoring&is_favorite=true"
```

**Get All Tags:**
```bash
curl http://localhost:8000/api/v1/saved-searches/tags
```

## Request/Response Models

### Request Models

- `CreateSavedSearchRequest` - Create new saved search
- `UpdateSavedSearchRequest` - Update existing saved search
- `ExecuteSearchRequest` - Execute with optional overrides
- `DuplicateSearchRequest` - Duplicate with optional new name

### Response Models

- `SavedSearchResponse` - Full saved search details
- `SavedSearchListResponse` - Paginated list of searches
- `ExecutionResultResponse` - Search execution results
- `TagCountResponse` - Tags with usage counts
- `FavoriteToggleResponse` - Favorite toggle result

## Integration

### Router Registration

Both routers are registered in `api/routers/__init__.py`:

```python
from .saved_search import router as saved_search_router, project_saved_search_router

api_router.include_router(saved_search_router)
api_router.include_router(project_saved_search_router)
```

### Service Integration with SearchService

```python
from api.services import get_search_service, get_saved_search_service

# Initialize with search service
search_service = get_search_service(neo4j_handler, config)
saved_search_service = get_saved_search_service(search_service)

# Execute a saved search
result = await saved_search_service.execute_search(search_id)
```

## Test Coverage

**File**: `tests/test_phase23_saved_search.py`

50 comprehensive tests covering:

- SearchScope enum values and creation
- SearchCategory enum values and creation
- SavedSearchConfig creation and validation
- SavedSearch dataclass operations
- SavedSearchService CRUD operations
- Filtering and pagination
- Favorites, recent, and popular searches
- Tag and category management
- Duplication and lifecycle
- API router configuration
- Request/response model validation
- Helper functions
- Service singleton behavior
- Service and router exports

```
tests/test_phase23_saved_search.py ... 50 passed in 1.68s
```

## Files Created/Modified

| File | Action | Description |
|------|--------|-------------|
| `api/services/saved_search.py` | Created | Saved search service (~600 lines) |
| `api/routers/saved_search.py` | Created | REST API endpoints (~650 lines) |
| `api/services/__init__.py` | Modified | Added Phase 23 exports |
| `api/routers/__init__.py` | Modified | Added router imports and registration |
| `tests/test_phase23_saved_search.py` | Created | 50 tests |

## Metrics

| Metric | Value |
|--------|-------|
| New tests | 50 |
| All Phase 23 tests passing | Yes |
| Combined Phase 21-23 tests | 130 passing |
| New endpoints | 17 |
| Categories supported | 6 |
| Scopes supported | 3 |
| Total lines of code | ~1,250 |

## API Summary

### Saved Search Endpoints (17 endpoints)

- Full CRUD for saved search configurations
- Execute saved searches with overrides
- Toggle favorite status
- Duplicate searches
- Filter by scope, project, category, tags
- Get favorites, recent, and popular searches
- Get all tags with counts
- Search through saved searches
- Project-scoped endpoints

## Features

### Organization Features
- **Categories**: Group searches by purpose (investigation, monitoring, risk, etc.)
- **Tags**: Flexible tagging system for custom organization
- **Favorites**: Quick access to frequently-used searches
- **Scopes**: Control visibility (global, project-specific, user-specific)

### Execution Features
- **Parameter Overrides**: Override query, project, limit, offset at execution time
- **Execution Tracking**: Track when and how often searches are run
- **Recent Searches**: Access recently executed searches
- **Popular Searches**: Find most-used searches

### Management Features
- **Duplication**: Clone searches for modification
- **Search Discovery**: Find saved searches by name or description
- **Pagination**: Efficient listing with offset/limit

## Conclusion

Phase 23 completes the saved search functionality:

- **SavedSearchService** provides comprehensive search configuration management
- **REST API** enables frontend integration with 17 endpoints
- **Organization features** (categories, tags, favorites) help manage large numbers of saved searches
- **Execution features** allow reusing searches with overrides

This builds on Phase 22's API infrastructure and integrates seamlessly with the existing SearchService from earlier phases.
