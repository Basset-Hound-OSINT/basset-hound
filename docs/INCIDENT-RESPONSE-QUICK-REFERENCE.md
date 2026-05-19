# Incident Response Quick Reference

**Version**: 1.0  
**Last Updated**: 2026-05-19  
**Purpose**: Quick lookup guide for incident responders  
**Format**: Print and keep at desk / pin in war room

---

## PRINT THIS PAGE AND KEEP AT YOUR DESK

This is a quick reference guide. For detailed procedures, see:
- `ROLLBACK-PROCEDURES.md` - Full rollback procedures
- `ROLLBACK-TEST-SCENARIOS.md` - Test procedures
- `PRODUCTION_INTEGRATION_GUIDE.md` - Deployment details

---

## Emergency Contacts

### Immediate Response Chain

```
INCIDENT DETECTED
       ↓
[1] ON-CALL ENGINEER (YOU)
    Contact: ___________________
    Phone: ___________________
    Slack: ___________________
       ↓
[2] DEVOPS LEAD (if needed after 10 min)
    Contact: ___________________
    Phone: ___________________
    Email: ___________________
       ↓
[3] ENGINEERING MANAGER (if needed after 30 min)
    Contact: ___________________
    Phone: ___________________
    Email: ___________________
       ↓
[4] EXECUTIVE (if needed after 60 min)
    Contact: ___________________
    Phone: ___________________
    Email: ___________________

STATUS PAGE ADMINISTRATOR
    Contact: ___________________
    Website: ___________________
```

### Team Notification

- **Slack Channel**: #incident-management
- **Email List**: ops@example.com
- **Paging System**: [System name/URL]
- **Status Page**: https://status.example.com

---

## Incident Timeline Actions

### 0-5 Minutes: Initial Response

```
☐ Acknowledge alert
☐ Log in to production server
☐ Run: curl http://localhost:8080/health
☐ Check services: docker compose ps
☐ Decision: Fix forward OR Rollback?
  ├─ Rollback if: API down, DB inaccessible, critical error
  └─ Fix forward if: Minor bug, single service affected
☐ Notify team in #incident-management
```

### 5-15 Minutes: Diagnosis & Action

**If Rollback Decision:**
```
☐ Run diagnostic script
☐ Backup current state (see ROLLBACK-PROCEDURES.md Step 2)
☐ Execute rollback (Step 3-8)
☐ Validate restoration (Step 8)
☐ Update status page: "Mitigation in progress"
☐ Post in Slack: Current status & ETA
```

**If Fix Forward:**
```
☐ Identify root cause from logs
☐ Make minimal fix
☐ Test fix thoroughly
☐ Deploy fix
☐ Verify on production
☐ Announce resolution
```

### 15-30 Minutes: Validation & Comms

```
☐ Run full health checks
☐ Verify all API endpoints responsive
☐ Check database integrity
☐ Test with real data
☐ Update status page: "Monitoring"
☐ Send update email to stakeholders
☐ Schedule post-incident review
```

### 30+ Minutes: Resolution & Documentation

```
☐ Confirm all systems stable
☐ Update status page: "Resolved"
☐ Send incident summary email
☐ Document timeline & actions
☐ Schedule root cause analysis
☐ Identify preventive measures
☐ Update procedures if needed
```

---

## Critical Commands (Copy-Paste Ready)

### System Health Check
```bash
docker compose ps
curl http://localhost:8080/health
docker exec neo4j_osint_db cypher-shell -u neo4j -p neo4jbasset "MATCH (n) RETURN count(n);"
```

### Stop Services
```bash
cd /opt/basset-hound
docker compose down --timeout 30
```

### Start Services
```bash
cd /opt/basset-hound
docker compose up -d
```

### View Recent Logs
```bash
docker compose logs --since 10m basset_api
docker compose logs --since 10m neo4j
```

### Database Node Count
```bash
docker exec neo4j_osint_db cypher-shell -u neo4j -p neo4jbasset "MATCH (n) RETURN count(n);"
```

