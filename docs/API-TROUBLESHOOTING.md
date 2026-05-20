# Basset Hound API Troubleshooting Guide

**Last Updated**: 2026-05-19  
**Version**: 3.0.0

---

## Quick Diagnostic

Before diving deep, run these commands:

```bash
# 1. Check API is responding
curl -s http://localhost:8080/health | jq '.services'

# 2. Check if you can list projects
curl -s http://localhost:8080/api/v1/projects | jq '.data | length'

# 3. Check response times
curl -w "Time: %{time_total}s\n" -o /dev/null -s http://localhost:8080/api/v1/projects

# 4. Check cache stats
curl -s http://localhost:8080/api/v1/cache/stats | jq '.data'
```

---

## Common Issues & Solutions

### Authentication Issues

#### 401 Unauthorized

**Symptoms**:
```
{
  "error": {
    "code": "AUTHENTICATION_FAILED",
    "message": "Invalid token"
  }
}
```

**Solutions**:

1. **Check token format**
   ```bash
   # Token must have "Bearer " prefix
   curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8080/api/v1/projects
   
   # NOT this:
   curl -H "Authorization: YOUR_TOKEN" ...
   ```

2. **Check token expiration**
   ```python
   import jwt
   token = "YOUR_TOKEN"
   decoded = jwt.decode(token, options={"verify_signature": False})
   print(f"Expires: {decoded['exp']}")
   ```

3. **Refresh expired token**
   ```bash
   curl -X POST http://localhost:8080/api/v1/auth/refresh \
     -H "Content-Type: application/json" \
     -d '{"refresh_token": "YOUR_REFRESH_TOKEN"}'
   ```

4. **Check if auth is enabled**
   ```bash
   # In development, auth may be disabled
   curl http://localhost:8080/api/v1/projects
   # Should work even without Authorization header
   ```

#### 403 Forbidden

**Symptoms**:
```
{
  "error": {
    "code": "PERMISSION_DENIED",
    "message": "Insufficient permissions"
  }
}
```

**Solutions**:
1. Check user scopes: `GET /auth/me`
2. Verify user role has required permissions
3. Contact admin to grant permissions
4. Check token scopes: `["read:projects", "write:entities"]`

---

### Entity Not Found

#### 404 Entity Not Found

**Symptoms**:
```bash
GET /api/v1/projects/proj_123/entities/ent_invalid
# Returns 404
```

**Solutions**:

1. **List entities to find correct ID**
   ```bash
   curl 'http://localhost:8080/api/v1/projects/proj_123/entities' | jq '.data[0].id'
   ```

2. **Check entity was created**
   ```bash
   curl 'http://localhost:8080/api/v1/projects/proj_123/entities?search=john' | jq '.data'
   ```

3. **Verify project_id is correct**
   ```bash
   curl 'http://localhost:8080/api/v1/projects' | jq '.data[].id'
   ```

4. **Check audit log**
   ```bash
   curl 'http://localhost:8080/api/v1/projects/proj_123/audit?type=entity.created'
   ```

---

### Rate Limiting

#### 429 Too Many Requests

