# Handoffs Documentation Consolidation Audit

**Date**: 2026-05-20
**Author**: analyst@basset-hound:docs-consolidation
**Status**: PROPOSAL — no files have been moved. Human review required before executing the `git mv` block.
**Target directory**: `docs/handoffs/archive/2026-05/` (does not yet exist)

---

## 1. File Counts

| Location | .md count | Notes |
|---|---|---|
| `docs/*.md` (top level) | 64 | Mixed canonical references + Phase-8 deliverables |
| `docs/handoffs/*.md` | 131 | Phase-8 working files (target of this audit) |
| `docs/handoffs/*.txt` and `*.sh` | 9 | AUDIT-SUMMARY.txt, INDEX-AGENT-DEPLOYMENT.txt, etc. |
| `docs/findings/*.md` | 78 | Older historical research (do not touch) |
| Combined md (handoffs + top-level docs) | **195** | per `wc -l` |

Recent activity: 130 of 131 handoff `.md` files were created on 2026-05-19 within a 7-hour window; only `AGENT-WORK-PLAN-2026-05-20.md` is dated 2026-05-20.

---

## 2. Per-Topic Consolidation Table

Legend: **K** = KEEP at current path · **A** = ARCHIVE to `docs/handoffs/archive/2026-05/` · **H** = HISTORICAL (keep, dated)

### 2.1 CHAOS Testing (8 files)
| Action | File | Rationale |
|---|---|---|
| K | `CHAOS-TESTING-REPORT.md` (21 KB, 22:29) | Canonical, largest, earliest of the polished set |
| K | `CHAOS-TESTING-INDEX.md` (9.5 KB, 22:32) | Active navigation hub |
| H | `CHAOS-EXECUTION-RESULTS-2026-05-19.md` | Dated execution record |
| A | `CHAOS-TEST-EXECUTION-PLAYBOOK.md` | Procedure folded into REPORT |
| A | `CHAOS-TESTING-EXECUTION-SUMMARY.md` | Superseded by EXECUTIVE-SUMMARY-2026-05-19 |
| A | `CHAOS-TESTING-EXECUTIVE-SUMMARY-2026-05-19.md` | Subsumed by INDEX + REPORT |
| A | `CHAOS-TESTING-FRAMEWORK-SUMMARY.md` | Framework details merged into REPORT |
| A | `CHAOS-TESTING-SCENARIO-1-ANALYSIS.md` | One-off scenario; results in REPORT |

### 2.2 FINAL-LOAD-TEST / LOAD-TEST family (16 files)
| Action | File | Rationale |
|---|---|---|
| K | `LOAD-TESTING-FINAL-REPORT-2026-05-19.md` (17 KB) | Canonical full report referenced by 4+ top-level docs |
| K | `FINAL-4WORKER-LOAD-TEST-REPORT.md` (7.9 KB) | Canonical for 4-worker config — referenced by `DEPLOYMENT-SIGN-OFF-CHECKLIST.md` |
| K | `LOAD-TESTING-INDEX.md` | Active load-test navigation |
| H | `FINAL-LOAD-TEST-REPORT-2026-05-19.md` | Earlier dated report |
| A | `FINAL-LOAD-TEST-100-CONCURRENT.md` (923 bytes) | Stub; data folded into final |
| A | `FINAL-LOAD-TEST-VALIDATION-REPORT.md` | Superseded by FINAL-VALIDATION-SUMMARY |
| A | `LOAD-TEST-ASYNC-REVALIDATION-REPORT.md` (1 KB) | Stub |
| A | `LOAD-TEST-EXECUTION-INDEX-2026-05-19.md` | Replaced by LOAD-TESTING-INDEX |
| A | `LOAD-TEST-FAILURES.md` | Pre-fix failure capture; resolved |
| A | `LOAD-TESTING-CHECKLIST.md` | Procedure absorbed into FINAL-REPORT |
| A | `load-testing-post-optimization-report.md` | Intermediate |
| A | `load-testing-summary.md` | Intermediate |
| A | `LOAD-TEST-POST-FIXES-REPORT.md` (2.8 KB) | Intermediate snapshot |
| A | `LOAD-TEST-REVALIDATION-FAILURES.md` | Resolved revalidation pass |
| A | `LOAD-TEST-REVALIDATION-INDEX.md` | Stale index |
| A | `LOAD-TEST-VALIDATION-EXECUTIVE-SUMMARY.md` | Folded into FINAL-VALIDATION-SUMMARY |
| A | `LOAD-TEST-VALIDATION-REPORT-INDEX.md` | Stale index |

