# Neo4j Service Refactor Proposal

**Date:** 2026-05-20
**Author:** architect@basset-hound:neo4j-refactor
**Target file:** `api/services/neo4j_service.py` (2,301 lines)
**Status:** Blueprint only — no code changes

## 1. Problem Statement

`AsyncNeo4jService` is a 2,301-line god class spanning eight concerns: driver lifecycle, retry/circuit breaker, query metrics, schema/index management, project CRUD, person CRUD, file management, JSON import/export, datetime/slug utilities, and platform-entity CRUD (Phase 48). The class is consumed by ~25 modules across `api/services/`, `api/routers/`, `basset_mcp/tools/`, and tests — almost all via `async with AsyncNeo4jService(): ...`. Splitting must preserve this surface exactly.

## 2. Current Method Map

| Method / Symbol | Lines | Concern | Proposed new file |
|---|---|---|---|
| `CircuitBreaker` class | 33–115 | reliability | `neo4j/circuit_breaker.py` |
| `timing_decorator` | 127–198 | metrics | `neo4j/metrics.py` |
| `_record_query_metric` | 201–237 | metrics (CSV writer) | `neo4j/metrics.py` |
| `Neo4jConnectionError`, `Neo4jQueryError` | 240–247 | exceptions | `neo4j/exceptions.py` |
| `AsyncNeo4jService.__init__` | 271–317 | lifecycle/config | `neo4j/driver.py` |
| `__aenter__` / `__aexit__` | 319–326 | lifecycle | `neo4j/driver.py` |
| `connect` | 328–393 | lifecycle + retry | `neo4j/driver.py` |
| `close` | 395–400 | lifecycle | `neo4j/driver.py` |
| `is_connected` (property) | 402–405 | lifecycle | `neo4j/driver.py` |
| `session` (async ctx mgr) | 407–428 | lifecycle | `neo4j/driver.py` |
| `_execute_query` | 430–496 | lifecycle + circuit breaker | `neo4j/driver.py` |
| `ensure_constraints` | 500–529 | schema | `neo4j/schema.py` |
| `setup_indexes` | 531–639 | schema | `neo4j/schema.py` |
| `get_query_profiling_info` | 641–682 | diagnostics | `neo4j/diagnostics.py` |
| `setup_schema_from_config` | 684–769 | schema | `neo4j/schema.py` |
| `create_project` | 773–811 | project CRUD | `neo4j/repositories/projects.py` |
| `get_project` | 813–838 | project CRUD | `neo4j/repositories/projects.py` |
| `get_all_projects` | 840–866 | project CRUD | `neo4j/repositories/projects.py` |
| `update_project` | 868–898 | project CRUD | `neo4j/repositories/projects.py` |
| `delete_project` | 901–928 | project CRUD | `neo4j/repositories/projects.py` |
| `create_person` | 932–995 | person CRUD | `neo4j/repositories/people.py` |
| `get_person` | 997–1079 | person CRUD | `neo4j/repositories/people.py` |
| `get_all_people` | 1081–1173 | person CRUD (read aggregate) | `neo4j/repositories/people.py` |
| `update_person` | 1175–1212 | person CRUD | `neo4j/repositories/people.py` |
| `set_person_field` | 1214–1278 | person fields | `neo4j/repositories/people.py` |
| `set_person_fields_batch` | 1280–1359 | person fields (batched) | `neo4j/repositories/people.py` |
| `handle_file_uploads_batch` | 1361–1427 | files (batched) | `neo4j/repositories/files.py` |
| `delete_person` | 1429–1463 | person CRUD | `neo4j/repositories/people.py` |
| `handle_file_upload` | 1467–1520 | files | `neo4j/repositories/files.py` |
| `get_file` | 1522–1540 | files | `neo4j/repositories/files.py` |
| `delete_file` | 1542–1560 | files | `neo4j/repositories/files.py` |
| `add_report_to_person` | 1564–1584 | reports | `neo4j/repositories/reports.py` |
| `remove_report_from_person` | 1586–1607 | reports | `neo4j/repositories/reports.py` |
| `import_from_json` | 1611–1637 | import/export | `neo4j/repositories/import_export.py` |
| `create_people_batch` | 1639–1701 | bulk import | `neo4j/repositories/import_export.py` |
| `export_to_json` | 1703–1713 | import/export | `neo4j/repositories/import_export.py` |
| `convert_neo4j_datetime` (static) | 1717–1734 | util | `neo4j/utils.py` |
| `convert_datetime_fields` (static) | 1736–1759 | util | `neo4j/utils.py` |
| `clean_data` (static) | 1761–1785 | util | `neo4j/utils.py` |
| `slugify` (static) | 1787–1799 | util | `neo4j/utils.py` |
| `ensure_platforms_seeded` | 1805–1865 | platform entity (Phase 48) | `neo4j/repositories/platforms.py` |
| `_get_major_platforms` (static) | 1867–1990 | platform seed data | `neo4j/repositories/platforms.py` |
| `list_platforms` | 1992–2015 | platform CRUD | `neo4j/repositories/platforms.py` |
| `get_platform` | 2017–2033 | platform CRUD | `neo4j/repositories/platforms.py` |
| `create_platform` | 2035–2068 | platform CRUD | `neo4j/repositories/platforms.py` |
| `update_platform` | 2070–2098 | platform CRUD | `neo4j/repositories/platforms.py` |
| `delete_platform` | 2100–2126 | platform CRUD | `neo4j/repositories/platforms.py` |
| `link_entity_to_platform` | 2128–2166 | account/relationship | `neo4j/repositories/accounts.py` |
| `get_accounts_for_entity` | 2168–2195 | account read | `neo4j/repositories/accounts.py` |
| `get_entities_on_platform` | 2197–2230 | account read | `neo4j/repositories/accounts.py` |
| `update_account_on_platform` | 2232–2270 | account update | `neo4j/repositories/accounts.py` |
| `remove_account_from_platform` | 2272–2301 | account delete | `neo4j/repositories/accounts.py` |

