# Phase 3: Backend Scaling Roadmap
## Weeks 5-8 (Post-Phase 2)

**Date**: 2026-05-19  
**Duration**: 4 weeks  
**Target**: Scale to 10,000+ concurrent users  
**Start**: Week of 2026-06-17 (Week 5 post-deployment)  
**Expected Completion**: Week of 2026-07-14 (Week 8)  
**Target Throughput**: 3+ req/s → 100+ req/s

---

## Executive Summary

Phase 3 focuses on backend scaling and database optimization. Currently, the system handles ~3-5 requests per second. By implementing query optimization, database replication, advanced caching, and an API gateway, we target >100 requests per second, supporting 10,000+ concurrent users.

**Key Focus**:
- Query Optimization (-400ms worst case)
- Database Replication (read scalability)
- Advanced Caching (Redis cluster)
- API Gateway (rate limiting + request aggregation)

---

## Success Criteria

### Primary Metrics
| Metric | Current | Target | Improvement |
|--------|---------|--------|------------|
| **API Throughput** | 3-5 req/s | 100+ req/s | 20-30x |
| **P99 Query Latency** | <100ms | <50ms | -50ms |
| **Cache Hit Rate** | 70% | 85%+ | +15% |
| **Database Queries/sec** | 200 | <50 | -75% |
| **Concurrent Users** | 100-200 | 10,000+ | 50-100x |
| **Error Rate** | <0.1% | <0.05% | Maintain |

### Infrastructure Scaling
| Component | Current | Scaled | Ratio |
|-----------|---------|--------|-------|
| **API Instances** | 1 | 4-8 | 4-8x |
| **Database Connections** | 150 | 300 | 2x |
| **Cache Nodes** | 1 | 3 (cluster) | 3x |
| **Read Replicas** | 0 | 2-3 | 2-3x |

---

## 1. Query Optimization (-400ms)

### 1.1 Query Performance Profiling

**Objective**: Identify slow queries and optimize them.

**Tool**: Neo4j Query Log

**Implementation**:
```bash
# Enable slow query logging in Neo4j
docker exec neo4j cypher-shell -u neo4j -p $PASSWORD <<'EOF'
CALL apoc.config.set('dbms.logs.query.enabled', true);
CALL apoc.config.set('dbms.logs.query.threshold', '100ms');
EOF

# Verify enabled
docker exec neo4j cypher-shell -u neo4j -p $PASSWORD \
  "SHOW SETTINGS WHERE name CONTAINS 'query'" | grep -E "enabled|threshold"
```

**Common Slow Queries**:
1. **Full graph traversal**: `MATCH (n) RETURN n` (unindexed)
2. **Regex searches**: `WHERE n.name =~ '.*pattern.*'` (slow)
3. **Cartesian products**: Missing WHERE clause causing N×M matches
4. **Missing indexes**: Query without index lookups

**File**: `/home/devel/basset-hound/api/services/neo4j_service.py`

### 1.2 Index Strategy

**Current Indexes**:
```
CREATE FULLTEXT INDEX entity_search IF NOT EXISTS
  FOR (e:Entity) ON EACH [e.name, e.description];
CREATE INDEX entity_type_idx IF NOT EXISTS
  FOR (e:Entity) ON (e.entity_type);
CREATE INDEX project_id_idx IF NOT EXISTS
  FOR (e:Entity) ON (e.project_id);
```

**New Indexes to Add**:
```cypher
-- Relationship efficiency
CREATE INDEX relationship_type_idx IF NOT EXISTS
  FOR (r:RELATES_TO) ON (r.relationship_type);
CREATE INDEX relationship_created_idx IF NOT EXISTS
  FOR (r:RELATES_TO) ON (r.created_at);

-- Activity tracking
CREATE INDEX activity_timestamp_idx IF NOT EXISTS
  FOR (a:ActivityLog) ON (a.timestamp);
CREATE INDEX activity_user_idx IF NOT EXISTS
  FOR (a:ActivityLog) ON (a.user_id);

-- Search optimization
CREATE INDEX entity_status_idx IF NOT EXISTS
  FOR (e:Entity) ON (e.status);
CREATE INDEX entity_updated_idx IF NOT EXISTS
  FOR (e:Entity) ON (e.updated_at);

-- Composite indexes for common queries
CREATE INDEX entity_project_type_idx IF NOT EXISTS
  FOR (e:Entity) ON (e.project_id, e.entity_type);
```

