# Docker / Compose / Nginx Hardening Review

**Date**: 2026-05-20
**Reviewer**: reviewer@basset-hound:docker-nginx-hardening (Wave 3)
**Scope**: `docker-compose.yml`, `docker-compose.dev.yml`, `Dockerfile`, `nginx/nginx.conf`, `.env.example`
**Context**: 4 uvicorn workers behind nginx; redis/neo4j/celery sidecars; host memory ceiling ~6 GB free.

---

## 1. Per-Service Table

| Service        | mem_limit / cpus | restart            | healthcheck                                              | Host port           | Notes                                                                                                       |
|----------------|------------------|--------------------|----------------------------------------------------------|---------------------|-------------------------------------------------------------------------------------------------------------|
| nginx          | none / none      | unless-stopped     | wget spider `:8080/nginx-health`                         | 8080 -> 8080        | Correct ingress. No resource ceiling.                                                                       |
| neo4j          | none / none      | unless-stopped     | wget spider `:7474`                                      | internal            | Heap configured (1G init / 2G max + 1G pagecache) but no Docker mem_limit. Real usage: ~3 GB.               |
| redis          | none / none      | unless-stopped     | `redis-cli ping`                                         | internal            | `maxmemory 256mb` set at app level. No Docker mem_limit / cpus.                                             |
| basset_verify  | none / none      | unless-stopped     | curl `:8001/health`                                      | internal            | OK. CORS `*` set on dev origin (acceptable inside private net).                                             |
| basset_api     | none / none      | unless-stopped     | curl `:8000/health`                                      | **internal only**   | 4 uvicorn workers. ~1 GB total expected. No mem_limit; one runaway request could OOM host.                  |
| celery_worker  | none / none      | unless-stopped     | **inherits broken HEALTHCHECK from Dockerfile**          | internal            | **BLOCKER**: image HEALTHCHECK calls `curl :8000/health`, but worker has no HTTP listener (see Issue C1).   |
| celery_beat    | none / none      | unless-stopped     | inherits same broken HEALTHCHECK; `depends_on` uses short-form, no `condition:` (Issue D2) | internal | Same healthcheck inheritance issue; depends_on bypasses healthy gating.                                  |
| prometheus     | none / none      | unless-stopped     | wget spider `:9090/-/healthy`                            | **9090 -> 9090**    | Exposed on host with no auth (Issue E1).                                                                    |
| grafana        | none / none      | unless-stopped     | wget spider `:3000/api/health`                           | **3001 -> 3000**    | Hard-coded admin/basset_admin credentials (Issue E2).                                                       |

**Fit check (~6 GB free)**: basset_api 1.0-1.4 GB + celery_worker 0.8-1.2 GB + celery_beat 0.15 GB + neo4j 3.0-3.5 GB + redis 0.3 GB + basset_verify 0.2 GB + prometheus/grafana 0.5 GB + nginx 0.05 GB ≈ **6.0-6.9 GB**. Stack is at-or-slightly-over the ceiling once neo4j warms. Without `mem_limit`, the OOM-killer will pick the largest worker (neo4j) and reproduce the load-test failure mode. MAJOR.

---

## 2. Nginx Review (`nginx/nginx.conf`)

| Aspect              | Current                                                      | Verdict                                                                    |
|---------------------|--------------------------------------------------------------|----------------------------------------------------------------------------|
| Headers             | X-Frame-Options=SAMEORIGIN, X-Content-Type-Options=nosniff, X-XSS-Protection, Referrer-Policy=strict-origin-when-cross-origin | OK for HTTP; **HSTS, CSP, Permissions-Policy missing** (Issue B1). |
| Server tokens       | default (on)                                                 | `server_tokens off;` missing (Issue B2, MINOR).                            |
| Rate limit          | zone defined `100r/s` but **never applied** via `limit_req`  | Issue B3, MAJOR — defined-but-unused gives false sense of security.        |
| Keepalive (upstream)| 256                                                          | Matches the NGINX-KEEPALIVE-FIX handoff. Good for 100+ concurrent.         |
| Keepalive (client)  | `keepalive_timeout 65`                                       | Reasonable.                                                                |
| Proxy timeouts      | connect/send/read = 60s                                      | **Mismatch with REQUEST_TIMEOUT=30** (Issue B4, MAJOR) — middleware aborts at 30s but nginx waits 60s; client sees double-billed latency or stale 504s.       |
| Buffers             | buffer_size 4k, buffers 8x16k, busy 24k                      | Reasonable for JSON; may need bump for large export endpoints.             |
| `proxy_http_version`| 1.1 on `/` and `/neo4j/`                                     | Good (required for keepalive).                                             |
| **`Connection` header for keepalive** | always `"upgrade"` (every request)              | **Issue B5, MAJOR** — sets `Connection: upgrade` unconditionally, defeating the upstream keepalive pool except on WS requests. Use the standard `$connection_upgrade` map idiom. This may be the actual root cause of the 4-worker concurrency ceiling described in the Phase 8 load test memory. |
| Worker connections  | 1024                                                         | Adequate for ~100 concurrent users; revisit at 1k.                         |
| `client_max_body_size` | 100M                                                      | Matches `MAX_UPLOAD_SIZE_MB=100` in .env.example. Good.                    |
| `/static/` cache    | `expires 7d; Cache-Control public, immutable`                | Good for the immutable filename strategy.                                  |
| Logging             | combined-plus-timings                                        | Good for SLO debugging.                                                    |
| `/neo4j/` exposure  | **proxied with no authentication**                           | Issue B6, BLOCKER for production — Neo4j Browser at `/neo4j/` allows DB administration with the leaked default password from compose env. |

