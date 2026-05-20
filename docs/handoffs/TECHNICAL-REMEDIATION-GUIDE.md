# Technical Remediation Guide

**Objective**: Fix Neo4j connection pool bottleneck and enable production deployment

**Timeline**: 2-3 days  
**Difficulty**: Medium (configuration changes + query optimization)

---

## Issue Analysis

### Current System Behavior

```
100 Concurrent Users
        ↓
4 Uvicorn Workers (25 requests each)
        ↓
Neo4j Connection Pool (~20 connections)
        ↓
Queue Buildup
        ↓
30-second Nginx timeout
        ↓
63.75% Error Rate
```

### Target Behavior After Fix

```
100 Concurrent Users
        ↓
4 Uvicorn Workers (25 requests each)
        ↓
Neo4j Connection Pool (150+ connections)
        ↓
Requests Complete in <500ms
        ↓
Request Queuing (Semaphore 50)
        ↓
<5% Error Rate
```

---

## Step-by-Step Remediation

### Step 1: Neo4j Connection Pool Expansion (0.5 days)

**File**: `docker-compose.yml`

**Current**:
```yaml
neo4j:
  image: neo4j:5.26-community
  environment:
    - NEO4J_AUTH=neo4j/neo4jbasset
```

**Change To**:
```yaml
neo4j:
  image: neo4j:5.26-community
  environment:
    - NEO4J_AUTH=neo4j/neo4jbasset
    # Connection pool tuning
    - NEO4J_dbms_connector_bolt_connection_guard_max_connections=150
    - NEO4J_dbms_connection_pool_acquisition_timeout=30
    - NEO4J_server_memory_heap_initial_size=2G
    - NEO4J_server_memory_heap_max_size=4G
    # Query timeout (5 seconds)
    - NEO4J_dbms_transaction_timeout=5s
```

**Validation**:
```bash
docker compose logs neo4j | grep "connection_guard"
# Should show: dbms.connector.bolt.connection_guard.max_connections=150
```

---

### Step 2: Query Optimization (1.5 days)

**Issue**: Projects endpoint uses N+1 query pattern

**Current Cypher** (in `api/routers/projects.py`):
```cypher
MATCH (project:Project {safe_name: $project_safe_name})
      -[:HAS_PERSON]->(person:Person)
OPTIONAL MATCH (person)-[:HAS_FIELD_VALUE]->(fv:FieldValue)
OPTIONAL MATCH (person)-[file_rel:HAS_FILE]->(file:File)
WITH person, COLLECT(DISTINCT {...}) AS field_values, ...
RETURN person, field_values, files
```

**Problem**: Three separate match clauses → multiple database round trips

**Optimized Cypher**:
```cypher
MATCH (project:Project {safe_name: $project_safe_name})
      -[:HAS_PERSON]->(person:Person)
OPTIONAL MATCH (person)-[:HAS_FIELD_VALUE]->(fv:FieldValue)
OPTIONAL MATCH (person)-[file_rel:HAS_FILE]->(file:File)
RETURN person,
       COLLECT(DISTINCT {
           section_id: fv.section_id,
           field_id: fv.field_id,
           value: fv.value
       }) AS field_values,
       COLLECT(DISTINCT {
           file: file,
           section_id: file_rel.section_id,
           field_id: file_rel.field_id
       }) AS files
ORDER BY person.created_at DESC
```

**Implementation**:
1. Use single RETURN clause (avoid intermediate WITH)
2. Server-side aggregation with COLLECT
3. Pre-compute relationships in single query

**Expected Impact**: 
- Query time: 15,000ms → <500ms
- Database round trips: 3+ → 1
- Connection pool contention: -66%

---

### Step 3: Implement Caching (1 day)

**File**: `api/services/cache_service.py`

**Add Cache Invalidation**:
```python
async def invalidate_project_cache(project_id: str):
    """Invalidate project cache when updated"""
    await cache.delete(f"projects:{project_id}")
    await cache.delete("projects:all")
```

