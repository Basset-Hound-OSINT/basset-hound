/**
 * Plugin Manager for Basset Hound
 *
 * Manages plugin lifecycle, execution, and communication:
 * - Plugin discovery and loading
 * - Sandboxed execution via iframes
 * - Plugin API for graph data access
 * - Plugin caching and versioning
 * - Marketplace integration
 *
 * Phase 8 Stream 7: Custom Visualization Plugins
 */

class PluginManager {
    constructor(apiBaseUrl = '/api/v1') {
        this.apiBaseUrl = apiBaseUrl;
        this.pluginsEndpoint = `${apiBaseUrl}/plugins`;
        this.plugins = new Map(); // plugin_id -> PluginInstance
        this.registry = new Map(); // plugin_id -> PluginMetadata
        this.executions = new Map(); // execution_id -> ExecutionContext
        this.eventListeners = new Map(); // event_name -> [listeners]
        this.cache = new Map(); // cache_key -> {data, timestamp}
        this.cacheTTL = 5 * 60 * 1000; // 5 minutes
        this.sandboxOrigin = window.location.origin;
    }

    // ==================== Plugin Discovery ====================

    /**
     * Load available plugins from marketplace
     */
    async loadPlugins(filter = {}) {
        try {
            let url = this.pluginsEndpoint;

            // Add filters
            const params = new URLSearchParams();
            if (filter.status) params.append('status', filter.status);
            if (filter.type) params.append('plugin_type', filter.type);
            if (filter.tags) params.append('tags', filter.tags.join(','));
            if (filter.search) params.append('search', filter.search);

            if (params.toString()) {
                url += '?' + params.toString();
            }

            const response = await fetch(url);
            if (!response.ok) throw new Error(`Failed to load plugins: ${response.statusText}`);

            const data = await response.json();
            data.plugins.forEach(plugin => {
                this.registry.set(plugin.id, plugin);
            });

            console.log(`Loaded ${data.total} plugins`);
            this.emit('plugins-loaded', { count: data.total });

            return data.plugins;
        } catch (error) {
            console.error('Failed to load plugins:', error);
            this.emit('error', { message: 'Failed to load plugins', error });
            throw error;
        }
    }

    /**
     * Get plugin metadata
     */
    async getPlugin(pluginId) {
        // Check cache first
        if (this.registry.has(pluginId)) {
            return this.registry.get(pluginId);
        }

        try {
            const response = await fetch(`${this.pluginsEndpoint}/${pluginId}`);
            if (!response.ok) throw new Error(`Plugin not found: ${pluginId}`);

            const plugin = await response.json();
            this.registry.set(pluginId, plugin);
            return plugin;
        } catch (error) {
            console.error(`Failed to get plugin ${pluginId}:`, error);
            throw error;
        }
    }

    /**
     * Search plugins by type
     */
    async searchByType(type) {
        try {
            const response = await fetch(
                `${this.pluginsEndpoint}?plugin_type=${type}`
            );
            if (!response.ok) throw new Error('Search failed');

            const data = await response.json();
            return data.plugins;
        } catch (error) {
            console.error('Plugin search error:', error);
            throw error;
        }
    }

    // ==================== Plugin Loading ====================

    /**
     * Download and load plugin code
     * Retrieves plugin metadata and code from server
     */
    async downloadPlugin(pluginId) {
        try {
            const response = await fetch(`${this.pluginsEndpoint}/${pluginId}`);
            if (!response.ok) throw new Error('Download failed');

            const plugin = await response.json();
            return {
                id: pluginId,
                code: plugin.code,
                manifest: plugin.manifest,
            };
        } catch (error) {
            console.error(`Failed to download plugin ${pluginId}:`, error);
            throw error;
        }
    }

