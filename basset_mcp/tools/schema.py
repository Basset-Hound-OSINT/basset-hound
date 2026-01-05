"""
Schema introspection tools for MCP.

Provides tools for querying and validating the data schema defined in
data_config.yaml, including section/field introspection and profile validation.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config_loader import get_section_by_id, get_field_by_id
from .base import get_schema_config, reload_schema_config


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


def register_schema_tools(mcp):
    """Register schema introspection tools with the MCP server."""

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
    def validate_profile(profile: dict) -> dict:
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
        return validate_profile_data(profile)

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
