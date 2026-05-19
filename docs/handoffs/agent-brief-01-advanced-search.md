# Agent Brief: Advanced Search Fix (Priority 1)

**Agent Instance**: `js-dev@basset-hound:search`  
**Target File**: `static/js/advanced-search.js`  
**Estimated Time**: 3-4 hours  
**Priority**: CRITICAL Phase 1 Blocker

## Problem Statement

The advanced-search.js file uses Phase 1-7 API endpoints that have been completely restructured in Phase 8. All search endpoints have moved from project-scoped paths to global paths.

### Current (Broken) API Calls
```javascript
// OLD - These endpoints no longer exist
fetch(`/api/v1/projects/${projectName}/search`)
fetch(`/api/v1/projects/${projectName}/search/advanced`)
fetch(`/api/v1/projects/${projectName}/search/autocomplete`)
```

### Phase 8 API Endpoints (Use These)
All search endpoints now use `/api/v1/search/*` (NO project context):

1. **Full-Text Search** (NEW)
   ```
   GET /api/v1/search/full-text?q=query&limit=20
   ```
   Response includes: `results[]`, `meta.total_results`, `meta.query_time_ms`, `meta.suggestion`

2. **Advanced/Faceted Search**
   ```
   GET /api/v1/search/advanced?entity_type=PERSON&tags=VIP&created_after=2026-01-01&limit=20&offset=0
   ```
   Parameters: `entity_type`, `tags`, `created_after`, `created_before`, `limit`, `offset`

3. **Autocomplete** (NEW)
   ```
   GET /api/v1/search/autocomplete?q=john&limit=10
   ```
   Quick suggestions as user types

4. **Did-You-Mean/Fuzzy Search** (NEW)
   ```
   GET /api/v1/search/did-you-mean?q=jon+smith
   ```
   Handles typos and variations

## Implementation Steps

1. **Read current file**: `/home/devel/basset-hound/static/js/advanced-search.js`
   - Identify all API endpoint calls (search for `fetch(` and `/api/v1/projects`)

2. **Update URL paths**: Remove `/projects/{projectName}` from all search endpoint paths

3. **Update query parameters**: Ensure parameters match Phase 8 schema
   - Phase 8 uses: `entity_type`, `tags`, `created_after/before`, not custom names
   - Parameter names must be lowercase with underscores

4. **Test locally**: 
   - Open browser console
   - Test: `fetch('/api/v1/search/full-text?q=test').then(r => r.json()).then(console.log)`
   - Verify response structure matches API documentation

5. **Report findings**: Create `/home/devel/basset-hound/docs/handoffs/frontend-fix-advanced-search-report.md`
   - List all changes made
   - Document any parameter mapping challenges
   - Include test results

## Reference Materials (READ-ONLY)

- `/home/devel/basset-hound/docs/API_REFERENCE.md` (Search Optimization Endpoints ~line 1921+)
- `/home/devel/basset-hound/docs/handoffs/reviewer-frontend-audit.md` (detailed audit findings)
- `/home/devel/basset-hound/docs/handoffs/AUDIT-SUMMARY.txt` (quick summary)

## Constraints

- **NO git commits** - user explicitly requested no commits
- Edit ONLY `static/js/advanced-search.js` - do not modify other files
- Do not create new files except the report
- All changes must be compatible with existing UI (no breaking HTML changes)

## Success Criteria

- [x] All `/api/v1/projects/{proj}/search*` calls removed
- [x] All calls updated to `/api/v1/search/*` endpoints
- [x] Query parameters match Phase 8 schema
- [x] At least one endpoint tested successfully in browser console
- [x] Report created with full details

---
**Status**: Awaiting agent start  
**Created**: 2026-05-19  
**Dashboard Status**: May have Jinja2 template error, but this won't affect API calls once frontend loads
