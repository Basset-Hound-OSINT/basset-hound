# Basset Hound: Master Execution Plan 2026-05-07
**Status**: EXECUTION PHASE  
**Date**: 2026-05-07  
**Objective**: Complete ALL outstanding work and ship production-ready system

---

## Current Status Snapshot

**Completed (Phase 2 - 2026-05-06):**
- ✅ Performance Optimization (Stream A): Cache, pagination, N+1 fixes, search debounce
- ✅ Monitoring & Observability (Stream B): Prometheus, structlog, Grafana
- ✅ LaTeX PDF Reporting (Stream C): pdflatex pipeline, templates, charts
- ✅ Advanced Analytics Research (Stream D): 4 documentation files with architecture
- ✅ Deployment Tests (Stream E): 5 test modules, fresh deployment e2e
- ✅ Phase 48 Backend (Stream 7): Platform entities, HAS_ACCOUNT_ON relationships

**Previously Completed (Phase 1 & Integration Work):**
- ✅ basset-verify integration (fully deployed)
- ✅ basset-hound-browser integration (Stream 8)
- ✅ Cletus integration (Stream 9)
- ✅ Stream 5: Bulk Import UI
- ✅ Stream 10: Production hardening
- ✅ Repository cleanup (root is clean)

**Git Status:**
- 7 commits ahead of origin/main
- All code staged and ready
- Phase 2 mega-commit created (62 files, 16,981 insertions)

---

## Remaining Work (Execution Plan)

### Phase 3: Frontend Polish & UI Completion

**Stream 1: Relationship Management UI** (if not done)
- Files: `static/js/relationship-manager.js`, `templates/dashboard.html`
- Tasks:
  - [ ] Build "Relationships" tab in entity detail panel
  - [ ] List all relationships with types and properties
  - [ ] "Add Relationship" modal with entity search dropdown
  - [ ] Delete relationship with confirmation
  - [ ] Display relationship badges (KNOWS, WORKS_WITH, FAMILY, etc.)
  - [ ] Style with Bootstrap + custom CSS
  - [ ] Test UI with live entity data
  - [ ] Verify relationship create/update/delete endpoints work

**Stream 2: Advanced Search UI** (if not done)
- Files: `static/js/advanced-search.js`, `templates/dashboard.html`
- Tasks:
  - [ ] Expand search bar to toggle advanced panel
  - [ ] Add field-specific filters (name, email, phone, entity type, tags)
  - [ ] Boolean mode toggle (AND/OR)
  - [ ] Date range filters (created_after, created_before)
  - [ ] Submit calls `/api/v1/projects/{name}/search/advanced`
  - [ ] Render results in entity list
  - [ ] Show result count badge
  - [ ] Style panel with Bootstrap grid
  - [ ] Test with multiple entity types

**Stream 3: Smart Suggestions Panel** (if not done)
- Sub-task 3a: Build React bundle
  - [ ] `cd frontend && npm install`
  - [ ] `npm run build`
  - [ ] Copy built assets to `static/js/suggestions/`
- Sub-task 3b: Embed in dashboard
  - [ ] Add suggestions bell icon/badge to header
  - [ ] Add collapsible side panel
  - [ ] Mount React component in dashboard
  - [ ] Wire WebSocket to `ws://localhost:8080/ws/suggestions/{projectId}`
  - [ ] Fetch from `GET /api/v1/suggestions/entity/{entityId}`
  - [ ] Implement "Link", "Dismiss", "Merge" actions
  - [ ] Test real-time suggestion updates

**Stream 4: Entity Merge & Deduplication UI** (if not done)
- Files: `static/js/merge-ui.js`, `templates/dashboard.html`
- Tasks:
  - [ ] Add "Find Duplicates" button to entity detail
  - [ ] Call `GET /api/v1/suggestions/entity/{entityId}?type=duplicate`
  - [ ] Build side-by-side comparison modal
  - [ ] Show match confidence scores
  - [ ] "Merge Into This" button calls merge endpoint
  - [ ] Confirmation warning (irreversible)
  - [ ] Reload UI after successful merge
  - [ ] Test with similar entities

