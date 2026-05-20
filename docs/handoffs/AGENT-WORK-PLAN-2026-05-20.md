# Basset-Hound Parallel Work Plan — 2026-05-20

Strategic plan produced by the `planner` orchestrator agent for coordinating 10 independent work streams across 4 waves. Each stream writes to a unique deliverable; no file conflicts.

## Context snapshot

- 60+ docs in `docs/` and `docs/handoffs/` — many duplicates/overlapping (10+ "FINAL-LOAD-TEST-*", 8+ "CHAOS-*", 6+ "NEO4J-POOL-*").
- `api/services/neo4j_service.py` = 2,301 lines, single class `AsyncNeo4jService` doing connection mgmt, circuit breaker, metrics, and all CRUD.
- `api/routers/` has 50+ router modules; `api/services/` has 50+ service modules.
- `tests/` has 90+ test files; `tests/integration/`, `tests/performance/`, `tests/deployment/` already established.
- Uncommitted diffs in: `.env`, `.env.example`, `api/config.py`, `api/main.py`, `api/services/neo4j_service.py`, `docker-compose.yml`, `nginx/nginx.conf`, `requirements.txt`.
- Memory budget: ~6 GB free, swap full → wave streams in groups of 2-3.

## Streams overview

| # | Stream | Agent | Wave | Runtime | Deliverable |
|---|--------|-------|------|---------|-------------|
| 1 | Docs consolidation audit (handoffs) | analyst | 1 | 60-90m | `docs/findings/2026-05-20-handoffs-consolidation-audit.md` |
| 2 | neo4j_service.py refactor proposal | architect | 1 | 60-90m | `docs/findings/2026-05-20-neo4j-service-refactor-proposal.md` |
| 3 | Uncommitted-diff review & risk audit | reviewer | 1 | 45-60m | `docs/findings/2026-05-20-uncommitted-diff-review.md` |
| 4 | Test coverage gap analysis | tester | 2 | 60-75m | `docs/findings/2026-05-20-test-coverage-gap-analysis.md` |
| 5 | Router surface area audit (50+ routers) | analyst | 2 | 60-75m | `docs/findings/2026-05-20-router-surface-audit.md` |
| 6 | Security posture re-check (post-Phase 8) | security-reviewer | 2 | 60-90m | `docs/findings/2026-05-20-security-recheck.md` |
| 7 | Docker/compose/nginx hardening review | reviewer | 3 | 45-60m | `docs/findings/2026-05-20-docker-nginx-review.md` |
| 8 | Frontend static asset & bundle audit | analyst | 3 | 45-60m | `docs/findings/2026-05-20-frontend-static-audit.md` |
| 9 | Dependency & supply-chain audit | security-reviewer | 3 | 30-45m | `docs/findings/2026-05-20-dependency-audit.md` |
| 10 | Master handoff & next-session plan | doc-writer | 4 | 30-45m | `docs/handoffs/MASTER-HANDOFF-2026-05-20.md` |

Waves: 1 → 2 → 3 → 4 (final aggregator). Within each wave, agents run in parallel (2-3 concurrent).

## Wave schedule (memory-bounded)

- **Wave 1** (parallel): Streams 1, 2, 3 — ~90m wall-clock
- **Wave 2** (parallel): Streams 4, 5, 6 — ~75m wall-clock
- **Wave 3** (parallel): Streams 7, 8, 9 — ~60m wall-clock
- **Wave 4** (solo): Stream 10 — ~45m wall-clock

Each agent ≈ 1.5-2 GB resident; orchestrator may overlap wave boundaries when memory permits.

## Hard constraints

- No commits, no deploys, no infra creation.
- No k8s/terraform/multi-region/rate-limiting-infra streams (blacklisted).
- No mobile-app streams (deferred).
- Skips bcrypt + neo4j-query-fix (already done; Stream 3 only audits those diffs).
- All deliverables are `.md` findings/handoffs — no code edits proposed by these streams.

## Conflict matrix

Every stream writes to a unique path. No two streams touch the same file. All work-zone reads are non-exclusive.

---

## Per-stream detail

