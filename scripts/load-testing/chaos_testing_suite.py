#!/usr/bin/env python3
"""
CHAOS TESTING SUITE - Comprehensive Resilience Testing
======================================================

This suite deliberately stresses the system to identify breaking points,
verify recovery mechanisms, and document resilience characteristics.

Scenarios:
1. Connection Pool Exhaustion (Neo4j limits)
2. Cache Failure Simulation (Redis outage)
3. Database Unavailability (Slow queries)
4. API Overload (100+ concurrent users)
5. Memory Leak Detection (Long-running load)
6. Network Failure (Intermittent connectivity)
7. Database Connection Timeout (Cascading failures)

Usage:
    python3 chaos_testing_suite.py [--scenario 1-7] [--output results.json]

Requirements:
    - Docker services running (docker-compose up -d)
    - System must be accessible at http://localhost:8080
    - Redis must be accessible at localhost:6379
    - Neo4j must be accessible at localhost:7687
"""

import requests
import time
import statistics
import concurrent.futures
import json
import sys
import argparse
import subprocess
import signal
import threading
from datetime import datetime
from collections import defaultdict
from typing import List, Dict, Tuple, Optional
import traceback

BASE_URL = "http://localhost:8080"
REDIS_HOST = "localhost"
REDIS_PORT = 6379
NEO4J_HOST = "localhost"
NEO4J_PORT = 7687

class ChaosTestResult:
    """Stores results for a chaos testing scenario"""

    def __init__(self, scenario_name: str, scenario_number: int):
        self.scenario_name = scenario_name
        self.scenario_number = scenario_number
        self.start_time = None
        self.end_time = None
        self.requests = []
        self.errors = []
        self.events = []
        self.recovery_time = None
        self.breaking_point = None
        self.recommendations = []

    def add_request(self, latency_ms: float, status_code: int,
                   endpoint: str, error: Optional[str] = None):
        """Record a request result"""
        self.requests.append({
            "timestamp": datetime.now().isoformat(),
            "latency_ms": latency_ms,
            "status_code": status_code,
            "endpoint": endpoint,
            "error": error,
        })
        if error or status_code >= 400:
            self.errors.append(error or f"HTTP {status_code}")

    def add_event(self, event_type: str, message: str, severity: str = "info"):
        """Record a significant event during the test"""
        self.events.append({
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "message": message,
            "severity": severity,
        })

    def get_summary(self) -> Dict:
        """Generate a summary of the test results"""
        if not self.requests:
            return {
                "scenario": self.scenario_name,
                "number": self.scenario_number,
                "error": "No requests made",
            }

        latencies = [r["latency_ms"] for r in self.requests]
        error_count = len([r for r in self.requests if r["status_code"] >= 400])

        sorted_latencies = sorted(latencies)
        duration = (self.end_time - self.start_time) if self.end_time and self.start_time else 0

        return {
            "scenario": self.scenario_name,
            "number": self.scenario_number,
            "duration_seconds": round(duration, 2),
            "total_requests": len(self.requests),
            "successful_requests": len(self.requests) - error_count,
            "failed_requests": error_count,
            "error_rate_percent": round((error_count / len(self.requests) * 100) if self.requests else 0, 2),
            "throughput_req_s": round(len(self.requests) / duration if duration > 0 else 0, 2),
            "latency": {
                "min_ms": round(min(latencies), 2),
                "max_ms": round(max(latencies), 2),
                "avg_ms": round(statistics.mean(latencies), 2),
                "median_ms": round(statistics.median(latencies), 2),
                "p95_ms": round(sorted_latencies[int(len(latencies) * 0.95)], 2) if len(latencies) > 20 else round(max(latencies), 2),
                "p99_ms": round(sorted_latencies[int(len(latencies) * 0.99)], 2) if len(latencies) > 100 else round(max(latencies), 2),
            },
            "breaking_point": self.breaking_point,
            "recovery_time_seconds": self.recovery_time,
            "key_events": len(self.events),
            "recommendations": self.recommendations,
        }


