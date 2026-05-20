# Uncommitted Diff Review — 2026-05-20

**Reviewer:** reviewer@basset-hound:uncommitted-diff
**Scope:** All files modified per `git diff HEAD` (excluding untracked docs)
**Context:** API container reported "unhealthy"; workers stuck in lifespan startup.
Recent stated fixes: (a) `bcrypt<4.0.0` pin, (b) replace malformed
`MATCH (n:Project) LIMIT 1` health probe with `driver.get_server_info()`.

---

## Per-file findings

### 1. `requirements.txt` — **CLEAN**

Diff adds a single line:
```
+bcrypt<4.0.0
```
Matches the stated fix for the passlib/bcrypt 4.x ABI incompatibility
(passlib<=1.7.4 calls `bcrypt.__about__.__version__`, removed in bcrypt 4.0).
Pin is correct. No regression risk. **Recommendation:** ship as-is.

### 2. `.env.example` — **MINOR**

Renames `NEO4J_POOL_SIZE` → `NEO4J_MAX_CONNECTION_POOL_SIZE` and sets the
template value to **150**, while production `.env` and `api/config.py` both
default to **500**. The example will mislead developers into provisioning an
undersized pool.
**Evidence:** `.env.example:13` (`NEO4J_MAX_CONNECTION_POOL_SIZE=150`) vs
`api/config.py:79` (`default=500`) and `.env:14` (`=500`).
**Recommendation:** raise the example to `500` (or document both tiers).

### 3. `.env` — **MAJOR**

Two concerns:

1. **Secret in tracked file.** `.env` is listed in `.gitignore` (line 10) but
   remains tracked because it was committed before the ignore rule. This diff
   does not *add* a new secret (`NEO4J_PASSWORD=neo4jbasset` and
   `SECRET_KEY=development-secret-key-change-in-production` were already
   present), but the file is being modified again and will keep these values
   in history. Not introduced by this change, but worth flagging before commit.
2. **Conflicting `REQUEST_TIMEOUT` value.** `.env:115` sets `REQUEST_TIMEOUT=5`
   with a comment saying "Changed from 30 to 5 seconds to fail fast"
   whereas `docker-compose.yml:170` sets `REQUEST_TIMEOUT=30`. Container
   `environment:` wins over `.env` in compose, so the production deploy uses
   30s. The 5s value in `.env` is then misleading and almost certainly wrong
   anyway: many legitimate Neo4j queries (constraint setup, platform seeding,
   first-time index build) exceed 5s, so if the override ever leaks into the
   container it would cause a 504 cascade and *look exactly like the hang
   currently being observed* (see "Theory on the API hang" below).

**Recommendation:** decide on one value (30s is safer), set it in both files,
and remove the conflicting "CRITICAL FIX" comment.

### 4. `api/config.py` — **CLEAN**

Defaults bumped (Neo4j pool 50→500, Redis 100→300) and new `request_timeout`
field added with default 5. The new field is read via `os.getenv` directly in
`main.py` (see file 5), not via `settings.request_timeout`, so the field is
documentation-only at the moment — harmless. **Recommendation:** ship; consider
following up to read it from `settings` for consistency.

### 5. `api/main.py` — **MAJOR**

Two issues:

1. **Timeout default mismatch.**
   `api/main.py:275` reads
   ```python
   request_timeout = int(os.getenv("REQUEST_TIMEOUT", "30"))
   ```
   but `api/config.py:199` defaults the same setting to **5**, and `.env:115`
   sets it to **5**. Three different defaults across three files. Behaviour
   depends on whether the container has `REQUEST_TIMEOUT` in its env block
   (yes, =30 — see docker-compose.yml:170), so prod is 30s by accident.
   **Recommendation:** read from `get_settings().request_timeout` for a single
   source of truth.

