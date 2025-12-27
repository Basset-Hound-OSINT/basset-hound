"""
Tests for the WebSocket Service (Phase 4)

Comprehensive test coverage for:
- NotificationType enum
- WebSocketMessage dataclass
- WebSocketConnection dataclass
- ConnectionManager class
- NotificationService class
- Project subscriptions
- Broadcasting functionality
- Message serialization
- Error handling
"""

import asyncio
import json
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from api.services.websocket_service import (
    ConnectionManager,
    NotificationService,
    NotificationType,
    WebSocketConnection,
    WebSocketMessage,
    get_connection_manager,
    get_notification_service,
    reset_websocket_services,
)


# ==================== NotificationType Tests ====================


class TestNotificationType:
    """Tests for NotificationType enum."""

    def test_entity_created_type(self):
        """Test ENTITY_CREATED notification type."""
        assert NotificationType.ENTITY_CREATED.value == "entity_created"

    def test_entity_updated_type(self):
        """Test ENTITY_UPDATED notification type."""
        assert NotificationType.ENTITY_UPDATED.value == "entity_updated"

    def test_entity_deleted_type(self):
        """Test ENTITY_DELETED notification type."""
        assert NotificationType.ENTITY_DELETED.value == "entity_deleted"

    def test_relationship_added_type(self):
        """Test RELATIONSHIP_ADDED notification type."""
        assert NotificationType.RELATIONSHIP_ADDED.value == "relationship_added"

    def test_relationship_removed_type(self):
        """Test RELATIONSHIP_REMOVED notification type."""
        assert NotificationType.RELATIONSHIP_REMOVED.value == "relationship_removed"

    def test_search_completed_type(self):
        """Test SEARCH_COMPLETED notification type."""
        assert NotificationType.SEARCH_COMPLETED.value == "search_completed"

    def test_report_ready_type(self):
        """Test REPORT_READY notification type."""
        assert NotificationType.REPORT_READY.value == "report_ready"

    def test_bulk_import_complete_type(self):
        """Test BULK_IMPORT_COMPLETE notification type."""
        assert NotificationType.BULK_IMPORT_COMPLETE.value == "bulk_import_complete"

    def test_connection_types(self):
        """Test connection-related notification types."""
        assert NotificationType.CONNECTED.value == "connected"
        assert NotificationType.DISCONNECTED.value == "disconnected"
        assert NotificationType.SUBSCRIBED.value == "subscribed"
        assert NotificationType.UNSUBSCRIBED.value == "unsubscribed"

    def test_ping_pong_types(self):
        """Test keepalive notification types."""
        assert NotificationType.PING.value == "ping"
        assert NotificationType.PONG.value == "pong"

    def test_error_type(self):
        """Test ERROR notification type."""
        assert NotificationType.ERROR.value == "error"

    def test_notification_type_is_string_enum(self):
        """Test that NotificationType inherits from str."""
        assert isinstance(NotificationType.ENTITY_CREATED, str)
        assert NotificationType.ENTITY_CREATED == "entity_created"


# ==================== WebSocketMessage Tests ====================


