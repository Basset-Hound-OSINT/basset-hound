# Basset Hound Development Roadmap

## Project Vision & Scope Clarification

### What Basset Hound IS

**Basset Hound is a configurable entity relationship management system** designed for:

1. **OSINT Investigations** - Original use case for tracking people, organizations, and their connections
2. **Generic Entity Relationship Management** - Extensible to ANY domain requiring relationship tracking
3. **Rapid Data Ingestion API** - Fast storage of structured information with custom schemas
4. **Graph-Based Analysis** - Leveraging Neo4j for complex relationship queries and traversal

### Core Value Proposition

> **"Configure once, relate anything"** - Define custom entity types with arbitrary identifiers, then track relationships between them using a graph database.

This differs from a traditional database because:
- **Schema is runtime-configurable** via YAML, not code changes
- **Relationships are first-class citizens** with bidirectional and transitive support
- **Identifiers are domain-specific** - any field can become an identifier
- **File attachments and reports** are integrated directly with entities

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

## Implementation Status (Updated: 2025-12-27)

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

### Next Steps (Phase 9+)

1. **UI for Multi-Entity Types** - Frontend support for creating/viewing different entity types
2. **Graph Visualization Enhancements** - Visual display of cross-project links, timeline view
3. **Real-time Notifications** - WebSocket support for live updates
4. **Report Scheduling** - Automated report generation
5. **Custom Report Templates** - User-defined templates
6. **Search Analytics** - Track popular queries, improve relevance
