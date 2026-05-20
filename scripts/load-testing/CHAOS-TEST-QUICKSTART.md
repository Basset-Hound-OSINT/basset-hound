# Chaos Testing Quick Start Guide

**Basset Hound OSINT Platform - Resilience Testing**

---

## Prerequisites

1. **System Running**
   ```bash
   cd /home/devel/basset-hound
   docker-compose up -d
   docker-compose logs -f basset_api  # Wait for "Application startup complete"
   ```

2. **Verify System Ready**
   ```bash
   curl http://localhost:8080/health
   # Should return 200 OK
   ```

3. **Python Dependencies** (should already be installed)
   ```bash
   pip install requests tenacity
   ```

---

## Quick Test (5 minutes)

Run single scenario to verify setup:

```bash
cd /home/devel/basset-hound/scripts/load-testing
python3 chaos_testing_suite.py --scenario 1 --output test-scenario-1.json
```

Expected output:
```
Chaos Testing Suite
======================================================================
✓ System is ready

======================================================================
SCENARIO 1: scenario_1_connection_pool_exhaustion
======================================================================
...
Results saved to: test-scenario-1.json
```

---

## Full Test Suite (90 minutes)

Run all 7 scenarios with comprehensive analysis:

```bash
cd /home/devel/basset-hound/scripts/load-testing
python3 chaos_testing_suite.py --output full-chaos-results.json
```

**Estimated Duration per Scenario:**
- Scenario 1 (Connection Pool): 3-5 min
- Scenario 2 (Cache Failure): 10-15 min (includes Docker restart)
- Scenario 3 (Database Slowdown): 5-7 min
- Scenario 4 (API Overload): 5-7 min
- Scenario 5 (Memory Leak): 10-15 min
- Scenario 6 (Network Failure): 5-7 min
- Scenario 7 (Timeout): 5-7 min
- **Total: 45-90 minutes**

---

## Interpreting Results

### JSON Output Format

```json
{
  "1": {
    "summary": {
      "scenario": "Connection Pool Exhaustion",
      "number": 1,
      "duration_seconds": 185.2,
      "total_requests": 15000,
      "successful_requests": 14550,
      "failed_requests": 450,
      "error_rate_percent": 3.0,
      "throughput_req_s": 81.0,
      "latency": {
        "min_ms": 5.2,
        "max_ms": 3500.0,
        "avg_ms": 150.0,
        "median_ms": 120.0,
        "p95_ms": 350.0,
        "p99_ms": 900.0
      },
      "breaking_point": {
        "concurrency": 200,
        "error_rate": 15.5,
        "timestamp": "2026-05-19T21:50:00"
      },
      "recovery_time_seconds": 42.3,
      "recommendations": [
        "Connection pool breaking point at 200 concurrent..."
      ]
    },
    "events": [...],
    "sample_errors": [...],
    "total_requests": 15000
  }
}
```

### Key Metrics to Review

| Metric | Good | Warning | Bad |
|--------|------|---------|-----|
| Error Rate | <2% | 2-10% | >10% |
| Throughput | >50 req/s | 20-50 | <20 |
| p99 Latency | <500ms | 500-1000ms | >1000ms |
| Recovery Time | <1 min | 1-5 min | >5 min |
| Memory Growth | <3% | 3-10% | >10% |

### Passing Criteria (All Must Pass)
- [ ] No cascading failures (isolated errors)
- [ ] Error rate within tolerance for scenario
- [ ] Recovery time acceptable (<5 min)
- [ ] No data loss observed
- [ ] Graceful degradation (not hard failure)

---

## Advanced Usage

### Custom Parameters

```bash
# Run with 60-second request timeout
python3 chaos_testing_suite.py --scenario 1 --timeout 60

# Run specific scenario with custom output
python3 chaos_testing_suite.py --scenario 2 --output cache-failure.json

# Run all scenarios with longer timeout
python3 chaos_testing_suite.py --timeout 45 --output extended-timeout-results.json
```

### Monitoring During Test

In another terminal, watch system metrics:

```bash
# Watch Docker stats
watch -n 1 'docker stats --no-stream basset_api basset_nginx neo4j redis_cache'

# Watch API logs
docker-compose logs -f basset_api | grep -E "ERROR|WARNING|Traceback"

# Watch Neo4j connection pool
docker exec neo4j_osint_db cypher-shell -u neo4j -p your-password \
  "SHOW RUNTIME CONNECTIONS" 2>/dev/null | head -20
```

### Parsing Results

Python script to extract summary:

```python
import json

with open('full-chaos-results.json') as f:
    results = json.load(f)

for scenario_id, data in results.items():
    summary = data['summary']
    print(f"Scenario {scenario_id}: {summary['scenario']}")
    print(f"  Error Rate: {summary['error_rate_percent']}%")
    print(f"  Throughput: {summary['throughput_req_s']} req/s")
    print(f"  p99 Latency: {summary['latency']['p99_ms']}ms")
    print(f"  Status: {'PASS' if summary['error_rate_percent'] < 10 else 'REVIEW'}")
    print()
```

