# Phase 24: Webhook Integrations

## Summary

Phase 24 adds webhook integration functionality for sending external notifications when events occur in Basset Hound. This enables integration with external services like Slack, custom dashboards, SIEM systems, and automation workflows.

**Important Philosophy Note**: Basset Hound does NOT rate limit API endpoints. The application is designed to scale with your hardware - the only limits are what Neo4j and your machine can support. The ONLY rate limiting is on **outbound webhook requests** to protect external services from being overwhelmed.

## Components Implemented

### 1. Webhook Service

**File**: `api/services/webhook_service.py`

A comprehensive service for managing webhooks and sending event notifications.

#### Features

- **CRUD Operations**: Create, read, update, delete webhooks
- **Event Types**: 20+ event types for entities, relationships, searches, reports, imports, and more
- **HMAC-SHA256 Signatures**: Secure payload verification with configurable secrets
- **Retry Logic**: Exponential backoff with configurable retry parameters
- **Delivery Logging**: Track delivery attempts, status, and responses
- **Outbound Throttling**: Protects external services from being spammed (10 req/sec default)
- **LRU Eviction**: Automatically cleans up old delivery records

#### Event Types

| Category | Events |
|----------|--------|
| Entity | `entity.created`, `entity.updated`, `entity.deleted` |
| Relationship | `relationship.created`, `relationship.updated`, `relationship.deleted` |
| Search | `search.executed`, `saved_search.executed` |
| Report | `report.generated`, `report.scheduled` |
| Import/Export | `import.started`, `import.completed`, `import.failed`, `export.completed` |
| Project | `project.created`, `project.deleted` |
| Orphan | `orphan.created`, `orphan.linked` |
| System | `system.health`, `rate_limit.exceeded` |

#### Data Models

| Model | Description |
|-------|-------------|
| `WebhookEvent` | Enum of all supported event types |
| `DeliveryStatus` | Enum: PENDING, SENDING, SUCCESS, FAILED, RETRYING |
| `RetryConfig` | Retry behavior (max_retries, delays, backoff) |
| `WebhookConfig` | Webhook configuration (name, URL, secret, events, etc.) |
| `Webhook` | Webhook with metadata and statistics |
| `WebhookDelivery` | Delivery attempt record |

#### Usage Example

```python
from api.services.webhook_service import (
    WebhookService,
    WebhookConfig,
    WebhookEvent,
    get_webhook_service,
)

service = get_webhook_service()

# Create a webhook
config = WebhookConfig(
    name="Entity Updates",
    url="https://example.com/webhook",
    secret="my-secret-key",
    events=[WebhookEvent.ENTITY_CREATED, WebhookEvent.ENTITY_UPDATED],
    project_id="project-123",  # Optional: filter to specific project
)
webhook_id = await service.create_webhook(config)

# Send an event (automatically delivered to subscribed webhooks)
await service.send_event(
    WebhookEvent.ENTITY_CREATED,
    project_id="project-123",
    data={"entity_id": "entity-456", "name": "John Doe"}
)

# Test a webhook
delivery = await service.test_webhook(webhook_id)
print(f"Test delivery status: {delivery.status}")

# Get statistics
stats = service.get_stats()
print(f"Total events: {stats['total_events']}")
print(f"Success rate: {stats['successful_deliveries'] / max(1, stats['total_events']) * 100:.1f}%")
```

### 2. Webhook API Router

**File**: `api/routers/webhooks.py`

REST API endpoints for managing webhooks and viewing deliveries.

#### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/webhooks` | Create a new webhook |
| GET | `/webhooks` | List all webhooks |
| GET | `/webhooks/events` | List available event types |
| GET | `/webhooks/stats` | Get webhook statistics |
| GET | `/webhooks/{webhook_id}` | Get a specific webhook |
| PUT | `/webhooks/{webhook_id}` | Update a webhook |
| DELETE | `/webhooks/{webhook_id}` | Delete a webhook |
| POST | `/webhooks/{webhook_id}/test` | Send a test event |
| GET | `/webhooks/{webhook_id}/deliveries` | Get delivery history |
| GET | `/webhooks/deliveries/{delivery_id}` | Get specific delivery |
| POST | `/webhooks/deliveries/{delivery_id}/retry` | Retry a failed delivery |

#### Project-Scoped Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/projects/{project_id}/webhooks` | List project webhooks |
| POST | `/projects/{project_id}/webhooks` | Create project webhook |

#### Usage Examples

**Create Webhook:**
```bash
curl -X POST http://localhost:8000/api/v1/webhooks \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Entity Updates",
    "url": "https://example.com/webhook",
    "secret": "my-secret-key",
    "events": ["entity.created", "entity.updated", "entity.deleted"],
    "active": true
  }'
```

**Test Webhook:**
```bash
curl -X POST http://localhost:8000/api/v1/webhooks/{id}/test
```

**Get Statistics:**
```bash
curl http://localhost:8000/api/v1/webhooks/stats
```

**List Available Events:**
```bash
curl http://localhost:8000/api/v1/webhooks/events
```

