# Integration Architecture

## System Overview

This document describes how the four repositories can be integrated into a cohesive OSINT and cybersecurity automation platform.

## High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                                 USER INTERFACE                                │
│  ┌────────────────────────┐  ┌────────────────────────┐  ┌────────────────┐  │
│  │   basset-hound Web UI  │  │   palletAI Agent CLI   │  │ Chrome Browser │  │
│  │   (Profile Management) │  │   (Task Management)    │  │ (Extension UI) │  │
│  └───────────┬────────────┘  └───────────┬────────────┘  └───────┬────────┘  │
└──────────────┼───────────────────────────┼───────────────────────┼───────────┘
               │                           │                       │
               ▼                           ▼                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                              ORCHESTRATION LAYER                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                         palletAI Agent Manager                          │ │
│  │  ┌─────────────────┐  ┌──────────────────┐  ┌─────────────────────────┐│ │
│  │  │ Agent Executor  │  │ Multi-Agent      │  │ Task DAG Engine        ││ │
│  │  │ (DAG Runner)    │  │ Coordinator      │  │ (Dependency Tracking)  ││ │
│  │  └────────┬────────┘  └────────┬─────────┘  └────────────┬────────────┘│ │
│  │           │                    │                          │             │ │
│  │           └────────────────────┴──────────────────────────┘             │ │
│  │                                │                                         │ │
│  │  ┌─────────────────────────────┴─────────────────────────────────────┐  │ │
│  │  │                    MCP Tool Executor                               │  │ │
│  │  │  Routes tool calls to appropriate handlers                         │  │ │
│  │  └────────────────────────────────────────────────────────────────────┘  │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
               │                           │                       │
               ▼                           ▼                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                               TOOL LAYER                                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌──────────┐ │
│  │ basset-hound    │  │ osint-resources │  │ Browser Tools   │  │ System   │ │
│  │ MCP Server      │  │ Knowledge Base  │  │ (Extension)     │  │ Tools    │ │
│  │                 │  │                 │  │                 │  │          │ │
│  │ • create_entity │  │ • query_tools   │  │ • navigate      │  │ • nmap   │ │
│  │ • update_entity │  │ • get_tool_info │  │ • fill_form     │  │ • whois  │ │
│  │ • add_relation  │  │ • find_by_input │  │ • click         │  │ • dig    │ │
│  │ • create_report │  │                 │  │ • screenshot    │  │ • curl   │ │
│  │ • search_entity │  │                 │  │ • get_content   │  │ • shodan │ │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘  └────┬─────┘ │
└───────────┼────────────────────┼────────────────────┼────────────────┼───────┘
            │                    │                    │                │
            ▼                    ▼                    ▼                ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                               DATA LAYER                                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐               │
│  │    Neo4j        │  │   PostgreSQL    │  │  File System    │               │
│  │ (Graph DB)      │  │ + pgvector      │  │                 │               │
│  │                 │  │                 │  │                 │               │
│  │ • Entities      │  │ • Agents        │  │ • Reports       │               │
│  │ • Relationships │  │ • Tasks         │  │ • Screenshots   │               │
│  │ • Files         │  │ • KB Embeddings │  │ • Evidence      │               │
│  │ • Reports       │  │ • Chat History  │  │ • Tool Outputs  │               │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘               │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Component Integration Details

### 1. palletAI ↔ basset-hound Integration

Create a new MCP server for basset-hound operations.

**File: `palletAI/agent_manager/mcp_servers/basset_hound/server.py`**

