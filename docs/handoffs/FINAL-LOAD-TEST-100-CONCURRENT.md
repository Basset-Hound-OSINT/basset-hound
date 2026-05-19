# Final Load Test Report: 100 Concurrent Users

**Date**: 2026-05-19T16:04:29.562869
**Duration**: 120.17 seconds
**Concurrent Users**: 100

## Executive Summary

❌ **TEST FAILED** - Issues detected during testing

See detailed results below for specific failures.

## Test Results

| Metric | Value |
|--------|-------|
| Total Requests | 400 |
| Successful | 95 (23.8%) |
| Failed | 305 (76.25%) |
| Throughput | 0.79 req/s |

## Per-Endpoint Results

### Health Check

- Requests: 61
- p99: 28387.94ms
- Max: 29411.86ms
- Avg: 13127.23ms

### Search (Responsive Check)

- Requests: 34
- p99: 28465.06ms
- Max: 29482.31ms
- Avg: 23329.05ms

## Success Criteria

| Criterion | Target | Actual | Status |
|-----------|--------|--------|--------|
| Health Check p99 | <100ms | 28387.94ms | ❌ |
| Error Rate | <5% | 76.25% | ❌ |
| Concurrent Users | 100 | 100 | ✅ |


**Report Generated**: 2026-05-19T16:04:29.563367
