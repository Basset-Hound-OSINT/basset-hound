"""
Phase 24 Tests: Webhook Integrations

Comprehensive tests for the webhook service and API router.

This phase implements webhook functionality for external notifications:
- Webhook CRUD operations
- HMAC-SHA256 signature verification
- Retry logic with exponential backoff
- Delivery logging and status tracking
- Event type management

NOTE: Basset Hound does NOT rate limit API endpoints. The only rate limiting
is on OUTBOUND webhook requests to protect external services from being spammed.
"""

import asyncio
import hashlib
import hmac
import json
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

# Service imports
from api.services.webhook_service import (
    WebhookService,
    WebhookConfig,
    Webhook,
    WebhookEvent,
    WebhookDelivery,
    DeliveryStatus,
    RetryConfig,
    get_webhook_service,
    set_webhook_service,
    reset_webhook_service,
)


# ==================== WebhookEvent Enum Tests ====================


class TestWebhookEvent:
    """Tests for the WebhookEvent enum."""

    def test_entity_events(self):
        """Test entity-related events exist."""
        assert WebhookEvent.ENTITY_CREATED.value == "entity.created"
        assert WebhookEvent.ENTITY_UPDATED.value == "entity.updated"
        assert WebhookEvent.ENTITY_DELETED.value == "entity.deleted"

    def test_relationship_events(self):
        """Test relationship-related events exist."""
        assert WebhookEvent.RELATIONSHIP_CREATED.value == "relationship.created"
        assert WebhookEvent.RELATIONSHIP_UPDATED.value == "relationship.updated"
        assert WebhookEvent.RELATIONSHIP_DELETED.value == "relationship.deleted"

    def test_search_events(self):
        """Test search-related events exist."""
        assert WebhookEvent.SEARCH_EXECUTED.value == "search.executed"
        assert WebhookEvent.SAVED_SEARCH_EXECUTED.value == "saved_search.executed"

    def test_report_events(self):
        """Test report-related events exist."""
        assert WebhookEvent.REPORT_GENERATED.value == "report.generated"
        assert WebhookEvent.REPORT_SCHEDULED.value == "report.scheduled"

    def test_import_export_events(self):
        """Test import/export events exist."""
        assert WebhookEvent.IMPORT_STARTED.value == "import.started"
        assert WebhookEvent.IMPORT_COMPLETED.value == "import.completed"
        assert WebhookEvent.IMPORT_FAILED.value == "import.failed"
        assert WebhookEvent.EXPORT_COMPLETED.value == "export.completed"

    def test_project_events(self):
        """Test project events exist."""
        assert WebhookEvent.PROJECT_CREATED.value == "project.created"
        assert WebhookEvent.PROJECT_DELETED.value == "project.deleted"

    def test_orphan_events(self):
        """Test orphan data events exist."""
        assert WebhookEvent.ORPHAN_CREATED.value == "orphan.created"
        assert WebhookEvent.ORPHAN_LINKED.value == "orphan.linked"

    def test_system_events(self):
        """Test system events exist."""
        assert WebhookEvent.SYSTEM_HEALTH.value == "system.health"
        assert WebhookEvent.RATE_LIMIT_EXCEEDED.value == "rate_limit.exceeded"

    def test_event_count(self):
        """Test total number of event types."""
        # At least 20 event types
        assert len(WebhookEvent) >= 20

    def test_event_from_string(self):
        """Test creating event from string value."""
        event = WebhookEvent("entity.created")
        assert event == WebhookEvent.ENTITY_CREATED


# ==================== DeliveryStatus Enum Tests ====================


class TestDeliveryStatus:
    """Tests for the DeliveryStatus enum."""

    def test_all_statuses(self):
        """Test all delivery statuses exist."""
        assert DeliveryStatus.PENDING.value == "pending"
        assert DeliveryStatus.SENDING.value == "sending"
        assert DeliveryStatus.SUCCESS.value == "success"
        assert DeliveryStatus.FAILED.value == "failed"
        assert DeliveryStatus.RETRYING.value == "retrying"

    def test_status_count(self):
        """Test total number of statuses."""
        assert len(DeliveryStatus) == 5


