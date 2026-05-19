# Agent Brief: Export Handler Fix (Priority 1)

**Agent Instance**: `js-dev@basset-hound:export`  
**Target File**: `static/js/export-handler.js`  
**Estimated Time**: 2-3 hours  
**Priority**: CRITICAL Phase 1 Blocker

## Problem Statement

The export-handler.js file uses GET requests with query parameters to export data. Phase 8 changed all export endpoints to use POST requests with JSON body containing filters and pagination.

### Current (Broken) API Call
```javascript
// OLD - GET with query params (no longer supported)
GET /api/v1/projects/{proj}/export/csv?entity_types=PERSON&tags=VIP&fields=id,name,email
```

### Phase 8 API Endpoints (Use These)
All exports now use **POST with JSON body** and include filters, fields, and pagination:

1. **Export as CSV**
   ```
   POST /api/v1/projects/{project_id}/export/csv
   Content-Type: application/json
   
   {
     "filters": {
       "created_after": "2026-01-01",
       "entity_types": ["Person"]
     },
     "fields": ["id", "name", "email"],
     "page": 1,
     "limit": 1000
   }
   ```

2. **Export as JSON**
   ```
   POST /api/v1/projects/{project_id}/export/json
   Content-Type: application/json
   
   {
     "include_entities": true,
     "include_relationships": true,
     "filters": {...}
   }
   ```

3. **Export as GraphML** (for graph visualization)
   ```
   POST /api/v1/projects/{project_id}/export/graphml
   Content-Type: application/json
   
   {
     "entity_types": ["Person"],
     "tags": ["VIP"],
     "include_properties": true
   }
   ```

4. **Export as GeoJSON** (for map visualization)
   ```
   POST /api/v1/projects/{project_id}/export/geojson
   Content-Type: application/json
   
   {
     "entity_type": "Location"
   }
   ```

5. **Export as PDF Report**
   ```
   POST /api/v1/projects/{project_id}/export/pdf
   Content-Type: application/json
   
   {
     "title": "Investigation Report",
     "include_charts": true,
     "include_metrics": true
   }
   ```

## Implementation Steps

1. **Read current file**: `/home/devel/basset-hound/static/js/export-handler.js`
   - Identify all export endpoint calls (look for `/export/` in fetch/XMLHttpRequest)
   - Note which format each call is for (CSV, JSON, GraphML, etc.)

2. **Convert GET → POST**: 
   - Change HTTP method from GET to POST
   - Move query parameters into JSON request body
   - Add `Content-Type: application/json` header

3. **Update request structure**:
   - Create filters object from existing parameters
   - Add `fields` array if applicable (CSV exports)
   - Add `include_*` flags if applicable (JSON exports)
   - Map old parameter names to Phase 8 schema

4. **Handle responses**:
   - POST endpoints return same data format as GET
   - No changes needed to response handling
   - Ensure download/display logic still works

5. **Test locally**:
   - Test at least one export format in browser console
   - Verify response structure is correct
   - Test download functionality if applicable

6. **Report findings**: Create `/home/devel/basset-hound/docs/handoffs/frontend-fix-export-handler-report.md`
   - List all export formats fixed (CSV, JSON, GraphML, GeoJSON, PDF)
   - Document parameter mapping
   - Include test results

## Reference Materials (READ-ONLY)

- `/home/devel/basset-hound/docs/API_REFERENCE.md` (Export Endpoints ~line 1757+)
- `/home/devel/basset-hound/docs/handoffs/reviewer-frontend-audit.md` (detailed audit findings)
- `/home/devel/basset-hound/docs/handoffs/AUDIT-SUMMARY.txt` (quick summary)

## Constraints

- **NO git commits** - user explicitly requested no commits
- Edit ONLY `static/js/export-handler.js` - do not modify other files
- Do not create new files except the report
- Must support all 5 export formats (CSV, JSON, GraphML, GeoJSON, PDF)

## Success Criteria

- [x] All export endpoints changed from GET to POST
- [x] Query parameters moved to JSON request body
- [x] Content-Type header set to application/json
- [x] All 5 export formats (CSV, JSON, GraphML, GeoJSON, PDF) supported
- [x] At least one export format tested successfully
- [x] Report created with full details

---
**Status**: Awaiting agent start  
**Created**: 2026-05-19  
**Dashboard Status**: May have Jinja2 template error, but this won't affect API calls once frontend loads
