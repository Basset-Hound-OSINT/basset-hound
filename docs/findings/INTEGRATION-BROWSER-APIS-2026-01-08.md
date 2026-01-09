# Browser Integration APIs - Phase 41 Research & Integration Plan

**Date:** 2026-01-08
**Phase:** 41 (Browser Integration APIs)
**Status:** Research Complete, Implementation Pending

---

## Executive Summary

This document captures research findings for Phase 41: Browser Integration APIs. Based on comprehensive code reviews of external repositories (autofill-extension, basset-hound-browser, palletai) and web research on browser extension patterns, this document outlines what basset-hound needs to implement to enable seamless integration.

**Key Finding:** The external repositories are already well-architected with MCP servers and WebSocket APIs. Basset-hound's role is to provide **MCP tools that these clients can consume**, not to implement browser-side functionality.

---

## 1. Integration Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    BASSET-HOUND (This Repo)                     │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              MCP Server (FastMCP)                        │   │
│  │  99 tools → 117+ tools with browser integration          │   │
│  │                                                          │   │
│  │  NEW TOOLS FOR PHASE 41:                                 │   │
│  │  - get_autofill_data          (for form filling)         │   │
│  │  - suggest_form_mapping       (field → entity mapping)   │   │
│  │  - capture_evidence           (store browser captures)   │   │
│  │  - create_warc_record         (evidence archiving)       │   │
│  │  - get_sock_puppet_profile    (identity for browser)     │   │
│  │  - register_browser_session   (session tracking)         │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ MCP Protocol / REST API
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│ autofill-     │     │ basset-hound- │     │   palletai    │
│ extension     │     │ browser       │     │               │
│               │     │               │     │               │
│ Chrome Ext    │     │ Electron App  │     │ AI Agent Orch │
│ 78 MCP tools  │     │ 40 MCP tools  │     │ Capability Sys│
│ WebSocket API │     │ WebSocket API │     │ MCP Client    │
└───────────────┘     └───────────────┘     └───────────────┘
```

---

## 2. External Repository Analysis

### 2.1 autofill-extension

**Current State:** Production-ready with 78 MCP tools

**Integration Points Already Implemented:**
- `utils/data-pipeline/basset-hound-sync.js` - Sync to basset-hound
- `utils/form/entity-form-filler.js` - Entity-based form filling
- OSINT field detection with verification
- Sock puppet form filling (Phase 10)

**What They Need from basset-hound:**

| Endpoint | Purpose | Priority |
|----------|---------|----------|
| `GET /api/v1/entities/{id}/autofill-data` | Flattened entity data for form filling | HIGH |
| `POST /api/v1/form-mapping/suggest` | Map form fields to entity paths | MEDIUM |
| `GET /api/v1/sock-puppets/{id}/profile` | Get sock puppet identity for forms | HIGH |
| `POST /api/v1/evidence/ingest` | Submit captured OSINT data | HIGH |

**Gaps in autofill-extension (for their roadmap):**
- Formalize basset-hound authentication in MCP calls
- Implement bidirectional entity sync (currently one-way)
- Standardize error codes with basset-hound's error taxonomy

### 2.2 basset-hound-browser

**Current State:** Production-ready Electron browser with 40 MCP tools

**Key Capabilities:**
- Evidence collection with chain of custody (Phase 18)
- Screenshot capture (viewport, full-page, element)
- Page archiving (MHTML, HTML, WARC)
- Network HAR capture
- MCP server for AI agents

**What They Need from basset-hound:**

| Endpoint | Purpose | Priority |
|----------|---------|----------|
| `POST /api/v1/evidence/capture` | Submit evidence package | HIGH |
| `POST /api/v1/evidence/warc` | Store WARC archive | HIGH |
| `GET /api/v1/investigations/{id}/context` | Get investigation state | MEDIUM |
| `POST /api/v1/provenance/record` | Track data provenance | HIGH |

**Gaps in basset-hound-browser (for their roadmap):**
- Direct data flow to basset-hound (currently manual)
- MCP resource support for investigation context
- Evidence package submission endpoint integration
- Session persistence to basset-hound

### 2.3 palletai

**Current State:** AI agent orchestration with capability system

**Key Capabilities:**
- 7 built-in capabilities
- Agent specialization system
- Multi-agent collaboration
- Security testing capability

**What They Need from basset-hound:**

| MCP Tool | Purpose | Priority |
|----------|---------|----------|
| All 99 existing tools | Entity/relationship CRUD | HIGH |
| `get_investigation_context` | For agent decision-making | MEDIUM |
| `get_entity_graph` | Relationship visualization | MEDIUM |

**Gaps in palletai (for their roadmap):**
- Create `osint_storage` capability (Phase 16)
- Create `browser_automation` capability (Phase 17)
- Implement OSINT agent specialization (Phase 15)
- Create basset-hound MCP client

---

## 3. New MCP Tools for basset-hound (Phase 41)

### 3.1 Autofill Data Tools

```python
@mcp.tool()
def get_autofill_data(
    project_id: str,
    entity_id: str,
    include_sock_puppet: bool = False
) -> dict:
    """
    Get flattened entity data formatted for form autofill.

    Returns fields in autofill-friendly format:
    {
        "firstName": "John",
        "lastName": "Doe",
        "email": "john@example.com",
        "phone": "+1234567890",
        ...
    }
    """

