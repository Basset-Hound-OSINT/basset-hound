# Rollback & Disaster Recovery Procedures

**Version**: 2.1.0  
**Last Updated**: 2026-05-19  
**Status**: Production Ready  
**Scope**: Phase 8 Deployment (2026-05-07)  
**Audience**: DevOps, System Administrators, On-Call Engineers

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Reference](#quick-reference)
3. [Full Rollback Procedures](#full-rollback-procedures)
4. [Partial Rollback Procedures](#partial-rollback-procedures)
5. [Data Recovery Procedures](#data-recovery-procedures)
6. [Communication Plan](#communication-plan)
7. [Testing & Validation](#testing--validation)
8. [Troubleshooting](#troubleshooting)
9. [Risk Assessment](#risk-assessment)
10. [Emergency Contacts](#emergency-contacts)

---

## Overview

### Purpose

This document provides step-by-step procedures for rolling back Phase 8 deployment and recovering from disasters. It covers:

- **Full rollback**: Complete revert to Phase 7 (last stable version)
- **Partial rollback**: Component-specific rollbacks (frontend, backend, database)
- **Data recovery**: Restore from backups with validation
- **Validation procedures**: Verify successful rollback/recovery
- **Risk assessment**: Understand rollback implications

### Key Information

| Item | Value |
|------|-------|
| **Current Version** | Phase 8 (v2.0.0) |
| **Previous Stable** | Phase 7 (v1.9.0) |
| **Estimated Full Rollback Time** | 15-30 minutes |
| **Estimated Data Recovery Time** | 30-60 minutes (depends on size) |
| **Backup Retention** | 30 days (daily backups) |
| **RTO (Recovery Time Objective)** | 1 hour maximum |
| **RPO (Recovery Point Objective)** | 24 hours (latest backup) |

### Critical Services

```
Basset Hound Deployment Stack:
├── Docker Containers (8 services)
│   ├── basset_api (FastAPI, port 8000)
│   ├── basset_nginx (Reverse proxy, port 8080)
│   ├── neo4j_osint_db (Graph DB, port 7474/7687)
│   ├── basset_redis (Cache, port 6379)
│   ├── basset_verify (Verification service, port 8001)
│   ├── prometheus (Metrics, port 9090)
│   ├── grafana (Dashboards, port 3000)
│   └── Additional services as configured
├── Data Volumes
│   ├── neo4j_data (Database)
│   ├── redis_data (Cache)
│   └── nginx_logs (Logs)
└── Backups (/opt/basset-hound/backups/)
    ├── neo4j_<timestamp>.dump
    ├── config_<timestamp>.tar.gz
    └── projects_<timestamp>.tar.gz
```

---

## Quick Reference

### Scenario: Service Down or Critical Error

**Action**: Execute quick rollback in 2-3 minutes

```bash
# 1. Stop Phase 8 services
docker compose down

# 2. Use Phase 7 image (if still available)
docker compose --env-file .env.phase7 up -d

# 3. Verify
curl http://localhost:8080/health

# If Phase 7 images unavailable, proceed to Full Rollback
```

### Scenario: Database Corruption

**Action**: Restore from latest backup

```bash
# 1. Stop services
docker compose down

# 2. Restore backup
docker volume rm basset-hound_neo4j_data
docker compose up -d neo4j
docker exec neo4j_osint_db neo4j-admin database load neo4j /backup/neo4j_latest.dump

# 3. Restart all services
docker compose up -d

# 4. Validate
curl http://localhost:8080/api/v1/projects
```

### Scenario: Frontend Not Loading

**Action**: Frontend-only rollback

```bash
# 1. Keep backend running
# 2. Rollback frontend only
cd frontend/
git checkout v1.9.0
npm install
npm run build:prod

# 3. Restart API to serve old frontend
docker compose restart basset_api

# 4. Test
curl http://localhost:8080/
```

---

## Full Rollback Procedures

### Overview

Full rollback reverts the entire system to Phase 7, the last stable version. This includes:
- Application containers
- Database schema
- Configuration files
- Frontend assets
- All dependent services

### Prerequisites

- Docker Compose 2.20+
- Access to Phase 7 Docker images or ability to rebuild
- Latest backup files present in `/opt/basset-hound/backups/`
- SSH access to deployment server
- 15-30 minutes downtime window

### Step 1: Pre-Rollback Checklist

```bash
#!/bin/bash
# Pre-rollback validation script

echo "=== Pre-Rollback Checklist ==="

# 1. Verify backups exist
echo "1. Checking backups..."
ls -lh /opt/basset-hound/backups/neo4j_*.dump.gz | tail -1
ls -lh /opt/basset-hound/backups/config_*.tar.gz | tail -1
ls -lh /opt/basset-hound/backups/projects_*.tar.gz | tail -1

# 2. Check disk space
echo "2. Checking disk space..."
df -h /opt/basset-hound/
free -h

# 3. Verify current deployment
echo "3. Checking current status..."
docker compose ps
docker compose logs -n 20 basset_api | tail -5

# 4. Document current state
echo "4. Saving current state..."
docker inspect basset_osint_db > /tmp/neo4j_state_before.json
docker stats --no-stream > /tmp/docker_stats_before.txt

# 5. Notify stakeholders
echo "5. Notifying stakeholders..."
# Send notifications (see Communication Plan section)

echo "=== Pre-Rollback Checklist Complete ==="
```

### Step 2: Backup Current State

Even when rolling back, preserve the Phase 8 state for analysis and potential forward recovery.

```bash
#!/bin/bash
# Backup current Phase 8 state

BACKUP_DIR="/opt/basset-hound/backups/rollback-2026-05-19"
mkdir -p "$BACKUP_DIR"

echo "Backing up Phase 8 state to $BACKUP_DIR..."

# Backup Neo4j current state
docker exec neo4j_osint_db neo4j-admin database dump neo4j \
  "$BACKUP_DIR/neo4j_phase8_final.dump"
gzip "$BACKUP_DIR/neo4j_phase8_final.dump"

# Backup configuration
tar -czf "$BACKUP_DIR/config_phase8_final.tar.gz" \
  /opt/basset-hound/.env \
  /opt/basset-hound/docker-compose.yml

# Backup frontend build
tar -czf "$BACKUP_DIR/frontend_phase8_final.tar.gz" \
  /opt/basset-hound/frontend/build/

# Backup application logs
tar -czf "$BACKUP_DIR/logs_phase8_final.tar.gz" \
  /var/lib/docker/containers/*/*/stdout*

echo "Phase 8 state backed up to $BACKUP_DIR"
```

### Step 3: Stop Current Services

```bash
#!/bin/bash
# Stop Phase 8 services

cd /opt/basset-hound

echo "Stopping Phase 8 services..."

# Graceful shutdown (30 second timeout)
docker compose down --timeout 30

# Verify all stopped
docker compose ps

# Should show no containers running
```

### Step 4: Prepare Phase 7 Environment

Option A: If Phase 7 Docker images still available locally

```bash
#!/bin/bash

# Check for Phase 7 images
echo "Checking for Phase 7 Docker images..."
docker images | grep basset | grep -E "v1.9|phase-7"

# If found, proceed with tagged images in docker-compose.yml
cp docker-compose.yml docker-compose.phase8.yml
cp docker-compose.phase7.yml docker-compose.yml

# If not found, rebuild from source
if [ $? -ne 0 ]; then
  echo "Phase 7 images not found locally, rebuilding from source..."
  git checkout tags/v1.9.0
  docker compose build --no-cache
  git checkout main  # Return to main branch
fi
```

Option B: If rebuilding from Phase 7 source

```bash
#!/bin/bash

echo "Rebuilding from Phase 7 source..."

# 1. Fetch Phase 7 source
git fetch origin
git checkout tags/v1.9.0

# 2. Rebuild Docker images
docker compose build --no-cache

# Verify images built
docker images | grep basset

# 3. Return to main branch (Phase 8)
git checkout main
```

### Step 5: Restore Database

```bash
#!/bin/bash
# Restore Neo4j database from backup

BACKUP_FILE="/opt/basset-hound/backups/neo4j_phase7_backup.dump.gz"

if [ ! -f "$BACKUP_FILE" ]; then
  echo "ERROR: Backup file not found: $BACKUP_FILE"
  echo "Available backups:"
  ls -lh /opt/basset-hound/backups/neo4j_*.dump.gz | head -5
  exit 1
fi

echo "Restoring Neo4j database from $BACKUP_FILE..."

# 1. Remove current volume
docker volume rm basset-hound_neo4j_data

# 2. Start Neo4j
docker compose up -d neo4j

# 3. Wait for Neo4j to be ready
echo "Waiting for Neo4j to start..."
docker compose exec neo4j sh -c 'until neo4j-admin server status 2>/dev/null | grep -q "running"; do sleep 2; done'

# 4. Restore from backup
gunzip -c "$BACKUP_FILE" > /tmp/neo4j_restore.dump

docker exec neo4j_osint_db neo4j-admin database load neo4j \
  /var/lib/neo4j/backups/neo4j_restore.dump

# 5. Verify restoration
docker exec neo4j_osint_db cypher-shell -u neo4j -p neo4jbasset \
  "MATCH (n) RETURN count(n) AS node_count;"

echo "Neo4j database restored"
```

### Step 6: Restore Configuration & Environment

```bash
#!/bin/bash
# Restore Phase 7 configuration

BACKUP_DIR="/opt/basset-hound/backups"
CONFIG_BACKUP="$BACKUP_DIR/config_phase7_backup.tar.gz"

if [ ! -f "$CONFIG_BACKUP" ]; then
  echo "ERROR: Configuration backup not found"
  exit 1
fi

echo "Restoring configuration from $CONFIG_BACKUP..."

# 1. Extract backup
cd /tmp
tar -xzf "$CONFIG_BACKUP"

# 2. Restore .env
cp .env /opt/basset-hound/.env

# 3. Restore docker-compose.yml if needed
# cp docker-compose.yml /opt/basset-hound/docker-compose.yml

# 4. Restore nginx config
tar -xzf "$CONFIG_BACKUP" -C /opt/basset-hound/

# 5. Verify configuration
grep "NEO4J_URI" /opt/basset-hound/.env
grep "BASSET_VERIFY_ENABLED" /opt/basset-hound/.env

echo "Configuration restored"
```

### Step 7: Start Phase 7 Services

```bash
#!/bin/bash
# Start Phase 7 services

cd /opt/basset-hound

echo "Starting Phase 7 services..."

# 1. Start all services
docker compose up -d

# 2. Monitor startup (2-3 minutes)
echo "Waiting for services to start (monitoring for 3 minutes)..."
for i in {1..30}; do
  echo -n "."
  sleep 6
done
echo ""

# 3. Check service health
docker compose ps
```

### Step 8: Validation & Testing

```bash
#!/bin/bash
# Validate Phase 7 rollback

echo "=== Rollback Validation ==="

# 1. Health checks
echo "1. Health checks..."
curl -f http://localhost:8080/health || {
  echo "ERROR: API health check failed"
  exit 1
}

# 2. Database connectivity
echo "2. Database connectivity..."
curl -f http://localhost:8080/api/v1/projects || {
  echo "ERROR: Cannot reach projects endpoint"
  exit 1
}

# 3. Service versions
echo "3. Checking service versions..."
curl http://localhost:8080/docs | grep -i "1.9.0\|phase 7" && echo "✓ Phase 7 frontend detected" || echo "⚠ Version uncertain"

# 4. Neo4j status
echo "4. Neo4j status..."
docker exec neo4j_osint_db cypher-shell -u neo4j -p neo4jbasset \
  "MATCH (n) RETURN count(n) AS total_nodes;" || {
  echo "ERROR: Cannot query Neo4j"
  exit 1
}

# 5. Log inspection
echo "5. Checking logs for errors..."
docker compose logs --since 5m | grep -i error | head -5 || echo "✓ No recent errors"

echo ""
echo "=== Rollback Validation Complete ==="
```

### Step 9: Post-Rollback Documentation

```bash
#!/bin/bash
# Document the rollback event

ROLLBACK_LOG="/opt/basset-hound/logs/rollback-2026-05-19.log"
mkdir -p "$(dirname "$ROLLBACK_LOG")"

cat > "$ROLLBACK_LOG" << EOF
=== Basset Hound Rollback Log ===
Date: $(date)
From: Phase 8 (v2.0.0)
To: Phase 7 (v1.9.0)
Reason: [SPECIFY REASON]
Duration: [TIME TAKEN]

Pre-Rollback State:
$(docker stats --no-stream 2>/dev/null || echo "N/A")

Post-Rollback Validation:
$(curl -s http://localhost:8080/health)

Database Node Count:
$(docker exec neo4j_osint_db cypher-shell -u neo4j -p neo4jbasset "MATCH (n) RETURN count(n);" 2>/dev/null || echo "N/A")

Services Status:
$(docker compose ps)

Completed By: [YOUR NAME]
Approved By: [APPROVER NAME]
EOF

cat "$ROLLBACK_LOG"
```

---

## Partial Rollback Procedures

### Frontend-Only Rollback

Use when backend is stable but frontend has issues.

```bash
#!/bin/bash
# Frontend-only rollback to Phase 7

cd /opt/basset-hound/frontend

echo "Rolling back frontend to Phase 7..."

# 1. Get Phase 7 frontend code
git fetch origin
git checkout tags/v1.9.0 -- .  # Checkout only frontend changes

# 2. Install dependencies
npm install

# 3. Build production version
npm run build:prod

# 4. Copy to API static directory
cp -r build/* ../api/static/

# 5. Restart API to serve new frontend
cd ..
docker compose restart basset_api

# 6. Verify
curl http://localhost:8080/ | grep -i "phase 7\|v1.9" || echo "Frontend updated"

echo "Frontend rollback complete"
```

### Backend API Rollback

Use when backend code has issues but database is fine.

```bash
#!/bin/bash
# Backend API rollback to Phase 7

echo "Rolling back backend API to Phase 7..."

# 1. Stop API container only
docker compose stop basset_api

# 2. Get Phase 7 API code
cd /opt/basset-hound
git fetch origin
git checkout tags/v1.9.0 -- api/  # Checkout only API code

# 3. Rebuild API image
docker compose build --no-cache basset_api

# 4. Start API
docker compose up -d basset_api

# 5. Verify
docker compose logs basset_api | grep "Started" || sleep 5

curl http://localhost:8080/api/v1/projects

echo "Backend API rollback complete"
```

### Database Schema Rollback

Use when database schema needs reverting (advanced).

```bash
#!/bin/bash
# Neo4j schema rollback

echo "Rolling back database schema to Phase 7..."

# Option 1: Restore from backup (recommended)
echo "Restoring from backup..."
docker volume rm basset-hound_neo4j_data
docker compose up -d neo4j
docker exec neo4j_osint_db neo4j-admin database load neo4j \
  /var/lib/neo4j/backups/neo4j_phase7.dump

# Option 2: Run migration rollback scripts (if available)
# docker exec neo4j_osint_db cypher-shell < rollback_schema.cypher

# 3. Restart services
docker compose restart

echo "Database schema rollback complete"
```

### Redis Cache Rollback

Use to clear corrupted cache without affecting data.

```bash
#!/bin/bash
# Clear Redis cache (for cache-specific issues)

echo "Clearing Redis cache..."

# 1. Connect to Redis
docker exec -it basset_redis redis-cli

# Commands in Redis CLI:
# FLUSHALL          # Clear all cache
# FLUSHDB 0         # Clear database 0
# INFO memory       # Check memory usage

# Or via command line:
docker exec basset_redis redis-cli FLUSHALL

# 2. Optionally restart Redis
docker compose restart redis

echo "Redis cache cleared"
```

---

## Data Recovery Procedures

### Overview

Data recovery procedures restore data from backups when corruption or loss occurs.

### Backup Location & Format

```
/opt/basset-hound/backups/
├── neo4j_20260519_020000.dump.gz      # Neo4j database export
├── config_20260519_020000.tar.gz       # Configuration files
└── projects_20260519_020000.tar.gz     # Project data files

Retention Policy:
- Daily backups: Kept for 30 days
- Weekly full backups: Kept for 90 days
- Monthly snapshots: Kept for 1 year (optional)
- Immediate pre-deployment: Kept until new version stable (1 week)
```

### Listing Available Backups

```bash
#!/bin/bash
# List available backups

BACKUP_DIR="/opt/basset-hound/backups"

echo "=== Available Neo4j Backups ==="
ls -lh "$BACKUP_DIR"/neo4j_*.dump.gz | awk '{print $6, $7, $8, $9}' | column -t

echo ""
echo "=== Available Configuration Backups ==="
ls -lh "$BACKUP_DIR"/config_*.tar.gz | awk '{print $6, $7, $8, $9}' | column -t

echo ""
echo "=== Available Project Backups ==="
ls -lh "$BACKUP_DIR"/projects_*.tar.gz | awk '{print $6, $7, $8, $9}' | column -t

echo ""
echo "=== Disk Space ==="
du -sh "$BACKUP_DIR"
df -h "$BACKUP_DIR"
```

### Recovery Time Estimates

| Scenario | Size | Time | Notes |
|----------|------|------|-------|
| Small DB (<1M entities) | 100 MB | 5-10 min | Quick restore |
| Medium DB (1-10M entities) | 500 MB - 2 GB | 10-20 min | Standard restore |
| Large DB (10M+ entities) | 5+ GB | 30-60 min | Enterprise class |

### Full Database Recovery

```bash
#!/bin/bash
# Full Neo4j recovery from backup

BACKUP_FILE="$1"  # Pass as argument

if [ -z "$BACKUP_FILE" ]; then
  echo "Usage: $0 <backup-file>"
  echo "Example: $0 /opt/basset-hound/backups/neo4j_20260519_020000.dump.gz"
  exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
  echo "ERROR: Backup file not found: $BACKUP_FILE"
  exit 1
fi

echo "Starting database recovery from: $BACKUP_FILE"
echo "Estimated time: 10-60 minutes depending on size"
echo "Backup size: $(du -h "$BACKUP_FILE" | cut -f1)"

# 1. Verify backup integrity
echo "1. Verifying backup integrity..."
gzip -t "$BACKUP_FILE" || {
  echo "ERROR: Backup file is corrupted"
  exit 1
}

# 2. Stop services
echo "2. Stopping services (downtime begins)..."
docker compose down

# 3. Remove current database volume
echo "3. Removing current database..."
docker volume rm basset-hound_neo4j_data

# 4. Start Neo4j
echo "4. Starting Neo4j..."
docker compose up -d neo4j

# 5. Wait for Neo4j startup
echo "5. Waiting for Neo4j to initialize (this takes 1-2 minutes)..."
for i in {1..60}; do
  if docker exec neo4j_osint_db neo4j-admin server status 2>/dev/null | grep -q "running"; then
    echo "✓ Neo4j is running"
    break
  fi
  echo -n "."
  sleep 2
done

# 6. Restore database
echo "6. Restoring database from backup..."
TEMP_BACKUP="/tmp/neo4j_restore.dump"
gunzip -c "$BACKUP_FILE" > "$TEMP_BACKUP"

docker exec neo4j_osint_db neo4j-admin database load neo4j "$TEMP_BACKUP"

rm "$TEMP_BACKUP"

# 7. Start all services
echo "7. Starting all services..."
docker compose up -d

# 8. Verify restoration
echo "8. Verifying restoration..."
sleep 5

NODE_COUNT=$(docker exec neo4j_osint_db cypher-shell -u neo4j -p neo4jbasset \
  "MATCH (n) RETURN count(n) AS count;" 2>/dev/null | tail -1)

if [ -z "$NODE_COUNT" ] || [ "$NODE_COUNT" = "0" ]; then
  echo "WARNING: Database appears empty or Neo4j not ready yet"
else
  echo "✓ Database restored with $NODE_COUNT nodes"
fi

# 9. Final health check
echo "9. Running health checks..."
curl -f http://localhost:8080/health && echo "✓ API is healthy" || echo "⚠ API health check failed"
curl -f http://localhost:8080/api/v1/projects && echo "✓ Projects endpoint accessible" || echo "⚠ Projects endpoint failed"

echo ""
echo "=== Recovery Complete ==="
```

### Partial Data Recovery

Recover specific projects or data without full database restore.

```bash
#!/bin/bash
# Recover specific project from backup

PROJECT_ID="$1"
BACKUP_FILE="$2"

if [ -z "$PROJECT_ID" ] || [ -z "$BACKUP_FILE" ]; then
  echo "Usage: $0 <project-id> <backup-file>"
  exit 1
fi

echo "Recovering project $PROJECT_ID from $BACKUP_FILE..."

# 1. Extract project data from backup
TEMP_DIR="/tmp/recovery_$PROJECT_ID"
mkdir -p "$TEMP_DIR"

cd "$TEMP_DIR"
tar -xzf "$BACKUP_FILE" projects/

# 2. Verify project exists in backup
if [ ! -d "projects/$PROJECT_ID" ]; then
  echo "ERROR: Project $PROJECT_ID not found in backup"
  exit 1
fi

# 3. Restore project directory
cp -r "projects/$PROJECT_ID" /opt/basset-hound/data/projects/

# 4. Verify restoration
echo "Project restored to /opt/basset-hound/data/projects/$PROJECT_ID"

# 5. Test access via API
curl http://localhost:8080/api/v1/projects/$PROJECT_ID

# Cleanup
rm -rf "$TEMP_DIR"
```

### Recovery Validation Checklist

After any recovery, verify:

```bash
#!/bin/bash
# Recovery validation checklist

echo "=== Recovery Validation Checklist ==="

# 1. Service health
echo "1. Service Health"
docker compose ps | grep -E "Up|healthy" > /dev/null && echo "   ✓ All services running" || echo "   ✗ Some services down"

# 2. Database accessibility
echo "2. Database Access"
docker exec neo4j_osint_db cypher-shell -u neo4j -p neo4jbasset "RETURN 1" > /dev/null 2>&1 && echo "   ✓ Neo4j accessible" || echo "   ✗ Neo4j inaccessible"

# 3. Data integrity
echo "3. Data Integrity"
NODE_COUNT=$(docker exec neo4j_osint_db cypher-shell -u neo4j -p neo4jbasset \
  "MATCH (n) RETURN count(n) AS count;" 2>/dev/null | tail -1)
if [ "$NODE_COUNT" -gt 0 ]; then
  echo "   ✓ Database contains data ($NODE_COUNT nodes)"
else
  echo "   ✗ Database appears empty"
fi

# 4. API functionality
echo "4. API Functionality"
curl -s http://localhost:8080/health | grep -q "healthy" && echo "   ✓ API health good" || echo "   ✗ API unhealthy"

# 5. Data access
echo "5. Data Access"
PROJECTS=$(curl -s http://localhost:8080/api/v1/projects | grep -c '"id"')
if [ "$PROJECTS" -gt 0 ]; then
  echo "   ✓ Can access projects ($PROJECTS found)"
else
  echo "   ⚠ No projects found (may be empty database)"
fi

# 6. Cache status
echo "6. Cache Status"
docker exec basset_redis redis-cli PING > /dev/null 2>&1 && echo "   ✓ Redis operational" || echo "   ✗ Redis not responding"

echo ""
echo "=== Validation Complete ==="
```

---

## Communication Plan

### Pre-Rollback Communication (24 hours before planned maintenance)

**To**: Team leads, ops, stakeholders  
**Channel**: Email + Slack  
**Template**:

```
Subject: [SCHEDULED MAINTENANCE] Phase 8 Deployment - Rollback Plan (2026-05-20 02:00-03:00 UTC)

Basset Hound Platform Maintenance Window

Maintenance scheduled for:
- Date: [DATE]
- Time: [TIME] UTC ([LOCAL TIME])
- Duration: ~60 minutes
- Services: Basset Hound, basset-verify, monitoring

What we're doing:
Deploying Phase 8 enhancements (performance optimizations, ML analytics, real-time features)

Rollback trigger:
Automatic rollback to Phase 7 if critical issues detected during deployment testing

User impact:
- Platform will be unavailable for ~1 hour (or minutes if rollback triggered)
- Data will not be affected
- No data loss expected

What to do:
- Pause integrations or batch jobs
- Don't start new projects during window
- Monitor email for completion notification

Questions?
Contact: ops@example.com
Slack: #incident-management

Status updates available at: https://status.example.com
```

### During-Rollback Communication (every 5-10 minutes)

**To**: All users via status page + ops channel  
**Channel**: Status page + Slack  
**Template**:

```
[INCIDENT] Rolling back Phase 8 deployment
Status: IN PROGRESS
Last Updated: 2026-05-19 02:15 UTC

Rollback Step 1/9: Stopping Phase 8 services
Estimated remaining time: 20 minutes
```

### Post-Rollback Communication (immediately after)

**To**: All stakeholders  
**Channel**: Email + Slack  
**Template**:

```
Subject: [RESOLVED] Phase 8 Rollback Complete - System Restored

Incident Summary:
- Detected: Critical database issue during Phase 8 deployment testing
- Action: Triggered automatic rollback to Phase 7
- Status: ✓ RESOLVED

Timeline:
- 02:00 UTC: Phase 8 deployment started
- 02:15 UTC: Database issue detected
- 02:17 UTC: Automatic rollback triggered
- 02:35 UTC: Phase 7 restored and verified
- 02:40 UTC: All systems operational

Impact:
- Actual downtime: 40 minutes (rollback duration)
- Data loss: None
- User data: Fully intact

Root Cause:
[Detailed technical explanation]

Next Steps:
- Phase 8 issues will be analyzed and fixed
- Retry deployment planned for [DATE]
- Root cause analysis meeting: [DATE/TIME]

Thank you for your patience.
```

### Post-Incident Communication (next business day)

**To**: All staff  
**Channel**: Email + meeting  
**Agenda**:
- What happened (incident timeline)
- Why it happened (root cause)
- What we did (response)
- What we learned (lessons)
- What's next (improvements)

---

## Testing & Validation

### Rollback Readiness Test (Monthly)

Perform monthly to ensure rollback procedures still work.

```bash
#!/bin/bash
# Monthly rollback readiness test

echo "=== Monthly Rollback Readiness Test ==="
echo "Date: $(date)"

# 1. Backup location check
echo "1. Checking backup availability..."
BACKUP_COUNT=$(ls /opt/basset-hound/backups/neo4j_*.dump.gz 2>/dev/null | wc -l)
if [ "$BACKUP_COUNT" -gt 0 ]; then
  echo "   ✓ Found $BACKUP_COUNT Neo4j backups"
else
  echo "   ✗ ERROR: No backups found!"
  exit 1
fi

# 2. Backup file integrity
echo "2. Checking backup integrity..."
LATEST_BACKUP=$(ls -t /opt/basset-hound/backups/neo4j_*.dump.gz | head -1)
if gzip -t "$LATEST_BACKUP"; then
  echo "   ✓ Latest backup is valid: $(basename "$LATEST_BACKUP")"
else
  echo "   ✗ ERROR: Latest backup is corrupted!"
  exit 1
fi

# 3. Docker image availability
echo "3. Checking Docker images..."
docker images | grep -q "basset_api" && echo "   ✓ API images available" || echo "   ⚠ API images not found"
docker images | grep -q "neo4j" && echo "   ✓ Neo4j images available" || echo "   ⚠ Neo4j images not found"

# 4. Disk space for recovery
echo "4. Checking disk space..."
AVAILABLE_GB=$(df /opt/basset-hound | tail -1 | awk '{print $4}')
BACKUP_GB=$(du -s /opt/basset-hound/backups | awk '{print $1}' | numfmt --to=iec)
echo "   Available: $AVAILABLE_GB KB ($(($AVAILABLE_GB/1024/1024)) GB)"
echo "   Needed for recovery: ~$BACKUP_GB"

if [ "$AVAILABLE_GB" -gt $((5*1024*1024)) ]; then
  echo "   ✓ Sufficient disk space"
else
  echo "   ✗ WARNING: Low disk space!"
fi

# 5. Procedure documentation
echo "5. Checking documentation..."
if [ -f "/opt/basset-hound/docs/ROLLBACK-PROCEDURES.md" ]; then
  echo "   ✓ Rollback procedures documented"
else
  echo "   ✗ ERROR: Procedures not found!"
fi

# 6. Contact information
echo "6. Checking emergency contacts..."
if [ -f "/opt/basset-hound/docs/ROLLBACK-PROCEDURES.md" ]; then
  if grep -q "emergency" /opt/basset-hound/docs/ROLLBACK-PROCEDURES.md; then
    echo "   ✓ Emergency contacts available"
  else
    echo "   ⚠ Emergency contacts not documented"
  fi
fi

echo ""
echo "=== Test Complete ==="
```

### Pre-Deployment Test

Run 48 hours before any major deployment.

```bash
#!/bin/bash
# Pre-deployment rollback test (non-destructive)

echo "=== Pre-Deployment Rollback Readiness Test ==="

# 1. Current system snapshot
echo "1. Creating pre-deployment snapshot..."
docker stats --no-stream > /tmp/pre_deployment_stats.txt
docker inspect basset_api > /tmp/pre_deployment_api_state.json

# 2. Verify backup procedures work
echo "2. Testing backup procedures..."
/opt/basset-hound/scripts/backup.sh > /tmp/test_backup.log 2>&1
if [ $? -eq 0 ]; then
  echo "   ✓ Backup procedure works"
else
  echo "   ✗ Backup procedure failed"
  cat /tmp/test_backup.log
fi

# 3. Verify restore procedures (on test environment only!)
echo "3. [SKIP on production] Verifying restore procedures..."
echo "   (Only run on staging/test environment)"

# 4. Network connectivity
echo "4. Testing network connectivity..."
curl -s http://localhost:8080/health | grep -q "healthy" && echo "   ✓ API accessible" || echo "   ✗ API not responding"
docker exec neo4j_osint_db cypher-shell -u neo4j -p neo4jbasset "RETURN 1" > /dev/null 2>&1 && echo "   ✓ Neo4j accessible" || echo "   ✗ Neo4j not responding"

# 5. Verify rollback contacts
echo "5. Verifying rollback contacts..."
if [ -n "$SLACK_WEBHOOK" ]; then
  echo "   ✓ Slack webhook configured"
else
  echo "   ⚠ Slack webhook not set"
fi

echo ""
echo "=== Pre-Deployment Test Complete ==="
echo "Status: READY FOR DEPLOYMENT" 
```

---

## Troubleshooting

### Issue: Neo4j fails to restore

**Symptoms**: `neo4j-admin database load` command hangs or fails

**Diagnostics**:
```bash
# Check Neo4j status
docker compose logs neo4j | tail -50

# Check disk space
df -h

# Verify backup file
gunzip -t /opt/basset-hound/backups/neo4j_*.dump.gz
```

**Solutions**:
1. Increase disk space: `df -h` should show >20GB available
2. Clear old logs: `docker compose logs --tail 0 > /dev/null`
3. Restart Neo4j: `docker compose restart neo4j`
4. Try different backup: `ls -t /opt/basset-hound/backups/neo4j_*.dump.gz | sed -n '2p'`

### Issue: Services fail to start after rollback

**Symptoms**: Containers exit immediately or hang

**Diagnostics**:
```bash
docker compose logs basset_api | tail -20
docker compose logs neo4j | tail -20
docker compose logs redis | tail -20
```

**Solutions**:
1. Check image compatibility: `docker images | grep basset`
2. Reset docker state: `docker system prune --volumes`
3. Rebuild images: `docker compose build --no-cache`
4. Check network: `docker network inspect basset-hound`

### Issue: Data appears corrupted after rollback

**Symptoms**: Missing entities, broken relationships, validation errors

**Diagnostics**:
```bash
# Verify node count
docker exec neo4j_osint_db cypher-shell -u neo4j -p neo4jbasset "MATCH (n) RETURN count(n);"

# Check for constraint violations
docker exec neo4j_osint_db cypher-shell -u neo4j -p neo4jbasset "CALL apoc.schema.assert({}, {});"

# Export sample data
docker exec neo4j_osint_db cypher-shell -u neo4j -p neo4jbasset "MATCH (n) LIMIT 10 RETURN n;"
```

**Solutions**:
1. Verify different backup: Try older backup file
2. Check backup before last deployment: `ls -t /opt/basset-hound/backups/neo4j_*.dump.gz | sed -n '3,5p'`
3. Restore from clean database: `MATCH (n) DETACH DELETE n;` (use with caution!)

### Issue: Rollback takes too long (>1 hour)

**Symptoms**: Exceeds expected 30-60 minute window

**Diagnostics**:
```bash
# Check I/O performance
iostat -x 5

# Check CPU
top -n 1 | head -15

# Check network (if using remote backups)
iftop -i eth0
```

**Solutions**:
1. Parallelize recovery: Restore Redis/API while Neo4j loads
2. Use faster storage: Ensure `/opt/basset-hound` is on SSD
3. Increase resources: Temporarily increase Neo4j memory/CPU
4. Partial recovery: Restore only essential projects

---

## Risk Assessment

### Rollback Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Data loss | Low | Critical | Multiple backups, tested restore |
| Incomplete rollback | Medium | High | Validation checklist, monitoring |
| Service degradation | Medium | High | Phase 7 performance baseline |
| Cascading failures | Low | Critical | Service dependency verification |
| Extended downtime | Medium | High | Parallel recovery procedures |

### Mitigation Strategies

1. **Data Protection**
   - Daily automated backups
   - Weekly full backups
   - Monthly snapshots
   - Backup verification tests
   - Off-site backup copies (recommended)

2. **Procedure Reliability**
   - Monthly procedure tests
   - Pre-deployment dry runs
   - Documentation reviews
   - Runbook automation (scripts)
   - Version control for all configs

3. **Communication**
   - 24-hour advance notice
   - Hourly status updates
   - Post-incident reviews
   - Stakeholder awareness
   - Emergency escalation plan

4. **Monitoring**
   - Real-time error tracking
   - Automated alerting
   - Service health dashboards
   - Performance baselines
   - Anomaly detection

### Success Criteria

Rollback is successful when:
- ✅ All services running and healthy
- ✅ Database has expected node count
- ✅ API responding to requests
- ✅ Frontend loads without errors
- ✅ Data integrity verified
- ✅ No increase in error rates
- ✅ Performance within baseline
- ✅ All integrations functional

---

## Emergency Contacts

### Escalation Hierarchy

1. **On-Call Engineer** (First responder)
   - Available 24/7
   - Executes rollback procedures
   - Initial assessment and decisions

2. **DevOps Lead** (Escalation)
   - Contacted if on-call needs help
   - Oversees complex scenarios
   - Approves partial rollbacks

3. **Engineering Manager** (Approval)
   - Approves major rollbacks
   - Communicates with stakeholders
   - Authorizes emergency procedures

4. **Executive Sponsor** (Final approval)
   - Contacted for critical incidents
   - Communicates with customers
   - Approves extended downtime

### Contact Template

```
=== INCIDENT CONTACTS ===

ON-CALL ENGINEER (24/7)
Name: [Name]
Phone: [Phone]
Email: [Email]
Slack: @[Handle]
On-call period: [Dates]

DEVOPS LEAD
Name: [Name]
Phone: [Phone]
Email: [Email]
Slack: @[Handle]

ENGINEERING MANAGER
Name: [Name]
Phone: [Phone]
Email: [Email]
Slack: @[Handle]

STAKEHOLDER NOTIFIER
Name: [Name]
Email: [Email]
Slack: @[Handle]
Responsibility: Customer communications

INFRASTRUCTURE TEAM
Slack: #incident-management
Email: ops@example.com
Page/Alert: [System name]

=== ESCALATION PROCEDURES ===

Step 1 (minutes 0-10):
- On-call engineer assesses situation
- Decision: Fix forward or rollback?
- If rollback: Proceed with procedures

Step 2 (minutes 10-30):
- If taking >20 min, contact DevOps Lead
- Brief on situation and ETA
- Get approval for escalation

Step 3 (minutes 30-60):
- If still ongoing, contact Engineering Manager
- Update status page every 10 minutes
- Customer communications if >1 hour

Step 4 (>60 minutes):
- Contact Executive Sponsor
- Begin post-incident review
- Prepare customer communication
```

---

## Appendix: Useful Commands

### Quick Health Check
```bash
docker compose ps
curl http://localhost:8080/health
docker exec neo4j_osint_db cypher-shell -u neo4j -p neo4jbasset "MATCH (n) RETURN count(n);"
```

### View Logs
```bash
docker compose logs -f basset_api          # Last 100 lines, follow
docker compose logs --since 1h             # Last hour
docker logs basset_api 2>&1 | head -50     # Specific service
```

### Database Queries
```bash
# Count entities
docker exec neo4j_osint_db cypher-shell -u neo4j -p neo4jbasset "MATCH (n) RETURN count(n);"

# List node types
docker exec neo4j_osint_db cypher-shell -u neo4j -p neo4jbasset \
  "MATCH (n) RETURN distinct labels(n) AS types;"

# Check indexes
docker exec neo4j_osint_db cypher-shell -u neo4j -p neo4jbasset "CALL db.indexes();"
```

### Cache Commands
```bash
docker exec basset_redis redis-cli PING
docker exec basset_redis redis-cli DBSIZE
docker exec basset_redis redis-cli FLUSHDB   # Clear cache
docker exec basset_redis redis-cli INFO memory
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.1.0 | 2026-05-19 | Initial comprehensive rollback procedures |
| 2.0.0 | 2026-05-07 | Phase 8 deployment (baseline) |
| 1.9.0 | 2026-04-30 | Phase 7 stable version |

---

**Last Updated**: 2026-05-19  
**Status**: PRODUCTION READY  
**Maintenance**: Review quarterly, test monthly  
**Owner**: DevOps Team
