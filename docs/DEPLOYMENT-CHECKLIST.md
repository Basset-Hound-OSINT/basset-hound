# Basset Hound: Production Deployment Checklist

**Version**: 2.1.0  
**Date**: 2026-05-19  
**Status**: Ready for Production Deployment  
**Last Review**: Phase 8 Complete

---

## Table of Contents

1. [Overview](#overview)
2. [Pre-Deployment Phase](#pre-deployment-phase)
3. [Deployment Phase](#deployment-phase)
4. [Post-Deployment Phase](#post-deployment-phase)
5. [Rollback Procedures](#rollback-procedures)
6. [Support Runbook](#support-runbook)

---

## Overview

This checklist provides step-by-step procedures for deploying Basset Hound to production. It covers:
- Pre-deployment verification and security audit
- Deployment with database migrations
- Post-deployment smoke tests and validation
- Rollback instructions if issues occur

**Estimated Time**: 30-60 minutes depending on data size

**Prerequisites**:
- Access to production environment
- Docker and Docker Compose installed
- Backup of current production database (if upgrading)
- Team notification of planned maintenance window

---

## Pre-Deployment Phase

### 1. Pre-Deployment Verification (30 minutes)

#### 1.1 Code Review Completion
- [ ] All Phase 8 features reviewed and approved
- [ ] Security audit completed (see section 1.4)
- [ ] Performance testing passed (see Performance Targets section)
- [ ] No critical or high-severity bugs open
- [ ] All blockers documented and resolved

**Verification**:
```bash
# Check git status
git status
# Expected: clean or only non-code files modified

# Check test results
npm test && pytest

# Check code quality
npm run lint && flake8 api/
```

#### 1.2 Environment Configuration
- [ ] `.env` file created with production values
- [ ] Database credentials secured and rotated
- [ ] JWT secret key generated (use `openssl rand -base64 64`)
- [ ] CORS origins configured for production domain
- [ ] Redis password configured (if not using Docker)
- [ ] All integration URLs verified

**Required Environment Variables**:
```bash
# Core
DEBUG=false
APP_VERSION=2.1.0
ENVIRONMENT=production

# Database
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=${SECURE_NEO4J_PASSWORD}
NEO4J_dbms_memory_heap_max__size=8G
NEO4J_server_memory_pagecache_size=4G

# Authentication
AUTH_ENABLED=true
SECRET_KEY=${SECURE_SECRET_KEY}
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# API Configuration
HOST=0.0.0.0
PORT=8000
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
CORS_ALLOW_CREDENTIALS=true

# Cache
CACHE_ENABLED=true
CACHE_DEFAULT_TTL=3600
REDIS_URL=redis://redis:6379/0
REDIS_MAX_MEMORY=256mb

# Integrations
BASSET_VERIFY_URL=http://basset-verify:8001
BASSET_VERIFY_ENABLED=true
BASSET_BROWSER_ENABLED=true
CLETUS_ENABLED=true
CLETUS_BASE_URL=http://cletus:9000

# Monitoring
PROMETHEUS_ENABLED=true
LOG_LEVEL=INFO
LOG_FORMAT=json
STRUCTURED_LOGGING=true

# Features (Phase 8)
ENABLE_ADVANCED_SEARCH=true
ENABLE_ML_ANALYTICS=false  # Only if ML models trained
ENABLE_COLLABORATION=true
ENABLE_PLUGINS=true
ENABLE_EXPORT=true
ENABLE_FULL_TEXT_SEARCH=true
```

**Verification**:
```bash
# Validate environment file
set -a
source .env
set +a

# Check required variables
for var in NEO4J_PASSWORD SECRET_KEY ENVIRONMENT; do
  [ -z "${!var}" ] && echo "ERROR: $var not set" && exit 1
done
echo "✓ Environment variables validated"
```

#### 1.3 Database Backup
- [ ] Neo4j backup created and tested
- [ ] Backup location verified and accessible
- [ ] Restore procedure documented and tested
- [ ] Backup retention policy configured (30 days minimum)

**Backup Procedure**:
```bash
#!/bin/bash
BACKUP_DIR="/opt/basset-hound/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DB_BACKUP="$BACKUP_DIR/neo4j_pre_deploy_$TIMESTAMP.dump"

mkdir -p "$BACKUP_DIR"

# Create backup
docker exec neo4j_osint_db neo4j-admin database dump neo4j "$DB_BACKUP" \
  --neo4j-conf=/etc/neo4j/neo4j.conf

# Compress
gzip "$DB_BACKUP"

echo "✓ Backup created: ${DB_BACKUP}.gz"

# Verify backup
if [ -f "${DB_BACKUP}.gz" ]; then
  echo "✓ Backup verification successful"
else
  echo "✗ Backup verification failed"
  exit 1
fi
```

#### 1.4 Security Audit Checklist
- [ ] **Authentication**: JWT enabled with strong secret key
  ```bash
  curl -X POST http://localhost:8080/api/v1/auth/tokens \
    -H "Content-Type: application/json" \
    -d '{"username":"test","password":"test"}'
  # Should require valid credentials
  ```

- [ ] **HTTPS/TLS**: SSL certificate valid and configured
  ```bash
  openssl x509 -in /etc/letsencrypt/live/yourdomain/fullchain.pem -text -noout | grep -E "Not Before|Not After"
  # Verify expiration date is in future
  ```

- [ ] **Database Security**: Neo4j password changed from default
  ```bash
  # Connect with old password should fail
  docker exec -it neo4j_osint_db cypher-shell -u neo4j -p neo4jbasset 2>&1 | grep -i "authentication"
  # Should show authentication error
  ```

- [ ] **Encryption at Rest**: Data volume encrypted (if applicable)
  ```bash
  cryptsetup status /dev/mapper/neo4j_data
  # Should show encryption details
  ```

- [ ] **Network Security**: Firewall rules configured
  ```bash
  sudo ufw status
  # Should show only necessary ports open (22, 80, 443)
  ```

- [ ] **Rate Limiting**: Configured in nginx or API
  ```bash
  grep -n "limit_req" /opt/basset-hound/nginx/nginx.conf
  # Should show rate limiting configuration
  ```

- [ ] **CORS**: Properly restricted to production domain
  ```bash
  grep CORS_ORIGINS .env
  # Should show only production domain(s)
  ```

- [ ] **Audit Logging**: Enabled and configured
  ```bash
  grep AUDIT .env
  AUDIT_ENABLED=true
  AUDIT_LOG_RETENTION_DAYS=90
  ```

- [ ] **Secrets Management**: No hardcoded credentials in code
  ```bash
  grep -r "password\|token\|secret" api/ --include="*.py" | grep -v "self\|config\|env" | wc -l
  # Should return 0 or only reference to env vars
  ```

**Verification Script**:
```bash
#!/bin/bash
echo "=== Security Audit Checklist ==="

# Check AUTH_ENABLED
[ "$(grep AUTH_ENABLED .env | cut -d= -f2)" = "true" ] && echo "✓ Auth enabled" || echo "✗ Auth disabled"

# Check DEBUG mode
[ "$(grep DEBUG .env | cut -d= -f2)" = "false" ] && echo "✓ Debug disabled" || echo "✗ Debug enabled"

# Check HTTPS
[ -f "/etc/letsencrypt/live/yourdomain/fullchain.pem" ] && echo "✓ HTTPS cert found" || echo "⚠ HTTPS cert not found"

# Check database password
[ ${#NEO4J_PASSWORD} -ge 16 ] && echo "✓ DB password length OK" || echo "⚠ DB password may be weak"

# Check Redis
redis-cli ping 2>/dev/null && echo "✓ Redis accessible" || echo "⚠ Redis not accessible"
```

#### 1.5 Performance Testing
- [ ] Load testing completed (2000+ req/s)
- [ ] Query latency p99 < 100ms
- [ ] Cache hit rate > 60%
- [ ] Memory usage within limits
- [ ] No memory leaks detected

**Performance Targets (Phase 8)**:
```
✅ Query Latency p99: <100ms
✅ Cache Hit Rate: 60%+
✅ API Throughput: 2000+ req/s
✅ Bundle Size (gzipped): <300KB
✅ FCP (First Paint): <2s
✅ Lighthouse Score: 90+
```

**Verification**:
```bash
# Test API performance
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8080/api/v1/projects

# Check cache hit rate
curl http://localhost:8080/api/v1/metrics/cache

# Monitor system resources
docker stats --no-stream

# Run Lighthouse audit
npm run lighthouse
```

#### 1.6 Integration Testing
- [ ] basset-verify integration verified
  ```bash
  curl http://basset-verify:8001/health
  ```

- [ ] basset-hound-browser integration verified
  ```bash
  curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" \
    http://localhost:8080/ws/browser
  ```

- [ ] cletus integration verified
  ```bash
  curl http://cletus:9000/health
  ```

- [ ] All Phase 8 feature endpoints tested:
  ```bash
  # Advanced search
  curl 'http://localhost:8080/api/v1/search/full-text?q=test'
  
  # ML analytics (if enabled)
  curl http://localhost:8080/api/v1/ml/models/status
  
  # Plugins
  curl http://localhost:8080/api/v1/plugins
  
  # Export
  curl http://localhost:8080/api/v1/projects/proj_123/export/csv
  ```

#### 1.7 Documentation Review
- [ ] API_REFERENCE.md current and complete
- [ ] DEPLOYMENT.md procedures tested and verified
- [ ] ARCHITECTURE.md matches current implementation
- [ ] BLOCKERS.md reviewed and resolved
- [ ] Phase 8 findings documented
- [ ] Runbook procedures reviewed and tested

**Verification**:
```bash
# Check all docs exist
for doc in API_REFERENCE.md DEPLOYMENT.md ARCHITECTURE.md README.md; do
  [ -f "docs/$doc" ] && echo "✓ $doc exists" || echo "✗ $doc missing"
done
```

---

## Deployment Phase

### 2. Pre-Deployment Preparation (15 minutes)

#### 2.1 Maintenance Window Announcement
- [ ] Send notification to all users 30 minutes before deployment
- [ ] Document expected downtime (30-60 minutes)
- [ ] Provide status update channel
- [ ] Have support team standby

**Sample Announcement**:
```
MAINTENANCE ALERT
=================
Basset Hound will be unavailable on [DATE] at [TIME] for approximately 1 hour.

Reason: Production deployment with performance and security upgrades
Expected Downtime: [TIME] - [TIME]

Phase 8 Features Coming:
- Advanced search with full-text indexing
- Real-time collaboration
- ML analytics
- Plugin system
- Enhanced export formats

Status Updates: [SLACK_CHANNEL / STATUS_PAGE]
```

#### 2.2 Health Check Baseline
- [ ] Current system health documented
- [ ] Key metrics recorded (request rate, error rate, latency)
- [ ] Database size recorded
- [ ] Connection pool status documented

**Baseline Metrics**:
```bash
#!/bin/bash
echo "=== Pre-Deployment Health Check ==="
echo "Timestamp: $(date)"

# API health
echo "API Health:"
curl -s http://localhost:8080/health | jq .

# Database metrics
echo "Database Size:"
docker exec neo4j_osint_db cypher-shell -u neo4j -p $NEO4J_PASSWORD \
  "CALL db.stats.retrieve('graph') YIELD section, key, value WHERE key = 'nodesCreated' RETURN value;" 2>/dev/null || echo "Database check skipped"

# Request metrics (last hour)
echo "Request Metrics (last hour):"
curl -s http://localhost:9090/api/v1/query?query=rate\(basset_request_count\[1h\]\) | jq . 2>/dev/null || echo "Prometheus unavailable"

# Memory usage
echo "Memory Usage:"
docker stats --no-stream | grep basset_api
```

#### 2.3 Rollback Plan Review
- [ ] Previous working version identified and tested
- [ ] Rollback procedure rehearsed with team
- [ ] Database restore from backup tested (dry run)
- [ ] Communication plan for rollback scenario documented

### 3. Deployment Execution (20-30 minutes)

#### 3.1 Service Shutdown (in order)
```bash
#!/bin/bash
set -e

echo "=== Basset Hound Deployment ==="
echo "Starting deployment at $(date)"

# 1. Stop accepting new requests
echo "Step 1: Draining connections..."
docker exec basset_api python -c "
import time
print('Draining remaining requests...')
time.sleep(5)
" || true

# 2. Stop Celery workers (can't interrupt long-running tasks)
echo "Step 2: Stopping Celery workers..."
docker compose stop celery_worker celery_beat

# 3. Stop API
echo "Step 3: Stopping API..."
docker compose stop basset_api

# 4. Keep database running for migrations
echo "Step 4: Database still running for migrations..."
docker compose ps | grep neo4j

echo "✓ Services stopped"
```

#### 3.2 Database Migrations
```bash
#!/bin/bash

echo "Step 5: Running database migrations..."

# Backup before migration
docker exec neo4j_osint_db neo4j-admin database dump neo4j \
  /opt/basset-hound/backups/pre_migration_$(date +%Y%m%d_%H%M%S).dump || echo "Backup optional"

# Run Phase 8 migrations
echo "Applying Phase 8 schema changes..."

# Migration 1: Add search indexes
docker exec neo4j_osint_db cypher-shell -u neo4j -p $NEO4J_PASSWORD <<'EOF'
-- Phase 8: Full-text search indexes
CREATE FULLTEXT INDEX entity_search IF NOT EXISTS
  FOR (e:Entity) ON EACH [e.name, e.description, e.identifier];

CREATE INDEX entity_type_idx IF NOT EXISTS FOR (e:Entity) ON (e.entity_type);
CREATE INDEX project_id_idx IF NOT EXISTS FOR (e:Entity) ON (e.project_id);
CREATE INDEX created_at_idx IF NOT EXISTS FOR (e:Entity) ON (e.created_at);

-- Verify indexes
SHOW INDEXES;
EOF

# Migration 2: Add ML analytics columns (if ML enabled)
if [ "${ENABLE_ML_ANALYTICS}" = "true" ]; then
  docker exec neo4j_osint_db cypher-shell -u neo4j -p $NEO4J_PASSWORD <<'EOF'
-- Add ML confidence scores
MATCH (e:Entity)
WHERE e.ml_confidence IS NULL
SET e.ml_confidence = 0.0
RETURN count(e) as updated;
EOF
fi

# Migration 3: Initialize collaboration timestamps
docker exec neo4j_osint_db cypher-shell -u neo4j -p $NEO4J_PASSWORD <<'EOF'
-- Add collaboration tracking
MATCH (e:Entity)
WHERE e.last_modified_by IS NULL
SET e.last_modified_by = "system",
    e.last_modified_at = datetime()
RETURN count(e) as updated;
EOF

echo "✓ Migrations completed"
```

#### 3.3 Update and Restart Services
```bash
#!/bin/bash

echo "Step 6: Building and restarting services..."

# Pull latest code (if using git)
git pull origin main || echo "Git pull skipped"

# Build new Docker images
docker compose build --no-cache basset_api celery_worker celery_beat

# Start services in correct order
echo "Starting database..."
docker compose up -d neo4j
sleep 30  # Wait for Neo4j to be ready

echo "Starting cache..."
docker compose up -d redis

echo "Starting API..."
docker compose up -d basset_api

echo "Waiting for API to be healthy..."
for i in {1..60}; do
  if curl -f http://localhost:8080/health > /dev/null 2>&1; then
    echo "✓ API is healthy"
    break
  fi
  echo "Waiting... ($i/60)"
  sleep 1
done

echo "Starting background workers..."
docker compose up -d celery_worker celery_beat

echo "Starting monitoring..."
docker compose up -d prometheus grafana nginx

echo "✓ All services started"
```

#### 3.4 Health Verification
```bash
#!/bin/bash

echo "Step 7: Verifying deployment..."

# Function to retry health check
check_health() {
  local service=$1
  local url=$2
  local max_attempts=30
  
  for ((i=1; i<=max_attempts; i++)); do
    if curl -f "$url" > /dev/null 2>&1; then
      echo "✓ $service is healthy"
      return 0
    fi
    echo "Waiting for $service... ($i/$max_attempts)"
    sleep 2
  done
  
  echo "✗ $service failed to become healthy"
  return 1
}

# Verify all services
check_health "API" "http://localhost:8080/health" || exit 1
check_health "Neo4j" "http://localhost:7474" || exit 1
check_health "Redis" "redis://localhost:6379" || exit 1

echo "✓ All services healthy"
```

---

## Post-Deployment Phase

### 4. Post-Deployment Validation (20-30 minutes)

#### 4.1 Smoke Tests
```bash
#!/bin/bash

echo "=== Post-Deployment Smoke Tests ==="

test_count=0
pass_count=0

run_test() {
  local name=$1
  local cmd=$2
  test_count=$((test_count + 1))
  
  echo -n "Testing $name... "
  if eval "$cmd" > /dev/null 2>&1; then
    echo "✓"
    pass_count=$((pass_count + 1))
  else
    echo "✗"
  fi
}

# Core API tests
run_test "API health" 'curl -f http://localhost:8080/health'
run_test "API docs" 'curl -f http://localhost:8080/docs | grep -q openapi'
run_test "Dashboard" 'curl -f http://localhost:8080/'

# Authentication tests
run_test "Auth endpoint" 'curl -f http://localhost:8080/api/v1/auth/tokens'

# Database tests
run_test "Projects endpoint" 'curl -f http://localhost:8080/api/v1/projects'
run_test "Database connection" 'docker exec neo4j_osint_db cypher-shell -u neo4j "RETURN 1"'

# Phase 8 feature tests
run_test "Advanced search" 'curl -f "http://localhost:8080/api/v1/search/full-text?q=test"'
run_test "Plugins" 'curl -f http://localhost:8080/api/v1/plugins'
run_test "Collaboration" 'curl -f "http://localhost:8080/api/v1/collaboration/presence"'

# Integration tests
run_test "basset-verify" 'curl -f http://basset-verify:8001/health'
run_test "cletus" 'curl -f http://cletus:9000/health'

# Monitoring tests
run_test "Prometheus" 'curl -f http://localhost:9090/-/healthy'
run_test "Grafana" 'curl -f http://localhost:3000/api/health'
run_test "Metrics export" 'curl -f http://localhost:8080/metrics | grep -q basset'

echo ""
echo "=== Test Summary ==="
echo "Passed: $pass_count / $test_count"

if [ $pass_count -eq $test_count ]; then
  echo "✓ All smoke tests passed"
  exit 0
else
  echo "✗ Some tests failed"
  exit 1
fi
```

#### 4.2 Performance Validation
```bash
#!/bin/bash

echo "=== Performance Validation ==="

# Query latency test
echo "Testing query latency..."
result=$(curl -s -w "%{time_total}" -o /dev/null http://localhost:8080/api/v1/projects)
latency_ms=$(echo "$result * 1000" | bc)
echo "Query latency: ${latency_ms}ms"
[ $(echo "$latency_ms < 100" | bc) -eq 1 ] && echo "✓ Latency acceptable" || echo "⚠ Latency elevated"

# Throughput test (simple)
echo "Testing throughput..."
start=$(date +%s%N)
for i in {1..100}; do
  curl -s http://localhost:8080/api/v1/projects > /dev/null
done
end=$(date +%s%N)
duration=$((($end - $start) / 1000000))  # milliseconds
throughput=$((100 * 1000 / duration))
echo "Throughput: $throughput req/s"
[ $throughput -gt 1000 ] && echo "✓ Throughput acceptable" || echo "⚠ Throughput low"

# Cache hit rate test
echo "Testing cache effectiveness..."
curl -s http://localhost:8080/api/v1/metrics/cache | jq .
# Expected: hit_rate > 0.60

# Memory usage test
echo "Memory usage:"
docker stats --no-stream | grep -E "NAME|basset_api|neo4j|redis"
```

#### 4.3 Data Integrity Checks
```bash
#!/bin/bash

echo "=== Data Integrity Checks ==="

# Verify entity counts
echo "Checking entity counts..."
docker exec neo4j_osint_db cypher-shell -u neo4j -p $NEO4J_PASSWORD <<'EOF'
MATCH (e:Entity) RETURN count(e) as entity_count;
MATCH (r:Relationship) RETURN count(r) as relationship_count;
MATCH (p:Platform) RETURN count(p) as platform_count;
EOF

# Verify indexes exist
echo "Verifying Phase 8 indexes..."
docker exec neo4j_osint_db cypher-shell -u neo4j -p $NEO4J_PASSWORD <<'EOF'
SHOW INDEXES WHERE name CONTAINS 'search' OR name CONTAINS 'entity_type';
EOF

# Check for data corruption
echo "Checking for orphaned nodes..."
docker exec neo4j_osint_db cypher-shell -u neo4j -p $NEO4J_PASSWORD <<'EOF'
MATCH (e:Entity)
WHERE NOT (e)-[]-()
RETURN count(e) as orphaned
LIMIT 10;
EOF

echo "✓ Data integrity check complete"
```

#### 4.4 Monitoring Setup Verification
```bash
#!/bin/bash

echo "=== Monitoring Verification ==="

# Check Prometheus targets
echo "Prometheus targets:"
curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job: .job, state: .health}'

# Check Grafana dashboards
echo "Grafana dashboards:"
curl -s http://localhost:3000/api/dashboards/search | jq '.[] | {title: .title, id: .id}'

# Check alert rules
echo "Alert rules:"
curl -s http://localhost:9090/api/v1/rules | jq '.data.groups[].rules[] | {alert: .alert, severity: .labels.severity}'

# Verify metrics are being collected
echo "Checking metric collection..."
curl -s http://localhost:8080/metrics | head -20
```

#### 4.5 Security Verification Post-Deployment
```bash
#!/bin/bash

echo "=== Post-Deployment Security Check ==="

# Verify HTTPS is enforced
echo "HTTPS enforcement:"
curl -i http://localhost:8080/api/v1/projects 2>/dev/null | grep -i "Location\|Upgrade"

# Verify auth headers required
echo "Testing auth requirement..."
curl -s http://localhost:8080/api/v1/admin 2>&1 | grep -q "unauthorized\|403" && echo "✓ Auth required" || echo "⚠ Auth may not be enforced"

# Check security headers
echo "Security headers:"
curl -i http://localhost:8080/ 2>/dev/null | grep -i "strict-transport\|x-content\|x-frame\|content-security"

# Verify no debug info leaked
echo "Checking for debug info..."
curl -s http://localhost:8080/api/v1/invalid 2>&1 | grep -i "traceback\|debug\|python" && echo "⚠ Debug info leaked" || echo "✓ No debug info"
```

#### 4.6 Team Notification
- [ ] Notify team that deployment successful
- [ ] Share performance metrics
- [ ] Document any issues encountered
- [ ] Update status page

**Sample Notification**:
```
DEPLOYMENT SUCCESSFUL ✓
=======================
Basset Hound Phase 8 deployed to production.

Timeline:
├─ Pre-deployment: 30 min
├─ Database migrations: 5 min
├─ Service restart: 8 min
└─ Testing & validation: 25 min
Total: 1 hour 8 minutes

New Features:
✓ Advanced search with full-text indexing
✓ Real-time collaboration features
✓ Enhanced plugin system
✓ Multiple export formats
✓ ML analytics (optional)

Performance:
✓ Query latency: 45ms (p99)
✓ Cache hit rate: 72%
✓ API throughput: 2500 req/s

No issues encountered. System operating normally.
```

---

## Rollback Procedures

### 5. Rollback to Previous Version

**Use if**: Critical issues detected post-deployment that cannot be quickly fixed

#### 5.1 Rollback Decision Criteria
- [ ] Multiple critical features broken
- [ ] Database corruption detected
- [ ] Performance degradation > 50%
- [ ] Security vulnerability discovered
- [ ] Cannot fix within 15 minutes

#### 5.2 Immediate Actions (First 5 minutes)
```bash
#!/bin/bash

echo "=== ROLLBACK INITIATED ==="
echo "Time: $(date)"

# 1. Stop accepting new requests immediately
echo "Step 1: Stopping new requests..."
docker compose stop basset_api celery_worker

# 2. Notify team
echo "Step 2: Notifying team..."
# Send alert to ops channel
echo "CRITICAL: Deployment rollback initiated at $(date)" | \
  slack_notify "#ops-critical"

# 3. Get backup list
echo "Step 3: Available backups..."
ls -lth /opt/basset-hound/backups/neo4j_*.dump* | head -5
```

#### 5.3 Database Rollback
```bash
#!/bin/bash

echo "Step 4: Rolling back database..."

BACKUP_FILE="/opt/basset-hound/backups/neo4j_pre_deploy_TIMESTAMP.dump.gz"

# 1. Verify backup exists
if [ ! -f "$BACKUP_FILE" ]; then
  echo "✗ Backup file not found: $BACKUP_FILE"
  exit 1
fi

# 2. Stop Neo4j
docker compose stop neo4j
sleep 5

# 3. Remove current database
docker volume rm basset-hound_neo4j_data || echo "Volume already removed"

# 4. Extract backup
gunzip -c "$BACKUP_FILE" > /tmp/neo4j_restore.dump

# 5. Start Neo4j
docker compose up -d neo4j
sleep 30

# 6. Restore from backup
docker exec neo4j_osint_db neo4j-admin database load neo4j \
  /tmp/neo4j_restore.dump --overwrite-destination

# 7. Restart Neo4j
docker compose restart neo4j
sleep 10

# 8. Verify restore
docker exec neo4j_osint_db cypher-shell -u neo4j -p $NEO4J_PASSWORD \
  "RETURN 'Database restored' as status;"

echo "✓ Database rollback complete"
```

#### 5.4 Application Rollback
```bash
#!/bin/bash

echo "Step 5: Rolling back application..."

# 1. Revert to previous Docker image
docker compose down
git checkout HEAD~1  # Revert to previous commit

# 2. Rebuild with previous version
docker compose build --no-cache basset_api celery_worker

# 3. Restart services
docker compose up -d neo4j redis
sleep 10

docker compose up -d basset_api celery_worker celery_beat
sleep 10

# 4. Verify services
for i in {1..30}; do
  if curl -f http://localhost:8080/health > /dev/null 2>&1; then
    echo "✓ Application rolled back successfully"
    exit 0
  fi
  sleep 1
done

echo "✗ Rollback failed - manual intervention required"
exit 1
```

#### 5.5 Post-Rollback Validation
```bash
#!/bin/bash

echo "Step 6: Validating rollback..."

# Run smoke tests again
./scripts/smoke-tests.sh || exit 1

# Verify data integrity
docker exec neo4j_osint_db cypher-shell -u neo4j -p $NEO4J_PASSWORD \
  "MATCH (n) RETURN count(n) as nodes;"

# Check system health
curl http://localhost:8080/health | jq .

echo "✓ Rollback validation complete"
echo "System is operational at previous version"
```

#### 5.6 Post-Rollback Communication
```
ROLLBACK NOTIFICATION
====================
Basset Hound has been rolled back to previous version.

Time Initiated: [TIME]
Duration: [DURATION]
Reason: [REASON]

Current Status: ✓ Operational at v2.0.0
Next Steps: 
- Engineering team investigating issue
- Will schedule re-deployment with fix
- ETA: [TIME]

We apologize for the disruption.
```

---

## Support Runbook

### 6. Common Issues & Resolutions

#### Issue: API Returns 500 Error Post-Deployment

**Symptoms**: HTTP 500 errors on API endpoints

**Diagnosis**:
```bash
# Check API logs
docker compose logs basset_api --tail=100 | grep ERROR

# Check database connectivity
docker exec basset_api python -c "
from api.db import neo4j_handler
handler = neo4j_handler.Neo4jHandler()
print('Connected:', handler.check_connection())
"

# Check Redis connectivity
redis-cli ping
```

**Resolution**:
```bash
# Option 1: Restart API
docker compose restart basset_api

# Option 2: Check database migrations ran
docker exec neo4j_osint_db cypher-shell -u neo4j -p $NEO4J_PASSWORD \
  "SHOW INDEXES" | grep -E "entity_search|entity_type_idx"

# Option 3: Clear Redis cache if corrupted
redis-cli FLUSHDB

# Option 4: Check environment variables
docker compose config | grep -E "NEO4J_|SECRET_KEY|AUTH"
```

#### Issue: High Memory Usage Post-Deployment

**Symptoms**: Container memory > 90%, requests slow

**Diagnosis**:
```bash
# Check which service is consuming memory
docker stats --no-stream

# Check Java memory (Neo4j)
docker exec neo4j_osint_db jcmd $(docker exec neo4j_osint_db pidof java) \
  VM.native_memory summary

# Check Redis memory
redis-cli INFO memory | grep used
```

**Resolution**:
```bash
# Option 1: Increase heap size
# Edit docker-compose.yml:
# NEO4J_dbms_memory_heap_max__size=16G (was 8G)

# Option 2: Reduce cache TTL
# Edit .env:
# CACHE_DEFAULT_TTL=1800 (was 3600)

# Option 3: Reduce Redis maxmemory
redis-cli CONFIG SET maxmemory 512mb

# Option 4: Restart and monitor
docker compose restart neo4j
watch docker stats
```

#### Issue: Database Migrations Failed

**Symptoms**: Migration errors in logs, schema mismatch

**Diagnosis**:
```bash
# Check migration status
docker exec neo4j_osint_db cypher-shell -u neo4j -p $NEO4J_PASSWORD \
  "SHOW INDEXES" | wc -l

# Expected indexes for Phase 8: at least 5
```

**Resolution**:
```bash
# Option 1: Re-run migrations
docker exec neo4j_osint_db cypher-shell -u neo4j -p $NEO4J_PASSWORD < \
  /opt/basset-hound/scripts/migrations/phase8.cypher

# Option 2: Restore from backup and retry
# See Rollback Procedures section

# Option 3: Manual index creation
docker exec neo4j_osint_db cypher-shell -u neo4j -p $NEO4J_PASSWORD <<'EOF'
CREATE FULLTEXT INDEX entity_search IF NOT EXISTS
  FOR (e:Entity) ON EACH [e.name, e.description];
EOF
```

#### Issue: Nginx Reverse Proxy Not Working

**Symptoms**: 502 Bad Gateway errors

**Diagnosis**:
```bash
# Check nginx logs
docker compose logs nginx --tail=50 | grep -i error

# Check if API is reachable
curl -v http://basset_api:8000/health

# Check nginx config
docker exec nginx nginx -t
```

**Resolution**:
```bash
# Option 1: Restart nginx
docker compose restart nginx

# Option 2: Check docker network
docker network inspect basset-hound | grep basset_api

# Option 3: Verify API is running
docker compose ps | grep basset_api

# Option 4: Reload nginx config
docker compose exec nginx nginx -s reload
```

#### Issue: WebSocket Connection Fails

**Symptoms**: Real-time features not working, WebSocket errors in browser console

**Diagnosis**:
```bash
# Test WebSocket endpoint
websocat ws://localhost:8080/ws/test 2>&1

# Check nginx WebSocket configuration
grep -A5 "location /ws" /opt/basset-hound/nginx/nginx.conf

# Check if API is handling WebSocket upgrades
curl -v -H "Upgrade: websocket" http://localhost:8080/ws/test
```

**Resolution**:
```bash
# Verify nginx has correct WebSocket headers
# In nginx.conf, should have:
# proxy_http_version 1.1;
# proxy_set_header Upgrade $http_upgrade;
# proxy_set_header Connection "upgrade";
# proxy_read_timeout 86400;

# Restart nginx
docker compose restart nginx

# Clear browser cache and try again
# In browser: Ctrl+Shift+Delete -> Clear browsing data
```

#### Issue: Slow Queries Post-Deployment

**Symptoms**: Query latency > 500ms, timeouts

**Diagnosis**:
```bash
# Check slow query log
docker compose logs neo4j | grep "slower than"

# Analyze query performance
docker exec neo4j_osint_db cypher-shell -u neo4j -p $NEO4J_PASSWORD <<'EOF'
PROFILE MATCH (e:Entity) RETURN count(e);
EOF

# Check index usage
docker exec neo4j_osint_db cypher-shell -u neo4j -p $NEO4J_PASSWORD \
  "SHOW INDEXES" | grep -E "FULLTEXT|BTREE|RANGE"
```

**Resolution**:
```bash
# Option 1: Rebuild indexes
docker exec neo4j_osint_db cypher-shell -u neo4j -p $NEO4J_PASSWORD <<'EOF'
DROP INDEX entity_search IF EXISTS;
CREATE FULLTEXT INDEX entity_search 
  FOR (e:Entity) ON EACH [e.name, e.description];
EOF

# Option 2: Check cache hit rate
curl http://localhost:8080/api/v1/metrics/cache

# Option 3: Increase Redis cache size
redis-cli CONFIG SET maxmemory 512mb

# Option 4: Monitor query execution
docker exec neo4j_osint_db cypher-shell -u neo4j -p $NEO4J_PASSWORD \
  "CALL db.stats.retrieve('graph') YIELD section, key, value RETURN section, key, value"
```

#### Issue: Celery Workers Not Processing Tasks

**Symptoms**: Background jobs stuck, tasks never complete

**Diagnosis**:
```bash
# Check Celery status
docker compose logs celery_worker --tail=50 | grep -i error

# Check Redis for queued tasks
redis-cli LLEN celery

# Check worker connectivity to broker
redis-cli PING
```

**Resolution**:
```bash
# Option 1: Restart workers
docker compose restart celery_worker celery_beat

# Option 2: Clear stuck tasks
redis-cli DEL celery
redis-cli DEL celery-results

# Option 3: Check Redis connection string
grep CELERY_BROKER .env

# Option 4: Monitor worker activity
docker compose logs -f celery_worker | grep -E "received|succeeded|failed"
```

### 7. Escalation Contacts

Create a contact file at `/opt/basset-hound/docs/CONTACTS.md`:

```markdown
# Basset Hound Support Contacts

## On-Call Engineer
- Name: [NAME]
- Phone: [PHONE]
- Email: [EMAIL]
- Slack: [SLACK_HANDLE]

## Engineering Lead
- Name: [NAME]
- Phone: [PHONE]
- Email: [EMAIL]

## Database Administrator
- Name: [NAME]
- Phone: [PHONE]
- Email: [EMAIL]

## Escalation Procedure
1. Try automated remediation (restart service, clear cache)
2. Contact on-call engineer (30 min response time)
3. Contact engineering lead (immediate escalation)
4. If critical: Page database administrator

## External Dependencies
- basset-verify: Team A, contact: [EMAIL]
- cletus: Team B, contact: [EMAIL]
- basset-hound-browser: Team C, contact: [EMAIL]

## Incident Response
- Severity 1 (Critical): All hands, immediate response
- Severity 2 (High): Core team + on-call
- Severity 3 (Medium): Scheduled response within 4 hours
- Severity 4 (Low): Next business day

## Status Page
- Public: [STATUS_PAGE_URL]
- Internal: [INTERNAL_DASHBOARD_URL]
```

### 8. Post-Deployment Checklist (Hours 1-24)

- [ ] Monitor error rate every 15 minutes (should be < 1%)
- [ ] Monitor latency percentiles (p95, p99)
- [ ] Review Grafana dashboards for anomalies
- [ ] Check Prometheus alerts configured
- [ ] Monitor disk usage growth rate
- [ ] Verify automated backups running
- [ ] Document any performance metrics for future reference
- [ ] Perform end-to-end user workflow test
- [ ] Gather feedback from early users
- [ ] Schedule post-deployment retrospective

**Sample Dashboard Queries (Prometheus)**:
```bash
# Error rate (should be < 1%)
rate(basset_request_count{status=~"5.."}[5m])

# Latency p99
histogram_quantile(0.99, basset_request_latency_seconds)

# Cache hit rate (should be > 60%)
basset_cache_hits_total / (basset_cache_hits_total + basset_cache_misses_total)

# Database connection pool
neo4j_client_connection_pool_size

# Memory usage
container_memory_usage_bytes / container_spec_memory_limit_bytes
```

### 9. Success Criteria

Deployment is considered successful when:

- [x] All smoke tests pass (100% pass rate)
- [x] Error rate < 1% over 1 hour
- [x] API latency p99 < 100ms
- [x] Cache hit rate > 60%
- [x] All Phase 8 features operational
- [x] Database integrity verified
- [x] No data loss or corruption
- [x] All integrations working
- [x] Monitoring and alerting active
- [x] Team acknowledges deployment success

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.1.0 | 2026-05-19 | Phase 8 deployment checklist, added all 8 streams |
| 2.0.0 | 2026-05-07 | Initial production deployment guide |

---

## Quick Reference

### Key Files
- Configuration: `/opt/basset-hound/.env`
- Backups: `/opt/basset-hound/backups/`
- Logs: `docker compose logs [service]`
- Docker Compose: `/opt/basset-hound/docker-compose.yml`

### Key Commands
```bash
# Health checks
curl http://localhost:8080/health
docker compose ps

# Logs
docker compose logs -f basset_api
docker compose logs --since 1h

# Backups
docker exec neo4j_osint_db neo4j-admin database dump neo4j /path/to/backup.dump

# Monitoring
curl http://localhost:9090  # Prometheus
curl http://localhost:3000  # Grafana
curl http://localhost:8080/metrics  # Metrics endpoint

# Rollback
git checkout HEAD~1
docker compose build --no-cache
docker compose up -d
```

### Emergency Contacts
- On-Call: See `/opt/basset-hound/docs/CONTACTS.md`
- Status Page: [See contact file]
- Slack Channel: [See contact file]

---

**Document Owner**: Engineering Team  
**Last Updated**: 2026-05-19  
**Next Review**: After Phase 8 completion and initial production stability