class TestWebSocketMessage:
    """Tests for WebSocketMessage dataclass."""

    def test_message_creation_minimal(self):
        """Test creating a message with minimal parameters."""
        message = WebSocketMessage(type=NotificationType.ENTITY_CREATED)

        assert message.type == NotificationType.ENTITY_CREATED
        assert message.project_id is None
        assert message.entity_id is None
        assert message.data is None
        assert message.timestamp is not None
        assert message.message_id is not None

    def test_message_creation_full(self):
        """Test creating a message with all parameters."""
        message = WebSocketMessage(
            type=NotificationType.ENTITY_UPDATED,
            project_id="project-123",
            entity_id="entity-456",
            data={"field": "value"},
            timestamp="2024-01-15T10:30:00Z",
            message_id="msg-789"
        )

        assert message.type == NotificationType.ENTITY_UPDATED
        assert message.project_id == "project-123"
        assert message.entity_id == "entity-456"
        assert message.data == {"field": "value"}
        assert message.timestamp == "2024-01-15T10:30:00Z"
        assert message.message_id == "msg-789"

    def test_message_to_dict(self):
        """Test converting message to dictionary."""
        message = WebSocketMessage(
            type=NotificationType.ENTITY_CREATED,
            project_id="project-123",
            entity_id="entity-456",
            data={"name": "Test"}
        )

        result = message.to_dict()

        assert result["type"] == "entity_created"
        assert result["project_id"] == "project-123"
        assert result["entity_id"] == "entity-456"
        assert result["data"] == {"name": "Test"}
        assert "timestamp" in result
        assert "message_id" in result

    def test_message_to_dict_minimal(self):
        """Test to_dict excludes None optional fields."""
        message = WebSocketMessage(type=NotificationType.PING)

        result = message.to_dict()

        assert result["type"] == "ping"
        assert "project_id" not in result
        assert "entity_id" not in result
        assert "data" not in result

    def test_message_to_json(self):
        """Test serializing message to JSON."""
        message = WebSocketMessage(
            type=NotificationType.ENTITY_CREATED,
            project_id="project-123"
        )

        json_str = message.to_json()
        parsed = json.loads(json_str)

        assert parsed["type"] == "entity_created"
        assert parsed["project_id"] == "project-123"

    def test_message_from_dict(self):
        """Test creating message from dictionary."""
        data = {
            "type": "entity_updated",
            "project_id": "project-123",
            "entity_id": "entity-456",
            "data": {"changes": ["field1"]},
            "timestamp": "2024-01-15T10:30:00Z",
            "message_id": "msg-123"
        }

        message = WebSocketMessage.from_dict(data)

        assert message.type == NotificationType.ENTITY_UPDATED
        assert message.project_id == "project-123"
        assert message.entity_id == "entity-456"
        assert message.data == {"changes": ["field1"]}

    def test_message_from_dict_unknown_type(self):
        """Test creating message with unknown type keeps it as string."""
        data = {
            "type": "custom_unknown_type",
            "data": {"info": "test"}
        }

        message = WebSocketMessage.from_dict(data)

        assert message.type == "custom_unknown_type"

    def test_message_from_json(self):
        """Test deserializing message from JSON."""
        json_str = '{"type": "entity_deleted", "project_id": "proj-1", "entity_id": "ent-1"}'

        message = WebSocketMessage.from_json(json_str)

        assert message.type == NotificationType.ENTITY_DELETED
        assert message.project_id == "proj-1"
        assert message.entity_id == "ent-1"

    def test_message_timestamp_format(self):
        """Test that timestamp is in ISO format."""
        message = WebSocketMessage(type=NotificationType.PING)

        # Should be parseable as ISO datetime
        timestamp = message.timestamp
        assert "T" in timestamp  # ISO format contains T separator


# ==================== WebSocketConnection Tests ====================


