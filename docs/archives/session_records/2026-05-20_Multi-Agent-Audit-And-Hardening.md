# Session Record — 2026-05-20: Multi-Agent Audit & Hardening

**Session type:** Orchestrated multi-agent audit + in-session fixes
**Orchestration model:** `/home/devel/palletai/claude_code_orchestra/` — waves of 2-3 agents, strict work-zone separation
**Git commits:** none (per user instruction — work continues)

---

## 1. What was done

### Root-cause fix: API container hang
The `basset_api` container had been hanging on startup for ~1 hour. Root cause: `neo4j_handler.py` passed `max_retry_time=...` to `GraphDatabase.driver()`, but the installed `neo4j` driver removed that config key. It raised `ConfigurationError`, which the `while True:` retry loop silently swallowed and retried forever.

- Removed the invalid `max_retry_time` kwarg
- Added fail-fast on `ConfigurationError`/`AuthError` (non-recoverable) + a 120s wait cap (`NEO4J_STARTUP_MAX_WAIT`)
- Earlier in the session: pinned `bcrypt<4.0.0` to resolve a separate `passlib` incompatibility crash

### 10-stream audit across 4 waves
Each agent wrote a unique findings file (no conflicts). All findings in `docs/findings/2026-05-20-*.md`:

| Wave | Streams | Output |
|------|---------|--------|
| 1 | docs consolidation, neo4j refactor proposal, uncommitted diff review | 3 findings |
| 2 | test coverage gaps, router surface audit, security re-check | 3 findings |
| 3 | docker/nginx review, frontend static audit, dependency audit | 3 findings |
| 4 | master synthesis | `docs/handoffs/MASTER-HANDOFF-2026-05-20.md` |

### Wave 5 — cleanup (3 agents)
- Deleted 3 orphan/dead router files (`cache.py`, `orphan.py`, `schedule.py`) — 1,497 LOC, 20 dead endpoints
- Deleted 288 KB of broken/dead frontend assets (`static/js/dist/`, orphan examples + READMEs)
- `requirements.txt`: `python-dotenv` bumped for CVE-2026-28684; major-version upper bounds on `mypy`, `pytest-asyncio`, `phonenumbers`, `websockets`

### Wave 6 — code work (3 agents)
- Removed `analytics.py` deprecated shim; migrated `tests/test_search_analytics.py` imports to `analytics_v2`
- Wrote `tests/test_normalizer_v2.py` — 70 new unit tests for the 0%-coverage `normalizer_v2` service
- Rebuilt + recreated `basset_api` on the new image; verified healthy, Neo4j connected, 405 routes

### In-session config/infra fixes
- `REQUEST_TIMEOUT` unified to 30s across `.env`, `api/config.py`, `api/main.py` (was inconsistent 5s/30s)
- `.env.example` pool-size drift corrected (150→500), obsolete `NEO4J_MAX_RETRY_TIME` removed
- Test infra unblocked: `GZipMiddleware` import typo fixed, `performance`/`deployment` pytest markers added, `TestResult` class renamed to `GraphVizTestResult` (was blocking collection) → 3,041 tests now collect with 0 errors
- `cletus_integration` router double-prefix bug fixed (`/api/v1/api/v1/cletus` → `/api/v1/cletus`)
- `regex=` → `pattern=` in `api/routers/search.py` (FastAPI deprecation)
- Removed duplicate `httpx` line in `requirements.txt`
- **nginx keepalive fix** — added `map $http_upgrade $connection_upgrade` so `Connection: upgrade` is only sent for WebSockets; previously it defeated the upstream keepalive pool on every request (suspected Phase 8 throughput ceiling)
- nginx proxy timeouts aligned to `REQUEST_TIMEOUT` (60s → 35s)
- Celery worker/beat healthchecks fixed — they were curling port 8000 (which celery doesn't serve), permanently "unhealthy"; replaced with `celery inspect ping` / `pgrep`
- nginx healthcheck `localhost` → `127.0.0.1` (IPv6 `::1` resolution caused false "unhealthy")

---

## 2. Decisions made

- **Auth/passwords are OUT OF SCOPE.** The security re-check (Stream 6) flagged P0s — `AUTH_ENABLED=false`, default admin/user passwords, ~50 routers with no auth. User clarified these are intentional for the single-tenant dev posture. No auth fixes were applied; findings are preserved in `docs/findings/2026-05-20-security-recheck.md` for future reference only.
- **No git commits** — user wants more work complete first.
- **Orphan routers deleted, not archived** — they were never mounted (zero importers verified before each deletion).
- **`analytics.py` shim safe to delete** — only blocker was a test import, which was migrated to `analytics_v2`.
- **neo4j_service.py refactor NOT executed** — 6-phase blueprint proposed by the architect (Stream 2) but deferred; it touches the core data layer and needs a dedicated session.

---

## 3. What's next

Priority order (from `docs/handoffs/MASTER-HANDOFF-2026-05-20.md`):

1. **Validate the Phase 8 fix** — re-run the 100-concurrent-user load test now that the nginx `$connection_upgrade` keepalive fix is live. Confirm whether it lifts the throughput ceiling.
2. **Investigate `/health` false negatives** — endpoint reports `redis`/`celery` as `unavailable` even though both containers are healthy and Redis logs "CONNECTED SUCCESSFULLY". Likely a bug in the cached background health updater (`_update_service_health` in `api/main.py`).
3. **Fix `scripts/minify-js.js`** — its regex destroys URLs and identifiers; replace with esbuild/terser. (`static/js/dist/` was deleted; minification is currently absent.)
4. **More test coverage** — 7 services still at 0% (`chart_generator`, `latex_report_service`, `notification_service`, `result_streaming`, `search_analytics`, etc. — see `docs/findings/2026-05-20-test-coverage-gap-analysis.md`).
5. **neo4j_service.py refactor** — execute Phase A of the blueprint in `docs/findings/2026-05-20-neo4j-service-refactor-proposal.md`.
6. **Docs consolidation** — ~85 handoff files proposed for archival; needs the 4 inbound-reference redirects done first (see `docs/findings/2026-05-20-handoffs-consolidation-audit.md`).
7. **Docker hardening backlog** — `mem_limit`/`cpus` on services, `server_tokens off`, TeXLive sidecar isolation (see `docs/findings/2026-05-20-docker-nginx-review.md`).

---

## 4. Blockers / open issues

- `/health` redis+celery false-negative (item 2 above) — not yet diagnosed.
- `import_mapping.py:258` — `SyntaxWarning: invalid escape sequence '\d'` observed at import time; minor, unfixed.
- `nginx` container was recreated to apply the healthcheck fix; verify it reports `healthy` next session.
- Phase 8 throughput ceiling is a *hypothesis* (nginx keepalive) — unproven until the load test is re-run.

---

## 5. Reference

- Master handoff: `docs/handoffs/MASTER-HANDOFF-2026-05-20.md`
- All findings: `docs/findings/2026-05-20-*.md` (see `docs/findings/INDEX.md`)
- Work plan: `docs/handoffs/AGENT-WORK-PLAN-2026-05-20.md`
