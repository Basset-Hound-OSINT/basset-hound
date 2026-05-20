# Wave 5 — Router Cleanup Progress

**Date:** 2026-05-20
**Agent:** py-dev@basset-hound:orphan-router-cleanup
**Scope:** `api/routers/{cache,orphan,analytics,schedule}.py` per Stream 5 audit
(`docs/findings/2026-05-20-router-surface-audit.md`)

## Per-file outcome

| File | Action | LOC removed | Endpoints removed | Rationale |
|---|---|---|---|---|
| `api/routers/cache.py` | **DELETED** | 228 | 9 | Zero importers anywhere in repo (verified with `grep -rn` for `from .cache import`, `routers.cache`, and `cache_router`). Not referenced in `api/routers/__init__.py` or `api/main.py`. |
| `api/routers/orphan.py` | **DELETED** | 1163 | 11 | Zero importers anywhere in repo. Not referenced in `__init__.py` or `main.py`. Orphan-domain feature was never wired up. |
| `api/routers/schedule.py` | **DELETED** | 106 | 0 (shim) | Zero Python importers. Phase 13 migration already moved test imports off `routers.schedule` to `routers.scheduler` (per `docs/findings/13-PHASE13-INFRASTRUCTURE.md`). Only doc references remain. |
| `api/routers/analytics.py` | **KEPT** | 0 | 0 (shim) | **Live importer found**: `tests/test_search_analytics.py` lines 1008 and 1017 import `router`, `project_analytics_router`, and response models from `api.routers.analytics` to verify the deprecation shim still works. Task instructions require flagging rather than deleting when an importer exists outside `__init__.py` dead code. Recommend updating those two test imports to `api.routers.analytics_v2` in a future pass, then removing the shim. |

**Totals deleted:** 1,497 LOC, 20 endpoints (9 reachable + 11 unreachable in `orphan.py`).

## `api/routers/__init__.py` changes

None required. Audit confirmed the file already does not import from `cache`, `orphan`, `schedule`, or `analytics`. Only a single comment at line 61 referenced `schedule.py`; left in place as it documents that `scheduler` (not `schedule`) is canonical.

## Verification

```
$ python3 -c "import api.routers"
# IMPORT OK — api_router has 405 routes registered (unchanged)

$ python3 -m pytest --collect-only 2>&1 | tail -5
# 3041 tests collected in 6.72s — no collection errors
```

No import errors observed. Pre-existing `bcrypt`/`jellyfish` warnings unrelated.

## Flagged follow-up

`tests/test_search_analytics.py::TestAnalyticsRouter::test_router_import` and
`::test_response_models_import` still import from the deprecated
`api.routers.analytics` shim. Once those two tests are migrated to
`api.routers.analytics_v2`, `analytics.py` (67 LOC, 0 endpoints) can be safely
removed. This agent could not edit tests per the BLOCKED constraint.
