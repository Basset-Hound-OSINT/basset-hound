# Wave 5 — Frontend Dead-Asset Cleanup

**Date:** 2026-05-20
**Agent:** analyst@basset-hound:frontend-dead-asset-cleanup
**Source audit:** `docs/findings/2026-05-20-frontend-static-audit.md`
**Scope:** delete confirmed-orphan static assets; do NOT touch `*.html`, `*.py`, or `scripts/minify-js.js`.

## Pre-delete verification

Ran `grep -rn` against `templates/` and `static/` (`*.html`, `*.js`) for every candidate. **Zero references** for all of them. Cross-checked `api/` and `*.py` as well — also zero.

```
grep -rn "/static/js/dist"  templates/ static/   →  0 matches
grep -rn "cache-dashboard-usage"   ...           →  0 matches
grep -rn "Test_Project"            ...           →  0 matches
grep -rn "CACHE_DASHBOARD_README|plugins/README" →  0 matches
```

## Per-item disposition

| Item | Action | Size | Reason |
|---|---|---:|---|
| `static/js/dist/` (22 files) | DELETED | 258,287 B | Broken regex-minifier output (URL/identifier corruption per audit §5); zero template refs. |
| `static/js/examples/cache-dashboard-usage.js` | DELETED | 11,796 B | Orphan demo; no loader. |
| `static/js/examples/` (empty parent dir) | DELETED | — | Emptied after file removal. |
| `static/downloads/Test_Project.json` | DELETED | 151 B | Test fixture under publicly served tree; no refs. |
| `static/downloads/` (empty parent dir) | DELETED | — | Emptied after file removal. |
| `static/js/CACHE_DASHBOARD_README.md` | DELETED | 7,491 B | Doc inside JS tree; belongs in `docs/`. |
| `static/plugins/README.md` | DELETED | 10,587 B | Doc in served static tree; not loaded by `plugin-manager.js`. |
| `frontend/dist/` | N/A | — | Does not exist on disk. `.gitignore:12` already covers `dist/`. No action. |

**Total bytes freed: 288,312 B (~282 KB)**

(Note: examples/ + downloads/ contained 15,892 B + 151 B file payloads; the directory entries themselves are negligible. dist/ accounted for 258 KB of the savings.)

## Console-log census (out of scope to remove; counted only)

`grep -cE "console\.(log|debug|info)"` across remaining `static/js/*.js` — **27 total occurrences** in active top-level modules. Top 5:

| File | Count |
|---|---:|
| `static/js/collaboration-manager.js` | 7 |
| `static/js/dashboard.js` | 5 |
| `static/js/tag-handler.js` | 3 |
| `static/js/plugin-manager.js` | 3 |
| `static/js/advanced-search.js` | 3 |

Stream 8 audit reported ~115 globally — that figure includes `dist/` duplicates (now gone) and subdirectories (`suggestions/`, `components/`, `plugins/`). The top-level shipped surface is 27. Recommend gating behind `window.__DEBUG__` in a future stream.

## References that blocked a delete

None. Every candidate had zero hits.

## Template shipped-JS verification

`templates/dashboard.html` lines 105–179 still load originals only (`/static/js/dashboard.js`, `api.js`, `ui-form-handlers.js`, `ui-people-list.js`, `ui-person-details.js`, `utils.js`, `tag-handler.js`, `report-handler.js`, `metrics-dashboard.js`, `components/basset-hound-ui.umd.js`, `suggestions/suggestions-init.js`, `file_explorer.js`). All 12 paths exist post-delete. `templates/index.html` loads only the Bootstrap CDN bundle. No template references the removed paths.

## Out-of-scope deferrals (per task brief)

- `scripts/minify-js.js` (broken minifier) — left intact.
- `static/js/components/basset-hound-ui.es.js` (unreferenced ESM build) — out of WRITE zone (`components/` not in allowlist); deferred.
- Console-log stripping — deferred.
