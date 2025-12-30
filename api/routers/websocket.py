"""
WebSocket Router for Basset Hound

This module provides WebSocket endpoints for real-time notifications.
Designed for local-first, single-user operation - no authentication required.

Endpoints:
- ws /api/v1/ws - Main WebSocket endpoint for general connections
- ws /api/v1/ws/projects/{project_id} - Project-scoped WebSocket endpoint
- ws /api/v1/ws/graph/{project_id} - Graph-focused WebSocket endpoint

Phase 4: Real-time Communication Layer
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Path

from api.services.websocket_service import (
    ConnectionManager,
    NotificationType,
    SubscriptionType,
    WebSocketMessage,
    get_connection_manager,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["WebSocket"])

# Track pending pings for latency measurement
_pending_pings: Dict[str, float] = {}


async def handle_client_message(
    websocket: WebSocket,
    connection_id: str,
    message_text: str,
    manager: ConnectionManager
) -> None:
    """
    Handle incoming messages from WebSocket clients.

    Supported message types:
    - ping: Keepalive ping (with optional latency tracking)
    - pong: Response to server ping (for latency measurement)
    - subscribe: Subscribe to a project
    - unsubscribe: Unsubscribe from a project
    - subscribe_type: Subscribe to a specific event type (graph, import_progress, all)
    - unsubscribe_type: Unsubscribe from a specific event type
    - get_quality: Get connection quality metrics

    Args:
        websocket: The WebSocket connection
        connection_id: The connection ID
        message_text: The raw message text
        manager: The connection manager
    """
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
        return

    message_type = message_data.get("type", "").lower()

    if message_type == "ping":
        # Track ping timestamp for latency measurement if client sends timestamp
        client_timestamp = message_data.get("timestamp")
        await manager.handle_ping(connection_id)
        if client_timestamp:
            # Calculate round-trip latency if client provided timestamp
            try:
                latency = (time.time() * 1000) - float(client_timestamp)
                await manager.record_latency(connection_id, latency)
            except (ValueError, TypeError):
                pass

    elif message_type == "pong":
        # Handle pong response for server-initiated pings
        ping_key = f"{connection_id}"
        if ping_key in _pending_pings:
            latency = (time.time() * 1000) - _pending_pings[ping_key]
            await manager.record_latency(connection_id, latency)
            del _pending_pings[ping_key]

    elif message_type == "subscribe":
        project_id = message_data.get("project_id")
        if project_id:
            await manager.subscribe_to_project(connection_id, project_id)
        else:
            await manager.send_personal(
                connection_id,
                WebSocketMessage(
                    type=NotificationType.ERROR,
                    data={"error": "project_id required for subscribe"}
                )
            )

    elif message_type == "unsubscribe":
        project_id = message_data.get("project_id")
        if project_id:
            await manager.unsubscribe_from_project(connection_id, project_id)
        else:
            await manager.send_personal(
                connection_id,
                WebSocketMessage(
                    type=NotificationType.ERROR,
                    data={"error": "project_id required for unsubscribe"}
                )
            )

    elif message_type == "subscribe_type":
        # Subscribe to a specific event type
        subscription_type = message_data.get("subscription_type")
        valid_types = [SubscriptionType.GRAPH, SubscriptionType.IMPORT_PROGRESS, SubscriptionType.ALL]
        if subscription_type in valid_types:
            await manager.subscribe_to_type(connection_id, subscription_type)
        else:
            await manager.send_personal(
                connection_id,
                WebSocketMessage(
                    type=NotificationType.ERROR,
                    data={
                        "error": f"Invalid subscription_type. Valid types: {valid_types}",
                        "valid_types": valid_types
                    }
                )
            )

    elif message_type == "unsubscribe_type":
        # Unsubscribe from a specific event type
        subscription_type = message_data.get("subscription_type")
        if subscription_type:
            await manager.unsubscribe_from_type(connection_id, subscription_type)
        else:
            await manager.send_personal(
                connection_id,
                WebSocketMessage(
                    type=NotificationType.ERROR,
                    data={"error": "subscription_type required for unsubscribe_type"}
                )
            )

    elif message_type == "get_quality":
        # Return connection quality metrics
        quality = manager.get_connection_quality(connection_id)
        await manager.send_personal(
            connection_id,
            WebSocketMessage(
                type=NotificationType.PONG,
                data={"quality": quality}
            )
        )

    else:
        logger.debug(f"Unknown message type from {connection_id}: {message_type}")
        await manager.send_personal(
            connection_id,
            WebSocketMessage(
                type=NotificationType.ERROR,
                data={"error": f"Unknown message type: {message_type}"}
            )
        )


@router.websocket("")
async def websocket_endpoint(
    websocket: WebSocket,
    client_id: Optional[str] = Query(default=None, description="Optional client identifier"),
):
    """
    Main WebSocket endpoint for real-time notifications.

    Query Parameters:
        client_id: Optional custom client identifier

    Message Protocol:
        - Send {"type": "ping"} to receive a pong response
        - Send {"type": "subscribe", "project_id": "..."} to subscribe to project events
        - Send {"type": "unsubscribe", "project_id": "..."} to unsubscribe from project events

    Connection Response:
        On successful connection, receives:
        {"type": "connected", "data": {"connection_id": "..."}, ...}
    """
    manager = get_connection_manager()

    connection = await manager.connect(
        websocket,
        connection_id=client_id,
        metadata={"source": "general"}
    )
    connection_id = connection.connection_id

    try:
        while True:
            message_text = await websocket.receive_text()
            await handle_client_message(websocket, connection_id, message_text, manager)

    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected: {connection_id}")
    except Exception as e:
        logger.error(f"WebSocket error for {connection_id}: {e}")
    finally:
        await manager.disconnect(connection_id)


@router.websocket("/projects/{project_id}")
async def websocket_project_endpoint(
    websocket: WebSocket,
    project_id: str = Path(..., description="Project ID to subscribe to"),
    client_id: Optional[str] = Query(default=None, description="Optional client identifier"),
):
    """
    Project-scoped WebSocket endpoint.

    Automatically subscribes the connection to the specified project's events.

    Path Parameters:
        project_id: The project ID to automatically subscribe to

    Query Parameters:
        client_id: Optional custom client identifier

    Message Protocol:
        - Send {"type": "ping"} to receive a pong response
        - Send {"type": "subscribe", "project_id": "..."} to subscribe to additional projects
        - Send {"type": "unsubscribe", "project_id": "..."} to unsubscribe from projects

    Connection Response:
        On successful connection, receives:
        {"type": "connected", "data": {"connection_id": "..."}, ...}
        Followed by:
        {"type": "subscribed", "project_id": "...", "data": {"project_id": "..."}, ...}
    """
    manager = get_connection_manager()

    connection = await manager.connect(
        websocket,
        connection_id=client_id,
        metadata={"source": "project", "initial_project": project_id}
    )
    connection_id = connection.connection_id

    # Auto-subscribe to the project
    await manager.subscribe_to_project(connection_id, project_id)

    try:
        while True:
            message_text = await websocket.receive_text()
            await handle_client_message(websocket, connection_id, message_text, manager)

    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected from project {project_id}: {connection_id}")
    except Exception as e:
        logger.error(f"WebSocket error for {connection_id} (project {project_id}): {e}")
    finally:
        await manager.disconnect(connection_id)


@router.websocket("/graph/{project_id}")
async def websocket_graph_endpoint(
    websocket: WebSocket,
    project_id: str = Path(..., description="Project ID to subscribe to for graph updates"),
    client_id: Optional[str] = Query(default=None, description="Optional client identifier"),
):
    """
    Graph-focused WebSocket endpoint for real-time graph visualization updates.

    Automatically subscribes the connection to:
    - The specified project's events
    - Graph-specific event types (node/edge changes, layout updates, cluster detection)

    Path Parameters:
        project_id: The project ID to automatically subscribe to

    Query Parameters:
        client_id: Optional custom client identifier

    Message Protocol:
        - Send {"type": "ping"} to receive a pong response
        - Send {"type": "ping", "timestamp": <ms>} for latency measurement
        - Send {"type": "subscribe", "project_id": "..."} to subscribe to additional projects
        - Send {"type": "unsubscribe", "project_id": "..."} to unsubscribe from projects
        - Send {"type": "subscribe_type", "subscription_type": "import_progress"} to add event types
        - Send {"type": "unsubscribe_type", "subscription_type": "graph"} to remove event types
        - Send {"type": "get_quality"} to get connection quality metrics

    Connection Response:
        On successful connection, receives:
        {"type": "connected", "data": {"connection_id": "..."}, ...}
        Followed by:
        {"type": "subscribed", "project_id": "...", "data": {"project_id": "..."}, ...}
        {"type": "subscribed", "data": {"subscription_type": "graph"}, ...}

    Graph Events Received:
        - graph_node_added: When a new entity is created
        - graph_node_updated: When an entity is modified
        - graph_node_deleted: When an entity is deleted
        - graph_edge_added: When a relationship is created
        - graph_edge_updated: When a relationship is modified
        - graph_edge_deleted: When a relationship is deleted
        - graph_layout_changed: When layout preferences change
        - graph_cluster_detected: When a new cluster is found
    """
    manager = get_connection_manager()

    connection = await manager.connect(
        websocket,
        connection_id=client_id,
        metadata={
            "source": "graph",
            "initial_project": project_id,
            "subscription_focus": "graph"
        }
    )
    connection_id = connection.connection_id

    # Auto-subscribe to the project
    await manager.subscribe_to_project(connection_id, project_id)

    # Auto-subscribe to graph event type (removes "all" default for focused experience)
    connection.subscription_types.discard(SubscriptionType.ALL)
    await manager.subscribe_to_type(connection_id, SubscriptionType.GRAPH)

    try:
        while True:
            message_text = await websocket.receive_text()
            await handle_client_message(websocket, connection_id, message_text, manager)

    except WebSocketDisconnect:
        logger.info(f"Graph WebSocket client disconnected from project {project_id}: {connection_id}")
    except Exception as e:
        logger.error(f"Graph WebSocket error for {connection_id} (project {project_id}): {e}")
    finally:
        await manager.disconnect(connection_id)


@router.websocket("/import/{project_id}")
async def websocket_import_endpoint(
    websocket: WebSocket,
    project_id: str = Path(..., description="Project ID to subscribe to for import updates"),
    client_id: Optional[str] = Query(default=None, description="Optional client identifier"),
):
    """
    Import-focused WebSocket endpoint for real-time import progress updates.

    Automatically subscribes the connection to:
    - The specified project's events
    - Import progress event types

    Path Parameters:
        project_id: The project ID to automatically subscribe to

    Query Parameters:
        client_id: Optional custom client identifier

    Import Events Received:
        - import_progress: Progress updates during data import
        - import_complete: When import finishes
    """
    manager = get_connection_manager()

    connection = await manager.connect(
        websocket,
        connection_id=client_id,
        metadata={
            "source": "import",
            "initial_project": project_id,
            "subscription_focus": "import_progress"
        }
    )
    connection_id = connection.connection_id

    # Auto-subscribe to the project
    await manager.subscribe_to_project(connection_id, project_id)

    # Auto-subscribe to import progress event type
    connection.subscription_types.discard(SubscriptionType.ALL)
    await manager.subscribe_to_type(connection_id, SubscriptionType.IMPORT_PROGRESS)

    try:
        while True:
            message_text = await websocket.receive_text()
            await handle_client_message(websocket, connection_id, message_text, manager)

    except WebSocketDisconnect:
        logger.info(f"Import WebSocket client disconnected from project {project_id}: {connection_id}")
    except Exception as e:
        logger.error(f"Import WebSocket error for {connection_id} (project {project_id}): {e}")
    finally:
        await manager.disconnect(connection_id)


# HTTP endpoints for WebSocket management (useful for debugging)

@router.get("/stats", tags=["WebSocket"])
async def get_websocket_stats() -> Dict[str, Any]:
    """
    Get WebSocket connection statistics.

    Returns information about active connections, total messages sent,
    and project subscription counts.

    Returns:
        Dictionary with WebSocket statistics
    """
    manager = get_connection_manager()
    return manager.get_stats()


@router.get("/connections", tags=["WebSocket"])
async def list_connections() -> Dict[str, Any]:
    """
    List all active WebSocket connections.

    Returns a list of connection IDs and their metadata.
    For debugging purposes.

    Returns:
        Dictionary with list of connections
    """
    manager = get_connection_manager()
    connections = []

    for connection_id in manager.get_all_connection_ids():
        connection = manager.get_connection(connection_id)
        if connection:
            connections.append({
                "connection_id": connection_id,
                "connected_at": connection.connected_at,
                "last_activity": connection.last_activity,
                "project_subscriptions": list(connection.project_subscriptions),
                "subscription_types": list(connection.subscription_types),
                "metadata": connection.metadata,
                "quality": connection.get_quality_info(),
            })

    return {
        "count": len(connections),
        "connections": connections,
    }


@router.get("/projects/{project_id}/subscribers", tags=["WebSocket"])
async def list_project_subscribers(
    project_id: str = Path(..., description="Project ID")
) -> Dict[str, Any]:
    """
    List all connections subscribed to a specific project.

    Args:
        project_id: The project ID to check

    Returns:
        Dictionary with list of subscriber connection IDs
    """
    manager = get_connection_manager()
    subscriber_ids = manager.get_project_subscriber_ids(project_id)

    return {
        "project_id": project_id,
        "subscriber_count": len(subscriber_ids),
        "subscribers": subscriber_ids,
    }


@router.get("/connections/{connection_id}/quality", tags=["WebSocket"])
async def get_connection_quality(
    connection_id: str = Path(..., description="Connection ID")
) -> Dict[str, Any]:
    """
    Get connection quality metrics for a specific connection.

    Args:
        connection_id: The connection ID to check

    Returns:
        Dictionary with connection quality metrics including:
        - latency_ms: Current latency in milliseconds
        - average_latency_ms: Average latency from recent measurements
        - messages_sent: Number of messages sent
        - messages_received: Number of messages received
        - errors_count: Number of errors encountered
    """
    manager = get_connection_manager()
    quality = manager.get_connection_quality(connection_id)

    if quality is None:
        return {
            "error": "Connection not found",
            "connection_id": connection_id,
        }

    return {
        "connection_id": connection_id,
        "quality": quality,
    }


@router.get("/subscription-types", tags=["WebSocket"])
async def get_subscription_types() -> Dict[str, Any]:
    """
    Get available subscription types.

    Returns:
        Dictionary with list of available subscription types
    """
    return {
        "subscription_types": [
            {
                "type": SubscriptionType.GRAPH,
                "description": "Graph visualization events (node/edge changes, layout, clusters)",
                "events": [
                    "graph_node_added",
                    "graph_node_updated",
                    "graph_node_deleted",
                    "graph_edge_added",
                    "graph_edge_updated",
                    "graph_edge_deleted",
                    "graph_layout_changed",
                    "graph_cluster_detected",
                ]
            },
            {
                "type": SubscriptionType.IMPORT_PROGRESS,
                "description": "Data import progress events",
                "events": [
                    "import_progress",
                    "import_complete",
                ]
            },
            {
                "type": SubscriptionType.ALL,
                "description": "All event types (default)",
                "events": ["all"]
            },
        ]
    }