---

## 3. Dockerfile Review

| Aspect                | Status                                                       | Verdict                                                                   |
|-----------------------|--------------------------------------------------------------|---------------------------------------------------------------------------|
| Multi-stage           | Yes (builder + production)                                    | Good.                                                                     |
| Non-root user         | Yes (`basset:basset`, uid/gid 1000)                          | Good.                                                                     |
| Base pin              | `python:3.12-slim` (tag only, no digest)                     | MINOR — pin to `python:3.12-slim@sha256:...` for reproducibility (Issue A1). |
| Runtime deps          | libpq5, libmagic1, curl, **full texlive-latex-base + extra + fonts-recommended + pictures + latexmk** | MAJOR (Issue A2) — TeXLive bloats the image by ~700 MB - 1.5 GB. If LaTeX export is required, isolate to a sidecar. |
| Layer hygiene         | `apt-get update && install && rm -rf /var/lib/apt/lists/*`   | Good.                                                                     |
| `COPY --chown` for app | Yes                                                          | Good.                                                                     |
| `HEALTHCHECK`         | `curl --fail http://localhost:8000/health`                   | **Inherited by celery containers that don't expose 8000** — Issue C1, BLOCKER. |
| `CMD`                 | `uvicorn --host 0.0.0.0 --port 8000` (no `--workers`)        | Overridden by compose. Fine.                                              |
| `.dockerignore`       | not checked in WORK_ZONE; recommend audit                    | NIT.                                                                      |
| Build deps in final   | Builder stage isolates `build-essential`/`gcc` ✓             | Good.                                                                     |
| `EXPOSE 5000`         | "Flask (legacy)" — dead port                                 | NIT (Issue A3) — drop to reduce confusion.                                |
| `PIP_NO_CACHE_DIR`    | builder only; production reuses /usr/local                   | Good.                                                                     |

---

## 4. Issues by Severity

### BLOCKER

- **C1. celery_worker / celery_beat healthcheck targets non-existent HTTP port.** Both celery containers use the basset_api Dockerfile and inherit `HEALTHCHECK CMD curl --fail http://localhost:8000/health`. Neither runs uvicorn, so they stay `unhealthy` forever. Any future `condition: service_healthy` on celery will deadlock. Fix: add per-service `healthcheck:` override using `celery -A api.tasks inspect ping -d celery@$$HOSTNAME` for the worker and a `pgrep -f 'celery.*beat'` check for beat.

- **B6. Neo4j Browser exposed via nginx with default credentials.** `location /neo4j/` proxies the Neo4j HTTP listener with no auth in front. Credentials `neo4j/neo4jbasset` are baked into `docker-compose.yml`. For any non-local deployment an attacker reaching :8080 owns the graph. Fix: (a) Basic Auth + IP allowlist on `/neo4j/`, (b) drop the route and use `docker-compose.dev.yml`, or (c) require a strong `${NEO4J_PASSWORD}`.

- **E3. Neo4j password hardcoded in compose** (`NEO4J_AUTH=neo4j/neo4jbasset`), repeated in `basset_api` and `celery_*`. Should be `${NEO4J_PASSWORD:?required}`.

### MAJOR

- **B4. Nginx proxy timeouts (60s) exceed FastAPI `REQUEST_TIMEOUT=30`.** Backend cancels at 30s and returns 504; nginx still holds the upstream socket another 30s. Use `proxy_connect_timeout 5s; proxy_send_timeout 35s; proxy_read_timeout 35s;` to mirror the app contract.

- **B5. `proxy_set_header Connection "upgrade"` applied to every request.** Downgrades HTTP/1.1 keepalive — nginx opens a fresh upstream socket per non-WS request, defeating the 32->256 pool bump. Use the standard `map $http_upgrade $connection_upgrade { default upgrade; '' ''; }` and `proxy_set_header Connection $connection_upgrade;`. Likely the actual cause of the Phase 8 concurrency ceiling.

- **B3. Rate-limit zone defined but never enforced.** `limit_req_zone ... zone=api_limit:10m rate=100r/s;` is declared but no `limit_req zone=api_limit ...;` directive references it. Add to `location /` with `burst=` and `nodelay`.

- **A2. TeXLive installed in the runtime image.** Adds ~700 MB - 1.5 GB and a large CVE surface. If LaTeX export is required, isolate to a sidecar; otherwise drop. Audit usage first.