**Stream 5: Graph Visualization Polish** (if not done)
- Files: `templates/map.html`, `static/js/map-handler.js`
- Tasks:
  - [ ] Test map.html with live API data
  - [ ] Add depth slider (1-5 hops) with re-fetch
  - [ ] Layout selector dropdown (COSE/Breadthfirst/Circle/Grid)
  - [ ] "Center" button to re-center graph
  - [ ] Node labels with entity names (truncated 15 chars)
  - [ ] Color nodes by entity type (Person=blue, Org=green, etc.)
  - [ ] Edge labels showing relationship type
  - [ ] Click node → open entity detail
  - [ ] Export button (`GET .../visualization/export?format=graphml`)
  - [ ] Link from entity detail to "View in Graph"
  - [ ] Verify Cytoscape renders correctly with 10+ entities

---

### Phase 4: Account Management & Frontend Integration

**Stream 6: Account Management UI** (Phase 48 Frontend)
- Files: `templates/dashboard.html`, `static/js/account-manager.js` (new)
- Tasks:
  - [ ] Add "Accounts" tab to entity detail panel
  - [ ] List entity's accounts via `GET /api/v1/projects/{name}/entities/{id}/accounts`
  - [ ] Show platform name, username/email, account properties
  - [ ] "Link Account" button → modal with platform dropdown
  - [ ] Form fields: platform select, account identifier, properties
  - [ ] Submit: `POST /api/v1/projects/{name}/entities/{id}/accounts`
  - [ ] Update account properties: `PUT .../accounts/{account_id}`
  - [ ] Delete account: `DELETE .../accounts/{account_id}` with confirmation
  - [ ] Show account creation/update timestamps
  - [ ] Style with Bootstrap badges and tables
  - [ ] Test with 3+ platforms

---

### Phase 5: Testing & Verification

**Stream 7: Frontend Integration Testing**
- Files: `tests/test_frontend_integration.py` (new)
- Tasks:
  - [ ] Test relationship creation from UI
  - [ ] Test advanced search with multiple filters
  - [ ] Test merge UI with duplicate detection
  - [ ] Test graph visualization with depth control
  - [ ] Test account linking to platforms
  - [ ] Test suggestions badge count update
  - [ ] Verify no console errors in browser
  - [ ] Test responsive design (mobile/tablet/desktop)
  - [ ] Load time benchmarks

**Stream 8: End-to-End Production Verification**
- Files: `tests/test_e2e_complete.py` (new)
- Tasks:
  - [ ] Start fresh: `docker compose down -v && docker compose up -d`
  - [ ] Health check: `GET /health` returns all services healthy
  - [ ] Create project → verify 15 platforms seeded
  - [ ] Create 3 entities (person, org, group)
  - [ ] Create relationships between entities
  - [ ] View in graph → verify layout, colors, edges
  - [ ] Add accounts to entity → verify HAS_ACCOUNT_ON edges
  - [ ] Search advanced → test 5+ filter combinations
  - [ ] Generate PDF report → verify file is valid PDF
  - [ ] Test bulk import with CSV
  - [ ] Verify Prometheus metrics on `/metrics`
  - [ ] Check Grafana dashboard at port 3001
  - [ ] Test suggestions workflow
  - [ ] Test merge UI with duplicates
  - [ ] Run deployment tests: `pytest tests/deployment/ -v`
  - [ ] All tests PASS with no errors

---

### Phase 6: Documentation & Knowledge Transfer

**Stream 9: Session Documentation**
- Files: `docs/archive/SESSION-2026-05-07.md` (this becomes the session record)
- Tasks:
  - [ ] Document all decisions made
  - [ ] List all files created/modified
  - [ ] Include deployment instructions
  - [ ] Note any blockers encountered
  - [ ] Performance metrics achieved
  - [ ] Testing results

**Stream 10: README & Deployment Guide Update**
- Files: `README.md`, `docs/DEPLOYMENT.md` (new if needed)
- Tasks:
  - [ ] Update README with full feature list
  - [ ] Add quick start instructions
  - [ ] Document all API endpoints by category
  - [ ] Include screenshot/diagram of dashboard
  - [ ] Add deployment guide for production
  - [ ] List all integrations and their status
  - [ ] Include troubleshooting section
  - [ ] Add contribution guidelines

**Stream 11: Final Repository Audit**
- Tasks:
  - [ ] Verify all .md files in root are gone
  - [ ] Verify docs/archive/ is organized
  - [ ] Check for any debug code or TODOs
  - [ ] Verify all commented-out imports are removed
  - [ ] Check git history is clean
  - [ ] Verify no credentials in code
  - [ ] Run linting/formatting if applicable

---

### Phase 7: Commit & Handoff

