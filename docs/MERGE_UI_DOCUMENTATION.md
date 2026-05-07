# Entity Merge & Deduplication UI - Stream 4, Phase 3

## Overview

The Entity Merge & Deduplication UI is a comprehensive feature that allows users to identify, compare, and merge duplicate entities in basset-hound. It provides an intuitive interface for managing data quality and consolidating duplicate records.

## Features

### 1. Find Duplicates Button
- **Location**: Entity detail header (next to Refresh button)
- **Style**: Warning button with clone icon
- **Behavior**: 
  - Appears automatically when entity detail is loaded
  - Clicking triggers duplicate detection
  - Only one button per entity detail view

### 2. Duplicate Detection API
- **Endpoint**: `GET /api/v1/suggestions/entity/{entityId}?type=duplicate&min_confidence=0.6&limit=100`
- **Min Confidence**: 0.6 (60%) - configurable
- **Top Results**: Shows top 5 highest confidence matches
- **Response Format**: JSON with matched entity IDs, names, and confidence scores

### 3. Duplicate Detection Modal
- **Dialog Type**: Bootstrap modal (modal-xl for wide layout)
- **Auto-sizing**: max-height: 70vh with scrollable content
- **Title**: "Duplicate Detection & Merge Tool"
- **Tab Interface**: One tab per duplicate candidate

### 4. Side-by-Side Comparison
- **Layout**: Bootstrap 2-column grid (col-md-6 each)
- **Left Column**: Current entity (primary border, blue header)
- **Right Column**: Duplicate candidate (danger border, red header)
- **Comparison Fields**:
  - Name
  - Email (with mailto link if available)
  - Phone
  - Entity Type (badge)
  - Created Date

### 5. Confidence Score Display
- **Format**: Percentage with color-coded badge
- **Calculation**: `confidence_score * 100`
- **Badge Colors**:
  - Green (bg-success): Score >= 80%
  - Yellow (bg-warning): 60% <= Score < 80%
  - Red (bg-danger): Score < 60%
- **Location**: 
  - Tab headers (next to entity name)
  - Alert box at bottom of comparison

### 6. Merge Confirmation
- **Initial State**: 
  - Merge button disabled
  - Warning alert displayed
  - Confirmation checkbox unchecked
- **Warning Message**:
  - "This will permanently merge [duplicate] into [current]"
  - "All data, relationships, and history will be transferred"
  - "The duplicate entity will be deleted and cannot be recovered"
- **Confirmation**: User must check "I understand this is irreversible" checkbox
- **After Confirmation**:
  - Merge button becomes enabled
  - Button text: "Merge Into This"

### 7. Merge Operation
- **API Endpoint**: `POST /api/v1/suggestions/linking/merge-entities`
- **Request Body**:
  ```json
  {
    "entity_id_1": "current_entity_id",
    "entity_id_2": "duplicate_entity_id",
    "keep_entity_id": "current_entity_id",
    "reason": "Duplicate entity merged via UI",
    "created_by": "web-ui"
  }
  ```
- **Processing**: Shows loading spinner with "Merging entities..." message
- **Timeout**: User should not close window during merge

### 8. Post-Merge Updates
- **Modal**: Closes automatically on success
- **Toast Notification**: Success toast appears (top-right, 3-5 second auto-dismiss)
- **Sidebar**: Merged entity removed with fade-out animation (opacity transition)
- **Detail View**: Current entity detail reloaded with updated data
- **Error Handling**: If merge fails, error alert appears in modal with dismiss option

## File Structure

### Frontend Files

#### `/static/js/merge-ui.js` (Main implementation)
- **initMergeUI()**: Initialize merge UI for an entity
- **findDuplicates()**: Fetch duplicates from API and render modal
- **renderDuplicatesComparison()**: Render comparison view with tabs
- **renderComparisonGrid()**: Render side-by-side comparison cards
- **renderEntityComparisonData()**: Format entity data for display
- **performMergeWithConfirmation()**: Show confirmation dialog
- **performMerge()**: Execute merge API call
- **createDuplicatesModal()**: Create modal container
- **showSuccessToast()**: Display success notification
- **getConfidenceBadgeClass()**: Get badge color class for score
- **extractEntityKeyData()**: Extract comparison fields from entity

#### `/templates/dashboard.html`
- Script tag loading merge-ui.js module
- Suggestions panel overlay (existing)
- No HTML modifications needed - button injected dynamically

### Backend Files

