# Frontend Export Handler Conversion Report

**Date**: 2026-05-19  
**Status**: COMPLETE  
**File Modified**: `/home/devel/basset-hound/static/js/export-handler.js`

## Overview

All export API endpoints in the frontend export handler have been successfully converted from GET with query parameters to POST with JSON request bodies, aligning with Phase 8 backend API changes documented in `API_REFERENCE.md`.

## Changes Summary

### 1. New Function: `downloadFileWithPost(url, requestBody)`

**Location**: Lines 248-285

Added new helper function to handle POST-based file downloads:

```javascript
async function downloadFileWithPost(url, requestBody = {}) {
    // Sends POST request with JSON body
    // Extracts filename from Content-Disposition header
    // Handles blob download properly
    // Includes error handling
}
```

**Key Features**:
- Sends POST request with `Content-Type: application/json`
- Extracts filename from `Content-Disposition` response header
- Creates object URL from response blob
- Properly cleans up resources (revokes blob URL)
- Comprehensive error handling

**Legacy Function Retained**: Original `downloadFile(url)` (Lines 291-295) kept for backward compatibility.

### 2. Updated Function: `handleExport(projectSafeName, exportType)`

**Location**: Lines 151-241

Converted all export endpoints to POST with JSON request bodies.

#### Endpoint Changes:

| Export Type | Old Endpoint | New Method | New Endpoint | Request Body |
|---|---|---|---|---|
| GraphML | `/export/graphml` (GET) | POST | `/export/graphml` | `{entity_types, tags, include_properties}` |
| CSV | `/export/entities/csv` (GET) | POST | `/export/csv` | `{filters, fields, page, limit}` |
| JSON | `/export/entities/json` (GET) | POST | `/export/json` | `{include_entities, include_relationships}` |
| GeoJSON | `/export/locations/geojson` (GET) | POST | `/export/geojson` | `{entity_type}` |
| Database | `/export/database-dump` (GET) | POST | `/export/database` | `{encrypt, compression}` |

**Details by Export Type**:

**GraphML Export** (Lines 160-167):
```javascript
// POST /api/v1/projects/{projectSafeName}/export/graphml
requestBody = {
    entity_types: [],
    tags: [],
    include_properties: true
};
```

**CSV Export** (Lines 169-177):
```javascript
// POST /api/v1/projects/{projectSafeName}/export/csv
requestBody = {
    filters: {},
    fields: ['id', 'name', 'email'],
    page: 1,
    limit: 1000
};
```

**JSON Export** (Lines 179-185):
```javascript
// POST /api/v1/projects/{projectSafeName}/export/json
requestBody = {
    include_entities: true,
    include_relationships: true
};
```

**GeoJSON Export** (Lines 187-192):
```javascript
// POST /api/v1/projects/{projectSafeName}/export/geojson
requestBody = {
    entity_type: 'Location'
};
```

**Database Dump Export** (Lines 218-224):
```javascript
// POST /api/v1/projects/{projectSafeName}/export/database
requestBody = {
    encrypt: false,
    compression: 'gzip'
};
```

**API Call Change** (Line 233):
```javascript
// OLD: downloadFile(url);
// NEW:
await downloadFileWithPost(url, requestBody);
```

### 3. Updated Function: `exportWithFilters(projectSafeName, filters)`

**Location**: Lines 380-397

Converted advanced/filtered CSV export from GET query params to POST JSON body:

**Before**:
```javascript
// Built URLSearchParams query string
const url = `/api/v1/projects/${projectSafeName}/export/entities/csv?${params}`;
downloadFile(url);
```

**After**:
```javascript
// POST with JSON body
const url = `/api/v1/projects/${projectSafeName}/export/csv`;
const requestBody = {
    filters: filters || {},
    fields: ['id', 'name', 'email'],
    page: 1,
    limit: filters.limit || 1000
};
await downloadFileWithPost(url, requestBody);
```

## API Compliance

All changes align with Phase 8 Export Endpoints specification in `docs/API_REFERENCE.md` (lines 1757-1836):

- GraphML: `POST /api/v1/projects/{project_id}/export/graphml`
- CSV: `POST /api/v1/projects/{project_id}/export/csv`
- JSON: `POST /api/v1/projects/{project_id}/export/json`
- GeoJSON: `POST /api/v1/projects/{project_id}/export/geojson`
- Database: `POST /api/v1/projects/{project_id}/export/database`

## Request Body Standards

All export endpoints now follow consistent JSON body structure with:
- **filters**: Object for filtering criteria
- **fields**: Array of field names to include
- **page/limit**: Pagination parameters
- **entity_type(s)**: Filter by entity types
- **tags**: Filter by tags
- **include_***: Boolean flags for what to include

## Error Handling

- POST request failures throw `HTTP error! status: {code}` with response status
- Comprehensive try-catch blocks in all functions
- User-friendly error notifications via `showNotification()`
- Console logging for debugging

## Testing Checklist

- [ ] GraphML export produces valid GraphML file
- [ ] CSV export returns CSV with proper headers
- [ ] JSON export includes entities and relationships
- [ ] GeoJSON export returns valid GeoJSON FeatureCollection
- [ ] Database dump returns encrypted/compressed archive
- [ ] Filtered exports respect filter parameters
- [ ] File downloads with correct filenames
- [ ] Error responses display user-friendly messages
- [ ] Network inspector shows POST requests with JSON bodies
- [ ] Content-Disposition header properly extracted

## Backward Compatibility

- Legacy `downloadFile(url)` function retained for any other code using it
- UI/UX unchanged - export menu interface identical
- All notification messages preserved
- Report exports already used POST method - no changes needed

## Files Modified

```
/home/devel/basset-hound/static/js/export-handler.js
```

**Lines Changed**: ~20 edits across 3 functions + 1 new function

## Phase 8 Integration

This fix completes Phase 8 frontend compatibility with updated export endpoints. The export handler now properly supports:

1. **Data Serialization**: JSON request bodies instead of query params
2. **Advanced Filtering**: Structured filter objects for complex criteria
3. **Content Negotiation**: Proper Content-Type headers
4. **File Downloads**: Correct blob handling with Content-Disposition parsing

## Next Steps for Deployment

1. Test all export formats in development environment
2. Verify file downloads work correctly in all browsers
3. Confirm backend API accepts new POST request format
4. Monitor error logs for any export failures
5. Update user documentation if export format changed

## Related Documentation

- **API Reference**: `/home/devel/basset-hound/docs/API_REFERENCE.md` (Export Endpoints section)
- **Phase 8 Status**: Memory file `/home/devel/.claude/projects/-home-devel-basset-hound/memory/phase-8-status.md`
- **Blockers**: `/home/devel/.claude/projects/-home-devel-basset-hound/memory/BLOCKERS-2026-05-07.md`

---

**Prepared by**: Claude Code (Haiku 4.5)  
**Estimated Time to Complete**: 45 minutes (ahead of 2-3 hour estimate)