### Cache Status
```bash
docker exec basset_redis redis-cli PING
docker exec basset_redis redis-cli INFO stats
```

### Check Disk Space
```bash
df -h /opt/basset-hound
```

### Full Rollback (Step by step)
```bash
# See ROLLBACK-PROCEDURES.md for full procedure
# Quick version:
docker compose down
docker volume rm basset-hound_neo4j_data
docker compose -f docker-compose.phase7.yml up -d neo4j
docker exec neo4j_osint_db neo4j-admin database load neo4j /backup/phase7.dump
docker compose up -d
```

---

## Common Issues & Quick Fixes

| Issue | Symptom | Quick Fix | Full Procedure |
|-------|---------|-----------|-----------------|
| API Down | curl fails | `docker compose restart basset_api` | ROLLBACK-PROCEDURES.md #Backend |
| DB Unreachable | Can't query Neo4j | `docker compose restart neo4j` | ROLLBACK-PROCEDURES.md #DB |
| Cache Issues | Slow responses | `docker exec basset_redis redis-cli FLUSHALL` | ROLLBACK-PROCEDURES.md #Cache |
| Frontend Error | Dashboard 404/500 | `docker compose restart basset_api` | ROLLBACK-PROCEDURES.md #Frontend |
| Full Failure | All services down | START ROLLBACK | ROLLBACK-PROCEDURES.md #Full |

---

## Decision Tree: Rollback or Fix Forward?

```
                    INCIDENT DETECTED
                           |
                           v
                    ┌──────────────┐
                    │ API Down?    │
                    └──────┬───────┘
                      YES /  \ NO
                         /    \
                        v      v
                    ROLLBACK  Continue
                         |
                ┌────────┴────────┐
                v                 v
           ┌─────────┐      ┌──────────────┐
           │DB Down? │      │Data Corrupted│
           └────┬────┘      └──────┬───────┘
           YES  │ NO            YES│ NO
               /                  /
              v                  v
           ROLLBACK          ROLLBACK  Continue
              |                 |
     ┌────────┴──────────┐     |
     v                   v     v
  FULL         DATABASE   FRONTEND
  ROLLBACK     ONLY       ONLY
```

**ROLLBACK WHEN:**
- ✗ API completely down
- ✗ Database inaccessible
- ✗ Data appears corrupted
- ✗ Critical feature broken
- ✗ Cannot diagnose in 10 minutes

**FIX FORWARD WHEN:**
- ✓ Single service affected
- ✓ Can identify root cause
- ✓ Fix is well-understood
- ✓ Can be tested quickly
- ✓ Low risk of cascading failure

---

## Escalation Triggers

Trigger escalation (call DevOps Lead) if:

```
[ ] Incident ongoing > 15 minutes
[ ] Unable to diagnose root cause
[ ] Rollback taking > 20 minutes
[ ] Rollback incomplete or failed
[ ] Multiple systems affected
[ ] Data integrity concerns
[ ] Unable to reach on-call
[ ] Need approval for major action
```

When escalating, provide:
1. **What**: Description of issue
2. **When**: Time detected
3. **Impact**: Users/systems affected
4. **Diagnosis**: What you've tried
5. **ETA**: Expected resolution time
6. **Help needed**: Specific assistance required

---

## Status Page Updates

### Critical Status Updates

Update at: https://status.example.com

**15 minutes in (incident ongoing):**
```
🟡 DEGRADED - Phase 8 rollback in progress
Affected: Basset Hound platform
Impact: Platform unavailable during maintenance
ETA: 30 minutes
Updates: Every 10 minutes
```

**After successful action:**
```
🟡 MONITORING - Services restored, monitoring
Affected: Basset Hound platform
Status: Phase 7 restored and verified
ETA: Full resolution in 10 minutes
```

**All clear:**
```
✅ RESOLVED - All systems operational
Affected: Basset Hound platform
Status: Phase 7 fully operational
Incident duration: 40 minutes
Post-incident review: Scheduled for [DATE]
```

---

## Notification Templates

### Initial Alert (Send within 5 minutes)

