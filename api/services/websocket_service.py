"""
WebSocket Service for Basset Hound

This module provides real-time notification capabilities through WebSocket connections.

Features:
- Connection management for multiple WebSocket clients
- Project-scoped subscriptions (subscribe to specific project events)
- Multiple notification types for different events
- Broadcasting to all connections or specific project subscribers
- Personal (direct) messaging to specific connections
- WebSocket authentication support (API key and JWT)

Phase 4: Real-time Communication Layer
Phase 14: Enterprise Features - WebSocket Authentication
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class NotificationType(str, Enum):
    """Types of notifications that can be sent through WebSocket."""

    # Entity events
    ENTITY_CREATED = "entity_created"
    ENTITY_UPDATED = "entity_updated"
    ENTITY_DELETED = "entity_deleted"

    # Relationship events
    RELATIONSHIP_ADDED = "relationship_added"
    RELATIONSHIP_REMOVED = "relationship_removed"

    # Async operation events
    SEARCH_COMPLETED = "search_completed"
    REPORT_READY = "report_ready"
    BULK_IMPORT_COMPLETE = "bulk_import_complete"

    # Connection events (internal)
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    SUBSCRIBED = "subscribed"
    UNSUBSCRIBED = "unsubscribed"

    # Error events
    ERROR = "error"

    # Keepalive
    PING = "ping"
    PONG = "pong"


@dataclass
class WebSocketMessage:
    """
    Represents a WebSocket message to be sent to clients.

    Attributes:
        type: The notification type
        project_id: The project this message relates to (if any)
        entity_id: The entity this message relates to (if any)
        data: Additional data payload
        timestamp: ISO format timestamp of when the message was created
        message_id: Unique identifier for this message
    """
    type: NotificationType
    project_id: Optional[str] = None
    entity_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    message_id: str = field(default_factory=lambda: str(uuid4()))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "type": self.type.value if isinstance(self.type, NotificationType) else self.type,
            "timestamp": self.timestamp,
            "message_id": self.message_id,
        }
        if self.project_id is not None:
            result["project_id"] = self.project_id
        if self.entity_id is not None:
            result["entity_id"] = self.entity_id
        if self.data is not None:
            result["data"] = self.data
        return result

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WebSocketMessage":
        """Create a WebSocketMessage from a dictionary."""
        notification_type = data.get("type")
        if isinstance(notification_type, str):
            try:
                notification_type = NotificationType(notification_type)
            except ValueError:
                # Keep as string if not a valid NotificationType
                pass

        return cls(
            type=notification_type,
            project_id=data.get("project_id"),
            entity_id=data.get("entity_id"),
            data=data.get("data"),
            timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat()),
            message_id=data.get("message_id", str(uuid4())),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "WebSocketMessage":
        """Deserialize from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)


@dataclass
class WebSocketConnection:
    """
    Represents an active WebSocket connection.

    Attributes:
        connection_id: Unique identifier for this connection
        websocket: The FastAPI WebSocket instance
        project_subscriptions: Set of project IDs this connection is subscribed to
        connected_at: Timestamp when the connection was established
        last_activity: Timestamp of last activity on this connection
        metadata: Optional metadata about the connection (user info, etc.)
        authenticated: Whether the connection is authenticated
        user_id: The authenticated user ID (if authenticated)
        username: The authenticated username (if authenticated)
        auth_method: The authentication method used
        scopes: The permission scopes for the authenticated user
    """
    connection_id: str
    websocket: WebSocket
    project_subscriptions: Set[str] = field(default_factory=set)
    connected_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_activity: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)
    authenticated: bool = False
    user_id: Optional[str] = None
    username: Optional[str] = None
    auth_method: Optional[str] = None
    scopes: List[str] = field(default_factory=list)

    def update_activity(self) -> None:
        """Update the last activity timestamp."""
        self.last_activity = datetime.now(timezone.utc).isoformat()

    def subscribe_to_project(self, project_id: str) -> bool:
        """
        Subscribe to a project's events.

        Returns:
            True if newly subscribed, False if already subscribed.
        """
        if project_id in self.project_subscriptions:
            return False
        self.project_subscriptions.add(project_id)
        return True

    def unsubscribe_from_project(self, project_id: str) -> bool:
        """
        Unsubscribe from a project's events.

        Returns:
            True if unsubscribed, False if wasn't subscribed.
        """
        if project_id not in self.project_subscriptions:
            return False
        self.project_subscriptions.discard(project_id)
        return True

    def is_subscribed_to(self, project_id: str) -> bool:
        """Check if subscribed to a project."""
        return project_id in self.project_subscriptions

    def has_scope(self, scope: str) -> bool:
        """
        Check if the connection has a specific permission scope.

        Args:
            scope: The scope to check for

        Returns:
            True if the connection has the scope or wildcard scope
        """
        return scope in self.scopes or "*" in self.scopes

    def has_any_scope(self, scopes: List[str]) -> bool:
        """
        Check if the connection has any of the specified scopes.

        Args:
            scopes: List of scopes to check

        Returns:
            True if any scope is present
        """
        return any(self.has_scope(s) for s in scopes)

    def is_authenticated(self) -> bool:
        """
        Check if the connection is authenticated.

        Returns:
            True if authenticated
        """
        return self.authenticated and self.user_id is not None

    def get_auth_info(self) -> Dict[str, Any]:
        """
        Get authentication information for this connection.

        Returns:
            Dictionary containing authentication details
        """
        return {
            "authenticated": self.authenticated,
            "user_id": self.user_id,
            "username": self.username,
            "auth_method": self.auth_method,
            "scopes": self.scopes,
        }


