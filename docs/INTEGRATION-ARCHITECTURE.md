# Basset Hound Ecosystem - Integration Architecture

**Last Updated:** January 4, 2026

---

## Overview

The Basset Hound ecosystem consists of three independent but integrated projects designed for OSINT investigations:

| Project | Purpose | Technology |
|---------|---------|------------|
| **basset-hound** | Entity relationship engine (backend) | Python, FastAPI, Neo4j |
| **autofill-extension** | Browser extension for data ingestion | JavaScript, Chrome MV3 |
| **basset-hound-browser** | Automated browser for OSINT agents | JavaScript, Electron |

---

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                        OSINT INVESTIGATION PLATFORM                          │
└──────────────────────────────────────────────────────────────────────────────┘
                                     │
        ┌────────────────────────────┼────────────────────────────┐
        │                            │                            │
        ▼                            ▼                            ▼
┌───────────────────┐    ┌───────────────────┐    ┌───────────────────┐
│  autofill-ext     │    │ basset-hound-     │    │   OSINT Agent     │
│  (Chrome MV3)     │    │   browser         │    │ (palletAI/Claude) │
│                   │    │   (Electron)      │    │                   │
│ Human-driven      │    │ Automated         │    │ AI-driven         │
│ data collection   │    │ investigation     │    │ orchestration     │
└─────────┬─────────┘    └─────────┬─────────┘    └─────────┬─────────┘
          │                        │                        │
          │  WebSocket/            │  WebSocket             │  MCP/REST API
          │  REST API              │  (ws://8765)           │
          │                        │                        │
          └────────────────────────┼────────────────────────┘
                                   │
                                   ▼
                    ┌─────────────────────────────┐
                    │        basset-hound         │
                    │    (Entity Relationship     │
                    │         Engine)             │
                    │                             │
                    │  REST API (8000)            │
                    │  MCP Server (stdio)         │
                    │                             │
                    │  ┌─────────────────────┐   │
                    │  │   Neo4j Graph DB    │   │
                    │  │   - Entities        │   │
                    │  │   - Relationships   │   │
                    │  │   - Orphan Data     │   │
                    │  │   - Timeline        │   │
                    │  └─────────────────────┘   │
                    └─────────────────────────────┘
```

---

## Data Flow

### 1. Human-Driven Collection (autofill-extension)

```
Web Page → Extension detects OSINT data → User clicks "Ingest"
    ↓
Extension captures:
  - Detected data (emails, phones, crypto, etc.)
  - Full URL and timestamp
  - Page context
    ↓
Client-side verification (format, checksum)
    ↓
Send to basset-hound with provenance
    ↓
basset-hound stores as orphan data
```

### 2. Automated Investigation (basset-hound-browser)

```
OSINT Agent requests investigation
    ↓
basset-hound-browser navigates to target
    ↓
Extract page content, technologies, OSINT data
    ↓
Capture evidence (screenshot, HTML, metadata)
    ↓
Send to basset-hound with provenance
    ↓
basset-hound stores and links entities
```

### 3. AI-Driven Orchestration (MCP/API)

```
AI Agent (Claude, etc.) plans investigation
    ↓
Uses MCP tools to:
  - Create entities
  - Store orphan data
  - Link relationships
  - Search graph
    ↓
Uses basset-hound-browser for:
  - Web navigation
  - Data extraction
  - Evidence capture
    ↓
Results stored in basset-hound
```

---

## Communication Protocols

### basset-hound API

| Protocol | Port | Purpose |
|----------|------|---------|
| REST API | 8000 | Full CRUD for entities, orphans, relationships |
| MCP | stdio | AI tool integration via Model Context Protocol |
| WebSocket | 8000/ws | Real-time notifications |

### autofill-extension

| Protocol | Endpoint | Purpose |
|----------|----------|---------|
| REST | basset-hound:8000 | Data ingestion, verification |
| WebSocket | basset-hound:8000/ws | Sync status updates |

### basset-hound-browser

| Protocol | Port | Purpose |
|----------|------|---------|
| WebSocket | 8765 | Browser automation commands |
| Tor SOCKS5 | 9050 | Anonymous browsing |
| Tor Control | 9051 | Tor circuit management |

---

## Key Data Structures

### DataProvenance

Tracks where data comes from:

```json
{
  "source_type": "website",
  "source_url": "https://example.com/about",
  "source_date": "2026-01-04T10:30:00Z",
  "captured_by": "autofill-extension",
  "page_title": "About Us - Example Company",
  "confidence": 0.95,
  "verification_status": "format_valid"
}
```

### OrphanData with Provenance

```json
{
  "identifier_type": "EMAIL",
  "identifier_value": "john@example.com",
  "metadata": {
    "context": "Contact: john@example.com",
    "verification": {
      "format_valid": true,
      "mx_exists": true,
      "disposable": false
    }
  },
  "provenance": {
    "source_type": "website",
    "source_url": "https://example.com/contact",
    "source_date": "2026-01-04T10:30:00Z",
    "captured_by": "autofill-extension"
  }
}
```

### Evidence Bundle

```json
{
  "url": "https://example.com/page",
  "timestamp": "2026-01-04T10:30:00Z",
  "screenshot": "base64...",
  "html": "<!DOCTYPE html>...",
  "metadata": {
    "title": "Page Title",
    "meta_tags": [...],
    "technologies": [...]
  }
}
```

---

## Integration Points

### 1. autofill-extension → basset-hound

**Endpoints Used:**
- `POST /api/v1/projects/{project}/orphans` - Create orphan data
- `POST /api/v1/verify/email` - Verify email
- `POST /api/v1/verify/crypto` - Verify crypto address
- `WS /api/v1/ws` - Real-time sync status

**Data Sent:**
- Detected OSINT identifiers
- Full provenance (URL, date, context)
- Verification results

### 2. basset-hound-browser → basset-hound

**Endpoints Used:**
- `POST /api/v1/projects/{project}/orphans/batch` - Bulk create orphans
- `POST /api/v1/projects/{project}/entities` - Create entities
- `POST /api/v1/files` - Upload evidence files

**Data Sent:**
- Extracted OSINT data
- Evidence bundles (screenshots, HTML)
- Investigation metadata

### 3. OSINT Agent → basset-hound (via MCP)

**MCP Tools:**
- `create_entity` - Create entities
- `create_orphan` - Store orphan data
- `link_entities` - Create relationships
- `search_entities` - Query graph
- `get_related_entities` - Traverse relationships
- `generate_report` - Create reports

### 4. OSINT Agent → basset-hound-browser (via WebSocket)

**Commands:**
- `navigate` - Navigate to URL
- `extract_osint_data` - Extract identifiers
- `capture_evidence` - Screenshot + HTML
- `get_page_state` - Page analysis
- `detect_technologies` - Tech stack detection

---

## Verification Flow

```
Data Input (email, phone, crypto, domain)
           ↓
    ┌──────────────────┐
    │ Format Validation│  ← Client-side (extension or browser)
    │ (regex, checksum)│
    └────────┬─────────┘
             │
    ┌────────▼─────────┐
    │ Network Verify   │  ← Server-side (basset-hound)
    │ (MX, DNS, WHOIS) │
    └────────┬─────────┘
             │
    ┌────────▼─────────┐
    │ External API     │  ← Server-side (basset-hound)
    │ (blockchain)     │
    └────────┬─────────┘
             │
             ▼
    ┌─────────────────┐
    │ Verification    │
    │ Result          │
    │ - format_valid  │
    │ - network_valid │
    │ - exists        │
    │ - confidence    │
    └─────────────────┘
```

---

## Security Considerations

### Authentication

| Component | Auth Method |
|-----------|-------------|
| basset-hound | Optional JWT/API key |
| autofill-extension | Token in localStorage |
| basset-hound-browser | WebSocket auth token |

### Data Protection

- HTTPS for all external communication
- WSS for WebSocket where possible
- Sensitive data encrypted at rest
- Evidence files stored securely

### Privacy

- Local-first design (data stays on your machine)
- No external telemetry
- Tor integration for anonymous browsing
- OSINT data handling follows ethical guidelines

---

## Deployment Topology

### Development (Single Machine)

```
localhost:8000  → basset-hound (FastAPI)
localhost:7474  → Neo4j Browser
localhost:8765  → basset-hound-browser (when running)
Chrome          → autofill-extension (loaded unpacked)
```

### Production (Docker)

```yaml
services:
  basset-hound:
    ports: ["8000:8000"]
  neo4j:
    ports: ["7474:7474", "7687:7687"]
  redis:
    ports: ["6379:6379"]
  # basset-hound-browser runs separately (Electron app)
```

---

## Future Enhancements

1. **Shared Session Pool** - basset-hound-browser instances managed by basset-hound
2. **Investigation Workflows** - Multi-step automated investigations
3. **Real-time Collaboration** - Multiple users investigating together
4. **Cloud Deployment** - Scalable cloud infrastructure option
5. **Mobile App** - Field OSINT collection

---

## Related Documentation

- [basset-hound ROADMAP](./ROADMAP.md)
- [autofill-extension ROADMAP](~/autofill-extension/docs/ROADMAP.md)
- [basset-hound-browser ROADMAP](~/basset-hound-browser/docs/ROADMAP.md)
- [Integration Research Findings](./findings/INTEGRATION-RESEARCH-2026-01-04.md)
