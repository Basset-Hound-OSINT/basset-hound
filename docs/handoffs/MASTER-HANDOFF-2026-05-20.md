# Master Handoff — 2026-05-20

**Author:** doc-writer@basset-hound:master-handoff
**Inputs:** 9 finding files across 3 agent waves (handoffs consolidation, neo4j refactor, uncommitted diff, test coverage, router surface, security recheck, docker/nginx, frontend static, dependency audit).
**Mode:** Synthesis only — no new recommendations beyond source findings.

---

## 1. Executive Summary

Nine agents audited the repo across documentation, code, infrastructure, security and supply-chain. The in-session orchestrator landed eight unblocking fixes (Neo4j driver flags, request timeout consistency, pytest marker hygiene, router prefix bug, container now healthy with 3041 tests collecting). The remaining picture is **functionally working but production-blocked**: the security audit's "0 issues / GDPR+OWASP+SOC2" claim is unsupported by code (50+ unauthenticated routers, `AUTH_ENABLED=false` in committed `.env`, project-ownership check is a `TODO`), the docs/handoffs directory has ~85 duplicate files, the frontend Phase 1 "minification win" ships a broken `static/js/dist/` tree, and Stream 7 surfaced a strong hypothesis that **nginx `Connection: "upgrade"` is unconditionally defeating upstream keepalive** — likely the actual Phase 8 concurrency ceiling, not the worker count. Verdict: **needs one more focused session before any production push**.

---

## 2. In-Session Fixes (DONE)

| # | Fix | File / Evidence |
|---|---|---|
| 1 | Removed invalid `max_retry_time` driver arg; added fail-fast on `ConfigurationError` / `AuthError`; capped startup wait at 120 s | `api/services/neo4j_handler.py` (per uncommitted-diff-review §6) |
| 2 | Bumped `REQUEST_TIMEOUT` from 5 s → 30 s in `.env`, `api/config.py` default, and `api/main.py` (now reads from `settings`) | `.env:115`, `api/config.py:199`, `api/main.py:275` (per uncommitted-diff-review §3, §5; security-recheck 5.5) |
| 3 | Aligned `.env.example` `NEO4J_MAX_CONNECTION_POOL_SIZE=500`; removed obsolete `NEO4J_MAX_RETRY_TIME` | `.env.example:13` (per uncommitted-diff-review §2) |
| 4 | Fixed `GZipMiddleware` import typo (was `GZIPMiddleware`) | `tests/test_gzip_compression.py` (per test-coverage-gap §3) |
| 5 | Registered `performance` and `deployment` pytest markers | `pytest.ini` (per test-coverage-gap §4) |
| 6 | Fixed `cletus_integration` router double-prefix (`/api/v1/api/v1/cletus` → `/cletus`) | `api/routers/cletus_integration.py` (per router-surface-audit §3) |
| 7 | Renamed `TestResult` → `GraphVizTestResult` to unblock pytest collection | `tests/test_graph_visualization_e2e.py` (per test-coverage-gap §3) |
| 8 | Migrated `regex=` → `pattern=` (FastAPI deprecation) | `api/routers/search.py` (orchestrator note) |
| 9 | Container `basset_api` now HEALTHY with Neo4j connected; **3041 tests collect cleanly** | runtime verification |

---

## 3. Top 10 Risks (Ranked)

