/**
 * Suggestions Panel Initialization
 *
 * Initializes the React-based Smart Suggestions panel and integrates it
 * with the dashboard. Handles:
 * - Loading React bundle and mounting SuggestionPanel component
 * - WebSocket connection and real-time updates
 * - API calls for accepting/dismissing suggestions
 * - Badge count management
 */

let suggestionsPanel = null;
let wsConnection = null;
let currentEntityId = null;

/**
 * Initialize the suggestions panel when the page is ready
 */
function initSuggestionsPanel() {
    // Ensure React and ReactDOM are loaded
    if (typeof React === 'undefined' || typeof ReactDOM === 'undefined') {
        console.warn('React or ReactDOM not available, skipping suggestions panel initialization');
        return;
    }

    // Get the React library from window (loaded via CDN)
    const { SuggestionPanel } = window.BassetHoundUI;

    if (!SuggestionPanel) {
        console.error('SuggestionPanel component not found in BassetHoundUI bundle');
        return;
    }

    // Setup bell icon click handler
    const bellIcon = document.getElementById('suggestions-bell-icon');
    const overlay = document.getElementById('suggestions-panel-overlay');

    if (bellIcon && overlay) {
        bellIcon.addEventListener('click', () => {
            if (overlay.style.display === 'none') {
                openSuggestionsPanel();
            } else {
                closeSuggestionsPanel();
            }
        });
    }

    // Listen for entity selection events from the dashboard
    document.addEventListener('entity-selected', (event) => {
        const entityId = event.detail?.entityId;
        if (entityId) {
            currentEntityId = entityId;
            // If panel is open, update it with new entity
            if (suggestionsPanel && suggestionsPanel.update) {
                suggestionsPanel.update(entityId);
            }
        }
    });

    console.log('Suggestions panel initialized');
}

/**
 * Open the suggestions panel overlay
 */
function openSuggestionsPanel() {
    const overlay = document.getElementById('suggestions-panel-overlay');
    if (overlay) {
        overlay.style.display = 'flex';
        document.body.classList.add('suggestions-panel-open');

        // Mount React component if not already mounted
        const projectId = window.currentProjectId;
        const entityId = currentEntityId;

        if (projectId && entityId) {
            mountSuggestionsPanel(projectId, entityId);
        } else {
            console.warn('Project ID or Entity ID not available for suggestions panel');
        }

        // Add close button handler
        setupCloseHandler();
    }
}

/**
 * Close the suggestions panel overlay
 */
function closeSuggestionsPanel() {
    const overlay = document.getElementById('suggestions-panel-overlay');
    if (overlay) {
        overlay.style.display = 'none';
        document.body.classList.remove('suggestions-panel-open');
    }
}

/**
 * Setup close button handler
 */
function setupCloseHandler() {
    const overlay = document.getElementById('suggestions-panel-overlay');
    if (!overlay) return;

    // Close on overlay click (outside the panel)
    overlay.addEventListener('click', (event) => {
        if (event.target === overlay) {
            closeSuggestionsPanel();
        }
    });

    // Close on ESC key
    const closeOnEsc = (event) => {
        if (event.key === 'Escape') {
            closeSuggestionsPanel();
            document.removeEventListener('keydown', closeOnEsc);
        }
    };
    document.addEventListener('keydown', closeOnEsc);
}

/**
 * Mount the React SuggestionPanel component
 */
async function mountSuggestionsPanel(projectId, entityId) {
    try {
        const { SuggestionPanel } = window.BassetHoundUI;
        const rootElement = document.getElementById('suggestions-panel-root');

        if (!rootElement) {
            console.error('suggestions-panel-root element not found');
            return;
        }

        // Clear existing content
        rootElement.innerHTML = '';

        // Create a wrapper div for close button and panel
        const wrapper = document.createElement('div');
        wrapper.style.height = '100%';
        wrapper.style.display = 'flex';
        wrapper.style.flexDirection = 'column';

        // Add close button
        const closeBtn = document.createElement('button');
        closeBtn.className = 'suggestions-panel-close-btn';
        closeBtn.innerHTML = '×';
        closeBtn.style.alignSelf = 'flex-end';
        closeBtn.onclick = closeSuggestionsPanel;

        // Add close button wrapper
        const closeWrapper = document.createElement('div');
        closeWrapper.style.padding = '8px 16px';
        closeWrapper.style.borderBottom = '1px solid #E5E7EB';
        closeWrapper.appendChild(closeBtn);

        wrapper.appendChild(closeWrapper);

        // Create container for panel content
        const panelContainer = document.createElement('div');
        panelContainer.style.flex = '1';
        panelContainer.style.overflow = 'auto';
        panelContainer.id = 'suggestions-panel-content';

        wrapper.appendChild(panelContainer);
        rootElement.appendChild(wrapper);

        // Mount React component
        suggestionsPanel = {
            projectId,
            entityId,
            update: (newEntityId) => {
                currentEntityId = newEntityId;
                // Unmount and remount with new entity
                unmountSuggestionsPanel();
                mountSuggestionsPanel(projectId, newEntityId);
            },
        };

        // Use ReactDOM to mount the component
        const root = ReactDOM.createRoot(panelContainer);

        // Create the component with props
        const component = React.createElement(SuggestionPanel, {
            projectId,
            entityId,
            onViewEntity: handleViewEntity,
            className: 'suggestions-panel-react',
        });

        root.render(component);

        console.log('SuggestionPanel mounted for entity:', entityId);

        // Start WebSocket connection for real-time updates
        startWebSocketConnection(projectId, entityId);
    } catch (error) {
        console.error('Error mounting suggestions panel:', error);
    }
}

