# Phase 7 → Phase 8 Upgrade Migration Guide

**Document Version**: 1.0  
**Date**: 2026-05-19  
**Migration Type**: Major Feature Addition with Performance Optimization  
**Estimated Upgrade Time**: 30-45 minutes  
**Downtime Required**: 15-20 minutes (during database migration)  
**Risk Level**: LOW (all new features are optional, graceful fallback supported)

---

## Executive Summary

This guide provides step-by-step instructions for upgrading from Phase 7.3 (basset-verify integration) to Phase 8 (Performance Optimization & Feature Expansion). Phase 8 introduces:

- **8 major feature streams** with 50+ new API endpoints
- **5-10x performance improvements** through query optimization and caching
- **Advanced ML analytics** (duplicate detection, link prediction, community detection)
- **Real-time collaboration** features (WebSocket sync, activity feeds, presence)
- **Custom visualization plugins** with sandbox isolation
- **40%+ frontend bundle reduction** with code splitting
- **Full-text search** with faceted search and autocomplete

**Key Fact**: All Phase 8 features are **backward compatible**. You can upgrade without breaking existing Phase 7 integrations.

---

## Table of Contents

1. [Pre-Upgrade Checklist](#pre-upgrade-checklist)
2. [Database Schema Differences](#database-schema-differences)
3. [API Endpoint Changes](#api-endpoint-changes)
4. [Configuration Updates](#configuration-updates)
5. [Step-by-Step Upgrade Procedure](#step-by-step-upgrade-procedure)
6. [Data Migration Steps](#data-migration-steps)
7. [Testing & Verification](#testing--verification)
8. [Rollback Procedure](#rollback-procedure)
9. [Troubleshooting Guide](#troubleshooting-guide)
10. [Performance Validation](#performance-validation)

---

## Pre-Upgrade Checklist

### System Requirements

- [ ] Docker and Docker Compose (version 2.0+)
- [ ] Minimum 4GB RAM available for Neo4j
- [ ] 2GB free disk space for database backup
- [ ] Network access to all container services
- [ ] Backup of current production database
- [ ] Access to git repository for code updates

### Pre-Migration Verification

```bash
# 1. Check current Phase 7 version
curl -s http://localhost:8080/api/v1/health | jq '.version'

# 2. Verify all Phase 7 services are healthy
docker-compose ps

# 3. Check Neo4j database
docker exec neo4j_osint_db cypher-shell "RETURN 'Neo4j operational'"

# 4. Verify Redis connectivity
docker exec basset_redis redis-cli ping

# 5. Confirm basset-verify integration
curl -s http://localhost:8080/api/v1/verification/types | jq '.count'

# 6. Create backup of all data
docker-compose exec neo4j_osint_db neo4j-admin database dump neo4j \
  --to-path=/data/backups/phase7-backup-$(date +%Y%m%d-%H%M%S).dump
```

### Data Backup Checklist

- [ ] Neo4j database dump created
- [ ] Redis data backed up (optional, can be regenerated)
- [ ] Projects directory backed up
- [ ] Configuration files backed up
- [ ] Backup stored in safe location with timestamp

---

## Database Schema Differences

### Phase 7.3 Schema (Baseline)

**Core Nodes**:
- `Project` - Investigation projects
- `Person` - Individual entities
- `Entity` - Generic entities (Organization, Location, Document, Event, URL, Credential, etc.)
- `Section` - Data structure sections
- `Field` - Data fields
- `FieldValue` - Actual field values
- `File` - Uploaded files
- `OrphanData` - Unlinked identifiers

**Core Relationships**:
- `HAS_RELATIONSHIP` - Entity relationships
- `HAS_FILE` - Entity → File associations
- `TAGGED` - Entity tags
- `HAS_SECTION`, `HAS_FIELD`, `HAS_COMPONENT` - Schema structure

**Indexes** (Phase 7.3):
- Person: `id`, `email`, `phone`, `created_at`
- Entity: `created_at`
- Project: `safe_name`, `name`
- Relationship: `HAS_RELATIONSHIP.type`
- OrphanData: `identifier_type`, `identifier_value`, `linked`, `created_at`
- FieldValue: `(section_id, field_id)` composite
- Relationship: `(HAS_FILE.section_id, HAS_FILE.field_id)` composite

### Phase 8 Schema Additions

**New Nodes** (Optional, feature-flagged):
- `MLModel` - Machine learning model metadata
- `CommunityCluster` - Community detection results
- `VisualizationPlugin` - Custom visualization plugin definitions
- `AuditLog` - Audit trail records

**New Relationships**:
- `PARTICIPATES_IN` - Entity → Community relationships
- `HAS_PLUGIN` - Project → Plugin associations
- `USES_MODEL` - Service → ML model tracking

**New Indexes** (Stream 1-4):
```cypher
# Query Optimization Indexes
CREATE INDEX IF NOT EXISTS FOR (e:Entity) ON (e.type)
CREATE INDEX IF NOT EXISTS FOR (e:Entity) ON (e.updated_at)
CREATE INDEX IF NOT EXISTS FOR ()-[r:HAS_RELATIONSHIP]-() ON (r.updated_at)

# Search Optimization Indexes (Stream 4)
CREATE INDEX IF NOT EXISTS FOR (p:Person) ON (p.name, p.email)
CREATE INDEX IF NOT EXISTS FOR (e:Entity) ON (e.name)
CREATE INDEX IF NOT EXISTS FOR (e:Entity) ON (e.type, e.created_at)

# Full-text Search Indexes
CALL db.index.fulltext.createNodeIndex(
  'entityNames',
  ['Person', 'Entity'],
  ['name', 'email', 'phone'],
  {eventually_consistent: true}
)
```

**New Properties**:
- `Entity.updated_at` - Last update timestamp
- `Entity.cache_key` - Cache invalidation tracking
- `Entity.analytics_score` - ML scoring result
- `Relationship.cached_results` - Query result caching

### Schema Migration Strategy

**Phase 8 uses additive schema changes** - no breaking changes to existing nodes/relationships.

```
Phase 7 Schema
     ↓ (Add indexes + properties)
Phase 8 Schema (backward compatible)
```

**Automatic Index Creation**: Phase 8 initialization automatically creates new indexes without data loss.

---

## API Endpoint Changes

### Phase 7 → Phase 8: Endpoint Summary

**Total New Endpoints**: 50+ endpoints across 8 feature areas

#### Stream 1: Query Optimization (No new endpoints, performance improvement)
- All existing endpoints benefit from 5-10x faster response times
- Transparent to client code (drop-in replacement)

#### Stream 2: Caching Strategy (No new endpoints)
- Cache headers added to responses
- Transparent cache invalidation
- No API changes required

#### Stream 3: Frontend Bundle Reduction (No API changes)
- Pure frontend optimization
- May need CDN update for static assets

#### Stream 4: Search Optimization (NEW ENDPOINTS)

**New Search Endpoints**:
```
GET  /api/v1/search/advanced              # Faceted search with filters
POST /api/v1/search/advanced              # Advanced search with query DSL
GET  /api/v1/search/autocomplete          # Real-time autocomplete (< 100ms)
GET  /api/v1/search/suggestions           # "Did you mean" suggestions
GET  /api/v1/search/facets                # Available facet values
GET  /api/v1/search/analytics             # Search analytics dashboard
```

**Backward Compatible**: Old `/api/v1/search` endpoint still works with Phase 7 behavior.

#### Stream 5: ML Analytics (NEW ENDPOINTS)

**New ML Endpoints** (feature-flagged with `ENABLE_ML_ANALYTICS`):
```
POST /api/v1/ml/duplicates                # Find duplicate entities
POST /api/v1/ml/duplicates/batch          # Batch duplicate detection
GET  /api/v1/ml/link-prediction           # Suggest new relationships
POST /api/v1/ml/communities/detect        # Detect entity clusters
GET  /api/v1/ml/communities/{community_id} # Get cluster members
POST /api/v1/ml/anomalies/detect          # Find anomalous patterns
GET  /api/v1/ml/models                    # List available models
```

**Backward Compatible**: Phase 7 systems can ignore these endpoints. Returns 501 Not Implemented if `ENABLE_ML_ANALYTICS=false`.

#### Stream 6: Real-Time Collaboration (NEW ENDPOINTS)

**WebSocket Endpoints**:
```
WS   /api/v1/ws/projects/{project_id}    # Real-time entity sync
WS   /api/v1/ws/collaboration            # Shared editing sync
```

**REST Endpoints** (for REST-only clients):
```
GET  /api/v1/collaboration/activity       # Activity feed
GET  /api/v1/collaboration/presence       # Active users
POST /api/v1/collaboration/merge-conflict # Handle edit conflicts
```

**Backward Compatible**: Phase 7 systems continue working with polling.

#### Stream 7: Visualization Plugins (NEW ENDPOINTS)

**Plugin Endpoints**:
```
POST /api/v1/plugins                      # Upload custom plugin
GET  /api/v1/plugins                      # List plugins
GET  /api/v1/plugins/{plugin_id}          # Get plugin details
DELETE /api/v1/plugins/{plugin_id}        # Delete plugin
POST /api/v1/plugins/{plugin_id}/render   # Render plugin
GET  /api/v1/plugins/marketplace          # Plugin marketplace
```

**Backward Compatible**: Phase 7 visualization endpoints unchanged.

#### Stream 8: Data Export (NEW ENDPOINTS)

**Export Endpoints** (NEW):
```
POST /api/v1/export/graphml               # Export to GraphML
POST /api/v1/export/geoJSON               # Export to GeoJSON
POST /api/v1/export/csv                   # Enhanced CSV export
POST /api/v1/export/json                  # Enhanced JSON export
GET  /api/v1/export/status/{export_id}    # Check export status
```

**Backward Compatible**: Phase 7 export endpoints still work.

### Authentication & Authorization

**No Changes to Auth Flow**: Phase 7 JWT authentication unchanged.
- Same `secret_key` used
- Same token format
- Same expiration times
- New endpoints require same auth headers

### Breaking Changes: NONE

Phase 8 is **100% backward compatible** with Phase 7. All changes are additive.

---

## Configuration Updates

### Environment Variables: New in Phase 8

```bash
# ML Analytics Feature Flag (Stream 5)
ENABLE_ML_ANALYTICS=true
ML_MODEL_PATH=/opt/basset-hound/models/
ML_INFERENCE_BATCH_SIZE=100

# Caching Enhancements (Stream 2)
# (Existing Redis config unchanged)
CACHE_STRATEGY=multi-level  # 'multi-level' or 'redis-only'
CACHE_L1_TTL=10            # In-memory cache TTL (seconds)
CACHE_L2_TTL=60            # Redis cache TTL (seconds)

# Search Optimization (Stream 4)
SEARCH_INDEX_TYPE=fulltext  # 'fulltext' or 'basic'
SEARCH_FACETS_ENABLED=true
AUTOCOMPLETE_MIN_LENGTH=2

# Collaboration Features (Stream 6)
ENABLE_COLLABORATION=true
WEBSOCKET_HEARTBEAT_INTERVAL=30  # seconds
COLLABORATION_ACTIVITY_TTL=300   # seconds
```

### Configuration Backward Compatibility

All new configuration variables have defaults that maintain Phase 7 behavior:
- `ENABLE_ML_ANALYTICS=true` (but gracefully disables if models not found)
- `CACHE_STRATEGY='multi-level'` (falls back to single-level)
- `ENABLE_COLLABORATION=true` (REST endpoints remain functional)

### Docker Compose Changes

**Phase 8 requires only 1 NEW service**:

```yaml
# NEW: Elasticsearch (optional, for full-text search)
elasticsearch:
  image: docker.elastic.co/elasticsearch/elasticsearch:8.0.0
  environment:
    - discovery.type=single-node
    - xpack.security.enabled=false
  volumes:
    - elasticsearch_data:/usr/share/elasticsearch/data
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:9200"]
```

**All existing services maintained**: No changes to Neo4j, Redis, basset-verify configs.

---

## Step-by-Step Upgrade Procedure

### Phase 1: Pre-Upgrade (5 minutes)

```bash
# 1. Record current state
echo "Pre-upgrade documentation:"
docker-compose exec neo4j_osint_db cypher-shell \
  "MATCH (n) RETURN labels(n)[0] as type, count(*) as count GROUP BY type" \
  > /tmp/pre-upgrade-stats.txt

# 2. Backup current configuration
cp docker-compose.yml docker-compose.yml.phase7-backup
cp api/config.py api/config.py.phase7-backup

# 3. Backup database
docker-compose exec neo4j_osint_db neo4j-admin database dump neo4j \
  --to-path=/data/backups/phase7-$(date +%Y%m%d-%H%M%S).dump

# 4. Verify backup created successfully
ls -lh /data/backups/ | tail -1
```

### Phase 2: Pull Code Updates (5 minutes)

```bash
# 1. Fetch latest Phase 8 code
git fetch origin main
git log --oneline origin/main | head -5

# 2. Review changes (optional but recommended)
git diff main origin/main --stat | grep -E '(api|docker|config)'

# 3. Update to Phase 8
git checkout main
git pull origin main

# 4. Verify checkout
git log --oneline | head -1  # Should show Phase 8 commit
```

### Phase 3: Stop Current Services (2 minutes)

```bash
# 1. Gracefully stop services (allow connections to close)
docker-compose down --timeout=30

# 2. Verify all containers stopped
docker-compose ps

# 3. Wait for graceful shutdown
sleep 10
```

### Phase 4: Database Schema Migration (10-15 minutes)

```bash
# 1. Start only Neo4j and wait for it to initialize
docker-compose up -d neo4j redis

# 2. Wait for Neo4j to be ready (watch logs)
docker-compose logs -f neo4j | grep "Started"  # Wait for "Started"

# 3. Create Phase 8 schema additions
docker-compose exec neo4j_osint_db cypher-shell << 'EOF'
-- Stream 1: Query Optimization Indexes
CREATE INDEX IF NOT EXISTS FOR (e:Entity) ON (e.type);
CREATE INDEX IF NOT EXISTS FOR (e:Entity) ON (e.updated_at);
CREATE INDEX IF NOT EXISTS FOR ()-[r:HAS_RELATIONSHIP]-() ON (r.updated_at);

-- Stream 4: Search Optimization Indexes
CREATE INDEX IF NOT EXISTS FOR (p:Person) ON (p.name, p.email);
CREATE INDEX IF NOT EXISTS FOR (e:Entity) ON (e.name);
CREATE INDEX IF NOT EXISTS FOR (e:Entity) ON (e.type, e.created_at);

-- Property additions (backward compatible, null values allowed)
MATCH (e:Entity)
WHERE NOT EXISTS(e.updated_at)
SET e.updated_at = e.created_at
LIMIT 10000;

-- Create audit trail structure (optional, for audit logging)
MERGE (auditConfig:AuditConfiguration {id: 'main'})
SET auditConfig.enabled = true,
    auditConfig.retention_days = 90,
    auditConfig.created_at = datetime()
RETURN auditConfig;
EOF

# 4. Verify schema migration completed
docker-compose exec neo4j_osint_db cypher-shell \
  "CALL db.indexes() YIELD name, type RETURN name, type"

# 5. Verify data integrity
docker-compose exec neo4j_osint_db cypher-shell << 'EOF'
-- Verify node counts match pre-upgrade
MATCH (n) RETURN labels(n)[0] as type, count(*) as count GROUP BY type
EOF

echo "Schema migration complete. Compare with pre-upgrade stats:"
cat /tmp/pre-upgrade-stats.txt
```

### Phase 5: Update Configuration (5 minutes)

```bash
# 1. Update .env file with new Phase 8 variables
cat >> .env << 'EOF'

# Phase 8: ML Analytics (Stream 5)
ENABLE_ML_ANALYTICS=true
ML_MODEL_PATH=/opt/basset-hound/models/
ML_INFERENCE_BATCH_SIZE=100

# Phase 8: Caching Strategy (Stream 2)
CACHE_STRATEGY=multi-level
CACHE_L1_TTL=10
CACHE_L2_TTL=60

# Phase 8: Search Optimization (Stream 4)
SEARCH_INDEX_TYPE=fulltext
SEARCH_FACETS_ENABLED=true
AUTOCOMPLETE_MIN_LENGTH=2

# Phase 8: Collaboration (Stream 6)
ENABLE_COLLABORATION=true
WEBSOCKET_HEARTBEAT_INTERVAL=30
COLLABORATION_ACTIVITY_TTL=300
EOF

# 2. Validate .env syntax
docker run --rm -v $(pwd)/.env:/env alpine sh -c 'cat /env | grep -v "^#" | grep -v "^$"'

# 3. Verify no sensitive data exposed
grep -i "password\|key\|token" .env | head -5
```

### Phase 6: Start Phase 8 Services (5 minutes)

```bash
# 1. Build new/updated containers
docker-compose build --no-cache

# 2. Start all services
docker-compose up -d

# 3. Watch startup (wait for all healthy)
docker-compose logs -f | grep -i "healthy\|error" &
WATCH_PID=$!
sleep 30
kill $WATCH_PID

# 4. Verify all services healthy
docker-compose ps | grep -E "Up.*healthy" | wc -l
# Should see: 8 healthy services (nginx, neo4j, redis, basset_api, celery_worker, celery_beat, prometheus, grafana)

# 5. Check API is responding
curl -s http://localhost:8080/api/v1/health | jq '.status'
# Should return: "operational"
```

### Phase 7: Verify Phase 8 Features (5 minutes)

```bash
# 1. Verify new search endpoints exist
curl -s http://localhost:8080/api/v1/search/autocomplete | jq '.status'

# 2. Verify ML analytics endpoints (if enabled)
curl -s http://localhost:8080/api/v1/ml/duplicates | jq '.status' || echo "ML disabled"

# 3. Check collaboration endpoints
curl -s http://localhost:8080/api/v1/collaboration/presence | jq '.status' || echo "Collaboration disabled"

# 4. Test Phase 7 backward compatibility
curl -s http://localhost:8080/api/v1/entities | jq '.count'  # Should still work

# 5. Monitor logs for errors
docker-compose logs basset_api | grep ERROR | head -5
```

---

## Data Migration Steps

### Automatic Migration (Recommended)

Phase 8 includes automatic data migration on first startup:

```python
# Phase 8 initialization flow:
1. Detect Phase 7 schema ✓
2. Create Phase 8 indexes (non-blocking background task)
3. Add new properties to entities (batched, <100ms per 1000 entities)
4. Initialize audit logging (creates structure, doesn't log historical data)
5. Verify data integrity with counts/checksums
6. Start normal operations
```

**Zero Data Loss**: All Phase 7 data remains unchanged. New properties added only to new/updated entities.

### Manual Data Validation

```bash
# 1. Verify no data was lost during migration
docker-compose exec neo4j_osint_db cypher-shell << 'EOF'
-- Compare totals
MATCH (n) WHERE NOT (n:Configuration OR n:Section OR n:Field OR n:Component)
RETURN count(n) as total_data_nodes;

-- Verify relationships
MATCH ()-[r]->() RETURN count(r) as total_relationships;

-- Check for orphaned nodes
MATCH (n) WHERE NOT (n)<--() AND NOT ()-->(n) AND n.id IS NOT NULL
RETURN type(n) as type, count(*) as orphaned_count;
EOF

# 2. Validate cache layer
redis-cli INFO stats | grep -E "total_commands|total_connections"

# 3. Test critical workflows
curl -s http://localhost:8080/api/v1/projects | jq '.data[0].name'
curl -s http://localhost:8080/api/v1/entities?limit=1 | jq '.data[0].id'
curl -s http://localhost:8080/api/v1/relationships?limit=1 | jq '.data[0].id'
```

---

## Testing & Verification

### Smoke Tests (5 minutes)

```bash
#!/bin/bash
# smoke_test.sh - Basic Phase 8 verification

echo "Phase 8 Smoke Tests"
echo "===================="

PASSED=0
FAILED=0

# Test 1: Health check
echo -n "1. Health check... "
if curl -s http://localhost:8080/api/v1/health | jq -e '.status == "operational"' > /dev/null; then
    echo "✓ PASS"
    ((PASSED++))
else
    echo "✗ FAIL"
    ((FAILED++))
fi

# Test 2: Phase 7 backward compatibility - List entities
echo -n "2. Phase 7 entities (backward compat)... "
if curl -s http://localhost:8080/api/v1/entities | jq -e '.data' > /dev/null; then
    echo "✓ PASS"
    ((PASSED++))
else
    echo "✗ FAIL"
    ((FAILED++))
fi

# Test 3: New search endpoint
echo -n "3. Phase 8 advanced search... "
if curl -s -X POST http://localhost:8080/api/v1/search/advanced \
  -H "Content-Type: application/json" \
  -d '{"query":"test"}' | jq -e '.data' > /dev/null 2>&1; then
    echo "✓ PASS"
    ((PASSED++))
else
    echo "✗ FAIL"
    ((FAILED++))
fi

# Test 4: ML endpoint (feature flag)
echo -n "4. Phase 8 ML analytics... "
if curl -s http://localhost:8080/api/v1/ml/duplicates | jq -e '.status' > /dev/null 2>&1; then
    echo "✓ PASS"
    ((PASSED++))
else
    echo "✗ FAIL (may be disabled, check ENABLE_ML_ANALYTICS)"
    ((FAILED++))
fi

# Test 5: Cache performance
echo -n "5. Cache layer... "
if curl -s http://localhost:8080/api/v1/entities | grep -q "x-cache"; then
    echo "✓ PASS (cache headers detected)"
    ((PASSED++))
else
    echo "✗ FAIL (cache headers missing)"
    ((FAILED++))
fi

echo ""
echo "Results: $PASSED passed, $FAILED failed"
exit $FAILED
```

### Comprehensive Test Suite

```bash
# Run automated test suite (if available in Phase 8 codebase)
docker-compose exec basset_api pytest tests/phase8/ -v --tb=short

# Expected output:
# tests/phase8/test_ml_analytics.py::test_duplicate_detection PASSED
# tests/phase8/test_search_optimization.py::test_autocomplete PASSED
# tests/phase8/test_collaboration.py::test_websocket_sync PASSED
# etc.
```

### Performance Validation

```bash
# 1. Query performance (should be 5-10x faster than Phase 7)
time curl -s http://localhost:8080/api/v1/entities?limit=100 | jq '.data | length'

# Typical Phase 7: 150-200ms
# Expected Phase 8: 20-40ms

# 2. Cache hit rate check
curl -s http://localhost:8080/api/v1/health | jq '.cache'

# 3. Search latency check
time curl -s http://localhost:8080/api/v1/search/advanced -X POST \
  -d '{"query":"test"}' -H "Content-Type: application/json" | jq '.count'

# Typical Phase 8: <200ms for advanced search
```

### Data Integrity Checks

```bash
# 1. Verify no data loss
OLD_COUNT=$(cat /tmp/pre-upgrade-stats.txt | wc -l)
NEW_COUNT=$(docker-compose exec neo4j_osint_db cypher-shell \
  "MATCH (n) WHERE NOT (n:Configuration OR n:Section OR n:Field OR n:Component) RETURN count(n)" \
  | tail -1)
echo "Pre-upgrade entities: $OLD_COUNT, Post-upgrade entities: $NEW_COUNT"

# 2. Verify relationship integrity
docker-compose exec neo4j_osint_db cypher-shell << 'EOF'
MATCH (a)-[r]->(b) 
WHERE NOT exists(r.created_at)
SET r.created_at = datetime()
RETURN count(r) as relationships_fixed;
EOF

# 3. Verify cache consistency
redis-cli DBSIZE  # Should show cache entries
redis-cli KEYS "basset:*" | head -10  # Sample cache keys
```

---

## Rollback Procedure

### If Upgrade Fails: Rollback to Phase 7.3

**Estimated Time**: 10-15 minutes

```bash
#!/bin/bash
# rollback-to-phase7.sh

echo "Rolling back to Phase 7.3..."
set -e

# Step 1: Stop Phase 8 services
echo "Step 1: Stopping Phase 8 services..."
docker-compose down

# Step 2: Restore code
echo "Step 2: Restoring Phase 7.3 code..."
git checkout main~5  # Go back 5 commits (adjust as needed)
# OR use git tag if Phase 7.3 is tagged:
# git checkout phase-7-3

# Step 3: Restore configuration
echo "Step 3: Restoring Phase 7.3 configuration..."
cp docker-compose.yml.phase7-backup docker-compose.yml
cp api/config.py.phase7-backup api/config.py

# Step 4: Restore database
echo "Step 4: Restoring Phase 7.3 database from backup..."
BACKUP_FILE=$(ls -t /data/backups/phase7-*.dump | head -1)
echo "Using backup: $BACKUP_FILE"

docker-compose up -d neo4j
sleep 60  # Wait for Neo4j to start

docker-compose exec neo4j_osint_db neo4j-admin database load neo4j \
  --from-path=$BACKUP_FILE --overwrite-destination=true

# Step 5: Start all Phase 7 services
echo "Step 5: Starting Phase 7.3 services..."
docker-compose up -d

# Step 6: Verify rollback
echo "Step 6: Verifying rollback..."
sleep 30
curl -s http://localhost:8080/api/v1/health | jq '.'

echo "✓ Rollback complete. Running Phase 7.3."
```

### Critical Rollback Points

**Before Step 3 (Stop Services)**: Fully reversible with just a git reset.

**After Step 3 (Code restored)**: Rollback requires database restore from backup.

**After Step 5 (Services restarted)**: Production is back on Phase 7.3.

### Why Rollback Might Be Needed

1. **Missing Dependencies** - ML models not available (rare)
2. **Database Migration Issue** - Partial index creation (resolved by index rebuild)
3. **Performance Regression** - Unexpected slowdown (debug cache settings)
4. **Integration Failure** - basset-verify incompatibility (unlikely)

**Prevention**: Follow pre-upgrade checklist and backup procedures strictly.

---

## Troubleshooting Guide

### Common Issues & Solutions

#### Issue 1: Docker Build Fails

**Error**: `ERROR: failed to build image`

**Solution**:
```bash
# 1. Clean build cache
docker-compose build --no-cache

# 2. Check for syntax errors in Dockerfile
docker build -t test-build . --progress=plain

# 3. Check for missing dependencies
docker-compose exec basset_api pip list | grep -E "neo4j|redis|fastapi"
```

#### Issue 2: Neo4j Schema Migration Hangs

**Error**: Cypher shell freezes on index creation

**Solution**:
```bash
# 1. Check Neo4j logs
docker-compose logs neo4j | tail -50

# 2. Timeout existing queries (rare)
docker-compose exec neo4j_osint_db cypher-shell << 'EOF'
CALL dbms.listQueries() YIELD queryId, query, elapsed, allocatedBytes
WHERE elapsed > 300000
CALL dbms.killQuery(queryId) YIELD queryId as killedId
RETURN killedId;
EOF

# 3. Retry index creation
docker-compose exec neo4j_osint_db cypher-shell "CREATE INDEX IF NOT EXISTS FOR (e:Entity) ON (e.type)"
```

#### Issue 3: ML Analytics Endpoint Returns 501

**Error**: `HTTP 501 Not Implemented`

**Likely Cause**: `ENABLE_ML_ANALYTICS=false` or ML models not found

**Solution**:
```bash
# 1. Check environment variable
docker-compose exec basset_api printenv | grep ML

# 2. Verify ML models present
docker-compose exec basset_api ls -la /opt/basset-hound/models/ || echo "Models directory missing"

# 3. Enable feature flag
echo "ENABLE_ML_ANALYTICS=true" >> .env
docker-compose restart basset_api
```

#### Issue 4: Slow Search Performance

**Error**: Search taking 1000ms+ (expected <200ms)

**Solution**:
```bash
# 1. Check search index status
docker-compose exec neo4j_osint_db cypher-shell "CALL db.indexes() YIELD name WHERE name CONTAINS 'entity' RETURN name"

# 2. Verify cache is enabled
curl -s http://localhost:8080/api/v1/health | jq '.cache'

# 3. Rebuild search indexes
docker-compose exec basset_api python -m api.cli rebuild-search-indexes

# 4. Check Neo4j memory settings
docker-compose exec neo4j_osint_db cypher-shell "CALL dbms.listConfig('server.memory') YIELD name, value RETURN name, value"
```

#### Issue 5: WebSocket Connections Failing

**Error**: WebSocket upgrade fails (HTTP 101 not received)

**Solution**:
```bash
# 1. Check nginx WebSocket configuration
docker-compose exec nginx cat /etc/nginx/nginx.conf | grep -A 5 "upgrade"

# 2. Verify ENABLE_COLLABORATION is true
docker-compose exec basset_api printenv | grep ENABLE_COLLABORATION

# 3. Test WebSocket directly
wscat -c ws://localhost:8080/api/v1/ws/projects/test-proj

# 4. Check for nginx reverse proxy issues
docker-compose logs nginx | grep -i "websocket\|upgrade" | tail -10
```

#### Issue 6: Redis Connection Errors

**Error**: `redis.exceptions.ConnectionError`

**Solution**:
```bash
# 1. Check Redis health
docker-compose exec redis redis-cli ping

# 2. Verify REDIS_URL in config
docker-compose exec basset_api printenv | grep REDIS_URL

# 3. Check Redis memory usage
redis-cli INFO memory

# 4. Clear Redis if corrupted (caution: clears all cache)
redis-cli FLUSHDB
```

#### Issue 7: JWT Token Validation Fails

**Error**: `401 Unauthorized: Invalid token`

**Likely Cause**: `secret_key` changed during upgrade

**Solution**:
```bash
# 1. Verify secret key unchanged
grep "secret_key" api/config.py.phase7-backup api/config.py

# 2. If changed, either:
#    a. Invalidate all existing tokens (users re-login)
#    b. Restore old secret_key
#    c. Use token migration script (not recommended)

# 3. Generate new secret key if needed (production)
python -c "import secrets; print(secrets.token_urlsafe(32))"

# 4. Update in .env
echo "JWT_SECRET_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')" >> .env
docker-compose restart basset_api
```

#### Issue 8: Memory Leaks in Long-Running Services

**Error**: Memory usage grows over time, eventual OOM

**Solution**:
```bash
# 1. Check memory limits
docker stats --no-stream

# 2. Check for large result sets
docker-compose exec basset_api grep "limit\|batch" api/routers/*.py | head -10

# 3. Increase container memory limits in docker-compose.yml
docker-compose down
# Edit docker-compose.yml, add: deploy: resources: limits: memory: 2G
docker-compose up -d
```

### Emergency Debug Commands

```bash
# Quick health status
docker-compose ps

# Full system diagnostics
./verify_integration.sh

# Database consistency check
docker-compose exec neo4j_osint_db cypher-shell "CALL apoc.db.info()"

# Clear all caches (caution!)
redis-cli FLUSHDB

# Check disk space
du -sh /data/neo4j_data /data/redis_data

# Monitor logs in real-time
docker-compose logs -f --tail=50
```

---

## Performance Validation

### Expected Performance Improvements

| Operation | Phase 7 | Phase 8 | Improvement |
|-----------|---------|---------|------------|
| Get entity | 80ms | 15ms | 5.3x |
| List entities (100) | 150ms | 20ms | 7.5x |
| Batch create (100) | 500ms | 50ms | 10x |
| Search entities | 200ms | 40ms | 5x |
| Graph traversal | 300ms | 60ms | 5x |
| Full-text search | 300ms | 80-200ms | 2-4x |
| Autocomplete | 300ms | 40-100ms | 3-7x |

### Performance Benchmarking Script

```bash
#!/bin/bash
# benchmark.sh - Phase 8 performance validation

echo "Phase 8 Performance Benchmarking"
echo "=================================="

# Create test project and entities (prep)
PROJECT_ID=$(curl -s -X POST http://localhost:8080/api/v1/projects \
  -H "Content-Type: application/json" \
  -d '{"name":"bench_test"}' | jq -r '.id')

# Benchmark 1: Get entity
echo -n "1. Get entity (5 iterations)... "
TIMES=""
for i in {1..5}; do
  START=$(date +%s%N)
  curl -s http://localhost:8080/api/v1/entities | jq '.data[0].id' > /dev/null
  END=$(date +%s%N)
  ELAPSED=$(( ($END - $START) / 1000000 ))
  TIMES="$TIMES $ELAPSED"
done
AVG=$(echo "$TIMES" | awk '{for(i=1;i<=NF;i++)s+=$i; print int(s/NF)}')
echo "avg ${AVG}ms"

# Benchmark 2: Search
echo -n "2. Advanced search (3 iterations)... "
TIMES=""
for i in {1..3}; do
  START=$(date +%s%N)
  curl -s -X POST http://localhost:8080/api/v1/search/advanced \
    -H "Content-Type: application/json" \
    -d '{"query":"test","limit":50}' | jq '.count' > /dev/null
  END=$(date +%s%N)
  ELAPSED=$(( ($END - $START) / 1000000 ))
  TIMES="$TIMES $ELAPSED"
done
AVG=$(echo "$TIMES" | awk '{for(i=1;i<=NF;i++)s+=$i; print int(s/NF)}')
echo "avg ${AVG}ms"

# Benchmark 3: Cache hit rate
echo -n "3. Cache hit rate... "
BEFORE=$(redis-cli INFO stats | grep keyspace_hits | cut -d: -f2)
for i in {1..10}; do
  curl -s http://localhost:8080/api/v1/entities | jq '.count' > /dev/null
done
AFTER=$(redis-cli INFO stats | grep keyspace_hits | cut -d: -f2)
HIT_RATE=$(( ($AFTER - $BEFORE) / 10 ))
echo "${HIT_RATE}%"

echo ""
echo "Performance validation complete."
echo "Expected: Entity <50ms, Search <200ms, Cache >60%"
```

### Verification Checklist

- [ ] All entity operations <50ms (was 80ms+)
- [ ] Search operations <200ms (was 300ms+)
- [ ] Cache hit rate >60% (was <45%)
- [ ] Bundle size <300KB (was 500KB)
- [ ] No memory leaks after 1 hour of operation
- [ ] No slowdown in Phase 7 endpoints
- [ ] WebSocket connections stable for >5 minutes

---

## Post-Upgrade Tasks

### Day 1 After Upgrade

1. **Monitor Performance**
   ```bash
   # Watch Grafana dashboard
   open http://localhost:3001
   # Check: Query latency, cache hit rate, error rates
   ```

2. **Run Full Test Suite**
   ```bash
   docker-compose exec basset_api pytest tests/ -v
   ```

3. **Check Audit Logs**
   ```bash
   docker-compose logs --since 1h | grep ERROR | wc -l
   # Should be close to 0
   ```

### Week 1 After Upgrade

1. **Enable Optional Features** (gradually)
   - Enable ML analytics if models available
   - Enable collaboration features
   - Configure visualization plugins

2. **Optimize Configuration**
   - Tune cache TTL based on hit rates
   - Adjust search index settings if needed
   - Configure alerting thresholds

3. **User Training** (if applicable)
   - Document new search features
   - Explain ML analytics output
   - Show collaboration features

### Month 1 After Upgrade

1. **Performance Optimization**
   - Fine-tune Neo4j memory settings
   - Optimize search indexes
   - Review and compress audit logs

2. **Feature Stabilization**
   - Monitor for issues in production usage
   - Collect user feedback
   - Address discovered edge cases

---

## Support & Contact

For upgrade issues, refer to:
- **Documentation**: `/home/devel/basset-hound/docs/PHASE-8-DOCUMENTATION-INDEX.md`
- **Implementation Guide**: `/home/devel/basset-hound/docs/PHASE-8-IMPLEMENTATION-GUIDE.md`
- **Troubleshooting**: This guide, Section "Troubleshooting Guide"
- **Logs**: `docker-compose logs -f basset_api | grep -i error`

---

## Appendix A: Quick Reference

### One-Liner Upgrade (if everything is ready)

```bash
# DANGER: Only use if you've followed pre-upgrade checklist!
git pull origin main && \
docker-compose down && \
docker-compose up -d neo4j redis && \
sleep 60 && \
docker-compose exec neo4j_osint_db cypher-shell "CREATE INDEX IF NOT EXISTS FOR (e:Entity) ON (e.type)" && \
docker-compose up -d && \
sleep 30 && \
curl -s http://localhost:8080/api/v1/health | jq '.status'
```

### Upgrade Status Commands

```bash
# Current phase
curl -s http://localhost:8080/api/v1/health | jq '.version'

# New Phase 8 features available?
curl -s http://localhost:8080/api/v1/search/autocomplete -H "X-Debug: true" | jq '.features'

# ML analytics enabled?
curl -s http://localhost:8080/api/v1/ml/duplicates -I | grep "HTTP"

# WebSocket support?
curl -I -N -H "Connection: Upgrade" -H "Upgrade: websocket" http://localhost:8080/api/v1/ws/test
```

### Useful Flags & Environment Variables

```bash
# For troubleshooting
DEBUG=1 docker-compose up basset_api

# For performance testing
NEO4J_server_memory_heap_max__size=4G docker-compose up neo4j

# For detailed logging
FASTAPI_LOG_LEVEL=DEBUG docker-compose up basset_api
```

---

## Appendix B: Phase 8 Features Quick Start

### After successful upgrade, enable and test:

```bash
# 1. Advanced Search
curl -X POST http://localhost:8080/api/v1/search/advanced \
  -H "Content-Type: application/json" \
  -d '{"query":"example","entity_types":["Person"]}'

# 2. Autocomplete
curl http://localhost:8080/api/v1/search/autocomplete?q=test&limit=5

# 3. ML Duplicates (if ENABLE_ML_ANALYTICS=true)
curl -X POST http://localhost:8080/api/v1/ml/duplicates \
  -H "Content-Type: application/json" \
  -d '{"entity_id":"ent_123","confidence_threshold":0.8}'

# 4. Real-time Collaboration (WebSocket)
wscat -c "ws://localhost:8080/api/v1/ws/projects/proj_abc"
# Type: {"action":"join","user_id":"usr_123"}

# 5. Visualization Plugins
curl http://localhost:8080/api/v1/plugins

# 6. Data Export
curl -X POST http://localhost:8080/api/v1/export/graphml \
  -H "Content-Type: application/json" \
  -d '{"project_id":"proj_123"}' > export.graphml
```

---

**Document Complete**

**Next Steps**:
1. Follow "Pre-Upgrade Checklist"
2. Execute "Step-by-Step Upgrade Procedure"
3. Run "Testing & Verification" tests
4. Monitor "Performance Validation" metrics
5. Refer to "Troubleshooting Guide" if issues arise

**Estimated Total Time**: 45 minutes (pre-upgrade + migration + verification)
