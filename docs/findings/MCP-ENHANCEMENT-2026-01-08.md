# MCP Server Enhancement Implementation

**Date:** 2026-01-08
**Phase:** 40 (MCP Server Enhancement)
**Status:** Completed

---

## Executive Summary

This document captures the implementation of enhanced MCP server tools for basset-hound. The enhancements provide comprehensive support for OSINT platform integration, including orphan data management, data provenance tracking, flexible entity querying, and graph export functionality.

---

## Implementation Overview

### New MCP Tool Modules

#### 1. Orphan Tools (`basset_mcp/tools/orphans.py`)

**Purpose:** Manage unlinked/orphan data - identifiers discovered during investigations that haven't yet been linked to specific entities.

**Tools Implemented (11 total):**

| Tool | Description |
|------|-------------|
| `create_orphan` | Create single orphan data record |
| `create_orphan_batch` | Batch create multiple orphans |
| `get_orphan` | Retrieve orphan by ID |
| `list_orphans` | List orphans with filtering |
| `search_orphans` | Search orphans by identifier value |
| `link_orphan` | Link orphan to entity |
| `link_orphan_batch` | Batch link orphans to entities |
| `update_orphan` | Update orphan properties |
| `delete_orphan` | Delete orphan record |
| `find_duplicate_orphans` | Detect potential duplicates |
| `count_orphans` | Count orphans with filters |

**Key Features:**
- Full CRUD operations on orphan data
- Batch operations for efficient bulk ingestion
- Flexible filtering by identifier type, linked status, tags
- Duplicate detection for data deduplication
- Field mapping support when linking to entities

---

#### 2. Provenance Tools (`basset_mcp/tools/provenance.py`)

**Purpose:** Track data origin, chain of custody, and verification history - critical for OSINT investigations requiring source attribution.

**Tools Implemented (6 total):**

| Tool | Description |
|------|-------------|
| `get_source_types` | List available source types |
| `get_capture_methods` | List available capture methods |
| `get_verification_states` | List verification states |
| `record_entity_provenance` | Record entity-level provenance |
| `record_field_provenance` | Record field-level provenance |
| `get_entity_provenance` | Get all provenance for entity |
| `update_verification_state` | Update verification state |
| `create_provenance_record` | Create standalone provenance record |

**Source Types Supported:**
- `website` - Data captured from web page
- `api` - External API data
- `file_import` - Imported from file
- `manual` - Manual entry
- `browser_extension` - Via autofill-extension
- `osint_agent` - Via basset-hound-browser agent
- `mcp_tool` - Via MCP tool
- `third_party` - External OSINT tools (Maltego, SpiderFoot)
- `clipboard`, `ocr`, `screenshot`, `other`

**Capture Methods Supported:**
- `auto_detected`, `user_selected`, `form_autofill`
- `clipboard`, `file_upload`, `api_fetch`, `scrape`, `manual`

**Verification States:**
- `unverified`, `format_valid`, `network_verified`
- `api_verified`, `human_verified`, `user_override`
- `failed`, `expired`

---

#### 3. Enhanced Entity Tools

**New Tool:** `query_entities`

**Purpose:** Flexible entity querying with filtering criteria beyond simple search.

**Parameters:**
- `filters` - Field path to value mapping (e.g., `{"contact.email": "john@example.com"}`)
- `created_after` / `created_before` - Date range filtering
- `has_field` - Field existence check
- `has_section` - Section existence check
- `has_relationship` - Filter by relationship existence
- `limit` / `offset` - Pagination support

**Example Usage:**
```python
# Find entities with email containing "example.com" created in 2024
result = query_entities(
    project_id="my-project",
    filters={"contact.email": "example.com"},
    created_after="2024-01-01T00:00:00",
    has_relationship=True,
    limit=50
)
```

---

#### 4. Enhanced Analysis Tools

**New Tool:** `get_entity_graph`

**Purpose:** Export complete entity relationship graph for visualization and analysis.

**Parameters:**
- `entity_ids` - Optional subset of entities (None = all)
- `include_orphans` - Include linked orphan data nodes
- `format` - Output format: `standard`, `adjacency`, `cytoscape`

**Output Formats:**

**Standard Format:**
```json
{
  "nodes": [{"id": "...", "type": "entity", "label": "..."}],
  "edges": [{"source": "...", "target": "...", "type": "WORKS_WITH"}]
}
```

**Cytoscape.js Format:**
```json
{
  "elements": {
    "nodes": [{"data": {"id": "...", "label": "..."}}],
    "edges": [{"data": {"source": "...", "target": "..."}}]
  }
}
```

**Adjacency List Format:**
```json
{
  "nodes": {"id1": {"label": "..."}, ...},
  "adjacency": {"id1": [{"target": "id2", "type": "..."}]}
}
```

---

## Updated Module Structure

