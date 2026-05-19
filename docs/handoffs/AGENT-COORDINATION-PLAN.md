# Frontend API Fix Coordination Plan - Phase 1 (Critical)

**Coordinator**: Claude Code Agent  
**Date**: 2026-05-19  
**Objective**: Spawn 4 parallel JavaScript developer agents to fix Priority 1 critical API compatibility issues

---

## Executive Summary

Dashboard is currently blocked by Jinja2 template error, but core backend API is working and tested. Frontend has 31-37 hours of identified fixes needed across multiple priority tiers. This document coordinates the spawning of **4 parallel agents** to fix the most critical blocking issues first.

**Current Status**: 
- Phase 8 backend: Complete and tested
- Frontend dashboard: Blocked by template issue (not a code issue)
- Frontend JavaScript: Has 4 CRITICAL files with breaking API changes
- Timeline: Agents should complete Priority 1 in 7-11 hours (parallel execution)

---

## Phase 1: Critical Blockers (4 Parallel Agents)

These 4 files have blocking issues preventing core functionality. Each gets its own agent with exclusive edit access.

### Agent 1: Search Fix
- **Instance Name**: `js-dev@basset-hound:search`
- **Target File**: `static/js/advanced-search.js`
- **Estimated Time**: 3-4 hours
- **Issues**: 
  - Search endpoints moved from `/api/v1/projects/{proj}/search/*` to `/api/v1/search/*`
  - New endpoints: full-text, autocomplete, did-you-mean
  - Query parameter schema changed
- **Briefing**: `/home/devel/basset-hound/docs/handoffs/agent-brief-01-advanced-search.md`
- **Report Destination**: `/home/devel/basset-hound/docs/handoffs/frontend-fix-advanced-search-report.md`

### Agent 2: Export Fix
- **Instance Name**: `js-dev@basset-hound:export`
- **Target File**: `static/js/export-handler.js`
- **Estimated Time**: 2-3 hours
- **Issues**:
  - Export endpoints changed from GET to POST
  - Query parameters moved to JSON body
  - Support 5 formats: CSV, JSON, GraphML, GeoJSON, PDF
- **Briefing**: `/home/devel/basset-hound/docs/handoffs/agent-brief-02-export-handler.md`
- **Report Destination**: `/home/devel/basset-hound/docs/handoffs/frontend-fix-export-handler-report.md`

### Agent 3: Collaboration/WebSocket Fix
- **Instance Name**: `js-dev@basset-hound:collaboration`
- **Target File**: `static/js/collaboration-manager.js`
- **Estimated Time**: 1-2 hours
- **Issues**:
  - WebSocket path changed from `/api/v1/collaboration/ws/projects/{proj}` to `/ws/sync/{proj}`
  - Message format changed
  - Event types updated for Phase 8
- **Briefing**: `/home/devel/basset-hound/docs/handoffs/agent-brief-03-collaboration-manager.md`
- **Report Destination**: `/home/devel/basset-hound/docs/handoffs/frontend-fix-collaboration-manager-report.md`

### Agent 4: Relationship Management Fix
- **Instance Name**: `js-dev@basset-hound:relationships`
- **Target File**: `static/js/relationship-manager.js`
- **Estimated Time**: 1-2 hours
- **Issues**:
  - `include_details=true` parameter removed (no longer exists)
  - Response schema changed
  - POST body structure updated
  - CRUD operations need schema updates
- **Briefing**: `/home/devel/basset-hound/docs/handoffs/agent-brief-04-relationship-manager.md`
- **Report Destination**: `/home/devel/basset-hound/docs/handoffs/frontend-fix-relationship-manager-report.md`

---

## Agent Orchestration Rules

### Exclusive File Access
```
Agent 1 (search):        static/js/advanced-search.js       (EXCLUSIVE EDIT)
Agent 2 (export):        static/js/export-handler.js        (EXCLUSIVE EDIT)
Agent 3 (collaboration): static/js/collaboration-manager.js (EXCLUSIVE EDIT)
Agent 4 (relationships): static/js/relationship-manager.js  (EXCLUSIVE EDIT)

All agents:              ALL OTHER FILES                    (READ-ONLY)
```

