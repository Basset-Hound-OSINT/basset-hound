# Chaos Test Execution Playbook

**Step-by-step guide for executing chaos testing scenarios**

---

## Pre-Test Checklist (15 minutes)

### System Preparation
- [ ] Close all other applications (free up RAM/CPU)
- [ ] Verify disk space: `df -h /` (minimum 20GB free)
- [ ] Clear Docker logs: `docker system prune -a --volumes` (optional)
- [ ] Verify network connectivity: `ping 8.8.8.8`

### Docker Verification
```bash
# Check Docker is running
docker ps
# Output should show containers (or be empty)

# Check Docker Compose version
docker-compose --version
# Should be >= 1.29.0

# Navigate to project
cd /home/devel/basset-hound
pwd  # Verify correct directory
```

### System Startup
```bash
# Start all services (if not already running)
docker-compose up -d

# Wait for services to be ready
sleep 30

# Verify health
curl http://localhost:8080/health
# Should return 200 OK with JSON response
```

### Health Verification
```bash
# Check all containers are running
docker-compose ps
# Should show:
# - basset_api (healthy)
# - basset_nginx (healthy)
# - neo4j (healthy)
# - redis_cache (healthy)

# Get API logs
docker-compose logs basset_api | tail -20
# Should show "Application startup complete"
```

---

## Quick Test Execution (5 minutes)

**Goal:** Verify test framework works before running full suite

### Execute Single Scenario
```bash
cd /home/devel/basset-hound/scripts/load-testing

# Run Scenario 1: Connection Pool Exhaustion
python3 chaos_testing_suite.py \
  --scenario 1 \
  --output test-scenario-1.json \
  --timeout 30

# Expected output:
# ======================================================================
# SCENARIO 1: scenario_1_connection_pool_exhaustion
# ======================================================================
# ...
# Results saved to: test-scenario-1.json
```

### Monitor During Test
In another terminal:
```bash
# Watch Docker metrics
watch -n 2 'docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"'

# Or in another terminal: watch API logs
docker-compose logs -f basset_api | grep -E "ERROR|WARNING|connection"
```

### Review Quick Test Results
```bash
# Look at results
cat test-scenario-1.json

# Parse with Python
python3 << 'EOF'
import json
with open('test-scenario-1.json') as f:
    data = json.load(f)
    summary = data['1']['summary']
    print(f"Error Rate: {summary['error_rate_percent']}%")
    print(f"Throughput: {summary['throughput_req_s']} req/s")
    print(f"p99 Latency: {summary['latency']['p99_ms']}ms")
    if summary['breaking_point']:
        print(f"Breaking Point: {summary['breaking_point']}")
EOF
```

### Pass/Fail Check
```bash
# Quick validation
python3 << 'EOF'
import json
with open('test-scenario-1.json') as f:
    data = json.load(f)
    error_rate = data['1']['summary']['error_rate_percent']
    if error_rate < 15:
        print("✓ PASS: Error rate within tolerance")
    else:
        print(f"✗ REVIEW: Error rate {error_rate}% (expected <15%)")
EOF
```

---

## Full Test Suite Execution (90 minutes)

**Goal:** Run all 7 scenarios for comprehensive resilience analysis

### Start Full Test
```bash
cd /home/devel/basset-hound/scripts/load-testing

# Start test (will take 60-90 minutes)
python3 chaos_testing_suite.py \
  --output full-chaos-results.json \
  --timeout 30

# Terminal will show progress:
# ======================================================================
# SCENARIO 1: scenario_1_connection_pool_exhaustion
# ======================================================================
# ...
# Scenario 1 complete, moving to Scenario 2
```

### Monitoring During Full Suite

**Terminal 1: Docker Metrics**
```bash
watch -n 5 'docker stats basset_api neo4j redis_cache basset_nginx --no-stream'
```

**Terminal 2: API Logs**
```bash
docker-compose logs -f basset_api | grep -E "ERROR|WARNING|connection" | tee api-errors.log
```

