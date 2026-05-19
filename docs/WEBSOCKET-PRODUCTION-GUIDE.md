# WebSocket Production Stability Guide

**Phase 8: Connection Pooling & Heartbeat for Production Stability**

This guide documents the WebSocket connection pooling and heartbeat mechanism implemented for supporting 1000+ concurrent WebSocket connections with production-grade stability.

## Overview

The WebSocket layer now includes:
- **Connection pooling** with configurable capacity limits
- **Automatic heartbeat/keepalive** mechanism (default: 30-second pings)
- **Connection health monitoring** with automatic timeout detection
- **Comprehensive metrics** for monitoring and debugging
- **Graceful error handling** preventing cascading failures

## Architecture

### Components

1. **ConnectionManager** (`api/services/websocket_service.py`)
   - Manages all active WebSocket connections
   - Implements heartbeat loop
   - Tracks connection health and metrics
   - Handles connection pooling and limits

2. **WebSocketConnection** (dataclass in websocket_service.py)
   - Represents individual connections
   - Tracks heartbeat state (missed pings)
   - Maintains connection quality metrics

3. **Health Check Endpoints** (`api/main.py`)
   - `/api/v1/ws/health` - Pool status and metrics
   - `/api/v1/ws/connections` - List active connections (debug)

### Configuration

WebSocket settings are configured via environment variables in `api/config.py`:

```python
# Heartbeat interval in seconds (default: 30)
WEBSOCKET_HEARTBEAT_INTERVAL=30

# Timeout for unresponsive connections in seconds (default: 60)
WEBSOCKET_TIMEOUT=60

# Maximum concurrent connections (None = unlimited)
WEBSOCKET_MAX_CONNECTIONS=1000

# Close connection after N missed pings (default: 3)
WEBSOCKET_MISSED_PINGS_THRESHOLD=3

# Enable detailed metrics (default: True)
WEBSOCKET_ENABLE_METRICS=True
```

## Protocol

### Heartbeat Message Format

The server sends periodic PING messages to all connected clients:

```json
{
  "type": "ping",
  "timestamp": "2026-05-19T10:30:00+00:00",
  "message_id": "uuid"
}
```

Clients should respond with a PONG:

```json
{
  "type": "pong",
  "timestamp": "2026-05-19T10:30:00+00:00",
  "message_id": "uuid"
}
```

### Connection Lifecycle

1. **Connection Established**
   - Client connects to `/api/v1/ws/projects/{project_id}`
   - Server accepts and sends `{"type": "connected", "data": {"connection_id": "..."}}`
   - Heartbeat tracking begins

2. **Active Communication**
   - Server sends PING every 30 seconds
   - Client responds with PONG
   - Missed pings counter resets on PONG
   - Connection marked healthy

3. **Timeout Detection**
   - If PONG not received within 60 seconds of PING, increment missed pings
   - After 3 consecutive missed pings, connection is closed
   - Connection logged and removed from pool

4. **Graceful Disconnection**
   - Client closes connection normally
   - Server cleans up subscriptions and logs disconnection

## Monitoring & Debugging

### Health Check Endpoint

```bash
# Check WebSocket pool health
curl http://localhost:8000/api/v1/ws/health

# Response:
{
  "status": "healthy",
  "pool": {
    "active_connections": 425,
    "healthy_connections": 425,
    "unhealthy_connections": 0,
    "capacity": 1000,
    "capacity_used_percent": 42.5
  },
  "heartbeat": {
    "interval_seconds": 30,
    "timeout_seconds": 60,
    "missed_pings_threshold": 3,
    "total_pings_sent": 15420,
    "total_pongs_received": 15401,
    "disconnections_due_to_timeout": 19
  },
  "statistics": {
    "total_connections_ever": 500,
    "total_messages_sent": 45821,
    "total_errors": 2,
    "project_subscriptions": {
      "project_1": 125,
      "project_2": 300
    }
  },
  "timestamp": "2026-05-19T10:30:00+00:00"
}
```

### Connections List Endpoint

```bash
# List all active connections (debug endpoint)
curl http://localhost:8000/api/v1/ws/connections

# Response:
{
  "total_connections": 425,
  "connections": [
    {
      "connection_id": "conn_abc123",
      "connected_at": "2026-05-19T10:15:00+00:00",
      "last_activity": "2026-05-19T10:29:55+00:00",
      "healthy": true,
      "missed_pings": 0,
      "project_subscriptions": ["project_1"],
      "subscription_types": ["all"],
      "quality": {
        "latency_ms": 45.5,
        "average_latency_ms": 42.3,
        "messages_sent": 120,
        "messages_received": 119,
        "errors_count": 0
      }
    }
  ],
  "timestamp": "2026-05-19T10:30:00+00:00"
}
```