2. **Middleware ordering inverts the comment.**
   The new code adds `request_timeout_middleware` via `@app.middleware("http")`
   (line 281) **before** `app.add_middleware(TimedMiddleware)` (line 321) and
   the existing `add_process_time_header` (line 326). In Starlette, middleware
   added later wraps middleware added earlier — i.e. the *outermost* request
   handler is the last one registered. So the actual call order on the request
   path is:
   `add_process_time_header → TimedMiddleware → request_timeout_middleware → router`.
   The comment claims "must be added before other middleware" and "timing
   middleware (after timeout middleware)" — both inverted. Functionally the
   timeout still fires, but `TimedMiddleware` metrics will *not* count requests
   killed by the 504 (the timeout returns from inside, before metrics record),
   which is the opposite of what's typically wanted.
   **Evidence:** `api/main.py:281-313` (timeout middleware) registered before
   `api/main.py:320-321` (`TimedMiddleware`) and `api/main.py:326-340`
   (`add_process_time_header`).
   **Recommendation:** either reorder so the timeout middleware is added last,
   or update the comments to reflect actual semantics.

Additionally, **pre-existing bug now more likely to bite**:
`api/main.py:92` calls `neo4j_handler.setup_schema_from_config(config)` *after*
the try/except at line 76-85 has already logged a warning and left
`neo4j_handler = None`. With graceful degradation enabled, an `AttributeError`
is raised and caught by the outer except at line 114, swallowing the schema
setup silently. Not introduced by this diff, but blocks any attempt to start
the API without Neo4j and may interact with the current hang.

### 6. `api/services/neo4j_service.py` — **MAJOR**

Adds a `CircuitBreaker` class (5 failures / 60s timeout) and wraps `query()`
in it. Pool size now reads `NEO4J_MAX_CONNECTION_POOL_SIZE` from env (default
500). The `connect()` method itself is unchanged in retry behaviour: still up
to 30 attempts × 2.0s delay = **~60s worst case before raising**, and the
lifespan calls it twice (once via `Neo4jHandler()` synchronously, once via
`async_service.connect()` in `main.py:99`). The doubled retry budget is the
most plausible cause of a multi-minute lifespan stall.

**Specific concerns:**

1. **Reference to `ServiceUnavailable` and `logger` outside their definitions.**
   The `CircuitBreaker` class is declared at module top (lines 32-120) but
   references `asyncio` (imported line 9 — OK), `time` (line 15 — OK),
   `logger` (defined further down in the module — **risk: NameError at class
   instantiation if called at import time**, but it's only used inside
   methods, so lazy lookup is fine), and `ServiceUnavailable` (imported from
   `neo4j.exceptions` line 24 — OK).
   **Verified safe** at runtime; flag is informational.

2. **Circuit-breaker lock acquired twice per call.**
   `CircuitBreaker.call` acquires `self._lock` in two separate critical
   sections (pre-check, post-result). Between them, multiple concurrent callers
   can sneak past the OPEN check after a reset. Minor race; not a blocker for
   commit but worth a follow-up.

3. **Pool size 500 + Neo4j default `dbms.connector.bolt.thread_pool_max_size`
   = 400.** If Neo4j is left at defaults, the driver pool can request more
   connections than the server will serve, producing acquisition timeouts that
   feed straight into the new circuit breaker. **Recommendation:** verify
   `NEO4J_dbms_connector_bolt_thread__pool__max__size` is raised in
   docker-compose or document the prerequisite.

