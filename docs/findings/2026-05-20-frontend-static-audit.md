# Frontend Static Asset & Bundle Audit

**Date:** 2026-05-20
**Scope:** `static/`, `frontend/src/`, `scripts/minify-js.js`
**Angle:** Bundle structure & asset organization (not CVE/dependency)
**Phase under review:** "FRONTEND-PHASE1-OPTIMIZATION" — claimed −520ms latency reduction

---

## 1. Executive Summary

Phase 1 docs claim a delivered −520ms / −36% transfer improvement. **Code reality:** three of five quick wins shipped, one is deferred, and the marquee "minification" win produces a **broken `static/js/dist/` tree** because the regex minifier corrupts URLs and hyphenated module specifiers. Templates still load originals, so production is unaffected — but the claimed −80ms / −33KB savings never shipped, and `dist/` is checked-in tech debt.

Three PNG logos (~4 MB combined) dominate the static payload. No asset hashing, no code splitting beyond manual `import()`, and no Vite output reaches the page outside the React suggestions widget.

---

## 2. Asset Inventory — Top 20 Largest Files

| # | Size (B) | Path | Category |
|---|---------:|------|----------|
| 1 | 1,525,572 | `static/imgs/basset_hound_logo_removebg.png` | Image |
| 2 | 1,261,061 | `static/imgs/basset_hound_osint_logo.png` | Image |
| 3 | 1,252,803 | `static/imgs/basset_hound_logo.png` | Image |
| 4 | 315,940 | `static/imgs/favicon_io/android-chrome-512x512.png` | Image |
| 5 | 60,420 | `static/js/components/basset-hound-ui.es.js` | Vite build (React lib) |
| 6 | 39,427 | `static/js/components/basset-hound-ui.umd.js` | Vite build (React lib) |
| 7 | 39,402 | `static/imgs/favicon_io/android-chrome-192x192.png` | Image |
| 8 | 38,449 | `static/js/ui-form-handlers.js` | App JS |
| 9 | 36,319 | `static/imgs/favicon_io/apple-touch-icon.png` | Image |
| 10 | 34,806 | `static/js/account-manager.js` | App JS |
| 11 | 31,744 | `static/js/ui-person-details.js` | App JS |
| 12 | 30,761 | `static/js/relationship-manager.js` | App JS |
| 13 | 28,928 | `static/js/advanced-search.js` | App JS |
| 14 | 24,077 | `static/js/merge-ui.js` | App JS |
| 15 | 23,881 | `static/js/dist/account-manager.js` | "Minified" (broken) |
| 16 | 23,665 | `static/js/dist/ui-form-handlers.js` | "Minified" (broken) |
| 17 | 23,592 | `static/js/collaboration-manager.js` | App JS |
| 18 | 23,445 | `static/js/metrics-dashboard.js` | App JS |
| 19 | 23,383 | `static/js/bulk-import.js` | App JS |
| 20 | 21,814 | `static/js/map-handler.js` | App JS |

**Totals:** `static/js/*.js` (active) ≈ 400 KB. `static/js/dist/*.js` (shadow) ≈ 252 KB. `static/css/` ≈ 32 KB (3 files). PNG logos ≈ 4 MB.

No file exceeds 200 KB unminified for JS/CSS. The headline bytes-on-the-wire issue is **images**, not JavaScript.

---

## 3. Build Pipeline Summary

**`frontend/vite.config.ts`** — Library mode (`build.lib`), entry `src/index.ts`, outputs `../static/js/components/basset-hound-ui.{es,umd}.js`. Externalizes `react`/`react-dom` (loaded from unpkg CDN at runtime). Defaults otherwise: no `manualChunks`, no hashing, no `assetsInlineLimit` tuning.

**`frontend/package.json`** — React 18 + Zustand for one widget (Smart Suggestions panel); rest of app is vanilla ES modules. Build script `tsc && vite build` not wired into Docker/CI from what is visible here. `zustand` and `clsx` are silently bundled into the widget (~60 KB ES).

**`scripts/minify-js.js`** — Regex-only "minifier" in CommonJS. Strips `//` and `/* */` comments, collapses whitespace, then re-inserts spaces around a fixed keyword list. No parser, no source maps, no string-aware handling.

**Net:** two pipelines — Vite (works, one widget) and `minify-js.js` (brittle, output broken, wired nowhere — see §5). No bundler/code-splitter/hashing for the ~20 vanilla ES modules.

---

## 4. Phase 1 Claim Verification

