"""
Orphan data management tools for MCP.

Provides tools for managing unlinked/orphan data in Basset Hound.
Orphan data represents identifiers or data fragments that have been discovered
but not yet linked to a specific entity. This is critical for OSINT workflows
where data is collected before the full picture emerges.
"""

from datetime import datetime
from uuid import uuid4
from typing import Optional, List

from .base import get_neo4j_handler, get_project_safe_name


def register_orphan_tools(mcp):
    """Register orphan data management tools with the MCP server."""

    @mcp.tool()
    def create_orphan(
        project_id: str,
        identifier_type: str,
        identifier_value: str,
        source_file: str = "",
        source_location: str = "",
        context: str = "",
        tags: list = None,
        notes: str = "",
        metadata: dict = None
    ) -> dict:
        """
        Create an orphan data record for an unlinked identifier.

        Orphan data represents discovered identifiers (emails, phone numbers,
        usernames, etc.) that haven't yet been linked to a specific entity.
        Common in OSINT workflows where data is collected incrementally.

        Args:
            project_id: The project ID or safe_name
            identifier_type: Type of identifier (email, phone, username, ip_address, etc.)
            identifier_value: The actual identifier value
            source_file: Optional source file path where data was found
            source_location: Optional location within source (line number, element path)
            context: Optional surrounding context/text
            tags: Optional list of tags for categorization
            notes: Optional notes about this orphan data
            metadata: Optional additional metadata dict

        Returns:
            The created orphan data record with generated ID
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        orphan_data = {
            "id": str(uuid4()),
            "identifier_type": identifier_type,
            "identifier_value": identifier_value,
            "source_file": source_file,
            "source_location": source_location,
            "context": context,
            "tags": tags or [],
            "notes": notes,
            "created_at": datetime.now().isoformat(),
        }

        if metadata:
            orphan_data["metadata"] = metadata

        result = handler.create_orphan_data(safe_name, orphan_data)

        if not result:
            return {"error": "Failed to create orphan data"}

        return result

    @mcp.tool()
    def create_orphan_batch(
        project_id: str,
        orphans: list
    ) -> dict:
        """
        Create multiple orphan data records in a single batch operation.

        Efficient for bulk data ingestion from scrapers, file imports, etc.

        Args:
            project_id: The project ID or safe_name
            orphans: List of orphan data dicts, each containing:
                - identifier_type: Type of identifier (required)
                - identifier_value: The identifier value (required)
                - source_file: Source file path (optional)
                - source_location: Location within source (optional)
                - context: Surrounding context (optional)
                - tags: List of tags (optional)
                - notes: Notes (optional)
                - metadata: Additional metadata dict (optional)

        Returns:
            Dictionary with created IDs, failed items, and total count
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        if not orphans:
            return {"created": [], "failed": [], "total": 0}

        # Validate required fields
        failed = []
        valid_orphans = []
        for i, orphan in enumerate(orphans):
            if not orphan.get("identifier_type") or not orphan.get("identifier_value"):
                failed.append({
                    "index": i,
                    "error": "Missing required field: identifier_type and identifier_value are required"
                })
            else:
                valid_orphans.append(orphan)

        if valid_orphans:
            result = handler.create_orphan_data_batch(safe_name, valid_orphans)
            result["failed"].extend(failed)
        else:
            result = {"created": [], "failed": failed, "total": len(orphans)}

        return result

    @mcp.tool()
    def get_orphan(project_id: str, orphan_id: str) -> dict:
        """
        Get an orphan data record by ID.

        Args:
            project_id: The project ID or safe_name
            orphan_id: The orphan data ID

        Returns:
            The orphan data record or error message
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        orphan = handler.get_orphan_data(safe_name, orphan_id)

        if not orphan:
            return {"error": f"Orphan data not found: {orphan_id}"}

        return orphan

    @mcp.tool()
    def list_orphans(
        project_id: str,
        identifier_type: str = None,
        linked: bool = None,
        tags: list = None,
        limit: int = 100,
        offset: int = 0
    ) -> dict:
        """
        List orphan data records with optional filtering.

        Args:
            project_id: The project ID or safe_name
            identifier_type: Filter by identifier type (email, phone, etc.)
            linked: Filter by linked status (True = linked, False = unlinked, None = all)
            tags: Filter by tags (returns orphans matching ANY of these tags)
            limit: Maximum records to return (default: 100)
            offset: Number of records to skip for pagination (default: 0)

        Returns:
            Dictionary with orphan records and pagination info
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        filters = {}
        if identifier_type:
            filters["identifier_type"] = identifier_type
        if linked is not None:
            filters["linked"] = linked
        if tags:
            filters["tags"] = tags

        orphans = handler.list_orphan_data(safe_name, filters=filters, limit=limit, offset=offset)

        return {
            "project_id": project_id,
            "count": len(orphans),
            "limit": limit,
            "offset": offset,
            "orphans": orphans
        }

    @mcp.tool()
    def search_orphans(project_id: str, query: str, limit: int = 100) -> dict:
        """
        Search orphan data by identifier value.

        Performs a case-insensitive search across orphan identifier values.

        Args:
            project_id: The project ID or safe_name
            query: Search query string
            limit: Maximum results to return (default: 100)

        Returns:
            List of matching orphan records
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        orphans = handler.search_orphan_data(safe_name, query, limit=limit)

        return {
            "project_id": project_id,
            "query": query,
            "count": len(orphans),
            "orphans": orphans
        }

    @mcp.tool()
    def link_orphan(
        project_id: str,
        orphan_id: str,
        entity_id: str,
        field_mapping: str = None
    ) -> dict:
        """
        Link an orphan data record to an entity.

        Once an orphan identifier has been identified as belonging to a specific
        entity, this tool creates the relationship and marks the orphan as linked.

        Args:
            project_id: The project ID or safe_name
            orphan_id: The orphan data ID to link
            entity_id: The entity ID to link to
            field_mapping: Optional field name in entity profile where this data should map

        Returns:
            Success status and updated orphan data
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        # Verify orphan exists
        orphan = handler.get_orphan_data(safe_name, orphan_id)
        if not orphan:
            return {"error": f"Orphan data not found: {orphan_id}"}

        # Verify entity exists
        entity = handler.get_person(safe_name, entity_id)
        if not entity:
            return {"error": f"Entity not found: {entity_id}"}

        # Check if already linked
        if orphan.get("linked") and orphan.get("linked_entity_id") == entity_id:
            return {"error": "Orphan is already linked to this entity", "orphan": orphan}

        # Perform the link using batch method (single item)
        links = [{"orphan_id": orphan_id, "entity_id": entity_id, "field_mapping": field_mapping}]
        result = handler.link_orphan_data_batch(safe_name, links)

        if result["linked"] > 0:
            # Fetch updated orphan data
            updated_orphan = handler.get_orphan_data(safe_name, orphan_id)
            return {
                "success": True,
                "orphan_id": orphan_id,
                "entity_id": entity_id,
                "orphan": updated_orphan
            }
        else:
            return {"error": "Failed to link orphan to entity"}

    @mcp.tool()
    def link_orphan_batch(project_id: str, links: list) -> dict:
        """
        Link multiple orphan data records to entities in a single batch.

        Args:
            project_id: The project ID or safe_name
            links: List of link specifications, each containing:
                - orphan_id: The orphan data ID (required)
                - entity_id: The entity ID to link to (required)
                - field_mapping: Optional field name for mapping

        Returns:
            Dictionary with linked count, failed links, and total
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        if not links:
            return {"linked": 0, "failed": [], "total": 0}

        result = handler.link_orphan_data_batch(safe_name, links)
        return result

    @mcp.tool()
    def update_orphan(
        project_id: str,
        orphan_id: str,
        identifier_type: str = None,
        identifier_value: str = None,
        source_file: str = None,
        source_location: str = None,
        context: str = None,
        tags: list = None,
        notes: str = None,
        metadata: dict = None
    ) -> dict:
        """
        Update an orphan data record.

        Only provided fields will be updated; others remain unchanged.

        Args:
            project_id: The project ID or safe_name
            orphan_id: The orphan data ID to update
            identifier_type: New identifier type (optional)
            identifier_value: New identifier value (optional)
            source_file: New source file (optional)
            source_location: New source location (optional)
            context: New context (optional)
            tags: New tags list (optional)
            notes: New notes (optional)
            metadata: New metadata dict (optional)

        Returns:
            The updated orphan data record
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        # Build updates dict from provided fields
        updates = {}
        if identifier_type is not None:
            updates["identifier_type"] = identifier_type
        if identifier_value is not None:
            updates["identifier_value"] = identifier_value
        if source_file is not None:
            updates["source_file"] = source_file
        if source_location is not None:
            updates["source_location"] = source_location
        if context is not None:
            updates["context"] = context
        if tags is not None:
            updates["tags"] = tags
        if notes is not None:
            updates["notes"] = notes
        if metadata is not None:
            updates["metadata"] = metadata

        if not updates:
            return {"error": "No updates provided"}

        result = handler.update_orphan_data(safe_name, orphan_id, updates)

        if not result:
            return {"error": f"Failed to update orphan data: {orphan_id}"}

        return result

    @mcp.tool()
    def delete_orphan(project_id: str, orphan_id: str) -> dict:
        """
        Delete an orphan data record.

        Args:
            project_id: The project ID or safe_name
            orphan_id: The orphan data ID to delete

        Returns:
            Success status
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        success = handler.delete_orphan_data(safe_name, orphan_id)

        if not success:
            return {"error": f"Failed to delete orphan data: {orphan_id}"}

        return {"success": True, "deleted_id": orphan_id}

    @mcp.tool()
    def find_duplicate_orphans(project_id: str) -> dict:
        """
        Find potential duplicate orphan data records.

        Identifies orphans with matching identifier_type and identifier_value,
        which may represent the same piece of data discovered multiple times.

        Args:
            project_id: The project ID or safe_name

        Returns:
            List of duplicate groups with orphan IDs
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        duplicates = handler.find_duplicate_orphans(safe_name)

        return {
            "project_id": project_id,
            "duplicate_groups": duplicates
        }

    @mcp.tool()
    def count_orphans(
        project_id: str,
        identifier_type: str = None,
        linked: bool = None
    ) -> dict:
        """
        Count orphan data records with optional filtering.

        Args:
            project_id: The project ID or safe_name
            identifier_type: Filter by identifier type
            linked: Filter by linked status

        Returns:
            Count of matching orphan records
        """
        handler = get_neo4j_handler()
        safe_name = get_project_safe_name(project_id)

        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        filters = {}
        if identifier_type:
            filters["identifier_type"] = identifier_type
        if linked is not None:
            filters["linked"] = linked

        count = handler.count_orphan_data(safe_name, filters=filters)

        return {
            "project_id": project_id,
            "count": count,
            "filters": filters
        }
