# Security Posture Re-check (2026-05-20)

**Auditor:** security-reviewer@basset-hound:posture-recheck
**Scope:** Verify claims in `FINAL-SECURITY-AUDIT-REPORT.md` and `SECURITY-AUDIT-PHASE8-FINAL.md` against code in `api/auth/`, `api/middleware/`, `api/utils/encryption.py`, `api/utils/rate_limiting.py`, plus reachable callers.
**Method:** Static review only. No exploit attempts, no live traffic.

---

## 1. Per-Finding Status Table

| # | Claim | Status | Citation |
|---|---|---|---|
| 1.1 | JWT HS256, signed, exp checked, type enforced | VERIFIED | `api/auth/jwt.py:99,186,220,245-253` |
| 1.2 | Refresh endpoint validates `expected_type="refresh"` | VERIFIED | `api/auth/routes.py:236` |
| 1.3 | All protected endpoints require auth | **DRIFTED** | Only `collaboration`, `export`, `ml_analytics` carry auth deps. ~50 routers (projects, search, entities, accounts, import_data, relationships, files, webhooks, bulk, mcp, marketplace, etc.) have **zero**. |
| 1.4 | 11 export endpoints require `current_user` | PARTIAL | `export.py:384,503,592,698,757,828,898,963,1069` — 9 endpoints carry the dep. Effective only when `AUTH_ENABLED=true`; `.env:30` ships `false`. |
| 1.5 | `_verify_project_access` raises 403 on non-member | **DRIFTED** | `export.py:273-323` — membership check is a `TODO` comment (lines 304-309). Any authenticated user reaches every project. |
| 1.6 | No hardcoded credentials | PARTIAL | `config.py:128` ships default `secret_key`; `.env:33` ships that literal; `routes.py:130,136` defaults admin/user passwords to `admin`/`user`. |
| 1.7 | No tokens/passwords logged | VERIFIED | grep on routers/services clean. |
| 1.8 | Session timeouts (30 min / 7 d) | VERIFIED | `config.py:133-142`, `jwt.py:175,212` |
| 2.1 | "AES-256" on dumps | VERIFIED w/ caveat | `encryption.py:98-156`. Fernet = **AES-128-CBC + HMAC-SHA256**, not 256. Construction sound; label inaccurate. |
| 2.2 | Encryption keys env-only | PARTIAL | `encryption.py:95` hardcodes fallback `"basset-hound-default-encryption-key-v1"`. If `DUMP_ENCRYPTION_KEY` unset, dumps are encrypted under a public-string key — equivalent to none. |
| 2.3 | TLS at deployment layer | DEFERRED | nginx, out of code scope. |
| 2.4 | bolt/env-credentialed Neo4j | VERIFIED | `config.py:58-69` |
| 2.5 | Dumps mandatorily encrypted | VERIFIED | via `EncryptionManager`. |
| 3.1 | No SQL injection (N/A) | VERIFIED | Neo4j-only. |
| 3.2 | No f-strings/format in Cypher | **DRIFTED** | `services/neo4j_service.py:2094` interpolates `set_clauses` (from `kwargs.keys()`) into Cypher. Currently bounded by `PlatformUpdate` Pydantic schema (`routers/platforms.py:244`), so not reachable — but the absolute claim is false. |
| 3.3 | No XSS | VERIFIED | JSON API + Jinja2 autoescape. |
| 3.4 | No command injection | VERIFIED | No `os.system`/`subprocess` on user input. |
| 4.1 | PII redaction | VERIFIED | `ml_analytics_service.py` (referenced). |
| 4.2 | Sensitive data not logged | VERIFIED | See 1.7. |
| 4.3 | Audit logging on sensitive ops | PARTIAL | `export.py:313-321` logs; `projects/entities/import_data` do not. |
| 4.4-4.5 | Data/backups at rest encrypted | VERIFIED via 2.5 | Same path. |
| 5.1 | CORS not wildcard | **DRIFTED** | `config.py:41`, `.env:50` ship `CORS_ORIGINS=*`. |
| 5.2 | Rate limiting enforced per-user | PARTIAL | `rate_limiting.py:22-69` is **process-local**. With 4 Uvicorn workers (`.env:109`), effective limit = `4 × max`. Key-fn fallback (`156-176`) collapses all unauth callers to a single shared `"anonymous"` bucket. |
| 5.3 | Pydantic input validation | VERIFIED | Used throughout. |
| 5.4 | Errors don't leak info | PARTIAL | `main.py:354` puts `str(exc)` in 500 body when `settings.debug`; `.env:22` ships `DEBUG=true`. |
| 5.5 | 30-s request timeout | DRIFTED | `main.py:278` defaults 30s only if unset; `.env:115` sets 5s. |
| 5.6 | Docs disabled in prod | **DRIFTED** | `main.py:257-259` hard-codes `/docs`, `/redoc`, `/openapi.json`; no env gate. |
| 6.1 | Secrets via env | PARTIAL | See 1.6, 2.2. |
| 6.2-6.3 | Docker / network | OUT OF SCOPE | — |
| 6.4 | Logging + audit | VERIFIED | `audit_logger.py` + structlog. |
| 7.x | GDPR / OWASP / SOC2 | **OVERSTATED** | Gaps in 1.3 + 1.5 alone defeat OWASP A01 / A07 and GDPR access-control obligations. |