**Symptoms**:
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded",
    "retry_after": 45
  }
}
```

**Limits**:
- 100 requests per minute per IP
- 1000 requests per hour per IP
- 20 concurrent simultaneous requests

**Solutions**:

1. **Check rate limit headers**
   ```bash
   curl -i http://localhost:8080/api/v1/projects | grep X-RateLimit
   
   # Output:
   # X-RateLimit-Limit: 100
   # X-RateLimit-Remaining: 23
   # X-RateLimit-Reset: 1725340800
   ```

2. **Implement exponential backoff**
   ```python
   import time
   import requests
   
   def retry_with_backoff(url, max_attempts=5):
       for attempt in range(max_attempts):
           response = requests.get(url)
           
           if response.status_code != 429:
               return response
           
           retry_after = int(response.headers.get('Retry-After', 60))
           print(f"Attempt {attempt+1}: Rate limited, waiting {retry_after}s")
           time.sleep(retry_after)
       
       raise Exception("Max retries exceeded")
   ```

3. **Batch requests efficiently**
   ```python
   # Instead of many small requests
   for entity in entities:
       requests.post(f'/entities', json=entity)  # Bad
   
   # Batch them
   for i in range(0, len(entities), 50):
       batch = entities[i:i+50]
       for entity in batch:
           requests.post(f'/entities', json=entity)
       time.sleep(5)  # Wait between batches
   ```

4. **Check if using shared IP**
   - If behind NAT/proxy, multiple users share rate limit
   - Consider contacting support for higher limits
   - Use API key instead of IP-based limiting (if available)

---

### Performance Issues

#### Slow Queries (>1000ms)

**Symptoms**:
```bash
curl -w "Response time: %{time_total}s\n" \
  http://localhost:8080/api/v1/projects/proj_123/search/advanced \
  -d '{"query": "john"}'