| # | Risk | Sev | Source | One-line Fix |
|---|---|---|---|---|
| 1 | ~407 of ~414 mounted endpoints have **no auth dependency**; default-open posture | **P0** | router-surface-audit §5; security-recheck P0/1.3 | Add `dependencies=[Depends(get_current_user_or_api_key)]` to `api_router` in `main.py:660`; explicit opt-out for `/health`, `/auth/*`, `/api` |
| 2 | `AUTH_ENABLED=false` shipped in committed `.env`; bypass returns synthetic `User(scopes=["*"])` | **P0** | security-recheck §2 P0 | Flip to `true`; treat var as opt-out only |
| 3 | nginx sets `Connection: "upgrade"` on every request → defeats upstream keepalive pool (likely true root cause of Phase 8 concurrency ceiling) — see §7 hypothesis | **P0** | docker-nginx-review B5; cross-ref Phase 8 memory | Add `map $http_upgrade $connection_upgrade { default upgrade; '' ''; }`; use `$connection_upgrade` in `proxy_set_header` |
| 4 | Project ownership check is a `TODO` (`export.py:304-309`); any authenticated user reaches any project | **P0** | security-recheck §2 P0; 1.5 | Implement membership Cypher query in `_verify_project_access` |
| 5 | Neo4j Browser exposed via nginx `/neo4j/` with hardcoded `neo4j/neo4jbasset` creds | **P0** | docker-nginx-review B6, E3 | Drop route or add Basic Auth + IP allowlist; require `${NEO4J_PASSWORD:?required}` |
| 6 | Default `admin`/`user` passwords + default `SECRET_KEY` shipped in `.env` | **P0** | security-recheck §2 P0; 1.6 | Remove demo users or gate behind `DEBUG`; require `JWT_SECRET_KEY` at startup |
| 7 | celery_worker / celery_beat inherit Dockerfile `HEALTHCHECK curl :8000/health` (no HTTP listener) — perpetually unhealthy | **P0** | docker-nginx-review C1 | Per-service `healthcheck:` overrides (`celery inspect ping`, `pgrep beat`) |
| 8 | `python-dotenv` CVE-2026-28684 (critical symlink overwrite); pinned `==1.1.0`, installed `1.0.1` (drift) | **P0** | dependency-audit §1, §3 | Bump to `>=1.2.2` |
| 9 | No `mem_limit` on any service; stack at 6.0-6.9 GB on a 6 GB host → OOM-killer reproduces load-test failure | **P1** | docker-nginx-review F1 | Add ceilings: neo4j 3.5g, basset_api 1.5g, celery_worker 1.0g, redis 384m, others smaller |
| 10 | `DEBUG=true` in `.env` + `main.py:354` puts `str(exc)` in 500 body | **P1** | security-recheck §2 P1; 5.4 | Set `DEBUG=false`; replace `str(exc)` with correlation ID |

Honorable mentions just below P1: encryption fallback to public-string key (`encryption.py:95`); rate limiter is process-local with no eviction (4 workers × limit; `"anonymous"` collapse); two divergent `get_current_user` implementations; `CORS_ORIGINS=*` shipped; nginx `limit_req_zone` declared but never applied.

---

## 4. Top 10 Quick Wins (Impact-to-Effort)

