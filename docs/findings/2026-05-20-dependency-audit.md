# Dependency and Supply-Chain Audit

**Date:** 2026-05-20
**Scope:** `requirements.txt`, `frontend/package.json`, `frontend/package-lock.json`, `Dockerfile`
**Mode:** Offline — no network CVE feed access; assessment uses Stream 6 (`2026-05-20-security-recheck.md`) and prior scan (`docs/handoffs/security-dependency-scan-report.md` dated 2026-05-19) as baseline plus general SCA knowledge.
**Net verdict:** **NEEDS-UPDATE** — one CRITICAL CVE outstanding, pervasive loose pins, frontend uses end-of-life Storybook 7 line, bcrypt pin is over-conservative.

---

## 1. Python dependencies — full table

Risk legend: **C** = critical, **H** = high, **M** = medium, **L** = low, **info** = housekeeping.

| Package | Pin in repo | Installed (2026-05-19) | Latest stable (known) | Risk | Notes |
|---|---|---|---|---|---|
| fastapi | `>=0.115.0` | 0.136.1 | ~0.136.x | M | Loose — no upper bound; pre-1.0 minor releases can break. |
| uvicorn[standard] | `>=0.32.0` | 0.46.0 | ~0.46.x | L | Loose. |
| starlette | `>=0.41.0` | 0.52.1 | 0.52.x | **H** | Range allows historic CVE versions (5 CVEs <0.52.0). Pin lower bound to `>=0.52.0`. |
| jinja2 | `>=3.1.0` | 3.2.0 | 3.2.x | **H** | Range allows pre-3.1.5 sandbox-escape CVEs. Pin `>=3.1.5`. |
| prometheus-client | `>=0.21.0` | 0.21.0 | 0.21.x | L | Loose. |
| structlog | `>=24.0` | 24.4.0 | 24.x | L | Loose, low blast radius. |
| python-dotenv | `==1.1.0` | 1.0.1 | 1.2.2+ | **C** | **CVE-2026-28684 symlink overwrite.** Pin says `==1.1.0` but env shows 1.0.1 — drift. Update to `>=1.2.2`. |
| PyYAML | `==6.0.2` | 6.0.2 | 6.0.x | L | Tight pin, clean. |
| pydantic[email] | `>=2.10.0` | 2.13.4 | 2.13.x | L | v2; loose but no known active CVE. |
| pydantic-settings | `>=2.6.0` | 2.14.1 | 2.14.x | L | Loose. |
| email-validator | `>=2.1.0` | 2.3.0 | 2.3.x | L | Loose. |
| neo4j | `==5.28.1` | 5.28.1 | 5.28.x (5.x LTS) | L | Tight pin, current. |
| celery[redis] | `>=5.3.0` | 5.6.3 | 5.6.x | M | Loose; celery <5.4 had message-deserialization CVE. Pin `>=5.4`. |
| redis | `>=5.0.0` | 6.4.0 | 6.4.x | M | Loose; redis-py <5.0.1 had CVE-2023-31655-class issues. Acceptable but pin `>=5.0.1`. |
| python-jose[cryptography] | `>=3.3.0` | 3.5.0 | 3.5.x | **H** | Range allows pre-3.4 algorithm-confusion CVEs (2 known). Pin `>=3.5.0`. Consider migrating to PyJWT only. |
| passlib[bcrypt] | `>=1.7.4` | 1.7.4 | 1.7.4 (last release 2020-10) | **H** | Unmaintained 5+ years. See section 6. |
| bcrypt | `<4.0.0` | 3.2.x (legacy C-ext) | 4.2.x | **H** | **Over-conservative pin.** See section 6. |
| python-multipart | `>=0.0.12` | 0.0.28 | 0.0.28+ | **H** | Range allows pre-0.0.18 DoS CVEs (3 known). Pin `>=0.0.25`. |
| mcp | `>=1.0.0` | 1.25.0 | 1.25.x | M | Range allows pre-1.25 (3 CVEs). Pin `>=1.25.0`. |
| aiofiles | `>=24.1.0` | 25.1.0 | 25.x | L | Loose. |
| python-magic | `>=0.4.27` | 0.4.27 | 0.4.27 (last 2022) | M | Stable but slow-moving; relies on system libmagic1 (installed in Dockerfile). |
| markdown | `>=3.0.0` | 3.10.2 | 3.10.x | M | Range allows pre-3.6 XSS-class CVEs. Pin `>=3.6`. |
| matplotlib | `>=3.9.0` | 3.10.9 | 3.10.x | L | Loose. |
| pylatex | `>=1.4.2` | 1.4.2 | 1.4.2 (last 2022) | M | Quasi-abandoned; shells out to `latexmk`. Audit any user-controlled LaTeX paths for injection. |
| networkx | `>=3.0` | 3.4.2 | 3.4.x | L | Loose, broad bound. Tighten to `>=3.2,<4`. |
| httpx | `>=0.27.0` | 0.28.1 | 0.28.x | L | **Listed twice** (lines 52 and 61). De-dupe. |
| websockets | `>=12.0` | 16.0 | 16.x | L | Loose; major bump 12→16 OK at runtime. |
| pytest | `>=8.3.0` | 9.0.2 | 9.0.x | M | Range allows pre-9.0 CVE (1 known). Dev-only, low blast radius. Pin `>=9.0.0`. |
| pytest-asyncio | `>=0.24.0` | 1.3.0 | 1.x | L | Major version jumped silently (0.24 → 1.3). Pin `>=1.0,<2`. |
| pytest-cov | `>=5.0.0` | 7.1.0 | 7.x | L | Dev only. |
| ruff | `>=0.8.0` | 0.15.13 | 0.15.x | info | Dev only; floating major releases. |
| mypy | `>=1.13.0` | 2.1.0 | 2.x | info | Major version jumped silently (1.13 → 2.1). Dev only. |
| rapidfuzz | `>=3.0.0` | 3.14.5 | 3.14.x | L | Loose. |
| phonenumbers | `>=8.13.0` | 9.0.30 | 9.x | L | Major bump 8→9 happened without pin update. |
| cryptography (transitive) | — | 46.0.7 | 46.x | L | Pulled by `python-jose[cryptography]`; clean. |
| pyjwt (transitive) | — | 2.12.1 | 2.12.x | L | Clean. |

