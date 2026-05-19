# Basset Hound Phase 8 - Production Deployment Checklist
**Date**: 2026-05-19  
**Status**: READY FOR DEPLOYMENT (with conditions)  
**Deployment Window**: 2026-05-19 16:00-18:00 UTC (estimated)

---

## Pre-Deployment Verification (Run 1 Hour Before Deployment)

### Code Review & Testing

- [ ] All agents have completed their tasks
  - [ ] DateTime serialization fix - Agent a4308862cf40b60b4
  - [ ] Integration tests passing - Agent a1e512146745c9793
  - [ ] Docker validation complete - Agent a8dba7a7e098a8bcd
  
- [ ] Code quality checks
  ```bash
  python3 -m py_compile api/main.py
  python3 -m py_compile api/routers/*.py
  python3 -m py_compile api/services/*.py
  ```
  
- [ ] All tests passing
  ```bash
  pytest tests/test_e2e_workflows.py -v
  pytest tests/test_activity_feed_user_verification.py -v
  pytest tests/test_activity_feed_integration.py -v
  ```

- [ ] No git commits made (confirmed)
  ```bash
  git status  # Should show modified files, no commits since baseline
  ```

### Docker Environment Verification

- [ ] Docker Compose file syntax valid
  ```bash
  docker-compose config > /dev/null && echo "✓ Valid"
  ```

- [ ] All services defined
  - [ ] FastAPI (basset_api)
  - [ ] Neo4j (neo4j_osint_db)
  - [ ] Redis (redis_cache)
  - [ ] Nginx (nginx)
  - [ ] Prometheus (prometheus)
  - [ ] Grafana (grafana)
  - [ ] Celery worker (celery_worker)
  - [ ] Celery beat (celery_beat)
  - [ ] PostgreSQL (if used)

- [ ] Environment variables configured
  ```bash
  cp .env.example .env
  # Review and update:
  # - NEO4J_AUTH credentials
  # - REDIS_URL
  # - JWT_SECRET_KEY (should be strong)
  # - DATABASE_URL (if PostgreSQL)
  ```

- [ ] Volumes ready for persistence
  ```bash
  mkdir -p data/neo4j data/redis data/postgres
  chmod 755 data/*
  ```

### Security Pre-Flight

- [ ] JWT secret key configured (not default)
  ```bash
  grep "^JWT_SECRET_KEY" .env | grep -v "change-me"
  ```

- [ ] Encryption key configured
  ```bash
  grep "^ENCRYPTION_KEY" .env | grep -v "^$"
  ```

- [ ] SSL/TLS certificates in place (for production)
  ```bash
  ls -l /etc/ssl/certs/basset-hound.*
  ```

- [ ] Database credentials changed from defaults
  ```bash
  grep "neo4jbasset" .env && echo "⚠️ WARNING: Using default password"
  ```

- [ ] API keys/tokens rotated (if any external integrations)

### Database Pre-Flight

- [ ] Neo4j backup created
  ```bash
  # In current environment:
  docker exec neo4j_osint_db tar czf /backups/neo4j-pre-deploy.tar.gz /var/lib/neo4j/data
  ```

- [ ] Schema migration tested
  ```bash
  # Test on staging/dev first
  python3 scripts/migrate_schema.py --dry-run
  ```

- [ ] Data integrity check
  ```bash
  docker exec neo4j_osint_db cypher-shell -u neo4j -p $NEO4J_PASSWORD \
    "MATCH (n) RETURN count(n) as node_count"
  ```

---

## Deployment Procedure (Execute in Order)

### Phase 1: Pre-Deployment Shutdown (15 minutes)

1. **Stop accepting new requests** (load balancer level if applicable)
   ```bash
   # If using load balancer, remove production server from rotation
   # or update DNS to point to staging during deployment
   ```

2. **Stop background jobs**
   ```bash
   docker exec celery_worker pkill -f celery
   docker exec celery_beat pkill -f celery
   ```

3. **Drain in-flight requests** (wait 60 seconds)
   ```bash
   sleep 60  # Wait for active connections to complete
   ```

4. **Stop services**
   ```bash
   docker compose down --remove-orphans
   ```

5. **Backup current state**
   ```bash
   # Backup database
   docker exec neo4j_osint_db bin/neo4j-admin dump \
     --database=neo4j --to=/var/lib/neo4j/backups/pre-deploy-$(date +%s).dump
   
   # Backup Redis
   docker exec redis_cache redis-cli BGSAVE
   ```

### Phase 2: Deploy New Version (20 minutes)

1. **Verify git state** (no uncommitted changes beyond staged)
   ```bash
   git status --short | grep -v "^?" | wc -l  # Should be 0
   ```

2. **Update environment**
   ```bash
   # If config changes needed:
   docker compose config --resolve-image-digests > docker-compose.deployed.yml
   ```

3. **Pull latest images** (if using image registry)
   ```bash
   docker compose pull
   ```

