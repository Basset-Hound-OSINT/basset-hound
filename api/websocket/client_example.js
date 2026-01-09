/**
 * WebSocket Client Example for Phase 45: Real-Time Notifications
 *
 * This example demonstrates how to connect to the WebSocket suggestion events
 * endpoint and handle real-time notifications for suggestions and linking actions.
 *
 * Usage:
 *   const client = new SuggestionWebSocketClient('proj_123');
 *   client.onSuggestionGenerated((data) => {
 *     console.log('New suggestions:', data);
 *     // Update UI with new suggestions
 *   });
 *   client.connect();
 *
 * Phase 45: WebSocket Real-Time Notifications
 */

class SuggestionWebSocketClient {
  /**
   * Create a new WebSocket client for suggestion events.
   *
   * @param {string} projectId - The project ID to subscribe to
   * @param {object} options - Configuration options
   * @param {string} options.url - WebSocket server URL (default: ws://localhost:8000)
   * @param {string} options.token - Optional authentication token
   * @param {number} options.reconnectInterval - Initial reconnect interval in ms (default: 1000)
   * @param {number} options.maxReconnectInterval - Max reconnect interval in ms (default: 30000)
   * @param {number} options.heartbeatInterval - Heartbeat interval in ms (default: 30000)
   */
  constructor(projectId, options = {}) {
    this.projectId = projectId;
    this.url = options.url || 'ws://localhost:8000';
    this.token = options.token || null;
    this.reconnectInterval = options.reconnectInterval || 1000;
    this.maxReconnectInterval = options.maxReconnectInterval || 30000;
    this.heartbeatInterval = options.heartbeatInterval || 30000;

    this.ws = null;
    this.connectionId = null;
    this.reconnectAttempts = 0;
    this.reconnectTimer = null;
    this.heartbeatTimer = null;
    this.entitySubscriptions = new Set();

    // Event handlers
    this.handlers = {
      connected: [],
      disconnected: [],
      suggestion_generated: [],
      suggestion_dismissed: [],
      entity_merged: [],
      data_linked: [],
      orphan_linked: [],
      error: []
    };
  }

  /**
   * Connect to the WebSocket server.
   */
  connect() {
    // Build WebSocket URL
    let wsUrl = `${this.url}/api/v1/ws/suggestions/${this.projectId}`;
    if (this.token) {
      wsUrl += `?token=${encodeURIComponent(this.token)}`;
    }

    console.log(`[WebSocket] Connecting to ${wsUrl}...`);
    this.ws = new WebSocket(wsUrl);

    // Connection opened
    this.ws.addEventListener('open', (event) => {
      console.log('[WebSocket] Connection established');
      this.reconnectAttempts = 0;
      this.startHeartbeat();
    });

    // Listen for messages
    this.ws.addEventListener('message', (event) => {
      try {
        const message = JSON.parse(event.data);
        this.handleMessage(message);
      } catch (error) {
        console.error('[WebSocket] Error parsing message:', error);
      }
    });

    // Connection closed
    this.ws.addEventListener('close', (event) => {
      console.log('[WebSocket] Connection closed', event.code, event.reason);
      this.stopHeartbeat();
      this.triggerHandlers('disconnected', { code: event.code, reason: event.reason });

      // Attempt to reconnect with exponential backoff
      this.reconnect();
    });

    // Connection error
    this.ws.addEventListener('error', (event) => {
      console.error('[WebSocket] Error:', event);
      this.triggerHandlers('error', { error: event });
    });
  }