### Stream 1 — Docs consolidation audit
- **Agent**: analyst
- **Wave**: 1
- **Work zone (READ-ONLY)**: `docs/handoffs/**`, `docs/*.md`
- **Writes ONLY to**: `docs/findings/2026-05-20-handoffs-consolidation-audit.md`
- **Task**: Catalog all 130+ handoff/docs files. Identify duplicates. Propose canonical-vs-archive list. Do NOT delete; propose moves to `docs/handoffs/archive/2026-05/`.

### Stream 2 — neo4j_service.py refactor proposal
- **Agent**: architect
- **Wave**: 1
- **Work zone (READ-ONLY)**: `api/services/neo4j_service.py`, `api/services/cache_service.py`, `api/services/query_cache.py`, `api/services/data_service.py`
- **Writes ONLY to**: `docs/findings/2026-05-20-neo4j-service-refactor-proposal.md`
- **Task**: Map all 2,301 lines into proposed modules. Identify cohesion clusters. Output a refactor blueprint with risk list — NO code changes.

### Stream 3 — Uncommitted-diff review & risk audit
- **Agent**: reviewer
- **Wave**: 1
- **Work zone (READ-ONLY)**: `git diff HEAD` for `.env`, `.env.example`, `api/config.py`, `api/main.py`, `api/services/neo4j_service.py`, `docker-compose.yml`, `nginx/nginx.conf`, `requirements.txt`
- **Writes ONLY to**: `docs/findings/2026-05-20-uncommitted-diff-review.md`
- **Task**: Audit uncommitted changes. Confirm bcrypt pin, `get_server_info()` health check, request-timeout middleware ordering, docker-compose worker bump, .env vs .env.example. Flag any blockers for commit.

### Stream 4 — Test coverage gap analysis
- **Agent**: tester
- **Wave**: 2
- **Work zone (READ-ONLY)**: `tests/**`, `api/services/**`, `.coverage`, `pytest.ini`
- **Writes ONLY to**: `docs/findings/2026-05-20-test-coverage-gap-analysis.md`

### Stream 5 — Router surface area audit
- **Agent**: analyst
- **Wave**: 2
- **Work zone (READ-ONLY)**: `api/routers/**`, `api/main.py`
- **Writes ONLY to**: `docs/findings/2026-05-20-router-surface-audit.md`

### Stream 6 — Security posture re-check
- **Agent**: security-reviewer
- **Wave**: 2
- **Work zone (READ-ONLY)**: `api/auth/**`, `api/middleware/**`, `api/utils/encryption.py`, `api/utils/rate_limiting.py`, prior security audit docs
- **Writes ONLY to**: `docs/findings/2026-05-20-security-recheck.md`

### Stream 7 — Docker/compose/nginx hardening review
- **Agent**: reviewer
- **Wave**: 3
- **Work zone (READ-ONLY)**: `docker-compose.yml`, `docker-compose.dev.yml`, `Dockerfile`, `nginx/nginx.conf`, `.env.example`
- **Writes ONLY to**: `docs/findings/2026-05-20-docker-nginx-review.md`
- **Dependencies**: Stream 3.

### Stream 8 — Frontend static asset & bundle audit
- **Agent**: analyst
- **Wave**: 3
- **Work zone (READ-ONLY)**: `static/**`, `frontend/src/**`, `frontend/package.json`, `frontend/vite.config.ts`
- **Writes ONLY to**: `docs/findings/2026-05-20-frontend-static-audit.md`

### Stream 9 — Dependency & supply-chain audit
- **Agent**: security-reviewer
- **Wave**: 3
- **Work zone (READ-ONLY)**: `requirements.txt`, `frontend/package.json`, `frontend/package-lock.json`
- **Writes ONLY to**: `docs/findings/2026-05-20-dependency-audit.md`
- **Dependencies**: Stream 3.

### Stream 10 — Master handoff
- **Agent**: doc-writer
- **Wave**: 4 (final)
- **Work zone (READ-ONLY)**: all 9 finding files
- **Writes ONLY to**: `docs/handoffs/MASTER-HANDOFF-2026-05-20.md`
- **Dependencies**: ALL streams 1-9 complete.