# Response time: 2.345s  <- TOO SLOW
```

**Solutions**:

1. **Check query complexity**
   ```bash
   # Simple queries should be <100ms
   curl 'http://localhost:8080/api/v1/projects/proj_123/entities?limit=10'
   
   # Complex queries may be slower
   curl -X POST \
     http://localhost:8080/api/v1/projects/proj_123/search/advanced \
     -d '{"query": "complex AND filter"}'
   ```

2. **Check database health**
   ```bash
   curl http://localhost:8080/health | jq '.services.neo4j'
   
   # Should show:
   # {
   #   "status": "connected",
   #   "latency_ms": 2
   # }
   ```

3. **Check cache hit rate**
   ```bash
   curl http://localhost:8080/api/v1/cache/stats | jq '.data.hit_rate'
   
   # Should be >0.60 (60%)
   # If <0.50, cache not working
   ```

4. **Use pagination to reduce payload**
   ```bash
   # Bad: Fetch all 10000 entities
   curl 'http://localhost:8080/api/v1/projects/proj_123/entities'
   
   # Good: Use pagination
   curl 'http://localhost:8080/api/v1/projects/proj_123/entities?limit=50&offset=0'
   ```

5. **Check for missing indexes**
   ```bash
   curl -X POST http://localhost:8080/api/v1/projects/proj_123/optimize \
     -H "Authorization: Bearer TOKEN"
   
   # This rebuilds indexes and optimizes performance
   ```

6. **Profile slow endpoints**
   ```python
   import requests
   import time
   
   endpoints = [
       '/projects/proj_123/entities',
       '/projects/proj_123/search/advanced',
       '/projects/proj_123/relationships'
   ]
   
   for endpoint in endpoints:
       start = time.time()
       response = requests.get(f'http://localhost:8080/api/v1{endpoint}')
       elapsed = time.time() - start
       count = len(response.json()['data'])
       rate = count / elapsed
       print(f'{endpoint}: {elapsed:.2f}s ({rate:.0f} items/s)')
   ```

---

### Connection Issues

#### Connection Timeout

**Symptoms**:
```
ConnectionError: ('Connection aborted.', timeout('_ssl.c:1129: The handshake operation timed out'))
```

**Solutions**:

1. **Check server is running**
   ```bash
   curl -s http://localhost:8080/health
   # Should return health status
   ```

2. **Check network connectivity**
   ```bash
   ping localhost
   # or
   telnet localhost 8080
   ```

3. **Increase timeout**
   ```python
   import requests
   
   response = requests.get(
       'http://localhost:8080/api/v1/projects',
       timeout=(5, 30)  # Connect timeout 5s, read timeout 30s
   )
   ```

4. **Check firewall**
   ```bash
   # On Linux
   sudo ufw status
   
   # On Mac
   sudo pfctl -s nat
   
   # On Windows
   netsh advfirewall show allprofiles
   ```

5. **Check if endpoint exists**
   ```bash
   curl -v http://localhost:8080/api/v1/projects 2>&1 | head -20
   ```

---

#### Connection Pool Exhausted

**Symptoms**:
```
ConnectionPoolError: Max retries exceeded with url
```

**Solutions**:

1. **Check pool size**
   ```bash
   curl http://localhost:8080/health | jq '.services.redis.pool_size'
   
   # Default is 100, may need increase for high concurrency
   ```

2. **Increase pool size** (in .env)
   ```
   REDIS_MAX_CONNECTIONS=150
   NEO4J_MAX_CONNECTION_POOL_SIZE=150
   ```

3. **Restart API**
   ```bash
   # Kill existing process
   pkill -f "uvicorn"
   
   # Restart
   python -m api.main
   ```

4. **Use connection pooling in your client**
   ```python
   import requests
   from requests.adapters import HTTPAdapter
   from urllib3.util.retry import Retry
   
   session = requests.Session()
   
   # Configure retries
   retry = Retry(
       total=3,
       backoff_factor=0.3,
       status_forcelist=(429, 500, 502, 503, 504)
   )
   
   # Configure adapter
   adapter = HTTPAdapter(
       max_retries=retry,
       pool_connections=100,
       pool_maxsize=100
   )
   
   session.mount('http://', adapter)
   session.mount('https://', adapter)
   ```

---

### Database Issues

#### Neo4j Connection Failed

**Symptoms**:
```bash
curl http://localhost:8080/health | jq '.services.neo4j.status'
# Returns: "disconnected"
```

**Solutions**:

1. **Check Neo4j is running**
   ```bash
   # Check process
   ps aux | grep neo4j
   
   # Or test connection
   nc -zv localhost 7687
   ```

2. **Check Neo4j credentials** (in .env)
   ```
   NEO4J_URI=bolt://localhost:7687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=neo4jbasset
   ```

3. **Check Neo4j logs**
   ```bash
   # Docker
   docker logs neo4j 2>&1 | tail -50
   
   # Or check log file
   tail -f /var/log/neo4j/neo4j.log
   ```

4. **Restart Neo4j**
   ```bash
   # Docker
   docker restart neo4j
   
   # Or systemd
   sudo systemctl restart neo4j
   ```

5. **Check disk space**
   ```bash
   df -h
   # Neo4j needs space to operate, check available space
   ```

---

#### Database Timeout

**Symptoms**:
```json
{
  "error": {
    "code": "DATABASE_ERROR",
    "message": "Neo4j connection timeout after 30s"
  }
}
```

**Solutions**:

1. **Check Neo4j performance**
   ```bash
   # Connect to Neo4j
   cypher-shell -u neo4j -p neo4jbasset
   
   # Check slow queries
   CALL dbms.queryJobs() YIELD username, statement, allocatedBytes;
   ```

2. **Increase connection timeout** (in .env)
   ```
   NEO4J_CONNECTION_TIMEOUT=60
   ```

3. **Optimize queries**
   - Add indexes: `CREATE INDEX ON :Entity(name)`
   - Use EXPLAIN to analyze plans: `EXPLAIN MATCH (n) RETURN n`
   - Check for missing indexes

4. **Check for connection leaks**
   ```bash
   # Monitor connections
   curl http://localhost:8080/health | jq '.services.neo4j.pool_size'
   ```

---

### Data Issues

#### Empty Results from Search

**Symptoms**:
```bash
curl 'http://localhost:8080/api/v1/projects/proj_123/search/advanced' \
  -d '{"query": "john"}' | jq '.data'