**Cache Projects List** (30 seconds):
```python
@cache.cached(ttl=30, cache_key="projects:all")
async def get_all_projects():
    return await neo4j_service.query_projects()
```

**Cache Search Results** (5 seconds):
```python
@cache.cached(ttl=5, cache_key=lambda q: f"search:{q}")
async def search_entities(query: str):
    return await neo4j_service.search(query)
```

**Expected Impact**:
- Cache hit rate: >60%
- Search latency p99: 28,604ms → <500ms (cached hits)
- Database load: -40%

---

### Step 4: Request Concurrency Limiting (0.5 days)

**File**: `api/dependencies.py`

**Add Semaphore**:
```python
# Global Neo4j query semaphore
NEO4J_SEMAPHORE = asyncio.Semaphore(50)  # Max 50 concurrent queries

async def get_neo4j_session():
    async with NEO4J_SEMAPHORE:
        return neo4j_handler.get_session()
```

**Usage in Routers**:
```python
async def get_projects(project_name: str):
    async with NEO4J_SEMAPHORE:
        projects = await neo4j_service.get_project(project_name)
    return projects
```

**Expected Impact**:
- Request queue forms before Neo4j (not at database)
- Better error messages (queue timeout vs db timeout)
- Cleaner degradation (max 50 concurrent queries)

---

### Step 5: Add Query Timeouts (0.5 days)

**File**: `api/services/neo4j_service.py`

**Current**:
```python
result = session.run(query, parameters=params)
```

**Change To**:
```python
try:
    # 5 second query timeout
    result = session.run(
        query, 
        parameters=params,
        timeout=5  # seconds
    )
except TimeoutError:
    logger.warning(f"Query timeout: {query[:50]}...")
    # Return cached result or empty
    return get_cached_result() or []
```

**Expected Impact**:
- Prevent hanging requests (15+ seconds → 5 seconds max)
- Faster fallback to cache
- Clearer failure modes

---

### Step 6: Circuit Breaker Pattern (0.5 days)

**File**: `api/middleware/circuit_breaker.py` (new file)

```python
class Neo4jCircuitBreaker:
    def __init__(self, failure_threshold=0.5, timeout=30):
        self.failure_threshold = failure_threshold  # 50%
        self.timeout = timeout  # 30 seconds
        self.failure_count = 0
        self.success_count = 0
        self.state = "closed"  # closed, open, half-open
        
    async def call(self, func, *args, **kwargs):
        if self.state == "open":
            if time.time() - self.opened_at > self.timeout:
                self.state = "half-open"
            else:
                raise CircuitBreakerOpen()
        
        try:
            result = await func(*args, **kwargs)
            self.record_success()
            return result
        except Exception as e:
            self.record_failure()
            raise
    
    def record_success(self):
        self.success_count += 1
        self.failure_count = 0
        if self.state == "half-open":
            self.state = "closed"
    
    def record_failure(self):
        self.failure_count += 1
        error_rate = self.failure_count / (self.failure_count + self.success_count)
        if error_rate > self.failure_threshold:
            self.state = "open"
            self.opened_at = time.time()
```

**Usage**:
```python
breaker = Neo4jCircuitBreaker()

async def get_projects():
    return await breaker.call(neo4j_service.get_projects)
```

**Expected Impact**:
- System degrades gracefully (not cascading failure)
- Auto-recovery after 30 seconds
- Clear distinction between "slow" and "broken"

---

### Step 7: Graceful Degradation (0.5 days)

**File**: `api/routers/projects.py`

**Current**:
```python
@router.get("/projects/{name}")
async def get_project(name: str):
    # Throws error if Neo4j unavailable
    return await neo4j_service.get_project(name)
```

**Change To**:
```python
@router.get("/projects/{name}")
async def get_project(name: str):
    try:
        # Try fresh data with 3-second timeout
        return await asyncio.wait_for(
            neo4j_service.get_project(name),
            timeout=3.0
        )
    except asyncio.TimeoutError:
        logger.warning(f"Project query timeout, returning cache")
        # Fall back to cached data
        cached = await cache.get(f"projects:{name}")
        if cached:
            return cached
        # If no cache, return empty/minimal response
        return {
            "name": name,
            "status": "degraded",
            "message": "Database temporarily unavailable, using cached data"
        }
```