class TestWebSocketConnection:
    """Tests for WebSocketConnection dataclass."""

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket."""
        ws = MagicMock()
        ws.send_text = AsyncMock()
        ws.close = AsyncMock()
        return ws

    def test_connection_creation(self, mock_websocket):
        """Test creating a WebSocket connection."""
        connection = WebSocketConnection(
            connection_id="conn-123",
            websocket=mock_websocket
        )

        assert connection.connection_id == "conn-123"
        assert connection.websocket == mock_websocket
        assert len(connection.project_subscriptions) == 0
        assert connection.connected_at is not None
        assert connection.last_activity is not None

    def test_connection_with_metadata(self, mock_websocket):
        """Test connection with metadata."""
        connection = WebSocketConnection(
            connection_id="conn-123",
            websocket=mock_websocket,
            metadata={"user_id": "user-456", "client": "web"}
        )

        assert connection.metadata["user_id"] == "user-456"
        assert connection.metadata["client"] == "web"

    def test_subscribe_to_project(self, mock_websocket):
        """Test subscribing to a project."""
        connection = WebSocketConnection(
            connection_id="conn-123",
            websocket=mock_websocket
        )

        result = connection.subscribe_to_project("project-1")

        assert result is True
        assert "project-1" in connection.project_subscriptions

    def test_subscribe_to_project_already_subscribed(self, mock_websocket):
        """Test subscribing to already subscribed project returns False."""
        connection = WebSocketConnection(
            connection_id="conn-123",
            websocket=mock_websocket,
            project_subscriptions={"project-1"}
        )

        result = connection.subscribe_to_project("project-1")

        assert result is False

    def test_unsubscribe_from_project(self, mock_websocket):
        """Test unsubscribing from a project."""
        connection = WebSocketConnection(
            connection_id="conn-123",
            websocket=mock_websocket,
            project_subscriptions={"project-1", "project-2"}
        )

        result = connection.unsubscribe_from_project("project-1")

        assert result is True
        assert "project-1" not in connection.project_subscriptions
        assert "project-2" in connection.project_subscriptions

    def test_unsubscribe_from_project_not_subscribed(self, mock_websocket):
        """Test unsubscribing from non-subscribed project returns False."""
        connection = WebSocketConnection(
            connection_id="conn-123",
            websocket=mock_websocket
        )

        result = connection.unsubscribe_from_project("project-1")

        assert result is False

    def test_is_subscribed_to(self, mock_websocket):
        """Test checking subscription status."""
        connection = WebSocketConnection(
            connection_id="conn-123",
            websocket=mock_websocket,
            project_subscriptions={"project-1"}
        )

        assert connection.is_subscribed_to("project-1") is True
        assert connection.is_subscribed_to("project-2") is False

    def test_update_activity(self, mock_websocket):
        """Test updating activity timestamp."""
        connection = WebSocketConnection(
            connection_id="conn-123",
            websocket=mock_websocket
        )
        initial_activity = connection.last_activity

        import time
        time.sleep(0.01)
        connection.update_activity()

        assert connection.last_activity != initial_activity


# ==================== ConnectionManager Tests ====================


class TestConnectionManager:
    """Tests for ConnectionManager class."""

    @pytest.fixture
    def manager(self):
        """Create a fresh connection manager for each test."""
        return ConnectionManager()

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket."""
        ws = MagicMock()
        ws.accept = AsyncMock()
        ws.send_text = AsyncMock()
        ws.close = AsyncMock()
        ws.receive_text = AsyncMock()
        return ws

    @pytest.mark.asyncio
    async def test_connect(self, manager, mock_websocket):
        """Test connecting a WebSocket."""
        connection = await manager.connect(mock_websocket)

        assert connection is not None
        assert connection.connection_id is not None
        assert manager.active_connections == 1
        mock_websocket.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_with_custom_id(self, manager, mock_websocket):
        """Test connecting with a custom connection ID."""
        connection = await manager.connect(
            mock_websocket,
            connection_id="custom-id-123"
        )

        assert connection.connection_id == "custom-id-123"

    @pytest.mark.asyncio
    async def test_connect_with_metadata(self, manager, mock_websocket):
        """Test connecting with metadata."""
        connection = await manager.connect(
            mock_websocket,
            metadata={"user": "test"}
        )

        assert connection.metadata["user"] == "test"

    @pytest.mark.asyncio
    async def test_disconnect(self, manager, mock_websocket):
        """Test disconnecting a WebSocket."""
        connection = await manager.connect(mock_websocket)
        connection_id = connection.connection_id

        result = await manager.disconnect(connection_id)

        assert result is True
        assert manager.active_connections == 0

    @pytest.mark.asyncio
    async def test_disconnect_nonexistent(self, manager):
        """Test disconnecting nonexistent connection."""
        result = await manager.disconnect("nonexistent-id")

        assert result is False

    @pytest.mark.asyncio
    async def test_disconnect_cleans_up_subscriptions(self, manager, mock_websocket):
        """Test that disconnect cleans up project subscriptions."""
        connection = await manager.connect(mock_websocket)
        connection_id = connection.connection_id

        await manager.subscribe_to_project(connection_id, "project-1")
        await manager.disconnect(connection_id)

        # Project should have no subscribers
        assert len(manager.get_project_subscriber_ids("project-1")) == 0

    @pytest.mark.asyncio
    async def test_subscribe_to_project(self, manager, mock_websocket):
        """Test subscribing to a project."""
        connection = await manager.connect(mock_websocket)
        connection_id = connection.connection_id

        result = await manager.subscribe_to_project(connection_id, "project-1")

        assert result is True
        assert "project-1" in connection.project_subscriptions
        assert connection_id in manager.get_project_subscriber_ids("project-1")

    @pytest.mark.asyncio
    async def test_subscribe_nonexistent_connection(self, manager):
        """Test subscribing nonexistent connection."""
        result = await manager.subscribe_to_project("nonexistent", "project-1")

        assert result is False

    @pytest.mark.asyncio
    async def test_unsubscribe_from_project(self, manager, mock_websocket):
        """Test unsubscribing from a project."""
        connection = await manager.connect(mock_websocket)
        connection_id = connection.connection_id

        await manager.subscribe_to_project(connection_id, "project-1")
        result = await manager.unsubscribe_from_project(connection_id, "project-1")

        assert result is True
        assert "project-1" not in connection.project_subscriptions

    @pytest.mark.asyncio
    async def test_unsubscribe_nonexistent_connection(self, manager):
        """Test unsubscribing nonexistent connection."""
        result = await manager.unsubscribe_from_project("nonexistent", "project-1")

        assert result is False

    @pytest.mark.asyncio
    async def test_send_personal(self, manager, mock_websocket):
        """Test sending personal message."""
        connection = await manager.connect(mock_websocket)
        connection_id = connection.connection_id
        message = WebSocketMessage(type=NotificationType.PING)

        result = await manager.send_personal(connection_id, message)

        assert result is True
        # The connected message is sent first, then the ping
        assert mock_websocket.send_text.call_count >= 2

    @pytest.mark.asyncio
    async def test_send_personal_nonexistent(self, manager):
        """Test sending to nonexistent connection."""
        message = WebSocketMessage(type=NotificationType.PING)

        result = await manager.send_personal("nonexistent", message)

        assert result is False

    @pytest.mark.asyncio
    async def test_broadcast(self, manager):
        """Test broadcasting to all connections."""
        ws1 = MagicMock()
        ws1.accept = AsyncMock()
        ws1.send_text = AsyncMock()

        ws2 = MagicMock()
        ws2.accept = AsyncMock()
        ws2.send_text = AsyncMock()

        await manager.connect(ws1, connection_id="conn-1")
        await manager.connect(ws2, connection_id="conn-2")

        message = WebSocketMessage(
            type=NotificationType.ENTITY_CREATED,
            project_id="project-1"
        )

        count = await manager.broadcast(message)

        assert count == 2

    @pytest.mark.asyncio
    async def test_broadcast_with_exclude(self, manager):
        """Test broadcasting with exclusion list."""
        ws1 = MagicMock()
        ws1.accept = AsyncMock()
        ws1.send_text = AsyncMock()

        ws2 = MagicMock()
        ws2.accept = AsyncMock()
        ws2.send_text = AsyncMock()

        await manager.connect(ws1, connection_id="conn-1")
        await manager.connect(ws2, connection_id="conn-2")

        message = WebSocketMessage(type=NotificationType.PING)

        count = await manager.broadcast(message, exclude={"conn-1"})

        assert count == 1

    @pytest.mark.asyncio
    async def test_broadcast_to_project(self, manager):
        """Test broadcasting to project subscribers only."""
        ws1 = MagicMock()
        ws1.accept = AsyncMock()
        ws1.send_text = AsyncMock()

        ws2 = MagicMock()
        ws2.accept = AsyncMock()
        ws2.send_text = AsyncMock()

        ws3 = MagicMock()
        ws3.accept = AsyncMock()
        ws3.send_text = AsyncMock()

        await manager.connect(ws1, connection_id="conn-1")
        await manager.connect(ws2, connection_id="conn-2")
        await manager.connect(ws3, connection_id="conn-3")

        # Only conn-1 and conn-2 subscribe to project-1
        await manager.subscribe_to_project("conn-1", "project-1")
        await manager.subscribe_to_project("conn-2", "project-1")

        message = WebSocketMessage(
            type=NotificationType.ENTITY_CREATED,
            project_id="project-1"
        )

        count = await manager.broadcast_to_project("project-1", message)

        assert count == 2

    @pytest.mark.asyncio
    async def test_broadcast_to_project_with_exclude(self, manager):
        """Test broadcasting to project with exclusion."""
        ws1 = MagicMock()
        ws1.accept = AsyncMock()
        ws1.send_text = AsyncMock()

        ws2 = MagicMock()
        ws2.accept = AsyncMock()
        ws2.send_text = AsyncMock()

        await manager.connect(ws1, connection_id="conn-1")
        await manager.connect(ws2, connection_id="conn-2")

        await manager.subscribe_to_project("conn-1", "project-1")
        await manager.subscribe_to_project("conn-2", "project-1")

        message = WebSocketMessage(type=NotificationType.ENTITY_UPDATED)

        count = await manager.broadcast_to_project("project-1", message, exclude={"conn-1"})

        assert count == 1

    @pytest.mark.asyncio
    async def test_broadcast_to_empty_project(self, manager):
        """Test broadcasting to project with no subscribers."""
        message = WebSocketMessage(type=NotificationType.ENTITY_CREATED)

        count = await manager.broadcast_to_project("empty-project", message)

        assert count == 0

    @pytest.mark.asyncio
    async def test_handle_ping(self, manager, mock_websocket):
        """Test handling ping message."""
        connection = await manager.connect(mock_websocket)
        connection_id = connection.connection_id

        result = await manager.handle_ping(connection_id)

        assert result is True
        # Should have sent a pong
        calls = mock_websocket.send_text.call_args_list
        pong_sent = any("pong" in str(call) for call in calls)
        assert pong_sent

    @pytest.mark.asyncio
    async def test_get_connection(self, manager, mock_websocket):
        """Test getting a connection by ID."""
        connection = await manager.connect(mock_websocket, connection_id="test-id")

        retrieved = manager.get_connection("test-id")

        assert retrieved is not None
        assert retrieved.connection_id == "test-id"

    @pytest.mark.asyncio
    async def test_get_connection_nonexistent(self, manager):
        """Test getting nonexistent connection."""
        retrieved = manager.get_connection("nonexistent")

        assert retrieved is None

    @pytest.mark.asyncio
    async def test_get_all_connection_ids(self, manager):
        """Test getting all connection IDs."""
        ws1 = MagicMock()
        ws1.accept = AsyncMock()
        ws1.send_text = AsyncMock()

        ws2 = MagicMock()
        ws2.accept = AsyncMock()
        ws2.send_text = AsyncMock()

        await manager.connect(ws1, connection_id="conn-1")
        await manager.connect(ws2, connection_id="conn-2")

        ids = manager.get_all_connection_ids()

        assert "conn-1" in ids
        assert "conn-2" in ids
        assert len(ids) == 2

    @pytest.mark.asyncio
    async def test_get_project_subscriber_ids(self, manager, mock_websocket):
        """Test getting project subscriber IDs."""
        connection = await manager.connect(mock_websocket, connection_id="test-conn")
        await manager.subscribe_to_project("test-conn", "project-1")

        subscriber_ids = manager.get_project_subscriber_ids("project-1")

        assert "test-conn" in subscriber_ids

    @pytest.mark.asyncio
    async def test_get_stats(self, manager, mock_websocket):
        """Test getting connection statistics."""
        await manager.connect(mock_websocket, connection_id="conn-1")
        await manager.subscribe_to_project("conn-1", "project-1")

        stats = manager.get_stats()

        assert stats["active_connections"] == 1
        assert stats["total_connections"] >= 1
        assert "project_subscriptions" in stats

    @pytest.mark.asyncio
    async def test_close_all(self, manager):
        """Test closing all connections."""
        ws1 = MagicMock()
        ws1.accept = AsyncMock()
        ws1.send_text = AsyncMock()
        ws1.close = AsyncMock()

        ws2 = MagicMock()
        ws2.accept = AsyncMock()
        ws2.send_text = AsyncMock()
        ws2.close = AsyncMock()

        await manager.connect(ws1, connection_id="conn-1")
        await manager.connect(ws2, connection_id="conn-2")

        count = await manager.close_all()

        assert count == 2
        assert manager.active_connections == 0

    @pytest.mark.asyncio
    async def test_multiple_project_subscriptions(self, manager, mock_websocket):
        """Test subscribing to multiple projects."""
        connection = await manager.connect(mock_websocket)
        connection_id = connection.connection_id

        await manager.subscribe_to_project(connection_id, "project-1")
        await manager.subscribe_to_project(connection_id, "project-2")
        await manager.subscribe_to_project(connection_id, "project-3")

        assert len(connection.project_subscriptions) == 3
        assert connection_id in manager.get_project_subscriber_ids("project-1")
        assert connection_id in manager.get_project_subscriber_ids("project-2")
        assert connection_id in manager.get_project_subscriber_ids("project-3")

    @pytest.mark.asyncio
    async def test_broadcast_handles_send_errors(self, manager):
        """Test that broadcast handles send errors gracefully."""
        ws1 = MagicMock()
        ws1.accept = AsyncMock()
        ws1.send_text = AsyncMock()

        ws2 = MagicMock()
        ws2.accept = AsyncMock()
        ws2.send_text = AsyncMock(side_effect=Exception("Send failed"))

        await manager.connect(ws1, connection_id="conn-1")
        await manager.connect(ws2, connection_id="conn-2")

        message = WebSocketMessage(type=NotificationType.PING)

        # Should not raise, should handle error gracefully
        count = await manager.broadcast(message)

        # conn-1 should succeed, conn-2 should fail and be cleaned up
        assert count == 1


