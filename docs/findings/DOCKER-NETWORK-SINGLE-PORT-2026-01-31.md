# Docker Network Single-Port Entry Implementation

**Date**: 2026-01-31
**Status**: Complete
**Session**: Docker network refactoring for single-port entry

---

## Summary

Implemented a single-port entry architecture for Basset Hound using nginx as a reverse proxy. All services now communicate internally via the `basset-hound` Docker network, with only port 8080 exposed to the host.

---

## Changes Made

### 1. Created nginx Configuration

**File**: `nginx/nginx.conf`

- Nginx reverse proxy listening on port 8080
- Routes all traffic to `basset_api:8000`
- Provides Neo4j browser access at `/neo4j/`
- WebSocket support for real-time features
- Gzip compression for performance
- Security headers (X-Frame-Options, X-XSS-Protection, etc.)
- Health endpoint at `/nginx-health`

### 2. Updated docker-compose.yml

**Key Changes**:

| Before | After |
|--------|-------|
| Network: `basset_network` | Network: `basset-hound` |
| 4 ports exposed (7475, 7688, 6379, 8000) | 1 port exposed (8080) |
| No reverse proxy | Nginx as entry point |

**Services Updated**:

| Service | Old Ports | New Ports |
|---------|-----------|-----------|
| nginx | N/A | 8080:8080 (NEW) |
| neo4j | 7475:7474, 7688:7687 | Internal only |
| redis | 6379:6379 | Internal only |
| basset_api | 8000:8000 | Internal only |
| celery_worker | - | Internal only |
| celery_beat | - | Internal only |

### 3. Created Development Override

**File**: `docker-compose.dev.yml`

For debugging, expose internal ports:
```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

Exposed ports in dev mode:
- Neo4j Browser: `localhost:7475`
- Neo4j Bolt: `localhost:7688`
- Redis: `localhost:6379`
- Basset API: `localhost:8000`

---

## Architecture

```
                    ┌─────────────────────────────────────────────────┐
                    │           basset-hound network                  │
                    │                                                 │
  User              │  ┌─────────┐        ┌──────────────┐           │
    │               │  │  nginx  │───────>│  basset_api  │           │
    │  Port 8080    │  │  :8080  │        │    :8000     │           │
    └──────────────>│  └─────────┘        └──────┬───────┘           │
                    │       │                    │                    │
                    │       │ /neo4j/            │                    │
                    │       v                    v                    │
                    │  ┌─────────┐        ┌──────────────┐           │
                    │  │  neo4j  │<───────│    redis     │           │
                    │  │  :7474  │        │    :6379     │           │
                    │  │  :7687  │        └──────────────┘           │
                    │  └─────────┘               ^                    │
                    │                            │                    │
                    │                    ┌───────┴───────┐           │
                    │                    │ celery_worker │           │
                    │                    │ celery_beat   │           │
                    │                    └───────────────┘           │
                    └─────────────────────────────────────────────────┘
```

---

## Access Points

### Production (Single Port)

| URL | Service |
|-----|---------|
| `http://localhost:8080/` | Basset Hound UI & API |
| `http://localhost:8080/docs` | OpenAPI Documentation |
| `http://localhost:8080/redoc` | ReDoc Documentation |
| `http://localhost:8080/api` | API Root |
| `http://localhost:8080/health` | Health Check |
| `http://localhost:8080/neo4j/` | Neo4j Browser (admin) |
| `http://localhost:8080/mcp/*` | MCP endpoints for AI agents |

### Development (Direct Access)

Use override file: `docker compose -f docker-compose.yml -f docker-compose.dev.yml up`

| URL | Service |
|-----|---------|
| `http://localhost:7475` | Neo4j Browser (direct) |
| `bolt://localhost:7688` | Neo4j Bolt (direct) |
| `localhost:6379` | Redis (direct) |
| `http://localhost:8000` | API (direct) |

---

## Testing Results

```
Test Results (2026-01-31):

✅ basset-hound network created
✅ All 6 containers connected to network
✅ Port 8080 exposed via nginx
✅ /nginx-health returns 200
✅ /health returns healthy status
✅ /api returns API info
✅ /docs accessible (200)
✅ /neo4j/ proxied to Neo4j browser (200)
✅ Internal ports not directly accessible
```

---

## Benefits

1. **Simplified Port Management**: Only one port (8080) to remember/configure
2. **Internal Isolation**: Services communicate internally, not exposed to host
3. **Centralized Entry**: All traffic flows through nginx for logging/security
4. **Easy Integration**: External projects connect to single endpoint
5. **Production Ready**: Can add TLS, rate limiting, caching at nginx level

---

## Files Created/Modified

| File | Action |
|------|--------|
| `nginx/nginx.conf` | Created |
| `docker-compose.yml` | Modified |
| `docker-compose.dev.yml` | Created |
| `tests/test_docker_network.sh` | Created |

---

## Usage

### Start Services
```bash
docker compose up --build -d
```

### Access Basset Hound
```bash
open http://localhost:8080
```

### View Logs
```bash
docker compose logs -f nginx
docker compose logs -f basset_api
```

### Stop Services
```bash
docker compose down -v
```

---

## Integration Notes

External projects (palletai, basset-verify, basset-hound-browser) should now connect to:

- **API**: `http://basset-hound:8080/api/v1/` (when on same Docker network)
- **MCP**: `http://basset-hound:8080/mcp/` (for AI agent tools)
- **Health**: `http://basset-hound:8080/health` (for health checks)

For external access from host:
- Use `http://localhost:8080/` for all endpoints
