# Agent Brief: Collaboration Manager Fix (Priority 1)

**Agent Instance**: `js-dev@basset-hound:collaboration`  
**Target File**: `static/js/collaboration-manager.js`  
**Estimated Time**: 1-2 hours  
**Priority**: CRITICAL Phase 1 Blocker

## Problem Statement

The collaboration-manager.js file uses an old WebSocket endpoint path that has been completely changed in Phase 8. The WebSocket connection cannot be established with the old path.

### Current (Broken) WebSocket Path
```javascript
// OLD - This endpoint no longer exists
WebSocket /api/v1/collaboration/ws/projects/{proj}
```

### Phase 8 WebSocket Endpoint (Use This)
```javascript
// NEW - Completely different base path
WebSocket /ws/sync/{project_id}
```

The new endpoint is simpler and message format has changed to support real-time collaboration.

## Phase 8 WebSocket Details

### Connection
```javascript
const ws = new WebSocket('ws://localhost:8080/ws/sync/proj_123');

ws.onopen = () => {
  console.log('Connected to real-time sync');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Event type:', data.type);
  // Handle incoming sync message
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};
```

### Message Format (Phase 8)
```json
{
  "type": "entity_updated",
  "entity_id": "ent_123",
  "changes": {
    "fields": {"email": "new@example.com"}
  },
  "user_id": "usr_456",
  "timestamp": "2026-05-07T12:00:00Z"
}
```

### Supported Message Types
- `entity_updated` - Entity data changed
- `entity_created` - New entity created
- `entity_deleted` - Entity removed
- `relationship_created` - Relationship added
- `relationship_updated` - Relationship modified
- `relationship_deleted` - Relationship removed
- `conflict` - Merge conflict detected

## Implementation Steps

1. **Read current file**: `/home/devel/basset-hound/static/js/collaboration-manager.js`
   - Find WebSocket constructor call
   - Locate URL construction with `/api/v1/collaboration/ws/projects/`

2. **Update WebSocket URL**:
   - Change from: `/api/v1/collaboration/ws/projects/{proj}`
   - Change to: `/ws/sync/{project_id}`
   - Ensure protocol is `ws://` (WebSocket) or `wss://` (secured)

3. **Update message handling**:
   - Update message type checks to match Phase 8 types
   - Adjust field access for new message structure
   - Ensure `changes.fields` object is properly handled

4. **Test WebSocket connection**:
   - Open browser console
   - Verify WebSocket connection: `new WebSocket('ws://localhost:8080/ws/sync/proj_test')`
   - Monitor onopen/onerror events
   - Send test message from server to verify message handling

5. **Report findings**: Create `/home/devel/basset-hound/docs/handoffs/frontend-fix-collaboration-manager-report.md`
   - Document WebSocket URL change
   - List message type updates
   - Include connection test results

## Reference Materials (READ-ONLY)

- `/home/devel/basset-hound/docs/API_REFERENCE.md` (Real-Time Collaboration Endpoints ~line 1622+)
- `/home/devel/basset-hound/docs/handoffs/reviewer-frontend-audit.md` (detailed audit findings)
- `/home/devel/basset-hound/docs/handoffs/AUDIT-SUMMARY.txt` (quick summary)

## Constraints

- **NO git commits** - user explicitly requested no commits
- Edit ONLY `static/js/collaboration-manager.js` - do not modify other files
- Do not create new files except the report
- WebSocket URL is the PRIMARY change (path completely different)

## Success Criteria

- [x] WebSocket URL updated to `/ws/sync/{project_id}`
- [x] Message type handling updated for Phase 8 schema
- [x] Message structure updated (fields now in `changes.fields`)
- [x] WebSocket connection tested and verified working
- [x] All message handlers compatible with new format
- [x] Report created with full details

---
**Status**: Awaiting agent start  
**Created**: 2026-05-19  
**Dashboard Status**: May have Jinja2 template error, but this won't affect WebSocket connections