### 2.3 FINAL-VALIDATION / Production Sign-off (7 files)
| Action | File | Rationale |
|---|---|---|
| K | `FINAL-PRODUCTION-AUTHORIZATION-2026-05-19.md` (12 KB, 21:56) | Latest go/no-go authorization |
| K | `PRODUCTION-READINESS-SIGN-OFF-2026-05-19.md` (35 KB, 16:31) | Canonical readiness doc |
| K | `INDEX-2026-05-19-FINAL-VALIDATION.md` | Active final-validation index |
| H | `FINAL-VALIDATION-ASSESSMENT-2026-05-19.md` | Dated assessment |
| A | `FINAL-VALIDATION-SUMMARY.md` | Subsumed by PRODUCTION-READINESS-SIGN-OFF |
| A | `VALIDATION-BLOCKER-IMMEDIATE-ACTION.md` (2.9 KB) | Blocker resolved; superseded by NEO4J-FIX-VALIDATION-REPORT |
| A | `EXECUTIVE-SUMMARY-2026-05-19.md` (11 KB, 14:46) | Early-day summary; replaced by OPERATIONAL-PLANNING-EXECUTIVE-SUMMARY |

### 2.4 SECURITY (15 files)
| Action | File | Rationale |
|---|---|---|
| K | `FINAL-SECURITY-AUDIT-REPORT.md` (51 KB, 21:46) | Canonical security audit |
| K | `SECURITY-AUDIT-PHASE8-FINAL.md` (22 KB) | Canonical Phase-8 audit (referenced by deployment docs) |
| K | `SECURITY-AUDIT-SUMMARY-FINAL.txt` | Companion summary |
| A | `SECURITY-AUDIT-PHASE8.md` (24 KB) | Superseded by `-FINAL` variant — but DEPLOYMENT-DOCUMENTATION-INDEX still links to it (see Risks §4) |
| A | `SECURITY-GAPS-TO-FIX.md` | Gaps closed per FINAL audit |
| A | `SECURITY-EXPORT-AUTH-FIX.md` | One-off fix; merged into FINAL audit |
| A | `security-dependency-scan-report.md` | Scan result subsumed by FINAL audit |
| A | `security-reviewer-findings.md` (31 KB) | Pre-audit findings; merged into FINAL |
| A | `security-fix-activity-feed-report.md` | Individual fix report |
| A | `security-fix-auth-report.md` | Individual fix report |
| A | `security-fix-authorization-report.md` | Individual fix report |
| A | `security-fix-autocomplete-privacy-report.md` | Individual fix report |
| A | `security-fix-cypher-injection-report.md` | Individual fix report |
| A | `security-fix-dump-encryption-report.md` | Individual fix report |
| A | `security-fix-pii-redaction-report.md` | Individual fix report |

### 2.5 NEO4J (6 files)
| Action | File | Rationale |
|---|---|---|
| K | `NEO4J-OPTIMIZATION-GUIDE.md` (17 KB) | Canonical operational guide |
| K | `NEO4J-FIX-VALIDATION-REPORT.md` (16 KB, 21:34) | Validation of pool fix |
| A | `NEO4J-FIX-EXECUTIVE-SUMMARY.md` | Folded into VALIDATION-REPORT |
| A | `NEO4J-POOL-IMPLEMENTATION-REPORT.md` | Implementation log; superseded by VALIDATION |
| A | `NEO4J-POOL-IMPLEMENTATION-STATUS.md` | Status snapshot |
| A | `NEO4J-POOL-QUICK-REFERENCE.md` (1.9 KB) | Stub; consolidate into GUIDE |

