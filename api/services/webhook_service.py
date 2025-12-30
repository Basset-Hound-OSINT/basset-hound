"""
Webhook Integration Service for Basset Hound OSINT Platform.

This module provides webhook functionality for sending notifications
to external URLs when events occur in the system.

Features:
- CRUD operations for webhook configurations
- HMAC-SHA256 signature for payload verification
- Retry logic with exponential backoff
- Delivery logging and status tracking
- Support for multiple event types

Usage:
    from api.services.webhook_service import (
        WebhookService,
        WebhookConfig,
        WebhookEvent,
        get_webhook_service,
    )

    service = get_webhook_service()

    # Create a webhook
    config = WebhookConfig(
        name="My Webhook",
        url="https://example.com/webhook",
        secret="my-secret-key",
        events=[WebhookEvent.ENTITY_CREATED, WebhookEvent.ENTITY_UPDATED],
    )
    webhook_id = await service.create_webhook(config)

    # Send a notification
    await service.send_event(
        WebhookEvent.ENTITY_CREATED,
        project_id="project-123",
        data={"entity_id": "entity-456", "name": "John Doe"}
    )
"""

import asyncio
import hashlib
import hmac
import json
import threading
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False


class WebhookEvent(str, Enum):
    """Types of events that can trigger webhooks."""
    # Entity events
    ENTITY_CREATED = "entity.created"
    ENTITY_UPDATED = "entity.updated"
    ENTITY_DELETED = "entity.deleted"

    # Relationship events
    RELATIONSHIP_CREATED = "relationship.created"
    RELATIONSHIP_UPDATED = "relationship.updated"
    RELATIONSHIP_DELETED = "relationship.deleted"

    # Search events
    SEARCH_EXECUTED = "search.executed"
    SAVED_SEARCH_EXECUTED = "saved_search.executed"

    # Report events
    REPORT_GENERATED = "report.generated"
    REPORT_SCHEDULED = "report.scheduled"

    # Import/Export events
    IMPORT_STARTED = "import.started"
    IMPORT_COMPLETED = "import.completed"
    IMPORT_FAILED = "import.failed"
    EXPORT_COMPLETED = "export.completed"

    # Project events
    PROJECT_CREATED = "project.created"
    PROJECT_DELETED = "project.deleted"

    # Orphan data events
    ORPHAN_CREATED = "orphan.created"
    ORPHAN_LINKED = "orphan.linked"

    # System events
    SYSTEM_HEALTH = "system.health"
    RATE_LIMIT_EXCEEDED = "rate_limit.exceeded"


class DeliveryStatus(str, Enum):
    """Status of webhook delivery."""
    PENDING = "pending"
    SENDING = "sending"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class RetryConfig:
    """
    Configuration for webhook retry behavior.

    Attributes:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds before first retry
        max_delay: Maximum delay between retries
        backoff_multiplier: Multiplier for exponential backoff
    """
    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0


@dataclass
class WebhookConfig:
    """
    Configuration for a webhook endpoint.

    Attributes:
        name: Display name for the webhook
        url: Target URL for webhook delivery
        secret: Secret key for HMAC signature (optional)
        events: List of events to subscribe to
        active: Whether the webhook is active
        headers: Additional headers to send
        retry_config: Retry behavior configuration
        project_id: Optional project filter (None = all projects)
    """
    name: str
    url: str
    secret: Optional[str] = None
    events: List[WebhookEvent] = field(default_factory=list)
    active: bool = True
    headers: Dict[str, str] = field(default_factory=dict)
    retry_config: RetryConfig = field(default_factory=RetryConfig)
    project_id: Optional[str] = None

    def __post_init__(self):
        """Validate configuration."""
        if not self.name or not self.name.strip():
            raise ValueError("Webhook name is required")
        if not self.url or not self.url.strip():
            raise ValueError("Webhook URL is required")
        if not self.url.startswith(("http://", "https://")):
            raise ValueError("Webhook URL must start with http:// or https://")


@dataclass
class Webhook:
    """
    A webhook with metadata.

    Attributes:
        id: Unique identifier
        config: Webhook configuration
        created_at: Creation timestamp
        updated_at: Last update timestamp
        last_triggered_at: Last successful trigger
        delivery_count: Total deliveries attempted
        success_count: Successful deliveries
        failure_count: Failed deliveries
    """
    id: str
    config: WebhookConfig
    created_at: datetime
    updated_at: datetime
    last_triggered_at: Optional[datetime] = None
    delivery_count: int = 0
    success_count: int = 0
    failure_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.config.name,
            "url": self.config.url,
            "events": [e.value for e in self.config.events],
            "active": self.config.active,
            "headers": self.config.headers,
            "project_id": self.config.project_id,
            "retry_config": {
                "max_retries": self.config.retry_config.max_retries,
                "initial_delay": self.config.retry_config.initial_delay,
                "max_delay": self.config.retry_config.max_delay,
            },
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_triggered_at": self.last_triggered_at.isoformat() if self.last_triggered_at else None,
            "delivery_count": self.delivery_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
        }


