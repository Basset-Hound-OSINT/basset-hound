# Agent Brief: Relationship Manager Fix (Priority 1)

**Agent Instance**: `js-dev@basset-hound:relationships`  
**Target File**: `static/js/relationship-manager.js`  
**Estimated Time**: 1-2 hours  
**Priority**: CRITICAL Phase 1 Blocker

## Problem Statement

The relationship-manager.js file uses deprecated API parameters and possibly incompatible request/response schemas. The primary issue is the `include_details=true` parameter which no longer exists in Phase 8 relationship API.

### Current (Broken) API Call
```javascript
// OLD - include_details parameter no longer exists
fetch(`/api/v1/projects/${projectName}/entities/${entityId}/relationships?include_details=true`)
```

### Phase 8 API Endpoints (Use These)

1. **List Relationships**
   ```
   GET /projects/{project_id}/relationships
   ```
   Parameters: `entity_id`, `relationship_type`, `limit`, `offset` (NO include_details)

2. **Create Relationship**
   ```
   POST /projects/{project_id}/relationships
   Content-Type: application/json
   
   {
     "source": "ent_001",
     "target": "ent_002",
     "type": "WORKS_FOR",
     "properties": {
       "title": "Senior Developer",
       "start_date": "2020-01-15",
       "confidence": 0.95
     },
     "bidirectional": false,
     "source": "analyst_observation",
     "confidence_level": "HIGH"
   }
   ```

3. **Get Relationship**
   ```
   GET /projects/{project_id}/relationships/{relationship_id}
   ```

4. **Update Relationship**
   ```
   PUT /projects/{project_id}/relationships/{relationship_id}
   Content-Type: application/json
   
   {
     "properties": {
       "title": "Lead Developer",
       "confidence": 0.98
     }
   }
   ```

5. **Delete Relationship**
   ```
   DELETE /projects/{project_id}/relationships/{relationship_id}
   ```

## Key Changes from Phase 7 to Phase 8

1. **Removed**: `include_details=true` parameter (no longer needed)
2. **Response Structure**: Relationships now include full details by default
3. **Required Fields**: POST requests need proper JSON body structure
4. **Type Field**: Use `type` field (not `relationship_type`)
5. **Properties**: Nested in `properties` object, not at root level

## Phase 8 Response Format

```json
{
  "status": "success",
  "data": {
    "id": "rel_001",
    "source": "ent_001",
    "target": "ent_002",
    "type": "WORKS_FOR",
    "properties": {
      "title": "Senior Developer",
      "start_date": "2020-01-15",
      "confidence": 0.95
    },
    "created_at": "2026-05-07T10:00:00Z",
    "updated_at": "2026-05-07T11:00:00Z"
  }
}
```

## Implementation Steps

1. **Read current file**: `/home/devel/basset-hound/static/js/relationship-manager.js`
   - Find all fetch calls to relationship endpoints
   - Identify `include_details=true` usage
   - Note any field mapping issues in request/response handling

2. **Remove deprecated parameters**:
   - Delete `?include_details=true` from all relationship GET requests
   - Phase 8 returns full details by default

3. **Update CRUD operations**:
   - **CREATE**: Ensure POST body matches Phase 8 schema (see above)
   - **READ**: Update to new endpoint path and remove include_details
   - **UPDATE**: Ensure properties are nested properly
   - **DELETE**: No changes needed (same path structure)

4. **Update response handling**:
   - Ensure code handles new response structure
   - Properties are now nested in `properties` object
   - Timestamps include both `created_at` and `updated_at`

5. **Test relationships**:
   - Test GET relationship list
   - Test creating a new relationship
   - Test updating relationship properties
   - Test deleting a relationship

6. **Report findings**: Create `/home/devel/basset-hound/docs/handoffs/frontend-fix-relationship-manager-report.md`
   - Document all parameter changes
   - List CRUD operation updates
   - Include test results for all operations

## Reference Materials (READ-ONLY)

- `/home/devel/basset-hound/docs/API_REFERENCE.md` (Relationship Endpoints ~line 540+)
- `/home/devel/basset-hound/docs/handoffs/reviewer-frontend-audit.md` (detailed audit findings)
- `/home/devel/basset-hound/docs/handoffs/AUDIT-SUMMARY.txt` (quick summary)

## Constraints

- **NO git commits** - user explicitly requested no commits
- Edit ONLY `static/js/relationship-manager.js` - do not modify other files
- Do not create new files except the report
- Must support all CRUD operations (Create, Read, Update, Delete)

## Success Criteria

- [x] All `include_details=true` parameters removed
- [x] POST request bodies match Phase 8 schema
- [x] Response handling updated for new structure
- [x] All CRUD operations tested successfully
- [x] Properties properly nested in objects
- [x] Report created with full details

---
**Status**: Awaiting agent start  
**Created**: 2026-05-19  
**Dashboard Status**: May have Jinja2 template error, but this won't affect relationship API calls
