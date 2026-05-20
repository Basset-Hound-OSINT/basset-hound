# Basset Hound Incident Response Playbook

**Version**: 2.0  
**Date**: 2026-05-19  
**Purpose**: Systematic procedures for responding to production incidents  
**Audience**: On-Call Engineers, DevOps Team, Engineering Managers

---

## Table of Contents

1. [Incident Severity Classification](#incident-severity-classification)
2. [Incident Response Process](#incident-response-process)
3. [Escalation Procedures](#escalation-procedures)
4. [Common Issues & Solutions](#common-issues--solutions)
5. [Rollback Decision Tree](#rollback-decision-tree)
6. [Communication Templates](#communication-templates)
7. [Post-Incident Review](#post-incident-review)

---

## Incident Severity Classification

### Severity Levels

| Level | Impact | Response Time | Escalation |
|-------|--------|---------------|------------|
| **P1: Critical** | Service down, >10% users affected | Immediate (5 min) | Page on-call + manager |
| **P2: High** | Functionality broken, 1-10% users | Urgent (30 min) | Notify manager, create ticket |
| **P3: Medium** | Degraded performance, <1% users | Standard (4 hours) | Create ticket, monitor |
| **P4: Low** | Minor issue, no user impact | Normal (1 week) | Document, schedule sprint |

### Incident Examples

**P1 - Critical**:
- API completely down (all endpoints returning 5xx)
- Database unreachable (0 successful queries)
- Data corruption detected (missing records)
- Security breach confirmed (unauthorized access)
- Complete cache layer failure (all requests hitting DB)

**P2 - High**:
- Search endpoint timing out (>500ms consistently)
- Export functionality broken
- WebSocket sync not working
- Authentication failing for new users
- Error rate >5% for 10+ minutes

**P3 - Medium**:
- API latency p99 >300ms
- Cache hit rate <30%
- Non-critical feature broken
- Minor data inconsistency
- Performance degradation 10-20%

**P4 - Low**:
- Console.log statements in browser
- Non-critical TODO comments
- Minor UI cosmetic issue
- Documentation typo
- Unused import warnings

---

## Incident Response Process

### Phase 1: DETECT & ASSESS (First 5 minutes)

**Goal**: Confirm issue and understand scope

#### Step 1.1: Receive Alert (Automatic)

```
Slack notification:
  🚨 [CRITICAL] API Error Rate High
  Error rate: 15.2% (threshold: 1%)
  Duration: 2 minutes
  Affected endpoint: /api/v1/search
```

**Action**: On-call engineer acknowledges alert

#### Step 1.2: Verify Issue

```bash
# Don't assume alert is correct - verify manually

# Check API health
curl -s http://localhost:8080/health | jq .
# Response: healthy / degraded / down

# Check specific endpoint
curl -s http://localhost:8080/api/v1/projects | jq .error
# Look for error response

# Check error rate in detail
curl -s http://localhost:8080/api/v1/metrics | jq '{error_rate, latency_p99, cache_hit_rate}'

# Check services are running
docker-compose ps | grep -E "api|neo4j|redis"
# All should show "Up"
```

#### Step 1.3: Assess Scope

Create incident ticket with:

```markdown
# Incident #123: [Brief description]

**Severity**: P1 / P2 / P3 / P4
**Detected**: 2026-05-20 14:05 UTC
**Duration**: < 5 minutes (estimate)

## Scope Assessment
- [ ] Is API responding? YES / NO
- [ ] Is database responding? YES / NO  
- [ ] Is cache responding? YES / NO
- [ ] All endpoints affected? YES / NO / PARTIALLY
- [ ] Estimated affected users: 0% / 1-10% / >10%
- [ ] Visible errors in logs? (include sample)

## Initial Diagnosis
[Brief hypothesis about root cause]

## Actions Taken
[List actions as they're taken]
```

#### Step 1.4: Page On-Call (if P1)

```bash
# For P1 incidents, immediately page
pagerduty trigger \
  --incident-key=basset-hound-p1 \
  --description="Basset Hound API Error Rate Critical" \
  --client=Basset-Hound

# Or use Slack command
/pagerduty trigger "API down" urgent
```

---

### Phase 2: STABILIZE (5-30 minutes)

**Goal**: Stop the bleeding, minimize impact

#### Step 2.1: Quick Diagnostics

```bash
# Gather immediate data for analysis
mkdir -p /tmp/incident-logs-$(date +%s)
cd /tmp/incident-logs-*

# Capture current state
docker-compose ps > services.txt
docker-compose logs api > api-logs.txt
docker-compose logs neo4j > neo4j-logs.txt
docker stats --no-stream > resources.txt
docker-compose exec neo4j cypher-shell "CALL dbms.cluster.overview()" > db-status.txt

# Check for obvious issues
echo "=== Recent Errors ===" >> summary.txt
grep -i "error\|exception\|critical" api-logs.txt | tail -20 >> summary.txt

echo "=== Resource Usage ===" >> summary.txt
cat resources.txt | grep -E "CONTAINER|api|neo4j|redis" >> summary.txt
```

#### Step 2.2: Decision: Restart vs Investigate

```
┌─ Is service responding?
│  YES → Continue to investigation
│  NO  → Restart service (Step 2.3)
│
├─ Is error rate >50%?
│  YES → Consider quick rollback (Step 2.4)
│  NO  → Proceed with investigation
│
└─ Can you identify root cause in <10 minutes?
   YES → Proceed with targeted fix
   NO  → Consider restart
```

#### Step 2.3: Restart Service (If Unresponsive)

```bash
# For API
docker-compose restart api
sleep 10
curl http://localhost:8080/health | jq .status
# Expected: "healthy"

# For Database
docker-compose restart neo4j
sleep 30  # Neo4j needs more time
docker-compose exec neo4j cypher-shell "RETURN 1"
# Expected: 1

# For Cache
docker-compose restart redis
sleep 5
docker-compose exec redis redis-cli ping
# Expected: PONG

# Monitor after restart
watch -n 2 'curl -s http://localhost:8080/api/v1/metrics | jq "{error_rate, latency_p99}"'
# Wait 5+ minutes to confirm recovery
```

**Decision Point**: 
- If error rate drops <1% and latency improves → **Incident contained**
- If error rate stays >5% → **Escalate to rollback**

#### Step 2.4: Quick Rollback (If Critical)

Only use if:
- Error rate remains >50%, OR
- Data corruption confirmed, OR
- Unable to restore service within 15 minutes

```bash
# Get last known good version
git log --oneline | head -5
# Find pre-deployment tag
git tag | grep pre-deployment

# Stop current deployment
docker-compose down

# Checkout previous version
git checkout pre-deployment-20260520
docker-compose build

# Start with previous version
docker-compose up -d
sleep 30

# Verify recovery
curl http://localhost:8080/health | jq .
# Expected: healthy

# Check error rate
curl http://localhost:8080/api/v1/metrics | jq .error_rate
# Expected: <0.5%
```

**During rollback**, notify team:

```
🔄 ROLLBACK INITIATED
Reason: [High error rate / Data corruption / Service unresponsive]
Rolled back to: [Previous version tag]
Estimated recovery: 5 minutes
```

---

### Phase 3: ROOT CAUSE ANALYSIS (30-60 minutes)

**Goal**: Understand what happened for reporting and fixing

#### Step 3.1: Log Analysis

```bash
# Find first error occurrence
docker-compose logs api | grep -i "error\|exception" | head -20

# Look for error patterns
docker-compose logs api | grep "500\|timeout\|connection" | wc -l

# Check timestamps to correlate with alert
docker-compose logs api | grep "2026-05-20 14:0" | head -20
```

#### Step 3.2: Root Cause Hypothesis

Based on error patterns, identify likely causes:

```markdown
## Hypotheses (in order of likelihood)

1. **Database Overload** (Probability: 60%)
   - Evidence: Many "timeout waiting for connection" errors
   - Check: Neo4j connection pool utilization
   - Fix: Increase pool size or optimize queries

2. **Memory Leak** (Probability: 25%)
   - Evidence: Memory grows from 2GB to 4GB over 1 hour
   - Check: docker stats memory trend
   - Fix: Restart API, investigate code

3. **Cascading Failures** (Probability: 10%)
   - Evidence: All endpoints fail simultaneously at T+5min
   - Check: System load and resource limits
   - Fix: Implement circuit breaker

4. **Configuration Error** (Probability: 5%)
   - Evidence: Logs show connection string issues
   - Check: .env file configuration
   - Fix: Correct configuration, restart
```

#### Step 3.3: Confirm Root Cause

```bash
# For database theory:
docker-compose exec neo4j cypher-shell "
  CALL dbms.monitoring.database_execution_time() 
  YIELD duration_ms, statement 
  RETURN statement, duration_ms 
  ORDER BY duration_ms DESC 
  LIMIT 5
"

# For memory leak theory:
docker stats --no-stream --format "{{.Container}}: {{.MemUsage}}"

# For cache theory:
curl http://localhost:8080/api/v1/cache/stats | jq .

# For configuration theory:
docker-compose logs api | grep -i "config\|setting" | head -10
```

---

### Phase 4: FIX & VERIFY (Variable time)

**Goal**: Implement permanent fix and validate

#### Step 4.1: Implement Fix

Based on root cause:

**If Database Overload**:
```python
# In api/services/neo4j_service.py
- Increase connection pool: 50 → 150
- Add query timeout: 30s → 5s
- Implement connection pooling at service level
```

**If Memory Leak**:
```python
# In api/main.py
- Inspect heap for large objects
- Add periodic garbage collection
- Check for unbounded caches
```

**If Cascading Failure**:
```python
# In api/utils/rate_limiting.py
- Add circuit breaker pattern
- Implement graceful degradation
- Return cached data when DB slow
```

**If Configuration**:
```bash
# Edit .env
NEO4J_CONNECTION_POOL_SIZE=150
REDIS_URL=redis://redis:6379/0
# Restart services
docker-compose restart
```

#### Step 4.2: Test Fix Locally

```bash
# Restart with fix
docker-compose restart

# Run smoke tests
python3 -m pytest tests/smoke/ -v

# Run load test
python3 load_testing_script.py

# Expected: Same baseline performance
```

#### Step 4.3: Deploy Fix

If only configuration change:
```bash
docker-compose restart api
```

If code change:
```bash
docker-compose build
docker-compose up -d api
```

#### Step 4.4: Verify Recovery

```bash
# Monitor metrics for 15 minutes
watch -n 5 'curl -s http://localhost:8080/api/v1/metrics | jq \
  "{error_rate, latency_p99, cache_hit_rate}"'

# Expected:
# error_rate: 0.0-0.05
# latency_p99: 85-100
# cache_hit_rate: 60+
```

---

### Phase 5: COMMUNICATE (Ongoing)

**Goal**: Keep stakeholders informed

#### Update Slack Every 10 Minutes

```
Status Update #1 (14:05)
🚨 Incident detected: API error rate 15%
Investigating now...

Status Update #2 (14:15)
Investigation ongoing. Hypothesis: Database overload
Checking connection pool utilization...

Status Update #3 (14:25)
Found issue: Connection pool exhausted
Implementing fix: Increase pool size to 150
Will deploy in 5 minutes...

Status Update #4 (14:35)
✅ Fix deployed
Monitoring for 15 minutes to confirm stability...

Status Update #5 (14:50)
✅ INCIDENT RESOLVED
- Error rate: 0.05% (normal)
- Latency p99: 85ms (normal)
- All endpoints healthy

Post-incident review scheduled for tomorrow 10am
```

---

## Escalation Procedures

### Escalation Matrix

```
P1 Incident → T+5min
  ↓
No progress? → Page secondary on-call
  ↓
Still no progress? → T+30min → Escalate to manager
  ↓
Critical business impact? → Page CTO
```

### Escalation Contacts

**Template for team to fill in**:

```yaml
escalation:
  level_1_oncall:
    name: [Name]
    phone: [Phone]
    slack: @[Slack Handle]
    available: "24/7"
  
  level_2_backup:
    name: [Name]
    phone: [Phone]
    slack: @[Slack Handle]
    available: "24/7"
  
  level_3_manager:
    name: [Name]
    phone: [Phone]
    email: [Email]
    available: "Business hours + on-call"
  
  level_4_exec:
    name: [Name]
    phone: [Phone]
    slack: @[Slack Handle]
    available: "For critical business impact"
```

### Escalation Triggers

```
Escalate to Level 2 if:
  - No progress after 15 minutes
  - Error rate still >5%
  - Unable to determine root cause

Escalate to Level 3 if:
  - P1 incident lasting >30 minutes
  - Data loss / corruption
  - Security incident

Escalate to Level 4 if:
  - Service down >1 hour
  - Enterprise customer affected
  - Revenue impact
  - Public/media attention
```

---

## Common Issues & Solutions

### Issue 1: High Error Rate (>5%)

**Detection**: Prometheus alert: "HighErrorRate"

**Quick Diagnosis** (1 min):

```bash
# Get error breakdown by endpoint
curl -s http://localhost:8080/api/v1/metrics | jq '.error_count_by_endpoint'

# Get error type breakdown
docker-compose logs api | grep "ERROR" | awk '{print $NF}' | sort | uniq -c | sort -rn | head -10
```

**Common Causes & Fixes**:

| Cause | Detection | Quick Fix | Time |
|-------|-----------|-----------|------|
| Database down | "connection refused" | Restart Neo4j | 1 min |
| Connection pool exhausted | "timeout waiting for connection" | Increase pool size | 2 min |
| Memory exhausted | "OutOfMemory" error | Restart API | 1 min |
| Cascading failures | "Context deadline exceeded" | Implement circuit breaker | 30 min |
| Slow queries | Latency >1s with low CPU | Optimize query | 15 min |

**Solution Flow**:

```
Error rate >5%?
  → Check error type in logs
  → If database error: Restart Neo4j
  → If memory error: Restart API  
  → If query error: Check database load
  → If consistent pattern: Deploy code fix
```

### Issue 2: High Latency (p99 >500ms)

**Detection**: Prometheus alert: "HighLatency"

**Quick Diagnosis**:

```bash
# Check if database is slow
docker-compose exec neo4j cypher-shell \
  "PROFILE MATCH (n) RETURN count(n)"

# Check if cache is working
curl -s http://localhost:8080/api/v1/cache/stats | jq .hit_rate

# Check system resources
docker stats --no-stream
```

**Solutions**:

```
High latency?
  → If cache hit rate <50%: Clear cache, warm up
  → If database latency >200ms: Optimize query
  → If memory >80%: Restart service
  → If CPU >80%: Scale horizontally (add workers)
```

### Issue 3: Out of Memory

**Detection**: Container OOMKilled or logs show "OutOfMemory"

**Quick Diagnosis**:

```bash
# Check memory usage over time
docker stats --no-stream api

# Check for memory leaks
docker inspect <container> | grep Memory

# Check for large operations
docker-compose logs api | grep "loaded\|allocated\|memory"
```

**Solutions**:

```
Out of memory?
  → 1. Increase Docker memory limit
  → 2. Restart service to free memory (temp fix)
  → 3. Identify memory leak (long term)
  → 4. Implement memory limits per operation
  → 5. Scale horizontally if sustained high usage
```

### Issue 4: Database Connection Issues

**Detection**: Logs show "bolt connection refused" or health check shows database disconnected

**Quick Diagnosis**:

```bash
# Check if Neo4j container is running
docker-compose ps neo4j

# Try to connect directly
docker-compose exec neo4j cypher-shell -u neo4j -p password "RETURN 1"

# Check Neo4j logs
docker-compose logs neo4j | tail -50
```

**Solutions**:

```
Database connection failed?
  → 1. Verify Neo4j container is running
  → 2. Check Neo4j password in .env
  → 3. Check network connectivity (docker network inspect)
  → 4. Restart Neo4j container
  → 5. If still failing, check data directory (may be corrupted)
  → 6. Restore from backup if necessary
```

### Issue 5: Cache Layer Unavailable

**Detection**: Cache hit rate 0% or Redis errors in logs

**Quick Diagnosis**:

```bash
# Check if Redis is running
docker-compose ps redis

# Try to connect
docker-compose exec redis redis-cli ping

# Check memory
docker-compose exec redis redis-cli info memory | grep used
```

**Solutions**:

```
Cache unavailable?
  → 1. Restart Redis container
  → 2. Check Redis memory usage
  → 3. Clear cache if out of memory: redis-cli FLUSHALL
  → 4. Verify Redis network connectivity
  → 5. Check for connection leaks (max connections exceeded)
```

---

## Rollback Decision Tree

```
Issue Severity?
  │
  ├─ P1 (Critical - service down or >50% error rate)
  │  └─ YES: Initiate rollback immediately
  │
  ├─ P2 (High - degraded performance or >10% error rate)
  │  └─ Time since deployment <30 min?
  │     ├─ YES: Rollback
  │     └─ NO: Attempt fix
  │
  ├─ P3 (Medium - minor degradation)
  │  └─ Can fix in <15 min?
  │     ├─ YES: Attempt fix
  │     └─ NO: Schedule for next maintenance
  │
  └─ P4 (Low - non-critical)
     └─ Fix during regular sprint
```

### Rollback Procedure

```bash
# STEP 1: Stop current services
docker-compose down

# STEP 2: Verify target version exists
git tag | grep pre-deployment

# STEP 3: Checkout previous version
git checkout pre-deployment-20260520

# STEP 4: Rebuild images
docker-compose build

# STEP 5: Start services
docker-compose up -d

# STEP 6: Verify health (wait 30 seconds)
sleep 30
curl http://localhost:8080/health | jq .

# STEP 7: Check error rate
curl http://localhost:8080/api/v1/metrics | jq .error_rate
# Expected: <0.5%

# STEP 8: Notify team
# "Rollback complete. Version: pre-deployment-20260520"
```

---

## Communication Templates

### Initial Alert (T+0)

```
🚨 INCIDENT ALERT
Service: Basset Hound API
Severity: P1 - CRITICAL
Status: INVESTIGATING
Detected: 2026-05-20 14:05 UTC

Issue: API error rate 15% (threshold: 1%)
Affected endpoint: /api/v1/search
Impact: ~10% of users experiencing timeouts

Next update: In 10 minutes
```

### Update #1 (T+10)

```
📊 STATUS UPDATE
Severity: P1 - CRITICAL  
Status: INVESTIGATING
Duration: 10 minutes

Finding: Database connection pool exhausted
Root cause: Query optimization regression
Fix in progress: Increasing pool size from 50 to 150

Estimated recovery: 15 minutes
```

### Update #2 (T+25)

```
🔧 STATUS UPDATE
Severity: P1 - CRITICAL
Status: FIXING
Duration: 25 minutes

Fix deployed: Increased Neo4j pool size to 150
Validation: Monitoring error rate and latency
Current status: Error rate 0.1% (improving)

Estimated full recovery: 10 minutes
```

### Resolution (T+35)

```
✅ INCIDENT RESOLVED
Service: Basset Hound API
Duration: 35 minutes
Resolved: 2026-05-20 14:40 UTC

Root cause: Neo4j connection pool exhaustion
Solution: Increased max connections from 50 to 150
Result: Error rate normalized to 0.05%

Post-incident review: Tomorrow 10:00 AM UTC
```

---

## Post-Incident Review

### Schedule RCA Meeting

Within 24 hours of incident, hold post-mortem:

```markdown
# Post-Incident Review: Incident #123

**Date**: 2026-05-21 10:00 UTC  
**Attendees**: On-call engineer, DevOps lead, engineering manager, affected service owner  
**Duration**: 60 minutes

## Incident Summary
- **Timeline**: 14:05 - 14:40 UTC (35 minutes)
- **Service**: Basset Hound API  
- **Impact**: ~10% of users affected
- **Root Cause**: Neo4j connection pool exhausted

## What Happened
1. T+0: Query optimization change deployed
2. T+5: High concurrency triggered pool exhaustion  
3. T+10: Cascading timeout failures begin
4. T+15: Error rate reaches 15%
5. T+20: Pool size increased from 50 to 150
6. T+35: Service recovered

## Root Cause Analysis
- **Why**: Pool size too small for optimization change
- **Why**: Load testing didn't simulate sustained high concurrency
- **Why**: No monitoring for pool utilization pre-deployment

## What Went Well
✅ Alert fired quickly (within 5 minutes)
✅ Root cause identified in 15 minutes  
✅ Fix deployed rapidly (5 minutes)
✅ Communication to users was timely

## What Didn't Go Well
❌ Pool size not tuned before deployment
❌ No pre-deployment load test at target concurrency
❌ No alert for connection pool utilization
❌ Database health check didn't catch pooling issue

## Action Items
- [ ] Add connection pool monitoring alert (Owner: DevOps, Due: 2026-05-23)
- [ ] Increase pre-deployment load test to 200 concurrent users (Owner: QA, Due: 2026-05-23)
- [ ] Document connection pool sizing guidelines (Owner: Tech Lead, Due: 2026-05-24)
- [ ] Review other services for similar pool issues (Owner: DevOps, Due: 2026-05-25)

## Lessons Learned
1. Always load test at 2x expected peak concurrency
2. Monitor database connection pool utilization as critical metric
3. Have rollback procedure tested and ready
4. Communication to users should happen immediately

## Follow-up
- Next RCA: 2026-05-28 if any related incidents
- Verify fixes deployed: 2026-05-23
```

### Publish RCA Summary

Share with broader team:

```markdown
# Incident #123 - Post-Mortem Summary

**What**: Neo4j connection pool exhaustion caused 35-minute outage
**When**: May 20, 14:05-14:40 UTC
**Impact**: ~10% of API requests failed for 35 minutes

**Root Cause**: Query optimization change increased database load but pool size wasn't tuned

**Resolution**: Increased connection pool from 50 to 150 connections

**How We're Preventing This**:
1. Added Prometheus alert for pool utilization >80%
2. Increased pre-deployment load test to 200 concurrent users
3. Documented connection pool tuning guidelines
4. Will audit other services for similar issues

**Timeline**:
- T+0: Deployed query optimization
- T+5: Alert fired (high error rate)
- T+15: Root cause identified (pool exhaustion)
- T+20: Fix deployed (increase pool size)
- T+35: Full recovery

Thanks to everyone involved in rapid response and resolution!
```

---

## Quick Reference Cards

### For On-Call Engineer

```
INCIDENT RESPONSE CHECKLIST

□ 1. DETECT (First 5 min)
  □ Acknowledge alert
  □ Verify issue with curl/dashboard
  □ Assess scope (how many users? which service?)
  □ Create incident ticket

□ 2. STABILIZE (Next 30 min)
  □ Gather logs and metrics
  □ Attempt diagnosis (check database/cache/API)
  □ Restart service if needed
  □ Monitor for recovery

□ 3. FIX (30-60 min)
  □ Implement targeted fix
  □ Test locally
  □ Deploy fix
  □ Verify recovery with 15-min monitoring

□ 4. COMMUNICATE
  □ Update Slack every 10 min
  □ Confirm resolution with teams
  □ Schedule post-mortem

□ 5. DOCUMENT
  □ Save logs and metrics
  □ Note timeline
  □ Identify root cause
  □ Document fix for RCA
```

### Critical Commands

```bash
# Health check
curl http://localhost:8080/health | jq .status

# Error rate
curl http://localhost:8080/api/v1/metrics | jq .error_rate

# Restart API
docker-compose restart api

# View logs
docker-compose logs api | tail -100

# Quick rollback
git checkout pre-deployment-<TAG>
docker-compose build && docker-compose up -d
```

---

**Document Status**: Final  
**Last Updated**: 2026-05-19  
**Owner**: On-Call / DevOps Team  
**Review Frequency**: After each major incident
