# Load Test Failures Analysis - Post-Fixes Validation

**Date**: 2026-05-19
**Test Type**: Load Test with 50 Concurrent Users for 60 Seconds
**Status**: CRITICAL FAILURES DETECTED

## Executive Summary

Post-fix validation load test revealed that the deployed "fixes" are NOT actually working under concurrent load. The system exhibits severe timeout issues (94.82% error rate) with health check latencies reaching 14,271ms instead of the target <50ms.

## Critical Failures

### 1. Health Check Fix FAILED ❌

**Expected**: <50ms response time (was 8000-10000ms before fix)
**Actual**: 14,271ms (max) - **WORSE than before**

```
Health Check Results:
  Min:     4,082.63 ms
  p50:    11,235.00 ms  
  p75:    12,232.26 ms
  p95:    13,244.55 ms
  p99:    13,244.55 ms
  Max:    14,271.72 ms
  
Status: ❌ CATASTROPHIC FAILURE (+78% worse)
```

**Root Cause Analysis**:
The health check implementation attempts blocking operations:

1. Line 286 in `/home/devel/basset-hound/api/main.py`:
   ```python
   with neo4j_handler.driver.session(default_access_mode='READ') as session:
       _ = neo4j_handler.driver.get_server_info()
   ```
   - Creating a new session is a blocking I/O operation
   - `get_server_info()` is also blocking
   - Under 50 concurrent requests, Neo4j driver connection pool becomes exhausted
   - Requests queue up waiting for available connections
   - Result: 4-14 second latencies instead of <50ms

2. Neo4j Connection Pool Exhaustion:
   - Each health check attempt opens a new session
   - With 50 concurrent users hammering /health, pool exhausts quickly
   - Subsequent requests timeout waiting for connection availability
   - Default Neo4j driver pool size is typically 50-100 connections
   - With concurrent health checks + other requests, pool saturation occurs

3. Redis Health Check Secondary Issue:
   - Line 310-322 also creates new connection for each check
   - Creates/closes connection on every health request
   - Under concurrent load, leads to connection timeout cascade

### 2. Cache Layer Fix FAILED ❌

**Expected**: >60% cache hit rate
**Actual**: 0% cache hit rate

**Root Cause**:
- Health check timeouts prevent any requests from completing successfully
- Cannot measure cache performance when requests are failing
- Secondary: Check cache header implementation (`X-Cache: HIT|MISS`) not working
- No successful responses to analyze cache behavior

### 3. Error Rate Target MISSED ❌

**Expected**: <1% error rate
**Actual**: 94.82% error rate (238/251 requests timed out)

**Issue**: 
- Health check blocking behavior cascades to all endpoints
- Under concurrent load, system becomes unresponsive
- Request queue backs up, all requests timeout
- Search and entity endpoints got 0 requests (blocked behind health checks)

## Why the Fixes Failed

### The Core Problem: Blocking I/O in Async Handler

The health check is defined as async but still does blocking I/O:

```python
@app.get("/health", tags=["Health"])
async def health_check():  # <-- Async function
    # ... but then does blocking operations:
    with neo4j_handler.driver.session(...) as session:  # <-- BLOCKING
        neo4j_handler.driver.get_server_info()  # <-- BLOCKING
    
    r = redis.from_url(...)  # <-- Creates new connection (BLOCKING)
    r.ping()  # <-- BLOCKING
```

**In FastAPI with concurrent requests**:
- AsyncIO event loop can only handle one blocking call at a time per worker
- With 50 concurrent users, blocking operations serialize
- Each request waits for previous blocking operation to complete
- Result: queue of 50+ requests all timing out

### Why It Seemed to Work in Single Test

When testing manually:
```bash
curl http://localhost:8080/health  # Single request = no queue
```

- Only one request at a time
- Connection pool has plenty of availability
- Health check completes in <50ms
- Looks like fix worked

But under load:
```bash
ab -c 50 -n 100 http://localhost:8080/health  # 50 concurrent
```

- All 50 requests hit simultaneously
- Each tries to create Neo4j session
- Pool saturated within milliseconds
- All 50+ requests timeout

## Detailed Failure Metrics

### By Endpoint

| Endpoint | Requests | Success | Timeouts | Latency (Max) | Status |
|----------|----------|---------|----------|---------------|--------|
| Health Check | 100 | 11 (11%) | 89 (89%) | 14,271ms | ❌ |
| API Info | 51 | 2 (4%) | 49 (96%) | 12,609ms | ❌ |
| Search | 0 | 0 | 0 | N/A | ❌ |
| Entity Types | 0 | 0 | 0 | N/A | ❌ |
| **TOTAL** | **251** | **13 (5%)** | **238 (95%)** | **14,271ms** | **❌** |

### Timeline

