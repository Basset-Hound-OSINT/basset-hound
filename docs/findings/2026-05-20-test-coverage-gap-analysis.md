# Test Coverage Gap Analysis

Date: 2026-05-20
Agent: tester@basset-hound:coverage-gap
Scope: `api/services/` (55 modules) vs `tests/` (85 test files)

## Executive Summary

- **Services**: 55 Python modules (54 functional + `__init__.py`)
- **Test files**: 85 `test_*.py` files (3,036 tests collected; 1 collection error)
- **Direct unit tests for services**: 22 of 54 functional services (40.7%)
- **Aggregate service coverage**: ~24% line coverage across `api/services/` (per stale `.coverage` from 2026-05-19)
- **7 services at 0% line coverage**; 13 services have no direct test file and no indirect imports
- **2 test collection failures** (1 hard import error, 1 broken legacy import)

The codebase has broad test breadth but shallow per-module depth. High-risk security/data services (`neo4j_service`, `audit_logger`, `auto_linker`, `cache_service`, `verification_service`) have direct tests but exercise <40% of code paths. Several brand-new or recently refactored modules (`normalizer_v2`, `orphan_service`, `notification_service`, `result_streaming`, `latex_report_service`, `chart_generator`) have 0% coverage.

## 1. Service-to-Test Mapping

Legend: D = direct `test_<service>.py`, I = indirect import in N other tests, Cov% = line coverage from stale `.coverage`.

| Service | Direct | Indirect | Cov% |
|---|---|---|---|
| analytics_service | - | 1 | 24% |
| audit_logger | D | 1 | 40% |
| auto_linker | D | 2 | 12% |
| bulk_operations | D | 1 | 15% |
| cache_service | D | 2 | 21% |
| chart_generator | - | 0 | 0% |
| cletus_ingestion | - | 1 | 60% |
| collaboration_service | D | 1 | 35% |
| cross_project_linker | D | 1 | 15% |
| crypto_ticker_service | D | 1 | 38% |
| data_import | - | 0 | 19% |
| data_quality | - | 1 | 33% |
| data_service | - | 3 | 18% |
| deduplication | - | 1 | 32% |
| entity_type_ui | - | 1 | 13% |
| export_service | - | 0 | 19% |
| file_hash_service | - | 3 | 21% |
| frontend_components | - | 1 | 83% |
| fuzzy_matcher | D | 1 | 12% |
| graph_format_converter | - | 2 | 25% |
| graph_service | - | 1 | 7% |
| graph_visualization | D | 0 | 18% |
| import_mapping | - | 1 | 34% |
| job_runner | D | 1 | 27% |
| latex_report_service | - | 0 | 0% |
| linking_service | - | 1 | 11% |
| llm_export | - | 2 | 25% |
| marketplace_service | D | 1 | 25% |
| matching_engine | D | 4 | 22% |
| ml_analytics_service | - | 0 | 27% |
| neo4j_service | - | 3 | 12% |
| normalizer | D | 1 | 14% |
| normalizer_v2 | - | 0 | 0% |
| notification_service | - | 1 | 0% |
| orphan_service | - | 0 | 0% |
| platform_service | - | 1 | 36% |
| plugin_service | - | 1 | 33% |
| query_cache | - | 1 | 35% |
| report_export_service | D | 3 | 16% |
| report_scheduler | D | 1 | 24% |
| report_storage | D | 1 | 29% |
| result_streaming | - | 1 | 0% |
| saved_search | - | 1 | 37% |
| scheduler_service | D | 1 | 23% |
| search_analytics | D | 1 | 0% |
| search_service | D | 3 | 15% |
| similarity_service | - | 0 | 17% |
| suggestion_service | - | 1 | 24% |
| template_service | D | 2 | 29% |
| timeline_service | D | 1 | 16% |
| timeline_visualization | - | 1 | 28% |
| verification_service | D | 3 | 22% |
| webhook_service | - | 1 | 37% |
| websocket_service | D | 3 | 35% |

## 2. Top 10 Untested / Under-Tested Services by Risk

Risk score = Domain criticality (1-5) x Coverage Gap (1-5).

