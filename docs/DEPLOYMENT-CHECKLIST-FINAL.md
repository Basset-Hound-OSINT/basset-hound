# Basset Hound Production Deployment Checklist

**Date Created**: 2026-05-19  
**Phase**: Phase 8 Complete (with Known Issues)  
**Status**: NOT YET APPROVED FOR PRODUCTION  
**Target Deployment**: Post-remediation (after Neo4j optimization)

---

## Executive Summary

This checklist provides a comprehensive pre-deployment verification process. **IMPORTANT**: The system currently fails production load tests due to Neo4j connection pool bottlenecks. Follow the remediation plan in Section 1 before proceeding with deployment steps.

**Current Status**: ❌ **BLOCKED** - System exhibits 63.75% error rate under 100 concurrent users

---

## SECTION 1: CRITICAL REMEDIATION (MUST COMPLETE FIRST)

### 1.1 Neo4j Connection Pool Expansion
- [ ] Verify current Neo4j connection pool size: `NEO4J_dbms_connector_bolt_connection_guard_max_connections`
- [ ] Set pool size to minimum 150 connections
- [ ] Update `docker-compose.yml` environment variables:
  ```yaml
  environment:
    NEO4J_dbms_connector_bolt_connection_guard_max_connections: 150
    NEO4J_dbms_connector_bolt_connection_guard_min_idle_sessions: 10
  ```
- [ ] Restart Neo4j container: `docker-compose restart neo4j`
- [ ] Verify pool is active: Check Neo4j metrics endpoint
- [ ] Document pool size in runbook

### 1.2 Query Optimization
- [ ] Review and optimize complex Cypher queries in `/api/services/neo4j_service.py`
- [ ] Convert N+1 query patterns to single UNION queries:
  - `get_projects()` endpoint (currently 2+ queries)
  - `search_entities()` endpoint (currently 2-5 queries)
- [ ] Add query execution timeouts (5 seconds maximum)
- [ ] Test each optimized query in Neo4j browser to verify performance
- [ ] Implement caching for frequently accessed queries:
  - Projects list: 30-second TTL
  - Search results: 5-second TTL
  - Entity counts: 1-minute TTL

### 1.3 Redis Caching Strategy
- [ ] Verify Redis is accessible: `redis-cli ping`
- [ ] Configure cache invalidation on data updates
- [ ] Test cache hit rates: Target >60%
- [ ] Monitor memory usage: Alert if >80%
- [ ] Configure LRU eviction policy
- [ ] Document cache keys and TTLs

### 1.4 Load Test Validation
- [ ] Execute load test script: `python3 load_testing_script.py`
- [ ] Verify throughput: **Target >3 req/s** (current: 1.21 req/s)
- [ ] Verify error rate: **Target <5%** (current: 63.75%)
- [ ] Verify health check latency: **Target <100ms p99** (current: 15,375ms)
- [ ] Verify concurrent user handling: 100 users stable for 60 seconds
- [ ] Document test results in `/docs/handoffs/LOAD-TEST-FINAL-VALIDATION.md`
- [ ] Obtain sign-off from DevOps lead before proceeding

**SUCCESS CRITERIA**: All metrics must pass before proceeding to Section 2

---

## SECTION 2: PRE-DEPLOYMENT VERIFICATION (15 Items)

### 2.1 Code Quality & Security
- [ ] All Python files compile without syntax errors
  ```bash
  python3 -m py_compile api/**/*.py
  ```
- [ ] No hardcoded secrets in code (verify `.env` is in `.gitignore`)
- [ ] CORS origins configured for production domain (not `*`)
  ```python
  CORS_ORIGINS = "https://your-production-domain.com"
  ```
- [ ] JWT_SECRET_KEY set to secure random value (minimum 256 bits)
- [ ] DEBUG mode disabled in production `.env`
  ```bash
  DEBUG=false
  ```

### 2.2 Configuration & Environment
- [ ] `.env` file created with production values (never committed to git)
- [ ] Database credentials stored in secure vault (AWS Secrets Manager, HashiCorp Vault)
- [ ] API keys rotated and configured
- [ ] ENCRYPTION_KEY generated and secured for database dumps
- [ ] Redis connection URL tested and accessible
- [ ] Neo4j password changed from default
- [ ] All required environment variables documented in `DEPLOYMENT-RUNBOOK-FINAL.md`

