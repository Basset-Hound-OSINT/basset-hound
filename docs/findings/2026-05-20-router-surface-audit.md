# Router Surface Audit
**Date:** 2026-05-20
**Scope:** `/home/devel/basset-hound/api/routers/**` + mount points in `api/main.py`, `api/routers/__init__.py`
**Total router files:** 59 (`__init__.py` + 58 `.py` modules)

## 1. Endpoint Totals

| Category | Count | Notes |
|---|---|---|
| Total endpoint decorators across all router files | ~436 | Counted via `@router.<verb>(` regex across all 58 modules |
| Mounted endpoint count (excludes `cache.py`, `orphan.py`, `analytics.py`, `schedule.py`) | ~414 | Orphan files contribute 20 endpoints that are loaded but never reachable |
| Explicitly public (no auth needed) | 5 | `GET /health`, `GET /metrics`, `GET /api`, `GET /api/info`, `POST /api/v1/auth/login` (+ `/refresh`, `/validate`) |
| Authenticated (uses `get_current_user`/`CurrentUser`) | ~22 | `collaboration` (15), `ml_analytics` (6), `export.py` (1, partial), `auth.py /me` |
| Effectively unauthenticated protected endpoints | ~407 | All other routers (projects, entities, relationships, files, reports, search, …) — see Section 5 |
| Admin-tagged | 6 | `scheduler.admin_router` only |

**Critical finding:** The codebase has a JWT auth system (`api/auth/`, `api/dependencies.py:get_current_user`) but **only 5 of 58 router modules actually wire it up**. The remaining ~407 endpoints accept anonymous traffic. See Section 5.

## 2. Per-Router Summary

Legend: M = mounted via `api/routers/__init__.py` (under `/api/v1`); SM = standalone-mounted in `api/main.py`; O = orphan (never imported).