    /**
     * Install and initialize a plugin
     */
    async installPlugin(pluginId) {
        try {
            // Call install endpoint on server
            const installResponse = await fetch(`${this.pluginsEndpoint}/${pluginId}/install`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
            });
            if (!installResponse.ok) throw new Error('Install request failed');

            const metadata = await this.getPlugin(pluginId);
            const pluginCode = await this.downloadPlugin(pluginId);

            const instance = new PluginInstance(
                pluginId,
                metadata,
                pluginCode.code,
                this
            );

            this.plugins.set(pluginId, instance);
            this.emit('plugin-installed', { pluginId, metadata });

            return instance;
        } catch (error) {
            console.error(`Failed to install plugin ${pluginId}:`, error);
            this.emit('error', { message: `Failed to install plugin: ${pluginId}`, error });
            throw error;
        }
    }

    /**
     * Uninstall a plugin
     */
    async uninstallPlugin(pluginId) {
        try {
            const response = await fetch(`${this.pluginsEndpoint}/${pluginId}`, {
                method: 'DELETE',
            });
            if (!response.ok) throw new Error('Uninstall request failed');

            const instance = this.plugins.get(pluginId);
            if (instance) {
                await instance.destroy();
                this.plugins.delete(pluginId);
                this.emit('plugin-uninstalled', { pluginId });
            }
        } catch (error) {
            console.error(`Failed to uninstall plugin ${pluginId}:`, error);
            throw error;
        }
    }

    // ==================== Plugin Execution ====================

    /**
     * Execute a plugin with graph data context
     */
    async executePlugin(pluginId, graphData, options = {}) {
        const executionId = `exec_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

        try {
            const instance = this.plugins.get(pluginId);
            if (!instance) {
                throw new Error(`Plugin not installed: ${pluginId}`);
            }

            const context = {
                executionId,
                pluginId,
                graphData,
                options,
                timestamp: new Date().toISOString(),
            };

            this.executions.set(executionId, context);
            this.emit('execution-start', { executionId, pluginId });

            const result = await instance.execute(graphData, options);

            this.emit('execution-complete', { executionId, pluginId, result });
            return result;

        } catch (error) {
            console.error(`Execution failed for plugin ${pluginId}:`, error);
            this.emit('execution-error', { executionId, pluginId, error: error.message });
            throw error;
        } finally {
            this.executions.delete(executionId);
        }
    }

    // ==================== Plugin API ====================

    /**
     * Expose API methods to plugins
     */
    getPluginAPI(pluginId) {
        return {
            // Data access methods
            queryGraph: async (query, params = {}) => {
                return await this.queryGraph(pluginId, query, params);
            },

            getEntities: async (filter = {}) => {
                return await this.getEntities(pluginId, filter);
            },

            getRelationships: async (filter = {}) => {
                return await this.getRelationships(pluginId, filter);
            },

            // Cache methods
            getCached: (key) => this.getCached(key),
            setCached: (key, value, ttl = this.cacheTTL) => {
                this.setCached(key, value, ttl);
            },

            // Event methods
            emit: (event, data) => this.emit(`plugin:${pluginId}:${event}`, data),
            on: (event, listener) => this.on(`plugin:${pluginId}:${event}`, listener),

            // Logging
            log: (level, message, data) => {
                console.log(`[${pluginId}] ${level}: ${message}`, data);
            },
        };
    }

    /**
     * Query graph data (placeholder - connects to API)
     */
    async queryGraph(pluginId, query, params = {}) {
        // This would call the actual graph query API
        console.log(`Graph query from ${pluginId}:`, query, params);
        return { nodes: [], edges: [] };
    }

    /**
     * Get entities (placeholder)
     */
    async getEntities(pluginId, filter = {}) {
        // This would call the actual entities API
        return [];
    }

    /**
     * Get relationships (placeholder)
     */
    async getRelationships(pluginId, filter = {}) {
        // This would call the actual relationships API
        return [];
    }

    // ==================== Caching ====================

    getCached(key) {
        const cached = this.cache.get(key);
        if (cached && Date.now() - cached.timestamp < this.cacheTTL) {
            return cached.data;
        }
        this.cache.delete(key);
        return null;
    }

    setCached(key, value, ttl = this.cacheTTL) {
        this.cache.set(key, {
            data: value,
            timestamp: Date.now(),
        });

        // Auto-expire
        setTimeout(() => this.cache.delete(key), ttl);
    }

    // ==================== Plugin Metadata & Data ====================

    /**
     * Get plugin data with filters
     * Phase 8 API endpoint: GET /api/v1/plugins/{plugin_id}/data
     */
    async getPluginData(pluginId, filters = {}) {
        try {
            const params = new URLSearchParams();
            if (filters.start_date) params.append('start_date', filters.start_date);
            if (filters.entity_type) params.append('entity_type', filters.entity_type);

            let url = `${this.pluginsEndpoint}/${pluginId}/data`;
            if (params.toString()) {
                url += '?' + params.toString();
            }

            const response = await fetch(url);
            if (!response.ok) throw new Error('Failed to get plugin data');

            return await response.json();
        } catch (error) {
            console.error('Failed to get plugin data:', error);
            throw error;
        }
    }

    // ==================== Event System ====================

    on(event, listener) {
        if (!this.eventListeners.has(event)) {
            this.eventListeners.set(event, []);
        }
        this.eventListeners.get(event).push(listener);
    }

    off(event, listener) {
        if (!this.eventListeners.has(event)) return;

        const listeners = this.eventListeners.get(event);
        const index = listeners.indexOf(listener);
        if (index > -1) {
            listeners.splice(index, 1);
        }
    }

    emit(event, data) {
        if (!this.eventListeners.has(event)) return;

        const listeners = this.eventListeners.get(event);
        listeners.forEach(listener => {
            try {
                listener(data);
            } catch (error) {
                console.error(`Event listener error for ${event}:`, error);
            }
        });
    }

    // ==================== Plugin Upload ====================

    /**
     * Upload a custom plugin
     * Phase 8 API endpoint: POST /api/v1/plugins/upload
     * Supports multipart/form-data with plugin.zip (max 5MB)
     */
    async uploadPlugin(pluginFile) {
        try {
            const formData = new FormData();
            formData.append('file', pluginFile);

            const response = await fetch(`${this.pluginsEndpoint}/upload`, {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Upload failed');
            }

            const plugin = await response.json();
            this.registry.set(plugin.id, plugin);
            this.emit('plugin-uploaded', { plugin });

            return plugin;

        } catch (error) {
            console.error('Plugin upload error:', error);
            throw error;
        }
    }

    // ==================== Utilities ====================

    /**
     * Get installed plugins
     */
    getInstalledPlugins() {
        return Array.from(this.plugins.values());
    }

    /**
     * Get registry plugins
     */
    getRegistryPlugins() {
        return Array.from(this.registry.values());
    }

    /**
     * Clear caches
     */
    clearCache() {
        this.cache.clear();
    }
}


/**
 * Plugin Instance
 *
 * Represents a loaded plugin with:
 * - Sandboxed execution environment
 * - Communication via postMessage
 * - Lifecycle management
 */
class PluginInstance {
    constructor(pluginId, metadata, code, manager) {
        this.pluginId = pluginId;
        this.metadata = metadata;
        this.code = code;
        this.manager = manager;
        this.sandbox = null;
        this.messageQueue = [];
        this.messageId = 0;
    }

    /**
     * Initialize sandbox iframe
     */
    async initialize() {
        // Create iframe for sandboxing
        this.sandbox = document.createElement('iframe');
        this.sandbox.id = `plugin-sandbox-${this.pluginId}`;
        this.sandbox.sandbox.add('allow-scripts', 'allow-same-origin');
        this.sandbox.style.display = 'none';
        document.body.appendChild(this.sandbox);

        // Set up message listener
        window.addEventListener('message', (event) => {
            if (event.source !== this.sandbox.contentWindow) return;
            this.handleMessage(event.data);
        });

        // Initialize plugin in sandbox
        await this.sendMessage('init', {
            pluginId: this.pluginId,
            metadata: this.metadata,
            api: this.manager.getPluginAPI(this.pluginId),
        });
    }

    /**
     * Execute plugin
     */
    async execute(graphData, options = {}) {
        return new Promise((resolve, reject) => {
            const executionId = ++this.messageId;

            const timeout = setTimeout(() => {
                reject(new Error('Plugin execution timeout'));
            }, 30000); // 30 second timeout

            this.messageQueue.push({
                executionId,
                resolve: (result) => {
                    clearTimeout(timeout);
                    resolve(result);
                },
                reject: (error) => {
                    clearTimeout(timeout);
                    reject(error);
                },
            });

            this.sendMessage('execute', {
                executionId,
                graphData,
                options,
            });
        });
    }

    /**
     * Send message to plugin
     */
    sendMessage(type, data) {
        const message = {
            type,
            data,
            timestamp: Date.now(),
        };

        if (this.sandbox && this.sandbox.contentWindow) {
            this.sandbox.contentWindow.postMessage(message, this.manager.sandboxOrigin);
        }
    }

    /**
     * Handle message from plugin
     */
    handleMessage(message) {
        const { type, data, executionId } = message;

        if (type === 'result' && executionId) {
            const queued = this.messageQueue.find(m => m.executionId === executionId);
            if (queued) {
                queued.resolve(data);
                const index = this.messageQueue.indexOf(queued);
                this.messageQueue.splice(index, 1);
            }
        } else if (type === 'error') {
            const queued = this.messageQueue.find(m => m.executionId === executionId);
            if (queued) {
                queued.reject(new Error(data.message));
                const index = this.messageQueue.indexOf(queued);
                this.messageQueue.splice(index, 1);
            }
        }
    }

    /**
     * Destroy plugin and clean up
     */
    async destroy() {
        if (this.sandbox) {
            this.sandbox.remove();
            this.sandbox = null;
        }
        this.messageQueue = [];
    }
}


/**
 * Plugin API Bridge
 *
 * Runs inside plugin sandbox and provides API methods
 */
class PluginAPIBridge {
    constructor(pluginId, metadata, apiMethods) {
        this.pluginId = pluginId;
        this.metadata = metadata;
        this.api = apiMethods;
        this.initialized = false;
    }

    /**
     * Initialize plugin bridge
     */
    static initialize() {
        window.addEventListener('message', async (event) => {
            const message = event.data;

            if (message.type === 'init') {
                // Initialize bridge with API
                window.pluginBridge = new PluginAPIBridge(
                    message.data.pluginId,
                    message.data.metadata,
                    message.data.api
                );
                window.pluginBridge.initialized = true;
            } else if (message.type === 'execute') {
                // Execute plugin
                const result = await window.pluginBridge.execute(
                    message.data.graphData,
                    message.data.options
                );

                event.source.postMessage({
                    type: 'result',
                    executionId: message.data.executionId,
                    data: result,
                }, event.origin);
            }
        });
    }

    /**
     * Execute plugin logic (override in plugin code)
     */
    async execute(graphData, options) {
        // Default implementation - plugins override this
        return {
            status: 'success',
            data: { message: 'Plugin executed' },
        };
    }

    /**
     * Get plugin metadata
     */
    getMetadata() {
        return this.metadata;
    }

    /**
     * Query graph
     */
    async queryGraph(query, params = {}) {
        return await this.api.queryGraph(query, params);
    }

    /**
     * Get entities
     */
    async getEntities(filter = {}) {
        return await this.api.getEntities(filter);
    }

    /**
     * Get relationships
     */
    async getRelationships(filter = {}) {
        return await this.api.getRelationships(filter);
    }

    /**
     * Cache operations
     */
    getCached(key) {
        return this.api.getCached(key);
    }

    setCached(key, value, ttl) {
        this.api.setCached(key, value, ttl);
    }

    /**
     * Logging
     */
    log(level, message, data) {
        this.api.log(level, message, data);
    }
}


// Initialize bridge on load
if (typeof document !== 'undefined') {
    PluginAPIBridge.initialize();
}


// Export for use in HTML/modules
if (typeof window !== 'undefined') {
    window.PluginManager = PluginManager;
    window.PluginInstance = PluginInstance;
    window.PluginAPIBridge = PluginAPIBridge;
}
