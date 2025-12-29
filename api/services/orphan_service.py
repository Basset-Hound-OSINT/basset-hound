"""
Orphan Data Service for Basset Hound OSINT Platform.

This service manages orphan data - unlinked identifiers (emails, phone numbers,
crypto addresses, etc.) that haven't been associated with entities yet. It provides
CRUD operations, search/filtering, auto-linking suggestions, and bulk operations.

Features:
- Full CRUD operations for orphan data management
- Advanced search and filtering capabilities
- Intelligent auto-linking with scoring algorithms
- Bulk import and duplicate detection
- Integration with Neo4j for persistent storage
- Production-ready error handling and logging
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from api.models.orphan import (
    IdentifierType,
    OrphanDataCreate,
    OrphanDataUpdate,
    OrphanDataResponse,
    OrphanDataList,
    OrphanLinkRequest,
    OrphanLinkResponse,
)

# Try to import fuzzy matcher for auto-linking
try:
    from api.services.fuzzy_matcher import (
        FuzzyMatcher,
        get_fuzzy_matcher,
        RAPIDFUZZ_AVAILABLE,
    )
except ImportError:
    RAPIDFUZZ_AVAILABLE = False
    FuzzyMatcher = None
    get_fuzzy_matcher = None


logger = logging.getLogger("basset_hound.orphan_service")


class OrphanService:
    """
    Service for managing orphan data in the OSINT platform.

    This service provides comprehensive orphan data management including:
    - CRUD operations for orphan records
    - Full-text search and filtering
    - Auto-linking suggestions with confidence scoring
    - Bulk operations for data import
    - Duplicate detection and prevention

    Usage:
        service = OrphanService(neo4j_handler)

        # Create orphan data
        orphan = service.create_orphan("project-123", orphan_data)

        # Search orphans
        results = service.search_orphans("project-123", "john@example.com")

        # Get auto-link suggestions
        suggestions = service.suggest_entity_matches("project-123", "orphan-id")

        # Link orphan to entity
        result = service.link_to_entity("project-123", "orphan-id", "entity-id")
    """

    # Auto-linking score thresholds
    SCORE_EXACT_MATCH = 10.0
    SCORE_FUZZY_HIGH = 9.0
    SCORE_FUZZY_MEDIUM = 7.0
    SCORE_FUZZY_LOW = 5.0
    SCORE_CONTEXT_HIGH = 3.0
    SCORE_CONTEXT_MEDIUM = 2.0
    SCORE_CONTEXT_LOW = 1.0
    SUGGESTION_THRESHOLD = 7.0

    # Identifier type to field mapping for auto-linking
    IDENTIFIER_FIELD_MAP = {
        IdentifierType.EMAIL: ["core.email", "contact.email", "online.email"],
        IdentifierType.PHONE: ["core.phone", "contact.phone"],
        IdentifierType.USERNAME: ["online.username", "social.username"],
        IdentifierType.CRYPTO_ADDRESS: ["financial.crypto_address", "blockchain.address"],
        IdentifierType.IP_ADDRESS: ["technical.ip_address", "network.ip"],
        IdentifierType.DOMAIN: ["online.domain", "website.domain"],
        IdentifierType.URL: ["online.url", "social.profile_url"],
        IdentifierType.MAC_ADDRESS: ["technical.mac_address", "network.mac"],
        IdentifierType.IMEI: ["device.imei", "technical.imei"],
    }

    def __init__(self, neo4j_handler):
        """
        Initialize the orphan service.

        Args:
            neo4j_handler: Neo4j database handler instance
        """
        self.neo4j = neo4j_handler
        self._fuzzy_matcher: Optional[FuzzyMatcher] = None
        self._ensure_orphan_constraints()

    @property
    def fuzzy_matcher(self) -> Optional[FuzzyMatcher]:
        """Get or create the fuzzy matcher instance for auto-linking."""
        if self._fuzzy_matcher is None and RAPIDFUZZ_AVAILABLE and get_fuzzy_matcher:
            try:
                self._fuzzy_matcher = get_fuzzy_matcher()
                logger.info("Fuzzy matcher initialized for orphan auto-linking")
            except Exception as e:
                logger.warning(f"Failed to initialize fuzzy matcher: {e}")
        return self._fuzzy_matcher

    def _ensure_orphan_constraints(self) -> None:
        """Ensure Neo4j constraints and indexes for orphan data."""
        try:
            with self.neo4j.driver.session() as session:
                constraints = [
                    "CREATE CONSTRAINT IF NOT EXISTS FOR (o:OrphanData) REQUIRE o.id IS UNIQUE",
                    "CREATE INDEX IF NOT EXISTS FOR (o:OrphanData) ON (o.identifier_type)",
                    "CREATE INDEX IF NOT EXISTS FOR (o:OrphanData) ON (o.identifier_value)",
                    "CREATE INDEX IF NOT EXISTS FOR (o:OrphanData) ON (o.discovered_date)",
                    "CREATE INDEX IF NOT EXISTS FOR (o:OrphanData) ON (o.linked_entity_id)",
                ]

                for constraint in constraints:
                    try:
                        session.run(constraint)
                    except Exception as e:
                        logger.warning(f"Constraint creation warning: {e}")

                logger.info("Orphan data constraints and indexes ensured")
        except Exception as e:
            logger.error(f"Failed to ensure orphan constraints: {e}")

    # =========================================================================
    # CRUD OPERATIONS
    # =========================================================================

    def create_orphan(
        self,
        project_id: str,
        orphan_data: OrphanDataCreate
    ) -> Optional[OrphanDataResponse]:
        """
        Create a new orphan data record.

        Args:
            project_id: Project ID to associate the orphan with
            orphan_data: Orphan data to create

        Returns:
            Created OrphanDataResponse or None if creation failed

        Raises:
            ValueError: If project doesn't exist or data is invalid
        """
        try:
            # Verify project exists
            project = self._get_project_by_id(project_id)
            if not project:
                raise ValueError(f"Project {project_id} not found")

            # Generate ID if not provided
            orphan_id = orphan_data.id or f"orphan-{uuid4()}"

            # Use current time if not provided
            discovered_date = orphan_data.discovered_date or datetime.now().isoformat()

            with self.neo4j.driver.session() as session:
                result = session.run("""
                    MATCH (project:Project)
                    WHERE project.id = $project_id OR project.safe_name = $project_id
                    CREATE (orphan:OrphanData {
                        id: $orphan_id,
                        identifier_type: $identifier_type,
                        identifier_value: $identifier_value,
                        source: $source,
                        notes: $notes,
                        tags: $tags,
                        confidence_score: $confidence_score,
                        discovered_date: $discovered_date,
                        metadata: $metadata,
                        linked_entity_id: null,
                        linked_at: null
                    })
                    CREATE (project)-[:HAS_ORPHAN]->(orphan)
                    RETURN orphan, project.id as proj_id
                """,
                    project_id=project_id,
                    orphan_id=orphan_id,
                    identifier_type=orphan_data.identifier_type.value,
                    identifier_value=orphan_data.identifier_value,
                    source=orphan_data.source,
                    notes=orphan_data.notes,
                    tags=orphan_data.tags,
                    confidence_score=orphan_data.confidence_score,
                    discovered_date=discovered_date,
                    metadata=self.neo4j.clean_data(orphan_data.metadata)
                )

                record = result.single()
                if record:
                    logger.info(f"Created orphan {orphan_id} in project {project_id}")
                    return self._orphan_node_to_response(
                        dict(record["orphan"]),
                        record["proj_id"]
                    )

                return None

        except Exception as e:
            logger.error(f"Failed to create orphan: {e}")
            raise

    def get_orphan(
        self,
        project_id: str,
        orphan_id: str
    ) -> Optional[OrphanDataResponse]:
        """
        Retrieve an orphan data record by ID.

        Args:
            project_id: Project ID
            orphan_id: Orphan data ID

        Returns:
            OrphanDataResponse or None if not found
        """
        try:
            with self.neo4j.driver.session() as session:
                result = session.run("""
                    MATCH (project:Project)-[:HAS_ORPHAN]->(orphan:OrphanData {id: $orphan_id})
                    WHERE project.id = $project_id OR project.safe_name = $project_id
                    RETURN orphan, project.id as proj_id
                """,
                    project_id=project_id,
                    orphan_id=orphan_id
                )

                record = result.single()
                if record:
                    return self._orphan_node_to_response(
                        dict(record["orphan"]),
                        record["proj_id"]
                    )

                return None

        except Exception as e:
            logger.error(f"Failed to get orphan {orphan_id}: {e}")
            return None

    def list_orphans(
        self,
        project_id: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 50,
        offset: int = 0
    ) -> OrphanDataList:
        """
        List orphan data records with optional filtering.

        Args:
            project_id: Project ID
            filters: Optional filter dictionary supporting:
                - identifier_type: Filter by type (str or list)
                - tags: Filter by tags (str or list, any match)
                - date_from: Minimum discovered date (ISO string)
                - date_to: Maximum discovered date (ISO string)
                - linked: Filter by linked status (bool)
                - min_confidence: Minimum confidence score (float)
                - max_confidence: Maximum confidence score (float)
            limit: Maximum results to return (max 200)
            offset: Number of results to skip

        Returns:
            OrphanDataList with orphans and total count
        """
        try:
            filters = filters or {}
            limit = min(max(1, limit), 200)
            offset = max(0, offset)

            # Build Cypher WHERE clauses
            where_clauses = []
            params = {
                "project_id": project_id,
                "limit": limit,
                "offset": offset,
            }

            # Identifier type filter
            if "identifier_type" in filters:
                id_types = filters["identifier_type"]
                if isinstance(id_types, str):
                    id_types = [id_types]
                where_clauses.append("orphan.identifier_type IN $identifier_types")
                params["identifier_types"] = id_types

            # Tags filter (any match)
            if "tags" in filters:
                tags = filters["tags"]
                if isinstance(tags, str):
                    tags = [tags]
                where_clauses.append("ANY(tag IN $tags WHERE tag IN orphan.tags)")
                params["tags"] = tags

            # Date range filters
            if "date_from" in filters:
                where_clauses.append("orphan.discovered_date >= $date_from")
                params["date_from"] = filters["date_from"]

            if "date_to" in filters:
                where_clauses.append("orphan.discovered_date <= $date_to")
                params["date_to"] = filters["date_to"]

            # Linked status filter
            if "linked" in filters:
                if filters["linked"]:
                    where_clauses.append("orphan.linked_entity_id IS NOT NULL")
                else:
                    where_clauses.append("orphan.linked_entity_id IS NULL")

            # Confidence score filters
            if "min_confidence" in filters:
                where_clauses.append("orphan.confidence_score >= $min_confidence")
                params["min_confidence"] = filters["min_confidence"]

            if "max_confidence" in filters:
                where_clauses.append("orphan.confidence_score <= $max_confidence")
                params["max_confidence"] = filters["max_confidence"]

            # Build WHERE clause
            where_sql = ""
            if where_clauses:
                where_sql = "AND " + " AND ".join(where_clauses)

            with self.neo4j.driver.session() as session:
                # Get total count
                count_result = session.run(f"""
                    MATCH (project:Project)-[:HAS_ORPHAN]->(orphan:OrphanData)
                    WHERE (project.id = $project_id OR project.safe_name = $project_id)
                    {where_sql}
                    RETURN count(orphan) as total
                """, params)

                total = count_result.single()["total"]

                # Get paginated results
                result = session.run(f"""
                    MATCH (project:Project)-[:HAS_ORPHAN]->(orphan:OrphanData)
                    WHERE (project.id = $project_id OR project.safe_name = $project_id)
                    {where_sql}
                    RETURN orphan, project.id as proj_id
                    ORDER BY orphan.discovered_date DESC
                    SKIP $offset
                    LIMIT $limit
                """, params)

                orphans = []
                for record in result:
                    orphan_response = self._orphan_node_to_response(
                        dict(record["orphan"]),
                        record["proj_id"]
                    )
                    if orphan_response:
                        orphans.append(orphan_response)

                return OrphanDataList(
                    orphans=orphans,
                    total=total,
                    project_id=project_id
                )

        except Exception as e:
            logger.error(f"Failed to list orphans: {e}")
            return OrphanDataList(orphans=[], total=0, project_id=project_id)

    def update_orphan(
        self,
        project_id: str,
        orphan_id: str,
        updates: OrphanDataUpdate
    ) -> Optional[OrphanDataResponse]:
        """
        Update an orphan data record (partial update).

        Args:
            project_id: Project ID
            orphan_id: Orphan data ID
            updates: Updates to apply (only provided fields are updated)

        Returns:
            Updated OrphanDataResponse or None if not found
        """
        try:
            # Build SET clauses for provided fields
            set_clauses = []
            params = {
                "project_id": project_id,
                "orphan_id": orphan_id,
            }

            update_dict = updates.model_dump(exclude_unset=True)

            for field, value in update_dict.items():
                if field == "identifier_type" and value is not None:
                    set_clauses.append(f"orphan.{field} = ${field}")
                    params[field] = value.value
                elif field == "metadata" and value is not None:
                    set_clauses.append(f"orphan.{field} = ${field}")
                    params[field] = self.neo4j.clean_data(value)
                elif value is not None:
                    set_clauses.append(f"orphan.{field} = ${field}")
                    params[field] = value

            if not set_clauses:
                # No updates provided
                return self.get_orphan(project_id, orphan_id)

            set_sql = ", ".join(set_clauses)

            with self.neo4j.driver.session() as session:
                result = session.run(f"""
                    MATCH (project:Project)-[:HAS_ORPHAN]->(orphan:OrphanData {{id: $orphan_id}})
                    WHERE project.id = $project_id OR project.safe_name = $project_id
                    SET {set_sql}
                    RETURN orphan, project.id as proj_id
                """, params)

                record = result.single()
                if record:
                    logger.info(f"Updated orphan {orphan_id}")
                    return self._orphan_node_to_response(
                        dict(record["orphan"]),
                        record["proj_id"]
                    )

                return None

        except Exception as e:
            logger.error(f"Failed to update orphan {orphan_id}: {e}")
            raise

    def delete_orphan(
        self,
        project_id: str,
        orphan_id: str
    ) -> bool:
        """
        Delete an orphan data record.

        Args:
            project_id: Project ID
            orphan_id: Orphan data ID

        Returns:
            True if deleted, False if not found
        """
        try:
            with self.neo4j.driver.session() as session:
                result = session.run("""
                    MATCH (project:Project)-[:HAS_ORPHAN]->(orphan:OrphanData {id: $orphan_id})
                    WHERE project.id = $project_id OR project.safe_name = $project_id
                    DETACH DELETE orphan
                    RETURN count(orphan) as deleted
                """,
                    project_id=project_id,
                    orphan_id=orphan_id
                )

                deleted_count = result.single()["deleted"]
                if deleted_count > 0:
                    logger.info(f"Deleted orphan {orphan_id}")
                    return True

                return False

        except Exception as e:
            logger.error(f"Failed to delete orphan {orphan_id}: {e}")
            return False

    # =========================================================================
    # SEARCH & FILTERING
    # =========================================================================

    def search_orphans(
        self,
        project_id: str,
        query: str,
        limit: int = 50
    ) -> List[OrphanDataResponse]:
        """
        Full-text search across orphan data.

        Searches in identifier_value, source, and notes fields.

        Args:
            project_id: Project ID
            query: Search query string
            limit: Maximum results to return

        Returns:
            List of matching OrphanDataResponse objects
        """
        try:
            if not query or not query.strip():
                return []

            search_lower = query.lower().strip()
            limit = min(max(1, limit), 200)

            with self.neo4j.driver.session() as session:
                result = session.run("""
                    MATCH (project:Project)-[:HAS_ORPHAN]->(orphan:OrphanData)
                    WHERE (project.id = $project_id OR project.safe_name = $project_id)
                    AND (
                        toLower(orphan.identifier_value) CONTAINS $query
                        OR toLower(orphan.source) CONTAINS $query
                        OR toLower(orphan.notes) CONTAINS $query
                    )
                    RETURN orphan, project.id as proj_id
                    ORDER BY orphan.discovered_date DESC
                    LIMIT $limit
                """,
                    project_id=project_id,
                    query=search_lower,
                    limit=limit
                )

                orphans = []
                for record in result:
                    orphan_response = self._orphan_node_to_response(
                        dict(record["orphan"]),
                        record["proj_id"]
                    )
                    if orphan_response:
                        orphans.append(orphan_response)

                logger.info(f"Search for '{query}' found {len(orphans)} orphans")
                return orphans

        except Exception as e:
            logger.error(f"Failed to search orphans: {e}")
            return []

    # =========================================================================
    # AUTO-LINKING
    # =========================================================================

    def suggest_entity_matches(
        self,
        project_id: str,
        orphan_id: str,
        max_suggestions: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Suggest entity matches for an orphan data record with scoring.

        Scoring algorithm:
        - Exact identifier match: 10.0 points
        - Fuzzy match (high): 9.0 points
        - Fuzzy match (medium): 7.0 points
        - Fuzzy match (low): 5.0 points
        - Context match: 1.0-3.0 points
        - Threshold for suggestions: >= 7.0

        Args:
            project_id: Project ID
            orphan_id: Orphan data ID
            max_suggestions: Maximum number of suggestions to return

        Returns:
            List of suggestion dictionaries with:
                - entity_id: Entity ID
                - score: Match score
                - match_type: Type of match (exact, fuzzy, context)
                - matched_field: Field that matched
                - entity_preview: Preview of entity data
        """
        try:
            # Get the orphan data
            orphan = self.get_orphan(project_id, orphan_id)
            if not orphan:
                logger.warning(f"Orphan {orphan_id} not found")
                return []

            # Get project
            project = self._get_project_by_id(project_id)
            if not project:
                logger.warning(f"Project {project_id} not found")
                return []

            project_safe_name = project.get("safe_name")

            # Get all entities in the project
            entities = self.neo4j.get_all_people(project_safe_name)

            if not entities:
                logger.info(f"No entities in project {project_id} for matching")
                return []

            # Calculate match scores for each entity
            suggestions = []
            identifier_type = orphan.identifier_type
            identifier_value = orphan.identifier_value

            # Determine which fields to check based on identifier type
            target_fields = self.IDENTIFIER_FIELD_MAP.get(
                identifier_type,
                []  # Empty list means check all fields
            )

            for entity in entities:
                entity_id = entity.get("id", "")
                profile = entity.get("profile", {})

                # Calculate match score
                score, match_type, matched_field = self._calculate_match_score(
                    identifier_value,
                    identifier_type,
                    profile,
                    target_fields
                )

                # Only include if above threshold
                if score >= self.SUGGESTION_THRESHOLD:
                    suggestions.append({
                        "entity_id": entity_id,
                        "score": score,
                        "match_type": match_type,
                        "matched_field": matched_field,
                        "entity_preview": self._extract_entity_preview(entity)
                    })

            # Sort by score descending
            suggestions.sort(key=lambda x: x["score"], reverse=True)

            # Limit results
            suggestions = suggestions[:max_suggestions]

            logger.info(
                f"Found {len(suggestions)} entity match suggestions "
                f"for orphan {orphan_id}"
            )

            return suggestions

        except Exception as e:
            logger.error(f"Failed to suggest matches for orphan {orphan_id}: {e}")
            return []

    def link_to_entity(
        self,
        project_id: str,
        orphan_id: str,
        entity_id: str,
        merge: bool = True,
        delete: bool = False
    ) -> OrphanLinkResponse:
        """
        Link an orphan data record to an entity.

        Args:
            project_id: Project ID
            orphan_id: Orphan data ID
            entity_id: Entity ID to link to
            merge: Whether to merge orphan data into entity profile
            delete: Whether to delete orphan after linking

        Returns:
            OrphanLinkResponse with operation results
        """
        try:
            # Get orphan and verify it exists
            orphan = self.get_orphan(project_id, orphan_id)
            if not orphan:
                return OrphanLinkResponse(
                    success=False,
                    orphan_id=orphan_id,
                    entity_id=entity_id,
                    merged=False,
                    deleted=False,
                    message=f"Orphan {orphan_id} not found"
                )

            # Get project
            project = self._get_project_by_id(project_id)
            if not project:
                return OrphanLinkResponse(
                    success=False,
                    orphan_id=orphan_id,
                    entity_id=entity_id,
                    merged=False,
                    deleted=False,
                    message=f"Project {project_id} not found"
                )

            project_safe_name = project.get("safe_name")

            # Verify entity exists
            entity = self.neo4j.get_person(project_safe_name, entity_id)
            if not entity:
                return OrphanLinkResponse(
                    success=False,
                    orphan_id=orphan_id,
                    entity_id=entity_id,
                    merged=False,
                    deleted=False,
                    message=f"Entity {entity_id} not found in project"
                )

            # Update orphan with linked entity
            linked_at = datetime.now().isoformat()

            with self.neo4j.driver.session() as session:
                session.run("""
                    MATCH (orphan:OrphanData {id: $orphan_id})
                    SET orphan.linked_entity_id = $entity_id,
                        orphan.linked_at = $linked_at
                """,
                    orphan_id=orphan_id,
                    entity_id=entity_id,
                    linked_at=linked_at
                )

            # Merge data into entity if requested
            merged = False
            if merge:
                merged = self._merge_orphan_to_entity(
                    orphan,
                    entity,
                    project_safe_name
                )

            # Delete orphan if requested
            deleted = False
            if delete:
                deleted = self.delete_orphan(project_id, orphan_id)

            message = "Orphan successfully linked to entity"
            if merged:
                message += " and data merged"
            if deleted:
                message += " and orphan deleted"

            logger.info(
                f"Linked orphan {orphan_id} to entity {entity_id} "
                f"(merged: {merged}, deleted: {deleted})"
            )

            return OrphanLinkResponse(
                success=True,
                orphan_id=orphan_id,
                entity_id=entity_id,
                merged=merged,
                deleted=deleted,
                message=message
            )

        except Exception as e:
            logger.error(f"Failed to link orphan {orphan_id} to entity: {e}")
            return OrphanLinkResponse(
                success=False,
                orphan_id=orphan_id,
                entity_id=entity_id,
                merged=False,
                deleted=False,
                message=f"Linking failed: {str(e)}"
            )

    # =========================================================================
    # BULK OPERATIONS
    # =========================================================================

    def import_orphans_bulk(
        self,
        project_id: str,
        orphans_list: List[OrphanDataCreate]
    ) -> Dict[str, Any]:
        """
        Batch import multiple orphan data records.

        Args:
            project_id: Project ID
            orphans_list: List of orphan data to import

        Returns:
            Dictionary with:
                - created: Number of orphans created
                - failed: Number that failed
                - orphan_ids: List of created orphan IDs
                - errors: List of error messages
        """
        try:
            if not orphans_list:
                return {
                    "created": 0,
                    "failed": 0,
                    "orphan_ids": [],
                    "errors": []
                }

            # Verify project exists
            project = self._get_project_by_id(project_id)
            if not project:
                return {
                    "created": 0,
                    "failed": len(orphans_list),
                    "orphan_ids": [],
                    "errors": [f"Project {project_id} not found"]
                }

            created_ids = []
            errors = []

            # Prepare batch data
            orphans_data = []
            now = datetime.now().isoformat()

            for orphan_create in orphans_list:
                orphan_id = orphan_create.id or f"orphan-{uuid4()}"
                discovered_date = orphan_create.discovered_date or now

                orphans_data.append({
                    "id": orphan_id,
                    "identifier_type": orphan_create.identifier_type.value,
                    "identifier_value": orphan_create.identifier_value,
                    "source": orphan_create.source,
                    "notes": orphan_create.notes,
                    "tags": orphan_create.tags,
                    "confidence_score": orphan_create.confidence_score,
                    "discovered_date": discovered_date,
                    "metadata": self.neo4j.clean_data(orphan_create.metadata)
                })

            # Batch create in Neo4j
            with self.neo4j.driver.session() as session:
                result = session.run("""
                    MATCH (project:Project)
                    WHERE project.id = $project_id OR project.safe_name = $project_id
                    UNWIND $orphans AS o
                    CREATE (orphan:OrphanData {
                        id: o.id,
                        identifier_type: o.identifier_type,
                        identifier_value: o.identifier_value,
                        source: o.source,
                        notes: o.notes,
                        tags: o.tags,
                        confidence_score: o.confidence_score,
                        discovered_date: o.discovered_date,
                        metadata: o.metadata,
                        linked_entity_id: null,
                        linked_at: null
                    })
                    CREATE (project)-[:HAS_ORPHAN]->(orphan)
                    RETURN collect(orphan.id) as created_ids
                """,
                    project_id=project_id,
                    orphans=orphans_data
                )

                record = result.single()
                if record:
                    created_ids = record["created_ids"]

            logger.info(
                f"Bulk imported {len(created_ids)}/{len(orphans_list)} orphans "
                f"to project {project_id}"
            )

            return {
                "created": len(created_ids),
                "failed": len(orphans_list) - len(created_ids),
                "orphan_ids": created_ids,
                "errors": errors
            }

        except Exception as e:
            logger.error(f"Bulk import failed: {e}")
            return {
                "created": 0,
                "failed": len(orphans_list) if orphans_list else 0,
                "orphan_ids": [],
                "errors": [str(e)]
            }

    def find_duplicates(
        self,
        project_id: str,
        similarity_threshold: float = 0.95
    ) -> List[Dict[str, Any]]:
        """
        Find duplicate orphan data records.

        Duplicates are identified by:
        - Same identifier_type and exact identifier_value match
        - Same identifier_type and fuzzy match above threshold

        Args:
            project_id: Project ID
            similarity_threshold: Fuzzy matching threshold (0.0-1.0)

        Returns:
            List of duplicate groups, each containing:
                - orphan_ids: List of duplicate orphan IDs
                - identifier_type: Type of identifier
                - identifier_value: The (primary) identifier value
                - match_type: 'exact' or 'fuzzy'
        """
        try:
            # Get all orphans in the project
            all_orphans = self.list_orphans(project_id, limit=10000)

            if all_orphans.total < 2:
                return []

            duplicates = []
            processed = set()

            orphans_by_type: Dict[str, List[OrphanDataResponse]] = {}

            # Group by identifier type
            for orphan in all_orphans.orphans:
                id_type = orphan.identifier_type
                if id_type not in orphans_by_type:
                    orphans_by_type[id_type] = []
                orphans_by_type[id_type].append(orphan)

            # Find duplicates within each type
            for id_type, orphans in orphans_by_type.items():
                if len(orphans) < 2:
                    continue

                # Check exact matches
                value_map: Dict[str, List[str]] = {}
                for orphan in orphans:
                    value_lower = orphan.identifier_value.lower().strip()
                    if value_lower not in value_map:
                        value_map[value_lower] = []
                    value_map[value_lower].append(orphan.id)

                # Add exact duplicate groups
                for value, orphan_ids in value_map.items():
                    if len(orphan_ids) > 1:
                        group_key = tuple(sorted(orphan_ids))
                        if group_key not in processed:
                            duplicates.append({
                                "orphan_ids": orphan_ids,
                                "identifier_type": id_type,
                                "identifier_value": value,
                                "match_type": "exact"
                            })
                            processed.add(group_key)

                # Check fuzzy matches if fuzzy matcher available
                if self.fuzzy_matcher and len(orphans) < 1000:  # Limit for performance
                    for i, orphan1 in enumerate(orphans):
                        for orphan2 in orphans[i + 1:]:
                            if orphan1.id == orphan2.id:
                                continue

                            # Skip if already in exact match group
                            group_key = tuple(sorted([orphan1.id, orphan2.id]))
                            if group_key in processed:
                                continue

                            # Calculate similarity
                            similarity = self.fuzzy_matcher.calculate_similarity(
                                orphan1.identifier_value,
                                orphan2.identifier_value,
                                normalize=True
                            )

                            if similarity >= similarity_threshold:
                                duplicates.append({
                                    "orphan_ids": [orphan1.id, orphan2.id],
                                    "identifier_type": id_type,
                                    "identifier_value": orphan1.identifier_value,
                                    "match_type": "fuzzy",
                                    "similarity": similarity
                                })
                                processed.add(group_key)

            logger.info(f"Found {len(duplicates)} duplicate groups in project {project_id}")
            return duplicates

        except Exception as e:
            logger.error(f"Failed to find duplicates: {e}")
            return []

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _orphan_node_to_response(
        self,
        orphan_node: Dict[str, Any],
        project_id: str
    ) -> Optional[OrphanDataResponse]:
        """Convert Neo4j orphan node to OrphanDataResponse."""
        try:
            return OrphanDataResponse(
                id=orphan_node.get("id", ""),
                project_id=project_id,
                identifier_type=IdentifierType(orphan_node.get("identifier_type", "other")),
                identifier_value=orphan_node.get("identifier_value", ""),
                source=orphan_node.get("source"),
                notes=orphan_node.get("notes"),
                tags=orphan_node.get("tags", []),
                confidence_score=orphan_node.get("confidence_score"),
                discovered_date=orphan_node.get("discovered_date", ""),
                metadata=orphan_node.get("metadata", {}),
                linked_entity_id=orphan_node.get("linked_entity_id"),
                linked_at=orphan_node.get("linked_at")
            )
        except Exception as e:
            logger.error(f"Failed to convert orphan node: {e}")
            return None

    def _get_project_by_id(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get project by ID or safe_name."""
        try:
            projects = self.neo4j.get_all_projects()
            for project in projects:
                if project.get("id") == project_id or project.get("safe_name") == project_id:
                    return project
            return None
        except Exception:
            return None

    def _calculate_match_score(
        self,
        identifier_value: str,
        identifier_type: IdentifierType,
        entity_profile: Dict[str, Any],
        target_fields: List[str]
    ) -> Tuple[float, str, str]:
        """
        Calculate match score between orphan identifier and entity profile.

        Returns:
            Tuple of (score, match_type, matched_field)
        """
        max_score = 0.0
        best_match_type = "none"
        best_field = ""

        identifier_lower = identifier_value.lower().strip()

        # Determine fields to search
        fields_to_check = []

        if target_fields:
            # Use specific target fields for this identifier type
            for field_path in target_fields:
                fields_to_check.append(field_path)
        else:
            # Check all fields
            for section_id, fields in entity_profile.items():
                if isinstance(fields, dict):
                    for field_id in fields.keys():
                        fields_to_check.append(f"{section_id}.{field_id}")

        # Check each field
        for field_path in fields_to_check:
            field_values = self._extract_field_values(entity_profile, field_path)

            for value in field_values:
                if not value:
                    continue

                value_lower = str(value).lower().strip()

                # Exact match
                if identifier_lower == value_lower:
                    if self.SCORE_EXACT_MATCH > max_score:
                        max_score = self.SCORE_EXACT_MATCH
                        best_match_type = "exact"
                        best_field = field_path
                    continue

                # Fuzzy match if available
                if self.fuzzy_matcher:
                    similarity = self.fuzzy_matcher.calculate_similarity(
                        identifier_value,
                        str(value),
                        normalize=True
                    )

                    # Calculate fuzzy score
                    fuzzy_score = 0.0
                    if similarity >= 0.95:
                        fuzzy_score = self.SCORE_FUZZY_HIGH
                    elif similarity >= 0.85:
                        fuzzy_score = self.SCORE_FUZZY_MEDIUM
                    elif similarity >= 0.75:
                        fuzzy_score = self.SCORE_FUZZY_LOW

                    if fuzzy_score > max_score:
                        max_score = fuzzy_score
                        best_match_type = "fuzzy"
                        best_field = field_path

                # Context match (substring)
                elif identifier_lower in value_lower or value_lower in identifier_lower:
                    context_score = self.SCORE_CONTEXT_MEDIUM
                    if context_score > max_score:
                        max_score = context_score
                        best_match_type = "context"
                        best_field = field_path

        return max_score, best_match_type, best_field

    def _extract_field_values(
        self,
        profile: Dict[str, Any],
        field_path: str
    ) -> List[str]:
        """Extract field value(s) from entity profile using dot notation."""
        parts = field_path.split('.')
        current = profile

        for part in parts:
            if current is None:
                return []

            if isinstance(current, dict):
                current = current.get(part)
            else:
                return []

        # Convert to list of strings
        if current is None:
            return []
        if isinstance(current, list):
            return [str(v) for v in current if v]
        return [str(current)] if current else []

    def _extract_entity_preview(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        """Extract preview data from entity for display."""
        preview = {
            "id": entity.get("id", ""),
            "created_at": entity.get("created_at", ""),
        }

        profile = entity.get("profile", {})

        # Try to extract name
        if "core" in profile:
            core = profile["core"]
            if "name" in core:
                names = core["name"]
                if isinstance(names, list) and names:
                    preview["name"] = names[0]
                elif isinstance(names, dict):
                    preview["name"] = names
                elif isinstance(names, str):
                    preview["name"] = names

            # Include email if present
            if "email" in core:
                emails = core["email"]
                if isinstance(emails, list) and emails:
                    preview["email"] = emails[0]
                elif isinstance(emails, str):
                    preview["email"] = emails

        return preview

    def _merge_orphan_to_entity(
        self,
        orphan: OrphanDataResponse,
        entity: Dict[str, Any],
        project_safe_name: str
    ) -> bool:
        """
        Merge orphan data into entity profile.

        Attempts to add the orphan identifier to the appropriate field
        in the entity profile based on the identifier type.
        """
        try:
            # Determine target field based on identifier type
            target_fields = self.IDENTIFIER_FIELD_MAP.get(
                orphan.identifier_type,
                []
            )

            if not target_fields:
                logger.warning(
                    f"No target field mapping for identifier type "
                    f"{orphan.identifier_type}"
                )
                return False

            # Use the first target field
            field_path = target_fields[0]
            parts = field_path.split('.')

            if len(parts) < 2:
                return False

            section_id = parts[0]
            field_id = '.'.join(parts[1:])

            # Get current field value
            entity_id = entity.get("id")
            profile = entity.get("profile", {})
            current_value = profile.get(section_id, {}).get(field_id, [])

            # Ensure it's a list
            if not isinstance(current_value, list):
                if current_value:
                    current_value = [current_value]
                else:
                    current_value = []

            # Add orphan value if not already present
            if orphan.identifier_value not in current_value:
                current_value.append(orphan.identifier_value)

                # Update entity in database
                self.neo4j.set_person_field(
                    entity_id,
                    section_id,
                    field_id,
                    current_value
                )

                logger.info(
                    f"Merged orphan {orphan.id} value into entity {entity_id} "
                    f"field {field_path}"
                )
                return True

            return True

        except Exception as e:
            logger.error(f"Failed to merge orphan to entity: {e}")
            return False


# =========================================================================
# MODULE-LEVEL FUNCTIONS
# =========================================================================

def get_orphan_service(neo4j_handler) -> OrphanService:
    """
    Factory function to create an OrphanService instance.

    Args:
        neo4j_handler: Neo4j database handler

    Returns:
        OrphanService instance
    """
    return OrphanService(neo4j_handler)
