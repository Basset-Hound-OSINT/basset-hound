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

### Proposed Comprehensive `data_config.yaml`

The current schema is good but limited. Here's a comprehensive expansion:

```yaml
# data_config.yaml - Comprehensive Entity Configuration
version: "2.0"
entity_type: Person  # Future: support multiple entity types

# =============================================================================
# SECTION DEFINITIONS
# =============================================================================
sections:

  # ---------------------------------------------------------------------------
  # PROFILE PICTURE
  # ---------------------------------------------------------------------------
  - id: profile_picture
    name: Profile Picture
    icon: fa-user-circle
    fields:
      - id: profile_photo
        type: file
        accept: image/*
        description: Primary profile photograph

  # ---------------------------------------------------------------------------
  # CORE IDENTITY
  # ---------------------------------------------------------------------------
  - id: core_identity
    name: Personal Information
    icon: fa-id-card
    fields:
      - id: name
        type: component
        multiple: true
        label: Full Name
        components:
          - id: first_name
            type: string
            required: true
          - id: middle_name
            type: string
          - id: last_name
            type: string
          - id: suffix
            type: string
            placeholder: "Jr., Sr., III, etc."

      - id: alias
        type: string
        multiple: true
        label: Known Aliases / Nicknames
        searchable: true

      - id: date_of_birth
        type: date
        multiple: true
        label: Date of Birth

      - id: gender
        type: select
        options: ["Male", "Female", "Non-binary", "Other", "Unknown"]

      - id: nationality
        type: string
        multiple: true
        label: Nationality / Citizenship

      - id: summary
        type: comment
        multiple: true
        label: Notes / Summary

  # ---------------------------------------------------------------------------
  # CONTACT INFORMATION
  # ---------------------------------------------------------------------------
  - id: contact
    name: Contact Information
    icon: fa-address-book
    fields:
      - id: email
        type: email
        multiple: true
        label: Email Addresses
        searchable: true
        identifier: true  # Can be used to link entities

      - id: phone
        type: component
        multiple: true
        label: Phone Numbers
        components:
          - id: number
            type: phone
          - id: type
            type: select
            options: ["Mobile", "Home", "Work", "Fax", "Other"]
          - id: country_code
            type: string
            placeholder: "+1"

      - id: address
        type: component
        multiple: true
        label: Physical Addresses
        components:
          - id: street
            type: string
          - id: city
            type: string
          - id: state
            type: string
          - id: postal_code
            type: string
          - id: country
            type: string
          - id: type
            type: select
            options: ["Home", "Work", "Other"]

  # ---------------------------------------------------------------------------
  # SOCIAL MEDIA - MAJOR PLATFORMS
  # ---------------------------------------------------------------------------
  - id: social_major
    name: Major Social Platforms
    icon: fa-share-alt
    fields:
      - id: facebook
        type: component
        multiple: true
        label: Facebook
        platform_url: https://facebook.com/{username}
        components:
          - id: url
            type: url
          - id: username
            type: string
          - id: display_name
            type: string
          - id: user_id
            type: string
            label: Facebook User ID

      - id: instagram
        type: component
        multiple: true
        label: Instagram
        platform_url: https://instagram.com/{username}
        components:
          - id: url
            type: url
          - id: username
            type: string
            identifier: true
          - id: display_name
            type: string

      - id: twitter_x
        type: component
        multiple: true
        label: Twitter / X
        platform_url: https://x.com/{handle}
        components:
          - id: url
            type: url
          - id: handle
            type: string
            identifier: true
          - id: display_name
            type: string
          - id: user_id
            type: string

      - id: tiktok
        type: component
        multiple: true
        label: TikTok
        platform_url: https://tiktok.com/@{username}
        components:
          - id: url
            type: url
          - id: username
            type: string
          - id: display_name
            type: string

      - id: youtube
        type: component
        multiple: true
        label: YouTube
        components:
          - id: channel_url
            type: url
          - id: channel_name
            type: string
          - id: channel_id
            type: string

      - id: snapchat
        type: component
        multiple: true
        label: Snapchat
        components:
          - id: username
            type: string

  # ---------------------------------------------------------------------------
  # PROFESSIONAL NETWORKS
  # ---------------------------------------------------------------------------
  - id: professional
    name: Professional Networks
    icon: fa-briefcase
    fields:
      - id: linkedin
        type: component
        multiple: true
        label: LinkedIn
        platform_url: https://linkedin.com/in/{username}
        components:
          - id: url
            type: url
          - id: username
            type: string
          - id: headline
            type: string
          - id: company
            type: string
          - id: email
            type: email
            multiple: true

      - id: github
        type: component
        multiple: true
        label: GitHub
        platform_url: https://github.com/{username}
        components:
          - id: url
            type: url
          - id: username
            type: string
            identifier: true
          - id: email
            type: email

      - id: gitlab
        type: component
        multiple: true
        label: GitLab
        platform_url: https://gitlab.com/{username}
        components:
          - id: url
            type: url
          - id: username
            type: string

      - id: bitbucket
        type: component
        multiple: true
        label: Bitbucket
        components:
          - id: url
            type: url
          - id: username
            type: string

      - id: stackoverflow
        type: component
        multiple: true
        label: Stack Overflow
        components:
          - id: url
            type: url
          - id: user_id
            type: string
          - id: display_name
            type: string

      - id: behance
        type: component
        multiple: true
        label: Behance
        components:
          - id: url
            type: url
          - id: username
            type: string

      - id: dribbble
        type: component
        multiple: true
        label: Dribbble
        components:
          - id: url
            type: url
          - id: username
            type: string

  # ---------------------------------------------------------------------------
  # FEDERATED / DECENTRALIZED SOCIAL
  # ---------------------------------------------------------------------------
  - id: federated_social
    name: Federated / Decentralized
    icon: fa-globe
    fields:
      - id: mastodon
        type: component
        multiple: true
        label: Mastodon
        components:
          - id: full_handle
            type: string
            placeholder: "@user@instance.social"
            identifier: true
          - id: instance_url
            type: url
          - id: profile_url
            type: url

      - id: bluesky
        type: component
        multiple: true
        label: Bluesky
        platform_url: https://bsky.app/profile/{handle}
        components:
          - id: handle
            type: string
            placeholder: "user.bsky.social"
            identifier: true
          - id: did
            type: string
            label: Decentralized ID (DID)

      - id: threads
        type: component
        multiple: true
        label: Threads (Meta)
        platform_url: https://threads.net/@{username}
        components:
          - id: url
            type: url
          - id: username
            type: string

      - id: nostr
        type: component
        multiple: true
        label: Nostr
        components:
          - id: npub
            type: string
            label: Public Key (npub)
            identifier: true
          - id: nip05
            type: string
            label: NIP-05 Identifier

      - id: lemmy
        type: component
        multiple: true
        label: Lemmy
        components:
          - id: full_handle
            type: string
            placeholder: "@user@instance.ml"
          - id: instance_url
            type: url

      - id: pixelfed
        type: component
        multiple: true
        label: Pixelfed
        components:
          - id: full_handle
            type: string
          - id: instance_url
            type: url

      - id: peertube
        type: component
        multiple: true
        label: PeerTube
        components:
          - id: channel_url
            type: url
          - id: username
            type: string
          - id: instance
            type: string

  # ---------------------------------------------------------------------------
  # REDDIT & FORUMS
  # ---------------------------------------------------------------------------
  - id: forums
    name: Forums & Communities
    icon: fa-comments
    fields:
      - id: reddit
        type: component
        multiple: true
        label: Reddit
        platform_url: https://reddit.com/user/{username}
        components:
          - id: username
            type: string
            identifier: true
          - id: url
            type: url

      - id: hackernews
        type: component
        multiple: true
        label: Hacker News
        platform_url: https://news.ycombinator.com/user?id={username}
        components:
          - id: username
            type: string

      - id: discord
        type: component
        multiple: true
        label: Discord
        components:
          - id: username
            type: string
            placeholder: "username#0000 or new username"
          - id: user_id
            type: string
            label: Discord User ID

      - id: slack
        type: component
        multiple: true
        label: Slack Workspaces
        components:
          - id: workspace
            type: string
          - id: display_name
            type: string
          - id: email
            type: email

      - id: telegram
        type: component
        multiple: true
        label: Telegram
        platform_url: https://t.me/{username}
        components:
          - id: username
            type: string
          - id: phone
            type: phone

      - id: keybase
        type: component
        multiple: true
        label: Keybase
        platform_url: https://keybase.io/{username}
        components:
          - id: username
            type: string

  # ---------------------------------------------------------------------------
  # GAMING & ENTERTAINMENT
  # ---------------------------------------------------------------------------
  - id: gaming
    name: Gaming & Entertainment
    icon: fa-gamepad
    fields:
      - id: steam
        type: component
        multiple: true
        label: Steam
        components:
          - id: profile_url
            type: url
          - id: username
            type: string
          - id: steam_id
            type: string

      - id: xbox
        type: component
        multiple: true
        label: Xbox / Microsoft
        components:
          - id: gamertag
            type: string

      - id: playstation
        type: component
        multiple: true
        label: PlayStation
        components:
          - id: psn_id
            type: string

      - id: nintendo
        type: component
        multiple: true
        label: Nintendo
        components:
          - id: friend_code
            type: string
          - id: username
            type: string

      - id: twitch
        type: component
        multiple: true
        label: Twitch
        platform_url: https://twitch.tv/{username}
        components:
          - id: url
            type: url
          - id: username
            type: string

      - id: spotify
        type: component
        multiple: true
        label: Spotify
        components:
          - id: profile_url
            type: url
          - id: username
            type: string

      - id: soundcloud
        type: component
        multiple: true
        label: SoundCloud
        components:
          - id: url
            type: url
          - id: username
            type: string

  # ---------------------------------------------------------------------------
  # DATING & PERSONAL
  # ---------------------------------------------------------------------------
  - id: dating
    name: Dating & Personal
    icon: fa-heart
    fields:
      - id: tinder
        type: component
        multiple: true
        label: Tinder
        components:
          - id: profile_id
            type: string

      - id: bumble
        type: component
        multiple: true
        label: Bumble
        components:
          - id: profile_id
            type: string

      - id: hinge
        type: component
        multiple: true
        label: Hinge
        components:
          - id: profile_id
            type: string

      - id: okcupid
        type: component
        multiple: true
        label: OkCupid
        components:
          - id: username
            type: string
          - id: url
            type: url

  # ---------------------------------------------------------------------------
  # FINANCIAL & CRYPTO
  # ---------------------------------------------------------------------------
  - id: financial
    name: Financial & Crypto
    icon: fa-wallet
    fields:
      - id: venmo
        type: component
        multiple: true
        label: Venmo
        components:
          - id: username
            type: string

      - id: paypal
        type: component
        multiple: true
        label: PayPal
        components:
          - id: email
            type: email
          - id: paypal_me
            type: url

      - id: cashapp
        type: component
        multiple: true
        label: Cash App
        components:
          - id: cashtag
            type: string
            placeholder: "$username"

      - id: ethereum_address
        type: string
        multiple: true
        label: Ethereum Addresses
        identifier: true

      - id: bitcoin_address
        type: string
        multiple: true
        label: Bitcoin Addresses
        identifier: true

  # ---------------------------------------------------------------------------
  # TECHNICAL IDENTIFIERS
  # ---------------------------------------------------------------------------
  - id: technical
    name: Technical Identifiers
    icon: fa-server
    fields:
      - id: ip_address
        type: ip_address
        multiple: true
        label: IP Addresses
        searchable: true
        identifier: true

      - id: mac_address
        type: string
        multiple: true
        label: MAC Addresses
        pattern: "^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$"

      - id: domain
        type: string
        multiple: true
        label: Owned Domains
        identifier: true

      - id: pgp_key
        type: component
        multiple: true
        label: PGP / GPG Keys
        components:
          - id: fingerprint
            type: string
          - id: key_id
            type: string
          - id: key_server_url
            type: url

      - id: ssh_key
        type: comment
        multiple: true
        label: SSH Public Keys

      - id: user_agent
        type: string
        multiple: true
        label: Known User Agents

  # ---------------------------------------------------------------------------
  # DEVICES & HARDWARE
  # ---------------------------------------------------------------------------
  - id: devices
    name: Devices & Hardware
    icon: fa-mobile-alt
    fields:
      - id: phone_device
        type: component
        multiple: true
        label: Phone Devices
        components:
          - id: brand
            type: string
          - id: model
            type: string
          - id: imei
            type: string
          - id: phone_number
            type: phone

      - id: computer
        type: component
        multiple: true
        label: Computers
        components:
          - id: type
            type: select
            options: ["Desktop", "Laptop", "Tablet", "Server"]
          - id: os
            type: string
          - id: hostname
            type: string

  # ---------------------------------------------------------------------------
  # EMPLOYMENT & EDUCATION
  # ---------------------------------------------------------------------------
  - id: employment
    name: Employment & Education
    icon: fa-graduation-cap
    fields:
      - id: employer
        type: component
        multiple: true
        label: Employment History
        components:
          - id: company
            type: string
          - id: title
            type: string
          - id: start_date
            type: date
          - id: end_date
            type: date
          - id: work_email
            type: email
          - id: location
            type: string

      - id: education
        type: component
        multiple: true
        label: Education
        components:
          - id: institution
            type: string
          - id: degree
            type: string
          - id: field
            type: string
          - id: graduation_year
            type: number

  # ---------------------------------------------------------------------------
  # CREDENTIALS (SENSITIVE)
  # ---------------------------------------------------------------------------
  - id: credentials
    name: Credentials
    icon: fa-key
    sensitive: true
    fields:
      - id: password
        type: password
        multiple: true
        label: Known Passwords
        encrypted: true

      - id: password_hash
        type: string
        multiple: true
        label: Password Hashes

      - id: security_questions
        type: component
        multiple: true
        label: Security Questions
        components:
          - id: question
            type: string
          - id: answer
            type: password

  # ---------------------------------------------------------------------------
  # FILES & DOCUMENTS
  # ---------------------------------------------------------------------------
  - id: files
    name: Files & Documents
    icon: fa-folder-open
    fields:
      - id: document
        type: file
        multiple: true
        label: Documents

      - id: screenshot
        type: file
        multiple: true
        label: Screenshots
        accept: image/*

      - id: evidence
        type: component
        multiple: true
        label: Evidence Files
        components:
          - id: file
            type: file
          - id: description
            type: comment
          - id: source
            type: string
          - id: date_obtained
            type: date

# =============================================================================
# FIELD TYPE DEFINITIONS (for reference and validation)
# =============================================================================
field_types:
  string:
    html_input: text
  email:
    html_input: email
    pattern: "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
  url:
    html_input: url
    pattern: "^https?://"
  date:
    html_input: date
  number:
    html_input: number
  phone:
    html_input: tel
  password:
    html_input: password
    encrypted: true
  comment:
    html_input: textarea
  file:
    html_input: file
  select:
    html_input: select
  ip_address:
    html_input: text
    pattern: "^(?:[0-9]{1,3}\\.){3}[0-9]{1,3}$|^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$"
  component:
    html_input: fieldset
```

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

### Next Steps (Phase 4+)

1. **Caching** - Redis integration for query caching
2. **Multi-Entity Types** - Organizations, locations, devices
3. **Frontend Crypto Ticker Display** - Show detected coin ticker next to crypto input fields
4. **Cross-Project Linking** - Link entities across different projects
5. **Fuzzy Matching** - Similar names, typo tolerance for auto-linking
6. **Timeline Analysis** - Relationship changes over time
