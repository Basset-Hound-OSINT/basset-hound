# FastMCP Server Implementation

## Overview

Implemented a FastMCP server that enables external applications to leverage Basset Hound's entity relationship management capabilities through the Model Context Protocol.

## Implementation

### File: `mcp/server.py`

The MCP server is built using the FastMCP library and provides 15 tools for entity management.

### Available Tools

#### Entity Management
1. **create_entity** - Create a new entity in a project
   - Parameters: `project_safe_name`, `profile_data` (optional)
   - Returns: Created entity with ID

2. **get_entity** - Retrieve a specific entity
   - Parameters: `project_safe_name`, `entity_id`
   - Returns: Full entity data with profile

3. **update_entity** - Update entity profile data
   - Parameters: `project_safe_name`, `entity_id`, `profile_data`
   - Returns: Updated entity

4. **delete_entity** - Remove an entity
   - Parameters: `project_safe_name`, `entity_id`
   - Returns: Success status

5. **list_entities** - List all entities in a project
   - Parameters: `project_safe_name`
   - Returns: Array of entities

#### Relationship Management
6. **link_entities** - Create relationship between entities
   - Parameters: `project_safe_name`, `source_id`, `target_id`
   - Returns: Updated relationships

7. **unlink_entities** - Remove relationship
   - Parameters: `project_safe_name`, `source_id`, `target_id`
   - Returns: Updated relationships

8. **get_related** - Get all related entities
   - Parameters: `project_safe_name`, `entity_id`
   - Returns: Tagged people and transitive relationships

#### Search Tools
9. **search_entities** - Full-text search across profiles
   - Parameters: `project_safe_name`, `query`
   - Returns: Matching entities

10. **search_by_identifier** - Search by specific field
    - Parameters: `project_safe_name`, `field_type`, `value`
    - Returns: Matching entities

#### Project Management
11. **create_project** - Create new investigation project
    - Parameters: `project_name`
    - Returns: Created project with ID

12. **list_projects** - List all projects
    - Parameters: none
    - Returns: Array of projects

13. **get_project** - Get project details
    - Parameters: `project_safe_name`
    - Returns: Project with people

#### Report Management
14. **create_report** - Create investigation report
    - Parameters: `project_safe_name`, `entity_id`, `tool_name`, `content`
    - Returns: Report metadata

15. **get_reports** - List entity reports
    - Parameters: `project_safe_name`, `entity_id`
    - Returns: Array of report filenames

## Usage Examples

### Starting the MCP Server

```bash
# Run the MCP server
python -m mcp.server
```

### Connecting from External Applications

```python
from mcp import Client

async with Client("basset-hound-mcp") as client:
    # Create a project
    project = await client.call_tool(
        "create_project",
        {"project_name": "Investigation Alpha"}
    )

    # Create an entity
    entity = await client.call_tool(
        "create_entity",
        {
            "project_safe_name": "investigation_alpha",
            "profile_data": {
                "core": {
                    "name": [{"first_name": "John", "last_name": "Doe"}],
                    "email": ["john@example.com"]
                },
                "social": {
                    "twitter": "@johndoe"
                }
            }
        }
    )

    # Search for entities
    results = await client.call_tool(
        "search_entities",
        {
            "project_safe_name": "investigation_alpha",
            "query": "john"
        }
    )

    # Link entities
    await client.call_tool(
        "link_entities",
        {
            "project_safe_name": "investigation_alpha",
            "source_id": entity["id"],
            "target_id": "other-entity-id"
        }
    )
```

## Integration Patterns

### 1. AI Agent Integration
AI agents can use the MCP server to:
- Store and retrieve investigation findings
- Manage entity relationships
- Generate and store reports
- Search across collected intelligence

### 2. Automation Pipelines
OSINT automation tools can:
- Push results directly to Basset Hound
- Create entities from discovered profiles
- Link related entities automatically
- Generate structured reports

### 3. Data Enrichment
External services can:
- Pull entity data for enrichment
- Update profiles with new information
- Track relationship changes

## Configuration

The MCP server uses the same Neo4j configuration as the main application:

```python
# Environment variables
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
```

## Security Considerations

1. **Authentication**: The MCP server inherits authentication from the calling context
2. **Authorization**: Tool access can be scoped per client
3. **Data Validation**: All inputs are validated before processing
4. **Path Security**: File operations prevent path traversal

## Future Enhancements

1. **Streaming Support**: Real-time updates for long-running searches
2. **Batch Operations**: Bulk entity creation/update
3. **Event Subscriptions**: Notify on entity changes
4. **Custom Tools**: Dynamic tool registration based on config
