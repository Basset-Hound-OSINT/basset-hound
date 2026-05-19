# Load Test Revalidation Report: Async Health Check Fix

**Date**: 2026-05-19T15:59:46.478536
**Test Type**: Health Check Performance Revalidation
**Duration**: 75.12 seconds
**Concurrent Users**: 50

## Executive Summary

❌ **REVALIDATION FAILED** - Issues detected

The async health check implementation may have issues.
See detailed results below for root cause analysis.

## Test Results

| Metric | Value |
|--------|-------|
| Total Requests | 250 |
| Successful | 31 |
| Failed | 219 |
| Error Rate | 87.60% |
| Test Duration | 75.12s |
| Throughput | 0.41 req/s |

## Health Check Performance (PRIMARY METRIC)

```
Requests:  26
Min:       4077.38ms
p50:       9123.34ms
p95:       12230.69ms
p99:       13243.79ms (target: <10ms)
Max:       13264.29ms
StdDev:    2588.29ms
Avg:       8404.32ms
```

❌ **FAIL** - 26 requests exceeded 10ms threshold
Max latency: 13264.29ms (target: <10ms)

## Before/After Comparison

| Metric | Previous (Sync) | Current (Async) | Improvement |
|--------|-----------------|-----------------|-------------|