```python
from fastmcp import FastMCP
import httpx

mcp = FastMCP("basset-hound")

BASSET_HOUND_URL = "http://localhost:5001"  # basset-hound Flask app

@mcp.tool
async def create_entity(
    project_id: str,
    entity_name: str,
    entity_type: str = "person",
    initial_data: dict = None
) -> dict:
    """
    Create a new entity (person) in basset-hound.

    Args:
        project_id: The project to add entity to
        entity_name: Display name for the entity
        entity_type: Type of entity (default: person)
        initial_data: Initial field values

    Returns:
        Created entity ID and status
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASSET_HOUND_URL}/add_person",
            json={
                "project_id": project_id,
                "name": entity_name,
                "type": entity_type,
                "data": initial_data or {}
            }
        )
        return response.json()

@mcp.tool
async def update_entity(
    entity_id: str,
    field_updates: dict
) -> dict:
    """
    Update an existing entity's fields.

    Args:
        entity_id: The entity to update
        field_updates: Dictionary of field_id -> value updates
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASSET_HOUND_URL}/update_person/{entity_id}",
            json=field_updates
        )
        return response.json()

@mcp.tool
async def create_relationship(
    source_entity_id: str,
    target_entity_id: str,
    relationship_type: str = "related_to"
) -> dict:
    """
    Create a relationship between two entities.

    Args:
        source_entity_id: The source entity
        target_entity_id: The target entity
        relationship_type: Type of relationship
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASSET_HOUND_URL}/tag_person/{source_entity_id}",
            json={
                "tagged_person_id": target_entity_id,
                "relationship_type": relationship_type
            }
        )
        return response.json()

@mcp.tool
async def create_osint_report(
    entity_id: str,
    tool_name: str,
    report_content: str,
    findings: list = None
) -> dict:
    """
    Create an OSINT report for an entity.

    Args:
        entity_id: The entity this report is about
        tool_name: Name of the tool that generated findings
        report_content: Markdown content of the report
        findings: Structured list of findings
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASSET_HOUND_URL}/person/{entity_id}/reports",
            json={
                "tool_name": tool_name,
                "content": report_content,
                "findings": findings or []
            }
        )
        return response.json()

@mcp.tool
async def search_entities(
    query: str,
    project_id: str = None
) -> list:
    """
    Search for entities matching a query.

    Args:
        query: Search term
        project_id: Optional project filter
    """
    async with httpx.AsyncClient() as client:
        params = {"q": query}
        if project_id:
            params["project_id"] = project_id
        response = await client.get(
            f"{BASSET_HOUND_URL}/search",
            params=params
        )
        return response.json()

@mcp.tool
async def get_entity_details(entity_id: str) -> dict:
    """
    Get full details of an entity including relationships.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASSET_HOUND_URL}/get_person/{entity_id}"
        )
        return response.json()
```

### 2. osint-resources Knowledge Base Ingestion

**File: `palletAI/agent_manager/repository_kbs.yaml` (add entry)**

```yaml
repositories:
  - name: osint-resources
    enabled: true
    path: ~/osint-resources/src/
    file_patterns:
      - "**/*.md"
    exclude_patterns:
      - "**/README.md"
      - "**/SUMMARY.md"
    auto_ingest: true
    chunking:
      strategy: semantic
      chunk_size: 1024
      chunk_overlap: 100
    metadata_extraction:
      enabled: true
      patterns:
        - name: tool_category
          regex: "^# (.+)$"
        - name: tool_url
          regex: "\\[.+\\]\\((https?://[^)]+)\\)"
```

**Tool Query Enhancement for osint-resources**

```python
@mcp.tool
async def find_osint_tools(
    input_type: str,
    category: str = None,
    max_results: int = 10
) -> list:
    """
    Find OSINT tools that accept a specific input type.

    Args:
        input_type: Type of input (email, phone, username, domain, ip)
        category: Optional category filter (social, records, breaches)
        max_results: Maximum tools to return

    Returns:
        List of tools with name, URL, and usage info
    """
    # Query the RAG system for relevant tools
    query = f"OSINT tools for {input_type}"
    if category:
        query += f" in category {category}"

    results = await rag_engine.query(
        query_text=query,
        agent_type="osint_agent",
        filters={"kb_name": "osint-resources"},
        top_k=max_results
    )

    # Parse tool information from results
    tools = []
    for result in results:
        # Extract tool info using regex patterns
        tool_info = extract_tool_info(result.content)
        if tool_info:
            tools.append(tool_info)

    return tools
```

### 3. Browser Extension ↔ palletAI Integration

**Communication Protocol via WebSocket**

```
┌────────────────┐         WebSocket          ┌────────────────┐
│   palletAI     │◄───────────────────────────│   Extension    │
│  Agent Manager │        Commands            │  Background.js │
│                │────────────────────────────►│                │
│                │        Responses           │                │
└────────────────┘                            └────────────────┘
        │                                             │
        │                                             ▼
        │                                     ┌────────────────┐
        │                                     │  Content.js    │
        │                                     │  (Per Tab)     │
        │                                     └────────────────┘
        │                                             │
        ▼                                             ▼
┌────────────────┐                            ┌────────────────┐
│   Task DAG     │                            │   Web Page     │
│   Execution    │                            │   DOM          │
└────────────────┘                            └────────────────┘
```

**Message Protocol**

