# basset-hound-browser Integration (Stream 8)

This document describes the integration between Basset Hound and basset-hound-browser, an Electron-based web browser designed for OSINT automation with bot detection evasion.

## Overview

basset-hound-browser is a specialized browser built on Electron that provides:

- **WebSocket API** for remote browser control (port 8765)
- **Bot detection evasion** with fingerprint spoofing and human-like behavior
- **OSINT capabilities** including screenshots, content extraction, and automation
- **Profile management** for multi-account operations
- **Network monitoring** with HAR export support
- **Proxy and user agent support** for identity management

Basset Hound integrates with this browser via a WebSocket client that enables:

- Automated web navigation and interaction
- Screenshot and evidence capture
- Form auto-fill with entity data
- Content extraction for intelligence analysis
- Network request logging

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│ Basset Hound API (FastAPI)                                  │
├─────────────────────────────────────────────────────────────┤
│ • api/clients/basset_hound_browser_client.py                │
│   └─ BrowserClient: Async WebSocket client                  │
│                                                              │
│ • api/routers/browser_actions.py                            │
│   └─ HTTP endpoints for browser control                     │
│       ├─ GET  /api/v1/browser/status                        │
│       ├─ POST /api/v1/browser/screenshot                    │
│       ├─ POST /api/v1/browser/navigate                      │
│       ├─ POST /api/v1/browser/capture                       │
│       ├─ POST /api/v1/browser/fill                          │
│       ├─ POST /api/v1/browser/click                         │
│       ├─ GET  /api/v1/browser/sessions                      │
│       └─ POST /api/v1/browser/execute                       │
└──────────────────────┬──────────────────────────────────────┘
                       │ WebSocket
                       │ (JSON RPC)
                       ↓