### 2.3 Docker & Containerization
- [ ] `docker-compose.yml` reviewed and validated
- [ ] All service images pinned to specific versions (not `latest`)
- [ ] Health check endpoints configured for all services
- [ ] Service dependencies properly declared with `depends_on`
- [ ] Volume mounts verified (no read-only conflicts)
- [ ] Log drivers configured (json-file with size limits)

### 2.4 Database Readiness
- [ ] Neo4j database initialized and accessible
- [ ] All required indexes created:
  ```cypher
  SHOW INDEXES
  ```
- [ ] Database backups configured and tested
- [ ] Restore procedure documented and practiced
- [ ] Connection pool size verified (150+ connections)
- [ ] Query performance validated in staging

### 2.5 API Endpoints
- [ ] All 50+ endpoints documented in `API_REFERENCE.md`
- [ ] Endpoint authentication verified (JWT or API key required)
- [ ] Rate limiting configured on expensive operations:
  - ML Operations: 5 req/min
  - Database Dump: 2 req/5min
  - Search: 30 req/min
  - Export: 10 req/min
- [ ] Response compression enabled (gzip for >1KB responses)
- [ ] Error handling returns proper HTTP status codes

### 2.6 Security Audit
- [ ] JWT authentication enforced for all protected endpoints
- [ ] API key authentication implemented and tested
- [ ] Encryption implemented for sensitive data (database dumps)
- [ ] Cypher injection prevention verified (parameterized queries)
- [ ] Rate limiting prevents DoS attacks
- [ ] PII redaction working (email/phone masking)
- [ ] Audit logging implemented and tested

### 2.7 Performance Baselines
- [ ] Query latency verified: **p99 <100ms** (current: 95ms ✅)
- [ ] Cache hit rate verified: **>60%** (current: 60%+ ✅)
- [ ] Search latency verified: **<200ms** (current: 150ms avg ✅)
- [ ] Export latency verified: **<500ms** (current: 300-400ms ✅)
- [ ] API throughput verified: **>3 req/s under load** (after remediation)
- [ ] No cascading failures under sustained load

### 2.8 Frontend Integration
- [ ] Dashboard loads without errors
- [ ] All Priority 1 & 2 fixes verified working
- [ ] WebSocket connection establishes successfully
- [ ] Search functionality end-to-end tested
- [ ] Export functionality tested (all 5 formats)
- [ ] Collaboration features tested
- [ ] Mobile responsiveness verified

### 2.9 Monitoring & Alerting
- [ ] Prometheus metrics collection configured
- [ ] Grafana dashboards created for key metrics
- [ ] Alert rules defined:
  - [ ] Error rate >1%
  - [ ] API latency p99 >200ms
  - [ ] Database latency >150ms
  - [ ] Cache hit rate <30%
  - [ ] Service health check failures
- [ ] Log aggregation configured (ELK, CloudWatch, etc.)
- [ ] Notification channels tested (Slack, PagerDuty, email)

### 2.10 Documentation
- [ ] `PRODUCTION-DEPLOYMENT-RUNBOOK-FINAL.md` complete
- [ ] `INCIDENT-RESPONSE-PLAYBOOK.md` documented
- [ ] `PRODUCTION-MONITORING-SETUP.md` configured
- [ ] Troubleshooting guide documented
- [ ] Backup/restore procedures tested
- [ ] Rollback procedures documented

---

## SECTION 3: DEPLOYMENT PHASE (Step-by-Step)

### 3.1 Pre-Deployment Preparation (30 mins)
- [ ] Create deployment window in production calendar
- [ ] Notify stakeholders of maintenance window
- [ ] Verify all team members have access to:
  - [ ] Production servers
  - [ ] Monitoring dashboards
  - [ ] Incident communication channels
  - [ ] Database backup systems
- [ ] Have rollback plan ready (previous stable version)
- [ ] Test all communication channels

### 3.2 Backup & Snapshot (15 mins)
- [ ] Create Neo4j database backup
  ```bash
  docker-compose exec neo4j neo4j-admin database dump neo4j /backups/pre-deployment.dump
  ```
- [ ] Verify backup file exists and is readable
- [ ] Take filesystem snapshots of critical volumes
- [ ] Document backup location and restoration procedure

