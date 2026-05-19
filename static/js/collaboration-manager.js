/**
 * Collaboration Manager - Real-time collaboration features
 *
 * Implements:
 * - WebSocket-based entity synchronization
 * - Concurrent edit detection
 * - Activity feed management
 * - Presence indicators
 * - Offline queue handling
 *
 * Phase 8, Stream 6: Real-Time Collaboration Features
 */

class CollaborationManager {
    constructor(projectId, userId) {
        this.projectId = projectId;
        this.userId = userId;
        this.websocket = null;
        this.isConnected = false;
        this.offlineQueue = [];
        this.entityLocks = new Map();
        this.presenceIndicators = new Map();
        this.activityFeed = [];
        this.messageHandlers = new Map();
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        this.currentlyEditingEntity = null;
        this.viewingEntity = null;

        // Event listeners
        this.eventListeners = {
            'presenceUpdated': [],
            'syncConfirmed': [],
            'activityLogged': [],
            'conflictDetected': [],
            'conflictResolved': [],
            'connectionStatusChanged': [],
        };

        this.setupMessageHandlers();
    }

    /**
     * Initialize the collaboration manager and WebSocket connection
     */
    async initialize() {
        try {
            // Setup offline queue
            this.loadOfflineQueue();

            // Sync on reconnection
            await this.syncOnReconnection();

            // Connect WebSocket
            this.connect();

            console.log('[Collaboration] Manager initialized', {
                projectId: this.projectId,
                userId: this.userId,
            });
        } catch (error) {
            console.error('[Collaboration] Initialization failed:', error);
        }
    }

    /**
     * Connect to WebSocket endpoint
     */
    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const url = `${protocol}//${window.location.host}/ws/sync/${this.projectId}?user=${this.userId}`;