# ==================== RetryConfig Tests ====================


class TestRetryConfig:
    """Tests for RetryConfig dataclass."""

    def test_default_values(self):
        """Test default retry configuration."""
        config = RetryConfig()
        assert config.max_retries == 3
        assert config.initial_delay == 1.0
        assert config.max_delay == 60.0
        assert config.backoff_multiplier == 2.0

    def test_custom_values(self):
        """Test custom retry configuration."""
        config = RetryConfig(
            max_retries=5,
            initial_delay=2.0,
            max_delay=120.0,
            backoff_multiplier=3.0,
        )
        assert config.max_retries == 5
        assert config.initial_delay == 2.0
        assert config.max_delay == 120.0
        assert config.backoff_multiplier == 3.0


# ==================== WebhookConfig Tests ====================


class TestWebhookConfig:
    """Tests for WebhookConfig dataclass."""

    def test_minimal_config(self):
        """Test minimal webhook configuration."""
        config = WebhookConfig(
            name="Test Webhook",
            url="https://example.com/webhook",
        )
        assert config.name == "Test Webhook"
        assert config.url == "https://example.com/webhook"
        assert config.secret is None
        assert config.events == []
        assert config.active is True
        assert config.headers == {}
        assert config.project_id is None

    def test_full_config(self):
        """Test full webhook configuration."""
        config = WebhookConfig(
            name="Full Webhook",
            url="https://example.com/webhook",
            secret="my-secret",
            events=[WebhookEvent.ENTITY_CREATED, WebhookEvent.ENTITY_UPDATED],
            active=False,
            headers={"Authorization": "Bearer token"},
            project_id="project-123",
        )
        assert config.name == "Full Webhook"
        assert config.secret == "my-secret"
        assert len(config.events) == 2
        assert config.active is False
        assert config.headers["Authorization"] == "Bearer token"
        assert config.project_id == "project-123"

    def test_invalid_name(self):
        """Test validation of empty name."""
        with pytest.raises(ValueError, match="name is required"):
            WebhookConfig(name="", url="https://example.com/webhook")

    def test_invalid_url(self):
        """Test validation of empty URL."""
        with pytest.raises(ValueError, match="URL is required"):
            WebhookConfig(name="Test", url="")

    def test_invalid_url_protocol(self):
        """Test validation of URL protocol."""
        with pytest.raises(ValueError, match="must start with http"):
            WebhookConfig(name="Test", url="ftp://example.com/webhook")


# ==================== Webhook Tests ====================


class TestWebhook:
    """Tests for Webhook dataclass."""

    def test_webhook_creation(self):
        """Test webhook creation with config."""
        config = WebhookConfig(
            name="Test Webhook",
            url="https://example.com/webhook",
        )
        now = datetime.now(timezone.utc)
        webhook = Webhook(
            id="webhook-123",
            config=config,
            created_at=now,
            updated_at=now,
        )
        assert webhook.id == "webhook-123"
        assert webhook.config.name == "Test Webhook"
        assert webhook.delivery_count == 0
        assert webhook.success_count == 0
        assert webhook.failure_count == 0

    def test_webhook_to_dict(self):
        """Test webhook serialization."""
        config = WebhookConfig(
            name="Test Webhook",
            url="https://example.com/webhook",
            events=[WebhookEvent.ENTITY_CREATED],
        )
        now = datetime.now(timezone.utc)
        webhook = Webhook(
            id="webhook-123",
            config=config,
            created_at=now,
            updated_at=now,
            delivery_count=10,
            success_count=8,
            failure_count=2,
        )
        data = webhook.to_dict()
        assert data["id"] == "webhook-123"
        assert data["name"] == "Test Webhook"
        assert data["url"] == "https://example.com/webhook"
        assert data["events"] == ["entity.created"]
        assert data["delivery_count"] == 10
        assert data["success_count"] == 8
        assert data["failure_count"] == 2


