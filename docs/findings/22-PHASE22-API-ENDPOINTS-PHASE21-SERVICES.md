# Phase 22: API Endpoints for Phase 21 Services

## Summary

Phase 22 adds REST API endpoints for the Phase 21 import/export services, making them accessible via the FastAPI application. This enables frontend applications and external integrations to use the import mapping, LLM export, and graph format conversion capabilities.

## Components Implemented

### 1. Import Mapping Router

**File**: `api/routers/import_mapping.py`

REST API endpoints for managing custom import field mappings.

#### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/import-mappings` | Create a new mapping configuration |
| GET | `/import-mappings` | List all mappings (with optional filters) |
| GET | `/import-mappings/{mapping_id}` | Get a specific mapping |
| PUT | `/import-mappings/{mapping_id}` | Update a mapping |
| DELETE | `/import-mappings/{mapping_id}` | Delete a mapping |
| POST | `/import-mappings/{mapping_id}/apply` | Apply mapping to data |
| POST | `/import-mappings/validate` | Validate mapping configuration |
| POST | `/import-mappings/preview` | Preview mapping transformation |

#### Usage Examples

**Create Mapping:**
```bash
curl -X POST http://localhost:8000/api/v1/import-mappings \
  -H "Content-Type: application/json" \
  -d '{
    "name": "salesforce_contacts",
    "description": "Map Salesforce exports to entities",
    "field_mappings": [
      {
        "source_field": "Email",
        "destination_field": "email",
        "transformations": ["lowercase", "trim"]
      }
    ],
    "tags": ["salesforce", "contacts"]
  }'
```

**Apply Mapping:**
```bash
curl -X POST http://localhost:8000/api/v1/import-mappings/{id}/apply \
  -H "Content-Type: application/json" \
  -d '{
    "data": [
      {"Email": "  JOHN@EXAMPLE.COM  "}
    ]
  }'
```

### 2. LLM Export Router

**File**: `api/routers/llm_export.py`

REST API endpoints for exporting data in LLM-optimized formats.

#### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/projects/{project}/llm-export/entity/{entity_id}` | Export single entity |
| POST | `/projects/{project}/llm-export/summary` | Export project summary |
| POST | `/projects/{project}/llm-export/entity/{entity_id}/context` | Export entity with N-hop context |
| POST | `/projects/{project}/llm-export/investigation-brief` | Export investigation brief |
| POST | `/llm-export/estimate-tokens` | Estimate tokens for content |
| GET | `/llm-export/formats` | List available formats |

#### Usage Examples

**Export Entity for LLM:**
```bash
curl -X POST http://localhost:8000/api/v1/projects/my-project/llm-export/entity/entity-123 \
  -H "Content-Type: application/json" \
  -d '{
    "format": "markdown",
    "max_tokens": 4000,
    "context": {
      "include_relationships": true,
      "include_statistics": true
    }
  }'
```

**Estimate Tokens:**
```bash
curl -X POST http://localhost:8000/api/v1/llm-export/estimate-tokens \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Sample text content",
    "format": "markdown"
  }'
```

**List Formats:**
```bash
curl http://localhost:8000/api/v1/llm-export/formats
```

### 3. Graph Format Router

**File**: `api/routers/graph_format.py`

REST API endpoints for graph format conversion.

#### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/graph-format/convert` | Convert between formats |
| POST | `/graph-format/convert-raw` | Convert and download as file |
| POST | `/graph-format/detect` | Auto-detect graph format |
| POST | `/graph-format/validate` | Validate graph data |
| GET | `/graph-format/formats` | List all supported formats |
| GET | `/graph-format/formats/{format}` | Get format details |

#### Usage Examples

**Convert Graph Format:**
```bash
curl -X POST http://localhost:8000/api/v1/graph-format/convert \
  -H "Content-Type: application/json" \
  -d '{
    "data": "{\"nodes\": [{\"id\": \"1\"}], \"links\": []}",
    "source_format": "d3",
    "target_format": "cytoscape",
    "options": {
      "include_properties": true,
      "pretty_print": true
    }
  }'
```

