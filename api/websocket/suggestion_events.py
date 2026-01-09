"""
WebSocket Suggestion Events for Phase 45: WebSocket Real-Time Notifications.

Provides WebSocket endpoints and event handlers for real-time suggestion
and linking action notifications.

WebSocket Endpoints:
- ws://localhost:8000/ws/suggestions/{project_id} - Suggestion updates for a project

Event Types:
- suggestion_generated: New suggestion available
- suggestion_dismissed: Suggestion dismissed by user
- entity_merged: Two entities merged
- data_linked: DataItems linked
- orphan_linked: Orphan linked to entity

Event Format:
{
  "event_type": "suggestion_generated",
  "timestamp": "2026-01-09T12:00:00Z",
  "data": {
    "entity_id": "ent_abc123",
    "suggestion_count": 5,
    "high_confidence_count": 2,
    "affected_entities": ["ent_abc123", "ent_def456"]
  },
  "_links": {
    "suggestions": {"href": "/api/v1/suggestions/entity/ent_abc123"}
  }
}

Phase 45: WebSocket Real-Time Notifications
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from enum import Enum

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Path

from api.services.websocket_service import (
    ConnectionManager,
    NotificationType,
    WebSocketMessage,
    get_connection_manager,
)

logger = logging.getLogger("basset_hound.suggestion_events")

router = APIRouter(prefix="/ws/suggestions", tags=["WebSocket Suggestions"])


class SuggestionEventType(str, Enum):
    """Types of suggestion-related events."""

    SUGGESTION_GENERATED = "suggestion_generated"
    SUGGESTION_DISMISSED = "suggestion_dismissed"
    ENTITY_MERGED = "entity_merged"
    DATA_LINKED = "data_linked"
    ORPHAN_LINKED = "orphan_linked"


class SuggestionSubscriptionType:
    """Subscription types for suggestion events."""

    SUGGESTIONS = "suggestions"
    LINKING_ACTIONS = "linking_actions"
    ALL = "all"


@router.websocket("/{project_id}")
async def websocket_suggestions_endpoint(
    websocket: WebSocket,
    project_id: str = Path(..., description="Project ID to subscribe to"),
    token: Optional[str] = Query(default=None, description="Optional authentication token"),
    client_id: Optional[str] = Query(default=None, description="Optional client identifier"),
):
    """
    WebSocket endpoint for real-time suggestion updates.

    Endpoint: ws://localhost:8000/ws/suggestions/{project_id}?token=abc

    Authentication:
    - token: Optional query parameter for authentication
    - For local-first operation, authentication is optional

    Path Parameters:
        project_id: The project ID to subscribe to

    Query Parameters:
        token: Optional authentication token
        client_id: Optional custom client identifier

    Message Protocol:
        Client can send:
        - {"type": "ping"} - Keepalive ping
        - {"type": "subscribe_entity", "entity_id": "ent_123"} - Subscribe to entity suggestions
        - {"type": "unsubscribe_entity", "entity_id": "ent_123"} - Unsubscribe from entity

    Events Received:
        - suggestion_generated: New suggestions available for an entity
        - suggestion_dismissed: User dismissed a suggestion
        - entity_merged: Two entities were merged
        - data_linked: Two data items were linked
        - orphan_linked: Orphan data was linked to an entity

    Connection Response:
        On successful connection:
        {
          "type": "connected",
          "data": {
            "connection_id": "...",
            "project_id": "...",
            "subscription_type": "suggestions"
          },
          "timestamp": "2026-01-09T12:00:00Z"
        }
    """
    manager = get_connection_manager()

    # TODO: Implement token-based authentication when needed
    # For now, local-first operation doesn't require authentication
    if token:
        logger.debug(f"Authentication token provided (not validated in local-first mode): {token[:10]}...")

    connection = await manager.connect(
        websocket,
        connection_id=client_id,
        metadata={
            "source": "suggestions",
            "project_id": project_id,
            "subscription_focus": "suggestions",
            "authenticated": bool(token),
        }
    )
    connection_id = connection.connection_id

    # Auto-subscribe to the project
    await manager.subscribe_to_project(connection_id, project_id)

    # Auto-subscribe to suggestions event type
    connection.subscription_types.discard("all")
    await manager.subscribe_to_type(connection_id, SuggestionSubscriptionType.SUGGESTIONS)

    # Track entity-specific subscriptions
    entity_subscriptions: set = set()

    try:
        while True:
            message_text = await websocket.receive_text()

            try:
                message_data = json.loads(message_text)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON from connection {connection_id}: {message_text[:100]}")
                await manager.send_personal(
                    connection_id,
                    WebSocketMessage(
                        type=NotificationType.ERROR,
                        data={"error": "Invalid JSON message"}
                    )
                )
                continue

            message_type = message_data.get("type", "").lower()

            if message_type == "ping":
                # Handle ping
                await manager.handle_ping(connection_id)

            elif message_type == "subscribe_entity":
                # Subscribe to specific entity's suggestions
                entity_id = message_data.get("entity_id")
                if entity_id:
                    entity_subscriptions.add(entity_id)
                    await manager.send_personal(
                        connection_id,
                        WebSocketMessage(
                            type=NotificationType.SUBSCRIBED,
                            data={
                                "entity_id": entity_id,
                                "message": f"Subscribed to suggestions for entity {entity_id}"
                            }
                        )
                    )
                    logger.debug(f"Connection {connection_id} subscribed to entity {entity_id}")
                else:
                    await manager.send_personal(
                        connection_id,
                        WebSocketMessage(
                            type=NotificationType.ERROR,
                            data={"error": "entity_id required for subscribe_entity"}
                        )
                    )

            elif message_type == "unsubscribe_entity":
                # Unsubscribe from specific entity's suggestions
                entity_id = message_data.get("entity_id")
                if entity_id and entity_id in entity_subscriptions:
                    entity_subscriptions.discard(entity_id)
                    await manager.send_personal(
                        connection_id,
                        WebSocketMessage(
                            type=NotificationType.UNSUBSCRIBED,
                            data={
                                "entity_id": entity_id,
                                "message": f"Unsubscribed from suggestions for entity {entity_id}"
                            }
                        )
                    )
                    logger.debug(f"Connection {connection_id} unsubscribed from entity {entity_id}")

            else:
                logger.debug(f"Unknown message type from {connection_id}: {message_type}")

    except WebSocketDisconnect:
        logger.info(f"Suggestions WebSocket client disconnected from project {project_id}: {connection_id}")
    except Exception as e:
        logger.error(f"Suggestions WebSocket error for {connection_id} (project {project_id}): {e}")
    finally:
        await manager.disconnect(connection_id)


# Connection management functions

async def get_active_suggestion_connections(project_id: str) -> int:
    """
    Get count of active suggestion connections for a project.

    Args:
        project_id: The project ID

    Returns:
        Number of active connections
    """
    manager = get_connection_manager()
    subscriber_ids = manager.get_project_subscriber_ids(project_id)

    # Filter for suggestion-focused connections
    count = 0
    for connection_id in subscriber_ids:
        connection = manager.get_connection(connection_id)
        if connection and connection.metadata.get("subscription_focus") == "suggestions":
            count += 1

    return count


async def broadcast_suggestion_event(
    project_id: str,
    event_type: SuggestionEventType,
    data: Dict[str, Any],
    links: Optional[Dict[str, Dict[str, str]]] = None
) -> int:
    """
    Broadcast a suggestion event to all subscribed connections.

    Args:
        project_id: The project ID
        event_type: Type of suggestion event
        data: Event data payload
        links: Optional HATEOAS links

    Returns:
        Number of connections the event was sent to
    """
    manager = get_connection_manager()

    # Prepare event payload
    event_data = data.copy()
    if links:
        event_data["_links"] = links

    message = WebSocketMessage(
        type=event_type.value,
        project_id=project_id,
        entity_id=data.get("entity_id"),
        data=event_data,
    )

    # Broadcast to all project subscribers with suggestions subscription
    sent_count = 0
    subscriber_ids = manager.get_project_subscriber_ids(project_id)

    for connection_id in subscriber_ids:
        connection = manager.get_connection(connection_id)
        if not connection:
            continue

        # Check if connection is subscribed to suggestions
        if connection.is_subscribed_to_type(SuggestionSubscriptionType.SUGGESTIONS):
            success = await manager.send_personal(connection_id, message)
            if success:
                sent_count += 1

    logger.debug(f"Broadcast {event_type.value} event to {sent_count} connections for project {project_id}")
    return sent_count


# ============================================================================
# Event Broadcasting Functions
# ============================================================================

async def broadcast_suggestion_generated(
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

    Args:
        project_id: The project ID
        entity_id: Entity ID that has new suggestions
        suggestion_count: Total number of suggestions
        high_confidence_count: Number of high confidence suggestions
        medium_confidence_count: Number of medium confidence suggestions
        low_confidence_count: Number of low confidence suggestions
        affected_entities: Optional list of other affected entity IDs

    Returns:
        Number of connections notified
    """
    return await broadcast_suggestion_event(
        project_id=project_id,
        event_type=SuggestionEventType.SUGGESTION_GENERATED,
        data={
            "entity_id": entity_id,
            "suggestion_count": suggestion_count,
            "high_confidence_count": high_confidence_count,
            "medium_confidence_count": medium_confidence_count,
            "low_confidence_count": low_confidence_count,
            "affected_entities": affected_entities or [entity_id],
        },
        links={
            "suggestions": {"href": f"/api/v1/suggestions/entity/{entity_id}"},
            "entity": {"href": f"/api/v1/projects/{project_id}/entities/{entity_id}"},
        }
    )