### 3.3 Staging Validation (2-3 hours recommended)
- [ ] Deploy to staging environment first (if not already done)
- [ ] Run full test suite: `pytest tests/ -v --tb=short`
- [ ] Execute load test: `python3 load_testing_script.py`
- [ ] Validate search, export, and API endpoints
- [ ] Monitor staging environment for 30+ minutes
- [ ] Verify no unexpected errors in logs
- [ ] Get formal approval from tech lead before production

### 3.4 Production Deployment (Phase A: Backend)
- [ ] Set maintenance mode (if applicable)
- [ ] Pull latest code to production server
- [ ] Update environment variables in production `.env`:
  ```bash
  DEBUG=false
  REQUIRE_AUTH=true
  CORS_ORIGINS="https://production-domain.com"
  NEO4J_PASSWORD=<secure-password>
  ENCRYPTION_KEY=<secure-key>
  JWT_SECRET_KEY=<secure-key>
  ```
- [ ] Build Docker images: `docker-compose build`
- [ ] Stop current services: `docker-compose down`
- [ ] Start new services: `docker-compose up -d`
- [ ] Wait for services to be healthy (check logs):
  ```bash
  docker-compose logs -f api
  ```

### 3.5 Production Deployment (Phase B: Validation)
- [ ] Verify all services are running:
  ```bash
  docker-compose ps
  ```
  Expected: All services show `Up`
- [ ] Test health endpoint:
  ```bash
  curl http://localhost:8080/health
  ```
  Expected: `{"status": "healthy"}`
- [ ] Test database connectivity:
  ```bash
  curl http://localhost:8080/api/v1/projects
  ```
  Expected: Returns project list (possibly empty initially)
- [ ] Check logs for errors:
  ```bash
  docker-compose logs api | grep -i "error\|critical"
  ```
- [ ] Verify monitoring is capturing metrics
- [ ] Verify alerting system is active

### 3.6 Gradual Traffic Ramp-Up
- [ ] Warm up cache by running smoke tests
- [ ] Direct 10% of traffic to new version
- [ ] Monitor error rates and latencies (target: <0.1% error rate)
- [ ] Direct 50% of traffic to new version
- [ ] Monitor for 10 minutes
- [ ] Direct 100% of traffic to new version
- [ ] Monitor for 30 minutes

### 3.7 Post-Deployment Validation (30 mins)
- [ ] Verify error rate <0.1%
- [ ] Verify API latency p99 <200ms
- [ ] Verify cache hit rate >40%
- [ ] Verify all endpoints respond correctly
- [ ] Check database query performance in monitoring
- [ ] Verify WebSocket connections working
- [ ] Test export functionality
- [ ] Verify audit logging is recording events
- [ ] Check backup systems are operational

---

## SECTION 4: POST-DEPLOYMENT VALIDATION (10 Items)

### 4.1 System Health
- [ ] All services show "healthy" status
- [ ] API response times normal (<200ms p99)
- [ ] Error rate below acceptable threshold (<0.1%)
- [ ] Database connections stable (pool not exhausted)
- [ ] Cache performance adequate (>40% hit rate)
- [ ] No memory leaks in logs
- [ ] No cascading failures under normal load

### 4.2 Data Integrity
- [ ] All data successfully migrated from previous version
- [ ] Database queries return expected results
- [ ] No data corruption detected
- [ ] Audit logs recording all changes
- [ ] User sessions maintained without issues

### 4.3 User Experience
- [ ] Dashboard loads without errors
- [ ] Search functionality working end-to-end
- [ ] Export operations complete successfully
- [ ] WebSocket synchronization working
- [ ] Collaboration features operational
- [ ] No visible performance degradation

### 4.4 Security
- [ ] Authentication required for protected endpoints
- [ ] Rate limiting preventing abuse
- [ ] No sensitive data in logs
- [ ] Encryption keys in secure storage
- [ ] API key authentication working
- [ ] CORS properly restricting origins

### 4.5 Monitoring
- [ ] Metrics flowing to dashboard
- [ ] Alerts firing correctly on test conditions
- [ ] Log aggregation capturing all events
- [ ] Health checks passing consistently
- [ ] Performance baselines established for trending