**Stream 12: Final Commit & Git Cleanup**
- Tasks:
  - [ ] Create comprehensive session record
  - [ ] Update MEMORY.md with key decisions
  - [ ] Commit all work: `git add -A && git commit`
  - [ ] Verify commit message is clear
  - [ ] Check git log looks good
  - [ ] Don't push (user decision)

---

## Execution Strategy

**Parallelization:**
- Phase 3 (Frontend UI): 5 streams in parallel
  - Stream 1: Relationship Manager
  - Stream 2: Advanced Search
  - Stream 3: Smart Suggestions
  - Stream 4: Entity Merge
  - Stream 5: Graph Visualization
- Phase 4 (Accounts): 1 stream (depends on Phase 3 complete)
- Phase 5 (Testing): 2 streams in parallel (after Phase 4)
  - Stream 7: Frontend Integration Tests
  - Stream 8: E2E Production Verification
- Phase 6 (Documentation): 3 streams in parallel (concurrent with Phase 5)
  - Stream 9: Session Documentation
  - Stream 10: README Update
  - Stream 11: Repository Audit
- Phase 7 (Commit): 1 stream (after all complete)

**Total Estimated Time:**
- Phase 3: 45 min (parallel)
- Phase 4: 20 min
- Phase 5: 30 min (parallel)
- Phase 6: 30 min (parallel)
- Phase 7: 10 min
- **Total: ~90 min working time (parallel execution)**

---

## Success Criteria (All Must Pass)

1. **Functionality**
   - [ ] All 5 Phase 3 UI streams working without errors
   - [ ] Account management fully integrated
   - [ ] No broken links or missing pages

2. **Testing**
   - [ ] Frontend integration tests: 10+/10+ PASS
   - [ ] E2E tests: 15+/15+ PASS
   - [ ] Deployment tests: 5+/5+ PASS
   - [ ] Zero console errors in browser

3. **Performance**
   - [ ] API response times < 500ms (cached)
   - [ ] Graph rendering < 1s (< 100 nodes)
   - [ ] PDF generation < 5s
   - [ ] Frontend load < 2s

4. **Documentation**
   - [ ] README updated with features
   - [ ] All integration points documented
   - [ ] Deployment instructions clear
   - [ ] Session record complete

5. **Repository**
   - [ ] Root is clean (README.md only)
   - [ ] docs/ is organized (archive/, findings/, etc.)
   - [ ] Git history is clean
   - [ ] No credentials in code

---

## Blockers & Fallbacks

**Potential Blockers:**
1. React build fails → Fallback: Use vanilla JS suggestions instead of React
2. Browser integration unavailable → Fallback: Skip browser tests, mark as optional
3. Cletus unavailable → Fallback: Skip Cletus ingest in e2e, mark as optional
4. Docker services fail to start → Fallback: Run unit tests only, mark deployment tests as skipped

**If Any Phase Fails:**
- Document the failure
- Note in session record
- Mark as incomplete/blocked
- Don't proceed to next phase
- Report findings to user

---

## Files to Create/Modify (Summary)

**Phase 3 Frontend (New Files):**
- `static/js/relationship-manager.js`
- `static/js/advanced-search.js`
- `static/js/merge-ui.js`
- `static/js/account-manager.js`
- `static/js/suggestions/` (React bundle)
- `static/css/suggestions.css`
- Templates modified: `dashboard.html`, `map.html`

**Phase 5 Testing (New Files):**
- `tests/test_frontend_integration.py`
- `tests/test_e2e_complete.py`

**Phase 6 Documentation (New/Modified):**
- `docs/archive/SESSION-2026-05-07.md`
- `README.md` (updated)
- `docs/DEPLOYMENT.md` (new if needed)
- `MEMORY.md` (updated with discoveries)

---

## Next Steps

1. ✅ This plan is created
2. ✅ This plan is saved to `docs/archive/MASTER-EXECUTION-PLAN-2026-05-07.md`
3. ⏳ Execute Phase 3 (5 agents in parallel)
4. ⏳ Execute Phase 4 (1 agent)
5. ⏳ Execute Phase 5 (2 agents in parallel)
6. ⏳ Execute Phase 6 (3 agents in parallel)
7. ⏳ Execute Phase 7 (1 agent - final commit)
8. ⏳ Report completion to user

---

**Plan Status**: READY FOR EXECUTION  
**Start Time**: 2026-05-07 (NOW)  
**Expected Completion**: ~90 minutes (with parallel execution)

All agents should spawn immediately upon approval.
