# Basset Hound - Comprehensive Deployment Runbook

**Version**: 1.0.0  
**Last Updated**: 2026-05-19  
**Status**: Production Ready  
**Target Audience**: DevOps Engineers, SREs, Operations Teams

---

## Table of Contents

1. [Executive Overview](#executive-overview)
2. [Pre-Deployment Checklist](#pre-deployment-checklist)
3. [Deployment Scenarios](#deployment-scenarios)
4. [Fresh Deployment](#fresh-deployment)
5. [Upgrade from Phase 7](#upgrade-from-phase-7)
6. [Staged Rollout](#staged-rollout)
7. [Emergency Hotfix](#emergency-hotfix)
8. [Post-Deployment Validation](#post-deployment-validation)
9. [Rollback Procedures](#rollback-procedures)
10. [Real-World Scenarios & Troubleshooting](#real-world-scenarios--troubleshooting)
11. [Communication Templates](#communication-templates)
12. [Runbook Maintenance](#runbook-maintenance)

---

## Executive Overview

### Deployment Scope

**Application**: Basset Hound OSINT Platform v2.0.0  
**Tech Stack**: FastAPI + Neo4j + Redis + Docker  
**Architecture**: 
- Single entry point (Nginx on port 8080)
- Graph database (Neo4j 5.28)
- Cache layer (Redis 7)
- Task queue (Celery, optional)

### Key Characteristics

- **Stateful**: Neo4j database persistence required
- **Single-Region**: No multi-region HA configuration
- **Container-Based**: Docker Compose orchestration
- **Integration-Heavy**: Depends on basset-verify, basset-hound-browser, cletus

### Estimated Timelines

| Scenario | Duration | Downtime |
|----------|----------|----------|
| Fresh deployment | 30-45 min | 0 min (greenfield) |
| Phase 7 upgrade | 45-60 min | 5-10 min |
| Staged rollout (3 regions) | 2-3 hours | 0 min (canary) |
| Emergency hotfix | 10-15 min | 1-2 min |

### Resource Requirements

**Minimum Production Setup**
- 2x CPU cores
- 4GB RAM (8GB recommended)
- 50GB storage (SSD)
- 1Gbps network

**Large Scale (10M+ entities)**
- 8+ CPU cores
- 32GB+ RAM
- 500GB+ SSD (Neo4j dedicated disk)
- 10Gbps network

---

## Pre-Deployment Checklist

### 30 Minutes Before Deployment

#### Code Review Checklist

```
☐ Code review completed (minimum 1 approver)
☐ All commits squashed or clean history
☐ Commit messages follow convention (feat:, fix:, docs:, etc.)
☐ No debug code or logging statements left in production code
☐ Environment variables documented in .env.example
☐ Version number updated in:
  ☐ api/config.py (APP_VERSION)
  ☐ docker-compose.yml (image tags)
  ☐ Dockerfile (LABEL org.opencontainers.image.version)
☐ CHANGELOG.md updated with new features/fixes
☐ Database schema changes documented (if any)
☐ Migration scripts prepared (if needed)
```

#### Security Audit Checklist

```
☐ No hardcoded secrets or API keys
☐ All environment variables properly set:
  ☐ POSTGRES_PASSWORD / NEO4J_PASSWORD changed
  ☐ SECRET_KEY is 64+ random characters
  ☐ JWT_SECRET_KEY set
  ☐ CORS_ORIGINS restricted to production domains
☐ Auth enabled in production (.env):
  ☐ AUTH_ENABLED=true
  ☐ JWT_ALGORITHM configured
☐ SSL/TLS certificates valid:
  ☐ Expiration date checked (renewal > 30 days)
  ☐ Certificate chain complete
  ☐ HSTS header configured
☐ Network restrictions in place:
  ☐ Firewall rules reviewed
  ☐ VPN/bastion host configured
  ☐ API endpoints behind authentication
☐ Audit logging enabled:
  ☐ AUDIT_ENABLED=true
  ☐ Log retention policy set
☐ No external service tokens exposed
☐ Dependency scan completed:
  ☐ No known CVEs in pip packages
  ☐ python-3.12.x or higher
☐ Database permissions reviewed
☐ User account cleanup (remove test accounts)
```

#### Performance Verification Checklist

```
☐ Load testing completed on staging environment
  ☐ Verified <100ms p99 query latency
  ☐ Verified 60%+ cache hit rate
  ☐ Verified 2000+ req/s throughput
  ☐ No memory leaks detected
☐ Neo4j indexes verified:
  ☐ CREATE INDEX entity_type_idx FOR (e:Entity) ON (e.entity_type)
  ☐ CREATE INDEX project_id_idx FOR (e:Entity) ON (e.project_id)
  ☐ CREATE INDEX identifier_idx FOR (d:Data) ON (d.identifier)
  ☐ Index usage confirmed in EXPLAIN PLAN
☐ Redis memory settings verified:
  ☐ maxmemory set to appropriate value
  ☐ maxmemory-policy=allkeys-lru
  ☐ Connection pool size adequate
☐ Monitoring dashboards loaded:
  ☐ Prometheus scrape interval: 15s
  ☐ Grafana dashboards created
  ☐ Alert thresholds set
☐ Browser compatibility verified:
  ☐ Chrome 120+
  ☐ Firefox 121+
  ☐ Safari 17+
  ☐ Mobile browsers tested
```

#### Test Results Review Checklist

```
☐ Unit tests passed: pytest tests/unit/ -v
☐ Integration tests passed: pytest tests/integration/ -v
☐ E2E tests passed: pytest tests/e2e/ -v
☐ API documentation tests passed
☐ Coverage report reviewed (>80% code coverage)
☐ Load test results reviewed:
  ☐ Response time distribution acceptable
  ☐ Error rate <0.1%
  ☐ No connection timeouts
☐ Smoke tests prepared:
  ☐ Health endpoint verification
  ☐ Basic CRUD operations
  ☐ Authentication flow
  ☐ Cache functionality
☐ Backup verification:
  ☐ Full database backup succeeds
  ☐ Backup can be restored
  ☐ Data integrity verified
```

#### Infrastructure Readiness Checklist

```
☐ Target environment specifications verified
☐ Networking configured:
  ☐ Firewall rules in place
  ☐ VPN access available
  ☐ DNS records created (if new domain)
  ☐ SSL certificate uploaded to load balancer
☐ Storage prepared:
  ☐ /opt/basset-hound directory exists
  ☐ /opt/basset-hound/backups directory created
  ☐ /opt/basset-hound/logs directory created
  ☐ Disk space verified (>100GB available)
☐ Docker resources verified:
  ☐ Docker daemon running
  ☐ docker-compose installed (version 2.20+)
  ☐ Docker images pulled or cached
  ☐ Docker network created: docker network inspect basset-hound
☐ Secrets management ready:
  ☐ Docker secrets created (if using Swarm)
  ☐ Vault integration configured (if using Enterprise)
  ☐ .env.production file created with secure permissions
☐ External services reachable:
  ☐ basset-verify service running
  ☐ basset-hound-browser configured
  ☐ cletus service running
  ☐ Network connectivity verified
```

---

## Deployment Scenarios

Basset Hound supports four primary deployment scenarios with different procedures and risk profiles:

### Scenario Selection Matrix

| Scenario | When to Use | Risk | Downtime | Duration |
|----------|------------|------|----------|----------|
| **Fresh Deployment** | New production environment, greenfield | Low | None | 30-45 min |
| **Phase 7 Upgrade** | Updating from Phase 7.x to Phase 8.0 | Medium | 5-10 min | 45-60 min |
| **Staged Rollout** | Multiple regions, gradual deployment | Low | 0 min (canary) | 2-3 hours |
| **Emergency Hotfix** | Critical bug fix, immediate deployment | High | 1-2 min | 10-15 min |

---

## Fresh Deployment

**Use Case**: First-time production deployment, no existing Phase 7 data

**Total Duration**: 30-45 minutes  
**Downtime**: None (greenfield deployment)  
**Rollback Difficulty**: Not applicable (first deployment)

### Phase 1: Pre-Deployment Preparation (5 minutes)

```bash
#!/bin/bash
# deployment-prep.sh

set -e

# 1. Verify all prerequisites
echo "[1/5] Verifying system requirements..."
docker --version || { echo "Docker not installed"; exit 1; }
docker-compose --version || { echo "docker-compose not installed"; exit 1; }
git --version || { echo "Git not installed"; exit 1; }

# 2. Create application directory structure
echo "[2/5] Creating directory structure..."
mkdir -p /opt/basset-hound/{data,logs,backups,projects}
chmod 755 /opt/basset-hound

# 3. Clone repository
echo "[3/5] Cloning repository..."
cd /opt
if [ -d "basset-hound" ]; then
  echo "Repository already exists, pulling latest..."
  cd basset-hound
  git pull origin main
else
  git clone https://github.com/yourusername/basset-hound.git
  cd basset-hound
fi

# 4. Verify critical files exist
echo "[4/5] Verifying deployment files..."
required_files=(
  "docker-compose.yml"
  ".env.example"
  "Dockerfile"
  "requirements.txt"
  "api/main.py"
)
for file in "${required_files[@]}"; do
  [ -f "$file" ] || { echo "Missing: $file"; exit 1; }
done

# 5. Create production environment file
echo "[5/5] Setting up environment..."
if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "Created .env file - EDIT THIS FILE NOW with production values"
  echo "Critical settings:"
  echo "  - NEO4J_PASSWORD: Change from default"
  echo "  - SECRET_KEY: Generate with: openssl rand -base64 64"
  echo "  - AUTH_ENABLED: Set to true"
  echo "  - CORS_ORIGINS: Set to your domain"
  exit 1  # Force manual intervention
fi

echo "✓ Pre-deployment preparation complete"
echo "Next step: verify .env file and run Phase 2"
```

**Status Check**: Stop here and manually verify `.env` file

### Phase 2: Docker Image Build (10-15 minutes)

```bash
#!/bin/bash
# deployment-build.sh

set -e

cd /opt/basset-hound

echo "[1/3] Building Docker images..."
docker compose build --no-cache

echo "[2/3] Verifying images..."
docker images | grep -E "basset|nginx|neo4j|redis" || { echo "Images not found"; exit 1; }

echo "[3/3] Pulling base images (if needed)..."
docker pull nginx:alpine
docker pull neo4j:5.28-community
docker pull redis:7-alpine
docker pull python:3.12-slim

echo "✓ Docker images built successfully"
```

**Estimated Time**: 10-15 minutes  
**Critical Path**: Building the Python application (most time-consuming)

### Phase 3: Database Initialization (5-10 minutes)

```bash
#!/bin/bash
# deployment-db-init.sh

set -e

cd /opt/basset-hound

echo "[1/4] Starting Neo4j database..."
docker compose up -d neo4j

echo "[2/4] Waiting for Neo4j to be healthy..."
max_attempts=30
attempt=0
while [ $attempt -lt $max_attempts ]; do
  if docker exec neo4j_osint_db cypher-shell -u neo4j -p neo4jbasset "MATCH (n) RETURN 1 LIMIT 1" 2>/dev/null; then
    echo "✓ Neo4j is ready"
    break
  fi
  
  echo "Attempt $((attempt + 1))/$max_attempts: Waiting for Neo4j..."
  sleep 2
  attempt=$((attempt + 1))
done

if [ $attempt -eq $max_attempts ]; then
  echo "✗ Neo4j failed to start"
  docker logs neo4j_osint_db | tail -20
  exit 1
fi

echo "[3/4] Creating database indexes..."
docker exec neo4j_osint_db cypher-shell -u neo4j -p neo4jbasset << 'EOF'
CREATE INDEX entity_type_idx IF NOT EXISTS FOR (e:Entity) ON (e.entity_type);
CREATE INDEX project_id_idx IF NOT EXISTS FOR (e:Entity) ON (e.project_id);
CREATE INDEX identifier_idx IF NOT EXISTS FOR (d:Data) ON (d.identifier);
CREATE INDEX timestamp_idx IF NOT EXISTS FOR (e:Entity) ON (e.created_at);
CREATE CONSTRAINT entity_id_unique IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE;
CREATE CONSTRAINT platform_id_unique IF NOT EXISTS FOR (p:Platform) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT project_id_unique IF NOT EXISTS FOR (p:Project) REQUIRE p.id IS UNIQUE;
EOF

echo "[4/4] Verifying database schema..."
docker exec neo4j_osint_db cypher-shell -u neo4j -p neo4jbasset "SHOW INDEXES;"

echo "✓ Database initialization complete"
```

### Phase 4: Service Startup (5 minutes)

```bash
#!/bin/bash
# deployment-startup.sh

set -e

cd /opt/basset-hound

echo "[1/4] Starting all services..."
docker compose up -d

echo "[2/4] Waiting for services to be healthy..."
services=("basset_api" "neo4j_osint_db" "basset_redis" "basset_nginx")
max_attempts=30

for service in "${services[@]}"; do
  attempt=0
  while [ $attempt -lt $max_attempts ]; do
    status=$(docker inspect -f '{{.State.Health.Status}}' "$service" 2>/dev/null || echo "unknown")
    
    if [ "$status" = "healthy" ]; then
      echo "✓ $service is healthy"
      break
    fi
    
    if [ $((attempt % 5)) -eq 0 ]; then
      echo "  Waiting for $service... (attempt $((attempt + 1))/$max_attempts)"
    fi
    
    sleep 1
    attempt=$((attempt + 1))
  done
  
  if [ $attempt -eq $max_attempts ]; then
    echo "✗ $service failed to become healthy"
    docker logs "$service" | tail -20
    exit 1
  fi
done

echo "[3/4] Verifying services..."
docker compose ps

echo "[4/4] Checking API connectivity..."
sleep 3
curl -s http://localhost:8080/health | jq . || { echo "API not responding"; exit 1; }

echo "✓ All services started successfully"
```

### Phase 5: Initial Data Setup (5 minutes)

```bash
#!/bin/bash
# deployment-data-setup.sh

set -e

cd /opt/basset-hound

echo "[1/3] Creating initial project..."
curl -X POST http://localhost:8080/api/v1/projects \
  -H "Content-Type: application/json" \
  -d '{
    "name": "production",
    "description": "Main production project",
    "owner": "admin"
  }' | jq .

echo "[2/3] Seeding default platforms..."
curl -X POST http://localhost:8080/api/v1/platforms/seed \
  -H "Content-Type: application/json" | jq .

echo "[3/3] Verifying data setup..."
curl -s http://localhost:8080/api/v1/projects | jq '.data | length'

echo "✓ Initial data setup complete"
```

### Fresh Deployment Validation Checklist

```bash
#!/bin/bash
# deployment-validate-fresh.sh

set -e

echo "=== Fresh Deployment Validation ==="

# 1. Health checks
echo "✓ Testing health endpoint..."
curl -s http://localhost:8080/health | jq '.status' | grep -q "healthy" || exit 1

# 2. Database connectivity
echo "✓ Testing Neo4j connectivity..."
curl -s http://localhost:8080/health | jq '.services.neo4j.status' | grep -q "connected" || exit 1

# 3. Redis connectivity
echo "✓ Testing Redis connectivity..."
curl -s http://localhost:8080/health | jq '.services.redis.status' | grep -q "connected" || exit 1

# 4. API functionality
echo "✓ Testing API endpoints..."
curl -s http://localhost:8080/api/v1/projects | jq '.data' > /dev/null || exit 1

# 5. Static assets
echo "✓ Testing static assets..."
curl -s http://localhost:8080/static/css/main.css > /dev/null || exit 1

# 6. Documentation
echo "✓ Verifying API docs..."
curl -s http://localhost:8080/docs | grep -q "openapi" || exit 1

# 7. Metrics endpoint
echo "✓ Verifying metrics endpoint..."
curl -s http://localhost:8080/metrics | grep -q "python_" || exit 1

echo "========== All Validations Passed =========="
```

---

## Upgrade from Phase 7

**Use Case**: Existing Phase 7 installation being upgraded to Phase 8.0

**Total Duration**: 45-60 minutes  
**Downtime**: 5-10 minutes (during migration)  
**Data Preservation**: Required (database migration)

### Prerequisites

- Phase 7 system is fully functional
- Database backups created within last 24 hours
- No active investigations in progress (user communication completed)
- Network connectivity verified between environments

### Phase 1: Pre-Upgrade Backup (5 minutes)

```bash
#!/bin/bash
# upgrade-backup-phase7.sh

set -e

echo "[1/3] Creating pre-upgrade backup..."
BACKUP_DIR="/opt/basset-hound/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/neo4j_pre_upgrade_$TIMESTAMP.dump"

mkdir -p "$BACKUP_DIR"

# Stop the application first
echo "Stopping Phase 7 services..."
cd /opt/basset-hound
docker compose down --remove-orphans

# Create database dump
echo "Creating database backup..."
docker exec neo4j_osint_db neo4j-admin database dump neo4j "$BACKUP_FILE" \
  --neo4j-conf=/etc/neo4j/neo4j.conf || {
  echo "Backup failed!"
  exit 1
}

# Compress backup
echo "Compressing backup..."
gzip "$BACKUP_FILE"

echo "[2/3] Backing up configuration files..."
tar -czf "$BACKUP_DIR/config_pre_upgrade_$TIMESTAMP.tar.gz" \
  /opt/basset-hound/.env \
  /opt/basset-hound/docker-compose.yml \
  /opt/basset-hound/nginx/nginx.conf

echo "[3/3] Verifying backups..."
ls -lh "$BACKUP_DIR"/neo4j_pre_upgrade_$TIMESTAMP.dump.gz
ls -lh "$BACKUP_DIR"/config_pre_upgrade_$TIMESTAMP.tar.gz

echo "✓ Pre-upgrade backup complete"
echo "Backup location: $BACKUP_DIR"
```

### Phase 2: Code Update (5 minutes)

```bash
#!/bin/bash
# upgrade-code-update.sh

set -e

cd /opt/basset-hound

echo "[1/4] Fetching latest code..."
git fetch origin main

echo "[2/4] Checking upgrade path..."
git diff $(git merge-base HEAD origin/main) origin/main -- \
  docker-compose.yml \
  Dockerfile \
  api/config.py \
  requirements.txt

echo "Review the differences above and verify they look correct"
read -p "Continue with upgrade? (yes/no) " confirm
if [ "$confirm" != "yes" ]; then
  echo "Upgrade cancelled"
  exit 1
fi

echo "[3/4] Updating to Phase 8..."
git checkout main
git pull origin main

echo "[4/4] Verifying new files..."
required_files=(
  "docker-compose.yml"
  ".env.example"
  "Dockerfile"
  "requirements.txt"
  "api/main.py"
)
for file in "${required_files[@]}"; do
  [ -f "$file" ] || { echo "Missing: $file"; exit 1; }
done

echo "✓ Code update complete"
```

### Phase 3: Environment Configuration Update (5 minutes)

```bash
#!/bin/bash
# upgrade-env-config.sh

set -e

cd /opt/basset-hound

echo "[1/2] Backing up current .env..."
cp .env .env.phase7.backup

echo "[2/2] Merging configuration..."
# Compare .env.example with current .env and identify new variables
echo "New variables in Phase 8:"
diff <(sort .env.phase7.backup | cut -d= -f1) <(sort .env.example | cut -d= -f1) | grep "^>" || true

echo ""
echo "=== Configuration Review Required ==="
echo "Review .env.example for new settings:"
echo "  - New Phase 8 feature flags"
echo "  - Updated service URLs"
echo "  - Modified cache settings"
echo ""
read -p "Edit .env now? (yes/no) " edit_env
if [ "$edit_env" = "yes" ]; then
  nano .env
fi

echo "✓ Environment configuration updated"
```

### Phase 4: Database Migration (5-10 minutes)

```bash
#!/bin/bash
# upgrade-db-migration.sh

set -e

cd /opt/basset-hound

echo "=== Database Migration ==="
echo "WARNING: This process will migrate your Phase 7 database to Phase 8 schema"
echo "Database downtime: 1-2 minutes"
read -p "Continue? (yes/no) " confirm
if [ "$confirm" != "yes" ]; then
  echo "Migration cancelled"
  exit 1
fi

echo "[1/4] Starting Neo4j with new image..."
docker compose up -d neo4j

echo "[2/4] Waiting for Neo4j to initialize..."
sleep 10

echo "[3/4] Running migration scripts..."
docker exec neo4j_osint_db cypher-shell -u neo4j -p neo4jbasset << 'EOF'
-- Phase 8 Schema Updates
-- Add new properties to Entity nodes if not present
MATCH (e:Entity)
WHERE NOT EXISTS(e.phase_8_migrated)
SET e.phase_8_migrated = true
RETURN COUNT(e) as updated_entities;

-- Update indexes (Phase 8 adds new ones)
CREATE INDEX entity_type_idx IF NOT EXISTS FOR (e:Entity) ON (e.entity_type);
CREATE INDEX project_id_idx IF NOT EXISTS FOR (e:Entity) ON (e.project_id);
CREATE INDEX identifier_idx IF NOT EXISTS FOR (d:Data) ON (d.identifier);
CREATE INDEX timestamp_idx IF NOT EXISTS FOR (e:Entity) ON (e.created_at);

-- Seed Platform entities (Phase 8 dynamic platforms feature)
-- These will be created via API on first startup, but we can pre-seed common ones
MERGE (p:Platform {id: "platform_twitter", name: "Twitter"})
SET p.domain = "twitter.com"
MERGE (p:Platform {id: "platform_linkedin", name: "LinkedIn"})
SET p.domain = "linkedin.com"

RETURN "Migration completed" as status;
EOF

echo "[4/4] Verifying migration..."
docker exec neo4j_osint_db cypher-shell -u neo4j -p neo4jbasset \
  "MATCH (e:Entity {phase_8_migrated: true}) RETURN COUNT(e) as migrated_count;"

echo "✓ Database migration complete"
```

### Phase 5: Service Startup (5 minutes)

```bash
#!/bin/bash
# upgrade-services-start.sh

set -e

cd /opt/basset-hound

echo "[1/3] Building new Docker images..."
docker compose build --no-cache

echo "[2/3] Starting all Phase 8 services..."
docker compose up -d

echo "[3/3] Waiting for services to be healthy..."
max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
  api_health=$(curl -s http://localhost:8080/health 2>/dev/null | jq -r '.status // "down"' || echo "down")
  
  if [ "$api_health" = "healthy" ]; then
    echo "✓ API is healthy"
    break
  fi
  
  echo "Attempt $((attempt + 1))/$max_attempts: Waiting for API..."
  sleep 2
  attempt=$((attempt + 1))
done

if [ $attempt -eq $max_attempts ]; then
  echo "✗ API failed to become healthy"
  docker logs basset_api | tail -30
  exit 1
fi

echo "✓ Services started successfully"
```

### Phase 6: Post-Upgrade Validation

```bash
#!/bin/bash
# upgrade-validate.sh

set -e

echo "=== Post-Upgrade Validation ==="

# 1. Health checks
echo "[1/5] Health checks..."
HEALTH=$(curl -s http://localhost:8080/health)
echo "$HEALTH" | jq '.services' | grep -q "connected" || {
  echo "✗ Service connectivity check failed"
  exit 1
}

# 2. Data integrity
echo "[2/5] Data integrity checks..."
PROJECT_COUNT=$(curl -s http://localhost:8080/api/v1/projects | jq '.data | length')
echo "  Projects: $PROJECT_COUNT"

ENTITY_COUNT=$(curl -s http://localhost:8080/health | jq '.metrics.total_entities')
echo "  Entities: $ENTITY_COUNT"

if [ "$ENTITY_COUNT" -eq 0 ] && [ "$PROJECT_COUNT" -eq 0 ]; then
  echo "⚠ WARNING: No data found. Database migration may have failed."
  exit 1
fi

# 3. Version verification
echo "[3/5] Version verification..."
VERSION=$(curl -s http://localhost:8080/api/info | jq -r '.version')
echo "  Running version: $VERSION"

# 4. Feature verification (Phase 8 specific)
echo "[4/5] Phase 8 feature checks..."
curl -s http://localhost:8080/api/v1/platforms | jq '.data | length' > /dev/null && \
  echo "  ✓ Dynamic platforms feature working" || \
  echo "  ✗ Dynamic platforms not available"

# 5. Integration tests
echo "[5/5] Running smoke tests..."
pytest tests/smoke/ -v || {
  echo "⚠ Some smoke tests failed"
  exit 1
}

echo "========== Upgrade Validation Complete =========="
echo "You can now safely close Phase 7 documentation"
```

### Upgrade Rollback (If Needed)

```bash
#!/bin/bash
# upgrade-rollback.sh

set -e

cd /opt/basset-hound

echo "=== Upgrading Rollback Procedure ==="
echo "WARNING: This will revert to Phase 7"

read -p "Continue with rollback? (yes/no) " confirm
if [ "$confirm" != "yes" ]; then
  exit 0
fi

echo "[1/4] Stopping Phase 8 services..."
docker compose down --remove-orphans

echo "[2/4] Restoring Phase 7 code..."
git checkout phase-7-latest
git pull origin phase-7-latest

echo "[3/4] Restoring Phase 7 configuration..."
cp .env.phase7.backup .env

echo "[4/4] Restoring database from backup..."
LATEST_BACKUP=$(ls -t /opt/basset-hound/backups/neo4j_pre_upgrade_*.dump.gz | head -1)
echo "Using backup: $LATEST_BACKUP"

docker compose up -d neo4j
sleep 10

gunzip -c "$LATEST_BACKUP" > /tmp/neo4j_restore.dump
docker exec neo4j_osint_db neo4j-admin database load neo4j /tmp/neo4j_restore.dump

echo "[5/4] Starting Phase 7 services..."
docker compose up -d

echo "✓ Rollback complete. Phase 7 services are running."
```

---

## Staged Rollout

**Use Case**: Multi-region or gradual deployment strategy

**Total Duration**: 2-3 hours (across all regions)  
**Downtime**: 0 minutes (canary deployment)  
**Risk**: Low (progressive validation)

### Deployment Strategy

```
Timeline:
├─ 0:00 - 0:30: Region A deployment (canary - 10% traffic)
├─ 0:30 - 1:00: Validation & monitoring (Region A)
├─ 1:00 - 1:30: Region B deployment (20% traffic)
├─ 1:30 - 2:00: Region C deployment (70% traffic)
└─ 2:00 - 2:30: Full validation & rollback plan deactivation
```

### Phase 1: Canary Deployment (Region A)

```bash
#!/bin/bash
# rollout-canary-region-a.sh

set -e

REGION="us-east-1"
TRAFFIC_WEIGHT=10
DEPLOYMENT_ID=$(date +%s)

echo "=== Canary Deployment: Region A ($REGION) ==="
echo "Traffic Weight: $TRAFFIC_WEIGHT%"
echo "Deployment ID: $DEPLOYMENT_ID"

cd /opt/basset-hound-${REGION}

echo "[1/4] Creating deployment snapshot..."
git checkout main && git pull origin main
git tag "rollout-$DEPLOYMENT_ID-start"

echo "[2/4] Building new image..."
docker compose build --no-cache --tag basset-api:$DEPLOYMENT_ID

echo "[3/4] Starting canary deployment..."
# Update load balancer to send 10% traffic to new version
docker compose up -d basset_api

echo "[4/4] Waiting for service readiness..."
sleep 10

# Health checks
for i in {1..30}; do
  health=$(curl -s http://localhost:8080/health | jq -r '.status // "down"')
  if [ "$health" = "healthy" ]; then
    echo "✓ Canary deployment healthy"
    break
  fi
  echo "Attempt $i/30: Waiting..."
  sleep 2
done

echo "✓ Canary deployment complete"
echo "Monitor logs with: docker compose logs -f basset_api"
```

### Phase 2: Canary Monitoring (30 minutes)

```bash
#!/bin/bash
# rollout-monitor-canary.sh

set -e

echo "=== Canary Monitoring (30 minutes) ==="
echo "Checking for errors, latency increases, and memory leaks"

MONITOR_INTERVAL=30  # Check every 30 seconds
TOTAL_DURATION=$((30 * 60))  # 30 minutes in seconds
elapsed=0

while [ $elapsed -lt $TOTAL_DURATION ]; do
  echo ""
  echo "=== Monitoring checkpoint ($(($elapsed / 60))m elapsed) ==="
  
  # Error rate check
  ERROR_RATE=$(curl -s http://localhost:8080/metrics | \
    grep 'basset_request_count{.*status="5' | \
    grep -oE '[0-9]+\.[0-9]+' | head -1 || echo "0")
  echo "Error rate: $ERROR_RATE"
  
  # Latency check (p99)
  LATENCY_P99=$(curl -s http://localhost:8080/metrics | \
    grep 'basset_request_latency_seconds{quantile="0.99' | \
    grep -oE '[0-9]+\.[0-9]+' || echo "0")
  echo "Latency p99: ${LATENCY_P99}s"
  
  # Memory check
  MEMORY_USAGE=$(docker stats --no-stream basset_api | tail -1 | awk '{print $6}')
  echo "Memory usage: $MEMORY_USAGE"
  
  # Check for thresholds
  if (( $(echo "$ERROR_RATE > 0.05" | bc -l) )); then
    echo "⚠ WARNING: Error rate above 5%!"
    echo "Recommend: Check logs and consider rollback"
  fi
  
  if (( $(echo "$LATENCY_P99 > 0.5" | bc -l) )); then
    echo "⚠ WARNING: Latency spike detected!"
  fi
  
  sleep $MONITOR_INTERVAL
  elapsed=$((elapsed + MONITOR_INTERVAL))
done

echo ""
echo "✓ Canary monitoring complete"
echo "If any warnings were raised, review before proceeding to Phase 2"
```

### Phase 3: Progressive Rollout

```bash
#!/bin/bash
# rollout-progressive-regions.sh

set -e

DEPLOYMENT_ID=$1
if [ -z "$DEPLOYMENT_ID" ]; then
  DEPLOYMENT_ID=$(date +%s)
fi

echo "=== Progressive Rollout ==="
echo "Deployment ID: $DEPLOYMENT_ID"

# Define regions and their traffic weights
regions=(
  "us-west-2:30"
  "eu-central-1:40"
  "ap-northeast-1:30"
)

for region_config in "${regions[@]}"; do
  IFS=':' read -r region weight <<< "$region_config"
  
  echo ""
  echo "Deploying to: $region (traffic: $weight%)"
  
  cd /opt/basset-hound-${region}
  
  # Update to latest code
  git pull origin main
  
  # Build image
  docker compose build --no-cache
  
  # Deploy
  docker compose up -d
  
  # Wait for health
  echo "Waiting for $region to be healthy..."
  for i in {1..30}; do
    health=$(curl -s http://localhost:8080/health 2>/dev/null | jq -r '.status // "down"' || echo "down")
    if [ "$health" = "healthy" ]; then
      echo "✓ $region is healthy"
      break
    fi
    sleep 2
  done
  
  # Update load balancer traffic weight
  echo "Updating load balancer: $region=$weight%"
  # Example for AWS ELB/ALB:
  # aws elbv2 modify-target-group-attributes \
  #   --target-group-arn arn:aws:... \
  #   --attributes Key=deregistration_delay.timeout_seconds,Value=30
  
  sleep 60  # Wait before next region
done

echo "✓ Progressive rollout complete"
```

### Phase 4: Full Rollout Validation

```bash
#!/bin/bash
# rollout-validate-full.sh

set -e

echo "=== Full Rollout Validation ==="

regions=("us-east-1" "us-west-2" "eu-central-1" "ap-northeast-1")

for region in "${regions[@]}"; do
  echo ""
  echo "Validating: $region"
  
  cd /opt/basset-hound-${region}
  
  # Health check
  health=$(curl -s http://localhost:8080/health | jq -r '.status')
  echo "  Status: $health"
  
  # Data consistency check
  project_count=$(curl -s http://localhost:8080/api/v1/projects | jq '.data | length')
  entity_count=$(curl -s http://localhost:8080/health | jq '.metrics.total_entities')
  echo "  Projects: $project_count, Entities: $entity_count"
  
  # Performance check
  latency=$(curl -s http://localhost:8080/metrics | grep 'basset_request_latency_seconds{quantile="0.99' | grep -oE '[0-9]+\.[0-9]+' || echo "0")
  echo "  Latency p99: ${latency}s"
  
  if [ "$health" != "healthy" ]; then
    echo "✗ Region $region unhealthy!"
    exit 1
  fi
done

echo ""
echo "✓ All regions validated successfully"
echo "Deployment complete - removing rollback plan"
```

---

## Emergency Hotfix

**Use Case**: Critical bug fix requiring immediate production deployment

**Total Duration**: 10-15 minutes  
**Downtime**: 1-2 minutes (API restart only)  
**Risk**: High (minimal testing window)

### Quick Decision Matrix

```
Hotfix candidate if:
✓ Critical bug affecting core functionality
✓ Security vulnerability discovered
✓ Data corruption risk
✓ Service unavailability

NOT a hotfix candidate if:
✗ Feature enhancement
✗ UI/UX improvements
✗ Non-critical bug
✗ Performance optimization
→ Wait for normal release cycle
```

### Hotfix Deployment Procedure

```bash
#!/bin/bash
# hotfix-emergency-deploy.sh

set -e

echo "=== EMERGENCY HOTFIX DEPLOYMENT ==="
echo "WARNING: Minimal testing. Production will go offline for 1-2 minutes."
echo ""

# Critical pre-flight checks
echo "[PRE-FLIGHT CHECKS]"
read -p "Has this fix been reviewed by at least one engineer? (yes/no) " review
[ "$review" = "yes" ] || { echo "Hotfix deployment aborted"; exit 1; }

read -p "Have backups been created in last 4 hours? (yes/no) " backup
[ "$backup" = "yes" ] || { echo "Create backup first with: ./backup.sh"; exit 1; }

read -p "Is the fix code already merged to main branch? (yes/no) " merged
[ "$merged" = "yes" ] || { echo "Merge to main branch first"; exit 1; }

HOTFIX_ID="hotfix-$(date +%Y%m%d-%H%M%S)"
echo "Hotfix ID: $HOTFIX_ID"

cd /opt/basset-hound

# 1. Quick code update (no git history review)
echo "[1/5] Pulling hotfix code..."
git fetch origin main
git reset --hard origin/main

# 2. Quick validation
echo "[2/5] Quick validation..."
# Syntax check on modified Python files
python -m py_compile api/main.py || {
  echo "Syntax error in hotfix code!"
  exit 1
}

# 3. Health check before deployment
echo "[3/5] Health check (pre-deployment)..."
PRE_HEALTH=$(curl -s http://localhost:8080/health | jq '.services')
echo "$PRE_HEALTH"

# 4. Minimal downtime update
echo "[4/5] Deploying hotfix (downtime: 1-2 minutes)..."
docker compose down
docker compose pull
docker compose up -d

# 5. Verify recovery
echo "[5/5] Verifying recovery..."
max_attempts=20
for i in {1..20}; do
  health=$(curl -s http://localhost:8080/health 2>/dev/null | jq -r '.status // "down"' || echo "down")
  if [ "$health" = "healthy" ]; then
    echo "✓ API recovered"
    break
  fi
  
  echo "Attempt $i/20: Waiting for recovery..."
  sleep 3
done

if [ "$health" != "healthy" ]; then
  echo "✗ CRITICAL: Hotfix deployment failed!"
  echo "Initiating automatic rollback..."
  # Rollback procedure
  git checkout main~1
  docker compose down
  docker compose up -d
  
  echo "System reverted to previous version"
  echo "ALERT: Investigate hotfix code before next attempt"
  exit 1
fi

# Post-deployment
echo ""
echo "✓✓✓ HOTFIX DEPLOYED SUCCESSFULLY ✓✓✓"
echo "Hotfix ID: $HOTFIX_ID"
echo "Downtime window: 1-2 minutes"
echo ""
echo "NEXT STEPS:"
echo "1. Notify stakeholders of deployment completion"
echo "2. Monitor error logs for next 30 minutes"
echo "3. Run full test suite when stable"
```

### Post-Hotfix Procedure (within 30 minutes)

```bash
#!/bin/bash
# hotfix-post-deploy.sh

set -e

echo "=== Post-Hotfix Verification ==="

# 1. Monitor for 30 minutes
echo "[1/3] Monitoring error logs..."
docker compose logs --since 5m basset_api | grep -i "error\|exception" | head -20 || echo "No errors detected"

# 2. Run smoke tests
echo "[2/3] Running smoke tests..."
pytest tests/smoke/ -v --tb=short || {
  echo "Smoke tests failed!"
  echo "Consider rolling back if tests were passing before"
}

# 3. Database integrity check
echo "[3/3] Checking database integrity..."
curl -s http://localhost:8080/health | jq '.metrics'

echo "✓ Post-hotfix verification complete"
echo "Status: READY FOR MONITORING"
```

---

## Post-Deployment Validation

**Duration**: 1 hour  
**Objective**: Verify production readiness and system stability

### 1. Health Checks (5 minutes)

```bash
#!/bin/bash
# post-deploy-health.sh

set -e

echo "=== POST-DEPLOYMENT HEALTH CHECKS ==="

# 1. API health endpoint
echo "[1/6] API Health..."
HEALTH=$(curl -s http://localhost:8080/health)
echo "$HEALTH" | jq .

# Expected output
required_fields=("status" "version" "services" "metrics" "uptime_seconds")
for field in "${required_fields[@]}"; do
  echo "$HEALTH" | jq ".$field" > /dev/null || {
    echo "✗ Missing field: $field"
    exit 1
  }
done

# 2. Service connectivity
echo "[2/6] Service Connectivity..."
NEO4J=$(curl -s http://localhost:8080/health | jq '.services.neo4j.status')
REDIS=$(curl -s http://localhost:8080/health | jq '.services.redis.status')
CELERY=$(curl -s http://localhost:8080/health | jq '.services.celery.status')

echo "  Neo4j: $NEO4J"
echo "  Redis: $REDIS"
echo "  Celery: $CELERY"

if [ "$NEO4J" != '"connected"' ] || [ "$REDIS" != '"connected"' ]; then
  echo "✗ Service connectivity check failed"
  exit 1
fi

# 3. Database health
echo "[3/6] Database Health..."
curl -s http://localhost:8080/api/v1/projects | jq '.meta' || exit 1

# 4. Performance baseline
echo "[4/6] Performance Baseline..."
echo "  Collecting 10 sample requests..."
for i in {1..10}; do
  curl -s -w "%{time_total}\n" -o /dev/null http://localhost:8080/api/v1/projects
done

# 5. Memory usage
echo "[5/6] Memory Usage..."
docker stats --no-stream | grep -E "basset|neo4j|redis"

# 6. Disk usage
echo "[6/6] Disk Usage..."
df -h /opt/basset-hound

echo ""
echo "✓ All health checks passed"
```

### 2. Smoke Tests (10 minutes)

```bash
#!/bin/bash
# post-deploy-smoke-tests.sh

set -e

echo "=== SMOKE TESTS ==="

# Test 1: Create project
echo "[1/8] Create project..."
PROJ=$(curl -s -X POST http://localhost:8080/api/v1/projects \
  -H "Content-Type: application/json" \
  -d '{"name":"smoke-test-'$(date +%s)'","description":"Smoke test"}' | jq -r '.data.id')
echo "  Created: $PROJ"

# Test 2: Create entity
echo "[2/8] Create entity..."
ENT=$(curl -s -X POST http://localhost:8080/api/v1/projects/$PROJ/entities \
  -H "Content-Type: application/json" \
  -d '{"entity_type":"Person","data":{"name":"Test User"}}' | jq -r '.data.id')
echo "  Created: $ENT"

# Test 3: Query entity
echo "[3/8] Query entity..."
curl -s http://localhost:8080/api/v1/projects/$PROJ/entities/$ENT | jq '.data.entity_type'

# Test 4: Create relationship
echo "[4/8] Create relationship..."
REL=$(curl -s -X POST http://localhost:8080/api/v1/projects/$PROJ/relationships \
  -H "Content-Type: application/json" \
  -d '{
    "from_entity_id":"'$ENT'",
    "to_entity_id":"'$ENT'",
    "relationship_type":"KNOWS",
    "properties":{}
  }' | jq -r '.data.id')
echo "  Created: $REL"

# Test 5: Search
echo "[5/8] Full-text search..."
curl -s 'http://localhost:8080/api/v1/search/full-text?q=Test' | jq '.meta.total'

# Test 6: Export
echo "[6/8] Export data..."
curl -s -X POST http://localhost:8080/api/v1/projects/$PROJ/export/csv | head -c 100
echo ""

# Test 7: Cache effectiveness
echo "[7/8] Cache effectiveness..."
# First request (cache miss)
FIRST=$(curl -s -w "%{time_total}" -o /dev/null http://localhost:8080/api/v1/projects)
# Second request (cache hit)
SECOND=$(curl -s -w "%{time_total}" -o /dev/null http://localhost:8080/api/v1/projects)
echo "  First request: ${FIRST}s (cache miss)"
echo "  Second request: ${SECOND}s (cache hit)"

# Test 8: WebSocket connectivity
echo "[8/8] WebSocket connectivity..."
# This requires websocat or similar tool, simplified check:
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" \
  http://localhost:8080/ws/suggestions/$PROJ 2>/dev/null | grep -q "101" && \
  echo "  ✓ WebSocket ready" || \
  echo "  ⚠ WebSocket may require additional setup"

echo ""
echo "✓ Smoke tests complete"
```

### 3. Log Monitoring (15 minutes)

```bash
#!/bin/bash
# post-deploy-log-monitor.sh

set -e

echo "=== LOG MONITORING (15 minutes) ==="

# Monitor for errors
start_time=$(date -u -d '15 minutes ago' +%Y-%m-%dT%H:%M:%S)

echo "Checking for errors since $start_time..."

echo ""
echo "[1/3] API errors..."
docker compose logs --since 15m basset_api | grep -i "error\|critical" | head -10 || echo "  No errors found"

echo ""
echo "[2/3] Neo4j warnings..."
docker compose logs --since 15m neo4j | grep -i "warn" | head -10 || echo "  No warnings found"

echo ""
echo "[3/3] Redis issues..."
docker compose logs --since 15m redis | grep -i "error" | head -10 || echo "  No issues found"

echo ""
echo "✓ Log monitoring complete"
```

### 4. Alert Verification (15 minutes)

```bash
#!/bin/bash
# post-deploy-alerts.sh

set -e

echo "=== ALERT VERIFICATION ==="

# Check Prometheus alerts
echo "[1/3] Prometheus alerts..."
curl -s http://localhost:9090/api/v1/alerts 2>/dev/null | jq '.data.alerts[0:5]' || \
  echo "  Prometheus not available"

# Check Grafana dashboards
echo "[2/3] Grafana dashboards..."
echo "  Access at: http://localhost:3000"
echo "  Check dashboards:"
echo "    - System Overview"
echo "    - API Performance"
echo "    - Database Performance"
echo "    - Error Tracking"

# Manual verification checklist
echo "[3/3] Manual verification..."
echo "  ☐ CPU usage < 70%"
echo "  ☐ Memory usage < 80%"
echo "  ☐ Disk usage < 80%"
echo "  ☐ Network latency < 10ms (internal)"
echo "  ☐ API response time < 200ms p99"

echo ""
echo "✓ Alert verification complete"
```

### 5. Performance Monitoring (15 minutes)

```bash
#!/bin/bash
# post-deploy-performance.sh

set -e

echo "=== PERFORMANCE MONITORING (15 minutes) ==="

echo "[1/4] Baseline metrics..."
curl -s http://localhost:8080/metrics | grep "basset_" | head -20

echo ""
echo "[2/4] Query latency..."
for i in {1..5}; do
  curl -s -w "Request $i latency: %{time_total}s\n" -o /dev/null \
    'http://localhost:8080/api/v1/search/full-text?q=test'
done

echo ""
echo "[3/4] Cache hit rate..."
curl -s http://localhost:8080/api/v1/cache/hit-rate 2>/dev/null || \
  echo "  Cache endpoint not available"

echo ""
echo "[4/4] Current resource usage..."
docker stats --no-stream | grep -E "basset|neo4j|redis"

echo ""
echo "✓ Performance monitoring complete"
```

### 6. User Acceptance Test (10 minutes)

```bash
#!/bin/bash
# post-deploy-uat.sh

set -e

echo "=== USER ACCEPTANCE TEST ==="
echo "This should be done with actual users/stakeholders"

echo ""
echo "Test Scenarios:"
echo ""
echo "[1] Create and manage a project"
echo "    a. Create new project"
echo "    b. Verify project appears in list"
echo "    c. Access project detail page"
echo "    Result: [ ] PASS [ ] FAIL"

echo ""
echo "[2] Entity management"
echo "    a. Add entity (person)"
echo "    b. Edit entity properties"
echo "    c. Delete entity"
echo "    d. Verify changes reflected"
echo "    Result: [ ] PASS [ ] FAIL"

echo ""
echo "[3] Relationships"
echo "    a. Create relationship between entities"
echo "    b. Visualize relationship graph"
echo "    c. Query relationships"
echo "    Result: [ ] PASS [ ] FAIL"

echo ""
echo "[4] Search functionality"
echo "    a. Full-text search"
echo "    b. Advanced search with filters"
echo "    c. Save search for later"
echo "    Result: [ ] PASS [ ] FAIL"

echo ""
echo "[5] Data export"
echo "    a. Export as CSV"
echo "    b. Export as JSON"
echo "    c. Export as PDF report"
echo "    Result: [ ] PASS [ ] FAIL"

echo ""
echo "Overall UAT Result: [ ] PASS [ ] FAIL"
```

### Post-Deployment Success Criteria

```
✓ All systems operational (health checks pass)
✓ No critical errors in logs
✓ Performance within SLA (latency p99 < 200ms)
✓ Cache hit rate > 50%
✓ Smoke tests pass
✓ Alerts configured and working
✓ User acceptance tests pass
✓ Data integrity verified
```

---

## Rollback Procedures

### Deciding When to Rollback

**Immediate Rollback Required If:**
- API down for > 2 minutes
- Data corruption detected
- Security breach discovered
- Core functionality broken
- Database migration failed

**Escalation Procedure:**
```
1. Declare P1 incident
2. Notify on-call manager
3. Execute rollback decision
4. Post-rollback analysis
5. Root cause investigation
```

### Quick Rollback (API Code Only)

```bash
#!/bin/bash
# rollback-quick.sh

set -e

echo "=== QUICK ROLLBACK ==="
echo "Rolling back API code to previous version"

cd /opt/basset-hound

# Get previous version tag
PREVIOUS_TAG=$(git describe --tags --abbrev=0 HEAD~1)
echo "Rolling back to: $PREVIOUS_TAG"

read -p "Confirm rollback? (yes/no) " confirm
[ "$confirm" = "yes" ] || { echo "Rollback cancelled"; exit 0; }

echo "[1/3] Stopping services..."
docker compose down

echo "[2/3] Reverting code..."
git checkout $PREVIOUS_TAG

echo "[3/3] Starting previous version..."
docker compose up -d

echo "✓ Rollback complete"
echo "Verify with: curl http://localhost:8080/health"
```

### Full Rollback (Database + Code)

```bash
#!/bin/bash
# rollback-full.sh

set -e

echo "=== FULL ROLLBACK ==="
echo "WARNING: This will revert database to backup"
echo "Data changes since backup will be lost"

cd /opt/basset-hound

read -p "Confirm full rollback? (yes/no) " confirm
[ "$confirm" = "yes" ] || { echo "Rollback cancelled"; exit 0; }

# Find most recent backup
BACKUP=$(ls -t /opt/basset-hound/backups/neo4j_*.dump.gz | head -1)
echo "Using backup: $BACKUP"

echo "[1/4] Stopping services..."
docker compose down -v  # Remove volumes

echo "[2/4] Restoring database..."
docker compose up -d neo4j
sleep 15

gunzip -c "$BACKUP" > /tmp/restore.dump
docker exec neo4j_osint_db neo4j-admin database load neo4j /tmp/restore.dump

echo "[3/4] Reverting application code..."
git checkout stable-release

echo "[4/4] Starting services..."
docker compose up -d

echo ""
echo "✓ Full rollback complete"
echo "Investigating cause before re-deployment"
```

### Rollback Validation

```bash
#!/bin/bash
# rollback-validate.sh

set -e

echo "=== ROLLBACK VALIDATION ==="

echo "[1/4] Health check..."
curl -s http://localhost:8080/health | jq '.status' | grep -q healthy || exit 1

echo "[2/4] Data integrity..."
curl -s http://localhost:8080/health | jq '.metrics'

echo "[3/4] Service connectivity..."
curl -s http://localhost:8080/health | jq '.services'

echo "[4/4] Basic functionality..."
curl -s http://localhost:8080/api/v1/projects | jq '.data | length'

echo ""
echo "✓ Rollback validation complete - system stable"
```

---

## Real-World Scenarios & Troubleshooting

### Scenario 1: Network Latency Issues

**Problem**: API responses slow, but system appears healthy

**Symptoms**:
- Request latency > 500ms
- Timeouts connecting to Neo4j
- Redis connection pooling issues

**Diagnosis**:

```bash
#!/bin/bash
# diagnose-network-latency.sh

echo "=== Network Latency Diagnosis ==="

# 1. Check container network
echo "[1/5] Docker network health..."
docker exec basset_api ping -c 3 neo4j_osint_db

# 2. Check DNS resolution
echo "[2/5] DNS resolution..."
docker exec basset_api nslookup neo4j_osint_db
docker exec basset_api nslookup redis

# 3. Check network interface
echo "[3/5] Network interface stats..."
docker stats --no-stream | grep -E "basset|neo4j|redis"

# 4. Check connection pools
echo "[4/5] Neo4j connection pool..."
curl -s http://localhost:8080/metrics | grep "neo4j.*connection"

# 5. Check load on services
echo "[5/5] Service load..."
docker top basset_api | tail -5
docker top neo4j_osint_db | tail -5
```

**Solutions**:

```bash
# Solution 1: Restart services in dependency order
docker compose stop basset_api redis neo4j
sleep 5
docker compose start neo4j
sleep 10
docker compose start redis
sleep 5
docker compose start basset_api

# Solution 2: Check and clear network bottlenecks
docker network inspect basset-hound

# Solution 3: Increase connection pool size
# In .env:
REDIS_CONNECTION_POOL_SIZE=50
NEO4J_CONNECTION_POOL_SIZE=100

# Solution 4: Rebuild network stack (nuclear option)
docker network rm basset-hound
docker compose down
docker compose up -d
```

### Scenario 2: Database Lock Issues

**Problem**: Database operations hang or timeout

**Symptoms**:
- "Lock timeout" errors in logs
- API requests timeout
- Database CPU at 100%

**Diagnosis**:

```bash
#!/bin/bash
# diagnose-db-locks.sh

echo "=== Database Lock Diagnosis ==="

# 1. Check active transactions
echo "[1/4] Active transactions..."
docker exec neo4j_osint_db cypher-shell -u neo4j -p neo4jbasset \
  "CALL dbms.listQueries() YIELD query, elapsedMillis, username RETURN query, elapsedMillis, username LIMIT 10;"

# 2. Check lock wait times
echo "[2/4] Lock wait analysis..."
docker exec neo4j_osint_db cypher-shell -u neo4j -p neo4jbasset \
  "MATCH (n) WHERE NOT EXISTS(n.locked_by) RETURN COUNT(n) as unlocked_nodes, COUNT(DISTINCT n) as total_nodes LIMIT 1;"

# 3. Check database size
echo "[3/4] Database statistics..."
docker exec neo4j_osint_db cypher-shell -u neo4j -p neo4jbasset \
  "CALL db.stats.retrieve('graph') YIELD section, key, value WHERE section='counts' RETURN key, value;"

# 4. Check for long-running queries
echo "[4/4] Long-running queries..."
docker exec neo4j_osint_db cypher-shell -u neo4j -p neo4jbasset \
  "CALL dbms.listQueries() YIELD query, elapsedMillis WHERE elapsedMillis > 30000 RETURN query, elapsedMillis;"
```

**Solutions**:

```bash
# Solution 1: Kill long-running queries
docker exec neo4j_osint_db cypher-shell -u neo4j -p neo4jbasset \
  "CALL dbms.killQuery('query-id-here');"

# Solution 2: Increase transaction timeout
# In docker-compose.yml:
environment:
  - NEO4J_transactions_memory_pageCache_warmupEnable=true
  - NEO4J_dbms_transaction_timeout=60s

# Solution 3: Restart Neo4j (if locks are stuck)
docker compose restart neo4j

# Solution 4: Check and optimize queries
# Enable slow query log:
docker exec neo4j_osint_db cypher-shell -u neo4j -p neo4jbasset \
  "CALL dbms.setConfigValue('dbms.logs.query.enabled', 'true');"
```

### Scenario 3: Cache Coherency Issues

**Problem**: Stale data in cache, users see old information

**Symptoms**:
- Different results for same query on refresh
- Cache hit rate dropping
- Memory usage growing

**Diagnosis**:

```bash
#!/bin/bash
# diagnose-cache-issues.sh

echo "=== Cache Coherency Diagnosis ==="

# 1. Check Redis memory
echo "[1/5] Redis memory..."
docker exec basset_redis redis-cli INFO memory

# 2. Check cache hit rate
echo "[2/5] Cache hit rate..."
curl -s http://localhost:8080/api/v1/cache/hit-rate | jq .

# 3. Check stale keys
echo "[3/5] Cache keys by age..."
docker exec basset_redis redis-cli --scan --pattern "*" | head -20

# 4. Check eviction policy
echo "[4/5] Redis eviction policy..."
docker exec basset_redis redis-cli CONFIG GET maxmemory-policy

# 5. Test cache invalidation
echo "[5/5] Cache invalidation test..."
# Request twice, check if results differ
curl -s http://localhost:8080/api/v1/projects | jq -r '.data[0].id' > /tmp/cache_test1
sleep 1
curl -s http://localhost:8080/api/v1/projects | jq -r '.data[0].id' > /tmp/cache_test2
diff /tmp/cache_test1 /tmp/cache_test2 && echo "Consistent" || echo "Inconsistent!"
```

**Solutions**:

```bash
# Solution 1: Clear cache
curl -X POST http://localhost:8080/api/v1/cache/clear

# Solution 2: Adjust TTL settings
# In .env:
CACHE_DEFAULT_TTL=300  # 5 minutes
CACHE_LIST_TTL=600     # 10 minutes for lists
CACHE_SEARCH_TTL=60    # 1 minute for search

# Solution 3: Increase Redis memory
# In docker-compose.yml:
command: redis-server --appendonly yes --maxmemory 512mb

# Solution 4: Restart Redis
docker compose restart redis

# Solution 4: Implement cache versioning
# Add version field to cache keys to force invalidation
```

### Scenario 4: Load Spike Handling

**Problem**: Sudden traffic increase causes slowdown or outages

**Symptoms**:
- High CPU/memory usage
- Request timeouts
- Error rates increasing

**Detection**:

```bash
#!/bin/bash
# detect-load-spike.sh

echo "=== Load Spike Detection ==="

# Get baseline (from previous hour)
BASELINE=$(curl -s http://localhost:8080/metrics | grep 'basset_request_count_total' | head -1 | grep -oE '[0-9]+$')

# Get current (last 5 minutes)
CURRENT=$(curl -s http://localhost:8080/metrics | grep 'basset_request_count_total' | head -1 | grep -oE '[0-9]+$')

SPIKE_RATIO=$(echo "scale=2; $CURRENT / $BASELINE" | bc)

echo "Baseline requests: $BASELINE"
echo "Current requests: $CURRENT"
echo "Spike ratio: ${SPIKE_RATIO}x"

if (( $(echo "$SPIKE_RATIO > 2" | bc -l) )); then
  echo "⚠ LOAD SPIKE DETECTED!"
  echo "Triggering auto-scaling..."
fi
```

**Mitigation**:

```bash
#!/bin/bash
# mitigate-load-spike.sh

echo "=== Load Spike Mitigation ==="

# 1. Scale API servers
echo "[1/4] Scaling API instances..."
docker compose up -d --scale basset_api=3

# 2. Enable aggressive caching
echo "[2/4] Enabling aggressive caching..."
docker exec basset_api curl -X POST http://localhost:8000/cache/warm

# 3. Increase connection pools
echo "[3/4] Increasing connection pools..."
docker exec basset_redis redis-cli CONFIG SET maxmemory 1gb

# 4. Rate limiting (if needed)
echo "[4/4] Enabling rate limiting..."
# Update nginx.conf to add rate limiting:
# limit_req_zone $binary_remote_addr zone=api:10m rate=100r/s;
# limit_req zone=api burst=200 nodelay;

# 5. Monitor recovery
echo "Monitoring recovery..."
for i in {1..60}; do
  CPU=$(docker stats --no-stream | grep basset_api | awk '{print $3}')
  echo "CPU: $CPU (attempt $i/60)"
  sleep 2
done
```

### Scenario 5: Emergency Situation Response

**Problem**: Multiple failures cascading

**Action Plan**:

```bash
#!/bin/bash
# emergency-response.sh

set -e

echo "=== EMERGENCY RESPONSE ==="
echo "Time: $(date)"
echo "Severity: P1 - CRITICAL"

# 1. Declare incident
echo "[1/5] Declaring P1 incident..."
echo "INCIDENT: Basset Hound production outage"
echo "SEVERITY: P1"
echo "STATUS: IN PROGRESS"
echo "TEAM: On-call (notify: ops@example.com)"

# 2. Assess situation
echo "[2/5] Assessing situation..."
HEALTH=$(curl -s http://localhost:8080/health 2>/dev/null || echo '{"status":"down"}')
echo "API Status: $(echo "$HEALTH" | jq -r '.status // "down"')"
docker compose ps

# 3. Immediate mitigation
echo "[3/5] Immediate mitigation..."
echo "  Option A: Restart all services"
echo "  Option B: Full rollback"
echo "  Option C: Circuit breaker (disable problematic feature)"
read -p "Select option (A/B/C): " mitigation

case $mitigation in
  A)
    docker compose restart
    ;;
  B)
    bash rollback-quick.sh
    ;;
  C)
    echo "Disabling optional features..."
    docker exec basset_api curl -X POST http://localhost:8000/features/disable/ml_analytics
    ;;
esac

# 4. Verify recovery
echo "[4/5] Verifying recovery..."
sleep 10
curl -s http://localhost:8080/health | jq . || exit 1

# 5. Post-incident
echo "[5/5] Post-incident..."
echo "  ✓ Document what happened"
echo "  ✓ Create incident report"
echo "  ✓ Schedule postmortem"
echo "  ✓ Update runbook"

echo ""
echo "✓ Emergency response complete"
```

---

## Communication Templates

### Pre-Deployment Notification

```
Subject: [SCHEDULED] Basset Hound Maintenance - 2026-05-XX 14:00 UTC

Dear Stakeholders,

We are performing scheduled maintenance on Basset Hound (OSINT Platform).

**Timing**: May XX, 2:00 PM - 4:00 PM UTC
**Duration**: 2 hours estimated
**Downtime**: 5-10 minutes expected
**Impact**: Service may be unavailable during upgrade window

**What's Being Updated**:
- Performance optimization (40%+ faster queries)
- Dynamic platform entity architecture
- Enhanced search functionality
- Cache layer improvements

**What You Should Do**:
- Save any open investigations before 1:50 PM UTC
- Plan to avoid critical work during 2:00-2:15 PM UTC window
- Expect service to be fully operational by 2:15 PM UTC
- Report any issues to ops-team@example.com

**Questions?** Contact operations team 1 hour before maintenance.

Thank you,
Operations Team
```

### Deployment Started

```
Subject: [DEPLOYMENT] Basset Hound v2.0.0 - Deployment Started

Deployment Start Time: 2026-05-19 14:00:00 UTC
Expected Completion: 2026-05-19 14:15:00 UTC
Status: IN PROGRESS

Phase 1: Code deployment - ✓ Complete (14:00)
Phase 2: Database migration - ⟳ In progress (14:05)
Phase 3: Service startup - ⏳ Pending
Phase 4: Validation - ⏳ Pending

Current downtime: 5 minutes
Estimated downtime until recovery: 10 minutes

Will provide update every 5 minutes.
```

### Deployment Complete

```
Subject: [SUCCESS] Basset Hound v2.0.0 Deployment Complete

Deployment Completion Time: 2026-05-19 14:12:00 UTC
Total Downtime: 10 minutes
Status: SUCCESSFUL

Summary:
✓ All 8 backend streams deployed
✓ Database migrated successfully
✓ 100% of entities preserved
✓ All services healthy and responsive
✓ Performance: 40% improvement in query latency

Metrics:
- API latency p99: 45ms (was 75ms)
- Cache hit rate: 68% (was 55%)
- Throughput: 2,500 req/s

Next Steps:
- UAT team should verify key workflows
- Monitor error rates for 30 minutes
- Report any issues immediately

Thank you for your patience,
Operations Team
```

### Deployment Failed - Rollback

```
Subject: [ALERT] Basset Hound Deployment Failed - Initiating Rollback

Deployment Status: FAILED at 14:08 UTC
Rollback Status: IN PROGRESS

Reason for Failure:
Database migration failed due to [specific issue]
New version has been rolled back to Phase 7.x

Current Status:
✓ Rollback initiated (14:10 UTC)
✓ Previous version restored
⟳ Service recovery in progress
⏳ UAT validation pending

Timeline:
- 14:08: Failure detected
- 14:10: Rollback initiated
- 14:12: Estimated recovery complete
- 14:15: Service should be fully available

Impact:
- All Phase 8 features temporarily unavailable
- v2.0.0 deployment cancelled
- Schedule new deployment after investigation

Investigation:
Root cause analysis in progress. Full report by EOD.

Operations Team
```

### Status Update Template

```
=== DEPLOYMENT STATUS UPDATE ===

Time: 2026-05-19 14:XX:XX UTC
Deployment ID: deploy-20260519-1400

Current Phase: [Phase Name]
Progress: [X/Y steps complete]

Metrics:
  - Services healthy: [X/Y]
  - Error rate: X%
  - API latency p99: XXms
  - Downtime elapsed: XX minutes

Status Indicators:
  ☐ Database healthy
  ☐ API responding
  ☐ Cache functional
  ☐ External services connected

Next Actions:
  [List of next steps]

Issues:
  [Any problems encountered and mitigation]

ETA to Completion: [Time]
Contact: [Ops team contact]
```

---

## Runbook Maintenance

### Version Control

```
Version History:

v1.0.0 (2026-05-19) - Initial comprehensive runbook
  - Fresh deployment procedure
  - Phase 7 upgrade procedure
  - Staged rollout procedure
  - Emergency hotfix procedure
  - Real-world scenarios
  - Communication templates

v1.1.0 (TBD) - Updates based on real deployments
  - Lessons learned from production
  - Timing calibration
  - Additional scenarios
```

### Review Schedule

- **After each deployment**: Update actual timings and gotchas
- **Monthly**: Review for new scenarios discovered
- **Quarterly**: Full runbook review with operations team

### Key Metrics to Track

```bash
#!/bin/bash
# track-deployment-metrics.sh

# Capture deployment metrics for runbook improvement
deployment_date=$(date +%Y-%m-%d)
deployment_log="/opt/basset-hound/backups/deployment-${deployment_date}.json"

cat > "$deployment_log" << 'EOF'
{
  "date": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "deployment_type": "upgrade",  # or "fresh", "hotfix", "rollout"
  "version_from": "1.9.0",
  "version_to": "2.0.0",
  "duration_minutes": 0,
  "downtime_minutes": 0,
  "phases": {
    "preparation": {"duration_minutes": 5, "status": "success"},
    "backup": {"duration_minutes": 3, "status": "success"},
    "deployment": {"duration_minutes": 10, "status": "success"},
    "validation": {"duration_minutes": 5, "status": "success"},
    "recovery": {"duration_minutes": 0, "status": "na"}
  },
  "issues": [],
  "rollbacks_triggered": 0,
  "success": true,
  "notes": ""
}
EOF

echo "Metrics captured: $deployment_log"
```

### Continuous Improvement Checklist

After each deployment:

```
☐ Actual vs. estimated times recorded
☐ Any surprises documented
☐ New failure modes identified
☐ Procedure steps refined
☐ Team feedback collected
☐ Documentation updated
☐ Next runbook version scheduled

Questions to ask:
  - What took longer than expected?
  - What was easier than expected?
  - What new scenarios did we encounter?
  - How can we improve the process?
  - Do we need additional safeguards?
```

---

## Appendix A: Quick Reference Commands

```bash
# Health Checks
curl http://localhost:8080/health | jq .
docker compose ps
docker stats

# Database Operations
docker exec neo4j_osint_db cypher-shell -u neo4j -p neo4jbasset
docker exec neo4j_osint_db neo4j-admin database dump neo4j /backup/dump
docker exec neo4j_osint_db neo4j-admin database load neo4j /backup/dump

# Logs
docker compose logs -f basset_api
docker compose logs --since 1h
docker logs basset_api | tail -100

# Performance
curl http://localhost:8080/metrics | grep basset
docker stats --no-stream

# Debugging
docker compose config
docker network inspect basset-hound
docker exec basset_api python -m pytest tests/

# Cleanup
docker compose down -v
docker system prune -a --volumes
docker network prune
```

## Appendix B: System Resource Recommendations

```
Small Deployment (< 100K entities):
├─ CPU: 2-4 cores
├─ RAM: 4-8 GB
├─ Storage: 50-100 GB
└─ Network: 100 Mbps

Medium Deployment (100K-1M entities):
├─ CPU: 4-8 cores
├─ RAM: 16-32 GB
├─ Storage: 200-500 GB
└─ Network: 1 Gbps

Large Deployment (1M+ entities):
├─ CPU: 8-16 cores
├─ RAM: 32-64 GB
├─ Storage: 500GB-2TB (RAID)
├─ Network: 10 Gbps
└─ DB: Enterprise Neo4j cluster
```

## Appendix C: Contact & Escalation

```
On-Call Rotation:
  Primary: [Name] - [Phone] - [Email]
  Secondary: [Name] - [Phone] - [Email]
  Manager: [Name] - [Phone] - [Email]

Slack Channels:
  #ops-incidents - Real-time incident updates
  #deployments - Deployment notifications
  #alerts - Automated alerts

Escalation Path:
  Level 1: On-call engineer (30 min response)
  Level 2: Team lead (15 min response)
  Level 3: Engineering manager (5 min response)
  Level 4: Director (immediate)
```

---

**Last Updated**: 2026-05-19  
**Maintained By**: Operations Team  
**Review Cycle**: Monthly  
**Next Review**: 2026-06-19