### 4.6 Team Handoff
- [ ] Runbook reviewed with operations team
- [ ] Escalation procedures documented
- [ ] On-call rotation established
- [ ] Incident response procedures walkthrough
- [ ] Monitoring dashboard access verified

---

## SECTION 5: ROLLBACK PROCEDURES (If Needed)

### 5.1 Quick Rollback (< 5 minutes)
If critical issues detected within first 30 minutes:

- [ ] Stop current services: `docker-compose down`
- [ ] Restore previous image versions
- [ ] Start services with previous version: `docker-compose up -d`
- [ ] Verify services are healthy
- [ ] Notify stakeholders of rollback

### 5.2 Database Rollback (If Data Corruption)
If data issues detected:

- [ ] Stop API services (keep database running)
- [ ] Restore database from pre-deployment backup
- [ ] Verify data integrity
- [ ] Investigate root cause before retry

### 5.3 Incident Investigation
- [ ] Collect logs for analysis
- [ ] Preserve system state for debugging
- [ ] Document incident timeline
- [ ] Identify root cause
- [ ] Create fix and retest in staging
- [ ] Document lessons learned

---

## SECTION 6: SUCCESS CRITERIA

### Deployment Successful If:
✅ All services healthy and responding  
✅ Error rate <0.1% for 30+ minutes  
✅ API latency p99 <200ms  
✅ Cache hit rate >40%  
✅ All endpoints returning correct data  
✅ No data corruption detected  
✅ Monitoring and alerting functional  
✅ Team confident in operational stability  

### Deployment Failed If:
❌ Any service fails to start  
❌ Error rate >1%  
❌ API latency p99 >500ms  
❌ Database connectivity issues  
❌ Data corruption detected  
❌ Security issues identified  
❌ Critical features not working  

---

## SECTION 7: POST-DEPLOYMENT CLEANUP

### Phase 9 Priority Tasks
- [ ] Remove console.log statements from frontend JavaScript
- [ ] Fix Python function signature error in `api/routers/export.py:694`
- [ ] Resolve Neo4j DateTime serialization issue
- [ ] Investigate Celery worker health status
- [ ] Debug Nginx reverse proxy health check
- [ ] Remove TODO/FIXME comments (or create issues)
- [ ] Implement frontend unit tests
- [ ] Setup CI/CD pipeline

### Performance Optimization
- [ ] Monitor cache TTL effectiveness
- [ ] Tune database query plans based on production patterns
- [ ] Optimize frontend bundle size (target: 44% reduction achieved)
- [ ] Profile API hotspots
- [ ] Document performance baselines

### Documentation Updates
- [ ] Update runbook with actual production values
- [ ] Document learned lessons
- [ ] Create operational handbook for team
- [ ] Record deployment metrics

---

## CHECKLIST SIGN-OFF

**Pre-Deployment Sign-Off** (Required before deploying)

- [ ] Technical Lead: _________________ Date: _______
- [ ] DevOps Engineer: ________________ Date: _______
- [ ] Security Lead: __________________ Date: _______
- [ ] Operations Manager: _____________ Date: _______

**Post-Deployment Sign-Off** (Required after 24 hours stable)

- [ ] Operations Manager: _____________ Date: _______
- [ ] Monitoring Lead: ________________ Date: _______
- [ ] Senior Engineer: ________________ Date: _______

---

## QUICK REFERENCE

### Critical Commands

```bash
# View service status
docker-compose ps

# View API logs
docker-compose logs -f api

# View database logs
docker-compose logs -f neo4j

# Execute health check
curl http://localhost:8080/health

# Run load test
python3 load_testing_script.py

# Restart all services
docker-compose down && docker-compose up -d

# View Neo4j metrics
docker-compose exec neo4j cypher-shell "SHOW DATABASE TRANSACTIONS"

# Check cache hit rate
curl http://localhost:8080/api/v1/cache/stats

# View error rate
curl http://localhost:8080/api/v1/metrics | grep error_rate
```

### Emergency Contacts
- **On-Call Engineer**: [Insert contact]
- **DevOps Lead**: [Insert contact]
- **Database Administrator**: [Insert contact]
- **Security Team**: [Insert contact]

---

**Document Status**: Draft (Final version after remediation)  
**Last Updated**: 2026-05-19  
**Next Review**: Post-remediation before production  
**Owner**: DevOps / Operations Team
