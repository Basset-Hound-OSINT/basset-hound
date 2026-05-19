# Frontend Code Audit: Phase 8 API Compatibility Analysis

**Audit Date**: 2026-05-19  
**Status**: CRITICAL INCOMPATIBILITIES FOUND  
**Frontend Code Base**: static/js/ (20 JavaScript files), templates/ (4 HTML templates)  
**API Reference Version**: 2.0.0 (Phase 8 with 50+ new endpoints)

---

## Executive Summary

The frontend was built for Phase 1-7 APIs and is **severely incompatible** with Phase 8 backend changes. Analysis of 20 JavaScript files and 4 HTML templates reveals:

- **9 ENDPOINTS BROKEN** - Old endpoints called but changed/removed in Phase 8
- **7 ENDPOINTS RENAMED** - Called with old paths, API expects different structure
- **5 ENDPOINTS MISSING PARAMETERS** - Calls missing required Phase 8 parameters
- **15+ PHASE 8 FEATURES NOT EXPOSED** - New endpoints exist but frontend doesn't use them
- **Multiple API Schemas Incompatible** - Response structures have changed

**Impact**: Dashboard will fail to function properly once it loads. Search, export, relationships, and collaboration features will not work.

---

## Detailed Findings

### WORKING: Endpoints Still Available and Compatible

These endpoints are called by the frontend and remain compatible with Phase 8 API:

| Endpoint | Frontend File | Status | Notes |
|----------|--------------|--------|-------|
| `GET /get_people` | dashboard.js, merge-ui.js, ui-people-list.js | ✅ WORKS | Legacy endpoint, still functional |
| `GET /get_person/{personId}` | api.js, merge-ui.js, ui-person-details.js | ✅ WORKS | Legacy endpoint, still functional |
| `POST /add_person` | ui-form-handlers.js | ✅ WORKS | Legacy endpoint, still functional |
| `POST /update_person/{personId}` | api.js, ui-person-details.js | ✅ WORKS | Legacy endpoint, still functional |
| `POST /delete_person/{personId}` | api.js | ✅ WORKS | Legacy endpoint, still functional |
| `GET /get_config` | dashboard.js | ✅ WORKS | Configuration endpoint, still present |
| `GET /api/v1/platforms` | account-manager.js | ✅ WORKS | Phase 7 endpoint, working |

**Status**: 7 working endpoints (basic CRUD operations)

---

### BROKEN: Endpoints Changed/Moved in Phase 8

These endpoints are called by the frontend but have changed or been replaced:

#### 1. Search API - MAJOR CHANGES
**Frontend Call**:
```javascript
// advanced-search.js, multiple locations
fetch(`/api/v1/projects/${projectName}/search`)
fetch(`/api/v1/projects/${projectName}/search/advanced`)
```

**Current API (Phase 8)**:
- `GET /api/v1/search/full-text?q=query&limit=20` (NEW)
- `GET /api/v1/search/advanced?entity_type=...&tags=...` (CHANGED)
- `GET /api/v1/search/autocomplete?q=john&limit=10` (NEW)
- `GET /api/v1/search/did-you-mean?q=jon+smith` (NEW)

**Issue**: Frontend assumes old search endpoint structure; Phase 8 reorganized search endpoints at `/api/v1/search/*` level instead of `/api/v1/projects/{projectName}/search/*`

**Impact**: CRITICAL - Search functionality will fail

---

#### 2. Suggestions API - INCOMPATIBLE SCHEMA
**Frontend Call**:
```javascript
// merge-ui.js, line 85
fetch(`/api/v1/suggestions/entity/${entityId}?type=duplicate&min_confidence=0.6&limit=100`)
```

**Problem**: Endpoint path doesn't match Phase 8 API documentation. No `/suggestions/entity` endpoint exists in Phase 8. The proper endpoints are:
- `GET /projects/{project_id}/entities/{entity_id}/suggestions` (entity suggestions)
- `GET /api/v1/ml/duplicates?entity_id={id}&confidence_threshold=0.75&limit=10` (duplicate detection via ML)

