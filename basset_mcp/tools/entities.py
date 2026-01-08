"""
Entity management tools for MCP.

Provides tools for CRUD operations on entities (people) in Basset Hound,
including creation, retrieval, update, and deletion with schema validation.
"""

from datetime import datetime
from uuid import uuid4

from .base import get_neo4j_handler, get_project_safe_name, validate_entity_profile


def register_entity_tools(mcp):
    """Register entity management tools with the MCP server."""

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

    @mcp.tool()
    def query_entities(
        project_id: str,
        filters: dict = None,
        created_after: str = None,
        created_before: str = None,
        has_field: str = None,
        has_section: str = None,
        has_relationship: bool = None,
        limit: int = 100,
        offset: int = 0
    ) -> dict:
        """
        Query entities with flexible filtering criteria.

        Provides more granular control than list_entities or search_entities,
        allowing filtering by metadata, date ranges, and profile structure.

        Args:
            project_id: The project ID or safe_name
            filters: Dict of field_path: value pairs to match
                    (e.g., {"contact.email": "john@example.com"})
            created_after: ISO date string - only entities created after this date
            created_before: ISO date string - only entities created before this date
            has_field: Field path that must exist (e.g., "contact.phone")
            has_section: Section ID that must have data (e.g., "social_media")
            has_relationship: If True, only entities with relationships; if False, only isolated
            limit: Maximum entities to return (default: 100)
            offset: Number of entities to skip for pagination (default: 0)

        Returns:
            Dictionary with matching entities and pagination info
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        all_entities = handler.get_all_people(safe_name)
        matching = []

        for entity in all_entities:
            # Apply filters
            if not _entity_matches_filters(entity, filters, created_after, created_before,
                                           has_field, has_section, has_relationship, handler, safe_name):
                continue
            matching.append(entity)

        # Apply pagination
        total = len(matching)
        paginated = matching[offset:offset + limit]

        return {
            "project_id": project_id,
            "total": total,
            "count": len(paginated),
            "limit": limit,
            "offset": offset,
            "has_more": (offset + limit) < total,
            "entities": paginated
        }


def _entity_matches_filters(entity, filters, created_after, created_before,
                            has_field, has_section, has_relationship, handler, safe_name):
    """Check if an entity matches all filter criteria."""
    profile = entity.get("profile", {})

    # Check created_after
    if created_after:
        created_at = entity.get("created_at")
        if created_at and created_at < created_after:
            return False

    # Check created_before
    if created_before:
        created_at = entity.get("created_at")
        if created_at and created_at > created_before:
            return False

    # Check has_section
    if has_section:
        section_data = profile.get(has_section, {})
        if not section_data or not isinstance(section_data, dict):
            return False
        # Check if section has any non-empty values
        has_data = any(v for v in section_data.values() if v)
        if not has_data:
            return False

    # Check has_field (dot-notation path)
    if has_field:
        if not _field_exists(profile, has_field):
            return False

    # Check filters (field_path: value pairs)
    if filters:
        for field_path, expected_value in filters.items():
            actual_value = _get_field_value(profile, field_path)
            if actual_value is None:
                return False
            # Case-insensitive string comparison
            if isinstance(actual_value, str) and isinstance(expected_value, str):
                if expected_value.lower() not in actual_value.lower():
                    return False
            elif isinstance(actual_value, list):
                # Check if any item in list matches
                found = False
                for item in actual_value:
                    if isinstance(item, str) and isinstance(expected_value, str):
                        if expected_value.lower() in item.lower():
                            found = True
                            break
                    elif item == expected_value:
                        found = True
                        break
                if not found:
                    return False
            elif actual_value != expected_value:
                return False

    # Check has_relationship
    if has_relationship is not None:
        # Check "Tagged People" section for relationships
        tagged_people = profile.get("Tagged People", {})
        has_tags = bool(tagged_people) and any(
            v for v in tagged_people.values() if v and isinstance(v, list) and len(v) > 0
        )
        if has_relationship and not has_tags:
            return False
        if not has_relationship and has_tags:
            return False

    return True


def _field_exists(profile: dict, field_path: str) -> bool:
    """Check if a field path exists in profile."""
    parts = field_path.split(".")
    current = profile

    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        elif isinstance(current, list):
            try:
                idx = int(part)
                if 0 <= idx < len(current):
                    current = current[idx]
                else:
                    return False
            except ValueError:
                return False
        else:
            return False

    return current is not None and current != "" and current != []


def _get_field_value(profile: dict, field_path: str):
    """Get value at field path, or None if not found."""
    parts = field_path.split(".")
    current = profile

    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        elif isinstance(current, list):
            try:
                idx = int(part)
                if 0 <= idx < len(current):
                    current = current[idx]
                else:
                    return None
            except ValueError:
                return None
        else:
            return None

    return current