#### `/api/routers/suggestions.py`
- `GET /api/v1/suggestions/entity/{entity_id}` - Returns entity suggestions
  - Supports `min_confidence` parameter (0.5-1.0)
  - Returns high/medium/low confidence groups
  - Limited to top matches by default
- `POST /api/v1/suggestions/linking/merge-entities` - Merges two entities
  - Validates keep_entity_id
  - Moves all data items and relationships
  - Returns action ID and operation details

#### `/tests/test_merge_ui.py`
- Unit tests for merge-ui.js logic
- Integration tests for API endpoints
- Browser behavior test outlines
- Test data fixtures for 3+ duplicate entities

## Testing Guide

### Prerequisites
1. Basset-hound instance running with populated data
2. 3+ entities with similar/duplicate data
3. Browser developer tools for console error checking

### Manual Testing Steps

#### Setup Test Data
1. Create Entity A: "John Doe"
   - Email: john.doe@example.com
   - Phone: +1-555-123-4567
   
2. Create Entity B: "John M Doe" (duplicate)
   - Email: john.doe@example.com
   - Phone: +1-555-123-4567
   
3. Create Entity C: "John Doe Jr" (duplicate)
   - Email: j.doe@example.com
   - Phone: +1-555-123-4567

#### Test 1: Find Duplicates Button
1. Open Entity A detail page
2. Verify "Find Duplicates" button appears in header
3. Verify button has warning styling and clone icon
4. Close button should not duplicate on refresh

#### Test 2: Duplicate Detection
1. Click "Find Duplicates" button
2. Verify modal opens with loading spinner
3. Verify modal title is "Duplicate Detection & Merge Tool"
4. Verify modal width is wide (modal-xl)
5. Wait for results to load

#### Test 3: Modal Display
1. Verify tabs appear for top 5 duplicates (expect 2: B and C)
2. Verify each tab shows:
   - Entity name
   - Confidence score as percentage
   - Color-coded badge
3. Verify first tab is selected by default
4. Click second tab and verify content changes

#### Test 4: Side-by-Side Comparison
1. Verify left column:
   - Header: "Current Entity" with blue color
   - Shows Entity A data
2. Verify right column:
   - Header: "Potential Duplicate" with red color
   - Shows Entity B data
3. Verify all fields displayed:
   - Name: Formatted correctly
   - Email: Clickable mailto link if present
   - Phone: Formatted correctly
   - Entity Type: Shows as badge
   - Created: Shows ISO date format
4. Verify confidence score at bottom:
   - Shows percentage
   - Has color badge (green for >80%, etc.)

#### Test 5: Merge Confirmation
1. Scroll to bottom of comparison
2. Verify "Cancel" and "Merge Into This" buttons
3. Verify "Merge Into This" button is disabled/grayed out
4. Verify warning alert appears above buttons:
   - Shows irreversible warning
   - Lists data that will be transferred
   - Has unchecked confirmation checkbox
5. Check the confirmation checkbox
6. Verify merge button becomes enabled
7. Verify button text changes to "Merge Into This"

#### Test 6: Merge Execution
1. Click "Merge Into This" button
2. Verify loading spinner appears
3. Verify message says "Merging entities..."
4. Wait for merge to complete (should take <5 seconds)
5. Verify:
   - Modal closes automatically
   - Success toast appears (top-right, green)
   - Toast message: "Successfully merged... entities!"
   - Toast auto-dismisses after 3-5 seconds

#### Test 7: Post-Merge Updates
1. Verify sidebar:
   - Entity B (merged entity) is removed
   - Fade-out animation visible
2. Verify current entity detail:
   - Data from Entity B is now included
   - Created/updated timestamps adjusted
   - No duplicate data shown
3. Refresh page and verify:
   - Entity B no longer appears in sidebar
   - Only Entity A and C remain
   - Entity A contains merged data

#### Test 8: Error Handling
1. Simulate merge failure:
   - Mock API error response
   - Or disable network and retry
2. Verify error alert appears in modal:
   - "Error Merging Entities" title
   - Readable error message
   - Dismiss button
3. Verify no broken state:
   - Can close modal
   - Can retry merge
4. Check browser console:
   - Error should be logged
   - No JavaScript errors should appear

#### Test 9: Multiple Merges
1. After first merge, open Entity A again
2. Click "Find Duplicates"
3. Verify Entity C is still shown as duplicate
4. Merge Entity C into Entity A
5. Verify both merges successful
6. Verify sidebar now shows only Entity A
7. Verify Entity A contains data from A, B, and C

