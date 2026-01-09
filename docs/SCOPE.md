# basset-hound Scope Definition

**Version:** 2.0 (Post-Phase 41 Clarification)
**Date:** 2026-01-09
**Status:** Active

---

## Purpose

basset-hound is an **intelligence management system** for OSINT investigations. It provides structured storage, relationship mapping, investigation tracking, and reporting through a Neo4j graph database and MCP server interface.

**Core Mission**: Store and manage intelligence in highly configurable ways, enabling AI agents and investigators to organize, query, and analyze collected information.

---

## In Scope

### ✅ Intelligence Storage

**Entity Management**:
- ✅ Create, read, update, delete entities
- ✅ Flexible JSON schema with entity types (person, organization, location, etc.)
- ✅ Entity attribute storage (names, identifiers, profile data)
- ✅ Entity metadata (created_at, updated_at, confidence scores)
- ✅ Custom entity type definitions via schema configuration

**Relationship Management**:
- ✅ Link entities with typed relationships (KNOWS, WORKS_FOR, LOCATED_IN, etc.)
- ✅ Relationship properties (since, until, confidence, strength)
- ✅ Bidirectional relationship queries
- ✅ Transitive relationship discovery (friends-of-friends)
- ✅ Path finding between entities

**Identifiers**:
- ✅ Store email, phone, crypto addresses, domains, IPs, URLs, usernames
- ✅ Link identifiers to entities
- ✅ Handle unlinked identifiers as "orphan data"
- ✅ Batch import of identifiers
- ✅ Identifier deduplication

### ✅ Investigation Management

**Investigations**:
- ✅ Create and manage investigation cases
- ✅ Investigation lifecycle (open, active, suspended, closed, archived)
- ✅ Investigation priorities (low, medium, high, critical)
- ✅ Investigation types (fraud, counter_intel, due_diligence, threat_actor, etc.)
- ✅ Investigation subjects (target, suspect, witness, associate, victim)

**Tasks & Activity Logging**:
- ✅ Create investigation tasks with status tracking
- ✅ Log investigation activity with timestamps
- ✅ Activity types (evidence_collected, interview_conducted, lead_discovered, etc.)
- ✅ Activity search and filtering

**Timeline & Progress**:
- ✅ Investigation timeline generation
- ✅ Progress tracking (entities added, relationships discovered, evidence collected)
- ✅ Investigation context for AI agents

### ✅ Sock Puppet Management

**Sock Puppet Identities**:
- ✅ Create sock puppet profiles for undercover investigations
- ✅ Store alias names, backstory, target platforms
- ✅ Link sock puppets to investigations
- ✅ Platform-specific profile data (LinkedIn, Twitter, forums)
- ✅ Sock puppet activity logging

**Credentials Reference**:
- ✅ Store **references** to credentials (e.g., "stored in 1Password as 'puppet_linkedin_001'")
- ✅ Track credential rotation dates
- ❌ **DO NOT** store actual passwords or credentials in basset-hound

**Browser Integration**:
- ✅ Provide sock puppet profile data for form autofill (via MCP tools)
- ✅ Track sock puppet usage across investigations

### ✅ Orphan Data Management

**Unlinked Identifiers**:
- ✅ Store identifiers not yet linked to entities ("orphan data")
- ✅ Batch import of orphan identifiers
- ✅ Link orphan data to entities when matches found
- ✅ Orphan data search and filtering
- ✅ Automatic linking suggestions based on similarity

**Use Case**: Collect email addresses from web pages → store as orphans → link to entities later

### ✅ Provenance Tracking

**Data Sources**:
- ✅ Record data provenance (where information came from)
- ✅ Chain of custody for evidence
- ✅ Source reliability ratings
- ✅ Collection method tracking (web_scraping, public_record, social_media, etc.)

**Audit Trail**:
- ✅ Track who added/modified data
- ✅ Timestamp all changes
- ✅ Source attribution for every data point

### ✅ Evidence Storage

**Evidence Capture**:
- ✅ Store evidence submitted by basset-hound-browser
- ✅ Evidence types (screenshot, page_archive, network_har, dom_snapshot, etc.)
- ✅ SHA-256 hashing for integrity verification
- ✅ Chain of custody tracking
- ✅ Evidence metadata (URL, title, viewport, timestamp)

**Evidence Management**:
- ✅ Retrieve evidence by ID
- ✅ List evidence for investigation
- ✅ Verify evidence integrity (SHA-256 match)
- ✅ Link evidence to entities and investigations

### ✅ Graph Analysis