**Functional duplication:** `python-jose[cryptography]` and `pyjwt` both transitive — basset-hound only needs one JWT lib. python-jose itself is slow-moving (3.5.0 = 2025); migrating to `pyjwt>=2.10.0` is cleaner.

**Dependency drift detected:** `python-dotenv==1.1.0` pinned in repo but `1.0.1` installed in the scan environment — either the scan ran against a stale lock or the pin was bumped after the scan. Resolve before next deploy.

**Loose-pin density:** 24 of 33 direct deps use `>=` only with no upper bound. That is the dominant supply-chain risk in this repo: a fresh `pip install` next month may pull a yet-unreleased breaking minor.

---

## 2. Python deps grouped by purpose

- **Web framework:** fastapi, uvicorn, starlette, jinja2
- **Async tooling:** httpx (x2 — dedupe), aiofiles, websockets
- **DB drivers:** neo4j, redis, celery[redis]
- **Auth/crypto:** python-jose, passlib, bcrypt, python-multipart, cryptography (transitive), pyjwt (transitive) — **two JWT libs is redundant**
- **ML/analytics:** matplotlib, networkx, rapidfuzz
- **Reports:** markdown, pylatex, matplotlib
- **MCP/integration:** mcp, websockets
- **Config:** python-dotenv, PyYAML, pydantic, pydantic-settings, email-validator
- **Testing/dev:** pytest, pytest-asyncio, pytest-cov, ruff, mypy
- **Other:** structlog, prometheus-client, python-magic, phonenumbers

---

## 3. Top 10 highest-risk dependencies

