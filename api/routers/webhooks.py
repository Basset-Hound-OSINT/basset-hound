"""
Webhook Router for Basset Hound OSINT Platform.

Provides RESTful API endpoints for managing webhooks and viewing deliveries.

Endpoints:
- POST /api/v1/webhooks - Create a new webhook
- GET /api/v1/webhooks - List all webhooks
- GET /api/v1/webhooks/{webhook_id} - Get a specific webhook
- PUT /api/v1/webhooks/{webhook_id} - Update a webhook
- DELETE /api/v1/webhooks/{webhook_id} - Delete a webhook
- POST /api/v1/webhooks/{webhook_id}/test - Test a webhook
- GET /api/v1/webhooks/{webhook_id}/deliveries - Get webhook deliveries
- GET /api/v1/webhooks/deliveries/{delivery_id} - Get specific delivery
- POST /api/v1/webhooks/deliveries/{delivery_id}/retry - Retry a delivery
- GET /api/v1/webhooks/events - List available event types
- GET /api/v1/webhooks/stats - Get webhook statistics
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, ConfigDict

from ..services.webhook_service import (
    WebhookService,
    WebhookConfig,
    Webhook,
    WebhookEvent,
    WebhookDelivery,
    DeliveryStatus,
    RetryConfig,
    get_webhook_service,
)


# ----- Pydantic Models -----

class RetryConfigModel(BaseModel):
    """Retry configuration model."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "max_retries": 3,
                "initial_delay": 1.0,
                "max_delay": 60.0,
                "backoff_multiplier": 2.0
            }
        }
    )

    max_retries: int = Field(3, ge=0, le=10, description="Maximum retry attempts")
    initial_delay: float = Field(1.0, ge=0.1, le=60.0, description="Initial delay in seconds")
    max_delay: float = Field(60.0, ge=1.0, le=3600.0, description="Maximum delay in seconds")
    backoff_multiplier: float = Field(2.0, ge=1.0, le=10.0, description="Backoff multiplier")


class CreateWebhookRequest(BaseModel):
    """Request model for creating a webhook."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Entity Updates Webhook",
                "url": "https://example.com/webhook",
                "secret": "my-secret-key",
                "events": ["entity.created", "entity.updated", "entity.deleted"],
                "active": True,
                "headers": {"Authorization": "Bearer token"},
                "project_id": "project-123"
            }
        }
    )

    name: str = Field(..., min_length=1, max_length=100, description="Webhook name")
    url: str = Field(..., min_length=1, description="Target URL")
    secret: Optional[str] = Field(None, description="Secret for HMAC signature")
    events: List[str] = Field(..., min_length=1, description="Events to subscribe to")
    active: bool = Field(True, description="Whether webhook is active")
    headers: Dict[str, str] = Field(default_factory=dict, description="Additional headers")
    project_id: Optional[str] = Field(None, description="Filter to specific project")
    retry_config: Optional[RetryConfigModel] = Field(None, description="Retry configuration")


class UpdateWebhookRequest(BaseModel):
    """Request model for updating a webhook."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Updated Webhook Name",
                "active": False,
                "events": ["entity.created"]
            }
        }
    )

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    url: Optional[str] = Field(None, min_length=1)
    secret: Optional[str] = Field(None)
    events: Optional[List[str]] = Field(None, min_length=1)
    active: Optional[bool] = Field(None)
    headers: Optional[Dict[str, str]] = Field(None)
    project_id: Optional[str] = Field(None)


class WebhookResponse(BaseModel):
    """Response model for a webhook."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "Entity Updates Webhook",
                "url": "https://example.com/webhook",
                "events": ["entity.created", "entity.updated"],
                "active": True,
                "headers": {},
                "project_id": None,
                "created_at": "2024-01-15T10:00:00Z",
                "updated_at": "2024-01-15T10:00:00Z",
                "delivery_count": 42,
                "success_count": 40,
                "failure_count": 2
            }
        }
    )

    id: str = Field(..., description="Webhook ID")
    name: str = Field(..., description="Webhook name")
    url: str = Field(..., description="Target URL")
    events: List[str] = Field(..., description="Subscribed events")
    active: bool = Field(..., description="Whether webhook is active")
    headers: Dict[str, str] = Field(..., description="Additional headers")
    project_id: Optional[str] = Field(None, description="Project filter")
    retry_config: Dict[str, Any] = Field(..., description="Retry configuration")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    last_triggered_at: Optional[str] = Field(None, description="Last trigger time")
    delivery_count: int = Field(..., description="Total deliveries")
    success_count: int = Field(..., description="Successful deliveries")
    failure_count: int = Field(..., description="Failed deliveries")


class WebhookListResponse(BaseModel):
    """Response model for webhook list."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "webhooks": [],
                "total": 0
            }
        }
    )

    webhooks: List[WebhookResponse] = Field(default_factory=list)
    total: int = Field(0, ge=0, description="Total webhooks")


