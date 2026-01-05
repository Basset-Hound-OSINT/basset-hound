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