class ConnectionManager:
    """
    Manages WebSocket connections for real-time notifications.

    Features:
    - Track active connections by ID
    - Project-scoped subscriptions
    - Broadcast to all or specific connections
    - Connection cleanup and error handling
    """

    def __init__(self):
        """Initialize the connection manager."""
        # Map of connection_id -> WebSocketConnection
        self._connections: Dict[str, WebSocketConnection] = {}
        # Map of project_id -> set of connection_ids
        self._project_subscribers: Dict[str, Set[str]] = {}
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
        # Statistics
        self._total_connections: int = 0
        self._total_messages_sent: int = 0
        self._total_errors: int = 0

    @property
    def active_connections(self) -> int:
        """Number of currently active connections."""
        return len(self._connections)

    @property
    def total_connections(self) -> int:
        """Total connections since startup."""
        return self._total_connections

    @property
    def total_messages_sent(self) -> int:
        """Total messages sent since startup."""
        return self._total_messages_sent

    def get_connection(self, connection_id: str) -> Optional[WebSocketConnection]:
        """Get a connection by ID."""
        return self._connections.get(connection_id)

    def get_all_connection_ids(self) -> List[str]:
        """Get all active connection IDs."""
        return list(self._connections.keys())

    def get_project_subscriber_ids(self, project_id: str) -> List[str]:
        """Get all connection IDs subscribed to a project."""
        return list(self._project_subscribers.get(project_id, set()))

    def get_authenticated_connection_ids(self) -> List[str]:
        """Get all authenticated connection IDs."""
        return [
            conn_id for conn_id, conn in self._connections.items()
            if conn.authenticated
        ]

    def get_connections_by_user_id(self, user_id: str) -> List[str]:
        """
        Get all connection IDs for a specific user.

        Args:
            user_id: The user ID to search for

        Returns:
            List of connection IDs belonging to the user
        """
        return [
            conn_id for conn_id, conn in self._connections.items()
            if conn.user_id == user_id
        ]

    def get_connections_with_scope(self, scope: str) -> List[str]:
        """
        Get all connection IDs that have a specific permission scope.

        Args:
            scope: The scope to check for

        Returns:
            List of connection IDs with the specified scope
        """
        return [
            conn_id for conn_id, conn in self._connections.items()
            if conn.has_scope(scope)
        ]

    async def connect(
        self,
        websocket: WebSocket,
        connection_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        authenticated: bool = False,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        auth_method: Optional[str] = None,
        scopes: Optional[List[str]] = None,
    ) -> WebSocketConnection:
        """
        Accept a WebSocket connection and register it.

        Args:
            websocket: The FastAPI WebSocket instance
            connection_id: Optional custom connection ID (generated if not provided)
            metadata: Optional metadata to attach to the connection
            authenticated: Whether the connection is authenticated
            user_id: The authenticated user ID
            username: The authenticated username
            auth_method: The authentication method used (jwt, api_key, etc.)
            scopes: Permission scopes for the authenticated user

        Returns:
            The created WebSocketConnection
        """
        await websocket.accept()

        if connection_id is None:
            connection_id = str(uuid4())

        connection = WebSocketConnection(
            connection_id=connection_id,
            websocket=websocket,
            metadata=metadata or {},
            authenticated=authenticated,
            user_id=user_id,
            username=username,
            auth_method=auth_method,
            scopes=scopes or [],
        )

        async with self._lock:
            self._connections[connection_id] = connection
            self._total_connections += 1

        auth_info = f" (user: {username})" if authenticated else ""
        logger.info(f"WebSocket connection established: {connection_id}{auth_info}")

        # Send connection confirmation with auth info
        await self._send_to_connection(
            connection,
            WebSocketMessage(
                type=NotificationType.CONNECTED,
                data={
                    "connection_id": connection_id,
                    "authenticated": authenticated,
                    "user_id": user_id,
                    "username": username,
                }
            )
        )

        return connection

    async def disconnect(self, connection_id: str) -> bool:
        """
        Disconnect and cleanup a WebSocket connection.

        Args:
            connection_id: The connection ID to disconnect

        Returns:
            True if connection was found and removed, False otherwise
        """
        async with self._lock:
            connection = self._connections.pop(connection_id, None)

            if connection is None:
                return False

            # Remove from all project subscriptions
            for project_id in connection.project_subscriptions:
                if project_id in self._project_subscribers:
                    self._project_subscribers[project_id].discard(connection_id)
                    if not self._project_subscribers[project_id]:
                        del self._project_subscribers[project_id]

        logger.info(f"WebSocket connection closed: {connection_id}")
        return True

    async def subscribe_to_project(
        self,
        connection_id: str,
        project_id: str
    ) -> bool:
        """
        Subscribe a connection to a project's events.

        Args:
            connection_id: The connection ID
            project_id: The project ID to subscribe to

        Returns:
            True if subscribed successfully, False if connection not found
        """
        async with self._lock:
            connection = self._connections.get(connection_id)
            if connection is None:
                return False

            if connection.subscribe_to_project(project_id):
                if project_id not in self._project_subscribers:
                    self._project_subscribers[project_id] = set()
                self._project_subscribers[project_id].add(connection_id)

                logger.debug(f"Connection {connection_id} subscribed to project {project_id}")

        # Send subscription confirmation
        await self._send_to_connection(
            connection,
            WebSocketMessage(
                type=NotificationType.SUBSCRIBED,
                project_id=project_id,
                data={"project_id": project_id}
            )
        )

        return True

    async def unsubscribe_from_project(
        self,
        connection_id: str,
        project_id: str
    ) -> bool:
        """
        Unsubscribe a connection from a project's events.

        Args:
            connection_id: The connection ID
            project_id: The project ID to unsubscribe from

        Returns:
            True if unsubscribed successfully, False if connection not found
        """
        async with self._lock:
            connection = self._connections.get(connection_id)
            if connection is None:
                return False

            if connection.unsubscribe_from_project(project_id):
                if project_id in self._project_subscribers:
                    self._project_subscribers[project_id].discard(connection_id)
                    if not self._project_subscribers[project_id]:
                        del self._project_subscribers[project_id]

                logger.debug(f"Connection {connection_id} unsubscribed from project {project_id}")

        # Send unsubscription confirmation
        await self._send_to_connection(
            connection,
            WebSocketMessage(
                type=NotificationType.UNSUBSCRIBED,
                project_id=project_id,
                data={"project_id": project_id}
            )
        )

        return True

    async def _send_to_connection(
        self,
        connection: WebSocketConnection,
        message: WebSocketMessage
    ) -> bool:
        """
        Send a message to a specific connection.

        Args:
            connection: The connection to send to
            message: The message to send

        Returns:
            True if sent successfully, False on error
        """
        try:
            await connection.websocket.send_text(message.to_json())
            connection.update_activity()
            self._total_messages_sent += 1
            return True
        except Exception as e:
            logger.error(f"Error sending to connection {connection.connection_id}: {e}")
            self._total_errors += 1
            return False

    async def send_personal(
        self,
        connection_id: str,
        message: WebSocketMessage
    ) -> bool:
        """
        Send a message to a specific connection by ID.

        Args:
            connection_id: The target connection ID
            message: The message to send

        Returns:
            True if sent successfully, False if connection not found or error
        """
        connection = self._connections.get(connection_id)
        if connection is None:
            logger.warning(f"Connection not found for personal message: {connection_id}")
            return False

        return await self._send_to_connection(connection, message)

    async def broadcast(
        self,
        message: WebSocketMessage,
        exclude: Optional[Set[str]] = None
    ) -> int:
        """
        Broadcast a message to all connected clients.

        Args:
            message: The message to broadcast
            exclude: Optional set of connection IDs to exclude

        Returns:
            Number of connections the message was successfully sent to
        """
        exclude = exclude or set()
        sent_count = 0
        failed_connections: List[str] = []

        # Get snapshot of connections
        connections_snapshot = list(self._connections.items())

        for connection_id, connection in connections_snapshot:
            if connection_id in exclude:
                continue

            success = await self._send_to_connection(connection, message)
            if success:
                sent_count += 1
            else:
                failed_connections.append(connection_id)

        # Cleanup failed connections
        for connection_id in failed_connections:
            await self.disconnect(connection_id)

        logger.debug(f"Broadcast message to {sent_count} connections")
        return sent_count

    async def broadcast_to_project(
        self,
        project_id: str,
        message: WebSocketMessage,
        exclude: Optional[Set[str]] = None
    ) -> int:
        """
        Broadcast a message to all connections subscribed to a project.

        Args:
            project_id: The project ID
            message: The message to broadcast
            exclude: Optional set of connection IDs to exclude

        Returns:
            Number of connections the message was successfully sent to
        """
        exclude = exclude or set()
        sent_count = 0
        failed_connections: List[str] = []

        # Get snapshot of project subscribers
        subscriber_ids = self._project_subscribers.get(project_id, set()).copy()

        for connection_id in subscriber_ids:
            if connection_id in exclude:
                continue

            connection = self._connections.get(connection_id)
            if connection is None:
                failed_connections.append(connection_id)
                continue

            success = await self._send_to_connection(connection, message)
            if success:
                sent_count += 1
            else:
                failed_connections.append(connection_id)

        # Cleanup failed connections
        for connection_id in failed_connections:
            await self.disconnect(connection_id)

        logger.debug(f"Broadcast to project {project_id}: {sent_count} connections")
        return sent_count

    async def handle_ping(self, connection_id: str) -> bool:
        """
        Handle a ping message from a client.

        Args:
            connection_id: The connection ID that sent the ping

        Returns:
            True if pong was sent successfully
        """
        return await self.send_personal(
            connection_id,
            WebSocketMessage(type=NotificationType.PONG)
        )

    def get_stats(self) -> Dict[str, Any]:
        """
        Get connection manager statistics.

        Returns:
            Dictionary of statistics
        """
        return {
            "active_connections": self.active_connections,
            "total_connections": self._total_connections,
            "total_messages_sent": self._total_messages_sent,
            "total_errors": self._total_errors,
            "project_subscriptions": {
                project_id: len(subscribers)
                for project_id, subscribers in self._project_subscribers.items()
            },
        }

    async def close_all(self) -> int:
        """
        Close all active connections.

        Returns:
            Number of connections closed
        """
        connection_ids = list(self._connections.keys())

        for connection_id in connection_ids:
            connection = self._connections.get(connection_id)
            if connection:
                try:
                    await connection.websocket.close()
                except Exception:
                    pass

        async with self._lock:
            count = len(self._connections)
            self._connections.clear()
            self._project_subscribers.clear()

        logger.info(f"Closed {count} WebSocket connections")
        return count