```
basset_mcp/
├── __init__.py
├── server.py
└── tools/
    ├── __init__.py          # Updated to register new modules
    ├── base.py              # Shared utilities
    ├── schema.py            # Schema introspection (6 tools)
    ├── entities.py          # Entity CRUD + query (6 tools)
    ├── relationships.py     # Relationship management (7 tools)
    ├── search.py            # Search tools (2 tools)
    ├── projects.py          # Project management (3 tools)
    ├── reports.py           # Report management (2 tools)
    ├── analysis.py          # Graph analysis + export (5 tools)
    ├── auto_linking.py      # Deduplication (4 tools)
    ├── orphans.py           # NEW: Orphan management (11 tools)
    └── provenance.py        # NEW: Provenance tracking (8 tools)
```

---

## Tool Count Summary

| Module | Tool Count | Status |
|--------|-----------|--------|
| schema | 6 | Existing |
| entities | 6 | +1 new (query_entities) |
| relationships | 7 | Existing |
| search | 2 | Existing |
| projects | 3 | Existing |
| reports | 2 | Existing |
| analysis | 5 | +1 new (get_entity_graph) |
| auto_linking | 4 | Existing |
| **orphans** | **11** | **NEW** |
| **provenance** | **8** | **NEW** |
| **TOTAL** | **54** | +21 new tools |

---

## Test Coverage

Created comprehensive test suite: `tests/test_mcp_enhanced_tools.py`

**Test Classes:**
- `TestOrphanTools` - 7 tests for orphan management
- `TestProvenanceTools` - 4 tests for provenance tracking
- `TestQueryEntitiesTools` - 4 tests for entity querying
- `TestGetEntityGraphTools` - 5 tests for graph export
- `TestToolRegistration` - 2 tests for module registration
- `TestIntegrationScenarios` - 3 tests for OSINT workflows

**Results:** 25 tests, all passing

---

## Integration with OSINT Platform

### For palletai (AI Agents)

AI agents can now:
1. Create orphan data as identifiers are discovered
2. Record provenance for all captured data
3. Link orphans to entities as relationships are confirmed
4. Query entities with flexible criteria
5. Export graphs for analysis/visualization

**Example Agent Workflow:**
```python
# 1. Agent discovers email on web page
orphan = await mcp_client.call("create_orphan", {
    "project_id": "investigation-1",
    "identifier_type": "email",
    "identifier_value": "target@example.com",
    "tags": ["linkedin", "osint"]
})

# 2. Record provenance
await mcp_client.call("record_entity_provenance", {
    "project_id": "investigation-1",
    "entity_id": "person-123",
    "source_type": "osint_agent",
    "source_url": "https://linkedin.com/in/target",
    "capture_method": "scrape",
    "captured_by": "basset-hound-browser",
    "confidence": 0.85
})

# 3. Link orphan to entity
await mcp_client.call("link_orphan", {
    "project_id": "investigation-1",
    "orphan_id": orphan["id"],
    "entity_id": "person-123",
    "field_mapping": "contact.email"
})

# 4. Export graph for visualization
graph = await mcp_client.call("get_entity_graph", {
    "project_id": "investigation-1",
    "include_orphans": True,
    "format": "cytoscape"
})
```

### For autofill-extension

Extension can:
- Record provenance when user selects data
- Create orphans for detected identifiers
- Link orphans when user confirms entity association

### For basset-hound-browser

Browser automation can:
- Record provenance for scraped data
- Create orphans in batch during automated extraction
- Record evidence chain with screenshot paths

---

## Security Considerations

1. **Provenance Integrity**
   - Provenance records include timestamps and captured_by fields
   - Supports verification state tracking
   - User override capability with reason logging

2. **Data Isolation**
   - All operations scoped to project_id
   - Orphan data linked to specific projects

3. **Audit Trail**
   - All provenance operations timestamped
   - Chain of custody maintained through transformation_notes

---

## Files Changed

### New Files
- `basset_mcp/tools/orphans.py` - Orphan data management tools
- `basset_mcp/tools/provenance.py` - Provenance tracking tools
- `tests/test_mcp_enhanced_tools.py` - Comprehensive test suite

### Modified Files
- `basset_mcp/tools/__init__.py` - Register new tool modules
- `basset_mcp/tools/entities.py` - Added query_entities tool
- `basset_mcp/tools/analysis.py` - Added get_entity_graph tool

---

## Related Documents

- Platform vision: `/home/devel/basset-hound/docs/findings/VISION-RESEARCH-2026-01-08.md`
- Provenance model: `/home/devel/basset-hound/api/models/provenance.py`
- Roadmap: `/home/devel/basset-hound/docs/ROADMAP.md`

---

## Next Steps

1. **palletai Integration (Phase 41)**
   - Create MCP client in palletai to connect to basset-hound MCP server
   - Implement OSINT agent type with investigation methodology

2. **Browser MCP Server (Phase 42)**
   - Expose basset-hound-browser via MCP for AI agent control
   - Integrate provenance recording with browser automation

3. **Evidence Collection (Phase 43)**
   - WARC format page archiving
   - Hash verification integration
   - Screenshot + metadata packaging