### 2.6 FRONTEND (13 files)
| Action | File | Rationale |
|---|---|---|
| K | `FRONTEND-PERFORMANCE-ANALYSIS.md` (34 KB) | Canonical analysis |
| K | `FRONTEND-OPTIMIZATION-ROADMAP.md` (36 KB) | Canonical roadmap (matches PHASE-2-ROADMAP) |
| K | `FRONTEND-PHASE1-COMPLETION-SUMMARY.md` | Active Phase-1 record |
| K | `FRONTEND-ANALYSIS-INDEX.md` | Navigation hub |
| K | `reviewer-frontend-audit.md` | Referenced from handoffs/README.md |
| A | `FRONTEND-PERFORMANCE-EXECUTIVE-SUMMARY.md` | Folded into ANALYSIS |
| A | `FRONTEND-PERFORMANCE-REPORT.md` (22 KB) | Earlier draft of ANALYSIS |
| A | `FRONTEND-PHASE1-IMPLEMENTATION.md` | Folded into COMPLETION-SUMMARY |
| A | `FRONTEND-PHASE1-QUICK-REFERENCE.md` | Stub |
| A | `frontend-fix-account-manager-report.md` through `frontend-fix-relationship-manager-report.md` (8 files) | Per-component fix reports — work complete; collect in archive |
| A | `frontend-new-cache-dashboard-report.md`, `frontend-new-metrics-dashboard-report.md` | Per-feature reports — work complete |

### 2.7 PHASE-8 (5 files in handoffs/)
| Action | File | Rationale |
|---|---|---|
| K | `PHASE-8-FINAL-VALIDATION-SUMMARY.md` | Active phase-end summary |
| K | `PHASE-8-FINAL-AGENT-INSTRUCTIONS.md` | Referenced by memory MEMORY.md (auto-load) |
| A | `PHASE-8-LOAD-TEST-SUMMARY-2026-05-19.txt` | Subset of LOAD-TESTING-FINAL-REPORT |
| K (top-level) | `docs/PHASE-8-COMPLETION-SUMMARY.md` | Canonical, leave in place |
| K (top-level) | `docs/PHASE-8-IMPLEMENTATION-GUIDE.md` | Canonical, referenced everywhere |

### 2.8 HEALTH-CHECK / Async Fix (5 files)
| Action | File | Rationale |
|---|---|---|
| K | `HEALTH-ASYNC-IMPLEMENTATION-SUMMARY.md` (14 KB) | Canonical |
| K | `HEALTH-ASYNC-FIX-INDEX.md` | Nav hub |
| A | `HEALTH-ASYNC-CORRECTIVE-FIX.md` | Folded |
| A | `HEALTH-ASYNC-FIX-EXECUTIVE-SUMMARY.txt` | Folded |
| A | `HEALTH-CHECK-FIX-REPORT.md` | Earlier version |

### 2.9 INDEX / Coordination / Agent files (10 files)
| Action | File | Rationale |
|---|---|---|
| K | `INDEX.md` | Master operational-planning index |
| K | `README.md` | Audit handoff README |
| K | `AGENT-WORK-PLAN-2026-05-20.md` | Currently active (today) |
| A | `AGENT-COORDINATION-PLAN.md`, `AGENT-SPAWN-INSTRUCTIONS.txt`, `AGENT-SPAWN-SUMMARY.md`, `INDEX-AGENT-DEPLOYMENT.txt` | Completed agent waves from 2026-05-19 |
| A | `agent-brief-01..04-*.md` (4 files) | Briefs already executed |
| A | `MASTER-EXECUTION-PLAN-2026-05-19.md` | Plan executed |

### 2.10 Misc fixes / one-offs (~15 files, all → A)
`CACHE-FIX-REPORT.md`, `CACHE-FIX-VERIFICATION.md`, `collaboration-parameter-ordering-fix.md`, `datetime-serialization-fix.md`, `debugger-blocker-findings.md`, `doc-writer-audit.md`, `STARTUP-BLOCKING-DIAGNOSIS.md`, `STARTUP-FIX-REPORT.md`, `PROJECT-OWNERSHIP-VERIFICATION-FIX.md`, `MULTI-WORKER-CONFIGURATION.md` (keep as K — referenced as canonical multi-worker source), `NGINX-KEEPALIVE-FIX.md`, `CRITICAL-FIXES-IMPLEMENTATION.md`, `IMPROVEMENT-OPPORTUNITIES.md`, `TECHNICAL-REMEDIATION-GUIDE.md`, `DEPLOYMENT-BLOCKERS-2026-05-19.md` (H — dated incident).

