# Basset Hound API Integration Guide

**Target Audience**: Developers integrating with Basset Hound API  
**Last Updated**: 2026-05-19  
**Version**: 3.0.0

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Authentication](#authentication)
3. [HTTP Client Setup](#http-client-setup)
4. [Request/Response Patterns](#requestresponse-patterns)
5. [Error Handling](#error-handling)
6. [Pagination & Filtering](#pagination--filtering)
7. [Rate Limiting](#rate-limiting)
8. [WebSocket Integration](#websocket-integration)
9. [Webhook Integration](#webhook-integration)
10. [Code Examples](#code-examples)
11. [Best Practices](#best-practices)
12. [Troubleshooting](#troubleshooting)

---

## Quick Start

### 1. Get API Base URL

```
Development: http://localhost:8080/api/v1
Production:  https://api.basset-hound.com/api/v1
```

### 2. Check Health

```bash
curl http://localhost:8080/health
# Check service status and connectivity
```

### 3. Authenticate (Production Only)

```bash
curl -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "password": "pass"}'
```

### 4. Make Request

```bash
curl http://localhost:8080/api/v1/projects \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Authentication

### Token Types

| Token | Lifespan | Purpose | Scope |
|-------|----------|---------|-------|
| Access Token | 30 minutes | API requests | User permissions |
| Refresh Token | 7 days | Get new access token | Long-term access |

### JWT Token Structure

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9
  .eyJzdWIiOiJ1c2VyXzEyMyIsImlhdCI6MTcyNTMzMzI5NywiZXhwIjoxNzI1MzM1MDk3fQ
  .signature
```

**Decoded payload**:
```json
{
  "sub": "user_123",
  "username": "analyst_001",
  "scopes": ["read:projects", "write:entities"],
  "iat": 1725333297,
  "exp": 1725335097
}
```

### Login Flow

```
1. POST /auth/login
   └─> Returns access_token + refresh_token

2. Add to Authorization header
   └─> Authorization: Bearer {access_token}

3. When token expires (optional)
   └─> POST /auth/refresh
   └─> Returns new access_token
```

### Example: Complete Auth Flow

```python
import requests
import json
from datetime import datetime, timedelta

class AuthManager:
    def __init__(self, base_url, username, password):
        self.base_url = base_url
        self.username = username
        self.password = password
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = None
    
    def login(self):
        """Login and get tokens."""
        response = requests.post(
            f'{self.base_url}/auth/login',
            json={'username': self.username, 'password': self.password}
        )
        response.raise_for_status()
        
        data = response.json()
        self.access_token = data['access_token']
        self.refresh_token = data['refresh_token']
        
        # Calculate expiration time
        expires_in = data['expires_in']
        self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)
        
        print(f"Logged in, token expires at {self.token_expires_at}")
    
    def refresh(self):
        """Refresh access token."""
        response = requests.post(
            f'{self.base_url}/auth/refresh',
            json={'refresh_token': self.refresh_token}
        )
        response.raise_for_status()
        
        data = response.json()
        self.access_token = data['access_token']
        
        expires_in = data['expires_in']
        self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)
        
        print(f"Token refreshed, new expiration at {self.token_expires_at}")
    
    def get_headers(self):
        """Get authorization headers."""
        # Refresh if token about to expire (within 5 minutes)
        if datetime.now() + timedelta(minutes=5) > self.token_expires_at:
            self.refresh()
        
        return {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }

# Usage
auth = AuthManager('http://localhost:8080/api/v1', 'user', 'password')
auth.login()
headers = auth.get_headers()  # Auto-refreshes if needed
```

---

## HTTP Client Setup

### cURL

```bash
# Basic request
curl -H "Authorization: Bearer TOKEN" \
     http://localhost:8080/api/v1/projects

# With JSON body
curl -X POST \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "My Project"}' \
  http://localhost:8080/api/v1/projects

# Follow pagination
curl 'http://localhost:8080/api/v1/projects?limit=50&offset=0'
```

### Python (requests)

```python
import requests

headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}

# GET request
response = requests.get(
    'http://localhost:8080/api/v1/projects',
    headers=headers
)

# POST request
response = requests.post(
    'http://localhost:8080/api/v1/projects',
    headers=headers,
    json={'name': 'My Project'}
)

# Check status
if response.status_code == 200:
    data = response.json()
else:
    error = response.json()
    print(f"Error: {error['error']['code']}")
```

### JavaScript (fetch)

```javascript
const token = 'YOUR_JWT_TOKEN';

async function apiRequest(method, endpoint, body = null) {
  const headers = {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  };

  const options = {
    method,
    headers,
    ...(body && { body: JSON.stringify(body) })
  };

  const response = await fetch(
    `http://localhost:8080/api/v1${endpoint}`,
    options
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error.message);
  }

  return response.json();
}

// Usage
const projects = await apiRequest('GET', '/projects');
const newProject = await apiRequest('POST', '/projects', {
  name: 'My Project'
});
```

### JavaScript (axios)

```javascript
const axios = require('axios');

const client = axios.create({
  baseURL: 'http://localhost:8080/api/v1',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
});

// GET
const projects = await client.get('/projects');

// POST
const newProject = await client.post('/projects', {
  name: 'My Project'
});

// Error handling
client.interceptors.response.use(
  response => response,
  error => {
    if (error.response.status === 429) {
      // Rate limited
      const retryAfter = error.response.headers['retry-after'];
      console.log(`Rate limited, retry after ${retryAfter}s`);
    }
    return Promise.reject(error);
  }
);
```

---

## Request/Response Patterns

### Standard Request

```
METHOD /path
Content-Type: application/json
Authorization: Bearer {token}

{
  "field1": "value1",
  "field2": "value2"
}
```

### Standard Response (Success)

```json
{
  "status": "success",
  "data": {
    "id": "resource_123",
    "name": "Resource Name"
  },
  "meta": {
    "timestamp": "2026-05-19T12:00:00Z",
    "version": "3.0.0",
    "request_id": "req_abc123"
  }
}
```

### Standard Response (Error)

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "details": {
      "field": "value"
    }
  },
  "meta": {
    "timestamp": "2026-05-19T12:00:00Z",
    "request_id": "req_abc123"
  }
}
```

### Standard Response (List)

```json
{
  "status": "success",
  "data": [
    {"id": "item_1", "name": "Item 1"},
    {"id": "item_2", "name": "Item 2"}
  ],
  "meta": {
    "total_count": 1250,
    "limit": 10,
    "offset": 0,
    "page": 1,
    "page_size": 10,
    "total_pages": 125
  }
}
```

---

## Error Handling

### HTTP Status Codes

```python
def handle_response(response):
    if response.status_code == 200:
        return response.json()['data']
    
    elif response.status_code == 201:
        return response.json()['data']
    
    elif response.status_code == 204:
        return None  # No content
    
    elif response.status_code == 400:
        error = response.json()['error']
        raise ValueError(f"Bad request: {error['message']}")
    
    elif response.status_code == 401:
        # Refresh token and retry
        refresh_token()
        return retry_request(response.request)
    
    elif response.status_code == 404:
        raise LookupError(f"Resource not found")
    
    elif response.status_code == 429:
        # Rate limited - implement exponential backoff
        retry_after = int(response.headers.get('Retry-After', 60))
        print(f"Rate limited, retrying after {retry_after}s")
        time.sleep(retry_after)
        return retry_request(response.request)
    
    elif response.status_code == 500:
        raise RuntimeError(f"Server error: {response.text}")
    
    else:
        raise Exception(f"Unexpected status {response.status_code}")
```

### Error Codes Reference

Common error codes and handling:

```python
ERROR_HANDLERS = {
    'ENTITY_NOT_FOUND': lambda e: "Entity does not exist, verify ID",
    'PROJECT_NOT_FOUND': lambda e: "Project does not exist",
    'AUTHENTICATION_FAILED': lambda e: "Invalid credentials",
    'TOKEN_EXPIRED': lambda e: "Token expired, refresh and retry",
    'PERMISSION_DENIED': lambda e: "No permission for this resource",
    'INVALID_REQUEST': lambda e: f"Invalid request: {e['details']}",
    'DUPLICATE_ENTITY': lambda e: "Entity already exists",
    'RATE_LIMIT_EXCEEDED': lambda e: f"Rate limited, wait {e['details']['retry_after']}s",
    'DATABASE_ERROR': lambda e: "Database unavailable, try again later",
}

def handle_error(response):
    error = response.json()['error']
    code = error['code']
    
    if code in ERROR_HANDLERS:
        return ERROR_HANDLERS[code](error['details'])
    else:
        return error['message']
```

---

## Pagination & Filtering

### Basic Pagination

```python
def get_all_entities(project_id, page_size=50):
    """Fetch all entities with automatic pagination."""
    offset = 0
    
    while True:
        response = requests.get(
            f'http://localhost:8080/api/v1/projects/{project_id}/entities',
            params={
                'limit': page_size,
                'offset': offset
            },
            headers=headers
        )
        
        data = response.json()
        entities = data['data']
        
        if not entities:
            break
        
        for entity in entities:
            yield entity
        
        offset += page_size
```

### Advanced Pagination with Cursor

```python
def paginate_with_cursor(endpoint, page_size=50):
    """Paginate through results using cursor."""
    cursor = None
    
    while True:
        params = {'limit': page_size}
        if cursor:
            params['cursor'] = cursor
        
        response = requests.get(endpoint, params=params)
        data = response.json()
        
        for item in data['data']:
            yield item
        
        # Check for next page
        next_cursor = data['meta'].get('next_cursor')
        if not next_cursor:
            break
        
        cursor = next_cursor
```

### Filtering

```python
# Search with filters
response = requests.post(
    'http://localhost:8080/api/v1/projects/proj_123/search/advanced',
    headers=headers,
    json={
        'query': 'john',
        'filters': {
            'type': 'Person',
            'created_after': '2026-01-01T00:00:00Z'
        },
        'limit': 20,
        'offset': 0
    }
)

results = response.json()['data']
```

### Sorting

```python
# Sort by multiple fields
response = requests.get(
    'http://localhost:8080/api/v1/projects/proj_123/entities',
    params={
        'sort': '-created_at,name',  # Newest first, then by name
        'limit': 50
    },
    headers=headers
)
```

---

## Rate Limiting

### Monitor Rate Limit Headers

```python
def check_rate_limit(response):
    """Check rate limit info from response headers."""
    limit = response.headers.get('X-RateLimit-Limit')
    remaining = response.headers.get('X-RateLimit-Remaining')
    reset = response.headers.get('X-RateLimit-Reset')
    
    print(f"Limit: {limit} requests/min")
    print(f"Remaining: {remaining}")
    print(f"Resets at: {reset}")
    
    return int(remaining)
```

### Implement Backoff Strategy

```python
import time
import random

def api_call_with_backoff(url, max_retries=3, base_wait=1):
    """API call with exponential backoff for rate limiting."""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers)
            
            if response.status_code == 429:
                # Exponential backoff with jitter
                wait_time = base_wait * (2 ** attempt) + random.uniform(0, 1)
                print(f"Rate limited, waiting {wait_time:.1f}s")
                time.sleep(wait_time)
                continue
            
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                raise
            
            wait_time = base_wait * (2 ** attempt)
            print(f"Attempt {attempt + 1} failed, retrying in {wait_time}s")
            time.sleep(wait_time)
    
    raise Exception("Max retries exceeded")
```

### Batch Processing to Avoid Rate Limits

```python
def batch_create_entities(project_id, entities, batch_size=10):
    """Create entities in batches with delay between batches."""
    for i in range(0, len(entities), batch_size):
        batch = entities[i:i+batch_size]
        
        for entity in batch:
            response = requests.post(
                f'http://localhost:8080/api/v1/projects/{project_id}/entities',
                json=entity,
                headers=headers
            )
            
            if response.status_code != 201:
                print(f"Failed to create entity: {entity}")
        
        # Wait between batches to avoid rate limit
        if i + batch_size < len(entities):
            print(f"Batch {i//batch_size + 1} complete, waiting 10s...")
            time.sleep(10)
```

---

## WebSocket Integration

### JavaScript Example

```javascript
class BassetHoundWebSocket {
  constructor(projectId, token, baseUrl = 'ws://localhost:8080') {
    this.projectId = projectId;
    this.token = token;
    this.ws = null;
    this.messageHandlers = {};
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
  }

  connect() {
    const wsUrl = `${this.baseUrl.replace('http', 'ws')}/api/v1/projects/${this.projectId}/ws?token=${this.token}`;
    
    this.ws = new WebSocket(wsUrl);
    
    this.ws.onopen = () => {
      console.log('Connected to WebSocket');
      this.reconnectAttempts = 0;
    };
    
    this.ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      
      // Route to appropriate handler
      const handler = this.messageHandlers[message.type];
      if (handler) {
        handler(message.data);
      }
    };
    
    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
    
    this.ws.onclose = () => {
      console.log('Disconnected from WebSocket');
      this.attemptReconnect();
    };
  }

  subscribe(event, callback) {
    this.messageHandlers[event] = callback;
    
    // Send subscription message
    this.send({
      type: 'subscribe',
      event: event,
      filters: {}
    });
  }

  send(message) {
    if (this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }

  attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      const delay = Math.pow(2, this.reconnectAttempts) * 1000;
      console.log(`Reconnecting in ${delay}ms...`);
      setTimeout(() => this.connect(), delay);
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
    }
  }
}

// Usage
const ws = new BassetHoundWebSocket('proj_123', 'YOUR_TOKEN');
ws.connect();

ws.subscribe('entity.created', (entity) => {
  console.log('New entity created:', entity);
  // Update UI with new entity
});

ws.subscribe('entity.updated', (entity) => {
  console.log('Entity updated:', entity);
  // Update UI
});
```

### Python Example

```python
import websocket
import json
import threading

class BassetHoundWebSocketClient:
    def __init__(self, project_id, token, base_url='ws://localhost:8080'):
        self.project_id = project_id
        self.token = token
        self.base_url = base_url
        self.ws = None
        self.handlers = {}
    
    def connect(self):
        """Connect to WebSocket."""
        ws_url = f'{self.base_url}/api/v1/projects/{self.project_id}/ws?token={self.token}'
        
        self.ws = websocket.WebSocketApp(
            ws_url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        
        # Run in separate thread
        self.ws_thread = threading.Thread(target=self.ws.run_forever)
        self.ws_thread.daemon = True
        self.ws_thread.start()
    
    def on_open(self, ws):
        """Handle WebSocket open."""
        print('Connected to WebSocket')
    
    def on_message(self, ws, message):
        """Handle incoming message."""
        data = json.loads(message)
        event_type = data.get('type')
        
        if event_type in self.handlers:
            self.handlers[event_type](data.get('data'))
    
    def on_error(self, ws, error):
        """Handle WebSocket error."""
        print(f'WebSocket error: {error}')
    
    def on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket close."""
        print('Disconnected from WebSocket')
    
    def subscribe(self, event, callback):
        """Subscribe to event."""
        self.handlers[event] = callback
        self.send({
            'type': 'subscribe',
            'event': event,
            'filters': {}
        })
    
    def send(self, message):
        """Send message."""
        if self.ws:
            self.ws.send(json.dumps(message))

# Usage
ws = BassetHoundWebSocketClient('proj_123', 'YOUR_TOKEN')
ws.connect()

def on_entity_created(entity):
    print(f'Entity created: {entity}')

ws.subscribe('entity.created', on_entity_created)
```

---

## Webhook Integration

### Receive Webhook Events

```python
from flask import Flask, request, jsonify
import hmac
import hashlib

app = Flask(__name__)
WEBHOOK_SECRET = 'your_webhook_secret'

@app.route('/webhook', methods=['POST'])
def receive_webhook():
    """Receive and validate webhook event."""
    
    # Verify webhook signature
    signature = request.headers.get('X-Webhook-Signature')
    payload = request.get_data()
    
    expected_signature = hmac.new(
        WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    if signature != f'sha256={expected_signature}':
        return jsonify({'error': 'Invalid signature'}), 401
    
    # Process event
    event = request.json
    event_type = event['type']
    event_data = event['data']
    
    if event_type == 'entity.created':
        print(f'New entity: {event_data}')
        # Update database, send notification, etc.
    
    elif event_type == 'entity.updated':
        print(f'Updated entity: {event_data}')
    
    elif event_type == 'relationship.created':
        print(f'New relationship: {event_data}')
    
    return jsonify({'status': 'received'}), 200

if __name__ == '__main__':
    app.run(port=5000)
```

### Create Webhook Subscription

```bash
curl -X POST http://localhost:8080/api/v1/projects/proj_123/webhooks \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-server.com/webhook",
    "events": ["entity.created", "entity.updated"],
    "secret": "your_webhook_secret"
  }'
```

---

## Code Examples

### Complete Python Client

```python
import requests
import json
from typing import List, Dict, Optional
from datetime import datetime, timedelta

class BassetHoundAPI:
    """Complete Basset Hound API client."""
    
    def __init__(self, base_url: str, username: str = None, password: str = None):
        self.base_url = base_url
        self.session = requests.Session()
        self.token = None
        self.token_expires = None
        
        if username and password:
            self.login(username, password)
    
    def login(self, username: str, password: str):
        """Login and obtain JWT tokens."""
        response = self.session.post(
            f'{self.base_url}/auth/login',
            json={'username': username, 'password': password}
        )
        response.raise_for_status()
        
        data = response.json()
        self.token = data['access_token']
        self.token_expires = datetime.now() + timedelta(seconds=data['expires_in'])
        
        self._update_headers()
    
    def _update_headers(self):
        """Update session headers with current token."""
        self.session.headers.update({
            'Authorization': f'Bearer {self.token}' if self.token else None,
            'Content-Type': 'application/json'
        })
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """Make HTTP request with error handling."""
        url = f'{self.base_url}{endpoint}'
        response = self.session.request(method, url, **kwargs)
        
        if response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 60))
            raise RateLimitError(f'Rate limited, retry after {retry_after}s')
        
        if response.status_code >= 400:
            error = response.json().get('error', {})
            raise APIError(error.get('code'), error.get('message'))
        
        return response.json() if response.text else {}
    
    # Project endpoints
    def list_projects(self, limit=20, offset=0) -> List[Dict]:
        """Get all projects."""
        data = self._request('GET', '/projects', params={'limit': limit, 'offset': offset})
        return data.get('data', [])
    
    def create_project(self, name: str, description: str = None) -> Dict:
        """Create a new project."""
        payload = {'name': name}
        if description:
            payload['description'] = description
        
        data = self._request('POST', '/projects', json=payload)
        return data.get('data', {})
    
    def get_project(self, project_id: str) -> Dict:
        """Get project details."""
        data = self._request('GET', f'/projects/{project_id}')
        return data.get('data', {})
    
    # Entity endpoints
    def list_entities(self, project_id: str, limit=20, offset=0, **filters) -> List[Dict]:
        """Get entities in a project."""
        params = {'limit': limit, 'offset': offset}
        params.update(filters)
        
        data = self._request('GET', f'/projects/{project_id}/entities', params=params)
        return data.get('data', [])
    
    def create_entity(self, project_id: str, name: str, entity_type: str, **metadata) -> Dict:
        """Create an entity."""
        payload = {
            'name': name,
            'type': entity_type,
            'metadata': metadata
        }
        
        data = self._request('POST', f'/projects/{project_id}/entities', json=payload)
        return data.get('data', {})
    
    def update_entity(self, project_id: str, entity_id: str, **updates) -> Dict:
        """Update an entity."""
        data = self._request('PUT', f'/projects/{project_id}/entities/{entity_id}', json=updates)
        return data.get('data', {})
    
    # Search endpoints
    def search(self, project_id: str, query: str, limit=20, **filters) -> List[Dict]:
        """Search entities."""
        payload = {'query': query, 'limit': limit}
        payload.update(filters)
        
        data = self._request('POST', f'/projects/{project_id}/search/advanced', json=payload)
        return data.get('data', [])
    
    def autocomplete(self, project_id: str, query: str, limit=10) -> List[Dict]:
        """Get autocomplete suggestions."""
        params = {'q': query, 'limit': limit}
        data = self._request('GET', f'/projects/{project_id}/search/autocomplete', params=params)
        return data.get('data', [])
    
    # Export endpoints
    def export_json(self, project_id: str) -> Dict:
        """Export project as JSON."""
        return self.session.get(f'{self.base_url}/projects/{project_id}/export/json').json()
    
    def export_csv(self, project_id: str) -> str:
        """Export project as CSV."""
        return self.session.get(f'{self.base_url}/projects/{project_id}/export/csv').text

class APIError(Exception):
    """API error exception."""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f'{code}: {message}')

class RateLimitError(Exception):
    """Rate limit exception."""
    pass

# Usage
client = BassetHoundAPI('http://localhost:8080/api/v1')

# List projects
projects = client.list_projects()

# Create entity
entity = client.create_entity('proj_123', 'John Doe', 'Person', email='john@example.com')

# Search
results = client.search('proj_123', 'john', type='Person')
```

---

## Best Practices

### 1. Error Handling

```python
try:
    result = client.search('proj_123', 'query')
except APIError as e:
    if e.code == 'AUTHENTICATION_FAILED':
        # Re-authenticate
        client.login(username, password)
    elif e.code == 'RATE_LIMIT_EXCEEDED':
        # Wait and retry
        time.sleep(60)
    else:
        # Log and re-raise
        logger.error(f'API error: {e}')
        raise
except Exception as e:
    logger.error(f'Unexpected error: {e}')
```

### 2. Connection Pooling

```python
# Use persistent session
session = requests.Session()

# Reuse for multiple requests
for project_id in project_ids:
    response = session.get(f'http://localhost:8080/api/v1/projects/{project_id}')
    # Process response
```

### 3. Caching

```python
from functools import lru_cache
import time

class CachedClient:
    def __init__(self, client):
        self.client = client
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes
    
    def get_project(self, project_id):
        """Get project with caching."""
        cache_key = f'project:{project_id}'
        cached = self.cache.get(cache_key)
        
        if cached and time.time() - cached['time'] < self.cache_ttl:
            return cached['data']
        
        data = self.client.get_project(project_id)
        self.cache[cache_key] = {'data': data, 'time': time.time()}
        return data
```

### 4. Timeout Handling

```python
# Set timeouts on requests
response = requests.get(
    'http://localhost:8080/api/v1/projects',
    timeout=(5, 30)  # (connect timeout, read timeout)
)
```

### 5. Request Logging

```python
import logging

logging.basicConfig(level=logging.DEBUG)

# Log requests and responses
session = requests.Session()
session.hooks = {
    'response': lambda r, *args, **kwargs: print(
        f'{r.request.method} {r.url} -> {r.status_code}'
    )
}
```

---

## Troubleshooting

### Token Expired

```
Error: 401 Unauthorized
Message: Token expired
```

**Solution**:
```python
# Auto-refresh expired tokens
if response.status_code == 401:
    client.refresh_token()
    # Retry request
```

### Rate Limited

```
Error: 429 Too Many Requests
Message: Rate limit exceeded
```

**Solution**:
```python
# Implement backoff
import time
retry_after = int(response.headers['Retry-After'])
time.sleep(retry_after)
# Retry request
```

### Connection Timeout

```
Error: ConnectionError
Message: Connection timeout
```

**Solution**:
```python
# Increase timeout or check server health
response = requests.get(
    'http://localhost:8080/health',
    timeout=10
)
```

### SSL Certificate Error

```
Error: SSLError
Message: Certificate verification failed
```

**Solution**:
```python
# For development only
response = requests.get(
    'https://api.example.com',
    verify=False  # Disable SSL verification
)
```

---

**Last Updated**: 2026-05-19  
**Version**: 3.0.0