## 3. Target Module Layout

Proposed package `api/services/neo4j/` (sibling to existing `neo4j_service.py` during transition):

- `__init__.py` — re-exports `AsyncNeo4jService`, exceptions, decorators
- `exceptions.py` — `Neo4jConnectionError`, `Neo4jQueryError`
- `circuit_breaker.py` — `CircuitBreaker` (driver-agnostic reliability primitive)
- `metrics.py` — `timing_decorator`, `_record_query_metric`, CSV path constant
- `utils.py` — `convert_neo4j_datetime`, `convert_datetime_fields`, `clean_data`, `slugify` (pure functions, no driver dep)
- `driver.py` — `Neo4jDriver` class: pool config, `connect`, `close`, `session`, `_execute_query`, circuit breaker holder. This is the only module that owns the `AsyncGraphDatabase` driver handle.
- `schema.py` — `SchemaManager(driver)`: `ensure_constraints`, `setup_indexes`, `setup_schema_from_config`
- `diagnostics.py` — `Diagnostics(driver)`: `get_query_profiling_info`
- `repositories/__init__.py`
- `repositories/projects.py` — `ProjectRepository(driver)`
- `repositories/people.py` — `PersonRepository(driver, file_repo)` (depends on FileRepository for embedded uploads)
- `repositories/files.py` — `FileRepository(driver)`
- `repositories/reports.py` — `ReportRepository(driver)`
- `repositories/import_export.py` — `ImportExportRepository(project_repo, person_repo)`
- `repositories/platforms.py` — `PlatformRepository(driver)` (Phase 48)
- `repositories/accounts.py` — `AccountRepository(driver)` (Phase 48 — HAS_ACCOUNT_ON edges)
- `facade.py` — `AsyncNeo4jService` thin composition: instantiates the driver and all repositories, delegates every public method via simple forwarding. Implements `__aenter__`/`__aexit__`.

`api/services/neo4j_service.py` becomes a 5-line re-export shim:

```python
from api.services.neo4j.facade import AsyncNeo4jService
from api.services.neo4j.exceptions import Neo4jConnectionError, Neo4jQueryError
from api.services.neo4j.metrics import timing_decorator
__all__ = ["AsyncNeo4jService", "Neo4jConnectionError", "Neo4jQueryError", "timing_decorator"]
```

## 4. Public API & Backward-Compat Surface

Consumers that **must keep working without edits**:

- `api/main.py` — calls `AsyncNeo4jService()`, `connect()`, `setup_indexes()`, `ensure_platforms_seeded()`, `close()`
- `api/services/__init__.py` — re-exports `AsyncNeo4jService` (line 8, 265)
- `api/services/plugin_service.py`, `data_service.py`, `platform_service.py`, `suggestion_service.py`, `matching_engine.py`, `ml_analytics_service.py`, `collaboration_service.py`, `linking_service.py` — all type-hint and inject `AsyncNeo4jService`
- `api/routers/suggestions.py` (12 call sites), `platforms.py`, `accounts.py`, `plugins.py`
- `basset_mcp/tools/data_management.py`, `linking.py`, `suggestions.py` — 25+ `async with AsyncNeo4jService()` blocks
- `tests/test_platform_entities.py`, `test_performance.py`, `test_data_management.py` — direct construction

