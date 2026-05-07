# E2E Verification Tests - Quick Start Guide

## What This Is

Comprehensive end-to-end production verification tests for Basset Hound OSINT Platform (Phase 5b).

- **41 tests** covering complete workflows, performance, and security
- **20-step workflow** validation for fresh deployments
- **Performance benchmarks** with automatic metric collection
- **Monitoring integration** for Grafana and Prometheus
- **Graceful degradation** for optional services

## Quick Commands

### Run Tests (Fastest)
```bash
cd /home/devel/basset-hound
pytest tests/test_e2e_complete.py -v
```

### Fresh Deployment + Tests
```bash
./tests/run_e2e_verification.sh fresh
```

### Generate Beautiful Report
```bash
./tests/run_e2e_verification.sh html
# Report opens automatically
```

### Watch Tests in Real-Time
```bash
./tests/run_e2e_verification.sh monitor
```

## Prerequisites

Ensure these are installed:
```bash
pip install pytest pytest-asyncio httpx pytest-html pytest-json-report
```

Docker and docker-compose must be available.

## What Gets Tested

### 1. Fresh Deployment (20 Steps)
- Create project → Create 3 entity types → Add tags → Create relationships
- Search entities → Get graph data → Link accounts → Generate PDF
- Bulk import → Get metrics → Entity suggestions → Cleanup

### 2. Monitoring (5 Tests)
- Prometheus health and targets
- Grafana dashboards
- Metrics endpoint

### 3. Performance (7 Benchmarks)
- Entity creation: < 1.0s
- Relationship creation: < 0.5s
- Search (cached): < 0.1s
- Search (uncached): < 0.5s
- Graph fetch: < 1.0s
- PDF generation: < 10.0s
- Metrics export: < 0.1s

### 4. Security (4 Tests)
- No hardcoded credentials
- No debug code left in
- CORS headers present
- No unhandled exceptions

### 5. Integration Tests
- basset-verify identifier verification
- cletus news integration
- browser extension compatibility

## Test Results

### Success (All Green)
```
42 passed in 1234.56s
Status: READY FOR PRODUCTION
```

### Partial (Some Optional Services Down)
```
35 passed, 7 skipped in 456.78s
Status: ACCEPTABLE (Non-critical services unavailable)
```

### Failure (Needs Investigation)
```
30 passed, 12 failed in 234.56s
Status: REQUIRES FIXES
Check: tests/results/e2e_report_*.html
```

## Where to Find Results

After running tests, check:

| What | Location |
|------|----------|
| HTML Report | `tests/results/e2e_report_*.html` |
| JSON Metrics | `tests/results/e2e_report.json` |
| Test Log | `tests/results/e2e_test_*.log` |
| Coverage | `tests/results/coverage_*/` |

## Common Issues & Fixes

### "Cannot connect to localhost:8000"
```bash
# Start services first
docker compose up -d
sleep 30
# Then run tests
```

### "All tests skipped"
- Check API is running: `curl http://localhost:8000/health`
- Verify environment: `echo $API_URL`

### "Performance tests fail"
- Check system resources: `docker stats`
- Run test in isolation: 
  ```bash
  pytest tests/test_e2e_complete.py::TestPerformance -v
  ```

### "Database connection error"
```bash
# Reset database
docker compose down -v
docker compose up -d
sleep 60
```

## Environment Variables

Set if using non-standard configuration:

```bash
export API_URL="http://localhost:8000"
export PROMETHEUS_URL="http://localhost:9090"
export GRAFANA_URL="http://localhost:3001"
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="neo4jbasset"
export REDIS_URL="redis://localhost:6379"
```

## For CI/CD

Add to your pipeline:

```bash
# GitHub Actions / GitLab CI / Jenkins
./tests/run_e2e_verification.sh fresh
```

This will:
1. Start fresh deployment
2. Run all tests
3. Generate reports
4. Exit with 0 (pass) or 1 (fail)

## Full Documentation

See comprehensive guides:
- `E2E_VERIFICATION_GUIDE.md` - Detailed guide with troubleshooting
- `E2E_TEST_SUMMARY.txt` - Complete test structure and metrics
- `test_e2e_complete.py` - Source code with inline documentation

## Key Features

✓ Automatic endpoint pattern matching (API versioning compatible)
✓ Graceful service degradation (optional services can be down)
✓ Performance tracking with decorators
✓ HTML/JSON report generation
✓ Global test state management
✓ Comprehensive error handling
✓ Security validation built-in
✓ <1 hour total execution

## Test Coverage by Phase

- **Phase 5b** - This suite (41 tests)
- **Phase 5c** - Load testing, chaos engineering
- **Phase 5d** - Penetration testing, documentation generation

## Need Help?

1. Check `E2E_VERIFICATION_GUIDE.md` troubleshooting section
2. Review test logs: `tail tests/results/e2e_test_*.log`
3. Check service logs: `docker compose logs basset_api`
4. Run in monitor mode: `./tests/run_e2e_verification.sh monitor`

## Success Criteria

- ✅ 40+ tests implemented
- ✅ 95%+ pass rate (with graceful degradation)
- ✅ All 20-step workflow tests passing
- ✅ Performance benchmarks met
- ✅ Security checks passing
- ✅ Reports generated automatically
- ✅ <1 hour execution time
