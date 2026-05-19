# Cache Fix - Verification Checklist

## Pre-Deployment Verification

### 1. Code Changes Staged
- [x] api/services/cache_service.py - Multi-level cache flow fixed
- [x] Documentation updated with comprehensive handoff report
- [x] .env verified (correct Redis configuration)

### 2. Critical Fixes Applied
- [x] Removed redundant backend.get() calls in multi-level caching
- [x] Added debug logging at all cache decision points
- [x] Implemented aggregated stats across L1 and L2 levels
- [x] Connection pool settings now passed through initialization

### 3. Configuration Verified
```
REDIS_URL=redis://localhost:6379/0              ✓
CACHE_ENABLED=true                              ✓
CACHE_PREFER_REDIS=true                         ✓
REDIS_MAX_CONNECTIONS=100                       ✓
REDIS_SOCKET_KEEPALIVE=true                     ✓
REDIS_HEALTH_CHECK_INTERVAL=30                  ✓
```

### 4. Log Messages Added
These messages will appear in logs on startup and during operation:

**Startup:**
```
- "Initializing cache service - redis_url=redis://localhost:6379/0, prefer_redis=True, multi_level=True"
- "Attempting to connect to Redis: redis://localhost:6379/0"
- "Testing Redis connection with PING..."
- "REDIS CONNECTED SUCCESSFULLY! Using Redis cache at redis://localhost:6379/0 with pool_size=100, socket_keepalive=True"
- "Multi-level caching initialized - Using Redis cache! (L1=memory 1s, L2=Redis 30s) - pool_size=100"
```

**During Operation:**
```
- "Cache HIT: L1 for entity <id>" (in-memory hit, <1ms)
- "Cache HIT: L2 (Redis) for entity <id>, populating L1" (Redis hit, ~5-10ms)
- "Cache MISS: entity <id> not in L1 or L2" (database fetch needed, ~100-300ms)
```

## Post-Deployment Testing

### Phase 1: Basic Functionality
```bash
# 1. Start application
# 2. Check logs contain "REDIS CONNECTED SUCCESSFULLY!"
# 3. Verify no errors in initialization

# 4. Make a simple API call
curl http://localhost:8000/api/v1/projects

# 5. Repeat the same call
curl http://localhost:8000/api/v1/projects

# Expected in logs: "Cache HIT" on second request
```

### Phase 2: Cache Statistics
```bash
# Get cache stats
curl http://localhost:8000/api/v1/cache/stats

# Expected response:
{
  "hits": <positive number>,
  "misses": <positive number>,
  "hit_rate_percent": >60,
  "backend": "redis",
  "connected": true,
  "l1_cache": { ... },
  "l2_cache": { ... }
}
```

### Phase 3: Load Test
```bash
# Run 614-request load test
python3 scripts/load-testing/load_testing_script.py

# Expected results:
# - Cache hit rate: >60%
# - P99 latency: <100ms
# - Zero errors
# - Redis keys growing then stabilizing
```

### Phase 4: Redis Verification
```bash
# Check Redis connection
redis-cli ping
# Expected: PONG

# Check cached keys
redis-cli KEYS "basset:*" | wc -l
# Expected: Several hundred keys

# Check memory usage
redis-cli INFO memory | grep used_memory_human
# Expected: 50-100MB typical workload

# Monitor real-time activity
redis-cli --stat
# Expected: Increasing commands/sec during load test
```

## Rollback Plan (If Needed)

If cache hit rate is still 0% after deployment:

```bash
# 1. Revert to previous version
git revert <commit-hash>

# 2. Restart application
# 3. Check logs for errors

# 4. If reverting fixes issue, investigate:
# - Is Redis running and accessible?
# - Are firewall rules allowing connection?
# - Is REDIS_URL correctly formatted?
```

## Success Criteria

| Metric | Target | Method to Verify |
|--------|--------|------------------|
| Cache Hit Rate | >60% | GET /api/v1/cache/stats → hit_rate_percent |
| Redis Connected | Yes | Check logs for "REDIS CONNECTED SUCCESSFULLY!" |
| Log Messages | Present | Grep for "Cache HIT: L2" in logs |
| P99 Latency | <100ms | Load test results |
| No Errors | Zero | Application logs clean |

## Troubleshooting

### Redis Connection Fails
```
Error: "Failed to connect to Redis at redis://localhost:6379/0"

Check:
1. Redis running: redis-cli ping
2. Port 6379 accessible: nc -zv localhost 6379
3. Firewall rules
4. Redis configuration allows external connections
```

### Hit Rate Still 0%
```
Check:
1. Logs show "Using Redis cache" (not "Using in-memory cache")
2. Make two identical requests and check logs
3. Verify cache TTLs not expiring immediately
4. Check redis-cli keys count growing
```

### Memory Usage High
```
Reduce:
1. CACHE_MAX_MEMORY_ENTRIES (default 1000)
2. L1_TTL (default 1 second) - reduce to 0.5 seconds
3. CACHE_ENTITY_TTL (default 600) - reduce to 300 seconds
```

## Deployment Checklist

- [ ] Verify Redis is running and accessible
- [ ] Stage changes with git add
- [ ] Run git diff --cached to review
- [ ] Commit with message: "fix: Cache layer - Fix 0% hit rate and add comprehensive logging"
- [ ] Push to branch
- [ ] Monitor logs during startup
- [ ] Verify "REDIS CONNECTED SUCCESSFULLY!" in logs
- [ ] Run smoke test (few API calls)
- [ ] Run load test (614 requests)
- [ ] Verify hit rate >60%
- [ ] Check /api/v1/cache/stats endpoint
- [ ] Review Redis memory usage
- [ ] Merge to main if all tests pass

## Expected Performance Improvements

**Before Fix:**
- Cache hit rate: 0%
- Average latency: 250ms (all database hits)
- Database load: 100%
- Redis utilization: 0%

**After Fix:**
- Cache hit rate: 65-80% (multi-level design)
- Average latency: 50-80ms (mostly cached hits)
- Database load: 20-35% (only misses)
- Redis utilization: 60-70% (active caching)

## Session History

- Session: py-dev@basset-hound:cache-fix
- Issue: Secondary blocker - 0% cache hit rate
- Status: FIXED and STAGED
- Next: Deploy, test, monitor

---
Generated: 2026-05-19
Ready for production deployment