| File | Mounted | Prefix (relative to `/api/v1` unless SM) | Endpoints | Auth | Notes |
|---|---|---|---|---|---|
| accounts.py | M | `/projects/{project_safe_name}/entities/{entity_id}/accounts` | 4 | (mixed; see below) | Phase 48 platform accounts |
| analysis.py | M | `/analysis/{project_safe_name}` | 6 | none | Graph analysis (paths, centrality) |
| analytics.py | not imported | – | 0 | – | **Deprecated re-export** of analytics_v2; emits `DeprecationWarning` |
| analytics_v2.py | M | `/analytics` + `project_router` | 13 | none | Primary analytics router |
| audit.py | M | `/audit` + project + entity routers | 5 | none | Change tracking |
| auth.py | M | `/auth` | 4 | self-auth | `/login`, `/refresh`, `/validate`, `/me` |
| auto_linker.py | M | `/projects/{project_safe_name}/auto-link` | 8 | none | |
| browser_actions.py | M | `/browser` | 8 | none | Headless browser ops — sensitive |
| bulk.py | M | `/projects/{project_safe_name}/bulk` | 5 | none | |
| cache.py | **NOT imported** | `/cache` | 9 | none | **Orphan file** — see Section 4 |
| cletus_integration.py | M | `/api/v1/cletus` (literal, double-prefix risk) | 7 | none | Prefix includes `/api/v1` AND mounted at `/api/v1` → endpoints land at `/api/v1/api/v1/cletus/*` |
| collaboration.py | M | `/collaboration` | 15 | **yes (all)** | Only fully-authenticated router |
| config.py | M | `/config` | 8 | none | |
| cross_project.py | M | `/cross-project` + `entity_router` | 5 | none | |
| crypto.py | M | `/crypto` | 5 | none | |
| data_quality.py | M | `/data-quality` + project router | 11 | none | |
| deduplication.py | M | `/deduplication` + project router | 12 | none | |
| entities.py | M | `/projects/{project_safe_name}/entities` | 7 | none | Core CRUD |
| entity_types.py | M | `/entity-types` + project router | 8 | none | |
| export.py | M | `/projects/{project_safe_name}/export` + entity + templates | 10 | **partial** (only `/templates/`-suffixed endpoint uses `get_current_user`) |
| files.py | M (+ SM) | `/projects/.../files` + `file_serve_router` | 5 | none | |
| frontend.py | SM | (no prefix — root paths `/`, `/dashboard`, `/new_project`, `/get_projects`, `/get_config`, `/save_config`, `/tag_person/{id}`) | 11 | none | Flask-migrated HTML routes |
| frontend_components.py | M | `/frontend` | 7 | none | |
| frontend_profiles.py | SM | (no prefix — `/get_people`, `/add_person`, `/update_person/{id}`, etc.) | 9 | none | Flask-migrated |
| frontend_reports.py | SM | (no prefix — `/person/{id}/reports*`) | 5 | none | Flask-migrated |
| graph.py | M | `/projects/{project_safe_name}/graph` | 3 | none | |
| graph_analytics.py | M | `/analytics/{project}` | 10 | none | **Prefix collides with analytics_v2** — see Section 3 |
| graph_format.py | M | `""` (empty prefix) | 6 | none | Mounts at `/api/v1` root — pollutes namespace |
| import_data.py | M | `/projects/{project_safe_name}/import` + `formats_router` | 8 | none | |
| import_mapping.py | M | (no prefix) | 8 | none | Endpoints land at `/api/v1` root |
| integrations.py | M | `/integrations` | 9 | none | |
| jobs.py | M | `/jobs` + `schedule_jobs_router` | 9 | none | |
| llm_export.py | M | (no prefix) | 6 | none | Endpoints land at `/api/v1` root |
| marketplace.py | M | `/marketplace` | 14 | none | |
| mcp.py | SM (mounted directly at `/mcp`) | `/mcp` (literal) | 6 | none | Mounted twice? See Section 4 |
| ml_analytics.py | M | `/ml-analytics` | 6 | **yes (all)** | Uses `CurrentUser` from `api.auth.dependencies` |
| orphan.py | **NOT imported** | `/projects/{project_id}/orphans` + global router | 11 | none | **Orphan file** — see Section 4 |
| osint.py | M | `/osint` | 5 | none | |
| platforms.py | M | `/platforms` | 5 | none | |
| plugins.py | M | `/plugins` | 9 | none | Plugin install/run — sensitive |
| projects.py | M | `/projects` | 7 | none | |
| relationships.py | M (+ SM) | `/projects/.../entities/{id}/relationships` + `project_relationships_router` | 10 | none | |
| reports.py | M (+ SM) | `/projects/.../reports` + `report_serve_router` | 11 | none | |
| reports_pdf.py | SM | `/api/v1/projects` (literal — also self-prefixed) | 4 | none | |
| report_storage.py | M | `/reports/stored` | 12 | none | |
| saved_search.py | M | `/saved-searches` + project router | 17 | none | Largest router |
| schedule.py | not imported | – | 0 | – | **Deprecated re-export** of scheduler |
| scheduler.py | M | (no prefix on `router`; `project_router`, `admin_router`) | 8 | none | |
| search.py | M | `/search` + `project_search_router` | 9 | none | |
| suggestions.py | M | `/suggestions` | 12 | none | |
| templates.py | M | `/templates` | 11 | none | Collides with `export.templates_router`? See Section 3 |
| timeline.py | M | `/projects/{project_id}` | 5 | none | Prefix differs from sibling routers (`project_id` vs `project_safe_name`) |
| timeline_visualization.py | M | `/timeline-viz/{project_safe_name}` | 6 | none | |
| utils.py | M | `/utils` | 6 | none | |
| verification.py | M | `/verify` | 10 | none | |
| visualization.py | M | `/projects/{project_safe_name}/visualization` | 6 | none | |
| webhooks.py | M | `/webhooks` + project router | 13 | none | |
| websocket.py | M | `/ws` | 5 | none | Plus 2 duplicate `/ws/*` in `main.py` (see Section 3) |

## 3. Suspected Duplicate / Overlapping Pairs

