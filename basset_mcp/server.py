"""
Basset Hound MCP Server

FastMCP server providing tools for entity relationship management in Basset Hound.
Implements entity CRUD, relationship management, search, project management, reports,
and dynamic schema introspection based on data_config.yaml.
"""

import os
import sys
import json
from datetime import datetime
from uuid import uuid4
from typing import Optional, Any, Dict, List

from mcp.server.fastmcp import FastMCP

# Add parent directory to path to import neo4j_handler and config_loader
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from neo4j_handler import Neo4jHandler
from config_loader import load_config, get_section_by_id, get_field_by_id

# Initialize FastMCP server
mcp = FastMCP("basset-hound")

# Lazy initialization of Neo4j handler
_neo4j_handler: Optional[Neo4jHandler] = None

# Lazy initialization of schema config
_schema_config: Optional[Dict] = None


def get_schema_config() -> Dict:
    """
    Get or load the schema configuration from data_config.yaml.

    The config is loaded once and cached for the lifetime of the server.
    This enables dynamic schema introspection without repeated file reads.

    Returns:
        The parsed data_config.yaml as a dictionary
    """
    global _schema_config
    if _schema_config is None:
        _schema_config = load_config()
    return _schema_config


def reload_schema_config() -> Dict:
    """
    Force reload the schema configuration from data_config.yaml.

    Useful when the config file has been modified and needs to be refreshed.

    Returns:
        The freshly parsed data_config.yaml as a dictionary
    """
    global _schema_config
    _schema_config = load_config()
    return _schema_config


def get_neo4j_handler() -> Neo4jHandler:
    """Get or create Neo4j handler instance."""
    global _neo4j_handler
    if _neo4j_handler is None:
        _neo4j_handler = Neo4jHandler()
    return _neo4j_handler


def get_project_safe_name(project_id: str) -> Optional[str]:
    """Get project safe_name from project_id (which could be id or safe_name)."""
    handler = get_neo4j_handler()

    # First try treating project_id as safe_name
    project = handler.get_project(project_id)
    if project:
        return project_id

    # Otherwise search through all projects
    projects = handler.get_all_projects()
    for p in projects:
        if p.get("id") == project_id:
            return p.get("safe_name")

    return None


def get_project_id_from_safe_name(safe_name: str) -> Optional[str]:
    """Get project id from safe_name."""
    handler = get_neo4j_handler()
    project = handler.get_project(safe_name)
    if project:
        return project.get("id")
    return None


# =============================================================================
# Schema Introspection Tools
# =============================================================================

@mcp.tool()
def get_schema() -> dict:
    """
    Get the complete schema structure from data_config.yaml.

    Returns the full schema including version, entity type, all sections with
    their fields, and field type definitions. This provides a comprehensive
    view of the data model used by Basset Hound.

    Returns:
        Complete schema structure with:
        - version: Schema version string
        - entity_type: The type of entity this schema describes
        - sections: List of all section definitions with fields
        - field_types: Mapping of field types to their HTML input types
    """
    config = get_schema_config()

    return {
        "version": config.get("version", "unknown"),
        "entity_type": config.get("entity_type", "unknown"),
        "sections": config.get("sections", []),
        "field_types": config.get("field_types", {}),
        "total_sections": len(config.get("sections", [])),
        "total_field_types": len(config.get("field_types", {}))
    }


@mcp.tool()
def get_sections() -> dict:
    """
    Get a list of all sections with their fields from the schema.

    Each section represents a logical grouping of related fields (e.g.,
    'core' for personal information, 'contact' for contact details).
    Returns section metadata and a summary of fields in each section.

    Returns:
        Dictionary with:
        - count: Total number of sections
        - sections: List of section summaries with id, name, icon, and field count
    """
    config = get_schema_config()
    sections = config.get("sections", [])

    section_summaries = []
    for section in sections:
        field_summaries = []
        for field in section.get("fields", []):
            field_summary = {
                "id": field.get("id"),
                "type": field.get("type"),
                "label": field.get("label", field.get("id")),
                "multiple": field.get("multiple", False),
                "identifier": field.get("identifier", False),
                "searchable": field.get("searchable", False)
            }
            # Include component info if present
            if field.get("type") == "component" and "components" in field:
                field_summary["components"] = [
                    {
                        "id": comp.get("id"),
                        "type": comp.get("type"),
                        "identifier": comp.get("identifier", False)
                    }
                    for comp in field.get("components", [])
                ]
            field_summaries.append(field_summary)

        section_summaries.append({
            "id": section.get("id"),
            "name": section.get("name"),
            "icon": section.get("icon"),
            "sensitive": section.get("sensitive", False),
            "description": section.get("description"),
            "field_count": len(section.get("fields", [])),
            "fields": field_summaries
        })

    return {
        "count": len(section_summaries),
        "sections": section_summaries
    }


@mcp.tool()
def get_identifiers() -> dict:
    """
    Get all fields marked as identifiers from the schema.

    Identifier fields are those that can uniquely identify an entity or
    serve as key lookup values (e.g., email addresses, usernames, phone
    numbers). This is useful for deduplication and entity resolution.

    Returns:
        Dictionary with:
        - count: Total number of identifier fields
        - identifiers: List of identifier field details including path,
          section, field id, type, and label
    """
    config = get_schema_config()
    sections = config.get("sections", [])

    identifiers = []
    for section in sections:
        section_id = section.get("id")
        for field in section.get("fields", []):
            field_id = field.get("id")
            field_type = field.get("type")

            # Check if field itself is an identifier
            if field.get("identifier", False):
                identifiers.append({
                    "path": f"{section_id}.{field_id}",
                    "section_id": section_id,
                    "section_name": section.get("name"),
                    "field_id": field_id,
                    "field_type": field_type,
                    "label": field.get("label", field_id),
                    "multiple": field.get("multiple", False)
                })

            # Check components for identifiers
            if field_type == "component" and "components" in field:
                for component in field.get("components", []):
                    if component.get("identifier", False):
                        comp_id = component.get("id")
                        identifiers.append({
                            "path": f"{section_id}.{field_id}.{comp_id}",
                            "section_id": section_id,
                            "section_name": section.get("name"),
                            "field_id": field_id,
                            "component_id": comp_id,
                            "field_type": component.get("type"),
                            "label": component.get("label", comp_id),
                            "parent_label": field.get("label", field_id),
                            "multiple": field.get("multiple", False)
                        })

    return {
        "count": len(identifiers),
        "identifiers": identifiers
    }


