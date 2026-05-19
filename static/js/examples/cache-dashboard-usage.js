/**
 * Cache Dashboard Usage Examples
 *
 * This file demonstrates how to integrate the CacheDashboard module
 * into various parts of the application.
 */

// ============================================================================
// EXAMPLE 1: Basic Dashboard Tab Integration
// ============================================================================

import { initCacheDashboard } from '../cache-dashboard.js';

// In your main dashboard.js or wherever tabs are managed:
function initCacheDashTab() {
    const cacheTabBtn = document.getElementById('cache-tab-btn');
    const cacheTabContent = document.getElementById('cache-tab-content');

    cacheTabBtn.addEventListener('click', async () => {
        // Initialize dashboard only once
        if (!cacheTabContent.hasChildNodes()) {
            const dashboard = await initCacheDashboard(cacheTabContent);
            // Store reference for later cleanup if needed
            window.cacheDashboard = dashboard;
        }
        cacheTabContent.style.display = 'block';
    });
}

// ============================================================================
// EXAMPLE 2: Admin Panel Integration
// ============================================================================

import { CacheDashboard } from '../cache-dashboard.js';

function initAdminPanel() {
    const adminContainer = document.getElementById('admin-panel');
    const cacheDashboard = new CacheDashboard(adminContainer);

    // Initialize and start dashboard
    cacheDashboard.init();

    // Optional: Store for later access
    window.adminCacheDashboard = cacheDashboard;

    // Optional: Cleanup on page unload
    window.addEventListener('beforeunload', () => {
        cacheDashboard.destroy();
    });
}

// ============================================================================
// EXAMPLE 3: Modal Implementation
// ============================================================================

import { initCacheDashboard } from '../cache-dashboard.js';

function setupCacheModal() {
    const cacheBtn = document.getElementById('cache-mgmt-btn');
    const modal = new bootstrap.Modal(document.getElementById('cacheModal'));

    cacheBtn.addEventListener('click', async () => {
        const container = document.getElementById('cache-modal-container');

        // Clear previous content
        container.innerHTML = '';

        // Initialize new dashboard
        const dashboard = await initCacheDashboard(container);

        // Show modal
        modal.show();

        // Cleanup when modal is hidden
        document.getElementById('cacheModal').addEventListener('hidden.bs.modal', () => {
            dashboard.destroy();
        }, { once: true });
    });
}

// ============================================================================
// EXAMPLE 4: Standalone Component (No Container Wrapper)
// ============================================================================

import { CacheDashboard } from '../cache-dashboard.js';

function createStandaloneDashboard() {
    // Create a container element
    const container = document.createElement('div');
    container.className = 'cache-dashboard-wrapper';

    // Append to page
    document.body.appendChild(container);

    // Initialize dashboard
    const dashboard = new CacheDashboard(container);
    dashboard.init();

    return dashboard;
}

// ============================================================================
// EXAMPLE 5: Polling and External Updates
// ============================================================================

import { CacheDashboard } from '../cache-dashboard.js';

async function setupCacheDashboardWithExternalPolling() {
    const container = document.getElementById('cache-dashboard-container');
    const dashboard = new CacheDashboard(container);

    // Initialize
    await dashboard.init();

    // Set up external polling (in addition to built-in auto-refresh)
    setInterval(async () => {
        // Load metrics from external service
        const metrics = await dashboard.loadHitRateMetrics();
        console.log('Current hit rate metrics:', metrics);
    }, 60000); // Every 60 seconds

    return dashboard;
}

// ============================================================================
// EXAMPLE 6: Event-Driven Integration
// ============================================================================

import { CacheDashboard } from '../cache-dashboard.js';

class CacheMonitor {
    constructor(container) {
        this.dashboard = new CacheDashboard(container);
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Listen for cache events from backend (if available)
        document.addEventListener('cache:cleared', () => {
            this.dashboard.loadCacheStats();
            this.notifyUser('Cache cleared by administrator');
        });

        document.addEventListener('cache:warmed', () => {
            this.dashboard.loadCacheStats();
            this.notifyUser('Cache warmed with common queries');
        });
    }

    async init() {
        await this.dashboard.init();
        return this;
    }

    notifyUser(message) {
        // Integrate with your notification system
        console.log('[Cache Monitor]', message);
    }
}

// ============================================================================
// EXAMPLE 7: Responsive Integration
// ============================================================================

import { initCacheDashboard } from '../cache-dashboard.js';

function setupResponsiveCacheDashboard() {
    const container = document.getElementById('cache-container');
    let dashboard = null;

    // Load on desktop
    if (window.innerWidth >= 768) {
        dashboard = initCacheDashboard(container);
    }

    // Handle window resize
    window.addEventListener('resize', async () => {
        if (window.innerWidth >= 768 && !dashboard) {
            dashboard = await initCacheDashboard(container);
        } else if (window.innerWidth < 768 && dashboard) {
            dashboard.destroy();
            dashboard = null;
        }
    });
}