1. **python-dotenv** — CVE-2026-28684 critical symlink overwrite; pin says `==1.1.0` but env has 1.0.1. **Fix today.**
2. **bcrypt `<4.0.0` + passlib 1.7.4** — both unmaintained; pin is over-conservative (see section 6).
3. **starlette `>=0.41.0`** — range admits 5 known CVEs.
4. **jinja2 `>=3.1.0`** — range admits 5 known CVEs incl. sandbox escapes.
5. **python-jose `>=3.3.0`** — range admits 2 algorithm-confusion CVEs.
6. **python-multipart `>=0.0.12`** — range admits 3 DoS CVEs.
7. **passlib 1.7.4** — last release Oct 2020 (5.5 yrs unmaintained); strategic liability.
8. **mcp `>=1.0.0`** — 3 known CVEs in range; pin tightening trivial.
9. **markdown `>=3.0.0`** — pre-3.6 XSS risk; reports are rendered as HTML.
10. **pylatex 1.4.2** — quasi-abandoned, shells to external latexmk; review for shell injection on user-supplied content.

---

## 4. Frontend (`frontend/package.json`) audit

All deps use `^` caret pins — minor/patch float. `package-lock.json` exists (15k lines) so installs are reproducible if `npm ci` is used; if `npm install` is run, the caret pins will refloat.

| Package | Pin | Risk | Notes |
|---|---|---|---|
| react | `^18.2.0` | L | Current major. |
| react-dom | `^18.2.0` | L | Matches react. |
| zustand | `^4.5.0` | L | Stable. |
| clsx | `^2.1.0` | L | Tiny, low risk. |
| @types/react | `^18.2.0` | info | Types only. |
| @types/react-dom | `^18.2.0` | info | Types only. |
| @vitejs/plugin-react | `^4.2.0` | L | Build-time. |
| typescript | `^5.3.0` | L | Build-time. |
| vite | `^5.0.0` | M | Vite 5 had esbuild dev-server CVE (GHSA-67mh-4wv8-2f99 class); ensure lockfile resolves esbuild >=0.25.0. Caret-5 will pull vite 5.x; consider bump to vite 6 LTS. |
| vitest | `^1.2.0` | M | Vitest 1.x is EOL line; current is 2.x/3.x. |
| @testing-library/react | `^14.1.0` | L | Test-only. |
| @testing-library/jest-dom | `^6.2.0` | L | Test-only. |
| jsdom | `^23.2.0` | M | Historic DOM-clobbering issues; ensure transitive `tough-cookie` is `>=4.1.3` (CVE-2023-26136 prototype pollution). |
| @storybook/react | `^7.6.0` | **H** | **Storybook 7.x is end-of-life Jan 2026**; SB 8 is current. Multiple advisories in SB7 (esbuild, vite-plugin issues) closed only in SB8. |
| @storybook/react-vite | `^7.6.0` | **H** | Same EOL exposure. |
| eslint | `^8.56.0` | M | ESLint 8 reached EOL 2024-10; current is 9.x. Lint-only, low runtime risk. |
| eslint-plugin-react-hooks | `^4.6.0` | L | Lint-only. |
| @typescript-eslint/eslint-plugin | `^6.19.0` | M | v6 line EOL; current is v8. |
| @typescript-eslint/parser | `^6.19.0` | M | Same. |

**Transitive watchlist (verify in `package-lock.json`):** `axios` (not a direct dep — confirm not pulled via Storybook), `lodash` (Storybook tree), `follow-redirects` (axios tree), `tough-cookie` (jsdom tree), `semver` (broad), `postcss` (vite), `esbuild` (vite). The frontend has no direct axios/lodash imports, which is good.

**No production runtime CVEs** in direct frontend runtime deps (react/zustand/clsx). Frontend risk is concentrated in **dev/build tooling** which still affects developer machines and CI.

---

## 5. Pin-hygiene observations

- 24 of 33 Python deps use `>=` with no upper bound — major version drift can land silently (already seen with mypy 1.13 → 2.1, pytest-asyncio 0.24 → 1.3, phonenumbers 8 → 9, websockets 12 → 16).
- `httpx` listed twice (lines 52 and 61) — harmless to pip but indicates the file is hand-maintained and drift-prone.
- `python-dotenv==1.1.0` pinned in repo vs. `1.0.1` in scan environment — investigate (CI uses different file? Lockfile mismatch?).
- No `requirements.lock` / `pip-tools` / `poetry.lock` — installs are not reproducible. Highest-leverage single fix.
- Frontend uses `^` (caret) on every dep; `npm ci` against lockfile is the only thing keeping installs deterministic. Confirm CI uses `npm ci`, not `npm install`.

---