@mcp.tool()
def get_field_info(section_id: str, field_id: str) -> dict:
    """
    Get detailed information about a specific field in the schema.

    Retrieves the full field definition including type, label, validation
    rules, and component structure for composite fields.

    Args:
        section_id: The ID of the section containing the field (e.g., 'core', 'contact')
        field_id: The ID of the field (e.g., 'email', 'name')

    Returns:
        Field definition or error if not found. Includes:
        - id, type, label, multiple, identifier, searchable
        - components (for component type fields)
        - accept (for file type fields)
        - placeholder, description if defined
    """
    config = get_schema_config()

    # Find the section
    section = get_section_by_id(config, section_id)
    if not section:
        return {"error": f"Section not found: {section_id}"}

    # Find the field
    field = get_field_by_id(section, field_id)
    if not field:
        return {"error": f"Field not found: {field_id} in section {section_id}"}

    # Get field type info
    field_types = config.get("field_types", {})
    field_type = field.get("type", "string")
    type_info = field_types.get(field_type, {})

    result = {
        "section_id": section_id,
        "section_name": section.get("name"),
        "field": field.copy(),
        "type_info": type_info
    }

    return result


@mcp.tool()
def validate_profile_data(profile: dict) -> dict:
    """
    Validate profile data against the schema.

    Checks that all sections and fields in the provided profile data
    exist in the schema. Reports any unknown sections, fields, or
    type mismatches.

    Args:
        profile: Profile data dictionary with section.field structure

    Returns:
        Validation result with:
        - valid: Boolean indicating if validation passed
        - errors: List of validation error messages
        - warnings: List of validation warning messages
        - validated_sections: Number of sections checked
        - validated_fields: Number of fields checked
    """
    config = get_schema_config()
    sections = config.get("sections", [])

    # Build lookup maps for faster validation
    section_map = {s.get("id"): s for s in sections}

    errors = []
    warnings = []
    validated_sections = 0
    validated_fields = 0

    for section_id, section_data in profile.items():
        validated_sections += 1

        # Check if section exists
        if section_id not in section_map:
            errors.append(f"Unknown section: '{section_id}'")
            continue

        section_def = section_map[section_id]
        field_map = {f.get("id"): f for f in section_def.get("fields", [])}

        if not isinstance(section_data, dict):
            errors.append(f"Section '{section_id}' data must be a dictionary, got {type(section_data).__name__}")
            continue

        for field_id, field_value in section_data.items():
            validated_fields += 1

            # Check if field exists
            if field_id not in field_map:
                errors.append(f"Unknown field: '{field_id}' in section '{section_id}'")
                continue

            field_def = field_map[field_id]
            field_type = field_def.get("type", "string")
            is_multiple = field_def.get("multiple", False)

            # Validate multiple fields should be lists
            if is_multiple:
                if not isinstance(field_value, list) and field_value is not None:
                    warnings.append(
                        f"Field '{section_id}.{field_id}' is marked as multiple but value is not a list"
                    )

            # Validate component fields
            if field_type == "component" and "components" in field_def:
                component_map = {c.get("id"): c for c in field_def.get("components", [])}
                values_to_check = field_value if isinstance(field_value, list) else [field_value]

                for idx, value in enumerate(values_to_check):
                    if value is None:
                        continue
                    if not isinstance(value, dict):
                        errors.append(
                            f"Component field '{section_id}.{field_id}' expects dict, got {type(value).__name__}"
                        )
                        continue

                    for comp_id in value.keys():
                        if comp_id not in component_map:
                            errors.append(
                                f"Unknown component: '{comp_id}' in field '{section_id}.{field_id}'"
                            )

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "validated_sections": validated_sections,
        "validated_fields": validated_fields
    }


@mcp.tool()
def reload_schema() -> dict:
    """
    Reload the schema configuration from disk.

    Forces a refresh of the cached schema configuration by re-reading
    data_config.yaml. Use this after modifying the configuration file
    to pick up changes without restarting the server.

    Returns:
        Confirmation with:
        - success: Boolean indicating reload success
        - version: The schema version after reload
        - section_count: Number of sections loaded
    """
    try:
        config = reload_schema_config()
        return {
            "success": True,
            "version": config.get("version", "unknown"),
            "section_count": len(config.get("sections", [])),
            "message": "Schema configuration reloaded successfully"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to reload schema configuration"
        }


# =============================================================================
# Schema Validation Helpers
# =============================================================================

def validate_entity_profile(profile: dict) -> tuple[bool, List[str]]:
    """
    Internal helper to validate entity profile data against schema.

    Args:
        profile: Profile data dictionary

    Returns:
        Tuple of (is_valid, list of error messages)
    """
    result = validate_profile_data(profile)
    return result["valid"], result["errors"]


# =============================================================================
# Entity Tools
# =============================================================================

