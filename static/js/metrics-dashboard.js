/**
 * Performance Metrics Dashboard Module
 *
 * Visualizes Phase 8 performance metrics with real-time updates:
 * - Overall performance (CPU, memory, connections, uptime)
 * - Response latency distribution (histogram)
 * - Request throughput (requests/sec graph)
 * - Query performance analysis (slow queries)
 * - Cache performance metrics
 *
 * APIs:
 * - GET /api/v1/metrics/performance - overall system metrics
 * - GET /api/v1/metrics/latency - latency distribution
 * - GET /api/v1/metrics/throughput - requests per second
 * - GET /api/v1/queries/slow - slow query analysis
 * - GET /api/v1/cache/stats - cache hit rate metrics
 */

// Chart.js CDN configuration
const CHART_JS_CDN = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js';
let Chart = null;
let chartsInitialized = false;
let metricsRefreshInterval = null;
let metricsCharts = {};

/**
 * Initialize metrics dashboard
 * Creates tab in dashboard and loads metrics
 */
export async function initMetricsDashboard() {
    try {
        // Load Chart.js library
        await loadChartLibrary();

        // Create dashboard tab if not exists
        createMetricsDashboardTab();

        // Setup event listeners
        setupMetricsEventListeners();

        // Start auto-refresh (every 30 seconds)
        startMetricsAutoRefresh();

        console.log('[MetricsDashboard] Initialized successfully');
    } catch (error) {
        console.error('[MetricsDashboard] Initialization error:', error);
    }
}

/**
 * Load Chart.js library dynamically
 */
async function loadChartLibrary() {
    return new Promise((resolve, reject) => {
        if (window.Chart) {
            Chart = window.Chart;
            chartsInitialized = true;
            resolve();
            return;
        }

        const script = document.createElement('script');
        script.src = CHART_JS_CDN;
        script.async = true;
        script.onload = () => {
            Chart = window.Chart;
            chartsInitialized = true;
            resolve();
        };
        script.onerror = () => reject(new Error('Failed to load Chart.js'));
        document.head.appendChild(script);
    });
}

/**
 * Create metrics dashboard tab/panel in UI
 */
function createMetricsDashboardTab() {
    const mainContent = document.querySelector('.main-content');
    if (!mainContent) return;

    // Create metrics container
    const metricsContainer = document.createElement('div');
    metricsContainer.id = 'metrics-dashboard';
    metricsContainer.className = 'metrics-dashboard';
    metricsContainer.innerHTML = `
        <div class="metrics-header">
            <div class="d-flex justify-content-between align-items-center">
                <h4><i class="fas fa-chart-line me-2"></i>Performance Metrics</h4>
                <div>
                    <button id="metrics-refresh-btn" class="btn btn-sm btn-outline-primary me-2">
                        <i class="fas fa-sync-alt"></i> Refresh
                    </button>
                    <button id="metrics-auto-refresh-toggle" class="btn btn-sm btn-outline-secondary" data-enabled="true">
                        <i class="fas fa-pause"></i> Pause Auto-Refresh
                    </button>
                </div>
            </div>
        </div>

        <div class="metrics-content">
            <!-- Overall Performance Stats -->
            <div class="metrics-section">
                <h5>System Performance</h5>
                <div class="metrics-grid" id="performance-stats">
                    <div class="metric-card">
                        <div class="metric-label">CPU Usage</div>
                        <div class="metric-value" id="cpu-usage">--</div>
                        <div class="metric-unit">%</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Memory Usage</div>
                        <div class="metric-value" id="memory-usage">--</div>
                        <div class="metric-unit">MB</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Avg Response Time</div>
                        <div class="metric-value" id="avg-response-time">--</div>
                        <div class="metric-unit">ms</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">P95 Response Time</div>
                        <div class="metric-value" id="p95-response-time">--</div>
                        <div class="metric-unit">ms</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">P99 Response Time</div>
                        <div class="metric-value" id="p99-response-time">--</div>
                        <div class="metric-unit">ms</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Requests/Sec</div>
                        <div class="metric-value" id="requests-per-sec">--</div>
                        <div class="metric-unit">RPS</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Cache Hit Rate</div>
                        <div class="metric-value" id="cache-hit-rate">--</div>
                        <div class="metric-unit">%</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">API Errors/Min</div>
                        <div class="metric-value" id="api-errors">--</div>
                        <div class="metric-unit">err/min</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Open Connections</div>
                        <div class="metric-value" id="open-connections">--</div>
                        <div class="metric-unit">conn</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Uptime</div>
                        <div class="metric-value" id="uptime">--</div>
                        <div class="metric-unit">min</div>
                    </div>
                </div>
            </div>

            <!-- Charts Section -->
            <div class="metrics-charts-grid">
                <!-- Latency Distribution -->
                <div class="metrics-section">
                    <h5>Response Latency Distribution</h5>
                    <canvas id="latency-histogram"></canvas>
                    <div id="latency-stats" class="chart-stats"></div>
                </div>

                <!-- Throughput Graph -->
                <div class="metrics-section">
                    <h5>Request Throughput (Last 60 seconds)</h5>
                    <canvas id="throughput-graph"></canvas>
                    <div id="throughput-stats" class="chart-stats"></div>
                </div>
            </div>

            <!-- Query Performance -->
            <div class="metrics-section">
                <h5>Slow Query Analysis</h5>
                <div id="query-analysis" class="query-table">
                    <table class="table table-sm">
                        <thead>
                            <tr>
                                <th>Query</th>
                                <th>Execution Time</th>
                                <th>Count</th>
                                <th>Avg Time</th>
                                <th>Max Time</th>
                            </tr>
                        </thead>
                        <tbody id="query-analysis-tbody">
                            <tr><td colspan="5" class="text-center text-muted">Loading...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Cache Performance -->
            <div class="metrics-section">
                <h5>Cache Performance</h5>
                <div class="metrics-grid" id="cache-stats">
                    <div class="metric-card">
                        <div class="metric-label">Total Requests</div>
                        <div class="metric-value" id="cache-total-requests">--</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Cache Hits</div>
                        <div class="metric-value" id="cache-hits">--</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Cache Misses</div>
                        <div class="metric-value" id="cache-misses">--</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Memory Used</div>
                        <div class="metric-value" id="cache-memory-used">--</div>
                        <div class="metric-unit">MB</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Entries Cached</div>
                        <div class="metric-value" id="cache-entries">--</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Avg Hit Latency</div>
                        <div class="metric-value" id="cache-hit-latency">--</div>
                        <div class="metric-unit">ms</div>
                    </div>
                </div>
            </div>
        </div>
    `;

    // Insert before person-details if it exists, otherwise append
    const personDetails = mainContent.querySelector('#person-details');
    if (personDetails) {
        personDetails.parentElement.insertBefore(metricsContainer, personDetails);
    } else {
        mainContent.appendChild(metricsContainer);
    }

    // Initially hide metrics dashboard
    metricsContainer.style.display = 'none';
}