### Shared Read-Only Access
All agents have read-only access to reference materials:
- `/home/devel/basset-hound/docs/API_REFERENCE.md` - Complete API documentation
- `/home/devel/basset-hound/docs/handoffs/reviewer-frontend-audit.md` - Detailed audit findings
- `/home/devel/basset-hound/docs/handoffs/AUDIT-SUMMARY.txt` - Quick reference summary

### Global Constraints
- **NO git commits** - User explicitly requested no commits
- **NO database changes** - API layer only
- **NO file conflicts** - Each agent has exclusive edit access to one file
- **Parallel execution** - All 4 agents work simultaneously
- **Report only** - Each agent creates one report file when done

---

## Agent Briefing Sequence

**For Coordinator/User**: To spawn agents, use the briefing documents:

```bash
# Agent 1 - Search Fix
# Use briefing: /home/devel/basset-hound/docs/handoffs/agent-brief-01-advanced-search.md

# Agent 2 - Export Fix
# Use briefing: /home/devel/basset-hound/docs/handoffs/agent-brief-02-export-handler.md

# Agent 3 - Collaboration Fix
# Use briefing: /home/devel/basset-hound/docs/handoffs/agent-brief-03-collaboration-manager.md

# Agent 4 - Relationship Fix
# Use briefing: /home/devel/basset-hound/docs/handoffs/agent-brief-04-relationship-manager.md
```

Each briefing document contains:
- Problem statement with before/after code
- Complete Phase 8 API endpoint specifications
- Implementation steps
- Test procedures
- Reference materials (all read-only)
- Success criteria

---

## Integration Testing (After Phase 1 Agents Complete)

Once all 4 agents report completion, run integration tests:

```javascript
// Test 1: Search
fetch('/api/v1/search/full-text?q=john&limit=10')
  .then(r => r.json())
  .then(d => console.log('Search result count:', d.data.results.length))

// Test 2: Export
fetch('/api/v1/projects/proj_test/export/csv', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({fields: ['id', 'name'], limit: 10})
})
  .then(r => r.json())
  .then(d => console.log('Export successful'))

// Test 3: WebSocket Collaboration
const ws = new WebSocket('ws://localhost:8080/ws/sync/proj_test')
ws.onopen = () => console.log('WebSocket connected')
ws.onerror = e => console.error('WebSocket error:', e)

// Test 4: Relationships
fetch('/projects/proj_test/relationships?entity_id=ent_001&limit=20')
  .then(r => r.json())
  .then(d => console.log('Relationship count:', d.data.length))
```

---

## Phase 2: Secondary Priority (After Phase 1)

Once Phase 1 agents complete, 3 more agents will be spawned for Phase 2:

1. **merge-ui.js** - Merge UI and suggestions API incompatibilities
2. **map-handler.js** - Map rendering and geolocation updates
3. **account-manager.js** - Account/user management endpoint changes

Phase 2 estimated time: 8-12 hours total (parallel)

---

## Timeline Estimate

| Phase | Tasks | Agents | Parallel Time | Status |
|-------|-------|--------|--------------|--------|
| Phase 1 | 4 critical files | 4 parallel | 7-11 hours | **SPAWNING NOW** |
| Integration Test | Verify all 4 fixes | Automated | 0.5 hours | Pending Phase 1 |
| Phase 2 | 3 secondary files | 3 parallel | 8-12 hours | Pending Phase 1 |
| **Total** | **7 files** | **7 agents** | **~20 hours** | |

---

## Key Notes

1. **Dashboard Still Blocked**: The Jinja2 template error may prevent dashboard from loading, but once it's fixed, these JavaScript fixes will be immediately needed.

2. **API Working**: The backend API is complete, tested, and working. Agents only need to update frontend calls to match the new API paths and schemas.

3. **No Breaking Changes**: All fixes are additive - they adapt existing features to new endpoints, they don't break existing working features.

4. **Reference Quality**: All agents have comprehensive reference materials (API_REFERENCE.md is 2000+ lines with all endpoint details).

---

## Spawn Instructions

To spawn the 4 agents, provide each with:
1. The appropriate briefing document (agent-brief-0X-*.md)
2. Repository path: `/home/devel/basset-hound`
3. Working directory context: Frontend JavaScript API layer
4. Constraint: No git commits, exclusive file access

**Briefing Documents Ready**: All 4 briefing documents created and ready for agent distribution.

---

**Coordinator Status**: Ready to dispatch agents  
**Created**: 2026-05-19 14:30  
**Updated**: 2026-05-19 14:35
