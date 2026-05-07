# Advanced Search UI - Stream 2 Phase 3

## Overview

The Advanced Search UI provides comprehensive search and filtering capabilities for the basset-hound OSINT dashboard. Users can search by specific fields, apply boolean filters, and use date ranges to find entities.

## Features Implemented

### 1. Search Toggle Button
- Located below basic search input in sidebar
- Toggles between basic and advanced search modes
- Visual indicator showing current search mode
- Smooth transition between modes

### 2. Field-Specific Filters
- **Name**: Search by first or last name
- **Email**: Search by email address
- **Phone**: Search by phone number
- **Username**: Search by username/social handle

### 3. Entity Type Selector
- Dropdown with multiple selection support
- Entity types: Person, Organization, Government, Group, Sock Puppet, Location, Unknown
- Allows filtering by one or more entity types

### 4. Boolean Mode Toggle
- **AND Mode**: All filters must match (default)
- **OR Mode**: Any filter can match
- Visual button group for easy selection
- Clear explanation of behavior

### 5. Date Range Filters
- **Created After**: Filter entities created after a specific date
- **Created Before**: Filter entities created before a specific date
- Both filters optional and can be used independently

### 6. Advanced Query Input
- Supports advanced boolean syntax
- Allows power users to write complex queries
- Syntax help link for documentation
- Example: `email:*@gmail.com AND tag:suspect`

### 7. Search Results
- Results display in entity list sidebar
- Shows entity type and relevance score
- Matched fields highlighted
- Clickable to view full entity details
- Result count badge shows total matches

### 8. Result Management
- Clear button to reset all filters
- Restores full entity list
- Session persistence for filter state
- Result count updates in real-time

### 9. Responsive Design
- Desktop: Full-width search panel with all options visible
- Tablet (768px): Optimized layout with smaller form controls
- Mobile (576px): Compact design with minimum required width
- Touch-friendly buttons and inputs

## Technical Architecture

### Files Modified/Created

1. **static/js/advanced-search.js** (651 lines)
   - Main advanced search module
   - Filter state management
   - API integration
   - UI event handling
   - Search execution and result rendering

2. **static/css/dashboard.css**
   - Advanced search panel styling
   - Responsive breakpoints
   - Form control customization
   - Result badge styling
   - Mobile optimization

3. **templates/dashboard.html**
   - Script module import already present
   - No additional HTML markup needed (UI created dynamically)

### Class: AdvancedSearchState
```javascript
{
    name: '',                    // Name filter
    email: '',                   // Email filter
    phone: '',                   // Phone filter
    username: '',                // Username filter
    entityTypes: [],             // Selected entity types
    tags: [],                    // Tag filters
    booleanMode: 'AND',          // AND or OR
    createdAfter: '',            // Date start
    createdBefore: '',           // Date end
    customQuery: ''              // Advanced syntax query
}
```

Methods:
- `save()`: Persist state to sessionStorage
- `load()`: Restore state from sessionStorage
- `clear()`: Reset all filters
- `hasActiveFilters()`: Check if any filters active

### Functions

#### initAdvancedSearch(projectName)
Main entry point for advanced search initialization.
- Called from dashboard.js with project safe name
- Sets up toggle button and search panel
- Restores previous search state if available

#### setupToggleButton()
Creates and manages the advanced search toggle button.
- Toggles between basic and advanced modes
- Updates mode indicator text
- Manages visibility of search input

#### setupAdvancedSearchPanel(state, projectName)
Creates the advanced search panel HTML and sets up event listeners.
- Builds responsive form with all filter options
- Injects into sidebar
- Restores saved state values

#### executeAdvancedSearch(state, projectName)
Executes the search via API.
- Builds query string from filters
- Handles boolean operators
- Calls `/api/v1/projects/{project}/search/advanced`
- Displays results in entity list

#### displaySearchResults(results, total)
Renders search results in the entity list.
- Creates clickable list items
- Shows type and relevance score
- Matched fields annotation
- Updates result count badge
- Loads full entity details on click

## API Integration

### Endpoints Used

