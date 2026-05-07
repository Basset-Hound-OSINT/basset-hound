# Merge UI Quick Start Guide

## What Is This?

The Entity Merge & Deduplication UI is a tool that finds duplicate entities in basset-hound and lets you merge them safely. It's part of Stream 4, Phase 3.

## For Users

### How to Use

1. **Open an Entity**: Navigate to any entity's detail page
2. **Find Duplicates**: Click the orange "Find Duplicates" button in the header
3. **Review Matches**: A modal opens showing potential duplicates (up to 5)
4. **Compare**: Each tab shows a side-by-side comparison
   - Left side: Current entity
   - Right side: Potential duplicate
   - Green badge: Very confident match (>80%)
   - Yellow badge: Confident match (60-80%)
   - Red badge: Lower confidence (<60%)
5. **Confirm Merge**: 
   - Read the irreversible warning carefully
   - Check "I understand..." checkbox
   - Click "Merge Into This" button
6. **Done**: Success toast appears, merged entity is removed, current entity updated

### What Gets Merged?

When you merge Entity A into Entity B:
- All data from A is transferred to B
- All relationships are updated to point to B
- Entity A is deleted
- This cannot be undone!

## For Developers

### File Locations

- **Main UI**: `/static/js/merge-ui.js`
- **Template**: `/templates/dashboard.html` (loads merge-ui.js)
- **Tests**: `/tests/test_merge_ui.py` and `test_merge_ui_integration.py`
- **Docs**: `MERGE_UI_DOCUMENTATION.md` (detailed)

### Key Functions in merge-ui.js

```javascript
// Initialize merge UI for an entity
initMergeUI(entityId, projectName)

// Fetch duplicates and show modal
findDuplicates(entityId, projectName)

// Show side-by-side comparison
renderDuplicatesComparison(modal, currentEntity, duplicates, ...)

// Merge with confirmation
performMergeWithConfirmation(modal, currentEntity, duplicateEntity, ...)

// Execute the merge
performMerge(modal, currentEntity, currentEntityId, duplicateEntityId, ...)
```

### API Endpoints Used

**Get Suggestions:**
```
GET /api/v1/suggestions/entity/{entityId}?type=duplicate&min_confidence=0.6&limit=100
```

**Merge Entities:**
```
POST /api/v1/suggestions/linking/merge-entities
```

### Testing

**Run tests:**
```bash
pytest tests/test_merge_ui.py -v
pytest tests/test_merge_ui_integration.py -v
```

**Manual test:**
1. Create 3 entities with similar data
2. Open Entity 1 detail page
3. Click "Find Duplicates"
4. Verify Entity 2 and 3 shown
5. Merge into Entity 1
6. Verify success

### Customization

**Change confidence threshold:**
In `findDuplicates()`, line with `min_confidence=0.6`:
```javascript
const duplicatesRes = await fetch(
  `/api/v1/suggestions/entity/${entityId}?min_confidence=0.7` // Changed to 0.7
);
```

**Change top results count:**
In `findDuplicates()`, change `.slice(0, 5)` to desired number:
```javascript
const topMatches = allMatches.slice(0, 10); // Top 10 instead of 5
```

**Customize button styling:**
In `initMergeUI()`, change button class:
```javascript
findDuplicatesBtn.className = 'btn btn-info'; // Changed from btn-warning
```

### Understanding the Flow

```
User clicks "Find Duplicates"
         ↓
Modal opens with spinner
         ↓
API call: GET /api/v1/suggestions/entity/{id}
         ↓
Results returned (top 5)
         ↓
Modal renders tabs for each duplicate
         ↓
User clicks tab to view comparison
         ↓
Modal shows side-by-side comparison
         ↓
User checks confirmation checkbox
         ↓
Merge button becomes enabled
         ↓
User clicks "Merge Into This"
         ↓
Loading spinner appears
         ↓
API call: POST /api/v1/suggestions/linking/merge-entities
         ↓
Merge successful
         ↓
Modal closes, toast appears
         ↓
UI updates: sidebar removes entity, detail reloads
```

### Common Issues & Fixes

**Problem**: Modal doesn't open
- **Fix**: Check browser console (F12 → Console)
- **Fix**: Verify entity ID is valid
- **Fix**: Check API is running

**Problem**: No duplicates found
- **Fix**: Verify entities have matching data (email, phone, name)
- **Fix**: Lower `min_confidence` threshold
- **Fix**: Run suggestion service to generate matches

**Problem**: Merge fails
- **Fix**: Check Network tab in developer tools
- **Fix**: Look for error message in modal
- **Fix**: Check server logs

**Problem**: After merge, sidebar not updated
- **Fix**: Refresh page manually (F5)
- **Fix**: Check browser console for errors

### Debugging Tips

1. **Check Console**: 
   - Press F12 to open Developer Tools
   - Go to Console tab
   - Look for errors (red X)

2. **Check Network**:
   - Go to Network tab
   - Click Find Duplicates
   - Look for API calls
   - Check response status (should be 200)

3. **Check Element**:
   - Go to Inspector tab
   - Find "Find Duplicates" button
   - Verify it's styled correctly
   - Check modal structure

4. **Use Debugger**:
   - Set breakpoints in merge-ui.js
   - Step through code
   - Inspect variables

### Integration with Other Features

**Related to:**
- Smart Suggestions Panel (Phase 44)
- Relationship Manager (Stream 3)
- Advanced Search (Stream 8)

**Depends on:**
- Bootstrap 5.3.0 modal
- Font Awesome 6.5.0 icons
- utils.js (getDisplayName)
- ui-person-details.js (renderPersonDetails)

## Quick Reference

| Component | File | Lines |
|-----------|------|-------|
| Main logic | merge-ui.js | 10-609 |
| Init function | merge-ui.js | 10-31 |
| Find duplicates | merge-ui.js | 90-176 |
| Render comparison | merge-ui.js | 177-278 |
| Perform merge | merge-ui.js | 452-532 |
| Modal creation | merge-ui.js | 537-564 |
| Toast notification | merge-ui.js | 569-609 |

## Version

**Merge UI v1.0.0** - Released May 7, 2026

## Support

For detailed documentation, see: `MERGE_UI_DOCUMENTATION.md`

For test details, see: `tests/test_merge_ui.py` and `test_merge_ui_integration.py`