| # | Win | Effort | Impact | Source |
|---|---|---|---|---|
| 1 | Add `Connection: $connection_upgrade` map idiom to nginx | **S** (5 min) | Likely unblocks Phase 9 concurrency ceiling | docker-nginx-review B5 |
| 2 | Align nginx proxy timeouts to 35 s (currently 60 s vs app's 30 s) | **S** (2 min) | Removes 30-s 504-ghost window | docker-nginx-review B4 |
| 3 | Apply `limit_req zone=api_limit` to `location /` (zone exists, unused) | **S** (5 min) | Real rate limiting on the front door | docker-nginx-review B3 |
| 4 | Bump `python-dotenv` to `>=1.2.2` (critical CVE) | **S** (1 min) | Closes the one outstanding critical CVE | dependency-audit §3 |
| 5 | Delete `static/js/dist/` (22 broken minifier outputs, 252 KB, never referenced) + `.gitignore` it | **S** (5 min) | Removes footgun; deletes 252 KB of checked-in dead weight | frontend-static-audit §5, §8 |
| 6 | Recompress 3 logo PNGs (~4 MB → <300 KB) with pngquant/oxipng | **S** (30 min) | Biggest user-visible page-weight win | frontend-static-audit §8 |
| 7 | Tighten 7 loose Python pin bounds (jinja2, starlette, python-jose, python-multipart, mcp, markdown, celery) | **S** (10 min) | Closes ranges admitting 5+5+2+3+3+pre-3.6+pre-5.4 known CVEs | dependency-audit §3 |
| 8 | Move secrets to `${VAR:?required}` in compose (neo4j password, grafana admin) | **S** (20 min) | Forces explicit ops decision; removes hardcoded creds | docker-nginx-review E2, E3, H1 |
| 9 | Delete `analytics.py` + `schedule.py` deprecated re-export shims (not imported anywhere) | **S** (5 min) | Removes `DeprecationWarning` noise; clarifies surface | router-surface-audit §4, §6 |
| 10 | Add `asyncio_mode = auto` to `pytest.ini`; remove duplicate marker registration | **S** (5 min) | Simplifies ~30 async tests; ends marker warnings | test-coverage-gap §4 |

---

## 5. Deferred Items (Top 5)

| # | Item | Why Deferred | Estimated Effort | Source |
|---|---|---|---|---|
| 1 | **Neo4j service refactor** — split 2,301-line god class into `neo4j/` package (driver, schema, repositories, facade) | Phases A–E mechanical but ~10 h focused work; touches ~25 consumers; needs test-gated phases | ~10 h, phased, fully reversible | neo4j-service-refactor-proposal §5, §10 |
| 2 | **bcrypt → argon2 migration** (drop passlib + `bcrypt<4.0.0` pin) | Option A: `passlib[argon2]` + lazy-rehash on login; no active CVE, P3 today | 2–4 h | security-recheck §3; dependency-audit §6 |
| 3 | **Handoffs archive sweep** — move ~85 superseded `.md` files into `docs/handoffs/archive/2026-05/` | Requires 4 inbound link updates in top-level `docs/*.md` first; pre-existing `docs/archive` vs `docs/archives` collision | 1 h after link updates | handoffs-consolidation-audit §3, §4 |
| 4 | **Strip or sidecar TeXLive** from runtime image (~700 MB – 1.5 GB CVE surface) | Needs prior audit of which endpoints actually shell to `latexmk` | 1–2 h after audit | docker-nginx-review A2 |
| 5 | **Replace `scripts/minify-js.js` with esbuild/terser** + activate hashed bundle output | Real bundler choice + manifest plumbing in Jinja; the broken regex minifier should be deleted today (quick win #5) | 3–4 h | frontend-static-audit §8 |

Also noted but deferred: Storybook 7 → 8 EOL upgrade (Q3); reconcile two `get_current_user` implementations; Redis-backed rate limiter; per-package `conftest.py` for test scoping; pip-tools / `uv` lockfile.

---

## 6. Recommended Next-Session Work Order

Ordered by impact-to-effort; first three are minutes of work each and should be done before anything else.

1. **Fix nginx `Connection` header + proxy timeouts + apply rate-limit zone** (docker-nginx-review B5, B4, B3). One file, ~10 min total. Validates Phase 8 hypothesis under live load.
2. **Apply global auth dependency to `api_router`** and flip `AUTH_ENABLED=true`; remove default `admin`/`user` users (security-recheck #1, #4). Two-line change in `main.py:660` + `.env` flip + delete demo users in `routes.py:130,136`. Closes the four largest P0 gaps.
3. **Bump `python-dotenv` to `>=1.2.2`** and tighten the 7 loose Python pin bounds (dependency-audit §3, §8). Single-commit change.
4. **Fix celery healthcheck inheritance** (docker-nginx-review C1) and add `mem_limit` to every compose service (F1). Stabilizes the stack at the 6 GB host ceiling.
5. **Delete `static/js/dist/`** + recompress logo PNGs (frontend-static-audit §8 #1, #3). One commit, biggest user-visible win.
6. **Implement project-membership check** in `_verify_project_access` (security-recheck P0 / 1.5). One Cypher query replacing the `TODO`.
7. **Gate or remove `/neo4j/` nginx route** and move compose secrets to `${VAR:?required}` (docker-nginx-review B6, E3, H1).
8. **Delete `analytics.py` + `schedule.py` shims**; resolve `cache.py` / `orphan.py` mount-or-delete; remove dead `mcp_router` import (router-surface-audit §7).
9. **Add `tests/test_neo4j_service.py`** + repair `tests/test_orphan_methods.py` legacy import (test-coverage-gap §5 tier 1–2). Closes the largest 0%-coverage hot zones before the refactor.
10. **Execute handoffs archive sweep** after updating the 4 inbound `docs/*.md` link targets (handoffs-consolidation-audit §3, §4). Shrinks handoffs/ from 131 → ~46 files.

---

## 7. Cross-Cutting Themes

- **Docs / code drift is the dominant pattern.** The Phase 8 final security audit's "36/36 / 0 issues / production ready / GDPR+OWASP+SOC2 compliant" claim conflicts with at least 12 substantive code-level gaps (security-recheck §4). The frontend Phase 1 "minification −80ms / 35.79% reduction" claim conflicts with a broken `dist/` tree that no template references (frontend-static-audit §4, §5). The handoffs directory has 131 files where ~46 would do (handoffs-consolidation-audit §2.11).
- **Auth posture is default-open, not default-closed.** Five of 58 router modules use auth dependencies; the rest are anonymously reachable. The Phase 8 audit treated "auth dependency present on N endpoints" as equivalent to "system protects N endpoints", missing that the global posture is opt-in (security-recheck §2 P0; router-surface-audit §5).
- **Phase 8 root cause hypothesis — HIGH but not certain.** Stream 7 (docker-nginx-review B5) identifies that nginx unconditionally sets `Connection: "upgrade"` on every proxied request, which downgrades HTTP/1.1 to non-keepalive against the upstream — defeating the recent `keepalive 32→256` bump (NGINX-KEEPALIVE-FIX.md) on all non-WebSocket traffic. The uncommitted-diff-review (§7) had earlier pinned the symptom on `--workers 4` + per-worker lifespan startup, with ~85% confidence. **Both can be true**: lifespan contention explains startup `unhealthy`; the keepalive defeat explains the 76% error rate at 100 concurrent users. This is a **hypothesis to validate empirically**, not a confirmed fix — once the `$connection_upgrade` map is applied, re-run the 100-user load test before declaring victory.
- **The 2,301-line `neo4j_service.py` is a strategic refactor target, not an emergency.** It scores risk-25 in test-coverage-gap §2 (zero direct unit tests, 12% line coverage, every router depends on it) and has a fully-planned 10-hour phased extraction (neo4j-service-refactor-proposal §5). Do it after Phase 8 is closed and authentication is wired.
- **Pin hygiene is the systemic supply-chain risk.** 24 of 33 Python deps use `>=` with no upper bound; mypy already silently jumped 1.13 → 2.1, pytest-asyncio 0.24 → 1.3, phonenumbers 8 → 9, websockets 12 → 16. No lockfile. One critical CVE outstanding (python-dotenv) but the next regression is a single upstream release away (dependency-audit §5).
- **Test infrastructure drift mirrors docs drift.** `pytest.ini` markers don't match `conftest.py` re-registrations; `.coveragerc` is empty; async mode not configured; stale `.coverage` data file from 2026-05-19 14:59; two test files declare `TestResult` classes that pytest skips silently. Direct test files exist for `search_analytics` and `graph_visualization` but coverage shows 0% / 18% — strong indicator that recent collection failures are masking real regressions (test-coverage-gap §7).

---

## 8. File Index

**Source findings (read-only, this session):**
- `/home/devel/basset-hound/docs/findings/2026-05-20-handoffs-consolidation-audit.md`
- `/home/devel/basset-hound/docs/findings/2026-05-20-neo4j-service-refactor-proposal.md`
- `/home/devel/basset-hound/docs/findings/2026-05-20-uncommitted-diff-review.md`
- `/home/devel/basset-hound/docs/findings/2026-05-20-test-coverage-gap-analysis.md`
- `/home/devel/basset-hound/docs/findings/2026-05-20-router-surface-audit.md`
- `/home/devel/basset-hound/docs/findings/2026-05-20-security-recheck.md`
- `/home/devel/basset-hound/docs/findings/2026-05-20-docker-nginx-review.md`
- `/home/devel/basset-hound/docs/findings/2026-05-20-frontend-static-audit.md`
- `/home/devel/basset-hound/docs/findings/2026-05-20-dependency-audit.md`

**Coordination + this handoff:**
- `/home/devel/basset-hound/docs/handoffs/AGENT-WORK-PLAN-2026-05-20.md` (work plan that produced the 9 findings)
- `/home/devel/basset-hound/docs/handoffs/MASTER-HANDOFF-2026-05-20.md` (this document)

**Word count:** ~2,150.