### Phase-8-specific claims (`SECURITY-AUDIT-PHASE8-FINAL.md`)

Items 1, 2, 4, 5, 6 (autocomplete privacy — `search.py:1214-1221` confirms empty-suggestions for anonymous): VERIFIED. Item 3 (Cypher injection): DRIFTED, see 3.2. Item 7 (rate limiting): PARTIAL, see 5.2. Items 8/18 (export auth + project ownership): PARTIAL — auth dep present, ownership TODO. Item 13 (hardcoded secrets): DRIFTED — `.env` ships the literal default.

---

## 2. New Issues Discovered

### P0 — `AUTH_ENABLED=false` in committed `.env`
`.env:30`. `api/auth/dependencies.py:125-132` short-circuits every auth-gated endpoint to a synthetic `User(scopes=["*"])`. If this `.env` is the deployment basis, all collaboration/ml_analytics auth becomes a no-op. (`api/dependencies.py:210` `get_current_user`, used by `export.py`, does **not** honour `AUTH_ENABLED` — see P1; export still 401s.)

### P0 — Default admin/user passwords are `admin`/`user`
`api/auth/routes.py:130,136`. With unset `ADMIN_PASSWORD`/`USER_PASSWORD`, the in-memory store accepts `admin:admin`. Combined with shipped default `SECRET_KEY`, any forgotten override exposes a trivial admin login issuing `scopes=["*"]` tokens.

### P0 — Project ownership check is a TODO
`api/routers/export.py:304-309`. The function returns the project to any authenticated user; the FINAL audit's "User A cannot access User B's projects, verified by test" assertion is unsupported by code.

### P0 — Vast majority of routers have no authentication
No `Depends(get_current_user|require_auth|CurrentUser)` in: `projects, entities, accounts, search, import_data, bulk, relationships, files, webhooks, analytics_v2, analysis, auto_linker, browser_actions, cache, cletus_integration, config, cross_project, crypto, data_quality, deduplication, entity_types, graph, graph_analytics, graph_format, import_mapping, integrations, jobs, llm_export, marketplace, mcp, orphan, osint, platforms, plugins, reports, reports_pdf, report_storage, saved_search, suggestions, templates, timeline, timeline_visualization, utils, verification, visualization, websocket, audit`. CRUD on projects/entities, imports, cross-project queries, MCP tool invocation, bulk operations all unauthenticated. The single most material gap.

### P1 — Two `get_current_user` implementations diverge
`api/dependencies.py:210` (used by `export.py`): JWT-only, does **not** check `AUTH_ENABLED`, returns `dict`. `api/auth/dependencies.py:116` (used by `collaboration.py`, `ml_analytics.py`): returns `User`, **does** honour `AUTH_ENABLED`. Same env var, different semantics per call site.

### P1 — No CSRF, no security headers
Search for `CSRFMiddleware`, `X-Frame-Options`, `Content-Security-Policy`, `Strict-Transport-Security`, `X-Content-Type-Options` in `api/`: zero hits. App also serves Jinja2 frontend routes (`api/routers/frontend*.py`) that submit forms — those are session-cookie territory in practice with no CSRF token, no `SameSite` controls. May be set in nginx — out of code scope.

### P1 — `DEBUG=true` ships in `.env`
`main.py:354` includes `str(exc)` in 500 body when `settings.debug`. `.env:22` ships `DEBUG=true`. Any uncaught error leaks internals.

### P1 — Encryption fallback key is a public constant
`api/utils/encryption.py:95` derives the key from the literal `"basset-hound-default-encryption-key-v1"` if `master_key` unset. Anyone with repo read access decrypts default-config dumps. The FINAL audit §2.2 claims fallback derives from `SECRET_KEY` — code does not.

### P2 — API key file storage default
`api/auth/api_key.py:101-103,277-294`. `APIKeyManager.__init__` auto-selects file storage (`data/api_keys.json`) when no `neo4j_handler` passed. No warning emitted.

### P2 — In-memory rate limiter has no eviction
`api/utils/rate_limiting.py:30-32`. Per-key request lists never removed when empty. Long-running process with many users leaks memory monotonically.

### P2 — `auto_error` mismatch between auth modules
`api/auth/dependencies.py:29` (`HTTPBearer(auto_error=False)`) vs `api/dependencies.py:196` (`OAuth2PasswordBearer`, auto-errors). Inconsistent 401 behaviour across modules.