| Pair | Notes / Likely Resolution |
|---|---|
| `analytics.py` ↔ `analytics_v2.py` | `analytics.py` self-declares `DEPRECATED` and re-exports from `analytics_v2`. **It is never imported in `__init__.py` or `main.py`** — safe to delete. |
| `schedule.py` ↔ `scheduler.py` | Same story: `schedule.py` is a self-declared deprecated re-export shim. Not imported anywhere. Safe to delete. |
| `analytics_v2.py` (`prefix=/analytics`) ↔ `graph_analytics.py` (`prefix=/analytics/{project}`) | Both mount under `/analytics`. `graph_analytics` shadows `/analytics/{project}` which may collide with analytics_v2 dynamic routes if any. Confirm no path overlap; consider renaming `graph_analytics` to `/graph-analytics/{project}`. |
| `templates.py` (`prefix=/templates`) ↔ `export.py templates_router` | Both serve `/templates`. `export.templates_router` is `/projects/{project_safe_name}/export/templates` (because mounted under `export_router`), but the re-export from `__init__.py` includes it as `export_templates_router`. Verify they don't both expose `GET /templates/{id}`. |
| `reports.py` ↔ `reports_pdf.py` ↔ `report_storage.py` ↔ `frontend_reports.py` | Four routers in the same domain. `reports_pdf.py` self-prefixes `/api/v1/projects` AND is mounted on `app` directly (not under `/api/v1`), so paths land at `/api/v1/projects/...` correctly — but if anyone re-mounts it under `/api/v1` later, it will double-prefix. |
| `frontend.py` ↔ `frontend_components.py` ↔ `frontend_profiles.py` ↔ `frontend_reports.py` | Four flat-rooted routers — `frontend_components` lives under `/api/v1/frontend`, while `frontend.py`, `frontend_profiles.py`, `frontend_reports.py` are mounted on `app` at root with no prefix. `/get_projects`, `/get_people` etc. live at `app` root. |
| `websocket.py` (`/api/v1/ws/*`) ↔ inline endpoints in `main.py` (`/api/v1/ws/health`, `/api/v1/ws/connections`) | `main.py` defines `GET /api/v1/ws/health` and `GET /api/v1/ws/connections` directly (lines 560, 611) while `websocket.py` also defines `/ws/stats`, `/ws/connections`, etc. **`/api/v1/ws/connections` is defined in both** — FastAPI will use whichever was registered first; the `main.py` definitions register before `app.include_router(api_router, …)` callback executes. Confirm and consolidate. |
| `mcp.py` mounted in TWO places | `main.py` line 665 mounts `mcp_router` directly; `__init__.py` does **not** include it in `api_router` (verified). OK, but the line `from .mcp import router as mcp_router` in `__init__.py` line 88 imports it but never includes — dead import. |
| `cletus_integration.py` literal prefix `/api/v1/cletus` mounted **under** `/api/v1` | Result: routes land at `/api/v1/api/v1/cletus/*`. Almost certainly a bug. |
| `timeline.py` uses `{project_id}` while every other project-scoped router uses `{project_safe_name}` | Inconsistent path param. May break shared middleware that resolves projects by `project_safe_name`. |

## 4. Orphan Router Files (Not Mounted)

Confirmed by `grep -r "routers.cache|routers.orphan"` returning zero importers within the API package.

| File | Endpoints | Why orphan? | Recommended action |
|---|---|---|---|
| `api/routers/cache.py` | 9 (`GET /cache/stats`, `/health`, `POST /cache/clear`, `/clear/project/{id}`, `/clear/entity/{id}`, `/clear/relationships`, `/clear/queries`, `GET /cache/info`, `POST /cache/warm`) | Not imported in `routers/__init__.py` or `main.py` | Mount it (cache mgmt is useful) **or** delete if `cache_service` already exposes these internally. |
| `api/routers/orphan.py` | 11 (`POST/GET/PUT/DELETE` on `/projects/{project_id}/orphans/*` + `/orphans/types`) | Not imported anywhere despite a fully-built domain | Decision needed: is orphan-data feature still in scope? If yes, mount. If no, delete (1,163 lines of dead code). |
| `api/routers/analytics.py` | 0 (re-export shim) | `__init__.py` line 59 explicitly says "analytics.py is deprecated and re-exports from analytics_v2" | Delete. |
| `api/routers/schedule.py` | 0 (re-export shim) | Same as above. Imports already point to `scheduler`. | Delete. |

## 5. Auth Gaps (Missing `Depends(get_current_user)` on Protected Routes)

The auth machinery exists in `api/auth/dependencies.py` (`CurrentUser`, `get_current_user`, `get_current_user_optional`, `get_current_user_or_api_key`) and `api/dependencies.py` (`get_current_user`, `require_auth`). Only the following routers actually consume it:

| Router | Coverage |
|---|---|
| `auth.py` | Self-auth (login/refresh/validate are public by design; `/me` uses dependency injection) |
| `collaboration.py` | All 15 endpoints require `CurrentUser` |
| `ml_analytics.py` | All 6 endpoints require `CurrentUser` |
| `export.py` | **Partial** — only the `POST /projects/{name}/export/templates/{template_id}` route uses `get_current_user`; the other 9 endpoints in this router are unauthenticated |
| `accounts.py` | Imports auth-related modules but `grep` shows no `Depends(get_current_user)` usage in endpoint signatures — needs manual confirmation |

**Routers handling sensitive operations that have ZERO auth dependencies and should be flagged:**

- `projects.py` — create/delete projects
- `entities.py` — create/delete people
- `relationships.py` / `project_relationships_router` — modify graph
- `files.py` / `file_serve_router` — upload/download arbitrary files (file serve is publicly readable)
- `reports.py` / `report_serve_router` / `reports_pdf.py` / `report_storage.py` — read/write/PDF-render investigation reports
- `bulk.py` — bulk import/delete
- `import_data.py` — import from external OSINT tools
- `import_mapping.py` — define import field mappings
- `browser_actions.py` — headless browser navigation, screenshots, script execution (severe)
- `plugins.py` — install/run plugins (severe)
- `osint.py` — outbound OSINT queries
- `webhooks.py` — create/delete webhooks (can be used for SSRF)
- `verification.py` — basset-verify integration
- `mcp.py` — MCP tool execute/batch (can invoke arbitrary tools)
- `integrations.py` — third-party integration credentials
- `cletus_integration.py` — event ingestion
- `frontend.py`, `frontend_profiles.py`, `frontend_reports.py` — full HTML CRUD for projects/people/reports, no auth at all
- `config.py` — read AND modify application config (`PUT /config/`)
- `cache.py` (if mounted) — cache invalidation
- `marketplace.py` — install community templates

**Recommendation:** Add a global dependency to `api_router` (e.g. `Depends(get_current_user_or_api_key)`) and explicitly opt routes out as public, rather than the current opt-in model. Five out of 58 modules using auth is a default-open posture.

## 6. Deprecated Endpoints

No endpoints carry the FastAPI `deprecated=True` flag. Only two **whole modules** carry `DEPRECATED` in their docstrings:

| Module | Status | Proposed Removal |
|---|---|---|
| `api/routers/analytics.py` | Re-export shim, not imported anywhere | Delete in next minor release (2026-06) |
| `api/routers/schedule.py` | Re-export shim, not imported anywhere | Delete in next minor release (2026-06) |

No callers were found inside the `api/` package or the broader repo's Python sources, so removal should be a no-op aside from any external import statements (verify with grep on `basset_mcp/`, `tests/`).

## 7. Suggested Cleanup Backlog

1. **Delete** `analytics.py` and `schedule.py` shim modules — they emit `DeprecationWarning` at import time but are not imported.
2. **Decide on** `cache.py` (mount or delete) and `orphan.py` (mount or delete). Each is hundreds of lines of unreachable code today.
3. **Fix** `cletus_integration.py` prefix — drop `/api/v1` from its `prefix=` since it's already mounted under `/api/v1`.
4. **Resolve** the WebSocket endpoint duplication between `main.py` inline endpoints and `websocket.py`.
5. **Standardize** project path param: `timeline.py` uses `{project_id}` while siblings use `{project_safe_name}`.
6. **Add** global auth dependency to `api_router` and explicitly mark `/auth/login`, `/health`, `/metrics`, `/api`, `/api/info` as public. The current default-open posture leaves ~407 endpoints unauthenticated.
7. **Remove** dead `from .mcp import router as mcp_router` in `__init__.py` (imported but not included).
8. **Clarify** `templates.py` vs `export.templates_router` ownership.
9. **Re-namespace** `graph_analytics.py` to avoid `/analytics/{project}` collision with `analytics_v2.py` `/analytics`.

## 8. Caveats

- Endpoint counts are decorator counts and may slightly overcount if a single function carries multiple decorators (none observed in spot checks).
- "Auth = none" means no `Depends(get_current_user|verify_token|require_auth|CurrentUser)` reference is present in the router file. Middleware-level enforcement was **not** audited here — a security reviewer is concurrently looking at `api/middleware/` and may report a global auth middleware that would change the picture. If such middleware exists and runs on `/api/v1/*`, much of Section 5 becomes moot; if not, Section 5 stands.
- `accounts.py` shows imports related to auth but no signature-level dependency. Manual review recommended.