#### Test 10: Console Error Check
1. Open browser Developer Tools (F12)
2. Go to Console tab
3. Perform all merge operations
4. Verify:
   - No JavaScript errors
   - No uncaught exceptions
   - No 404s for API calls
   - All API responses successful

### Automated Testing

Run pytest tests:
```bash
pytest tests/test_merge_ui.py -v
```

Tests verify:
- Confidence badge color logic
- Entity data extraction
- API response parsing
- Merge request validation
- Error handling

## API Integration

### GET /api/v1/suggestions/entity/{entityId}

**Parameters:**
- `type` (optional): "duplicate" to filter for duplicates
- `min_confidence` (float): 0.6 default, range 0.0-1.0
- `limit` (int): 100 default, max 100
- `offset` (int): 0 default, for pagination
- `include_partial` (bool): true default

**Response:**
```json
{
  "data": {
    "entity_id": "person_001",
    "suggestions": [
      {
        "confidence": "HIGH",
        "matches": [
          {
            "data_id": "data_001",
            "data_type": "email",
            "data_value": "john.doe@example.com",
            "match_type": "exact_hash",
            "confidence_score": 0.95,
            "matched_entity_id": "person_002",
            "matched_entity_name": "John M Doe"
          }
        ]
      }
    ],
    "total_count": 1,
    "high_confidence_count": 1,
    "medium_confidence_count": 0,
    "low_confidence_count": 0,
    "dismissed_count": 0
  },
  "pagination": {...},
  "_links": {...}
}
```

### POST /api/v1/suggestions/linking/merge-entities

**Request:**
```json
{
  "entity_id_1": "person_001",
  "entity_id_2": "person_002",
  "keep_entity_id": "person_001",
  "reason": "Duplicate entity merged via UI",
  "created_by": "web-ui"
}
```

**Response:**
```json
{
  "success": true,
  "action_id": "action_12345",
  "kept_entity_id": "person_001",
  "merged_entity_id": "person_002",
  "data_items_moved": 5,
  "relationships_moved": 2,
  "reason": "Duplicate entity merged via UI",
  "created_at": "2025-05-07T12:00:00Z",
  "warning": null,
  "_links": {...}
}
```

**Error Responses:**
- 400: Invalid keep_entity_id or malformed request
- 404: Entity not found
- 409: Cannot merge (conflict or other issue)
- 500: Internal server error

## Browser Compatibility

- Chrome/Edge: Latest 2 versions
- Firefox: Latest 2 versions
- Safari: Latest 2 versions
- Bootstrap 5.3.0
- Font Awesome 6.5.0

## Performance Considerations

- **API call**: Cached by browser (60 second default)
- **Modal rendering**: <500ms for 5 duplicates
- **Merge operation**: 1-10 seconds depending on data volume
- **UI update**: <300ms for fade and removal

## Known Limitations

1. Merge is always into the "current" entity (first parameter)
2. No undo/rollback after merge (check audit trail for history)
3. Top 5 duplicates shown (can be increased via API limit parameter)
4. Requires Entity A data to already be loaded in detail view

## Future Enhancements

1. Merge direction selector (merge A into B or B into A)
2. Batch merge multiple entities at once
3. Undo/rollback merge operation (with audit trail)
4. Customizable confidence thresholds per entity type
5. Merge preview showing all combined data
6. Conflict resolution UI for overlapping data
7. Scheduled automatic duplicate detection
8. Smart duplicate detection based on entity type

## Support & Troubleshooting

### Modal doesn't appear
1. Check browser console for errors
2. Verify API endpoint is accessible
3. Ensure entity ID is valid
4. Check if duplicates exist (may show "No duplicates found")

### Merge fails
1. Check network tab in developer tools
2. Verify API response in Network tab
3. Look for error message in modal
4. Check server logs for detailed error

### No duplicates detected
1. Verify test data has matching fields
2. Check min_confidence threshold (may be too high)
3. Ensure entities are in same project
4. Run suggestion service to generate matches

## Related Features

- Smart Suggestions Panel (Phase 44)
- Relationship Manager (Stream 3)
- Advanced Search (Stream 8)
- Bulk Import (Stream 10)

## Version History

- **v1.0.0** (2026-05-07): Initial release - Stream 4, Phase 3
  - Find Duplicates button
  - Side-by-side comparison modal
  - Confidence scoring with badges
  - Merge operation with confirmation
  - Post-merge UI updates
