# WebSocket Real-Time Notifications

This package provides WebSocket support for real-time notifications in the Basset Hound OSINT platform.

## Phase 45: WebSocket Real-Time Notifications (2026-01-09)

### Overview

The WebSocket system enables real-time updates for:
- **Suggestion Events**: When new suggestions are generated for entities
- **Linking Actions**: When data items are linked or entities are merged
- **Orphan Management**: When orphan data is linked to entities

### Quick Start

#### Server-Side (Python)

```python
from api.services.notification_service import get_notification_service

# Get singleton notification service
notification_service = get_notification_service()

# Broadcast a suggestion generated event
await notification_service.broadcast_suggestion_generated(
    project_id="proj_123",
    entity_id="ent_abc123",
    suggestion_count=5,
    high_confidence_count=2
)

# Broadcast an entity merged event
await notification_service.broadcast_entity_merged(
    project_id="proj_123",
    entity_id_1="ent_abc123",
    entity_id_2="ent_def456",
    kept_entity_id="ent_abc123",
    reason="Duplicate detection"
)
```

#### Client-Side (JavaScript)

```javascript
// Import the client library
// <script src="/api/websocket/client_example.js"></script>

const client = new SuggestionWebSocketClient('proj_123');

client.onSuggestionGenerated((data) => {
    console.log('New suggestions:', data);
    updateSuggestionBadge(data.entity_id, data.suggestion_count);
});

client.onEntityMerged((data) => {
    console.log('Entities merged:', data);
    refreshEntityList();
});

client.connect();
```

## Files

### Core Implementation

- **suggestion_events.py**: WebSocket endpoint and event broadcasting functions
- **client_example.js**: JavaScript client library with framework integration examples

### Supporting Files

- **README.md**: This file
- **__init__.py**: Package initialization

## WebSocket Endpoint

**URL**: `ws://localhost:8000/ws/suggestions/{project_id}`

**Query Parameters**:
- `token` (optional): Authentication token
- `client_id` (optional): Custom client identifier

**Auto-subscriptions**:
- Project-level events (automatic)
- Suggestion event type (automatic)

## Event Types

### 1. suggestion_generated

Triggered when new suggestions are computed for an entity.

```json
{
  "type": "suggestion_generated",
  "project_id": "proj_123",
  "entity_id": "ent_abc123",
  "data": {
    "suggestion_count": 5,
    "high_confidence_count": 2,
    "medium_confidence_count": 2,
    "low_confidence_count": 1,
    "affected_entities": ["ent_abc123", "ent_def456"]
  },
  "_links": {
    "suggestions": {"href": "/api/v1/suggestions/entity/ent_abc123"}
  }
}
```

### 2. suggestion_dismissed

Triggered when a user dismisses a suggestion.

```json
{
  "type": "suggestion_dismissed",
  "project_id": "proj_123",
  "entity_id": "ent_abc123",
  "data": {
    "suggestion_id": "data_xyz789",
    "reason": "Not the same person"
  }
}
```

### 3. entity_merged

Triggered when two entities are merged.

```json
{
  "type": "entity_merged",
  "project_id": "proj_123",
  "data": {
    "entity_id_1": "ent_abc123",
    "entity_id_2": "ent_def456",
    "kept_entity_id": "ent_abc123",
    "discarded_entity_id": "ent_def456",
    "merged_data_count": 15,
    "reason": "Duplicate detection"
  },
  "_links": {
    "kept_entity": {"href": "/api/v1/projects/proj_123/entities/ent_abc123"}
  }
}
```

### 4. data_linked

Triggered when two data items are linked.

```json
{
  "type": "data_linked",
  "project_id": "proj_123",
  "data": {
    "data_id_1": "data_abc123",
    "data_id_2": "data_def456",
    "reason": "Same email address",
    "confidence": 0.95,
    "affected_entities": ["ent_abc", "ent_def"]
  },
  "_links": {
    "data_1": {"href": "/api/v1/data/data_abc123"},
    "data_2": {"href": "/api/v1/data/data_def456"}
  }
}
```

### 5. orphan_linked

Triggered when orphan data is linked to an entity.

```json
{
  "type": "orphan_linked",
  "project_id": "proj_123",
  "data": {
    "orphan_id": "orphan_xyz789",
    "entity_id": "ent_abc123",
    "reason": "Matching email",
    "confidence": 0.92
  },
  "_links": {
    "orphan": {"href": "/api/v1/orphans/orphan_xyz789"},
    "entity": {"href": "/api/v1/projects/proj_123/entities/ent_abc123"}
  }
}
```

