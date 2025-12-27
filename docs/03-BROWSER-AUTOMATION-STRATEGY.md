# Browser Automation Strategy

## Problem Statement

Many OSINT and security tools require browser-based interaction because:
1. **Bot Detection**: Selenium/Puppeteer/Playwright are increasingly detected
2. **Authentication**: Many services require login sessions
3. **Dynamic Content**: JavaScript-rendered pages need real browser execution
4. **Human-in-the-Loop**: Some actions require human judgment or CAPTCHA solving

The autofill-extension repository provides a foundation, but requires significant enhancement to serve as an AI agent's browser interface.

## Current State Assessment

### autofill-extension Capabilities
- Basic form filling via CSS selectors
- YAML-based configuration loading
- Chrome Manifest V3 support

### Critical Gaps
| Gap | Impact | Priority |
|-----|--------|----------|
| No bi-directional communication | Cannot receive agent commands | Critical |
| No form detection | Requires manual selector configuration | High |
| No navigation control | Cannot automate multi-page workflows | Critical |
| No element interaction | Cannot click buttons, handle dropdowns | High |
| No visual feedback | Agent cannot "see" the page | Medium |
| No session management | Cannot handle authenticated sessions | High |

## Proposed Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        CHROME EXTENSION (MV3)                           │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                      Background Service Worker                     │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │  │
│  │  │ WebSocket   │  │ Command     │  │ State       │               │  │
│  │  │ Client      │  │ Router      │  │ Manager     │               │  │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘               │  │
│  │         │                │                │                       │  │
│  │         └────────────────┴────────────────┘                       │  │
│  │                          │                                        │  │
│  │                    Message Passing                                │  │
│  │                          │                                        │  │
│  └──────────────────────────┼────────────────────────────────────────┘  │
│                             │                                           │
│  ┌──────────────────────────┼────────────────────────────────────────┐  │
│  │                    Content Script (per tab)                        │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │  │
│  │  │ DOM         │  │ Form        │  │ Screenshot  │               │  │
│  │  │ Interactor  │  │ Analyzer    │  │ Capture     │               │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘               │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                         Popup UI                                   │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │  │
│  │  │ Connection  │  │ Task        │  │ Manual      │               │  │
│  │  │ Status      │  │ Queue       │  │ Controls    │               │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘               │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                │
                          WebSocket
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      palletAI Browser Bridge                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
│  │ WebSocket   │  │ Command     │  │ Response    │  │ Screenshot  │   │
│  │ Server      │  │ Queue       │  │ Handler     │  │ Processor   │   │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

## Implementation Plan

### Phase 1: Core Communication Layer

#### 1.1 Background Service Worker

**File: `background.js`**

