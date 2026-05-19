# Basset Hound - Troubleshooting Guide

**Version**: 2.0.0  
**Last Updated**: 2026-05-19  
**Purpose**: Solutions for common issues and problems

---

## Table of Contents

1. [Quick Diagnostics](#quick-diagnostics)
2. [Service Health Checks](#service-health-checks)
3. [Docker Issues](#docker-issues)
4. [API Issues](#api-issues)
5. [Database Issues](#database-issues)
6. [Frontend Issues](#frontend-issues)
7. [Performance Issues](#performance-issues)
8. [Integration Issues](#integration-issues)
9. [Advanced Debugging](#advanced-debugging)
10. [Getting Help](#getting-help)

---

## Quick Diagnostics

### Run Complete System Check

```bash
#!/bin/bash
# save as check-system.sh

echo "=== SYSTEM CHECK ===" 
echo "Docker version:"
docker --version

echo -e "\n=== SERVICE STATUS ==="
docker-compose ps

echo -e "\n=== API HEALTH ==="
curl -s http://localhost:8080/health | jq .

echo -e "\n=== NEO4J STATUS ==="
curl -s http://localhost:7474/db/neo4j/check | jq .

echo -e "\n=== REDIS STATUS ==="
redis-cli ping

echo -e "\n=== DISK SPACE ==="
df -h | grep -E "^/dev|^Filesystem"

echo -e "\n=== MEMORY USAGE ==="
docker stats --no-stream

echo -e "\n=== RECENT LOGS ==="
docker-compose logs --tail=20 basset_api
```

### One-Minute Diagnosis

```bash
# Is everything running?
docker-compose ps

# Can we reach the API?
curl http://localhost:8080/health

# Is the database responding?
curl http://localhost:7474

# Check for error logs
docker-compose logs basset_api | grep ERROR
```

---

## Service Health Checks

### All Services Healthy

```json
{
  "status": "ok",
  "services": {
    "api": "healthy",
    "neo4j": "healthy",
    "redis": "healthy",
    "nginx": "healthy"
  }
}
```

### Check Individual Services

```bash
# API service
curl http://localhost:8080/health

# Neo4j database
curl -u neo4j:neo4jbasset http://localhost:7474/browser

# Redis cache
docker-compose exec redis redis-cli ping

# Prometheus metrics
curl http://localhost:9090/-/healthy

# Grafana
curl http://localhost:3000/api/health
```

### Service Status Dashboard

Open **Grafana** at http://localhost:3000 for visual service health dashboard.

---

## Docker Issues

### Service Won't Start

**Symptom**: `docker-compose up` fails or service exits immediately

**Debug**:
```bash
# View full logs
docker-compose logs basset_api

# Check specific error
docker-compose logs basset_api | tail -50

# Restart with verbose output
docker-compose up --no-daemon basset_api
```

**Common Causes**:

| Issue | Solution |
|-------|----------|
| **Port already in use** | Change port in `.env` or kill process: `lsof -i :8080 \| kill -9 <PID>` |
| **Out of disk space** | `docker system prune -a` to clean up, then increase disk |
| **Out of memory** | Increase Docker memory limit, reduce service heap |
| **Network error** | Check Docker network: `docker network inspect basset-hound_default` |

### Container Keeps Restarting

**Symptom**: Container exits and immediately restarts

```bash
# View restart count
docker-compose ps

# Check logs for crash reason
docker-compose logs --tail=100 basset_api | grep -E "Traceback|Error|CRITICAL"

# Get container ID and inspect
CONTAINER=$(docker-compose ps -q basset_api)
docker inspect $CONTAINER | grep -A5 "RestartCount"
```

**Solutions**:
- Check logs for errors
- Verify environment variables in `.env`
- Check database connectivity
- Increase container resources

### High Memory Usage

**Symptom**: `docker stats` shows >80% memory usage

```bash
# Check what's using memory
docker stats --no-stream

# Check Neo4j memory specifically
docker-compose exec neo4j jcmd $(pgrep java) VM.native_memory summary

# Check Python memory
docker-compose exec basset_api ps aux | head -20
```

**Solutions**:

```bash
# Reduce Neo4j heap
# Edit docker-compose.yml
environment:
  - NEO4J_HEAP_MEMORY=512M  # Reduce from 1G

# Reduce Redis memory
# Edit docker-compose.yml
command: redis-server --maxmemory 256mb

# Restart services
docker-compose down
docker-compose up -d
```

### Disk Space Issues

```bash
# Check disk usage
df -h /

# Clean up Docker
docker system prune -a  # Remove unused images/containers
docker volume prune     # Remove unused volumes

# Check largest containers
docker exec $(docker-compose ps -q neo4j) du -sh /data

# Check largest images
docker images --sort=size
```

---

## API Issues

### API Returns 500 Error

**Symptom**: `curl http://localhost:8080/api/v1/...` returns 500

```bash
# Check logs
docker-compose logs basset_api | grep "ERROR" | tail -20

# Test API directly
curl -v http://localhost:8080/health

# View full error
curl -s http://localhost:8080/api/v1/projects | jq .
```

**Common Causes**:

| Error | Solution |
|-------|----------|
| `unhashable type: 'dict'` | Jinja2 template cache issue - documented in BLOCKERS-2026-05-07.md |
| `Connection refused` | Neo4j not responding - check `docker-compose logs neo4j` |
| `Request timeout` | Query too slow - check database performance |
| `Invalid JSON` | Malformed request body - check Content-Type header |

### Slow API Responses

**Symptom**: API calls take >1 second

```bash
# Check response times
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8080/api/v1/projects

# Monitor in real-time
watch -n 1 'curl -s http://localhost:9090/api/v1/query?query=basset_api_request_latency_p99 | jq'

# Check query performance
docker-compose logs basset_api | grep "query took"
```

**Solutions**:
- Enable caching: `CACHE_ENABLED=true`
- Add database indexes: See DEPLOYMENT.md
- Check query optimization: `docs/findings/QUERY-OPTIMIZATION-2026-05-07.md`
- Monitor with Prometheus: http://localhost:9090

### Authentication Errors

**Symptom**: `401 Unauthorized` or `403 Forbidden`

```bash
# Check if auth is enabled
grep "REQUIRE_AUTH" .env

# Test with token
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8080/api/v1/projects

# Get token (if auth enabled)
curl -X POST http://localhost:8080/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password"}'
```

### Rate Limiting

**Symptom**: `429 Too Many Requests`

```bash
# Check rate limit in response headers
curl -i http://localhost:8080/api/v1/projects | head -20

# Rate limits are per IP per minute
# Default: 100 requests/min
# Configure in docker-compose.yml:
# RATE_LIMIT_REQUESTS=100
# RATE_LIMIT_WINDOW=60
```

---

## Database Issues

### Neo4j Connection Failed

**Symptom**: `Connection refused` or `Unable to connect to database`

```bash
# Check if Neo4j is running
docker-compose ps neo4j

# View logs
docker-compose logs neo4j | tail -30

# Test connection
curl -u neo4j:neo4jbasset http://localhost:7474/db/neo4j/check

# Connection string in .env
# Should be: bolt://localhost:7687 (or neo4j:7687 if using docker network name)
```

**Solutions**:

```bash
# Verify Neo4j is healthy
docker-compose exec neo4j cypher-shell -u neo4j -p neo4jbasset "RETURN 1"

# Check Neo4j logs for startup issues
docker-compose logs neo4j | grep -E "ERROR|WARN"

# Restart Neo4j
docker-compose restart neo4j

# Rebuild Neo4j (deletes all data)
docker-compose down -v
docker-compose up -d neo4j
```

### Database Locked

**Symptom**: Queries hang or fail with "database locked"

```bash
# Check for long-running queries
docker-compose exec neo4j cypher-shell -u neo4j -p neo4jbasset \
  "CALL dbms.listQueries() YIELD query, elapsed"

# Kill long-running query
docker-compose exec neo4j cypher-shell -u neo4j -p neo4jbasset \
  "CALL dbms.killQuery('query_id')"

# Check write locks
docker-compose logs neo4j | grep -E "WriteConflict|LOCK"
```

### High Database Memory

**Symptom**: Neo4j using >80% of allocated memory

```bash
# Check memory usage
docker stats neo4j

# View heap stats
docker-compose exec neo4j jcmd $(pgrep java) VM.heap_dump

# Reduce cache size in docker-compose.yml
environment:
  - NEO4J_DBMS_MEMORY_PAGECACHE_SIZE=256m  # Reduce from 512m

# Increase heap if needed
environment:
  - NEO4J_HEAP_MEMORY=1024m
```

### Slow Queries

**Symptom**: Database queries taking >100ms

```bash
# Enable query logging
docker-compose exec neo4j cypher-shell -u neo4j -p neo4jbasset \
  "CALL dbms.setConfig('server.logs.query.enabled', 'true')"

# View query log
docker-compose exec neo4j tail -f /var/lib/neo4j/logs/query.log

# Find slow queries
docker-compose logs neo4j | grep "took more than"

# Analyze query plan
docker-compose exec neo4j cypher-shell -u neo4j -p neo4jbasset \
  "EXPLAIN MATCH (n:Person) RETURN n"
```

---

## Frontend Issues

### Dashboard Won't Load

**Symptom**: Blank page or JavaScript errors in browser console

**Known Blocker** (documented in BLOCKERS-2026-05-07.md):
```
Jinja2 template cache error: unhashable type: 'dict'
Location: api/routers/frontend.py line 84
```

**Temporary Workarounds**:
1. Use API directly: http://localhost:8080/docs
2. Use Grafana dashboard: http://localhost:3000
3. Use CLI tools instead

**Debug**:
```bash
# Check browser console (F12)
# Should show error message

# View server logs
docker-compose logs basset_api | grep frontend

# Test static files
curl http://localhost:8080/static/js/app.js

# Check template rendering
curl -v http://localhost:8080/
```

### JavaScript Errors

**Symptom**: "Cannot read property 'x' of undefined" or similar

```bash
# Check browser console (F12 → Console tab)
# Note the exact error and line number

# View frontend logs
docker-compose logs basset_api | grep "static"

# Check API endpoint the frontend is calling
# Use Network tab in DevTools
```

### Styling Issues

**Symptom**: Page looks broken or unstyled

```bash
# Check CSS is loading
curl http://localhost:8080/static/css/style.css

# Check for 404 errors in DevTools Network tab

# Clear browser cache
# Ctrl+Shift+Delete (Windows/Linux)
# Cmd+Shift+Delete (macOS)

# Hard refresh
# Ctrl+Shift+R (Windows/Linux)
# Cmd+Shift+R (macOS)
```

---

## Performance Issues

### Slow Search Queries

**Symptom**: Search takes >500ms

```bash
# Check search index status
curl http://localhost:8080/api/v1/projects/proj_123/search/status | jq .

# Monitor search performance
curl -s http://localhost:9090/api/v1/query?query=basset_search_latency_p99 | jq .

# Enable full-text indexing (Phase 8)
# In .env:
SEARCH_FULL_TEXT_ENABLED=true
```

### High CPU Usage

**Symptom**: System responsive but CPU at 100%

```bash
# Check which process
docker stats --no-stream

# Profile Python
docker-compose exec basset_api python -m cProfile -s cumulative main.py

# Check query intensity
docker-compose logs basset_api | grep "query took"

# Reduce concurrent operations
# In docker-compose.yml:
WORKER_THREADS=2  # Reduce from 4
```

### Memory Leaks

**Symptom**: Memory usage grows over time

```bash
# Monitor memory
watch -n 5 'docker stats basset_api --no-stream'

# Check for growing collections in Python
docker-compose exec basset_api python -m memory_profiler main.py

# Restart service (temporary)
docker-compose restart basset_api

# Enable cache cleanup
# In .env:
CACHE_MAX_SIZE_MB=512
CACHE_EVICTION_POLICY=lru
```

---

## Integration Issues

### basset-verify Not Responding

**Symptom**: Verification endpoints timeout

```bash
# Check if service is running
docker-compose ps basset_verify

# Test endpoint
curl http://localhost:8081/health

# Check logs
docker-compose logs basset_verify

# Verify network connectivity
docker-compose exec basset_api curl http://basset_verify:8000/health
```

### WebSocket Connection Failed

**Symptom**: Real-time updates not working

```bash
# Check WebSocket endpoint
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" \
  http://localhost:8080/ws/suggestions/test

# Check nginx WebSocket proxy
docker-compose exec nginx grep -A5 "location /ws" /etc/nginx/nginx.conf

# View WebSocket logs
docker-compose logs nginx | grep websocket
```

### Cletus News Feed Issues

**Symptom**: News feed not updating

```bash
# Check cletus service
curl http://localhost:8082/health

# View logs
docker-compose logs cletus

# Check API token
grep CLETUS_API_KEY .env
```

---

## Advanced Debugging

### Enable Debug Mode

```bash
# Set environment variable
export DEBUG=true

# Or add to .env
DEBUG=true

# Restart service
docker-compose restart basset_api

# Check debug logs
docker-compose logs basset_api | grep "DEBUG"
```

### Database Query Debugging

```bash
# Enable query logging
docker-compose exec neo4j cypher-shell -u neo4j -p neo4jbasset \
  "CALL dbms.setConfig('server.logs.query.enabled', 'true')"

# View queries being executed
docker-compose exec neo4j tail -f /var/lib/neo4j/logs/query.log

# Filter for slow queries
docker-compose exec neo4j tail -f /var/lib/neo4j/logs/query.log | \
  grep -E "took [0-9]{4,}ms"
```

### API Request Tracing

```bash
# Capture detailed request/response
curl -v http://localhost:8080/api/v1/projects

# With timing breakdown
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8080/api/v1/projects

# Curl format file (save as curl-format.txt):
# ========================
#     time_namelookup:  %{time_namelookup}
#        time_connect:  %{time_connect}
#     time_appconnect:  %{time_appconnect}
#    time_pretransfer:  %{time_pretransfer}
#       time_redirect:  %{time_redirect}
#  time_starttransfer:  %{time_starttransfer}
#  time_total:  %{time_total}
# ========================
```

### Container Inspection

```bash
# View container internals
CONTAINER=$(docker-compose ps -q basset_api)

# List processes
docker exec $CONTAINER ps aux

# Check network connections
docker exec $CONTAINER netstat -tlnp

# View environment variables
docker exec $CONTAINER env

# Check disk usage
docker exec $CONTAINER du -sh /app
```

---

## Getting Help

### Collect Information for Support

```bash
#!/bin/bash
# save as collect-debug-info.sh

mkdir -p debug-info
cd debug-info

echo "Collecting debug information..."

# System info
uname -a > system.txt
docker --version >> system.txt

# Service status
docker-compose ps > services.txt
docker stats --no-stream > docker-stats.txt

# Logs (last 100 lines)
docker-compose logs --tail=100 > combined.log

# API health
curl http://localhost:8080/health > api-health.json 2>&1

# Database info
docker-compose exec neo4j cypher-shell -u neo4j -p neo4jbasset \
  "CALL dbms.info()" > neo4j-info.txt 2>&1

# Environment (sanitized)
grep -v PASSWORD .env > environment.txt 2>/dev/null || echo "No .env file" > environment.txt

echo "Debug info collected in debug-info/"
tar czf debug-info.tar.gz *.txt *.log *.json
echo "Created debug-info.tar.gz for sharing"
```

### Support Resources

**Documentation**:
- [SETUP.md](./SETUP.md) - Local development setup
- [DEPLOYMENT.md](./DEPLOYMENT.md) - Production deployment
- [API_REFERENCE.md](./API_REFERENCE.md) - API documentation
- [ARCHITECTURE.md](./ARCHITECTURE.md) - System architecture

**Community**:
- GitHub Issues: https://github.com/yourusername/basset-hound/issues
- GitHub Discussions: https://github.com/yourusername/basset-hound/discussions

**Official Support**:
- Email: support@example.com
- Documentation: https://docs.basset-hound.example.com

### Filing a Bug Report

Include:
1. Clear description of the issue
2. Steps to reproduce
3. Expected vs actual behavior
4. Output of `check-system.sh` script above
5. Relevant log excerpts
6. Environment info (OS, Docker version, etc.)

---

## Common Solutions Quick Reference

| Problem | Quick Fix |
|---------|-----------|
| Services not starting | `docker-compose down -v && docker-compose up --build` |
| High memory | Reduce heap: `NEO4J_HEAP_MEMORY=512M` |
| Slow queries | Enable caching: `CACHE_ENABLED=true` |
| Dashboard blank | Use API directly: `/docs` (known blocker) |
| Port in use | Kill process: `lsof -i :8080 \| kill -9` |
| Database locked | Restart Neo4j: `docker-compose restart neo4j` |
| WebSocket issues | Check nginx proxy config |
| Out of disk | `docker system prune -a` |
| Certificate errors | Check HTTPS setup in DEPLOYMENT.md |

---

**Last Updated**: 2026-05-19  
**Related**: BLOCKERS-2026-05-07.md | DEPLOYMENT.md | ARCHITECTURE.md