```
Subject: [INCIDENT] Basset Hound - Investigating issue

We're aware of an issue affecting Basset Hound and are investigating.
We will have an update in 5-10 minutes.

Status: INVESTIGATING
Impact: Platform may be unavailable
Time: 2026-05-19 02:15 UTC

We'll keep you updated.
```

### Progress Update (Every 10 minutes)

```
Subject: [INCIDENT UPDATE] Basset Hound - Still investigating

We're actively working on the issue.
Current action: [Describe what you're doing]
Estimated time: [When it will be fixed]

Status: IN PROGRESS
Last updated: [TIME] UTC
```

### Resolution (Immediately after)

```
Subject: [RESOLVED] Basset Hound - Service restored

The issue has been resolved and Basset Hound is fully operational.

Timeline:
- Issue detected: [TIME]
- Resolution started: [TIME]
- Resolution complete: [TIME]

Cause: [Brief description]
Impact: [What was affected, roughly how many users]

We will provide a detailed analysis tomorrow.
Thank you for your patience.
```

---

## File Locations & Paths

### Critical Directories
```
/opt/basset-hound/              - Application root
/opt/basset-hound/backups/      - All backups
/opt/basset-hound/docker-compose.yml - Service config
/opt/basset-hound/.env          - Environment variables
/opt/basset-hound/logs/         - Application logs
/var/lib/docker/containers/     - Container logs
```

### Docker Volumes
```
basset-hound_neo4j_data         - Database
basset-hound_redis_data         - Cache
basset-hound_nginx_logs         - Web logs
```

### Key Configuration
```
Database password:              $NEO4J_PASSWORD (in .env)
API port:                       8000 (internal), 8080 (external)
Neo4j ports:                    7474 (HTTP), 7687 (Bolt)
Redis port:                     6379 (internal only)
```

---

## Rollback Checklist (Keep in Desk Drawer)

```
ROLLBACK EXECUTION CHECKLIST
============================

Incident: _________________________________
Started: _________________________________
Authorized by: _____________________________

EXECUTION PHASE

Step 1: Pre-Checks
  [ ] Backups exist
  [ ] Disk space > 10 GB
  [ ] Team notified
  [ ] Status page updated
  
Step 2: Stop Services
  [ ] docker compose down --timeout 30
  [ ] Verify stopped: docker compose ps
  
Step 3: Restore Phase 7
  [ ] Prepare Phase 7 environment
  [ ] Remove old volumes
  [ ] Restore database from backup
  
Step 4: Start Services
  [ ] docker compose up -d
  [ ] Wait 2-3 minutes
  [ ] Check docker compose ps
  
Step 5: Validation
  [ ] curl http://localhost:8080/health
  [ ] curl http://localhost:8080/api/v1/projects
  [ ] Check Neo4j: docker exec neo4j... [command]
  
Step 6: Communication
  [ ] Update status page
  [ ] Send email to stakeholders
  [ ] Post in #incident-management
  
COMPLETION

Rollback completed: _____________ Time: _______
Verified by: ________________________
Approved by: ________________________

Incident resolved: [ ] Yes [ ] No
Duration: ________________________
Next steps: _________________________
```

---

## Quick Decision Matrix

```
WHAT'S HAPPENING?              WHAT DO I DO?                WHERE'S THE PROCEDURE?
─────────────────────────────────────────────────────────────────────────────────

API returning 500 errors       → Check logs, restart API    → Fix Forward Guide
                                  
Database connection timeout     → Restart Neo4j              → Database Rollback

All services down              → Full rollback to Phase 7   → Full Rollback #Step3+

Frontend not loading           → Restart API, check frontend → Frontend Rollback

High error rate (>5%)          → Escalate & diagnose        → Fix Forward Guide

Data appears corrupted         → Stop services, restore DB  → Data Recovery #Step8+

Services crash on restart      → Check config, rebuild      → Troubleshooting

Can't diagnose after 10 min   → Start rollback             → Full Rollback #Step1+

Never seen this before        → Escalate to DevOps Lead    → Contact [Name]
```

---