**Expected Improvement**: -150ms

**Effort**: 3 hours  
**Priority**: P0

### 1.3 Query Plan Optimization

**Technique**: Reorder WHERE clauses to use indexes first.

**BEFORE** (scans all entities):
```cypher
MATCH (e:Entity)
WHERE e.name CONTAINS 'search_term'
  AND e.entity_type = 'Person'
  AND e.project_id = 'proj_123'
RETURN e
```

**AFTER** (uses index first):
```cypher
MATCH (e:Entity)
WHERE e.project_id = 'proj_123'     -- Index lookup first
  AND e.entity_type = 'Person'      -- Filter by indexed property
  AND e.name CONTAINS 'search_term' -- Expensive operation last
RETURN e
```

**Parameterized Queries**:
```python
# GOOD: Uses query plan caching
query = """
MATCH (e:Entity)
WHERE e.project_id = $project_id
  AND e.entity_type = $entity_type
RETURN e
"""
result = neo4j_service.query(query, {
  "project_id": project_id,
  "entity_type": entity_type
})

# BAD: Each query is unique, no caching
query = f"MATCH (e:Entity) WHERE e.project_id = '{project_id}' RETURN e"
```

**Expected Improvement**: -100ms

**Effort**: 4 hours  
**Priority**: P0

### 1.4 Result Set Projection

**Technique**: Only fetch needed columns.

**BEFORE** (fetches everything):
```cypher
MATCH (e:Entity)
WHERE e.project_id = $project_id
RETURN e  -- Returns all properties
```

**AFTER** (fetches only needed columns):
```cypher
MATCH (e:Entity)
WHERE e.project_id = $project_id
RETURN e.id, e.name, e.entity_type, e.created_at
-- Skips: description, metadata, internal fields
```

**Expected Improvement**: -50ms (reduced network transfer)

**Effort**: 2 hours  
**Priority**: P1

### 1.5 Lazy Loading Strategy

**Implementation**:
```python
# entities_service.py
async def get_entity(entity_id: str, include_relationships: bool = False):
    """
    Get entity by ID.
    Relationships are loaded on-demand only.
    """
    query = """
    MATCH (e:Entity {id: $entity_id})
    RETURN e.id, e.name, e.entity_type, e.created_at
    """
    
    entity = await neo4j_service.query(query, {"entity_id": entity_id})
    
    if include_relationships:
        # Load relationships separately
        rel_query = """
        MATCH (e:Entity {id: $entity_id})-[r]->(target)
        RETURN type(r) as rel_type, target.id, target.name
        """
        relationships = await neo4j_service.query(
            rel_query,
            {"entity_id": entity_id}
        )
        entity['relationships'] = relationships
    
    return entity
```

**Expected Improvement**: -100ms

**Effort**: 3 hours  
**Priority**: P0

**Total Expected Improvement**: -400ms

---

## 2. Database Replication

### 2.1 Read Replica Setup

**Architecture**:
```
Primary (Write)
├── Replica 1 (Read)
└── Replica 2 (Read)
```

**Neo4j Replication Setup** (Neo4j 5.0+):
```bash
# On primary
docker exec neo4j_primary cypher-shell <<'EOF'
:system
enable server [Neo4j] primary;
EOF

# On replica 1
docker exec neo4j_replica1 cypher-shell <<'EOF'
:system
enable server [Neo4j] secondary;
EOF

# Verify replication
docker exec neo4j_primary cypher-shell "SHOW SERVERS;"
```

**Application Configuration** (`api/config.py`):
```python
class DatabaseConfig(BaseSettings):
    # Primary (write)
    NEO4J_PRIMARY_URI: str = "bolt://neo4j-primary:7687"
    
    # Replicas (read-only)
    NEO4J_REPLICA_URIS: list[str] = [
        "bolt://neo4j-replica1:7687",
        "bolt://neo4j-replica2:7687"
    ]
    
    # Connection routing
    NEO4J_ROUTING_POLICY: str = "least_connected"  # Round-robin load balancing
```

**Write Consistency Strategy**:
- All writes go to primary
- Reads can go to any replica (eventual consistency)
- Critical reads (within transaction) go to primary

**Effort**: 6 hours  
**Priority**: P1

### 2.2 Failover Procedures

**Automatic Failover** (Neo4j Causal Clustering):
1. Monitor primary health (heartbeat every 5s)
2. If primary unresponsive for 15s, promote replica
3. Update connection strings
4. Resume operations

