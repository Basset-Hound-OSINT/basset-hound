# Basset Hound Production Deployment Runbook

**Version**: 2.0  
**Date**: 2026-05-19  
**Status**: For Operations Team Use (Post-Remediation)  
**Target Audience**: DevOps Engineers, System Administrators, SREs

---

## Table of Contents

1. [System Architecture Overview](#system-architecture-overview)
2. [Pre-Deployment Requirements](#pre-deployment-requirements)
3. [Step-by-Step Deployment](#step-by-step-deployment)
4. [Post-Deployment Validation](#post-deployment-validation)
5. [Health Checks & Monitoring](#health-checks--monitoring)
6. [Troubleshooting Guide](#troubleshooting-guide)
7. [Incident Response](#incident-response)
8. [Rollback Procedures](#rollback-procedures)

---

## System Architecture Overview

### Service Components

The Basset Hound platform consists of the following services running in Docker containers:

```
┌─────────────────────────────────────────────────────────────┐
│                     Nginx Reverse Proxy                      │
│                    (Port 8080, routes requests)              │
├──────────────────────┬──────────────────────┬────────────────┤
│                      │                      │                │
│  FastAPI Backend     │  Neo4j Database      │  Redis Cache   │
│  (4 Uvicorn workers) │  (Bolt on 7687)     │  (Port 6379)   │
│  (Port 8000)         │                      │                │
│                      │                      │                │
└──────────────────────┴──────────────────────┴────────────────┘
      ↑                       ↑                       ↑
   /api/v1/*                 Neo4j                   Session/
   /ws/*                     Drivers                 Query Cache
   Static files
```

### Key Services

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| nginx | nginx:alpine | 8080 | Reverse proxy, load balancing |
| api | basset-hound:latest | 8000 | FastAPI backend with Uvicorn |
| neo4j | neo4j:5.26-community | 7687 | Graph database |
| redis | redis:7-alpine | 6379 | Cache and session store |
| prometheus | prom/prometheus | 9090 | Metrics collection |
| grafana | grafana/grafana | 3000 | Metrics dashboards |

### Data Flow

1. **Frontend Request** → Nginx (port 8080)
2. Nginx routes to FastAPI backend (port 8000)
3. FastAPI queries Neo4j (port 7687) with parameterized queries
4. Neo4j response cached in Redis (port 6379)
5. Response returned to frontend with gzip compression

### Performance Targets (After Remediation)

| Metric | Target | Alert Threshold | Critical Threshold |
|--------|--------|-----------------|-------------------|
| API Latency (p99) | <100ms | >200ms | >500ms |
| Error Rate | <0.1% | >0.5% | >1% |
| Cache Hit Rate | >60% | <30% | <10% |
| Database Latency | <100ms | >150ms | >250ms |
| Health Check | <100ms | >200ms | >1000ms |
| Throughput | >3 req/s | <2 req/s | <1 req/s |

---

## Pre-Deployment Requirements

### 1. Infrastructure Prerequisites

**Hardware Requirements:**
- CPU: 4+ cores (recommended 8+)
- RAM: 8GB minimum (recommended 16GB+)
- Storage: 100GB+ free space (SSD recommended)
- Network: 1Gbps+ connection
- Uptime: 99.5% availability

**Software Requirements:**
```bash
# Check Docker installation
docker --version          # >=20.10
docker-compose --version  # >=2.0

# Check Python installation
python3 --version        # >=3.9

# Required OS packages
apt-get install curl wget git vim htop
```

### 2. Environment Configuration

Create production `.env` file with secure values:

```bash
# .env (DO NOT COMMIT TO GIT)

# --- API Configuration ---
DEBUG=false
REQUIRE_AUTH=true
CORS_ORIGINS="https://production-domain.com"
API_WORKERS=4
API_TIMEOUT=30

# --- Database Configuration ---
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=${SECURE_NEO4J_PASSWORD}
NEO4J_ENCRYPTED=true
NEO4J_TRUST=TRUST_ALL_CERTIFICATES
NEO4J_CONNECTION_POOL_SIZE=150
NEO4J_QUERY_TIMEOUT=5000  # 5 seconds

# --- Cache Configuration ---
REDIS_URL=redis://redis:6379/0
CACHE_DEFAULT_TTL=300
CACHE_PROJECTS_TTL=1800
CACHE_SEARCH_TTL=300

# --- Security Configuration ---
JWT_SECRET_KEY=${SECURE_JWT_KEY}  # 256-bit minimum
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
ENCRYPTION_KEY=${SECURE_ENCRYPTION_KEY}

# --- Monitoring Configuration ---
PROMETHEUS_ENABLED=true
SENTRY_DSN=${SENTRY_DSN}  # For error tracking

# --- Rate Limiting ---
ML_OPERATIONS_LIMIT=5
ML_OPERATIONS_WINDOW=60
DATABASE_DUMP_LIMIT=2
DATABASE_DUMP_WINDOW=300
SEARCH_LIMIT=30
SEARCH_WINDOW=60
EXPORT_LIMIT=10
EXPORT_WINDOW=60

# --- Feature Flags ---
FEATURE_ML_ANALYTICS=true
FEATURE_WEBSOCKET_SYNC=true
FEATURE_COLLABORATIVE_EDITING=true
FEATURE_EXPORT_ALL_FORMATS=true
```

### 3. Security Requirements

Before deployment, ensure:

- [ ] JWT_SECRET_KEY: 256-bit random value (use `openssl rand -hex 32`)
- [ ] Neo4j password changed from default
- [ ] Database credentials in secure vault (AWS Secrets Manager, HashiCorp Vault)
- [ ] Encryption keys generated and stored securely
- [ ] HTTPS/TLS certificates obtained (Let's Encrypt)
- [ ] API key authentication configured
- [ ] Rate limiting rules defined

**Generate Secure Values:**

```bash
# Generate JWT secret (256 bits)
python3 -c "import secrets; print(secrets.token_hex(32))"
# Output: a1b2c3d4e5f6...

# Generate encryption key
python3 -c "import base64, secrets; print(base64.b64encode(secrets.token_bytes(32)).decode())"
# Output: a1b2c3d4e5f6...==
```

### 4. Network Configuration

**Port Requirements:**

| Port | Service | Access | Purpose |
|------|---------|--------|---------|
| 8080 | Nginx | Public | Main application endpoint |
| 8000 | FastAPI | Internal | Backend API (not exposed) |
| 7687 | Neo4j | Internal | Database Bolt driver |
| 6379 | Redis | Internal | Cache layer |
| 9090 | Prometheus | Internal | Metrics collection |
| 3000 | Grafana | Admin only | Monitoring dashboard |

**Firewall Rules:**

```bash
# Allow public access to main endpoint
iptables -A INPUT -p tcp --dport 8080 -j ACCEPT

# Allow admin access to monitoring
iptables -A INPUT -s <admin-ip> -p tcp --dport 3000 -j ACCEPT

# Block direct database access
iptables -A INPUT -p tcp --dport 7687 -j DROP
iptables -A INPUT -p tcp --dport 6379 -j DROP
```

### 5. SSL/TLS Configuration

**Obtain Certificate (Let's Encrypt):**

```bash
# Install certbot
apt-get install certbot python3-certbot-nginx

# Obtain certificate
certbot certonly --standalone -d your-domain.com

# Certificate location
/etc/letsencrypt/live/your-domain.com/fullchain.pem
/etc/letsencrypt/live/your-domain.com/privkey.pem
```

**Update Nginx Configuration:**

```nginx
# In docker-compose.yml, mount certificates
volumes:
  - /etc/letsencrypt/live/your-domain.com:/etc/nginx/certs:ro

# In nginx.conf
server {
    listen 443 ssl http2;
    ssl_certificate /etc/nginx/certs/fullchain.pem;
    ssl_certificate_key /etc/nginx/certs/privkey.pem;
    
    # Redirect HTTP to HTTPS
}
server {
    listen 80;
    return 301 https://$host$request_uri;
}
```

---

## Step-by-Step Deployment

### Phase 1: Pre-Deployment Checks (30 minutes)

#### Step 1.1: Verify Infrastructure

```bash
# Check system resources
free -h                  # Memory usage
df -h                    # Disk space
nproc                    # CPU cores
uptime                   # System uptime

# Expected outputs:
# Memory: 16GB+ available
# Disk: 100GB+ free
# CPU: 4+ cores
# Uptime: system stable
```

#### Step 1.2: Verify Docker

```bash
# Check Docker daemon
docker ps                # Should list current containers
docker-compose --version # Should be v2.0+

# Expected output:
# Docker version 20.10+
# Docker Compose version 2.0+
```

#### Step 1.3: Verify Network

```bash
# Check DNS resolution
nslookup neo4j           # Should resolve if containers running
curl -I http://localhost:8080/health  # Current health

# Test connectivity
ping -c 1 8.8.8.8       # Internet connectivity
```

#### Step 1.4: Verify Backups

```bash
# Check backup directory exists
ls -lh /backups

# Verify backup system accessible
# (e.g., AWS S3, Azure Blob, GCS, or local storage)
```

#### Step 1.5: Notify Team

Send deployment notification:

```plaintext
SUBJECT: Production Deployment - Basset Hound Phase 8
TIME: 2026-05-20 14:00 UTC
DURATION: 30-45 minutes
IMPACT: Brief interruption to services expected
ROLLBACK: Available if critical issues detected

Team members required online:
- DevOps lead
- Database administrator
- On-call engineer
- Frontend tech lead
```

### Phase 2: Pre-Deployment Backup (15 minutes)

#### Step 2.1: Backup Database

```bash
# Create database backup
docker-compose exec neo4j neo4j-admin database dump neo4j \
  /backups/pre-deployment-$(date +%Y%m%d_%H%M%S).dump

# Verify backup
ls -lh /backups/pre-deployment-*.dump

# Copy to remote storage
aws s3 cp /backups/pre-deployment-*.dump \
  s3://your-backup-bucket/neo4j/

# Expected output:
# -rw-r--r-- 1 root root 2.3G pre-deployment-20260520_140000.dump
```

#### Step 2.2: Backup Configuration

```bash
# Backup current docker-compose.yml
cp docker-compose.yml docker-compose.yml.backup-20260520

# Backup current .env
cp .env .env.backup-20260520

# Backup application code
git tag pre-deployment-20260520
git push origin pre-deployment-20260520
```

#### Step 2.3: Create Filesystem Snapshot

```bash
# For LVM-based volumes
lvcreate -L 10G -s -n neo4j_snapshot /dev/vg0/neo4j_data

# For cloud providers
# AWS: Create EBS snapshot
# Azure: Create VM snapshot
# GCP: Create disk snapshot
```

### Phase 3: Staging Validation (2-3 hours)

#### Step 3.1: Deploy to Staging

```bash
# Setup staging environment (if separate server)
ssh staging-server

# Pull latest code
cd /opt/basset-hound
git pull origin main

# Copy production .env to staging
scp production-server:/opt/basset-hound/.env .

# Build and start services
docker-compose down
docker-compose build
docker-compose up -d

# Wait for services to be healthy
sleep 30
docker-compose ps
```

#### Step 3.2: Run Tests

```bash
# Execute full test suite
python3 -m pytest tests/ -v --tb=short

# Expected output:
# ======================== test session starts =========================
# collected 2500+ items
# tests/... PASSED
# tests/... PASSED
# ======================== 2500+ passed in 250s =======================
```

#### Step 3.3: Execute Load Test

```bash
# Run load test script
python3 load_testing_script.py

# Expected output:
# Load Test Results:
# Throughput: 3.5 req/s (target: >3) ✓
# Error Rate: 0.2% (target: <5%) ✓
# Latency p99: 85ms (target: <100ms) ✓
# Health Check: 45ms (target: <100ms) ✓
```

#### Step 3.4: Manual Validation

```bash
# Test critical endpoints
curl http://localhost:8080/health
curl http://localhost:8080/api/v1/projects
curl http://localhost:8080/api/v1/search/full-text?q=test

# Test WebSocket (requires browser/wscat)
wscat -c ws://localhost:8080/ws/sync/proj_test

# Test export functionality
curl -X POST http://localhost:8080/api/v1/export/csv \
  -H "Content-Type: application/json" \
  -d '{"project_id": "proj_test"}'
```

#### Step 3.5: Monitor Staging

```bash
# Monitor for 30+ minutes
watch -n 5 'docker-compose logs api | tail -20'

# Check for errors
docker-compose logs api | grep -i "error\|exception\|critical"

# Verify no memory leaks
docker stats --no-stream

# Expected: Stable memory, CPU <20%, no errors
```

### Phase 4: Production Deployment (45 minutes)

#### Step 4.1: Enable Maintenance Mode (Optional)

```bash
# If using maintenance page
docker-compose up -d maintenance-page

# Or update Nginx to return 503
# Edit nginx.conf:
# return 503 "Maintenance in progress"
```

#### Step 4.2: Pre-Deployment Snapshot

```bash
# Take final snapshot before changes
docker-compose exec neo4j cypher-shell "CALL dbms.checkpoint()"

# Get current stats for comparison
docker-compose exec neo4j cypher-shell "SHOW DATABASE" > db-stats-pre.txt
```

#### Step 4.3: Stop Current Services

```bash
# Graceful shutdown (allow connections to drain)
docker-compose stop api redis
sleep 10

# Force stop if needed
docker-compose kill

# Verify stopped
docker-compose ps
# Expected: All services stopped except neo4j
```

#### Step 4.4: Update Configuration

```bash
# Update docker-compose.yml if needed
git pull origin main

# Update production .env with new values
vim .env  # Edit with new credentials/settings

# Verify no secrets in git
git diff docker-compose.yml  # Should show no .env changes
```

#### Step 4.5: Build and Start Services

```bash
# Build new images
docker-compose build

# Start services (neo4j first, wait for healthy)
docker-compose up -d neo4j
sleep 30

# Check neo4j is ready
docker-compose exec neo4j cypher-shell "RETURN 1"
# Expected output: 1

# Start remaining services
docker-compose up -d redis api nginx prometheus grafana

# Wait for API to be ready
sleep 30
docker-compose ps
# Expected: All services "Up"
```

#### Step 4.6: Verify Service Health

```bash
# Check all services responding
for i in {1..30}; do
  echo "Health check attempt $i/30..."
  curl -s http://localhost:8080/health
  if [ $? -eq 0 ]; then
    echo "✓ Services healthy"
    break
  fi
  sleep 2
done

# Expected output:
# {"status": "healthy", "timestamp": "2026-05-20T14:05:00Z"}
```

#### Step 4.7: Validate Data Integrity

```bash
# Check database is accessible
docker-compose exec neo4j cypher-shell "MATCH (n) RETURN count(n) AS count"

# Expected output:
# count
# 12500+

# Check specific indexes exist
docker-compose exec neo4j cypher-shell "SHOW INDEXES"

# Verify replication (if using cluster)
docker-compose exec neo4j cypher-shell "CALL dbms.cluster.overview()"
```

#### Step 4.8: Run Smoke Tests

```bash
# Test critical endpoints
echo "Testing health endpoint..."
curl http://localhost:8080/health | jq .

echo "Testing projects endpoint..."
curl http://localhost:8080/api/v1/projects | jq .data | head -5

echo "Testing search endpoint..."
curl http://localhost:8080/api/v1/search/full-text?q=test | jq .data | head -5

echo "Testing authentication..."
curl -H "Authorization: Bearer invalid_token" \
  http://localhost:8080/api/v1/projects | jq .error
```

### Phase 5: Gradual Traffic Ramp-Up (15 minutes)

#### Step 5.1: Warm Up Cache

```bash
# Execute warmup script to populate cache
python3 scripts/warmup_cache.py

# Monitor cache hit rate
watch -n 2 'curl -s http://localhost:8080/api/v1/cache/stats | jq .hit_rate'
# Target: >60% after 5 minutes
```

#### Step 5.2: Monitor Initial Traffic

```bash
# Watch API logs for errors
tail -f docker-compose logs api | grep -E "error|exception|500"

# Monitor system resources
watch -n 2 'docker stats --no-stream'
# Target: CPU <30%, Memory <60%, no errors
```

#### Step 5.3: Gradual Ramp-Up (if using load balancer)

```bash
# If using AWS ALB, gradually increase traffic
# Time: 5 min | Traffic: 10% | Monitor: error rate, latency
# Time: 10 min | Traffic: 50% | Monitor: error rate, latency
# Time: 15 min | Traffic: 100% | Monitor: sustained

# If using Nginx, adjust upstream weights
# upstream api {
#     server api:8000 weight=25;  # Start at 25%
#     ...
# }
```

#### Step 5.4: Continuous Monitoring

```bash
# Monitor key metrics continuously
watch -n 5 'curl -s http://localhost:8080/api/v1/metrics | jq \
  "{error_rate: .error_rate, latency_p99: .latency_p99, cache_hit: .cache_hit_rate}"'

# Expected output:
# {
#   "error_rate": 0.0,
#   "latency_p99": 85,
#   "cache_hit_rate": 62.5
# }
```

---

## Post-Deployment Validation

### Immediate Validation (First 30 minutes)

```bash
# 1. Verify all services running
docker-compose ps
# Expected: All services "Up"

# 2. Check error rate
curl http://localhost:8080/api/v1/metrics | jq .error_rate
# Expected: <0.5%

# 3. Check latency
curl http://localhost:8080/api/v1/metrics | jq .latency_p99
# Expected: <200ms

# 4. Check cache hit rate
curl http://localhost:8080/api/v1/metrics | jq .cache_hit_rate
# Expected: >40%

# 5. Check no critical errors
docker-compose logs api | grep -i "critical\|fatal"
# Expected: No output
```

### Extended Validation (24 hours)

Create validation report template:

```markdown
# Post-Deployment Validation Report
**Date**: 2026-05-20  
**Deployment**: Production Phase 8  
**Validator**: [Name]

## Service Health
- [ ] All services responding (8:00 AM, 12:00 PM, 4:00 PM, 8:00 PM)
- [ ] Error rate consistently <0.1%
- [ ] No service restarts or crashes
- [ ] Database connections stable

## Performance Metrics
- [ ] API latency p99: <200ms (sustained)
- [ ] Cache hit rate: >40% (sustained)
- [ ] Database latency: <150ms (sustained)
- [ ] Throughput: >3 req/s (sustained)

## Data Integrity
- [ ] All entities accessible
- [ ] Search functionality working
- [ ] Export operations successful
- [ ] Audit logs recording changes

## User Experience
- [ ] Dashboard loads normally
- [ ] Search results accurate
- [ ] Export functionality working
- [ ] WebSocket sync operational
- [ ] No user-reported issues

## Monitoring & Alerting
- [ ] Prometheus collecting metrics
- [ ] Grafana dashboards populated
- [ ] Alert rules functioning
- [ ] Log aggregation working

## Sign-Off
**Operations Manager**: _________________ Date: _______  
**DevOps Lead**: _________________ Date: _______  
**Monitoring Lead**: _________________ Date: _______
```

---

## Health Checks & Monitoring

### Health Check Endpoint

The health check endpoint is critical for monitoring:

```bash
# Basic health check
curl http://localhost:8080/health

# Response (healthy):
{
  "status": "healthy",
  "timestamp": "2026-05-20T14:00:00Z",
  "services": {
    "api": "healthy",
    "database": "connected",
    "cache": "healthy"
  },
  "uptime_seconds": 3600,
  "version": "2.0.0"
}

# Response (degraded):
{
  "status": "degraded",
  "timestamp": "2026-05-20T14:00:00Z",
  "services": {
    "api": "healthy",
    "database": "connected",
    "cache": "unavailable"  # <-- Issue
  },
  "message": "Cache layer unavailable, using database"
}
```

### Key Metrics to Monitor

```bash
# Error Rate (target: <0.1%)
curl http://localhost:8080/api/v1/metrics | jq .error_rate

# API Latency P99 (target: <100ms)
curl http://localhost:8080/api/v1/metrics | jq .latency_p99

# Cache Hit Rate (target: >60%)
curl http://localhost:8080/api/v1/metrics | jq .cache_hit_rate

# Database Connection Pool (target: <80% utilized)
docker-compose exec neo4j cypher-shell \
  "CALL dbms.monitoring.connection_pool() YIELD active, idle RETURN active, idle"

# Request Throughput (target: >3 req/s)
curl http://localhost:8080/api/v1/metrics | jq .requests_per_second

# Error Count by Endpoint
curl http://localhost:8080/api/v1/metrics | jq .error_count_by_endpoint
```

### Monitoring with Prometheus

```bash
# Access Prometheus
curl http://localhost:9090/api/v1/query?query=up

# Query request rate
curl http://localhost:9090/api/v1/query?query='rate(http_requests_total[5m])'

# Query error rate
curl http://localhost:9090/api/v1/query?query='rate(http_errors_total[5m])'

# Query latency
curl http://localhost:9090/api/v1/query?query='http_request_duration_seconds_p99'
```

### Grafana Dashboards

Access Grafana at `http://localhost:3000/`:
- **Default credentials**: admin / admin (change on first login)
- **Dashboard**: Basset Hound Overview (shows all key metrics)
- **Alerts**: Alert Rules page shows configured alerts

---

## Troubleshooting Guide

### Problem 1: Services Fail to Start

**Symptom**: `docker-compose up -d` fails or services exit immediately

**Diagnosis**:

```bash
# Check service logs
docker-compose logs neo4j
docker-compose logs api
docker-compose logs redis

# Check Docker resources
docker system df
docker volume ls

# Check port conflicts
netstat -tlnp | grep -E "8000|8080|7687|6379"
```

**Solution**:

```bash
# If port conflict:
# 1. Identify process using port
lsof -i :8000

# 2. Kill conflicting process
kill -9 <PID>

# 3. Restart services
docker-compose restart

# If insufficient resources:
# 1. Remove unused images/volumes
docker image prune -a
docker volume prune

# 2. Increase Docker resource limits
# Edit /etc/docker/daemon.json
# Add: "memory": "8g", "cpus": "4.0"
systemctl restart docker
```

### Problem 2: High Error Rate (>1%)

**Symptom**: `/api/v1/metrics` shows `error_rate: >0.01`

**Diagnosis**:

```bash
# Check logs for error patterns
docker-compose logs api | grep -i "error\|exception\|traceback" | head -20

# Check specific error types
docker-compose logs api | grep "500\|timeout\|connection" | wc -l

# Check database connectivity
docker-compose exec neo4j cypher-shell "RETURN 1"

# Check cache connectivity
docker-compose exec redis redis-cli ping
# Expected: PONG
```

**Solution by Error Type**:

```bash
# If "ConnectionError" (database):
# 1. Verify Neo4j is running
docker-compose ps neo4j  # Should be "Up"

# 2. Check Neo4j logs
docker-compose logs neo4j | tail -50

# 3. Verify connection pool size
# Edit .env: NEO4J_CONNECTION_POOL_SIZE=150
docker-compose restart neo4j

# If "timeout" errors:
# 1. Check query performance
docker-compose exec neo4j cypher-shell \
  "PROFILE MATCH (n) RETURN n LIMIT 10"

# 2. Check slow queries log
# Enable profiling in neo4j.conf

# If "CacheError" (Redis):
# 1. Verify Redis is running
docker-compose ps redis

# 2. Check Redis memory
docker-compose exec redis redis-cli info memory

# 3. Clear cache if needed (last resort)
docker-compose exec redis redis-cli FLUSHALL
docker-compose restart api
```

### Problem 3: Slow API Response Times

**Symptom**: Latency p99 >500ms (target: <100ms)

**Diagnosis**:

```bash
# Check query latency
curl http://localhost:8080/api/v1/metrics | jq .latency_p99

# Check slow queries
docker-compose logs api | grep "duration_ms" | sort -t= -k2 -rn | head -5

# Check database load
docker-compose exec neo4j cypher-shell \
  "CALL dbms.monitoring.database_execution_time() YIELD duration_ms, statement RETURN statement, duration_ms ORDER BY duration_ms DESC LIMIT 5"

# Check system resources
docker stats --no-stream api
# Look for high CPU or memory usage
```

**Solution**:

```bash
# If high CPU:
# 1. Identify hot endpoints
curl http://localhost:8080/api/v1/metrics | jq .slow_endpoints | head -5

# 2. Optimize slow queries
# Edit /api/services/neo4j_service.py
# Add EXPLAIN to query, check execution plan

# 3. Add caching for frequently accessed data
# Increase CACHE_DEFAULT_TTL in .env

# If high memory:
# 1. Check for memory leaks
docker stats --no-stream --interval 1 api | tail -30

# 2. Restart API to free memory
docker-compose restart api

# 3. Consider limiting result sets
# Add pagination to large queries
```

### Problem 4: Database Connectivity Issues

**Symptom**: Health check returns `"database": "disconnected"`

**Diagnosis**:

```bash
# Check Neo4j container
docker-compose exec neo4j cypher-shell "RETURN 1"

# If connection refused:
docker-compose logs neo4j | grep -i "error\|listen\|bind"

# Check Neo4j logs for startup issues
docker-compose logs neo4j | tail -100

# Check network connectivity
docker network ls
docker network inspect <network> | grep neo4j
```

**Solution**:

```bash
# If Neo4j won't start:
# 1. Check disk space
df -h /var/lib/docker/volumes

# 2. Check logs for specific error
docker-compose logs neo4j | grep -A 5 "error"

# 3. Verify Neo4j data volume
docker volume inspect neo4j_data

# 4. Restart Neo4j
docker-compose restart neo4j
sleep 30

# If still failing:
# 1. Check Neo4j configuration
docker-compose exec neo4j cat conf/neo4j.conf | grep -i bolt

# 2. Verify connection parameters in .env
# NEO4J_URI should be: bolt://neo4j:7687

# 3. If data corrupted, restore from backup:
docker-compose stop neo4j
docker volume rm neo4j_data
docker-compose up -d neo4j  # Recreates volume
# Restore from backup dump (see Rollback section)
```

### Problem 5: Out of Memory

**Symptom**: Services killed with signal 9, logs show "OOMKilled"

**Diagnosis**:

```bash
# Check memory usage
docker stats --no-stream

# Check for memory leaks
docker stats --no-stream --interval 1 api | tail -10

# Check if specific requests cause memory spike
curl http://localhost:8080/api/v1/export/csv > /dev/null
docker stats --no-stream api

# Check available system memory
free -h
```

**Solution**:

```bash
# Immediate:
# 1. Increase Docker memory limit
# Edit /etc/docker/daemon.json:
# {
#   "memory": "16g",
#   "memswap": "16g"
# }
systemctl restart docker

# 2. Restart services
docker-compose restart

# 3. Reduce worker count temporarily
# Edit docker-compose.yml: command: "uvicorn ... --workers 2"

# Long-term:
# 1. Profile memory usage
docker-compose exec api python3 -m memory_profiler api/main.py

# 2. Fix memory leaks in code
# Look for unbounded caches, connection leaks

# 3. Optimize large data exports
# Implement streaming for large result sets
```

---

## Incident Response

### Incident Classification

| Severity | Response | Escalation |
|----------|----------|------------|
| Critical | Immediate (5 min) | Page on-call |
| High | Urgent (30 min) | Notify manager |
| Medium | Standard (4 hours) | Log ticket |
| Low | Batch (next sprint) | Document |

### Critical Incident Response

**Trigger**: Error rate >5% for >5 minutes, or core service down

```bash
# STEP 1: ASSESS (1-2 minutes)
1. Confirm issue:
   curl http://localhost:8080/health
   curl http://localhost:8080/api/v1/metrics

2. Gather immediate data:
   docker-compose logs api | tail -50 > incident-logs.txt
   docker stats --no-stream > incident-resources.txt
   docker-compose ps > incident-services.txt

3. Determine scope:
   - Is API responding? (yes/no)
   - Is database responding? (yes/no)
   - Is it affecting all endpoints or specific ones?

# STEP 2: NOTIFY (1 minute)
4. Page on-call engineer
5. Notify stakeholders via Slack
6. Create incident ticket in Jira/PagerDuty

# STEP 3: MITIGATE (2-5 minutes)
7. Decision tree:
   IF error_rate > 50% OR service_down:
     THEN: Initiate rollback (see Rollback section)
     ELSE: Attempt restart
   
8. Restart procedure:
   docker-compose logs api | tail -100  # Check for error pattern
   docker-compose restart api
   sleep 10
   curl http://localhost:8080/health  # Verify recovery

# STEP 4: ROOT CAUSE (During incident)
9. Analyze logs:
   - grep for "ERROR\|CRITICAL\|EXCEPTION"
   - Check timestamp of first error
   - Identify affected endpoints

10. Check system resources:
    - Memory: > 90% = restart needed
    - CPU: > 80% = load issue
    - Disk: > 95% = cleanup needed

# STEP 5: RESOLVE (5-30 minutes)
11. If restart resolves issue:
    - Monitor for 15+ minutes
    - Check if recurring
    - Prepare communication to users

12. If restart doesn't resolve:
    - Escalate to database team
    - Consider rollback
    - Prepare incident post-mortem

# STEP 6: COMMUNICATION
13. Keep stakeholders updated every 5 minutes
14. Post-incident: Write RCA and prevention plan
```

### Rollback Decision Tree

```
┌─ Is error rate > 50% for > 5 minutes?
│  YES → Rollback immediately (go to Rollback section)
│  NO  → Continue troubleshooting
│
├─ Did issue appear within 30 min of deployment?
│  YES → Likely deployment-caused, rollback
│  NO  → Likely pre-existing, debug
│
├─ Is core functionality broken (search, projects)?
│  YES → Rollback
│  NO  → May be able to continue with workarounds
│
└─ Can we fix within 15 minutes?
   YES → Attempt fix, monitor closely
   NO  → Rollback
```

---

## Rollback Procedures

### Quick Rollback (< 5 minutes)

Use this if critical issues detected within 30 minutes:

```bash
# STEP 1: Verify rollback target exists
git tag | grep pre-deployment
docker images | grep basset-hound

# STEP 2: Stop current services
docker-compose down

# STEP 3: Restore previous version
git checkout pre-deployment-20260520
docker-compose build

# STEP 4: Restore .env from backup
cp .env.backup-20260520 .env

# STEP 5: Start services with previous version
docker-compose up -d

# STEP 6: Verify recovery
sleep 30
curl http://localhost:8080/health
curl http://localhost:8080/api/v1/metrics | jq .error_rate

# Expected: error_rate < 0.5%
```

### Database Rollback (If Data Issue)

```bash
# STEP 1: Stop API services (keep database)
docker-compose stop api redis

# STEP 2: Restore database from backup
docker volume remove neo4j_data  # Be VERY careful here
docker-compose up -d neo4j
sleep 30

# STEP 3: Restore database dump
docker-compose exec neo4j neo4j-admin database load neo4j \
  /backups/pre-deployment-20260520.dump

# STEP 4: Start API services
docker-compose up -d api redis

# STEP 5: Verify data integrity
docker-compose exec neo4j cypher-shell "MATCH (n) RETURN count(n)"
# Should match pre-deployment count
```

### Partial Rollback (Feature Flag)

For issues affecting specific features:

```bash
# Disable problematic feature temporarily
# Edit .env:
FEATURE_WEBSOCKET_SYNC=false      # Disable WebSocket
FEATURE_ML_ANALYTICS=false        # Disable ML features

# Restart API
docker-compose restart api

# Monitor for 15+ minutes
curl http://localhost:8080/api/v1/metrics | jq .error_rate
```

---

## Maintenance Operations

### Regular Maintenance Tasks

**Daily**:
```bash
# Check system health
docker-compose ps
curl http://localhost:8080/health

# Monitor logs for errors
docker-compose logs api | grep -i error | wc -l
# Should be < 10 errors per day
```

**Weekly**:
```bash
# Check disk usage
df -h /var/lib/docker

# Prune old logs
docker container prune -f

# Backup database
docker-compose exec neo4j neo4j-admin database dump neo4j \
  /backups/weekly-$(date +%Y%m%d).dump
```

**Monthly**:
```bash
# Full system health check
python3 -m pytest tests/ -v

# Clean up old backups
find /backups -mtime +30 -delete

# Review metrics and trends
# Generate report from Grafana

# Security audit
# Review auth logs, rate limiting, access patterns
```

---

## Emergency Contacts

**Critical Issues**:
- **On-Call Engineer**: [24/7 contact]
- **Engineering Manager**: [Business hours + on-call]
- **DevOps Lead**: [Contact details]

**Escalation**:
- **CTO**: [Availability]
- **Security Team**: [For security issues]
- **Database Team**: [For database issues]

**External Support**:
- **Cloud Provider Support**: [Ticket URL]
- **Neo4j Support**: [Support details if applicable]

---

**Document Status**: Final  
**Last Updated**: 2026-05-19  
**Next Review**: Post-deployment (24 hours)  
**Owner**: Operations / DevOps Team

---

## Appendix: Command Quick Reference

```bash
# Service Management
docker-compose ps                      # List services
docker-compose logs <service>          # View logs
docker-compose restart <service>       # Restart service
docker-compose exec <service> <cmd>    # Execute command

# Health Checks
curl http://localhost:8080/health      # Overall health
curl http://localhost:8080/api/v1/metrics  # Detailed metrics

# Database
docker-compose exec neo4j cypher-shell "RETURN 1"  # Connection test
docker-compose exec neo4j cypher-shell "SHOW INDEXES"  # List indexes

# Cache
docker-compose exec redis redis-cli ping    # Test connection
docker-compose exec redis redis-cli info    # Redis stats
docker-compose exec redis redis-cli FLUSHALL  # Clear cache

# Monitoring
curl http://localhost:9090/api/v1/query?query=up  # Prometheus
# http://localhost:3000 → Grafana dashboard

# Logs
docker-compose logs --tail=100 api  # Last 100 lines
docker-compose logs --follow api    # Follow logs
docker-compose logs api > api.log   # Save to file
```

---

## Success Criteria Checklist

After deployment, verify:

- [ ] All services healthy (docker-compose ps shows "Up")
- [ ] Error rate < 0.1% for 30+ minutes
- [ ] API latency p99 < 200ms
- [ ] Cache hit rate > 40%
- [ ] No data corruption
- [ ] All endpoints responding correctly
- [ ] WebSocket connections stable
- [ ] Export functionality working
- [ ] Authentication enforced
- [ ] Rate limiting active
- [ ] Monitoring collecting metrics
- [ ] Alerting functional
- [ ] Backup systems operational
- [ ] Team confident in stability

**Deployment Status**: ✅ **SUCCESSFUL** (when all checked)
