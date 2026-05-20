# Wave 6: Analytics Shim Removal (2026-05-20)

**Agent:** py-dev@basset-hound:analytics-shim-removal

## Summary

Removed the deprecated `api/routers/analytics.py` re-export shim. The shim
existed only for backward compatibility and was blocked from deletion in
Stream 11 by two import sites in `tests/test_search_analytics.py`. Those
imports were migrated to `api.routers.analytics_v2` directly.

## Symbols Migrated

All symbols below previously imported via the deprecated shim. Each was
verified to exist in `analytics_v2.py` before migration.

| Symbol                    | New Source                  | Notes                          |
|---------------------------|-----------------------------|--------------------------------|
| `router`                  | `api.routers.analytics_v2`  | Same name                      |
| `project_analytics_router`| `api.routers.analytics_v2`  | Imported as `project_router as project_analytics_router` |
| `RecordSearchRequest`     | `api.routers.analytics_v2`  | Pydantic model                 |
| `RecordSearchResponse`    | `api.routers.analytics_v2`  | Pydantic model                 |
| `QueryStatsResponse`      | `api.routers.analytics_v2`  | Pydantic model                 |
| `TopQueriesResponse`      | `api.routers.analytics_v2`  | Pydantic model                 |
| `SuggestionsResponse`     | `api.routers.analytics_v2`  | Pydantic model                 |
| `ClearAnalyticsResponse`  | `api.routers.analytics_v2`  | Pydantic model                 |
| `AnalyticsSummaryResponse`| `api.routers.analytics_v2`  | Pydantic model                 |

The `warnings.catch_warnings()` wrappers in the two test methods were
also dropped — they only existed to silence the now-gone
`DeprecationWarning`.

## Files Changed

- **Modified:** `tests/test_search_analytics.py` (test_router_import,
  test_response_models_import in `TestAnalyticsRouter`)
- **Deleted:** `api/routers/analytics.py` (67-line shim)

## Validation

- `pytest tests/test_search_analytics.py --collect-only`: 71 tests collected
- `python3 -c "import api.routers"`: OK, 405 routes
- Full `pytest --collect-only`: **3041 tests collected** (matches baseline)
- Repo-wide grep confirmed no remaining `from api.routers.analytics import`
  consumers; `api/routers/__init__.py` already used `analytics_v2` directly.