// ============================================================================
// EXAMPLE 8: Sidebar Widget
// ============================================================================

import { CacheDashboard } from '../cache-dashboard.js';

function createSidebarCacheWidget() {
    const widget = document.createElement('div');
    widget.className = 'sidebar-widget cache-widget card';
    widget.innerHTML = `
        <div class="card-header">
            <h6 class="mb-0"><i class="fas fa-database"></i> Cache Status</h6>
        </div>
        <div class="card-body" id="sidebar-cache-container"></div>
    `;

    const sidebar = document.getElementById('admin-sidebar');
    sidebar.appendChild(widget);

    // Initialize in compact mode
    const dashboard = new CacheDashboard(
        document.getElementById('sidebar-cache-container')
    );
    dashboard.init();

    return dashboard;
}

// ============================================================================
// EXAMPLE 9: Custom Status Display
// ============================================================================

import { CacheDashboard } from '../cache-dashboard.js';

class CustomCacheDashboard extends CacheDashboard {
    showStatus(message, type = 'info') {
        // Override to use custom notification system
        console.log(`[Cache Status - ${type.toUpperCase()}]`, message);

        // Example: Send to toast notification system
        if (window.toastr) {
            window.toastr[type](message);
        } else {
            super.showStatus(message, type);
        }
    }

    updateStats(stats) {
        super.updateStats(stats);

        // Additional custom processing
        this.logMetrics(stats);
        this.checkThresholds(stats);
    }

    logMetrics(stats) {
        console.table({
            'Hit Rate': `${(stats.hit_rate * 100).toFixed(1)}%`,
            'Memory Usage': `${stats.memory_used_mb}/${stats.memory_limit_mb} MB`,
            'Entries': `${stats.entries_count}/${stats.entries_max}`,
            'Total Requests': stats.total_requests
        });
    }

    checkThresholds(stats) {
        // Alert if hit rate drops below 50%
        if (stats.hit_rate < 0.5) {
            console.warn('Warning: Cache hit rate below 50%');
        }

        // Alert if memory usage exceeds 80%
        const memPercent = (stats.memory_used_mb / stats.memory_limit_mb) * 100;
        if (memPercent > 80) {
            console.warn(`Warning: Cache memory usage at ${memPercent.toFixed(1)}%`);
        }
    }
}

// ============================================================================
// EXAMPLE 10: Dashboard in Settings/Configuration Page
// ============================================================================

import { initCacheDashboard } from '../cache-dashboard.js';

async function initSettingsPage() {
    // Settings navigation
    const tabs = {
        general: () => console.log('Show general settings'),
        cache: async () => {
            const container = document.getElementById('cache-settings-container');
            container.innerHTML = '';
            await initCacheDashboard(container);
        },
        security: () => console.log('Show security settings'),
        api: () => console.log('Show API settings')
    };

    // Tab click handlers
    document.querySelectorAll('.settings-nav button').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const tabName = e.target.dataset.tab;
            if (tabs[tabName]) {
                await tabs[tabName]();
            }
        });
    });
}

// ============================================================================
// HTML STRUCTURE TEMPLATES
// ============================================================================

/*
<!-- TEMPLATE 1: Tab Implementation -->
<ul class="nav nav-tabs">
    <li class="nav-item">
        <button class="nav-link active" id="general-tab" data-bs-toggle="tab">
            General
        </button>
    </li>
    <li class="nav-item">
        <button class="nav-link" id="cache-tab-btn" data-bs-toggle="tab">
            <i class="fas fa-database"></i> Cache Dashboard
        </button>
    </li>
</ul>

<div class="tab-content">
    <div id="cache-tab-content" class="tab-pane fade"></div>
</div>

<script type="module">
import { initCacheDashboard } from './cache-dashboard.js';
initCacheDashTab();
</script>

<!-- TEMPLATE 2: Modal Implementation -->
<button class="btn btn-sm btn-outline-secondary" id="cache-mgmt-btn">
    <i class="fas fa-database"></i> Cache Management
</button>

<div class="modal fade" id="cacheModal" tabindex="-1">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">Cache Management</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <div id="cache-modal-container"></div>
            </div>
        </div>
    </div>
</div>

<!-- TEMPLATE 3: Standalone Container -->
<div id="cache-dashboard-container" class="container mt-4"></div>

<script type="module">
import { initCacheDashboard } from './cache-dashboard.js';
const container = document.getElementById('cache-dashboard-container');
initCacheDashboard(container);
</script>
*/

// ============================================================================
// EXPORT FOR USE IN OTHER MODULES
// ============================================================================

export { setupCacheModal, createStandaloneDashboard, CacheMonitor };