4. **The health-check fix is *not* in this diff.** `api/main.py:389` calls
   `neo4j_handler.driver.get_server_info()` — this is the synchronous Bolt
   driver from `neo4j_handler` (not the async service). The change appears
   to already be committed (it's not in `git diff HEAD`). Mentioning because
   the task asked to verify the fix; what's left to commit does not touch it.

### 7. `docker-compose.yml` — **BLOCKER (likely root cause)**

```yaml
command: >
  uvicorn api.main:app
  --host 0.0.0.0
  --port 8000
  --workers 4
```

Combined with `lifespan=lifespan` on the FastAPI app, **every one of the 4
workers runs the full startup sequence independently**: each calls
`Neo4jHandler()` + `async_service.connect()` + `setup_indexes()` +
`ensure_platforms_seeded()` against the same Neo4j instance.

With pool size 500 per worker × 4 workers = 2000 advertised connections vs a
Neo4j default cap of ~400, plus four concurrent schema/index/seed batches
hammering the same constraints, this will:
- saturate Neo4j's connection acceptor,
- cause `connect()`'s 30-attempt retry loop to spin for the full 60s on at
  least three workers,
- trip Docker's healthcheck `start_period: 30s` (line 187) **before** any
  worker finishes lifespan, marking the container "unhealthy".

This matches the reported symptom exactly: "workers stuck in lifespan startup,
container unhealthy."

**Evidence:** `docker-compose.yml:153-157` (`--workers 4`) + `api/main.py:60-194`
(lifespan runs per-worker) + `api/services/neo4j_service.py:328-393`
(30×2s retry) + `docker-compose.yml:187` (`start_period: 30s`).

**Recommendation (any one of):**
- Drop to `--workers 1` until startup is idempotent and lightning-fast, **or**
- Move schema/index/seed into a one-shot init container that runs before the
  API starts, **or**
- Increase healthcheck `start_period` to `120s` and reduce the `connect()`
  retry budget so a failed worker dies fast instead of looking healthy-then-
  unhealthy.

Also note `UVICORN_WORKERS=4` (line 169) is exported but unused — the `command`
override sets workers via CLI flag. Remove the env var to avoid confusion.

### 8. `nginx/nginx.conf` — **CLEAN**

`keepalive 32 → 256` for the `basset_api` upstream. Reasonable for 4-worker
fan-out. Ship as-is.

---

## Theory on the API hang — **HIGH confidence (~85%)**

**Root cause:** the `--workers 4` change in `docker-compose.yml` (file 7) is
incompatible with the current lifespan implementation. Each worker independently
runs the full Neo4j connect + schema setup + index creation + platform seeding
sequence at boot. Against a freshly-started Neo4j with default thread-pool caps,
the four workers contend for connections, fall into the 60s retry loop, and the
30s healthcheck `start_period` fires before any worker reaches
`yield`. The container is then marked unhealthy and the cycle restarts.

Secondary aggravators:
- bcrypt pin (file 1) is fine; not implicated.
- New circuit breaker (file 6) doesn't fire at startup because connect() and
  ensure_constraints() bypass `query()`.
- Conflicting `REQUEST_TIMEOUT` (5 in .env vs 30 in compose) would cause
  request-time symptoms, not lifespan stalls, so it's not *the* hang but it's a
  ticking bomb.

**Disconfirming evidence to check:** if `docker logs basset_api` shows
`Connected to Neo4j` four times followed by stalled `setup_indexes`, the theory
is confirmed. If only one connection succeeds and the others log AuthError, the
issue is credential-related instead.

---

## Net commit-readiness verdict

**BLOCKED.**

Must-fix before commit:
1. Resolve `--workers 4` × per-worker lifespan startup conflict
   (`docker-compose.yml:153-157`). This is almost certainly the active hang.
2. Reconcile `REQUEST_TIMEOUT` value across `.env`, `docker-compose.yml`,
   `api/config.py`, and `api/main.py` — pick one source (recommend `settings`).
3. Either reorder or relabel the timeout middleware vs `TimedMiddleware`
   (`api/main.py:275-321`).

Should-fix (non-blocking):
4. Raise `.env.example` pool size to match `api/config.py` default.
5. Confirm Neo4j server-side thread-pool ceiling supports pool size 500 × 4.
6. Add a regression test that boots the app with `--workers 4` and asserts
   `/health` returns 200 within 60s.

Once items 1-3 are addressed, the change set (bcrypt pin, health-probe fix,
pool sizing, circuit breaker, GZip-compatible timeout middleware) is a solid
forward step and worth committing.

---

**Word count:** ~1,420