**Manual Failover Procedure**:
```bash
#!/bin/bash
# scripts/failover.sh

PRIMARY="neo4j_primary"
REPLICA1="neo4j_replica1"

# 1. Stop writes to primary
docker exec $PRIMARY /bin/sh -c 'kill -SIGSTOP 1'

# 2. Promote replica
docker exec $REPLICA1 cypher-shell -u neo4j <<'EOF'
:system
enable server [Neo4j] primary;
EOF

# 3. Update application config
# Edit docker-compose.yml or .env to point to new primary

# 4. Restart API
docker compose restart basset_api

# 5. Verify data consistency
docker exec $REPLICA1 cypher-shell "MATCH (n) RETURN count(n);"
```

**Effort**: 3 hours  
**Priority**: P1

### 2.3 Read Load Balancing

**File**: `/home/devel/basset-hound/api/services/neo4j_service.py`

```python
class Neo4jService:
    def __init__(self):
        self.primary_driver = GraphDatabase.driver(config.NEO4J_PRIMARY_URI)
        self.replica_drivers = [
            GraphDatabase.driver(uri)
            for uri in config.NEO4J_REPLICA_URIS
        ]
        self.replica_index = 0
    
    async def execute_read(self, query: str, params: dict = None):
        """
        Execute read query on least-connected replica.
        Falls back to primary if all replicas down.
        """
        # Round-robin through replicas
        driver = self.replica_drivers[self.replica_index % len(self.replica_drivers)]
        self.replica_index += 1
        
        try:
            session = driver.session()
            result = session.run(query, params)
            return list(result)
        except Exception as e:
            logger.warning(f"Replica query failed: {e}, falling back to primary")
            session = self.primary_driver.session()
            result = session.run(query, params)
            return list(result)
    
    async def execute_write(self, query: str, params: dict = None):
        """
        Execute write query on primary only.
        """
        session = self.primary_driver.session()
        tx = session.begin_transaction()
        try:
            result = tx.run(query, params)
            tx.commit()
            return list(result)
        except Exception as e:
            tx.rollback()
            raise
```

**Expected Improvement**: 3-5x throughput increase

**Effort**: 4 hours  
**Priority**: P1

---

## 3. Advanced Caching

### 3.1 Redis Cluster Setup

**Current**: Single Redis instance  
**Target**: 3-node Redis cluster

**Setup**:
```bash
# docker-compose.yml additions
redis-1:
  image: redis:7-alpine
  command: redis-server --port 6379 --cluster-enabled yes
  ports: ["6379:6379"]
  volumes: ["redis_1_data:/data"]

redis-2:
  image: redis:7-alpine
  command: redis-server --port 6379 --cluster-enabled yes
  ports: ["6380:6379"]
  volumes: ["redis_2_data:/data"]

redis-3:
  image: redis:7-alpine
  command: redis-server --port 6379 --cluster-enabled yes
  ports: ["6381:6379"]
  volumes: ["redis_3_data:/data"]

# Create cluster
docker exec redis-1 redis-cli --cluster create \
  127.0.0.1:6379 127.0.0.1:6380 127.0.0.1:6381 \
  --cluster-replicas 1
```

**Application Update** (`api/config.py`):
```python
REDIS_CLUSTER_NODES = [
    "redis-1:6379",
    "redis-2:6379",
    "redis-3:6379"
]

# Create cluster client
from redis.cluster import RedisCluster
redis_client = RedisCluster(
    startup_nodes=REDIS_CLUSTER_NODES,
    decode_responses=True,
    skip_full_coverage_check=True
)
```

**Expected Improvement**: 3x throughput, auto-failover

**Effort**: 4 hours  
**Priority**: P1

### 3.2 Cache Warming Strategy

**Objective**: Pre-load hot data on startup.