class NotificationService:
    """
    High-level service for sending notifications through WebSocket.

    Provides convenient methods for common notification patterns.
    """

    def __init__(self, connection_manager: ConnectionManager):
        """
        Initialize the notification service.

        Args:
            connection_manager: The connection manager to use
        """
        self.manager = connection_manager

    async def notify_entity_created(
        self,
        project_id: str,
        entity_id: str,
        entity_data: Optional[Dict[str, Any]] = None
    ) -> int:
        """Notify subscribers that an entity was created."""
        message = WebSocketMessage(
            type=NotificationType.ENTITY_CREATED,
            project_id=project_id,
            entity_id=entity_id,
            data=entity_data,
        )
        return await self.manager.broadcast_to_project(project_id, message)

    async def notify_entity_updated(
        self,
        project_id: str,
        entity_id: str,
        changes: Optional[Dict[str, Any]] = None
    ) -> int:
        """Notify subscribers that an entity was updated."""
        message = WebSocketMessage(
            type=NotificationType.ENTITY_UPDATED,
            project_id=project_id,
            entity_id=entity_id,
            data=changes,
        )
        return await self.manager.broadcast_to_project(project_id, message)

    async def notify_entity_deleted(
        self,
        project_id: str,
        entity_id: str
    ) -> int:
        """Notify subscribers that an entity was deleted."""
        message = WebSocketMessage(
            type=NotificationType.ENTITY_DELETED,
            project_id=project_id,
            entity_id=entity_id,
        )
        return await self.manager.broadcast_to_project(project_id, message)

    async def notify_relationship_added(
        self,
        project_id: str,
        source_entity_id: str,
        target_entity_id: str,
        relationship_type: str,
        relationship_data: Optional[Dict[str, Any]] = None
    ) -> int:
        """Notify subscribers that a relationship was added."""
        message = WebSocketMessage(
            type=NotificationType.RELATIONSHIP_ADDED,
            project_id=project_id,
            data={
                "source_entity_id": source_entity_id,
                "target_entity_id": target_entity_id,
                "relationship_type": relationship_type,
                **(relationship_data or {}),
            },
        )
        return await self.manager.broadcast_to_project(project_id, message)

    async def notify_relationship_removed(
        self,
        project_id: str,
        source_entity_id: str,
        target_entity_id: str,
        relationship_type: str
    ) -> int:
        """Notify subscribers that a relationship was removed."""
        message = WebSocketMessage(
            type=NotificationType.RELATIONSHIP_REMOVED,
            project_id=project_id,
            data={
                "source_entity_id": source_entity_id,
                "target_entity_id": target_entity_id,
                "relationship_type": relationship_type,
            },
        )
        return await self.manager.broadcast_to_project(project_id, message)

    async def notify_search_completed(
        self,
        project_id: str,
        search_id: str,
        results_count: int,
        results_summary: Optional[Dict[str, Any]] = None
    ) -> int:
        """Notify subscribers that a search has completed."""
        message = WebSocketMessage(
            type=NotificationType.SEARCH_COMPLETED,
            project_id=project_id,
            data={
                "search_id": search_id,
                "results_count": results_count,
                "summary": results_summary,
            },
        )
        return await self.manager.broadcast_to_project(project_id, message)

    async def notify_report_ready(
        self,
        project_id: str,
        report_id: str,
        report_name: str,
        download_url: Optional[str] = None
    ) -> int:
        """Notify subscribers that a report is ready."""
        message = WebSocketMessage(
            type=NotificationType.REPORT_READY,
            project_id=project_id,
            data={
                "report_id": report_id,
                "report_name": report_name,
                "download_url": download_url,
            },
        )
        return await self.manager.broadcast_to_project(project_id, message)

    async def notify_bulk_import_complete(
        self,
        project_id: str,
        import_id: str,
        entities_created: int,
        entities_updated: int,
        errors: Optional[List[str]] = None
    ) -> int:
        """Notify subscribers that a bulk import has completed."""
        message = WebSocketMessage(
            type=NotificationType.BULK_IMPORT_COMPLETE,
            project_id=project_id,
            data={
                "import_id": import_id,
                "entities_created": entities_created,
                "entities_updated": entities_updated,
                "errors": errors or [],
            },
        )
        return await self.manager.broadcast_to_project(project_id, message)

    async def send_error(
        self,
        connection_id: str,
        error_message: str,
        error_code: Optional[str] = None
    ) -> bool:
        """Send an error message to a specific connection."""
        message = WebSocketMessage(
            type=NotificationType.ERROR,
            data={
                "error": error_message,
                "code": error_code,
            },
        )
        return await self.manager.send_personal(connection_id, message)


# Global instances
_connection_manager: Optional[ConnectionManager] = None
_notification_service: Optional[NotificationService] = None


def get_connection_manager() -> ConnectionManager:
    """
    Get or create the global connection manager instance.

    Returns:
        The connection manager singleton
    """
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionManager()
    return _connection_manager


def get_notification_service() -> NotificationService:
    """
    Get or create the global notification service instance.

    Returns:
        The notification service singleton
    """
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService(get_connection_manager())
    return _notification_service


def reset_websocket_services() -> None:
    """
    Reset the global WebSocket service instances.

    Useful for testing to ensure clean state.
    """
    global _connection_manager, _notification_service
    _connection_manager = None
    _notification_service = None