## Client Message Protocol

Clients can send these messages to the server:

### Ping (Keepalive)

```json
{"type": "ping", "timestamp": 1704801600000}
```

Server responds with:
```json
{"type": "pong"}
```

### Subscribe to Entity

```json
{"type": "subscribe_entity", "entity_id": "ent_abc123"}
```

Server responds with:
```json
{
  "type": "subscribed",
  "data": {"entity_id": "ent_abc123"}
}
```

### Unsubscribe from Entity

```json
{"type": "unsubscribe_entity", "entity_id": "ent_abc123"}
```

Server responds with:
```json
{
  "type": "unsubscribed",
  "data": {"entity_id": "ent_abc123"}
}
```

## Connection Management

### Heartbeat
- **Interval**: 30 seconds (default)
- **Purpose**: Keep connection alive, measure latency

### Reconnection
- **Strategy**: Exponential backoff
- **Initial Delay**: 1000ms
- **Max Delay**: 30000ms (30 seconds)

### Connection Lifecycle

1. **Connect**: Client connects to WebSocket endpoint
2. **Accept**: Server accepts and sends `connected` message
3. **Subscribe**: Server automatically subscribes to project
4. **Active**: Client receives events, sends heartbeats
5. **Disconnect**: Connection closed (graceful or error)
6. **Reconnect**: Client automatically reconnects with backoff

## Integration

### LinkingService Integration

The `LinkingService` automatically broadcasts WebSocket events when:
- Data items are linked (`link_data_items()`)
- Entities are merged (`merge_entities()`)
- Orphans are linked (`link_orphan_to_entity()`)

To disable notifications:
```python
linking_service = LinkingService(neo4j_service, enable_notifications=False)
```

### SuggestionService Integration

When suggestions are computed, broadcast the event:

```python
from api.services.suggestion_service import SuggestionService
from api.services.notification_service import get_notification_service

async with SuggestionService() as service:
    suggestions = await service.get_entity_suggestions("ent_abc123")

    # Count suggestions by confidence
    high_count = sum(1 for s in suggestions if s.confidence >= 0.9)
    med_count = sum(1 for s in suggestions if 0.7 <= s.confidence < 0.9)
    low_count = sum(1 for s in suggestions if s.confidence < 0.7)

    # Broadcast event
    notification_service = get_notification_service()
    await notification_service.broadcast_suggestion_generated(
        project_id="proj_123",
        entity_id="ent_abc123",
        suggestion_count=len(suggestions),
        high_confidence_count=high_count,
        medium_confidence_count=med_count,
        low_confidence_count=low_count
    )
```

## Testing

Run tests with:
```bash
pytest tests/test_websocket_notifications.py -v
```

Run load tests:
```bash
pytest tests/test_websocket_notifications.py -v -m slow
```

## Performance

### Single Server Limits
- **Recommended**: < 1,000 concurrent connections
- **Maximum**: ~10,000 connections (depends on resources)

### Multi-Server Deployment

For horizontal scaling, implement Redis pub/sub:

1. Install Redis: `pip install redis[hiredis]`
2. Configure Redis in settings
3. Extend `NotificationService` to publish to Redis
4. Each server subscribes to Redis and forwards to local connections

See Phase 45 documentation for implementation details.

## Security

### Authentication
- Optional token-based authentication via query parameter
- Can be extended to validate JWT tokens
- Future: OAuth2, API keys

### Authorization
- Project-level access control
- Events only sent to authorized subscribers

### Data Exposure
- Events include minimal data (IDs, counts)
- Full details fetched via REST API with proper authorization
- HATEOAS links for secure navigation

## Examples

See `client_example.js` for comprehensive examples including:
- Basic usage
- React integration (hooks)
- Vue integration (composables)
- Entity subscriptions
- Error handling
- Reconnection logic

## Documentation

Full documentation: `/home/devel/basset-hound/docs/findings/PHASE45-WEBSOCKET-2026-01-09.md`

## Related Files

- `/home/devel/basset-hound/api/services/notification_service.py` - High-level notification API
- `/home/devel/basset-hound/api/services/websocket_service.py` - Core WebSocket service
- `/home/devel/basset-hound/api/services/linking_service.py` - Integration with linking operations
- `/home/devel/basset-hound/tests/test_websocket_notifications.py` - Test suite

---

**Phase**: 45
**Date**: 2026-01-09
**Status**: Complete ✅