**Implementation** (`api/services/cache_service.py`):
```python
async def warm_cache():
    """
    Pre-populate cache with frequently accessed data on startup.
    Runs at server startup.
    """
    logger.info("Starting cache warm-up...")
    
    # 1. Cache popular entities
    popular_entities = await neo4j_service.query("""
        MATCH (e:Entity)
        WHERE e.view_count > 100
        RETURN e.id, e.name, e.entity_type
        ORDER BY e.view_count DESC
        LIMIT 1000
    """)
    
    for entity in popular_entities:
        await redis_client.setex(
            f"entity:{entity['id']}",
            ttl=3600,
            value=json.dumps(entity)
        )
    
    # 2. Cache relationship types
    rel_types = await neo4j_service.query("""
        MATCH (r:RELATES_TO)
        RETURN DISTINCT r.relationship_type
    """)
    
    await redis_client.setex(
        "relationship_types",
        ttl=86400,
        value=json.dumps([r['relationship_type'] for r in rel_types])
    )
    
    # 3. Cache project metadata
    projects = await neo4j_service.query("""
        MATCH (p:Project)
        RETURN p.id, p.name, p.entity_count
    """)
    
    for project in projects:
        await redis_client.setex(
            f"project:{project['id']}",
            ttl=1800,
            value=json.dumps(project)
        )
    
    logger.info(f"Cache warm-up complete: {len(popular_entities)} entities cached")

# Call on startup
@app.on_event("startup")
async def startup():
    await warm_cache()
```

**Expected Improvement**: -50ms (first request latency)

**Effort**: 3 hours  
**Priority**: P2

### 3.3 Intelligent Cache Invalidation

**Technique**: Event-based invalidation instead of time-based.

**Implementation**:
```python
# In update_entity() method
async def update_entity(entity_id: str, updates: dict):
    # 1. Update database
    entity = await neo4j_service.update_entity(entity_id, updates)
    
    # 2. Invalidate affected caches
    invalidation_keys = [
        f"entity:{entity_id}",
        f"entity:{entity_id}:relationships",
        f"search:*",  # Invalidate all searches
        f"transitive:*:{entity_id}:*",  # Invalidate transitive queries
    ]
    
    for key_pattern in invalidation_keys:
        if '*' in key_pattern:
            # Delete by pattern
            keys = await redis_client.keys(key_pattern)
            if keys:
                await redis_client.delete(*keys)
        else:
            # Direct delete
            await redis_client.delete(key_pattern)
    
    # 3. Publish event for other services
    await redis_client.publish('entity:updated', json.dumps({
        'entity_id': entity_id,
        'timestamp': datetime.utcnow().isoformat()
    }))
    
    return entity
```

**Expected Improvement**: Reduced cache misses

**Effort**: 2 hours  
**Priority**: P1

---

## 4. API Gateway Implementation

### 4.1 Rate Limiting

**Architecture**: Nginx-based rate limiting (edge) + API rate limiting (application)

**Nginx Configuration** (`nginx/nginx.conf`):
```nginx
# Rate limiting upstream
upstream basset_api {
    # Load balance across 4 API instances
    server basset_api_1:8000;
    server basset_api_2:8000;
    server basset_api_3:8000;
    server basset_api_4:8000;
    keepalive 32;
}

# Rate limit zones
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=100r/s;
limit_req_zone $http_x_api_key zone=api_key_limit:10m rate=1000r/s;
limit_req_zone $request_uri zone=endpoint_limit:10m rate=500r/s;

server {
    listen 80;
    
    # Global rate limit
    limit_req zone=api_limit burst=200 nodelay;
    
    location /api/v1/ {
        # Endpoint-specific rate limit
        limit_req zone=endpoint_limit burst=50 nodelay;
        
        # API key rate limit (if using API keys)
        limit_req zone=api_key_limit burst=200 nodelay;
        
        # Proxy to upstream
        proxy_pass http://basset_api;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

**Application-Level Rate Limiting** (`api/utils/rate_limiting.py`):
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# Usage in endpoints
@app.get("/api/v1/entities")
@limiter.limit("100/minute")  # 100 requests per minute
async def list_entities():
    # ...
    pass

# Expensive operations: lower limit
@app.post("/api/v1/ml/duplicates/merge")
@limiter.limit("10/minute")  # 10 requests per minute
async def merge_entities():
    # ...
    pass
```

**Expected Improvement**: Protection from abuse, fair resource allocation

**Effort**: 3 hours  
**Priority**: P1

### 4.2 Request Aggregation

**Objective**: Combine multiple requests into one backend call.

**Example**: Fetch multiple entities efficiently

**BEFORE** (5 requests):
```javascript
// Browser sends 5 separate requests
const entity1 = await fetch('/api/v1/entities/id1');
const entity2 = await fetch('/api/v1/entities/id2');
const entity3 = await fetch('/api/v1/entities/id3');
const entity4 = await fetch('/api/v1/entities/id4');
const entity5 = await fetch('/api/v1/entities/id5');
// Latency: 5x network roundtrip
```