## HMAC Signature Verification

When a secret is configured, each webhook delivery includes an `X-Webhook-Signature` header:

```
X-Webhook-Signature: sha256=<hex-digest>
```

To verify in your receiving service:

```python
import hmac
import hashlib

def verify_signature(payload: bytes, secret: str, signature: str) -> bool:
    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

    # Signature format is "sha256=<digest>"
    provided = signature.replace("sha256=", "")
    return hmac.compare_digest(expected, provided)
```

## Retry Configuration

Default retry behavior:

| Setting | Default | Description |
|---------|---------|-------------|
| `max_retries` | 3 | Maximum retry attempts |
| `initial_delay` | 1.0s | Delay before first retry |
| `max_delay` | 60.0s | Maximum delay between retries |
| `backoff_multiplier` | 2.0 | Exponential backoff factor |

Custom retry configuration:

```bash
curl -X POST http://localhost:8000/api/v1/webhooks \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Critical Alerts",
    "url": "https://alerts.example.com/webhook",
    "events": ["import.failed"],
    "retry_config": {
      "max_retries": 5,
      "initial_delay": 2.0,
      "max_delay": 120.0,
      "backoff_multiplier": 3.0
    }
  }'
```

## Outbound Rate Limiting

Basset Hound includes outbound throttling to protect external webhook endpoints:

- **Default rate**: 10 requests per second
- **Purpose**: Prevents overwhelming external services during burst events
- **Configuration**: Set via `max_requests_per_second` parameter

This is the ONLY rate limiting in Basset Hound. Internal API operations have no artificial limits.

## Test Coverage

**File**: `tests/test_phase24_webhooks.py`

71 comprehensive tests covering:

- WebhookEvent enum (10 tests)
- DeliveryStatus enum (2 tests)
- RetryConfig dataclass (2 tests)
- WebhookConfig validation (5 tests)
- Webhook dataclass (2 tests)
- WebhookDelivery dataclass (2 tests)
- WebhookService CRUD (8 tests)
- WebhookService listing (4 tests)
- Event sending (3 tests)
- Delivery management (6 tests)
- Statistics (2 tests)
- Clear operation (1 test)
- Singleton pattern (3 tests)
- HMAC signatures (1 test)
- Router imports (4 tests)
- Request models (3 tests)
- Response models (5 tests)
- Service exports (1 test)
- Router exports (1 test)
- Outbound throttling (3 tests)
- LRU eviction (1 test)
- No-rate-limiting philosophy (2 tests)

```
tests/test_phase24_webhooks.py ... 71 passed in 1.76s
```

## Files Created/Modified

| File | Action | Description |
|------|--------|-------------|
| `api/services/webhook_service.py` | Created | Webhook service (~760 lines) |
| `api/routers/webhooks.py` | Created | REST API endpoints (~720 lines) |
| `api/services/__init__.py` | Modified | Added Phase 24 exports |
| `api/routers/__init__.py` | Modified | Added webhook router registration |
| `tests/test_phase24_webhooks.py` | Created | 71 comprehensive tests |

## Metrics

| Metric | Value |
|--------|-------|
| New tests | 71 |
| All Phase 24 tests passing | Yes |
| New endpoints | 13 |
| Event types supported | 20 |
| Delivery statuses | 5 |
| Total lines of code | ~1,480 |

## Integration Points

### With Other Services

```python
# In your entity creation code
from api.services.webhook_service import get_webhook_service, WebhookEvent

async def create_entity(data):
    # ... create entity logic ...

    # Notify subscribers
    webhook_service = get_webhook_service()
    await webhook_service.send_event(
        WebhookEvent.ENTITY_CREATED,
        project_id=entity.project_id,
        data={"entity_id": entity.id, "type": entity.type, "name": entity.name}
    )
```

### Webhook Payload Format

All webhook payloads follow this structure:

```json
{
  "event": "entity.created",
  "timestamp": "2024-01-15T10:30:00Z",
  "project_id": "project-123",
  "data": {
    "entity_id": "entity-456",
    "type": "person",
    "name": "John Doe"
  }
}
```

## Performance Philosophy

Basset Hound is designed for maximum performance:

1. **No API Rate Limiting**: Internal endpoints have no artificial throttles
2. **Scale With Hardware**: Performance scales with your machine's capabilities
3. **Database is the Limit**: Neo4j and your hardware determine throughput
4. **Outbound Protection Only**: Only webhook deliveries are throttled to protect external services

## Conclusion

Phase 24 completes the webhook integration functionality:

- **WebhookService** provides comprehensive webhook management and event delivery
- **REST API** with 13 endpoints for full webhook lifecycle management
- **HMAC signatures** for secure payload verification
- **Retry logic** with exponential backoff for reliable delivery
- **Outbound throttling** to protect external services (not to limit users)

This enables integration with:
- Slack/Discord notifications
- SIEM systems
- Custom dashboards
- Automation workflows (Zapier, n8n, etc.)
- External monitoring systems