async def broadcast_suggestion_dismissed(
    project_id: str,
    entity_id: str,
    suggestion_id: str,
    reason: Optional[str] = None
) -> int:
    """
    Broadcast that a suggestion was dismissed by the user.

    Args:
        project_id: The project ID
        entity_id: Entity ID
        suggestion_id: ID of the dismissed suggestion
        reason: Optional reason for dismissal

    Returns:
        Number of connections notified
    """
    return await broadcast_suggestion_event(
        project_id=project_id,
        event_type=SuggestionEventType.SUGGESTION_DISMISSED,
        data={
            "entity_id": entity_id,
            "suggestion_id": suggestion_id,
            "reason": reason,
            "dismissed_at": datetime.now(timezone.utc).isoformat(),
        },
        links={
            "entity": {"href": f"/api/v1/projects/{project_id}/entities/{entity_id}"},
        }
    )


async def broadcast_entity_merged(
    project_id: str,
    entity_id_1: str,
    entity_id_2: str,
    kept_entity_id: str,
    reason: str,
    merged_data_count: int = 0
) -> int:
    """
    Broadcast that two entities were merged.

    Args:
        project_id: The project ID
        entity_id_1: First entity ID
        entity_id_2: Second entity ID
        kept_entity_id: ID of the entity that was kept
        reason: Reason for the merge
        merged_data_count: Number of data items merged

    Returns:
        Number of connections notified
    """
    discarded_entity_id = entity_id_1 if kept_entity_id == entity_id_2 else entity_id_2

    return await broadcast_suggestion_event(
        project_id=project_id,
        event_type=SuggestionEventType.ENTITY_MERGED,
        data={
            "entity_id_1": entity_id_1,
            "entity_id_2": entity_id_2,
            "kept_entity_id": kept_entity_id,
            "discarded_entity_id": discarded_entity_id,
            "reason": reason,
            "merged_data_count": merged_data_count,
            "merged_at": datetime.now(timezone.utc).isoformat(),
        },
        links={
            "kept_entity": {"href": f"/api/v1/projects/{project_id}/entities/{kept_entity_id}"},
        }
    )