┌──────────────────────────────────────────────────────────────┐
│ basset-hound-browser (Electron App)                          │
├──────────────────────────────────────────────────────────────┤
│ • WebSocket Server (ws://localhost:8765)                    │
│ • 300+ automation commands                                   │
│ • Bot detection evasion                                      │
│ • Profile management                                         │
│ • Network monitoring                                         │
└──────────────────────────────────────────────────────────────┘
```

### Request/Response Flow

```
Client Request
    │
    ↓
[HTTP POST] → browser_actions router
    │
    ↓
BrowserClient (async WebSocket client)
    │
    ├─ Generate request ID
    ├─ Create request message
    ├─ Send via WebSocket
    └─ Wait for response (async)
    │
    ↓
[WebSocket] → basset-hound-browser
    │
    ├─ Parse command
    ├─ Execute action
    └─ Send response
    │
    ↓
[WebSocket] → BrowserClient
    │
    ├─ Receive response
    ├─ Match to request ID
    └─ Resolve future
    │
    ↓
HTTP Response → Client
```

## Setup

### Prerequisites

1. **basset-hound-browser running** on `ws://localhost:8765`
   ```bash
   cd basset-hound-browser
   npm install
   npm start
   ```

2. **Python WebSocket library**
   ```bash
   pip install websockets>=12.0
   ```

### Configuration

#### Environment Variables

Add to `.env`:

```bash
# Browser WebSocket connection
BASSET_BROWSER_WS_URL=ws://localhost:8765

# Optional: Authentication token (if browser requires it)
BASSET_BROWSER_WS_TOKEN=your-token-here

# Optional: Custom timeout (default 10 seconds)
# BASSET_BROWSER_WS_TIMEOUT=10.0
```

#### Default Values

If environment variables are not set:

```python
ws_url = os.getenv("BASSET_BROWSER_WS_URL", "ws://localhost:8765")
token = os.getenv("BASSET_BROWSER_WS_TOKEN", None)
timeout = 10.0
```

## HTTP API Reference

### Health Check

**Endpoint:** `GET /api/v1/browser/status`

**Description:** Check if browser is running and responsive

**Response:**
```json
{
  "status": "healthy|unhealthy|unavailable|error",
  "message": "Optional status message",
  "browser_info": {
    "version": "1.0.0",
    "uptime": 12345,
    "tabs": 2
  }
}
```

**Status Codes:**
- `200 OK` - Status retrieved (regardless of health)
- `500 Internal Server Error` - Unexpected error

### Navigate

**Endpoint:** `POST /api/v1/browser/navigate`

**Request:**
```json
{
  "url": "https://example.com",
  "wait_until": "load"
}
```

**Response:**
```json
{
  "url": "https://example.com",
  "success": true,
  "timestamp": "2026-05-06T12:34:56.789012"
}
```

**Status Codes:**
- `200 OK` - Navigation successful
- `503 Service Unavailable` - Browser not available
- `500 Internal Server Error` - Navigation failed

### Screenshot

**Endpoint:** `POST /api/v1/browser/screenshot`

**Request:**
```json
{
  "url": "https://example.com",
  "full_page": false
}
```

**Response:**
```json
{
  "image": "iVBORw0KGgoAAAANSUhEUgAAAAEA...",
  "format": "base64",
  "full_page": false,
  "timestamp": "2026-05-06T12:34:56.789012"
}
```

**Parameters:**
- `url` (optional): Navigate to URL before taking screenshot
- `full_page` (boolean): Capture full page (default: false)

**Status Codes:**
- `200 OK` - Screenshot captured
- `503 Service Unavailable` - Browser not available
- `500 Internal Server Error` - Screenshot failed

### Capture Evidence

**Endpoint:** `POST /api/v1/browser/capture`

**Description:** Capture comprehensive evidence including screenshot, extracted content, and network logs

**Request:**
```json
{
  "url": "https://example.com",
  "project_id": "my-investigation",
  "entity_id": "entity-123",
  "description": "Evidence from target website"
}
```

**Response:**
```json
{
  "evidence_id": "a1b2c3d4e5f6g7h8",
  "url": "https://example.com",
  "screenshot_size": 102400,
  "content_extracted": true,
  "network_requests": 45,
  "timestamp": "2026-05-06T12:34:56.789012"
}
```

**Status Codes:**
- `200 OK` - Evidence captured and stored
- `503 Service Unavailable` - Browser not available
- `500 Internal Server Error` - Capture failed

### Fill Form

**Endpoint:** `POST /api/v1/browser/fill`

**Description:** Auto-fill form fields with provided values

**Request:**
```json
{
  "fields": {
    "#email": "test@example.com",
    "#password": "password123"
  },
  "click_submit": true,
  "submit_selector": "button[type='submit']"
}
```

**Response:**
```json
{
  "#email": "filled",
  "#password": "filled",
  "__submit__": "clicked"
}
```

**Status Codes:**
- `200 OK` - Form filled (partial or full success)
- `503 Service Unavailable` - Browser not available
- `500 Internal Server Error` - Fill operation failed

### Click Element

**Endpoint:** `POST /api/v1/browser/click`

**Request:**
```json
{
  "selector": "button.submit",
  "wait_after": 2000
}
```

**Response:**
```json
{
  "selector": "button.submit",
  "success": true,
  "timestamp": "2026-05-06T12:34:56.789012"
}
```

**Status Codes:**
- `200 OK` - Element clicked
- `503 Service Unavailable` - Browser not available
- `500 Internal Server Error` - Click failed

### Execute JavaScript

**Endpoint:** `POST /api/v1/browser/execute`

**Description:** Execute arbitrary JavaScript in browser context

**Request:**
```json
{
  "script": "return window.location.href"
}
```

**Response:**
```json
{
  "success": true,
  "result": "https://example.com",
  "error": null
}
```

**Status Codes:**
- `200 OK` - Script executed
- `503 Service Unavailable` - Browser not available
- `500 Internal Server Error` - Execution failed

### List Sessions

**Endpoint:** `GET /api/v1/browser/sessions`

**Response:**
```json
{
  "sessions": [
    {
      "id": "session-123",
      "name": "Default Session",
      "url": "https://example.com",
      "active": true
    }
  ]
}
```

**Status Codes:**
- `200 OK` - Sessions listed
- `503 Service Unavailable` - Browser not available
- `500 Internal Server Error` - Failed to retrieve sessions

## Python Client Usage

### Basic Example

```python
from api.clients.basset_hound_browser_client import get_browser_client

async def capture_website():
    async with get_browser_client() as client:
        if not client:
            print("Browser not available")
            return
        
        # Navigate to URL
        await client.navigate("https://example.com")
        
        # Take screenshot
        image_base64 = await client.screenshot(full_page=True)
        
        # Extract content
        content = await client.extract_all()
        
        print(f"Captured {len(image_base64)} bytes")
        print(f"Extracted {len(content)} characters")
```

### Direct Client Usage

```python
from api.clients.basset_hound_browser_client import BrowserClient

async def direct_usage():
    client = BrowserClient(
        ws_url="ws://localhost:8765",
        token=None,
        timeout=10.0
    )
    
    try:
        await client.connect()
        
        # Use any command
        await client.navigate("https://example.com")
        
        # Check health
        is_healthy = await client.health_check()
        print(f"Browser healthy: {is_healthy}")
        
    finally:
        await client.disconnect()
```

## Command Reference

### Navigation Commands

- `navigate(url)` - Navigate to URL
- `get_url()` - Get current URL
- `back()` - Navigate back
- `forward()` - Navigate forward
- `refresh()` - Refresh page

### Interaction Commands

- `click(selector)` - Click element by selector
- `fill(selector, value)` - Fill form field
- `type(selector, text, delay)` - Type text with delay
- `scroll(direction, amount)` - Scroll page
- `wait_for_selector(selector, timeout)` - Wait for element

### Data Extraction Commands

- `screenshot(full_page)` - Take screenshot
- `extract_all()` - Extract all page content
- `get_page_state()` - Get full page state
- `get_cookies()` - Get page cookies
- `get_network_logs()` - Get network requests

### Session Commands

- `list_sessions()` - List active sessions
- `create_session(name)` - Create new session
- `switch_session(id)` - Switch to session

### Execution Commands

- `execute_script(script)` - Execute JavaScript

## Graceful Degradation

The integration is designed to gracefully degrade when the browser is unavailable:

1. **Connection Failure:** If the browser is not running, `get_browser_client()` returns `None` instead of raising an error

2. **HTTP Endpoints:** Return `503 Service Unavailable` when browser is down

3. **No Impact on Other Systems:** OSINT operations can continue without the browser

Example:
```python
async with get_browser_client() as client:
    if client:
        screenshot = await client.screenshot()
    else:
        # Browser not available, use fallback
        screenshot = None
        log_warning("Browser unavailable, skipping screenshot capture")
```

## Evidence Storage

### File Structure

Evidence is stored in the project directory:

```
projects/
  my-investigation/
    evidence/
      a1b2c3d4e5f6g7h8_screenshot.png
      a1b2c3d4e5f6g7h8_metadata.json
```

### Metadata Format

```json
{
  "id": "a1b2c3d4e5f6g7h8",
  "url": "https://example.com",
  "timestamp": "2026-05-06T12:34:56.789012",
  "description": "Evidence from target website",
  "screenshot_file": "a1b2c3d4e5f6g7h8_screenshot.png",
  "screenshot_size": 102400,
  "extracted_content": {
    "text": "Page text content",
    "html": "<html>...</html>",
    "metadata": {}
  },
  "network_requests": 45
}
```

### Neo4j Integration (Future)

Evidence nodes will be created with relationships:

```cypher
(Entity) -[CAPTURED_FROM]-> (Evidence)
(Evidence) {
  evidence_id: string,
  url: string,
  timestamp: datetime,
  screenshot_path: string,
  content_extracted: boolean,
  network_request_count: integer
}
```

## Testing

### Run Integration Tests

```bash
# Run all tests
pytest tests/integration/test_browser_integration.py

# Run specific test
pytest tests/integration/test_browser_integration.py::TestBrowserClient::test_client_initialization

# Skip browser tests (if browser not running)
pytest --skip-browser-tests
```

### Test Browser Availability

```bash
curl http://localhost:8000/api/v1/browser/status
```

## Troubleshooting

### Browser Not Responding

1. **Check if browser is running:**
   ```bash
   lsof -i :8765
   ```

2. **Restart browser:**
   ```bash
   cd basset-hound-browser
   npm start
   ```

3. **Check connection:**
   ```bash
   nc -zv localhost 8765
   ```

### Connection Timeout

- Increase timeout in client: `BrowserClient(timeout=30.0)`
- Check network latency
- Verify WebSocket URL is correct

### Screenshot Failures

- Check browser has loaded page completely
- Ensure element selectors are correct
- Verify page is not behind authentication

### Memory Issues

- Browser may accumulate memory with many screenshots
- Restart browser periodically
- Clear browser cache and history

## API Documentation

### OpenAPI/Swagger

Browser API endpoints are documented in Swagger UI:

```
http://localhost:8000/docs
```

Search for `/browser` endpoints to view:
- Request/response schemas
- Example usage
- Error codes

## Future Enhancements

- [ ] Neo4j evidence node integration
- [ ] Evidence version control and comparison
- [ ] Screenshot annotation tools
- [ ] OCR extraction from screenshots
- [ ] Automated form field detection
- [ ] Multi-browser session orchestration
- [ ] Evidence chain of custody tracking

## Security Considerations

### Authentication

1. **Token-based auth** (optional): Set `BASSET_BROWSER_WS_TOKEN` for authenticated connections

2. **Network security**: Keep browser on localhost or trusted network

3. **Data sensitivity**: Screenshots may contain sensitive information
   - Implement access controls
   - Encrypt evidence storage
   - Audit evidence access

### Data Privacy

- Evidence files are stored locally
- Network logs may contain sensitive URLs
- Consider encryption for evidence storage

## References

- [basset-hound-browser README](../basset-hound-browser/README.md)
- [WebSocket API Documentation](../basset-hound-browser/docs/API.md)
- [Stream 8: Browser Integration Design](./stream-8-design.md)

## Contributing

To add new browser commands:

1. Add method to `BrowserClient` in `api/clients/basset_hound_browser_client.py`
2. Add HTTP endpoint to `api/routers/browser_actions.py`
3. Add tests to `tests/integration/test_browser_integration.py`
4. Update this documentation

## License

Part of the Basset Hound OSINT toolkit.
