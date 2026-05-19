# Cache Management Dashboard - Quick Reference

**File**: `cache-dashboard.js`  
**Size**: ~15KB (7KB minified)  
**Type**: ES6 Module  
**Phase**: 8 (Performance Optimization)  

## Quick Start

### Basic Usage
```javascript
import { initCacheDashboard } from '/static/js/cache-dashboard.js';

// Initialize in any container element
const container = document.getElementById('cache-container');
const dashboard = await initCacheDashboard(container);

// Dashboard automatically:
// - Fetches cache statistics
// - Renders UI components
// - Attaches event listeners
// - Sets up error handling
```

### Class Usage
```javascript
import { CacheDashboard } from '/static/js/cache-dashboard.js';

const dashboard = new CacheDashboard(document.getElementById('container'));
await dashboard.init();

// Access methods:
dashboard.loadCacheStats();      // Refresh stats
dashboard.clearCache();          // Clear all cache
dashboard.warmCache();           // Pre-populate cache
dashboard.toggleAutoRefresh();   // Enable 30s polling
dashboard.destroy();             // Cleanup
```

## API Endpoints Called

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/cache/stats` | GET | Fetch cache statistics |
| `/api/v1/cache/hit-rate` | GET | Get hit rate metrics |
| `/api/v1/cache/clear` | POST | Clear all cache |
| `/api/v1/cache/warm` | POST | Warm cache with common queries |

## Dashboard Components

### Statistics Display
```
Hit Rate: 62.0%              Memory: 85 MB / 256 MB
Cached Items: 450 / 1000     Total Requests: 10,000
Hit Latency: 0.50ms          Miss Latency: 45.00ms
```

### Interactive Controls
- **Refresh** - Manual stats reload
- **Warm Cache** - Pre-populate with common queries
- **Clear All** - Clear entire cache (with confirmation)
- **Auto Refresh** - Toggle 30-second polling

### Visual Indicators
- Memory usage progress bar (green)
- Entry capacity progress bar (blue)
- Contextual status messages (info/success/danger)

## Key Methods

### Initialization
```javascript
async init()  // Renders dashboard and loads initial stats
```

### Data Loading
```javascript
async loadCacheStats()        // Fetch and display statistics
async loadHitRateMetrics()    // Get detailed hit rate data
```

### User Actions
```javascript
async clearCache()            // Clear cache (with confirmation)
async warmCache()             // Pre-populate cache
toggleAutoRefresh()           // Enable/disable 30s polling
```

### UI Management
```javascript
render()                      // Build dashboard HTML
showStatus(msg, type)         // Display status alerts
attachEventListeners()        // Wire up button handlers
destroy()                     // Cleanup and remove
```

## Error Handling

The module automatically handles:
- Network failures (graceful fallback)
- API errors (user-friendly messages)
- Missing data (default values)
- Browser compatibility (vanilla JS)

Example error responses:
```
"Error: API error: 500"
"Error: Cache service is not available"
"Error: Failed to load cache stats"
```

## Status Messages

**Auto-dismiss** (3 seconds):
- "Loading cache statistics..."
- "Cache cleared successfully"
- "Cache warmed successfully"

**Persistent** (user must close):
- "Error: API error: 500"
- "Error: Connection timeout"

## Integration Patterns

### Tab Implementation
```html
<ul class="nav nav-tabs">
    <li class="nav-item">
        <button class="nav-link" data-tab="cache">Cache</button>
    </li>
</ul>

<div id="cache-container"></div>

<script type="module">
import { initCacheDashboard } from './cache-dashboard.js';
document.querySelector('[data-tab="cache"]')
    .addEventListener('click', async () => {
        await initCacheDashboard(document.getElementById('cache-container'));
    });
</script>
```

### Modal Implementation
```html
<button id="cache-btn">Cache Management</button>

<div class="modal" id="cacheModal">
    <div class="modal-content">
        <div id="cache-container"></div>
    </div>
</div>

<script type="module">
import { initCacheDashboard } from './cache-dashboard.js';
document.getElementById('cache-btn').addEventListener('click', async () => {
    await initCacheDashboard(document.getElementById('cache-container'));
    new bootstrap.Modal(document.getElementById('cacheModal')).show();
});
</script>
```

### Sidebar Widget
```html
<div id="sidebar-cache"></div>

<script type="module">
import { initCacheDashboard } from './cache-dashboard.js';
initCacheDashboard(document.getElementById('sidebar-cache'));
</script>
```

## CSS Classes Used

**From Bootstrap 5** (pre-installed):
- `card`, `card-header`, `card-body`
- `btn`, `btn-primary`, `btn-warning`, `btn-outline-secondary`
- `progress`, `progress-bar`
- `alert`, `alert-success`, `alert-danger`, `alert-info`
- `d-flex`, `align-items-center`, `gap-3`
- `text-muted`, `border-start`

**Custom Classes** (in module):
- `.cache-dashboard` - Main container
- `.cache-stat-value` - Stat display values
- `.btn-group` - Button group styling

## Performance

| Metric | Value |
|--------|-------|
| Module Size | 15KB (7KB minified) |
| DOM Overhead | ~15 elements |
| Initial Render | <50ms |
| API Call | <200ms (depends on backend) |
| Memory Footprint | ~5KB |

## Browser Support

- Chrome 55+
- Firefox 67+
- Safari 10.1+
- Edge 79+
- All modern browsers with ES6 module support

## Configuration

No configuration file needed. The module uses:
- Default base URL: `/api/v1`
- Default auto-refresh interval: 30 seconds
- Default status message timeout: 3 seconds

To customize, extend the class:
```javascript
class CustomCacheDashboard extends CacheDashboard {
    constructor(container) {
        super(container);
        this.BASE_URL = 'https://api.example.com/v1'; // Custom URL
    }
}
```

## Troubleshooting

**Dashboard doesn't appear**
- Verify container element exists
- Check browser console for errors
- Ensure `/api/v1/cache/stats` endpoint is available

**Stats not updating**
- Check network tab for failed requests
- Verify cache endpoints are active (Phase 8)
- Check CORS settings if cross-origin

**Auto-refresh not working**
- Verify browser allows auto-refresh
- Check memory (long polling can consume resources)
- Use browser dev tools to monitor polling

**Buttons not responding**
- Check that event listeners are attached
- Verify no JavaScript errors in console
- Test with different browser

## Examples

See `/static/js/examples/cache-dashboard-usage.js` for:
- Tab integration
- Modal implementation
- Sidebar widget
- Custom extensions
- Event-driven updates
- Responsive design
- HTML templates

## Related Files

- **API Reference**: `/docs/API_REFERENCE.md` (Lines 1473-1530)
- **Phase 8 Features**: `/docs/API_REFERENCE.md` (Lines 1469+)
- **Implementation Report**: `/docs/handoffs/frontend-new-cache-dashboard-report.md`
- **Usage Examples**: `/static/js/examples/cache-dashboard-usage.js`

## Future Enhancements

- [ ] Historical metrics graph
- [ ] Configurable refresh interval
- [ ] Cache key browser
- [ ] Export metrics as CSV
- [ ] Performance alerts
- [ ] Dark mode support
- [ ] Custom themes

## Support

For issues or questions:
1. Check this README first
2. Review examples in `/static/js/examples/`
3. Read full documentation in `/docs/handoffs/frontend-new-cache-dashboard-report.md`
4. Examine module source code in `/static/js/cache-dashboard.js`

---

**Last Updated**: 2026-05-19  
**Phase**: 8 (Performance Optimization)  
**Status**: Complete & Ready for Integration
