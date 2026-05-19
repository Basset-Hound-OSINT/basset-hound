# Agent Spawn Summary - Phase 1 Critical Fixes

**Date**: 2026-05-19  
**Time**: 14:35 UTC  
**Status**: READY FOR DEPLOYMENT  
**Coordinator**: Claude Code

---

## Summary

4 comprehensive briefing documents have been created for 4 parallel JavaScript developer agents to fix critical Phase 8 API compatibility issues in the frontend.

### Quick Status
- ✅ All 4 briefing documents created and ready
- ✅ API reference materials verified
- ✅ Exclusive file access mapped (no conflicts)
- ✅ Integration testing procedures documented
- ✅ Master coordination plan created

---

## Agents to Spawn (4 Total)

### 1️⃣ Search Fix Agent
- **Name**: `js-dev@basset-hound:search`
- **File**: `static/js/advanced-search.js`
- **Time**: 3-4 hours
- **Briefing**: `agent-brief-01-advanced-search.md`
- **Key Fix**: Update search endpoints from `/api/v1/projects/{proj}/search/*` → `/api/v1/search/*`
- **Tests**: Full-text, advanced, autocomplete, did-you-mean searches

### 2️⃣ Export Fix Agent
- **Name**: `js-dev@basset-hound:export`
- **File**: `static/js/export-handler.js`
- **Time**: 2-3 hours
- **Briefing**: `agent-brief-02-export-handler.md`
- **Key Fix**: Convert export endpoints from GET with query params → POST with JSON body
- **Tests**: CSV, JSON, GraphML, GeoJSON, PDF exports

### 3️⃣ Collaboration Fix Agent
- **Name**: `js-dev@basset-hound:collaboration`
- **File**: `static/js/collaboration-manager.js`
- **Time**: 1-2 hours
- **Briefing**: `agent-brief-03-collaboration-manager.md`
- **Key Fix**: Update WebSocket path from `/api/v1/collaboration/ws/projects/{proj}` → `/ws/sync/{proj}`
- **Tests**: WebSocket connection, message handling

### 4️⃣ Relationship Fix Agent
- **Name**: `js-dev@basset-hound:relationships`
- **File**: `static/js/relationship-manager.js`
- **Time**: 1-2 hours
- **Briefing**: `agent-brief-04-relationship-manager.md`
- **Key Fix**: Remove deprecated `include_details=true` parameter, update schema
- **Tests**: Relationship CRUD operations (create, read, update, delete)

---

## Total Estimated Time
- **Parallel Execution**: 7-11 hours (all agents working simultaneously)
- **Integration Testing**: ~0.5 hours (sequential after all agents complete)
- **Critical Path**: Search (longest) at 3-4 hours determines overall time

---

## File Locations

### Briefing Documents (Ready to Distribute)
```
/home/devel/basset-hound/docs/handoffs/
├── agent-brief-01-advanced-search.md      (92 lines)
├── agent-brief-02-export-handler.md       (140 lines)
├── agent-brief-03-collaboration-manager.md (121 lines)
└── agent-brief-04-relationship-manager.md  (156 lines)
```

### Master Coordination Documents
```
/home/devel/basset-hound/docs/handoffs/
├── AGENT-COORDINATION-PLAN.md             (Complete orchestration plan)
├── AGENT-SPAWN-SUMMARY.md                 (This document)
├── reviewer-frontend-audit.md             (Original audit findings)
├── AUDIT-SUMMARY.txt                      (Quick summary)
└── API_REFERENCE.md                       (Complete API documentation)
```

### Expected Report Destinations (After Agents Complete)
```
/home/devel/basset-hound/docs/handoffs/
├── frontend-fix-advanced-search-report.md      (Agent 1 output)
├── frontend-fix-export-handler-report.md       (Agent 2 output)
├── frontend-fix-collaboration-manager-report.md (Agent 3 output)
└── frontend-fix-relationship-manager-report.md  (Agent 4 output)
```

---

## Key Coordination Points

### Exclusive Edit Access (No File Conflicts)
```
Agent 1 → static/js/advanced-search.js       (EXCLUSIVE)
Agent 2 → static/js/export-handler.js        (EXCLUSIVE)
Agent 3 → static/js/collaboration-manager.js (EXCLUSIVE)
Agent 4 → static/js/relationship-manager.js  (EXCLUSIVE)
```

### Shared Read-Only Access
All agents can read:
- `/home/devel/basset-hound/docs/API_REFERENCE.md` (comprehensive API docs)
- `/home/devel/basset-hound/docs/handoffs/reviewer-frontend-audit.md` (detailed findings)
- `/home/devel/basset-hound/docs/handoffs/AUDIT-SUMMARY.txt` (quick reference)

