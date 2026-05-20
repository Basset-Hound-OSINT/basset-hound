# Basset Hound Webhook Documentation

**Last Updated**: 2026-05-19  
**Version**: 3.0.0

---

## Table of Contents

1. [Overview](#overview)
2. [Webhook Events](#webhook-events)
3. [Creating Webhooks](#creating-webhooks)
4. [Webhook Format](#webhook-format)
5. [Delivery & Retry Policy](#delivery--retry-policy)
6. [Security](#security)
7. [Testing](#testing)
8. [Troubleshooting](#troubleshooting)

---

## Overview

Webhooks allow you to receive real-time notifications when events occur in Basset Hound. Instead of polling the API for changes, you can subscribe to events and receive push notifications.

### Use Cases

- **Real-time Sync**: Keep external systems synchronized with Basset Hound
- **Notifications**: Send alerts when entities or relationships are created
- **Automation**: Trigger workflows based on Basset Hound events
- **Audit Trail**: Log all changes in external systems
- **Integration**: Connect with third-party tools (Slack, email, etc.)

### Benefits

- **Efficient**: Only notified when changes occur (no polling)
- **Real-time**: Events delivered immediately (within seconds)
- **Reliable**: Automatic retry with exponential backoff
- **Secure**: HMAC-SHA256 signature verification
- **Flexible**: Filter events by type and criteria

---

## Webhook Events

### Available Events

| Event | Trigger | Example Data |
|-------|---------|--------------|
| `entity.created` | New entity created | Entity object with ID, name, type |
| `entity.updated` | Entity modified | Entity object with updated fields |
| `entity.deleted` | Entity removed | Entity ID and name |
| `relationship.created` | New relationship created | Relationship with source, target, type |
| `relationship.updated` | Relationship modified | Relationship with updated properties |
| `relationship.deleted` | Relationship removed | Relationship IDs |
| `project.created` | New project created | Project object |
| `project.updated` | Project modified | Project with updated fields |
| `project.deleted` | Project removed | Project ID |

### Event Data Structure

```json
{
  "event_id": "evt_123abc",
  "type": "entity.created",
  "timestamp": "2026-05-19T12:00:00Z",
  "project_id": "proj_123",
  "data": {
    "id": "ent_456",
    "name": "John Doe",
    "type": "Person",
    "metadata": {
      "email": "john@example.com"
    },
    "created_at": "2026-05-19T12:00:00Z"
  }
}
```

### Event Filtering

You can filter which events trigger your webhook:

```bash
# Subscribe to multiple event types
curl -X POST http://localhost:8080/api/v1/projects/proj_123/webhooks \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-server.com/webhook",
    "events": ["entity.created", "entity.updated"],
    "filters": {
      "entity_type": "Person",
      "include_metadata": true
    }
  }'
```

---

## Creating Webhooks

### Step 1: Create Webhook Subscription

```bash
curl -X POST http://localhost:8080/api/v1/projects/proj_123/webhooks \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-server.com/webhook",
    "events": ["entity.created", "entity.updated", "relationship.created"],
    "secret": "your_webhook_secret_key",
    "active": true,
    "description": "Sync entities to external system"
  }'
```

**Response (201 Created)**
```json
{
  "status": "success",
  "data": {
    "webhook_id": "wh_abc123xyz",
    "url": "https://your-server.com/webhook",
    "events": ["entity.created", "entity.updated", "relationship.created"],
    "active": true,
    "created_at": "2026-05-19T12:00:00Z",
    "last_triggered": null
  }
}
```

### Step 2: Receive Webhook Events

Your endpoint will receive POST requests with event data:

```http
POST /webhook HTTP/1.1
Host: your-server.com
Content-Type: application/json
X-Webhook-ID: wh_abc123xyz
X-Webhook-Signature: sha256=abc123...
X-Webhook-Timestamp: 2026-05-19T12:00:00Z

{
  "event_id": "evt_123",
  "type": "entity.created",
  "timestamp": "2026-05-19T12:00:00Z",
  "project_id": "proj_123",
  "data": {
    "id": "ent_456",
    "name": "John Doe",
    "type": "Person"
  }
}
```

### Step 3: Send Confirmation Response

Basset Hound expects a 2xx status code within 30 seconds:

```python
@app.route('/webhook', methods=['POST'])
def webhook():
    # Process event
    event = request.json
    print(f"Received {event['type']} event")
    
    # Return 200 OK
    return jsonify({'status': 'received'}), 200
```

---

## Webhook Format

### Request Headers

| Header | Value | Description |
|--------|-------|-------------|
| `Content-Type` | `application/json` | Always JSON |
| `X-Webhook-ID` | `wh_abc123` | Webhook subscription ID |
| `X-Webhook-Signature` | `sha256=...` | HMAC-SHA256 signature |
| `X-Webhook-Timestamp` | ISO 8601 | Event timestamp |
| `User-Agent` | `BassetHound/3.0` | API version |

### Request Body

```json
{
  "event_id": "evt_abc123",
  "type": "entity.created",
  "timestamp": "2026-05-19T12:00:00Z",
  "project_id": "proj_123",
  "webhook_id": "wh_xyz789",
  "data": {
    "id": "ent_456",
    "name": "John Doe",
    "type": "Person",
    "metadata": {
      "email": "john@example.com",
      "phone": "+1-555-0100"
    },
    "created_at": "2026-05-19T12:00:00Z"
  }
}
```

### Response Format

Basset Hound expects:

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "status": "received",
  "event_id": "evt_abc123"
}
```

---

## Delivery & Retry Policy

### Delivery Behavior

1. **Immediate**: Event sent to your endpoint within 1-5 seconds
2. **Confirmation**: Expects 2xx status code within 30 seconds
3. **Timeout**: Treats no response as failure after 30 seconds

### Retry Policy

If delivery fails (non-2xx status or timeout):

| Attempt | Wait Time | Total Time | Details |
|---------|-----------|-----------|---------|
| 1st attempt | - | 0s | Immediate |
| 2nd attempt | 5s | 5s | After 5 seconds |
| 3rd attempt | 25s | 30s | After 5+25 seconds |
| 4th attempt | 125s | 155s | After 5+25+125 seconds |
| 5th attempt | 625s | 780s | After 5+25+125+625 seconds (13 min) |

**Total retry window: ~13 minutes**

After 5 failed attempts, the webhook is marked as "failed" and you'll receive notification via email.

### Exponential Backoff Example

```
Attempt 1: 0s      -> Fail
Attempt 2: 5s      -> Fail
Attempt 3: 30s     -> Fail
Attempt 4: 155s    -> Fail
Attempt 5: 780s    -> Success (delivery complete)
```

### Manual Retry

```bash
# Retry a failed delivery
curl -X POST http://localhost:8080/api/v1/projects/proj_123/webhooks/wh_123/deliveries/dlv_456/retry \
  -H "Authorization: Bearer TOKEN"
```

---

## Security

### Signature Verification

Every webhook includes an HMAC-SHA256 signature in the `X-Webhook-Signature` header. Verify it to ensure authenticity:

**Signature Format**: `sha256=<hash>`

### Python Example

```python
import hmac
import hashlib
from flask import Flask, request, jsonify

app = Flask(__name__)
WEBHOOK_SECRET = 'your_webhook_secret_key'

@app.route('/webhook', methods=['POST'])
def receive_webhook():
    # Get signature from header
    signature = request.headers.get('X-Webhook-Signature', '')
    
    # Get raw request body
    payload = request.get_data()
    
    # Calculate expected signature
    expected_sig = hmac.new(
        WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    # Verify signature
    if not hmac.compare_digest(f'sha256={expected_sig}', signature):
        return jsonify({'error': 'Invalid signature'}), 401
    
    # Process event
    event = request.json
    print(f"Verified event: {event['type']}")
    
    return jsonify({'status': 'received'}), 200
```

### JavaScript Example

```javascript
const crypto = require('crypto');
const express = require('express');

const app = express();
const WEBHOOK_SECRET = 'your_webhook_secret_key';

app.use(express.raw({ type: 'application/json' }));

app.post('/webhook', (req, res) => {
  const signature = req.headers['x-webhook-signature'];
  const payload = req.body;
  
  // Calculate expected signature
  const expectedSig = crypto
    .createHmac('sha256', WEBHOOK_SECRET)
    .update(payload)
    .digest('hex');
  
  // Verify signature
  if (`sha256=${expectedSig}` !== signature) {
    return res.status(401).json({ error: 'Invalid signature' });
  }
  
  // Process event
  const event = JSON.parse(payload);
  console.log(`Verified event: ${event.type}`);
  
  res.json({ status: 'received' });
});

app.listen(3000);
```

### Best Practices

1. **Always verify signatures** - Never trust unsigned webhooks
2. **Use HTTPS** - Webhook URLs must use HTTPS in production
3. **Keep secret secure** - Never commit webhook secrets to version control
4. **Validate data** - Check event_id for duplicates to prevent double-processing
5. **Log events** - Keep audit trail of all received webhooks
6. **Set timeouts** - Implement timeout logic if processing takes time

---

## Testing

### Test Webhook

```bash
curl -X POST http://localhost:8080/api/v1/projects/proj_123/webhooks/wh_123/test \
  -H "Authorization: Bearer TOKEN"
```

This sends a test event to your webhook endpoint:

```json
{
  "event_id": "evt_test_abc123",
  "type": "test.webhook",
  "timestamp": "2026-05-19T12:00:00Z",
  "project_id": "proj_123",
  "data": {
    "message": "This is a test webhook event"
  }
}
```

### View Webhook Deliveries

```bash
# List all deliveries for a webhook
curl http://localhost:8080/api/v1/projects/proj_123/webhooks/wh_123/deliveries \
  -H "Authorization: Bearer TOKEN"
```

**Response**
```json
{
  "status": "success",
  "data": [
    {
      "delivery_id": "dlv_123",
      "event_id": "evt_abc123",
      "event_type": "entity.created",
      "status": "success",
      "status_code": 200,
      "response_time_ms": 245,
      "attempts": 1,
      "delivered_at": "2026-05-19T12:00:00Z"
    },
    {
      "delivery_id": "dlv_124",
      "event_id": "evt_def456",
      "event_type": "entity.updated",
      "status": "failed",
      "status_code": 500,
      "response_time_ms": 30000,
      "attempts": 5,
      "last_attempt_at": "2026-05-19T12:13:00Z"
    }
  ]
}
```

### Get Delivery Details

```bash
curl http://localhost:8080/api/v1/projects/proj_123/webhooks/wh_123/deliveries/dlv_123 \
  -H "Authorization: Bearer TOKEN"
```

**Response**
```json
{
  "delivery_id": "dlv_123",
  "webhook_id": "wh_123",
  "event_id": "evt_abc123",
  "event_type": "entity.created",
  "status": "success",
  "request": {
    "method": "POST",
    "url": "https://your-server.com/webhook",
    "headers": {
      "Content-Type": "application/json",
      "X-Webhook-Signature": "sha256=abc123..."
    },
    "body": "{...}"
  },
  "response": {
    "status_code": 200,
    "headers": {
      "Content-Type": "application/json"
    },
    "body": "{\"status\":\"received\"}"
  },
  "response_time_ms": 245,
  "attempts": 1,
  "delivered_at": "2026-05-19T12:00:00Z"
}
```

---

## Managing Webhooks

### List Webhooks

```bash
curl http://localhost:8080/api/v1/projects/proj_123/webhooks \
  -H "Authorization: Bearer TOKEN"
```

### Update Webhook

```bash
curl -X PUT http://localhost:8080/api/v1/projects/proj_123/webhooks/wh_123 \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://new-url.com/webhook",
    "events": ["entity.created", "entity.deleted"],
    "active": true
  }'
```

### Delete Webhook

```bash
curl -X DELETE http://localhost:8080/api/v1/projects/proj_123/webhooks/wh_123 \
  -H "Authorization: Bearer TOKEN"
```

### Get Webhook

```bash
curl http://localhost:8080/api/v1/projects/proj_123/webhooks/wh_123 \
  -H "Authorization: Bearer TOKEN"
```

**Response**
```json
{
  "status": "success",
  "data": {
    "webhook_id": "wh_123",
    "url": "https://your-server.com/webhook",
    "events": ["entity.created", "entity.updated"],
    "active": true,
    "secret": "***" (masked),
    "created_at": "2026-05-19T12:00:00Z",
    "last_triggered": "2026-05-19T12:05:00Z",
    "stats": {
      "total_events": 45,
      "successful_deliveries": 44,
      "failed_deliveries": 1,
      "success_rate": 0.978
    }
  }
}
```

---

## Examples

### Example 1: Sync to Slack

```python
from flask import Flask, request, jsonify
import requests
import hmac
import hashlib

app = Flask(__name__)
WEBHOOK_SECRET = 'your_webhook_secret'
SLACK_WEBHOOK_URL = 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'

@app.route('/webhook', methods=['POST'])
def webhook():
    # Verify signature
    signature = request.headers.get('X-Webhook-Signature')
    payload = request.get_data()
    
    expected_sig = hmac.new(
        WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    if signature != f'sha256={expected_sig}':
        return jsonify({'error': 'Invalid signature'}), 401
    
    # Parse event
    event = request.json
    event_type = event['type']
    data = event['data']
    
    # Format Slack message
    if event_type == 'entity.created':
        message = f":star: New entity: *{data['name']}* (Type: {data['type']})"
    elif event_type == 'relationship.created':
        message = f":link: New relationship: {data['source_name']} -> {data['target_name']}"
    else:
        message = f"Event: {event_type}"
    
    # Send to Slack
    requests.post(SLACK_WEBHOOK_URL, json={
        'text': message,
        'blocks': [
            {
                'type': 'section',
                'text': {
                    'type': 'mrkdwn',
                    'text': message
                }
            },
            {
                'type': 'context',
                'elements': [
                    {
                        'type': 'mrkdwn',
                        'text': f"Project: {event['project_id']} | Time: {event['timestamp']}"
                    }
                ]
            }
        ]
    })
    
    return jsonify({'status': 'received'}), 200
```

### Example 2: Log to Database

```python
from flask import Flask, request, jsonify
from datetime import datetime
import sqlite3
import hmac
import hashlib

app = Flask(__name__)
DB_PATH = 'webhooks.db'
WEBHOOK_SECRET = 'your_webhook_secret'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS webhook_log (
            id INTEGER PRIMARY KEY,
            event_id TEXT UNIQUE,
            event_type TEXT,
            project_id TEXT,
            data TEXT,
            received_at TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/webhook', methods=['POST'])
def webhook():
    # Verify signature
    signature = request.headers.get('X-Webhook-Signature')
    payload = request.get_data()
    
    expected_sig = hmac.new(
        WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    if signature != f'sha256={expected_sig}':
        return jsonify({'error': 'Invalid signature'}), 401
    
    # Parse event
    event = request.json
    
    # Store in database
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
        INSERT INTO webhook_log (event_id, event_type, project_id, data, received_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        event['event_id'],
        event['type'],
        event['project_id'],
        str(event['data']),
        datetime.now()
    ))
    conn.commit()
    conn.close()
    
    return jsonify({'status': 'received'}), 200

if __name__ == '__main__':
    init_db()
    app.run(port=5000)
```

### Example 3: Deduplication Processing

```python
from flask import Flask, request, jsonify
import hmac
import hashlib
import requests

app = Flask(__name__)
WEBHOOK_SECRET = 'your_webhook_secret'
BASSET_API_URL = 'http://localhost:8080/api/v1'
API_TOKEN = 'your_api_token'

@app.route('/webhook', methods=['POST'])
def webhook():
    # Verify signature
    signature = request.headers.get('X-Webhook-Signature')
    payload = request.get_data()
    
    expected_sig = hmac.new(
        WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    if signature != f'sha256={expected_sig}':
        return jsonify({'error': 'Invalid signature'}), 401
    
    # Parse event
    event = request.json
    
    # Process new entities - check for duplicates
    if event['type'] == 'entity.created':
        entity = event['data']
        project_id = event['project_id']
        
        # Find duplicates using API
        response = requests.get(
            f'{BASSET_API_URL}/projects/{project_id}/deduplication/find',
            headers={'Authorization': f'Bearer {API_TOKEN}'},
            json={
                'entity_ids': [entity['id']],
                'threshold': 0.85
            }
        )
        
        if response.status_code == 200:
            duplicates = response.json()['data']['duplicates']
            
            if duplicates:
                print(f"Found {len(duplicates)} potential duplicates for {entity['name']}")
                # Log or notify about duplicates
    
    return jsonify({'status': 'received'}), 200
```

---

## Troubleshooting

### Webhook Not Receiving Events

**Problem**: Webhook URL never receives POST requests

**Solutions**:
1. Check webhook is active: `GET /webhooks/{webhook_id}`
2. Test webhook: `POST /webhooks/{webhook_id}/test`
3. Verify events are happening: Check audit log for changes
4. Check firewall/network: Ensure Basset Hound can reach your endpoint
5. Check URL is HTTPS: Required in production

### Failed Deliveries

**Problem**: Webhook deliveries showing as failed

**Solutions**:
1. Check response status code: Should be 200-299
2. Verify signature: May be rejecting unsigned requests
3. Check timeout: Response must arrive within 30 seconds
4. Review logs: Check webhook delivery details
5. Test endpoint: Use `curl` to verify endpoint works

### Duplicate Events

**Problem**: Processing same event multiple times

**Solutions**:
1. Store `event_id`: Check for duplicates before processing
2. Use idempotent operations: Safe to retry without side effects
3. Implement deduplication: Track processed event IDs

### High Latency

**Problem**: Webhook deliveries taking too long

**Solutions**:
1. Process asynchronously: Don't do heavy work in webhook handler
2. Use job queue: Defer processing to background job
3. Return immediately: Send 200 response before processing

---

**Last Updated**: 2026-05-19  
**Version**: 3.0.0
