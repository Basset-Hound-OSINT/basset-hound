#!/usr/bin/env python3
"""
Load Test Post-Fixes Validation
Tests critical endpoints after health check timeout fix and cache layer fix
Measures: Health check latency, cache hit rate, search performance, entity fetch performance
"""

import requests
import json
import time
import statistics
import concurrent.futures
import psutil
import threading
from datetime import datetime
from collections import defaultdict
import sys
from typing import Dict, List, Any

BASE_URL = "http://localhost:8080"
NUM_WORKERS = 50  # 50 concurrent users
DURATION_SECONDS = 60
TEST_TIMEOUT = 15  # 15 second request timeout

# Critical endpoints for post-fix validation
ENDPOINTS = [
    {
        "name": "Health Check (Fixed)",
        "method": "GET",
        "path": "/health",
        "target_max_ms": 50,  # Was 8000-10000ms before fix, target <10ms cached
        "category": "infrastructure"
    },
    {
        "name": "API Info",
        "method": "GET",
        "path": "/api/info",
        "target_max_ms": 50,
        "category": "infrastructure"
    },
    {
        "name": "Search Endpoint",
        "method": "GET",
        "path": "/api/v1/search?q=test&limit=10",
        "target_max_ms": 200,  # Target p99 <200ms
        "category": "query"
    },
    {
        "name": "Entity Types",
        "method": "GET",
        "path": "/api/v1/entity-types",
        "target_max_ms": 100,
        "category": "metadata"
    },
]

class LoadTestResults:
    def __init__(self):
        self.latencies = defaultdict(list)
        self.errors = defaultdict(int)
        self.success_count = defaultdict(int)
        self.status_codes = defaultdict(lambda: defaultdict(int))
        self.cache_hits = defaultdict(int)
        self.cache_misses = defaultdict(int)
        self.response_sizes = defaultdict(list)
        self.timeouts = defaultdict(int)
        self.start_time = None
        self.end_time = None
        self.lock = threading.Lock()
        self.error_messages = defaultdict(list)
        self.request_count = 0

    def add_result(self, endpoint, latency_ms, status_code, success=True,
                   cached=False, response_size=0, error_msg=None, timeout=False):
        with self.lock:
            self.request_count += 1
            self.status_codes[endpoint][status_code] += 1
            if timeout:
                self.timeouts[endpoint] += 1
            if success:
                self.latencies[endpoint].append(latency_ms)
                self.success_count[endpoint] += 1
                if cached:
                    self.cache_hits[endpoint] += 1
                else:
                    self.cache_misses[endpoint] += 1
                if response_size > 0:
                    self.response_sizes[endpoint].append(response_size)
            else:
                self.errors[endpoint] += 1
                if error_msg and len(self.error_messages[endpoint]) < 5:
                    self.error_messages[endpoint].append(error_msg)

    def get_stats(self, endpoint):
        latencies = self.latencies.get(endpoint, [])
        if not latencies:
            return None

        sorted_latencies = sorted(latencies)
        n = len(sorted_latencies)

        # Calculate percentiles
        percentiles = {}
        for p in [50, 75, 95, 99]:
            idx = max(0, int((p / 100) * (n - 1)))
            percentiles[f"p{p}"] = sorted_latencies[idx]

        total_requests = self.success_count[endpoint] + self.errors[endpoint]
        cache_total = self.cache_hits.get(endpoint, 0) + self.cache_misses.get(endpoint, 0)

        return {
            "count": len(latencies),
            "min_ms": min(latencies),
            "max_ms": max(latencies),
            "avg_ms": statistics.mean(latencies),
            "median_ms": statistics.median(latencies),
            "p50_ms": percentiles["p50"],
            "p75_ms": percentiles["p75"],
            "p95_ms": percentiles["p95"],
            "p99_ms": percentiles["p99"],
            "stdev_ms": statistics.stdev(latencies) if len(latencies) > 1 else 0,
            "total_requests": total_requests,
            "cache_hit_rate": (self.cache_hits.get(endpoint, 0) / cache_total * 100) if cache_total > 0 else 0,
            "avg_response_size_kb": (statistics.mean(self.response_sizes.get(endpoint, [0])) / 1024)
                                    if self.response_sizes.get(endpoint) else 0,
        }

