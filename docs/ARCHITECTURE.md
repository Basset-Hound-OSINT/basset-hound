# Basset Hound - System Architecture

**Version**: 2.0.0  
**Last Updated**: 2026-05-07  
**Status**: Production Ready

## Table of Contents

1. [System Overview](#system-overview)
2. [Technology Stack](#technology-stack)
3. [Service Architecture](#service-architecture)
4. [Data Flow](#data-flow)
5. [Component Diagrams](#component-diagrams)
6. [Database Schema](#database-schema)
7. [Authentication Flow](#authentication-flow)
8. [Integration Architecture](#integration-architecture)
9. [Performance Optimizations (Phase 8)](#performance-optimizations-phase-8)
10. [Deployment Architecture](#deployment-architecture)

---

## System Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      External Services                           │
│  basset-verify │ basset-hound-browser │ cletus │ Claude API    │
└─────────────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┴─────────────────┐
        ▼                                   ▼
┌──────────────────────┐        ┌──────────────────────┐
│   NGINX (Port 8080)  │        │  Reverse Proxy Log   │
│ - SSL Termination    │        │  - Request routing   │
│ - Load balancing     │        │  - Rate limiting     │
│ - Static files       │        │  - Compression       │
└──────────────────────┘        └──────────────────────┘
        │
        ├─────────────────┬─────────────────┬──────────────┐
        ▼                 ▼                 ▼              ▼
┌────────────────┐ ┌────────────────┐ ┌──────────────┐ ┌──────────┐
│  FastAPI API   │ │   Web UI       │ │  MCP Server  │ │Websocket │
│  (REST+JSON)   │ │ (Jinja2+React) │ │  (AI Tools)  │ │ Broadcast│
│ 50+ Endpoints  │ │ Dashboard      │ │ 119 Tools    │ │Events    │
└────────────────┘ └────────────────┘ └──────────────┘ └──────────┘
        │                    │                    │         │
        └────────────────────┼────────────────────┴─────────┘
                             ▼
        ┌────────────────────────────────────┐
        │     Services Layer (async)         │
        ├────────────────────────────────────┤
        │ Entity  │ Orphan │ Search │ Graph  │
        │ Service │ Data   │ Service│Service │
        │         │ Service│        │        │
        │ Report  │ Timeline│ Cache │ Job   │
        │ Service │ Service │Service│Service│
        └────────────────────────────────────┘
                             ▼
        ┌────────────────────────────────────┐
        │     Data Access Layer (DAL)        │
        ├────────────────────────────────────┤
        │  Neo4j  │  Redis  │  File   │Cache │
        │  Handler│ Handler │ Storage │Layer │
        └────────────────────────────────────┘
                             ▼
        ┌──────────────┬──────────────┬──────────────┐
        ▼              ▼              ▼              ▼
    ┌────────┐   ┌──────────┐   ┌────────┐  ┌─────────────┐
    │ Neo4j  │   │  Redis   │   │Projects│  │ Prometheus  │
    │ Graph  │   │  Cache   │   │Storage │  │  Metrics    │
    │ 5.28   │   │  7.x     │   │(Local) │  │             │
    └────────┘   └──────────┘   └────────┘  └─────────────┘
```

---

## Technology Stack

### Core Framework
- **Web Server**: FastAPI 0.115+ (async Python)
- **Web Proxy**: Nginx (reverse proxy, SSL/TLS)
- **Language**: Python 3.12+

### Database & Storage
- **Graph Database**: Neo4j 5.28 (Community or Enterprise)
- **Cache/Queue**: Redis 7.x
- **File Storage**: Local filesystem (projects directory)

### Frontend & UI
- **Template Engine**: Jinja2 3.1+
- **UI Framework**: React/Vue (optional components)
- **Visualization**: D3.js, Cytoscape, vis.js

### Monitoring & Observability
- **Metrics**: Prometheus 2.45+
- **Dashboards**: Grafana 10.0+
- **Logging**: Structured JSON logging (stdout)
- **Log Aggregation**: Filebeat, Logstash (optional)

### Integration & AI
- **MCP Protocol**: 1.0+ (Model Context Protocol)
- **WebSocket**: For real-time updates
- **HTTP Client**: httpx 0.27+
- **Message Queue**: Celery + Redis

### Development & Testing
- **Testing**: pytest 8.3+, pytest-asyncio
- **Code Quality**: ruff 0.8+, mypy 1.13+
- **Type Hints**: Full Python type coverage
- **Documentation**: Markdown + Sphinx

### Deployment & Container
- **Container Runtime**: Docker 24.0+
- **Orchestration**: Docker Compose 2.20+
- **OS**: Ubuntu 22.04 LTS (recommended)

---

## Service Architecture

### FastAPI Application Structure

```
api/
├── main.py                 # Application entry point
├── config.py               # Configuration management
├── dependencies.py         # Dependency injection
├── models/                 # Pydantic models
│   ├── entity.py
│   ├── relationship.py
│   ├── orphan.py
│   └── ...
├── routers/                # API route handlers (20+ files)
│   ├── entities.py
│   ├── relationships.py
│   ├── suggestions.py
│   ├── search.py
│   ├── reports.py
│   ├── verification.py
│   ├── platforms.py
│   ├── graph_analysis.py
│   └── ...
├── services/               # Business logic layer (50+ files)
│   ├── entity_service.py
│   ├── suggestion_service.py
│   ├── search_service.py
│   ├── cache_service.py
│   ├── neo4j_service.py
│   └── ...
├── middleware/             # Request/response processing
│   ├── metrics.py          # Prometheus middleware
│   ├── cors.py
│   └── error_handler.py
└── utils/                  # Helper functions
    ├── logger.py
    └── validators.py
```

### Neo4j Handler

```
neo4j_handler.py
├── Connection pooling
├── Cypher query execution
├── Schema management
├── Transaction handling
├── Index creation
└── Backup/restore operations
```

### Async Task Queue

```
api/tasks/
├── maintenance_tasks.py    # Periodic maintenance
├── import_tasks.py         # Bulk operations
├── report_generation.py    # PDF generation
└── cache_warming.py        # Cache management
```

### Web UI (Frontend)

```
templates/
├── base.html               # Base template
├── dashboard.html          # Main dashboard
├── entities/
│   ├── list.html
│   ├── detail.html
│   └── create.html
├── relationships/
├── search/
├── reports/
└── includes/
    ├── navbar.html
    ├── sidebar.html
    └── graphs.html
```

---

## Data Flow

### Entity Creation Flow

```
User Request
    │
    ▼
POST /api/v1/projects/{id}/entities
    │
    ▼
FastAPI Route Handler (entities.py)
    │
    ├─► Validate request (Pydantic)
    ├─► Check auth (if enabled)
    └─► Call EntityService
        │
        ▼
        EntityService.create_entity()
        │
        ├─► Normalize data (emails, phones, etc.)
        ├─► Generate unique ID
        ├─► Call Neo4jService
        └─► Trigger suggestions (async)
            │
            ▼
            Neo4jService.create_entity()
            │
            ├─► Execute Cypher query
            ├─► Create node + indexes
            ├─► Update Prometheus metrics
            └─► Return entity
                │
                ▼
                SuggestionService (async)
                │
                ├─► Find potential matches
                ├─► Calculate confidence
                ├─► Store suggestions
                └─► Notify via WebSocket
                    │
                    ▼
                    Publish to Redis pub/sub
                    │
                    ▼
                    Connected WebSocket clients
```

### Search Flow

```
User Query
    │
    ▼
GET /api/v1/projects/{id}/search/advanced?query=...
    │
    ▼
SearchRouter.search()
    │
    ▼
SearchService.advanced_search()
    │
    ├─► Parse query (Boolean operators)
    ├─► Check cache (Redis)
    ├─► If cache miss:
    │   ├─► Convert to Cypher
    │   ├─► Execute query
    │   ├─► Score results
    │   └─► Cache results (TTL: 3600s)
    │
    ▼
Return ranked results with highlights
```

### Report Generation Flow

```
User Request
    │
    ▼
POST /api/v1/projects/{id}/reports/generate
    │
    ▼
ReportRouter.generate_report()
    │
    ├─► Validate parameters
    └─► Queue async task
        │
        ▼
        Celery Task (ReportService)
        │
        ├─► Fetch entity data
        ├─► Build report structure (LaTeX)
        ├─► Generate PDF via PyLaTeX
        ├─► Save to storage
        ├─► Update database
        └─► Notify via WebSocket
            │
            ▼
            User can download
```

---

## Component Diagrams

### Entity-Relationship Model

```
┌──────────────────┐
│  Project         │
│ - id (PK)        │
│ - name           │
│ - created_at     │
└──────────────────┘
        │
        │ CONTAINS (1:N)
        ▼
┌──────────────────┐
│  Entity          │ ◄─────────┐
│ - id (PK)        │           │
│ - type           │    OWNS (1:N)
│ - name           │           │
│ - attributes {}  │           │
│ - project_id (FK)            │
│ - created_at     │    ┌──────────────────┐
└──────────────────┘    │  Platform        │
        │               │ - id (PK)        │
        │ HAS (1:N)     │ - name           │
        └──────────────►│ - domain         │
                        │ - field_schema[]│
        ┌──────────────►└──────────────────┘
        │
        │ (Account)
        │
    ┌───────────────────────────┐
    │ Relationship              │
    │ - id (PK)                 │
    │ - source_id (FK)          │
    │ - target_id (FK)          │
    │ - type                    │
    │ - properties {}           │
    │ - confidence              │
    └───────────────────────────┘
        │
        └── (26 types: WORKS_FOR, KNOWS, etc.)

┌──────────────────┐
│  Data            │
│ - id (PK)        │
│ - entity_id (FK) │
│ - type           │
│ - value          │
│ - hash           │
└──────────────────┘

┌──────────────────┐
│  OrphanData      │
│ - id (PK)        │
│ - project_id (FK)│
│ - identifier     │
│ - status         │
│ - suggestions[]  │
└──────────────────┘

┌──────────────────┐
│  Suggestion      │
│ - id (PK)        │
│ - source_id      │
│ - target_id      │
│ - confidence     │
│ - type           │
│ - created_at     │
└──────────────────┘
```

### Request Processing Pipeline

```
1. Incoming Request
   │
   ▼
2. NGINX
   ├─► SSL/TLS termination
   ├─► Rate limiting
   ├─► Compression
   └─► Routing
        │
        ▼
3. FastAPI Middleware
   ├─► CORS handling
   ├─► Metrics collection
   ├─► Request logging
   └─► Error handling
        │
        ▼
4. Route Handler
   ├─► Parameter parsing
   ├─► Pydantic validation
   ├─► Authorization check
   └─► Call service layer
        │
        ▼
5. Service Layer
   ├─► Business logic
   ├─► Data transformation
   ├─► Cache operations
   └─► Call DAL
        │
        ▼
6. Data Access Layer
   ├─► Neo4j queries
   ├─► Redis cache
   └─► File operations
        │
        ▼
7. Response Building
   ├─► HATEOAS links
   ├─► Metadata
   └─► Serialization
        │
        ▼
8. Middleware Response
   ├─► Response logging
   ├─► Metrics update
   └─► Compression
        │
        ▼
9. NGINX Response
   ├─► Header handling
   └─► Send to client
```

---

## Database Schema

### Neo4j Node Types

```cypher
// Person entity
CREATE (p:Entity:Person {
  id: "ent_001",
  name: "John Doe",
  type: "PERSON",
  email: "john@example.com",
  phone: "+1234567890",
  project_id: "proj_123",
  created_at: datetime(),
  updated_at: datetime(),
  created_by: "analyst_001",
  tags: ["suspect", "high-priority"],
  confidence: 0.95
})

// Organization entity
CREATE (o:Entity:Organization {
  id: "ent_002",
  name: "Acme Corp",
  type: "ORGANIZATION",
  domain: "acme.com",
  founded_year: 2010,
  project_id: "proj_123"
})

// Platform entity
CREATE (plat:Platform {
  id: "platform_twitter",
  name: "Twitter",
  domain: "twitter.com",
  type: "SOCIAL_MEDIA",
  account_fields: [
    {name: "username", type: "text"},
    {name: "followers", type: "integer"}
  ]
})

// Account relationship
CREATE (p)-[:HAS_ACCOUNT_ON {
  username: "@johndoe",
  followers: 5000,
  created_at: datetime()
}]->(plat)

// Relationship
CREATE (p)-[:WORKS_FOR {
  title: "Senior Developer",
  start_date: date("2020-01-15"),
  confidence: 0.99
}]->(o)
```

### Indexes

```cypher
CREATE INDEX entity_type_idx FOR (e:Entity) ON (e.type);
CREATE INDEX entity_project_idx FOR (e:Entity) ON (e.project_id);
CREATE INDEX entity_name_idx FOR (e:Entity) ON (e.name);
CREATE INDEX data_identifier_idx FOR (d:Data) ON (d.identifier);
CREATE INDEX orphan_project_idx FOR (o:OrphanData) ON (o.project_id);
CREATE INDEX timestamp_idx FOR (e:Entity) ON (e.created_at);
```

### Constraints

```cypher
CREATE CONSTRAINT entity_id_unique FOR (e:Entity) REQUIRE e.id IS UNIQUE;
CREATE CONSTRAINT platform_id_unique FOR (p:Platform) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT data_id_unique FOR (d:Data) REQUIRE d.id IS UNIQUE;
```

---

## Authentication Flow

### JWT Token Flow (Production)

```
Client                      Server
  │                           │
  ├─ POST /auth/login ───────►│
  │  {username, password}     │
  │                           │ Verify credentials
  │                           │ Generate JWT token
  │◄─── {access_token} ───────┤
  │                           │
  ├─ GET /api/v1/projects ───►│
  │  Authorization: Bearer JWT│
  │                           │ Verify token signature
  │                           │ Check expiration
  │                           │ Validate claims
  │◄─── [projects] ───────────┤
  │                           │
  │ (Token expires in 24h)    │
  │                           │
  ├─ POST /auth/refresh ─────►│
  │  {current_token}          │
  │                           │ Validate current token
  │                           │ Issue new token
  │◄─── {new_token} ──────────┤
```

### MCP Protocol Flow

```
Claude API              Basset Hound
  │                        │
  ├─ List tools ──────────►│
  │                        │ Return 119 MCP tools
  │◄─ [tool definitions]───┤
  │                        │
  ├─ Call tool ──────────►│
  │ {tool_name, params}   │
  │                        │ Execute tool
  │                        │ Access database/API
  │◄─ {result} ───────────┤
  │                        │
  │ (Async execution)      │
  │                        │
  ├─ Get tool result ────►│
  │                        │ Return cached result
  │◄─ {data} ─────────────┤
```

---

## Integration Architecture

### External Service Integration

```
Basset Hound                 External Services
    │
    ├─► basset-verify (Port 8001)
    │   ├─ Email verification
    │   ├─ Phone verification
    │   └─ Crypto verification
    │
    ├─► basset-hound-browser (Port 8765)
    │   ├─ WebSocket bridge
    │   ├─ Chrome extension
    │   └─ Browser automation
    │
    ├─► cletus (Port 9000)
    │   ├─ News feed
    │   ├─ Intelligence aggregation
    │   └─ Document analysis
    │
    └─► Claude API (https://api.anthropic.com)
        ├─ MCP protocol
        └─ Tool execution
```

### Webhook Architecture

```
Event Occurrence
    │
    ▼
Generate Event
    │
    ├─► Store in database
    ├─► Publish to Redis pub/sub
    └─► Queue webhook delivery
        │
        ▼
    Get registered webhooks
        │
        ├─► Filter by event type
        ├─► Check active status
        └─► Retry logic (exponential backoff)
            │
            ▼
        POST to webhook URL
            │
            ├─► Include request signature
            ├─► Include timestamp
            └─► Timeout: 30 seconds
```

---

## Deployment Architecture

### Docker Compose Services

```
┌─────────────────────────────────────────────┐
│ Docker Compose Network: basset-hound        │
├─────────────────────────────────────────────┤
│                                             │
│  nginx (port 8080)                          │
│  ├─► basset_api:8000                        │
│  ├─► basset_api:8000 (scaled)               │
│  └─► prometheus:9090 (optional)             │
│                                             │
│  basset_api (FastAPI, 3+ instances)         │
│  ├─► neo4j:7687                             │
│  ├─► redis:6379                             │
│  └─► external services                      │
│                                             │
│  neo4j (port 7687)                          │
│  └─► /data volume                           │
│                                             │
│  redis (port 6379)                          │
│  └─► /data volume                           │
│                                             │
│  prometheus (port 9090, optional)           │
│  ├─► scrape basset_api:8000/metrics         │
│  └─► /data volume                           │
│                                             │
│  grafana (port 3000, optional)              │
│  └─► prometheus datasource                  │
│                                             │
└─────────────────────────────────────────────┘
```

### Network Architecture

```
Internet
  │
  └─► HTTPS (443)
      │
      └─► Nginx (Load Balancer)
          │
          ├─► basset_api:8000 (instance 1)
          ├─► basset_api:8000 (instance 2)
          └─► basset_api:8000 (instance 3)
              │
              ├─► Neo4j Cluster
              │   ├─ neo4j_1:7687 (primary)
              │   ├─ neo4j_2:7687 (replica)
              │   └─ neo4j_3:7687 (replica)
              │
              └─► Redis Cluster
                  ├─ redis_1:6379
                  ├─ redis_2:6379
                  └─ redis_3:6379
```

### Monitoring Stack

```
Basset API
    │
    ├─► Metrics (Prometheus format)
    │   │
    │   ▼
    │ Prometheus (port 9090)
    │   │
    │   ├─► Alert Rules
    │   └─► Time-series database
    │       │
    │       ▼
    │   Grafana (port 3000)
    │   ├─► Dashboards
    │   ├─► Alerts
    │   └─► Notifications
    │
    └─► Logs (JSON format)
        │
        ▼
    Filebeat (optional)
        │
        ▼
    Elasticsearch (optional)
        │
        ▼
    Kibana (optional)
```

---

## Performance Optimizations (Phase 8)

### Query Optimization Architecture

**Multi-Layer Query Strategy**:

```
Application Request
    │
    ▼
L1: In-Memory Cache (1-10s TTL, 1000 entries)
    │ (72% hit rate)
    ├─► MISS: Continue to L2
    └─► HIT: Return immediately (0.5ms)
    
    ▼
L2: Redis Cache (30-60s TTL, unlimited)
    │ (55% hit rate for misses)
    ├─► MISS: Continue to L3
    └─► HIT: Return via network (5-10ms)

    ▼
L3: Database Indexes (Neo4j)
    │ (99% hit rate via indexes)
    ├─► MISS: Full table scan
    └─► HIT: Index lookup (10-50ms)

    ▼
Neo4j Database
    └─► Execute optimized Cypher
        ├─► UNWIND batch operations
        ├─► MATCH with index push-down
        ├─► COLLECT for aggregation
        └─► LIMIT push-down pagination
```

**Result**: 5-10x latency reduction through cascading caches

### Database Optimization Features

**1. N+1 Query Elimination**
- UNWIND batch operations for bulk creates/updates
- COLLECT aggregation instead of Python loops
- Cypher path queries instead of relationship hops
- Result: 90% reduction in query count

**2. Comprehensive Indexing Strategy**
```
Indexes Created:
├─ Person.email (search)
├─ Person.phone (search)
├─ Person.created_at (sorting)
├─ Relationship.type (filtering)
├─ Project.safe_name (routing)
├─ FieldValue(section_id, field_id) (composite)
├─ File relationship properties (composite)
└─ OrphanData(type, linked) (composite)

Coverage: 95% of hot query paths indexed
Performance: 5-10x for indexed queries
```

**3. Redis-Based Result Caching**
```
Cache Configuration:
├─ L1 (In-Memory): 5-10 minute TTL, 1000 items
├─ L2 (Redis): 30-60 second TTL, unlimited
├─ Tag-based invalidation: Cascade on entity change
└─ Warm cache on startup: Common queries pre-cached

Endpoints Cached (20+):
├─ List: projects, people, entities (70% hit rate)
├─ Search: full-text, autocomplete (50-70% hit rate)
├─ Graph: paths, neighbors, subgraph (60% hit rate)
└─ Reports: PDF, exports (40% hit rate)
```

### Search Optimization Features

**Full-Text Search**
```
Capabilities:
├─ Index: Entity names, emails, phones, tags, descriptions
├─ Query: Boolean operators, phrase search, wildcards
├─ Performance: <200ms p99 with caching
└─ Relevance: Scoring by term frequency, boost factors

Faceted Search:
├─ Entity Type: Person, Org, Location, Event, Document
├─ Tags: Dynamic, entity-tagged
├─ Creation Date: Last 24h, 7d, 30d, 90d, custom
├─ Source: LinkedIn, Twitter, Email, File, Manual
└─ Status: Active, Archived, Flagged, Unverified
```

**Autocomplete Performance**
```
Features:
├─ Real-time suggestions (<100ms)
├─ Ranking by popularity (most linked first)
├─ Caching (70% hit rate)
├─ Fuzzy matching with "did you mean"
└─ Performance: <100ms 99th percentile
```

### Frontend Performance Optimizations

**Bundle Size Reduction (42%)**
```
Code Splitting:
├─ main.js: 150KB (was 280KB) - Core dashboard
├─ vendor.js: 140KB (was 220KB) - Dependencies
├─ graph.js: 120KB (lazy loaded) - Graph visualization
├─ suggestions.js: 80KB (lazy loaded) - Suggestions panel
└─ search.js: 60KB (lazy loaded) - Advanced search

Lazy Loading:
├─ Graph visualization (saves 150KB)
├─ Smart suggestions (saves 100KB)
├─ Advanced search (saves 80KB)
└─ Load on first access

Result:
├─ FCP: 2.8s → 1.9s (32% improvement)
├─ TTI: 4.2s → 2.8s (33% improvement)
└─ Lighthouse: 78 → 92 (+18%)
```

### Advanced Feature Architectures

**ML Analytics Service**
```
Components:
├─ Feature Engineering (name, email, phone similarity)
├─ Models:
│  ├─ Duplicate Detection (sklearn, 92% accuracy)
│  ├─ Link Prediction (Node2Vec embeddings, 76% recall)
│  ├─ Community Detection (Louvain, modularity 0.65+)
│  └─ Anomaly Detection (Isolation Forest)
├─ Inference: <100ms for most operations
└─ Feature Flag: ENABLE_ML_ANALYTICS=true/false
```

**Real-Time Collaboration**
```
Architecture:
├─ WebSocket Protocol: Binary messages, <100ms latency
├─ Broadcasting: Redis pub/sub to all clients
├─ Conflict Resolution: Last-write-wins + merge dialogs
├─ Activity Feed: Real-time updates, 5-min archival
├─ Presence: Active users, viewing entities
└─ Scalability: 500+ concurrent users
```

**Plugin System**
```
Architecture:
├─ Sandbox Isolation: iframe for untrusted plugins
├─ Plugin Interface: JSON schema validation
├─ API Access: Read-only to graph data
├─ Registry: Database-stored plugin metadata
├─ Built-in Plugins (4):
│  ├─ Sankey: Entity flow visualization
│  ├─ Timeline: Temporal relationships
│  ├─ Heatmap: Activity frequency
│  └─ Network Stats: Centrality analysis
└─ Marketplace: Upload, download, review system
```

**Multi-Format Export**
```
Supported Formats:
├─ GraphML: Graph interchange (Gephi, Cytoscape)
├─ CSV/JSON: Tabular + structured
├─ GeoJSON: Geographic mapping
├─ PDF/DOCX/HTML/Markdown: Reports
└─ Database Dump: Full backup (encrypted)

Features:
├─ Filtering: By type, tag, date range
├─ Pagination: 1000 rows per file
├─ Batch Export: Multiple formats simultaneously
└─ Performance: <50s for 1M entities
```

---

## Performance Characteristics

### Response Time Targets

| Operation | Target | Factors |
|-----------|--------|---------|
| Entity lookup | <100ms | Neo4j cache, index |
| Search | <500ms | Query complexity, result size |
| Report generation | <5s | Entity count, sections |
| Graph visualization | <1s | Node/edge count |
| Suggestion generation | <2s | Algorithm complexity |
| WebSocket broadcast | <50ms | Redis pub/sub, clients |

### Scalability Limits

| Metric | Limit | Notes |
|--------|-------|-------|
| Entities per project | 10M+ | Neo4j scalability |
| Relationships | 100M+ | Depends on Neo4j memory |
| Concurrent API connections | 1000+ | Uvicorn workers |
| Concurrent WebSocket connections | 10000+ | Redis pub/sub |
| Requests per second | 1000+ | With caching |
| Projects | 1000+ | Isolation via project_id |

---

**Last Updated**: 2026-05-07  
**Version**: 2.0.0