/**
 * Setup event listeners for metrics controls
 */
function setupMetricsEventListeners() {
    // Refresh button
    const refreshBtn = document.getElementById('metrics-refresh-btn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
            refreshMetrics();
        });
    }

    // Auto-refresh toggle
    const toggleBtn = document.getElementById('metrics-auto-refresh-toggle');
    if (toggleBtn) {
        toggleBtn.addEventListener('click', () => {
            const enabled = toggleBtn.getAttribute('data-enabled') === 'true';
            if (enabled) {
                pauseMetricsAutoRefresh();
                toggleBtn.setAttribute('data-enabled', 'false');
                toggleBtn.innerHTML = '<i class="fas fa-play"></i> Resume Auto-Refresh';
            } else {
                startMetricsAutoRefresh();
                toggleBtn.setAttribute('data-enabled', 'true');
                toggleBtn.innerHTML = '<i class="fas fa-pause"></i> Pause Auto-Refresh';
            }
        });
    }

    // Listen for tab switching
    document.addEventListener('metrics-tab-opened', () => {
        refreshMetrics();
    });
}

/**
 * Start auto-refresh of metrics every 30 seconds
 */
function startMetricsAutoRefresh() {
    if (metricsRefreshInterval) {
        clearInterval(metricsRefreshInterval);
    }
    metricsRefreshInterval = setInterval(() => {
        refreshMetrics();
    }, 30000); // 30 seconds
}

/**
 * Pause auto-refresh
 */
function pauseMetricsAutoRefresh() {
    if (metricsRefreshInterval) {
        clearInterval(metricsRefreshInterval);
        metricsRefreshInterval = null;
    }
}

/**
 * Refresh all metrics from API
 */
async function refreshMetrics() {
    try {
        const [performance, latency, throughput, queryAnalysis, cacheStats] = await Promise.all([
            fetchPerformanceMetrics(),
            fetchLatencyMetrics(),
            fetchThroughputMetrics(),
            fetchQueryAnalysis(),
            fetchCacheStats()
        ]);

        updatePerformanceDisplay(performance);
        updateLatencyChart(latency);
        updateThroughputChart(throughput);
        updateQueryAnalysisTable(queryAnalysis);
        updateCacheDisplay(cacheStats);

        console.log('[MetricsDashboard] Metrics refreshed at', new Date().toLocaleTimeString());
    } catch (error) {
        console.error('[MetricsDashboard] Error refreshing metrics:', error);
        showMetricsError('Failed to load metrics: ' + error.message);
    }
}

