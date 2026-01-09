"""
Data management tools for MCP - Phase 43.1: Data ID System.

Provides tools for CRUD operations on DataItems, enabling smart suggestions
and better data management across entities.
"""

import asyncio
from datetime import datetime
from typing import Optional, Dict, List, Any

from .base import get_neo4j_handler, get_project_safe_name


def register_data_management_tools(mcp):
    """Register data management tools with the MCP server."""

    @mcp.tool()
    def create_data_item(
        project_id: str,
        data_type: str,
        value: Any,
        entity_id: Optional[str] = None,
        orphan_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> dict:
        """
        Create a new DataItem in a project.

        DataItems represent discrete pieces of data (emails, phones, images, etc.)
        that can be linked to entities or exist as orphans. Each DataItem gets
        a unique ID in the format data_abc123.

        Args:
            project_id: The project ID or safe_name
            data_type: Type of data (email, phone, image, document, etc.)
            value: The actual data value or file path
            entity_id: Optional entity ID to link to
            orphan_id: Optional orphan ID to link to
            metadata: Optional metadata dictionary (source, confidence, etc.)

        Returns:
            The created DataItem data including generated ID, or error message
        """
        safe_name = get_project_safe_name(project_id)
        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        # Import here to avoid circular imports
        from api.models.data_item import DataItem
        from api.services.data_service import DataService
        from api.services.neo4j_service import AsyncNeo4jService

        # Create DataItem
        data_item = DataItem(
            id=DataItem.generate_id(),
            type=data_type,
            value=value,
            normalized_value=DataItem.normalize_value(value, data_type),
            entity_id=entity_id,
            orphan_id=orphan_id,
            created_at=datetime.now(),
            metadata=metadata or {}
        )

        # Store in Neo4j using async service
        async def _create():
            async with AsyncNeo4jService() as neo4j:
                service = DataService(neo4j)
                created_item = await service.create_data_item(data_item)

                # Link to entity if specified
                if entity_id:
                    await service.link_data_to_entity(created_item.id, entity_id)

                # Link to orphan if specified
                if orphan_id:
                    await service.link_data_to_orphan(created_item.id, orphan_id)

                return created_item.to_dict()

        try:
            result = asyncio.run(_create())
            return result
        except Exception as e:
            return {"error": f"Failed to create data item: {str(e)}"}

    @mcp.tool()
    def get_data_item(project_id: str, data_id: str) -> dict:
        """
        Get a DataItem by ID.

        Args:
            project_id: The project ID or safe_name
            data_id: The DataItem ID (format: data_abc123)

        Returns:
            The DataItem data or error message
        """
        safe_name = get_project_safe_name(project_id)
        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        from api.services.data_service import DataService
        from api.services.neo4j_service import AsyncNeo4jService

        async def _get():
            async with AsyncNeo4jService() as neo4j:
                service = DataService(neo4j)
                data_item = await service.get_data_item(data_id)

                if not data_item:
                    return {"error": f"DataItem not found: {data_id}"}

                return data_item.to_dict()

        try:
            result = asyncio.run(_get())
            return result
        except Exception as e:
            return {"error": f"Failed to get data item: {str(e)}"}

    @mcp.tool()
    def list_entity_data(
        project_id: str,
        entity_id: str,
        data_type: Optional[str] = None
    ) -> dict:
        """
        List all DataItems linked to an entity.

        Args:
            project_id: The project ID or safe_name
            entity_id: The entity (Person) ID
            data_type: Optional filter by data type

        Returns:
            List of DataItems or error message
        """
        safe_name = get_project_safe_name(project_id)
        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        from api.services.data_service import DataService
        from api.services.neo4j_service import AsyncNeo4jService

        async def _list():
            async with AsyncNeo4jService() as neo4j:
                service = DataService(neo4j)
                data_items = await service.list_data_items(
                    entity_id=entity_id,
                    data_type=data_type
                )

                return {
                    "data_items": [item.to_dict() for item in data_items],
                    "count": len(data_items),
                    "entity_id": entity_id
                }

        try:
            result = asyncio.run(_list())
            return result
        except Exception as e:
            return {"error": f"Failed to list entity data: {str(e)}"}

    @mcp.tool()
    def delete_data_item(project_id: str, data_id: str) -> dict:
        """
        Delete a DataItem by ID.

        Args:
            project_id: The project ID or safe_name
            data_id: The DataItem ID to delete

        Returns:
            Success status or error message
        """
        safe_name = get_project_safe_name(project_id)
        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        from api.services.data_service import DataService
        from api.services.neo4j_service import AsyncNeo4jService

        async def _delete():
            async with AsyncNeo4jService() as neo4j:
                service = DataService(neo4j)
                deleted = await service.delete_data_item(data_id)

                if not deleted:
                    return {"error": f"DataItem not found: {data_id}"}

                return {"success": True, "data_id": data_id}

        try:
            result = asyncio.run(_delete())
            return result
        except Exception as e:
            return {"error": f"Failed to delete data item: {str(e)}"}

    @mcp.tool()
    def link_data_to_entity(project_id: str, data_id: str, entity_id: str) -> dict:
        """
        Link a DataItem to an entity.

        Creates a HAS_DATA relationship between the entity (Person) and the DataItem.

        Args:
            project_id: The project ID or safe_name
            data_id: The DataItem ID
            entity_id: The entity (Person) ID

        Returns:
            Success status or error message
        """
        safe_name = get_project_safe_name(project_id)
        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        from api.services.data_service import DataService
        from api.services.neo4j_service import AsyncNeo4jService

        async def _link():
            async with AsyncNeo4jService() as neo4j:
                service = DataService(neo4j)
                linked = await service.link_data_to_entity(data_id, entity_id)

                if not linked:
                    return {
                        "error": f"Failed to link data item {data_id} to entity {entity_id}. "
                                 f"Ensure both IDs are valid."
                    }

                return {
                    "success": True,
                    "data_id": data_id,
                    "entity_id": entity_id
                }

        try:
            result = asyncio.run(_link())
            return result
        except Exception as e:
            return {"error": f"Failed to link data to entity: {str(e)}"}

    @mcp.tool()
    def unlink_data_from_entity(project_id: str, data_id: str) -> dict:
        """
        Unlink a DataItem from its entity.

        Removes the HAS_DATA relationship and clears the entity_id.

        Args:
            project_id: The project ID or safe_name
            data_id: The DataItem ID

        Returns:
            Success status or error message
        """
        safe_name = get_project_safe_name(project_id)
        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        from api.services.data_service import DataService
        from api.services.neo4j_service import AsyncNeo4jService

        async def _unlink():
            async with AsyncNeo4jService() as neo4j:
                service = DataService(neo4j)
                unlinked = await service.unlink_data_from_entity(data_id)

                if not unlinked:
                    return {"error": f"DataItem not found: {data_id}"}

                return {
                    "success": True,
                    "data_id": data_id
                }

        try:
            result = asyncio.run(_unlink())
            return result
        except Exception as e:
            return {"error": f"Failed to unlink data from entity: {str(e)}"}

    @mcp.tool()
    def find_similar_data(
        project_id: str,
        value: Any,
        data_type: str,
        exclude_id: Optional[str] = None
    ) -> dict:
        """
        Find DataItems with similar values.

        Uses normalized value comparison to detect duplicates and suggest matches.
        Useful for smart suggestions and deduplication.

        Args:
            project_id: The project ID or safe_name
            value: The value to search for
            data_type: Type of data (email, phone, etc.)
            exclude_id: Optional DataItem ID to exclude from results

        Returns:
            List of similar DataItems or error message
        """
        safe_name = get_project_safe_name(project_id)
        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        from api.models.data_item import DataItem
        from api.services.data_service import DataService
        from api.services.neo4j_service import AsyncNeo4jService

        async def _find():
            normalized_value = DataItem.normalize_value(value, data_type)

            async with AsyncNeo4jService() as neo4j:
                service = DataService(neo4j)
                similar_items = await service.find_similar_data(
                    normalized_value=normalized_value,
                    data_type=data_type,
                    exclude_id=exclude_id
                )

                return {
                    "similar_items": [item.to_dict() for item in similar_items],
                    "count": len(similar_items),
                    "search_value": value,
                    "normalized_value": normalized_value,
                    "data_type": data_type
                }

        try:
            result = asyncio.run(_find())
            return result
        except Exception as e:
            return {"error": f"Failed to find similar data: {str(e)}"}

    @mcp.tool()
    def find_duplicate_files(project_id: str, file_path: str) -> dict:
        """
        Find DataItems with the same file hash.

        Computes SHA-256 hash of the given file and searches for duplicates.
        Useful for detecting duplicate images, documents, etc.

        Args:
            project_id: The project ID or safe_name
            file_path: Path to the file to check

        Returns:
            List of DataItems with matching hash or error message
        """
        safe_name = get_project_safe_name(project_id)
        if not safe_name:
            return {"error": f"Project not found: {project_id}"}

        from api.services.data_service import DataService
        from api.services.neo4j_service import AsyncNeo4jService

        async def _find():
            async with AsyncNeo4jService() as neo4j:
                service = DataService(neo4j)

                # Compute hash
                file_hash = service._compute_file_hash(file_path)
                if not file_hash:
                    return {"error": f"Failed to compute hash for file: {file_path}"}

                # Find duplicates
                duplicates = await service.find_by_hash(file_hash)

                return {
                    "duplicates": [item.to_dict() for item in duplicates],
                    "count": len(duplicates),
                    "file_path": file_path,
                    "file_hash": file_hash
                }

        try:
            result = asyncio.run(_find())
            return result
        except Exception as e:
            return {"error": f"Failed to find duplicate files: {str(e)}"}