### 2.11 Always-Keep set (final whitelist in handoffs/)
After archival the directory should retain ~30 files: the 7 operational-planning docs from INDEX.md (OPERATIONAL-READINESS-MATRIX, OPERATIONAL-PLANNING-EXECUTIVE-SUMMARY, PHASE-2/3/4-ROADMAP, RESOURCE-REQUIREMENTS, HANDOFF-CHECKLIST), plus the canonicals identified in §2.1-2.9, plus dated incident records (H).

---

## 3. Proposed `git mv` Script (REVIEW BEFORE RUNNING)

```bash
#!/usr/bin/env bash
# PROPOSAL ONLY — do not run without human review.
# Run from /home/devel/basset-hound. Expects clean git working tree.
set -euo pipefail

cd /home/devel/basset-hound
mkdir -p docs/handoffs/archive/2026-05

H=docs/handoffs
A=docs/handoffs/archive/2026-05

# 2.1 CHAOS
git mv $H/CHAOS-TEST-EXECUTION-PLAYBOOK.md $A/
git mv $H/CHAOS-TESTING-EXECUTION-SUMMARY.md $A/
git mv $H/CHAOS-TESTING-EXECUTIVE-SUMMARY-2026-05-19.md $A/
git mv $H/CHAOS-TESTING-FRAMEWORK-SUMMARY.md $A/
git mv $H/CHAOS-TESTING-SCENARIO-1-ANALYSIS.md $A/

# 2.2 LOAD-TEST
git mv $H/FINAL-LOAD-TEST-100-CONCURRENT.md $A/
git mv $H/FINAL-LOAD-TEST-VALIDATION-REPORT.md $A/
git mv $H/LOAD-TEST-ASYNC-REVALIDATION-REPORT.md $A/
git mv $H/LOAD-TEST-EXECUTION-INDEX-2026-05-19.md $A/
git mv $H/LOAD-TEST-FAILURES.md $A/
git mv $H/LOAD-TESTING-CHECKLIST.md $A/
git mv $H/load-testing-post-optimization-report.md $A/
git mv $H/load-testing-summary.md $A/
git mv $H/LOAD-TEST-POST-FIXES-REPORT.md $A/
git mv $H/LOAD-TEST-REVALIDATION-FAILURES.md $A/
git mv $H/LOAD-TEST-REVALIDATION-INDEX.md $A/
git mv $H/LOAD-TEST-VALIDATION-EXECUTIVE-SUMMARY.md $A/
git mv $H/LOAD-TEST-VALIDATION-REPORT-INDEX.md $A/
git mv $H/REVALIDATION-SUMMARY.txt $A/

# 2.3 FINAL-VALIDATION
git mv $H/FINAL-VALIDATION-SUMMARY.md $A/
git mv $H/VALIDATION-BLOCKER-IMMEDIATE-ACTION.md $A/
git mv $H/EXECUTIVE-SUMMARY-2026-05-19.md $A/

# 2.4 SECURITY (NOTE: SECURITY-AUDIT-PHASE8.md is referenced — see Risks §4 before moving)
git mv $H/SECURITY-GAPS-TO-FIX.md $A/
git mv $H/SECURITY-EXPORT-AUTH-FIX.md $A/
git mv $H/security-dependency-scan-report.md $A/
git mv $H/security-reviewer-findings.md $A/
git mv $H/security-fix-activity-feed-report.md $A/
git mv $H/security-fix-auth-report.md $A/
git mv $H/security-fix-authorization-report.md $A/
git mv $H/security-fix-autocomplete-privacy-report.md $A/
git mv $H/security-fix-cypher-injection-report.md $A/
git mv $H/security-fix-dump-encryption-report.md $A/
git mv $H/security-fix-pii-redaction-report.md $A/
# git mv $H/SECURITY-AUDIT-PHASE8.md $A/   # BLOCKED: see Risks §4

# 2.5 NEO4J
git mv $H/NEO4J-FIX-EXECUTIVE-SUMMARY.md $A/
git mv $H/NEO4J-POOL-IMPLEMENTATION-REPORT.md $A/
git mv $H/NEO4J-POOL-IMPLEMENTATION-STATUS.md $A/
git mv $H/NEO4J-POOL-QUICK-REFERENCE.md $A/

# 2.6 FRONTEND
git mv $H/FRONTEND-PERFORMANCE-EXECUTIVE-SUMMARY.md $A/
git mv $H/FRONTEND-PERFORMANCE-REPORT.md $A/
git mv $H/FRONTEND-PHASE1-IMPLEMENTATION.md $A/
git mv $H/FRONTEND-PHASE1-QUICK-REFERENCE.md $A/
for f in account-manager advanced-search collaboration-manager export-handler map-handler merge-ui plugin-manager relationship-manager; do
  git mv $H/frontend-fix-${f}-report.md $A/
done
git mv $H/frontend-new-cache-dashboard-report.md $A/
git mv $H/frontend-new-metrics-dashboard-report.md $A/

# 2.7 PHASE-8 (handoffs scope only)
git mv $H/PHASE-8-LOAD-TEST-SUMMARY-2026-05-19.txt $A/

# 2.8 HEALTH-CHECK
git mv $H/HEALTH-ASYNC-CORRECTIVE-FIX.md $A/
git mv $H/HEALTH-ASYNC-FIX-EXECUTIVE-SUMMARY.txt $A/
git mv $H/HEALTH-CHECK-FIX-REPORT.md $A/
git mv $H/HEALTH-ENDPOINT-TEST-SCRIPT.sh $A/

# 2.9 Agent coordination
git mv $H/AGENT-COORDINATION-PLAN.md $A/
git mv $H/AGENT-SPAWN-INSTRUCTIONS.txt $A/
git mv $H/AGENT-SPAWN-SUMMARY.md $A/
git mv $H/INDEX-AGENT-DEPLOYMENT.txt $A/
for f in 01-advanced-search 02-export-handler 03-collaboration-manager 04-relationship-manager; do
  git mv $H/agent-brief-${f}.md $A/
done
git mv $H/MASTER-EXECUTION-PLAN-2026-05-19.md $A/

# 2.10 Misc fixes
git mv $H/CACHE-FIX-REPORT.md $A/
git mv $H/CACHE-FIX-VERIFICATION.md $A/
git mv $H/collaboration-parameter-ordering-fix.md $A/
git mv $H/datetime-serialization-fix.md $A/
git mv $H/debugger-blocker-findings.md $A/
git mv $H/doc-writer-audit.md $A/
git mv $H/STARTUP-BLOCKING-DIAGNOSIS.md $A/
git mv $H/STARTUP-FIX-REPORT.md $A/
git mv $H/PROJECT-OWNERSHIP-VERIFICATION-FIX.md $A/
git mv $H/AUDIT-SUMMARY.txt $A/
git mv $H/CODE-CHANGE-MANIFEST.txt $A/
git mv $H/CRITICAL-FIXES-IMPLEMENTATION.md $A/
git mv $H/IMPROVEMENT-OPPORTUNITIES.md $A/
git mv $H/TECHNICAL-REMEDIATION-GUIDE.md $A/

# Misc intermediates
git mv $H/deployment-verification-report.md $A/
git mv $H/docker-deployment-validation.md $A/
git mv $H/e2e-testing-technical-summary.md $A/
git mv $H/E2E-WORKFLOW-TESTING-COMPLETION.md $A/
git mv $H/e2e-workflow-testing-report.md $A/
git mv $H/integration-test-report.md $A/
git mv $H/integration-test-results.md $A/
git mv $H/performance-analysis-detailed.md $A/
git mv $H/performance-validation-report.md $A/
git mv $H/pre-production-readiness-report.md $A/
git mv $H/PRODUCTION-DEPLOYMENT-CHECKLIST.md $A/  # superseded by docs/PRODUCTION-DEPLOYMENT-RUNBOOK-FINAL.md
git mv $H/SESSION-STATUS-2026-05-19.md $A/
git mv $H/PHASE-8-FINAL-AGENT-INSTRUCTIONS.md $A/ # OPTIONAL — see Risks §4 (MEMORY.md references it)

git status
```