**Expected Impact**:
- Users get stale data instead of errors
- System remains available even when slow
- Better user experience during outages

---

## Testing & Validation

### Load Test After Each Step

```bash
# Step 1: Rerun with larger pool only
python3 scripts/load-testing/final_4worker_validation.py

# Expected: Throughput increases to 2-2.5 req/s

# Step 2: Rerun after query optimization
# Expected: Throughput increases to 3+ req/s, latency <500ms

# Step 3: Rerun after caching
# Expected: Error rate drops to <5%, cache hits >60%

# Step 4: Rerun after concurrency limiting
# Expected: Clean queue behavior, no cascading failures

# Step 5: Rerun after query timeouts
# Expected: Max latency <5 seconds, faster failure recovery

# Step 6: Rerun after circuit breaker
# Expected: Graceful degradation on failures, auto-recovery

# Step 7: Final validation with full stack
# Expected: All success criteria passed
```

### Success Criteria (Must Pass All)

```
✅ Throughput: 3+ req/s
✅ Error Rate: <5%
✅ Health Check p99: <100ms
✅ Projects p99: <500ms
✅ Search p99: <1000ms
✅ No Cascading Failures: System stable for full 60 seconds
✅ Graceful Degradation: Cached results on timeout
```

---

## Rollback Plan

If remediation causes issues:

```bash
# Revert docker-compose.yml to previous version
git checkout HEAD -- docker-compose.yml

# Restart services
docker compose down -v
docker compose up --build

# Verify previous behavior
curl http://localhost:8080/health
```

---

## Deployment Checklist After Remediation

- [ ] Neo4j connection pool set to 150
- [ ] Cypher queries optimized (single round trip)
- [ ] Cache layer implemented for projects/search
- [ ] Concurrency semaphore added (50 max)
- [ ] Query timeouts set to 5 seconds
- [ ] Circuit breaker pattern implemented
- [ ] Graceful degradation returns cache/degraded response
- [ ] Load test passes all success criteria
- [ ] No cascading failures observed
- [ ] Monitoring/alerts configured
- [ ] Rollback plan documented
- [ ] Team trained on new architecture

---

## Estimated Timeline

| Phase | Task | Time | Status |
|-------|------|------|--------|
| 1 | Connection pool + monitoring | 0.5 days | Ready |
| 2 | Query optimization | 1 day | Design phase |
| 3 | Caching + invalidation | 0.5 days | Ready |
| 4 | Concurrency semaphore | 0.5 days | Ready |
| 5 | Query timeouts | 0.5 days | Ready |
| 6 | Circuit breaker | 0.5 days | Design phase |
| 7 | Graceful degradation | 0.5 days | Ready |
| 8 | Testing + validation | 1 day | Depends on implementation |
| **Total** | | **4.5 days** | **Start Phase 1 today** |

---

## Questions & Troubleshooting

**Q: Why not just increase worker count to 8?**  
A: Workers don't help if the database is the bottleneck. More workers = more competition for connections.

**Q: Why 150 connections?**  
A: Safe maximum for ~100 concurrent users with 20% headroom. Too many increases Neo4j memory usage.

**Q: Can we deploy with cache-only mode first?**  
A: No - search and projects endpoints would serve stale data, unacceptable for OSINT platform.

**Q: What if Neo4j optimization doesn't help?**  
A: Likely missing N+1 query or other pattern. Profile with Neo4j query logs:
```
docker exec neo4j_osint_db cat /logs/neo4j.log | grep "SLOW"
```

---

**Next Step**: Implement Step 1 (Neo4j pool) and retest  
**Owner**: Backend team  
**Start Date**: Today (2026-05-19)  
**Target Completion**: 2026-05-22 (3 days)