## Metrics & Prometheus

WebSocket metrics are exposed via `/metrics` endpoint in Prometheus format:

Key metrics to monitor:
- `websocket_connections_active` - Current active connections
- `websocket_connections_total` - Total connections since startup
- `websocket_messages_sent_total` - Total messages sent
- `websocket_errors_total` - Total errors encountered
- `websocket_pings_sent_total` - Total heartbeat pings
- `websocket_pongs_received_total` - Total pong responses
- `websocket_timeouts_total` - Connections closed due to timeout

### Prometheus Configuration

Add to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'basset_hound_websocket'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

### Alerting Rules

```yaml
groups:
  - name: websocket_alerts
    rules:
      # Alert if WebSocket pool is near capacity
      - alert: WebSocketPoolNearCapacity
        expr: |
          (websocket_connections_active / websocket_max_connections) > 0.8
        for: 5m
        annotations:
          summary: "WebSocket pool at {{ $value | humanizePercentage }} capacity"

      # Alert if too many timeouts
      - alert: WebSocketHighTimeoutRate
        expr: |
          rate(websocket_timeouts_total[5m]) > 0.1
        for: 5m
        annotations:
          summary: "High WebSocket timeout rate: {{ $value }} per second"

      # Alert if error rate is high
      - alert: WebSocketHighErrorRate
        expr: |
          rate(websocket_errors_total[5m]) > 0.05
        for: 5m
        annotations:
          summary: "High WebSocket error rate: {{ $value }} per second"
```

## Client Implementation

### JavaScript/TypeScript Example

```javascript
class WebSocketClient {
  constructor(projectId, userId) {
    this.projectId = projectId;
    this.userId = userId;
    this.connectionId = null;
    this.socket = null;
  }

  connect() {
    const url = `ws://localhost:8000/api/v1/ws/projects/${this.projectId}?user=${this.userId}`;
    this.socket = new WebSocket(url);

    this.socket.onopen = () => {
      console.log('Connected to WebSocket');
    };

    this.socket.onmessage = (event) => {
      const message = JSON.parse(event.data);
      this.handleMessage(message);
    };

    this.socket.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    this.socket.onclose = () => {
      console.log('Disconnected from WebSocket');
      this.attemptReconnect();
    };
  }

  handleMessage(message) {
    switch (message.type) {
      case 'connected':
        this.connectionId = message.data.connection_id;
        console.log('Connection established:', this.connectionId);
        break;

      case 'ping':
        // Respond to server ping
        this.sendPong();
        break;

      case 'pong':
        // Server confirmed our ping
        console.log('Received pong from server');
        break;

      // ... handle other message types
    }
  }

  sendPong() {
    this.socket.send(JSON.stringify({ type: 'pong' }));
  }

  attemptReconnect() {
    setTimeout(() => {
      console.log('Attempting to reconnect...');
      this.connect();
    }, 5000);
  }
}

// Usage
const client = new WebSocketClient('project_123', 'user_456');
client.connect();
```

### Python Example (using websockets)

```python
import asyncio
import json
from websockets import connect

class WebSocketClient:
    def __init__(self, project_id, user_id):
        self.project_id = project_id
        self.user_id = user_id
        self.uri = f"ws://localhost:8000/api/v1/ws/projects/{project_id}?user={user_id}"

    async def connect(self):
        async with connect(self.uri) as websocket:
            try:
                while True:
                    message = await websocket.recv()
                    await self.handle_message(websocket, json.loads(message))
            except Exception as e:
                print(f"Error: {e}")
                await asyncio.sleep(5)
                await self.connect()

    async def handle_message(self, websocket, message):
        msg_type = message.get("type")

        if msg_type == "ping":
            # Respond to heartbeat ping
            await websocket.send(json.dumps({"type": "pong"}))
        elif msg_type == "connected":
            print(f"Connected: {message['data']['connection_id']}")
        elif msg_type == "sync_confirmed":
            print(f"Update confirmed: {message['update']['update_id']}")
        # ... handle other types