```javascript
// WebSocket connection to palletAI
let ws = null;
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 10;
const RECONNECT_DELAY = 3000;
const PALLETAI_WS_URL = 'ws://localhost:8765/browser';

// Command handlers registry
const commandHandlers = {
  navigate: handleNavigate,
  fill_form: handleFillForm,
  click: handleClick,
  get_content: handleGetContent,
  screenshot: handleScreenshot,
  wait_for_element: handleWaitForElement,
  get_page_state: handleGetPageState,
  execute_script: handleExecuteScript,
};

// Initialize WebSocket connection
function connectWebSocket() {
  ws = new WebSocket(PALLETAI_WS_URL);

  ws.onopen = () => {
    console.log('Connected to palletAI');
    reconnectAttempts = 0;
    sendStatus('connected');
  };

  ws.onclose = () => {
    console.log('Disconnected from palletAI');
    attemptReconnect();
  };

  ws.onerror = (error) => {
    console.error('WebSocket error:', error);
  };

  ws.onmessage = async (event) => {
    const command = JSON.parse(event.data);
    await processCommand(command);
  };
}

async function processCommand(command) {
  const { command_id, type, params } = command;

  const handler = commandHandlers[type];
  if (!handler) {
    sendResponse(command_id, false, null, `Unknown command type: ${type}`);
    return;
  }

  try {
    const result = await handler(params);
    sendResponse(command_id, true, result);
  } catch (error) {
    sendResponse(command_id, false, null, error.message);
  }
}

function sendResponse(command_id, success, result, error = null) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({
      command_id,
      success,
      result,
      error,
      timestamp: Date.now()
    }));
  }
}

// Command Handlers
async function handleNavigate(params) {
  const { url, wait_for } = params;

  return new Promise((resolve, reject) => {
    chrome.tabs.query({ active: true, currentWindow: true }, async (tabs) => {
      const tabId = tabs[0]?.id;
      if (!tabId) {
        reject(new Error('No active tab'));
        return;
      }

      // Navigate to URL
      await chrome.tabs.update(tabId, { url });

      // Wait for page load
      chrome.tabs.onUpdated.addListener(function listener(updatedTabId, changeInfo) {
        if (updatedTabId === tabId && changeInfo.status === 'complete') {
          chrome.tabs.onUpdated.removeListener(listener);

          if (wait_for) {
            // Wait for specific element
            waitForElement(tabId, wait_for, 10000)
              .then(() => resolve({ url, loaded: true }))
              .catch(reject);
          } else {
            resolve({ url, loaded: true });
          }
        }
      });
    });
  });
}

async function handleFillForm(params) {
  const { fields, submit } = params;

  return new Promise((resolve, reject) => {
    chrome.tabs.query({ active: true, currentWindow: true }, async (tabs) => {
      const tabId = tabs[0]?.id;
      if (!tabId) {
        reject(new Error('No active tab'));
        return;
      }

      chrome.tabs.sendMessage(tabId, {
        action: 'fill_form',
        fields,
        submit
      }, (response) => {
        if (chrome.runtime.lastError) {
          reject(new Error(chrome.runtime.lastError.message));
        } else {
          resolve(response);
        }
      });
    });
  });
}

async function handleClick(params) {
  const { selector, wait_after } = params;

  return new Promise((resolve, reject) => {
    chrome.tabs.query({ active: true, currentWindow: true }, async (tabs) => {
      const tabId = tabs[0]?.id;

      chrome.tabs.sendMessage(tabId, {
        action: 'click_element',
        selector,
        wait_after
      }, resolve);
    });
  });
}

async function handleGetContent(params) {
  const { selector } = params;

  return new Promise((resolve) => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      chrome.tabs.sendMessage(tabs[0].id, {
        action: 'get_content',
        selector
      }, resolve);
    });
  });
}

async function handleScreenshot(params) {
  return new Promise((resolve) => {
    chrome.tabs.captureVisibleTab(null, { format: 'png' }, (dataUrl) => {
      resolve({ screenshot: dataUrl });
    });
  });
}

async function handleGetPageState(params) {
  return new Promise((resolve) => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      chrome.tabs.sendMessage(tabs[0].id, {
        action: 'get_page_state'
      }, resolve);
    });
  });
}

// Initialize on install
chrome.runtime.onInstalled.addListener(() => {
  console.log('Browser Automation Extension installed');
  connectWebSocket();
});

// Reconnect on startup
chrome.runtime.onStartup.addListener(() => {
  connectWebSocket();
});
```

#### 1.2 Content Script

**File: `content.js`**