**AFTER** (1 request):
```javascript
// Browser sends 1 request with batch
const response = await fetch('/api/v1/entities/batch', {
  method: 'POST',
  body: JSON.stringify({
    ids: ['id1', 'id2', 'id3', 'id4', 'id5']
  })
});
const entities = await response.json();
// Latency: 1x network roundtrip
```

**Implementation** (`api/routers/entities.py`):
```python
@router.post("/api/v1/entities/batch")
async def get_entities_batch(request: BatchEntityRequest):
    """
    Get multiple entities in a single request.
    Reduces API calls and latency.
    """
    entity_ids = request.ids[:100]  # Limit to 100 per request
    
    query = """
    MATCH (e:Entity)
    WHERE e.id IN $ids
    RETURN e.id, e.name, e.entity_type, e.created_at
    """
    
    entities = await neo4j_service.query(query, {"ids": entity_ids})
    return {
        "entities": entities,
        "count": len(entities),
        "total_requested": len(request.ids)
    }
```

**Expected Improvement**: 50-80% reduction in API calls

**Effort**: 2 hours  
**Priority**: P2

### 4.3 Response Caching in Gateway

**Technique**: Cache GET responses at Nginx level.

**Nginx Configuration**:
```nginx
# Cache configuration
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=api_cache:100m max_size=1g inactive=60m;

location /api/v1/ {
    # Cache only GET requests
    proxy_cache api_cache;
    proxy_cache_methods GET HEAD;
    proxy_cache_valid 200 302 60m;
    proxy_cache_valid 404 1m;
    
    # Add cache status header for debugging
    add_header X-Cache-Status $upstream_cache_status;
    
    proxy_pass http://basset_api;
}
```

**Expected Improvement**: 2-3x throughput increase for GET-heavy workloads

**Effort**: 1 hour  
**Priority**: P2

---

## 5. Horizontal Scaling Implementation

### 5.1 Multi-Instance Deployment

**Current**: 1 API instance  
**Target**: 4-8 instances

**Docker Compose Configuration**:
```yaml
services:
  basset_api_1:
    image: basset-hound:phase3
    environment:
      - API_PORT=8001
    ports: ["8001:8001"]

  basset_api_2:
    image: basset-hound:phase3
    environment:
      - API_PORT=8002
    ports: ["8002:8002"]

  basset_api_3:
    image: basset-hound:phase3
    environment:
      - API_PORT=8003
    ports: ["8003:8003"]

  basset_api_4:
    image: basset-hound:phase3
    environment:
      - API_PORT=8004
    ports: ["8004:8004"]

  nginx:
    image: nginx:alpine
    ports: ["80:80", "443:443"]
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - basset_api_1
      - basset_api_2
      - basset_api_3
      - basset_api_4
```

**Load Balancing** (in nginx.conf):
```nginx
upstream basset_api {
    least_conn;  # Route to least-connected instance
    server basset_api_1:8001 max_fails=2 fail_timeout=30s;
    server basset_api_2:8002 max_fails=2 fail_timeout=30s;
    server basset_api_3:8003 max_fails=2 fail_timeout=30s;
    server basset_api_4:8004 max_fails=2 fail_timeout=30s;
}
```

**Health Checks**:
```nginx
location /health {
    access_log off;
    proxy_pass http://basset_api;
}
```

**Expected Improvement**: 4-8x throughput increase

**Effort**: 4 hours  
**Priority**: P0

### 5.2 Session Affinity (if needed)

**Technique**: Use sticky sessions for WebSocket connections.

```nginx
map $remote_addr $route_id {
    default "route_${msec}";
}

upstream basset_api {
    hash $route_id consistent;  # Sticky routing
    server basset_api_1:8001;
    server basset_api_2:8002;
    server basset_api_3:8003;
    server basset_api_4:8004;
}
```

**Effort**: 1 hour  
**Priority**: P2

---

## Project Timeline

### Week 5 (Jun 17 - Jun 23)

**Sprint Goals**: Query optimization + index tuning

| Day | Task | Effort | Owner |
|-----|------|--------|-------|
| Mon | Query profiling + analysis | 3h | Backend |
| Tue | Index strategy + implementation | 3h | DBA |
| Wed | Query plan optimization | 4h | Backend |
| Thu | Lazy loading implementation | 3h | Backend |
| Fri | Performance testing | 2h | QA |