| Rank | Service | LOC | Cov% | Risk | Why it matters | Proposed scope |
|---|---|---|---|---|---|---|
| 1 | `neo4j_service` | 667 | 12% | 25 | Core data layer; every router touches it; transaction safety, retries, pooling | Connection-pool fixture; mock Bolt driver; tests for retry, deadlock, session lifecycle, async paths |
| 2 | `orphan_service` | 485 | 0% | 25 | Newly merged (mtime 2026-05-19); handles unmatched evidence (chain-of-custody critical) | Unit tests for orphan creation, merge-into-entity, dedupe paths; round-trip with mock Neo4j |
| 3 | `auto_linker` | 475 | 12% | 20 | Auto-creates relationships between entities — false positives corrupt investigations | Edge cases: identical normalized values, conflicting confidences, batch rollback |
| 4 | `search_service` | 937 | 15% | 20 | Largest service; powers UI/API search; injection surface | Cypher injection fuzz, pagination, facet aggregation, empty-query semantics |
| 5 | `verification_service` | 310 | 22% | 20 | Sock-puppet/identity verification — security-critical | Confidence-band tests, threshold boundaries, multi-platform reconciliation |
| 6 | `normalizer_v2` | 429 | 0% | 20 | Recent rewrite — replaces `normalizer` (which still has tests). No tests against v2 contract | Port `test_normalizer.py` scenarios; add v2-specific date/phone/IBAN tests |
| 7 | `bulk_operations` | 403 | 15% | 16 | Mass-update/delete; idempotency and partial-failure rollback | Atomic-batch tests, dry-run mode, 10k-entity stress (mocked) |
| 8 | `cache_service` | 842 | 21% | 16 | Distributed cache layer; stale-data risk | TTL expiry, invalidation cascade, Redis disconnect graceful degradation |
| 9 | `data_import` | 654 | 19% | 16 | Untrusted-input ingestion; injection + memory exhaustion | Malformed-CSV, huge-payload, schema-mismatch, encoding sniff tests |
| 10 | `audit_logger` | 209 | 40% | 12 | Compliance/forensic trail — tampering surface | Append-only enforcement, signed-hash chain, replay-attack resistance |

Notable also-rans:
- `latex_report_service` (0%, 154 LOC) — PDF generation; low risk but easy quick win
- `chart_generator` (0%, 149 LOC) — no consumers in tests; verify it's still wired
- `result_streaming` (0%, 152 LOC) — referenced in `test_phase20_performance.py` only via `from api.services` (no functional asserts)
- `notification_service` (0%, 61 LOC) — referenced in two websocket tests but not exercised
- `search_analytics` (0%, 208 LOC) — **has a direct test file** but `.coverage` shows 0%; the test file likely never executed in the latest run, suggesting test-run breakage or selective execution

## 3. Orphan / Suspicious Test Files

| File | Issue |
|---|---|
| `tests/test_gzip_compression.py` | Hard `ImportError: cannot import name 'GZIPMiddleware' from 'fastapi.middleware.gzip'` — correct symbol is `GZipMiddleware`. Aborts collection of any session that includes it. |
| `tests/test_orphan_methods.py` | Imports `from neo4j_handler import Neo4jHandler` (top-level `neo4j_handler.py` at repo root). Legacy import; works only when CWD is repo root. Should be `api.services.neo4j_service` or removed if obsolete. |
| `tests/test_add_entity_modal.py` | Defines class `TestResult` with `__init__` — pytest skips collection (warning). Effectively dead. |
| `tests/test_graph_visualization_e2e.py` | Same `TestResult` collection-warning issue — dead class. |
| `tests/test_account_manager.py` | Imports only `from api.main`; tests an "account manager" but no `account_manager.py` service exists. Likely targets `auth/api_key.py` or removed module — verify intent. |
| `tests/test_activity_feed_integration.py` | No `api.*` imports at all; appears to be pure HTTP black-box. Confirm it isn't a stale Phase 14 artifact. |
| `tests/test_e2e_complete.py`, `tests/test_e2e_workflows.py`, `tests/test_graph_visualization_e2e.py` | No `api.*` imports — pure HTTP/Selenium-style; safe but should be marked `@pytest.mark.e2e` (currently unmarked). |
| `tests/test_orphan_methods.py` (again) | Targets `orphan_service` but uses obsolete `Neo4jHandler` path — likely the reason `orphan_service.py` reports 0% coverage despite having "tests". |
| `tests/test_phase23_saved_search.py` | Import line contains `from api.routers."""` (apparent docstring-collision typo) — verify file integrity. |
| `tests/performance/test_suggestion_performance.py` | Uses `@pytest.mark.performance` but marker not registered in `pytest.ini` (warnings). |

## 4. Test Infrastructure Observations

- **`pytest.ini`**: Strict markers enabled. Registers `unit`, `integration`, `e2e`, `slow`, `neo4j`, `mcp`, `api`, `service`, `graph`, `osint`. Missing: `performance` (used by performance suite), `deployment` (registered dynamically in `conftest.py`). Inconsistency: `pytest_configure` in conftest re-adds `integration` and `slow` (duplicate registration).
- **`.coveragerc`**: Empty file — coverage uses defaults. No source filter, no omit list. Means tests, migrations, and `__pycache__` may artificially inflate or deflate ratios.
- **`conftest.py`**: Single global file. Provides `mock_neo4j_handler`, `mock_config`, `sample_project`, `sample_entity`, `sample_report`, plus deployment fixtures (`api_base_url`, `neo4j_config`, `redis_config`). Sets env vars at import time (TESTING=true). No async fixtures; no Redis mock; no JWT/auth fixture (each test re-mocks).
- **No `pytest-asyncio` mode declared** in `pytest.ini` — async tests use `@pytest.mark.asyncio` explicitly. `asyncio_mode = auto` would simplify the ~30+ async tests.
- **No per-package `conftest.py`** under `tests/integration/`, `tests/deployment/`, `tests/performance/` — fixtures aren't scoped, increasing collection cost.
- **`.coverage` data file** dates 2026-05-19 14:59 — stale relative to the Phase 8 multi-worker fix and recent service refactors. Run is incomplete (only 30% TOTAL despite 3036 tests) likely due to load-test collection abort.
- **Pytest collection succeeds for 3036 tests with 1 hard error** (`test_gzip_compression.py`) — needs immediate fix to unblock full-suite runs.