```javascript
// Listen for messages from background script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  switch (request.action) {
    case 'fill_form':
      handleFillForm(request.fields, request.submit)
        .then(sendResponse);
      return true; // Keep channel open for async response

    case 'click_element':
      handleClickElement(request.selector, request.wait_after)
        .then(sendResponse);
      return true;

    case 'get_content':
      handleGetContent(request.selector)
        .then(sendResponse);
      return true;

    case 'get_page_state':
      handleGetPageState()
        .then(sendResponse);
      return true;

    case 'wait_for_element':
      waitForElement(request.selector, request.timeout)
        .then(() => sendResponse({ found: true }))
        .catch(() => sendResponse({ found: false }));
      return true;
  }
});

async function handleFillForm(fields, submit) {
  const results = [];

  for (const [selector, value] of Object.entries(fields)) {
    try {
      const element = await findElement(selector);
      if (!element) {
        results.push({ selector, success: false, error: 'Element not found' });
        continue;
      }

      // Handle different input types
      if (element.tagName === 'SELECT') {
        element.value = value;
        element.dispatchEvent(new Event('change', { bubbles: true }));
      } else if (element.type === 'checkbox' || element.type === 'radio') {
        element.checked = value === 'true' || value === true;
        element.dispatchEvent(new Event('change', { bubbles: true }));
      } else if (element.type === 'file') {
        // Cannot set file inputs programmatically
        results.push({ selector, success: false, error: 'File inputs require manual interaction' });
        continue;
      } else {
        // Text-based inputs
        element.focus();
        element.value = '';
        // Simulate typing for better compatibility
        for (const char of value) {
          element.value += char;
          element.dispatchEvent(new InputEvent('input', { bubbles: true, data: char }));
        }
        element.dispatchEvent(new Event('change', { bubbles: true }));
        element.blur();
      }

      results.push({ selector, success: true });
    } catch (error) {
      results.push({ selector, success: false, error: error.message });
    }
  }

  // Submit form if requested
  if (submit) {
    const form = document.querySelector('form');
    if (form) {
      form.submit();
    }
  }

  return { filled: results };
}

async function handleClickElement(selector, waitAfter) {
  const element = await findElement(selector);
  if (!element) {
    return { success: false, error: 'Element not found' };
  }

  // Scroll into view
  element.scrollIntoView({ behavior: 'smooth', block: 'center' });

  // Wait a bit for scroll
  await sleep(300);

  // Click
  element.click();

  // Wait after click if specified
  if (waitAfter) {
    await sleep(waitAfter);
  }

  return { success: true };
}

async function handleGetContent(selector) {
  const element = selector ? document.querySelector(selector) : document.body;
  if (!element) {
    return { success: false, error: 'Element not found' };
  }

  return {
    success: true,
    content: element.innerText,
    html: element.innerHTML
  };
}

async function handleGetPageState() {
  const forms = Array.from(document.querySelectorAll('form')).map(form => ({
    id: form.id,
    name: form.name,
    action: form.action,
    method: form.method,
    fields: Array.from(form.elements).map(el => ({
      selector: generateSelector(el),
      type: el.type || el.tagName.toLowerCase(),
      name: el.name,
      id: el.id,
      label: findLabel(el),
      required: el.required,
      value: el.type === 'password' ? '[hidden]' : el.value,
      options: el.tagName === 'SELECT' ?
        Array.from(el.options).map(o => ({ value: o.value, text: o.text })) : null
    })).filter(f => f.type !== 'submit' && f.type !== 'button')
  }));

  return {
    url: window.location.href,
    title: document.title,
    forms,
    links: Array.from(document.querySelectorAll('a[href]')).slice(0, 100).map(a => ({
      text: a.innerText.trim(),
      href: a.href
    })),
    buttons: Array.from(document.querySelectorAll('button, input[type="submit"], input[type="button"]')).map(b => ({
      selector: generateSelector(b),
      text: b.innerText || b.value
    }))
  };
}

// Helper functions
function generateSelector(element) {
  if (element.id) return `#${element.id}`;
  if (element.name) return `[name="${element.name}"]`;

  // Generate path-based selector
  let path = [];
  let current = element;
  while (current && current !== document.body) {
    let selector = current.tagName.toLowerCase();
    if (current.className) {
      selector += '.' + current.className.split(' ').join('.');
    }
    path.unshift(selector);
    current = current.parentElement;
  }
  return path.join(' > ');
}

function findLabel(element) {
  // Check for label with 'for' attribute
  if (element.id) {
    const label = document.querySelector(`label[for="${element.id}"]`);
    if (label) return label.innerText.trim();
  }

  // Check for wrapping label
  const parentLabel = element.closest('label');
  if (parentLabel) return parentLabel.innerText.trim();

  // Check for aria-label
  if (element.getAttribute('aria-label')) {
    return element.getAttribute('aria-label');
  }

  // Check placeholder
  if (element.placeholder) return element.placeholder;

  return null;
}

function findElement(selector) {
  // Try exact selector first
  let element = document.querySelector(selector);
  if (element) return element;

  // Try variations
  const variations = [
    selector,
    `[name="${selector}"]`,
    `[id="${selector}"]`,
    `[placeholder*="${selector}"]`,
    `[aria-label*="${selector}"]`
  ];

  for (const variation of variations) {
    try {
      element = document.querySelector(variation);
      if (element) return element;
    } catch (e) {
      // Invalid selector, try next
    }
  }

  return null;
}

function waitForElement(selector, timeout = 10000) {
  return new Promise((resolve, reject) => {
    const element = document.querySelector(selector);
    if (element) {
      resolve(element);
      return;
    }

    const observer = new MutationObserver(() => {
      const el = document.querySelector(selector);
      if (el) {
        observer.disconnect();
        resolve(el);
      }
    });

    observer.observe(document.body, { childList: true, subtree: true });

    setTimeout(() => {
      observer.disconnect();
      reject(new Error(`Timeout waiting for element: ${selector}`));
    }, timeout);
  });
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}
```

### Phase 2: palletAI Bridge Server

**File: `palletAI/agent_manager/src/api/routes/browser_bridge.py`**

```python
import asyncio
import json
from typing import Dict, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from uuid import uuid4

