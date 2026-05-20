# Findings Index

Research and analysis outputs. Newest sessions first.

## 2026-05-20 — Multi-Agent Audit & Hardening

Session record: [`docs/archives/session_records/2026-05-20_Multi-Agent-Audit-And-Hardening.md`](../archives/session_records/2026-05-20_Multi-Agent-Audit-And-Hardening.md)
Master synthesis: [`docs/handoffs/MASTER-HANDOFF-2026-05-20.md`](../handoffs/MASTER-HANDOFF-2026-05-20.md)

### Audit findings (Waves 1-3)
| File | Topic |
|------|-------|
| [handoffs-consolidation-audit](2026-05-20-handoffs-consolidation-audit.md) | ~85 handoff docs proposed for archival |
| [neo4j-service-refactor-proposal](2026-05-20-neo4j-service-refactor-proposal.md) | 6-phase blueprint to split the 2,301-line service |
| [uncommitted-diff-review](2026-05-20-uncommitted-diff-review.md) | Review of staged changes; flagged REQUEST_TIMEOUT drift |
| [test-coverage-gap-analysis](2026-05-20-test-coverage-gap-analysis.md) | 22/54 services tested; 7 at 0% coverage |
| [router-surface-audit](2026-05-20-router-surface-audit.md) | 58 routers, orphans + duplicate-prefix bugs |
| [security-recheck](2026-05-20-security-recheck.md) | CRITICAL-GAPS verdict — note: auth findings are out-of-scope per user |
| [docker-nginx-review](2026-05-20-docker-nginx-review.md) | nginx keepalive root-cause hypothesis, healthcheck bugs |
| [frontend-static-audit](2026-05-20-frontend-static-audit.md) | Broken minifier, dead assets, 4MB of logos |
| [dependency-audit](2026-05-20-dependency-audit.md) | python-dotenv CVE, loose pins, bcrypt migration path |

### Cleanup notes (Waves 5-6)
| File | Topic |
|------|-------|
| [wave5-cleanup-router](2026-05-20-wave5-cleanup-router.md) | 3 orphan routers deleted (1,497 LOC) |
| [wave5-cleanup-frontend](2026-05-20-wave5-cleanup-frontend.md) | 288 KB dead frontend assets removed |
| [wave5-cleanup-deps](2026-05-20-wave5-cleanup-deps.md) | python-dotenv CVE + 4 pin upper-bounds |
| [wave6-analytics-shim](2026-05-20-wave6-analytics-shim.md) | analytics.py shim removed |
| [wave6-normalizer-tests](2026-05-20-wave6-normalizer-tests.md) | 70 new unit tests for normalizer_v2 |

## Earlier sessions

Pre-2026-05-20 findings (Phase 8, search optimization, vision research, session summaries) also live in this directory — filenames are dated or topic-prefixed.