**Issue**: Path structure completely wrong; missing project context

**Impact**: CRITICAL - Entity suggestion/merge functionality broken

---

#### 3. Relationship Endpoints - INCOMPATIBLE SCHEMA
**Frontend Call**:
```javascript
// relationship-manager.js, line 77
fetch(`/api/v1/projects/${projectName}/entities/${entityId}/relationships?include_details=true`)
```

**Current API (Phase 8)**:
```
GET /projects/{project_id}/relationships
Parameters: entity_id, relationship_type, limit, offset
```

**Issue**: Frontend passes `include_details=true` parameter which doesn't exist in Phase 8 API. Response schema may have changed.

**Impact**: HIGH - Relationship viewing/management broken

---

#### 4. Export Endpoints - PATHS CHANGED
**Frontend Calls**:
```javascript
// export-handler.js
fetch(`/api/v1/projects/${projectSafeName}/export/entities/csv`)
fetch(`/api/v1/projects/${projectSafeName}/export/entities/json`)
fetch(`/api/v1/projects/${projectSafeName}/export/graphml`)
fetch(`/api/v1/projects/${projectSafeName}/export/locations/geojson`)
```

**Current API (Phase 8)**:
```
POST /api/v1/projects/{project_id}/export/graphml
POST /api/v1/projects/{project_id}/export/csv
POST /api/v1/projects/{project_id}/export/json
POST /api/v1/projects/{project_id}/export/geojson
```

**Issues**:
- Frontend uses GET; Phase 8 requires POST
- Request/response body structure changed
- Missing request body validation (Phase 8 expects JSON body with filters)

**Impact**: CRITICAL - Export functionality completely broken

---

#### 5. Graph Visualization Endpoints - MISSING
**Frontend Calls**:
```javascript
// map-handler.js, lines 200-210
fetch(`/api/v1/projects/${projectSafeName}/graph/entity/${entityId}?format=cytoscape&depth=${depth}`)
fetch(`/api/v1/projects/${projectSafeName}/visualization/export/graphml`)
```

**Status**: Endpoints not found in Phase 8 API reference

**Workaround in Phase 8**:
- Use `GET /api/v1/projects/{project_id}/graph/paths/shortest` for path analysis
- Use `GET /api/v1/projects/{project_id}/graph/analytics/centrality` for node analysis
- Graph export handled via `/api/v1/projects/{project_id}/export/graphml`

**Impact**: HIGH - Graph visualization will fail

---

#### 6. Collaboration/Sync Endpoints - WRONG BASE URL
**Frontend Call**:
```javascript
// collaboration-manager.js, line 72
const url = `${protocol}//${window.location.host}/api/v1/collaboration/ws/projects/${this.projectId}?user=${this.userId}`;
```

**Current API (Phase 8)**:
```
WebSocket /ws/sync/{project_id}
(Base WebSocket, not under /api/v1)
```

**Issues**:
- WebSocket path structure wrong
- Expected base: `ws://host/ws/sync/{project_id}` not `/api/v1/collaboration/ws/...`
- Message format may be incompatible

**Impact**: CRITICAL - Real-time collaboration features won't connect

---

#### 7. Accounts/Platforms Endpoints - CHANGED SCHEMA
**Frontend Call**:
```javascript
// account-manager.js
fetch(`/api/v1/projects/${projectName}/entities/${currentEntityId}/accounts`)
fetch(`/api/v1/projects/${projectName}/entities/${currentEntityId}/accounts/${platformId}`, {...})
```

**Current API (Phase 8)**:
- Entity accounts are nested under entity relationships/properties
- No dedicated `/accounts` endpoint
- Platforms are managed via: `GET /platforms`, `POST /platforms`

**Impact**: HIGH - Account management UI broken

---