**Expected Gains**: -400ms, 2x throughput

### Week 6 (Jun 24 - Jun 30)

**Sprint Goals**: Database replication + read scaling

| Day | Task | Effort | Owner |
|-----|------|--------|-------|
| Mon | Replica setup + testing | 6h | DBA |
| Tue | Failover procedures | 3h | DBA |
| Wed | Read load balancing | 4h | Backend |
| Thu | Multi-instance deployment | 4h | DevOps |
| Fri | Load testing | 2h | QA |

**Expected Gains**: 3-5x throughput

### Week 7 (Jul 1 - Jul 7)

**Sprint Goals**: Advanced caching + cluster setup

| Day | Task | Effort | Owner |
|-----|------|--------|-------|
| Mon | Redis cluster setup | 4h | DevOps |
| Tue | Cache warming + strategy | 3h | Backend |
| Wed | Intelligent invalidation | 2h | Backend |
| Thu | Rate limiting implementation | 3h | Backend |
| Fri | Performance testing | 2h | QA |

**Expected Gains**: 3x throughput, improved cache hit rate

### Week 8 (Jul 8 - Jul 14)

**Sprint Goals**: API gateway + comprehensive testing

| Day | Task | Effort | Owner |
|-----|------|--------|-------|
| Mon | Request aggregation | 2h | Backend |
| Tue | Response caching | 1h | DevOps |
| Wed | Horizontal scaling setup | 4h | DevOps |
| Thu | Load testing (10k concurrent) | 4h | QA |
| Fri | Documentation + validation | 2h | DevOps |

**Expected Gains**: 20-30x total improvement from Phase 1

---

## Success Metrics & Validation

### Load Testing (Locust / Apache JMeter)

```bash
# Test script: 10,000 concurrent users, 60 seconds
npm run load-test:heavy

# Expected results
# Throughput: 100+ req/s (from 3-5 req/s)
# P99 latency: <50ms
# Error rate: <0.05%
# Cache hit rate: 85%+
```

### Database Performance

```bash
# Verify indexes used
docker exec neo4j cypher-shell <<'EOF'
PROFILE MATCH (e:Entity)
WHERE e.project_id = 'test_proj'
  AND e.entity_type = 'Person'
RETURN e;
EOF

# Expected: IndexSeek, not AllNodesScan
```

### Cache Metrics

```bash
curl http://localhost:8080/api/v1/metrics

# Expected:
# cache_hit_rate: >0.85
# cache_misses: <1000 per minute
# average_query_latency: <50ms
```

---

## Deliverables

### Code Changes
- [ ] Query optimization and indexing
- [ ] Database replication setup
- [ ] Read load balancing
- [ ] Redis cluster implementation
- [ ] Cache warming and invalidation
- [ ] Rate limiting
- [ ] Request aggregation
- [ ] Multi-instance deployment
- [ ] Nginx configuration updates

### Infrastructure
- [ ] 2-3 read replicas configured
- [ ] Redis 3-node cluster
- [ ] 4-8 API instances
- [ ] Load balancer configuration
- [ ] Monitoring and alerts

### Documentation
- [ ] Database architecture diagram
- [ ] Scaling procedures
- [ ] Failover runbook
- [ ] Cache strategy guide
- [ ] Capacity planning

---

## Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|---|---|---|
| **Replication lag issues** | Medium | Medium | Implement read-after-write guarantee |
| **Cache coherency** | Medium | High | Explicit invalidation + monitoring |
| **Load balancer bottleneck** | Low | High | Use Nginx least-conn + keepalive |
| **Database connection exhaustion** | Low | Critical | Monitor pool usage + scale replicas |
| **Network bandwidth limit** | Low | Medium | Implement compression + caching |

---

## References

- [Neo4j Replication Documentation](https://neo4j.com/docs/operations-manual/current/clustering/)
- [Redis Cluster Documentation](https://redis.io/docs/management/scaling/)
- [Nginx Load Balancing](https://nginx.org/en/docs/http/load_balancing.html)
- [Database Indexing Best Practices](https://neo4j.com/docs/cypher-manual/current/performance/)

---

**Owner**: Backend + DevOps Team  
**Last Updated**: 2026-05-19  
**Status**: Ready for Planning  
**Next Review**: Start of Week 5 (2026-06-17)