@dataclass
class WebhookDelivery:
    """
    Record of a webhook delivery attempt.

    Attributes:
        id: Unique delivery ID
        webhook_id: ID of the webhook
        event: Event type that triggered delivery
        payload: The payload that was sent
        status: Current delivery status
        attempts: Number of delivery attempts
        last_attempt_at: Time of last attempt
        next_retry_at: Scheduled time for next retry
        response_code: HTTP response code (if received)
        response_body: Response body (truncated)
        error_message: Error message if failed
    """
    id: str
    webhook_id: str
    event: WebhookEvent
    payload: Dict[str, Any]
    status: DeliveryStatus = DeliveryStatus.PENDING
    attempts: int = 0
    last_attempt_at: Optional[datetime] = None
    next_retry_at: Optional[datetime] = None
    response_code: Optional[int] = None
    response_body: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "webhook_id": self.webhook_id,
            "event": self.event.value,
            "payload": self.payload,
            "status": self.status.value,
            "attempts": self.attempts,
            "last_attempt_at": self.last_attempt_at.isoformat() if self.last_attempt_at else None,
            "next_retry_at": self.next_retry_at.isoformat() if self.next_retry_at else None,
            "response_code": self.response_code,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
        }


class WebhookService:
    """
    Service for managing webhooks and sending notifications.

    Provides CRUD operations for webhooks, event dispatching,
    and delivery tracking with retry logic.

    NOTE: This service includes rate limiting for OUTBOUND requests only.
    This protects external services from being overwhelmed by webhook
    deliveries. Basset Hound does not rate limit any internal API operations -
    the only limits are what the underlying hardware and database can support.
    """

    def __init__(
        self,
        max_deliveries: int = 1000,
        timeout: float = 30.0,
        max_requests_per_second: float = 10.0,
    ):
        """
        Initialize the webhook service.

        Args:
            max_deliveries: Maximum delivery records to keep (LRU)
            timeout: HTTP request timeout in seconds
            max_requests_per_second: Rate limit for outbound webhook requests
                                     (protects external services from spam)
        """
        self._lock = threading.RLock()
        self._webhooks: Dict[str, Webhook] = {}
        self._deliveries: OrderedDict[str, WebhookDelivery] = OrderedDict()
        self._max_deliveries = max_deliveries
        self._timeout = timeout
        self._max_rps = max_requests_per_second
        self._last_request_time = 0.0

        # Statistics
        self._stats = {
            "total_events": 0,
            "successful_deliveries": 0,
            "failed_deliveries": 0,
            "retried_deliveries": 0,
        }

    async def create_webhook(self, config: WebhookConfig) -> str:
        """
        Create a new webhook.

        Args:
            config: Webhook configuration

        Returns:
            ID of the created webhook
        """
        with self._lock:
            webhook_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)

            webhook = Webhook(
                id=webhook_id,
                config=config,
                created_at=now,
                updated_at=now,
            )

            self._webhooks[webhook_id] = webhook
            return webhook_id

    async def get_webhook(self, webhook_id: str) -> Optional[Webhook]:
        """Get a webhook by ID."""
        with self._lock:
            return self._webhooks.get(webhook_id)

    async def update_webhook(
        self,
        webhook_id: str,
        updates: Dict[str, Any]
    ) -> Optional[Webhook]:
        """
        Update a webhook configuration.

        Args:
            webhook_id: Webhook ID
            updates: Fields to update

        Returns:
            Updated webhook or None if not found
        """
        with self._lock:
            webhook = self._webhooks.get(webhook_id)
            if not webhook:
                return None

            config = webhook.config

            # Update config fields
            if "name" in updates:
                config.name = updates["name"]
            if "url" in updates:
                config.url = updates["url"]
            if "secret" in updates:
                config.secret = updates["secret"]
            if "events" in updates:
                config.events = [
                    WebhookEvent(e) if isinstance(e, str) else e
                    for e in updates["events"]
                ]
            if "active" in updates:
                config.active = updates["active"]
            if "headers" in updates:
                config.headers = updates["headers"]
            if "project_id" in updates:
                config.project_id = updates["project_id"]

            webhook.updated_at = datetime.now(timezone.utc)
            return webhook

    async def delete_webhook(self, webhook_id: str) -> bool:
        """Delete a webhook."""
        with self._lock:
            if webhook_id in self._webhooks:
                del self._webhooks[webhook_id]
                return True
            return False

    async def list_webhooks(
        self,
        project_id: Optional[str] = None,
        active_only: bool = False,
    ) -> List[Webhook]:
        """
        List webhooks with optional filtering.

        Args:
            project_id: Filter by project
            active_only: Only return active webhooks

        Returns:
            List of matching webhooks
        """
        with self._lock:
            webhooks = list(self._webhooks.values())

            if project_id:
                webhooks = [
                    w for w in webhooks
                    if w.config.project_id is None or w.config.project_id == project_id
                ]

            if active_only:
                webhooks = [w for w in webhooks if w.config.active]

            return webhooks

    async def send_event(
        self,
        event: WebhookEvent,
        project_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """
        Send an event to all subscribed webhooks.

        Args:
            event: Event type
            project_id: Project context for the event
            data: Event-specific data

        Returns:
            List of delivery IDs created
        """
        with self._lock:
            self._stats["total_events"] += 1

            # Find webhooks subscribed to this event
            webhooks = [
                w for w in self._webhooks.values()
                if w.config.active
                and event in w.config.events
                and (w.config.project_id is None or w.config.project_id == project_id)
            ]

        if not webhooks:
            return []

        # Create payload
        payload = {
            "event": event.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "project_id": project_id,
            "data": data or {},
        }

        # Send to each webhook
        delivery_ids = []
        for webhook in webhooks:
            delivery_id = await self._send_to_webhook(webhook, event, payload)
            delivery_ids.append(delivery_id)

        return delivery_ids

    async def _send_to_webhook(
        self,
        webhook: Webhook,
        event: WebhookEvent,
        payload: Dict[str, Any],
    ) -> str:
        """Send payload to a specific webhook."""
        delivery_id = str(uuid.uuid4())

        # Create delivery record
        delivery = WebhookDelivery(
            id=delivery_id,
            webhook_id=webhook.id,
            event=event,
            payload=payload,
        )

        with self._lock:
            # Add to deliveries (LRU eviction)
            while len(self._deliveries) >= self._max_deliveries:
                self._deliveries.popitem(last=False)
            self._deliveries[delivery_id] = delivery

        # Attempt delivery
        await self._attempt_delivery(webhook, delivery)

        return delivery_id

    async def _throttle_outbound(self) -> None:
        """
        Throttle outbound requests to avoid overwhelming external services.

        This is the ONLY rate limiting in Basset Hound - it protects
        external webhook endpoints from being spammed, not the user.
        """
        if self._max_rps <= 0:
            return

        min_interval = 1.0 / self._max_rps
        now = time.time()
        elapsed = now - self._last_request_time

        if elapsed < min_interval:
            await asyncio.sleep(min_interval - elapsed)

        self._last_request_time = time.time()

    async def _attempt_delivery(
        self,
        webhook: Webhook,
        delivery: WebhookDelivery,
    ) -> bool:
        """Attempt to deliver a webhook payload."""
        if not HTTPX_AVAILABLE:
            with self._lock:
                delivery.status = DeliveryStatus.FAILED
                delivery.error_message = "httpx library not available"
                self._stats["failed_deliveries"] += 1
            return False

        config = webhook.config
        retry_config = config.retry_config

        while delivery.attempts < retry_config.max_retries + 1:
            # Throttle outbound requests to protect external services
            await self._throttle_outbound()
            delivery.attempts += 1
            delivery.last_attempt_at = datetime.now(timezone.utc)
            delivery.status = DeliveryStatus.SENDING

            try:
                # Prepare payload
                payload_json = json.dumps(delivery.payload, default=str)

                # Calculate signature if secret is configured
                headers = dict(config.headers)
                headers["Content-Type"] = "application/json"

                if config.secret:
                    signature = hmac.new(
                        config.secret.encode(),
                        payload_json.encode(),
                        hashlib.sha256
                    ).hexdigest()
                    headers["X-Webhook-Signature"] = f"sha256={signature}"

                # Send request
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    response = await client.post(
                        config.url,
                        content=payload_json,
                        headers=headers,
                    )

                delivery.response_code = response.status_code
                delivery.response_body = response.text[:500] if response.text else None

                if 200 <= response.status_code < 300:
                    # Success
                    with self._lock:
                        delivery.status = DeliveryStatus.SUCCESS
                        webhook.last_triggered_at = datetime.now(timezone.utc)
                        webhook.delivery_count += 1
                        webhook.success_count += 1
                        self._stats["successful_deliveries"] += 1
                    return True

                # Non-2xx response - retry
                delivery.error_message = f"HTTP {response.status_code}"

            except httpx.TimeoutException:
                delivery.error_message = "Request timeout"
            except httpx.RequestError as e:
                delivery.error_message = f"Request error: {str(e)}"
            except Exception as e:
                delivery.error_message = f"Unexpected error: {str(e)}"

            # Check if we should retry
            if delivery.attempts <= retry_config.max_retries:
                delivery.status = DeliveryStatus.RETRYING
                with self._lock:
                    self._stats["retried_deliveries"] += 1

                # Calculate backoff delay
                delay = min(
                    retry_config.initial_delay * (
                        retry_config.backoff_multiplier ** (delivery.attempts - 1)
                    ),
                    retry_config.max_delay
                )
                delivery.next_retry_at = datetime.now(timezone.utc)

                await asyncio.sleep(delay)
            else:
                # Max retries exceeded
                with self._lock:
                    delivery.status = DeliveryStatus.FAILED
                    webhook.delivery_count += 1
                    webhook.failure_count += 1
                    self._stats["failed_deliveries"] += 1
                return False

        return False

    async def get_delivery(self, delivery_id: str) -> Optional[WebhookDelivery]:
        """Get a delivery record by ID."""
        with self._lock:
            return self._deliveries.get(delivery_id)

    async def list_deliveries(
        self,
        webhook_id: Optional[str] = None,
        status: Optional[DeliveryStatus] = None,
        limit: int = 50,
    ) -> List[WebhookDelivery]:
        """
        List delivery records with optional filtering.

        Args:
            webhook_id: Filter by webhook
            status: Filter by status
            limit: Maximum records to return

        Returns:
            List of delivery records
        """
        with self._lock:
            deliveries = list(self._deliveries.values())

            if webhook_id:
                deliveries = [d for d in deliveries if d.webhook_id == webhook_id]

            if status:
                deliveries = [d for d in deliveries if d.status == status]

            # Sort by created_at descending
            deliveries.sort(key=lambda d: d.created_at, reverse=True)

            return deliveries[:limit]

    async def retry_delivery(self, delivery_id: str) -> bool:
        """
        Manually retry a failed delivery.

        Args:
            delivery_id: Delivery ID to retry

        Returns:
            True if retry was initiated
        """
        with self._lock:
            delivery = self._deliveries.get(delivery_id)
            if not delivery:
                return False

            if delivery.status not in (DeliveryStatus.FAILED, DeliveryStatus.RETRYING):
                return False

            webhook = self._webhooks.get(delivery.webhook_id)
            if not webhook:
                return False

        # Reset delivery state
        delivery.status = DeliveryStatus.PENDING
        delivery.attempts = 0
        delivery.error_message = None

        # Attempt delivery
        await self._attempt_delivery(webhook, delivery)
        return True

    async def test_webhook(self, webhook_id: str) -> Optional[WebhookDelivery]:
        """
        Send a test event to a webhook.

        Args:
            webhook_id: Webhook ID to test

        Returns:
            Delivery record for the test
        """
        with self._lock:
            webhook = self._webhooks.get(webhook_id)
            if not webhook:
                return None

        payload = {
            "event": "test",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": "This is a test webhook delivery from Basset Hound",
        }

        delivery_id = await self._send_to_webhook(
            webhook,
            WebhookEvent.SYSTEM_HEALTH,
            payload
        )

        return await self.get_delivery(delivery_id)

    def get_stats(self) -> Dict[str, Any]:
        """Get webhook service statistics."""
        with self._lock:
            return {
                **self._stats,
                "active_webhooks": sum(
                    1 for w in self._webhooks.values() if w.config.active
                ),
                "total_webhooks": len(self._webhooks),
                "pending_deliveries": sum(
                    1 for d in self._deliveries.values()
                    if d.status in (DeliveryStatus.PENDING, DeliveryStatus.RETRYING)
                ),
            }

    def clear(self) -> Tuple[int, int]:
        """
        Clear all webhooks and deliveries.

        Returns:
            Tuple of (webhooks cleared, deliveries cleared)
        """
        with self._lock:
            webhooks_count = len(self._webhooks)
            deliveries_count = len(self._deliveries)
            self._webhooks.clear()
            self._deliveries.clear()
            return webhooks_count, deliveries_count


# Module-level singleton
_webhook_service: Optional[WebhookService] = None


def get_webhook_service(
    max_deliveries: int = 1000,
    timeout: float = 30.0,
) -> WebhookService:
    """
    Get or create the WebhookService singleton.

    Args:
        max_deliveries: Maximum delivery records to keep
        timeout: HTTP request timeout

    Returns:
        WebhookService instance
    """
    global _webhook_service

    if _webhook_service is None:
        _webhook_service = WebhookService(max_deliveries, timeout)

    return _webhook_service


def set_webhook_service(service: Optional[WebhookService]) -> None:
    """Set the global WebhookService instance."""
    global _webhook_service
    _webhook_service = service


def reset_webhook_service() -> None:
    """Reset the singleton instance."""
    global _webhook_service
    _webhook_service = None