**Relationship Analysis**:
- ✅ Find paths between entities
- ✅ Centrality analysis (who is most connected?)
- ✅ Community detection (clusters of related entities)
- ✅ Relationship strength scoring
- ✅ Export graph for visualization (Gephi, Cytoscape)

**Visualization**:
- ✅ Export graph in standard formats (JSON, GraphML)
- ✅ Generate entity type schemas for UI rendering
- ✅ Subgraph extraction (entities within N hops)

### ✅ Search & Query

**Full-Text Search**:
- ✅ Search entities by name, identifier, attribute
- ✅ Search investigations by title, description
- ✅ Search orphan data by identifier value

**Structured Queries**:
- ✅ Filter entities by type, attribute, date range
- ✅ Filter relationships by type, strength, date range
- ✅ Cypher query support for advanced users

### ✅ Reports

**Report Generation**:
- ✅ Entity profile reports (with relationships and activity)
- ✅ Investigation summary reports
- ✅ Relationship network reports
- ✅ Timeline reports

**Export Formats**:
- ✅ JSON (machine-readable)
- ✅ Markdown (human-readable)
- ✅ Future: PDF, HTML

### ✅ Projects

**Project Management**:
- ✅ Create projects as data isolation boundaries
- ✅ All entities belong to a project
- ✅ Project-level permissions (future)
- ✅ Project metadata (name, description, created_at)

### ✅ MCP Server

**AI Agent Interface**:
- ✅ 100 MCP tools for entity/relationship/investigation management
- ✅ FastMCP server on port 8000
- ✅ Tool discovery and documentation
- ✅ Async/await support for long-running operations

### ✅ Browser Integration

**Autofill Data**:
- ✅ Provide entity data in flattened format for form filling
- ✅ Suggest form field mappings to entity paths
- ✅ Provide sock puppet profile data for autofill

**Browser Session Tracking**:
- ✅ Register browser sessions
- ✅ Track session activity (pages visited, evidence captured)
- ✅ End sessions with summary

### ✅ Smart Suggestions & Data Matching (Phase 43 - Future)

**Data-Level Identity**:
- ✅ Every piece of data gets unique ID (data_abc123)
- ✅ Hash-based file identification (SHA-256)
- ✅ Images, documents, evidence files tracked independently
- ✅ Data can exist without being linked to entities

**Intelligent Matching**:
- ✅ Exact hash matching (images, documents) - 1.0 confidence
- ✅ Exact string matching (email, phone, crypto) - 0.95 confidence
- ✅ Partial matching (names, addresses) - 0.3-0.9 confidence
- ✅ Cross-entity duplicate detection
- ✅ Orphan data to entity matching

**Suggestion System**:
- ✅ Show "Suggested Tags" section on entity profiles
- ✅ Suggest potential matches with confidence scores
- ✅ Human operator reviews and decides (view, link, dismiss)
- ✅ No automatic linking - always require human verification
- ✅ Dismissed suggestions hidden permanently
- ✅ Audit trail for all linking decisions

**Use Cases**:
- Same image appears in two entities → suggest possible duplicate
- Same email in entity and orphan data → suggest linking
- Partial address match → suggest but flag as low confidence
- Same document hash → highlight potential relationship

**Philosophy**: Assist human operators with intelligent suggestions, but never force deduplication or auto-link. Low-confidence matches (e.g., same street address but different cities) are suggested but easily dismissed.

---

## Out of Scope

### ❌ OSINT Automation

- ❌ Web scraping (use palletai agents + basset-hound-browser)
- ❌ Social media enumeration (use palletai agents)
- ❌ Username checking across platforms (use palletai agents)
- ❌ Automated data collection (use palletai agents)
- ❌ Scheduled scraping jobs (use palletai agents)

**Reason**: basset-hound is **intelligence management**, not OSINT automation. AI agents (palletai) perform tool automation and data collection. basset-hound stores the results.

### ❌ Identifier Verification

- ❌ Email verification (use basset-verify)
- ❌ Phone verification (use basset-verify)
- ❌ Crypto address detection (use basset-verify)
- ❌ Domain DNS lookups (use basset-verify)
- ❌ IP geolocation (use basset-verify - future)

**Reason**: Verification is a separate concern. basset-verify is a standalone microservice that basset-hound calls **optionally** when user clicks "Verify" button. basset-hound must work even if basset-verify is down (graceful degradation).

### ❌ Browser Automation

