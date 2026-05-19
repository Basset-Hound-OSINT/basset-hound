#!/usr/bin/env python3
"""
Performance Analysis and Diagnostics
Analyzes load test results and identifies optimization opportunities
"""

import json
from pathlib import Path
from datetime import datetime
import statistics

def analyze_load_test_results():
    """Analyze the load testing results"""

    results_summary = {
        "test_date": "2026-05-19",
        "test_version": "Optimized Load Test v4",
        "findings": {
            "endpoint_performance": {
                "health_check": {
                    "p99_ms": 8125.10,
                    "target_ms": 50,
                    "status": "CRITICAL",
                    "issue": "8+ second timeout issue - likely Neo4j connectivity hanging",
                    "success_rate": "6%",
                    "notes": [
                        "Health check polls Neo4j which is in 'disconnected' state",
                        "Query timeout/retry logic may be blocking",
                        "Consider: async health checks, timeout reduction, health status caching"
                    ]
                },
                "api_info": {
                    "p99_ms": float('inf'),
                    "target_ms": 50,
                    "status": "CRITICAL",
                    "issue": "Complete timeout under load",
                    "success_rate": "0%",
                    "notes": [
                        "Endpoint timing out completely during concurrent load",
                        "May indicate connection pool exhaustion",
                        "Verify if endpoint queries database"
                    ]
                },
                "frontend_dashboard": {
                    "p99_ms": 5276.71,
                    "target_ms": 100,
                    "status": "WARN",
                    "issue": "High variance - some requests very slow",
                    "success_rate": "100%",
                    "median_ms": 59.75,
                    "notes": [
                        "Min: 20ms (good), Max: 6290ms (bad) - 300x variance",
                        "Likely blocking I/O or template rendering under load",
                        "Consider: async template rendering, static file caching"
                    ]
                },
                "search": {
                    "p99_ms": 493.83,
                    "target_ms": 200,
                    "status": "WARN",
                    "issue": "p99 exceeds target by 2.5x",
                    "success_rate": "100%",
                    "median_ms": 452.98,
                    "notes": [
                        "Search is consistently slow (median ~450ms)",
                        "Not timeout issue (all requests succeed)",
                        "Consider: full-text search optimization, caching, indexing"
                    ]
                },
                "entity_types": {
                    "p99_ms": 158.72,
                    "target_ms": 100,
                    "status": "WARN",
                    "issue": "p99 slightly exceeds target",
                    "success_rate": "100%",
                    "median_ms": 54.86,
                    "notes": [
                        "Mostly good performance (p50: 54ms)",
                        "Occasional spikes to 158ms",
                        "Consider: query optimization, caching metadata"
                    ]
                }
            },
            "overall_metrics": {
                "error_rate": 38.80,
                "target_error_rate": 1.0,
                "status": "CRITICAL",
                "issue": "Primarily health check and API info timeouts",
                "notes": [
                    "38.8% error rate is problematic",
                    "97 failed requests out of 250 total",
                    "Main failures: health check (47 fails) + API info (50 fails)",
                    "Query endpoints (search, entity types): 0% error rate"
                ]
            },
            "cache_hit_rate": {
                "measured": 0.0,
                "target": 60.0,
                "status": "CRITICAL",
                "issue": "No cache hits recorded",
                "notes": [
                    "Either cache layer not working or responses marked as uncacheable",
                    "Recommend checking cache headers in responses",
                    "Verify Redis connection and cache configuration"
                ]
            },
            "throughput": {
                "measured_req_s": 2.79,
                "target_req_s": 5000,
                "status": "FAIL (test limited)",
                "notes": [
                    "Test worker pool limit: 20 workers",
                    "Actual throughput likely higher - test is bottleneck",
                    "Sustained request rate during test: ~4.6 req/s at end",
                    "With more workers, throughput would improve"
                ]
            }
        },
        "root_causes": [
            {
                "issue": "Neo4j Health Check Blocking",
                "severity": "CRITICAL",
                "description": "Health check endpoint queries Neo4j with 10+ second timeout",
                "affected_endpoints": ["/health"],
                "impact": "Cascades failures during load test due to thread exhaustion",
                "recommendation": "Implement async health checks or separate health check without DB query"
            },
            {
                "issue": "Search Latency",
                "severity": "HIGH",
                "description": "Full-text search p99: 493ms (target: 200ms)",
                "affected_endpoints": ["/api/v1/search"],
                "impact": "Query endpoints miss performance targets",
                "recommendation": "Profile search queries, optimize indexing, consider caching"
            },
            {
                "issue": "No Cache Hits",
                "severity": "MEDIUM",
                "description": "Cache hit rate 0% despite optimization target of 60%",
                "affected_endpoints": ["All"],
                "impact": "Increased database load, higher latencies",
                "recommendation": "Verify cache headers, implement cache warming, review TTL settings"
            },
            {
                "issue": "Frontend Response Variance",
                "severity": "MEDIUM",
                "description": "Dashboard min 20ms, max 6290ms - 300x variance",
                "affected_endpoints": ["/"],
                "impact": "Unpredictable response times for users",
                "recommendation": "Identify blocking operations, profile template rendering"
            }
        ],
        "optimization_priority": [
            {
                "rank": 1,
                "area": "Health Check Optimization",
                "effort": "LOW",
                "impact": "HIGH",
                "actions": [
                    "Move Neo4j query from health check",
                    "Cache health status for 5-10 seconds",
                    "Use async/non-blocking health verification",
                    "Expected improvement: 8000ms -> <50ms"
                ]
            },
            {
                "rank": 2,
                "area": "Search Performance",
                "effort": "MEDIUM",
                "impact": "MEDIUM",
                "actions": [
                    "Profile current search query execution",
                    "Verify database indexes on search fields",
                    "Implement result caching (Redis)",
                    "Consider search result pagination optimization",
                    "Expected improvement: 493ms -> <200ms p99"
                ]
            },
            {
                "rank": 3,
                "area": "Cache Configuration",
                "effort": "MEDIUM",
                "impact": "HIGH",
                "actions": [
                    "Verify cache response headers",
                    "Implement cache warming on startup",
                    "Set appropriate TTL for each endpoint",
                    "Monitor cache hit rate in metrics",
                    "Expected improvement: 0% -> >60% hit rate"
                ]
            },
            {
                "rank": 4,
                "area": "Frontend Response Stability",
                "effort": "MEDIUM",
                "impact": "MEDIUM",
                "actions": [
                    "Profile template rendering",
                    "Move blocking I/O outside request path",
                    "Consider static file serving optimization",
                    "Expected improvement: Reduce variance, target p99 <100ms"
                ]
            }
        ]
    }

    return results_summary