@mcp.tool()
def suggest_form_mapping(
    project_id: str,
    entity_id: str,
    form_fields: list
) -> dict:
    """
    Suggest mappings between form fields and entity data.

    Args:
        form_fields: List of {id, name, type, label, placeholder}

    Returns:
        {
            "mappings": [
                {"field_id": "email_input", "entity_path": "contact.email", "confidence": 0.95}
            ]
        }
    """
```

### 3.2 Evidence Capture Tools

```python
@mcp.tool()
def capture_evidence(
    project_id: str,
    investigation_id: str = None,
    evidence_type: str = "screenshot",
    content_base64: str = None,
    url: str = None,
    metadata: dict = None,
    captured_by: str = "browser"
) -> dict:
    """
    Store evidence captured by browser with chain of custody.

    Args:
        evidence_type: screenshot, page_archive, network_har, dom_snapshot
        content_base64: Base64 encoded content
        url: Source URL
        metadata: Additional metadata (title, timestamp, viewport, etc.)
        captured_by: Source identifier (browser, extension, agent)

    Returns:
        {
            "evidence_id": "ev_123",
            "sha256": "abc...",
            "provenance_id": "prov_456",
            "chain_of_custody_started": true
        }
    """

@mcp.tool()
def create_warc_record(
    project_id: str,
    investigation_id: str = None,
    warc_content: str = None,  # Base64 encoded WARC
    url: str = None,
    warc_type: str = "response"
) -> dict:
    """
    Store a WARC record for web archiving.

    WARC is the ISO 28500 standard for web evidence.
    """
```

### 3.3 Sock Puppet Profile Tools

```python
@mcp.tool()
def get_sock_puppet_profile(
    project_id: str,
    puppet_id: str,
    platform: str = None,
    include_credentials_ref: bool = False
) -> dict:
    """
    Get sock puppet identity profile for browser use.

    Returns identity suitable for form filling and authentication:
    {
        "alias_name": "Cover Identity",
        "backstory": "IT Consultant from Seattle...",
        "platform_accounts": [
            {
                "platform": "linkedin",
                "username": "cover.identity",
                "email": "cover@protonmail.com",
                "credential_vault_ref": "keepass://..."  # Only if include_credentials_ref
            }
        ]
    }
    """
```

### 3.4 Browser Session Tools

```python
@mcp.tool()
def register_browser_session(
    project_id: str,
    session_id: str,
    browser_type: str,  # "electron", "chrome_extension"
    user_agent: str = None,
    fingerprint_hash: str = None
) -> dict:
    """
    Register a browser session for tracking.

    Enables correlation of evidence to browser instances.
    """

@mcp.tool()
def get_investigation_context(
    project_id: str,
    investigation_id: str = None,
    include_subjects: bool = True,
    include_recent_activity: bool = True
) -> dict:
    """
    Get investigation context for browser/agent decision-making.

    Returns current investigation state useful for:
    - Deciding what to capture
    - Identifying known entities on page
    - Suggesting next investigation steps
    """
```

---

## 4. Data Flow Patterns

### 4.1 Form Autofill Flow

```
Browser Extension                basset-hound MCP
       │                                │
       │ get_autofill_data(entity_id)   │
       │ ────────────────────────────►  │
       │                                │ Query entity
       │ ◄─────────────────────────────│ Flatten to form format
       │ {firstName, lastName, email}   │
       │                                │
       │ Fill form with data            │
       ▼                                │
```

### 4.2 Evidence Capture Flow

```
Browser (Electron/Extension)     basset-hound MCP
       │                                │
       │ Take screenshot                │
       │ Compute SHA-256 hash           │
       │                                │
       │ capture_evidence(              │
       │   type="screenshot",           │
       │   content_base64="...",        │
       │   url="...",                   │
       │   metadata={...}               │
       │ )                              │
       │ ────────────────────────────►  │
       │                                │ Store evidence
       │                                │ Create provenance
       │                                │ Start chain of custody
       │ ◄─────────────────────────────│
       │ {evidence_id, sha256,          │
       │  chain_of_custody_started}     │
       ▼                                │
```

### 4.3 OSINT Data Ingestion Flow

```
Browser Extension                basset-hound MCP
       │                                │
       │ Detect OSINT data on page      │
       │ (emails, phones, crypto)       │
       │                                │
       │ verify_identifier(email)       │
       │ ────────────────────────────►  │ Validate format
       │ ◄─────────────────────────────│ Check disposable
       │ {valid, details}               │
       │                                │
       │ create_orphan_batch([          │
       │   {type: email, value: ...},   │
       │   {type: phone, value: ...}    │
       │ ])                             │
       │ ────────────────────────────►  │
       │                                │ Store as orphans
       │                                │ Record provenance
       │ ◄─────────────────────────────│
       │ {created: [...]}               │
       ▼                                │