  /**
   * Disconnect from the WebSocket server.
   */
  disconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    this.stopHeartbeat();

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  /**
   * Reconnect with exponential backoff.
   */
  reconnect() {
    if (this.reconnectTimer) {
      return; // Already scheduled
    }

    this.reconnectAttempts++;
    const delay = Math.min(
      this.reconnectInterval * Math.pow(2, this.reconnectAttempts - 1),
      this.maxReconnectInterval
    );

    console.log(`[WebSocket] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})...`);

    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, delay);
  }

  /**
   * Start heartbeat (ping/pong) to keep connection alive.
   */
  startHeartbeat() {
    this.stopHeartbeat();

    this.heartbeatTimer = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.send({
          type: 'ping',
          timestamp: Date.now()
        });
      }
    }, this.heartbeatInterval);
  }

  /**
   * Stop heartbeat timer.
   */
  stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  /**
   * Send a message to the server.
   */
  send(message) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.warn('[WebSocket] Cannot send message - not connected');
    }
  }

  /**
   * Handle incoming messages from the server.
   */
  handleMessage(message) {
    const { type, data, project_id, entity_id, timestamp } = message;

    switch (type) {
      case 'connected':
        this.connectionId = data.connection_id;
        console.log(`[WebSocket] Connected with ID: ${this.connectionId}`);
        this.triggerHandlers('connected', data);

        // Re-subscribe to entities if we had any
        this.entitySubscriptions.forEach(entityId => {
          this.subscribeToEntity(entityId);
        });
        break;

      case 'subscribed':
        console.log('[WebSocket] Subscribed:', data);
        break;

      case 'unsubscribed':
        console.log('[WebSocket] Unsubscribed:', data);
        break;

      case 'pong':
        // Heartbeat response
        break;

      case 'suggestion_generated':
        console.log('[WebSocket] Suggestion generated:', data);
        this.triggerHandlers('suggestion_generated', data);
        break;

      case 'suggestion_dismissed':
        console.log('[WebSocket] Suggestion dismissed:', data);
        this.triggerHandlers('suggestion_dismissed', data);
        break;

      case 'entity_merged':
        console.log('[WebSocket] Entity merged:', data);
        this.triggerHandlers('entity_merged', data);
        break;

      case 'data_linked':
        console.log('[WebSocket] Data linked:', data);
        this.triggerHandlers('data_linked', data);
        break;

      case 'orphan_linked':
        console.log('[WebSocket] Orphan linked:', data);
        this.triggerHandlers('orphan_linked', data);
        break;

      case 'error':
        console.error('[WebSocket] Server error:', data);
        this.triggerHandlers('error', data);
        break;

      default:
        console.warn('[WebSocket] Unknown message type:', type);
    }
  }

  /**
   * Subscribe to a specific entity's suggestions.
   */
  subscribeToEntity(entityId) {
    this.entitySubscriptions.add(entityId);
    this.send({
      type: 'subscribe_entity',
      entity_id: entityId
    });
  }

  /**
   * Unsubscribe from a specific entity's suggestions.
   */
  unsubscribeFromEntity(entityId) {
    this.entitySubscriptions.delete(entityId);
    this.send({
      type: 'unsubscribe_entity',
      entity_id: entityId
    });
  }

  /**
   * Register an event handler.
   */
  on(eventType, handler) {
    if (this.handlers[eventType]) {
      this.handlers[eventType].push(handler);
    } else {
      console.warn(`[WebSocket] Unknown event type: ${eventType}`);
    }
    return this; // For chaining
  }

  /**
   * Remove an event handler.
   */
  off(eventType, handler) {
    if (this.handlers[eventType]) {
      this.handlers[eventType] = this.handlers[eventType].filter(h => h !== handler);
    }
    return this; // For chaining
  }

  /**
   * Trigger handlers for an event.
   */
  triggerHandlers(eventType, data) {
    if (this.handlers[eventType]) {
      this.handlers[eventType].forEach(handler => {
        try {
          handler(data);
        } catch (error) {
          console.error(`[WebSocket] Error in ${eventType} handler:`, error);
        }
      });
    }
  }

  // Convenience methods for registering handlers

  onConnected(handler) {
    return this.on('connected', handler);
  }

  onDisconnected(handler) {
    return this.on('disconnected', handler);
  }

  onSuggestionGenerated(handler) {
    return this.on('suggestion_generated', handler);
  }

  onSuggestionDismissed(handler) {
    return this.on('suggestion_dismissed', handler);
  }

  onEntityMerged(handler) {
    return this.on('entity_merged', handler);
  }

  onDataLinked(handler) {
    return this.on('data_linked', handler);
  }

  onOrphanLinked(handler) {
    return this.on('orphan_linked', handler);
  }

  onError(handler) {
    return this.on('error', handler);
  }
}

// ============================================================================
// Usage Examples
// ============================================================================

/**
 * Example 1: Basic usage with event handlers
 */
function example1_BasicUsage() {
  const client = new SuggestionWebSocketClient('proj_123');

  client.onConnected((data) => {
    console.log('Connected!', data);
  });

  client.onSuggestionGenerated((data) => {
    console.log('New suggestions available for entity:', data.entity_id);
    console.log('Total suggestions:', data.suggestion_count);
    console.log('High confidence:', data.high_confidence_count);

    // Update UI to show notification badge
    updateSuggestionBadge(data.entity_id, data.suggestion_count);

    // Optionally fetch full suggestions via REST API
    if (data._links && data._links.suggestions) {
      fetch(data._links.suggestions.href)
        .then(res => res.json())
        .then(suggestions => {
          console.log('Full suggestions:', suggestions);
          displaySuggestions(suggestions);
        });
    }
  });

  client.onEntityMerged((data) => {
    console.log('Entities merged:', data);
    console.log('Kept entity:', data.kept_entity_id);
    console.log('Discarded entity:', data.discarded_entity_id);

    // Update UI to reflect merged entity
    handleEntityMerge(data);
  });

  client.connect();
}

/**
 * Example 2: Subscribe to specific entities
 */
