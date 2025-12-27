"""
WebSocket Router for Basset Hound

This module provides WebSocket endpoints for real-time notifications.

Endpoints:
- ws /api/v1/ws - Main WebSocket endpoint for general connections
- ws /api/v1/ws/projects/{project_id} - Project-scoped WebSocket endpoint

Phase 4: Real-time Communication Layer
"""

import json
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Path

from api.services.websocket_service import (
    ConnectionManager,
    NotificationService,
    NotificationType,
    WebSocketMessage,
    get_connection_manager,
    get_notification_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["WebSocket"])


async def handle_client_message(
    websocket: WebSocket,
    connection_id: str,
    message_text: str,
    manager: ConnectionManager
) -> None:
    """
    Handle incoming messages from WebSocket clients.

    Supported message types:
    - ping: Keepalive ping
    - subscribe: Subscribe to a project
    - unsubscribe: Unsubscribe from a project

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
        await manager.handle_ping(connection_id)

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
    client_id: Optional[str] = Query(default=None, description="Optional client identifier")
):
    """
    Main WebSocket endpoint for general connections.

    This endpoint accepts WebSocket connections and handles real-time
    notifications. Clients can subscribe to specific projects after
    connecting.

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

    # Connect with optional custom ID
    connection = await manager.connect(
        websocket,
        connection_id=client_id,
        metadata={"source": "general"}
    )
    connection_id = connection.connection_id

    try:
        while True:
            # Wait for messages from client
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
    client_id: Optional[str] = Query(default=None, description="Optional client identifier")
):
    """
    Project-scoped WebSocket endpoint.

    This endpoint accepts WebSocket connections and automatically subscribes
    them to the specified project's events.

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

    # Connect with optional custom ID
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
            # Wait for messages from client
            message_text = await websocket.receive_text()
            await handle_client_message(websocket, connection_id, message_text, manager)

    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected from project {project_id}: {connection_id}")
    except Exception as e:
        logger.error(f"WebSocket error for {connection_id} (project {project_id}): {e}")
    finally:
        await manager.disconnect(connection_id)


# HTTP endpoints for WebSocket management (useful for debugging/admin)

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
    For debugging and administrative purposes.

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
                "subscriptions": list(connection.project_subscriptions),
                "metadata": connection.metadata,
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
