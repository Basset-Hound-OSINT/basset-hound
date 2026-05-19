/**
 * Cache Management Dashboard
 * Provides UI controls and monitoring for Phase 8 cache management endpoints
 *
 * API Endpoints:
 * - GET /api/v1/cache/stats - Cache statistics
 * - GET /api/v1/cache/hit-rate - Hit rate metrics
 * - POST /api/v1/cache/clear - Clear all cache
 * - POST /api/v1/cache/warm - Warm cache with common queries
 */

export class CacheDashboard {
    constructor(container) {
        this.container = container;
        this.isLoading = false;
        this.autoRefreshInterval = null;
        this.BASE_URL = '/api/v1';
    }

    /**
     * Initialize and render the cache dashboard
     */
    async init() {
        this.render();
        await this.loadCacheStats();
        this.attachEventListeners();
    }

    /**
     * Render the dashboard UI structure
     */
    render() {
        this.container.innerHTML = '';

        const dashboard = document.createElement('div');
        dashboard.className = 'cache-dashboard card';
        dashboard.id = 'cache-dashboard';

        const header = document.createElement('div');
        header.className = 'card-header d-flex justify-content-between align-items-center';
        header.innerHTML = `
            <div>
                <h5 class="mb-0">
                    <i class="fas fa-database"></i> Cache Management Dashboard
                </h5>
                <small class="text-muted">Phase 8 Performance Optimization</small>
            </div>
            <button class="btn btn-sm btn-outline-secondary" id="cache-refresh-btn">
                <i class="fas fa-sync-alt"></i> Refresh
            </button>
        `;
        dashboard.appendChild(header);

        const body = document.createElement('div');
        body.className = 'card-body';

        // Stats section
        const statsSection = document.createElement('div');
        statsSection.className = 'mb-4';
        statsSection.innerHTML = `
            <h6 class="mb-3">Cache Statistics</h6>
            <div class="row">
                <div class="col-md-3 mb-3">
                    <div class="border-start border-primary ps-3">
                        <small class="text-muted d-block">Hit Rate</small>
                        <div class="cache-stat-value" id="cache-hit-rate">--%</div>
                        <small class="text-muted" id="cache-hits-count"></small>
                    </div>
                </div>
                <div class="col-md-3 mb-3">
                    <div class="border-start border-success ps-3">
                        <small class="text-muted d-block">Memory Usage</small>
                        <div class="cache-stat-value" id="cache-memory-usage">-- MB</div>
                        <small class="text-muted" id="cache-memory-limit"></small>
                    </div>
                </div>
                <div class="col-md-3 mb-3">
                    <div class="border-start border-info ps-3">
                        <small class="text-muted d-block">Cached Items</small>
                        <div class="cache-stat-value" id="cache-entries-count">--</div>
                        <small class="text-muted" id="cache-entries-limit"></small>
                    </div>
                </div>
                <div class="col-md-3 mb-3">
                    <div class="border-start border-warning ps-3">
                        <small class="text-muted d-block">Total Requests</small>
                        <div class="cache-stat-value" id="cache-total-requests">--</div>
                        <small class="text-muted" id="cache-miss-rate"></small>
                    </div>
                </div>
            </div>
            <div class="mt-3">
                <small class="text-muted d-block mb-2">Hit Latency: <span id="cache-hit-latency">-- ms</span> | Miss Latency: <span id="cache-miss-latency">-- ms</span></small>
            </div>
        `;
        body.appendChild(statsSection);

        // Progress bars
        const progressSection = document.createElement('div');
        progressSection.className = 'mb-4';
        progressSection.innerHTML = `
            <div class="mb-3">
                <small class="text-muted d-block mb-1">Memory Usage</small>
                <div class="progress" style="height: 20px;">
                    <div id="cache-memory-bar" class="progress-bar bg-success" role="progressbar"
                         style="width: 0%;" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100">
                    </div>
                </div>
            </div>
            <div>
                <small class="text-muted d-block mb-1">Entry Capacity</small>
                <div class="progress" style="height: 20px;">
                    <div id="cache-entries-bar" class="progress-bar bg-info" role="progressbar"
                         style="width: 0%;" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100">
                    </div>
                </div>
            </div>
        `;
        body.appendChild(progressSection);

        // Controls section
        const controlsSection = document.createElement('div');
        controlsSection.className = 'border-top pt-3';
        controlsSection.innerHTML = `
            <h6 class="mb-3">Cache Controls</h6>
            <div class="btn-group" role="group">
                <button type="button" class="btn btn-sm btn-primary" id="cache-warm-btn">
                    <i class="fas fa-fire"></i> Warm Cache
                </button>
                <button type="button" class="btn btn-sm btn-warning" id="cache-clear-btn">
                    <i class="fas fa-trash"></i> Clear All
                </button>
                <button type="button" class="btn btn-sm btn-outline-secondary" id="cache-auto-refresh-btn">
                    <i class="fas fa-clock"></i> Auto Refresh
                </button>
            </div>
            <div id="cache-status-message" class="mt-3"></div>
        `;
        body.appendChild(controlsSection);

        dashboard.appendChild(body);
        this.container.appendChild(dashboard);
    }

