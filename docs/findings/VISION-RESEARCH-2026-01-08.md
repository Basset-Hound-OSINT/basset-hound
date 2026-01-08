# Vision Research: Multi-Project OSINT Platform Integration

**Date:** 2026-01-08
**Scope:** basset-hound, autofill-extension, basset-hound-browser, palletai

## Executive Summary

This document captures comprehensive research on expanding the basset-hound ecosystem into a full-featured OSINT investigation platform with AI agent integration, browser automation, and law enforcement sock puppet management capabilities.

---

## 1. Entity Type Expansion

### Current State (basset-hound)
- 6 entity types: PERSON, ORGANIZATION, DEVICE, LOCATION, EVENT, DOCUMENT
- Heavily developed PERSON type (70+ fields in data_config.yaml)
- Schema-driven via YAML configuration

### Proposed Expansion

| Entity Type | Description | Key Use Cases |
|-------------|-------------|---------------|
| **PERSON** | Individuals (existing) | Targets, subjects, witnesses |
| **ORGANIZATION** | Companies/groups (existing) | Corporate investigations |
| **GOVERNMENT_ENTITY** | Agencies, departments, authorities | Jurisdiction tracking, inter-agency relations |
| **SOCIAL_GROUP** | Religious, tribal, community groups | Group dynamics, membership tracking |
| **PHYSICAL_INFRASTRUCTURE** | Buildings, roads, trains, utilities | Attack surface analysis, physical presence |
| **DIGITAL_INFRASTRUCTURE** | Websites, online banks, APIs, servers | Digital attack surface, hosting relationships |

### Rationale for Infrastructure Separation
- A **company** can operate using multiple **physical infrastructures** (offices, warehouses)
- Multiple **companies** can share the same **digital infrastructure** (cloud hosting, online banking)
- An online bank is BOTH a **company** AND a **digital infrastructure** - two entities, same name, different types
- Enables clearer attack vector analysis: "Which companies are vulnerable if this physical building is compromised?"

---

## 2. Sock Puppet / Undercover Identity Management

### Industry Research