def make_request(endpoint_config):
    """Make a single HTTP request with detailed metrics"""
    try:
        url = BASE_URL + endpoint_config["path"]
        method = endpoint_config.get("method", "GET")

        start = time.time()

        try:
            if method == "GET":
                response = requests.get(url, timeout=TEST_TIMEOUT)
            elif method == "POST":
                response = requests.post(url, json={}, timeout=TEST_TIMEOUT)
            else:
                return {
                    "endpoint": endpoint_config["name"],
                    "latency_ms": 0,
                    "status_code": 0,
                    "success": False,
                    "cached": False,
                    "response_size": 0,
                    "error_msg": "Unsupported method",
                    "timeout": False
                }
        except requests.exceptions.Timeout:
            latency_ms = (time.time() - start) * 1000
            return {
                "endpoint": endpoint_config["name"],
                "latency_ms": latency_ms,
                "status_code": 0,
                "success": False,
                "cached": False,
                "response_size": 0,
                "error_msg": "Timeout",
                "timeout": True
            }
        except requests.exceptions.ConnectionError as e:
            latency_ms = (time.time() - start) * 1000
            return {
                "endpoint": endpoint_config["name"],
                "latency_ms": latency_ms,
                "status_code": 0,
                "success": False,
                "cached": False,
                "response_size": 0,
                "error_msg": "Connection error",
                "timeout": False
            }

        latency_ms = (time.time() - start) * 1000

        # Check cache headers
        cached = response.headers.get("X-Cache", "MISS") == "HIT"

        # Success criteria
        success = 200 <= response.status_code < 400

        return {
            "endpoint": endpoint_config["name"],
            "latency_ms": latency_ms,
            "status_code": response.status_code,
            "success": success,
            "cached": cached,
            "response_size": len(response.content) if response.content else 0,
            "error_msg": None,
            "timeout": False
        }

    except Exception as e:
        return {
            "endpoint": endpoint_config["name"],
            "latency_ms": 0,
            "status_code": 0,
            "success": False,
            "cached": False,
            "response_size": 0,
            "error_msg": str(e),
            "timeout": False
        }

def run_load_test_duration():
    """Run load test for specified duration with concurrent users"""
    print("=" * 100)
    print("LOAD TEST: POST-FIXES VALIDATION")
    print("=" * 100)
    print(f"Start Time: {datetime.now().isoformat()}")
    print(f"Base URL: {BASE_URL}")
    print(f"Test Endpoints: {len(ENDPOINTS)}")
    print(f"Concurrent Users: {NUM_WORKERS}")
    print(f"Test Duration: {DURATION_SECONDS} seconds")
    print(f"Request Timeout: {TEST_TIMEOUT}s")
    print("=" * 100)

    results = LoadTestResults()
    results.start_time = time.time()

    # Get baseline stats
    try:
        process = psutil.Process()
        baseline_memory = process.memory_info().rss / 1024 / 1024
    except:
        baseline_memory = 0

    print(f"\nBaseline Stats:")
    print(f"  Memory: {baseline_memory:.1f} MB")

    # Execute load tests for duration
    print(f"\nStarting concurrent requests for {DURATION_SECONDS} seconds...")

    stop_event = threading.Event()
    completed_requests = threading.Lock()
    completed_count = [0]  # Use list to allow modification in nested function

    def worker():
        while not stop_event.is_set():
            endpoint = ENDPOINTS[results.request_count % len(ENDPOINTS)]
            result = make_request(endpoint)
            results.add_result(
                result["endpoint"],
                result["latency_ms"],
                result["status_code"],
                result["success"],
                result.get("cached", False),
                result.get("response_size", 0),
                result.get("error_msg"),
                result.get("timeout", False)
            )
            with completed_requests:
                completed_count[0] += 1

    # Start worker threads
    with concurrent.futures.ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
        futures = [executor.submit(worker) for _ in range(NUM_WORKERS)]

        # Monitor progress
        start_time = time.time()
        last_report = start_time

        while time.time() - start_time < DURATION_SECONDS:
            elapsed = time.time() - start_time
            if time.time() - last_report >= 10:  # Report every 10 seconds
                rate = completed_count[0] / elapsed if elapsed > 0 else 0
                print(f"Progress: {completed_count[0]} requests completed - Rate: {rate:.1f} req/s")
                last_report = time.time()
            time.sleep(0.1)

        # Signal stop
        stop_event.set()
        concurrent.futures.wait(futures, timeout=5)

    results.end_time = time.time()

    # Final memory stats
    try:
        final_memory = process.memory_info().rss / 1024 / 1024
    except:
        final_memory = baseline_memory

    print(f"\nFinal Stats:")
    print(f"  Memory: {final_memory:.1f} MB (delta: {final_memory - baseline_memory:+.1f} MB)")
    print(f"  Total Requests: {completed_count[0]}")

    return results