@mcp.tool()
def create_entity(project_id: str, profile: dict, validate: bool = True) -> dict:
    """
    Create a new entity in a project.

    The profile data is validated against the schema defined in data_config.yaml.
    Validation can be disabled for legacy data or special cases.

    Args:
        project_id: The project ID or safe_name
        profile: Entity profile data as a dictionary with section/field structure
        validate: Whether to validate profile against schema (default: True)

    Returns:
        The created entity data including generated ID, or error with validation details
    """
    handler = get_neo4j_handler()
    safe_name = get_project_safe_name(project_id)

    if not safe_name:
        return {"error": f"Project not found: {project_id}"}

    # Validate profile against schema
    if validate and profile:
        is_valid, errors = validate_entity_profile(profile)
        if not is_valid:
            return {
                "error": "Profile validation failed",
                "validation_errors": errors
            }

    # Prepare entity data
    entity_id = str(uuid4())
    entity_data = {
        "id": entity_id,
        "created_at": datetime.now().isoformat(),
        "profile": profile
    }

    # Create entity in Neo4j
    result = handler.create_person(safe_name, entity_data)

    if not result:
        return {"error": "Failed to create entity"}

    return result


@mcp.tool()
def get_entity(project_id: str, entity_id: str) -> dict:
    """
    Get an entity by ID.

    Args:
        project_id: The project ID or safe_name
        entity_id: The entity ID

    Returns:
        The entity data or error message
    """
    handler = get_neo4j_handler()
    safe_name = get_project_safe_name(project_id)

    if not safe_name:
        return {"error": f"Project not found: {project_id}"}

    entity = handler.get_person(safe_name, entity_id)

    if not entity:
        return {"error": f"Entity not found: {entity_id}"}

    return entity


@mcp.tool()
def update_entity(project_id: str, entity_id: str, profile: dict, validate: bool = True) -> dict:
    """
    Update an existing entity.

    The profile data is validated against the schema defined in data_config.yaml.
    Validation can be disabled for legacy data or special cases.

    Args:
        project_id: The project ID or safe_name
        entity_id: The entity ID to update
        profile: Updated profile data (partial updates supported)
        validate: Whether to validate profile against schema (default: True)

    Returns:
        The updated entity data or error message
    """
    handler = get_neo4j_handler()
    safe_name = get_project_safe_name(project_id)

    if not safe_name:
        return {"error": f"Project not found: {project_id}"}

    # Check entity exists
    existing = handler.get_person(safe_name, entity_id)
    if not existing:
        return {"error": f"Entity not found: {entity_id}"}

    # Validate profile against schema
    if validate and profile:
        is_valid, errors = validate_entity_profile(profile)
        if not is_valid:
            return {
                "error": "Profile validation failed",
                "validation_errors": errors
            }

    # Update entity
    updated_data = {"profile": profile}
    result = handler.update_person(safe_name, entity_id, updated_data)

    if not result:
        return {"error": "Failed to update entity"}

    return result


@mcp.tool()
def delete_entity(project_id: str, entity_id: str) -> dict:
    """
    Delete an entity.

    Args:
        project_id: The project ID or safe_name
        entity_id: The entity ID to delete

    Returns:
        Success status
    """
    handler = get_neo4j_handler()
    safe_name = get_project_safe_name(project_id)

    if not safe_name:
        return {"error": f"Project not found: {project_id}"}

    success = handler.delete_person(safe_name, entity_id)

    if not success:
        return {"error": f"Failed to delete entity: {entity_id}"}

    return {"success": True, "deleted_id": entity_id}


@mcp.tool()
def list_entities(project_id: str) -> dict:
    """
    List all entities in a project.

    Args:
        project_id: The project ID or safe_name

    Returns:
        List of entities in the project
    """
    handler = get_neo4j_handler()
    safe_name = get_project_safe_name(project_id)

    if not safe_name:
        return {"error": f"Project not found: {project_id}"}

    entities = handler.get_all_people(safe_name)

    return {
        "project_id": project_id,
        "count": len(entities),
        "entities": entities
    }


# =============================================================================
# Relationship Tools
# =============================================================================

# Valid relationship types for reference
VALID_RELATIONSHIP_TYPES = [
    # Generic
    "RELATED_TO", "KNOWS",
    # Professional
    "WORKS_WITH", "BUSINESS_PARTNER", "REPORTS_TO", "MANAGES",
    "COLLEAGUE", "CLIENT", "EMPLOYER", "EMPLOYEE",
    # Family
    "FAMILY", "MARRIED_TO", "PARENT_OF", "CHILD_OF", "SIBLING_OF", "SPOUSE",
    # Social
    "FRIEND", "ACQUAINTANCE", "NEIGHBOR",
    # Organizational
    "MEMBER_OF", "AFFILIATED_WITH",
    # Investigative
    "ASSOCIATED_WITH", "SUSPECTED_ASSOCIATE", "ALIAS_OF",
    # Communication
    "COMMUNICATES_WITH", "CONTACTED"
]

# Confidence levels
VALID_CONFIDENCE_LEVELS = ["confirmed", "high", "medium", "low", "unverified"]


@mcp.tool()
def get_relationship_types() -> dict:
    """
    Get all available relationship types and their categories.

    Returns a list of valid relationship types that can be used when
    creating or updating relationships between entities.

    Returns:
        Dictionary with:
        - types: List of all valid relationship type names
        - categories: Relationship types organized by category
        - confidence_levels: Valid confidence level values
    """
    return {
        "types": VALID_RELATIONSHIP_TYPES,
        "categories": {
            "generic": ["RELATED_TO", "KNOWS"],
            "professional": [
                "WORKS_WITH", "BUSINESS_PARTNER", "REPORTS_TO", "MANAGES",
                "COLLEAGUE", "CLIENT", "EMPLOYER", "EMPLOYEE"
            ],
            "family": [
                "FAMILY", "MARRIED_TO", "PARENT_OF", "CHILD_OF", "SIBLING_OF", "SPOUSE"
            ],
            "social": ["FRIEND", "ACQUAINTANCE", "NEIGHBOR"],
            "organizational": ["MEMBER_OF", "AFFILIATED_WITH"],
            "investigative": ["ASSOCIATED_WITH", "SUSPECTED_ASSOCIATE", "ALIAS_OF"],
            "communication": ["COMMUNICATES_WITH", "CONTACTED"]
        },
        "confidence_levels": VALID_CONFIDENCE_LEVELS
    }