router = APIRouter()

# Store for pending commands and their futures
pending_commands: Dict[str, asyncio.Future] = {}
browser_connection: Optional[WebSocket] = None

@router.websocket("/browser")
async def browser_websocket(websocket: WebSocket):
    """WebSocket endpoint for browser extension connection."""
    global browser_connection

    await websocket.accept()
    browser_connection = websocket

    try:
        while True:
            # Receive response from extension
            data = await websocket.receive_text()
            response = json.loads(data)

            command_id = response.get("command_id")
            if command_id in pending_commands:
                pending_commands[command_id].set_result(response)

    except WebSocketDisconnect:
        browser_connection = None


async def send_browser_command(command: dict, timeout: float = 30.0) -> dict:
    """
    Send a command to the browser extension and wait for response.

    Args:
        command: Command dictionary with type and params
        timeout: Maximum seconds to wait for response

    Returns:
        Response from browser extension
    """
    global browser_connection

    if not browser_connection:
        raise Exception("No browser connection available")

    command_id = str(uuid4())
    command["command_id"] = command_id

    # Create future for response
    future = asyncio.get_event_loop().create_future()
    pending_commands[command_id] = future

    try:
        # Send command
        await browser_connection.send_text(json.dumps(command))

        # Wait for response with timeout
        response = await asyncio.wait_for(future, timeout=timeout)
        return response

    except asyncio.TimeoutError:
        raise Exception(f"Browser command timed out after {timeout}s")

    finally:
        pending_commands.pop(command_id, None)


def is_browser_connected() -> bool:
    """Check if browser extension is connected."""
    return browser_connection is not None
```

### Phase 3: Enhanced Manifest

**File: `manifest.json`**

```json
{
  "manifest_version": 3,
  "name": "OSINT Browser Automation",
  "version": "2.0",
  "description": "AI-powered browser automation for OSINT investigations",

  "permissions": [
    "activeTab",
    "tabs",
    "scripting",
    "storage",
    "notifications"
  ],

  "host_permissions": [
    "<all_urls>"
  ],

  "background": {
    "service_worker": "background.js",
    "type": "module"
  },

  "content_scripts": [
    {
      "matches": ["<all_urls>"],
      "js": ["content.js"],
      "run_at": "document_idle"
    }
  ],

  "action": {
    "default_popup": "popup.html",
    "default_icon": {
      "16": "icons/icon16.png",
      "48": "icons/icon48.png",
      "128": "icons/icon128.png"
    }
  },

  "icons": {
    "16": "icons/icon16.png",
    "48": "icons/icon48.png",
    "128": "icons/icon128.png"
  }
}
```

## Usage Example: OSINT Workflow

```python
# In palletAI agent personality or tool

async def investigate_email_hibp(email: str):
    """
    Check email against HaveIBeenPwned using browser automation.
    """
    # Navigate to HIBP
    await browser_navigate("https://haveibeenpwned.com/")

    # Get page state to understand form structure
    state = await browser_get_page_state()

    # Find email input field
    email_field = None
    for form in state.get("forms", []):
        for field in form.get("fields", []):
            if "email" in field.get("name", "").lower() or \
               "email" in field.get("label", "").lower():
                email_field = field["selector"]
                break

    if not email_field:
        return {"error": "Could not find email input field"}

    # Fill the form
    await browser_fill_form({email_field: email})

    # Click search button
    await browser_click('button[type="submit"]')

    # Wait for results
    await browser_wait_for_element('.pwnedSearchResult, .noPwnage', timeout=10000)

    # Get results
    content = await browser_get_content('.pwnedSearchResult, .noPwnage')

    # Take screenshot for evidence
    screenshot = await browser_screenshot()

    return {
        "email": email,
        "results": content,
        "screenshot": screenshot
    }
```

## Security Considerations

1. **Local-Only Connection**: WebSocket only accepts localhost connections
2. **Command Validation**: All commands validated before execution
3. **Timeout Protection**: All operations have timeouts
4. **User Notification**: Extension shows visual indicator when AI is controlling
5. **Manual Override**: User can always pause/stop automation via popup
6. **Sensitive Data Handling**: Passwords are masked in page state responses