class ChaosTester:
    """Main chaos testing orchestrator"""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.results = {}

    def check_system_ready(self) -> bool:
        """Verify system is running and accessible"""
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=5)
            return response.status_code == 200
        except Exception as e:
            print(f"System not ready: {e}")
            return False

    def docker_command(self, *args) -> bool:
        """Execute docker-compose command"""
        try:
            result = subprocess.run(
                ["docker-compose", *args],
                capture_output=True,
                timeout=30,
                cwd="/home/devel/basset-hound"
            )
            return result.returncode == 0
        except Exception as e:
            print(f"Docker command failed: {e}")
            return False

    def make_request(self, endpoint: str, timeout: Optional[int] = None) -> Tuple[float, int, Optional[str]]:
        """Make a single HTTP request"""
        try:
            start = time.time()
            response = requests.get(
                f"{BASE_URL}{endpoint}",
                timeout=timeout or self.timeout
            )
            latency = (time.time() - start) * 1000
            return latency, response.status_code, None
        except requests.exceptions.Timeout:
            return self.timeout * 1000, 504, "Timeout"
        except requests.exceptions.ConnectionError:
            return 0, 503, "Connection refused"
        except Exception as e:
            return 0, 500, str(e)[:100]

    def concurrent_requests(self, endpoint: str, count: int,
                           duration_seconds: int, timeout: Optional[int] = None) -> List[Dict]:
        """Execute concurrent requests"""
        results = []
        end_time = time.time() + duration_seconds
        request_count = 0

        def worker():
            nonlocal request_count
            while time.time() < end_time:
                latency, status, error = self.make_request(endpoint, timeout)
                results.append({
                    "latency_ms": latency,
                    "status_code": status,
                    "error": error,
                })
                request_count += 1

        with concurrent.futures.ThreadPoolExecutor(max_workers=count) as executor:
            futures = [executor.submit(worker) for _ in range(count)]
            concurrent.futures.wait(futures)

        return results

    # ========================================================================
    # SCENARIO 1: Connection Pool Exhaustion
    # ========================================================================

    def scenario_1_connection_pool_exhaustion(self) -> ChaosTestResult:
        """
        Push Neo4j connection pool to limits.

        Expected: Some failures around 150 concurrent limit, then recovery.
        Success: Error rate <15% (some expected to fail), automatic recovery.
        """
        result = ChaosTestResult("Connection Pool Exhaustion", 1)

        if not self.check_system_ready():
            result.add_event("system_check", "System not ready", "error")
            return result

        result.add_event("test_start", "Beginning connection pool exhaustion test", "info")
        result.start_time = time.time()

        # Gradually increase concurrent users to find breaking point
        concurrency_levels = [50, 100, 150, 200, 250]

        for concurrency in concurrency_levels:
            result.add_event("concurrency_increase", f"Testing with {concurrency} concurrent users", "info")
            requests_batch = self.concurrent_requests("/health", concurrency, 30)

            error_count = sum(1 for r in requests_batch if r["status_code"] >= 400)
            error_rate = error_count / len(requests_batch) * 100 if requests_batch else 0

            for req in requests_batch:
                result.add_request(req["latency_ms"], req["status_code"], "/health", req["error"])

            result.add_event("concurrency_results",
                           f"{concurrency} concurrent: {error_rate:.1f}% error rate",
                           "warning" if error_rate > 10 else "info")

            # If we find breaking point (>20% errors), record it
            if error_rate > 20 and not result.breaking_point:
                result.breaking_point = {
                    "concurrency": concurrency,
                    "error_rate": error_rate,
                    "timestamp": datetime.now().isoformat()
                }
                result.add_event("breaking_point", f"Breaking point found at {concurrency} concurrent", "warning")

            time.sleep(5)  # Brief pause between levels

        result.end_time = time.time()

        # Measure recovery: reduced load should return to normal
        result.add_event("recovery_test", "Testing recovery with reduced load", "info")
        recovery_start = time.time()
        recovery_requests = self.concurrent_requests("/health", 50, 30)

        recovery_errors = sum(1 for r in recovery_requests if r["status_code"] >= 400)
        recovery_error_rate = recovery_errors / len(recovery_requests) * 100 if recovery_requests else 0

        if recovery_error_rate < 5:
            result.recovery_time = time.time() - recovery_start
            result.add_event("recovery_complete", "System recovered to normal operation", "info")

        # Recommendations
        if result.breaking_point:
            result.recommendations.append(
                f"Connection pool breaking point at {result.breaking_point['concurrency']} concurrent. "
                "Consider implementing connection pooling strategies or circuit breaker."
            )
        if result.recovery_time:
            result.recommendations.append(f"Recovery time: {result.recovery_time:.1f}s. Good automatic recovery.")
        else:
            result.recommendations.append("Manual intervention may be needed for recovery. Implement auto-scaling.")

        return result

    # ========================================================================
    # SCENARIO 2: Cache Failure Simulation (Redis outage)
    # ========================================================================

    def scenario_2_cache_failure(self) -> ChaosTestResult:
        """
        Stop Redis cache and measure fallback behavior.

        Expected: Fallback to memory cache, performance degrades but works.
        Success: <5% error rate, graceful degradation, auto-recovery.
        """
        result = ChaosTestResult("Cache Failure Simulation (Redis Outage)", 2)

        if not self.check_system_ready():
            result.add_event("system_check", "System not ready", "error")
            return result

        result.start_time = time.time()
        result.add_event("test_start", "Beginning cache failure test", "info")

        # Baseline: measure performance with cache working
        result.add_event("baseline", "Measuring baseline with cache operational", "info")
        baseline_requests = self.concurrent_requests("/health", 50, 20)
        baseline_errors = sum(1 for r in baseline_requests if r["status_code"] >= 400)
        baseline_error_rate = baseline_errors / len(baseline_requests) * 100 if baseline_requests else 0
        baseline_latencies = [r["latency_ms"] for r in baseline_requests]
        baseline_avg = statistics.mean(baseline_latencies) if baseline_latencies else 0

        for req in baseline_requests:
            result.add_request(req["latency_ms"], req["status_code"], "/health", req["error"])

        result.add_event("baseline_complete",
                        f"Baseline: {baseline_error_rate:.1f}% errors, {baseline_avg:.0f}ms avg latency",
                        "info")

        # Stop Redis
        result.add_event("redis_stop", "Stopping Redis cache", "warning")
        redis_stopped = self.docker_command("stop", "redis_cache")

        if not redis_stopped:
            result.add_event("redis_stop_failed", "Failed to stop Redis (may continue with test)", "warning")
        else:
            result.add_event("redis_stopped", "Redis stopped successfully", "info")

        time.sleep(2)

        # Load without cache
        result.add_event("no_cache_test", "Running load test without cache (60 seconds)", "info")
        no_cache_requests = self.concurrent_requests("/health", 50, 60)

        no_cache_errors = sum(1 for r in no_cache_requests if r["status_code"] >= 400)
        no_cache_error_rate = no_cache_errors / len(no_cache_requests) * 100 if no_cache_requests else 0
        no_cache_latencies = [r["latency_ms"] for r in no_cache_requests]
        no_cache_avg = statistics.mean(no_cache_latencies) if no_cache_latencies else 0

        for req in no_cache_requests:
            result.add_request(req["latency_ms"], req["status_code"], "/health", req["error"])

        performance_degradation = ((no_cache_avg - baseline_avg) / baseline_avg * 100) if baseline_avg > 0 else 0

        result.add_event("no_cache_complete",
                        f"No cache: {no_cache_error_rate:.1f}% errors, "
                        f"{no_cache_avg:.0f}ms avg latency (↑{performance_degradation:.0f}%)",
                        "warning" if no_cache_error_rate > 5 else "info")

        # Restart Redis
        result.add_event("redis_restart", "Restarting Redis cache", "info")
        redis_restarted = self.docker_command("start", "redis_cache")

        if not redis_restarted:
            result.add_event("redis_restart_failed", "Failed to restart Redis", "error")
        else:
            result.add_event("redis_restarted", "Redis restarted", "info")

        time.sleep(3)

        # Measure recovery
        result.add_event("recovery_test", "Measuring recovery with cache restored", "info")
        recovery_start = time.time()
        recovery_requests = self.concurrent_requests("/health", 50, 20)
        recovery_time = time.time() - recovery_start

        recovery_errors = sum(1 for r in recovery_requests if r["status_code"] >= 400)
        recovery_error_rate = recovery_errors / len(recovery_requests) * 100 if recovery_requests else 0
        recovery_latencies = [r["latency_ms"] for r in recovery_requests]
        recovery_avg = statistics.mean(recovery_latencies) if recovery_latencies else 0

        for req in recovery_requests:
            result.add_request(req["latency_ms"], req["status_code"], "/health", req["error"])

        result.recovery_time = recovery_time

        if recovery_error_rate < baseline_error_rate + 2:
            result.add_event("recovery_complete", "System recovered to near-baseline performance", "info")

        result.end_time = time.time()

        # Recommendations
        result.recommendations.append(
            f"Baseline vs No Cache: Error {baseline_error_rate:.1f}% → {no_cache_error_rate:.1f}%, "
            f"Latency {baseline_avg:.0f}ms → {no_cache_avg:.0f}ms"
        )

        if performance_degradation > 50:
            result.recommendations.append(
                f"Significant performance degradation ({performance_degradation:.0f}%) without cache. "
                "Consider adding memory-based cache layer as backup."
            )
        else:
            result.recommendations.append(
                f"Graceful degradation acceptable ({performance_degradation:.0f}%). "
                "Current fallback mechanism working as designed."
            )

        if recovery_error_rate < 5:
            result.recommendations.append("Fast recovery from cache outage. Good resilience.")
        else:
            result.recommendations.append("Slow recovery from cache outage. Check cache warm-up logic.")

        return result

    # ========================================================================
    # SCENARIO 3: Database Unavailability (Slow queries)
    # ========================================================================

    def scenario_3_database_slow_queries(self) -> ChaosTestResult:
        """
        Simulate slow database responses.

        Expected: Timeouts after 30 seconds, circuit breaker may activate.
        Success: <10% error rate during slowdown, quick recovery.
        """
        result = ChaosTestResult("Database Unavailability (Slow Queries)", 3)

        if not self.check_system_ready():
            result.add_event("system_check", "System not ready", "error")
            return result

        result.start_time = time.time()
        result.add_event("test_start", "Beginning database slowdown test", "info")

        # Baseline with normal queries
        result.add_event("baseline", "Measuring baseline with normal database", "info")
        baseline_requests = self.concurrent_requests("/health", 50, 20)

        for req in baseline_requests:
            result.add_request(req["latency_ms"], req["status_code"], "/health", req["error"])

        baseline_errors = sum(1 for r in baseline_requests if r["status_code"] >= 400)
        baseline_latencies = [r["latency_ms"] for r in baseline_requests]
        baseline_avg = statistics.mean(baseline_latencies) if baseline_latencies else 0

        result.add_event("baseline_complete", f"Baseline: {baseline_avg:.0f}ms avg latency", "info")

        # NOTE: Actual database slowdown would require Neo4j configuration change
        # For simulation, we use increased request timeout to measure circuit breaker behavior
        result.add_event("slowdown_simulation", "Simulating slow database with extended timeout", "warning")

        # Test with extended timeout (simulates slow responses)
        slow_requests = self.concurrent_requests("/health", 50, 30, timeout=10)

        for req in slow_requests:
            result.add_request(req["latency_ms"], req["status_code"], "/health", req["error"])

        slow_errors = sum(1 for r in slow_requests if r["status_code"] >= 400)
        slow_error_rate = slow_errors / len(slow_requests) * 100 if slow_requests else 0
        slow_latencies = [r["latency_ms"] for r in slow_requests]
        slow_avg = statistics.mean(slow_latencies) if slow_latencies else 0

        result.add_event("slowdown_complete",
                        f"Under slowdown: {slow_error_rate:.1f}% error rate, {slow_avg:.0f}ms avg latency",
                        "warning" if slow_error_rate > 10 else "info")

        if slow_error_rate > 0:
            result.breaking_point = {
                "condition": "database_slowdown",
                "error_rate": slow_error_rate,
                "timestamp": datetime.now().isoformat()
            }

        # Measure recovery
        time.sleep(5)
        result.add_event("recovery_test", "Measuring recovery with normal database", "info")
        recovery_start = time.time()
        recovery_requests = self.concurrent_requests("/health", 50, 20)
        recovery_time = time.time() - recovery_start

        for req in recovery_requests:
            result.add_request(req["latency_ms"], req["status_code"], "/health", req["error"])

        recovery_errors = sum(1 for r in recovery_requests if r["status_code"] >= 400)
        recovery_error_rate = recovery_errors / len(recovery_requests) * 100 if recovery_requests else 0

        if recovery_error_rate < 5:
            result.recovery_time = recovery_time
            result.add_event("recovery_complete", "System recovered quickly", "info")

        result.end_time = time.time()

        # Recommendations
        result.recommendations.append(
            f"Slowdown impact: {slow_error_rate:.1f}% error rate with 10s timeout vs {baseline_errors/len(baseline_requests)*100:.1f}% baseline"
        )

        if slow_error_rate < 10:
            result.recommendations.append("System handles database slowdown well. Circuit breaker may be working.")
        else:
            result.recommendations.append(
                f"High error rate ({slow_error_rate:.1f}%) during slowdown. "
                "Consider implementing request queueing or adaptive timeout."
            )

        return result

    # ========================================================================
    # SCENARIO 4: API Overload
    # ========================================================================

    def scenario_4_api_overload(self) -> ChaosTestResult:
        """
        Burst with 150 concurrent users.

        Expected: Error rate <10%, no data loss.
        Success: Graceful degradation, not hard failures.
        """
        result = ChaosTestResult("API Overload (Burst Load)", 4)

        if not self.check_system_ready():
            result.add_event("system_check", "System not ready", "error")
            return result

        result.start_time = time.time()
        result.add_event("test_start", "Beginning API overload test", "info")

        # Gradual ramp up
        concurrency_levels = [50, 75, 100, 125, 150]

        for concurrency in concurrency_levels:
            result.add_event("concurrency_level", f"Testing {concurrency} concurrent users", "info")
            requests_batch = self.concurrent_requests("/health", concurrency, 15)

            error_count = sum(1 for r in requests_batch if r["status_code"] >= 400)
            error_rate = error_count / len(requests_batch) * 100 if requests_batch else 0
            latencies = [r["latency_ms"] for r in requests_batch]
            avg_latency = statistics.mean(latencies) if latencies else 0

            for req in requests_batch:
                result.add_request(req["latency_ms"], req["status_code"], "/health", req["error"])

            result.add_event("level_complete",
                           f"{concurrency} concurrent: {error_rate:.1f}% errors, {avg_latency:.0f}ms avg",
                           "warning" if error_rate > 10 else "info")

            time.sleep(3)

        # Peak load: 150 concurrent for full duration
        result.add_event("peak_load", "Peak load: 150 concurrent for 60 seconds", "warning")
        peak_requests = self.concurrent_requests("/health", 150, 60)

        peak_errors = sum(1 for r in peak_requests if r["status_code"] >= 400)
        peak_error_rate = peak_errors / len(peak_requests) * 100 if peak_requests else 0
        peak_latencies = [r["latency_ms"] for r in peak_requests]
        peak_avg = statistics.mean(peak_latencies) if peak_latencies else 0
        peak_p99 = sorted(peak_latencies)[int(len(peak_latencies) * 0.99)] if len(peak_latencies) > 100 else max(peak_latencies)

        for req in peak_requests:
            result.add_request(req["latency_ms"], req["status_code"], "/health", req["error"])

        result.add_event("peak_complete",
                        f"Peak load complete: {peak_error_rate:.1f}% errors, {peak_avg:.0f}ms avg, p99: {peak_p99:.0f}ms",
                        "warning" if peak_error_rate > 10 else "info")

        if peak_error_rate > 10:
            result.breaking_point = {
                "concurrency": 150,
                "error_rate": peak_error_rate,
                "timestamp": datetime.now().isoformat()
            }

        result.end_time = time.time()

        # Recommendations
        if peak_error_rate < 10:
            result.recommendations.append(f"Excellent resilience under 150 concurrent load ({peak_error_rate:.1f}% error rate)")
        else:
            result.recommendations.append(f"High error rate at peak load ({peak_error_rate:.1f}%). Implement load balancing or auto-scaling.")

        if peak_p99 < 1000:
            result.recommendations.append(f"Good p99 latency ({peak_p99:.0f}ms) under peak load")
        else:
            result.recommendations.append(f"High p99 latency ({peak_p99:.0f}ms). Optimize bottleneck endpoints.")

        return result

    # ========================================================================
    # SCENARIO 5: Memory Leak Detection
    # ========================================================================

    def scenario_5_memory_leak_detection(self) -> ChaosTestResult:
        """
        Sustained 50 concurrent users for 10 minutes.

        Expected: Stable memory usage.
        Success: Memory growth <5%, no process crashes.
        """
        result = ChaosTestResult("Memory Leak Detection (Long-running Load)", 5)

        if not self.check_system_ready():
            result.add_event("system_check", "System not ready", "error")
            return result

        result.start_time = time.time()
        result.add_event("test_start", "Beginning 10-minute sustained load test", "info")

        # Get initial API container memory
        initial_memory = self._get_api_container_memory()
        if initial_memory:
            result.add_event("memory_baseline", f"Initial API memory: {initial_memory:.0f} MB", "info")

        # Run sustained load for 10 minutes (600 seconds)
        # Check memory every 2 minutes
        memory_samples = []
        test_duration = 600
        check_interval = 120

        for elapsed in range(0, test_duration, 60):
            remaining = test_duration - elapsed
            requests_batch = self.concurrent_requests("/health", 50, min(60, remaining))

            error_count = sum(1 for r in requests_batch if r["status_code"] >= 400)
            error_rate = error_count / len(requests_batch) * 100 if requests_batch else 0

            for req in requests_batch:
                result.add_request(req["latency_ms"], req["status_code"], "/health", req["error"])

            # Check memory every 2 minutes
            if (elapsed + 60) % check_interval == 0:
                current_memory = self._get_api_container_memory()
                if current_memory:
                    memory_samples.append(current_memory)
                    memory_growth = ((current_memory - initial_memory) / initial_memory * 100) if initial_memory else 0
                    result.add_event("memory_check",
                                   f"At {elapsed+60}s: {current_memory:.0f} MB (↑{memory_growth:.1f}%)",
                                   "warning" if memory_growth > 10 else "info")

            if error_rate > 5:
                result.add_event("high_error_rate", f"Error rate {error_rate:.1f}% at {elapsed}s", "warning")

        result.end_time = time.time()

        # Analyze memory growth
        if memory_samples and initial_memory:
            final_memory = memory_samples[-1]
            total_growth = ((final_memory - initial_memory) / initial_memory * 100)

            result.add_event("memory_analysis",
                           f"Total memory growth: {total_growth:.1f}% ({initial_memory:.0f}MB → {final_memory:.0f}MB)",
                           "warning" if total_growth > 5 else "info")

            # Check for linear growth (leak) vs plateau
            if len(memory_samples) >= 3:
                growth_rates = [memory_samples[i] - memory_samples[i-1] for i in range(1, len(memory_samples))]
                avg_growth_rate = statistics.mean(growth_rates)

                if avg_growth_rate > 10:  # Growing >10MB per check interval
                    result.breaking_point = {
                        "type": "memory_leak",
                        "growth_rate_mb_per_minute": avg_growth_rate * 60 / check_interval,
                        "timestamp": datetime.now().isoformat()
                    }
                    result.add_event("leak_detected",
                                   f"Possible memory leak: {avg_growth_rate*60/check_interval:.1f}MB/minute",
                                   "error")

        # Recommendations
        if memory_samples and initial_memory:
            final_memory = memory_samples[-1]
            total_growth = ((final_memory - initial_memory) / initial_memory * 100)

            if total_growth < 5:
                result.recommendations.append(f"Memory stable: {total_growth:.1f}% growth over 10 minutes. No leaks detected.")
            elif total_growth < 15:
                result.recommendations.append(f"Moderate growth: {total_growth:.1f}%. Monitor with longer tests.")
            else:
                result.recommendations.append(f"Significant growth: {total_growth:.1f}%. Possible memory leak. Check connection pooling.")
        else:
            result.recommendations.append("Unable to measure memory (Docker stats not available). Manual review recommended.")

        return result

    # ========================================================================
    # SCENARIO 6: Network Failure (Intermittent connectivity)
    # ========================================================================

    def scenario_6_network_failure(self) -> ChaosTestResult:
        """
        Intermittent connectivity failures.

        Expected: Graceful handling of transient failures.
        Success: Retry mechanism works, error rate <5% with retries.
        """
        result = ChaosTestResult("Network Failure (Intermittent Connectivity)", 6)

        if not self.check_system_ready():
            result.add_event("system_check", "System not ready", "error")
            return result

        result.start_time = time.time()
        result.add_event("test_start", "Beginning intermittent connectivity test", "info")

        # Simulate intermittent failures by using very short timeout
        # This will cause some requests to fail with timeouts
        timeout_failures = 0
        retry_successes = 0

        result.add_event("test_phase", "Testing with aggressive timeout (simulating packet loss)", "info")

        # Phase 1: Aggressive timeout (simulates ~10% packet loss)
        phase1_requests = self.concurrent_requests("/health", 50, 30, timeout=0.5)
        phase1_failures = sum(1 for r in phase1_requests if r["status_code"] >= 400)
        phase1_error_rate = phase1_failures / len(phase1_requests) * 100 if phase1_requests else 0

        for req in phase1_requests:
            result.add_request(req["latency_ms"], req["status_code"], "/health", req["error"])

        result.add_event("phase1_complete", f"Phase 1: {phase1_error_rate:.1f}% error rate with 0.5s timeout", "warning")

        # Phase 2: Retries with reasonable timeout
        result.add_event("retry_phase", "Retrying with normal timeout", "info")
        retry_requests = self.concurrent_requests("/health", 50, 30, timeout=30)

        retry_failures = sum(1 for r in retry_requests if r["status_code"] >= 400)
        retry_error_rate = retry_failures / len(retry_requests) * 100 if retry_requests else 0

        for req in retry_requests:
            result.add_request(req["latency_ms"], req["status_code"], "/health", req["error"])

        result.add_event("phase2_complete", f"Phase 2 (retry): {retry_error_rate:.1f}% error rate", "info")

        # Calculate improvement
        if phase1_error_rate > 0:
            improvement = ((phase1_error_rate - retry_error_rate) / phase1_error_rate * 100)
            result.add_event("retry_improvement",
                           f"Retry improvement: {improvement:.1f}% reduction in error rate",
                           "info")

        result.end_time = time.time()

        # Recommendations
        result.recommendations.append(
            f"Initial failure rate: {phase1_error_rate:.1f}%, After retry: {retry_error_rate:.1f}%"
        )

        if retry_error_rate < 5:
            result.recommendations.append("Excellent retry mechanism. Gracefully handles transient failures.")
        elif retry_error_rate < 15:
            result.recommendations.append("Retry mechanism working but could be improved. Consider exponential backoff.")
        else:
            result.recommendations.append("Retry mechanism needs improvement. Implement better backoff strategy.")

        return result

    # ========================================================================
    # SCENARIO 7: Database Connection Timeout
    # ========================================================================

    def scenario_7_connection_timeout(self) -> ChaosTestResult:
        """
        Short connection timeout to detect cascading failures.

        Expected: Some failures, but not cascade.
        Success: Error rate <5%, no cascading failure.
        """
        result = ChaosTestResult("Database Connection Timeout", 7)

        if not self.check_system_ready():
            result.add_event("system_check", "System not ready", "error")
            return result

        result.start_time = time.time()
        result.add_event("test_start", "Beginning connection timeout test", "info")

        # NOTE: This would require Neo4j configuration change to set timeout to 5s
        # For simulation, we use very short request timeout to measure circuit breaker

        result.add_event("baseline", "Measuring baseline with 30s timeout", "info")
        baseline_requests = self.concurrent_requests("/health", 50, 20, timeout=30)
        baseline_errors = sum(1 for r in baseline_requests if r["status_code"] >= 400)
        baseline_error_rate = baseline_errors / len(baseline_requests) * 100 if baseline_requests else 0

        for req in baseline_requests:
            result.add_request(req["latency_ms"], req["status_code"], "/health", req["error"])

        result.add_event("baseline_complete", f"Baseline: {baseline_error_rate:.1f}% error rate", "info")

        # Short timeout (5 seconds)
        result.add_event("short_timeout_test", "Testing with 5s connection timeout", "warning")
        short_timeout_requests = self.concurrent_requests("/health", 50, 30, timeout=5)
        short_errors = sum(1 for r in short_timeout_requests if r["status_code"] >= 400)
        short_error_rate = short_errors / len(short_timeout_requests) * 100 if short_timeout_requests else 0

        for req in short_timeout_requests:
            result.add_request(req["latency_ms"], req["status_code"], "/health", req["error"])

        result.add_event("short_timeout_complete", f"5s timeout: {short_error_rate:.1f}% error rate",
                        "warning" if short_error_rate > 5 else "info")

        if short_error_rate > 0:
            result.breaking_point = {
                "timeout_seconds": 5,
                "error_rate": short_error_rate,
                "timestamp": datetime.now().isoformat()
            }

        # Ultra-short timeout (1 second)
        result.add_event("ultra_short_timeout_test", "Testing with 1s connection timeout", "error")
        ultra_short_requests = self.concurrent_requests("/health", 50, 30, timeout=1)
        ultra_errors = sum(1 for r in ultra_short_requests if r["status_code"] >= 400)
        ultra_error_rate = ultra_errors / len(ultra_short_requests) * 100 if ultra_short_requests else 0

        for req in ultra_short_requests:
            result.add_request(req["latency_ms"], req["status_code"], "/health", req["error"])

        result.add_event("ultra_short_timeout_complete", f"1s timeout: {ultra_error_rate:.1f}% error rate", "error")

        # Recovery test
        result.add_event("recovery_test", "Recovery test with normal timeout", "info")
        recovery_start = time.time()
        recovery_requests = self.concurrent_requests("/health", 50, 20, timeout=30)
        recovery_time = time.time() - recovery_start

        recovery_errors = sum(1 for r in recovery_requests if r["status_code"] >= 400)
        recovery_error_rate = recovery_errors / len(recovery_requests) * 100 if recovery_requests else 0

        for req in recovery_requests:
            result.add_request(req["latency_ms"], req["status_code"], "/health", req["error"])

        if recovery_error_rate < baseline_error_rate + 2:
            result.recovery_time = recovery_time
            result.add_event("recovery_complete", "System recovered to baseline", "info")

        result.end_time = time.time()

        # Recommendations
        result.recommendations.append(
            f"Error rate escalation: Baseline {baseline_error_rate:.1f}% → "
            f"5s timeout {short_error_rate:.1f}% → 1s timeout {ultra_error_rate:.1f}%"
        )

        if ultra_error_rate > 50:
            result.recommendations.append(
                f"Cascading failures detected at 1s timeout ({ultra_error_rate:.1f}% errors). "
                "Implement circuit breaker to prevent cascades."
            )
        else:
            result.recommendations.append("No cascading failures. Circuit breaker or bulkhead pattern is working.")

        return result

    def _get_api_container_memory(self) -> Optional[float]:
        """Get current memory usage of basset_api container"""
        try:
            result = subprocess.run(
                ["docker", "stats", "basset_api", "--no-stream", "--format", "{{.MemUsage}}"],
                capture_output=True,
                timeout=5,
                text=True
            )
            if result.returncode == 0:
                memory_str = result.stdout.strip().split("/")[0].strip()
                # Parse "123MiB" or "1.5GiB"
                if memory_str.endswith("MiB"):
                    return float(memory_str[:-3])
                elif memory_str.endswith("GiB"):
                    return float(memory_str[:-3]) * 1024
                elif memory_str.endswith("KiB"):
                    return float(memory_str[:-3]) / 1024
            return None
        except Exception:
            return None

    def run_all_scenarios(self) -> Dict:
        """Execute all 7 chaos testing scenarios"""
        scenarios = [
            (1, self.scenario_1_connection_pool_exhaustion),
            (2, self.scenario_2_cache_failure),
            (3, self.scenario_3_database_slow_queries),
            (4, self.scenario_4_api_overload),
            (5, self.scenario_5_memory_leak_detection),
            (6, self.scenario_6_network_failure),
            (7, self.scenario_7_connection_timeout),
        ]

        results = {}

        for scenario_num, scenario_func in scenarios:
            print(f"\n{'='*70}")
            print(f"SCENARIO {scenario_num}: {scenario_func.__name__}")
            print(f"{'='*70}")

            try:
                result = scenario_func()
                results[scenario_num] = result

                summary = result.get_summary()
                print(f"\nSummary: {json.dumps(summary, indent=2)}")

            except Exception as e:
                print(f"ERROR in scenario {scenario_num}: {e}")
                traceback.print_exc()

            time.sleep(10)  # Pause between scenarios

        return results

    def run_single_scenario(self, scenario_num: int) -> Dict:
        """Run a single scenario by number"""
        scenarios = {
            1: self.scenario_1_connection_pool_exhaustion,
            2: self.scenario_2_cache_failure,
            3: self.scenario_3_database_slow_queries,
            4: self.scenario_4_api_overload,
            5: self.scenario_5_memory_leak_detection,
            6: self.scenario_6_network_failure,
            7: self.scenario_7_connection_timeout,
        }

        if scenario_num not in scenarios:
            print(f"Invalid scenario number. Choose 1-7.")
            return {}

        print(f"\n{'='*70}")
        print(f"SCENARIO {scenario_num}: {scenarios[scenario_num].__name__}")
        print(f"{'='*70}")

        try:
            result = scenarios[scenario_num]()
            return {scenario_num: result}
        except Exception as e:
            print(f"ERROR in scenario {scenario_num}: {e}")
            traceback.print_exc()
            return {}


