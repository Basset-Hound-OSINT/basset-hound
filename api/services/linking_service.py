"""
LinkingService for Phase 43.5: Linking Actions.

Provides operations for acting on smart suggestions:
- Link DataItems together
- Merge entities based on data matches
- Create relationships from suggestions
- Link orphans to entities
- Dismiss suggestions with reason tracking

All operations require explicit user intent (reason parameter) and create
comprehensive audit trails for accountability.

Phase 45 Integration: WebSocket notifications for linking actions.
"""

import json
from datetime import datetime
from typing import Dict, List, Optional

from api.models.data_item import DataItem
from api.models.relationship import RelationshipType, ConfidenceLevel
from api.services.neo4j_service import AsyncNeo4jService
from api.services.data_service import DataService


class LinkingAction:
    """Model for tracking a linking action in the audit trail."""

    def __init__(
        self,
        action_id: str,
        action_type: str,
        created_at: datetime,
        created_by: str,
        reason: str,
        details: Dict,
        confidence: float = 0.0,
    ):
        self.action_id = action_id
        self.action_type = action_type
        self.created_at = created_at
        self.created_by = created_by
        self.reason = reason
        self.details = details
        self.confidence = confidence

    def to_dict(self) -> Dict:
        """Convert to dictionary for storage."""
        return {
            "action_id": self.action_id,
            "action_type": self.action_type,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "reason": self.reason,
            "details": self.details,
            "confidence": self.confidence,
        }