### P3 — JWT algorithm read from env without whitelist
`jwt.py:48`. Misconfig (e.g. `JWT_ALGORITHM=none`) flows to `algorithms=[ALGORITHM]` (line 245). python-jose rejects `none` at the library level, so exploitable confusion is blocked there — but app code does not enforce a whitelist.

### P3 — `nbf` not enforced
`verify_token` (line 244) sets only `verify_exp`. Issued tokens don't include `nbf` today, so moot — but future patches adding `nbf` will skip its validation by default.

---

## 3. Bcrypt Pin Discussion

`requirements.txt:33-34` pins `passlib[bcrypt]>=1.7.4` + `bcrypt<4.0.0`.

**Reason for pin:** passlib 1.7.4 reads `bcrypt.__about__.__version__` at import; bcrypt 4.1.0 removed that attribute, causing `AttributeError`. Community fix is to pin `bcrypt<4.1.0`; `<4.0.0` is over-conservative and locks the legacy C-extension (3.2.x).

**Security profile of bcrypt 3.x:** no significant CVEs; 72-byte truncation is bcrypt-design (not version-specific); unmaintained since 2023. passlib 1.7.4 also unmaintained since 2020. Combination is a long-term liability, not an acute vulnerability.

**Recommended upgrade path (low risk, high benefit):**
1. Migrate to `argon2-cffi` via `passlib[argon2]`, drop bcrypt. Argon2id is OWASP-recommended.
2. Or: bump to `bcrypt>=4.1.0` and call `bcrypt.hashpw`/`checkpw` directly (drop passlib wrapper, which now adds no security value).
3. Re-hash on next login (`deprecated="auto"` already supports this).

**Severity: P3** — no active exploit, becomes P2 once passlib breaks against a future Python release.

---

## 4. Drift Summary (docs vs code)

| Doc Claim | Reality |
|---|---|
| "36/36 checks passed, 0 issues" | At least 12 substantive gaps (P0×4, P1×4, P2×3, P3×2). |
| "All sensitive endpoints have auth deps" | ~5% of routers do. |
| "User A cannot access User B's projects" | Ownership check is a `TODO`. |
| "No f-strings in Cypher" | One exists at `neo4j_service.py:2094`. |
| "30-s request timeout" | `.env` sets 5 s. |
| "AES-256 encryption" | AES-128-CBC + HMAC-SHA256. |
| "Must set DUMP_ENCRYPTION_KEY in prod" | Silent fallback to hardcoded constant. |
| "CORS not wildcard" | `.env` ships `*`. |
| "DEBUG=false in prod" | `.env` ships `true`. |
| "Disable Swagger in prod" | Not gate-able without code edit. |
| "GDPR/OWASP/SOC2 compliant" | Broken Access Control defeats this. |

---

## 5. Net Verdict

**CRITICAL-GAPS.**

The Phase-8-final audit correctly flagged the export-endpoint auth gap (now partially fixed: 9 endpoints have `Depends(get_current_user)`). The follow-on `FINAL-SECURITY-AUDIT-REPORT.md` declaring "0 issues / production ready / GDPR+OWASP+SOC2 compliant" is **not supported by code**. It conflates "auth dependency present" with "end-to-end access control", ignoring (a) `AUTH_ENABLED=false` shipping in `.env`, (b) the `TODO`-stubbed project ownership check, and (c) 50+ unauthenticated routers.

**Recommended next actions, in order:**
1. Set `AUTH_ENABLED=true` in `.env`; remove the bypass from `api/auth/dependencies.py` (treat the var as opt-out, never opt-in).
2. Apply a global `dependencies=[Depends(get_current_user)]` to `app.include_router(api_router, …)` in `main.py:660`; explicit opt-out for `/health`, `/auth/*`, `/api`.
3. Implement the project membership check in `_verify_project_access` (one Cypher query).
4. Remove demo `admin`/`user` users from `routes.py` or gate behind `if DEBUG`.
5. Require `JWT_SECRET_KEY` and `DUMP_ENCRYPTION_KEY` at startup (raise on missing).
6. Add security-headers middleware (HSTS, X-Frame-Options, X-Content-Type-Options, CSP, Referrer-Policy).
7. Gate `/docs`, `/redoc`, `/openapi.json` behind `settings.debug`.
8. Replace `str(exc)` leak in `main.py:354` with a correlation ID.
9. Move rate limiter to Redis-backed (Redis already a dependency).
10. Reconcile the two `get_current_user` implementations.
11. Schedule bcrypt→argon2 migration for next quarter.

Until items 1–5 land, the system should **not** be deployed to any environment handling real investigation data.

---

**Status:** REPORT COMPLETE. No code modified; only `docs/findings/2026-05-20-security-recheck.md` written.