def generate_detailed_analysis_report():
    """Generate detailed analysis report"""

    report_path = Path("/home/devel/basset-hound/docs/handoffs/performance-analysis-detailed.md")
    report_path.parent.mkdir(parents=True, exist_ok=True)

    analysis = analyze_load_test_results()

    with open(report_path, "w") as f:
        f.write("# Detailed Performance Analysis & Optimization Report\n\n")
        f.write(f"**Date**: {datetime.now().isoformat()}\n")
        f.write(f"**Analysis Type**: Load Test Post-Mortem\n")
        f.write(f"**Phase**: 8 Performance Validation\n\n")

        # Executive Summary
        f.write("## Executive Summary\n\n")
        f.write("Load testing revealed several critical performance issues that must be addressed:\n\n")
        f.write("| Issue | Severity | Current | Target | Gap |\n")
        f.write("|-------|----------|---------|--------|-----|\n")
        f.write("| Health Check Latency | CRITICAL | 8125ms | 50ms | -16150% |\n")
        f.write("| Error Rate | CRITICAL | 38.8% | 1% | +3780% |\n")
        f.write("| Cache Hit Rate | CRITICAL | 0% | 60% | -100% |\n")
        f.write("| Search Latency (p99) | HIGH | 493ms | 200ms | -147% |\n")
        f.write("| Frontend Variance | MEDIUM | 6290ms max | <100ms p99 | -6190% |\n\n")

        # Root Cause Analysis
        f.write("## Root Cause Analysis\n\n")

        for cause in analysis["root_causes"]:
            f.write(f"### {cause['issue']} (Severity: {cause['severity']})\n\n")
            f.write(f"**Description**: {cause['description']}\n\n")
            f.write(f"**Affected Endpoints**: {', '.join(cause['affected_endpoints'])}\n\n")
            f.write(f"**Impact**: {cause['impact']}\n\n")
            f.write(f"**Recommended Fix**: {cause['recommendation']}\n\n")

        # Endpoint Deep Dive
        f.write("## Endpoint-by-Endpoint Analysis\n\n")

        for endpoint, data in analysis["findings"]["endpoint_performance"].items():
            status_icon = "🔴" if data["status"] == "CRITICAL" else "🟡" if data["status"] == "WARN" else "🟢"
            f.write(f"### {status_icon} {endpoint.replace('_', ' ').title()}\n\n")

            if "p99_ms" in data and data["p99_ms"] != float('inf'):
                f.write(f"- **p99 Latency**: {data['p99_ms']:.2f}ms (target: {data['target_ms']}ms)\n")
            if "median_ms" in data:
                f.write(f"- **Median Latency**: {data['median_ms']:.2f}ms\n")
            f.write(f"- **Success Rate**: {data['success_rate']}\n")
            f.write(f"- **Issue**: {data['issue']}\n\n")
            f.write(f"**Recommendations**:\n")
            for note in data.get("notes", []):
                f.write(f"- {note}\n")
            f.write("\n")

        # Optimization Roadmap
        f.write("## Optimization Roadmap\n\n")

        for item in analysis["optimization_priority"]:
            f.write(f"### Priority {item['rank']}: {item['area']}\n\n")
            f.write(f"**Effort**: {item['effort']} | **Impact**: {item['impact']}\n\n")
            f.write(f"**Actions**:\n")
            for action in item["actions"]:
                f.write(f"- {action}\n")
            f.write("\n")

        # Implementation Plan
        f.write("## Implementation Plan\n\n")
        f.write("### Phase 1: Critical Fixes (Target: 1 day)\n\n")
        f.write("1. **Health Check Refactoring**\n")
        f.write("   - Remove DB query from health check\n")
        f.write("   - Implement lightweight status check\n")
        f.write("   - Cache status for 10 seconds\n")
        f.write("   - Expected Impact: 8000ms -> <50ms\n\n")

        f.write("2. **Cache Configuration Review**\n")
        f.write("   - Verify response headers include caching directives\n")
        f.write("   - Enable caching on safe endpoints\n")
        f.write("   - Set up Redis cache layer\n")
        f.write("   - Expected Impact: 0% -> 40% hit rate\n\n")

        f.write("### Phase 2: Performance Optimization (Target: 2-3 days)\n\n")
        f.write("1. **Search Query Optimization**\n")
        f.write("   - Profile current search execution\n")
        f.write("   - Add database indexes\n")
        f.write("   - Implement result caching\n")
        f.write("   - Expected Impact: 493ms -> <200ms p99\n\n")

        f.write("2. **Frontend Stability**\n")
        f.write("   - Identify blocking operations\n")
        f.write("   - Optimize template rendering\n")
        f.write("   - Expected Impact: Reduce p99 variance\n\n")

        # Validation Plan
        f.write("## Validation Plan\n\n")
        f.write("### Test Configuration\n")
        f.write("- Workers: 20\n")
        f.write("- Requests per Endpoint: 50\n")
        f.write("- Total Requests: 250\n")
        f.write("- Duration: ~55 seconds\n\n")

        f.write("### Target Metrics (Post-Optimization)\n")
        f.write("| Metric | Current | Target | Success Criteria |\n")
        f.write("|--------|---------|--------|------------------|\n")
        f.write("| Error Rate | 38.8% | <1% | ✅ <1% |\n")
        f.write("| Health Check p99 | 8125ms | 50ms | ✅ <100ms |\n")
        f.write("| Search p99 | 493ms | 200ms | ✅ <250ms |\n")
        f.write("| Cache Hit Rate | 0% | 60% | ✅ >50% |\n")
        f.write("| Throughput | 2.79 req/s | 100+ req/s | ✅ <1% error |\n\n")

        # Next Steps
        f.write("## Next Steps\n\n")
        f.write("1. **Immediate** (Next 1 hour)\n")
        f.write("   - Investigate health check timeout root cause\n")
        f.write("   - Check Neo4j connection status\n")
        f.write("   - Review application logs for errors\n\n")

        f.write("2. **Short Term** (Next 2-4 hours)\n")
        f.write("   - Implement health check refactoring\n")
        f.write("   - Fix cache header configuration\n")
        f.write("   - Re-run load tests\n\n")

        f.write("3. **Medium Term** (Next 1-2 days)\n")
        f.write("   - Optimize search performance\n")
        f.write("   - Profile and fix frontend variance\n")
        f.write("   - Full performance validation\n\n")

        # Metrics Dashboard Recommendations
        f.write("## Monitoring Recommendations\n\n")
        f.write("### Key Metrics to Monitor\n")
        f.write("- Health check latency (should be <50ms)\n")
        f.write("- API error rate (should be <1%)\n")
        f.write("- Cache hit rate (should be >60%)\n")
        f.write("- Search latency p99 (should be <200ms)\n")
        f.write("- Database connection pool utilization\n")
        f.write("- Neo4j query execution time\n\n")

        f.write("### Alert Thresholds\n")
        f.write("- Error rate > 5%: Investigate immediately\n")
        f.write("- p99 latency > 200ms: Review slow queries\n")
        f.write("- Cache hit rate < 30%: Review cache configuration\n")
        f.write("- Connection pool > 80% utilization: Check for leaks\n\n")

        # Appendix
        f.write("## Appendix\n\n")
        f.write("### Test Environment\n")
        f.write("- API: Basset Hound (uvicorn, port 8080)\n")
        f.write("- Database: Neo4j 5.26 (appears disconnected)\n")
        f.write("- Cache: Redis (connected, 0ms latency)\n")
        f.write("- Workers: 20 concurrent\n\n")

        f.write("### Load Test Results\n")
        f.write("- Total Requests: 250\n")
        f.write("- Successful: 153 (61.2%)\n")
        f.write("- Failed: 97 (38.8%)\n")
        f.write("- Test Duration: 54.85 seconds\n\n")

        f.write("---\n\n")
        f.write(f"**Report Generated**: {datetime.now().isoformat()}\n")
        f.write("**Analyst**: Load Testing Agent\n")

    return report_path

if __name__ == "__main__":
    report_path = generate_detailed_analysis_report()
    print(f"✅ Detailed analysis report generated: {report_path}")

    analysis = analyze_load_test_results()
    print("\n" + "=" * 100)
    print("CRITICAL FINDINGS SUMMARY")
    print("=" * 100)

    print("\nRoot Causes Identified:")
    for i, cause in enumerate(analysis["root_causes"], 1):
        print(f"\n{i}. {cause['issue']} ({cause['severity']})")
        print(f"   {cause['description']}")
        print(f"   → {cause['recommendation']}")

    print("\n" + "=" * 100)
    print("OPTIMIZATION PRIORITIES")
    print("=" * 100)

    for item in analysis["optimization_priority"]:
        print(f"\nP{item['rank']}: {item['area']} ({item['effort']} effort, {item['impact']} impact)")
        print(f"  {item['actions'][0]}")