async def broadcast_data_linked(
    project_id: str,
    data_id_1: str,
    data_id_2: str,
    reason: str,
    confidence: float = 0.8,
    affected_entities: Optional[List[str]] = None
) -> int:
    """
    Broadcast that two data items were linked.

    Args:
        project_id: The project ID
        data_id_1: First data item ID
        data_id_2: Second data item ID
        reason: Reason for the link
        confidence: Confidence score (0.0-1.0)
        affected_entities: Optional list of affected entity IDs

    Returns:
        Number of connections notified
    """
    return await broadcast_suggestion_event(
        project_id=project_id,
        event_type=SuggestionEventType.DATA_LINKED,
        data={
            "data_id_1": data_id_1,
            "data_id_2": data_id_2,
            "reason": reason,
            "confidence": confidence,
            "affected_entities": affected_entities or [],
            "linked_at": datetime.now(timezone.utc).isoformat(),
        },
        links={
            "data_1": {"href": f"/api/v1/data/{data_id_1}"},
            "data_2": {"href": f"/api/v1/data/{data_id_2}"},
        }
    )


async def broadcast_orphan_linked(
    project_id: str,
    orphan_id: str,
    entity_id: str,
    reason: str,
    confidence: float = 0.8
) -> int:
    """
    Broadcast that an orphan was linked to an entity.

    Args:
        project_id: The project ID
        orphan_id: Orphan data ID
        entity_id: Entity ID that orphan was linked to
        reason: Reason for the link
        confidence: Confidence score (0.0-1.0)

    Returns:
        Number of connections notified
    """
    return await broadcast_suggestion_event(
        project_id=project_id,
        event_type=SuggestionEventType.ORPHAN_LINKED,
        data={
            "orphan_id": orphan_id,
            "entity_id": entity_id,
            "reason": reason,
            "confidence": confidence,
            "linked_at": datetime.now(timezone.utc).isoformat(),
        },
        links={
            "orphan": {"href": f"/api/v1/orphans/{orphan_id}"},
            "entity": {"href": f"/api/v1/projects/{project_id}/entities/{entity_id}"},
        }
    )