## 6. bcrypt pin — concrete migration path

**Current state (from Stream 6 recheck):**
- `passlib[bcrypt]>=1.7.4` + `bcrypt<4.0.0`.
- passlib 1.7.4 reads `bcrypt.__about__.__version__` at import; bcrypt 4.1.0 removed that attribute → `AttributeError`.
- Community fix is `bcrypt<4.1.0`; the current `<4.0.0` is **one minor more conservative than needed** and locks the legacy C-extension (3.2.x).
- bcrypt 3.x has no known CVEs but is unmaintained since 2023. passlib has been unmaintained since Oct 2020.

**Recommended path — Option A (preferred): migrate to argon2-cffi**

```text
# requirements.txt
passlib[argon2]>=1.7.4    # replaces passlib[bcrypt]
# bcrypt<4.0.0            # remove entirely
argon2-cffi>=23.1.0       # added transitively by passlib[argon2], but pin explicitly
```

Code change: in the user/auth service, switch the passlib `CryptContext` schemes from `["bcrypt"]` to `["argon2", "bcrypt"]` (argon2 default for new hashes, bcrypt kept for verifying legacy hashes). On next login of each user, transparently re-hash to argon2 via `pwd_context.verify_and_update()`.

- **Effort:** ~2-4 hours: requirements change, ~10 lines in auth service, migration plan for existing hashes (lazy rehash on login), unit test update.
- **Risk:** Low. passlib's `verify_and_update` pattern is well-trodden. Existing bcrypt hashes keep working until each user next logs in.
- **Benefit:** Drops the dead C-extension; argon2id is OWASP 2024 first-choice; eliminates the bcrypt-4.x pin trap.

**Option B (fallback): drop passlib, use bcrypt directly**

```text
bcrypt>=4.1.0,<5
# remove passlib entirely
```

- **Effort:** ~3-5 hours: rewrite the password-hashing helper to call `bcrypt.hashpw` / `bcrypt.checkpw` directly; remove passlib import sites.
- **Risk:** Medium. Existing passlib-formatted bcrypt hashes (`$2b$...`) are byte-compatible with `bcrypt.checkpw`, so backward verification works, but identifier rounds/format need verification on real production hashes.
- **Benefit:** Drops two unmaintained deps at once. Loses passlib's identifier-prefix multi-scheme abstraction.

**Recommendation:** **Option A.** Schedule for the next sprint. Stream 6 already classified this as **P3 today, P2 once passlib breaks against a future Python release.** Python 3.13 is the deadline-pressure horizon.

---

## 7. Abandoned / slow-moving packages

| Package | Last release | Status |
|---|---|---|
| passlib | 2020-10-08 (1.7.4) | Effectively abandoned |
| bcrypt 3.x | 2023 | Unmaintained line |
| pylatex | 2022 (1.4.2) | Quasi-abandoned |
| python-magic | 2022 (0.4.27) | Stable but slow |

Storybook 7 line is **planned-EOL by maintainer**, not abandoned.

---

## 8. Immediate action checklist

1. **Today:** Bump `python-dotenv` to `>=1.2.2`, reconcile the `==1.1.0` vs `1.0.1` drift.
2. **This week:** Tighten lower bounds on jinja2, starlette, python-jose, python-multipart, mcp, markdown, celery (see Stream 6 recommendations and section 3).
3. **This sprint:** Generate a lockfile (`pip-compile` or migrate to `uv`/`poetry`); add `npm ci` enforcement in CI if not already.
4. **Next sprint:** Execute Option A bcrypt → argon2 migration; remove the duplicate `httpx` line.
5. **Next quarter:** Plan Storybook 7 → 8 upgrade and ESLint 8 → 9 in frontend tooling; remove deprecated `python-jose` in favor of `pyjwt` only.

---

**Net verdict:** **NEEDS-UPDATE** — not CRITICAL because the one critical CVE (python-dotenv) is a single-line fix and the bcrypt/passlib situation has no active exploit. The dominant issue is **pin hygiene**: 24 unbounded `>=` pins and no lockfile mean today's "clean" install is one upstream release away from regressing. Fix the CVE, tighten the seven flagged ranges, and introduce a lockfile — after that the project clears to CLEAN.