1. **GET /api/v1/projects/{project}/search/advanced**
   - Main advanced search endpoint
   - Parameters: `q` (query), `limit`, `offset`, `highlight`
   - Returns: Results with scores, highlights, and matched fields

2. **GET /api/v1/projects/{project}/search**
   - Basic search fallback
   - Used for basic mode result counting

### Query Format

```
name:John AND email:*@gmail.com
tag:suspect OR tag:poi
(created_after:2024-01-01 AND created_before:2024-12-31)
NOT status:cleared
```

## Usage Examples

### Example 1: Find Gmail Users Named John
1. Toggle to Advanced Search
2. Enter "John" in Name field
3. Enter "*@gmail.com" in Email field
4. Keep AND mode selected
5. Click Search

### Example 2: Find All Suspects or POIs
1. Toggle to Advanced Search
2. Enter `tag:suspect OR tag:poi` in Advanced Query field
3. Click Search

### Example 3: Find Recent Entities
1. Toggle to Advanced Search
2. Set Created After to 2024-01-01
3. Select desired entity types
4. Click Search

### Example 4: Complex Boolean Query
1. Toggle to Advanced Search
2. Use Advanced Query: `(name:John OR name:Jane) AND email:*@example.com AND NOT archived:true`
3. Click Search

## Event Flow

```
1. User clicks "Advanced" button
   ↓
2. Advanced search panel appears
   ↓
3. User fills form and clicks Search
   ↓
4. executeAdvancedSearch() builds query
   ↓
5. API call to /api/v1/projects/{project}/search/advanced
   ↓
6. Results returned with highlights
   ↓
7. displaySearchResults() renders list items
   ↓
8. User clicks result item
   ↓
9. Full entity details fetched and displayed
```

## Keyboard Shortcuts

- **Enter** in any text field: Triggers search
- **Escape** in form: Could close panel (future enhancement)
- **Tab**: Navigate through form fields

## Error Handling

- Invalid search syntax: User-friendly alert message
- Network errors: Logged to console, graceful failure
- Missing project: HTTP 404 handled with notification
- Empty results: Shows "No results found" message

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+
- Mobile browsers: Chrome Android, Safari iOS

## Performance Characteristics

- **Pagination**: Unlimited results (default 100, max 1000)
- **Debounce**: 300ms for basic search typing
- **State Persistence**: Via sessionStorage (survives page refresh)
- **Caching**: None at client-level
- **Highlight**: Enabled by default for keyword matches

## CSS Classes

### Main Classes
- `#advanced-search-panel` - Container for entire panel
- `.card-header` - Top section with close button
- `.card-body` - Form content area
- `#search-result-badge` - Result count display

### Responsive Classes
- `d-none` - Hide elements
- `d-flex` - Flexbox layout
- `flex-wrap` - Wrap flex items
- `flex-grow-1` - Fill available space
- Bootstrap 5 grid classes

## Session Storage

Search state saved with key: `advancedSearchState`

Contents:
```json
{
    "name": "John",
    "email": "john@example.com",
    "entityTypes": ["person"],
    "booleanMode": "AND",
    "customQuery": "email:*@gmail.com",
    ...
}
```

## Future Enhancements

1. Saved searches feature
2. Search history with recents
3. Advanced operators: NEAR, WITHIN distance
4. Regex pattern support
5. Field value autocomplete
6. Search suggestions as you type
7. Export search results to CSV
8. Bulk actions on search results

## Testing Checklist

- [ ] Toggle button works without errors
- [ ] All form fields populate correctly
- [ ] AND/OR mode affects results
- [ ] Date filters work as expected
- [ ] Entity type filter works
- [ ] Custom query syntax supported
- [ ] Results display with correct styling
- [ ] Clicking result loads details
- [ ] Clear button resets form
- [ ] Mobile layout adapts properly
- [ ] Search persists after page reload
- [ ] No console errors

## Debugging

Enable console logging with:
```javascript
// In advanced-search.js
console.log('Advanced Search Debug:', { state, query, response });
```

View saved state:
```javascript
// In browser console
JSON.parse(sessionStorage.getItem('advancedSearchState'))
```

## Version

- Version: 1.0
- Release: Stream 2, Phase 3
- Last Updated: 2026-05-07