Based on research from [SANS Institute](https://www.sans.org/blog/what-are-sock-puppets-in-osint), [Maltego](https://www.maltego.com/blog/how-to-use-sock-puppet-accounts-to-gather-social-media-intelligence/), and [SockPuppet.io](https://www.sockpuppet.io/):

**Definition:** Sock puppets are fictitious online personas used by OSINT investigators and law enforcement to:
- Access information requiring account authentication
- Conduct passive surveillance without revealing identity
- Infiltrate closed communities for intelligence gathering

**Key Operational Security (OPSEC) Considerations:**
- Complete separation from real identity
- Dedicated devices, phone numbers, password managers
- Platform-specific configuration (Facebook friend suggestions, LinkedIn profile views)
- Burn date management and identity retirement

### Professional Tools Reference

| Tool | Capabilities |
|------|-------------|
| **SockPuppet.io Alias** | Virtual desktops, virtual phones, SMS services, centralized dashboard |
| **Firefox Multi-Account Containers** | Session isolation per identity |
| **KeePass/Bitwarden** | Credential management per persona |
| **Maltego** | Passive OSINT without direct platform access |

### Proposed basset-hound Implementation

**New Entity Subtype: SOCK_PUPPET (extends PERSON)**

```yaml
sections:
  - id: cover_identity
    fields: [alias_name, backstory, birth_date, nationality]
  - id: operational
    fields: [handler_id, operation_id, created_date, burn_date, status]
  - id: platforms
    fields: [platform_accounts]  # Array of {platform, username, password, 2fa_seed, created, last_active}
  - id: attribution
    fields: [fingerprint_profile, proxy_config, browser_profile_id]
```

**New Relationship Types:**
- `HANDLER_OF` / `HANDLED_BY`
- `COVER_FOR` (sock puppet covering real identity)
- `OPERATION_TARGET` (linking to investigation targets)

---

## 3. Data Provenance & Chain of Custody

### Current State (basset-hound)
Already implemented comprehensive provenance model:
- Source types: WEBSITE, API, FILE_IMPORT, MANUAL, BROWSER_EXTENSION, OSINT_AGENT, MCP_TOOL
- Capture methods: AUTO_DETECTED, USER_SELECTED, FORM_AUTOFILL, CLIPBOARD_PASTE
- Verification states with user override capability

### Law Enforcement Evidence Management Research

Based on research from [Axon](https://www.axon.com/resources/digital-evidence-management-guide), [Kaseware](https://www.kaseware.com/evidence-management), and [Tracker Products](https://trackerproducts.com/):

**Required Capabilities:**
- Unbreakable chain of custody documentation
- Every access logged with timestamp, user, action
- Hash verification for integrity (MD5, SHA-256)
- CJIS and SOC II compliance standards
- Barcode/RFID tracking for physical evidence

### Enhancement Recommendations

```python
# Enhanced DataProvenance model
class EvidenceChainEntry:
    timestamp: datetime
    user_id: str
    action: str  # viewed, modified, exported, shared
    ip_address: str
    device_fingerprint: str
    hash_before: str
    hash_after: str
    notes: str

class ForensicMetadata:
    file_hash_md5: str
    file_hash_sha256: str
    acquisition_method: str
    acquisition_tool: str
    examiner_id: str
    case_number: str
    exhibit_number: str
```

---

## 4. Database Architecture Considerations

### Current State
- Neo4j 5.28.1 graph database
- Excellent for relationship traversal and pattern discovery

### Research: Neo4j vs Alternatives

Based on research from [PuppyGraph](https://www.puppygraph.com/blog/neo4j-alternatives), [DataWalk](https://datawalk.com/neo4jalternative/), and [Memgraph](https://memgraph.com/blog/neo4j-alternative-what-are-my-open-source-db-options):

| Database | Strengths | Weaknesses |
|----------|-----------|------------|
| **Neo4j** | Native graph, ACID, Cypher query | Population-level query performance |
| **Memgraph** | 8x faster reads, 50x faster writes | Less mature ecosystem |
| **DataWalk** | No-code UI, entity resolution built-in | Proprietary, expensive |
| **ScyllaDB** | High throughput, low latency | Not native graph (use with JanusGraph) |
| **TigerGraph** | Distributed, fraud detection | Complex licensing |

### Recommendation
**Stay with Neo4j** for basset-hound. Reasons:
1. Native graph is essential for relationship-first OSINT
2. Cypher queries are well-suited for investigation patterns
3. Entity resolution algorithms available in Graph Data Science Library
4. Migration cost outweighs marginal performance gains
5. Population-level queries can be optimized with proper indexing

For **massive scale** (billions of entities), consider:
- **NebulaGraph** for distributed graph at scale
- **JanusGraph + ScyllaDB** for write-heavy workloads

---

## 5. Browser Automation & Bot Detection Evasion

### Research Findings

Based on research from [SOAX](https://soax.com/blog/prevent-browser-fingerprinting), [BrowserCat](https://www.browsercat.com/post/browser-fingerprint-spoofing-explained), and [GeeTest](https://www.geetest.com/en/article/how-to-defeat-botbrowser-in-2025):

**Key Fingerprint Vectors:**
- Canvas fingerprinting
- WebGL renderer/vendor strings
- AudioContext frequency analysis
- TLS/SSL JA3/JA4 fingerprints
- Navigator properties (webdriver, platform, plugins)
- Behavioral patterns (mouse movement, typing cadence)

**Modern Evasion Techniques:**
- Kernel-level spoofing (Octo Browser)
- Behavioral AI simulation
- Proxy rotation with residential IPs
- TLS fingerprint matching

### Current State (basset-hound-browser)
**Already Implemented:**
- Comprehensive fingerprint spoofing (Canvas, WebGL, Audio, Screen, Timezone)
- Human behavior simulation with Bezier curve mouse movements
- 70+ user agent rotation
- Proxy/Tor integration
- Profile isolation

**Gaps:**
- No TLS/JA3 fingerprint spoofing
- No behavioral AI adaptation
- Limited credential management integration

---

## 6. AI Agent & MCP Integration

### MCP (Model Context Protocol) Research

Based on research from [IBM](https://www.ibm.com/think/topics/model-context-protocol), [Anthropic](https://www.anthropic.com/engineering/code-execution-with-mcp), and [Linux Foundation](https://www.linuxfoundation.org/press/linux-foundation-announces-the-formation-of-the-agentic-ai-foundation):

**2025 Status:** MCP has become the industry standard for connecting AI systems to tools and data.

**Key Capabilities:**
- Universal interface for file access, function execution, contextual prompts
- Adopted by OpenAI, Microsoft, AWS, Google Cloud, Azure
- Part of Linux Foundation's Agentic AI Foundation (AAIF)

### Integration Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   OSINT Agent   │────▶│  MCP Protocol    │────▶│  basset-hound   │
│   (palletai)    │     │                  │     │  MCP Server     │
└─────────────────┘     └──────────────────┘     └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│ Browser MCP     │────▶│ autofill-ext     │────▶│ Entity Storage  │
│ Server          │     │ MCP Server       │     │ & Relationships │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

### Required MCP Tools

**basset-hound MCP (partially exists):**
- `create_entity(type, data)` - Create new entity
- `update_entity(id, data)` - Update existing
- `create_relationship(from, to, type, properties)`
- `query_entities(filters)` - Search entities
- `link_orphan(orphan_id, entity_id)` - Link orphan data
- `get_entity_graph(id, depth)` - Get relationship subgraph

**browser MCP (needed):**
- `navigate(url)` - Navigate to URL
- `fill_form(fields)` - Fill form with data
- `fill_form_with_entity(entity_id)` - Auto-fill from entity
- `screenshot()` - Capture page
- `extract_data()` - Extract OSINT data from page
- `ingest_to_entity(entity_id, data)` - Save extracted data

**autofill-extension MCP (partially exists):**
- `detect_fields()` - Detect form fields
- `get_page_osint_data()` - Get detected OSINT data
- `ingest_selection(entity_id)` - Ingest user selection
- `capture_evidence()` - Screenshot + metadata

---

## 7. Project Scope Definitions

### Platform Evolution

**Important Note:** While this document focuses on OSINT applications, both **basset-hound** and **basset-hound-browser** have evolved beyond OSINT-specific use cases:

- **basset-hound**: Now a general-purpose entity relationship backbone (not just OSINT)
- **basset-hound-browser**: Evolving toward general browser automation (not just OSINT)

The platform is designed to be **open to integration but not open-ended in scope**.

### basset-hound
**Core Mission:** General-purpose entity relationship storage and graph analysis (data backbone)
- Store entities with typed fields
- Track relationships between entities
- Manage orphan data (unlinked identifiers)
- Provide API/MCP for external tools
- Data provenance and chain of custody
- Serves OSINT, pentesting, research, or any domain needing entity tracking

**NOT in scope:**
- Browser automation (→ basset-hound-browser)
- Form detection/autofill (→ autofill-extension)
- AI agent logic (→ palletai)

### autofill-extension
**Core Mission:** Quick-start browser automation via Chrome extension
- Detect data on web pages
- Identify form fields and their types
- Allow user selection and labeling
- Capture screenshots and element context
- Send data to basset-hound with provenance
- **Target user:** Quick-start users who want ease of use

**Relationship with basset-hound-browser:** Both provide similar functionality but serve different user needs. autofill-extension is for quick-start users; basset-hound-browser is for power users needing full control.

**NOT in scope:**
- Entity storage (→ basset-hound)
- Deep browser customization (→ basset-hound-browser)
- TLS fingerprint control (→ basset-hound-browser)
- AI decision making (→ palletai)

### basset-hound-browser
**Core Mission:** Full-control browser automation with anti-detection (power-user option)
- Full browser automation (navigate, click, fill, extract)
- Advanced bot detection evasion (TLS, fingerprinting, behavioral AI)
- Profile/identity isolation
- Proxy and Tor integration
- WebSocket API for external control
- **Target user:** Power users who need boutique configurations
- **Evolving toward:** General browser automation beyond just OSINT

**Relationship with autofill-extension:** Both provide similar functionality but serve different user needs. basset-hound-browser is for power users; autofill-extension is for quick-start users.

**NOT in scope:**
- Entity storage (→ basset-hound)
- Quick-start simplicity (→ autofill-extension)
- AI agent logic (→ palletai)

### palletai
**Core Mission:** AI agent orchestration - MCP servers as "system tools"
- Agent creation and specialization
- Knowledge base management (RAG)
- Multi-agent collaboration
- Human-in-the-loop workflows
- **MCP client for external tools (treated like nmap, curl, etc.)**

**Key Architecture:** Agents treat MCP servers the same as local system tools. There is no need for a separate "MCP coordinator" project - palletai handles all tool orchestration.

**NOT in scope:**
- Entity storage (→ basset-hound)
- Browser automation code (→ basset-hound-browser)
- Browser extension features (→ autofill-extension)

---

## 8. Integration Points Summary

| From | To | Integration Method | Purpose |
|------|-----|-------------------|---------|
| autofill-extension | basset-hound | REST API + WebSocket | Data ingestion with provenance |
| basset-hound-browser | basset-hound | REST API | Automated data storage |
| palletai | basset-hound | MCP Server | Entity CRUD, relationship management |
| palletai | basset-hound-browser | MCP Server (new) | Browser automation commands |
| palletai | autofill-extension | MCP Server | Form detection, data extraction |
| autofill-extension | basset-hound-browser | Message passing | Coordinate on same pages |

---

## 9. Research Sources

### Sock Puppet Management
- [SANS Institute - What are Sock Puppets in OSINT](https://www.sans.org/blog/what-are-sock-puppets-in-osint)
- [Maltego - How to Use Sock Puppet Accounts](https://www.maltego.com/blog/how-to-use-sock-puppet-accounts-to-gather-social-media-intelligence/)
- [SockPuppet.io - Digital Identities on Demand](https://www.sockpuppet.io/)
- [Forensic OSINT - Sock Puppet Guide](https://www.forensicosint.com/sock-puppet-accounts-for-osint)

### Evidence Management
- [Axon - Digital Evidence Management Guide](https://www.axon.com/resources/digital-evidence-management-guide)
- [Kaseware - Evidence Management Software](https://www.kaseware.com/evidence-management)
- [Tracker Products SAFE](https://trackerproducts.com/)

### Database Architecture
- [PuppyGraph - Top 5 Neo4j Alternatives](https://www.puppygraph.com/blog/neo4j-alternatives)
- [DataWalk - Neo4j Alternative](https://datawalk.com/neo4jalternative/)
- [Memgraph - Open Source Neo4j Alternative](https://memgraph.com/blog/neo4j-alternative-what-are-my-open-source-db-options)
- [Neo4j - Entity Resolution Use Cases](https://neo4j.com/blog/graph-data-science/graph-data-science-use-cases-entity-resolution/)

### Browser Fingerprinting
- [SOAX - Browser Fingerprint Evasion Tools](https://soax.com/blog/prevent-browser-fingerprinting)
- [BrowserCat - Fingerprint Spoofing Explained](https://www.browsercat.com/post/browser-fingerprint-spoofing-explained)
- [GitHub - Browser Fingerprinting Analysis](https://github.com/niespodd/browser-fingerprinting)

### MCP & AI Agents
- [IBM - What is Model Context Protocol](https://www.ibm.com/think/topics/model-context-protocol)
- [Anthropic - Code Execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp)
- [Linux Foundation - Agentic AI Foundation](https://www.linuxfoundation.org/press/linux-foundation-announces-the-formation-of-the-agentic-ai-foundation)
- [MCP Specification 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25)
