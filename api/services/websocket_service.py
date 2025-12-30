"""
WebSocket Service for Basset Hound

This module provides real-time notification capabilities through WebSocket connections.
Designed for local-first, single-user operation.

Features:
- Connection management for multiple WebSocket clients
- Project-scoped subscriptions (subscribe to specific project events)
- Multiple notification types for different events
- Broadcasting to all connections or specific project subscribers
- Personal (direct) messaging to specific connections

Phase 4: Real-time Communication Layer
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
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

    # Graph visualization events
    GRAPH_NODE_ADDED = "graph_node_added"
    GRAPH_NODE_UPDATED = "graph_node_updated"
    GRAPH_NODE_DELETED = "graph_node_deleted"
    GRAPH_EDGE_ADDED = "graph_edge_added"
    GRAPH_EDGE_UPDATED = "graph_edge_updated"
    GRAPH_EDGE_DELETED = "graph_edge_deleted"
    GRAPH_LAYOUT_CHANGED = "graph_layout_changed"
    GRAPH_CLUSTER_DETECTED = "graph_cluster_detected"

    # Import events
    IMPORT_PROGRESS = "import_progress"
    IMPORT_COMPLETE = "import_complete"

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


class GraphAction(str, Enum):
    """Actions that can be performed on graph elements."""
    ADDED = "added"
    UPDATED = "updated"
    DELETED = "deleted"


@dataclass
class GraphNodeUpdate:
    """
    Represents an update to a graph node.

    Attributes:
        node_id: Unique identifier for the node
        entity_type: Type of entity (person, organization, etc.)
        action: The action performed (added, updated, deleted)
        position: Optional x,y coordinates for the node position
        properties: Optional properties of the node
    """
    node_id: str
    entity_type: str
    action: GraphAction
    position: Optional[Dict[str, float]] = None
    properties: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "node_id": self.node_id,
            "entity_type": self.entity_type,
            "action": self.action.value if isinstance(self.action, GraphAction) else self.action,
        }
        if self.position is not None:
            result["position"] = self.position
        if self.properties is not None:
            result["properties"] = self.properties
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GraphNodeUpdate":
        """Create a GraphNodeUpdate from a dictionary."""
        action = data.get("action")
        if isinstance(action, str):
            try:
                action = GraphAction(action)
            except ValueError:
                pass
        return cls(
            node_id=data["node_id"],
            entity_type=data["entity_type"],
            action=action,
            position=data.get("position"),
            properties=data.get("properties"),
        )


@dataclass
class GraphEdgeUpdate:
    """
    Represents an update to a graph edge (relationship).

    Attributes:
        edge_id: Unique identifier for the edge
        source: Source node ID
        target: Target node ID
        relationship_type: Type of relationship
        action: The action performed (added, updated, deleted)
        properties: Optional properties of the edge
    """
    edge_id: str
    source: str
    target: str
    relationship_type: str
    action: GraphAction
    properties: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "edge_id": self.edge_id,
            "source": self.source,
            "target": self.target,
            "relationship_type": self.relationship_type,
            "action": self.action.value if isinstance(self.action, GraphAction) else self.action,
        }
        if self.properties is not None:
            result["properties"] = self.properties
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GraphEdgeUpdate":
        """Create a GraphEdgeUpdate from a dictionary."""
        action = data.get("action")
        if isinstance(action, str):
            try:
                action = GraphAction(action)
            except ValueError:
                pass
        return cls(
            edge_id=data["edge_id"],
            source=data["source"],
            target=data["target"],
            relationship_type=data["relationship_type"],
            action=action,
            properties=data.get("properties"),
        )


@dataclass
class GraphLayoutUpdate:
    """
    Represents a graph layout change.

    Attributes:
        layout_type: Type of layout (force-directed, hierarchical, circular, etc.)
        affected_nodes: List of node IDs affected by the layout change
        positions: Optional mapping of node_id -> {x, y} positions
    """
    layout_type: str
    affected_nodes: List[str]
    positions: Optional[Dict[str, Dict[str, float]]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "layout_type": self.layout_type,
            "affected_nodes": self.affected_nodes,
        }
        if self.positions is not None:
            result["positions"] = self.positions
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GraphLayoutUpdate":
        """Create a GraphLayoutUpdate from a dictionary."""
        return cls(
            layout_type=data["layout_type"],
            affected_nodes=data["affected_nodes"],
            positions=data.get("positions"),
        )


@dataclass
class GraphClusterUpdate:
    """
    Represents a detected cluster in the graph.

    Attributes:
        cluster_id: Unique identifier for the cluster
        node_ids: List of node IDs in the cluster
        cluster_type: Type/category of the cluster
        confidence: Optional confidence score for the cluster detection
        properties: Optional additional properties
    """
    cluster_id: str
    node_ids: List[str]
    cluster_type: str
    confidence: Optional[float] = None
    properties: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "cluster_id": self.cluster_id,
            "node_ids": self.node_ids,
            "cluster_type": self.cluster_type,
        }
        if self.confidence is not None:
            result["confidence"] = self.confidence
        if self.properties is not None:
            result["properties"] = self.properties
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GraphClusterUpdate":
        """Create a GraphClusterUpdate from a dictionary."""
        return cls(
            cluster_id=data["cluster_id"],
            node_ids=data["node_ids"],
            cluster_type=data["cluster_type"],
            confidence=data.get("confidence"),
            properties=data.get("properties"),
        )


@dataclass
class ImportProgressUpdate:
    """
    Represents progress of a data import operation.

    Attributes:
        job_id: Unique identifier for the import job
        progress_percent: Progress percentage (0-100)
        records_processed: Number of records processed so far
        current_phase: Current phase of the import (parsing, validating, importing, etc.)
        total_records: Optional total number of records
        errors_count: Optional count of errors encountered
        message: Optional status message
    """
    job_id: str
    progress_percent: float
    records_processed: int
    current_phase: str
    total_records: Optional[int] = None
    errors_count: Optional[int] = None
    message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "job_id": self.job_id,
            "progress_percent": self.progress_percent,
            "records_processed": self.records_processed,
            "current_phase": self.current_phase,
        }
        if self.total_records is not None:
            result["total_records"] = self.total_records
        if self.errors_count is not None:
            result["errors_count"] = self.errors_count
        if self.message is not None:
            result["message"] = self.message
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ImportProgressUpdate":
        """Create an ImportProgressUpdate from a dictionary."""
        return cls(
            job_id=data["job_id"],
            progress_percent=data["progress_percent"],
            records_processed=data["records_processed"],
            current_phase=data["current_phase"],
            total_records=data.get("total_records"),
            errors_count=data.get("errors_count"),
            message=data.get("message"),
        )


@dataclass
class SubscriptionType:
    """
    Represents subscription types for WebSocket connections.
    """
    GRAPH = "graph"
    IMPORT_PROGRESS = "import_progress"
    ALL = "all"


@dataclass
class ConnectionQuality:
    """
    Tracks connection quality metrics.

    Attributes:
        latency_ms: Current latency in milliseconds
        latency_history: List of recent latency measurements
        last_ping_sent: Timestamp of last ping sent
        last_pong_received: Timestamp of last pong received
        messages_sent: Number of messages sent on this connection
        messages_received: Number of messages received on this connection
        errors_count: Number of errors on this connection
    """
    latency_ms: Optional[float] = None
    latency_history: List[float] = field(default_factory=list)
    last_ping_sent: Optional[str] = None
    last_pong_received: Optional[str] = None
    messages_sent: int = 0
    messages_received: int = 0
    errors_count: int = 0

    def record_latency(self, latency_ms: float, max_history: int = 10) -> None:
        """Record a new latency measurement."""
        self.latency_ms = latency_ms
        self.latency_history.append(latency_ms)
        if len(self.latency_history) > max_history:
            self.latency_history = self.latency_history[-max_history:]

    def get_average_latency(self) -> Optional[float]:
        """Get average latency from recent measurements."""
        if not self.latency_history:
            return None
        return sum(self.latency_history) / len(self.latency_history)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "latency_ms": self.latency_ms,
            "average_latency_ms": self.get_average_latency(),
            "messages_sent": self.messages_sent,
            "messages_received": self.messages_received,
            "errors_count": self.errors_count,
        }


@dataclass
class WebSocketConnection:
    """
    Represents an active WebSocket connection.

    Attributes:
        connection_id: Unique identifier for this connection
        websocket: The FastAPI WebSocket instance
        project_subscriptions: Set of project IDs this connection is subscribed to
        subscription_types: Set of subscription types (graph, import_progress, all)
        connected_at: Timestamp when the connection was established
        last_activity: Timestamp of last activity on this connection
        metadata: Optional metadata about the connection
        quality: Connection quality metrics
    """
    connection_id: str
    websocket: WebSocket
    project_subscriptions: Set[str] = field(default_factory=set)
    subscription_types: Set[str] = field(default_factory=lambda: {SubscriptionType.ALL})
    connected_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_activity: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)
    quality: ConnectionQuality = field(default_factory=ConnectionQuality)

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

    def subscribe_to_type(self, subscription_type: str) -> bool:
        """
        Subscribe to a specific event type.

        Args:
            subscription_type: Type of events to subscribe to (graph, import_progress, all)

        Returns:
            True if newly subscribed, False if already subscribed.
        """
        if subscription_type in self.subscription_types:
            return False
        self.subscription_types.add(subscription_type)
        return True

    def unsubscribe_from_type(self, subscription_type: str) -> bool:
        """
        Unsubscribe from a specific event type.

        Args:
            subscription_type: Type of events to unsubscribe from

        Returns:
            True if unsubscribed, False if wasn't subscribed.
        """
        if subscription_type not in self.subscription_types:
            return False
        self.subscription_types.discard(subscription_type)
        return True

    def is_subscribed_to_type(self, subscription_type: str) -> bool:
        """Check if subscribed to a specific event type."""
        return SubscriptionType.ALL in self.subscription_types or subscription_type in self.subscription_types

    def get_quality_info(self) -> Dict[str, Any]:
        """Get connection quality information."""
        return self.quality.to_dict()


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

    async def connect(
        self,
        websocket: WebSocket,
        connection_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> WebSocketConnection:
        """
        Accept a WebSocket connection and register it.

        Args:
            websocket: The FastAPI WebSocket instance
            connection_id: Optional custom connection ID (generated if not provided)
            metadata: Optional metadata to attach to the connection

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
        )

        async with self._lock:
            self._connections[connection_id] = connection
            self._total_connections += 1

        logger.info(f"WebSocket connection established: {connection_id}")

        # Send connection confirmation
        await self._send_to_connection(
            connection,
            WebSocketMessage(
                type=NotificationType.CONNECTED,
                data={"connection_id": connection_id}
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

    async def subscribe_to_type(
        self,
        connection_id: str,
        subscription_type: str
    ) -> bool:
        """
        Subscribe a connection to a specific event type.

        Args:
            connection_id: The connection ID
            subscription_type: The type of events to subscribe to (graph, import_progress, all)

        Returns:
            True if subscribed successfully, False if connection not found
        """
        async with self._lock:
            connection = self._connections.get(connection_id)
            if connection is None:
                return False

            connection.subscribe_to_type(subscription_type)
            logger.debug(f"Connection {connection_id} subscribed to type {subscription_type}")

        # Send subscription confirmation
        await self._send_to_connection(
            connection,
            WebSocketMessage(
                type=NotificationType.SUBSCRIBED,
                data={"subscription_type": subscription_type}
            )
        )

        return True

    async def unsubscribe_from_type(
        self,
        connection_id: str,
        subscription_type: str
    ) -> bool:
        """
        Unsubscribe a connection from a specific event type.

        Args:
            connection_id: The connection ID
            subscription_type: The type of events to unsubscribe from

        Returns:
            True if unsubscribed successfully, False if connection not found
        """
        async with self._lock:
            connection = self._connections.get(connection_id)
            if connection is None:
                return False

            connection.unsubscribe_from_type(subscription_type)
            logger.debug(f"Connection {connection_id} unsubscribed from type {subscription_type}")

        # Send unsubscription confirmation
        await self._send_to_connection(
            connection,
            WebSocketMessage(
                type=NotificationType.UNSUBSCRIBED,
                data={"subscription_type": subscription_type}
            )
        )

        return True

    async def broadcast_to_project_with_type(
        self,
        project_id: str,
        message: WebSocketMessage,
        subscription_type: str,
        exclude: Optional[Set[str]] = None
    ) -> int:
        """
        Broadcast a message to connections subscribed to a project AND a specific type.

        Args:
            project_id: The project ID
            message: The message to broadcast
            subscription_type: The subscription type to filter by
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

            # Check if connection is subscribed to this type
            if not connection.is_subscribed_to_type(subscription_type):
                continue

            success = await self._send_to_connection(connection, message)
            if success:
                sent_count += 1
            else:
                failed_connections.append(connection_id)

        # Cleanup failed connections
        for connection_id in failed_connections:
            await self.disconnect(connection_id)

        logger.debug(f"Broadcast to project {project_id} (type: {subscription_type}): {sent_count} connections")
        return sent_count

    async def broadcast_node_change(
        self,
        project_id: str,
        node_update: "GraphNodeUpdate"
    ) -> int:
        """
        Broadcast a graph node change to all subscribers.

        Args:
            project_id: The project ID
            node_update: The node update payload

        Returns:
            Number of connections the message was sent to
        """
        # Determine the notification type based on the action
        action_to_type = {
            GraphAction.ADDED: NotificationType.GRAPH_NODE_ADDED,
            GraphAction.UPDATED: NotificationType.GRAPH_NODE_UPDATED,
            GraphAction.DELETED: NotificationType.GRAPH_NODE_DELETED,
        }
        notification_type = action_to_type.get(
            node_update.action,
            NotificationType.GRAPH_NODE_UPDATED
        )

        message = WebSocketMessage(
            type=notification_type,
            project_id=project_id,
            entity_id=node_update.node_id,
            data=node_update.to_dict(),
        )

        return await self.broadcast_to_project_with_type(
            project_id,
            message,
            SubscriptionType.GRAPH
        )

    async def broadcast_edge_change(
        self,
        project_id: str,
        edge_update: "GraphEdgeUpdate"
    ) -> int:
        """
        Broadcast a graph edge change to all subscribers.

        Args:
            project_id: The project ID
            edge_update: The edge update payload

        Returns:
            Number of connections the message was sent to
        """
        # Determine the notification type based on the action
        action_to_type = {
            GraphAction.ADDED: NotificationType.GRAPH_EDGE_ADDED,
            GraphAction.UPDATED: NotificationType.GRAPH_EDGE_UPDATED,
            GraphAction.DELETED: NotificationType.GRAPH_EDGE_DELETED,
        }
        notification_type = action_to_type.get(
            edge_update.action,
            NotificationType.GRAPH_EDGE_UPDATED
        )

        message = WebSocketMessage(
            type=notification_type,
            project_id=project_id,
            data=edge_update.to_dict(),
        )

        return await self.broadcast_to_project_with_type(
            project_id,
            message,
            SubscriptionType.GRAPH
        )

    async def broadcast_layout_change(
        self,
        project_id: str,
        layout_update: "GraphLayoutUpdate"
    ) -> int:
        """
        Broadcast a graph layout change to all subscribers.

        Args:
            project_id: The project ID
            layout_update: The layout update payload

        Returns:
            Number of connections the message was sent to
        """
        message = WebSocketMessage(
            type=NotificationType.GRAPH_LAYOUT_CHANGED,
            project_id=project_id,
            data=layout_update.to_dict(),
        )

        return await self.broadcast_to_project_with_type(
            project_id,
            message,
            SubscriptionType.GRAPH
        )

    async def broadcast_cluster_detected(
        self,
        project_id: str,
        cluster_update: "GraphClusterUpdate"
    ) -> int:
        """
        Broadcast a cluster detection event to all subscribers.

        Args:
            project_id: The project ID
            cluster_update: The cluster update payload

        Returns:
            Number of connections the message was sent to
        """
        message = WebSocketMessage(
            type=NotificationType.GRAPH_CLUSTER_DETECTED,
            project_id=project_id,
            data=cluster_update.to_dict(),
        )

        return await self.broadcast_to_project_with_type(
            project_id,
            message,
            SubscriptionType.GRAPH
        )

    async def broadcast_import_progress(
        self,
        project_id: str,
        progress_update: "ImportProgressUpdate"
    ) -> int:
        """
        Broadcast import progress to all subscribers.

        Args:
            project_id: The project ID
            progress_update: The import progress payload

        Returns:
            Number of connections the message was sent to
        """
        message = WebSocketMessage(
            type=NotificationType.IMPORT_PROGRESS,
            project_id=project_id,
            data=progress_update.to_dict(),
        )

        return await self.broadcast_to_project_with_type(
            project_id,
            message,
            SubscriptionType.IMPORT_PROGRESS
        )

    async def broadcast_import_complete(
        self,
        project_id: str,
        job_id: str,
        total_records: int,
        success_count: int,
        error_count: int,
        errors: Optional[List[str]] = None
    ) -> int:
        """
        Broadcast import completion to all subscribers.

        Args:
            project_id: The project ID
            job_id: The import job ID
            total_records: Total number of records processed
            success_count: Number of successfully imported records
            error_count: Number of errors
            errors: Optional list of error messages

        Returns:
            Number of connections the message was sent to
        """
        message = WebSocketMessage(
            type=NotificationType.IMPORT_COMPLETE,
            project_id=project_id,
            data={
                "job_id": job_id,
                "total_records": total_records,
                "success_count": success_count,
                "error_count": error_count,
                "errors": errors or [],
            },
        )

        return await self.broadcast_to_project_with_type(
            project_id,
            message,
            SubscriptionType.IMPORT_PROGRESS
        )

    def get_connection_quality(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """
        Get connection quality metrics for a specific connection.

        Args:
            connection_id: The connection ID

        Returns:
            Dictionary with quality metrics or None if connection not found
        """
        connection = self._connections.get(connection_id)
        if connection is None:
            return None
        return connection.get_quality_info()

    async def record_latency(
        self,
        connection_id: str,
        latency_ms: float
    ) -> bool:
        """
        Record a latency measurement for a connection.

        Args:
            connection_id: The connection ID
            latency_ms: The latency in milliseconds

        Returns:
            True if recorded successfully, False if connection not found
        """
        connection = self._connections.get(connection_id)
        if connection is None:
            return False

        connection.quality.record_latency(latency_ms)
        return True

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

    # Graph-specific notification methods

    async def notify_graph_node_added(
        self,
        project_id: str,
        node_id: str,
        entity_type: str,
        position: Optional[Dict[str, float]] = None,
        properties: Optional[Dict[str, Any]] = None
    ) -> int:
        """Notify subscribers that a graph node was added."""
        node_update = GraphNodeUpdate(
            node_id=node_id,
            entity_type=entity_type,
            action=GraphAction.ADDED,
            position=position,
            properties=properties,
        )
        return await self.manager.broadcast_node_change(project_id, node_update)

    async def notify_graph_node_updated(
        self,
        project_id: str,
        node_id: str,
        entity_type: str,
        position: Optional[Dict[str, float]] = None,
        properties: Optional[Dict[str, Any]] = None
    ) -> int:
        """Notify subscribers that a graph node was updated."""
        node_update = GraphNodeUpdate(
            node_id=node_id,
            entity_type=entity_type,
            action=GraphAction.UPDATED,
            position=position,
            properties=properties,
        )
        return await self.manager.broadcast_node_change(project_id, node_update)

    async def notify_graph_node_deleted(
        self,
        project_id: str,
        node_id: str,
        entity_type: str
    ) -> int:
        """Notify subscribers that a graph node was deleted."""
        node_update = GraphNodeUpdate(
            node_id=node_id,
            entity_type=entity_type,
            action=GraphAction.DELETED,
        )
        return await self.manager.broadcast_node_change(project_id, node_update)

    async def notify_graph_edge_added(
        self,
        project_id: str,
        edge_id: str,
        source: str,
        target: str,
        relationship_type: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> int:
        """Notify subscribers that a graph edge was added."""
        edge_update = GraphEdgeUpdate(
            edge_id=edge_id,
            source=source,
            target=target,
            relationship_type=relationship_type,
            action=GraphAction.ADDED,
            properties=properties,
        )
        return await self.manager.broadcast_edge_change(project_id, edge_update)

    async def notify_graph_edge_updated(
        self,
        project_id: str,
        edge_id: str,
        source: str,
        target: str,
        relationship_type: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> int:
        """Notify subscribers that a graph edge was updated."""
        edge_update = GraphEdgeUpdate(
            edge_id=edge_id,
            source=source,
            target=target,
            relationship_type=relationship_type,
            action=GraphAction.UPDATED,
            properties=properties,
        )
        return await self.manager.broadcast_edge_change(project_id, edge_update)

    async def notify_graph_edge_deleted(
        self,
        project_id: str,
        edge_id: str,
        source: str,
        target: str,
        relationship_type: str
    ) -> int:
        """Notify subscribers that a graph edge was deleted."""
        edge_update = GraphEdgeUpdate(
            edge_id=edge_id,
            source=source,
            target=target,
            relationship_type=relationship_type,
            action=GraphAction.DELETED,
        )
        return await self.manager.broadcast_edge_change(project_id, edge_update)

    async def notify_graph_layout_changed(
        self,
        project_id: str,
        layout_type: str,
        affected_nodes: List[str],
        positions: Optional[Dict[str, Dict[str, float]]] = None
    ) -> int:
        """Notify subscribers that the graph layout has changed."""
        layout_update = GraphLayoutUpdate(
            layout_type=layout_type,
            affected_nodes=affected_nodes,
            positions=positions,
        )
        return await self.manager.broadcast_layout_change(project_id, layout_update)

    async def notify_graph_cluster_detected(
        self,
        project_id: str,
        cluster_id: str,
        node_ids: List[str],
        cluster_type: str,
        confidence: Optional[float] = None,
        properties: Optional[Dict[str, Any]] = None
    ) -> int:
        """Notify subscribers that a new cluster was detected."""
        cluster_update = GraphClusterUpdate(
            cluster_id=cluster_id,
            node_ids=node_ids,
            cluster_type=cluster_type,
            confidence=confidence,
            properties=properties,
        )
        return await self.manager.broadcast_cluster_detected(project_id, cluster_update)

    async def notify_import_progress(
        self,
        project_id: str,
        job_id: str,
        progress_percent: float,
        records_processed: int,
        current_phase: str,
        total_records: Optional[int] = None,
        errors_count: Optional[int] = None,
        message: Optional[str] = None
    ) -> int:
        """Notify subscribers of import progress."""
        progress_update = ImportProgressUpdate(
            job_id=job_id,
            progress_percent=progress_percent,
            records_processed=records_processed,
            current_phase=current_phase,
            total_records=total_records,
            errors_count=errors_count,
            message=message,
        )
        return await self.manager.broadcast_import_progress(project_id, progress_update)

    async def notify_import_complete(
        self,
        project_id: str,
        job_id: str,
        total_records: int,
        success_count: int,
        error_count: int,
        errors: Optional[List[str]] = None
    ) -> int:
        """Notify subscribers that an import has completed."""
        return await self.manager.broadcast_import_complete(
            project_id=project_id,
            job_id=job_id,
            total_records=total_records,
            success_count=success_count,
            error_count=error_count,
            errors=errors,
        )


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


# ============================================================================
# Integration Hooks
# ============================================================================
# These hooks can be called from entity/relationship services to automatically
# broadcast changes through WebSocket connections.


class GraphUpdateHooks:
    """
    Integration hooks for broadcasting graph updates from entity/relationship services.

    Usage:
        from api.services.websocket_service import graph_hooks

        # In your entity service after creating an entity:
        await graph_hooks.on_entity_created(project_id, entity_id, entity_type, properties)

        # In your relationship service after creating a relationship:
        await graph_hooks.on_relationship_created(
            project_id, relationship_id, source_id, target_id, rel_type
        )
    """

    def __init__(self):
        """Initialize the graph update hooks."""
        self._enabled = True

    @property
    def enabled(self) -> bool:
        """Check if hooks are enabled."""
        return self._enabled

    def enable(self) -> None:
        """Enable the hooks."""
        self._enabled = True

    def disable(self) -> None:
        """Disable the hooks (useful during bulk operations)."""
        self._enabled = False

    async def on_entity_created(
        self,
        project_id: str,
        entity_id: str,
        entity_type: str,
        properties: Optional[Dict[str, Any]] = None,
        position: Optional[Dict[str, float]] = None
    ) -> int:
        """
        Hook to call when an entity is created.

        Args:
            project_id: The project ID
            entity_id: The entity ID
            entity_type: Type of entity
            properties: Optional entity properties
            position: Optional position for graph visualization

        Returns:
            Number of clients notified
        """
        if not self._enabled:
            return 0

        notification_service = get_notification_service()

        # Send entity created notification (existing functionality)
        await notification_service.notify_entity_created(
            project_id, entity_id, properties
        )

        # Send graph node added notification (new functionality)
        return await notification_service.notify_graph_node_added(
            project_id=project_id,
            node_id=entity_id,
            entity_type=entity_type,
            position=position,
            properties=properties,
        )

    async def on_entity_updated(
        self,
        project_id: str,
        entity_id: str,
        entity_type: str,
        changes: Optional[Dict[str, Any]] = None,
        position: Optional[Dict[str, float]] = None
    ) -> int:
        """
        Hook to call when an entity is updated.

        Args:
            project_id: The project ID
            entity_id: The entity ID
            entity_type: Type of entity
            changes: Optional dictionary of changes
            position: Optional updated position

        Returns:
            Number of clients notified
        """
        if not self._enabled:
            return 0

        notification_service = get_notification_service()

        # Send entity updated notification (existing functionality)
        await notification_service.notify_entity_updated(
            project_id, entity_id, changes
        )

        # Send graph node updated notification (new functionality)
        return await notification_service.notify_graph_node_updated(
            project_id=project_id,
            node_id=entity_id,
            entity_type=entity_type,
            position=position,
            properties=changes,
        )

    async def on_entity_deleted(
        self,
        project_id: str,
        entity_id: str,
        entity_type: str
    ) -> int:
        """
        Hook to call when an entity is deleted.

        Args:
            project_id: The project ID
            entity_id: The entity ID
            entity_type: Type of entity

        Returns:
            Number of clients notified
        """
        if not self._enabled:
            return 0

        notification_service = get_notification_service()

        # Send entity deleted notification (existing functionality)
        await notification_service.notify_entity_deleted(project_id, entity_id)

        # Send graph node deleted notification (new functionality)
        return await notification_service.notify_graph_node_deleted(
            project_id=project_id,
            node_id=entity_id,
            entity_type=entity_type,
        )

    async def on_relationship_created(
        self,
        project_id: str,
        relationship_id: str,
        source_entity_id: str,
        target_entity_id: str,
        relationship_type: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Hook to call when a relationship is created.

        Args:
            project_id: The project ID
            relationship_id: The relationship ID
            source_entity_id: Source entity ID
            target_entity_id: Target entity ID
            relationship_type: Type of relationship
            properties: Optional relationship properties

        Returns:
            Number of clients notified
        """
        if not self._enabled:
            return 0

        notification_service = get_notification_service()

        # Send relationship added notification (existing functionality)
        await notification_service.notify_relationship_added(
            project_id=project_id,
            source_entity_id=source_entity_id,
            target_entity_id=target_entity_id,
            relationship_type=relationship_type,
            relationship_data=properties,
        )

        # Send graph edge added notification (new functionality)
        return await notification_service.notify_graph_edge_added(
            project_id=project_id,
            edge_id=relationship_id,
            source=source_entity_id,
            target=target_entity_id,
            relationship_type=relationship_type,
            properties=properties,
        )

    async def on_relationship_updated(
        self,
        project_id: str,
        relationship_id: str,
        source_entity_id: str,
        target_entity_id: str,
        relationship_type: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Hook to call when a relationship is updated.

        Args:
            project_id: The project ID
            relationship_id: The relationship ID
            source_entity_id: Source entity ID
            target_entity_id: Target entity ID
            relationship_type: Type of relationship
            properties: Optional updated properties

        Returns:
            Number of clients notified
        """
        if not self._enabled:
            return 0

        notification_service = get_notification_service()

        # Send graph edge updated notification
        return await notification_service.notify_graph_edge_updated(
            project_id=project_id,
            edge_id=relationship_id,
            source=source_entity_id,
            target=target_entity_id,
            relationship_type=relationship_type,
            properties=properties,
        )

    async def on_relationship_deleted(
        self,
        project_id: str,
        relationship_id: str,
        source_entity_id: str,
        target_entity_id: str,
        relationship_type: str
    ) -> int:
        """
        Hook to call when a relationship is deleted.

        Args:
            project_id: The project ID
            relationship_id: The relationship ID
            source_entity_id: Source entity ID
            target_entity_id: Target entity ID
            relationship_type: Type of relationship

        Returns:
            Number of clients notified
        """
        if not self._enabled:
            return 0

        notification_service = get_notification_service()

        # Send relationship removed notification (existing functionality)
        await notification_service.notify_relationship_removed(
            project_id=project_id,
            source_entity_id=source_entity_id,
            target_entity_id=target_entity_id,
            relationship_type=relationship_type,
        )

        # Send graph edge deleted notification (new functionality)
        return await notification_service.notify_graph_edge_deleted(
            project_id=project_id,
            edge_id=relationship_id,
            source=source_entity_id,
            target=target_entity_id,
            relationship_type=relationship_type,
        )

    async def on_layout_changed(
        self,
        project_id: str,
        layout_type: str,
        affected_nodes: List[str],
        positions: Optional[Dict[str, Dict[str, float]]] = None
    ) -> int:
        """
        Hook to call when graph layout changes.

        Args:
            project_id: The project ID
            layout_type: Type of layout applied
            affected_nodes: List of affected node IDs
            positions: Optional mapping of node_id -> position

        Returns:
            Number of clients notified
        """
        if not self._enabled:
            return 0

        notification_service = get_notification_service()
        return await notification_service.notify_graph_layout_changed(
            project_id=project_id,
            layout_type=layout_type,
            affected_nodes=affected_nodes,
            positions=positions,
        )

    async def on_cluster_detected(
        self,
        project_id: str,
        cluster_id: str,
        node_ids: List[str],
        cluster_type: str,
        confidence: Optional[float] = None,
        properties: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Hook to call when a new cluster is detected.

        Args:
            project_id: The project ID
            cluster_id: Unique cluster identifier
            node_ids: List of node IDs in the cluster
            cluster_type: Type/category of the cluster
            confidence: Optional confidence score
            properties: Optional additional properties

        Returns:
            Number of clients notified
        """
        if not self._enabled:
            return 0

        notification_service = get_notification_service()
        return await notification_service.notify_graph_cluster_detected(
            project_id=project_id,
            cluster_id=cluster_id,
            node_ids=node_ids,
            cluster_type=cluster_type,
            confidence=confidence,
            properties=properties,
        )


class ImportProgressHooks:
    """
    Integration hooks for broadcasting import progress updates.

    Usage:
        from api.services.websocket_service import import_hooks

        # During import:
        await import_hooks.on_progress(
            project_id, job_id, progress_percent=50,
            records_processed=500, current_phase="importing"
        )

        # When import completes:
        await import_hooks.on_complete(
            project_id, job_id, total_records=1000,
            success_count=990, error_count=10
        )
    """

    def __init__(self):
        """Initialize the import progress hooks."""
        self._enabled = True

    @property
    def enabled(self) -> bool:
        """Check if hooks are enabled."""
        return self._enabled

    def enable(self) -> None:
        """Enable the hooks."""
        self._enabled = True

    def disable(self) -> None:
        """Disable the hooks."""
        self._enabled = False

    async def on_progress(
        self,
        project_id: str,
        job_id: str,
        progress_percent: float,
        records_processed: int,
        current_phase: str,
        total_records: Optional[int] = None,
        errors_count: Optional[int] = None,
        message: Optional[str] = None
    ) -> int:
        """
        Hook to call to report import progress.

        Args:
            project_id: The project ID
            job_id: The import job ID
            progress_percent: Progress percentage (0-100)
            records_processed: Number of records processed
            current_phase: Current phase description
            total_records: Optional total record count
            errors_count: Optional error count
            message: Optional status message

        Returns:
            Number of clients notified
        """
        if not self._enabled:
            return 0

        notification_service = get_notification_service()
        return await notification_service.notify_import_progress(
            project_id=project_id,
            job_id=job_id,
            progress_percent=progress_percent,
            records_processed=records_processed,
            current_phase=current_phase,
            total_records=total_records,
            errors_count=errors_count,
            message=message,
        )

    async def on_complete(
        self,
        project_id: str,
        job_id: str,
        total_records: int,
        success_count: int,
        error_count: int,
        errors: Optional[List[str]] = None
    ) -> int:
        """
        Hook to call when import completes.

        Args:
            project_id: The project ID
            job_id: The import job ID
            total_records: Total records processed
            success_count: Successful imports
            error_count: Failed imports
            errors: Optional list of error messages

        Returns:
            Number of clients notified
        """
        if not self._enabled:
            return 0

        notification_service = get_notification_service()
        return await notification_service.notify_import_complete(
            project_id=project_id,
            job_id=job_id,
            total_records=total_records,
            success_count=success_count,
            error_count=error_count,
            errors=errors,
        )


# Global hook instances
graph_hooks = GraphUpdateHooks()
import_hooks = ImportProgressHooks()
