# Todo: Next Session (2026-05-07)

## Critical Path (Must Do First)

### 1. Unblock Dashboard Access
- [ ] Investigate Jinja2 "unhashable type: 'dict'" error
  - [ ] Check Starlette/Jinja2 version compatibility
  - [ ] Review `api/routers/frontend.py` template initialization
  - [ ] Test minimal template rendering reproduction
  - [ ] Try alternative: raw HTML responses instead of Jinja2
- [ ] Get dashboard loading at http://localhost:8080
  - [ ] Verify no errors in response
  - [ ] Confirm HTML is being served correctly
  - [ ] Test page functionality (basic clicks, navigation)

### 2. Audit Frontend Code vs API
Once dashboard loads:
- [ ] Review all JavaScript files in `static/js/`
- [ ] List all API endpoints called from frontend
- [ ] Compare against `docs/API_REFERENCE.md`
- [ ] Document missing endpoints
- [ ] Document schema mismatches

### 3. Verify Core Functionality
- [ ] Create test project via API
- [ ] Create test entity via API
- [ ] Verify entity appears in dashboard (if loaded)
- [ ] Test basic CRUD operations

---

## Backend Issues (If Dashboard Unblocked)

- [ ] Investigate Neo4j "disconnected" status in health check
- [ ] Fix celery worker health status
- [ ] Fix nginx health status
- [ ] Run full integration test suite: `pytest tests/ -v`

---

## Frontend Work (Phase 2)

Once backend is stable:
- [ ] Update entity detail view for Phase 8 changes
- [ ] Implement relationship management UI (already exists but needs testing)
- [ ] Implement advanced search UI (already exists but needs testing)
- [ ] Implement smart suggestions panel (React component exists)
- [ ] Implement merge UI (already exists but needs testing)
- [ ] Implement graph visualization enhancements
- [ ] Add ML analytics UI components
- [ ] Add export UI options

---

## Testing (Phase 3)

- [ ] Write frontend unit tests
- [ ] Write frontend integration tests
- [ ] Run full test suite
- [ ] Load test: 1000+ entities
- [ ] Performance test: query latency, cache hit rate

---

## Documentation (Phase 4)

- [ ] Update frontend developer guide
- [ ] Update ROADMAP.md with completion status
- [ ] Create frontend architecture diagram
- [ ] Document all API changes from Phase 8
- [ ] Create migration guide for frontend updates

---

## Deployment Checklist (Phase 5)

Before shipping to production:
- [ ] All 3,000+ tests passing
- [ ] Zero console errors in browser
- [ ] All dashboard features working
- [ ] Performance benchmarks met (see docs/findings/PERFORMANCE-REPORT-2026-05-07.md)
- [ ] Security audit complete
- [ ] Load test passed
- [ ] All services healthy

---

## Reference Files

**Must Read**:
- docs/BLOCKERS-2026-05-07.md
- docs/API_REFERENCE.md
- docs/ARCHITECTURE.md

**Helpful**:
- docs/DEPLOYMENT.md
- docker-compose.yml
- docs/findings/PERFORMANCE-REPORT-2026-05-07.md

**Code to Review**:
- api/routers/frontend.py (problem location)
- static/js/ (frontend code needing update)
- templates/index.html, dashboard.html, map.html

---

## Time Estimates

- Unblock dashboard: 30-60 min
- Audit frontend: 60 min
- Update frontend for Phase 8: 2-3 hours
- Testing & hardening: 1-2 hours
- **Total next session**: 4-6 hours

---

## Notes

- Do NOT make speculative commits - only commit when tested and verified working
- Deploy and test after each meaningful change
- Keep blockers document updated
- Run tests before claiming "done"
- Check browser console for errors before saying frontend works

---

Created: 2026-05-07  
Status: AWAITING NEXT SESSION