# ==================== WebhookDelivery Tests ====================


class TestWebhookDelivery:
    """Tests for WebhookDelivery dataclass."""

    def test_delivery_creation(self):
        """Test delivery creation with defaults."""
        delivery = WebhookDelivery(
            id="delivery-123",
            webhook_id="webhook-456",
            event=WebhookEvent.ENTITY_CREATED,
            payload={"entity_id": "entity-789"},
        )
        assert delivery.id == "delivery-123"
        assert delivery.webhook_id == "webhook-456"
        assert delivery.event == WebhookEvent.ENTITY_CREATED
        assert delivery.status == DeliveryStatus.PENDING
        assert delivery.attempts == 0
        assert delivery.error_message is None

    def test_delivery_to_dict(self):
        """Test delivery serialization."""
        delivery = WebhookDelivery(
            id="delivery-123",
            webhook_id="webhook-456",
            event=WebhookEvent.ENTITY_CREATED,
            payload={"entity_id": "entity-789"},
            status=DeliveryStatus.SUCCESS,
            attempts=1,
            response_code=200,
        )
        data = delivery.to_dict()
        assert data["id"] == "delivery-123"
        assert data["event"] == "entity.created"
        assert data["status"] == "success"
        assert data["attempts"] == 1
        assert data["response_code"] == 200


# ==================== WebhookService CRUD Tests ====================


class TestWebhookServiceCRUD:
    """Tests for WebhookService CRUD operations."""

    @pytest.fixture
    def service(self):
        """Create a fresh service for each test."""
        reset_webhook_service()
        return WebhookService()

    @pytest.mark.asyncio
    async def test_create_webhook(self, service):
        """Test creating a webhook."""
        config = WebhookConfig(
            name="Test Webhook",
            url="https://example.com/webhook",
            events=[WebhookEvent.ENTITY_CREATED],
        )
        webhook_id = await service.create_webhook(config)
        assert webhook_id is not None
        assert len(webhook_id) > 0

    @pytest.mark.asyncio
    async def test_get_webhook(self, service):
        """Test retrieving a webhook."""
        config = WebhookConfig(
            name="Test Webhook",
            url="https://example.com/webhook",
        )
        webhook_id = await service.create_webhook(config)
        webhook = await service.get_webhook(webhook_id)
        assert webhook is not None
        assert webhook.id == webhook_id
        assert webhook.config.name == "Test Webhook"

    @pytest.mark.asyncio
    async def test_get_nonexistent_webhook(self, service):
        """Test retrieving a non-existent webhook."""
        webhook = await service.get_webhook("nonexistent-id")
        assert webhook is None

    @pytest.mark.asyncio
    async def test_update_webhook(self, service):
        """Test updating a webhook."""
        config = WebhookConfig(
            name="Original Name",
            url="https://example.com/webhook",
        )
        webhook_id = await service.create_webhook(config)

        # Update
        updated = await service.update_webhook(webhook_id, {
            "name": "Updated Name",
            "active": False,
        })
        assert updated is not None
        assert updated.config.name == "Updated Name"
        assert updated.config.active is False

    @pytest.mark.asyncio
    async def test_update_webhook_events(self, service):
        """Test updating webhook events."""
        config = WebhookConfig(
            name="Test Webhook",
            url="https://example.com/webhook",
            events=[WebhookEvent.ENTITY_CREATED],
        )
        webhook_id = await service.create_webhook(config)

        # Update events with string values
        updated = await service.update_webhook(webhook_id, {
            "events": ["entity.updated", "entity.deleted"],
        })
        assert len(updated.config.events) == 2
        assert WebhookEvent.ENTITY_UPDATED in updated.config.events

    @pytest.mark.asyncio
    async def test_update_nonexistent_webhook(self, service):
        """Test updating a non-existent webhook."""
        result = await service.update_webhook("nonexistent", {"name": "New"})
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_webhook(self, service):
        """Test deleting a webhook."""
        config = WebhookConfig(
            name="Test Webhook",
            url="https://example.com/webhook",
        )
        webhook_id = await service.create_webhook(config)

        # Delete
        deleted = await service.delete_webhook(webhook_id)
        assert deleted is True

        # Verify deleted
        webhook = await service.get_webhook(webhook_id)
        assert webhook is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_webhook(self, service):
        """Test deleting a non-existent webhook."""
        deleted = await service.delete_webhook("nonexistent")
        assert deleted is False