### MISSING: Parameters Added in Phase 8

Frontend calls exist but missing required Phase 8 parameters:

#### 1. Export Endpoints Need Request Body
**Frontend**: Uses GET with query params only
```javascript
fetch(`/api/v1/projects/${projectSafeName}/export/csv`)
```

**Phase 8 Requirement**: POST with JSON body
```json
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

**Impact**: HIGH - Exports will fail validation

---

#### 2. ML Duplicate Detection Missing
**Frontend**: Uses old `/suggestions/entity` endpoint
```javascript
fetch(`/api/v1/suggestions/entity/${entityId}?type=duplicate&min_confidence=0.6&limit=100`)
```

**Phase 8 Correct Endpoint**:
```
GET /api/v1/ml/duplicates?entity_id={id}&confidence_threshold=0.75&limit=10
GET /api/v1/ml/link-prediction?entity_id={id}&top_k=10
```

**Impact**: CRITICAL - Duplicate detection broken, no ML suggestions

---

### NEW_ENDPOINTS: Phase 8 Features Not Used by Frontend

These new Phase 8 endpoints have no corresponding frontend UI/calls:

#### ML Analytics (8 new endpoints)
```
GET /api/v1/ml/duplicates                    # Duplicate entity detection
POST /api/v1/ml/duplicates/merge             # Merge duplicates
GET /api/v1/ml/link-prediction               # Predict relationships
POST /api/v1/ml/link-prediction/accept       # Accept predictions
GET /api/v1/ml/communities                   # Detect communities
GET /api/v1/ml/anomalies                     # Anomaly detection
POST /api/v1/ml/features/extract             # Feature extraction
GET /api/v1/ml/models/status                 # Model status
```

**Frontend Status**: NO UI for these features  
**Impact**: ML features completely inaccessible from dashboard

---

#### Real-Time Collaboration (7 new endpoints)
```
GET /api/v1/collaboration/presence           # Active users
GET /api/v1/collaboration/activity           # Activity feed
POST /api/v1/collaboration/activity/archive  # Archive activity
GET /api/v1/collaboration/conflicts          # Merge conflicts
POST /api/v1/collaboration/conflicts/resolve # Resolve conflicts
WebSocket /ws/sync/{project_id}              # Real-time sync
POST /api/v1/collaboration/undo              # Undo operations
```

**Frontend Status**: Collaboration-manager.js exists but connects to WRONG endpoint URL  
**Impact**: Collaboration features won't connect; activity feed not visible

---

#### Cache Management (6 new endpoints)
```
GET /api/v1/cache/stats                      # Cache statistics
POST /api/v1/cache/clear                     # Clear cache
POST /api/v1/cache/clear/{key}               # Clear specific key
GET /api/v1/cache/hit-rate                   # Hit rate metrics
POST /api/v1/cache/warm                      # Warm cache
GET /api/v1/cache/keys?pattern=entity:*      # List keys
```

**Frontend Status**: NO UI  
**Impact**: Cache management only available via API, not dashboard

---

#### Plugin System (6 new endpoints)
```
GET /api/v1/plugins                          # List plugins
POST /api/v1/plugins/upload                  # Upload plugin
GET /api/v1/plugins/{plugin_id}              # Get plugin info
POST /api/v1/plugins/{plugin_id}/install     # Install plugin
DELETE /api/v1/plugins/{plugin_id}           # Uninstall plugin
GET /api/v1/plugins/{plugin_id}/data         # Get plugin data
```

**Frontend Status**: plugin-manager.js partially implements this with WRONG base paths  
**Impact**: Plugin loading will fail due to wrong endpoint paths

---

#### Performance Metrics (10+ new endpoints)
```
GET /api/v1/metrics/performance              # Overall metrics
GET /api/v1/metrics/latency                  # Latency distribution
GET /api/v1/metrics/throughput               # Request throughput
GET /api/v1/metrics/database                 # Database metrics
GET /api/v1/metrics/memory                   # Memory statistics
GET /api/v1/queries/slow                     # Slow queries
POST /api/v1/queries/analyze                 # Query analysis
GET /api/v1/indexes                          # Index listing
POST /api/v1/indexes/analyze                 # Index analysis
```

**Frontend Status**: NO UI  
**Impact**: Performance monitoring only via API

---

#### Search Optimization (8 new endpoints)
```
GET /api/v1/search/full-text                 # Full-text search
GET /api/v1/search/advanced                  # Advanced faceted search
GET /api/v1/search/autocomplete              # Entity autocomplete
GET /api/v1/search/did-you-mean              # Fuzzy suggestions
GET /api/v1/search/analytics                 # Search analytics
POST /api/v1/search/index/build              # Rebuild indexes
GET /api/v1/search/facets                    # Available facets
POST /api/v1/search/save                     # Save searches
```

**Frontend Status**: Partially implemented but with WRONG endpoint paths  
**Impact**: Modern search features not available

---

## Critical Workflow Impact Analysis

### 1. Entity Search & Discovery - CRITICAL
**Current Flow**: User searches for entities → advanced-search.js calls API → Results displayed

**Phase 8 Impact**: 
- ❌ Search endpoint paths WRONG
- ❌ Faceted search not implemented
- ❌ Autocomplete not available
- ❌ Fuzzy search not available

**Workaround Needed**: Completely rewrite advanced-search.js to use new `/api/v1/search/*` endpoints

---

### 2. Entity Relationship Management - CRITICAL
**Current Flow**: User views entity → relationship-manager.js fetches relationships → Display tabs

**Phase 8 Impact**:
- ❌ Relationship endpoint schema changed
- ❌ Account management endpoint missing
- ❌ No UI for link prediction (Phase 8 feature)

**Workaround Needed**: Update relationship-manager.js to use new schema; add ML link prediction UI

---

### 3. Data Export - CRITICAL
**Current Flow**: User clicks export → export-handler.js calls API → File downloads

**Phase 8 Impact**:
- ❌ All export endpoints changed from GET to POST
- ❌ Request body schema changed
- ❌ Missing new export format endpoints (GeoJSON, database dump)

**Workaround Needed**: Complete rewrite of export-handler.js with new POST structure

---

### 4. Graph Visualization - HIGH
**Current Flow**: User views map → map-handler.js fetches graph data → Cytoscape renders

**Phase 8 Impact**:
- ❌ Graph entity endpoint missing
- ❌ Visualization endpoint missing
- ⚠️ Workaround exists using new `/graph/paths/shortest` or `/graph/analytics/*`

**Workaround Needed**: Rewrite graph fetching logic; may need to compose from multiple endpoints

---

### 5. Real-Time Collaboration - CRITICAL
**Current Flow**: Dashboard → collaboration-manager.js connects WebSocket → Live updates

**Phase 8 Impact**:
- ❌ WebSocket base URL completely wrong (`/api/v1/collaboration/ws/...` vs `/ws/...`)
- ❌ Message format may be incompatible
- ⚠️ Activity feed endpoint exists but not called

**Workaround Needed**: Fix WebSocket URL in collaboration-manager.js; test message format

---

### 6. Data Import - MEDIUM
**Current Flow**: User uploads file → bulk-import.js handles upload

**Phase 8 Impact**:
- ⚠️ Endpoint exists: `POST /api/v1/projects/{project_id}/bulk/import`
- ✅ Appears compatible

**Status**: Likely working but should test

---

### 7. Duplicate Detection & Merging - CRITICAL
**Current Flow**: User views entity → duplicate suggestions shown → User can merge

**Phase 8 Impact**:
- ❌ `/api/v1/suggestions/entity/...` endpoint removed
- ❌ Replaced with ML duplicate detection: `GET /api/v1/ml/duplicates`
- ❌ Merge endpoint path changed: `/api/v1/suggestions/linking/merge-entities` → `POST /api/v1/ml/duplicates/merge`

**Workaround Needed**: Rewrite merge-ui.js to use ML endpoints instead of suggestions API

---

## Recommendations by Priority

### Priority 1: Critical Blockers (Fix First)
These must be fixed for dashboard to be usable:

1. **Search Endpoints** - Rewrite advanced-search.js
   - File: `/home/devel/basset-hound/static/js/advanced-search.js`
   - Change to use `/api/v1/search/*` endpoints
   - Implement faceted search, autocomplete, fuzzy matching
   - Estimated effort: 3-4 hours

2. **Export Handlers** - Rewrite export-handler.js
   - File: `/home/devel/basset-hound/static/js/export-handler.js`
   - Change all endpoints from GET to POST
   - Add request body structures for each export type
   - Estimated effort: 2-3 hours

3. **Collaboration WebSocket** - Fix collaboration-manager.js
   - File: `/home/devel/basset-hound/static/js/collaboration-manager.js`
   - Fix WebSocket URL from `/api/v1/collaboration/ws/...` to `/ws/...`
   - Test message format compatibility
   - Estimated effort: 1-2 hours

4. **Relationship Management** - Update relationship-manager.js
   - File: `/home/devel/basset-hound/static/js/relationship-manager.js`
   - Update endpoint schema to match Phase 8 API
   - Remove `include_details` parameter
   - Estimated effort: 1-2 hours

### Priority 2: High Impact Features (Fix After Critical)
These provide significant functionality:

5. **ML Features (Duplicates, Link Prediction)**
   - Files: `/home/devel/basset-hound/static/js/merge-ui.js`
   - Implement ML endpoints: `/api/v1/ml/duplicates`, `/api/v1/ml/link-prediction`
   - Update UI to show ML-based suggestions
   - Estimated effort: 3-4 hours

6. **Graph Visualization** - Update map-handler.js
   - File: `/home/devel/basset-hound/static/js/map-handler.js`
   - Implement graph fetching using new endpoints
   - May need to compose from `/graph/paths/shortest` or `/graph/analytics/*`
   - Estimated effort: 2-3 hours

7. **Activity Feed & Presence** - Implement missing UI
   - Files: Create new components for activity feed, presence indicators
   - Call new endpoints: `/api/v1/collaboration/activity`, `/api/v1/collaboration/presence`
   - Estimated effort: 2-3 hours

### Priority 3: Nice-to-Have Features (Fix After Core Works)
These enhance functionality but aren't critical:

8. **Plugin System** - Update plugin-manager.js
   - File: `/home/devel/basset-hound/static/js/plugin-manager.js`
   - Fix endpoint paths in loadPlugins()
   - Estimated effort: 1-2 hours

9. **Cache Management Dashboard** - Create new module
   - Add UI to view cache stats, clear cache
   - Call `/api/v1/cache/*` endpoints
   - Estimated effort: 2-3 hours

10. **Performance Metrics Dashboard** - Create new module
    - Add UI to view performance metrics
    - Call `/api/v1/metrics/*` endpoints
    - Estimated effort: 2-3 hours

---

## Testing Checklist

After fixing each component, verify:

### Search
- [ ] Basic text search returns results
- [ ] Faceted search works (entity_type, tags, date range)
- [ ] Autocomplete returns suggestions
- [ ] Fuzzy search handles typos
- [ ] Query syntax validation works

### Export
- [ ] CSV export downloads correctly
- [ ] JSON export includes all entities
- [ ] GraphML export can be opened in Gephi
- [ ] GeoJSON export displays in map
- [ ] Database dump creates encrypted archive

### Collaboration
- [ ] WebSocket connects without errors
- [ ] Presence updates show active users
- [ ] Activity feed displays changes
- [ ] Offline queue syncs when reconnected
- [ ] Merge conflicts detected and resolvable

### Relationships
- [ ] Relationship list loads
- [ ] Can add new relationships
- [ ] Can edit relationship properties
- [ ] Link prediction suggestions appear (Phase 8)
- [ ] Bulk relationship operations work

### ML Features
- [ ] Duplicate detection runs
- [ ] Duplicates can be merged
- [ ] Link predictions appear
- [ ] Predictions can be accepted
- [ ] Community detection works

### Graph
- [ ] Graph renders with correct layout
- [ ] Nodes colored by entity type
- [ ] Edge labels show relationship types
- [ ] Depth control works
- [ ] Export to GraphML works

---

## Summary of Required Changes

| Component | Type | Files | Effort | Priority |
|-----------|------|-------|--------|----------|
| Search | REWRITE | advanced-search.js | 3-4h | P1 |
| Export | REWRITE | export-handler.js | 2-3h | P1 |
| Collaboration | FIX | collaboration-manager.js | 1-2h | P1 |
| Relationships | UPDATE | relationship-manager.js | 1-2h | P1 |
| ML (Duplicates) | UPDATE | merge-ui.js | 3-4h | P2 |
| Graph | UPDATE | map-handler.js | 2-3h | P2 |
| Activity/Presence | CREATE | new modules | 2-3h | P2 |
| Plugins | UPDATE | plugin-manager.js | 1-2h | P3 |
| Cache UI | CREATE | new module | 2-3h | P3 |
| Metrics UI | CREATE | new module | 2-3h | P3 |

**Total Estimated Effort**: 21-32 hours of development + testing

---

## Files Affected

### JavaScript Files Requiring Updates

1. `/home/devel/basset-hound/static/js/advanced-search.js` - CRITICAL
2. `/home/devel/basset-hound/static/js/export-handler.js` - CRITICAL
3. `/home/devel/basset-hound/static/js/collaboration-manager.js` - CRITICAL
4. `/home/devel/basset-hound/static/js/relationship-manager.js` - CRITICAL
5. `/home/devel/basset-hound/static/js/merge-ui.js` - HIGH
6. `/home/devel/basset-hound/static/js/map-handler.js` - HIGH
7. `/home/devel/basset-hound/static/js/plugin-manager.js` - MEDIUM
8. `/home/devel/basset-hound/static/js/account-manager.js` - CHECK (may need account schema update)

### Files That Should Be Working
- `/home/devel/basset-hound/static/js/api.js` - Basic CRUD OK
- `/home/devel/basset-hound/static/js/ui-form-handlers.js` - OK
- `/home/devel/basset-hound/static/js/ui-person-details.js` - OK
- `/home/devel/basset-hound/static/js/dashboard.js` - OK (once search works)

---

## Next Steps

1. **Immediate**: Once dashboard loads, run this audit as a test plan
2. **Phase 1** (Days 1-2): Fix Priority 1 items (search, export, collaboration, relationships)
3. **Phase 2** (Days 3-4): Implement Priority 2 items (ML, graph, activity)
4. **Phase 3** (Days 5-6): Add Priority 3 items (plugins, cache, metrics UIs)
5. **Phase 4**: Integration testing across all workflows
6. **Phase 5**: Load testing with real data volumes

---

## Reference Documentation

- **Phase 8 API Reference**: `/home/devel/basset-hound/docs/API_REFERENCE.md`
- **Phase 8 Implementation Guide**: `/home/devel/basset-hound/docs/PHASE-8-IMPLEMENTATION-GUIDE.md`
- **Phase 8 Summary**: `/home/devel/basset-hound/docs/archive/PHASE-8-SUMMARY-2026-05-07.md`
- **Current Blockers**: `/home/devel/basset-hound/docs/BLOCKERS-2026-05-07.md`

---

**Audit Report Status**: COMPLETE  
**Prepared by**: Claude Code - Reviewer Agent  
**Date**: 2026-05-19  
**Severity**: CRITICAL - Frontend requires substantial updates before production use