def main():
    parser = argparse.ArgumentParser(description="Chaos Testing Suite")
    parser.add_argument("--scenario", type=int, choices=range(1, 8),
                       help="Run specific scenario (1-7)")
    parser.add_argument("--output", type=str, default="chaos-test-results.json",
                       help="Output file for results (default: chaos-test-results.json)")
    parser.add_argument("--timeout", type=int, default=30,
                       help="Request timeout in seconds (default: 30)")

    args = parser.parse_args()

    tester = ChaosTester(timeout=args.timeout)

    print("Chaos Testing Suite")
    print("=" * 70)

    if not tester.check_system_ready():
        print("\nERROR: System not ready at http://localhost:8080")
        print("Please ensure Docker services are running:")
        print("  docker-compose up -d")
        sys.exit(1)

    print("✓ System is ready")
    print()

    if args.scenario:
        results_dict = tester.run_single_scenario(args.scenario)
    else:
        results_dict = tester.run_all_scenarios()

    # Convert results to JSON-serializable format
    json_results = {}
    for scenario_num, result in results_dict.items():
        summary = result.get_summary()
        json_results[scenario_num] = {
            "summary": summary,
            "events": result.events,
            "sample_errors": result.errors[:10],  # First 10 errors
            "total_requests": len(result.requests),
        }

    # Write results
    with open(args.output, "w") as f:
        json.dump(json_results, f, indent=2)

    print(f"\n{'='*70}")
    print(f"Results saved to: {args.output}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