### Generating Report

Create summary report from results:

```bash
python3 << 'EOF'
import json
import sys
from datetime import datetime

with open('full-chaos-results.json') as f:
    results = json.load(f)

print("=" * 70)
print("CHAOS TESTING RESULTS SUMMARY")
print(f"Generated: {datetime.now().isoformat()}")
print("=" * 70)
print()

passed = 0
warnings = 0
failed = 0

for scenario_id in sorted(results.keys()):
    data = results[str(scenario_id)]
    summary = data['summary']
    
    error_rate = summary['error_rate_percent']
    status = "PASS" if error_rate < 10 else "WARN" if error_rate < 20 else "FAIL"
    
    if status == "PASS":
        passed += 1
        symbol = "✓"
    elif status == "WARN":
        warnings += 1
        symbol = "⚠"
    else:
        failed += 1
        symbol = "✗"
    
    print(f"{symbol} Scenario {scenario_id}: {summary['scenario']}")
    print(f"   Error Rate: {error_rate}%")
    print(f"   Requests: {summary['total_requests']}")
    print(f"   Throughput: {summary['throughput_req_s']} req/s")
    print()

print("=" * 70)
print(f"Results: {passed} PASS, {warnings} WARN, {failed} FAIL")
print("=" * 70)

if failed > 0:
    sys.exit(1)
EOF
```

---

## Troubleshooting

### "Connection refused" Error
```bash
# Check if system is running
curl http://localhost:8080/health

# If fails, start services
docker-compose up -d
docker-compose logs basset_api  # Wait for startup complete
```

### Tests Running Slowly
- Check system resources: `docker stats`
- Check if other processes using CPU/disk
- Increase timeout: `--timeout 60`
- Reduce concurrency by editing `concurrent_requests()` calls

### Docker Command Failures
- Ensure docker-compose installed: `docker-compose --version`
- Check permissions: `docker ps` (should not require sudo)
- Verify correct directory: `cd /home/devel/basset-hound`

### Memory Tests Failing
- Baseline may vary: Use first run as reference
- Run on idle system (no other services)
- Ensure sufficient disk space for logs

---

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Chaos Testing
on:
  schedule:
    - cron: '0 2 * * 0'  # Weekly Sunday 2am
  workflow_dispatch:

jobs:
  chaos-test:
    runs-on: ubuntu-latest
    services:
      neo4j:
        image: neo4j:5.26-community
        options: >-
          --health-cmd "wget -q --spider http://localhost:7474"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 3
      redis:
        image: redis:latest

    steps:
      - uses: actions/checkout@v3
      
      - name: Start API
        run: |
          docker-compose up -d basset_api basset_nginx
          sleep 30
          
      - name: Run chaos tests
        run: |
          cd scripts/load-testing
          python3 chaos_testing_suite.py --output results.json
          
      - name: Parse results
        run: |
          python3 << 'EOF'
          import json
          with open('scripts/load-testing/results.json') as f:
              data = json.load(f)
              for scenario_id, result in data.items():
                  error_rate = result['summary']['error_rate_percent']
                  if error_rate > 15:  # Allow 15% error rate
                      print(f"FAIL: Scenario {scenario_id} ({error_rate}%)")
                      exit(1)
          print("All scenarios passed")
          EOF
          
      - name: Upload results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: chaos-test-results
          path: scripts/load-testing/results.json
```

---

## Expected Results (Baseline)

Based on Phase 8 optimization deliverables:

| Scenario | Expected Error Rate | Expected Recovery |
|----------|-------------------|------------------|
| 1. Pool Exhaustion | <5% @ 150 concurrent | <1 minute |
| 2. Cache Failure | <5% without cache | <5 minutes |
| 3. DB Slowdown | <10% with timeout | <30 seconds |
| 4. API Overload | <10% @ 150 concurrent | Immediate |
| 5. Memory Leak | <5% growth @ 50 concurrent for 10min | N/A |
| 6. Network Failure | <5% after retry | <5 seconds |
| 7. Timeout Cascade | <5% (no cascade) | <30 seconds |

**Overall Rating: 7.5/10** (Production-ready with monitoring)

---

## Next Steps

1. ✅ Run quick test (scenario 1) to validate setup
2. ✅ Review results against expected metrics
3. ✅ Run full suite on clean system
4. ✅ Archive results with timestamp
5. ✅ Create GitHub issue for any failures
6. ✅ Schedule weekly chaos tests
7. ✅ Add to CI/CD pipeline

---

## Support

For issues or questions:
1. Check logs: `docker-compose logs -f`
2. Review CHAOS-TESTING-REPORT.md for detailed analysis
3. Inspect results.json for metrics breakdown
4. Contact platform team

**Test Framework:** chaos_testing_suite.py  
**Report:** /home/devel/basset-hound/docs/handoffs/CHAOS-TESTING-REPORT.md  
**Location:** /home/devel/basset-hound/scripts/load-testing/