**Terminal 3: Check Progress**
```bash
# Watch file size growth (test is generating data)
watch -n 10 'ls -lh /home/devel/basset-hound/scripts/load-testing/full-chaos-results.json'

# Or tail the most recent events
python3 << 'EOF'
import json
import time
while True:
    try:
        with open('full-chaos-results.json') as f:
            data = json.load(f)
        print(f"Scenarios completed: {len(data)}/7")
        time.sleep(30)
    except:
        pass
EOF
```

### Time Estimates per Scenario
```
Scenario 1 (Connection Pool):      3-5 min
  ↓ (pause 10 seconds)
Scenario 2 (Cache Failure):       10-15 min  ⚠️ Longest (Docker ops)
  ↓ (pause 10 seconds)
Scenario 3 (Database Slowdown):    5-7 min
  ↓ (pause 10 seconds)
Scenario 4 (API Overload):         5-7 min
  ↓ (pause 10 seconds)
Scenario 5 (Memory Leak):         10-15 min  ⚠️ Second longest (10 min load)
  ↓ (pause 10 seconds)
Scenario 6 (Network Failure):      5-7 min
  ↓ (pause 10 seconds)
Scenario 7 (Connection Timeout):   5-7 min

Total: 45-90 minutes (depending on system speed)
```

---

## Post-Test Analysis (30 minutes)

### Basic Results Review
```bash
# Verify results file generated
ls -lh full-chaos-results.json

# Count scenarios completed
python3 << 'EOF'
import json
with open('full-chaos-results.json') as f:
    data = json.load(f)
print(f"Scenarios: {len(data)}/7")
for sid in sorted(data.keys()):
    name = data[sid]['summary']['scenario']
    rate = data[sid]['summary']['error_rate_percent']
    print(f"  {sid}. {name}: {rate}% error rate")
EOF
```

### Final Scoring
```bash
python3 << 'EOF'
import json
with open('full-chaos-results.json') as f:
    data = json.load(f)

results = {}
for scenario_id, d in data.items():
    error_rate = d['summary']['error_rate_percent']
    threshold = 15 if scenario_id in ['1', '4', '6', '7'] else 10
    status = "PASS" if error_rate <= threshold else "REVIEW" if error_rate <= 20 else "FAIL"
    results[scenario_id] = {"error_rate": error_rate, "status": status}

print("\n" + "=" * 70)
print("CHAOS TEST RESULTS")
print("=" * 70)

for sid in sorted(results.keys()):
    r = results[sid]
    symbol = "✓" if r['status'] == "PASS" else "⚠" if r['status'] == "REVIEW" else "✗"
    print(f"{symbol} Scenario {sid}: {r['status']} ({r['error_rate']}% error rate)")

passed = sum(1 for r in results.values() if r['status'] == 'PASS')
print(f"\nResult: {passed}/7 scenarios passed")
print("=" * 70)
EOF
```

---

## Quick Reference

### Run Quick Test
```bash
cd /home/devel/basset-hound/scripts/load-testing
python3 chaos_testing_suite.py --scenario 1 --output test.json
```

### Run Full Suite
```bash
cd /home/devel/basset-hound/scripts/load-testing
python3 chaos_testing_suite.py --output results.json
```

### Check Results
```bash
python3 << 'EOF'
import json
with open('results.json') as f:
    for sid, d in json.load(f).items():
        s = d['summary']
        print(f"Scenario {sid}: {s['error_rate_percent']}% error rate")
EOF
```

---

## Troubleshooting

### System Not Ready
```bash
docker-compose up -d
sleep 30
curl http://localhost:8080/health
```

### Test Hangs
```bash
# Check if running
ps aux | grep chaos_testing_suite.py

# Check Docker
docker stats basset_api --no-stream
```

### High Error Rates
```bash
# Check logs
docker-compose logs basset_api | tail -50

# Check system health
docker stats --no-stream
```

---

**Playbook Version:** 1.0  
**Location:** `/home/devel/basset-hound/docs/handoffs/CHAOS-TEST-EXECUTION-PLAYBOOK.md`