    /**
     * Load cache statistics from API
     */
    async loadCacheStats() {
        if (this.isLoading) return;

        this.isLoading = true;
        this.showStatus('Loading cache statistics...', 'info');

        try {
            const response = await fetch(`${this.BASE_URL}/cache/stats`);
            if (!response.ok) {
                throw new Error(`API error: ${response.status}`);
            }

            const data = await response.json();
            if (data.status === 'success') {
                this.updateStats(data.data);
                this.showStatus('Cache statistics updated', 'success');
            } else {
                throw new Error(data.error?.message || 'Unknown error');
            }
        } catch (error) {
            console.error('Error loading cache stats:', error);
            this.showStatus(`Error: ${error.message}`, 'danger');
        } finally {
            this.isLoading = false;
        }
    }

    /**
     * Update dashboard with cache statistics
     */
    updateStats(stats) {
        // Hit rate
        const hitRatePercent = (stats.hit_rate * 100).toFixed(1);
        document.getElementById('cache-hit-rate').textContent = `${hitRatePercent}%`;
        document.getElementById('cache-hits-count').textContent =
            `${stats.total_hits?.toLocaleString() || 0} hits`;

        // Miss rate
        const missRatePercent = (stats.miss_rate * 100).toFixed(1);
        document.getElementById('cache-miss-rate').textContent =
            `${missRatePercent}% miss rate`;

        // Total requests
        document.getElementById('cache-total-requests').textContent =
            (stats.total_requests || 0).toLocaleString();

        // Memory usage
        const memoryPercent = ((stats.memory_used_mb || 0) / (stats.memory_limit_mb || 1) * 100).toFixed(1);
        document.getElementById('cache-memory-usage').textContent =
            `${stats.memory_used_mb || 0} MB`;
        document.getElementById('cache-memory-limit').textContent =
            `/ ${stats.memory_limit_mb || 256} MB`;
        document.getElementById('cache-memory-bar').style.width = `${memoryPercent}%`;
        document.getElementById('cache-memory-bar').setAttribute('aria-valuenow', memoryPercent);

        // Entries count
        const entriesPercent = ((stats.entries_count || 0) / (stats.entries_max || 1000) * 100).toFixed(1);
        document.getElementById('cache-entries-count').textContent =
            `${stats.entries_count || 0}`;
        document.getElementById('cache-entries-limit').textContent =
            `/ ${stats.entries_max || 1000} items`;
        document.getElementById('cache-entries-bar').style.width = `${entriesPercent}%`;
        document.getElementById('cache-entries-bar').setAttribute('aria-valuenow', entriesPercent);

        // Latency
        document.getElementById('cache-hit-latency').textContent =
            `${(stats.avg_hit_latency_ms || 0).toFixed(2)}`;
        document.getElementById('cache-miss-latency').textContent =
            `${(stats.avg_miss_latency_ms || 0).toFixed(2)}`;
    }