```typescript
// Command from palletAI to Extension
interface AgentCommand {
  command_id: string;
  type: "navigate" | "fill_form" | "click" | "get_content" | "screenshot" | "wait";
  params: {
    url?: string;
    selector?: string;
    value?: string;
    timeout?: number;
    fields?: Record<string, string>;
  };
}

// Response from Extension to palletAI
interface CommandResponse {
  command_id: string;
  success: boolean;
  result?: any;
  error?: string;
  screenshot?: string;  // Base64 encoded
  page_state?: {
    url: string;
    title: string;
    forms: FormInfo[];
  };
}

interface FormInfo {
  form_id: string;
  action: string;
  method: string;
  fields: FieldInfo[];
}

interface FieldInfo {
  selector: string;
  type: string;
  name: string;
  label: string;
  required: boolean;
  value: string;
}
```

**palletAI Browser Tool Implementation**

```python
@mcp.tool
async def browser_navigate(url: str, wait_for: str = None) -> dict:
    """
    Navigate browser to URL.

    Args:
        url: URL to navigate to
        wait_for: Optional CSS selector to wait for
    """
    command = {
        "command_id": str(uuid.uuid4()),
        "type": "navigate",
        "params": {"url": url, "wait_for": wait_for}
    }
    return await send_browser_command(command)

@mcp.tool
async def browser_fill_form(fields: dict, submit: bool = False) -> dict:
    """
    Fill form fields in the browser.

    Args:
        fields: Dictionary mapping selectors to values
        submit: Whether to submit the form after filling
    """
    command = {
        "command_id": str(uuid.uuid4()),
        "type": "fill_form",
        "params": {"fields": fields, "submit": submit}
    }
    return await send_browser_command(command)

@mcp.tool
async def browser_get_page_content(selector: str = "body") -> str:
    """
    Get text content from the page.
    """
    command = {
        "command_id": str(uuid.uuid4()),
        "type": "get_content",
        "params": {"selector": selector}
    }
    return await send_browser_command(command)

@mcp.tool
async def browser_screenshot() -> str:
    """
    Take a screenshot of the current page.
    Returns base64 encoded image.
    """
    command = {
        "command_id": str(uuid.uuid4()),
        "type": "screenshot",
        "params": {}
    }
    return await send_browser_command(command)
```

## Data Flow Examples

### Example 1: OSINT Email Investigation

```
1. User Input: "Investigate email: target@example.com"

2. palletAI Agent Manager:
   └─ Spawns OSINT Agent with task

3. OSINT Agent:
   ├─ Queries osint-resources KB: "tools for email investigation"
   ├─ Gets list: [HaveIBeenPwned, Hunter.io, Holehe, EmailRep]
   │
   ├─ For each tool:
   │   ├─ Check if web-based → Use browser_navigate + browser_fill_form
   │   ├─ Check if CLI-based → Use execute_command
   │   └─ Parse results
   │
   ├─ Creates entity in basset-hound: create_entity("target@example.com")
   ├─ Updates with findings: update_entity(entity_id, findings)
   └─ Creates report: create_osint_report(entity_id, "email_investigation", report)

4. Results stored in:
   ├─ Neo4j (basset-hound): Entity + relationships
   ├─ PostgreSQL (palletAI): Task history + agent memories
   └─ File system: Screenshots + raw outputs
```

### Example 2: Multi-Agent Reconnaissance

```
1. User Input: "Full recon on domain: target.com"

2. palletAI Coordinator:
   └─ Spawns Reconnaissance Orchestrator Agent

3. Orchestrator:
   ├─ Spawns Coworker: DNS Agent
   │   └─ Task: "Enumerate DNS records for target.com"
   │   └─ Tools: dig, dnsenum, execute_command
   │
   ├─ Spawns Coworker: Subdomain Agent
   │   └─ Task: "Find all subdomains"
   │   └─ Tools: subfinder, amass, web_search
   │
   ├─ Spawns Coworker: Web Tech Agent
   │   └─ Task: "Identify web technologies"
   │   └─ Tools: browser_navigate, browser_get_page_content
   │
   └─ Waits for all coworkers (Task DAG)

4. Aggregation:
   ├─ Orchestrator collects results from all coworkers
   ├─ Creates entity hierarchy in basset-hound:
   │   └─ Domain → Subdomains → IPs → Services
   ├─ Creates relationships between discovered entities
   └─ Generates comprehensive report
```

## Security Considerations

### 1. API Authentication
- Add JWT authentication to basset-hound
- Store credentials in palletAI environment
- Validate all tool requests

### 2. Browser Extension Security
- WebSocket connection only from localhost
- Command validation before execution
- Sandbox sensitive operations

### 3. Scope Constraints
- Limit agent capabilities per task
- Prevent recursive coworker spawning
- Timeout long-running operations

### 4. Data Protection
- Encrypt sensitive fields in Neo4j
- Secure file storage paths
- Audit logging for all operations