**Detect Format:**
```bash
curl -X POST http://localhost:8000/api/v1/graph-format/detect \
  -H "Content-Type: application/json" \
  -d '{
    "data": "<?xml version=\"1.0\"?><graphml>...</graphml>"
  }'
```

**List Formats:**
```bash
curl http://localhost:8000/api/v1/graph-format/formats
```

## Request/Response Models

### Import Mapping Models

- `CreateMappingRequest` - Create new mapping
- `UpdateMappingRequest` - Update existing mapping
- `ApplyMappingRequest` - Data to transform
- `ValidateMappingRequest` - Config + sample data
- `PreviewMappingRequest` - Preview transformation
- `MappingResponse` - Full mapping details
- `ValidationResponse` - Validation results
- `PreviewResponse` - Preview results

### LLM Export Models

- `EntityExportRequest` - Single entity export config
- `ProjectSummaryRequest` - Project summary config
- `EntityContextRequest` - Entity with context config
- `InvestigationBriefRequest` - Investigation brief config
- `TokenEstimateRequest` - Token estimation input
- `TokenEstimateResponse` - Token count and metadata
- `FormatInfo` - Export format details
- `FormatsListResponse` - List of formats

### Graph Format Models

- `ConvertRequest` - Conversion parameters
- `DetectFormatRequest` - Data for format detection
- `ValidateFormatRequest` - Data and expected format
- `FormatInfo` - Format metadata
- `FormatDetailsResponse` - Extended format info
- `FormatsListResponse` - List of all formats

## Integration

### Router Registration

All routers are registered in `api/routers/__init__.py`:

```python
from .import_mapping import router as import_mapping_router
from .llm_export import router as llm_export_router
from .graph_format import router as graph_format_router

api_router.include_router(import_mapping_router)
api_router.include_router(llm_export_router)
api_router.include_router(graph_format_router)
```

### Router Tags

- `import-mapping` - Import mapping endpoints
- `llm-export` - LLM export endpoints
- `graph-format` - Graph format endpoints

### OpenAPI Documentation

All endpoints are documented with:
- Detailed descriptions
- Request/response examples
- Parameter documentation
- Error response codes

Access the docs at `http://localhost:8000/docs`.

## Test Coverage

**File**: `tests/test_phase22_api_endpoints.py`

41 comprehensive tests covering:

- Router existence and endpoint paths
- Request model validation
- Response model structure
- Model field requirements and limits
- Helper function behavior
- Router integration
- Async endpoint functions

```
tests/test_phase22_api_endpoints.py ... 41 passed in 1.63s
```

## Files Created/Modified

| File | Action | Description |
|------|--------|-------------|
| `api/routers/import_mapping.py` | Created | Import mapping endpoints (~650 lines) |
| `api/routers/llm_export.py` | Created | LLM export endpoints (~627 lines) |
| `api/routers/graph_format.py` | Created | Graph format endpoints (~530 lines) |
| `api/routers/__init__.py` | Modified | Added router imports and registration |
| `tests/test_phase22_api_endpoints.py` | Created | 41 tests |

## Metrics

| Metric | Value |
|--------|-------|
| New endpoints | 20 |
| New tests | 41 |
| All tests passing | Yes |
| Total lines of code | ~1,807 |

## API Summary

### Import Mapping (8 endpoints)
- Full CRUD for mapping configurations
- Apply mappings to transform data
- Validate and preview before use

### LLM Export (6 endpoints)
- Entity and project exports
- N-hop context exports
- Investigation briefs
- Token estimation
- Format listing

### Graph Format (6 endpoints)
- Format conversion
- Raw file download
- Format detection
- Validation
- Format metadata

## Conclusion

Phase 22 completes the API layer for Phase 21 services:

- **Import Mapping Router** enables programmatic access to field mappings
- **LLM Export Router** allows AI/LLM integrations to consume OSINT data
- **Graph Format Router** provides interoperability with graph tools

All 20 new endpoints follow FastAPI best practices with proper validation, documentation, and error handling. The endpoints are ready for use by frontend applications and external integrations.
