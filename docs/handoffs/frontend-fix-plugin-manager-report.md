# Plugin Manager Endpoint Path Fix - Report

**Date**: 2026-05-19  
**File**: `/home/devel/basset-hound/static/js/plugin-manager.js`  
**Status**: COMPLETED  
**Priority**: 3 (Medium)

## Summary

Fixed all plugin endpoint paths in `plugin-manager.js` to align with Phase 8 API specification. All 7 methods updated to use correct REST endpoints defined in `API_REFERENCE.md`.

## Issues Fixed

### 1. searchByType() Method
**Issue**: Used non-standard endpoint path
```javascript
// BEFORE
GET /api/v1/plugins/search/by-type?plugin_type=${type}

// AFTER
GET /api/v1/plugins?plugin_type=${type}
```
**Fix**: Simplified to use main plugins endpoint with query parameter per Phase 8 API spec.

### 2. downloadPlugin() Method
**Issue**: Used non-existent `/download` endpoint
```javascript
// BEFORE
GET /api/v1/plugins/{plugin_id}/download

// AFTER
GET /api/v1/plugins/{plugin_id}
```
**Fix**: Updated to retrieve plugin data from standard GET endpoint. Plugin object contains code and manifest properties.

### 3. installPlugin() Method
**Issue**: Missing server-side install endpoint call
```javascript
// BEFORE
const metadata = await this.getPlugin(pluginId);
const pluginCode = await this.downloadPlugin(pluginId);

// AFTER
const installResponse = await fetch(`${this.pluginsEndpoint}/${pluginId}/install`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
});
const metadata = await this.getPlugin(pluginId);
const pluginCode = await this.downloadPlugin(pluginId);
```
**Fix**: Added server-side install endpoint call per Phase 8 API: `POST /api/v1/plugins/{plugin_id}/install`

### 4. uninstallPlugin() Method
**Issue**: Missing server-side uninstall endpoint call
```javascript
// BEFORE
const instance = this.plugins.get(pluginId);
if (instance) {
    await instance.destroy();
    this.plugins.delete(pluginId);
    this.emit('plugin-uninstalled', { pluginId });
}

// AFTER
const response = await fetch(`${this.pluginsEndpoint}/${pluginId}`, {
    method: 'DELETE',
});
// ... then cleanup
```
**Fix**: Added server-side DELETE endpoint call per Phase 8 API: `DELETE /api/v1/plugins/{plugin_id}`

### 5. reviewPlugin() & getReviews() Methods
**Issue**: Methods used non-existent `/reviews` endpoints not in Phase 8 API
**Fix**: Replaced with `getPluginData()` method that uses Phase 8 API endpoint:
- **Endpoint**: `GET /api/v1/plugins/{plugin_id}/data`
- **Parameters**: `start_date`, `entity_type`
- **Support**: Query parameter filtering for plugin data retrieval

### 6. registerPlugin() Method
**Issue**: Used non-existent `/register` endpoint
**Fix**: Replaced with `uploadPlugin()` method that uses Phase 8 API endpoint:
- **Endpoint**: `POST /api/v1/plugins/upload`
- **Format**: multipart/form-data with `file` field
- **Max Size**: 5MB (plugin.zip)
- **Support**: Proper FormData handling

## Phase 8 API Endpoint Alignment

| Method | Old Path | New Path | HTTP Method |
|--------|----------|----------|-------------|
| loadPlugins() | `/plugins?...` | `/plugins?...` | GET |
| getPlugin() | `/plugins/{id}` | `/plugins/{id}` | GET |
| searchByType() | `/plugins/search/by-type?plugin_type=...` | `/plugins?plugin_type=...` | GET |
| downloadPlugin() | `/plugins/{id}/download` | `/plugins/{id}` | GET |
| installPlugin() | (none) | `/plugins/{id}/install` | POST |
| uninstallPlugin() | (none) | `/plugins/{id}` | DELETE |
| getPluginData() | (new) | `/plugins/{id}/data` | GET |
| uploadPlugin() | `/plugins/register` | `/plugins/upload` | POST |

## Code Quality

- ✓ Syntax validation: Passed Node.js syntax check
- ✓ Error handling: Maintained comprehensive try-catch blocks
- ✓ Logging: Console errors preserved for debugging
- ✓ Event emissions: Updated event names where appropriate
- ✓ Documentation: Added Phase 8 API endpoint comments

## Testing Recommendations

1. **Plugin Loading**: Verify `loadPlugins()` works with query filtering
2. **Plugin Search**: Test `searchByType()` with various plugin types
3. **Plugin Installation**: Confirm `installPlugin()` triggers server install endpoint
4. **Plugin Uninstall**: Verify `uninstallPlugin()` calls DELETE endpoint
5. **Plugin Data Retrieval**: Test `getPluginData()` with date/type filters
6. **Plugin Upload**: Test `uploadPlugin()` with zip file handling
7. **Error Handling**: Verify error messages appear for failed requests

## Files Modified

- `/home/devel/basset-hound/static/js/plugin-manager.js`
  - Lines updated: 94, 114, 132-142, 165-170, 306-331, 365-397
  - Lines of code changed: ~60
  - Methods updated: 7
  - New methods added: 1 (getPluginData)

## API Reference

All changes aligned with Phase 8 API specification:
- **Document**: `/home/devel/basset-hound/docs/API_REFERENCE.md`
- **Section**: Plugin System Endpoints (lines 1716-1756)

## Notes

- `downloadPlugin()` now expects plugin objects returned from GET endpoint to include `code` and `manifest` properties
- `uploadPlugin()` method requires `FormData` API support (modern browsers)
- Server must properly set `Content-Type: application/json` for install endpoint
- All endpoint paths use consistent `/api/v1` base URL from constructor

## Validation Checklist

- [x] All endpoint paths updated to Phase 8 API spec
- [x] HTTP methods corrected (GET, POST, DELETE)
- [x] Query parameters properly formatted
- [x] Error handling maintained
- [x] Event emissions preserved
- [x] Code syntax valid
- [x] Documentation comments added
- [x] No git commits created (per constraints)