# ==================== NotificationService Tests ====================


class TestNotificationService:
    """Tests for NotificationService class."""

    @pytest.fixture
    def manager(self):
        """Create a connection manager."""
        return ConnectionManager()

    @pytest.fixture
    def service(self, manager):
        """Create a notification service."""
        return NotificationService(manager)

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket."""
        ws = MagicMock()
        ws.accept = AsyncMock()
        ws.send_text = AsyncMock()
        return ws

    @pytest.mark.asyncio
    async def test_notify_entity_created(self, service, manager, mock_websocket):
        """Test entity created notification."""
        connection = await manager.connect(mock_websocket, connection_id="conn-1")
        await manager.subscribe_to_project("conn-1", "project-1")

        count = await service.notify_entity_created(
            project_id="project-1",
            entity_id="entity-123",
            entity_data={"name": "Test Entity"}
        )

        assert count == 1

    @pytest.mark.asyncio
    async def test_notify_entity_updated(self, service, manager, mock_websocket):
        """Test entity updated notification."""
        await manager.connect(mock_websocket, connection_id="conn-1")
        await manager.subscribe_to_project("conn-1", "project-1")

        count = await service.notify_entity_updated(
            project_id="project-1",
            entity_id="entity-123",
            changes={"field": "new_value"}
        )

        assert count == 1

    @pytest.mark.asyncio
    async def test_notify_entity_deleted(self, service, manager, mock_websocket):
        """Test entity deleted notification."""
        await manager.connect(mock_websocket, connection_id="conn-1")
        await manager.subscribe_to_project("conn-1", "project-1")

        count = await service.notify_entity_deleted(
            project_id="project-1",
            entity_id="entity-123"
        )

        assert count == 1

    @pytest.mark.asyncio
    async def test_notify_relationship_added(self, service, manager, mock_websocket):
        """Test relationship added notification."""
        await manager.connect(mock_websocket, connection_id="conn-1")
        await manager.subscribe_to_project("conn-1", "project-1")

        count = await service.notify_relationship_added(
            project_id="project-1",
            source_entity_id="entity-1",
            target_entity_id="entity-2",
            relationship_type="KNOWS"
        )

        assert count == 1

    @pytest.mark.asyncio
    async def test_notify_relationship_removed(self, service, manager, mock_websocket):
        """Test relationship removed notification."""
        await manager.connect(mock_websocket, connection_id="conn-1")
        await manager.subscribe_to_project("conn-1", "project-1")

        count = await service.notify_relationship_removed(
            project_id="project-1",
            source_entity_id="entity-1",
            target_entity_id="entity-2",
            relationship_type="KNOWS"
        )

        assert count == 1

    @pytest.mark.asyncio
    async def test_notify_search_completed(self, service, manager, mock_websocket):
        """Test search completed notification."""
        await manager.connect(mock_websocket, connection_id="conn-1")
        await manager.subscribe_to_project("conn-1", "project-1")

        count = await service.notify_search_completed(
            project_id="project-1",
            search_id="search-123",
            results_count=42,
            results_summary={"top_results": []}
        )

        assert count == 1

    @pytest.mark.asyncio
    async def test_notify_report_ready(self, service, manager, mock_websocket):
        """Test report ready notification."""
        await manager.connect(mock_websocket, connection_id="conn-1")
        await manager.subscribe_to_project("conn-1", "project-1")

        count = await service.notify_report_ready(
            project_id="project-1",
            report_id="report-123",
            report_name="Investigation Report",
            download_url="/reports/report-123.pdf"
        )

        assert count == 1

    @pytest.mark.asyncio
    async def test_notify_bulk_import_complete(self, service, manager, mock_websocket):
        """Test bulk import complete notification."""
        await manager.connect(mock_websocket, connection_id="conn-1")
        await manager.subscribe_to_project("conn-1", "project-1")

        count = await service.notify_bulk_import_complete(
            project_id="project-1",
            import_id="import-123",
            entities_created=10,
            entities_updated=5,
            errors=["Warning: duplicate entry"]
        )

        assert count == 1

    @pytest.mark.asyncio
    async def test_send_error(self, service, manager, mock_websocket):
        """Test sending error message."""
        connection = await manager.connect(mock_websocket, connection_id="conn-1")

        result = await service.send_error(
            connection_id="conn-1",
            error_message="Something went wrong",
            error_code="ERR_001"
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_send_error_to_nonexistent(self, service):
        """Test sending error to nonexistent connection."""
        result = await service.send_error(
            connection_id="nonexistent",
            error_message="Test error"
        )

        assert result is False


# ==================== Singleton Tests ====================


class TestSingletons:
    """Tests for singleton pattern implementation."""

    def setup_method(self):
        """Reset singletons before each test."""
        reset_websocket_services()

    def test_get_connection_manager_creates_singleton(self):
        """Test that get_connection_manager returns singleton."""
        manager1 = get_connection_manager()
        manager2 = get_connection_manager()

        assert manager1 is manager2

    def test_get_notification_service_creates_singleton(self):
        """Test that get_notification_service returns singleton."""
        service1 = get_notification_service()
        service2 = get_notification_service()

        assert service1 is service2

    def test_notification_service_uses_connection_manager(self):
        """Test that notification service uses the connection manager singleton."""
        manager = get_connection_manager()
        service = get_notification_service()

        assert service.manager is manager

    def test_reset_websocket_services(self):
        """Test resetting singletons."""
        manager1 = get_connection_manager()
        reset_websocket_services()
        manager2 = get_connection_manager()

        assert manager1 is not manager2


# ==================== Integration-like Tests ====================


class TestWebSocketIntegration:
    """Integration-like tests for WebSocket service."""

    @pytest.fixture
    def manager(self):
        """Create a fresh connection manager."""
        return ConnectionManager()

    @pytest.fixture
    def service(self, manager):
        """Create a notification service."""
        return NotificationService(manager)

    def create_mock_websocket(self):
        """Helper to create mock WebSockets."""
        ws = MagicMock()
        ws.accept = AsyncMock()
        ws.send_text = AsyncMock()
        ws.close = AsyncMock()
        return ws

    @pytest.mark.asyncio
    async def test_full_connection_lifecycle(self, manager, service):
        """Test complete connection lifecycle."""
        ws = self.create_mock_websocket()

        # Connect
        connection = await manager.connect(ws, connection_id="test-conn")
        assert manager.active_connections == 1

        # Subscribe to project
        await manager.subscribe_to_project("test-conn", "project-1")
        assert connection.is_subscribed_to("project-1")

        # Receive notification
        count = await service.notify_entity_created(
            project_id="project-1",
            entity_id="entity-1"
        )
        assert count == 1

        # Unsubscribe
        await manager.unsubscribe_from_project("test-conn", "project-1")
        assert not connection.is_subscribed_to("project-1")

        # No notification after unsubscribe
        count = await service.notify_entity_updated(
            project_id="project-1",
            entity_id="entity-1"
        )
        assert count == 0

        # Disconnect
        await manager.disconnect("test-conn")
        assert manager.active_connections == 0

    @pytest.mark.asyncio
    async def test_multiple_clients_scenario(self, manager, service):
        """Test scenario with multiple clients."""
        ws1 = self.create_mock_websocket()
        ws2 = self.create_mock_websocket()
        ws3 = self.create_mock_websocket()

        # Connect three clients
        await manager.connect(ws1, connection_id="client-1")
        await manager.connect(ws2, connection_id="client-2")
        await manager.connect(ws3, connection_id="client-3")

        # client-1 and client-2 subscribe to project-A
        await manager.subscribe_to_project("client-1", "project-A")
        await manager.subscribe_to_project("client-2", "project-A")

        # client-2 and client-3 subscribe to project-B
        await manager.subscribe_to_project("client-2", "project-B")
        await manager.subscribe_to_project("client-3", "project-B")

        # Notification to project-A should reach client-1 and client-2
        count_a = await service.notify_entity_created(
            project_id="project-A",
            entity_id="entity-1"
        )
        assert count_a == 2

        # Notification to project-B should reach client-2 and client-3
        count_b = await service.notify_entity_created(
            project_id="project-B",
            entity_id="entity-2"
        )
        assert count_b == 2

        # Broadcast to all should reach everyone
        count_all = await manager.broadcast(
            WebSocketMessage(type=NotificationType.PING)
        )
        assert count_all == 3

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, manager):
        """Test concurrent connection/disconnection operations."""
        async def connect_and_disconnect(i):
            ws = self.create_mock_websocket()
            conn = await manager.connect(ws, connection_id=f"conn-{i}")
            await manager.subscribe_to_project(f"conn-{i}", "shared-project")
            await asyncio.sleep(0.01)
            await manager.disconnect(f"conn-{i}")
            return True

        # Run 10 concurrent connect/disconnect cycles
        tasks = [connect_and_disconnect(i) for i in range(10)]
        results = await asyncio.gather(*tasks)

        assert all(results)
        assert manager.active_connections == 0

    @pytest.mark.asyncio
    async def test_message_serialization_roundtrip(self):
        """Test message serialization and deserialization."""
        original = WebSocketMessage(
            type=NotificationType.ENTITY_UPDATED,
            project_id="project-123",
            entity_id="entity-456",
            data={
                "changes": ["name", "email"],
                "old_values": {"name": "Old Name"},
                "new_values": {"name": "New Name"}
            }
        )

        # Serialize to JSON
        json_str = original.to_json()

        # Deserialize back
        restored = WebSocketMessage.from_json(json_str)

        assert restored.type == original.type
        assert restored.project_id == original.project_id
        assert restored.entity_id == original.entity_id
        assert restored.data == original.data