4. **Start services** with health checks
   ```bash
   docker compose up -d --wait
   # Wait for services to be healthy
   sleep 30  # Services should stabilize
   ```

5. **Verify all services running**
   ```bash
   docker compose ps  # All should show "Up"
   docker compose exec basset_api curl http://localhost:8000/health
   ```

### Phase 3: Post-Deployment Validation (15 minutes)

1. **Health check endpoint**
   ```bash
   curl -s http://localhost:8000/health | jq .
   # Expected: neo4j: connected, redis: connected, status: healthy
   ```

2. **Database connectivity**
   ```bash
   docker exec neo4j_osint_db cypher-shell -u neo4j -p $NEO4J_PASSWORD \
     "MATCH (n) RETURN count(n) LIMIT 1"
   ```

3. **Critical API endpoints**
   ```bash
   # Test project creation
   curl -X POST http://localhost:8000/api/v1/projects \
     -H "Content-Type: application/json" \
     -d '{"name": "Deployment Test"}'
   
   # Test project list
   curl http://localhost:8000/api/v1/projects
   
   # Test search
   curl "http://localhost:8000/api/v1/projects/test_project/search?q=test"
   ```

4. **Frontend serving**
   ```bash
   curl -s http://localhost:80/ | grep "<title>" | head -1
   # Should contain Basset Hound or dashboard title
   ```

5. **WebSocket connectivity**
   ```bash
   # Test WebSocket via wscat (npm install -g wscat)
   wscat -c ws://localhost:8000/ws/sync/test_project
   # Or test via browser console: new WebSocket('ws://localhost:8000/...')
   ```

6. **Error handling**
   ```bash
   # Test 404 handling
   curl http://localhost:8000/api/v1/projects/nonexistent
   # Should return proper 404 JSON response
   
   # Test 500 error handling
   # (Intentionally trigger an error to verify error response format)
   ```

7. **Metrics endpoint**
   ```bash
   curl http://localhost:9090/api/v1/query?query=up
   # Prometheus should be scraping metrics
   ```

### Phase 4: Re-Enable Production Traffic (5 minutes)

1. **Update load balancer** (if applicable)
   ```bash
   # Add server back to rotation or update DNS
   ```

2. **Monitor error rates**
   ```bash
   # Watch for errors in real-time:
   docker compose logs -f basset_api | grep ERROR
   ```

3. **Monitor performance**
   ```bash
   # Via Prometheus/Grafana dashboard
   # Check: API latency, error rate, cache hit rate, connection pools
   ```

---

## Rollback Procedure (If Needed)

### Decision Point: When to Rollback

Rollback if ANY of these conditions occur:
- [ ] Health check endpoint returning 500+ errors for >5 consecutive calls
- [ ] Neo4j database unreachable (cannot execute queries)
- [ ] API endpoints returning >10% error rate
- [ ] Frontend not loading (404s or 500s)
- [ ] WebSocket connections consistently failing
- [ ] Memory/CPU usage >90% (indicates resource issue)
- [ ] Database queries timing out

### Rollback Steps (Execute Immediately)

```bash
# 1. Stop accepting traffic
# (Load balancer removal or DNS rollback)

# 2. Stop all services
docker compose down

# 3. Restore from pre-deployment backup
# For Neo4j:
docker exec neo4j_osint_db bin/neo4j-admin load \
  --database=neo4j \
  --from=/var/lib/neo4j/backups/pre-deploy-TIMESTAMP.dump --force

# 4. Restart services
docker compose up -d

# 5. Verify rollback successful
docker compose exec basset_api curl http://localhost:8000/health

# 6. Re-enable production traffic
```

**Estimated Rollback Time**: 10-15 minutes

---

## Post-Deployment Monitoring (First 24 Hours)

### Hourly Checks (First 8 Hours)

- [ ] Error rate stable (<1%)
- [ ] API response times normal (<200ms p95)
- [ ] No memory leaks (memory usage stable)
- [ ] Database connection pool healthy
- [ ] Cache hit rate >60%
- [ ] No warnings in logs

```bash
# View last 100 lines of logs
docker compose logs --tail=100

# Count errors in last hour
docker compose logs --since 1h | grep ERROR | wc -l
```

### 4-Hour Checks

- [ ] Database query performance normal
- [ ] WebSocket connections stable
- [ ] Background jobs completing successfully
- [ ] Metrics being collected and stored

### 24-Hour Checks (Next Morning)

- [ ] Load test results consistent with pre-deployment
- [ ] No data integrity issues
- [ ] All integrations working (basset-verify, etc.)
- [ ] Monitoring dashboards showing expected metrics
- [ ] Team reporting no user-facing issues

### Weekly Verification

- [ ] Scheduled backups running successfully
- [ ] Performance trending stable or improving
- [ ] Security logs showing no anomalies
- [ ] All features fully operational

---

## Communication Plan

### Pre-Deployment Notification (2 Hours Before)

