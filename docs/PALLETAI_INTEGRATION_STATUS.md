# PalletAI Integration Status

**Date**: 2026-01-16
**Integration Version**: v1.0.0
**Status**: OPERATIONAL

## Overview

Basset Hound is integrated with PalletAI as an **external MCP (Model Context Protocol) service**. PalletAI agents can discover and invoke Basset Hound tools dynamically without hardcoded tool definitions.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              PalletAI                                        │
│                      (Agent Orchestration)                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     UniversalToolRegistry                            │    │
│  │                (src/core/tool_registry.py)                          │    │
│  │                                                                      │    │
│  │  Discovers tools from:                                               │    │
│  │  • Local MCP Server (FastMCP) - 20 tools                            │    │
│  │  • ResearchHub MCP API - 34 tools                                   │    │
│  │  • Basset Hound MCP API - 130 tools ← THIS INTEGRATION              │    │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                     │                                        │
│                                     ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        PromptManager                                 │    │
│  │  Injects tool documentation into agent system prompts               │    │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                     │                                        │
└─────────────────────────────────────┼────────────────────────────────────────┘
                                      │
                                      │ HTTP/REST
                                      │ Port 8000 (default)
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                             Basset Hound                                     │
│                          (This Service)                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  MCP API Endpoints:                                                          │
│  • GET  /mcp/tools           - List all available tools                     │
│  • GET  /mcp/tools/{name}    - Get tool info                                │
│  • GET  /mcp/tools?category= - Filter by category                           │
│  • POST /mcp/execute         - Execute a tool                               │
│  • POST /mcp/batch           - Batch execute tools                          │
│  • POST /mcp/validate        - Validate parameters                          │
│  • GET  /mcp/health          - Service health check                         │
│                                                                              │
│  130 Tools Across 18 Categories:                                             │
│  • entities (6): create_entity, get_entity, update_entity, etc.             │
│  • projects (3): create_project, list_projects, get_project                 │
│  • relationships (7): create_relationship, get_relationships, etc.          │
│  • investigations (16): create_investigation, add_task, log_activity, etc.  │
│  • sock_puppets (13): create_sock_puppet, deploy_sock_puppet, etc.          │
│  • verification (12): verify_email, verify_phone, verify_crypto, etc.       │
│  • orphans (11): find_orphans, link_orphan, get_orphan_stats, etc.          │
│  • browser_integration (11): capture_evidence, submit_form_data, etc.       │
│  • analysis (6): find_paths, compute_centrality, detect_clusters, etc.      │
│  • provenance (8): record_source, get_chain_of_custody, etc.                │
│  • auto_linking (4): detect_duplicates, merge_entities, etc.                │
│  • search (2): full_text_search, identifier_search                          │
│  • schema (6): get_schema, validate_profile, list_entity_types, etc.        │
│  • file_hashing (4): compute_hash, find_duplicates, etc.                    │
│  • reports (2): create_report, get_report                                   │
│  • data_management (8): Smart suggestion data management                    │
│  • suggestions (5): compute_suggestions, get_suggestion, etc.               │
│  • linking (6): accept_link, reject_link, defer_link, etc.                  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Integration Direction

**CRITICAL**: The integration is **one-way**:

| Direction | Supported | Description |
|-----------|-----------|-------------|
| PalletAI → Basset Hound | ✅ YES | PalletAI agents can call Basset Hound tools |
| Basset Hound → PalletAI | ❌ NO | Basset Hound does NOT consume PalletAI services |

**Basset Hound is the source of truth for OSINT data:**
- Entity storage and management
- Relationship graphs
- Investigation workflows
- Provenance tracking
- Verification results

**PalletAI updates flow TO Basset Hound, never FROM:**
- If Basset Hound's API changes, PalletAI must update its client
- If Basset Hound adds new tools, PalletAI discovers them automatically
- Basset Hound never imports PalletAI code or configuration

## Exposed Endpoints for PalletAI

### Tool Discovery
```
GET http://localhost:8000/mcp/tools
```

Response format:
```json
{
  "tools": [
    {
      "name": "create_entity",
      "description": "Create a new entity in a project...",
      "category": "entities",
      "parameters": [
        {"name": "project_id", "type": "string", "required": true},
        {"name": "profile", "type": "object", "required": true},
        {"name": "validate", "type": "boolean", "required": false, "default": true}
      ],
      "inputSchema": {...}
    }
    // ... 129 more tools
  ],
  "total": 130,
  "categories": ["entities", "projects", "relationships", ...]
}
```

### Category Filtering
```
GET http://localhost:8000/mcp/tools?category=investigations
```

### Tool Execution
```
POST http://localhost:8000/mcp/execute
Content-Type: application/json

{
  "tool": "create_entity",
  "params": {
    "project_id": "my-investigation",
    "profile": {
      "basic_info": {
        "name": "John Doe",
        "aliases": ["JD", "Johnny"]
      }
    }
  }
}
```