- ❌ Page navigation (use basset-hound-browser)
- ❌ Evidence capture (use basset-hound-browser)
- ❌ Form filling (use basset-hound-browser)
- ❌ Screenshot capture (use basset-hound-browser)
- ❌ Session management (use basset-hound-browser)
- ❌ Tor integration (use basset-hound-browser)

**Reason**: basset-hound-browser handles browser automation. basset-hound stores evidence submitted by the browser.

### ❌ AI Agent Orchestration

- ❌ Agent spawning (use palletai)
- ❌ Task planning (use palletai)
- ❌ Multi-agent coordination (use palletai)
- ❌ Tool automation (use palletai)
- ❌ Workflow execution (use palletai)

**Reason**: palletai handles AI agent orchestration. basset-hound provides the MCP server for agents to interact with.

### ❌ Real-Time Monitoring

- ❌ Social media monitoring
- ❌ Alert generation
- ❌ Notification systems
- ❌ Threat intelligence feeds

**Reason**: basset-hound is for **investigation management**, not real-time monitoring.

### ❌ Active Reconnaissance

- ❌ Port scanning
- ❌ Service fingerprinting
- ❌ Banner grabbing
- ❌ Vulnerability scanning
- ❌ Password cracking
- ❌ Exploit execution

**Reason**: basset-hound manages **collected intelligence**, it does not perform active reconnaissance.

### ❌ Credential Management

- ❌ Password storage (use 1Password, Bitwarden, KeePass)
- ❌ Credential encryption (use external vault)
- ❌ Credential rotation automation (use external vault)

**Reason**: Sock puppets store **references** to credentials ("stored in 1Password as 'puppet_001'"), not actual passwords. Specialized tools handle credential management better than basset-hound.

---

## Integration Architecture

### basset-hound ↔ basset-verify

**basset-hound calls basset-verify**:
- When user clicks "Verify" button on entity page
- For manual verification of specific identifiers
- For batch verification of orphan data (user-initiated)

**basset-hound stores results**:
- Verification status (verified, unverified, invalid)
- Confidence score (0.0 - 1.0)
- Verification timestamp
- Verification level (format, network)

**Graceful degradation**:
```python
try:
    result = await basset_verify_client.verify_email(email)
except ConnectionError:
    return {"status": "verification_unavailable"}
```

### basset-hound ↔ basset-hound-browser

**basset-hound-browser submits evidence**:
- Screenshots, page archives, network HAR, DOM snapshots
- SHA-256 hashes for integrity verification
- Metadata (URL, title, viewport, timestamp)

**basset-hound provides context**:
- Investigation details for browser decisions
- Sock puppet profiles for form autofill
- Known entities to highlight on page

**basset-hound tracks sessions**:
- Register browser sessions
- Track activity counters
- End sessions with summary

### basset-hound ↔ palletai

**AI agents use basset-hound**:
- Store collected intelligence via MCP tools
- Query entities and relationships
- Create investigation tasks
- Log activity

**basset-hound provides**:
- 100 MCP tools for intelligence management
- Investigation context for decision-making
- Entity/relationship graph for analysis

**AI agents perform automation**:
- Web scraping (palletai agents)
- Social media enumeration (palletai agents)
- Data collection (palletai agents)
- Tool orchestration (palletai agents)

### basset-hound ↔ autofill-extension

**Extension requests autofill data**:
- Flattened entity data for form filling
- Sock puppet profile data
- Form field mapping suggestions

**Extension submits collected data**:
- Identifiers extracted from forms
- Evidence captured from pages (via basset-hound-browser)

---

## Data Model

### Core Entities

**Entity Node**:
```cypher
(:Entity {
    id: string,
    project_id: string,
    entity_type: string,  // person, organization, location, etc.
    name: string,
    attributes: json,
    confidence: float,
    created_at: datetime,
    updated_at: datetime
})
```

**Relationship**:
```cypher
(:Entity)-[:RELATIONSHIP_TYPE {
    since: date,
    until: date,
    strength: float,
    confidence: float,
    properties: json
}]->(:Entity)
```

**Orphan Data**:
```cypher
(:OrphanIdentifier {
    id: string,
    project_id: string,
    identifier_type: string,
    identifier_value: string,
    source: string,
    collected_at: datetime
})
```

**Investigation**:
```cypher
(:Investigation {
    id: string,
    project_id: string,
    title: string,
    investigation_type: string,
    status: string,
    priority: string,
    opened_at: datetime,
    closed_at: datetime
})
```

