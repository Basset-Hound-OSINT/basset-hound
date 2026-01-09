"""
Notification Service for Phase 45: WebSocket Real-Time Notifications.

Centralized service for broadcasting real-time notifications via WebSocket.
Provides convenience methods for common notification patterns and integrates
with suggestion and linking services.

Key Features:
- Suggestion event broadcasting
- Linking action notifications
- Entity merge notifications
- Integration with WebSocket connection manager
- Support for both project-level and entity-level notifications

Phase 45: WebSocket Real-Time Notifications
"""

import logging
from typing import Any, Dict, List, Optional

from api.websocket.suggestion_events import (
    broadcast_suggestion_generated,
    broadcast_suggestion_dismissed,
    broadcast_entity_merged,
    broadcast_data_linked,
    broadcast_orphan_linked,
)

logger = logging.getLogger("basset_hound.notification_service")


class NotificationService:
    """
    Centralized service for broadcasting real-time notifications.

    This service provides high-level methods for broadcasting various types
    of events through WebSocket connections. It integrates with the suggestion
    and linking services to provide real-time updates to connected clients.

    Usage:
        notification_service = NotificationService()

        # Broadcast suggestion generated
        await notification_service.broadcast_suggestion_generated(
            project_id="proj_123",
            entity_id="ent_abc",
            suggestion_count=5,
            high_confidence_count=2
        )

        # Broadcast entity merged
        await notification_service.broadcast_entity_merged(
            project_id="proj_123",
            entity_id_1="ent_abc",
            entity_id_2="ent_def",
            kept_entity_id="ent_abc"
        )
    """

    # ========================================================================
    # Suggestion Events
    # ========================================================================

    async def broadcast_suggestion_generated(
        self,
        project_id: str,
        entity_id: str,
        suggestion_count: int,
        high_confidence_count: int = 0,
        medium_confidence_count: int = 0,
        low_confidence_count: int = 0,
        affected_entities: Optional[List[str]] = None
    ) -> int:
        """
        Broadcast that new suggestions have been generated for an entity.

        This event is triggered when:
        - A new entity is created and suggestions are computed
        - Suggestions are manually refreshed for an entity
        - New data is added that creates new matching opportunities

        Args:
            project_id: The project ID
            entity_id: Entity ID that has new suggestions
            suggestion_count: Total number of suggestions
            high_confidence_count: Number of high confidence suggestions (score >= 0.9)
            medium_confidence_count: Number of medium confidence suggestions (score 0.7-0.89)
            low_confidence_count: Number of low confidence suggestions (score 0.5-0.69)
            affected_entities: Optional list of other affected entity IDs

        Returns:
            Number of WebSocket connections notified

        Example:
            await notification_service.broadcast_suggestion_generated(
                project_id="proj_123",
                entity_id="ent_abc123",
                suggestion_count=5,
                high_confidence_count=2,
                medium_confidence_count=2,
                low_confidence_count=1,
                affected_entities=["ent_abc123", "ent_def456"]
            )
        """
        try:
            count = await broadcast_suggestion_generated(
                project_id=project_id,
                entity_id=entity_id,
                suggestion_count=suggestion_count,
                high_confidence_count=high_confidence_count,
                medium_confidence_count=medium_confidence_count,
                low_confidence_count=low_confidence_count,
                affected_entities=affected_entities
            )
            logger.info(
                f"Broadcasted suggestion_generated event for entity {entity_id} "
                f"in project {project_id} to {count} connections"
            )
            return count
        except Exception as e:
            logger.error(f"Error broadcasting suggestion_generated event: {e}")
            return 0

    async def broadcast_suggestion_dismissed(
        self,
        project_id: str,
        entity_id: str,
        suggestion_id: str,
        reason: Optional[str] = None
    ) -> int:
        """
        Broadcast that a suggestion was dismissed by the user.

        This event is triggered when a user explicitly dismisses a suggestion
        so it won't appear in future suggestions.

        Args:
            project_id: The project ID
            entity_id: Entity ID
            suggestion_id: ID of the dismissed suggestion (data_id)
            reason: Optional reason for dismissal

        Returns:
            Number of WebSocket connections notified

        Example:
            await notification_service.broadcast_suggestion_dismissed(
                project_id="proj_123",
                entity_id="ent_abc123",
                suggestion_id="data_xyz789",
                reason="Not the same person"
            )
        """
        try:
            count = await broadcast_suggestion_dismissed(
                project_id=project_id,
                entity_id=entity_id,
                suggestion_id=suggestion_id,
                reason=reason
            )
            logger.info(
                f"Broadcasted suggestion_dismissed event for entity {entity_id} "
                f"in project {project_id} to {count} connections"
            )
            return count
        except Exception as e:
            logger.error(f"Error broadcasting suggestion_dismissed event: {e}")
            return 0

    # ========================================================================
    # Linking Action Events
    # ========================================================================

    async def broadcast_entity_merged(
        self,
        project_id: str,
        entity_id_1: str,
        entity_id_2: str,
        kept_entity_id: str,
        reason: str = "User initiated merge",
        merged_data_count: int = 0
    ) -> int:
        """
        Broadcast that two entities were merged.

        This event is triggered when two entities are merged into one,
        typically based on a high-confidence suggestion that they represent
        the same person.

        Args:
            project_id: The project ID
            entity_id_1: First entity ID involved in merge
            entity_id_2: Second entity ID involved in merge
            kept_entity_id: ID of the entity that was kept (must be one of the above)
            reason: Reason for the merge (default: "User initiated merge")
            merged_data_count: Number of data items that were merged

        Returns:
            Number of WebSocket connections notified

        Raises:
            ValueError: If kept_entity_id is not one of entity_id_1 or entity_id_2

        Example:
            await notification_service.broadcast_entity_merged(
                project_id="proj_123",
                entity_id_1="ent_abc123",
                entity_id_2="ent_def456",
                kept_entity_id="ent_abc123",
                reason="Same email and phone number",
                merged_data_count=15
            )
        """
        if kept_entity_id not in [entity_id_1, entity_id_2]:
            raise ValueError(
                f"kept_entity_id must be one of {entity_id_1} or {entity_id_2}, "
                f"got {kept_entity_id}"
            )

        try:
            count = await broadcast_entity_merged(
                project_id=project_id,
                entity_id_1=entity_id_1,
                entity_id_2=entity_id_2,
                kept_entity_id=kept_entity_id,
                reason=reason,
                merged_data_count=merged_data_count
            )
            logger.info(
                f"Broadcasted entity_merged event for entities {entity_id_1} and {entity_id_2} "
                f"in project {project_id} to {count} connections"
            )
            return count
        except Exception as e:
            logger.error(f"Error broadcasting entity_merged event: {e}")
            return 0

    async def broadcast_data_linked(
        self,
        project_id: str,
        data_id_1: str,
        data_id_2: str,
        reason: str = "User initiated link",
        confidence: float = 0.8,
        affected_entities: Optional[List[str]] = None
    ) -> int:
        """
        Broadcast that two data items were linked.

        This event is triggered when two data items are linked together,
        indicating they represent the same information (e.g., same email,
        same image uploaded twice).

        Args:
            project_id: The project ID
            data_id_1: First data item ID
            data_id_2: Second data item ID
            reason: Reason for the link (default: "User initiated link")
            confidence: Confidence score for the link (0.0-1.0, default: 0.8)
            affected_entities: Optional list of entity IDs affected by this link

        Returns:
            Number of WebSocket connections notified

        Example:
            await notification_service.broadcast_data_linked(
                project_id="proj_123",
                data_id_1="data_abc123",
                data_id_2="data_def456",
                reason="Same email address",
                confidence=0.95,
                affected_entities=["ent_abc", "ent_def"]
            )
        """
        try:
            count = await broadcast_data_linked(
                project_id=project_id,
                data_id_1=data_id_1,
                data_id_2=data_id_2,
                reason=reason,
                confidence=confidence,
                affected_entities=affected_entities
            )
            logger.info(
                f"Broadcasted data_linked event for data items {data_id_1} and {data_id_2} "
                f"in project {project_id} to {count} connections"
            )
            return count
        except Exception as e:
            logger.error(f"Error broadcasting data_linked event: {e}")
            return 0

    async def broadcast_orphan_linked(
        self,
        project_id: str,
        orphan_id: str,
        entity_id: str,
        reason: str = "User initiated link",
        confidence: float = 0.8
    ) -> int:
        """
        Broadcast that an orphan was linked to an entity.

        This event is triggered when orphan data (data without a parent entity)
        is linked to an existing entity based on a suggestion.

        Args:
            project_id: The project ID
            orphan_id: Orphan data ID
            entity_id: Entity ID that the orphan was linked to
            reason: Reason for the link (default: "User initiated link")
            confidence: Confidence score for the link (0.0-1.0, default: 0.8)

        Returns:
            Number of WebSocket connections notified

        Example:
            await notification_service.broadcast_orphan_linked(
                project_id="proj_123",
                orphan_id="orphan_xyz789",
                entity_id="ent_abc123",
                reason="Matching email address",
                confidence=0.92
            )
        """
        try:
            count = await broadcast_orphan_linked(
                project_id=project_id,
                orphan_id=orphan_id,
                entity_id=entity_id,
                reason=reason,
                confidence=confidence
            )
            logger.info(
                f"Broadcasted orphan_linked event for orphan {orphan_id} to entity {entity_id} "
                f"in project {project_id} to {count} connections"
            )
            return count
        except Exception as e:
            logger.error(f"Error broadcasting orphan_linked event: {e}")
            return 0

    # ========================================================================
    # Batch Operations
    # ========================================================================

    async def broadcast_batch_link_complete(
        self,
        project_id: str,
        operation_type: str,
        items_processed: int,
        successful_links: int,
        failed_links: int,
        affected_entities: Optional[List[str]] = None
    ) -> int:
        """
        Broadcast that a batch linking operation has completed.

        This is useful for bulk operations where multiple links are created
        at once and you want to notify clients of the overall result.

        Args:
            project_id: The project ID
            operation_type: Type of batch operation (e.g., "bulk_data_link", "bulk_orphan_link")
            items_processed: Total number of items processed
            successful_links: Number of successful links created
            failed_links: Number of failed link attempts
            affected_entities: Optional list of affected entity IDs

        Returns:
            Number of WebSocket connections notified

        Example:
            await notification_service.broadcast_batch_link_complete(
                project_id="proj_123",
                operation_type="bulk_orphan_link",
                items_processed=100,
                successful_links=95,
                failed_links=5,
                affected_entities=["ent_abc", "ent_def", "ent_ghi"]
            )
        """
        # For batch operations, we can reuse the data_linked event type
        # with a special batch indicator
        try:
            from api.websocket.suggestion_events import broadcast_suggestion_event, SuggestionEventType

            count = await broadcast_suggestion_event(
                project_id=project_id,
                event_type=SuggestionEventType.DATA_LINKED,  # Reuse event type
                data={
                    "batch_operation": True,
                    "operation_type": operation_type,
                    "items_processed": items_processed,
                    "successful_links": successful_links,
                    "failed_links": failed_links,
                    "success_rate": successful_links / items_processed if items_processed > 0 else 0,
                    "affected_entities": affected_entities or [],
                },
                links={
                    "project": {"href": f"/api/v1/projects/{project_id}"},
                }
            )
            logger.info(
                f"Broadcasted batch_link_complete event for {operation_type} "
                f"in project {project_id} to {count} connections"
            )
            return count
        except Exception as e:
            logger.error(f"Error broadcasting batch_link_complete event: {e}")
            return 0


# Module-level singleton
_notification_service_instance: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """
    Get or create the singleton NotificationService instance.

    Returns:
        NotificationService instance
    """
    global _notification_service_instance

    if _notification_service_instance is None:
        _notification_service_instance = NotificationService()

    return _notification_service_instance