Send notification to stakeholders:
```
Subject: Basset Hound Phase 8 Production Deployment - Scheduled Downtime

The Basset Hound OSINT platform will undergo a scheduled maintenance deployment 
on [DATE] at [TIME] UTC.

Expected duration: 1 hour
Downtime: ~30 minutes
Impact: All users will be unable to access the system

We will notify you when the system is restored.

For questions: [support email]
```

### During Deployment

- Monitor deployment progress
- Watch error logs for issues
- Be ready for immediate rollback if needed

### Post-Deployment Notification

Send completion notification:
```
Subject: Basset Hound Phase 8 Deployment Complete - Service Restored

The Basset Hound OSINT platform has been successfully deployed and is now 
fully operational. 

Deployment status: ✅ SUCCESSFUL
All systems: ✅ HEALTHY

New features and improvements are now available:
- [List major improvements]

Thank you for your patience during the maintenance window.
```

---

## Troubleshooting Guide

### Issue: Services Not Starting

```bash
# Check logs
docker compose logs basset_api

# Common causes:
# 1. Port already in use
netstat -tuln | grep 8000

# 2. Invalid environment variables
grep "error\|Error\|ERROR" .env

# 3. Database connection failed
docker compose exec basset_api python -c "from neo4j import GraphDatabase; ..."

# Fix: Review error message, correct issue, restart
docker compose restart basset_api
```

### Issue: Database Connection Errors

```bash
# Verify Neo4j is running
docker compose exec neo4j_osint_db bin/neo4j status

# Check credentials
docker exec neo4j_osint_db cypher-shell -u neo4j -p $NEO4J_PASSWORD "MATCH (n) RETURN count(n) LIMIT 1"

# If restore needed:
docker exec neo4j_osint_db bin/neo4j-admin load --database=neo4j --from=/path/to/backup.dump --force
docker compose restart neo4j_osint_db
```

### Issue: API Returning 500 Errors

```bash
# Check API logs
docker compose logs basset_api --tail=50

# Common causes:
# 1. DateTime serialization (Pydantic validation error)
# 2. Neo4j query error
# 3. Missing environment variable

# Debug specific endpoint:
docker compose exec basset_api \
  python -c "import traceback; from api.main import app; ..."
```

### Issue: WebSocket Connections Failing

```bash
# Check WebSocket logs
docker compose logs basset_api | grep -i websocket

# Verify WebSocket port accessible
nc -zv localhost 8000

# Check message format
# WebSocket expects JSON messages with proper structure
```

### Issue: Performance Degradation

```bash
# Check resource usage
docker stats

# Check database queries
docker exec neo4j_osint_db bin/cypher-shell "CALL dbms.listQueries()"

# Check connection pool
docker exec redis_cache redis-cli INFO stats | grep connected_clients

# Common fixes:
# 1. Increase connection pool size (see deployment guide)
# 2. Add database indexes (scripts/add-indexes.py)
# 3. Clear cache (redis-cli FLUSHALL)
```

---

## Sign-Off Checklist

Before declaring deployment complete, verify:

- [ ] All health checks passing
- [ ] All critical API endpoints tested
- [ ] WebSocket connectivity verified
- [ ] Frontend loading in browser
- [ ] Database query performance acceptable
- [ ] Error rate <1%
- [ ] No warnings in logs
- [ ] Team member verified everything works
- [ ] Monitoring dashboards updated
- [ ] Communication sent to stakeholders

---

## Deployment Timeline

```
T-60min: Pre-deployment verification
T-45min: Notify stakeholders
T-30min: Prepare backup/rollback
T-15min: Stop new requests
T-00min: BEGIN DEPLOYMENT
   ├─ Phase 1: Shutdown (15 min)
   ├─ Phase 2: Deploy (20 min)
   ├─ Phase 3: Validate (15 min)
   └─ Phase 4: Re-enable traffic (5 min)
T+55min: Deployment complete
T+1h00m: Send notification
T+4h00m: 4-hour check-in
T+24h00m: 24-hour validation
```

---

## Key Contacts & Escalation

| Role | Name | Email | Phone |
|------|------|-------|-------|
| Deployment Lead | [Name] | [Email] | [Phone] |
| Database Admin | [Name] | [Email] | [Phone] |
| Ops Manager | [Name] | [Email] | [Phone] |
| Security Lead | [Name] | [Email] | [Phone] |

---

## Success Criteria (Post-Deployment)

- ✅ Zero critical errors in first 1 hour
- ✅ All endpoints responsive (<500ms)
- ✅ WebSocket connectivity established
- ✅ Database queries completing successfully
- ✅ Monitoring showing healthy metrics
- ✅ User acceptance testing passed
- ✅ Team confident in deployment

---

**Deployment Checklist Version**: 1.0  
**Last Updated**: 2026-05-19  
**Prepared By**: Phase 8 Completion Team  
**Status**: READY FOR DEPLOYMENT
"