class DeliveryResponse(BaseModel):
    """Response model for a webhook delivery."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "delivery-123",
                "webhook_id": "webhook-456",
                "event": "entity.created",
                "status": "success",
                "attempts": 1,
                "response_code": 200,
                "created_at": "2024-01-15T10:00:00Z"
            }
        }
    )

    id: str = Field(..., description="Delivery ID")
    webhook_id: str = Field(..., description="Webhook ID")
    event: str = Field(..., description="Event type")
    payload: Dict[str, Any] = Field(..., description="Payload sent")
    status: str = Field(..., description="Delivery status")
    attempts: int = Field(..., description="Delivery attempts")
    last_attempt_at: Optional[str] = Field(None, description="Last attempt time")
    next_retry_at: Optional[str] = Field(None, description="Next retry time")
    response_code: Optional[int] = Field(None, description="HTTP response code")
    error_message: Optional[str] = Field(None, description="Error message")
    created_at: str = Field(..., description="Creation timestamp")


class DeliveryListResponse(BaseModel):
    """Response model for delivery list."""

    deliveries: List[DeliveryResponse] = Field(default_factory=list)
    total: int = Field(0, ge=0, description="Total deliveries")


class EventTypeResponse(BaseModel):
    """Response model for event types."""

    events: List[Dict[str, str]] = Field(..., description="Available event types")
    total: int = Field(..., description="Total event types")


class WebhookStatsResponse(BaseModel):
    """Response model for webhook statistics."""

    total_events: int = Field(..., description="Total events dispatched")
    successful_deliveries: int = Field(..., description="Successful deliveries")
    failed_deliveries: int = Field(..., description="Failed deliveries")
    retried_deliveries: int = Field(..., description="Retried deliveries")
    active_webhooks: int = Field(..., description="Active webhooks")
    total_webhooks: int = Field(..., description="Total webhooks")
    pending_deliveries: int = Field(..., description="Pending deliveries")


# ----- Helper Functions -----

def webhook_to_response(webhook: Webhook) -> WebhookResponse:
    """Convert Webhook to response model."""
    data = webhook.to_dict()
    return WebhookResponse(**data)


def delivery_to_response(delivery: WebhookDelivery) -> DeliveryResponse:
    """Convert WebhookDelivery to response model."""
    data = delivery.to_dict()
    return DeliveryResponse(**data)


# ----- Dependencies -----

def get_webhook_service_dep() -> WebhookService:
    """Dependency to get WebhookService instance."""
    return get_webhook_service()


# ----- Router -----

router = APIRouter(
    prefix="/webhooks",
    tags=["webhooks"],
    responses={
        500: {"description": "Internal server error"},
    },
)


# ----- Endpoints -----

@router.post(
    "",
    response_model=WebhookResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new webhook",
    description="Create a new webhook to receive event notifications.",
    responses={
        201: {"description": "Webhook created successfully"},
        400: {"description": "Invalid request data"},
    }
)
async def create_webhook(
    request: CreateWebhookRequest,
    service: WebhookService = Depends(get_webhook_service_dep),
):
    """
    Create a new webhook.

    - **name**: Display name for the webhook
    - **url**: Target URL for webhook delivery
    - **secret**: Optional secret for HMAC signature verification
    - **events**: List of event types to subscribe to
    - **active**: Whether the webhook is active
    - **project_id**: Optional project filter
    """
    try:
        # Convert event strings to enum
        events = []
        for event_str in request.events:
            try:
                events.append(WebhookEvent(event_str))
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid event type: {event_str}"
                )

        # Build retry config
        retry_config = RetryConfig()
        if request.retry_config:
            retry_config = RetryConfig(
                max_retries=request.retry_config.max_retries,
                initial_delay=request.retry_config.initial_delay,
                max_delay=request.retry_config.max_delay,
                backoff_multiplier=request.retry_config.backoff_multiplier,
            )

        config = WebhookConfig(
            name=request.name,
            url=request.url,
            secret=request.secret,
            events=events,
            active=request.active,
            headers=request.headers,
            retry_config=retry_config,
            project_id=request.project_id,
        )

        webhook_id = await service.create_webhook(config)
        webhook = await service.get_webhook(webhook_id)

        if not webhook:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create webhook"
            )

        return webhook_to_response(webhook)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "",
    response_model=WebhookListResponse,
    summary="List webhooks",
    description="List all webhooks with optional filtering.",
    responses={
        200: {"description": "List of webhooks"},
    }
)
async def list_webhooks(
    project_id: Optional[str] = Query(None, description="Filter by project"),
    active_only: bool = Query(False, description="Only return active webhooks"),
    service: WebhookService = Depends(get_webhook_service_dep),
):
    """List webhooks with optional filters."""
    webhooks = await service.list_webhooks(project_id, active_only)

    return WebhookListResponse(
        webhooks=[webhook_to_response(w) for w in webhooks],
        total=len(webhooks),
    )


@router.get(
    "/events",
    response_model=EventTypeResponse,
    summary="List available event types",
    description="Get a list of all available webhook event types.",
)
async def list_event_types():
    """List all available webhook event types."""
    events = [
        {
            "event": e.value,
            "description": e.name.replace("_", " ").title(),
        }
        for e in WebhookEvent
    ]

    return EventTypeResponse(
        events=events,
        total=len(events),
    )


@router.get(
    "/stats",
    response_model=WebhookStatsResponse,
    summary="Get webhook statistics",
    description="Get statistics about webhook usage and deliveries.",
)
async def get_stats(
    service: WebhookService = Depends(get_webhook_service_dep),
):
    """Get webhook service statistics."""
    stats = service.get_stats()
    return WebhookStatsResponse(**stats)


@router.get(
    "/deliveries/{delivery_id}",
    response_model=DeliveryResponse,
    summary="Get a specific delivery",
    description="Get details of a specific webhook delivery.",
    responses={
        200: {"description": "Delivery found"},
        404: {"description": "Delivery not found"},
    }
)
async def get_delivery(
    delivery_id: str,
    service: WebhookService = Depends(get_webhook_service_dep),
):
    """Get a specific delivery by ID."""
    delivery = await service.get_delivery(delivery_id)

    if not delivery:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Delivery '{delivery_id}' not found"
        )

    return delivery_to_response(delivery)


@router.post(
    "/deliveries/{delivery_id}/retry",
    response_model=DeliveryResponse,
    summary="Retry a failed delivery",
    description="Manually retry a failed webhook delivery.",
    responses={
        200: {"description": "Retry initiated"},
        404: {"description": "Delivery not found"},
        400: {"description": "Delivery cannot be retried"},
    }
)
async def retry_delivery(
    delivery_id: str,
    service: WebhookService = Depends(get_webhook_service_dep),
):
    """Retry a failed delivery."""
    success = await service.retry_delivery(delivery_id)

    if not success:
        delivery = await service.get_delivery(delivery_id)
        if not delivery:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Delivery '{delivery_id}' not found"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Delivery cannot be retried (not in failed state)"
        )

    delivery = await service.get_delivery(delivery_id)
    return delivery_to_response(delivery)


@router.get(
    "/{webhook_id}",
    response_model=WebhookResponse,
    summary="Get a webhook",
    description="Get a specific webhook by ID.",
    responses={
        200: {"description": "Webhook found"},
        404: {"description": "Webhook not found"},
    }
)
async def get_webhook(
    webhook_id: str,
    service: WebhookService = Depends(get_webhook_service_dep),
):
    """Get a webhook by ID."""
    webhook = await service.get_webhook(webhook_id)

    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook '{webhook_id}' not found"
        )

    return webhook_to_response(webhook)


@router.put(
    "/{webhook_id}",
    response_model=WebhookResponse,
    summary="Update a webhook",
    description="Update an existing webhook configuration.",
    responses={
        200: {"description": "Webhook updated"},
        404: {"description": "Webhook not found"},
    }
)
async def update_webhook(
    webhook_id: str,
    request: UpdateWebhookRequest,
    service: WebhookService = Depends(get_webhook_service_dep),
):
    """Update a webhook."""
    # Build updates dict
    updates = {}

    if request.name is not None:
        updates["name"] = request.name
    if request.url is not None:
        updates["url"] = request.url
    if request.secret is not None:
        updates["secret"] = request.secret
    if request.active is not None:
        updates["active"] = request.active
    if request.headers is not None:
        updates["headers"] = request.headers
    if request.project_id is not None:
        updates["project_id"] = request.project_id
    if request.events is not None:
        try:
            updates["events"] = [WebhookEvent(e) for e in request.events]
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid event type: {e}"
            )

    webhook = await service.update_webhook(webhook_id, updates)

    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook '{webhook_id}' not found"
        )

    return webhook_to_response(webhook)


@router.delete(
    "/{webhook_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a webhook",
    description="Delete a webhook by ID.",
    responses={
        204: {"description": "Webhook deleted"},
        404: {"description": "Webhook not found"},
    }
)
async def delete_webhook(
    webhook_id: str,
    service: WebhookService = Depends(get_webhook_service_dep),
):
    """Delete a webhook."""
    deleted = await service.delete_webhook(webhook_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook '{webhook_id}' not found"
        )

    return None


@router.post(
    "/{webhook_id}/test",
    response_model=DeliveryResponse,
    summary="Test a webhook",
    description="Send a test event to a webhook.",
    responses={
        200: {"description": "Test sent"},
        404: {"description": "Webhook not found"},
    }
)
async def test_webhook(
    webhook_id: str,
    service: WebhookService = Depends(get_webhook_service_dep),
):
    """Send a test event to a webhook."""
    delivery = await service.test_webhook(webhook_id)

    if not delivery:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook '{webhook_id}' not found"
        )

    return delivery_to_response(delivery)


@router.get(
    "/{webhook_id}/deliveries",
    response_model=DeliveryListResponse,
    summary="Get webhook deliveries",
    description="Get delivery history for a specific webhook.",
    responses={
        200: {"description": "Delivery list"},
        404: {"description": "Webhook not found"},
    }
)
async def get_webhook_deliveries(
    webhook_id: str,
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    limit: int = Query(50, ge=1, le=100, description="Maximum results"),
    service: WebhookService = Depends(get_webhook_service_dep),
):
    """Get deliveries for a webhook."""
    # Verify webhook exists
    webhook = await service.get_webhook(webhook_id)
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook '{webhook_id}' not found"
        )

    # Parse status filter
    delivery_status = None
    if status_filter:
        try:
            delivery_status = DeliveryStatus(status_filter)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status_filter}"
            )

    deliveries = await service.list_deliveries(
        webhook_id=webhook_id,
        status=delivery_status,
        limit=limit,
    )

    return DeliveryListResponse(
        deliveries=[delivery_to_response(d) for d in deliveries],
        total=len(deliveries),
    )


# ----- Project-scoped Router -----

project_webhooks_router = APIRouter(
    prefix="/projects/{project_id}/webhooks",
    tags=["webhooks", "projects"],
    responses={
        500: {"description": "Internal server error"},
    },
)


@project_webhooks_router.get(
    "",
    response_model=WebhookListResponse,
    summary="List project webhooks",
    description="List webhooks for a specific project.",
)
async def list_project_webhooks(
    project_id: str,
    active_only: bool = Query(False, description="Only return active webhooks"),
    service: WebhookService = Depends(get_webhook_service_dep),
):
    """List webhooks for a specific project."""
    webhooks = await service.list_webhooks(project_id=project_id, active_only=active_only)

    return WebhookListResponse(
        webhooks=[webhook_to_response(w) for w in webhooks],
        total=len(webhooks),
    )


@project_webhooks_router.post(
    "",
    response_model=WebhookResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create project webhook",
    description="Create a webhook for a specific project.",
)
async def create_project_webhook(
    project_id: str,
    request: CreateWebhookRequest,
    service: WebhookService = Depends(get_webhook_service_dep),
):
    """Create a webhook scoped to a project."""
    try:
        # Convert event strings to enum
        events = []
        for event_str in request.events:
            try:
                events.append(WebhookEvent(event_str))
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid event type: {event_str}"
                )

        # Build retry config
        retry_config = RetryConfig()
        if request.retry_config:
            retry_config = RetryConfig(
                max_retries=request.retry_config.max_retries,
                initial_delay=request.retry_config.initial_delay,
                max_delay=request.retry_config.max_delay,
                backoff_multiplier=request.retry_config.backoff_multiplier,
            )

        config = WebhookConfig(
            name=request.name,
            url=request.url,
            secret=request.secret,
            events=events,
            active=request.active,
            headers=request.headers,
            retry_config=retry_config,
            project_id=project_id,  # Use path parameter
        )

        webhook_id = await service.create_webhook(config)
        webhook = await service.get_webhook(webhook_id)

        if not webhook:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create webhook"
            )

        return webhook_to_response(webhook)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