Response:
```json
{
  "success": true,
  "tool": "create_entity",
  "result": {
    "id": "entity-uuid-here",
    "created_at": "2026-01-16T...",
    "profile": {...}
  },
  "error": null,
  "execution_time_ms": 42
}
```

### Batch Execution
```
POST http://localhost:8000/mcp/batch
Content-Type: application/json

{
  "tools": [
    {"tool": "verify_email", "params": {"email": "test@example.com"}},
    {"tool": "verify_phone", "params": {"phone": "+1234567890"}}
  ],
  "parallel": true
}
```

### Health Check
```
GET http://localhost:8000/mcp/health

{
  "status": "healthy",
  "service": "basset-hound-mcp",
  "version": "1.0.0",
  "timestamp": "2026-01-16T...",
  "tools_available": 130,
  "database": "connected"
}
```

## Configuration

### Default Ports

| Service | Port | Notes |
|---------|------|-------|
| Basset Hound API | 8000 | MCP endpoints at /mcp/* |
| Neo4j | 7687 | Graph database |
| Neo4j Browser | 7474 | Web interface |

### PalletAI Client Configuration

```python
# In PalletAI: src/core/tool_executor.py
EXTERNAL_SERVICE_CONFIG = {
    "basset_hound": {
        "base_url": "http://localhost:8000",
        "execute_endpoint": "/mcp/execute",
        "timeout": 60.0,
    }
}
```

## Testing the Integration

### From PalletAI Side

```bash
# Test tool discovery
curl http://localhost:8000/mcp/tools | jq '.tools | length'
# Expected: 130

# Test tool execution
curl -X POST http://localhost:8000/mcp/execute \
  -H "Content-Type: application/json" \
  -d '{"tool": "list_projects", "params": {}}'
```

### From Basset Hound Side

```bash
# Verify MCP endpoints are working
curl http://localhost:8000/mcp/health
curl http://localhost:8000/mcp/tools | jq '.total'
```

## Tool Categories Reference

| Category | Tools | Description |
|----------|-------|-------------|
| entities | 6 | Entity CRUD operations |
| projects | 3 | Project management |
| relationships | 7 | Entity relationship management |
| investigations | 16 | Investigation lifecycle, tasks, milestones |
| sock_puppets | 13 | Undercover identity management |
| verification | 12 | Email, phone, crypto, domain verification |
| orphans | 11 | Unlinked identifier management |
| browser_integration | 11 | Evidence capture, form data submission |
| analysis | 6 | Graph analysis (paths, centrality, clusters) |
| provenance | 8 | Data source and chain of custody tracking |
| auto_linking | 4 | Duplicate detection and entity merging |
| search | 2 | Full-text and identifier search |
| schema | 6 | Schema introspection and validation |
| file_hashing | 4 | File hash computation and deduplication |
| reports | 2 | Report creation and retrieval |
| data_management | 8 | Smart suggestion data management |
| suggestions | 5 | On-demand suggestion computation |
| linking | 6 | Linking actions on suggestions |

## Troubleshooting

### Basset Hound Not Reachable

1. Check if the server is running:
   ```bash
   curl http://localhost:8000/health
   ```

2. Check logs:
   ```bash
   docker logs basset_api
   # or
   tail -f logs/basset-hound.log
   ```

3. Verify Neo4j is connected:
   ```bash
   curl http://localhost:8000/mcp/health | jq '.database'
   ```

### Tool Discovery Timeout

If PalletAI can't discover Basset Hound tools:

1. Increase timeout in `tool_registry.py`:
   ```python
   registry = UniversalToolRegistry(discovery_timeout=30.0)
   ```

2. Force refresh the cache:
   ```python
   await registry.discover_all_tools(force=True)
   ```

### Tool Execution Errors

Common errors and solutions:

| Error | Cause | Solution |
|-------|-------|----------|
| `Project not found` | Invalid project_id | Use project safe_name or UUID |
| `Entity not found` | Invalid entity_id | Check entity exists in project |
| `Database disconnected` | Neo4j down | Restart Neo4j container |

## Related Documentation

- **PalletAI Side**:
  - `agent_manager_docs/findings/UNIVERSAL_TOOL_AWARENESS.md`
  - `agent_manager_docs/findings/researchhub-integration/BASSET_HOUND_INTEGRATION_STATUS.md`
  - `agent_manager_docs/ROADMAP.md` (v0.7.1 section)

- **Basset Hound Side**:
  - `docs/SCOPE.md` - Project scope and boundaries
  - `docs/API.md` - Full API documentation
  - `docs/INTEGRATION-ARCHITECTURE.md` - Integration patterns

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v1.0.0 | 2026-01-16 | Initial MCP HTTP adapter implementation |