/**
 * Fetch overall performance metrics
 * GET /api/v1/metrics/performance
 */
async function fetchPerformanceMetrics() {
    const response = await fetch('/api/v1/metrics/performance');
    if (!response.ok) throw new Error('Failed to fetch performance metrics');
    const result = await response.json();
    return result.data || {};
}

/**
 * Fetch latency distribution metrics
 * GET /api/v1/metrics/latency
 */
async function fetchLatencyMetrics() {
    const response = await fetch('/api/v1/metrics/latency');
    if (!response.ok) throw new Error('Failed to fetch latency metrics');
    const result = await response.json();
    return result.data || {};
}

/**
 * Fetch throughput metrics
 * GET /api/v1/metrics/throughput
 */
async function fetchThroughputMetrics() {
    const response = await fetch('/api/v1/metrics/throughput');
    if (!response.ok) throw new Error('Failed to fetch throughput metrics');
    const result = await response.json();
    return result.data || {};
}

/**
 * Fetch slow query analysis
 * GET /api/v1/queries/slow
 */
async function fetchQueryAnalysis() {
    const response = await fetch('/api/v1/queries/slow?limit=10');
    if (!response.ok) throw new Error('Failed to fetch query analysis');
    const result = await response.json();
    return result.data || [];
}

/**
 * Fetch cache statistics
 * GET /api/v1/cache/stats
 */
async function fetchCacheStats() {
    const response = await fetch('/api/v1/cache/stats');
    if (!response.ok) throw new Error('Failed to fetch cache stats');
    const result = await response.json();
    return result.data || {};
}

/**
 * Update performance metrics display
 */
function updatePerformanceDisplay(data) {
    const updates = {
        'cpu-usage': (data.cpu_usage_percent || 0).toFixed(1),
        'memory-usage': (data.memory_usage_mb || 0).toFixed(0),
        'avg-response-time': (data.avg_response_time_ms || 0).toFixed(1),
        'p95-response-time': (data.p95_response_time_ms || 0).toFixed(1),
        'p99-response-time': (data.p99_response_time_ms || 0).toFixed(1),
        'requests-per-sec': (data.requests_per_second || 0).toFixed(1),
        'cache-hit-rate': ((data.cache_hit_rate || 0) * 100).toFixed(1),
        'api-errors': (data.api_errors_per_minute || 0).toFixed(1),
        'open-connections': (data.open_connections || 0).toFixed(0),
        'uptime': (data.uptime_minutes || 0).toFixed(0)
    };

    Object.entries(updates).forEach(([elementId, value]) => {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = value;
        }
    });
}

/**
 * Update latency histogram chart
 */
function updateLatencyChart(data) {
    if (!chartsInitialized) return;

    const canvas = document.getElementById('latency-histogram');
    if (!canvas) return;

    // Parse latency distribution
    const buckets = data.buckets || [];
    const labels = buckets.map(b => b.range || 'Unknown');
    const values = buckets.map(b => b.count || 0);

    // Destroy existing chart if it exists
    if (metricsCharts.latency) {
        metricsCharts.latency.destroy();
    }

    // Create new histogram
    metricsCharts.latency = new Chart(canvas, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Request Count',
                data: values,
                backgroundColor: 'rgba(54, 162, 235, 0.7)',
                borderColor: 'rgba(54, 162, 235, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            indexAxis: 'x',
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Request Count'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Response Time (ms)'
                    }
                }
            },
            plugins: {
                legend: { display: true },
                title: { display: false }
            }
        }
    });

    // Update stats
    updateLatencyStats(data);
}

/**
 * Update latency stats display
 */
function updateLatencyStats(data) {
    const statsDiv = document.getElementById('latency-stats');
    if (!statsDiv) return;

    const min = (data.min_ms || 0).toFixed(2);
    const max = (data.max_ms || 0).toFixed(2);
    const median = (data.median_ms || 0).toFixed(2);
    const stdDev = (data.stddev_ms || 0).toFixed(2);

    statsDiv.innerHTML = `
        <div class="stats-row">
            <span>Min: ${min}ms</span>
            <span>Max: ${max}ms</span>
            <span>Median: ${median}ms</span>
            <span>StdDev: ${stdDev}ms</span>
        </div>
    `;
}

/**
 * Update throughput graph
 */
