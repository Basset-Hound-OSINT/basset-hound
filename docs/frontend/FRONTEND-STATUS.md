# Basset-Hound Frontend Status

**Last Updated:** 2026-01-31
**Overall Status:** Early stage - approximately 5-10% of API features exposed

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current Capabilities](#current-capabilities)
3. [Recent Changes](#recent-changes)
4. [Gap Analysis](#gap-analysis)
5. [Prioritized Improvements](#prioritized-improvements)
6. [Technical Details](#technical-details)

---

## Executive Summary

Basset-Hound is an **API-first** application with a secondary web frontend. The backend API is mature with 130+ MCP tools and comprehensive REST endpoints. However, the frontend exposes only a small fraction of these capabilities.

### Quick Stats

| Metric | Value |
|--------|-------|
| API Endpoints | 100+ |
| MCP Tools | 130 |
| Frontend Features | ~10-15 |
| API Feature Coverage | ~5-10% |

### Status by Category

| Category | API | Frontend | Gap |
|----------|-----|----------|-----|
| Entity CRUD | Full | Full | None |
| Entity Types | 7 types | 7 types | None |
| Relationships | Full CRUD | None | Critical |
| Search | Advanced | Basic text | Major |
| Deduplication | Full | None | Major |
| Bulk Import | CSV, JSON, Neo4j | None | Major |
| Graph Visualization | Full API | Basic (untested) | Moderate |
| Smart Suggestions | Full API | None | Major |
| Timeline | Full API | None | Minor |

---

## Current Capabilities

### Working Features

#### 1. Project Management (Full)
- **Create new project**: Form with project name
- **List projects**: Shows all existing projects with metadata
- **Open project**: Navigate to project dashboard
- **Download project**: Export project data

**Files:**
- `/templates/index.html` - Project selection page
- `/static/js/dashboard.js` - Project context management

#### 2. Entity Management (Full)
- **Add Entity**: Modal with entity type selection
  - Person, Organization, Government, Group, Sock Puppet, Location, Unknown
- **View Entity**: Display entity details with all fields
- **Edit Entity**: Inline field editing
- **Delete Entity**: With confirmation
- **List Entities**: Sidebar list with search

**Files:**
- `/templates/dashboard.html` - Main dashboard with entity list and details
- `/static/js/ui-people-list.js` - Entity list management
- `/static/js/ui-person-details.js` - Entity detail view
- `/static/js/ui-form-handlers.js` - Form handling

#### 3. Basic Search (Limited)
- **Text search**: Search entities by name
- No advanced filters
- No search across all fields
- No saved searches

**Files:**
- Search input in `/templates/dashboard.html` sidebar

#### 4. File Management (Basic)
- **Upload files**: Drag-and-drop or file picker
- **List files**: File explorer overlay
- **View files**: Preview supported formats
- **Download files**: Direct download links
- **Reports**: Create/edit Markdown reports

**Files:**
- `/static/js/file_explorer.js` - File explorer functionality
- `/static/js/report-handler.js` - Report management
- `/static/css/file_explorer.css` - File explorer styling

#### 5. Graph Visualization (Exists, Untested)
- **Network map**: Cytoscape.js-based graph view
- Located at `/map.html`
- **Status**: Needs testing with current API

**Files:**
- `/templates/map.html` - Graph visualization page
- `/static/js/map-handler.js` - Graph rendering logic

#### 6. Tags (Basic)
- **Add tags**: Tag entities with custom labels
- **View tags**: Display tags on entity details

**Files:**
- `/static/js/tag-handler.js` - Tag functionality

---

## Recent Changes

### 2026-01-31: Add Entity Modal Update

**Change:** "Add Person" button changed to "Add Entity" with type selection modal.

**Implementation:**
- Added entity type selection modal to `dashboard.html`
- 7 entity types supported:
  - Person (fa-user)
  - Organization (fa-building)
  - Government (fa-landmark)
  - Group (fa-users)
  - Sock Puppet (fa-user-secret)
  - Location (fa-map-marker-alt)
  - Unknown (fa-question-circle)

**Modal Structure:**
```html
<div class="modal" id="entityTypeModal">
  <div class="list-group" id="entity-type-list">
    <button data-entity-type="person">Person</button>
    <button data-entity-type="organization">Organization</button>
    <!-- ... other types -->
  </div>
</div>
```

---

## Gap Analysis

### Critical Gaps (No Frontend UI)

#### 1. Relationship Management
**API Capabilities:**
- Create relationships between entities
- Delete relationships
- List relationships for an entity
- Relationship types: KNOWS, WORKS_WITH, LOCATED_AT, etc.
- Bidirectional relationships
- Relationship properties (confidence, date range, notes)

**Frontend Status:** No UI whatsoever

**Impact:** Users cannot create or view relationships - the core graph functionality is inaccessible.

**API Endpoints:**
```
GET  /api/v1/relationships/{project}/{entity_id}
POST /api/v1/relationships/{project}
DELETE /api/v1/relationships/{project}/{relationship_id}
GET  /api/v1/relationship-types
```

#### 2. Advanced Search
**API Capabilities:**
- Full-text search across all fields
- Fuzzy/phonetic matching
- Entity type filtering
- Date range filtering
- Relationship depth filtering
- Field-specific search
- Saved search configurations

**Frontend Status:** Basic text search only

**Impact:** Investigations require finding related data - basic search is insufficient.

**API Endpoints:**
```
POST /api/v1/search/{project}/advanced
POST /api/v1/search/{project}/fuzzy
GET  /api/v1/saved-searches/{project}
POST /api/v1/saved-searches/{project}
```

#### 3. Deduplication & Merge
**API Capabilities:**
- Duplicate candidate detection
- Confidence scoring
- Entity merging with data consolidation
- Merge preview
- Audit trail

**Frontend Status:** No UI

**Impact:** Data quality suffers as duplicates accumulate.

**API Endpoints:**
```
GET  /api/v1/deduplication/{project}/candidates
POST /api/v1/entities/{project}/merge
GET  /api/v1/suggestions/{project}
```

#### 4. Smart Suggestions
**API Capabilities:**
- Match suggestions with confidence scores
- Batch accept/dismiss
- Auto-accept configuration
- Match explanation

**Frontend Status:** No UI (specs exist in `docs/UI-COMPONENTS-SPECIFICATION.md`)

**Impact:** Users miss potential connections between data.

**API Endpoints:**
```
GET  /api/v1/suggestions/{project}
POST /api/v1/suggestions/batch/accept
POST /api/v1/suggestions/auto-accept/preview
POST /api/v1/suggestions/auto-accept/execute
```

#### 5. Bulk Import
**API Capabilities:**
- CSV import with field mapping
- JSON import
- Neo4j import
- Import validation
- Import history

**Frontend Status:** No UI

**Impact:** Manual data entry is tedious for large datasets.

**API Endpoints:**
```
POST /api/v1/import/{project}/csv
POST /api/v1/import/{project}/json
GET  /api/v1/import/{project}/history
```

### Moderate Gaps

#### 6. Relationship Type Management
**API Capabilities:**
- List all relationship types
- Custom relationship types
- Type metadata (description, icon, color)

**Frontend Status:** No UI for viewing or managing types

#### 7. Timeline Visualization
**API Capabilities (Phase 17):**
- Entity timeline events
- Relationship timeline
- Activity heatmap
- Temporal snapshots
- Period comparison

**Frontend Status:** No UI (API ready)

---

## Prioritized Improvements

### Priority 1: Critical (Blocks Core Functionality)

| Feature | Effort | Value | Notes |
|---------|--------|-------|-------|
| Relationship Management UI | Medium | High | Core graph feature |
| Advanced Search UI | Medium | High | Essential for investigations |

### Priority 2: Important (Improves Workflow)

| Feature | Effort | Value | Notes |
|---------|--------|-------|-------|
| Deduplication UI | Medium | Medium | Data quality |
| Smart Suggestions UI | Medium | Medium | Specs already exist |
| Bulk Import UI | High | Medium | Data ingestion |

### Priority 3: Nice to Have (Polish)

| Feature | Effort | Value | Notes |
|---------|--------|-------|-------|
| Graph Visualization Polish | Low | Low | Test existing, add filters |
| Timeline Visualization | Medium | Low | API ready |
| Relationship Type Management | Low | Low | Admin feature |

---

## Technical Details

### Frontend Architecture

**Technology Stack:**
- Vanilla JavaScript (ES6 modules)
- Bootstrap 5.3.0
- jQuery 3.6.0 (legacy, being phased out)
- Cytoscape.js (graph visualization)
- Marked.js (Markdown rendering)
- Font Awesome 6.5.0 (icons)

**Module Structure:**
```
/static/js/
  api.js              # API communication
  dashboard.js        # Main dashboard logic
  ui-form-handlers.js # Form handling
  ui-people-list.js   # Entity list
  ui-person-details.js # Entity details
  file_explorer.js    # File management
  report-handler.js   # Report handling
  tag-handler.js      # Tagging
  map-handler.js      # Graph visualization
  utils.js            # Utility functions
```

**CSS Structure:**
```
/static/css/
  dashboard.css       # Main dashboard styles
  file_explorer.css   # File explorer styles
```

**Template Structure:**
```
/templates/
  index.html          # Project selection
  dashboard.html      # Main dashboard
  map.html            # Graph visualization
  osint.html          # OSINT tools (legacy)
```

### API Integration Pattern

**Current Pattern:**
```javascript
// api.js
export async function getEntities(projectId) {
  const response = await fetch(`/api/v1/entities/${projectId}`);
  return response.json();
}

// Usage in components
import { getEntities } from './api.js';
const entities = await getEntities(window.currentProjectId);
```

### Configuration

**App Config (passed to frontend):**
```javascript
window.appConfig = {{ config|tojson|safe }};
```

Configuration includes:
- Entity type definitions
- Field configurations
- Section layouts

### Adding New Features

**Recommended Approach:**
1. Create new JS module in `/static/js/`
2. Add CSS to `/static/css/` if needed
3. Add HTML components/modals to `dashboard.html`
4. Use existing patterns from `api.js` for API calls
5. Test thoroughly before deployment

**Example: Adding Relationship UI**
```javascript
// static/js/relationship-handler.js
import { api } from './api.js';

export async function createRelationship(projectId, data) {
  return api.post(`/relationships/${projectId}`, data);
}

export function renderRelationshipList(relationships) {
  // Render relationship list UI
}
```

---

## Related Documentation

- [ROADMAP.md](../ROADMAP.md) - Project roadmap with Phase 52 frontend improvements
- [UI-COMPONENTS-SPECIFICATION.md](../UI-COMPONENTS-SPECIFICATION.md) - Smart Suggestions UI specs
- [UI-INTERACTION-FLOWS.md](../UI-INTERACTION-FLOWS.md) - Interaction flow designs
- [Phase 17 Findings](../findings/17-PHASE17-FRONTEND-INTEGRATION-UI-ENHANCEMENTS.md) - Frontend integration APIs

---

## Changelog

| Date | Change |
|------|--------|
| 2026-01-31 | Initial document created |
| 2026-01-31 | Documented Add Entity modal with type selection |
