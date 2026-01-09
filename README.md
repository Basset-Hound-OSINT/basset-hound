# Basset Hound

<div align="center">
<img src="static/imgs/basset_hound_osint_logo.png" width="200">

**A lightweight, graph-based entity relationship engine for OSINT investigations**

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![Neo4j](https://img.shields.io/badge/Neo4j-5.28+-red.svg)](https://neo4j.com/)
</div>

---

## What is Basset Hound?

Basset Hound is a **focused, API-first entity relationship engine** inspired by [BloodHound](https://github.com/BloodHoundAD/BloodHound), but designed for general OSINT work. It's meant to be **integrated into other applications** - not a standalone enterprise platform.

### Design Philosophy

| Principle | What It Means |
|-----------|---------------|
| **Lightweight** | Core functionality only - no bloat, no enterprise features |
| **Integration-First** | Built to be consumed by LLMs, AI agents, and other tools via API/MCP |
| **Local-First** | Runs on your laptop, scales with more hardware |
| **Graph-Powered** | Neo4j for relationship traversal and pattern discovery |
| **Simple but Powerful** | Few features done well, not many features done poorly |

### What Basset Hound IS
- An entity relationship storage and query engine
- A graph analysis backend for path finding, clustering, and centrality
- An API/MCP server for AI tool integration
- A data ingestion pipeline from OSINT tools

### What Basset Hound is NOT
- A full-featured reporting platform (reports exist for LLM context, not end-users)
- A multi-user enterprise application
- A replacement for specialized OSINT tools
- A UI-first application (API-first, UI is secondary)

Unlike traditional databases, Basset Hound treats relationships as first-class citizens and allows you to:

- **Store unlinked data** (emails, phones, addresses) before you know who they belong to
- **Build entity profiles** from scattered information across multiple sources
- **Discover hidden connections** through graph analysis and relationship mapping
- **Track investigation progress** with timeline and change tracking
- **Automate linking** using intelligent identifier matching

### Core Philosophy: "Collect Now, Connect Later"

In OSINT investigations, you often discover fragments of information before knowing the full picture:
- A phone number mentioned in a forum post
- An email address in a data breach
- A crypto wallet in a transaction
- A username on social media

**Traditional approach:** Wait until you have enough info to create a full profile
**Basset Hound approach:** Store everything immediately as "orphan data", then link it when connections become clear

This is the **orphan data** concept: storing identifiers and information fragments without requiring an entity assignment. As your investigation progresses, Basset Hound suggests connections and helps you merge orphan data into entity profiles.

---

## Key Features

### 🔍 Smart Suggestions & Data Matching
- **Automatic duplicate detection** using file hashing (SHA-256) and string matching
- **Intelligent suggestions** for linking orphan data to entities (50-100% confidence)
- **Fuzzy matching** for names, addresses, and usernames with similarity scoring
- **Data deduplication** - detect when same email, phone, or file appears multiple times
- Track data provenance (source, confidence, timestamps)
- Store unlinked identifiers until connections are discovered

### 🆔 Advanced Data Management
- **Unique Data IDs** - Every piece of data gets a trackable ID (format: `data_abc123`)
- **File integrity verification** - SHA-256 hashing for evidence chain of custody
- **Cross-entity tracking** - See when same data appears in multiple entities
- **Smart normalization** - Email, phone, address, and name standardization for accurate matching

### 👤 Multi-Entity Type Support
- **Person** - Individuals with detailed social/contact info
- **Organization** - Companies, groups, agencies
- **Device** - Phones, computers, IoT devices
- **Location** - Addresses, venues, regions
- **Event** - Incidents, meetings, transactions
- **Document** - Files, reports, evidence

### 🕸️ Graph-Based Relationships
- 26 relationship types (WORKS_WITH, KNOWS, FAMILY, OWNS, etc.)
- Bidirectional and transitive relationship support
- Path finding (shortest path, all paths)
- Cluster detection and centrality analysis
- Cross-project entity linking

### 🔎 Advanced Search
- Boolean operators: AND, OR, NOT
- Phrase search: "exact match"
- Field-specific: `email:john@example.com`
- Wildcards: `name:John*`, `phone:555?`
- Fuzzy matching with phonetic support

### 📊 Visualization & Analysis
- Graph visualization API (D3.js, vis.js, Cytoscape formats)
- Timeline analysis for entity/relationship changes
- Activity heat maps and pattern detection
- ML-powered query suggestions

### 🤖 API & MCP Integration
- **Full REST API** with OpenAPI docs (9 suggestion endpoints)
- **MCP (Model Context Protocol)** server for AI tools (119 tools)
- **WebSocket notifications** for real-time updates (5 event types)
- **HATEOAS-compliant** API design for self-discovery
- Bulk import/export (JSON, CSV, JSONL)
- Rate limiting (100 req/min per IP)

### 🛡️ Privacy-Focused
- **Local-first** - Your data never leaves your machine
- **No authentication** - Single-user, trusted environment
- **No telemetry** - 100% offline operation
- **Open source** - Full transparency and control

---

## Quick Start

### Prerequisites
- **Python 3.12+**
- **Docker & Docker Compose** (for Neo4j)
- **Git**

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/basset-hound.git
cd basset-hound

# 2. Start Neo4j database
docker compose up -d neo4j

# 3. Set up Python environment
python3.12 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# 4. Start Basset Hound
python main.py
```

### Access Points

- **Web UI:** http://localhost:5000 (Flask legacy UI)
- **FastAPI Docs:** http://localhost:8000/docs
- **Neo4j Browser:** http://localhost:7474 (user: neo4j, pass: your_password)

---

## Usage Examples

### Storing Orphan Data

```bash
# Found an email but don't know who it belongs to yet
curl -X POST http://localhost:8000/api/v1/projects/my-investigation/orphan-data \
  -H "Content-Type: application/json" \
  -d '{
    "identifier_type": "EMAIL",
    "identifier_value": "suspicious@example.com",
    "metadata": {
      "source": "data breach xyz",
      "confidence": "high",
      "notes": "Found in leaked customer list"
    },
    "tags": ["breach-2024", "investigate"]
  }'
```

### Getting Match Suggestions

```bash
# Check if this orphan data matches any existing entities
curl http://localhost:8000/api/v1/projects/my-investigation/orphan-data/{orphan_id}/suggestions
```

### Linking Orphan to Entity

```bash
# Merge orphan data into an entity profile
curl -X POST http://localhost:8000/api/v1/projects/my-investigation/orphan-data/{orphan_id}/link/{entity_id}
```

### Advanced Search

```bash
# Boolean search with field-specific queries
curl "http://localhost:8000/api/v1/projects/my-investigation/search/advanced?query=email:*@gmail.com+AND+tag:suspect+AND+NOT+status:cleared"
```

### Graph Visualization

```bash
# Get graph data in D3.js format
curl "http://localhost:8000/api/v1/projects/my-investigation/graph?format=d3&include_orphans=true"
```

---

## Configuration

Basset Hound uses `data_config.yaml` for runtime schema configuration. You can add custom fields, sections, and entity types without modifying code.

Example custom field:
```yaml
sections:
  - id: custom_section
    name: My Custom Data
    fields:
      - id: custom_field
        type: string
        label: Custom Field
        identifier: true  # Use for entity matching
        searchable: true  # Include in search index
```

See [docs/ROADMAP.md](docs/ROADMAP.md) for full configuration documentation.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Basset Hound                            │
├─────────────────────────────────────────────────────────────┤
│  FastAPI (REST API)  │  Flask (Web UI)  │  MCP Server       │
├─────────────────────────────────────────────────────────────┤
│                     Services Layer                           │
│  • Entity Management    • Orphan Data    • Graph Analysis   │
│  • Auto-Linking         • Search         • Timeline         │
│  • Bulk Operations      • Reports        • Cache            │
├─────────────────────────────────────────────────────────────┤
│                     Neo4j Graph Database                     │
│  Entities (Person, Org, Device, etc.) + Relationships        │
└─────────────────────────────────────────────────────────────┘
```

---

## Development

### Running Tests

```bash
# All tests
python -m pytest tests/ -v

# Specific test file
python -m pytest tests/test_orphan_data.py -v

# With coverage
python -m pytest tests/ --cov=api --cov-report=html
```

### Project Structure

```
basset-hound/
├── api/                    # FastAPI application
│   ├── routers/           # REST API endpoints
│   ├── services/          # Business logic
│   ├── models/            # Pydantic models
│   └── utils/             # Utilities
├── mcp/                   # MCP server
├── tests/                 # Pytest tests
├── docs/                  # Documentation
│   ├── ROADMAP.md         # Development roadmap
│   └── findings/          # Phase documentation
├── static/                # Web UI assets
├── templates/             # Jinja2 templates
├── data_config.yaml       # Schema configuration
└── main.py               # Entry point
```

---

## REST API

Basset Hound provides a comprehensive REST API following 2026 best practices:

### Suggestion Endpoints

```bash
# Get smart suggestions for an entity
GET /api/v1/suggestions/entity/{entity_id}?confidence_level=HIGH&limit=20

# Dismiss a suggestion
POST /api/v1/suggestions/{suggestion_id}/dismiss
{
  "reason": "Not a match - different person",
  "dismissed_by": "analyst_123"
}

# Merge entities (irreversible)
POST /api/v1/suggestions/linking/merge-entities
{
  "entity_id_1": "ent_abc123",
  "entity_id_2": "ent_def456",
  "keep_entity_id": "ent_abc123",
  "reason": "Confirmed duplicate",
  "created_by": "analyst_123"
}

# Get audit trail
GET /api/v1/suggestions/linking/history/{entity_id}
```

### API Features

- **HATEOAS Links**: Self-discoverable with navigation links
- **Smart Pagination**: Next/prev links with query preservation
- **Rate Limiting**: 100 requests/minute per IP
- **OpenAPI Docs**: Interactive testing at `http://localhost:8000/docs`
- **Response Times**: <500ms for all endpoints

## WebSocket Real-Time Updates

Connect to receive instant notifications:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/suggestions/proj_123');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  switch (data.event_type) {
    case 'suggestion_generated':
      showNotification(`${data.suggestion_count} new suggestions`);
      break;
    case 'entity_merged':
      refreshEntityList();
      break;
    case 'data_linked':
      updateEntityProfile(data.entity_id);
      break;
  }
};
```

### Event Types

- `suggestion_generated` - New suggestions available
- `suggestion_dismissed` - User dismissed suggestion
- `entity_merged` - Entities were merged
- `data_linked` - Data items linked
- `orphan_linked` - Orphan linked to entity

See `api/websocket/client_example.js` for full client library with React/Vue examples.

---

## Use Cases

### OSINT Investigations
Track people, organizations, and their connections across multiple sources

### Threat Intelligence
Map threat actors, infrastructure, and attack patterns

### Data Breach Analysis
Correlate leaked credentials, emails, and personal information

### Social Network Analysis
Discover hidden relationships and community structures

### Research & Genealogy
Build knowledge graphs for academic research or family trees

---

## Roadmap

See [docs/ROADMAP.md](docs/ROADMAP.md) for detailed development plans.

**Core Features (Completed):**
- ✅ Entity relationship storage with Neo4j
- ✅ Multi-entity type support (Person, Org, Device, Location, Event, Document)
- ✅ Graph analysis (path finding, clustering, centrality)
- ✅ Orphan data management (store-now, link-later workflow)
- ✅ **Smart Suggestions** - Automatic data matching with confidence scoring (Phase 43)
- ✅ **File Hashing** - SHA-256 duplicate detection and integrity verification
- ✅ **Data ID System** - Unique IDs for every data item (data_abc123 format)
- ✅ **REST API** - 9 HATEOAS-compliant endpoints for suggestions (Phase 44)
- ✅ **WebSocket Notifications** - Real-time updates for merges/links (Phase 45)
- ✅ **UI Components** - Production-ready designs (WCAG 2.1 AA) (Phase 46)
- ✅ Data import connectors (Maltego, SpiderFoot, Shodan, HIBP, etc.)
- ✅ API + MCP server for AI integration (119 total MCP tools)
- ✅ 114+ comprehensive tests with 95% pass rate

**Priority Focus Areas:**
- 🎯 Graph analytics (community detection, influence propagation)
- 🎯 Query optimization for large datasets
- 🎯 Import/export flexibility
- 🎯 API stability and documentation

---

## Contributing

Basset Hound is open source and welcomes contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## License

[Your License Here - e.g., MIT, GPL, Apache 2.0]

---

## Credits

Inspired by [BloodHound](https://github.com/BloodHoundAD/BloodHound)'s approach to graph-based relationship analysis, adapted for general OSINT investigations with a focus on simplicity and integration.

Built with:
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [Neo4j](https://neo4j.com/) - Graph database for relationship storage
- [Pydantic](https://pydantic-docs.helpmanual.io/) - Data validation
- [MCP](https://modelcontextprotocol.io/) - AI tool integration protocol

---

## Support

- **Issues:** https://github.com/yourusername/basset-hound/issues
- **Documentation:** [docs/](docs/)
- **Discussions:** [GitHub Discussions](https://github.com/yourusername/basset-hound/discussions)