# Usage
client = WebSocketClient("project_123", "user_456")
asyncio.run(client.connect())
```

## Troubleshooting

### High Timeout Rate

**Symptoms:**
- Many disconnections showing in `/api/v1/ws/health`
- Clients experiencing unexpected disconnections

**Causes:**
- Network latency > 60 seconds (default timeout)
- Slow client processing blocking pong responses
- High server CPU/memory causing delayed heartbeat

**Solutions:**
- Increase `WEBSOCKET_TIMEOUT` if network is slow
- Optimize client processing to respond to pings quickly
- Scale server capacity or add load balancing

### Connection Pool At Capacity

**Symptoms:**
- New connections rejected
- `capacity_used_percent` approaching 100%

**Solutions:**
- Increase `WEBSOCKET_MAX_CONNECTIONS` limit
- Implement connection recycling for idle clients
- Deploy additional server instances with load balancing

### High Error Rate

**Symptoms:**
- Errors in WebSocket communication
- Clients unable to receive messages

**Causes:**
- Network connectivity issues
- Server crashes or crashes during message send
- Client disconnecting abruptly

**Solutions:**
- Check network connectivity
- Review server logs for crash information
- Implement exponential backoff in client reconnection

### Silent Disconnections

**Symptoms:**
- Connections drop without warning
- Client unable to detect failure

**Prevention:**
- Ensure clients respond to PING messages
- Monitor `/api/v1/ws/health` for unexpected disconnections
- Implement client-side timeout detection (e.g., no data for 2x heartbeat interval)

## Performance Tuning

### Recommended Settings for Different Scales

#### Development (< 100 connections)
```
WEBSOCKET_HEARTBEAT_INTERVAL=60
WEBSOCKET_TIMEOUT=120
WEBSOCKET_MAX_CONNECTIONS=500
WEBSOCKET_MISSED_PINGS_THRESHOLD=3
```

#### Production (100-500 connections)
```
WEBSOCKET_HEARTBEAT_INTERVAL=30
WEBSOCKET_TIMEOUT=60
WEBSOCKET_MAX_CONNECTIONS=1000
WEBSOCKET_MISSED_PINGS_THRESHOLD=3
WEBSOCKET_ENABLE_METRICS=True
```

#### Large Scale (500-1000+ connections)
```
WEBSOCKET_HEARTBEAT_INTERVAL=20
WEBSOCKET_TIMEOUT=45
WEBSOCKET_MAX_CONNECTIONS=2000
WEBSOCKET_MISSED_PINGS_THRESHOLD=2
WEBSOCKET_ENABLE_METRICS=True
# Use load balancer with sticky sessions
# Deploy multiple instances
# Consider Redis pub/sub for multi-instance broadcasting
```

### Memory Considerations

- Each connection uses approximately 10-50 KB of memory
- 1000 connections = 10-50 MB baseline
- Metrics tracking adds ~100 bytes per connection
- Connection quality history adds ~1 KB per connection

## Security Considerations

1. **Authentication**: WebSocket connections should validate authentication tokens
2. **Rate Limiting**: Implement rate limiting on message handling
3. **Input Validation**: Validate all incoming WebSocket messages
4. **Resource Limits**: Set maximum message size and frequency

## Best Practices

1. **Monitor Metrics Continuously**
   - Use Prometheus + Grafana for real-time visibility
   - Set up alerts for capacity and error thresholds

2. **Test Connection Failover**
   - Simulate network failures during testing
   - Verify client reconnection behavior

3. **Graceful Degradation**
   - Have fallback HTTP endpoints for critical operations
   - Design clients to handle WebSocket failures

4. **Log Analysis**
   - Review WebSocket logs regularly for patterns
   - Monitor timeout frequency and causes

5. **Capacity Planning**
   - Monitor growth of active connections
   - Plan scale-out before hitting limits

## Future Improvements

- [ ] Redis pub/sub support for multi-instance deployments
- [ ] Automatic connection migration during server restarts
- [ ] Compression support for message payloads
- [ ] Selective message routing based on subscription type
- [ ] Automatic client reconnection with exponential backoff
- [ ] WebSocket connection pooling on client side

## References

- FastAPI WebSocket Documentation: https://fastapi.tiangolo.com/advanced/websockets/
- RFC 6455 - The WebSocket Protocol: https://tools.ietf.org/html/rfc6455
- WebSocket Best Practices: https://www.ably.io/topic/websockets

---

**Document Version:** 1.0  
**Last Updated:** 2026-05-19  
**Phase:** 8 (Production Stability)