**Critical observation:** `api/dependencies.py:get_neo4j_handler` returns the legacy sync `Neo4jHandler`, *not* the async service. There is no DI factory for `AsyncNeo4jService`; consumers self-construct. The refactor inherits this pattern (no DI changes required).

Static methods consumed externally: `AsyncNeo4jService.convert_datetime_fields`, `AsyncNeo4jService.convert_neo4j_datetime`, `AsyncNeo4jService.clean_data`, `AsyncNeo4jService.slugify`. The facade must keep these as `@staticmethod` forwards to `neo4j.utils`.

## 5. Migration Plan (Phases)

Each phase ends with `pytest` green and no behavior change.

**Phase A — Extract leaves (no class changes).** Move `CircuitBreaker`, `timing_decorator`, `_record_query_metric`, `QUERY_METRICS_CSV`, both exception classes, and the four `@staticmethod` utility functions to new modules. Re-import them at the top of `neo4j_service.py`. Risk: low. Verifies module wiring.

**Phase B — Extract driver shell.** Create `neo4j/driver.py` with a `Neo4jDriver` class containing `__init__` pool config, `connect`, `close`, `session`, `is_connected`, `_execute_query`, and the circuit-breaker instance. Inside `AsyncNeo4jService`, hold `self._driver_obj = Neo4jDriver(...)` and delegate every existing attribute (`self._driver`, `self._connected`, `self.session`, `self._execute_query`) via `@property` and method forwards. This phase keeps the god class intact but with its lifecycle logic externalized.

**Phase C — Extract schema & diagnostics.** Move `ensure_constraints`, `setup_indexes`, `setup_schema_from_config`, `get_query_profiling_info` into `schema.py` / `diagnostics.py`. Class methods on `AsyncNeo4jService` become one-line delegations: `return await self._schema.ensure_constraints()`. Note: `connect()` calls `ensure_constraints()` at line 379 — this internal call must continue working.

**Phase D — Extract repositories one cluster at a time.** Order, smallest blast radius first:
1. `files.py` (`handle_file_upload`, `handle_file_uploads_batch`, `get_file`, `delete_file`)
2. `reports.py` (`add_report_to_person`, `remove_report_from_person`)
3. `projects.py` (5 methods)
4. `people.py` (7 methods — depends on `files.py` for embedded uploads in `set_person_field` / `set_person_fields_batch`)
5. `accounts.py` (5 methods)
6. `platforms.py` (5 methods + seed data)
7. `import_export.py` (3 methods — depends on `projects.py` + `people.py`)

After each step the public method on `AsyncNeo4jService` becomes `return await self._<repo>.<method>(...)`. Static utility callers (`self.slugify`, `self.clean_data`, `self.convert_datetime_fields`) stay as static method forwards.

**Phase E — Final facade.** Once every method body is a one-line delegate, move the class itself to `neo4j/facade.py`. Replace `neo4j_service.py` with the 5-line re-export shim. The file path stays valid; every existing import keeps working.

**Phase F — Optional follow-up (not part of refactor).** Introduce a `get_neo4j_service()` async factory + FastAPI `Depends` so the MCP tools and routers can stop self-constructing and reuse a process-wide pool. Out of scope for the mechanical split.

## 6. Backward-Compatible Facade Strategy

Three invariants:

1. **Module path:** `api.services.neo4j_service` must remain importable and continue exposing `AsyncNeo4jService`, `Neo4jConnectionError`, `Neo4jQueryError`, and `timing_decorator`. Achieved via re-export shim.
2. **Constructor signature:** `AsyncNeo4jService(uri=None, user=None, password=None, max_connection_lifetime=None, max_connection_pool_size=None, connection_acquisition_timeout=None)` is reproduced verbatim by the facade.
3. **Static-method access:** `AsyncNeo4jService.slugify("...")` style calls (used internally and possibly externally) preserved by re-attaching the utils as `@staticmethod` on the facade.

The facade keeps the `_driver`, `_connected`, `_circuit_breaker`, and `session()` accessors public — some consumers (e.g. `data_service.py`) reach into these. Grep `\._driver|\.session\(` across consumers before each phase to confirm.

## 7. Test Impact Assessment

