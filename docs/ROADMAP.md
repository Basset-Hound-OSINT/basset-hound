# Basset Hound Development Roadmap

## Project Vision & Philosophy

### What Basset Hound IS

**Basset Hound is a lightweight, API-first entity relationship engine** inspired by [BloodHound](https://github.com/BloodHoundAD/BloodHound), designed for:

1. **OSINT Investigations** - Tracking people, organizations, and their connections
2. **Integration Backend** - API/MCP server for LLMs, AI agents, and other tools
3. **Graph-Based Analysis** - Neo4j-powered relationship queries and pattern discovery
4. **Data Ingestion** - Import from various OSINT tools and formats

### Design Principles

| Principle | Description |
|-----------|-------------|
| **Lightweight** | Core features only - no enterprise bloat |
| **Integration-First** | Built to be consumed by other applications via API/MCP |
| **Local-First** | Runs on a laptop, scales with hardware |
| **Graph-Powered** | Neo4j for relationship traversal and pattern discovery |
| **Simple but Powerful** | Few features done well > many features done poorly |

### What Basset Hound is NOT

- ❌ A full-featured enterprise reporting platform
- ❌ A multi-user collaborative application
- ❌ A replacement for specialized OSINT tools
- ❌ A UI-first application (API-first, UI is secondary)

### Core Value Proposition

> **"Store now, connect later"** - Capture data fragments immediately, discover relationships as your investigation progresses.

Key differentiators from traditional databases:
- **Orphan data workflow** - Store identifiers before knowing who they belong to
- **Relationships are first-class** - Not just foreign keys, but typed, weighted, and queryable
- **Schema is runtime-configurable** via YAML
- **Built for AI integration** - API and MCP server for LLM consumption

---

## Current Architecture Summary

### Technology Stack (As-Is)

| Component | Technology | Purpose |
|-----------|------------|---------|
| Backend | **Flask 3.1.0** | REST API and server-rendered templates |
| Database | **Neo4j 5.28.1** | Graph storage for entities and relationships |
| Frontend | **Vanilla JS + Bootstrap** | Configuration-driven UI |
| Schema | **YAML** | Dynamic entity type definitions |
| Files | **Filesystem** | Attached files and reports |

### Current Capabilities

- **Entity Management**: CRUD for people/entities with dynamic fields
- **Relationship Tracking**: Bidirectional tagging with transitive relationship detection
- **File Management**: Upload, organize, and serve files per entity
- **Report Generation**: Markdown reports with entity cross-references
- **Multi-Project**: Isolated workspaces for different investigations
- **Configuration-Driven**: Schema changes without code modifications

### Current Limitations

1. **No Authentication** - All endpoints publicly accessible
2. **Flask (Sync)** - Not optimized for high-concurrency workloads
3. **Limited Entity Types** - Currently focused on "Person" entities
4. **No API Documentation** - Missing OpenAPI/Swagger specs
5. **Limited Social Networks** - Only LinkedIn and Twitter in schema
6. **No MCP Integration** - Cannot be used as an AI tool server
7. **Frontend Tightly Coupled** - API designed for web UI, not external clients

---

## Strategic Decision: Flask to FastAPI Migration

### Recommendation: **YES, Migrate to FastAPI**

**Rationale:**

| Factor | Flask (Current) | FastAPI (Proposed) |
|--------|-----------------|-------------------|
| **Async Support** | Limited (WSGI) | Native (ASGI) |
| **API Documentation** | Manual | Auto-generated OpenAPI |
| **Type Safety** | None | Pydantic models |
| **Performance** | Good | Excellent (3-5x faster) |
| **MCP Compatibility** | Manual | FastMCP native |
| **Modern Standards** | Legacy | Current best practices |
| **Learning Curve** | Already learned | Similar to Flask |

### Migration Strategy

**Phase 1: Parallel Development**
- Create new `api/` directory with FastAPI routes
- Keep Flask running for UI during transition
- Use FastAPI for new API-only endpoints

**Phase 2: Route Migration**
- Migrate blueprints to FastAPI routers
- Convert Flask routes one at a time
- Maintain backward compatibility

**Phase 3: UI Modernization** (Optional)
- Keep Jinja2 templates OR migrate to SPA
- FastAPI can still serve templates via Jinja2

---

## Enhanced Data Configuration Schema

### `data_config.yaml` Structure

The configuration schema supports dynamic entity types with flexible field definitions. Here's a condensed example showing all supported field types:

```yaml
# data_config.yaml - Sample showing all field types
version: "2.0"
entity_type: Person

sections:
  - id: sample_section
    name: Sample Section (All Field Types)
    icon: fa-cog
    fields:
      # Simple field types
      - id: name
        type: string
        label: Name
        searchable: true
        identifier: true      # Can be used for entity linking

      - id: email
        type: email
        multiple: true
        label: Email Addresses

      - id: website
        type: url
        label: Website

      - id: birth_date
        type: date
        label: Date of Birth

      - id: age
        type: number
        label: Age

      - id: phone
        type: phone
        multiple: true

      - id: notes
        type: comment         # Textarea
        label: Notes

      - id: status
        type: select
        options: ["Active", "Inactive", "Unknown"]

      - id: avatar
        type: file
        accept: image/*

      - id: ip
        type: ip_address
        pattern: "^(?:[0-9]{1,3}\\.){3}[0-9]{1,3}$"

      - id: secret
        type: password
        encrypted: true

      # Component field (nested structure)
      - id: address
        type: component
        multiple: true
        label: Addresses
        components:
          - id: street
            type: string
          - id: city
            type: string
          - id: country
            type: string
          - id: type
            type: select
            options: ["Home", "Work", "Other"]

# Field type definitions
field_types:
  string:    { html_input: text }
  email:     { html_input: email, pattern: "..." }
  url:       { html_input: url }
  date:      { html_input: date }
  number:    { html_input: number }
  phone:     { html_input: tel }
  password:  { html_input: password, encrypted: true }
  comment:   { html_input: textarea }
  file:      { html_input: file }
  select:    { html_input: select }
  ip_address: { html_input: text, pattern: "..." }
  component: { html_input: fieldset }
```

**Key Features:**
- `multiple: true` - Allow multiple values for a field
- `identifier: true` - Use for entity matching/linking
- `searchable: true` - Include in search indexing
- `sensitive: true` - Mark section as containing sensitive data
- `platform_url` - Template URL for social platforms

---

## Roadmap Phases

### Phase 1: Core Modernization (Foundation)

**Priority: CRITICAL**

#### 1.1 FastAPI Migration

| Task | Description | Effort |
|------|-------------|--------|
| Create FastAPI app structure | New `api/` directory with routers | Medium |
| Migrate Project endpoints | `/projects/*` routes | Low |
| Migrate Person endpoints | `/people/*` routes with Pydantic models | Medium |
| Migrate File endpoints | `/files/*` with async file handling | Medium |
| Migrate Report endpoints | `/reports/*` routes | Low |
| Add OpenAPI documentation | Auto-generated Swagger UI | Free |
| Add authentication | JWT-based auth with API keys | Medium |

**Deliverables:**
- FastAPI app running on port 8000
- OpenAPI spec at `/docs`
- All existing Flask functionality preserved
- Authentication system operational

#### 1.2 Enhanced Data Config

| Task | Description | Effort |
|------|-------------|--------|
| Implement comprehensive schema | Full social network coverage | Medium |
| Add schema versioning | `version` field with migration support | Low |
| Add field validation rules | `pattern`, `required`, `min/max` | Medium |
| Add `identifier` field support | Mark fields as unique identifiers | Low |
| Add `searchable` field support | Index fields for full-text search | Medium |

#### 1.3 Database Enhancements

| Task | Description | Effort |
|------|-------------|--------|
| Add full-text search | Neo4j full-text indexes | Medium |
| Optimize queries | Query profiling and index tuning | Medium |
| Add relationship types | Named relationship categories | Medium |
| Connection pooling | Async Neo4j driver | Low |

---

### Phase 2: MCP Server Integration

**Priority: HIGH**

#### 2.1 FastMCP Server

| Task | Description | Effort |
|------|-------------|--------|
| Create MCP server structure | FastMCP setup in `mcp/` directory | Low |
| Implement entity tools | `create_entity`, `get_entity`, `update_entity`, `delete_entity` | Medium |
| Implement relationship tools | `link_entities`, `unlink_entities`, `get_related` | Medium |
| Implement search tools | `search_entities`, `search_by_identifier` | Medium |
| Implement report tools | `generate_report`, `get_reports` | Low |
| Add configuration tools | `get_schema`, `validate_entity` | Low |

**MCP Tool Definitions:**

```python
# Example MCP tool structure
@mcp.tool()
async def create_entity(
    project_id: str,
    entity_type: str,  # Future: support multiple types
    profile: dict,
    tags: list[str] = []
) -> dict:
    """Create a new entity in Basset Hound."""
    pass

@mcp.tool()
async def link_entities(
    project_id: str,
    source_id: str,
    target_id: str,
    relationship_type: str = "RELATED_TO",
    properties: dict = {}
) -> dict:
    """Create a relationship between two entities."""
    pass

@mcp.tool()
async def search_by_identifier(
    project_id: str,
    identifier_type: str,  # email, username, ip_address, etc.
    identifier_value: str
) -> list[dict]:
    """Find entities by a specific identifier value."""
    pass
```

#### 2.2 MCP Resource Providers

| Task | Description | Effort |
|------|-------------|--------|
| Entity list resource | List all entities in project | Low |
| Schema resource | Provide current config schema | Low |
| Relationship graph resource | Provide entity relationship data | Medium |

---

### Phase 3: Advanced Relationship Features

**Priority: MEDIUM**

#### 3.1 Relationship Types

| Task | Description | Effort |
|------|-------------|--------|
| Named relationships | "WORKS_WITH", "KNOWS", "FAMILY", etc. | Medium |
| Relationship properties | Confidence, source, timestamp | Low |
| Directional relationships | A -> B vs A <-> B | Low |
| Relationship strength | Weighted connections | Low |

#### 3.2 Graph Analysis

| Task | Description | Effort |
|------|-------------|--------|
| Path finding | Shortest path between entities | Medium |
| Cluster detection | Find groups of related entities | High |
| Centrality analysis | Identify most connected entities | Medium |
| Timeline analysis | Relationship changes over time | High |

#### 3.3 Auto-Linking

| Task | Description | Effort |
|------|-------------|--------|
| Identifier matching | Auto-link entities with same email/username | Medium |
| Fuzzy matching | Similar names, typo tolerance | High |
| Cross-project linking | Link entities across projects | Medium |

---

### Phase 4: Performance & Scalability

**Priority: MEDIUM**

#### 4.1 Caching Layer

| Task | Description | Effort |
|------|-------------|--------|
| Redis integration | Cache frequently accessed entities | Medium |
| Query result caching | Cache complex graph queries | Medium |
| Invalidation strategy | Smart cache invalidation | Medium |

#### 4.2 Async Operations

| Task | Description | Effort |
|------|-------------|--------|
| Background jobs | Celery/ARQ for long-running tasks | Medium |
| Bulk import | Async large dataset ingestion | Medium |
| Report generation | Background report creation | Low |

#### 4.3 Horizontal Scaling

| Task | Description | Effort |
|------|-------------|--------|
| Stateless API | Remove global state | Medium |
| Load balancer support | Multiple API instances | Low |
| Neo4j clustering | Multi-node Neo4j setup | High |

---

### Phase 5: Extended Entity Types

**Priority: LOW (Future)**

#### 5.1 Multi-Entity Support

| Task | Description | Effort |
|------|-------------|--------|
| Entity type definitions | Person, Organization, Device, Location | High |
| Type-specific schemas | Different fields per type | Medium |
| Cross-type relationships | Person -> Organization links | Medium |

#### 5.2 Additional Entity Types

- **Organization**: Companies, groups, agencies
- **Location**: Addresses, venues, regions
- **Device**: Phones, computers, IoT
- **Event**: Incidents, meetings, transactions
- **Document**: Files, reports, evidence

---

## Non-OSINT Use Cases

### Basset Hound as Generic Entity Manager

The architecture supports many domains beyond OSINT:

| Use Case | Entity Types | Relationships |
|----------|-------------|---------------|
| **CRM** | Customers, Companies, Deals | Customer -> Company, Deal -> Customer |
| **Research** | Authors, Papers, Citations | Paper -> Author, Paper -> Paper (citation) |
| **Genealogy** | People, Locations, Events | Parent -> Child, Born at -> Location |
| **Inventory** | Items, Locations, Vendors | Item -> Location, Item -> Vendor |
| **Network Mapping** | Devices, Subnets, Services | Device -> Subnet, Device -> Service |
| **Knowledge Graph** | Concepts, Sources, Facts | Fact -> Concept, Fact -> Source |

### MCP Integration Benefits

With an MCP server, Basset Hound becomes accessible to:
- **Claude Desktop** - AI assistant with entity management
- **Custom AI Agents** - OSINT automation, research assistants
- **Third-party Tools** - Any MCP-compatible application
- **Automation Scripts** - Programmatic entity management

---

## File Structure After Migration

```
basset-hound/
├── api/                          # FastAPI application
│   ├── __init__.py
│   ├── main.py                   # FastAPI app entry
│   ├── config.py                 # Settings and configuration
│   ├── dependencies.py           # Dependency injection
│   ├── routers/
│   │   ├── projects.py
│   │   ├── entities.py
│   │   ├── relationships.py
│   │   ├── files.py
│   │   └── reports.py
│   ├── models/
│   │   ├── project.py            # Pydantic models
│   │   ├── entity.py
│   │   ├── relationship.py
│   │   └── file.py
│   ├── services/
│   │   ├── neo4j_service.py      # Async Neo4j handler
│   │   ├── file_service.py
│   │   └── search_service.py
│   └── auth/
│       ├── jwt.py
│       └── api_key.py
│
├── mcp/                          # MCP Server
│   ├── __init__.py
│   ├── server.py                 # FastMCP server
│   ├── tools/
│   │   ├── entities.py
│   │   ├── relationships.py
│   │   └── search.py
│   └── resources/
│       └── schema.py
│
├── web/                          # Flask UI (legacy, optional)
│   ├── app.py
│   ├── templates/
│   └── static/
│
├── data_config.yaml              # Enhanced schema
├── docker-compose.yml
├── pyproject.toml                # Modern Python packaging
└── docs/
    └── ROADMAP.md
```

---

## Success Metrics

| Metric | Target |
|--------|--------|
| API Response Time | < 100ms for simple queries |
| Concurrent Users | 100+ simultaneous connections |
| Entity Capacity | 100,000+ entities per project |
| MCP Tool Latency | < 500ms for tool execution |
| Search Performance | < 1s for full-text queries |
| Uptime | 99.9% availability |

---

## Conclusion

Basset Hound has a solid foundation for entity relationship management. The proposed roadmap transforms it from an OSINT-focused Flask application into a:

1. **Modern FastAPI service** with proper async support
2. **Comprehensive entity manager** supporting any domain
3. **MCP-enabled tool** for AI agent integration
4. **Scalable platform** for enterprise use cases

The key insight is that **entity relationship management is the core value**, not specifically OSINT. By abstracting the schema and adding MCP support, Basset Hound can serve any use case requiring structured entity data with complex relationships.

---

*Generated: 2025-12-27*
*Version: 1.0*

---

## Implementation Status (Updated: 2026-01-09)

### Phase 1: Core Modernization - ✅ COMPLETED

| Task | Status | Notes |
|------|--------|-------|
| Create FastAPI app structure | ✅ Done | `api/` directory with full structure |
| Migrate Project endpoints | ✅ Done | `api/routers/projects.py` |
| Migrate Person endpoints | ✅ Done | `api/routers/entities.py` |
| Migrate File endpoints | ✅ Done | `api/routers/files.py` |
| Migrate Report endpoints | ✅ Done | `api/routers/reports.py` |
| Add OpenAPI documentation | ✅ Done | Auto-generated at `/docs` |
| Add authentication | ✅ Done | JWT + API key in `api/auth/` |
| Implement comprehensive schema | ✅ Done | `data_config_enhanced.yaml` with 50+ networks |
| Async Neo4j service | ✅ Done | `api/services/neo4j_service.py` |
| Pydantic v2 models | ✅ Done | `api/models/` directory |

### Phase 2: MCP Server Integration - ✅ COMPLETED

| Task | Status | Notes |
|------|--------|-------|
| Create MCP server structure | ✅ Done | `mcp/server.py` using FastMCP |
| Implement entity tools | ✅ Done | create, get, update, delete, list |
| Implement relationship tools | ✅ Done | link, unlink, get_related |
| Implement search tools | ✅ Done | search_entities, search_by_identifier |
| Implement report tools | ✅ Done | create_report, get_reports |
| Implement project tools | ✅ Done | create, list, get projects |

### Files Created

```
# Root level
main.py                       # Unified entry point (FastAPI + MCP)
.env                          # Development configuration
data_config.yaml              # Enhanced schema (50+ networks)
data_config_old.yaml          # Original basic schema (backup)

api/
├── __init__.py
├── config.py                  # Pydantic Settings
├── dependencies.py            # DI system
├── main.py                   # FastAPI entry point
├── auth/
│   ├── __init__.py
│   ├── jwt.py                # JWT utilities
│   ├── api_key.py            # API key management
│   ├── dependencies.py       # Auth dependencies
│   └── routes.py             # Auth endpoints
├── models/
│   ├── __init__.py
│   ├── project.py
│   ├── entity.py
│   ├── relationship.py
│   ├── file.py
│   ├── report.py
│   ├── config.py
│   └── auth.py
├── routers/
│   ├── __init__.py
│   ├── projects.py
│   ├── entities.py
│   ├── relationships.py
│   ├── files.py
│   ├── reports.py
│   └── config.py
└── services/
    ├── __init__.py
    └── neo4j_service.py      # Async Neo4j

mcp/
├── __init__.py
└── server.py                 # FastMCP with 15 tools

tests/
├── __init__.py
├── conftest.py               # Pytest fixtures
├── test_models.py
├── test_api_projects.py
├── test_api_entities.py
└── test_mcp_server.py

docs/findings/
├── 01-FASTAPI-MIGRATION.md
├── 02-MCP-SERVER.md
└── 03-ENHANCED-CONFIG.md
```

### Dependencies Added (requirements.txt)

```
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
pydantic>=2.10.0
pydantic-settings>=2.6.0
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
python-multipart>=0.0.12
mcp>=1.0.0
aiofiles>=24.1.0
httpx>=0.27.0
pytest>=8.3.0
pytest-asyncio>=0.24.0
```

### Running the Applications

**Unified Entry Point (Recommended):**
```bash
# 1. Start Docker containers (Neo4j)
docker-compose up -d

# 2. Install dependencies (first time only)
pip install -r requirements.txt

# 3. Start Basset Hound (FastAPI + MCP Server)
python main.py
```

This starts both the FastAPI server (port 8000) and MCP server concurrently.

**Command Line Options:**
```bash
python main.py --help
python main.py --port 9000        # Custom port
python main.py --no-mcp           # FastAPI only
python main.py --mcp-only         # MCP server only
```

**Individual Components (Alternative):**
```bash
# FastAPI only
uvicorn api.main:app --reload
# Runs on http://localhost:8000
# Docs at http://localhost:8000/docs

# MCP Server only
python -m mcp.server

# Flask (Legacy - deprecated)
python app.py
# Runs on http://localhost:5000
```

### Phase 2.5: Intelligent Data Processing - ✅ COMPLETED (2025-12-27)

| Task | Status | Notes |
|------|--------|-------|
| Cryptocurrency address detection | ✅ Done | Auto-detect 20+ crypto types from address format |
| Dynamic MCP schema introspection | ✅ Done | MCP tools dynamically reflect data_config.yaml |
| Crypto detection API endpoints | ✅ Done | `/utils/detect-crypto`, batch detection, validation |
| Unified crypto address field type | ✅ Done | Single field auto-detects coin type |
| Comprehensive crypto tests | ✅ Done | 85 pytest tests covering all cryptocurrencies |
| Schema validation in MCP | ✅ Done | `validate_profile_data` tool for entity validation |

#### Cryptocurrency Detection Features

- **Automatic coin detection** from pasted address (BTC, ETH, LTC, XRP, SOL, ADA, DOGE, XMR, TRX, etc.)
- **20+ cryptocurrencies supported** including all major coins and EVM chains
- **Confidence scores** indicating match certainty (0.0-1.0)
- **Explorer URLs** auto-generated for detected addresses
- **Batch detection** for processing multiple addresses at once
- **EVM chain hints** to specify which EVM network (ETH, BNB, MATIC, ARB, etc.)

#### Dynamic Schema Introspection

- **`get_schema()`** - Returns complete data_config.yaml structure
- **`get_sections()`** - Lists all sections with field summaries
- **`get_identifiers()`** - Finds all identifier fields for entity resolution
- **`get_field_info()`** - Detailed info for specific fields
- **`validate_profile_data()`** - Validates entity data against schema
- **`reload_schema()`** - Hot-reload schema changes without restart

#### Files Created

```
api/utils/
├── __init__.py
└── crypto_detector.py    # 20+ crypto detection patterns

api/routers/
└── utils.py              # Crypto detection API endpoints

tests/
└── test_crypto_detector.py  # 85 comprehensive tests

docs/findings/
├── 04-CRYPTO-DETECTION.md
└── 05-DYNAMIC-MCP-SCHEMA.md
```

### Phase 3: Advanced Relationship Features - ✅ COMPLETED (2025-12-27)

| Task | Status | Notes |
|------|--------|-------|
| Named relationship types | ✅ Done | 26 relationship types: WORKS_WITH, KNOWS, FAMILY, FRIEND, etc. |
| Relationship properties | ✅ Done | Confidence levels, source, notes, timestamps, verification |
| Directional relationships | ✅ Done | Support for asymmetric relationships (PARENT_OF ↔ CHILD_OF) |
| Bidirectional relationship creation | ✅ Done | Automatic inverse relationship for symmetric types |
| Path finding | ✅ Done | Shortest path and all-paths algorithms in Neo4j |
| Cluster detection | ✅ Done | Union-find based connected component analysis |
| Centrality analysis | ✅ Done | Degree centrality with incoming/outgoing counts |
| Neighborhood exploration | ✅ Done | N-hop ego network extraction |
| Auto-linking by identifier | ✅ Done | Email, phone, username matching with confidence scores |
| Entity merging | ✅ Done | Combine duplicate entities with profile merging |
| Comprehensive tests | ✅ Done | All 212 tests passing (74 Phase 3 tests + existing tests) |
| CORS configuration fix | ✅ Done | Fixed CORS configuration parsing in `api/config.py` |

#### Relationship Types Implemented

**Generic:** RELATED_TO, KNOWS
**Professional:** WORKS_WITH, BUSINESS_PARTNER, REPORTS_TO, MANAGES, COLLEAGUE, CLIENT, EMPLOYER, EMPLOYEE
**Family:** FAMILY, MARRIED_TO, PARENT_OF, CHILD_OF, SIBLING_OF, SPOUSE
**Social:** FRIEND, ACQUAINTANCE, NEIGHBOR
**Organizational:** MEMBER_OF, AFFILIATED_WITH
**Investigative:** ASSOCIATED_WITH, SUSPECTED_ASSOCIATE, ALIAS_OF
**Communication:** COMMUNICATES_WITH, CONTACTED

#### Graph Analysis Features

- **Shortest Path:** Find most direct connection between two entities
- **All Paths:** Discover all possible paths up to configurable depth
- **Degree Centrality:** Count total connections (in + out)
- **Normalized Centrality:** Ratio of connections vs. max possible
- **Most Connected:** Rank entities by connection count
- **Neighborhood:** Extract N-hop ego network with edges
- **Cluster Detection:** Find connected components/communities

#### Auto-Linking Features

- **Identifier Weights:** Email (3.0), Phone (2.5), Crypto (3.5), Social handles (2.0)
- **Duplicate Threshold:** Score ≥5.0 suggests same person
- **Link Threshold:** Score ≥2.0 suggests relationship
- **Project-Wide Scan:** Find all potential duplicates across entities
- **Entity Merge:** Combine profiles with primary taking precedence

#### Files Created

```
api/models/
└── relationship.py           # RelationshipType enum, Pydantic models

api/routers/
├── relationships.py          # Enhanced relationship endpoints
└── analysis.py               # Graph analysis API endpoints

api/services/
└── auto_linker.py            # AutoLinker service with merging

neo4j_handler.py              # Graph analysis methods added (lines 596-1475)

tests/
├── test_relationships.py     # 25 relationship model tests
├── test_graph_analysis.py    # 24 graph analysis tests
└── test_auto_linker.py       # 25 auto-linker tests
```

#### API Endpoints Added

**Relationship Endpoints:**
- `GET /projects/{id}/relationships/` - List all relationships
- `GET /projects/{id}/relationships/stats` - Relationship statistics
- `POST/PATCH/DELETE /entities/{id}/relationships/tag/{target_id}` - CRUD relationships
- `GET /entities/{id}/relationships/types` - Available relationship types

**Analysis Endpoints:**
- `GET /analysis/{project}/path/{id1}/{id2}` - Shortest path
- `GET /analysis/{project}/paths/{id1}/{id2}` - All paths
- `GET /analysis/{project}/centrality/{id}` - Entity centrality
- `GET /analysis/{project}/most-connected` - Top connected entities
- `GET /analysis/{project}/neighborhood/{id}` - N-hop neighborhood
- `GET /analysis/{project}/clusters` - Cluster detection

**Auto-Link Endpoints:**
- `GET /auto-link/duplicates` - Find project duplicates
- `GET /auto-link/entities/{id}/duplicates` - Entity duplicates
- `GET /auto-link/entities/{id}/suggested-links` - Link suggestions
- `POST /auto-link/scan` - Full project scan
- `POST /auto-link/merge` - Merge entities
- `GET /auto-link/identifier-fields` - List identifier fields

### Phase 4: Performance & Scalability - ✅ COMPLETED (2025-12-27)

| Task | Status | Notes |
|------|--------|-------|
| Redis cache integration | ✅ Done | Full Redis support with automatic fallback to in-memory cache |
| In-memory cache backend | ✅ Done | LRU eviction, TTL support, tag-based invalidation |
| Entity caching | ✅ Done | Project-aware entity caching with smart invalidation |
| Relationship caching | ✅ Done | Directional relationship caching (all/incoming/outgoing) |
| Query result caching | ✅ Done | Hash-based query caching with configurable TTL |
| Project-wide invalidation | ✅ Done | Cascade invalidation for all project data |
| Cache statistics | ✅ Done | Hit/miss tracking, hit rate, uptime metrics |
| Health check endpoint | ✅ Done | Cache health monitoring via API |
| Comprehensive tests | ✅ Done | 346 tests passing (including 66 cache service tests) |

#### Caching Features

- **Dual Backend Support**: Redis (primary) with in-memory fallback
- **TTL Configuration**: Separate TTLs for entities (600s), queries (60s), relationships (300s)
- **Tag-Based Invalidation**: Group cache entries by project, entity, or custom tags
- **LRU Eviction**: In-memory cache uses LRU with configurable max size
- **Cache Statistics**: Track hits, misses, sets, deletes, invalidations
- **Automatic Cleanup**: Background task for expired entry cleanup

#### Configuration Options

```python
# api/config.py - Cache Settings
cache_enabled: bool = True                    # Enable/disable caching
redis_url: Optional[str] = None               # Redis connection URL
cache_ttl: int = 300                          # Default TTL (5 min)
cache_entity_ttl: int = 600                   # Entity TTL (10 min)
cache_query_ttl: int = 60                     # Query TTL (1 min)
cache_relationship_ttl: int = 300             # Relationship TTL (5 min)
cache_max_memory_entries: int = 1000          # Max in-memory entries
cache_prefer_redis: bool = True               # Prefer Redis over memory
```

#### Files Created

```
api/services/
└── cache_service.py              # Full cache implementation (1391 lines)

tests/
└── test_cache_service.py         # 66 comprehensive cache tests
```

### Phase 5: Multi-Entity Type Support - ✅ COMPLETED (2025-12-27)

| Task | Status | Notes |
|------|--------|-------|
| EntityType enum | ✅ Done | 6 types: Person, Organization, Device, Location, Event, Document |
| EntityTypeConfig model | ✅ Done | Per-type configuration with sections, icons, colors |
| Cross-type relationships | ✅ Done | 17 relationship patterns between entity types |
| Entity type registry | ✅ Done | Singleton registry for type management |
| Default configurations | ✅ Done | Full config for all 6 entity types |
| Field mappings | ✅ Done | Cross-type field mapping support |
| Backwards compatibility | ✅ Done | Person remains default, existing data unaffected |
| Comprehensive tests | ✅ Done | 48 entity type tests passing |

#### Entity Types Implemented

| Type | Icon | Description | Sections |
|------|------|-------------|----------|
| **Person** | fa-user | Individuals (default) | 35 sections (existing) |
| **Organization** | fa-building | Companies, groups, agencies | org_identity, org_contact, org_structure |
| **Device** | fa-mobile-alt | Phones, computers, IoT | device_identity, device_technical, device_network |
| **Location** | fa-map-marker-alt | Addresses, venues, regions | location_identity, location_address, location_coordinates |
| **Event** | fa-calendar-alt | Incidents, meetings, transactions | event_identity, event_timing, event_participants |
| **Document** | fa-file-alt | Files, reports, evidence | document_identity, document_metadata, document_content |

#### Cross-Type Relationships

Person-Organization: EMPLOYED_BY, MEMBER_OF, FOUNDED, OWNS
Person-Device: OWNS_DEVICE, USES
Person-Location: LIVES_AT, WORKS_AT, VISITED
Person-Event: PARTICIPATED_IN, ORGANIZED
Person-Document: AUTHORED, MENTIONED_IN
Organization-Location: LOCATED_AT, OPERATES_IN
Organization-Organization: SUBSIDIARY_OF, PARTNER_WITH
Device-Location: LOCATED_AT
Event-Location: OCCURRED_AT

#### Files Created

```
api/models/
└── entity_types.py               # Entity type definitions (642 lines)

tests/
└── test_entity_types.py          # 48 entity type tests
```

### Phase 6: Cross-Project & Fuzzy Matching - ✅ COMPLETED (2025-12-27)

| Task | Status | Notes |
|------|--------|-------|
| Fix Pydantic deprecation warnings | ✅ Done | Migrated all models from `class Config` to `model_config = ConfigDict()` |
| Cross-project linking service | ✅ Done | Link entities across different projects |
| Cross-project API endpoints | ✅ Done | Full REST API for cross-project operations |
| Fuzzy matching service | ✅ Done | Multiple matching strategies with phonetic support |
| Fuzzy matching tests | ✅ Done | 52 comprehensive tests |
| Cross-project tests | ✅ Done | Service and API endpoint tests |
| All tests passing | ✅ Done | 439 tests passing, 0 warnings |

#### Cross-Project Linking Features

- **Link Types**: SAME_PERSON, RELATED, ALIAS, ASSOCIATE, FAMILY, ORGANIZATION
- **Confidence Scoring**: 0.0 to 1.0 confidence for each link
- **Bidirectional Links**: Links are stored as Neo4j relationships
- **Automatic Match Finding**: Uses identifier matching to find potential links
- **Metadata Support**: Custom metadata can be attached to links

**API Endpoints:**
- `POST /api/v1/cross-project/link` - Create a cross-project link
- `DELETE /api/v1/cross-project/link` - Remove a cross-project link
- `GET /api/v1/projects/{project_id}/entities/{entity_id}/cross-links` - Get entity's cross-project links
- `GET /api/v1/cross-project/find-matches/{project_id}/{entity_id}` - Find potential matches
- `GET /api/v1/projects/{project_id}/entities/{entity_id}/cross-links/all-linked` - Get all linked entities

#### Fuzzy Matching Features

- **Multiple Matching Strategies**:
  - Levenshtein distance
  - Jaro-Winkler similarity
  - Token set ratio (handles word reordering)
  - Token sort ratio
  - Partial ratio

- **Phonetic Matching**: Double Metaphone algorithm for sounds-alike matching
- **Name Normalization**: Removes accents, special characters, normalizes whitespace
- **Combined Similarity**: Weighted combination of multiple strategies
- **Configurable Thresholds**: Set minimum similarity for matches

**FuzzyMatcher Methods:**
- `normalize_name(name)` - Normalize for comparison
- `calculate_similarity(str1, str2, strategy)` - Get similarity score
- `find_similar_names(name, candidates, threshold)` - Find similar from list
- `match_entities_fuzzy(entities, field_path, threshold)` - Find similar entities
- `phonetic_match(str1, str2)` - Check if strings sound alike

#### Files Created

```
api/services/
├── cross_project_linker.py       # Cross-project linking service
└── fuzzy_matcher.py              # Fuzzy matching service with rapidfuzz

api/routers/
└── cross_project.py              # Cross-project API endpoints

tests/
├── test_cross_project_linker.py  # Cross-project linking tests
└── test_fuzzy_matcher.py         # Fuzzy matching tests (52 tests)
```

#### Dependencies Added

```
rapidfuzz>=3.0.0                  # High-performance fuzzy matching
```

### Phase 7: Timeline, Auto-Linker Fuzzy, & Bulk Ops - ✅ COMPLETED (2025-12-27)

| Task | Status | Notes |
|------|--------|-------|
| Timeline Analysis service | ✅ Done | Track entity/relationship changes over time |
| Timeline API endpoints | ✅ Done | Entity/project timelines, relationship history, activity analysis |
| Fuzzy matching + Auto-Linker integration | ✅ Done | Combined identifier + fuzzy matching for entity linking |
| Bulk operations service | ✅ Done | Batch import/export in JSON, CSV, JSONL formats |
| Bulk operations API | ✅ Done | Import, export, validate endpoints |
| Comprehensive tests | ✅ Done | 562 tests passing (123 new tests) |
| ROADMAP.md cleanup | ✅ Done | Trimmed data_config.yaml from 850+ to 88 lines |

#### Timeline Analysis Features

- **Event Types**: CREATED, UPDATED, DELETED, RELATIONSHIP_ADDED/REMOVED/UPDATED, MERGED, TAGGED, FILE_ADDED, etc.
- **Event Recording**: Auto-generated UUIDs, timestamps, optional actor tracking
- **Timeline Queries**: Filter by date range, event types, with pagination
- **Relationship History**: Track changes between specific entity pairs
- **Activity Analysis**: Events per day, most active periods, type distribution

**API Endpoints:**
- `GET /api/v1/projects/{project}/timeline` - Project-wide timeline
- `GET /api/v1/projects/{project}/entities/{id}/timeline` - Entity timeline
- `GET /api/v1/projects/{project}/relationships/{id1}/{id2}/history` - Relationship history
- `GET /api/v1/projects/{project}/entities/{id}/activity` - Activity stats
- `POST /api/v1/projects/{project}/entities/{id}/timeline` - Record event

#### Fuzzy Matching + Auto-Linker Integration

- **Combined Matching**: Identifier matching + fuzzy name matching
- **Configurable**: Enable/disable, threshold, fields to match
- **Match Details**: Shows which values matched and similarity scores
- **Strategies**: Levenshtein, Jaro-Winkler, token ratios, phonetic

**New Auto-Linker Endpoints:**
- `GET /api/v1/projects/{project}/auto-link/entities/{id}/fuzzy-matches` - Find fuzzy matches
- `GET /api/v1/projects/{project}/auto-link/fuzzy-config` - Get fuzzy config

#### Bulk Operations Features

- **Import Formats**: JSON (list of entities), CSV with field mapping
- **Export Formats**: JSON, CSV, JSONL (JSON Lines)
- **Validation**: Pre-import validation with detailed error reporting
- **Options**: Include relationships, filter by entity IDs, update vs skip existing

**API Endpoints:**
- `POST /api/v1/projects/{project}/bulk/import` - Import entities (JSON)
- `POST /api/v1/projects/{project}/bulk/import/csv` - Import from CSV
- `GET /api/v1/projects/{project}/bulk/export` - Export entities
- `POST /api/v1/projects/{project}/bulk/export/csv` - Export specific fields to CSV
- `POST /api/v1/projects/{project}/bulk/validate` - Validate before import

#### Files Created

```
api/services/
├── timeline_service.py           # Timeline tracking (EventType, TimelineEvent, TimelineService)
└── bulk_operations.py            # Bulk import/export (BulkImportResult, BulkExportOptions)

api/routers/
├── timeline.py                   # Timeline API endpoints
└── bulk.py                       # Bulk operations API endpoints

api/services/auto_linker.py       # Enhanced with fuzzy matching integration

tests/
├── test_timeline_service.py      # 44 timeline tests
├── test_auto_linker_fuzzy.py     # 32 fuzzy auto-linker tests
└── test_bulk_operations.py       # 47 bulk operations tests
```

### Phase 8: Crypto Ticker, Search & Reports - ✅ COMPLETED (2025-12-27)

| Task | Status | Notes |
|------|--------|-------|
| Crypto Ticker Display API | ✅ Done | Detect crypto addresses and provide metadata, icons, explorer links |
| Advanced Search Service | ✅ Done | Full-text search with fuzzy matching, highlighting, pagination |
| Data Export Reports | ✅ Done | Generate PDF/HTML/Markdown reports with templates |
| Comprehensive tests | ✅ Done | 737 tests passing (175 new tests) |

#### Crypto Ticker Display Features

- **30+ Cryptocurrencies**: BTC, ETH, LTC, BCH, DOGE, XMR, SOL, ADA, DOT, ATOM, and more
- **Address Type Detection**: P2PKH, P2SH, Bech32, Taproot, EVM, etc.
- **Block Explorer URLs**: Auto-generate links to blockchain explorers
- **FontAwesome Icons**: UI-ready icon classes for each currency
- **Batch Processing**: Look up multiple addresses in one request

**API Endpoints:**
- `GET /api/v1/crypto/ticker/{address}` - Single address lookup
- `POST /api/v1/crypto/ticker/batch` - Batch lookup (max 100)
- `GET /api/v1/crypto/currencies` - List supported currencies
- `GET /api/v1/crypto/explorer-url/{address}` - Generate explorer URL

#### Advanced Search Features

- **Full-Text Search**: Neo4j Lucene-based indexing
- **Fuzzy Matching**: Typo tolerance using existing FuzzyMatcher
- **Highlighting**: `**matched text**` snippets in results
- **Field-Specific**: Search only in specific fields
- **Multi-Project**: Search across all projects or scope to one
- **Pagination**: Limit and offset support

**API Endpoints:**
- `GET /api/v1/search` - Global search
- `GET /api/v1/projects/{project}/search` - Project-scoped search
- `GET /api/v1/search/fields` - Get searchable fields
- `POST /api/v1/projects/{project}/search/reindex` - Rebuild index

#### Report Export Features

- **Formats**: PDF (via WeasyPrint), HTML, Markdown
- **Templates**: default (modern), professional (formal), minimal (clean)
- **Content Options**: Include graph, timeline, statistics
- **Entity Reports**: Single entity or project summary
- **Custom Sections**: Define custom report sections

**API Endpoints:**
- `POST /api/v1/projects/{project}/export/report` - Custom report
- `GET /api/v1/projects/{project}/export/summary/{format}` - Project summary
- `GET /api/v1/projects/{project}/entities/{id}/export/{format}` - Entity report
- `GET /api/v1/export/templates` - List templates

#### Files Created

```
api/services/
├── crypto_ticker_service.py      # Crypto address metadata (30+ currencies)
├── search_service.py             # Full-text search with fuzzy
└── report_export_service.py      # PDF/HTML/MD report generation

api/routers/
├── crypto.py                     # Crypto ticker API endpoints
├── search.py                     # Search API endpoints
└── export.py                     # Report export endpoints

tests/
├── test_crypto_ticker_service.py # 63 crypto ticker tests
├── test_search_service.py        # 50+ search tests
└── test_report_export_service.py # 60 report export tests
```

#### Dependencies Added

```
markdown>=3.0.0                   # Markdown to HTML conversion
# weasyprint>=60.0                # Optional PDF generation
```

### Phase 9: Real-Time & Automation - ✅ COMPLETED (2025-12-27)

| Task | Status | Notes |
|------|--------|-------|
| Report Scheduling service | ✅ Done | ONCE, HOURLY, DAILY, WEEKLY, MONTHLY frequencies + cron |
| Custom Report Templates | ✅ Done | 5 template types with Jinja2 support, import/export |
| Search Analytics | ✅ Done | Query tracking, zero-result detection, suggestions |
| WebSocket Notifications | ✅ Done | Real-time entity/relationship/report notifications |
| Comprehensive tests | ✅ Done | 302 new tests (1039 total) |

#### Report Scheduling Features

- **Frequencies**: ONCE, HOURLY, DAILY, WEEKLY, MONTHLY
- **Cron Support**: Custom cron expressions via croniter
- **Lifecycle**: Create, update, delete, enable, disable schedules
- **Execution**: Manual trigger or automatic via due detection
- **Timezone Awareness**: UTC-based scheduling

**API Endpoints:**
- `POST /api/v1/projects/{project}/schedules` - Create schedule
- `GET /api/v1/projects/{project}/schedules` - List schedules
- `PATCH /api/v1/schedules/{id}` - Update schedule
- `DELETE /api/v1/schedules/{id}` - Delete schedule
- `POST /api/v1/schedules/{id}/run` - Trigger immediate run

#### Custom Template Features

- **Template Types**: ENTITY_REPORT, PROJECT_SUMMARY, RELATIONSHIP_GRAPH, TIMELINE, CUSTOM
- **Jinja2 Syntax**: Full template language with validation
- **Variable Types**: STRING, LIST, DICT, NUMBER, BOOLEAN
- **Default Templates**: Pre-loaded for each type
- **Import/Export**: Share templates between instances

**API Endpoints:**
- `POST /api/v1/templates` - Create template
- `GET /api/v1/templates` - List templates
- `POST /api/v1/templates/{id}/render` - Render with context
- `POST /api/v1/templates/validate` - Validate syntax
- `POST /api/v1/templates/{id}/preview` - Preview with sample data

#### Search Analytics Features

- **Event Recording**: Query, results, response time, fields, filters
- **Aggregations**: Top queries, zero-result queries, slow queries
- **Time Analysis**: Searches by day/hour/week
- **Suggestions**: Related queries, query improvements
- **Export**: JSON and CSV formats

**API Endpoints:**
- `POST /api/v1/analytics/search` - Record search event
- `GET /api/v1/analytics/summary` - Analytics summary
- `GET /api/v1/analytics/top-queries` - Popular queries
- `GET /api/v1/analytics/zero-results` - Failed queries
- `GET /api/v1/analytics/export` - Export data

#### WebSocket Notification Features

- **Connection Management**: Connect, disconnect, reconnect with ID
- **Subscriptions**: Subscribe to project updates
- **Message Types**: Entity, relationship, search, report, bulk import
- **Heartbeat**: Ping/pong for connection health

**Endpoints:**
- `WS /api/v1/ws` - WebSocket connection
- `GET /api/v1/ws/stats` - Connection statistics

#### Files Created

```
api/services/
├── report_scheduler.py        # Report scheduling (62 tests)
├── template_service.py        # Custom templates (55 tests)
├── search_analytics.py        # Search analytics (60 tests)
└── websocket_service.py       # WebSocket notifications (125 tests)

api/routers/
├── schedule.py               # Scheduling endpoints
├── analytics.py              # Analytics endpoints
├── templates.py              # Template endpoints
└── websocket.py              # WebSocket endpoints
```

### Phase 10: Background Processing & Advanced Features - ✅ COMPLETED (2025-12-27)

| Task | Status | Notes |
|------|--------|-------|
| Background Job Runner | ✅ Done | ARQ-compatible async job execution with retry logic |
| Report Storage with history | ✅ Done | Version control, diffing, deduplication, export/import |
| Template Marketplace | ✅ Done | Publish, search, download, rate/review templates |
| ML Analytics | ✅ Done | Query suggestions, pattern detection, entity insights |
| Comprehensive tests | ✅ Done | 542 new tests (1581 total passing) |

#### Background Job Runner Features

- **Job Types**: REPORT, EXPORT, BULK_IMPORT, CUSTOM
- **Priority Levels**: CRITICAL, HIGH, NORMAL, LOW
- **Status Tracking**: PENDING, RUNNING, COMPLETED, FAILED, CANCELLED
- **Retry Logic**: Configurable max retries with exponential backoff
- **Worker Lifecycle**: Start/stop worker, worker status, heartbeat
- **Job Statistics**: Success rate, average duration, execution metrics

**API Endpoints:**
- `POST /api/v1/jobs` - Enqueue job
- `GET /api/v1/jobs` - List jobs with filtering
- `GET /api/v1/jobs/{id}` - Get job details
- `DELETE /api/v1/jobs/{id}` - Cancel job
- `GET /api/v1/jobs/stats` - Get statistics
- `POST /api/v1/jobs/worker/start` - Start worker
- `POST /api/v1/jobs/worker/stop` - Stop worker

#### Report Storage Features

- **Version History**: Multiple versions per report with sequential numbering
- **Content Deduplication**: Context hash to detect duplicate content
- **Version Comparison**: Unified diff between any two versions
- **Cleanup**: Remove old versions, keep most recent N
- **Export/Import**: Full backup and restore with all versions

**API Endpoints:**
- `POST /api/v1/reports` - Store report
- `GET /api/v1/reports/{id}/versions` - List versions
- `GET /api/v1/reports/{id}/diff` - Compare versions
- `POST /api/v1/reports/{id}/cleanup` - Cleanup old versions
- `GET /api/v1/reports/{id}/export` - Export report

#### Template Marketplace Features

- **Publishing**: Share templates with descriptions, tags, preview images
- **Searching**: Filter by query, type, tags, author; sort by downloads/rating
- **Downloading**: Import templates to local library with one click
- **Ratings & Reviews**: 1-5 stars with comments, update existing reviews
- **Statistics**: Total templates, downloads, authors, average rating

**API Endpoints:**
- `POST /api/v1/marketplace/templates` - Publish template
- `GET /api/v1/marketplace/templates` - Search templates
- `POST /api/v1/marketplace/templates/{id}/download` - Download template
- `POST /api/v1/marketplace/templates/{id}/reviews` - Add review
- `GET /api/v1/marketplace/popular` - Popular templates
- `GET /api/v1/marketplace/top-rated` - Top rated templates

#### ML Analytics Features

- **Query Suggestions**: Auto-complete based on history, patterns, semantic similarity
- **Pattern Detection**: Trending, common, declining, entity-type patterns
- **Entity Insights**: Related entities, data quality issues, search frequency
- **Query Similarity**: TF-IDF + Jaccard + Edit distance combination
- **Query Clustering**: Group similar queries using greedy clustering
- **Zero-Result Prediction**: Predict likelihood of no results

**ML Techniques Used:**
- TF-IDF vectorization for semantic similarity
- N-gram analysis (bigrams, trigrams) for pattern detection
- Levenshtein distance for edit-based similarity
- Frequency analysis for trend detection

**API Endpoints:**
- `POST /api/v1/ml/record-query` - Record query for learning
- `GET /api/v1/ml/suggest` - Get query suggestions
- `GET /api/v1/ml/patterns` - Detect search patterns
- `GET /api/v1/ml/entity-insights/{id}` - Get entity insights
- `GET /api/v1/ml/predict-zero-results` - Predict zero results

#### Files Created

```
api/services/
├── job_runner.py           # Background job execution (1042 lines)
├── report_storage.py       # Report versioning (682 lines)
├── marketplace_service.py  # Template marketplace (873 lines)
└── ml_analytics.py         # ML-powered suggestions (1165 lines)

api/routers/
├── jobs.py                 # Job runner endpoints
├── report_storage.py       # Report storage endpoints
├── marketplace.py          # Marketplace endpoints
└── ml_analytics.py         # ML analytics endpoints

tests/
├── test_job_runner.py
├── test_report_storage.py
├── test_marketplace_service.py
└── test_ml_analytics.py
```

### Comprehensive Code Review Results (2025-12-27)

**Test Results:** 1,581 passed, 2 skipped in 16.02 seconds

#### What's Working Well
- All Phase 1-10 features fully functional and tested
- 150+ API endpoints across 26 routers
- Comprehensive Pydantic models with validation
- Proper HTTP semantics and error handling
- Extensive test coverage across all services

#### Issues Identified (Prioritized)

| Priority | Issue | Affected Services |
|----------|-------|-------------------|
| HIGH | Thread safety for in-memory storage | job_runner, report_storage, marketplace, template_service, scheduler |
| MEDIUM | Inconsistent datetime handling | report_storage, marketplace, template, ml_analytics, search_analytics |
| MEDIUM | Jinja2 templates not sandboxed | template_service |
| MEDIUM | API path conflict | marketplace router (/api/v1/api/v1) |
| LOW | Duplicate router functionality | analytics vs analytics_v2, schedule vs scheduler |
| LOW | N+1 query in get_all_people | neo4j_service |
| LOW | Missing CRUD endpoints | projects (no update), files (no list) |

See [10-COMPREHENSIVE-REVIEW.md](docs/findings/10-COMPREHENSIVE-REVIEW.md) for full details.

---

### Phase 11: Production Hardening - ✅ COMPLETED (2025-12-27)

| Task | Status | Notes |
|------|--------|-------|
| Thread safety for in-memory services | ✅ Done | Added RLock to job_runner, report_storage, marketplace, template_service |
| Datetime standardization | ✅ Done | Replaced datetime.now()/utcnow() with datetime.now(timezone.utc) |
| Router conflict resolution | ✅ Done | Fixed marketplace prefix, deprecated analytics.py and schedule.py |
| Jinja2 sandboxing | ✅ Done | SandboxedEnvironment for user templates, 14 security tests |
| Missing CRUD endpoints | ✅ Done | Added project update (PATCH) and file list (GET) endpoints |
| Comprehensive tests | ✅ Done | 1,595 tests passing, 2 skipped |

#### Thread Safety Implementation

Added `threading.RLock()` to all in-memory services ensuring safe concurrent access.

#### Datetime Standardization

All services now use `datetime.now(timezone.utc)` for timezone-aware timestamps.

#### Router Consolidation

- Fixed `marketplace.py` prefix from `/api/v1/marketplace` to `/marketplace`
- Created deprecation wrappers for legacy `analytics.py` → `analytics_v2`
- Created deprecation wrappers for legacy `schedule.py` → `scheduler`

#### Jinja2 Security

Added `SandboxedEnvironment` for user template rendering with 14 comprehensive security tests.

#### New Endpoints

- `PATCH /projects/{safe_name}` - Update project name/description
- `GET /projects/{safe_name}/entities/{entity_id}/files/` - List entity files

See [11-PHASE11-PRODUCTION-HARDENING.md](docs/findings/11-PHASE11-PRODUCTION-HARDENING.md) for full details.

---

### Phase 12: Performance & Scalability Optimization (COMPLETED)

**Date:** 2024-12-28
**Tests:** 1595 passed

#### N+1 Query Fixes
- Added `get_people_batch()` for bulk entity fetching
- Updated `find_shortest_path()`, `get_entity_neighborhood()`, `find_clusters()` to use batch queries

#### Database-Level Pagination
- Added `get_all_people_paginated()` with SKIP/LIMIT
- Added `get_people_count()` for efficient counting
- Updated bulk operations to use database pagination

#### Cache Improvements
- Converted `_zero_result_queries` to OrderedDict with LRU eviction
- Added `max_zero_result_queries` parameter (default: 1000)
- Added TF-IDF cache invalidation methods

#### Batch Import
- Added `create_people_batch()` using UNWIND
- Updated `import_entities()` for batch creation

See [12-PHASE12-PERFORMANCE-SCALABILITY.md](docs/findings/12-PHASE12-PERFORMANCE-SCALABILITY.md) for full details.

---

### Phase 13: Infrastructure (COMPLETED)

**Date:** 2024-12-28
**Tests:** 1628 passed, 2 skipped

#### Celery Task Processing
- Created Celery app configuration with Redis broker
- Implemented report generation tasks (`generate_scheduled_report`, `process_due_reports`)
- Implemented maintenance tasks (`cleanup_expired_cache`, `health_check`, etc.)
- Added Celery Beat schedule for periodic tasks

#### Docker Compose Enhancement
- Added Redis 7 service with persistence and health checks
- Added Celery worker service with 4 concurrent workers
- Added Celery Beat scheduler service
- Updated basset_hound service with Redis dependency

#### Deprecation Fix
- Updated test imports from deprecated `schedule` to `scheduler` module
- Added `_parse_format()` function to scheduler.py

See [13-PHASE13-INFRASTRUCTURE.md](docs/findings/13-PHASE13-INFRASTRUCTURE.md) for full details.

---

### Phase 14: Local-First Simplification (COMPLETED)

**Date:** 2024-12-28
**Tests:** 1692 passed
**Philosophy:** Local-first, single-user application for security researchers

#### Change Tracking Service
- Lightweight change tracking for debugging and audit purposes
- Log CREATE, UPDATE, DELETE, LINK, UNLINK, VIEW actions
- Track entity_type, entity_id, project_id, changes, timestamps
- In-memory storage with pluggable backend interface
- Query methods for filtering by entity, project, action, date range
- No user attribution (single-user application)

#### Simplified WebSocket Service
- Removed authentication complexity (not needed for local use)
- Clean connection management
- Project-scoped subscriptions
- Real-time notifications without auth overhead

#### Code Cleanup
- Removed api/middleware/auth.py (WebSocket authentication)
- Removed 53 auth-related tests (no longer needed)
- Simplified audit logger (removed user_id, ip_address tracking)
- Reduced WebSocket service from 904 to 787 lines
- Reduced WebSocket router from 475 to 271 lines

---

## Design Philosophy

Basset Hound is a **local-first, single-user tool** for security researchers:

1. **No Authentication Required** - Run locally on your own machine
2. **No Multi-User Support** - One researcher, one instance
3. **Open Source** - Self-hosted, full control over your data
4. **API/MCP Integration** - External tools can leverage the API without auth barriers
5. **Simple by Design** - Focus on OSINT data management, not enterprise features

---

### Phase 15: Orphan Data Management & Data Normalization - ✅ COMPLETED (2025-12-29)

| Task | Status | Notes |
|------|--------|-------|
| Orphan data Pydantic models | ✅ Done | 15 identifier types, CRUD models, link/detach models |
| Orphan data service layer | ✅ Done | Full CRUD, search, auto-linking, bulk operations |
| Orphan data REST API | ✅ Done | 10+ endpoints for orphan management |
| Neo4j orphan data methods | ✅ Done | Constraints, indexes, relationship queries |
| Bidirectional orphan data flow | ✅ Done | Link orphan→entity AND detach entity→orphan |
| Data normalization service | ✅ Done | Phone, email, username, domain, URL, IP, crypto, MAC |
| Detach endpoint | ✅ Done | Soft-delete: move entity data to orphan status |
| Comprehensive tests | ✅ Done | Normalizer tests with all identifier types |

#### Orphan Data Management

Orphan data represents unlinked identifiers (emails, phones, crypto addresses, usernames, IPs, etc.) that haven't been tied to entities yet. This is critical for OSINT work where data is collected before entity relationships are established.

**Identifier Types Supported:**
- EMAIL, PHONE, CRYPTO_ADDRESS, USERNAME, IP_ADDRESS
- DOMAIN, URL, SOCIAL_MEDIA, LICENSE_PLATE, PASSPORT
- SSN, ACCOUNT_NUMBER, MAC_ADDRESS, IMEI, OTHER

**Bidirectional Data Flow:**
- **Link to Entity**: Move orphan data into an entity's profile (`POST /orphans/{id}/link`)
- **Detach from Entity**: Move entity field data to orphan status (`POST /orphans/detach`)
- Data is never truly deleted - just moved between states (soft delete)

**API Endpoints:**
- `POST /projects/{id}/orphans` - Create orphan
- `GET /projects/{id}/orphans` - List/search orphans
- `GET /projects/{id}/orphans/{id}` - Get by ID
- `PUT /projects/{id}/orphans/{id}` - Update
- `DELETE /projects/{id}/orphans/{id}` - Delete
- `GET /projects/{id}/orphans/{id}/suggestions` - Entity match suggestions
- `POST /projects/{id}/orphans/{id}/link` - Link to entity
- `POST /projects/{id}/orphans/detach` - Detach data from entity
- `POST /projects/{id}/orphans/batch` - Bulk import
- `GET /projects/{id}/orphans/duplicates` - Find duplicates

#### Data Normalization Service

Standardizes data formats before storage to make searching consistent and reliable.

**Phone Normalization:**
- `(555) 123-4567` → `5551234567`
- `+1-555-123-4567` → `+15551234567` (preserves country code)
- Extracts: `country_code`, `local_number`, `has_country_code`

**Email Normalization:**
- `User@EXAMPLE.COM` → `user@example.com`
- Plus-addressing: `service+support@gmail.com` stores both:
  - Normalized: `service+support@gmail.com`
  - Alternative: `service@gmail.com` (base email)
- Extracts: `user`, `domain`, `tag` (if plus-addressing)

**Username Normalization:**
- `@JohnDoe` → `johndoe`
- Removes leading @, lowercases

**Domain Normalization:**
- `https://WWW.Example.COM/` → `example.com`
- Removes protocol, www prefix, trailing slashes

**URL Normalization:**
- `HTTP://WWW.Example.COM/Path/Page` → `http://example.com/Path/Page`
- Lowercases domain, preserves path case

**IP Normalization:**
- `192.168.001.001` → `192.168.1.1` (removes leading zeros)
- IPv6: `::1` → `0000:0000:0000:0000:0000:0000:0000:0001`

**Crypto Address Normalization:**
- Trims whitespace, preserves case (checksum-sensitive)
- Auto-detects: Bitcoin, Ethereum, Litecoin, Ripple, Monero, Dogecoin, etc.

**MAC Address Normalization:**
- `00-1A-2B-3C-4D-5E` → `00:1a:2b:3c:4d:5e`
- Standardizes to colon-separated lowercase

#### Files Created

```
api/models/
└── orphan.py                    # Pydantic models (DetachRequest, DetachResponse, etc.)

api/services/
├── orphan_service.py            # OrphanService with bidirectional flow
└── normalizer.py                # DataNormalizer for all identifier types

api/routers/
└── orphan.py                    # REST API endpoints with detach support

tests/
└── test_normalizer.py           # Comprehensive normalizer tests
```

---

### Phase 16: Enhanced Visualization & Data Import - COMPLETED (2025-12-29)

| Task | Status | Notes |
|------|--------|-------|
| Graph Visualization Service | ✅ Done | 5 layout algorithms, 4 export formats, graph metrics |
| Layout algorithms | ✅ Done | Force-directed, Hierarchical, Circular, Radial, Grid |
| Export formats | ✅ Done | D3.js JSON, Cytoscape.js JSON, GraphML, DOT |
| Graph metrics | ✅ Done | Degree centrality, betweenness centrality, node degrees |
| Data Import Connectors | ✅ Done | 7 connectors for OSINT tools |
| Maltego connector | ✅ Done | CSV entity exports with type mapping |
| SpiderFoot connector | ✅ Done | JSON scan results with module attribution |
| TheHarvester connector | ✅ Done | JSON email/domain/IP discovery |
| Shodan connector | ✅ Done | JSON host exports with service data |
| HIBP connector | ✅ Done | JSON breach data import |
| Generic CSV/JSON connectors | ✅ Done | Flexible import with column mapping |
| Auto type detection | ✅ Done | Email, phone, IP, domain, URL, username, crypto, MAC |
| Visualization API endpoints | ✅ Done | Project graph, entity neighborhood, clusters, export |
| Import API endpoints | ✅ Done | Per-tool import, formats list, validate |

#### Graph Visualization Features

- **Layout Algorithms:**
  - Force-Directed (Fruchterman-Reingold) - physics-based spring simulation
  - Hierarchical - tree-like level arrangement
  - Circular - nodes on a circle
  - Radial - concentric circles based on distance from center
  - Grid - simple grid arrangement

- **Export Formats:**
  - D3.js JSON - force-simulation compatible
  - Cytoscape.js JSON - graph library format
  - GraphML - XML-based standard
  - DOT - Graphviz format

- **Graph Metrics:**
  - Degree centrality (normalized connection count)
  - Betweenness centrality (path importance)
  - Node degrees (in/out connection counts)

#### Data Import Connectors

- **Supported Tools:**
  - Maltego (CSV) - entity exports with links
  - SpiderFoot (JSON) - 20+ data types
  - TheHarvester (JSON) - email/subdomain discovery
  - Shodan (JSON) - host/service data
  - HIBP (JSON) - breach data
  - Generic CSV - configurable mapping
  - Generic JSON - flexible import

- **Features:**
  - Auto type detection for 10+ identifier types
  - Dry-run validation mode
  - ImportResult with success/error/warning tracking
  - Entity and orphan creation support
  - Relationship preservation from source tools

#### Files Created

```
api/models/
├── visualization.py         # Pydantic models (enums, graph data)
└── data_import.py          # Import models (formats, results)

api/services/
├── graph_visualization.py   # 1900+ lines - layouts, metrics, exporters
└── data_import.py          # 2000+ lines - 7 import connectors

api/routers/
├── visualization.py        # Visualization endpoints
└── import_data.py          # Import endpoints

docs/findings/
└── 16-PHASE16-ENHANCED-VISUALIZATION-DATA-IMPORT.md
```

See [16-PHASE16-ENHANCED-VISUALIZATION-DATA-IMPORT.md](docs/findings/16-PHASE16-ENHANCED-VISUALIZATION-DATA-IMPORT.md) for full details.

---

### Phase 17: Frontend Integration & UI Enhancements - ✅ COMPLETED (2025-12-29)

| Task | Status | Notes |
|------|--------|-------|
| Timeline Visualization Service | ✅ Done | Entity/relationship timelines, heatmaps, snapshots, evolution tracking |
| Timeline Visualization API | ✅ Done | 6 endpoints for temporal graph analysis |
| Entity Type UI Service | ✅ Done | UI configuration for all 6 entity types |
| Entity Type UI API | ✅ Done | 8 endpoints for type configs, icons, colors, fields, validation |
| Frontend Components API | ✅ Done | Component specifications for React/Vue/vanilla JS |
| WebSocket Enhancements | ✅ Done | 10 new notification types for real-time graph updates |
| Comprehensive tests | ✅ Done | 49 Phase 17 integration tests, 60 entity type tests |

#### Timeline Visualization Features

- **Entity Timeline**: Track all events for an entity (creation, updates, relationships)
- **Relationship Timeline**: Track changes between two specific entities
- **Activity Heatmap**: Aggregate events by hour/day/week/month for heatmap visualization
- **Temporal Snapshots**: Reconstruct graph state at any point in time
- **Entity Evolution**: Track version history of entity profiles with change diffs
- **Period Comparison**: Compare graph statistics between two time periods

**API Endpoints:**
- `GET /timeline-viz/{project}/entity/{entity_id}` - Entity timeline events
- `GET /timeline-viz/{project}/relationship/{entity1}/{entity2}` - Relationship timeline
- `GET /timeline-viz/{project}/activity` - Activity heatmap data
- `GET /timeline-viz/{project}/snapshot` - Temporal graph snapshot
- `GET /timeline-viz/{project}/entity/{entity_id}/evolution` - Entity evolution history
- `POST /timeline-viz/{project}/compare` - Compare time periods

#### Entity Type UI Features

- **Type Configurations**: Icons, colors, labels for Person, Organization, Device, Location, Event, Document
- **Form Field Definitions**: Type-specific fields with validation rules
- **Cross-Type Relationships**: Valid relationship types between entity types
- **Entity Validation**: Validate data against type schemas
- **Type Statistics**: Per-project entity type distribution

**API Endpoints:**
- `GET /entity-types` - List all entity types
- `GET /entity-types/{type}` - Get specific type config
- `GET /entity-types/{type}/icon` - Get type icon
- `GET /entity-types/{type}/color` - Get type color
- `GET /entity-types/{type}/fields` - Get form fields
- `GET /entity-types/{source}/relationships/{target}` - Cross-type relationships
- `POST /entity-types/{type}/validate` - Validate entity data
- `GET /projects/{project}/entity-types/stats` - Entity type statistics

#### Frontend Components API Features

Component specifications for building frontend applications:

- **GraphViewer** - D3.js graph visualization with layouts, zoom, real-time updates
- **EntityCard** - Entity summary cards with actions
- **TimelineViewer** - Temporal event visualization
- **ImportWizard** - Multi-step import flow
- **SearchBar** - Search with autocomplete and filters

**API Endpoints:**
- `GET /frontend/components` - All component specs
- `GET /frontend/components/{type}` - Specific component spec
- `GET /frontend/typescript` - TypeScript definitions
- `GET /frontend/css-variables` - CSS custom properties
- `GET /frontend/dependencies` - NPM dependencies
- `GET /frontend/frameworks` - Supported frameworks

#### WebSocket Enhancements

New notification types for real-time graph updates:

```python
GRAPH_NODE_ADDED     # New node added
GRAPH_NODE_UPDATED   # Node modified
GRAPH_NODE_DELETED   # Node removed
GRAPH_EDGE_ADDED     # New edge added
GRAPH_EDGE_UPDATED   # Edge modified
GRAPH_EDGE_DELETED   # Edge removed
GRAPH_LAYOUT_CHANGED # Layout changed
GRAPH_CLUSTER_DETECTED  # Cluster identified
IMPORT_PROGRESS      # Import progress
IMPORT_COMPLETE      # Import complete
```

#### Files Created

```
api/services/
├── timeline_visualization.py   # ~900 lines - temporal graph visualization
├── entity_type_ui.py          # ~600 lines - entity type UI config
└── frontend_components.py     # ~800 lines - frontend component specs

api/models/
└── entity_type_ui.py          # ~645 lines - entity type UI models

api/routers/
├── timeline_visualization.py  # ~900 lines - timeline visualization API
├── entity_types.py           # ~750 lines - entity types API
└── frontend_components.py    # ~190 lines - frontend components API

tests/
└── test_phase17_integration.py # 49 comprehensive tests
```

See [17-PHASE17-FRONTEND-INTEGRATION-UI-ENHANCEMENTS.md](docs/findings/17-PHASE17-FRONTEND-INTEGRATION-UI-ENHANCEMENTS.md) for full details.

---

### Phase 18: Advanced Graph Analytics ✅ COMPLETE

**Completed:** December 2024

Focus on graph-powered discovery - the core value proposition.

**Implemented:**
1. ✅ **Community Detection** - Louvain/Label Propagation for finding entity clusters
2. ✅ **Influence Propagation** - PageRank, influence spread simulation, key entity detection
3. ✅ **Similarity Scoring** - Jaccard, Cosine, Common Neighbors, SimRank
4. ✅ **Temporal Patterns** - Burst detection, trend analysis, cyclical patterns, anomalies
5. ✅ **Graph Analytics API** - REST endpoints for all graph analytics features

**Files Created:**
- `api/services/community_detection.py` - Community detection algorithms
- `api/services/influence_service.py` - Influence propagation & key entity detection
- `api/services/similarity_service.py` - Entity similarity scoring
- `api/services/temporal_patterns.py` - Temporal pattern detection
- `api/routers/graph_analytics.py` - REST API endpoints

**Test Coverage:** 56 tests, all passing

See [18-PHASE18-ADVANCED-GRAPH-ANALYTICS.md](findings/18-PHASE18-ADVANCED-GRAPH-ANALYTICS.md) for full details.

---

### Phase 19: Deployment & Infrastructure - ✅ COMPLETED (2025-12-29)

| Task | Status | Notes |
|------|--------|-------|
| Dockerfile multi-stage build | ✅ Done | Python 3.12-slim, non-root user, health checks |
| docker-compose.yml full stack | ✅ Done | Neo4j 5.28 + GDS, Redis, Celery worker/beat |
| Native Ubuntu 22.04 install script | ✅ Done | install.sh with Python 3.12, Neo4j 5.x, GDS plugin |
| Neo4j GDS guaranteed | ✅ Done | GDS plugin auto-installed in both deployment options |
| Pydantic v2 deprecation fixes | ✅ Done | Fixed influence_service.py model configs |
| Documentation cleanup | ✅ Done | Updated service docstrings to reflect GDS guarantee |

**Philosophy:** Two deployment paths, both fully supported:
1. **Docker** - Single command deployment with all dependencies pre-configured
2. **Native Ubuntu 22.04** - Direct installation with venv for development/customization

**Key Changes:**
- Neo4j GDS is now guaranteed via deployment (not optional)
- Python fallback implementations kept for testing/in-memory analysis only
- Docker exposes API (port 8000), Neo4j Browser (port 7474), Redis (port 6379)
- install.sh handles Python 3.12, Neo4j 5.x, GDS plugin, Redis

**Files Created/Updated:**
- `Dockerfile` - Multi-stage build with libmagic, non-root user
- `docker-compose.yml` - Full stack: Neo4j + GDS, Redis, FastAPI, Celery
- `install.sh` - Native Ubuntu 22.04 installation script (24KB)
- `api/services/community_detection.py` - Updated documentation
- `api/services/influence_service.py` - Fixed Pydantic deprecation warnings

See [19-PHASE19-DEPLOYMENT-INFRASTRUCTURE.md](docs/findings/19-PHASE19-DEPLOYMENT-INFRASTRUCTURE.md) for full details.

---

### Phase 20: Query & Performance Optimization - ✅ COMPLETED (2025-12-29)

| Task | Status | Notes |
|------|--------|-------|
| Query Cache Service | ✅ Done | Decorator-based caching with TTL per query type |
| Neo4j Index Optimization | ✅ Done | Composite indexes for FieldValue, OrphanData |
| Batch Orphan Operations | ✅ Done | UNWIND-based batch create and link |
| Result Streaming | ✅ Done | ChunkedIterator, AsyncResultStream, pagination |
| Performance Tests | ✅ Done | 36 comprehensive tests |

**Key Features:**

1. **Query Cache Service** (`api/services/query_cache.py`)
   - `@cached_query` decorator for automatic caching
   - 10 query types with configurable TTLs (2 min to 1 hour)
   - Project and entity-aware cache invalidation
   - LRU eviction, statistics tracking

2. **Neo4j Index Optimization**
   - FieldValue composite index: `(section_id, field_id)`
   - OrphanData composite index: `(identifier_type, linked)`
   - Person profile index for search
   - TAGGED relationship index

3. **Batch Operations**
   - `create_orphan_data_batch()` - O(n) to O(1) query reduction
   - `link_orphan_data_batch()` - Bulk linking with UNWIND

4. **Result Streaming** (`api/services/result_streaming.py`)
   - `PaginatedResult` for API responses
   - `ChunkedIterator` for memory-efficient processing
   - `AsyncResultStream` for streaming large datasets
   - `process_in_batches()` for parallel processing

**Files Created/Updated:**
- `api/services/query_cache.py` - Query cache service (350+ lines)
- `api/services/result_streaming.py` - Streaming utilities (350+ lines)
- `neo4j_handler.py` - Batch orphan ops, new indexes
- `tests/test_phase20_performance.py` - 36 tests

See [20-PHASE20-QUERY-PERFORMANCE-OPTIMIZATION.md](docs/findings/20-PHASE20-QUERY-PERFORMANCE-OPTIMIZATION.md) for full details.

---

### Phase 21: Import/Export Flexibility - ✅ COMPLETED (2025-12-29)

| Task | Status | Notes |
|------|--------|-------|
| Import Mapping Service | ✅ Done | 18 transformation types, reusable configs, validation |
| LLM Export Service | ✅ Done | 5 formats, token estimation, intelligent truncation |
| Graph Format Converter | ✅ Done | 8 formats: GraphML, GEXF, D3, Cytoscape, DOT, Pajek |
| Comprehensive Tests | ✅ Done | 39 tests, all passing |
| Documentation | ✅ Done | Full Phase 21 findings documented |

**Key Features:**

1. **Import Mapping Service** (`api/services/import_mapping.py`)
   - 18 transformation types (direct, uppercase, lowercase, trim, replace, regex, split, join, concat, default, date format, extract, hash, template, JSON path, lookup, custom, conditional)
   - Reusable mapping configurations with CRUD operations
   - Validation and preview before applying mappings
   - Apply mappings to transform imported data

2. **LLM Export Service** (`api/services/llm_export.py`)
   - 5 export formats: Markdown, JSON, YAML, Plain Text, XML
   - Token estimation using GPT-family approximation
   - Intelligent truncation to fit context limits
   - Configurable context (entities, relationships, timeline, stats)
   - Export types: single entity, project summary, entity context, investigation brief

3. **Graph Format Converter** (`api/services/graph_format_converter.py`)
   - 8 graph formats supported:
     - GraphML (XML-based, widely supported)
     - GEXF (Gephi format)
     - JSON Graph (JSON-based structure)
     - Cytoscape (Cytoscape.js format)
     - D3 (D3.js force layout)
     - DOT (Graphviz format)
     - Pajek (network format)
     - Adjacency List (simple text)
   - Format auto-detection and validation
   - Property preservation and direction handling
   - Internal graph representation for conversions

**Files Created:**
- `api/services/import_mapping.py` - Import mapping service (~500 lines)
- `api/services/llm_export.py` - LLM export service (~580 lines)
- `api/services/graph_format_converter.py` - Graph format converter (~660 lines)
- `tests/test_phase21_import_export.py` - 39 tests

See [21-PHASE21-IMPORT-EXPORT-FLEXIBILITY.md](docs/findings/21-PHASE21-IMPORT-EXPORT-FLEXIBILITY.md) for full details.

---

### Phase 22: API Endpoints for Phase 21 Services - ✅ COMPLETED (2025-12-29)

| Task | Status | Notes |
|------|--------|-------|
| Import Mapping Router | ✅ Done | 8 endpoints for CRUD, apply, validate, preview |
| LLM Export Router | ✅ Done | 6 endpoints for entity/project exports, token estimation |
| Graph Format Router | ✅ Done | 6 endpoints for convert, detect, validate, list formats |
| Router Integration | ✅ Done | All routers registered in api_router |
| Comprehensive Tests | ✅ Done | 41 tests, all passing |
| Documentation | ✅ Done | Full Phase 22 findings documented |

**Key Features:**

1. **Import Mapping Router** (`api/routers/import_mapping.py`)
   - POST /import-mappings - Create mapping
   - GET /import-mappings - List mappings
   - GET /import-mappings/{id} - Get mapping
   - PUT /import-mappings/{id} - Update mapping
   - DELETE /import-mappings/{id} - Delete mapping
   - POST /import-mappings/{id}/apply - Apply mapping to data
   - POST /import-mappings/validate - Validate config
   - POST /import-mappings/preview - Preview transformation

2. **LLM Export Router** (`api/routers/llm_export.py`)
   - POST /projects/{project}/llm-export/entity/{id} - Export entity
   - POST /projects/{project}/llm-export/summary - Export project summary
   - POST /projects/{project}/llm-export/entity/{id}/context - Export with context
   - POST /projects/{project}/llm-export/investigation-brief - Export investigation
   - POST /llm-export/estimate-tokens - Estimate tokens
   - GET /llm-export/formats - List formats

3. **Graph Format Router** (`api/routers/graph_format.py`)
   - POST /graph-format/convert - Convert between formats
   - POST /graph-format/convert-raw - Convert and download file
   - POST /graph-format/detect - Auto-detect format
   - POST /graph-format/validate - Validate format
   - GET /graph-format/formats - List all formats
   - GET /graph-format/formats/{format} - Get format details

**Files Created:**
- `api/routers/import_mapping.py` - Import mapping endpoints (~650 lines)
- `api/routers/llm_export.py` - LLM export endpoints (~627 lines)
- `api/routers/graph_format.py` - Graph format endpoints (~530 lines)
- `tests/test_phase22_api_endpoints.py` - 41 tests

See [22-PHASE22-API-ENDPOINTS-PHASE21-SERVICES.md](docs/findings/22-PHASE22-API-ENDPOINTS-PHASE21-SERVICES.md) for full details.

---

### Phase 23: Saved Search Configurations - ✅ COMPLETED (2025-12-29)

| Task | Status | Notes |
|------|--------|-------|
| Saved Search Service | ✅ Done | Full CRUD, scopes, categories, tags, favorites |
| Search Execution | ✅ Done | Execute saved searches with parameter overrides |
| Saved Search Router | ✅ Done | 17 endpoints for management and execution |
| Project-scoped Searches | ✅ Done | Project and global search scope support |
| Usage Tracking | ✅ Done | Execution count, last executed, recent/popular |
| Comprehensive Tests | ✅ Done | 50 tests, all passing |
| Documentation | ✅ Done | Full Phase 23 findings documented |

**Key Features:**

1. **Saved Search Service** (`api/services/saved_search.py`)
   - Save search configurations with name, description, query
   - Three scopes: GLOBAL, PROJECT, USER
   - Six categories: GENERAL, INVESTIGATION, MONITORING, COMPLIANCE, RISK, CUSTOM
   - Tag-based organization with usage counts
   - Favorites, recent, and popular searches
   - Duplicate and clone searches
   - Search through saved searches by name/description

2. **Search Execution**
   - Execute saved searches with stored parameters
   - Override any parameter at execution time (query, limit, project, etc.)
   - Track execution time, count, and last execution
   - Integration with existing SearchService

3. **REST API Endpoints** (`api/routers/saved_search.py`)
   - POST /saved-searches - Create saved search
   - GET /saved-searches - List with filtering
   - GET /saved-searches/{id} - Get specific search
   - PUT /saved-searches/{id} - Update search
   - DELETE /saved-searches/{id} - Delete search
   - POST /saved-searches/{id}/execute - Execute search
   - POST /saved-searches/{id}/duplicate - Clone search
   - POST /saved-searches/{id}/toggle-favorite - Toggle favorite
   - GET /saved-searches/favorites - Get favorites
   - GET /saved-searches/recent - Get recently executed
   - GET /saved-searches/popular - Get most popular
   - GET /saved-searches/tags - Get all tags with counts
   - GET /saved-searches/by-category/{category} - Filter by category
   - GET /saved-searches/by-tag/{tag} - Filter by tag
   - GET /saved-searches/search - Search saved searches
   - GET/POST /projects/{project}/saved-searches - Project-scoped endpoints

**Files Created:**
- `api/services/saved_search.py` - Saved search service (~600 lines)
- `api/routers/saved_search.py` - REST API endpoints (~650 lines)
- `tests/test_phase23_saved_search.py` - 50 tests

**Combined Tests:** 130 tests (Phase 21-23), all passing

See [23-PHASE23-SAVED-SEARCH-CONFIGURATIONS.md](docs/findings/23-PHASE23-SAVED-SEARCH-CONFIGURATIONS.md) for full details.

---

---

## Performance Philosophy: No Artificial Limits

Basset Hound is designed with a **no artificial rate limiting** philosophy:

### What This Means

1. **No API Rate Limiting**: Internal API endpoints have NO rate limits. Your queries, searches, analytics, and data operations are only limited by your hardware capabilities and database performance.

2. **Scale With Your Hardware**: If you have a powerful machine with lots of RAM and a fast SSD, Basset Hound will use it. If you're on a laptop, it will still work - just slower.

3. **Database is the Bottleneck, Not the App**: The only real limits are what Neo4j and your storage can handle. Basset Hound never artificially restricts throughput.

### The Only Exception: Outbound Rate Limiting

The **only** rate limiting in Basset Hound applies to **outbound requests to external services**:

- **Webhook Deliveries**: Limited to ~10 requests/second by default to avoid overwhelming external webhook endpoints
- **External API Calls**: Any future integrations with external services will include polite rate limiting

This protects third-party services from being spammed, not the user.

### Why This Matters

- **OSINT workflows are bursty**: You might import 10,000 records, then do nothing for an hour
- **Local-first means local resources**: You're running on your own machine, not a shared server
- **Research requires speed**: When investigating, waiting for artificial throttling is counterproductive

---

### Phase 24: Webhook Integrations - ✅ COMPLETED (2025-12-29)

| Task | Status | Notes |
|------|--------|-------|
| Webhook Service | ✅ Done | CRUD, HMAC signatures, retry logic, delivery tracking |
| 20+ Event Types | ✅ Done | Entity, relationship, search, report, import/export, project, system |
| Outbound Throttling | ✅ Done | 10 req/sec to protect external services (ONLY rate limiting in app) |
| Webhook API Router | ✅ Done | 13 endpoints for webhook management and delivery tracking |
| Project-scoped Webhooks | ✅ Done | Filter webhooks by project, project-scoped endpoints |
| Comprehensive Tests | ✅ Done | 71 tests, all passing |
| Documentation | ✅ Done | Full Phase 24 findings documented |

**Key Features:**

1. **Webhook Service** (`api/services/webhook_service.py`)
   - Full CRUD for webhook configurations
   - HMAC-SHA256 signature verification
   - Retry logic with exponential backoff
   - Delivery logging and status tracking (PENDING, SENDING, SUCCESS, FAILED, RETRYING)
   - LRU eviction for delivery records

2. **Event Types** (20+)
   - Entity: created, updated, deleted
   - Relationship: created, updated, deleted
   - Search: executed, saved_search_executed
   - Report: generated, scheduled
   - Import/Export: started, completed, failed, export_completed
   - Project: created, deleted
   - Orphan: created, linked
   - System: health, rate_limit_exceeded

3. **Outbound Throttling**
   - Default: 10 requests/second
   - Protects external webhook endpoints from being spammed
   - This is the ONLY rate limiting in Basset Hound

4. **REST API Endpoints** (`api/routers/webhooks.py`)
   - POST /webhooks - Create webhook
   - GET /webhooks - List webhooks
   - GET /webhooks/events - List event types
   - GET /webhooks/stats - Get statistics
   - GET /webhooks/{id} - Get specific webhook
   - PUT /webhooks/{id} - Update webhook
   - DELETE /webhooks/{id} - Delete webhook
   - POST /webhooks/{id}/test - Send test event
   - GET /webhooks/{id}/deliveries - Get delivery history
   - GET /webhooks/deliveries/{id} - Get specific delivery
   - POST /webhooks/deliveries/{id}/retry - Retry failed delivery
   - GET/POST /projects/{project}/webhooks - Project-scoped endpoints

**Files Created:**
- `api/services/webhook_service.py` - Webhook service (~760 lines)
- `api/routers/webhooks.py` - REST API endpoints (~720 lines)
- `tests/test_phase24_webhooks.py` - 71 tests

See [24-PHASE24-WEBHOOK-INTEGRATIONS.md](docs/findings/24-PHASE24-WEBHOOK-INTEGRATIONS.md) for full details.

---

### Phase 25: Entity Deduplication & Data Quality Engine - ✅ COMPLETED (2025-12-29)

| Task | Status | Notes |
|------|--------|-------|
| Data Quality Service | ✅ Done | 6 quality dimensions, source reliability, letter grades |
| Deduplication Service | ✅ Done | 7 match types, 7 merge strategies, conflict resolution |
| Data Quality API Router | ✅ Done | 10 endpoints for scoring, config, reports, compare |
| Deduplication API Router | ✅ Done | 11 endpoints for find, merge, preview, history |
| Project-scoped Endpoints | ✅ Done | Quality reports and dedup reports per project |
| Comprehensive Tests | ✅ Done | 70 tests, all passing |
| Documentation | ✅ Done | Full Phase 25 findings documented |

**Key Features:**

1. **Data Quality Service** (`api/services/data_quality.py`)
   - 6 quality dimensions: Completeness, Freshness, Accuracy, Consistency, Uniqueness, Validity
   - 11 data sources with reliability ratings (manual_entry: 0.90, maltego: 0.85, shodan: 0.85, etc.)
   - Letter grades (A-F) based on weighted dimension scores
   - Field-level quality scoring with recommendations
   - Project quality reports with grade distribution
   - Quality comparison between entities
   - LRU caching for performance

2. **Deduplication Service** (`api/services/deduplication.py`)
   - 7 match types: exact, case_insensitive, fuzzy, phonetic, normalized, partial, token_set
   - 7 merge strategies: keep_primary, keep_duplicate, keep_newest, keep_oldest, keep_longest, keep_all, manual
   - Levenshtein similarity for fuzzy matching
   - Phonetic matching (Soundex-like algorithm)
   - Merge preview with conflict detection
   - Merge history and undo support
   - Duplicate reports per project

3. **Data Quality API** (`api/routers/data_quality.py`)
   - POST /data-quality/score - Score single entity
   - POST /data-quality/score/batch - Score multiple entities
   - GET /data-quality/config - Get quality config
   - PUT /data-quality/config - Update config
   - GET /data-quality/sources - List sources with reliability
   - PUT /data-quality/sources/{source} - Update source reliability
   - POST /data-quality/compare - Compare two entities
   - GET /data-quality/stats - Service statistics
   - POST /data-quality/clear-cache - Clear cache
   - GET /projects/{project}/data-quality/report - Project quality report

4. **Deduplication API** (`api/routers/deduplication.py`)
   - POST /deduplication/find - Find duplicates for entity
   - POST /deduplication/find-all - Find all project duplicates
   - POST /deduplication/preview - Preview merge
   - POST /deduplication/merge - Execute merge
   - POST /deduplication/undo/{merge_id} - Undo merge
   - GET /deduplication/history - Get merge history
   - GET /deduplication/config - Get config
   - PUT /deduplication/config - Update config
   - GET /deduplication/stats - Service statistics
   - POST /deduplication/clear-cache - Clear cache
   - GET /projects/{project}/deduplication/report - Project dedup report

**Files Created:**
- `api/services/data_quality.py` - Data quality service (~900 lines)
- `api/services/deduplication.py` - Deduplication service (~900 lines)
- `api/routers/data_quality.py` - Data quality API (~550 lines)
- `api/routers/deduplication.py` - Deduplication API (~500 lines)
- `tests/test_phase25_deduplication_quality.py` - 70 tests

See [25-PHASE25-DEDUPLICATION-DATA-QUALITY.md](docs/findings/25-PHASE25-DEDUPLICATION-DATA-QUALITY.md) for full details.

---

### Phase 26: Data Verification Service - 📋 PLANNED

| Task | Status | Notes |
|------|--------|-------|
| Add DataProvenance model | 📋 Planned | Track source_type, source_url, source_date, captured_by |
| Format validators | 📋 Planned | Email, phone, crypto, domain format validation |
| DNS/MX verification | 📋 Planned | Server-side email domain verification |
| Blockchain verification | 📋 Planned | Check crypto address existence on-chain |
| Phone number parsing | 📋 Planned | libphonenumber integration for validation |
| WHOIS/RDAP lookup | 📋 Planned | Domain registration verification |
| Verification API endpoints | 📋 Planned | POST /verify/email, /verify/phone, /verify/crypto, /verify/domain |
| Integration with orphan creation | 📋 Planned | Optional verification before ingest |

**Purpose:** Verify that ingested data is plausible and exists before storing.

**New Dependencies:**
- `phonenumbers>=8.13.0`
- `dnspython>=2.4.0`
- `httpx>=0.27.0` (for blockchain APIs)

**Key Features:**
1. **DataProvenance Model** - Track where data comes from (human entry vs website)
2. **Format Validators** - Client-compatible validation (regex, checksum)
3. **Network Validators** - Server-side MX record, DNS verification
4. **Blockchain Validators** - Check if crypto addresses have on-chain activity
5. **Verification API** - REST endpoints for data verification

See [INTEGRATION-RESEARCH-2026-01-04.md](docs/findings/INTEGRATION-RESEARCH-2026-01-04.md) for details.

---

### Phase 27: Integration with autofill-extension - 📋 PLANNED

| Task | Status | Notes |
|------|--------|-------|
| Accept provenance in orphan API | 📋 Planned | Enhance POST /orphans to include provenance |
| Verification-gated ingestion | 📋 Planned | Block ingestion if verification fails (configurable) |
| WebSocket notifications for extension | 📋 Planned | Real-time sync status updates |
| Bulk ingest endpoint | 📋 Planned | POST /orphans/batch with provenance |

**Purpose:** Enable autofill-extension to send detected data with full provenance.

---

### Phase 28: Integration with basset-hound-browser - 📋 PLANNED

| Task | Status | Notes |
|------|--------|-------|
| OSINT agent API design | 📋 Planned | Endpoints optimized for automated investigation |
| Evidence storage | 📋 Planned | Store screenshots, HTML, metadata as files |
| Investigation workflow support | 📋 Planned | Track investigation steps and findings |
| Relationship discovery automation | 📋 Planned | Auto-link entities from same source |

**Purpose:** Enable OSINT agents to store investigation findings with full provenance.

---

### Phase 29: Graph Visualization Enhancements - ✅ COMPLETE

| Task | Status | Notes |
|------|--------|-------|
| Center graph on current entity | ✅ Complete | COSE layout with cy.animate({center}) after layoutstop |
| Entity-centric view mode | ✅ Complete | Shows N-hop ego network from current entity |
| Highlight current entity | ✅ Complete | Orange color, larger node size, bold label |
| Navigation from graph | ✅ Complete | Click node to navigate to that entity's profile |
| Relationship filtering | 📋 Planned | Filter edges by relationship type |
| Depth control | ✅ Complete | URL parameter ?depth=N (default 2) |

**Purpose:** When viewing a profile, the relationship map should center on that profile.
**Completed:** 2026-01-04/05 - Graph now centers on current entity with visual highlighting.

---

### Phase 30: MCP Server Modularization - ✅ COMPLETE

| Task | Status | Notes |
|------|--------|-------|
| Split MCP server into modules | ✅ Complete | 10 module files totaling 1,842 lines |
| Schema tools module | ✅ Complete | 6 tools: get_schema, get_sections, get_identifiers, etc. |
| Entity tools module | ✅ Complete | 5 tools: create_entity, get_entity, update_entity, etc. |
| Relationship tools module | ✅ Complete | 7 tools: link_entities, get_related, etc. |
| Search tools module | ✅ Complete | 2 tools: search_entities, search_by_identifier |
| Analysis tools module | ✅ Complete | 4 tools: find_path, analyze_connections, etc. |
| Auto-linking tools module | ✅ Complete | 4 tools: find_duplicates, merge_entities, etc. |
| Projects tools module | ✅ Complete | 3 tools: create_project, list_projects, get_project |
| Reports tools module | ✅ Complete | 2 tools: create_report, get_reports |

**Purpose:** Make the MCP server easier to maintain and extend.
**Completed:** 2026-01-04/05 - All 33 tools split into 8 logical modules.

**Final Structure:**
```
basset_mcp/
├── server.py           # Main entry point (28 lines)
├── __init__.py         # Package exports
├── tools/
│   ├── __init__.py     # Registration hub (45 lines)
│   ├── base.py         # Shared utilities (102 lines)
│   ├── schema.py       # 6 schema tools (350 lines)
│   ├── entities.py     # 5 entity tools (183 lines)
│   ├── relationships.py # 7 relationship tools (407 lines)
│   ├── search.py       # 2 search tools (142 lines)
│   ├── projects.py     # 3 project tools (84 lines)
│   ├── reports.py      # 2 report tools (141 lines)
│   ├── analysis.py     # 4 analysis tools (161 lines)
│   └── auto_linking.py # 4 auto-linking tools (227 lines)
```

---

### Phase 31: Verification & OSINT Agent Integration - ✅ COMPLETE

| Task | Status | Notes |
|------|--------|-------|
| Verification Service | ✅ Complete | Multi-level verification (format, network, external) |
| Verification Router | ✅ Complete | 9 endpoints for email, phone, domain, IP, crypto, etc. |
| DataProvenance Model | ✅ Complete | Full provenance tracking with chain of custody |
| OSINT Router | ✅ Complete | Ingest, investigate, extract endpoints |
| Batch Verification | ✅ Complete | Verify up to 100 identifiers in parallel |

**Purpose:** Enable OSINT agents and browser extensions to verify and ingest data with provenance.
**Completed:** 2026-01-05

**New Files Created:**
- `api/services/verification_service.py` - Verification logic (~650 lines)
- `api/routers/verification.py` - REST endpoints (~350 lines)
- `api/models/provenance.py` - Provenance models (~330 lines)
- `api/routers/osint.py` - OSINT integration endpoints (~450 lines)

**Verification Capabilities:**
| Type | Format | Network | External |
|------|--------|---------|----------|
| Email | RFC 5322, disposable detection | MX lookup | - |
| Phone | E.164, country extraction | - | - |
| Domain | Format validation | DNS A lookup | - |
| IP | IPv4/IPv6, private range detection | - | - |
| URL | Format, component extraction | - | - |
| Crypto | 20+ coins, address type detection | - | Blockchain APIs (planned) |
| Username | Format validation | - | - |

**OSINT Integration Endpoints:**
- `POST /api/v1/osint/ingest` - Ingest identifiers with provenance
- `POST /api/v1/osint/investigate` - Start OSINT investigation job
- `POST /api/v1/osint/extract` - Extract identifiers from HTML
- `GET /api/v1/osint/capabilities` - List supported types
- `GET /api/v1/osint/stats` - Get ingestion statistics

---

### Phase 32: Comprehensive Testing & Code Cleanup - ✅ COMPLETE

| Task | Status | Notes |
|------|--------|-------|
| Verification Service Tests | ✅ Complete | 39 tests covering email, phone, domain, IP, URL, crypto, username |
| OSINT Router Tests | ✅ Complete | Tests for ingest, investigate, extract, capabilities, stats endpoints |
| Provenance Model Tests | ✅ Complete | Tests for all enums, DataProvenance, ProvenanceCreate, ProvenanceChain |
| Dead Code Analysis | ✅ Complete | Identified unused normalizer_v2.py, unused imports |
| Code Cleanup | ✅ Complete | Removed 5 unused imports from app.py |

**Purpose:** Comprehensive test coverage for new verification/OSINT features and codebase cleanup.
**Completed:** 2026-01-05

**Test Files Created:**
- `tests/test_verification_service.py` - 39 tests for multi-level verification
- `tests/test_osint_router.py` - OSINT endpoint tests with FastAPI TestClient
- `tests/test_provenance_models.py` - Full model validation tests

**Dead Code Identified:**
- `api/services/normalizer_v2.py` (1289 lines) - Never imported anywhere in codebase
- Unused imports in `app.py`: pprint, defaultdict, hashlib, uuid4, initialize_person_data

**Code Cleanup Actions:**
- Removed 5 unused imports from `app.py`
- Created [CODE-CLEANUP-2026-01-05.md](docs/findings/CODE-CLEANUP-2026-01-05.md) documenting findings

**Test Summary:**
- Total: 64 new tests passing
- Coverage: Verification service, OSINT router, Provenance models

---

### Phase 33: User Override for Verification - ✅ COMPLETE

| Task | Status | Notes |
|------|--------|-------|
| User override fields in DataProvenance | ✅ Complete | user_verified, user_override, override_reason, override_at |
| USER_OVERRIDE verification state | ✅ Complete | New enum value for user-confirmed data |
| Advisory flags in VerificationResult | ✅ Complete | allows_override, override_hint fields |
| Enhanced IP verification | ✅ Complete | Advisory warnings with override hints for private/loopback IPs |
| Updated API response models | ✅ Complete | VerifyResponse includes override advisory fields |
| Tests for user override | ✅ Complete | 2 new tests for override functionality |

**Purpose:** Verification is ADVISORY, not authoritative. Users can override any verification result.
**Completed:** 2026-01-05

**Philosophy:**
Verification helps catch typos and obvious errors, but the user is the ultimate authority:
- Private IP (10.x.x.x) might be valid on an internal network
- User might be on a VPN where public/private distinctions differ
- Some data might appear invalid but be correct in context

**New Fields in DataProvenance:**
```python
user_verified: bool       # User explicitly confirmed data is correct
user_override: bool       # User overrode automatic verification
override_reason: str      # User's explanation (e.g., "Valid on internal network")
override_at: datetime     # When override was applied
```

**New Fields in VerificationResult:**
```python
allows_override: bool     # Can user override this result?
override_hint: str        # Hint explaining when override is appropriate
```

**Example Override Hints:**
- Private IP: "Override if this is a valid target on your internal network or VPN"
- Loopback: "Override if intentionally targeting localhost"
- Link-local: "Override if this is a known APIPA address on your network"

**Test Summary:**
- Total: 96 tests passing (verification, OSINT, provenance)

---

### Phase 34: Verification Enhancement Research - ✅ COMPLETE

| Task | Status | Notes |
|------|--------|-------|
| Research email verification best practices | ✅ Complete | SPF/DMARC, disposable detection, role-based emails |
| Research phone validation standards | ✅ Complete | libphonenumber integration recommended |
| Research crypto address validation | ✅ Complete | Checksum validation, on-chain verification |
| Research domain/IP reputation | ✅ Complete | RDAP, GeoIP, VirusTotal integration |
| Test coverage gap analysis | ✅ Complete | 55-60% coverage, critical gaps identified |

**Purpose:** Research best practices for improving verification service.
**Completed:** 2026-01-05

**Recommended Dependencies to Add:**
```
phonenumbers>=8.13.0        # Phone validation (libphonenumber)
coinaddrvalidator>=1.1.0    # Crypto checksum validation
base58>=2.1.0               # Base58Check encoding
eth-utils>=2.0.0            # Ethereum utilities
geoip2>=4.0.0               # IP geolocation
```

**Priority Enhancements Identified:**
1. Replace phone regex with libphonenumber (High)
2. Expand disposable email list from 9 to 3000+ domains (High)
3. Add crypto address checksum validation (High)
4. Add RDAP lookup for domains (Medium)
5. Add IP geolocation (Medium)

**Test Coverage Gaps Identified:**
- graph_service.py (Critical - no tests)
- similarity_service.py (Critical - no tests)
- community_detection.py (Critical - no tests)
- neo4j_service.py (Critical - no tests)
- graph.py router (Critical - no tests)

See [SESSION-2026-01-05-PART2.md](docs/findings/SESSION-2026-01-05-PART2.md) for full details.

---

### Phase 35: Verification Enhancement Implementation - ✅ COMPLETE

| Task | Status | Notes |
|------|--------|-------|
| Integrate `phonenumbers` library | ✅ Complete | Enhanced phone validation with libphonenumber |
| Expand disposable email list | ✅ Complete | 9 → 450+ domains |
| Update phone verification tests | ✅ Complete | Tests updated for new API |
| Add phone number type detection test | ✅ Complete | New test for mobile/landline/VOIP detection |

**Purpose:** Implement high-priority enhancements identified in Phase 34 research.
**Completed:** 2026-01-05

**Phone Validation Enhancements:**
- Full libphonenumber (phonenumbers) integration
- E.164, international, and national format output
- Country code and region detection
- Number type detection (mobile, landline, VOIP, toll-free, etc.)
- Carrier detection (when available)
- Geographic location hints
- Better validation with is_possible_number and is_valid_number
- Improved error messages with specific parse failure reasons

**Disposable Email Detection:**
- Expanded from 9 domains to 450+ domains
- Covers all major disposable email services
- Includes variants and subdomains
- Organized by category (tempmail, mailinator, guerrillamail, etc.)

**Tests Updated:**
- 40 verification service tests passing
- 27 provenance model tests passing
- 30 OSINT router tests passing
- Total: 97 tests passing

See [SESSION-2026-01-05-PART3.md](docs/findings/SESSION-2026-01-05-PART3.md) for full details.

---

### Phase 36: Cryptocurrency Address Checksum Validation - ✅ COMPLETE

| Task | Status | Notes |
|------|--------|-------|
| Implement Base58Check validator | ✅ Complete | Bitcoin, Litecoin, Dogecoin, Tron, Dash, Zcash |
| Implement Bech32/Bech32m validator | ✅ Complete | Bitcoin SegWit and Taproot addresses |
| Implement EIP-55 validator | ✅ Complete | Ethereum mixed-case checksum |
| Update crypto detector with checksum | ✅ Complete | Confidence adjusted based on checksum validity |
| Update detect_evm with checksum | ✅ Complete | EIP-55 validation for all EVM chains |
| Update detect_all_possible with checksum | ✅ Complete | Checksum info in all results |
| Add comprehensive checksum tests | ✅ Complete | 113 crypto detector tests passing |
| Fix test fixtures with valid addresses | ✅ Complete | Generated addresses with proper checksums |

**Purpose:** Add cryptographic checksum validation to cryptocurrency address detection for improved confidence.
**Completed:** 2026-01-05

**Checksum Validators Implemented:**

1. **Base58CheckValidator**
   - Standard Bitcoin Base58Check validation (double SHA-256)
   - Supports: Bitcoin (P2PKH, P2SH), Litecoin, Dogecoin, Tron, Dash, Zcash transparent
   - Uses `base58` library for decoding

2. **Bech32Validator**
   - BIP-173 (Bech32) and BIP-350 (Bech32m) support
   - Supports: Bitcoin SegWit (bc1q...), Bitcoin Taproot (bc1p...), Litecoin SegWit
   - Implements polymod checksum verification

3. **EIP55Validator**
   - Ethereum EIP-55 mixed-case checksum validation
   - Uses Keccak-256 hash (via pycryptodome)
   - All-lowercase and all-uppercase bypass checksum (per EIP-55 spec)

**Confidence Score Adjustments:**
- Valid checksum: +0.03 to confidence (max 0.99)
- Invalid checksum: -0.30 to confidence (min 0.10)
- Unknown checksum: No adjustment

**Notes:**
- XRP/Ripple uses a different checksum algorithm - NOT supported (different from Bitcoin)
- Installed dependencies: `base58==2.1.1`, `pycryptodome==3.23.0`

**Tests:**
- 113 crypto detector tests passing
- 40 verification service tests passing
- New test classes: TestChecksumValidation, TestBase58CheckValidator, TestBech32Validator, TestEIP55Validator

See [SESSION-2026-01-05-PART4.md](docs/findings/SESSION-2026-01-05-PART4.md) for full details.

---

### Future Work (Prioritized)

**Priority 1 - High Impact:**
- ~~Integrate `phonenumbers` library for phone validation~~ ✅ (Phase 35)
- ~~Expand disposable email detection~~ ✅ (Phase 35 - 9 → 450+ domains)
- ~~Add crypto address checksum validation~~ ✅ (Phase 36 - Base58Check, Bech32, EIP-55)
- Add tests for graph_service.py

**Priority 2 - Medium Impact:**
- RDAP lookup for domains
- IP geolocation service (MaxMind GeoLite2)
- Tests for similarity_service.py, community_detection.py
- VirusTotal integration for domain reputation

**Priority 3 - Lower Priority:**
- Plugin architecture for custom analyzers
- Redis backend for query cache
- Multi-tenant support (for team usage)
- Decision on `normalizer_v2.py` (integrate or remove)

---

## Strategic Vision: Multi-Project Intelligence Platform

### Evolution from OSINT to General-Purpose

**basset-hound** started as an OSINT-focused entity tracker but has evolved into a **general-purpose entity relationship backbone** that can serve multiple domains:
- Open Source Intelligence (OSINT) investigations
- Penetration testing target tracking
- Research and data collection
- Any domain requiring entity-relationship storage with provenance

### Project Scope Definition

**basset-hound Core Mission:** Entity relationship storage, graph analysis, and data provenance tracking - serving as the **data backbone** for intelligence applications.

| In Scope | Out of Scope |
|----------|--------------|
| Entity CRUD with typed fields | Browser automation (→ basset-hound-browser) |
| Relationship tracking and graph traversal | Form detection/autofill (→ autofill-extension) |
| Orphan data management | AI agent logic (→ palletai) |
| Data provenance and chain of custody | Chrome extension features |
| API/MCP server for external tools | Headless browser operation |
| Verification and validation services | |
| Schema-driven entity configuration | User interface (UI is secondary to API) |

### Integration Philosophy

basset-hound exposes an **MCP server** that AI agents (via palletai) treat as a "system tool" - similar to how an agent might use `nmap` or `curl`. The MCP tools are:
- `create_entity`, `update_entity`, `query_entities`
- `create_relationship`, `get_entity_graph`
- `link_orphan`, `record_provenance`

### Related Projects Integration

```
┌─────────────────────────────────────────────────────────────────────┐
│                     INTELLIGENCE PLATFORM ECOSYSTEM                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                      palletai (Orchestrator)                   │  │
│  │   AI agents treat MCP servers as "system tools" like nmap     │  │
│  └──────────────────────────────┬───────────────────────────────┘  │
│                                 │                                    │
│            ┌────────────────────┼────────────────────┐              │
│            │ MCP Client         │ MCP Client         │ MCP Client   │
│            ▼                    ▼                    ▼              │
│  ┌──────────────┐    ┌───────────────────┐    ┌──────────────────┐ │
│  │ basset-hound │    │ basset-hound-     │    │ autofill-ext     │ │
│  │ MCP Server   │    │ browser MCP Srvr  │    │ MCP Server       │ │
│  │ (Data Store) │    │ (Browser Auto)    │    │ (Chrome Plugin)  │ │
│  └──────────────┘    └───────────────────┘    └──────────────────┘ │
│         │                      │                        │           │
│         │         Similar functionality, different deployment:      │
│         │         - autofill-ext: Quick-start Chrome extension     │
│         │         - bh-browser: Full-control Electron app          │
│         │                                                           │
└─────────────────────────────────────────────────────────────────────┘
```

### Browser Projects Relationship

**autofill-extension** and **basset-hound-browser** provide similar functionality but serve different user needs:

| Aspect | autofill-extension | basset-hound-browser |
|--------|-------------------|---------------------|
| **Deployment** | Chrome Web Store install | Standalone Electron app |
| **User type** | Quick-start users | Power users |
| **Customization** | Limited by Chrome APIs | Fully customizable |
| **Control** | Subject to Chrome restrictions | Full open-source control |
| **Use case** | Get up and running fast | Deep configuration, boutique setups |

Both projects are developed in parallel and expose similar MCP tools to AI agents.

---

## Proposed Feature Roadmap

### Phase 37: Entity Type Expansion

**Goal:** Expand entity types to support comprehensive OSINT investigations.

| New Entity Type | Description | Use Case |
|-----------------|-------------|----------|
| **GOVERNMENT_ENTITY** | Agencies, departments, regulatory bodies | Jurisdiction tracking, inter-agency relationships |
| **SOCIAL_GROUP** | Religious, tribal, community organizations | Group dynamics, membership analysis |
| **PHYSICAL_INFRASTRUCTURE** | Buildings, roads, utilities, facilities | Physical attack surface analysis |
| **DIGITAL_INFRASTRUCTURE** | Websites, servers, APIs, online services | Digital attack surface, hosting relationships |

**Rationale:**
- A company can operate across multiple physical infrastructures
- Multiple companies can share digital infrastructure (cloud hosting)
- Same entity name may exist as both COMPANY and DIGITAL_INFRASTRUCTURE
- Enables clearer attack vector analysis

**Implementation Tasks:**
- [ ] Extend EntityType enum in `api/models/entity_types.py`
- [ ] Add sections to `data_config.yaml` for each new type
- [ ] Create relationship types for infrastructure connections
- [ ] Update UI entity type selector
- [ ] Add tests for new entity types

### Phase 38: Sock Puppet / Undercover Identity Management

**Goal:** Support law enforcement sock puppet account management.

**Background:** Based on industry research from [SANS Institute](https://www.sans.org/blog/what-are-sock-puppets-in-osint) and [SockPuppet.io](https://www.sockpuppet.io/), sock puppets are fictitious online personas used by OSINT investigators for:
- Accessing information requiring authentication
- Passive surveillance without identity exposure
- Infiltrating closed communities

**New Entity Subtype: SOCK_PUPPET (extends PERSON)**

```yaml
sections:
  - id: cover_identity
    fields: [alias_name, backstory, cover_story, nationality, occupation_cover]
  - id: operational
    fields: [handler_id, operation_id, created_date, burn_date, status, budget]
  - id: platform_accounts
    fields: [platform, username, email, password_encrypted, 2fa_seed, recovery_codes]
  - id: attribution_config
    fields: [fingerprint_profile_id, proxy_config, browser_profile_id, phone_number]
  - id: activity_log
    fields: [last_active, total_posts, connections_made, incidents]
```

**New Relationship Types:**
- `HANDLER_OF` / `HANDLED_BY` - Agent to sock puppet
- `COVER_FOR` - Sock puppet to real identity
- `OPERATION_TARGET` - Linking to investigation targets
- `USED_ON_PLATFORM` - Sock puppet to platform entity

**Implementation Tasks:**
- [ ] Create SOCK_PUPPET entity subtype
- [ ] Implement encrypted credential storage
- [ ] Add handler assignment workflow
- [ ] Create burn date tracking and alerts
- [ ] Integrate with basset-hound-browser profiles
- [ ] Add operation/objective linking
- [ ] Implement activity logging

### Phase 39: Enhanced Evidence Chain of Custody

**Goal:** Meet law enforcement evidence management standards.

**Industry Reference:** Based on [Axon Evidence](https://www.axon.com/resources/digital-evidence-management-guide) and [Kaseware](https://www.kaseware.com/evidence-management).

**New Models:**

```python
class EvidenceChainEntry:
    timestamp: datetime
    user_id: str
    action: Literal["created", "viewed", "modified", "exported", "shared", "deleted"]
    ip_address: str
    device_fingerprint: str
    hash_before: Optional[str]
    hash_after: Optional[str]
    notes: str

class ForensicMetadata:
    file_hash_md5: str
    file_hash_sha256: str
    acquisition_method: str
    acquisition_tool: str
    examiner_id: str
    case_number: str
    exhibit_number: str
    court_jurisdiction: str
```

**Implementation Tasks:**
- [ ] Extend DataProvenance with EvidenceChainEntry
- [ ] Add ForensicMetadata to file attachments
- [ ] Implement hash verification on every access
- [ ] Create audit log export for court proceedings
- [ ] Add CJIS compliance headers
- [ ] Implement evidence integrity verification API

### Phase 40: MCP Server Enhancement for AI Integration ✅ COMPLETED (2026-01-08)

**Goal:** Full MCP protocol support for AI agent integration via palletai.

**Completed Implementation:**

**New Tool Modules Created:**

1. **Orphan Tools (`basset_mcp/tools/orphans.py`)** - 11 tools
   - `create_orphan`, `create_orphan_batch` - Create orphan data
   - `get_orphan`, `list_orphans`, `search_orphans` - Query orphans
   - `link_orphan`, `link_orphan_batch` - Link to entities
   - `update_orphan`, `delete_orphan` - CRUD operations
   - `find_duplicate_orphans`, `count_orphans` - Analysis

2. **Provenance Tools (`basset_mcp/tools/provenance.py`)** - 8 tools
   - `get_source_types`, `get_capture_methods`, `get_verification_states`
   - `record_entity_provenance`, `record_field_provenance`
   - `get_entity_provenance`, `update_verification_state`
   - `create_provenance_record`

3. **Enhanced Entity Tools**
   - `query_entities` - Flexible filtering with date ranges, field existence, relationships

4. **Enhanced Analysis Tools**
   - `get_entity_graph` - Export graph in standard, adjacency, or Cytoscape.js format

**Tool Count:** 54 total MCP tools (was 33, added 21)

**Test Coverage:** 25 tests in `tests/test_mcp_enhanced_tools.py`

**Documentation:** `docs/findings/MCP-ENHANCEMENT-2026-01-08.md`

**Tasks Completed:**
- [x] Add orphan data management tools (11 tools)
- [x] Add provenance tracking tools (8 tools)
- [x] Enhance entity query capabilities (query_entities)
- [x] Add graph export tool (get_entity_graph with 3 formats)
- [x] Register new modules in tools/__init__.py
- [x] Create comprehensive test suite
- [x] Document implementation findings

### Phase 40.5: Remaining MCP Tools ✅ COMPLETED (2026-01-08)

**Goal:** Complete MCP tool coverage for OSINT investigation workflows.

**Completed Implementation:**

1. **Sock Puppet Tools (`basset_mcp/tools/sock_puppets.py`)** - 15 tools
   - CRUD: `create_sock_puppet`, `get_sock_puppet`, `list_sock_puppets`
   - Lifecycle: `activate_sock_puppet`, `deactivate_sock_puppet`, `burn_sock_puppet`, `retire_sock_puppet`
   - Platform accounts: `add_platform_account`, `update_platform_account`
   - Operations: `record_puppet_activity`, `assign_handler`, `get_puppet_activity_log`, `assess_puppet_risk`

   **Design Note:** Stores metadata/references only - actual credentials should be in external password managers (KeePass, HashiCorp Vault). This is intentional for security.

2. **Verification Tools (`basset_mcp/tools/verification.py`)** - 12 tools
   - Generic: `get_verification_types`, `verify_identifier`, `batch_verify`
   - Specific: `verify_email`, `verify_phone`, `verify_domain`, `verify_ip`, `verify_url`, `verify_username`
   - Crypto: `verify_crypto`, `get_all_crypto_matches`, `get_supported_cryptocurrencies`

**Tool Count:** 81 total MCP tools (was 54, added 27)

**Test Coverage:** 28 tests in `tests/test_mcp_sock_puppets_verification.py`

**Documentation:** `docs/findings/MCP-PHASE40.5-2026-01-08.md`

**Entity Type Visualization (documented for future implementation):**
- PERSON: `#4A90D9` (blue)
- SOCK_PUPPET: `#9B59B6` (purple)
- COMPANY: `#27AE60` (green)
- ORGANIZATION: `#E67E22` (orange)

### Phase 40.6: Investigation Management Tools ✅ COMPLETED (2026-01-08)

**Goal:** Complete case management capabilities for law enforcement and OSINT workflows.

**Completed Implementation:**

| Tool | Description |
|------|-------------|
| `create_investigation` | Initialize project as investigation |
| `get_investigation` | Retrieve investigation details with stats |
| `update_investigation` | Update investigation properties |
| `set_investigation_status` | Change investigation status |
| `advance_investigation_phase` | Move to next phase with milestone |
| `close_investigation` | Close with final disposition |
| `add_investigation_subject` | Add entity as investigation subject |
| `update_subject_role` | Update subject's role/priority |
| `clear_subject` | Mark subject as not involved |
| `list_investigation_subjects` | List subjects with filtering |
| `create_investigation_task` | Create investigation task |
| `complete_investigation_task` | Mark task as completed |
| `list_investigation_tasks` | List tasks with filtering |
| `log_investigation_activity` | Log custom audit activity |
| `get_investigation_activity_log` | Get audit log with filtering |
| `list_investigations` | List all investigations across projects |

**Investigation Lifecycle:**
- 10 status values (intake, planning, active, pending_info, pending_review, on_hold, closed_resolved, closed_unfounded, closed_referred, reopened)
- 8 OSINT phases (identification, acquisition, authentication, analysis, preservation, validation, reporting, closure)
- 10 subject roles (target, subject, suspect, witness, victim, informant, complainant, associate, handler, undercover)

**Compliance Features:**
- Full audit trail for CJIS compliance
- Chain of custody integration with provenance tools
- Access control via confidentiality levels
- Formal case disposition documentation

**Updated Tool Count:** 99 MCP tools total (+17 investigation tools, +1 visualization tool)

**Documentation:** `docs/findings/MCP-PHASE40.6-2026-01-08.md`

**Entity Type Detection Implemented:**
- [x] `get_entity_type_schema` tool - Returns visualization schema for all entity types
- [x] `detect_entity_type()` function - Detects PERSON, SOCK_PUPPET, COMPANY, ORGANIZATION
- [x] Graph export includes `entity_type`, `color`, and `icon` for each node
- [x] 8 new tests for entity type detection

**Total Test Coverage:** 98 MCP tests (1 skipped for IPv6)

### Phase 41: Browser Integration APIs ✅ COMPLETED (2026-01-08)

**Goal:** Provide MCP tools for autofill-extension and basset-hound-browser integration.

**Completed Implementation:**

| Tool Category | Tools | Description |
|--------------|-------|-------------|
| **Autofill Data** | 2 | `get_autofill_data`, `suggest_form_mapping` |
| **Evidence Capture** | 4 | `capture_evidence`, `get_evidence`, `list_evidence`, `verify_evidence_integrity` |
| **Sock Puppet Profile** | 1 | `get_sock_puppet_profile` |
| **Browser Session** | 4 | `register_browser_session`, `update_browser_session`, `end_browser_session`, `get_investigation_context` |
| **Total** | **13** | Browser integration tools |

**Key Features:**
- Form field to entity path mapping with confidence scores
- Evidence storage with SHA-256 hashing and chain of custody
- Sock puppet profile retrieval (metadata only, not credentials)
- Browser session tracking across investigations
- Investigation context for AI agent decision-making

**Evidence Types Supported:**
- screenshot, page_archive, network_har, dom_snapshot
- console_log, cookies, local_storage, metadata

**Tool Count:** 112 MCP tools total (+13 browser integration)

**Test Coverage:** 45 tests in `tests/test_mcp_browser_integration.py`

**Full MCP Test Suite:** 143 passed, 1 skipped

**Documentation:**
- `docs/findings/MCP-PHASE41-2026-01-08.md` - Phase 41 implementation
- `docs/findings/INTEGRATION-BROWSER-APIS-2026-01-08.md` - Integration master doc
- Integration docs copied to autofill-extension, basset-hound-browser, palletai

**External Repository Integration:**
- autofill-extension: Phases 14-16 added to roadmap
- basset-hound-browser: Phases 19-21 added to roadmap
- palletai: Phases 15-17 added to roadmap

---

### Phase 42: Verification Migration to basset-verify ✅ COMPLETED (2026-01-09)

**Goal:** Extract verification services into standalone basset-verify package for modularity and reusability.

**Migration Summary:**
- Moved 12 verification MCP tools from basset-hound to basset-verify package
- Verification services (email, phone, crypto, domain, IP) now in separate package
- basset-hound maintains core entity/relationship management
- Clean separation of concerns: data management vs. verification logic

**Tools Migrated to basset-verify:**
- `verify_email` - Email deliverability verification
- `verify_phone` - Phone number validity and carrier lookup
- `verify_crypto_address` - Cryptocurrency address validation
- `verify_domain` - Domain registration and DNS verification
- `verify_ip` - IP geolocation and reputation checking
- `verify_username` - Social media username verification
- `verify_all_identifiers` - Batch verification of entity identifiers
- `get_verification_history` - Verification audit trail
- `get_verification_stats` - Verification statistics
- `get_verifiable_fields` - List of verifiable field types
- `recheck_verification` - Re-verify previously checked identifier
- `clear_verification_cache` - Cache management

**Tool Count Changes:**
- **Before Phase 42:** 112 MCP tools
- **After Phase 42:** 100 MCP tools (-12 verification tools migrated)

**basset-verify Package:**
- Independent PyPI package with its own MCP server
- Can be used standalone or integrated with basset-hound
- Documentation: `basset-verify/README.md`
- Installation: `pip install basset-verify`

**Integration:**
- basset-hound can optionally use basset-verify as dependency
- Verification results stored in Neo4j as before
- Clean API boundary between packages

**Documentation:**
- Phase 42 planning: `docs/findings/PHASE42-VERIFICATION-MIGRATION-2026-01-09.md`

---

### Phase 43: Smart Suggestions & Data Matching 🔄 IN PROGRESS (2026-01-09)

**Goal:** Intelligent suggestion system to help human operators identify potential matches, duplicates, and related data across entities and orphan data.

**Status:** Phase 43 Planning Complete - Ready for Implementation

**Timeline:** 5 weeks (6 sub-phases: 43.1 through 43.6)

**Core Principle:** Suggest possible matches based on data analysis (hashes, exact matches, partial matches), but **always require human verification** before linking.

#### Overview

The Smart Suggestions system will:
- **Suggest** entities that might be related based on shared data
- **Detect** potential duplicates using hash-based matching
- **Highlight** orphan data that matches entity data
- **Assist** with deduplication while preventing false positives
- **Never auto-link** - all suggestions require human operator approval

#### Implementation Sub-Phases

**Phase 43.1: Data ID System (Week 1)**
- Create `DataItem` model for all entity data
- Create `(:DataItem)` node type in Neo4j
- Migrate existing entity attributes to DataItem nodes
- Generate unique IDs for all data: `data_abc123`
- Add `[:HAS_DATA]` relationships

**Phase 43.2: Hash Computation (Week 2)**
- Create `FileHashService` class
- Compute SHA-256 for uploaded images/documents
- Store hashes in DataItem.hash field
- Add hash verification for evidence integrity

**Phase 43.3: Matching Engine (Week 2-3)**
- Create `MatchingEngine` class
- Implement exact hash matching (1.0 confidence)
- Implement exact string matching for email, phone, crypto (0.95 confidence)
- Implement partial string matching for names, addresses (0.3-0.9 confidence)
- Performance optimization with indexes

**Phase 43.4: Suggestion System (Week 3-4)**
- Create `Suggestion` model
- Compute suggestions on-demand when viewing entity profile
- Implement suggestion caching (5-minute TTL)
- User can dismiss irrelevant suggestions
- Store dismissed suggestions in user preferences

**Phase 43.5: Linking Actions (Week 4)**
- Accept suggestion and merge entities (same person)
- Accept suggestion and create relationship (KNOWS, WORKS_WITH, etc.)
- Link orphan data to entity based on suggestion
- Audit logging for all linking actions
- Prevent accidental merges with confirmation required

**Phase 43.6: Testing & Documentation (Week 5)**
- Unit tests for MatchingEngine
- Integration tests for suggestion flow
- Performance tests (10,000+ entities)
- Documentation for new MCP tools
- Update SCOPE.md and ROADMAP.md

#### New MCP Tools (8 tools)

| Tool | Description |
|------|-------------|
| `compute_file_hash` | Compute SHA-256 hash for uploaded file |
| `find_data_matches` | Find all matches for a data item |
| `get_entity_suggestions` | Get all suggestions for an entity profile |
| `dismiss_suggestion` | Dismiss a suggestion (user says "not related") |
| `accept_suggestion_merge` | Accept suggestion and merge entities |
| `accept_suggestion_link` | Accept suggestion and create relationship |
| `link_orphan_to_entity` | Link orphan data to entity based on suggestion |
| `list_dismissed_suggestions` | Show user's dismissed suggestions |

#### Data Types for Matching

**Hash-Based Matching (Exact - 1.0 confidence):**
- Images (JPEG, PNG, GIF, WebP)
- Documents (PDF, DOCX, TXT)
- Evidence files (screenshots, archives)
- SHA-256 for all files

**Exact String Matching (0.95 confidence):**
- Email addresses
- Phone numbers (normalized to E.164)
- Cryptocurrency addresses
- URLs (normalized)
- Social media handles
- IP addresses

**Partial/Fuzzy Matching (0.3-0.9 confidence):**
- Full name matches
- Partial name matches
- Name variations (nickname detection)
- Exact address vs. partial address (different cities)

#### Use Cases

**Image Hash Matching:**
Investigator uploads profile photo for Entity A. System computes SHA-256 hash and finds match with Entity B. Suggestion shown: "This image matches Entity B (ID: ent_456)". Human operator decides whether to merge entities, create relationship, or ignore.

**Shared Email Address:**
Entity A has email "support@company.com", Entity B also has same email. System shows suggestion. Human operator decides if it's same person, shared corporate email, or working for same company.

**Orphan Data Matching:**
Orphan email "john@example.com" exists. Entity A is created with same email. System suggests linking orphan to entity. Human operator confirms or keeps separate.

#### Tool Count Changes

- **Before Phase 43:** 100 MCP tools
- **After Phase 43:** 108 MCP tools (+8 smart suggestion tools)

#### Success Criteria

Phase 43 is successful if:
1. Every piece of data has a unique ID (data_xxx)
2. All uploaded files have SHA-256 hashes
3. Matching engine finds exact hash matches (1.0 confidence)
4. Matching engine finds exact string matches (0.95 confidence)
5. Matching engine finds partial name/address matches (0.3-0.9 confidence)
6. Entity profiles show suggested matches
7. Human operators can view, link, or dismiss suggestions
8. Dismissed suggestions are hidden
9. All linking actions are logged (audit trail)
10. Performance: <500ms to compute suggestions for entity with 100 data items

**Documentation:**
- Phase 43 planning: `docs/findings/SMART-SUGGESTIONS-PLANNING-2026-01-09.md`

---

### Phase 44: Future Enhancements 📋 PLANNED

**Status:** TBD based on Phase 43 results

**Potential Focus Areas:**
- Advanced fuzzy string matching with Levenshtein distance
- Nickname detection ("Robert" → "Bob")
- Company name variations ("Inc" vs "Incorporated")
- Machine learning for pattern detection
- Bulk deduplication operations
- Enhanced anomaly detection

**Tool Count:** TBD (depends on features selected)

---

## Database Architecture Notes

### Current: Neo4j 5.28.1

**Strengths:**
- Native graph traversal for relationship analysis
- ACID compliance for data integrity
- Cypher query language well-suited for investigations
- Graph Data Science library for entity resolution

**Performance Considerations:**
Based on research from [DataWalk](https://datawalk.com/neo4jalternative/) and [Memgraph](https://memgraph.com/blog/neo4j-alternative-what-are-my-open-source-db-options):
- Population-level queries can be slow
- Consider Memgraph (8x faster reads, 50x faster writes) for high-throughput scenarios
- For billions of entities, consider NebulaGraph or JanusGraph + ScyllaDB

**Recommendation:** Stay with Neo4j unless scaling to billions of entities. Focus on:
- Proper indexing strategies
- Query optimization
- Caching layer (Redis) for frequent queries

---

## Documentation References

See [VISION-RESEARCH-2026-01-08.md](docs/findings/VISION-RESEARCH-2026-01-08.md) for comprehensive research on:
- Sock puppet management best practices
- Evidence chain of custody standards
- Database architecture comparisons
- Browser fingerprinting techniques
- MCP integration patterns