function updateThroughputChart(data) {
    if (!chartsInitialized) return;

    const canvas = document.getElementById('throughput-graph');
    if (!canvas) return;

    // Parse throughput data (should be time series)
    const timestamps = data.timestamps || [];
    const throughputs = data.values || [];

    // Limit to last 60 data points
    const maxPoints = 60;
    const startIdx = Math.max(0, timestamps.length - maxPoints);
    const labels = timestamps.slice(startIdx).map(t => new Date(t).toLocaleTimeString());
    const values = throughputs.slice(startIdx);

    // Destroy existing chart if it exists
    if (metricsCharts.throughput) {
        metricsCharts.throughput.destroy();
    }

    // Create new line chart
    metricsCharts.throughput = new Chart(canvas, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Requests/Second',
                data: values,
                borderColor: 'rgba(75, 192, 75, 1)',
                backgroundColor: 'rgba(75, 192, 75, 0.1)',
                borderWidth: 2,
                tension: 0.1,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Requests/Second'
                    }
                }
            },
            plugins: {
                legend: { display: true },
                title: { display: false }
            }
        }
    });

    // Update stats
    updateThroughputStats(data);
}

/**
 * Update throughput stats
 */
function updateThroughputStats(data) {
    const statsDiv = document.getElementById('throughput-stats');
    if (!statsDiv) return;

    const current = (data.current_rps || 0).toFixed(1);
    const average = (data.average_rps || 0).toFixed(1);
    const peak = (data.peak_rps || 0).toFixed(1);

    statsDiv.innerHTML = `
        <div class="stats-row">
            <span>Current: ${current} RPS</span>
            <span>Average: ${average} RPS</span>
            <span>Peak: ${peak} RPS</span>
        </div>
    `;
}

/**
 * Update query analysis table
 */
function updateQueryAnalysisTable(queries) {
    const tbody = document.getElementById('query-analysis-tbody');
    if (!tbody) return;

    if (!queries || queries.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">No slow queries detected</td></tr>';
        return;
    }

    tbody.innerHTML = queries.map(q => `
        <tr>
            <td class="query-text" title="${q.query || ''}">${truncateQuery(q.query || '', 50)}</td>
            <td>${(q.execution_time_ms || 0).toFixed(2)} ms</td>
            <td>${q.count || 0}</td>
            <td>${(q.avg_time_ms || 0).toFixed(2)} ms</td>
            <td>${(q.max_time_ms || 0).toFixed(2)} ms</td>
        </tr>
    `).join('');
}

/**
 * Truncate query for display
 */
function truncateQuery(query, length) {
    if (query.length <= length) return query;
    return query.substring(0, length) + '...';
}

/**
 * Update cache stats display
 */
function updateCacheDisplay(data) {
    const updates = {
        'cache-total-requests': (data.total_requests || 0).toFixed(0),
        'cache-hits': (data.total_hits || 0).toFixed(0),
        'cache-misses': (data.total_misses || 0).toFixed(0),
        'cache-memory-used': (data.memory_used_mb || 0).toFixed(1),
        'cache-entries': (data.entries_count || 0).toFixed(0),
        'cache-hit-latency': (data.avg_hit_latency_ms || 0).toFixed(2)
    };

    Object.entries(updates).forEach(([elementId, value]) => {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = value;
        }
    });
}

/**
 * Show error message
 */
function showMetricsError(message) {
    const statsDiv = document.getElementById('performance-stats');
    if (statsDiv) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-danger alert-dismissible';
        errorDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        statsDiv.parentElement.insertBefore(errorDiv, statsDiv);
    }
}

/**
 * Show/hide metrics dashboard
 */
export function toggleMetricsDashboard(show = null) {
    const dashboard = document.getElementById('metrics-dashboard');
    const personDetails = document.getElementById('person-details');
    const personForm = document.getElementById('person-form-container');
    const closeMetricsBtn = document.getElementById('close-metrics-btn');

    if (!dashboard) return;

    if (show === null) {
        show = dashboard.style.display === 'none';
    }

    dashboard.style.display = show ? 'block' : 'none';
    if (personDetails) personDetails.style.display = show ? 'none' : 'block';
    if (personForm) personForm.style.display = 'none';
    if (closeMetricsBtn) closeMetricsBtn.style.display = show ? 'block' : 'none';

    if (show) {
        refreshMetrics();
        // Setup close button
        if (closeMetricsBtn) {
            closeMetricsBtn.onclick = () => toggleMetricsDashboard(false);
        }
    } else {
        pauseMetricsAutoRefresh();
        if (closeMetricsBtn) {
            closeMetricsBtn.style.display = 'none';
        }
    }
}

/**
 * Cleanup on page unload
 */
window.addEventListener('beforeunload', () => {
    pauseMetricsAutoRefresh();
    Object.values(metricsCharts).forEach(chart => {
        if (chart) chart.destroy();
    });
});

// Auto-initialize if DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initMetricsDashboard);
} else {
    initMetricsDashboard();
}