/**
 * Unmount the React SuggestionPanel component
 */
function unmountSuggestionsPanel() {
    const container = document.getElementById('suggestions-panel-content');
    if (container) {
        try {
            const root = ReactDOM.createRoot(container);
            root.unmount();
        } catch (error) {
            console.warn('Error unmounting suggestions panel:', error);
        }
    }
}

/**
 * Start WebSocket connection for real-time suggestion updates
 */
async function startWebSocketConnection(projectId, entityId) {
    if (wsConnection) {
        wsConnection.close();
    }

    try {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/suggestions/${projectId}`;

        wsConnection = new WebSocket(wsUrl);

        wsConnection.onopen = () => {
            console.log('Suggestions WebSocket connected');
            // Request initial suggestions count
            updateSuggestionsCount(projectId, entityId);
        };

        wsConnection.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                handleWebSocketMessage(data);
            } catch (error) {
                console.error('Error parsing WebSocket message:', error);
            }
        };

        wsConnection.onerror = (error) => {
            console.error('Suggestions WebSocket error:', error);
        };

        wsConnection.onclose = () => {
            console.log('Suggestions WebSocket closed');
            wsConnection = null;
        };
    } catch (error) {
        console.error('Error starting WebSocket connection:', error);
    }
}

/**
 * Handle incoming WebSocket messages
 */
function handleWebSocketMessage(data) {
    const { eventType, data: eventData } = data;

    switch (eventType) {
        case 'suggestion_generated':
            // Update badge count
            updateSuggestionsCountFromEvent(eventData);
            showToast('New suggestion available', 'info');
            break;

        case 'suggestion_dismissed':
            // Update badge count
            updateSuggestionsCountFromEvent(eventData);
            showToast('Suggestion dismissed', 'success');
            break;

        case 'entity_merged':
            // Update badge and show notification
            updateSuggestionsCountFromEvent(eventData);
            showToast('Entities merged successfully', 'success');
            break;

        case 'data_linked':
            // Update badge
            updateSuggestionsCountFromEvent(eventData);
            showToast('Data linked successfully', 'success');
            break;

        case 'orphan_linked':
            // Update badge
            updateSuggestionsCountFromEvent(eventData);
            showToast('Orphan linked successfully', 'success');
            break;

        default:
            console.log('Unknown WebSocket event:', eventType);
    }
}

/**
 * Update suggestions count from WebSocket event data
 */
function updateSuggestionsCountFromEvent(eventData) {
    const countElement = document.getElementById('suggestions-count');
    if (countElement && eventData.suggestionCount !== undefined) {
        countElement.textContent = eventData.suggestionCount;

        // Show/hide badge based on count
        const badgeContainer = document.getElementById('suggestions-badge-container');
        if (badgeContainer) {
            if (eventData.suggestionCount > 0) {
                badgeContainer.style.display = 'inline-block';
            } else {
                badgeContainer.style.display = 'none';
            }
        }
    }
}

/**
 * Update suggestions count via API
 */
async function updateSuggestionsCount(projectId, entityId) {
    try {
        const response = await fetch(`/api/v1/suggestions/entity/${entityId}`);
        if (response.ok) {
            const data = await response.json();
            const summary = data.summary;
            const countElement = document.getElementById('suggestions-count');

            if (countElement && summary) {
                countElement.textContent = summary.totalCount || 0;

                // Show/hide badge based on count
                const badgeContainer = document.getElementById('suggestions-badge-container');
                if (badgeContainer) {
                    if (summary.totalCount > 0) {
                        badgeContainer.style.display = 'inline-block';
                    } else {
                        badgeContainer.style.display = 'none';
                    }
                }
            }
        }
    } catch (error) {
        console.error('Error fetching suggestions count:', error);
    }
}

/**
 * Handle view entity action
 */
function handleViewEntity(entityId) {
    // Dispatch event to select entity in the dashboard
    const event = new CustomEvent('select-entity', {
        detail: { entityId },
    });
    document.dispatchEvent(event);

    // Close the suggestions panel
    closeSuggestionsPanel();
}

/**
 * Show toast notification
 */
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `suggestions-toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    // Auto-remove after 4 seconds
    setTimeout(() => {
        toast.style.animation = 'slideDown 0.3s ease-in-out forwards';
        setTimeout(() => {
            document.body.removeChild(toast);
        }, 300);
    }, 4000);
}

// Initialize when page is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSuggestionsPanel);
} else {
    initSuggestionsPanel();
}

// Export functions for dashboard integration
export {
    initSuggestionsPanel,
    openSuggestionsPanel,
    closeSuggestionsPanel,
    updateSuggestionsCount,
    handleViewEntity,
};