```

---

## 5. Evidence and WARC Integration

### 5.1 WARC Format Support

Based on web research, basset-hound should support WARC (ISO 28500) for evidence:

**Python Library:** `warcio` (recommended)

```python
# Evidence storage with WARC
from warcio.warcwriter import WARCWriter
from warcio.statusandheaders import StatusAndHeaders

def store_warc_evidence(content, url, project_id):
    """Store web capture as WARC record."""
    warc_path = f"evidence/{project_id}/{uuid4()}.warc.gz"

    with open(warc_path, 'wb') as output:
        writer = WARCWriter(output, gzip=True)
        record = writer.create_warc_record(
            url,
            'response',
            payload=content,
            warc_headers_dict={
                'WARC-Source-URI': url,
                'WARC-Payload-Digest': f'sha256:{hash}'
            }
        )
        writer.write_record(record)

    return warc_path
```

### 5.2 Chain of Custody Schema

```python
class EvidenceCustody:
    """Chain of custody record for legal compliance."""

    evidence_id: str
    sha256_hash: str
    collected_at: datetime
    collected_by: str  # Agent/browser identifier
    source_url: str
    source_ip: str
    collection_method: str  # screenshot, archive, scrape

    custody_chain: List[CustodyEvent]

class CustodyEvent:
    timestamp: datetime
    action: str  # created, accessed, exported, verified
    actor: str
    details: dict
```

---

## 6. Implementation Plan

### Phase 41a: Core Browser Integration Tools

**Files to Create:**
- `basset_mcp/tools/browser_integration.py` - 18 new tools

**Tools:**
1. `get_autofill_data` - Entity data for forms
2. `suggest_form_mapping` - Field mapping suggestions
3. `get_sock_puppet_profile` - Identity for browser
4. `get_platform_account` - Platform-specific credentials ref
5. `capture_evidence` - Store browser evidence
6. `create_warc_record` - WARC archive storage
7. `get_evidence` - Retrieve stored evidence
8. `list_evidence` - List evidence for investigation
9. `verify_evidence_integrity` - Check SHA-256 hashes
10. `export_evidence_package` - Generate court-ready package
11. `register_browser_session` - Track browser sessions
12. `update_browser_session` - Update session state
13. `end_browser_session` - Close session
14. `get_investigation_context` - Context for browsers/agents
15. `get_target_urls` - URLs to investigate
16. `record_page_visit` - Log visited pages
17. `detect_known_entities` - Check if entities on page
18. `get_entity_identifiers` - All identifiers for entity

**Estimated Tool Count:** 99 current + 18 = 117 tools

### Phase 41b: Evidence Storage Layer

**Files to Modify:**
- `api/models/evidence.py` - Evidence data models
- `api/services/evidence_service.py` - Evidence business logic

**New Dependencies:**
- `warcio` - WARC file handling

### Phase 41c: Integration Tests

**Test File:**
- `tests/test_mcp_browser_integration.py`

---

## 7. External Repository Updates Required

### 7.1 For autofill-extension

**Copy this document to:** `/home/devel/autofill-extension/docs/findings/BASSET-HOUND-INTEGRATION-2026-01-08.md`

**Roadmap updates:**
- Phase 14: basset-hound MCP client formalization
- Phase 15: Bidirectional entity sync
- Phase 16: Error code standardization

### 7.2 For basset-hound-browser

**Copy this document to:** `/home/devel/basset-hound-browser/docs/findings/BASSET-HOUND-INTEGRATION-2026-01-08.md`

**Roadmap updates:**
- Phase 19: Direct evidence submission to basset-hound
- Phase 20: Investigation context resource
- Phase 21: Session persistence

### 7.3 For palletai

**Copy this document to:** `/home/devel/palletai/docs/findings/BASSET-HOUND-INTEGRATION-2026-01-08.md`

**Roadmap updates:**
- Phase 15: OSINT agent specialization
- Phase 16: basset-hound MCP client
- Phase 17: Browser automation capability

---

## 8. API Compatibility Notes

### CORS Configuration

basset-hound should accept requests from browser extension origins:

```python
# In FastAPI
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "chrome-extension://*",
        "moz-extension://*",
        "http://localhost:*",
    ],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Extension-Version"],
)
```

### Authentication Headers

Browser clients should use:
- `Authorization: Bearer <token>` for API auth
- `X-Extension-Version: 2.17.0` for version tracking
- `X-Browser-Session-ID: <uuid>` for session correlation

---

## 9. Dependencies to Add

```
# requirements.txt additions
warcio>=1.7.0  # WARC file handling
```

---

## 10. Summary

**Basset-hound's Role:**
- Provide MCP tools for browser data consumption
- Store evidence with chain of custody
- Manage sock puppet identities
- Track browser sessions
- Provide investigation context

**What basset-hound Does NOT Do:**
- Browser automation (that's basset-hound-browser/autofill-extension)
- Form detection (that's autofill-extension)
- Screenshot capture (that's the browsers)
- AI orchestration (that's palletai)

This separation of concerns keeps each repository focused on its core competency while enabling powerful integration through MCP.