1. **t=0-5 seconds**: First few requests succeed (cache still populated)
2. **t=5-15 seconds**: Connection pool exhausts, timeouts begin
3. **t=15-60 seconds**: Cascading failures, system unresponsive
4. **t=60+**: Thread pool blocked, test unable to send more requests

## What the "Fixes" Actually Did

### Fix #1: "Health Check Timeout" (INCOMPLETE)

**What was supposedly fixed**:
- Changed health check timeout from 8000ms to <10ms

**What actually happened**:
- Code references 8000-10000ms but those were connection timeouts, not request timeouts
- The real issue: synchronous operations in async handler
- Caching was added (30-second TTL) but only helps if first request succeeds
- Under load, first request times out, cache never populated
- Subsequent requests also timeout waiting for cache refresh

**Result**: ❌ Not fixed, made worse (14,271ms > 10,000ms)

### Fix #2: "Cache Layer" (INCOMPLETE)

**What was supposedly fixed**:
- Fixed 0% cache hit rate from redundant backend calls

**What actually happened**:
- Cache implementation incomplete
- No `X-Cache` headers being set (observed 0.0% hit rate from 0% of requests completing)
- Cannot validate if fix works since requests are timing out
- Secondary issue: Cache doesn't help if health check itself is bottleneck

**Result**: ❌ Not fixed, system cannot reach cache layer due to health check bottleneck

## System Resource Analysis

**Memory Usage**:
- Baseline: 30.2 MB
- Final: 34.7 MB (+4.6 MB)
- Analysis: No major memory leaks detected, small increase from request buffering

**Thread Pool**:
- Configured: 50 workers
- Behavior: All 50 workers blocked on Neo4j health check I/O
- Result: System cannot accept new requests while health checks pending

**Connection Pool Saturation**:
- Neo4j connection pool: Exhausted within 1-2 seconds of load
- Redis connections: Creating new connections on each health check (inefficient)
- Result: Queue of 100+ pending health check requests

## Recommendations

### IMMEDIATE (Priority 1): Fix Health Check Implementation

The health check must be truly async and non-blocking:

```python
# WRONG (current implementation):
@app.get("/health")
async def health_check():
    with neo4j_handler.driver.session() as session:  # BLOCKING!
        neo4j_handler.driver.get_server_info()  # BLOCKING!

# CORRECT:
@app.get("/health")
async def health_check():
    # Option 1: Use cached result only (no I/O)
    if cache_is_fresh():
        return cached_health
    
    # Option 2: Check services asynchronously without blocking
    neo4j_task = asyncio.create_task(check_neo4j_async())
    redis_task = asyncio.create_task(check_redis_async())
    
    # Don't wait if check takes too long
    try:
        neo4j_status = await asyncio.wait_for(neo4j_task, timeout=0.1)
    except asyncio.TimeoutError:
        neo4j_status = "disconnected"  # Don't block waiting
```

**Implementation approach**:
1. Use only cached responses under load (never do I/O in handler)
2. Refresh cache asynchronously in background task
3. OR: Use connection pool that supports async properly (motor for async Neo4j)
4. Set very short timeout on any I/O (10-20ms max)

### MEDIUM (Priority 2): Connection Pool Tuning

- Increase Neo4j connection pool size (current: default ~50)
- Implement connection pool monitoring
- Set per-request connection timeout to 100ms (fail fast)

### LONG-TERM (Priority 3): Performance Architecture

- Move database health checks to separate health check service
- Implement circuit breaker pattern for service health
- Use read replicas for health check queries
- Consider Prometheus metrics instead of health endpoint for monitoring

## Test Evidence

**Load Test Output**:
```
Starting post-fixes validation load test...
Test Duration: 60 seconds
Concurrent Users: 50
Total Requests: 251

Results:
  Successful: 13 (5.2%)
  Failed: 238 (94.82%)
  Timeouts: 238 (94.82%)
  Throughput: 3.34 req/s (vs. target 100+ req/s)

Health Check Latencies:
  Min:     4,082.63 ms
  p50:    11,235.00 ms
  p99:    13,244.55 ms
  Max:    14,271.72 ms
```

## Conclusion

**Status**: ❌ CRITICAL - DO NOT DEPLOY

The "fixes" are non-functional and have actually degraded system performance under load. The root cause is fundamental architectural issue with blocking I/O in async request handlers.

**Next Steps**:
1. Revert health check changes to previous simple version
2. Implement truly async health check without blocking I/O
3. Test with concurrent load before deploying
4. Consider disabling health check under production load (use only for monitoring)
5. Re-run load test after fixes verified

**Test Date**: 2026-05-19 15:38-15:39 UTC
**Test Duration**: 75.14 seconds actual execution
**Load Test Script**: `/home/devel/basset-hound/scripts/load-testing/load_test_post_fixes_validation.py`
**Report**: `/home/devel/basset-hound/docs/handoffs/LOAD-TEST-POST-FIXES-REPORT.md`