        try {
            this.websocket = new WebSocket(url);

            this.websocket.onopen = () => {
                console.log('[Collaboration] WebSocket connected');
                this.isConnected = true;
                this.reconnectAttempts = 0;
                this.emit('connectionStatusChanged', { status: 'connected' });

                // Send queued updates
                this.flushOfflineQueue();

                // Update presence
                this.updatePresence();
            };

            this.websocket.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    this.handleMessage(message);
                } catch (error) {
                    console.error('[Collaboration] Failed to parse message:', error);
                }
            };

            this.websocket.onerror = (error) => {
                console.error('[Collaboration] WebSocket error:', error);
                this.isConnected = false;
                this.emit('connectionStatusChanged', { status: 'error' });
            };

            this.websocket.onclose = () => {
                console.log('[Collaboration] WebSocket disconnected');
                this.isConnected = false;
                this.emit('connectionStatusChanged', { status: 'disconnected' });
                this.attemptReconnect();
            };
        } catch (error) {
            console.error('[Collaboration] Failed to connect:', error);
            this.attemptReconnect();
        }
    }

    /**
     * Attempt to reconnect to WebSocket
     */
    attemptReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.warn('[Collaboration] Max reconnect attempts reached');
            return;
        }

        this.reconnectAttempts++;
        const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
        console.log(`[Collaboration] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);

        setTimeout(() => {
            this.connect();
        }, delay);
    }

    /**
     * Setup message handlers for WebSocket messages
     * Phase 8: Updated to support new message types and formats
     */
    setupMessageHandlers() {
        // Presence updates from other users
        this.messageHandlers.set('presence_updated', (data) => {
            this.emit('presenceUpdated', data.presence || data);
        });

        // Entity sync confirmations
        this.messageHandlers.set('sync_confirmed', (data) => {
            this.emit('syncConfirmed', data.update || data);
        });

        // Entity update events (Phase 8)
        this.messageHandlers.set('entity_updated', (data) => {
            this.activityFeed.push(data);
            this.emit('activityLogged', data);
            this.emit('syncConfirmed', data);
        });

        // Activity logging
        this.messageHandlers.set('activity_logged', (data) => {
            this.activityFeed.push(data.activity || data);
            this.emit('activityLogged', data.activity || data);
        });

        // Conflict detection
        this.messageHandlers.set('conflict_detected', (data) => {
            this.emit('conflictDetected', data.conflict || data);
        });

        // Ping/pong for connection keep-alive
        this.messageHandlers.set('pong', () => {
            // Ping response received
        });

        // Error messages
        this.messageHandlers.set('error', (data) => {
            console.error('[Collaboration] Server error:', data.error || data.message);
        });
    }

    /**
     * Handle incoming WebSocket message
     */
    handleMessage(message) {
        const handler = this.messageHandlers.get(message.type);
        if (handler) {
            handler(message);
        } else {
            console.warn('[Collaboration] Unknown message type:', message.type);
        }
    }

    /**
     * Send a message over WebSocket (if connected)
     */
    send(message) {
        if (!this.isConnected || !this.websocket) {
            console.warn('[Collaboration] WebSocket not connected, queuing message');
            this.offlineQueue.push(message);
            this.saveOfflineQueue();
            return false;
        }

        try {
            this.websocket.send(JSON.stringify(message));
            return true;
        } catch (error) {
            console.error('[Collaboration] Failed to send message:', error);
            this.offlineQueue.push(message);
            this.saveOfflineQueue();
            return false;
        }
    }

    /**
     * Broadcast an entity update to other clients
     */
    broadcastEntityUpdate(entityId, operation, data) {
        const message = {
            type: 'sync',
            entity_id: entityId,
            operation: operation,  // "create", "update", "delete"
            data: data,
            timestamp: new Date().toISOString(),
        };

        this.send(message);
    }

    /**
     * Update user presence in the project
     */
    updatePresence(viewingEntityId = null, isEditing = false) {
        this.viewingEntity = viewingEntityId;
        this.currentlyEditingEntity = isEditing ? viewingEntityId : null;

        const message = {
            type: 'presence',
            viewing_entity_id: viewingEntityId,
            is_editing: isEditing,
            cursor_position: this.getCursorPosition(),
            timestamp: new Date().toISOString(),
        };

        this.send(message);
    }

    /**
     * Get current cursor position (if editing)
     */
    getCursorPosition() {
        if (!this.currentlyEditingEntity) {
            return null;
        }

        // Try to get cursor position from an active editor
        const editors = document.querySelectorAll('[contenteditable="true"]');
        for (const editor of editors) {
            const selection = window.getSelection();
            if (selection.rangeCount > 0) {
                const range = selection.getRangeAt(0);
                const rect = range.getBoundingClientRect();
                return {
                    x: rect.left,
                    y: rect.top,
                    offset: this.getTextOffset(editor, range),
                };
            }
        }

        return null;
    }

    /**
     * Get text offset in editor
     */
    getTextOffset(element, range) {
        let offset = 0;
        const preCaretRange = range.cloneRange();
        preCaretRange.selectNodeContents(element);
        preCaretRange.setEnd(range.endContainer, range.endOffset);
        offset = preCaretRange.toString().length;
        return offset;
    }

    /**
     * Log an activity event
     */
    logActivity(action, entityId = null, details = null) {
        const message = {
            type: 'activity',
            action: action,
            entity_id: entityId,
            details: details || {},
            timestamp: new Date().toISOString(),
        };

        this.send(message);
    }

    /**
     * Sync pending updates from offline queue on reconnection
     * Note: Phase 8 syncing happens automatically via WebSocket reconnection
     */
    async syncOnReconnection() {
        try {
            // Phase 8: Sync endpoint changed to activity API
            const response = await fetch(
                `/api/v1/collaboration/activity?project_id=${this.projectId}&limit=100`
            );
            const data = await response.json();

            if (data.status === 'success' && data.data && data.data.length > 0) {
                console.log(`[Collaboration] Synced ${data.data.length} pending updates`);
                data.data.forEach(activity => {
                    this.emit('syncConfirmed', activity);
                });
            }
        } catch (error) {
            console.error('[Collaboration] Failed to sync on reconnection:', error);
        }
    }

    /**
     * Load offline queue from localStorage
     */
    loadOfflineQueue() {
        try {
            const key = `collaboration_queue_${this.projectId}_${this.userId}`;
            const queued = localStorage.getItem(key);
            if (queued) {
                this.offlineQueue = JSON.parse(queued);
                console.log(`[Collaboration] Loaded ${this.offlineQueue.length} offline updates`);
            }
        } catch (error) {
            console.error('[Collaboration] Failed to load offline queue:', error);
        }
    }

    /**
     * Save offline queue to localStorage
     */
    saveOfflineQueue() {
        try {
            const key = `collaboration_queue_${this.projectId}_${this.userId}`;
            localStorage.setItem(key, JSON.stringify(this.offlineQueue));
        } catch (error) {
            console.error('[Collaboration] Failed to save offline queue:', error);
        }
    }

    /**
     * Flush queued updates when connection is re-established
     */
    flushOfflineQueue() {
        if (this.offlineQueue.length === 0) {
            return;
        }

        console.log(`[Collaboration] Flushing ${this.offlineQueue.length} offline updates`);
        const queue = [...this.offlineQueue];
        this.offlineQueue = [];
        this.saveOfflineQueue();

        queue.forEach(message => {
            this.send(message);
        });
    }

    /**
     * Get active users in the project (via API)
     */
    async getActiveUsers() {
        try {
            // Phase 8: Updated to new presence endpoint
            const response = await fetch(
                `/api/v1/collaboration/presence?project_id=${this.projectId}`
            );
            const data = await response.json();

            if (data.status === 'success') {
                this.presenceIndicators = new Map(
                    data.data.active_users.map(user => [user.user_id, user])
                );
                return data.data.active_users;
            }
        } catch (error) {
            console.error('[Collaboration] Failed to get active users:', error);
        }
        return [];
    }

    /**
     * Get users currently viewing an entity
     * Note: Phase 8 presence data comes via WebSocket messages, this filters them
     */
    async getEntityViewers(entityId) {
        try {
            // Phase 8: Get active users and filter by viewing_entity
            const response = await fetch(
                `/api/v1/collaboration/presence?project_id=${this.projectId}`
            );
            const data = await response.json();

            if (data.status === 'success') {
                return data.data.active_users.filter(
                    user => user.viewing_entity_id === entityId
                );
            }
        } catch (error) {
            console.error('[Collaboration] Failed to get entity viewers:', error);
        }
        return [];
    }

    /**
     * Get activity feed for the project
     */
    async getActivityFeed(options = {}) {
        try {
            // Phase 8: Updated to new activity endpoint structure
            const params = new URLSearchParams({
                project_id: this.projectId,
                limit: options.limit || 100,
            });

            if (options.offset) {
                params.append('offset', options.offset);
            }

            const response = await fetch(
                `/api/v1/collaboration/activity?${params}`
            );
            const data = await response.json();

            if (data.status === 'success') {
                this.activityFeed = data.data;
                return data.data;
            }
        } catch (error) {
            console.error('[Collaboration] Failed to get activity feed:', error);
        }
        return [];
    }

    /**
     * Detect concurrent edits for an entity
     * Note: Phase 8 conflict detection primarily happens via WebSocket messages
     */
    async detectConcurrentEdit(entityId, data) {
        try {
            // Phase 8: Get conflicts endpoint to check for active conflicts
            const response = await fetch(
                `/api/v1/collaboration/conflicts?project_id=${this.projectId}`
            );
            const result = await response.json();

            if (result.status === 'success') {
                const entityConflicts = result.data.filter(
                    conflict => conflict.entity_id === entityId
                );
                if (entityConflicts.length > 0) {
                    const conflict = entityConflicts[0];
                    this.emit('conflictDetected', conflict);
                    return conflict;
                }
            }
        } catch (error) {
            console.error('[Collaboration] Failed to detect concurrent edit:', error);
        }
        return null;
    }

    /**
     * Resolve a conflict
     */
    async resolveConflict(conflictId, strategy = 'merge') {
        try {
            // Phase 8: Updated conflicts/resolve endpoint format
            const response = await fetch(
                `/api/v1/collaboration/conflicts/resolve`,
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        conflict_id: conflictId,
                        resolution: strategy,
                    }),
                }
            );
            const result = await response.json();

            if (result.status === 'success') {
                this.emit('conflictResolved', {
                    conflictId: conflictId,
                    mergedData: result.data,
                    strategy: strategy,
                });
                return result.data;
            }
        } catch (error) {
            console.error('[Collaboration] Failed to resolve conflict:', error);
        }
        return null;
    }

    /**
     * Show "edited by X" indicator for an entity
     */
    showEditingIndicator(entityId, userName) {
        const element = document.getElementById(`entity-${entityId}`);
        if (!element) {
            return;
        }

        // Create or update the indicator
        let indicator = element.querySelector('.editing-indicator');
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.className = 'editing-indicator';
            indicator.style.cssText = `
                position: relative;
                background-color: #fff3cd;
                border: 1px solid #ffc107;
                border-radius: 3px;
                padding: 5px 10px;
                margin-bottom: 10px;
                font-size: 12px;
                color: #856404;
            `;
            element.insertBefore(indicator, element.firstChild);
        }

        indicator.innerHTML = `⚠️ Currently being edited by <strong>${this.escapeHtml(userName)}</strong>`;
    }

    /**
     * Remove "edited by X" indicator
     */
    removeEditingIndicator(entityId) {
        const element = document.getElementById(`entity-${entityId}`);
        if (!element) {
            return;
        }

        const indicator = element.querySelector('.editing-indicator');
        if (indicator) {
            indicator.remove();
        }
    }

    /**
     * Render presence indicators for a project
     */
    async renderPresenceIndicators() {
        const users = await this.getActiveUsers();
        const container = document.getElementById('presence-indicators');

        if (!container) {
            return;
        }

        if (users.length === 0) {
            container.innerHTML = '<p>No active users</p>';
            return;
        }

        let html = '<div class="presence-list">';
        users.forEach(user => {
            // Phase 8: Handle both old (user) and new (name/user_id) field names
            const userName = user.name || user.user || 'Unknown';
            const isEditing = user.is_editing ? '✏️' : '';
            const viewingText = user.viewing_entity_id ? ` (viewing entity)` : '';
            html += `
                <div class="presence-item">
                    <span class="presence-user">${isEditing} ${this.escapeHtml(userName)}</span>
                    <span class="presence-status">${viewingText}</span>
                </div>
            `;
        });
        html += '</div>';

        container.innerHTML = html;
    }

    /**
     * Render activity feed
     */
    async renderActivityFeed(containerId = 'activity-feed') {
        const activities = await this.getActivityFeed();
        const container = document.getElementById(containerId);

        if (!container) {
            return;
        }

        if (activities.length === 0) {
            container.innerHTML = '<p>No activity</p>';
            return;
        }

        let html = '<div class="activity-list">';
        activities.forEach(activity => {
            const timestamp = new Date(activity.timestamp).toLocaleString();
            // Phase 8: Handle both user and user_id field names
            const userName = activity.user || activity.user_id || 'Unknown';
            const userBadge = userName ? `<span class="badge bg-info">${this.escapeHtml(userName)}</span>` : '';
            // Phase 8: Activity structure may use 'action' or message from type
            const actionText = activity.action || activity.type || 'Unknown action';
            html += `
                <div class="activity-item">
                    <div class="activity-action">${actionText}</div>
                    <div class="activity-meta">
                        ${userBadge}
                        <span class="activity-time">${timestamp}</span>
                    </div>
                </div>
            `;
        });
        html += '</div>';

        container.innerHTML = html;
    }

    /**
     * Show merge conflict dialog
     */
    showMergeConflictDialog(conflict) {
        const dialog = document.createElement('div');
        dialog.className = 'modal fade';
        dialog.id = `conflict-dialog-${conflict.conflict_id || conflict.id}`;
        // Phase 8: Handle both old and new field names
        const conflictId = conflict.conflict_id || conflict.id;
        const entityId = conflict.entity_id || 'Unknown';
        const user1 = conflict.user_1 || conflict.source_user || 'Unknown';
        const user2 = conflict.user_2 || conflict.target_user || 'Unknown';

        dialog.innerHTML = `
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Merge Conflict Detected</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <p>Entity <strong>${this.escapeHtml(entityId)}</strong> is being edited by multiple users.</p>
                        <p>User 1: <strong>${this.escapeHtml(user1)}</strong></p>
                        <p>User 2: <strong>${this.escapeHtml(user2)}</strong></p>
                        <p>How would you like to resolve this?</p>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-primary" onclick="window.collaborationManager.resolveConflict('${conflictId}', 'last_write')">
                            Use Latest Changes
                        </button>
                        <button type="button" class="btn btn-secondary" onclick="window.collaborationManager.resolveConflict('${conflictId}', 'merge')">
                            Merge Changes
                        </button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(dialog);
        const modal = new bootstrap.Modal(dialog);
        modal.show();
    }

    /**
     * Emit an event
     */
    emit(eventName, data) {
        const listeners = this.eventListeners[eventName] || [];
        listeners.forEach(listener => {
            try {
                listener(data);
            } catch (error) {
                console.error(`[Collaboration] Error in ${eventName} listener:`, error);
            }
        });
    }

    /**
     * Subscribe to an event
     */
    on(eventName, listener) {
        if (!this.eventListeners[eventName]) {
            this.eventListeners[eventName] = [];
        }
        this.eventListeners[eventName].push(listener);
    }

    /**
     * Unsubscribe from an event
     */
    off(eventName, listener) {
        if (this.eventListeners[eventName]) {
            this.eventListeners[eventName] = this.eventListeners[eventName].filter(l => l !== listener);
        }
    }

    /**
     * Escape HTML special characters
     */
    escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, m => map[m]);
    }

    /**
     * Cleanup and disconnect
     */
    destroy() {
        if (this.websocket) {
            this.websocket.close();
        }
        this.isConnected = false;
    }
}

// Export for use in dashboard
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CollaborationManager;
}