function example2_EntitySubscriptions() {
  const client = new SuggestionWebSocketClient('proj_123');

  client.onConnected(() => {
    // Subscribe to specific entities we're interested in
    client.subscribeToEntity('ent_abc123');
    client.subscribeToEntity('ent_def456');
  });

  client.onSuggestionGenerated((data) => {
    // Only receives suggestions for subscribed entities
    console.log('Suggestion for entity:', data.entity_id);
  });

  client.connect();
}

/**
 * Example 3: React integration
 */
function example3_ReactIntegration() {
  // React Hook for WebSocket client
  function useWebSocketSuggestions(projectId) {
    const [suggestions, setSuggestions] = React.useState([]);
    const [isConnected, setIsConnected] = React.useState(false);

    React.useEffect(() => {
      const client = new SuggestionWebSocketClient(projectId);

      client.onConnected(() => {
        setIsConnected(true);
      });

      client.onDisconnected(() => {
        setIsConnected(false);
      });

      client.onSuggestionGenerated((data) => {
        setSuggestions(prev => [...prev, data]);
      });

      client.connect();

      return () => {
        client.disconnect();
      };
    }, [projectId]);

    return { suggestions, isConnected };
  }

  // Usage in a React component
  function SuggestionDashboard({ projectId }) {
    const { suggestions, isConnected } = useWebSocketSuggestions(projectId);

    return (
      <div>
        <div className="connection-status">
          {isConnected ? '🟢 Connected' : '🔴 Disconnected'}
        </div>
        <div className="suggestions-list">
          {suggestions.map((suggestion, idx) => (
            <div key={idx} className="suggestion-item">
              <p>Entity: {suggestion.entity_id}</p>
              <p>Count: {suggestion.suggestion_count}</p>
              <p>High confidence: {suggestion.high_confidence_count}</p>
            </div>
          ))}
        </div>
      </div>
    );
  }
}

/**
 * Example 4: Vue integration
 */
function example4_VueIntegration() {
  // Vue composable for WebSocket client
  function useWebSocketSuggestions(projectId) {
    const suggestions = Vue.ref([]);
    const isConnected = Vue.ref(false);
    let client = null;

    Vue.onMounted(() => {
      client = new SuggestionWebSocketClient(projectId.value);

      client.onConnected(() => {
        isConnected.value = true;
      });

      client.onDisconnected(() => {
        isConnected.value = false;
      });

      client.onSuggestionGenerated((data) => {
        suggestions.value.push(data);
      });

      client.connect();
    });

    Vue.onUnmounted(() => {
      if (client) {
        client.disconnect();
      }
    });

    return { suggestions, isConnected };
  }
}

/**
 * Example 5: Authentication with token
 */
function example5_AuthenticationWithToken() {
  const authToken = 'your-auth-token-here';

  const client = new SuggestionWebSocketClient('proj_123', {
    url: 'wss://production-server.com',  // Use wss:// for secure connections
    token: authToken
  });

  client.onConnected(() => {
    console.log('Authenticated connection established');
  });

  client.connect();
}

/**
 * Example 6: Handle all event types
 */
function example6_HandleAllEvents() {
  const client = new SuggestionWebSocketClient('proj_123');

  client
    .onSuggestionGenerated((data) => {
      showNotification(`${data.suggestion_count} new suggestions for ${data.entity_id}`);
    })
    .onSuggestionDismissed((data) => {
      console.log(`Suggestion dismissed: ${data.suggestion_id}`);
    })
    .onEntityMerged((data) => {
      showNotification(`Entities merged: ${data.entity_id_1} + ${data.entity_id_2}`);
      refreshEntityList();
    })
    .onDataLinked((data) => {
      console.log(`Data linked: ${data.data_id_1} <-> ${data.data_id_2}`);
    })
    .onOrphanLinked((data) => {
      console.log(`Orphan ${data.orphan_id} linked to ${data.entity_id}`);
      refreshOrphanList();
    })
    .onError((data) => {
      console.error('WebSocket error:', data);
      showErrorNotification(data.error);
    });

  client.connect();
}

// ============================================================================
// Helper Functions (placeholders for actual implementation)
// ============================================================================

function updateSuggestionBadge(entityId, count) {
  // Update UI badge showing number of suggestions
  console.log(`Badge updated: ${entityId} has ${count} suggestions`);
}

function displaySuggestions(suggestions) {
  // Display suggestions in UI
  console.log('Displaying suggestions:', suggestions);
}

function handleEntityMerge(data) {
  // Handle entity merge in UI (remove discarded entity, update kept entity)
  console.log('Handling entity merge:', data);
}

function refreshEntityList() {
  // Refresh the entity list in UI
  console.log('Refreshing entity list');
}

function refreshOrphanList() {
  // Refresh the orphan list in UI
  console.log('Refreshing orphan list');
}

function showNotification(message) {
  // Show a notification to the user
  console.log('Notification:', message);
}

function showErrorNotification(error) {
  // Show an error notification
  console.error('Error notification:', error);
}

// Export for use in modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = SuggestionWebSocketClient;
}