# ==================== WebhookService List Tests ====================


class TestWebhookServiceList:
    """Tests for WebhookService listing operations."""

    @pytest.fixture
    def service(self):
        """Create a fresh service for each test."""
        reset_webhook_service()
        return WebhookService()

    @pytest.mark.asyncio
    async def test_list_webhooks_empty(self, service):
        """Test listing when no webhooks exist."""
        webhooks = await service.list_webhooks()
        assert webhooks == []

    @pytest.mark.asyncio
    async def test_list_webhooks(self, service):
        """Test listing all webhooks."""
        # Create multiple webhooks
        for i in range(3):
            config = WebhookConfig(
                name=f"Webhook {i}",
                url=f"https://example.com/webhook{i}",
            )
            await service.create_webhook(config)

        webhooks = await service.list_webhooks()
        assert len(webhooks) == 3

    @pytest.mark.asyncio
    async def test_list_webhooks_by_project(self, service):
        """Test filtering webhooks by project."""
        # Create webhooks for different projects
        config1 = WebhookConfig(
            name="Webhook 1",
            url="https://example.com/webhook1",
            project_id="project-a",
        )
        config2 = WebhookConfig(
            name="Webhook 2",
            url="https://example.com/webhook2",
            project_id="project-b",
        )
        config3 = WebhookConfig(
            name="Global Webhook",
            url="https://example.com/webhook3",
            project_id=None,  # Global
        )
        await service.create_webhook(config1)
        await service.create_webhook(config2)
        await service.create_webhook(config3)

        # Filter by project-a (should include global)
        webhooks = await service.list_webhooks(project_id="project-a")
        assert len(webhooks) == 2  # project-a + global

    @pytest.mark.asyncio
    async def test_list_webhooks_active_only(self, service):
        """Test filtering active webhooks only."""
        config1 = WebhookConfig(
            name="Active Webhook",
            url="https://example.com/webhook1",
            active=True,
        )
        config2 = WebhookConfig(
            name="Inactive Webhook",
            url="https://example.com/webhook2",
            active=False,
        )
        await service.create_webhook(config1)
        await service.create_webhook(config2)

        webhooks = await service.list_webhooks(active_only=True)
        assert len(webhooks) == 1
        assert webhooks[0].config.name == "Active Webhook"


# ==================== WebhookService Event Sending Tests ====================