Total proposed moves: **~85 files**. Result: handoffs/ shrinks from 131 to ~46 (30 canonical + 6 dated history + 10 keep-set roadmaps).

---

## 4. Risks & Inbound References

External files that link into `docs/handoffs/` (found via grep across `docs/*.md` and `README.md`):

| Source file | Referenced handoff file | Action required if archived |
|---|---|---|
| `docs/DEPLOYMENT-DOCUMENTATION-INDEX.md` | `SECURITY-AUDIT-PHASE8.md` | Update link to `SECURITY-AUDIT-PHASE8-FINAL.md` BEFORE archiving the older file |
| `docs/DEPLOYMENT-CHECKLIST-FINAL.md` | `SECURITY-AUDIT-PHASE8.md` | Same as above |
| `docs/DEPLOYMENT-SIGN-OFF-CHECKLIST.md` | `FINAL-4WORKER-LOAD-TEST-REPORT.md`, `SECURITY-AUDIT-PHASE8.md` | First file kept; update second-link target |
| `docs/LOAD-TEST-SESSION-SUMMARY.md` | `LOAD-TESTING-FINAL-REPORT-2026-05-19.md`, `LOAD-TEST-FINAL-VALIDATION.md` | First file kept; second link is **broken already** (file does not exist) |
| `docs/handoffs/README.md` (line 337) | `docs/archive/PHASE-8-SUMMARY-2026-05-07.md` | Path is **already stale**: file is in `docs/archives/` (plural), not `docs/archive/`. Fix while consolidating. |
| `docs/handoffs/INDEX.md` line 423 | `ROLLBACK-PROCEDURES.md` (in `docs/`) | OK — target exists |
| Auto-memory `MEMORY.md` (user-level) | `PHASE-8-FINAL-AGENT-INSTRUCTIONS.md` | Marked OPTIONAL in script; consider keeping in place until Phase-8 fix work is complete |