- **F1. No `mem_limit` / `cpus` on any service.** Stack is borderline at 6 GB; one leak in neo4j or a celery task takes the host down. Suggested ceilings: neo4j 3.5g/2cpu, basset_api 1.5g/2cpu, celery_worker 1.0g/1cpu, redis 384m/0.5cpu, basset_verify 256m/0.5cpu, prometheus 256m/0.5cpu, grafana 256m/0.5cpu, nginx 128m/0.5cpu.

- **E1. Prometheus exposed on host port 9090 with no auth.** Move behind nginx with Basic Auth + IP allowlist, or strip the host binding and only expose via `docker-compose.dev.yml`.

- **E2. Grafana admin password hardcoded** (`basset_admin`) and Grafana exposed on host 3001. Use `${GRAFANA_ADMIN_PASSWORD:?required}` and gate behind nginx.

- **D2. `celery_beat.depends_on` uses short form** (no `condition`), so it can start before redis is healthy. Switch to `condition: service_healthy` after fixing C1.

- **G1. Bind mounts are read-write and host-relative.** `./projects:/app/projects` and `./static:/app/static` are both RW in basset_api and celery_worker. No direct path-traversal at the bind layer, but any upload bug that escapes app-level sanitization can persist hostile content into the served static tree. Recommend `./static:/app/static:ro` (the API serves a prebuilt bundle) and `:rw,Z` on SELinux hosts for `./projects`.

### MINOR

- **A1. Base image not pinned by digest** (`python:3.12-slim`).
- **B1. Missing security headers**: HSTS, CSP, Permissions-Policy, COOP. Stream 6 confirmed the app does not emit them — add at nginx. HSTS only once TLS terminates in front of nginx.
- **B2. `server_tokens off;` not set** — nginx leaks version on errors.
- **D1. `basset_api.depends_on` correctly uses `condition: service_healthy` for neo4j/redis/basset_verify** (item 10 verified).
- **H1. Compose interpolation**: docker-compose.yml uses zero `${VAR}` substitutions; everything is hardcoded including passwords. Add `${NEO4J_PASSWORD:?required}`, `${GRAFANA_ADMIN_PASSWORD:?required}`, `${REQUEST_TIMEOUT:-30}`, `${UVICORN_WORKERS:-4}`.
- **H2. `.env.example` drift**: missing `UVICORN_WORKERS`, `REQUEST_TIMEOUT`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`; `REDIS_URL` uses db 0 in example vs db 1 in compose.
- **B7. `/static/` proxies to FastAPI** instead of being served by nginx directly. Mount `./static:/usr/share/nginx/html/static:ro` and `try_files` ahead of upstream.

### NIT

- **A3. Dockerfile `EXPOSE 5000` (Flask legacy)** — drop.
- **B8. `worker_processes auto;`** + `worker_connections 1024;` adequate for now.
- **C2. basset_api `start_period: 30s`** is tight given uvicorn + 4 workers + neo4j driver warmup; bump to 60s.

---

## 5. Recommendations Ordered by Impact-to-Effort

1. Fix celery healthcheck (C1) — 10 min. BLOCKER.
2. Fix `Connection` header / keepalive map (B5) — 5 min. May finally unlock Phase 9 concurrency. MAJOR.
3. Align nginx proxy timeouts to 35s vs REQUEST_TIMEOUT=30 (B4) — 2 min. MAJOR.
4. Add `mem_limit` to every service (F1) — 15 min. MAJOR.
5. Apply `limit_req` to `location /` (B3) — 5 min. MAJOR.
6. Gate or remove `/neo4j/` route (B6) — 30 min. BLOCKER for prod.
7. Move secrets to `${VAR:?required}` interpolation (E2, E3, H1) — 20 min. MAJOR.
8. Strip TeXLive or move to sidecar (A2) — 1-2 hr after usage audit. MAJOR.
9. HSTS / CSP / Permissions-Policy + `server_tokens off;` (B1, B2) — 15 min. MINOR.
10. Reconcile `.env.example` with compose (H2) — 10 min. MINOR.
11. Pin base image by digest (A1) and drop `EXPOSE 5000` (A3) — 10 min. MINOR/NIT.

---

## 6. Cross-checks against existing handoffs

- `NGINX-KEEPALIVE-FIX.md` documents the 32->256 bump. Necessary but not sufficient — B5 still defeats the pool on non-WS requests. Amend the handoff.
- `MULTI-WORKER-CONFIGURATION.md` recommends `least_conn` / `ip_hash` to "fix uneven load distribution." That advice is wrong for uvicorn workers behind a single container — the kernel's `SO_REUSEPORT` already distributes accepts across workers inside `basset_api`. The real lever is fixing B5 so the upstream keepalive pool actually recycles.
- `docker-compose.dev.yml` correctly scopes direct port exposure to dev. Good separation.

---

**No infra files modified.** Only `docs/findings/2026-05-20-docker-nginx-review.md` created.