    /**
     * Clear all cache
     */
    async clearCache() {
        if (!confirm('Are you sure you want to clear all cache? This may temporarily impact performance.')) {
            return;
        }

        this.isLoading = true;
        this.showStatus('Clearing cache...', 'info');

        try {
            const response = await fetch(`${this.BASE_URL}/cache/clear`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });

            if (!response.ok) {
                throw new Error(`API error: ${response.status}`);
            }

            const data = await response.json();
            if (data.status === 'success') {
                this.showStatus('Cache cleared successfully', 'success');
                // Reload stats
                await this.loadCacheStats();
            } else {
                throw new Error(data.error?.message || 'Unknown error');
            }
        } catch (error) {
            console.error('Error clearing cache:', error);
            this.showStatus(`Error: ${error.message}`, 'danger');
        } finally {
            this.isLoading = false;
        }
    }

    /**
     * Warm cache with common queries
     */
    async warmCache() {
        this.isLoading = true;
        this.showStatus('Warming cache with common queries...', 'info');

        try {
            const response = await fetch(`${this.BASE_URL}/cache/warm`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });

            if (!response.ok) {
                throw new Error(`API error: ${response.status}`);
            }

            const data = await response.json();
            if (data.status === 'success') {
                const queriesWarmed = data.data?.queries_warmed || 'N/A';
                this.showStatus(`Cache warmed successfully (${queriesWarmed} queries)`, 'success');
                // Reload stats
                await this.loadCacheStats();
            } else {
                throw new Error(data.error?.message || 'Unknown error');
            }
        } catch (error) {
            console.error('Error warming cache:', error);
            this.showStatus(`Error: ${error.message}`, 'danger');
        } finally {
            this.isLoading = false;
        }
    }

    /**
     * Load hit rate metrics
     */
    async loadHitRateMetrics() {
        try {
            const response = await fetch(`${this.BASE_URL}/cache/hit-rate`);
            if (!response.ok) {
                throw new Error(`API error: ${response.status}`);
            }

            const data = await response.json();
            if (data.status === 'success') {
                console.log('Hit rate metrics:', data.data);
                return data.data;
            } else {
                throw new Error(data.error?.message || 'Unknown error');
            }
        } catch (error) {
            console.error('Error loading hit rate metrics:', error);
            return null;
        }
    }

    /**
     * Show status message
     */
    showStatus(message, type = 'info') {
        const messageEl = document.getElementById('cache-status-message');
        if (!messageEl) return;

        const alertClass = `alert alert-${type}`;
        messageEl.innerHTML = `<div class="${alertClass}" role="alert">${message}</div>`;

        // Auto-dismiss success and info messages
        if (type === 'success' || type === 'info') {
            setTimeout(() => {
                if (messageEl.innerHTML.includes(message)) {
                    messageEl.innerHTML = '';
                }
            }, 3000);
        }
    }

    /**
     * Toggle auto-refresh
     */
    toggleAutoRefresh() {
        const btn = document.getElementById('cache-auto-refresh-btn');

        if (this.autoRefreshInterval) {
            // Stop auto-refresh
            clearInterval(this.autoRefreshInterval);
            this.autoRefreshInterval = null;
            btn.classList.remove('active');
            btn.classList.add('btn-outline-secondary');
            btn.classList.remove('btn-secondary');
            this.showStatus('Auto-refresh disabled', 'info');
        } else {
            // Start auto-refresh every 30 seconds
            this.autoRefreshInterval = setInterval(() => {
                this.loadCacheStats();
            }, 30000);
            btn.classList.add('active');
            btn.classList.remove('btn-outline-secondary');
            btn.classList.add('btn-secondary');
            this.showStatus('Auto-refresh enabled (every 30 seconds)', 'success');
        }
    }

    /**
     * Attach event listeners
     */
    attachEventListeners() {
        document.getElementById('cache-refresh-btn')?.addEventListener('click', () => {
            this.loadCacheStats();
        });

        document.getElementById('cache-clear-btn')?.addEventListener('click', () => {
            this.clearCache();
        });

        document.getElementById('cache-warm-btn')?.addEventListener('click', () => {
            this.warmCache();
        });

        document.getElementById('cache-auto-refresh-btn')?.addEventListener('click', () => {
            this.toggleAutoRefresh();
        });
    }

    /**
     * Destroy dashboard and cleanup
     */
    destroy() {
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
            this.autoRefreshInterval = null;
        }
        this.container.innerHTML = '';
    }
}

/**
 * Initialize cache dashboard on a specific container
 * Usage: initCacheDashboard(document.getElementById('cache-container'))
 */
export async function initCacheDashboard(container) {
    const dashboard = new CacheDashboard(container);
    await dashboard.init();
    return dashboard;
}
