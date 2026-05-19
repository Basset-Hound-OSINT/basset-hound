# Load Test Post-Fixes Validation Report

**Date**: 2026-05-19T15:39:15.619601
**Test Type**: Post-Fixes Performance Validation
**Duration**: 75.14 seconds
**Concurrent Users**: 50

## Executive Summary

Validation of critical fixes deployed:
1. **Health check timeout fix** - Changed from 8000ms to <10ms cached
2. **Cache layer fix** - Fixed 0% hit rate (was redundant backend call)

**Test Results**: 2026-05-19 15:39:15 UTC

| Metric | Value |
|--------|-------|
| Total Duration | 75.14s |
| Total Requests | 251 |
| Successful | 13 (5.2%) |
| Failed | 238 |
| Error Rate | 94.82% |
| Timeout Rate | 94.82% |
| Throughput | 3.34 req/s |

## Success Criteria Validation

### 1. Health Check: ALL <50ms

- **p99**: 13244.55ms ❌
- **Max**: 14271.72ms ❌
- **Status**: ❌ FAIL

### 2. Cache Hit Rate: >60%

- **Average**: 0.0% ❌
- **Status**: ❌ FAIL

Detailed by endpoint:
  - Health Check (Fixed): 0.0%
  - API Info: 0.0%

### 3. Error Rate: <1%

- **Measured**: 94.82% ❌
- **Status**: ❌ FAIL
- **Timeouts**: 94.82%

### 4. Search Response: <200ms p99

- **Status**: ❌ NO DATA

## Success Criteria Summary

**Overall**: 0/4 criteria met

- ❌ Health check: ALL <50ms
- ❌ Error rate: <1%
- ❌ Cache hit rate: >60%
- ❌ Search: <200ms p99

## Detailed Endpoint Results

| Endpoint | Requests | Min (ms) | p50 (ms) | p99 (ms) | Max (ms) | Target | Cache Hit | Status |
|----------|----------|----------|----------|----------|----------|--------|-----------|--------|
| Health Check (Fixed) | 100 | 4082.6 | 11235.0 | 13244.6 | 14271.7 | 50 | 0% | ❌ |
| API Info | 51 | 10190.0 | 10190.0 | 10190.0 | 12608.5 | 50 | 0% | ❌ |
| Search Endpoint | 0 | N/A | N/A | N/A | N/A | 200 | N/A | ❌ |
| Entity Types | 0 | N/A | N/A | N/A | N/A | 100 | N/A | ❌ |

## Before/After Comparison

| Metric | Before Fix | After Fix | Improvement |
|--------|-----------|-----------|-------------|
| Health Check (max) | 8000-10000ms | 14271.72ms | **-42.7%** |
| Cache Hit Rate | 0% | 0.0% | **0.0%** |
| Error Rate | 100% (timeouts) | 94.82% | **5.2%** |

## Key Findings

⚠️ **Issues Detected**

   - Health check still exceeds target latency
   - Cache hit rate below 60% target (0.0%)
   - Error rate above 1% target (94.82%)
   - Timeout rate elevated (94.82%)

## Recommendations

⚠️ **Further Investigation Needed**

- Health check latency not meeting targets - review recent changes
- Cache hit rate below target - check cache configuration
- Review application error logs

## Test Configuration

- **Test Duration**: 60 seconds
- **Concurrent Users**: 50
- **Base URL**: http://localhost:8080
- **Request Timeout**: 15s
- **Total Requests**: 251
- **Throughput**: 3.34 req/s

## Conclusion

⚠️ **VALIDATION INCOMPLETE**

Some criteria not fully met. See issues section above.

---

**Report Generated**: 2026-05-19T15:39:15.619701