# Returns: []
```

**Solutions**:

1. **Verify entities exist**
   ```bash
   curl 'http://localhost:8080/api/v1/projects/proj_123/entities' | jq '.meta.total_count'
   # Should be >0
   ```

2. **Check entity data**
   ```bash
   curl 'http://localhost:8080/api/v1/projects/proj_123/entities?limit=1' | jq '.data[0]'
   ```

3. **Simplify search query**
   ```bash
   # Complex query may match nothing
   curl 'http://localhost:8080/api/v1/projects/proj_123/search/advanced' \
     -d '{"query": "john AND email:*@example.com"}'
   
   # Try simpler query
   curl 'http://localhost:8080/api/v1/projects/proj_123/search/advanced' \
     -d '{"query": "john"}'
   ```

4. **Check index status**
   ```bash
   curl 'http://localhost:8080/api/v1/projects/proj_123/search/stats' | jq '.data'
   ```

5. **Rebuild search index**
   ```bash
   curl -X POST 'http://localhost:8080/api/v1/projects/proj_123/search/reindex' \
     -H "Authorization: Bearer TOKEN"
   ```

---

#### Duplicate Entities

**Symptoms**: Same entity appears multiple times in results

**Solutions**:

1. **Find duplicates**
   ```bash
   curl -X POST \
     http://localhost:8080/api/v1/projects/proj_123/deduplication/find \
     -d '{"threshold": 0.85}'
   ```

2. **Merge duplicates**
   ```bash
   curl -X POST \
     http://localhost:8080/api/v1/projects/proj_123/entities/merge \
     -d '{
       "source_id": "ent_001",
       "target_id": "ent_002",
       "strategy": "merge_all_data"
     }'
   ```

3. **Enable auto-linking**
   ```bash
   curl -X POST \
     http://localhost:8080/api/v1/projects/proj_123/auto-linker/scan
   ```

---

### Request Issues

#### 400 Bad Request

**Symptoms**:
```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Invalid field: 'name' is required",
    "details": {
      "field": "name",
      "constraint": "required"
    }
  }
}
```

**Solutions**:

1. **Check required fields**
   ```python
   # GET /projects returns spec
   # POST /projects requires: name
   
   # Bad:
   requests.post('/projects', json={})
   
   # Good:
   requests.post('/projects', json={'name': 'My Project'})
   ```

2. **Validate JSON format**
   ```bash
   # Validate JSON
   echo '{"name": "test"}' | jq .
   
   # Should return valid JSON, not error
   ```

3. **Check field types**
   ```python
   # If field expects integer
   {"limit": 10}  # Correct
   {"limit": "10"}  # Wrong
   ```

4. **Review API documentation**
   - Check `/docs` Swagger UI
   - Review API-REFERENCE-COMPREHENSIVE.md
   - Check field types and constraints

---

#### 422 Unprocessable Entity

**Symptoms**:
```json
{
  "error": "validation error",
  "details": [
    {
      "field": "email",
      "message": "Invalid email format"
    }
  ]
}
```

**Solutions**:

1. **Validate email format**
   ```python
   import re
   email = "john@example.com"
   if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
       print("Valid email")
   ```

2. **Check field constraints**
   - Length: Check min/max length
   - Format: Email, URL, etc.
   - Type: String, integer, etc.

3. **Use validated client**
   ```python
   from pydantic import BaseModel, EmailStr, Field
   
   class EntityCreate(BaseModel):
       name: str = Field(..., min_length=1, max_length=255)
       email: EmailStr
       phone: str = Field(..., regex=r'^\+?1?\d{9,15}$')
   
   # Validates before sending
   entity = EntityCreate(
       name="John Doe",
       email="john@example.com",
       phone="+15550100"
   )
   ```

---

### WebSocket Issues

#### WebSocket Connection Failed

**Symptoms**:
```javascript
WebSocket is closed before the connection is established.
```

**Solutions**:

1. **Check WebSocket URL format**
   ```javascript
   // Correct format
   ws://localhost:8080/api/v1/projects/proj_123/ws?token=YOUR_TOKEN
   
   // Wrong:
   http://localhost:8080/...  // Should be ws:// not http://
   ```

2. **Check token is valid**
   ```javascript
   // Verify token works with HTTP API first
   fetch('/api/v1/projects', {
       headers: { 'Authorization': `Bearer ${token}` }
   })
   ```

3. **Check CORS configuration**
   ```bash
   # CORS headers should allow WebSocket
   curl -i http://localhost:8080/health | grep -i access-control
   ```

4. **Monitor WebSocket health**
   ```bash
   curl http://localhost:8080/api/v1/ws/health | jq '.data.pool'
   ```

---

### Cache Issues

#### Cache Not Working

**Symptoms**:
- Slow repeated queries (not cached)
- Cache hit rate <0.5

**Solutions**:

1. **Check cache is enabled**
   ```bash
   curl http://localhost:8080/api/v1/cache/stats | jq '.data'
   
   # Should show:
   # {
   #   "hit_rate": 0.623,
   #   "total_keys": 12450
   # }
   ```

2. **Check Redis connection**
   ```bash
   curl http://localhost:8080/health | jq '.services.redis.status'
   # Should be "connected"
   ```

3. **Check cache TTL**
   ```bash
   # Default cache TTL is 3600s (1 hour)
   # Queries cached for: project lists, entity counts, search results
   # Not cached: real-time data, reports
   ```

4. **Clear cache if needed**
   ```bash
   curl -X POST http://localhost:8080/api/v1/cache/clear \
     -H "Authorization: Bearer TOKEN"
   ```

5. **Enable debug logging**
   ```bash
   # Set in environment
   DEBUG=true
   
   # Check logs for cache hits/misses
   tail -f logs/api.log | grep cache
   ```

---

## Debug Techniques

### Enable Debug Mode

```bash
# Set environment variable
export DEBUG=true