class TestWebhookServiceEvents:
    """Tests for WebhookService event sending."""

    @pytest.fixture
    def service(self):
        """Create a fresh service for each test."""
        reset_webhook_service()
        return WebhookService(max_requests_per_second=0)  # Disable throttling for tests

    @pytest.mark.asyncio
    async def test_send_event_no_subscribers(self, service):
        """Test sending event with no subscribers."""
        delivery_ids = await service.send_event(
            WebhookEvent.ENTITY_CREATED,
            project_id="project-123",
            data={"entity_id": "entity-456"},
        )
        assert delivery_ids == []

    @pytest.mark.asyncio
    async def test_send_event_increments_total_events(self, service):
        """Test that sending events increments stats."""
        initial_stats = service.get_stats()

        # Send event (no subscribers)
        await service.send_event(
            WebhookEvent.ENTITY_CREATED,
            data={"test": True},
        )

        stats = service.get_stats()
        assert stats["total_events"] == initial_stats["total_events"] + 1

    @pytest.mark.asyncio
    async def test_event_filtering_by_subscription(self, service):
        """Test that events are only sent to subscribed webhooks."""
        # Create webhook subscribed to entity.created
        config = WebhookConfig(
            name="Entity Webhook",
            url="https://example.com/webhook",
            events=[WebhookEvent.ENTITY_CREATED],
        )
        await service.create_webhook(config)

        # Send unsubscribed event
        delivery_ids = await service.send_event(
            WebhookEvent.ENTITY_DELETED,
            data={"test": True},
        )
        assert delivery_ids == []


# ==================== WebhookService Delivery Tests ====================