@mcp.tool()
def link_entities(
    project_id: str,
    source_id: str,
    target_id: str,
    relationship_type: str = "RELATED_TO",
    confidence: str = "unverified",
    source: str = None,
    notes: str = None,
    bidirectional: bool = False
) -> dict:
    """
    Create a named relationship between two entities with properties.

    Uses the "Tagged People" section to store relationships, which provides
    bidirectional relationship tracking with transitive relationship detection.

    Args:
        project_id: The project ID or safe_name
        source_id: The source entity ID
        target_id: The target entity ID
        relationship_type: Type of relationship (e.g., WORKS_WITH, FRIEND, FAMILY)
            Valid types: RELATED_TO, KNOWS, WORKS_WITH, BUSINESS_PARTNER,
            REPORTS_TO, MANAGES, COLLEAGUE, CLIENT, EMPLOYER, EMPLOYEE,
            FAMILY, MARRIED_TO, PARENT_OF, CHILD_OF, SIBLING_OF, SPOUSE,
            FRIEND, ACQUAINTANCE, NEIGHBOR, MEMBER_OF, AFFILIATED_WITH,
            ASSOCIATED_WITH, SUSPECTED_ASSOCIATE, ALIAS_OF, COMMUNICATES_WITH, CONTACTED
        confidence: Confidence level (confirmed, high, medium, low, unverified)
        source: Source of the relationship information (e.g., "LinkedIn", "public records")
        notes: Additional notes about the relationship
        bidirectional: Whether to create the inverse relationship on target entity

    Returns:
        Success status and relationship info
    """
    handler = get_neo4j_handler()
    safe_name = get_project_safe_name(project_id)

    if not safe_name:
        return {"error": f"Project not found: {project_id}"}

    # Build properties
    properties = {
        "timestamp": datetime.now().isoformat()
    }
    if confidence:
        properties["confidence"] = confidence
    if source:
        properties["source"] = source
    if notes:
        properties["notes"] = notes

    # Create the relationship using the new handler method
    if bidirectional:
        result = handler.create_bidirectional_relationship(
            safe_name, source_id, target_id,
            relationship_type, properties
        )
        if not result:
            return {"error": "Failed to create bidirectional relationship"}

        return {
            "success": True,
            "source_id": source_id,
            "target_id": target_id,
            "relationship_type": relationship_type,
            "bidirectional": True,
            "forward": result.get("forward"),
            "reverse": result.get("reverse")
        }
    else:
        result = handler.create_relationship(
            safe_name, source_id, target_id,
            relationship_type, properties
        )

        if not result:
            return {"error": "Failed to create relationship"}

        return {
            "success": True,
            "source_id": source_id,
            "target_id": target_id,
            "relationship_type": relationship_type,
            "properties": result.get("properties", {})
        }


@mcp.tool()
def update_relationship(
    project_id: str,
    source_id: str,
    target_id: str,
    relationship_type: str = None,
    confidence: str = None,
    source: str = None,
    notes: str = None
) -> dict:
    """
    Update an existing relationship between two entities.

    Args:
        project_id: The project ID or safe_name
        source_id: The source entity ID
        target_id: The target entity ID
        relationship_type: New relationship type (optional)
        confidence: New confidence level (optional)
        source: New source information (optional)
        notes: New notes (optional)

    Returns:
        Updated relationship info or error
    """
    handler = get_neo4j_handler()
    safe_name = get_project_safe_name(project_id)

    if not safe_name:
        return {"error": f"Project not found: {project_id}"}

    # Build properties update
    properties = {}
    if confidence is not None:
        properties["confidence"] = confidence
    if source is not None:
        properties["source"] = source
    if notes is not None:
        properties["notes"] = notes

    result = handler.update_relationship(
        safe_name, source_id, target_id,
        relationship_type,
        properties if properties else None
    )

    if not result:
        return {"error": f"Relationship between {source_id} and {target_id} not found"}

    return {
        "success": True,
        "source_id": result["source_id"],
        "target_id": result["target_id"],
        "relationship_type": result["relationship_type"],
        "properties": result.get("properties", {})
    }


@mcp.tool()
def get_single_relationship(
    project_id: str,
    source_id: str,
    target_id: str
) -> dict:
    """
    Get details of a specific relationship between two entities.

    Args:
        project_id: The project ID or safe_name
        source_id: The source entity ID
        target_id: The target entity ID

    Returns:
        Relationship details including type and properties
    """
    handler = get_neo4j_handler()
    safe_name = get_project_safe_name(project_id)

    if not safe_name:
        return {"error": f"Project not found: {project_id}"}

    result = handler.get_relationship(safe_name, source_id, target_id)

    if not result:
        return {"error": f"Relationship between {source_id} and {target_id} not found"}

    return result


@mcp.tool()
def list_relationships(
    project_id: str,
    entity_id: str = None,
    relationship_type: str = None
) -> dict:
    """
    List all relationships in a project, optionally filtered.

    Args:
        project_id: The project ID or safe_name
        entity_id: Filter to relationships involving this entity (optional)
        relationship_type: Filter to this relationship type (optional)

    Returns:
        List of relationships with their types and properties
    """
    handler = get_neo4j_handler()
    safe_name = get_project_safe_name(project_id)

    if not safe_name:
        return {"error": f"Project not found: {project_id}"}

    relationships = handler.get_all_relationships(
        safe_name,
        entity_id=entity_id,
        relationship_type=relationship_type
    )

    # Get type counts
    type_counts = handler.get_relationship_type_counts(safe_name)

    return {
        "project_id": project_id,
        "count": len(relationships),
        "relationships": relationships,
        "relationship_type_counts": type_counts
    }