## 5. Recommended Test Additions (Impact-to-Effort Ordered)

### Tier 1 — Quick wins (<2h each, high impact)

1. **Fix `tests/test_gzip_compression.py`** — single-line rename `GZIPMiddleware` -> `GZipMiddleware`. Unblocks full-suite CI runs.
2. **Delete or repair `tests/test_orphan_methods.py`** — legacy import; replace with proper `tests/test_orphan_service.py` mocking `neo4j_service`. Surfaces the 485-LOC 0%-coverage hot zone.
3. **Add `performance` marker** to `pytest.ini`. Eliminates 8 warning lines and unifies marker registration.
4. **Add `tests/test_normalizer_v2.py`** — port the existing `test_normalizer.py` scenarios to v2; closes the largest 0%-coverage code path (429 LOC).
5. **Register `pytest-asyncio` mode** — add `asyncio_mode = auto` to `pytest.ini`.

### Tier 2 — Targeted unit tests (3-5h each)

6. **`tests/test_neo4j_service.py`** — direct unit test against mock Bolt driver. Cover: session/transaction lifecycle, retry-on-transient, parameter sanitization, connection pool exhaustion.
7. **`tests/test_data_import.py`** — malformed CSV/JSON fixtures, oversized payloads, encoding edge cases.
8. **`tests/test_notification_service.py`** — fan-out, deduplication, websocket failure handling.
9. **`tests/test_chart_generator.py` / `tests/test_latex_report_service.py`** — small surface area, fast wins to reach >50% coverage.
10. **`tests/test_result_streaming.py`** — chunking, backpressure, client-disconnect.

### Tier 3 — Hardening (1-2 days)

11. **Augment `test_auto_linker.py`** — add property-based tests (hypothesis) for confidence aggregation and false-positive rate.
12. **Augment `test_audit_logger.py`** — hash-chain integrity, tamper detection.
13. **Augment `test_search_service.py`** — Cypher injection fuzzing, large-result pagination.
14. **Integration test for `orphan_service` + `verification_service` + `auto_linker`** — the three-way evidence-promotion flow currently has no end-to-end coverage.
15. **Investigate why `test_search_analytics.py` shows 0%** — file exists with comprehensive intent (per docstring) but coverage shows 0; likely skipped via missing fixture or import-time failure.

### Tier 4 — Infrastructure

16. **Per-package `conftest.py`** for integration/deployment to scope service-bound fixtures.
17. **Populate `.coveragerc`** with `source = api/`, `omit = */tests/*,*/migrations/*,api/main.py`, branch coverage on.
18. **CI gate**: fail PRs that drop service coverage below 30% TOTAL or any individual high-risk service below its current baseline.

## 6. Coverage by Layer (from stale `.coverage`)

| Layer | Avg Cov | Notes |
|---|---|---|
| `api/services/` | ~24% | This report's focus |
| `api/routers/` | ~40% | Better, but `frontend.py`, `cache.py`, `orphan.py`, `frontend_profiles.py`, `frontend_reports.py`, `reports_pdf.py`, `schedule.py` at 0% |
| `api/models/` | ~65% | Healthiest layer; `data_import.py` and `visualization.py` at 0% |
| `api/main.py` | 0% | Application bootstrap not exercised in unit run |
| `api/middleware/metrics.py` | 0% | Untested middleware |
| **TOTAL** | **30%** | Across 32,754 statements |

## 7. Key Findings

1. **Hidden 0% test files**: Direct test files exist for `search_analytics` and `graph_visualization`, but coverage shows 0% / 18% respectively — strong indicator that recent test-collection failures are masking real regressions.
2. **Orphan-data domain is the largest blind spot**: `orphan_service.py` (485 LOC, 0%) + `normalizer_v2.py` (429 LOC, 0%) account for ~914 LOC of completely untested critical-path code introduced in recent phases.
3. **No test exists exclusively for `neo4j_service`** — the data layer everything depends on. It's only exercised indirectly through 3 other test files, all of which mock it.
4. **`test_gzip_compression.py` blocks full-suite CI** — a one-character fix that should be applied immediately.
5. **Test-infrastructure drift**: `pytest.ini` markers don't match `conftest.py` registrations; `.coveragerc` is empty; async mode not configured. Consolidation needed.

Word count: ~1,720.