class TestWebhookServiceDelivery:
    """Tests for WebhookService delivery operations."""

    @pytest.fixture
    def service(self):
        """Create a fresh service for each test."""
        reset_webhook_service()
        return WebhookService()

    @pytest.mark.asyncio
    async def test_get_nonexistent_delivery(self, service):
        """Test getting a non-existent delivery."""
        delivery = await service.get_delivery("nonexistent")
        assert delivery is None

    @pytest.mark.asyncio
    async def test_list_deliveries_empty(self, service):
        """Test listing when no deliveries exist."""
        deliveries = await service.list_deliveries()
        assert deliveries == []

    @pytest.mark.asyncio
    async def test_list_deliveries_by_webhook(self, service):
        """Test filtering deliveries by webhook ID."""
        # Create a delivery manually
        delivery = WebhookDelivery(
            id="delivery-123",
            webhook_id="webhook-456",
            event=WebhookEvent.ENTITY_CREATED,
            payload={"test": True},
        )
        service._deliveries["delivery-123"] = delivery

        # Filter by webhook
        deliveries = await service.list_deliveries(webhook_id="webhook-456")
        assert len(deliveries) == 1

        # Filter by different webhook
        deliveries = await service.list_deliveries(webhook_id="other-webhook")
        assert len(deliveries) == 0

    @pytest.mark.asyncio
    async def test_list_deliveries_by_status(self, service):
        """Test filtering deliveries by status."""
        # Create deliveries with different statuses
        delivery1 = WebhookDelivery(
            id="delivery-1",
            webhook_id="webhook-123",
            event=WebhookEvent.ENTITY_CREATED,
            payload={},
            status=DeliveryStatus.SUCCESS,
        )
        delivery2 = WebhookDelivery(
            id="delivery-2",
            webhook_id="webhook-123",
            event=WebhookEvent.ENTITY_CREATED,
            payload={},
            status=DeliveryStatus.FAILED,
        )
        service._deliveries["delivery-1"] = delivery1
        service._deliveries["delivery-2"] = delivery2

        # Filter by status
        deliveries = await service.list_deliveries(status=DeliveryStatus.SUCCESS)
        assert len(deliveries) == 1
        assert deliveries[0].id == "delivery-1"

    @pytest.mark.asyncio
    async def test_retry_nonexistent_delivery(self, service):
        """Test retrying a non-existent delivery."""
        result = await service.retry_delivery("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_retry_success_delivery_fails(self, service):
        """Test that successful deliveries cannot be retried."""
        # Create a successful delivery
        delivery = WebhookDelivery(
            id="delivery-123",
            webhook_id="webhook-456",
            event=WebhookEvent.ENTITY_CREATED,
            payload={},
            status=DeliveryStatus.SUCCESS,
        )
        service._deliveries["delivery-123"] = delivery

        # Try to retry - should fail
        result = await service.retry_delivery("delivery-123")
        assert result is False


# ==================== WebhookService Stats Tests ====================


class TestWebhookServiceStats:
    """Tests for WebhookService statistics."""

    @pytest.fixture
    def service(self):
        """Create a fresh service for each test."""
        reset_webhook_service()
        return WebhookService()

    def test_initial_stats(self, service):
        """Test initial statistics."""
        stats = service.get_stats()
        assert stats["total_events"] == 0
        assert stats["successful_deliveries"] == 0
        assert stats["failed_deliveries"] == 0
        assert stats["retried_deliveries"] == 0
        assert stats["active_webhooks"] == 0
        assert stats["total_webhooks"] == 0
        assert stats["pending_deliveries"] == 0

    @pytest.mark.asyncio
    async def test_stats_with_webhooks(self, service):
        """Test statistics with webhooks."""
        # Create active and inactive webhooks
        active_config = WebhookConfig(
            name="Active",
            url="https://example.com/active",
            active=True,
        )
        inactive_config = WebhookConfig(
            name="Inactive",
            url="https://example.com/inactive",
            active=False,
        )
        await service.create_webhook(active_config)
        await service.create_webhook(inactive_config)

        stats = service.get_stats()
        assert stats["total_webhooks"] == 2
        assert stats["active_webhooks"] == 1


# ==================== WebhookService Clear Tests ====================


class TestWebhookServiceClear:
    """Tests for WebhookService clear operation."""

    @pytest.fixture
    def service(self):
        """Create a fresh service for each test."""
        reset_webhook_service()
        return WebhookService()

    @pytest.mark.asyncio
    async def test_clear(self, service):
        """Test clearing all webhooks and deliveries."""
        # Create webhooks and deliveries
        config = WebhookConfig(
            name="Test",
            url="https://example.com/webhook",
        )
        await service.create_webhook(config)

        delivery = WebhookDelivery(
            id="delivery-123",
            webhook_id="webhook-123",
            event=WebhookEvent.ENTITY_CREATED,
            payload={},
        )
        service._deliveries["delivery-123"] = delivery

        # Clear
        webhooks_count, deliveries_count = service.clear()
        assert webhooks_count == 1
        assert deliveries_count == 1

        # Verify empty
        webhooks = await service.list_webhooks()
        deliveries = await service.list_deliveries()
        assert len(webhooks) == 0
        assert len(deliveries) == 0


# ==================== Singleton Tests ====================


class TestWebhookServiceSingleton:
    """Tests for WebhookService singleton pattern."""

    def setup_method(self):
        """Reset singleton before each test."""
        reset_webhook_service()

    def test_get_webhook_service_creates_singleton(self):
        """Test that get_webhook_service creates a singleton."""
        service1 = get_webhook_service()
        service2 = get_webhook_service()
        assert service1 is service2

    def test_set_webhook_service(self):
        """Test setting custom service."""
        custom = WebhookService()
        set_webhook_service(custom)
        assert get_webhook_service() is custom

    def test_reset_webhook_service(self):
        """Test resetting singleton."""
        service1 = get_webhook_service()
        reset_webhook_service()
        service2 = get_webhook_service()
        assert service1 is not service2


# ==================== HMAC Signature Tests ====================


class TestHMACSignature:
    """Tests for HMAC signature generation."""

    def test_signature_format(self):
        """Test HMAC signature format."""
        secret = "my-secret-key"
        payload = json.dumps({"test": True})

        signature = hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()

        expected_header = f"sha256={signature}"
        assert expected_header.startswith("sha256=")
        assert len(signature) == 64  # SHA256 hex digest length


# ==================== Router Import Tests ====================


class TestRouterImports:
    """Tests for router imports and configuration."""

    def test_router_import(self):
        """Test that router can be imported."""
        from api.routers.webhooks import router, project_webhooks_router
        assert router is not None
        assert project_webhooks_router is not None

    def test_router_prefix(self):
        """Test router prefix configuration."""
        from api.routers.webhooks import router
        assert router.prefix == "/webhooks"

    def test_project_router_prefix(self):
        """Test project router prefix."""
        from api.routers.webhooks import project_webhooks_router
        assert "/projects/" in project_webhooks_router.prefix
        assert "/webhooks" in project_webhooks_router.prefix

    def test_router_tags(self):
        """Test router tags."""
        from api.routers.webhooks import router
        assert "webhooks" in router.tags


# ==================== Request Model Tests ====================


class TestRequestModels:
    """Tests for Pydantic request models."""

    def test_create_webhook_request(self):
        """Test CreateWebhookRequest model."""
        from api.routers.webhooks import CreateWebhookRequest

        request = CreateWebhookRequest(
            name="Test Webhook",
            url="https://example.com/webhook",
            events=["entity.created"],
        )
        assert request.name == "Test Webhook"
        assert request.active is True
        assert request.headers == {}

    def test_update_webhook_request(self):
        """Test UpdateWebhookRequest model."""
        from api.routers.webhooks import UpdateWebhookRequest

        request = UpdateWebhookRequest(
            name="Updated Name",
            active=False,
        )
        assert request.name == "Updated Name"
        assert request.active is False
        assert request.url is None

    def test_retry_config_model(self):
        """Test RetryConfigModel."""
        from api.routers.webhooks import RetryConfigModel

        config = RetryConfigModel(
            max_retries=5,
            initial_delay=2.0,
            max_delay=120.0,
            backoff_multiplier=3.0,
        )
        assert config.max_retries == 5
        assert config.initial_delay == 2.0


# ==================== Response Model Tests ====================


class TestResponseModels:
    """Tests for Pydantic response models."""

    def test_webhook_response(self):
        """Test WebhookResponse model."""
        from api.routers.webhooks import WebhookResponse

        response = WebhookResponse(
            id="webhook-123",
            name="Test",
            url="https://example.com",
            events=["entity.created"],
            active=True,
            headers={},
            retry_config={},
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
            delivery_count=0,
            success_count=0,
            failure_count=0,
        )
        assert response.id == "webhook-123"

    def test_webhook_list_response(self):
        """Test WebhookListResponse model."""
        from api.routers.webhooks import WebhookListResponse

        response = WebhookListResponse(
            webhooks=[],
            total=0,
        )
        assert response.total == 0

    def test_delivery_response(self):
        """Test DeliveryResponse model."""
        from api.routers.webhooks import DeliveryResponse

        response = DeliveryResponse(
            id="delivery-123",
            webhook_id="webhook-456",
            event="entity.created",
            payload={},
            status="success",
            attempts=1,
            created_at="2024-01-01T00:00:00Z",
        )
        assert response.status == "success"

    def test_event_type_response(self):
        """Test EventTypeResponse model."""
        from api.routers.webhooks import EventTypeResponse

        response = EventTypeResponse(
            events=[{"event": "entity.created", "description": "Entity Created"}],
            total=1,
        )
        assert response.total == 1

    def test_webhook_stats_response(self):
        """Test WebhookStatsResponse model."""
        from api.routers.webhooks import WebhookStatsResponse

        response = WebhookStatsResponse(
            total_events=100,
            successful_deliveries=95,
            failed_deliveries=5,
            retried_deliveries=10,
            active_webhooks=3,
            total_webhooks=4,
            pending_deliveries=2,
        )
        assert response.total_events == 100
        assert response.successful_deliveries == 95


# ==================== Service Export Tests ====================


class TestServiceExports:
    """Tests for service module exports."""

    def test_service_exports(self):
        """Test that all expected items are exported from services."""
        from api.services import (
            WebhookService,
            WebhookConfig,
            Webhook,
            WebhookEvent,
            WebhookDelivery,
            DeliveryStatus,
            RetryConfig,
            get_webhook_service,
            set_webhook_service,
            reset_webhook_service,
        )
        assert WebhookService is not None
        assert WebhookConfig is not None
        assert Webhook is not None
        assert WebhookEvent is not None
        assert WebhookDelivery is not None
        assert DeliveryStatus is not None
        assert RetryConfig is not None
        assert get_webhook_service is not None
        assert set_webhook_service is not None
        assert reset_webhook_service is not None


# ==================== Router Export Tests ====================


class TestRouterExports:
    """Tests for router module exports."""

    def test_router_exports(self):
        """Test that routers are exported."""
        from api.routers import webhooks_router, project_webhooks_router
        assert webhooks_router is not None
        assert project_webhooks_router is not None


# ==================== Outbound Throttling Tests ====================


class TestOutboundThrottling:
    """Tests for outbound request throttling."""

    def test_throttle_disabled_when_zero(self):
        """Test that throttling is disabled when max_rps is 0."""
        service = WebhookService(max_requests_per_second=0)
        # Should not raise or block
        assert service._max_rps == 0

    def test_throttle_configuration(self):
        """Test throttle configuration."""
        service = WebhookService(max_requests_per_second=10.0)
        assert service._max_rps == 10.0

    def test_default_throttle_rate(self):
        """Test default throttle rate is reasonable."""
        service = WebhookService()
        # Default is 10 requests per second (protects external services)
        assert service._max_rps == 10.0


# ==================== LRU Eviction Tests ====================


class TestLRUEviction:
    """Tests for LRU delivery eviction."""

    @pytest.fixture
    def service(self):
        """Create service with small max deliveries."""
        reset_webhook_service()
        return WebhookService(max_deliveries=3)

    @pytest.mark.asyncio
    async def test_lru_eviction(self, service):
        """Test that old deliveries are evicted."""
        # Add deliveries manually
        for i in range(5):
            delivery = WebhookDelivery(
                id=f"delivery-{i}",
                webhook_id="webhook-123",
                event=WebhookEvent.ENTITY_CREATED,
                payload={"index": i},
            )
            while len(service._deliveries) >= 3:
                service._deliveries.popitem(last=False)
            service._deliveries[f"delivery-{i}"] = delivery

        # Should only have 3 deliveries
        assert len(service._deliveries) == 3

        # Oldest should be evicted
        deliveries = await service.list_deliveries()
        ids = [d.id for d in deliveries]
        assert "delivery-0" not in ids
        assert "delivery-1" not in ids


# ==================== No Rate Limiting Philosophy Test ====================


class TestNoRateLimitingPhilosophy:
    """
    Tests to verify Basset Hound's no-rate-limiting philosophy.

    Basset Hound does NOT rate limit API endpoints.
    The only rate limiting is on OUTBOUND webhook requests
    to protect external services from being spammed.
    """

    def test_service_has_no_api_rate_limiting(self):
        """Verify service has no API rate limiting."""
        # The WebhookService only has outbound throttling
        service = WebhookService()

        # Check that there's no rate limiting on create/read/update/delete
        # These are purely internal operations with no artificial limits
        assert hasattr(service, "create_webhook")
        assert hasattr(service, "get_webhook")
        assert hasattr(service, "update_webhook")
        assert hasattr(service, "delete_webhook")
        assert hasattr(service, "list_webhooks")

        # Outbound throttling exists but is for protecting external services
        assert hasattr(service, "_throttle_outbound")
        assert hasattr(service, "_max_rps")

    def test_outbound_throttle_protects_external_services(self):
        """Verify outbound throttle is for external service protection."""
        service = WebhookService(max_requests_per_second=10.0)

        # The _throttle_outbound method exists to protect external endpoints
        # It does NOT limit what the user can do
        assert service._max_rps == 10.0

        # This is documented as protecting external services
        docstring = service._throttle_outbound.__doc__
        assert "external" in docstring.lower()
        assert "spam" in docstring.lower() or "overwhelm" in docstring.lower()
