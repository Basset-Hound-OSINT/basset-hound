# Dynamic MCP Schema Introspection

## Overview

Enhanced the MCP server to dynamically reflect the `data_config.yaml` schema, allowing LLM tools to understand and work with the current entity configuration without requiring code changes.

## Implementation Date

2025-12-27

## Problem Statement

The original MCP server had hardcoded entity structures. When the `data_config.yaml` schema was updated (adding new fields, sections, or identifiers), the MCP server didn't reflect these changes. This meant:

1. LLMs couldn't discover available entity fields
2. No validation of entity data against the schema
3. Schema changes required MCP server code changes
4. No way to introspect what identifiers were available for entity resolution

## Solution

Added schema introspection tools to the MCP server that load and expose `data_config.yaml` structure dynamically. The schema is cached at startup and can be reloaded without restart.

## New MCP Tools

### get_schema()
Returns the complete schema structure from data_config.yaml.

```json
{
  "version": "3.0",
  "entity_type": "Person",
  "sections": [...],
  "field_types": {...},
  "total_sections": 25,
  "total_field_types": 12
}
```

### get_sections()
Returns all sections with their fields summarized.

```json
{
  "count": 25,
  "sections": [
    {
      "id": "core",
      "name": "Personal Information",
      "icon": "fa-id-card",
      "sensitive": false,
      "description": "Core identity...",
      "field_count": 7,
      "fields": [
        {
          "id": "email",
          "type": "email",
          "label": "Email Addresses",
          "multiple": true,
          "identifier": true,
          "searchable": true
        }
      ]
    }
  ]
}
```

### get_identifiers()
Returns all fields marked as `identifier: true` for entity resolution.

```json
{
  "count": 45,
  "identifiers": [
    {
      "path": "core.email",
      "section_id": "core",
      "section_name": "Personal Information",
      "field_id": "email",
      "field_type": "email",
      "label": "Email Addresses",
      "multiple": true
    },
    {
      "path": "social_major.instagram.username",
      "section_id": "social_major",
      "section_name": "Major Social Platforms",
      "field_id": "instagram",
      "component_id": "username",
      "field_type": "string",
      "label": "Username",
      "parent_label": "Instagram",
      "multiple": true
    }
  ]
}
```

### get_field_info(section_id, field_id)
Returns detailed information about a specific field.

```json
{
  "section_id": "core",
  "section_name": "Personal Information",
  "field": {
    "id": "email",
    "type": "email",
    "multiple": true,
    "label": "Email Addresses",
    "searchable": true,
    "identifier": true
  },
  "type_info": {
    "html_input": "email",
    "pattern": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
  }
}
```

### validate_profile_data(profile)
Validates entity profile data against the schema.

```json
Request:
{
  "core": {
    "email": ["john@example.com"],
    "invalid_field": "value"
  },
  "unknown_section": {}
}

Response:
{
  "valid": false,
  "errors": [
    "Unknown section: 'unknown_section'",
    "Unknown field: 'invalid_field' in section 'core'"
  ],
  "warnings": [],
  "validated_sections": 2,
  "validated_fields": 2
}
```

### reload_schema()
Reloads the schema from disk for hot-reload without restart.

```json
{
  "success": true,
  "version": "3.0",
  "section_count": 25,
  "message": "Schema configuration reloaded successfully"
}
```

## Entity Tool Updates

Updated `create_entity()` and `update_entity()` to include optional schema validation:

```python
@mcp.tool()
def create_entity(project_id: str, profile: dict, validate: bool = True) -> dict:
    """
    Create a new entity in a project.

    The profile data is validated against the schema defined in data_config.yaml.
    Validation can be disabled for legacy data or special cases.
    """
    # Validate profile against schema
    if validate and profile:
        is_valid, errors = validate_entity_profile(profile)
        if not is_valid:
            return {
                "error": "Profile validation failed",
                "validation_errors": errors
            }
    # ... create entity
```

## Implementation Details

### Schema Loading

```python
from config_loader import load_config, get_section_by_id, get_field_by_id

_schema_config: Optional[Dict] = None

def get_schema_config() -> Dict:
    """Lazy-load and cache schema configuration."""
    global _schema_config
    if _schema_config is None:
        _schema_config = load_config()
    return _schema_config
```

### Identifier Discovery

The `get_identifiers()` tool traverses the schema tree to find:
1. Top-level fields with `identifier: true`
2. Component fields with `identifier: true`

This enables LLMs to understand which fields can be used for entity matching and deduplication.

### Validation Logic

Validation checks:
1. Section existence in schema
2. Field existence within sections
3. Component existence for component-type fields
4. Multiple field values should be lists
5. Component field values should be dictionaries

## Benefits

1. **Self-Documenting API**: LLMs can discover available fields
2. **Data Integrity**: Validates entities before creation/update
3. **Hot Reload**: Schema changes don't require restart
4. **Identifier Discovery**: Enables smart entity matching
5. **Configuration-Driven**: No code changes needed for schema updates

## Files Modified

| File | Changes |
|------|---------|
| `mcp/server.py` | Added 6 new tools, validation logic, schema caching (~250 lines) |
| `config_loader.py` | Used existing helper functions |

## Use Cases for LLMs

### Entity Creation with Validation
```
LLM: "I need to create a new person entity with email john@example.com"
1. Call get_sections() to understand available fields
2. Call create_entity() with validate=True
3. If validation fails, adjust data and retry
```

### Entity Resolution
```
LLM: "Find all entities with matching identifiers"
1. Call get_identifiers() to discover identifier fields
2. Call search_by_identifier() for each identifier type
3. Merge results and suggest potential duplicates
```

### Schema-Aware Data Entry
```
LLM: "What social platforms can I record for this person?"
1. Call get_sections() and filter for social-related sections
2. Present available platforms with their field structures
3. Guide user through data entry with proper field types
```

## Testing

Tested through:
1. Python syntax verification (`py_compile`)
2. Import verification
3. Config loader function tests
4. get_identifiers logic simulation
5. validate_profile_data logic simulation

## Future Enhancements

1. **Type Coercion**: Auto-convert values to expected types
2. **Required Field Validation**: Enforce required fields
3. **Pattern Validation**: Validate against regex patterns
4. **Cross-Field Validation**: Check field dependencies
5. **Schema Versioning**: Track schema version changes
6. **Migration Support**: Auto-migrate data between schema versions