**Pre-archive checklist (must do BEFORE running git mv):**
1. Update 4 inbound references in top-level `docs/*.md` to point at `-FINAL` variants.
2. Decide on `SECURITY-AUDIT-PHASE8.md`: either edit links first, or leave it in place and only archive the per-fix files.
3. Decide on `PHASE-8-FINAL-AGENT-INSTRUCTIONS.md`: keep until the Phase-8 multi-worker fix is shipped.
4. Two index files in `docs/` (`DEPLOYMENT-DOCUMENTATION-INDEX.md`, `API-DOCUMENTATION-INDEX.md`) are themselves untracked in git — confirm they should be committed before adding archive links to them.
5. Verify nothing in `api/` or `nginx/` code paths references handoff markdown by name: `grep -rE "docs/handoffs/[A-Z]" api/ nginx/ docker-compose.yml` (analyst was blocked from doing this; please run before executing).

**Other notes:**
- Two parallel "archive" directories already exist: `docs/archive/` and `docs/archives/`. Resolve which is canonical before introducing `docs/handoffs/archive/`.
- 9 non-md files (`.txt`, `.sh`) in handoffs are included in the script — git will track moves cleanly.
- The script preserves git history (`git mv` rather than rm+add).
- No file is deleted by this proposal — everything is movable and reversible.

---

## 5. Summary

- **131** handoff `.md` files exist; ~**85** are duplicates/superseded and proposed for archival.
- **6 topic groups** (CHAOS, LOAD-TEST, SECURITY, NEO4J, FRONTEND, HEALTH-CHECK) account for the bulk of the duplication; each collapses to 2-3 canonical files.
- The 7-file operational-planning suite from `INDEX.md` (OPERATIONAL-READINESS-MATRIX, OPERATIONAL-PLANNING-EXECUTIVE-SUMMARY, PHASE-2/3/4-ROADMAP, RESOURCE-REQUIREMENTS, HANDOFF-CHECKLIST) is the **must-keep** core.
- **4 inbound link updates** in top-level docs are required before archiving any SECURITY file.
- **1 pre-existing broken link** (`docs/archive/` vs `docs/archives/` in handoffs/README.md) should be fixed in the same change.

Word count: ~1,650.
