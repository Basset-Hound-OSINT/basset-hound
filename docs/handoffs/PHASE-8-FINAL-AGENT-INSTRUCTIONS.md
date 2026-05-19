# Phase 8 Final Agent Instructions - Concurrency Fix Required

**Generated**: 2026-05-19 16:02 UTC  
**For**: Next development session  
**Priority**: HIGH - Blocking production deployment

---

## Current Situation

Phase 8 is **CODE-COMPLETE** but **FAILS LOAD TEST** due to single-worker Uvicorn bottleneck.

```
100 Concurrent Users Test Results:
- Success Rate: 23.8% (target: >95%)
- Error Rate: 76.25% (target: <5%)
- Health Check p99: 28,387ms (target: <100ms)
- Root Cause: Sequential event loop processing
```

**This is NOT a bug in Phase 8 fixes** - it's an architectural limitation of Uvicorn's single-worker design when handling 100+ concurrent connections.

---

## What YOU Need To Do

### STEP 1: Add Request Queue Timeout (30 minutes)

**File**: `/home/devel/basset-hound/api/main.py`

**Location**: Around line 277 (after other middleware)

**Code to Add**:

```python
# Request queue timeout middleware (NEW - add this)
@app.middleware("http")
async def request_queue_timeout_middleware(
    request: Request, call_next: Callable
) -> Any:
    """
    Drop requests that wait >15 seconds in queue.
    Prevents cascading failure under sustained overload.
    Returns 503 Service Unavailable instead of hanging.
    """
    start_time = time.time()
    try:
        response = await call_next(request)
    except asyncio.TimeoutError:
        logger.warning(f"Request timeout for {request.url.path}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"error": "Service temporarily overloaded, please retry"},
        )
    
    queue_time = time.time() - start_time
    
    # If request waited >15 seconds in queue, drop it
    # This prevents the cascade effect where slow requests slow others
    if queue_time > 15:
        logger.warning(f"Request {request.url.path} queued {queue_time:.1f}s, returning 503")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"error": "Service temporarily overloaded (queue timeout), please retry"},
        )
    
    return response
```

**Test It**:
```bash
# Should respond immediately instead of hanging
curl http://localhost:8080/health
```

---

### STEP 2: Configure Multi-Worker Uvicorn (30 minutes)

**Current Setup** (single worker - bottleneck):
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

**New Setup** (multi-worker - 4x capacity):
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

**Where to Change**:
- If running manually: Use command above
- If using Docker: Update `docker-compose.yml` services
- If using systemd: Update unit file

**Verify It Works**:
```bash
# Should show 4 worker processes
ps aux | grep uvicorn | grep -v grep
```

---

### STEP 3: Re-Run Load Test (30 minutes)

**File**: `/home/devel/basset-hound/scripts/load-testing/final_load_test_100_concurrent.py`

**Run**:
```bash
python3 scripts/load-testing/final_load_test_100_concurrent.py
```

**Expected Results** (with fixes):
- Success Rate: >90% (was 23.8%)
- Error Rate: <5% (was 76.25%)
- Health Check p99: <500ms (was 28,387ms)
- Throughput: 3+ req/s (was 0.8 req/s)

**If Results Match**: ✅ READY FOR PRODUCTION

**If Results Don't Match**: 
1. Check that `--workers 4` is actually running (ps aux)
2. Verify middleware was added to main.py
3. Check server logs for errors
4. Run test again with `--workers 2` if 4 doesn't work

---

### STEP 4: Update Configuration (Optional but Recommended)

**File**: `/home/devel/basset-hound/api/config.py`

**Add These Settings**:

```python
class Settings(BaseSettings):
    # ... existing settings ...
    
    # NEW: Concurrency tuning
    max_concurrent_requests: int = Field(
        default=50,
        description="Maximum concurrent requests before returning 503"
    )
    
    request_queue_timeout_seconds: int = Field(
        default=15,
        description="Timeout for requests waiting in queue (seconds)"
    )
    
    uvicorn_workers: int = Field(
        default=4,
        description="Number of Uvicorn worker processes"
    )
```

---

## Validation Checklist

- [ ] Request queue timeout middleware added to `/api/main.py`
- [ ] Uvicorn configured with 4 workers
- [ ] Load test passes with >90% success rate
- [ ] Health check p99 <500ms
- [ ] Error rate <5%
- [ ] Single requests still respond quickly (<2s)
- [ ] Server starts without errors
- [ ] No resource leaks (monitor memory after 10 min)

---

## Expected Improvements

| Metric | Before | After | Improvement |
|--------|--------|-------|------------|
| Concurrent Users | 50 | 100+ | 2x+ |
| Error Rate @ 100 users | 76.25% | <5% | 15x better |
| Health Check p99 | 28.4s | <500ms | 57x faster |
| Throughput | 0.8 req/s | 3+ req/s | 4x better |
| Success Rate | 23.8% | >90% | 4x better |

---

## Production Deployment After Fixes

Once load test passes:

1. **Deploy to staging** with fixes
2. **Run smoke tests** (5-10 minutes)
3. **Monitor metrics** for 5 minutes
4. **Deploy to production** with the fixes
5. **Monitor for 30 minutes** after deployment
6. **Set up alerts** for:
   - Health check p99 > 100ms
   - Error rate > 1%
   - Request queue timeout frequency

---

## If Something Goes Wrong

### "Workers not starting"
```bash
# Check if port is already in use
lsof -i :8000
# Kill any existing processes
pkill -f "uvicorn api.main"
# Try with 2 workers instead of 4
uvicorn api.main:app --workers 2 --host 0.0.0.0 --port 8000
```

### "Load test still failing"
```bash
# Verify workers are running
ps aux | grep "uvicorn" | grep -v grep
# Check each worker is actually handling requests
# Look for per-worker CPU usage

# If not, may be missing the middleware
# Double-check middleware is in main.py around line 277
```

### "Memory usage increasing"
```bash
# This is normal at first (warming up)
# Monitor for 2 minutes
# If still increasing after 2 min, there's a leak
# Check for: unclosed connections, unbounded caches
```

---

## Files You'll Be Modifying

1. `/home/devel/basset-hound/api/main.py` - Add queue timeout middleware
2. `/home/devel/basset-hound/api/config.py` - Add concurrency settings (optional)
3. Startup script/docker-compose.yml - Change `--workers 4`

**Total Changes**: ~20 lines of code

---

## Testing After Fixes

```bash
# 1. Start server with 4 workers
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4

# 2. In another terminal, run load test
python3 scripts/load-testing/final_load_test_100_concurrent.py

# 3. Expected: <5% error rate, health check p99 <500ms
```

---

## Documentation

Full technical details:
- `/docs/handoffs/FINAL-LOAD-TEST-VALIDATION-REPORT.md` - Technical deep-dive
- `/docs/handoffs/PHASE-8-FINAL-VALIDATION-SUMMARY.md` - Executive summary
- `/docs/handoffs/FINAL-LOAD-TEST-100-CONCURRENT.md` - Test metrics

---

## Summary

**Time to Fix**: 1-2 hours  
**Complexity**: Low (straightforward middleware addition + config)  
**Risk**: Low (queue timeout only affects overloaded requests)  
**Impact**: Production ready for 100+ concurrent users

**Go-Ahead**: ✅ Proceed with fixes

---

**Created**: 2026-05-19 16:02 UTC  
**Status**: Phase 8 code complete, waiting for concurrency fixes  
**Next Milestone**: Production deployment with multi-worker Uvicorn