## Phone Tree (Write In Your Names)

```
INCIDENT PHONE TREE
===================

When to call (escalation):
- 10 minutes with no progress → Call DevOps Lead
- 30 minutes ongoing → Call Engineering Manager  
- 60 minutes ongoing → Call Executive

ON-CALL ENGINEER
Name: _____________________
Phone: _____________________

DEVOPS LEAD
Name: _____________________
Phone: _____________________

ENGINEERING MANAGER
Name: _____________________
Phone: _____________________

EXECUTIVE ON-CALL
Name: _____________________
Phone: _____________________

OPERATIONS CENTER
Number: _____________________
Hours: _____________________
```

---

## Critical Service Ports

```
Service                 Internal    External    Via Nginx
────────────────────────────────────────────────────────────────
API (FastAPI)          8000        —           8080
Neo4j Browser          7474        —           8080/neo4j/
Neo4j Bolt             7687        —           N/A
Redis                  6379        —           N/A
basset-verify          8001        —           N/A
Prometheus             9090        —           N/A
Grafana                3000        —           N/A
Nginx                  80          8080        —
```

---

## One-Page Rollback Summary

```
FULL ROLLBACK TO PHASE 7 (QUICK VERSION)
=========================================

1. ASSESS (2 min)
   - Health check: curl http://localhost:8080/health
   - Is it bad enough to rollback? (See Decision Tree)
   - Notify team

2. BACKUP (5 min)
   - Current state: docker compose logs > /tmp/phase8_logs.txt
   - DB snapshot: run backup script
   - Config backup: tar of /opt/basset-hound/.env

3. STOP (2 min)
   - docker compose down --timeout 30

4. RESTORE (15-30 min)
   - Remove volume: docker volume rm basset-hound_neo4j_data
   - Start Neo4j: docker compose up -d neo4j
   - Restore DB: neo4j-admin database load neo4j [backup.dump]

5. START (3 min)
   - docker compose up -d

6. VALIDATE (5 min)
   - Health: curl http://localhost:8080/health
   - DB: docker exec neo4j... count nodes
   - API: curl http://localhost:8080/api/v1/projects

7. COMMUNICATE (2 min)
   - Update status page
   - Send email to stakeholders

TOTAL TIME: ~30-45 minutes
```

---

## Post-Incident Checklist

```
AFTER INCIDENT RESOLUTION
==========================

Within 1 hour:
  [ ] All services stable (monitored for 15 min)
  [ ] Status page shows "resolved"
  [ ] Team notified of resolution
  [ ] Incident logged with timestamp

Within 24 hours:
  [ ] Incident timeline documented
  [ ] Root cause analysis completed
  [ ] Team debriefing meeting scheduled
  [ ] Any procedure updates identified

Within 1 week:
  [ ] Root cause analysis complete
  [ ] Preventive measures implemented
  [ ] Procedures updated
  [ ] Team trained on changes
  [ ] Lessons learned documented

INCIDENT TICKET: ____________________
ROOT CAUSE: _________________________
PREVENTIVE MEASURES: _________________
```

---

## Last Minute Reminders

✓ **BREATHE** - You have time. Don't panic.

✓ **DOCUMENT** - Write down what you do. You'll need it.

✓ **COMMUNICATE** - Keep team in loop. Silence is scary.

✓ **ESCALATE** - Ask for help at 10, 30, 60 minute marks.

✓ **VALIDATE** - After every action, confirm it worked.

✓ **STOP & THINK** - If unsure, SLOW DOWN. Haste causes errors.

✓ **FOLLOW THE PLAYBOOK** - You have detailed procedures. Use them.

✓ **SAVE EVERYTHING** - Logs, screenshots, commands. You'll need them.

---

**KEEP THIS CARD ACCESSIBLE**

Print this page and:
- Tape to your monitor
- Keep in your desk drawer
- Share with your on-call team
- Update with real names & numbers
- Review quarterly

**Last Updated**: 2026-05-19  
**Next Review**: 2026-08-19 (3 months)  
**Owner**: DevOps Team