### Global Constraints
- ❌ NO git commits (user explicitly requested)
- ❌ NO database changes
- ❌ NO file conflicts (exclusive edit access enforced)
- ✅ Parallel execution (all agents work simultaneously)
- ✅ Reports only (agents create markdown reports)

---

## What Each Agent Does

### Step 1: Read Briefing
Each agent reads their specific briefing document which includes:
- Problem statement with code examples
- Phase 8 endpoint specifications
- Parameter changes
- Request/response formats
- Implementation steps
- Test procedures
- Success criteria

### Step 2: Analyze Current Code
Agent reads their assigned JavaScript file and identifies:
- Current API calls and endpoints
- Deprecated parameters
- Response structure assumptions

### Step 3: Implement Fixes
Agent makes targeted changes:
- Update endpoint paths
- Convert request/response structures
- Remove deprecated parameters
- Update message/event handling

### Step 4: Test Locally
Agent verifies fixes work:
- Browser console testing
- Endpoint compatibility checks
- Message format validation

### Step 5: Report Results
Agent creates detailed report with:
- Changes made (with code snippets)
- Tests performed and results
- Any blockers or issues encountered
- Success criteria met/not met

---

## Integration Testing (After Phase 1)

Once all agents complete, verify with these manual tests:

```javascript
// Test 1: Search API (Agent 1)
fetch('/api/v1/search/full-text?q=john&limit=10')
  .then(r => r.json())
  .then(d => console.log('✅ Search:', d.data.results.length, 'results'))

// Test 2: Export API (Agent 2)
fetch('/api/v1/projects/proj_test/export/csv', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({fields: ['id', 'name'], limit: 10})
})
  .then(r => r.json())
  .then(d => console.log('✅ Export: CSV generation started'))

// Test 3: WebSocket Collaboration (Agent 3)
const ws = new WebSocket('ws://localhost:8080/ws/sync/proj_test')
ws.onopen = () => console.log('✅ WebSocket: Connected')
ws.onerror = e => console.error('❌ WebSocket error:', e)

// Test 4: Relationships API (Agent 4)
fetch('/api/v1/projects/proj_test/relationships?entity_id=ent_001&limit=10')
  .then(r => r.json())
  .then(d => console.log('✅ Relationships:', d.data.length, 'found'))
```

---

## Dashboard Status Note

⚠️ **Current Status**: Dashboard may still have Jinja2 template error preventing it from loading. However:

1. **This is a separate issue** - not related to the JavaScript API fixes
2. **API fixes are independent** - they work regardless of dashboard loading status
3. **Once dashboard loads** - these API fixes will be immediately needed
4. **Backend is working** - all APIs are tested and functional

---

## What Happens Next

### For Coordinator (User)
1. Review this summary and briefing documents
2. Spawn 4 agents with their respective briefing documents
3. Monitor agents' progress (they'll report to their respective report files)
4. Once all 4 agents complete, run integration tests (instructions above)
5. Evaluate Phase 2 work (3 more secondary agents)

### For Each Agent
1. Read briefing document for their assigned file
2. Read current JavaScript code
3. Make targeted fixes according to Phase 8 API specs
4. Test at least one endpoint locally
5. Create comprehensive report with findings
6. Signal completion

### Dependencies
- **Agent 1** (Search) → No dependencies, can start immediately
- **Agent 2** (Export) → No dependencies, can start immediately
- **Agent 3** (Collaboration) → No dependencies, can start immediately
- **Agent 4** (Relationships) → No dependencies, can start immediately
- **Integration Testing** → Depends on all 4 agents completing

---

## Reference Quality

Each briefing includes:
- ✅ Current (broken) endpoint examples
- ✅ Phase 8 (correct) endpoint specifications
- ✅ Parameter mappings
- ✅ Request/response format changes
- ✅ Implementation steps
- ✅ Test procedures
- ✅ Success criteria
- ✅ Links to reference materials

---

## Coordinator Checklist

Before spawning agents, verify:
- ✅ All 4 briefing documents created
- ✅ API reference materials available
- ✅ Target files exist and readable
- ✅ Exclusive edit access mapped
- ✅ Report destinations ready
- ✅ Integration testing procedures documented
- ✅ No file conflicts possible
- ✅ Git commit constraints clear

**All items checked. Ready to spawn agents.**

---

## Next Steps

1. **Immediate**: Spawn all 4 agents with their briefing documents
2. **Parallel**: All agents work simultaneously (7-11 hour total)
3. **Monitor**: Check report files as agents complete
4. **Verify**: Run integration tests (0.5 hours)
5. **Phase 2**: Spawn 3 secondary agents (if needed)

---

**Status**: READY FOR AGENT DEPLOYMENT  
**Created**: 2026-05-19 14:35 UTC  
**Coordinator**: Claude Code  
**Repository**: /home/devel/basset-hound
