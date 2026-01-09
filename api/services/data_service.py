"""
DataService for Phase 43.1: Data ID System.

Provides CRUD operations for DataItems in Neo4j with support for
linking/unlinking from entities and orphans.
"""

import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional

from api.models.data_item import DataItem
from api.services.neo4j_service import AsyncNeo4jService


class DataService:
    """
    Service for managing DataItems in Neo4j.

    Handles creation, retrieval, updates, deletion, and linking/unlinking
    of data items to entities and orphans.
    """

    def __init__(self, neo4j_service: AsyncNeo4jService):
        """
        Initialize the DataService.

        Args:
            neo4j_service: AsyncNeo4jService instance
        """
        self.neo4j = neo4j_service

    async def create_data_item(self, data_item: DataItem) -> DataItem:
        """
        Create a new DataItem in Neo4j.

        Args:
            data_item: DataItem to create

        Returns:
            DataItem: Created data item with ID
        """
        # Ensure ID is set
        if not data_item.id:
            data_item.id = DataItem.generate_id()

        # Ensure normalized_value is set
        if not data_item.normalized_value:
            data_item.normalized_value = DataItem.normalize_value(
                data_item.value, data_item.type
            )

        # Compute hash for file types
        if data_item.type in ["image", "document", "video", "audio"] and isinstance(data_item.value, str):
            data_item.hash = self._compute_file_hash(data_item.value)

        # Create node in Neo4j
        async with self.neo4j.session() as session:
            await session.run(
                """
                CREATE (d:DataItem {
                    id: $id,
                    type: $type,
                    value: $value,
                    hash: $hash,
                    normalized_value: $normalized_value,
                    entity_id: $entity_id,
                    orphan_id: $orphan_id,
                    created_at: $created_at,
                    metadata: $metadata
                })
                RETURN d
                """,
                id=data_item.id,
                type=data_item.type,
                value=self._serialize_value(data_item.value),
                hash=data_item.hash,
                normalized_value=data_item.normalized_value,
                entity_id=data_item.entity_id,
                orphan_id=data_item.orphan_id,
                created_at=data_item.created_at.isoformat() if isinstance(data_item.created_at, datetime) else data_item.created_at,
                metadata=self._serialize_metadata(data_item.metadata)
            )

        return data_item

    async def get_data_item(self, data_id: str) -> Optional[DataItem]:
        """
        Get a DataItem by ID.

        Args:
            data_id: DataItem ID

        Returns:
            DataItem or None if not found
        """
        async with self.neo4j.session() as session:
            result = await session.run(
                """
                MATCH (d:DataItem {id: $data_id})
                RETURN d
                """,
                data_id=data_id
            )

            record = await result.single()
            if not record:
                return None

            return self._node_to_data_item(dict(record["d"]))

    async def list_data_items(
        self,
        entity_id: Optional[str] = None,
        orphan_id: Optional[str] = None,
        data_type: Optional[str] = None,
        limit: int = 100
    ) -> List[DataItem]:
        """
        List DataItems with optional filtering.

        Args:
            entity_id: Filter by entity ID (optional)
            orphan_id: Filter by orphan ID (optional)
            data_type: Filter by data type (optional)
            limit: Maximum number of results

        Returns:
            List of DataItems
        """
        # Build query based on filters
        where_clauses = []
        params = {"limit": limit}

        if entity_id:
            where_clauses.append("d.entity_id = $entity_id")
            params["entity_id"] = entity_id

        if orphan_id:
            where_clauses.append("d.orphan_id = $orphan_id")
            params["orphan_id"] = orphan_id

        if data_type:
            where_clauses.append("d.type = $data_type")
            params["data_type"] = data_type

        where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        query = f"""
        MATCH (d:DataItem)
        {where_clause}
        RETURN d
        ORDER BY d.created_at DESC
        LIMIT $limit
        """

        async with self.neo4j.session() as session:
            result = await session.run(query, params)
            records = await result.data()

            return [self._node_to_data_item(dict(record["d"])) for record in records]

    async def delete_data_item(self, data_id: str) -> bool:
        """
        Delete a DataItem by ID.

        Args:
            data_id: DataItem ID

        Returns:
            True if deleted, False if not found
        """
        async with self.neo4j.session() as session:
            result = await session.run(
                """
                MATCH (d:DataItem {id: $data_id})
                DETACH DELETE d
                RETURN count(d) as deleted_count
                """,
                data_id=data_id
            )

            record = await result.single()
            return record is not None and record["deleted_count"] > 0

    async def link_data_to_entity(self, data_id: str, entity_id: str) -> bool:
        """
        Link a DataItem to an entity and create relationship.

        Args:
            data_id: DataItem ID
            entity_id: Entity (Person) ID

        Returns:
            True if linked successfully, False otherwise
        """
        async with self.neo4j.session() as session:
            # Update the data item's entity_id and create relationship
            result = await session.run(
                """
                MATCH (d:DataItem {id: $data_id})
                MATCH (p:Person {id: $entity_id})
                SET d.entity_id = $entity_id
                MERGE (p)-[r:HAS_DATA]->(d)
                RETURN count(r) as link_count
                """,
                data_id=data_id,
                entity_id=entity_id
            )

            record = await result.single()
            return record is not None and record["link_count"] > 0

    async def unlink_data_from_entity(self, data_id: str) -> bool:
        """
        Unlink a DataItem from its entity.

        Args:
            data_id: DataItem ID

        Returns:
            True if unlinked successfully, False otherwise
        """
        async with self.neo4j.session() as session:
            result = await session.run(
                """
                MATCH (d:DataItem {id: $data_id})
                OPTIONAL MATCH (p:Person)-[r:HAS_DATA]->(d)
                SET d.entity_id = null
                DELETE r
                RETURN count(d) as updated_count
                """,
                data_id=data_id
            )

            record = await result.single()
            return record is not None and record["updated_count"] > 0

    async def link_data_to_orphan(self, data_id: str, orphan_id: str) -> bool:
        """
        Link a DataItem to an orphan and create relationship.

        Args:
            data_id: DataItem ID
            orphan_id: Orphan ID

        Returns:
            True if linked successfully, False otherwise
        """
        async with self.neo4j.session() as session:
            result = await session.run(
                """
                MATCH (d:DataItem {id: $data_id})
                MATCH (o:Orphan {id: $orphan_id})
                SET d.orphan_id = $orphan_id
                MERGE (o)-[r:HAS_DATA]->(d)
                RETURN count(r) as link_count
                """,
                data_id=data_id,
                orphan_id=orphan_id
            )

            record = await result.single()
            return record is not None and record["link_count"] > 0

    async def find_similar_data(
        self,
        normalized_value: str,
        data_type: str,
        exclude_id: Optional[str] = None
    ) -> List[DataItem]:
        """
        Find DataItems with similar normalized values.

        Useful for detecting duplicates and suggesting matches.

        Args:
            normalized_value: Normalized value to search for
            data_type: Type of data
            exclude_id: DataItem ID to exclude from results

        Returns:
            List of similar DataItems
        """
        async with self.neo4j.session() as session:
            if exclude_id:
                result = await session.run(
                    """
                    MATCH (d:DataItem)
                    WHERE d.normalized_value = $normalized_value
                      AND d.type = $data_type
                      AND d.id <> $exclude_id
                    RETURN d
                    ORDER BY d.created_at DESC
                    """,
                    normalized_value=normalized_value,
                    data_type=data_type,
                    exclude_id=exclude_id
                )
            else:
                result = await session.run(
                    """
                    MATCH (d:DataItem)
                    WHERE d.normalized_value = $normalized_value
                      AND d.type = $data_type
                    RETURN d
                    ORDER BY d.created_at DESC
                    """,
                    normalized_value=normalized_value,
                    data_type=data_type
                )

            records = await result.data()
            return [self._node_to_data_item(dict(record["d"])) for record in records]

    async def find_by_hash(self, file_hash: str) -> List[DataItem]:
        """
        Find DataItems by file hash.

        Useful for detecting duplicate files.

        Args:
            file_hash: SHA-256 hash of the file

        Returns:
            List of DataItems with matching hash
        """
        async with self.neo4j.session() as session:
            result = await session.run(
                """
                MATCH (d:DataItem)
                WHERE d.hash = $file_hash
                RETURN d
                ORDER BY d.created_at DESC
                """,
                file_hash=file_hash
            )

            records = await result.data()
            return [self._node_to_data_item(dict(record["d"])) for record in records]

    # Helper methods

    def _compute_file_hash(self, file_path: str) -> Optional[str]:
        """
        Compute SHA-256 hash of a file.

        Args:
            file_path: Path to the file

        Returns:
            SHA-256 hash as hex string, or None if file cannot be read
        """
        try:
            hasher = hashlib.sha256()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except (FileNotFoundError, PermissionError, IOError):
            return None

    def _serialize_value(self, value: Any) -> str:
        """
        Serialize value for storage in Neo4j.

        Args:
            value: Value to serialize

        Returns:
            Serialized value as string
        """
        if isinstance(value, (dict, list)):
            import json
            return json.dumps(value)
        return str(value)

    def _serialize_metadata(self, metadata: dict) -> str:
        """
        Serialize metadata for storage in Neo4j.

        Args:
            metadata: Metadata dictionary

        Returns:
            JSON string
        """
        import json
        return json.dumps(metadata)

    def _node_to_data_item(self, node: dict) -> DataItem:
        """
        Convert Neo4j node to DataItem.

        Args:
            node: Neo4j node as dictionary

        Returns:
            DataItem instance
        """
        import json

        # Deserialize value if it's a JSON string
        value = node.get("value", "")
        try:
            value = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            pass

        # Deserialize metadata
        metadata = node.get("metadata", "{}")
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                metadata = {}

        # Parse created_at
        created_at = node.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.now()

        return DataItem(
            id=node["id"],
            type=node["type"],
            value=value,
            hash=node.get("hash"),
            normalized_value=node["normalized_value"],
            entity_id=node.get("entity_id"),
            orphan_id=node.get("orphan_id"),
            created_at=created_at,
            metadata=metadata
        )