@mcp.tool()
def unlink_entities(project_id: str, source_id: str, target_id: str, bidirectional: bool = False) -> dict:
    """
    Remove a relationship between two entities.

    Args:
        project_id: The project ID or safe_name
        source_id: The source entity ID
        target_id: The target entity ID to unlink
        bidirectional: Also remove the reverse relationship from target entity

    Returns:
        Success status
    """
    handler = get_neo4j_handler()
    safe_name = get_project_safe_name(project_id)

    if not safe_name:
        return {"error": f"Project not found: {project_id}"}

    # Delete the relationship using the new handler method
    result = handler.delete_relationship(safe_name, source_id, target_id)

    if not result:
        return {"error": f"No relationship found between {source_id} and {target_id}"}

    # Optionally delete reverse relationship
    if bidirectional:
        handler.delete_relationship(safe_name, target_id, source_id)

    return {
        "success": True,
        "source_id": source_id,
        "unlinked_id": target_id,
        "bidirectional": bidirectional
    }


@mcp.tool()
def get_related(project_id: str, entity_id: str) -> dict:
    """
    Get all entities related to a given entity.

    Returns both direct relationships (entities this entity tagged) and
    reverse relationships (entities that tagged this entity), including
    relationship types and properties.

    Args:
        project_id: The project ID or safe_name
        entity_id: The entity ID to find relationships for

    Returns:
        Dictionary with direct and reverse relationships, including types and properties
    """
    handler = get_neo4j_handler()
    safe_name = get_project_safe_name(project_id)

    if not safe_name:
        return {"error": f"Project not found: {project_id}"}

    # Get the entity
    entity = handler.get_person(safe_name, entity_id)
    if not entity:
        return {"error": f"Entity not found: {entity_id}"}

    # Get direct relationships (entities this entity tagged)
    tagged_section = entity.get("profile", {}).get("Tagged People", {})
    direct_ids = tagged_section.get("tagged_people", [])
    relationship_types = tagged_section.get("relationship_types", {})
    relationship_properties = tagged_section.get("relationship_properties", {})

    if not isinstance(direct_ids, list):
        direct_ids = [direct_ids] if direct_ids else []
    if not isinstance(relationship_types, dict):
        relationship_types = {}
    if not isinstance(relationship_properties, dict):
        relationship_properties = {}

    direct_relationships = []
    for related_id in direct_ids:
        related_entity = handler.get_person(safe_name, related_id)
        if related_entity:
            direct_relationships.append({
                "id": related_id,
                "relationship_type": relationship_types.get(related_id, "RELATED_TO"),
                "properties": relationship_properties.get(related_id, {}),
                "entity": related_entity
            })

    # Get reverse relationships (entities that tagged this entity)
    all_entities = handler.get_all_people(safe_name)
    reverse_relationships = []

    for other_entity in all_entities:
        if other_entity.get("id") == entity_id:
            continue

        other_tagged = other_entity.get("profile", {}).get("Tagged People", {})
        other_tagged_ids = other_tagged.get("tagged_people", [])
        other_rel_types = other_tagged.get("relationship_types", {})
        other_rel_props = other_tagged.get("relationship_properties", {})

        if not isinstance(other_tagged_ids, list):
            other_tagged_ids = [other_tagged_ids] if other_tagged_ids else []
        if not isinstance(other_rel_types, dict):
            other_rel_types = {}
        if not isinstance(other_rel_props, dict):
            other_rel_props = {}

        if entity_id in other_tagged_ids:
            reverse_relationships.append({
                "id": other_entity.get("id"),
                "relationship_type": other_rel_types.get(entity_id, "RELATED_TO"),
                "properties": other_rel_props.get(entity_id, {}),
                "entity": other_entity
            })

    return {
        "entity_id": entity_id,
        "direct_relationships": direct_relationships,
        "reverse_relationships": reverse_relationships,
        "total_direct": len(direct_relationships),
        "total_reverse": len(reverse_relationships)
    }


# =============================================================================
# Search Tools
# =============================================================================

@mcp.tool()
def search_entities(project_id: str, query: str) -> dict:
    """
    Full text search across all entities in a project.

    Searches through all profile fields for matching text.

    Args:
        project_id: The project ID or safe_name
        query: Search query string

    Returns:
        List of matching entities with match context
    """
    handler = get_neo4j_handler()
    safe_name = get_project_safe_name(project_id)

    if not safe_name:
        return {"error": f"Project not found: {project_id}"}

    all_entities = handler.get_all_people(safe_name)
    query_lower = query.lower()

    matches = []

    for entity in all_entities:
        match_fields = []

        # Search through profile
        profile = entity.get("profile", {})
        for section_id, section_data in profile.items():
            if not isinstance(section_data, dict):
                continue

            for field_id, field_value in section_data.items():
                # Convert value to string for searching
                value_str = json.dumps(field_value) if isinstance(field_value, (dict, list)) else str(field_value)

                if query_lower in value_str.lower():
                    match_fields.append({
                        "section": section_id,
                        "field": field_id,
                        "value": field_value
                    })

        if match_fields:
            matches.append({
                "entity": entity,
                "matches": match_fields
            })

    return {
        "query": query,
        "project_id": project_id,
        "count": len(matches),
        "results": matches
    }


