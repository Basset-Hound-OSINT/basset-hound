"""
WebSocket Router for Basset Hound

This module provides WebSocket endpoints for real-time notifications.

Endpoints:
- ws /api/v1/ws - Main WebSocket endpoint for general connections (authentication required)
- ws /api/v1/ws/public - Public WebSocket endpoint (no authentication required)
- ws /api/v1/ws/projects/{project_id} - Project-scoped WebSocket endpoint (authentication required)

Phase 4: Real-time Communication Layer
Phase 14: Enterprise Features - WebSocket Authentication
"""

import json
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Path, status

from api.services.websocket_service import (
    ConnectionManager,
    NotificationService,
    NotificationType,
    WebSocketMessage,
    get_connection_manager,
    get_notification_service,
)
from api.middleware.auth import (
    WebSocketAuthenticator,
    WebSocketAuthResult,
    authenticate_websocket,
    default_authenticator,
    optional_authenticator,
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


async def _connect_with_auth(
    websocket: WebSocket,
    manager: ConnectionManager,
    auth_result: WebSocketAuthResult,
    client_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
):
    """
    Helper to create an authenticated connection.

    Args:
        websocket: The WebSocket connection
        manager: The connection manager
        auth_result: The authentication result
        client_id: Optional custom client ID
        metadata: Optional additional metadata

    Returns:
        The WebSocket connection object
    """
    connection_metadata = metadata or {}
    connection_metadata.update(auth_result.to_connection_metadata())

    return await manager.connect(
        websocket,
        connection_id=client_id,
        metadata=connection_metadata,
        authenticated=auth_result.authenticated,
        user_id=auth_result.user.user_id if auth_result.user else None,
        username=auth_result.user.username if auth_result.user else None,
        auth_method=auth_result.auth_method.value,
        scopes=auth_result.user.scopes if auth_result.user else [],
    )


@router.websocket("")
async def websocket_endpoint(
    websocket: WebSocket,
    client_id: Optional[str] = Query(default=None, description="Optional client identifier"),
    token: Optional[str] = Query(default=None, description="JWT token for authentication"),
    api_key: Optional[str] = Query(default=None, description="API key for authentication"),
):
    """
    Main WebSocket endpoint for authenticated connections.

    This endpoint requires authentication via either JWT token or API key.
    Authentication can be provided via:
    - Query parameter: ?token=<jwt> or ?api_key=<key>
    - Headers: Authorization: Bearer <jwt> or X-API-Key: <key>

    Query Parameters:
        client_id: Optional custom client identifier
        token: Optional JWT token for authentication
        api_key: Optional API key for authentication

    Message Protocol:
        - Send {"type": "ping"} to receive a pong response
        - Send {"type": "subscribe", "project_id": "..."} to subscribe to project events
        - Send {"type": "unsubscribe", "project_id": "..."} to unsubscribe from project events

    Connection Response:
        On successful connection, receives:
        {"type": "connected", "data": {"connection_id": "...", "authenticated": true, ...}, ...}

    Authentication Failure:
        Connection is closed with code 1008 (Policy Violation) and error message
    """
    manager = get_connection_manager()

    # Authenticate the connection
    auth_result = await default_authenticator.authenticate(websocket)

    if not auth_result.authenticated:
        logger.warning(f"WebSocket authentication failed: {auth_result.error}")
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason=auth_result.error or "Authentication failed"
        )
        return

    # Connect with authentication info
    connection = await _connect_with_auth(
        websocket,
        manager,
        auth_result,
        client_id=client_id,
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


@router.websocket("/public")
async def websocket_public_endpoint(
    websocket: WebSocket,
    client_id: Optional[str] = Query(default=None, description="Optional client identifier"),
):
    """
    Public WebSocket endpoint (no authentication required).

    This endpoint accepts WebSocket connections without requiring authentication.
    Authentication is still attempted if credentials are provided, but not required.

    Query Parameters:
        client_id: Optional custom client identifier

    Message Protocol:
        - Send {"type": "ping"} to receive a pong response
        - Send {"type": "subscribe", "project_id": "..."} to subscribe to project events
        - Send {"type": "unsubscribe", "project_id": "..."} to unsubscribe from project events

    Connection Response:
        On successful connection, receives:
        {"type": "connected", "data": {"connection_id": "...", "authenticated": false, ...}, ...}
    """
    manager = get_connection_manager()

    # Attempt optional authentication
    auth_result = await optional_authenticator.authenticate(websocket)

    # Connect (authentication not required for public endpoint)
    connection = await _connect_with_auth(
        websocket,
        manager,
        auth_result,
        client_id=client_id,
        metadata={"source": "public"}
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
    client_id: Optional[str] = Query(default=None, description="Optional client identifier"),
    token: Optional[str] = Query(default=None, description="JWT token for authentication"),
    api_key: Optional[str] = Query(default=None, description="API key for authentication"),
):
    """
    Project-scoped WebSocket endpoint (authentication required).

    This endpoint requires authentication and automatically subscribes
    the connection to the specified project's events.

    Path Parameters:
        project_id: The project ID to automatically subscribe to

    Query Parameters:
        client_id: Optional custom client identifier
        token: Optional JWT token for authentication
        api_key: Optional API key for authentication

    Message Protocol:
        - Send {"type": "ping"} to receive a pong response
        - Send {"type": "subscribe", "project_id": "..."} to subscribe to additional projects
        - Send {"type": "unsubscribe", "project_id": "..."} to unsubscribe from projects

    Connection Response:
        On successful connection, receives:
        {"type": "connected", "data": {"connection_id": "...", "authenticated": true, ...}, ...}
        Followed by:
        {"type": "subscribed", "project_id": "...", "data": {"project_id": "..."}, ...}

    Authentication Failure:
        Connection is closed with code 1008 (Policy Violation) and error message
    """
    manager = get_connection_manager()

    # Authenticate the connection
    auth_result = await default_authenticator.authenticate(websocket)

    if not auth_result.authenticated:
        logger.warning(f"WebSocket authentication failed for project {project_id}: {auth_result.error}")
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason=auth_result.error or "Authentication failed"
        )
        return

    # Connect with authentication info
    connection = await _connect_with_auth(
        websocket,
        manager,
        auth_result,
        client_id=client_id,
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
    stats = manager.get_stats()

    # Add authentication statistics
    stats["authenticated_connections"] = len(manager.get_authenticated_connection_ids())

    return stats


@router.get("/connections", tags=["WebSocket"])
async def list_connections() -> Dict[str, Any]:
    """
    List all active WebSocket connections.

    Returns a list of connection IDs and their metadata,
    including authentication information.
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
                "authenticated": connection.authenticated,
                "user_id": connection.user_id,
                "username": connection.username,
                "auth_method": connection.auth_method,
            })

    return {
        "count": len(connections),
        "authenticated_count": sum(1 for c in connections if c["authenticated"]),
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
        Dictionary with list of subscriber connection IDs and their auth status
    """
    manager = get_connection_manager()
    subscriber_ids = manager.get_project_subscriber_ids(project_id)

    subscribers = []
    for conn_id in subscriber_ids:
        conn = manager.get_connection(conn_id)
        if conn:
            subscribers.append({
                "connection_id": conn_id,
                "authenticated": conn.authenticated,
                "user_id": conn.user_id,
                "username": conn.username,
            })

    return {
        "project_id": project_id,
        "subscriber_count": len(subscribers),
        "subscribers": subscribers,
    }


@router.get("/users/{user_id}/connections", tags=["WebSocket"])
async def list_user_connections(
    user_id: str = Path(..., description="User ID")
) -> Dict[str, Any]:
    """
    List all connections for a specific user.

    Args:
        user_id: The user ID to check

    Returns:
        Dictionary with list of connection IDs for the user
    """
    manager = get_connection_manager()
    connection_ids = manager.get_connections_by_user_id(user_id)

    connections = []
    for conn_id in connection_ids:
        conn = manager.get_connection(conn_id)
        if conn:
            connections.append({
                "connection_id": conn_id,
                "connected_at": conn.connected_at,
                "last_activity": conn.last_activity,
                "subscriptions": list(conn.project_subscriptions),
                "auth_method": conn.auth_method,
            })

    return {
        "user_id": user_id,
        "connection_count": len(connections),
        "connections": connections,
    }
