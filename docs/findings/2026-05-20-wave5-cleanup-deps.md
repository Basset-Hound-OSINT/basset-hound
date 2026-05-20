# Wave 5 Cleanup — Dependency Hygiene

**Date:** 2026-05-20
**Agent:** py-dev@basset-hound:dependency-hygiene
**Source audit:** `docs/findings/2026-05-20-dependency-audit.md` (Stream 9)
**Scope of edits:** `requirements.txt` only.

## Changes applied

| Dep | Old pin | New pin | Reason |
|---|---|---|---|
| python-dotenv | `==1.1.0` | `>=1.2.2,<2.0.0` | **CVE-2026-28684** symlink overwrite (critical); also reconciles 1.1.0 vs 1.0.1 drift flagged in audit section 5 |
| mypy | `>=1.13.0` | `>=1.13.0,<3.0.0` | Silent major bump 1.13 → 2.1 already occurred; cap below 3.x to prevent recurrence |
| pytest-asyncio | `>=0.24.0` | `>=1.0.0,<2.0.0` | Silent major bump 0.24 → 1.3 already occurred; floor raised to current major, capped below 2.x |
| phonenumbers | `>=8.13.0` | `>=8.13.0,<10.0.0` | Silent major bump 8.x → 9.x already occurred; cap below 10.x |
| websockets | `>=12.0` | `>=12.0,<17.0` | Silent major bump 12 → 16 already occurred; cap below 17.x (next-major guard) |

**Total deps modified:** 5 (matches plan: 1 CVE + 4 floating-pin tightens).

## Constraints honored

- `bcrypt<4.0.0` — left untouched (separate migration plan exists, audit section 6)
- `passlib[bcrypt]>=1.7.4` — left untouched (same)
- httpx duplicate — not re-touched (already fixed in earlier orchestrator pass; only one `httpx>=0.27.0` line present)
- Other 20 floating `>=` pins — intentionally left to minimize churn per task instructions
- All section headers and comments preserved; only inline reason-comments added on the 5 changed lines

## Validation

Ran the task's validation command (with pip-standard inline-comment stripping at ` #`, since the raw form fails on the pre-existing `jinja2  # Template rendering...` inline comment unrelated to this change):

```
Parsed OK: 34 | Errors: 0
```

All 34 requirement specifiers parse cleanly via `packaging.requirements.Requirement`. No syntactic regressions.

## Out of scope / deferred

The audit's section 3 also flagged tightening lower bounds on starlette, jinja2, python-jose, python-multipart, mcp, markdown, celery, redis — those are explicitly **not** in this task ("minimize churn — only the 4 listed + python-dotenv CVE"). They remain tracked in the Stream 9 audit for a follow-up wave.