# Or in .env
DEBUG=true

# Restart API
```

### Check Logs

```bash
# Docker
docker logs -f api

# Or file
tail -f logs/api.log

# Filter by level
grep -i error logs/api.log
grep -i warning logs/api.log
```

### Use Verbose cURL

```bash
# Show headers and timing
curl -v http://localhost:8080/api/v1/projects

# Show only headers
curl -i http://localhost:8080/api/v1/projects

# Show timing details
curl -w "\n
time_namelookup: %{time_namelookup}
time_connect: %{time_connect}
time_appconnect: %{time_appconnect}
time_pretransfer: %{time_pretransfer}
time_redirect: %{time_redirect}
time_starttransfer: %{time_starttransfer}
time_total: %{time_total}\n" \
  http://localhost:8080/api/v1/projects
```

### Profile Performance

```python
import requests
import time

def profile_endpoint(url, label):
    start = time.time()
    response = requests.get(url)
    elapsed = time.time() - start
    
    print(f"{label}:")
    print(f"  Status: {response.status_code}")
    print(f"  Time: {elapsed:.3f}s")
    print(f"  Size: {len(response.content)} bytes")
    
    # Calculate speed
    if elapsed > 0:
        speed = len(response.content) / elapsed / 1024 / 1024
        print(f"  Speed: {speed:.2f} MB/s")

profile_endpoint('http://localhost:8080/api/v1/projects', 'Projects List')
profile_endpoint('http://localhost:8080/api/v1/projects/proj_123/entities', 'Entities List')
profile_endpoint('http://localhost:8080/api/v1/projects/proj_123/export/json', 'Export JSON')
```

---

## Getting Help

### Resources

1. **API Documentation**
   - Swagger UI: `http://localhost:8080/docs`
   - ReDoc: `http://localhost:8080/redoc`
   - OpenAPI: `http://localhost:8080/openapi.json`

2. **Health Check**
   - Status: `http://localhost:8080/health`
   - WebSocket: `http://localhost:8080/api/v1/ws/health`
   - Cache: `http://localhost:8080/api/v1/cache/stats`

3. **Documentation Files**
   - API-REFERENCE-COMPREHENSIVE.md - Complete endpoint reference
   - INTEGRATION-GUIDE.md - Integration patterns
   - WEBHOOK-DOCUMENTATION.md - Webhook setup
   - This file - Troubleshooting guide

4. **Contact Support**
   - Email: support@basset-hound.com
   - Include: Error message, steps to reproduce, API logs

---

**Last Updated**: 2026-05-19  
**Version**: 3.0.0