@mcp.tool()
def search_by_identifier(project_id: str, identifier_type: str, value: str) -> dict:
    """
    Find entities by a specific identifier type and value.

    Common identifier types include:
    - email, phone, username, social media handles, etc.

    Args:
        project_id: The project ID or safe_name
        identifier_type: The type of identifier to search (e.g., "email", "phone")
        value: The identifier value to find

    Returns:
        List of matching entities
    """
    handler = get_neo4j_handler()
    safe_name = get_project_safe_name(project_id)

    if not safe_name:
        return {"error": f"Project not found: {project_id}"}

    all_entities = handler.get_all_people(safe_name)
    value_lower = value.lower()
    identifier_lower = identifier_type.lower()

    matches = []

    for entity in all_entities:
        profile = entity.get("profile", {})

        for section_id, section_data in profile.items():
            if not isinstance(section_data, dict):
                continue

            for field_id, field_value in section_data.items():
                # Check if field name matches identifier type
                if identifier_lower in field_id.lower() or identifier_lower in section_id.lower():
                    # Check if value matches
                    if isinstance(field_value, str) and value_lower in field_value.lower():
                        matches.append({
                            "entity": entity,
                            "matched_field": {
                                "section": section_id,
                                "field": field_id,
                                "value": field_value
                            }
                        })
                    elif isinstance(field_value, list):
                        for item in field_value:
                            item_str = str(item) if not isinstance(item, dict) else json.dumps(item)
                            if value_lower in item_str.lower():
                                matches.append({
                                    "entity": entity,
                                    "matched_field": {
                                        "section": section_id,
                                        "field": field_id,
                                        "value": item
                                    }
                                })
                                break

    return {
        "identifier_type": identifier_type,
        "value": value,
        "project_id": project_id,
        "count": len(matches),
        "results": matches
    }


# =============================================================================
# Project Tools
# =============================================================================

@mcp.tool()
def create_project(name: str) -> dict:
    """
    Create a new project.

    Args:
        name: The project name

    Returns:
        The created project data
    """
    handler = get_neo4j_handler()

    # Create project
    project = handler.create_project(name)

    if not project:
        return {"error": f"Failed to create project: {name}"}

    # Create project directory
    project_id = project.get("id")
    if project_id:
        os.makedirs(f"projects/{project_id}", exist_ok=True)

    return {
        "success": True,
        "project": project
    }


@mcp.tool()
def list_projects() -> dict:
    """
    List all projects.

    Returns:
        List of all projects with basic info
    """
    handler = get_neo4j_handler()

    projects = handler.get_all_projects()

    return {
        "count": len(projects),
        "projects": projects
    }


@mcp.tool()
def get_project(project_id: str) -> dict:
    """
    Get detailed project information.

    Args:
        project_id: The project ID or safe_name

    Returns:
        Full project data including all entities
    """
    handler = get_neo4j_handler()
    safe_name = get_project_safe_name(project_id)

    if not safe_name:
        return {"error": f"Project not found: {project_id}"}

    project = handler.get_project(safe_name)

    if not project:
        return {"error": f"Project not found: {project_id}"}

    return project


# =============================================================================
# Report Tools
# =============================================================================

def get_reports_dir(project_id: str, entity_id: str) -> str:
    """Get the reports directory path for an entity."""
    return os.path.join("projects", project_id, "people", entity_id, "reports")


@mcp.tool()
def create_report(project_id: str, entity_id: str, content: str, toolname: str = "mcp") -> dict:
    """
    Create a report for an entity.

    Args:
        project_id: The project ID or safe_name
        entity_id: The entity ID to attach the report to
        content: The report content (markdown format)
        toolname: Name of the tool creating the report (for filename)

    Returns:
        Success status and report info
    """
    handler = get_neo4j_handler()
    safe_name = get_project_safe_name(project_id)

    if not safe_name:
        return {"error": f"Project not found: {project_id}"}

    # Verify entity exists
    entity = handler.get_person(safe_name, entity_id)
    if not entity:
        return {"error": f"Entity not found: {entity_id}"}

    # Get the actual project ID for file paths
    actual_project_id = get_project_id_from_safe_name(safe_name)
    if not actual_project_id:
        actual_project_id = project_id

    # Generate report name
    date_str = datetime.now().strftime("%Y%m%d")
    unique_id = str(uuid4())[:8]
    report_name = f"{toolname}_{date_str}_{entity_id}_{unique_id}.md"

    # Create reports directory
    reports_dir = get_reports_dir(actual_project_id, entity_id)
    os.makedirs(reports_dir, exist_ok=True)

    # Write report file
    report_path = os.path.join(reports_dir, report_name)
    with open(report_path, "w") as f:
        f.write(content)

    # Register in Neo4j
    report_data = {
        "name": report_name,
        "path": report_name,
        "tool": toolname,
        "created_at": datetime.now().isoformat(),
        "id": unique_id
    }
    handler.add_report_to_person(safe_name, entity_id, report_data)

    return {
        "success": True,
        "report_name": report_name,
        "report_path": report_path,
        "entity_id": entity_id
    }


@mcp.tool()
def get_reports(project_id: str, entity_id: str) -> dict:
    """
    List all reports for an entity.

    Args:
        project_id: The project ID or safe_name
        entity_id: The entity ID

    Returns:
        List of reports for the entity
    """
    handler = get_neo4j_handler()
    safe_name = get_project_safe_name(project_id)

    if not safe_name:
        return {"error": f"Project not found: {project_id}"}

    # Verify entity exists
    entity = handler.get_person(safe_name, entity_id)
    if not entity:
        return {"error": f"Entity not found: {entity_id}"}

    # Get the actual project ID for file paths
    actual_project_id = get_project_id_from_safe_name(safe_name)
    if not actual_project_id:
        actual_project_id = project_id

    # Get reports from filesystem
    reports_dir = get_reports_dir(actual_project_id, entity_id)

    reports = []
    if os.path.exists(reports_dir):
        for filename in os.listdir(reports_dir):
            if filename.endswith(".md"):
                file_path = os.path.join(reports_dir, filename)
                stat = os.stat(file_path)

                # Read first few lines for preview
                with open(file_path, "r") as f:
                    preview = f.read(500)
                    if len(preview) == 500:
                        preview += "..."

                reports.append({
                    "name": filename,
                    "path": file_path,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "preview": preview
                })

    return {
        "entity_id": entity_id,
        "project_id": project_id,
        "count": len(reports),
        "reports": reports
    }


# =============================================================================
# Graph Analysis Tools
# =============================================================================

