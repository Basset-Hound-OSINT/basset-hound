"""
Search tools for MCP.

Provides tools for full-text search and identifier-based search
across entities in Basset Hound projects.
"""

import json

from .base import get_neo4j_handler, get_project_safe_name


def register_search_tools(mcp):
    """Register search tools with the MCP server."""

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