| Claim (from `FRONTEND-PHASE1-COMPLETION-SUMMARY.md`) | Code reality | Drift |
|---|---|---|
| Event delegation: 114 → 1 listener on person list (−200ms) | `static/js/ui-people-list.js` exposes `attachPersonListEventDelegation`; wired in `setupSearch`. **Plausible**, not measured in this audit. | None. |
| Cache reuse: `window.people` consumed by `ui-person-details.js` (−200ms) | `dashboard.js:89` initialises cache; `ui-person-details.js` uses cache-first lookup. **Confirmed.** | None. |
| Async `marked.js` (−15ms) | `templates/dashboard.html:178` has `<script async src=".../marked.min.js">`. **Confirmed.** | None. |
| GZIP enhancement (`gzip_min_length 1000`, font MIME types) | Out-of-scope for this audit (nginx is another agent's zone), but listed here for completeness. | Not verified here. |
| Minification: 35.79% reduction, 22/22 files OK (−80ms) | Script runs and produces output, **but the output is broken**: URLs are corrupted, hyphenated module specifiers are split, and `await import('./bulk-import.js')` becomes `await import ('./bulk- import .js')`. See §5. | **Major drift.** Files exist but are not loadable. Templates do not reference them. |
| Templates updated to point at `dist/` | `grep -n "/static/js/dist" templates/*.html` → **0 hits.** All templates still load originals from `/static/js/*.js`. | **Activation never happened.** The claimed −80ms / −33KB transfer saving has not shipped. |
| "Code Splitting / lazy-loading" implied as part of Phase 1 follow-on | Already in source via `await import()` for `advanced-search`, `bulk-import`, `collaboration-manager`, `merge-ui`, `account-manager`, `relationship-manager`, `metrics-dashboard`, `suggestions-init`. Pre-existing, not from Phase 1. | Claim accurate but pre-dates Phase 1. |
| Asset hashing for cache-busting | **None.** Vite lib output has fixed filenames; vanilla JS served as-is. | Not implemented. |

**Net Phase 1 reality:** quick wins 1–3 shipped (~−415ms claimed). Quick win 4 (gzip) deferred to nginx agent. Quick win 5 (minification) is **shipped artifact, broken content, never activated** — the headline 35.79% / −80ms saving is a paper claim.

---

## 5. The Minification Bug (critical finding)

Two regex passes in `minify-js.js` are unsafe and produce broken JS:

**Bug A — URL corruption.** `code.replace(/\/\/.*?$/gm, '')` is not string-aware, so `'https://cdn.jsdelivr.net/...'` becomes `'https:` (everything past `//` is deleted to end-of-line). Confirmed in `static/js/dist/metrics-dashboard.js:1` — `const CHART_JS_CDN='https:` — Chart.js will never load.

**Bug B — Keyword regex splits identifiers.** The "restore spaces" pass `\b(if|else|...|import|export|from|as)\b` injects a space on both sides at every non-word boundary. In `static/js/dist/dashboard.js:1`: `from './ export -handler.js'` and `await import ('./bulk- import .js')`. Any browser loading this would throw `SyntaxError` / 404. Also rewrites string content inside template literals (e.g. `'Error loading bulk import :'`).

**Why production hasn't burned:** templates still reference unminified originals (`grep -n "/static/js/dist" templates/*.html` → 0 hits). The `dist/` tree is 252 KB of checked-in dead weight and a footgun for anyone who follows the Phase 1 doc's activation steps verbatim.

---

## 6. Orphan / Dead Asset List

Cross-referenced every file in `static/` against:
- `grep -rn "static/" templates/ api/`
- Module-level `import` statements in `static/js/*.js`
- Dynamic `await import('./X.js')` calls

**Confirmed orphans (zero references found):**

| Path | Size | Notes |
|---|---:|---|
| `static/js/dist/**` (entire directory, 22 files) | ~252 KB | Broken minifier output, never wired into a template (§5). |
| `static/js/examples/cache-dashboard-usage.js` | 11,796 B | Only referenced from a sibling README; no template or runtime loader pulls it. |
| `static/js/CACHE_DASHBOARD_README.md` | — | Doc inside the JS tree; should live under `docs/`. |
| `static/downloads/Test_Project.json` | — | Test fixture committed under `static/downloads/`; no code references it. |
| `static/js/components/basset-hound-ui.es.js` | 60,420 B | Only the `.umd.js` is loaded from `templates/dashboard.html:120`. The ESM build is unreferenced. |
| `static/plugins/README.md` | — | Doc file in served static tree; not loaded by `plugin-manager.js`. |

**Conditionally loaded (NOT orphans):**
- `merge-ui.js`, `relationship-manager.js`, `account-manager.js`, `advanced-search.js`, `bulk-import.js`, `collaboration-manager.js`, `cache-dashboard.js`, `metrics-dashboard.js`, `report-handler-pdf.js` — pulled via `await import()` from `dashboard.js` / `ui-person-details.js` / `advanced-search.js` / `tag-handler.js`. Some are large (≥20 KB) but legitimately code-split.
- `static/plugins/{sankey,timeline,network-stats,heatmap}/plugin.js` — loaded dynamically by `plugin-manager.js`.

**Recommend deletion:** all files in the "Confirmed orphans" table. Estimated savings: ~324 KB on disk, ~252 KB never-shipped artifacts removed from review surface.

---

## 7. Bundle Composition Observations

- **No real bundler for the main app.** `templates/dashboard.html` loads nine ES modules via separate `<script type="module">` tags (L105–113); each module fetches its static `import` chain. HTTP/2 mutes but doesn't eliminate the cost.
- **CDN-served React.** React 18 + ReactDOM from `unpkg.com` (L116–117) — third-party origin on critical path. Zustand and clsx are silently bundled into the widget (~60 KB ES / ~39 KB UMD).
- **Dead ESM copy of the React widget.** `basset-hound-ui.es.js` is built but only `.umd.js` is referenced. Vite `lib` config builds both unconditionally.
- **Console noise in shipped JS.** ~115 `console.log/debug/info` across `static/js/*.js`, weighted toward `collaboration-manager.js` (25), `plugin-manager.js` (13), `dashboard.js` (11), `tag-handler.js` (8). No `debugger;` statements.
- **CSS is small.** `dashboard.css` (21 KB), `file_explorer.css` (4 KB), `map-controls.css` (4 KB), `suggestions-panel.css` (3 KB). Bootstrap and Font Awesome are CDN.
- **Images dominate.** Three 1.2–1.5 MB logo PNGs; `_removebg.png` (1.5 MB) looks like an unoptimized editor export. `android-chrome-512x512.png` (316 KB) is oversized.
- **No file-name hashing** → manual cache-busting required at deploy.

---

## 8. Recommendations (ordered by impact-to-effort)

1. **Delete `static/js/dist/` entirely** and add it to `.gitignore`. Broken, unreferenced, and the Phase 1 doc advertises it as activation-ready — actively dangerous. (5 min.)
2. **Replace `scripts/minify-js.js` with esbuild or terser.** A one-liner (`npx esbuild --minify` or `npx terser`) is correct, source-mapped, and gives 50–70% reduction. Unlocks the actual −80ms claim. (1–2 hours.)
3. **Recompress logo PNGs** with pngquant/oxipng or WebP. Realistic target <100 KB each; saves ~4 MB initial page weight. (30 min, highest user-visible win.)
4. **Drop the dead ESM widget build.** Restrict `vite.config.ts` `lib.formats` to `['umd']` or delete `.es.js` post-build. (5 min.)
5. **Strip console logging from shipped JS** via esbuild `drop: ['console','debugger']`. Until then, gate behind `window.__DEBUG__`. (1 hour.)
6. **Add file-name hashing** when migrating to a real bundler; have the Jinja layer read a manifest. (3–4 hours.)
7. **Bundle the nine top-level `<script type="module">` tags into 1–2 chunks** to remove the dependency-graph fetch waterfall and enable tree-shaking. (Half-day.)
8. **Move `static/js/CACHE_DASHBOARD_README.md`, `static/plugins/README.md`, and `static/downloads/Test_Project.json` out of `static/`** (served publicly today). (15 min.)
9. **Externalize Zustand/clsx in `vite.config.ts`** or document why they're bundled. Re-evaluate need for the ESM build at all. (30 min.)
10. **Amend `FRONTEND-PHASE1-COMPLETION-SUMMARY.md`** — minification is claimed complete but artifact is broken and never activated. (15 min.)

---

## 9. Relevant Files

- `/home/devel/basset-hound/scripts/minify-js.js` — broken regex minifier
- `/home/devel/basset-hound/static/js/dist/` — 22 broken "minified" files (delete)
- `/home/devel/basset-hound/static/js/dist/metrics-dashboard.js` line 1 — visible URL corruption (`const CHART_JS_CDN='https:`)
- `/home/devel/basset-hound/static/js/dist/dashboard.js` line 1 — visible identifier corruption (`'./ export -handler.js'`, `'./bulk- import .js'`)
- `/home/devel/basset-hound/frontend/vite.config.ts` — library build, no hashing, no manualChunks
- `/home/devel/basset-hound/templates/dashboard.html` lines 94–179 — actual asset wiring (none point at `dist/`)
- `/home/devel/basset-hound/static/imgs/basset_hound_logo_removebg.png` — 1.5 MB image, recompression candidate
- `/home/devel/basset-hound/docs/handoffs/FRONTEND-PHASE1-COMPLETION-SUMMARY.md` — claims to verify against