- **`tests/test_platform_entities.py`** — constructs `AsyncNeo4jService(uri=..., user=..., password=...)`. Unchanged after refactor.
- **`tests/test_performance.py`, `tests/test_data_management.py`** — same.
- **`tests/test_suggestion_api.py:33`** — `patch("api.routers.suggestions.AsyncNeo4jService")`. This patches the *import alias* in the router; still works because the router still imports the name from `neo4j_service`. Verify after Phase E.
- **`tests/test_*` files patching `get_neo4j_handler`** — unaffected (different code path, sync handler).
- **No tests appear to mock individual methods on the service**, so internal restructuring is safe.

New tests to add per phase: small unit tests around the extracted leaf modules (`CircuitBreaker`, `clean_data`, `slugify`, `convert_datetime_fields`) which currently have no dedicated coverage.

## 8. Risk Register

**R1 — Async lifecycle on the driver handle.** The `_driver` and `_connected` attributes are read by `_execute_query`, `session`, and `is_connected`. If `Neo4jDriver` holds the actual handle and the facade caches a stale reference, callers like `data_service.py` that read `service._driver` directly will break. Mitigation: expose `_driver` as `@property` on the facade returning the inner driver's handle.

**R2 — Circuit breaker shared state.** Currently one breaker per service instance. Multiple consumers (`AsyncNeo4jService()` constructed 50+ places) means many independent breakers. The refactor must preserve this (do not promote to module-global) to avoid behavior change.

**R3 — `connect()` side-effect.** `connect()` calls `ensure_constraints()` (line 379). After Phase C, this becomes a cross-module call (`driver.connect()` invoking `schema.ensure_constraints(driver)`). Risk of circular import. Mitigation: schema module imports driver type only under `TYPE_CHECKING`; connect() invokes schema via injected callback or post-connect hook.

**R4 — Static methods used inside instance methods.** Many methods call `self.clean_data(...)`, `self.slugify(...)`, `self.convert_datetime_fields(...)`. After repository extraction, the repos need access to these. Either import the utils functions directly (preferred) or re-attach them as static methods on the repo classes. Mitigation: standardize on `from api.services.neo4j.utils import clean_data, slugify, convert_datetime_fields` inside every repo.

**R5 — `set_person_field` / `set_person_fields_batch` cross-repo coupling.** Both call `handle_file_upload` / `handle_file_uploads_batch`. After extraction, `PersonRepository` must hold a `FileRepository` reference. Constructor ordering matters in the facade.

**R6 — `import_from_json` / `create_people_batch` cross-repo.** They call `create_project`, `get_project`, `set_person_fields_batch`. `ImportExportRepository` becomes a higher-level orchestrator that takes both `ProjectRepository` and `PersonRepository` as collaborators.

**R7 — MCP tools self-construct.** 25+ `async with AsyncNeo4jService()` sites in `basset_mcp/`. Each creates a fresh driver pool (already a known wart, see Phase 8 load-test notes). The refactor does not fix this — explicitly out of scope to avoid coupling refactor to runtime behavior changes.

**R8 — Test patches use full dotted path.** `patch("api.routers.suggestions.AsyncNeo4jService")` works because the router does `from api.services.neo4j_service import AsyncNeo4jService`. As long as the shim re-exports the name, patches survive.

**R9 — Performance regression from method indirection.** Each call now traverses facade → repo → driver. Python attribute lookup is cheap (~50ns) and our queries are 1–100ms — negligible. No expected impact on the <100ms p99 target.

**R10 — Concurrent migration.** Two other agents are touching docs and `git diff` review. No conflict on `api/services/neo4j_service.py` because this proposal is docs-only.

## 9. Unknowns / Open Questions

- Is there an undocumented consumer (e.g. a notebook, deployment script) that imports private attributes (`_circuit_breaker`, `_max_connection_pool_size`)? Grep before Phase B.
- Should `QUERY_METRICS_CSV` move to a config setting? Currently a hard-coded path at `Path(__file__).parent.parent.parent / "query_metrics.csv"`. Out of scope but worth flagging.
- The two-logger-import pattern inside `ensure_platforms_seeded` (lines 1823–1825, 1858–1859, 1862–1863) is a smell — should consolidate to module-level. Trivial fix during Phase D.

## 10. Estimated Effort

- Phase A: 1 hour (mechanical moves + import fixes)
- Phase B: 2 hours (driver extraction, attribute proxying)
- Phase C: 1.5 hours (schema/diagnostics, address R3)
- Phase D: 4–6 hours total (7 repositories, ~30–60 min each)
- Phase E: 30 min (final shim + facade move)
- Phase F: deferred

Total: ~10 hours of focused work, fully test-gated, no behavior change, fully reversible per phase.