**Sock Puppet**:
```cypher
(:SockPuppet {
    id: string,
    project_id: string,
    alias_name: string,
    entity_id: string,  // Link to entity
    platforms: json,
    credentials_ref: string,  // Reference to external vault
    created_at: datetime
})
```

---

## Technology Stack

### Core
- **Language**: Python 3.11+
- **Database**: Neo4j 5.x (graph database)
- **API**: FastAPI (REST API)
- **MCP**: FastMCP (Model Context Protocol server)

### Libraries
- py2neo (Neo4j driver)
- pydantic (data validation)
- httpx (async HTTP client for basset-verify integration)

### Deployment
- Docker container
- Docker Compose with Neo4j
- Optional Kubernetes deployment

---

## Performance Requirements

- **Entity creation**: < 100ms
- **Relationship queries**: < 500ms (with proper indexing)
- **Full-text search**: < 1s
- **Graph analysis**: < 5s for subgraphs up to 1000 nodes
- **Concurrent requests**: 100+ requests/second
- **Database size**: Support 100,000+ entities

---

## Security Requirements

- ✅ No plaintext password storage
- ✅ No automatic verification (prevents alerting threat actors)
- ✅ Project-level data isolation
- ✅ Audit logging for all data changes
- ✅ Chain of custody for evidence
- ✅ SHA-256 integrity verification
- ✅ TLS/HTTPS for all external connections

---

## Testing Requirements

- ✅ Unit tests for all MCP tools (>90% coverage)
- ✅ Integration tests with Neo4j
- ✅ API endpoint tests
- ✅ Graph query tests
- ✅ Evidence integrity tests
- ✅ Graceful degradation tests (when basset-verify is down)

---

## Documentation Requirements

- ✅ README with installation instructions
- ✅ SCOPE.md (this document)
- ✅ ROADMAP.md with development phases
- ✅ MCP tool documentation (auto-generated)
- ✅ Integration guides for external tools
- ✅ Schema configuration guide
- ✅ Findings documents for each phase

---

## Versioning & Stability

### API Stability Promise

basset-hound follows semantic versioning (MAJOR.MINOR.PATCH):

- **MAJOR**: Breaking schema or API changes
- **MINOR**: New MCP tools, backward compatible
- **PATCH**: Bug fixes

### Schema Migration

- Schema changes must be backward compatible
- Migration scripts provided for breaking changes
- Neo4j constraints and indexes maintained

---

## Success Criteria

basset-hound is successful if:

1. ✅ Intelligence is stored in a flexible, queryable structure
2. ✅ AI agents can easily interact via MCP tools
3. ✅ Investigators can manage investigations effectively
4. ✅ Relationships are discoverable and analyzable
5. ✅ Evidence has verified chain of custody
6. ✅ Sock puppets enable undercover investigations
7. ✅ System degrades gracefully when dependencies fail
8. ✅ No automatic operations alert threat actors

---

## Non-Goals

- **Not an OSINT automation platform** (use palletai)
- **Not a verification service** (use basset-verify)
- **Not a browser automation tool** (use basset-hound-browser)
- **Not a threat intelligence platform**
- **Not a real-time monitoring system**
- **Not a credential manager** (use 1Password, etc.)
- **Not a social media scraper**
- **Not an active reconnaissance tool**

basset-hound does **one thing well**: manage intelligence in highly configurable ways.

---

## Feature Removal (Post-Phase 41 Clarification)

The following features were **removed from basset-hound scope** and migrated to appropriate repositories:

### Migrated to basset-verify
- ❌ `verify_identifier` tool → basset-verify
- ❌ `verify_email` tool → basset-verify
- ❌ `verify_phone` tool → basset-verify
- ❌ `verify_crypto` tool → basset-verify
- ❌ `verify_domain` tool → basset-verify
- ❌ `verify_ip` tool → basset-verify
- ❌ `verify_url` tool → basset-verify
- ❌ `verify_username` tool → basset-verify
- ❌ `batch_verify` tool → basset-verify
- ❌ `get_supported_cryptocurrencies` tool → basset-verify
- ❌ `get_all_crypto_matches` tool → basset-verify
- ❌ `get_verification_types` tool → basset-verify

**Total tools removed**: 12 (Phase 40.5)
**New tool count**: 112 → 100 tools

---

## Review Schedule

This scope document should be reviewed:

- **Quarterly**: Ensure scope remains focused on intelligence management
- **Before major releases**: Confirm no scope creep
- **When adding new features**: Verify alignment with core mission

**Last Review**: 2026-01-09 (Post-Phase 41 Clarification)
**Next Review**: 2026-04-09