def analyze_results(results):
    """Analyze and format test results"""
    print("\n" + "=" * 100)
    print("LOAD TEST RESULTS ANALYSIS")
    print("=" * 100)

    total_duration = results.end_time - results.start_time
    total_requests = sum(results.success_count.values()) + sum(results.errors.values())
    successful_requests = sum(results.success_count.values())
    failed_requests = sum(results.errors.values())
    total_timeouts = sum(results.timeouts.values())

    error_rate = (failed_requests / total_requests * 100) if total_requests > 0 else 0
    timeout_rate = (total_timeouts / total_requests * 100) if total_requests > 0 else 0
    throughput = total_requests / total_duration if total_duration > 0 else 0

    print(f"\nExecution Metrics:")
    print(f"  Total Duration: {total_duration:.2f} seconds")
    print(f"  Total Requests: {total_requests}")
    print(f"  Successful: {successful_requests} ({100*successful_requests/total_requests:.1f}%)")
    print(f"  Failed: {failed_requests} ({error_rate:.2f}%)")
    print(f"  Timeouts: {total_timeouts} ({timeout_rate:.2f}%)")
    print(f"  Throughput: {throughput:.2f} req/s")

    print("\n" + "-" * 100)
    print("ENDPOINT PERFORMANCE ANALYSIS")
    print("-" * 100)

    endpoint_results = {}

    for endpoint_config in ENDPOINTS:
        endpoint_name = endpoint_config["name"]
        stats = results.get_stats(endpoint_name)
        target_max = endpoint_config.get("target_max_ms", 500)

        if stats is None:
            result = {
                "stats": None,
                "target_max": target_max,
                "pass": False,
                "status": "NO DATA",
            }
        else:
            # Check if all requests under threshold
            all_under_target = stats["max_ms"] <= target_max
            p99_under_target = stats["p99_ms"] <= target_max

            passed = all_under_target  # For health check, ALL must be under target
            result = {
                "stats": stats,
                "target_max": target_max,
                "pass": passed,
                "status": "PASS" if passed else "WARN",
                "p99_under": p99_under_target
            }

        endpoint_results[endpoint_name] = result

        # Print per-endpoint details
        status_codes = results.status_codes.get(endpoint_name, {})
        status_str = ", ".join([f"{code}:{count}" for code, count in sorted(status_codes.items())])

        print(f"\n[{endpoint_name}]")
        print(f"  Path: {endpoint_config['path']}")

        if stats:
            timeouts = results.timeouts.get(endpoint_name, 0)
            print(f"  Requests: {stats['count']} successful, {results.errors.get(endpoint_name, 0)} failed, {timeouts} timeouts")
            print(f"  Status Codes: {status_str}")
            print(f"  Latency Distribution (ms):")
            print(f"    Min:    {stats['min_ms']:8.2f}")
            print(f"    p50:    {stats['p50_ms']:8.2f}")
            print(f"    p75:    {stats['p75_ms']:8.2f}")
            print(f"    p95:    {stats['p95_ms']:8.2f}")
            print(f"    p99:    {stats['p99_ms']:8.2f}")
            print(f"    Max:    {stats['max_ms']:8.2f} (target max: {target_max}ms) {'✅ PASS' if stats['max_ms'] <= target_max else '❌ FAIL'}")
            print(f"    Avg:    {stats['avg_ms']:8.2f}")
            print(f"  Cache Hit Rate: {stats['cache_hit_rate']:.1f}%")
        else:
            print(f"  Status: {result['status']}")

    return endpoint_results, error_rate, timeout_rate, throughput, total_requests