@mcp.tool()
def find_path(project_id: str, entity_id_1: str, entity_id_2: str, find_all: bool = False, max_depth: int = 5) -> dict:
    """
    Find path(s) between two entities in the relationship graph.

    Uses graph traversal to find connections between entities through
    their tagged relationships. Can find either the shortest path or
    all paths up to a maximum depth.

    Args:
        project_id: The project ID or safe_name
        entity_id_1: The starting entity ID
        entity_id_2: The target entity ID
        find_all: If True, find all paths; if False, find only shortest path (default: False)
        max_depth: Maximum path depth when finding all paths (default: 5)

    Returns:
        Dictionary with path information:
        - For shortest path: found, path_length, entity_ids, entities
        - For all paths: found, path_count, paths (list of path info)
    """
    handler = get_neo4j_handler()
    safe_name = get_project_safe_name(project_id)

    if not safe_name:
        return {"error": f"Project not found: {project_id}"}

    # Verify both entities exist
    entity1 = handler.get_person(safe_name, entity_id_1)
    entity2 = handler.get_person(safe_name, entity_id_2)

    if not entity1:
        return {"error": f"Entity not found: {entity_id_1}"}
    if not entity2:
        return {"error": f"Entity not found: {entity_id_2}"}

    if find_all:
        result = handler.find_all_paths(safe_name, entity_id_1, entity_id_2, max_depth)
    else:
        result = handler.find_shortest_path(safe_name, entity_id_1, entity_id_2)

    if result is None:
        return {"error": "Failed to find path - entities may not exist in the project"}

    return result


@mcp.tool()
def analyze_connections(project_id: str, entity_id: str = None, top_n: int = 10) -> dict:
    """
    Analyze connection patterns and centrality in the entity graph.

    If entity_id is provided, returns detailed centrality metrics for that entity.
    If entity_id is not provided, returns the most connected entities in the project.

    Args:
        project_id: The project ID or safe_name
        entity_id: Optional entity ID to analyze (if None, returns most connected entities)
        top_n: Number of most connected entities to return (default: 10)

    Returns:
        For specific entity: degree centrality, incoming/outgoing connections, normalized score
        For project-wide: list of most connected entities with connection counts
    """
    handler = get_neo4j_handler()
    safe_name = get_project_safe_name(project_id)

    if not safe_name:
        return {"error": f"Project not found: {project_id}"}

    if entity_id:
        # Get centrality for specific entity
        result = handler.get_entity_centrality(safe_name, entity_id)
        if result is None:
            return {"error": f"Entity not found: {entity_id}"}
        return result
    else:
        # Get most connected entities
        result = handler.get_most_connected(safe_name, limit=top_n)
        return result


@mcp.tool()
def get_network_clusters(project_id: str, include_isolated: bool = True) -> dict:
    """
    Detect and return connected components (clusters) in the entity network.

    Identifies groups of entities that are connected to each other through
    relationships but not connected to entities in other groups. Useful for
    finding distinct networks or communities within a project.

    Args:
        project_id: The project ID or safe_name
        include_isolated: Whether to include isolated entities (no connections) as single-entity clusters (default: True)

    Returns:
        Dictionary with:
        - cluster_count: Total number of clusters
        - connected_clusters: Number of clusters with 2+ entities
        - isolated_count: Number of entities with no connections
        - clusters: List of cluster details (size, members, internal edges)
    """
    handler = get_neo4j_handler()
    safe_name = get_project_safe_name(project_id)

    if not safe_name:
        return {"error": f"Project not found: {project_id}"}

    result = handler.find_clusters(safe_name)

    if not include_isolated:
        # Filter out isolated entities
        result["clusters"] = [c for c in result["clusters"] if not c["is_isolated"]]
        result["cluster_count"] = len(result["clusters"])

    return result


@mcp.tool()
def get_entity_network(project_id: str, entity_id: str, depth: int = 2) -> dict:
    """
    Get the neighborhood network around a specific entity.

    Returns all entities within N hops of the specified entity,
    creating an ego network useful for understanding an entity's
    local connections and influence.

    Args:
        project_id: The project ID or safe_name
        entity_id: The center entity ID
        depth: Maximum number of hops from the center entity (default: 2)

    Returns:
        Dictionary with:
        - center_entity_id: The specified entity
        - total_entities: Count of entities in the neighborhood
        - neighborhood: Entities organized by distance (depth_0, depth_1, etc.)
        - edges: List of connections within the neighborhood
    """
    handler = get_neo4j_handler()
    safe_name = get_project_safe_name(project_id)

    if not safe_name:
        return {"error": f"Project not found: {project_id}"}

    result = handler.get_entity_neighborhood(safe_name, entity_id, depth)

    if result is None:
        return {"error": f"Entity not found: {entity_id}"}

    return result


# =============================================================================
# Auto-Linking Tools
# =============================================================================

# Lazy initialization of AutoLinker
_auto_linker = None

def get_auto_linker():
    """Get or create AutoLinker instance."""
    global _auto_linker
    if _auto_linker is None:
        # Import here to avoid circular imports
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from api.services.auto_linker import AutoLinker
        _auto_linker = AutoLinker(get_neo4j_handler())
    return _auto_linker