class LinkingService:
    """
    Service for managing linking actions based on smart suggestions.

    All operations require a reason parameter to ensure human accountability.
    Every action creates an audit trail for compliance and undo functionality.
    """

    def __init__(
        self,
        neo4j_service: AsyncNeo4jService,
        enable_notifications: bool = True
    ):
        """
        Initialize the LinkingService.

        Args:
            neo4j_service: AsyncNeo4jService instance
            enable_notifications: Whether to broadcast WebSocket notifications (default: True)
        """
        self.neo4j = neo4j_service
        self.data_service = DataService(neo4j_service)
        self.enable_notifications = enable_notifications

    async def link_data_items(
        self,
        data_id_1: str,
        data_id_2: str,
        reason: str,
        confidence: float = 0.8,
        created_by: str = "system",
    ) -> Dict:
        """
        Link two DataItems together with a LINKED_TO relationship.

        This is useful when two data items represent the same information
        (e.g., same email appearing in different contexts, same image uploaded twice).

        Args:
            data_id_1: First DataItem ID
            data_id_2: Second DataItem ID
            reason: Human-readable reason for the link (required)
            confidence: Confidence score 0.0-1.0 (default: 0.8)
            created_by: User or system that created the link

        Returns:
            Dictionary with success status and linking details

        Raises:
            ValueError: If reason is empty or data items don't exist
        """
        if not reason or not reason.strip():
            raise ValueError("Reason is required for linking data items")

        # Verify both data items exist
        data_1 = await self.data_service.get_data_item(data_id_1)
        data_2 = await self.data_service.get_data_item(data_id_2)

        if not data_1:
            raise ValueError(f"DataItem not found: {data_id_1}")
        if not data_2:
            raise ValueError(f"DataItem not found: {data_id_2}")

        # Prevent self-linking
        if data_id_1 == data_id_2:
            raise ValueError("Cannot link a data item to itself")

        # Create linking action ID
        action_id = f"link_action_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        # Create LINKED_TO relationship in Neo4j
        async with self.neo4j.session() as session:
            result = await session.run(
                """
                MATCH (d1:DataItem {id: $data_id_1})
                MATCH (d2:DataItem {id: $data_id_2})

                // Create bidirectional LINKED_TO relationships
                MERGE (d1)-[r1:LINKED_TO]->(d2)
                SET r1.reason = $reason,
                    r1.confidence = $confidence,
                    r1.created_at = $created_at,
                    r1.created_by = $created_by,
                    r1.action_id = $action_id

                MERGE (d2)-[r2:LINKED_TO]->(d1)
                SET r2.reason = $reason,
                    r2.confidence = $confidence,
                    r2.created_at = $created_at,
                    r2.created_by = $created_by,
                    r2.action_id = $action_id

                RETURN r1, r2
                """,
                data_id_1=data_id_1,
                data_id_2=data_id_2,
                reason=reason,
                confidence=confidence,
                created_at=datetime.now().isoformat(),
                created_by=created_by,
                action_id=action_id,
            )

            record = await result.single()
            if not record:
                raise RuntimeError("Failed to create LINKED_TO relationship")

        # Create audit trail
        await self._create_audit_trail(
            action_id=action_id,
            action_type="link_data_items",
            created_by=created_by,
            reason=reason,
            details={
                "data_id_1": data_id_1,
                "data_id_2": data_id_2,
                "confidence": confidence,
            },
            confidence=confidence,
        )

        # Phase 45: Broadcast WebSocket notification
        if self.enable_notifications:
            try:
                from api.services.notification_service import get_notification_service

                # Extract project_id from entities owning the data items
                project_id = await self._get_project_id_from_data(data_id_1)
                if project_id:
                    notification_service = get_notification_service()
                    await notification_service.broadcast_data_linked(
                        project_id=project_id,
                        data_id_1=data_id_1,
                        data_id_2=data_id_2,
                        reason=reason,
                        confidence=confidence
                    )
            except Exception as e:
                # Don't fail the operation if notification fails
                logger = logging.getLogger("basset_hound.linking_service")
                logger.warning(f"Failed to broadcast data_linked event: {e}")

        return {
            "success": True,
            "action_id": action_id,
            "linked_data_items": [data_id_1, data_id_2],
            "reason": reason,
            "confidence": confidence,
            "created_at": datetime.now().isoformat(),
        }

    async def merge_entities(
        self,
        entity_id_1: str,
        entity_id_2: str,
        keep_entity_id: str,
        reason: str,
        created_by: str = "system",
    ) -> Dict:
        """
        Merge two entities, moving all data to the kept entity.

        This operation is IRREVERSIBLE (unless audit trail is used for rollback).
        All DataItems, relationships, and profile data from the discarded entity
        are moved to the kept entity.

        Args:
            entity_id_1: First entity ID
            entity_id_2: Second entity ID
            keep_entity_id: Which entity to keep (must be entity_id_1 or entity_id_2)
            reason: Human-readable reason for merge (required)
            created_by: User performing the merge

        Returns:
            Dictionary with merge results and audit information

        Raises:
            ValueError: If reason is empty, entities don't exist, or keep_entity_id is invalid
        """
        if not reason or not reason.strip():
            raise ValueError("Reason is required for merging entities")

        if keep_entity_id not in [entity_id_1, entity_id_2]:
            raise ValueError(f"keep_entity_id must be either {entity_id_1} or {entity_id_2}")

        discard_entity_id = entity_id_2 if keep_entity_id == entity_id_1 else entity_id_1

        # Create action ID
        action_id = f"merge_action_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        async with self.neo4j.session() as session:
            # 1. Verify both entities exist
            verify_result = await session.run(
                """
                MATCH (e1:Person {id: $entity_id_1})
                MATCH (e2:Person {id: $entity_id_2})
                RETURN e1.id as id1, e2.id as id2
                """,
                entity_id_1=entity_id_1,
                entity_id_2=entity_id_2,
            )
            verify_record = await verify_result.single()
            if not verify_record:
                raise ValueError(f"One or both entities not found: {entity_id_1}, {entity_id_2}")

            # 2. Move all DataItems from discarded entity to kept entity
            data_result = await session.run(
                """
                MATCH (discard:Person {id: $discard_id})-[r:HAS_DATA]->(d:DataItem)
                MATCH (keep:Person {id: $keep_id})

                // Update DataItem's entity_id
                SET d.entity_id = $keep_id

                // Delete old relationship and create new one
                DELETE r
                MERGE (keep)-[new_r:HAS_DATA]->(d)

                RETURN count(d) as data_moved
                """,
                discard_id=discard_entity_id,
                keep_id=keep_entity_id,
            )
            data_record = await data_result.single()
            data_moved = data_record["data_moved"] if data_record else 0

            # 3. Merge profile data (JSON merge in application layer)
            # Get both profiles
            profile_result = await session.run(
                """
                MATCH (keep:Person {id: $keep_id})
                MATCH (discard:Person {id: $discard_id})
                RETURN keep.profile as keep_profile, discard.profile as discard_profile
                """,
                keep_id=keep_entity_id,
                discard_id=discard_entity_id,
            )
            profile_record = await profile_result.single()

            if profile_record:
                keep_profile = json.loads(profile_record["keep_profile"]) if isinstance(profile_record["keep_profile"], str) else profile_record["keep_profile"]
                discard_profile = json.loads(profile_record["discard_profile"]) if isinstance(profile_record["discard_profile"], str) else profile_record["discard_profile"]

                # Merge profiles (keep takes precedence, combine lists)
                merged_profile = self._merge_profiles(keep_profile or {}, discard_profile or {})

                # Update kept entity with merged profile
                await session.run(
                    """
                    MATCH (keep:Person {id: $keep_id})
                    SET keep.profile = $merged_profile
                    """,
                    keep_id=keep_entity_id,
                    merged_profile=json.dumps(merged_profile),
                )

            # 4. Move all relationships from discarded entity to kept entity
            rel_result = await session.run(
                """
                MATCH (discard:Person {id: $discard_id})-[r:TAGGED]-(other:Person)
                MATCH (keep:Person {id: $keep_id})
                WHERE other.id <> $keep_id

                // Create new relationship on kept entity
                MERGE (keep)-[new_r:TAGGED]-(other)
                SET new_r = properties(r)

                // Delete old relationship
                DELETE r

                RETURN count(r) as relationships_moved
                """,
                discard_id=discard_entity_id,
                keep_id=keep_entity_id,
            )
            rel_record = await rel_result.single()
            relationships_moved = rel_record["relationships_moved"] if rel_record else 0

            # 5. Mark discarded entity as merged (don't delete yet for audit trail)
            await session.run(
                """
                MATCH (discard:Person {id: $discard_id})
                SET discard.merged_into = $keep_id,
                    discard.merged_at = $merged_at,
                    discard.merge_reason = $reason,
                    discard.merge_action_id = $action_id
                """,
                discard_id=discard_entity_id,
                keep_id=keep_entity_id,
                merged_at=datetime.now().isoformat(),
                reason=reason,
                action_id=action_id,
            )

        # Create audit trail
        await self._create_audit_trail(
            action_id=action_id,
            action_type="merge_entities",
            created_by=created_by,
            reason=reason,
            details={
                "entity_id_1": entity_id_1,
                "entity_id_2": entity_id_2,
                "kept_entity_id": keep_entity_id,
                "discarded_entity_id": discard_entity_id,
                "data_items_moved": data_moved,
                "relationships_moved": relationships_moved,
            },
            confidence=1.0,
        )

        # Phase 45: Broadcast WebSocket notification
        if self.enable_notifications:
            try:
                from api.services.notification_service import get_notification_service

                # Extract project_id from kept entity
                project_id = await self._get_project_id_from_entity(keep_entity_id)
                if project_id:
                    notification_service = get_notification_service()
                    await notification_service.broadcast_entity_merged(
                        project_id=project_id,
                        entity_id_1=entity_id_1,
                        entity_id_2=entity_id_2,
                        kept_entity_id=keep_entity_id,
                        reason=reason,
                        merged_data_count=data_moved
                    )
            except Exception as e:
                # Don't fail the operation if notification fails
                import logging
                logger = logging.getLogger("basset_hound.linking_service")
                logger.warning(f"Failed to broadcast entity_merged event: {e}")

        return {
            "success": True,
            "action_id": action_id,
            "kept_entity_id": keep_entity_id,
            "merged_entity_id": discard_entity_id,
            "data_items_moved": data_moved,
            "relationships_moved": relationships_moved,
            "reason": reason,
            "created_at": datetime.now().isoformat(),
            "warning": "This merge is irreversible. The discarded entity has been marked as merged.",
        }

    async def create_relationship_from_suggestion(
        self,
        entity_id_1: str,
        entity_id_2: str,
        relationship_type: str,
        reason: str,
        confidence: Optional[str] = None,
        created_by: str = "system",
    ) -> Dict:
        """
        Create a relationship between two entities based on a suggestion.

        This is used when a suggestion indicates entities are related but NOT duplicates.
        For example, two people sharing an address might work together or be family.

        Args:
            entity_id_1: First entity ID (source)
            entity_id_2: Second entity ID (target)
            relationship_type: Type of relationship (WORKS_WITH, KNOWS, etc.)
            reason: Human-readable reason for creating relationship (required)
            confidence: Confidence level (confirmed, high, medium, low, unverified)
            created_by: User creating the relationship

        Returns:
            Dictionary with relationship creation details

        Raises:
            ValueError: If reason is empty or entities don't exist
        """
        if not reason or not reason.strip():
            raise ValueError("Reason is required for creating relationships")

        # Validate relationship type
        try:
            rel_type = RelationshipType(relationship_type)
        except ValueError:
            raise ValueError(f"Invalid relationship type: {relationship_type}")

        # Set default confidence
        if confidence:
            try:
                conf_level = ConfidenceLevel(confidence)
            except ValueError:
                raise ValueError(f"Invalid confidence level: {confidence}")
        else:
            conf_level = ConfidenceLevel.UNVERIFIED

        # Create action ID
        action_id = f"relationship_action_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        async with self.neo4j.session() as session:
            # Verify both entities exist
            verify_result = await session.run(
                """
                MATCH (e1:Person {id: $entity_id_1})
                MATCH (e2:Person {id: $entity_id_2})
                RETURN e1.id as id1, e2.id as id2
                """,
                entity_id_1=entity_id_1,
                entity_id_2=entity_id_2,
            )
            verify_record = await verify_result.single()
            if not verify_record:
                raise ValueError(f"One or both entities not found: {entity_id_1}, {entity_id_2}")

            # Create TAGGED relationship with properties
            result = await session.run(
                """
                MATCH (e1:Person {id: $entity_id_1})
                MATCH (e2:Person {id: $entity_id_2})

                MERGE (e1)-[r:TAGGED]->(e2)
                SET r.relationship_type = $relationship_type,
                    r.confidence = $confidence,
                    r.reason = $reason,
                    r.source = $source,
                    r.created_at = $created_at,
                    r.created_by = $created_by,
                    r.action_id = $action_id

                RETURN r
                """,
                entity_id_1=entity_id_1,
                entity_id_2=entity_id_2,
                relationship_type=rel_type.value,
                confidence=conf_level.value,
                reason=reason,
                source="smart_suggestion",
                created_at=datetime.now().isoformat(),
                created_by=created_by,
                action_id=action_id,
            )

            record = await result.single()
            if not record:
                raise RuntimeError("Failed to create relationship")

            # If symmetric relationship, create inverse
            if RelationshipType.is_symmetric(rel_type):
                await session.run(
                    """
                    MATCH (e1:Person {id: $entity_id_1})
                    MATCH (e2:Person {id: $entity_id_2})

                    MERGE (e2)-[r:TAGGED]->(e1)
                    SET r.relationship_type = $relationship_type,
                        r.confidence = $confidence,
                        r.reason = $reason,
                        r.source = $source,
                        r.created_at = $created_at,
                        r.created_by = $created_by,
                        r.action_id = $action_id
                    """,
                    entity_id_1=entity_id_1,
                    entity_id_2=entity_id_2,
                    relationship_type=rel_type.value,
                    confidence=conf_level.value,
                    reason=reason,
                    source="smart_suggestion",
                    created_at=datetime.now().isoformat(),
                    created_by=created_by,
                    action_id=action_id,
                )

        # Create audit trail
        await self._create_audit_trail(
            action_id=action_id,
            action_type="create_relationship",
            created_by=created_by,
            reason=reason,
            details={
                "entity_id_1": entity_id_1,
                "entity_id_2": entity_id_2,
                "relationship_type": rel_type.value,
                "confidence": conf_level.value,
                "is_symmetric": RelationshipType.is_symmetric(rel_type),
            },
            confidence=0.8,
        )

        return {
            "success": True,
            "action_id": action_id,
            "source_entity_id": entity_id_1,
            "target_entity_id": entity_id_2,
            "relationship_type": rel_type.value,
            "confidence": conf_level.value,
            "reason": reason,
            "is_symmetric": RelationshipType.is_symmetric(rel_type),
            "created_at": datetime.now().isoformat(),
        }

    async def link_orphan_to_entity(
        self,
        orphan_id: str,
        entity_id: str,
        reason: str,
        created_by: str = "system",
    ) -> Dict:
        """
        Convert orphan data to entity data by linking it to an entity.

        Moves all DataItems from the orphan to the entity and marks the orphan
        as resolved.

        Args:
            orphan_id: Orphan ID to link
            entity_id: Entity ID to link to
            reason: Human-readable reason for linking (required)
            created_by: User performing the action

        Returns:
            Dictionary with linking results

        Raises:
            ValueError: If reason is empty or orphan/entity don't exist
        """
        if not reason or not reason.strip():
            raise ValueError("Reason is required for linking orphans to entities")

        # Create action ID
        action_id = f"orphan_link_action_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        async with self.neo4j.session() as session:
            # Verify orphan and entity exist
            verify_result = await session.run(
                """
                MATCH (o:Orphan {id: $orphan_id})
                MATCH (e:Person {id: $entity_id})
                RETURN o.id as orphan_id, e.id as entity_id
                """,
                orphan_id=orphan_id,
                entity_id=entity_id,
            )
            verify_record = await verify_result.single()
            if not verify_record:
                raise ValueError(f"Orphan or entity not found: {orphan_id}, {entity_id}")

            # Move all DataItems from orphan to entity
            data_result = await session.run(
                """
                MATCH (o:Orphan {id: $orphan_id})-[r:HAS_DATA]->(d:DataItem)
                MATCH (e:Person {id: $entity_id})

                // Update DataItem to point to entity
                SET d.entity_id = $entity_id,
                    d.orphan_id = null

                // Delete orphan relationship and create entity relationship
                DELETE r
                MERGE (e)-[new_r:HAS_DATA]->(d)

                RETURN count(d) as data_moved
                """,
                orphan_id=orphan_id,
                entity_id=entity_id,
            )
            data_record = await data_result.single()
            data_moved = data_record["data_moved"] if data_record else 0

            # Mark orphan as resolved
            await session.run(
                """
                MATCH (o:Orphan {id: $orphan_id})
                SET o.resolved = true,
                    o.resolved_at = $resolved_at,
                    o.resolved_by = $created_by,
                    o.linked_to_entity = $entity_id,
                    o.resolution_reason = $reason,
                    o.resolution_action_id = $action_id
                """,
                orphan_id=orphan_id,
                entity_id=entity_id,
                resolved_at=datetime.now().isoformat(),
                created_by=created_by,
                reason=reason,
                action_id=action_id,
            )

        # Create audit trail
        await self._create_audit_trail(
            action_id=action_id,
            action_type="link_orphan_to_entity",
            created_by=created_by,
            reason=reason,
            details={
                "orphan_id": orphan_id,
                "entity_id": entity_id,
                "data_items_moved": data_moved,
            },
            confidence=1.0,
        )

        return {
            "success": True,
            "action_id": action_id,
            "orphan_id": orphan_id,
            "entity_id": entity_id,
            "data_items_moved": data_moved,
            "reason": reason,
            "created_at": datetime.now().isoformat(),
        }

    async def dismiss_suggestion(
        self,
        entity_id: str,
        data_id: str,
        reason: str,
        created_by: str = "system",
    ) -> Dict:
        """
        Dismiss a suggestion so it doesn't reappear (unless data changes).

        Creates a DISMISSED_SUGGESTION relationship between entity and data
        to track that the user has explicitly rejected this suggestion.

        Args:
            entity_id: Entity ID
            data_id: DataItem ID that was suggested
            reason: Why the suggestion was dismissed (required)
            created_by: User dismissing the suggestion

        Returns:
            Dictionary with dismissal details

        Raises:
            ValueError: If reason is empty or entity/data don't exist
        """
        if not reason or not reason.strip():
            raise ValueError("Reason is required for dismissing suggestions")

        # Create action ID
        action_id = f"dismiss_action_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        async with self.neo4j.session() as session:
            # Verify entity and data item exist
            verify_result = await session.run(
                """
                MATCH (e:Person {id: $entity_id})
                MATCH (d:DataItem {id: $data_id})
                RETURN e.id as entity_id, d.id as data_id
                """,
                entity_id=entity_id,
                data_id=data_id,
            )
            verify_record = await verify_result.single()
            if not verify_record:
                raise ValueError(f"Entity or data item not found: {entity_id}, {data_id}")

            # Create DISMISSED_SUGGESTION relationship
            result = await session.run(
                """
                MATCH (e:Person {id: $entity_id})
                MATCH (d:DataItem {id: $data_id})

                MERGE (e)-[r:DISMISSED_SUGGESTION]->(d)
                SET r.reason = $reason,
                    r.dismissed_at = $dismissed_at,
                    r.dismissed_by = $created_by,
                    r.action_id = $action_id

                RETURN r
                """,
                entity_id=entity_id,
                data_id=data_id,
                reason=reason,
                dismissed_at=datetime.now().isoformat(),
                created_by=created_by,
                action_id=action_id,
            )

            record = await result.single()
            if not record:
                raise RuntimeError("Failed to create DISMISSED_SUGGESTION relationship")

        # Create audit trail
        await self._create_audit_trail(
            action_id=action_id,
            action_type="dismiss_suggestion",
            created_by=created_by,
            reason=reason,
            details={
                "entity_id": entity_id,
                "data_id": data_id,
            },
            confidence=1.0,
        )

        return {
            "success": True,
            "action_id": action_id,
            "entity_id": entity_id,
            "data_id": data_id,
            "reason": reason,
            "dismissed_at": datetime.now().isoformat(),
        }

    # Helper methods

    def _merge_profiles(self, keep_profile: Dict, discard_profile: Dict) -> Dict:
        """
        Merge two profile dictionaries, preferring values from keep_profile.

        For lists, combines and deduplicates values.
        For nested dicts, merges recursively.

        Args:
            keep_profile: Profile to keep (takes precedence)
            discard_profile: Profile to merge in

        Returns:
            Merged profile dictionary
        """
        merged = keep_profile.copy()

        for section_id, section_data in discard_profile.items():
            if section_id not in merged:
                merged[section_id] = section_data
            elif isinstance(section_data, dict):
                # Merge section fields
                for field_id, field_value in section_data.items():
                    if field_id not in merged[section_id]:
                        merged[section_id][field_id] = field_value
                    elif isinstance(field_value, list) and isinstance(merged[section_id][field_id], list):
                        # Combine lists and deduplicate
                        merged[section_id][field_id] = self._merge_lists(
                            merged[section_id][field_id], field_value
                        )

        return merged

    def _merge_lists(self, list1: List, list2: List) -> List:
        """
        Merge two lists, removing duplicates while preserving order.

        Args:
            list1: First list (takes precedence)
            list2: Second list

        Returns:
            Merged list with duplicates removed
        """
        # Convert to JSON strings for comparison (handles dicts and complex objects)
        seen = set()
        merged = []

        for item in list1:
            item_str = json.dumps(item, sort_keys=True) if isinstance(item, (dict, list)) else str(item)
            if item_str not in seen:
                seen.add(item_str)
                merged.append(item)

        for item in list2:
            item_str = json.dumps(item, sort_keys=True) if isinstance(item, (dict, list)) else str(item)
            if item_str not in seen:
                seen.add(item_str)
                merged.append(item)

        return merged

    async def _get_project_id_from_entity(self, entity_id: str) -> Optional[str]:
        """
        Get project_id from an entity.

        Args:
            entity_id: Entity ID

        Returns:
            Project ID or None if not found
        """
        try:
            async with self.neo4j.session() as session:
                result = await session.run(
                    """
                    MATCH (p:Person {id: $entity_id})
                    RETURN p.project_id as project_id
                    """,
                    entity_id=entity_id
                )
                record = await result.single()
                return record["project_id"] if record else None
        except Exception:
            return None

    async def _get_project_id_from_data(self, data_id: str) -> Optional[str]:
        """
        Get project_id from a data item by finding its parent entity.

        Args:
            data_id: Data item ID

        Returns:
            Project ID or None if not found
        """
        try:
            async with self.neo4j.session() as session:
                result = await session.run(
                    """
                    MATCH (d:DataItem {id: $data_id})<-[:HAS_DATA]-(p:Person)
                    RETURN p.project_id as project_id
                    LIMIT 1
                    """,
                    data_id=data_id
                )
                record = await result.single()
                return record["project_id"] if record else None
        except Exception:
            return None

    async def _create_audit_trail(
        self,
        action_id: str,
        action_type: str,
        created_by: str,
        reason: str,
        details: Dict,
        confidence: float,
    ) -> None:
        """
        Create an audit trail entry for a linking action.

        Stores the action in Neo4j as a LinkingAction node for accountability
        and potential undo functionality.

        Args:
            action_id: Unique action ID
            action_type: Type of action (link_data_items, merge_entities, etc.)
            created_by: User or system that performed the action
            reason: Human-readable reason
            details: Action-specific details
            confidence: Confidence score for the action
        """
        async with self.neo4j.session() as session:
            await session.run(
                """
                CREATE (a:LinkingAction {
                    action_id: $action_id,
                    action_type: $action_type,
                    created_at: $created_at,
                    created_by: $created_by,
                    reason: $reason,
                    details: $details,
                    confidence: $confidence
                })
                """,
                action_id=action_id,
                action_type=action_type,
                created_at=datetime.now().isoformat(),
                created_by=created_by,
                reason=reason,
                details=json.dumps(details),
                confidence=confidence,
            )

    async def get_linking_history(
        self,
        entity_id: Optional[str] = None,
        action_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict]:
        """
        Get linking action history for audit purposes.

        Args:
            entity_id: Optional entity ID to filter by
            action_type: Optional action type to filter by
            limit: Maximum number of results

        Returns:
            List of linking action dictionaries
        """
        async with self.neo4j.session() as session:
            where_clauses = []
            params = {"limit": limit}

            if entity_id:
                where_clauses.append("(a.details CONTAINS $entity_id)")
                params["entity_id"] = entity_id

            if action_type:
                where_clauses.append("a.action_type = $action_type")
                params["action_type"] = action_type

            where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

            query = f"""
            MATCH (a:LinkingAction)
            {where_clause}
            RETURN a
            ORDER BY a.created_at DESC
            LIMIT $limit
            """

            result = await session.run(query, params)
            records = await result.data()

            actions = []
            for record in records:
                action = dict(record["a"])
                # Parse details JSON
                if "details" in action and isinstance(action["details"], str):
                    action["details"] = json.loads(action["details"])
                actions.append(action)

            return actions