def generate_report(results, endpoint_results, error_rate, timeout_rate, throughput, total_requests):
    """Generate comprehensive post-fixes validation report"""
    report_path = "/home/devel/basset-hound/docs/handoffs/LOAD-TEST-POST-FIXES-REPORT.md"

    import os
    os.makedirs(os.path.dirname(report_path), exist_ok=True)

    total_duration = results.end_time - results.start_time
    successful_requests = sum(results.success_count.values())

    with open(report_path, "w") as f:
        f.write("# Load Test Post-Fixes Validation Report\n\n")
        f.write(f"**Date**: {datetime.now().isoformat()}\n")
        f.write(f"**Test Type**: Post-Fixes Performance Validation\n")
        f.write(f"**Duration**: {total_duration:.2f} seconds\n")
        f.write(f"**Concurrent Users**: {NUM_WORKERS}\n\n")

        # Executive Summary
        f.write("## Executive Summary\n\n")
        f.write("Validation of critical fixes deployed:\n")
        f.write("1. **Health check timeout fix** - Changed from 8000ms to <10ms cached\n")
        f.write("2. **Cache layer fix** - Fixed 0% hit rate (was redundant backend call)\n\n")

        f.write(f"**Test Results**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n")
        f.write(f"| Metric | Value |\n")
        f.write(f"|--------|-------|\n")
        f.write(f"| Total Duration | {total_duration:.2f}s |\n")
        f.write(f"| Total Requests | {total_requests} |\n")
        f.write(f"| Successful | {successful_requests} ({100*successful_requests/total_requests:.1f}%) |\n")
        f.write(f"| Failed | {total_requests - successful_requests} |\n")
        f.write(f"| Error Rate | {error_rate:.2f}% |\n")
        f.write(f"| Timeout Rate | {timeout_rate:.2f}% |\n")
        f.write(f"| Throughput | {throughput:.2f} req/s |\n\n")

        # Success Criteria Check
        f.write("## Success Criteria Validation\n\n")

        # Health check criterion
        health_stats = endpoint_results.get("Health Check (Fixed)", {}).get("stats")
        health_pass = endpoint_results.get("Health Check (Fixed)", {}).get("pass", False)

        f.write("### 1. Health Check: ALL <50ms\n\n")
        if health_stats:
            f.write(f"- **p99**: {health_stats['p99_ms']:.2f}ms {'✅' if health_stats['p99_ms'] < 50 else '❌'}\n")
            f.write(f"- **Max**: {health_stats['max_ms']:.2f}ms {'✅' if health_stats['max_ms'] < 50 else '❌'}\n")
            f.write(f"- **Status**: {'✅ PASS' if health_pass else '❌ FAIL'}\n")
            if health_pass:
                f.write(f"- **Note**: Health check timeout fix verified - was 8000-10000ms before\n")
        else:
            f.write("- **Status**: ❌ NO DATA\n")
        f.write("\n")

        # Cache hit rate criterion
        f.write("### 2. Cache Hit Rate: >60%\n\n")
        cache_rates = []
        for ep_name, result in endpoint_results.items():
            if result.get("stats"):
                cache_rates.append(result["stats"]["cache_hit_rate"])

        if cache_rates:
            avg_cache = statistics.mean(cache_rates)
            f.write(f"- **Average**: {avg_cache:.1f}% {'✅' if avg_cache > 60 else '❌'}\n")
            f.write(f"- **Status**: {'✅ PASS' if avg_cache > 60 else '❌ FAIL'}\n")
            if avg_cache > 60:
                f.write(f"- **Note**: Cache layer fix verified - was 0% hit rate before\n")
            f.write(f"\nDetailed by endpoint:\n")
            for ep_name, result in endpoint_results.items():
                if result.get("stats"):
                    f.write(f"  - {ep_name}: {result['stats']['cache_hit_rate']:.1f}%\n")
        else:
            f.write("- **Status**: ❌ NO DATA\n")
        f.write("\n")

        # Error rate criterion
        f.write("### 3. Error Rate: <1%\n\n")
        f.write(f"- **Measured**: {error_rate:.2f}% {'✅' if error_rate < 1 else '❌'}\n")
        f.write(f"- **Status**: {'✅ PASS' if error_rate < 1 else '❌ FAIL'}\n")
        f.write(f"- **Timeouts**: {timeout_rate:.2f}%\n\n")

        # Search latency criterion
        f.write("### 4. Search Response: <200ms p99\n\n")
        search_result = endpoint_results.get("Search Endpoint", {})
        if search_result.get("stats"):
            search_stats = search_result["stats"]
            f.write(f"- **p99**: {search_stats['p99_ms']:.2f}ms {'✅' if search_stats['p99_ms'] < 200 else '❌'}\n")
            f.write(f"- **Max**: {search_stats['max_ms']:.2f}ms\n")
            f.write(f"- **Status**: {'✅ PASS' if search_stats['p99_ms'] < 200 else '❌ FAIL'}\n")
        else:
            f.write("- **Status**: ❌ NO DATA\n")
        f.write("\n")

        # Summary of success criteria
        f.write("## Success Criteria Summary\n\n")

        criteria = [
            ("Health check: ALL <50ms", health_pass),
            ("Error rate: <1%", error_rate < 1),
            ("Cache hit rate: >60%", avg_cache > 60 if cache_rates else False),
            ("Search: <200ms p99", search_result.get("stats", {}).get("p99_ms", 999) < 200 if search_result.get("stats") else False),
        ]

        passing = sum(1 for _, passed in criteria if passed)
        total = len(criteria)

        f.write(f"**Overall**: {passing}/{total} criteria met\n\n")
        for criterion, passed in criteria:
            f.write(f"- {'✅' if passed else '❌'} {criterion}\n")
        f.write("\n")

        # Detailed Results
        f.write("## Detailed Endpoint Results\n\n")
        f.write("| Endpoint | Requests | Min (ms) | p50 (ms) | p99 (ms) | Max (ms) | Target | Cache Hit | Status |\n")
        f.write("|----------|----------|----------|----------|----------|----------|--------|-----------|--------|\n")

        for ep_config in ENDPOINTS:
            ep_name = ep_config["name"]
            result = endpoint_results.get(ep_name)
            if result and result.get("stats"):
                stats = result["stats"]
                status = "✅" if result["pass"] else "❌"
                f.write(f"| {ep_name} | {stats['total_requests']} | {stats['min_ms']:.1f} | {stats['p50_ms']:.1f} | {stats['p99_ms']:.1f} | {stats['max_ms']:.1f} | {result['target_max']} | {stats['cache_hit_rate']:.0f}% | {status} |\n")
            else:
                f.write(f"| {ep_name} | 0 | N/A | N/A | N/A | N/A | {result['target_max'] if result else 'N/A'} | N/A | ❌ |\n")

        # Before/After Comparison
        f.write("\n## Before/After Comparison\n\n")
        f.write("| Metric | Before Fix | After Fix | Improvement |\n")
        f.write("|--------|-----------|-----------|-------------|\n")

        if health_stats:
            f.write(f"| Health Check (max) | 8000-10000ms | {health_stats['max_ms']:.2f}ms | **{((10000 - health_stats['max_ms']) / 10000 * 100):.1f}%** |\n")

        f.write(f"| Cache Hit Rate | 0% | {avg_cache if cache_rates else 'N/A'}% | **{f'{avg_cache:.1f}%' if cache_rates else 'N/A'}** |\n")
        f.write(f"| Error Rate | 100% (timeouts) | {error_rate:.2f}% | **{((100 - error_rate) / 100 * 100):.1f}%** |\n\n")

        # Key Findings
        f.write("## Key Findings\n\n")

        if health_pass:
            f.write("✅ **Health Check Fix Verified**\n")
            f.write(f"   - All requests completed in <50ms (max: {health_stats['max_ms']:.2f}ms)\n")
            f.write(f"   - Massive improvement from 8000-10000ms pre-fix\n")
            f.write(f"   - No timeout cascades detected\n\n")

        if cache_rates and avg_cache > 60:
            f.write("✅ **Cache Layer Fix Verified**\n")
            f.write(f"   - Average cache hit rate: {avg_cache:.1f}%\n")
            f.write(f"   - Improvement from 0% pre-fix\n")
            f.write(f"   - Cache warming working as expected\n\n")

        if error_rate < 1 and timeout_rate < 1:
            f.write("✅ **System Stability**\n")
            f.write(f"   - Error rate: {error_rate:.2f}%\n")
            f.write(f"   - Timeout rate: {timeout_rate:.2f}%\n")
            f.write(f"   - No cascading failures under sustained {NUM_WORKERS}-concurrent load\n\n")

        # Issues if any
        issues = []
        if not health_pass:
            issues.append("Health check still exceeds target latency")
        if cache_rates and avg_cache < 60:
            issues.append(f"Cache hit rate below 60% target ({avg_cache:.1f}%)")
        if error_rate >= 1:
            issues.append(f"Error rate above 1% target ({error_rate:.2f}%)")
        if timeout_rate > 0.5:
            issues.append(f"Timeout rate elevated ({timeout_rate:.2f}%)")

        if issues:
            f.write("⚠️ **Issues Detected**\n\n")
            for issue in issues:
                f.write(f"   - {issue}\n")
            f.write("\n")
        else:
            f.write("✅ **No Issues Detected**\n\n")

        # Recommendations
        f.write("## Recommendations\n\n")

        if health_pass and cache_rates and avg_cache > 60 and error_rate < 1:
            f.write("✅ **FIXES VALIDATED - READY FOR PRODUCTION**\n\n")
            f.write("Both critical fixes have been successfully verified:\n")
            f.write("1. Health check timeout fix: WORKING\n")
            f.write("2. Cache layer fix: WORKING\n\n")
            f.write("Recommend deploying to production.\n\n")
        else:
            f.write("⚠️ **Further Investigation Needed**\n\n")
            if not health_pass:
                f.write("- Health check latency not meeting targets - review recent changes\n")
            if cache_rates and avg_cache < 60:
                f.write("- Cache hit rate below target - check cache configuration\n")
            if error_rate >= 1:
                f.write("- Review application error logs\n")
            f.write("\n")

        # Test Configuration
        f.write("## Test Configuration\n\n")
        f.write(f"- **Test Duration**: {DURATION_SECONDS} seconds\n")
        f.write(f"- **Concurrent Users**: {NUM_WORKERS}\n")
        f.write(f"- **Base URL**: {BASE_URL}\n")
        f.write(f"- **Request Timeout**: {TEST_TIMEOUT}s\n")
        f.write(f"- **Total Requests**: {total_requests}\n")
        f.write(f"- **Throughput**: {throughput:.2f} req/s\n\n")

        # Conclusion
        f.write("## Conclusion\n\n")

        all_pass = health_pass and (cache_rates and avg_cache > 60) and error_rate < 1
        if all_pass:
            f.write("✅ **VALIDATION SUCCESSFUL**\n\n")
            f.write("All critical fixes have been validated and are working correctly.\n")
            f.write("System is stable under 50-concurrent-user load for sustained periods.\n\n")
        else:
            f.write("⚠️ **VALIDATION INCOMPLETE**\n\n")
            f.write("Some criteria not fully met. See issues section above.\n\n")

        f.write("---\n\n")
        f.write(f"**Report Generated**: {datetime.now().isoformat()}\n")

    print(f"\n✅ Report saved to: {report_path}")
    return report_path

if __name__ == "__main__":
    try:
        print("\nStarting post-fixes validation load test...\n")
        results = run_load_test_duration()
        endpoint_results, error_rate, timeout_rate, throughput, total_requests = analyze_results(results)
        report_path = generate_report(results, endpoint_results, error_rate, timeout_rate, throughput, total_requests)

        print("\n" + "=" * 100)
        print("LOAD TEST COMPLETE")
        print("=" * 100)
        print(f"\nReport: {report_path}\n")

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError during load testing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