@mcp.tool()
def find_duplicates(project_id: str, entity_id: str = None, min_confidence: float = 5.0) -> dict:
    """
    Find potential duplicate entities based on matching identifiers.

    Scans entities for matching identifiers such as email addresses, phone numbers,
    usernames, crypto addresses, and other identifier fields marked in the schema.
    Returns entities that likely represent the same person based on shared identifiers.

    If entity_id is provided, finds duplicates for that specific entity.
    If entity_id is not provided, scans all entities in the project for duplicates.

    Confidence scoring:
    - 5.0+: Very likely the same person (multiple matching identifiers)
    - 3.0-5.0: Probably the same person (key identifiers match)
    - 2.0-3.0: Possibly related (some shared identifiers)

    Args:
        project_id: The project ID or safe_name
        entity_id: Optional entity ID to find duplicates for. If None, scans entire project.
        min_confidence: Minimum confidence score to consider as duplicate (default: 5.0)

    Returns:
        Dictionary with:
        - duplicates: List of potential duplicate pairs with matching identifiers
        - confidence_scores: Confidence level for each match
        - matching_identifiers: Specific identifiers that matched
    """
    safe_name = get_project_safe_name(project_id)
    if not safe_name:
        return {"error": f"Project not found: {project_id}"}

    auto_linker = get_auto_linker()

    if entity_id:
        # Find duplicates for specific entity
        suggestions = auto_linker.find_matching_entities(
            safe_name, entity_id, min_confidence=min_confidence
        )

        return {
            "entity_id": entity_id,
            "project_id": project_id,
            "duplicates": [s.to_dict() for s in suggestions],
            "count": len(suggestions)
        }
    else:
        # Scan entire project for duplicates
        result = auto_linker.auto_link_all(safe_name, create_links=False)

        # Filter to only high-confidence duplicates
        duplicates = [d for d in result.get("potential_duplicates", [])
                     if d.get("confidence_score", 0) >= min_confidence]

        return {
            "project_id": project_id,
            "entities_scanned": result.get("entities_scanned", 0),
            "duplicates": duplicates,
            "count": len(duplicates),
            "scanned_at": result.get("scanned_at")
        }


@mcp.tool()
def suggest_entity_links(project_id: str, entity_id: str) -> dict:
    """
    Suggest potential connections for an entity based on shared identifiers.

    Analyzes the entity's profile for identifier fields (emails, phones, usernames,
    etc.) and finds other entities that share any of these identifiers. Returns
    categorized suggestions:

    - potential_duplicates: High confidence matches (likely same person)
    - suggested_links: Lower confidence matches (possibly related/connected)

    This is useful for:
    - Identifying duplicate profiles that should be merged
    - Discovering connections between entities
    - Finding related accounts across platforms

    Args:
        project_id: The project ID or safe_name
        entity_id: The entity ID to find suggestions for

    Returns:
        Dictionary with:
        - potential_duplicates: High-confidence matches (confidence >= 5.0)
        - suggested_links: Lower-confidence matches (confidence 2.0-5.0)
        - total_suggestions: Total number of suggestions found
        - matching_identifiers: Details of which identifiers matched
    """
    safe_name = get_project_safe_name(project_id)
    if not safe_name:
        return {"error": f"Project not found: {project_id}"}

    # Verify entity exists
    handler = get_neo4j_handler()
    entity = handler.get_person(safe_name, entity_id)
    if not entity:
        return {"error": f"Entity not found: {entity_id}"}

    auto_linker = get_auto_linker()
    result = auto_linker.suggest_links(safe_name, entity_id)

    return result


@mcp.tool()
def merge_entities(
    project_id: str,
    primary_entity_id: str,
    secondary_entity_id: str,
    delete_secondary: bool = False
) -> dict:
    """
    Merge two entities that represent the same person.

    Combines profile data from the secondary entity into the primary entity.
    The primary entity is preserved and updated, while the secondary entity
    can optionally be deleted after the merge.

    Merge behavior:
    - For simple values: Primary entity values take precedence
    - For lists/arrays: Values are combined (duplicates removed)
    - For nested objects: Merged recursively, primary takes precedence

    Common use cases:
    - Merging duplicate profiles discovered through find_duplicates
    - Consolidating data from multiple investigation sources
    - Cleaning up accidentally split profiles

    Args:
        project_id: The project ID or safe_name
        primary_entity_id: The entity to keep and merge into
        secondary_entity_id: The entity to merge from
        delete_secondary: Whether to delete the secondary entity after merge (default: False)

    Returns:
        Dictionary with:
        - success: Boolean indicating if merge succeeded
        - merged_entity: The updated primary entity with merged data
        - secondary_deleted: Whether the secondary was deleted
        - merge_details: Information about what data was merged
    """
    safe_name = get_project_safe_name(project_id)
    if not safe_name:
        return {"error": f"Project not found: {project_id}"}

    auto_linker = get_auto_linker()
    result = auto_linker.merge_entities(
        safe_name,
        primary_entity_id,
        secondary_entity_id,
        delete_secondary=delete_secondary
    )

    return result


@mcp.tool()
def auto_link_project(project_id: str, create_links: bool = False) -> dict:
    """
    Scan all entities in a project for potential links and duplicates.

    Performs a comprehensive scan of all entities in the project, extracting
    identifier values and finding matches across the entire dataset. This is
    useful for:

    - Initial data quality assessment
    - Discovering hidden connections in imported data
    - Bulk duplicate detection
    - Automated relationship creation

    The scan extracts values from all identifier fields defined in the schema,
    including emails, phone numbers, social media usernames, crypto addresses,
    and other unique identifiers.

    Args:
        project_id: The project ID or safe_name
        create_links: Whether to automatically create links for suggestions (default: False)
                     If True, creates "Tagged People" relationships for matches

    Returns:
        Dictionary with:
        - entities_scanned: Total number of entities analyzed
        - entities_with_identifiers: Entities that have identifier values
        - potential_duplicates: High-confidence duplicate pairs
        - suggested_links: Lower-confidence relationship suggestions
        - total_suggestions: Total suggestions found
        - links_created: Number of links created (if create_links=True)
        - scanned_at: Timestamp of the scan
    """
    safe_name = get_project_safe_name(project_id)
    if not safe_name:
        return {"error": f"Project not found: {project_id}"}

    auto_linker = get_auto_linker()
    result = auto_linker.auto_link_all(safe_name, create_links=create_links)

    return result


# =============================================================================
# Server Entry Point
# =============================================================================

if __name__ == "__main__":
    mcp.run()
