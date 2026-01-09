# UI Interaction Flows
## Smart Suggestions System

**Version:** 1.0
**Date:** 2026-01-09
**Status:** Draft

---

## Table of Contents

1. [Overview](#overview)
2. [Core Flows](#core-flows)
3. [Edge Cases](#edge-cases)
4. [Error Handling](#error-handling)
5. [State Management](#state-management)

---

## Overview

This document defines all user interaction flows for the Smart Suggestions system. Each flow includes:
- Step-by-step user actions
- System responses
- Visual state changes
- Error handling
- Success/failure paths

---

## Core Flows

### Flow 1: View Suggestions

**User Goal:** Browse available suggestions

**Entry Points:**
- Navigate to entity detail page
- Click "Suggestions" tab
- Receive real-time notification

**Flow Diagram:**

```
Start
  │
  ├─→ Load Entity Page
  │     │
  │     ├─→ Show skeleton loader
  │     │   └─→ "Finding matches..." (0-500ms)
  │     │
  │     ├─→ Fetch suggestions via API
  │     │   └─→ Progress bar: 0% → 100%
  │     │
  │     └─→ Render suggestions
  │           │
  │           ├─→ Group by confidence level
  │           ├─→ Sort by score (descending)
  │           └─→ Show filters (HIGH/MEDIUM/LOW)
  │
  └─→ Success State
        │
        ├─→ Display suggestion cards
        ├─→ Show count badge "(5)"
        └─→ Enable all actions
```

**Detailed Steps:**

1. **Initial Load**
   ```
   User Action: Navigate to /entities/ent_abc123
   System Response:
   - Render page skeleton
   - Show loading indicator
   - Display "Finding matches..." message
   ```

2. **Fetching Suggestions**
   ```
   System Action: GET /api/suggestions?entity_id=ent_abc123
   Progress Updates:
   - 0%: "Analyzing entities..."
   - 30%: "Comparing data items..."
   - 60%: "Calculating confidence scores..."
   - 90%: "Ranking suggestions..."
   - 100%: "Complete!"
   ```

3. **Rendering Results**
   ```
   System Response:
   - Animate in suggestion cards (stagger 50ms each)
   - Update filter counts: HIGH (2), MEDIUM (2), LOW (1)
   - Enable all interactive elements
   - Focus first suggestion card
   ```

4. **No Suggestions Found**
   ```
   System Response:
   - Show empty state illustration
   - Display message: "No suggestions found"
   - Show help text: "We'll notify you when matches are detected"
   - Offer action: "Configure suggestion settings"
   ```

**State Transitions:**

```
LOADING → LOADED (with results)
LOADING → EMPTY (no results)
LOADING → ERROR (network failure)
```

**Visual States:**

```
LOADING:
┌─────────────────────────────────────────┐
│ ⏳ Finding matches...                   │
│ [████████████░░░░░░░░] 65%             │
│ Analyzing 127 entities...               │
└─────────────────────────────────────────┘

LOADED:
┌─────────────────────────────────────────┐
│ Suggested Tags (5)         [Settings]   │
│ [🟢 HIGH (2)] [🟡 MEDIUM (2)]          │
│ ... (suggestion cards) ...              │
└─────────────────────────────────────────┘

EMPTY:
┌─────────────────────────────────────────┐
│         🔍                              │
│     No suggestions found                │
│                                         │
│ We'll notify you when matches are       │
│ detected for this entity.               │
│                                         │
│ [Configure Settings]                    │
└─────────────────────────────────────────┘
```

---

### Flow 2: Link Entities

**User Goal:** Create a link between two entities without merging

**Prerequisites:**
- User has viewed a suggestion
- Suggestion confidence score ≥ 0.5

**Flow Diagram:**

```
Start
  │
  ├─→ User clicks "Link Entities"
  │     │
  │     ├─→ Show confirmation prompt (optional)
  │     │   └─→ "Link john.doe@example.com to John Smith?"
  │     │
  │     ├─→ Update UI optimistically
  │     │   ├─→ Disable button
  │     │   ├─→ Show spinner: "Linking..."
  │     │   └─→ Fade suggestion card
  │     │
  │     ├─→ Send API request
  │     │   └─→ POST /api/entity-links
  │     │
  │     └─→ Handle response
  │           │
  │           ├─→ SUCCESS
  │           │   ├─→ Remove suggestion card
  │           │   ├─→ Show toast: "✓ Successfully linked"
  │           │   ├─→ Update entity profile
  │           │   └─→ Enable undo (5 seconds)
  │           │
  │           └─→ ERROR
  │               ├─→ Restore suggestion card
  │               ├─→ Show error toast
  │               └─→ Re-enable button
  │
  └─→ End
```

**Detailed Steps:**

1. **User Initiates Action**
   ```
   User Action: Click "Link Entities" button

   System Response:
   - Disable button immediately
   - Show loading spinner
   - Change button text: "Link Entities" → "Linking..."
   - Add CSS class: .loading
   ```

2. **Optimistic Update**
   ```
   UI Changes:
   - Fade out suggestion card (300ms)
   - Slide up remaining cards
   - Update count badge: (5) → (4)
   - Update filter counts
   ```

3. **API Request**
   ```
   POST /api/entity-links
   {
     "source_entity_id": "ent_abc123",
     "target_entity_id": "ent_def456",
     "link_type": "data_match",
     "confidence_score": 0.95,
     "reason": "Email match: john.doe@example.com"
   }

   Response:
   {
     "link_id": "link_xyz789",
     "created_at": "2026-01-09T10:32:00Z",
     "status": "active"
   }
   ```

4. **Success Response**
   ```
   System Actions:
   - Remove suggestion from DOM (after animation)
   - Show toast notification:
     ┌────────────────────────────────────┐
     │ ✓ Successfully linked entities     │
     │ john.doe@example.com → John Smith  │
     │ [Undo]                        [✕]  │
     └────────────────────────────────────┘

   - Update entity profile (add linked entity)
   - Refresh related data counts
   - Log action to audit trail
   ```

5. **Undo Window**
   ```
   User Action: Click "Undo" within 5 seconds

   System Response:
   - DELETE /api/entity-links/link_xyz789
   - Restore suggestion card (animate in)
   - Update count badge: (4) → (5)
   - Show confirmation: "Link removed"
   - Re-enable all actions
   ```

**State Machine:**

```
IDLE → LINKING → LINKED → [UNDO] → IDLE
                    ↓
                  ERROR → IDLE
```

**Error Scenarios:**

1. **Network Error**
   ```
   Toast:
   ┌────────────────────────────────────┐
   │ ✕ Failed to link entities          │
   │ Network error. Please try again.   │
   │ [Retry]                       [✕]  │
   └────────────────────────────────────┘

   Actions:
   - Restore suggestion card
   - Re-enable button
   - Log error details
   ```

2. **Validation Error**
   ```
   Toast:
   ┌────────────────────────────────────┐
   │ ⚠ Cannot link entities             │
   │ Target entity was deleted.         │
   │ [Refresh Page]                [✕]  │
   └────────────────────────────────────┘

   Actions:
   - Remove suggestion (no longer valid)
   - Update count badge
   - Refresh suggestions list
   ```

3. **Duplicate Link**
   ```
   Toast:
   ┌────────────────────────────────────┐
   │ ℹ️ Entities already linked          │
   │ This link already exists.          │
   │ [View Link]                   [✕]  │
   └────────────────────────────────────┘

   Actions:
   - Remove suggestion (redundant)
   - Navigate to existing link (if clicked)
   ```

---

### Flow 3: Merge Entities

**User Goal:** Permanently merge two entities into one

**Prerequisites:**
- User has admin permissions
- Both entities exist and are not already merged

**Flow Diagram:**

```
Start
  │
  ├─→ User clicks "Merge Duplicates"
  │     │
  │     ├─→ Open Merge Preview Modal
  │     │   ├─→ Fetch both entities' full data
  │     │   ├─→ Calculate merge preview
  │     │   └─→ Display side-by-side comparison
  │     │
  │     ├─→ User reviews data
  │     │   ├─→ Expand/collapse sections
  │     │   ├─→ Review all data items
  │     │   └─→ Read warnings
  │     │
  │     ├─→ User enters reason (required)
  │     │   ├─→ Validate: min 10 characters
  │     │   └─→ Enable "Merge" button
  │     │
  │     ├─→ User clicks "Merge Entities"
  │     │   ├─→ Show confirmation dialog
  │     │   └─→ "This action cannot be undone"
  │     │
  │     ├─→ User confirms
  │     │   ├─→ Send merge request
  │     │   ├─→ Show progress indicator
  │     │   └─→ Wait for response
  │     │
  │     └─→ Handle result
  │           │
  │           ├─→ SUCCESS
  │           │   ├─→ Close modal
  │           │   ├─→ Redirect to merged entity
  │           │   ├─→ Show success message
  │           │   └─→ Remove suggestion
  │           │
  │           └─→ ERROR
  │               ├─→ Show error in modal
  │               ├─→ Keep modal open
  │               └─→ Allow retry
  │
  └─→ End
```

**Detailed Steps:**

1. **Open Merge Modal**
   ```
   User Action: Click "Merge Duplicates" button

   System Response:
   - Dim background (overlay: rgba(0,0,0,0.5))
   - Animate modal in (slide up + fade)
   - Focus modal title
   - Load entity data:
     GET /api/entities/ent_abc123?include=all_data
     GET /api/entities/ent_def456?include=all_data
   ```

2. **Display Merge Preview**
   ```
   Modal Content:

   ┌─────────────────────────────────────────────────┐
   │ Merge Entities                        [Close ✕] │
   ├─────────────────────────────────────────────────┤
   │ ⚠️ Warning: This action cannot be undone        │
   │                                                 │
   │ Entity A (Discard)    Entity B (Keep)          │
   │ ┌─────────────────┐  ┌─────────────────┐      │
   │ │ John Doe        │  │ John Smith      │      │
   │ │ ent_abc123      │  │ ent_def456      │      │
   │ └─────────────────┘  └─────────────────┘      │
   │                                                 │
   │ Data to merge:                                  │
   │ ✓ 3 emails        ✓ 2 emails                   │
   │ ✓ 1 phone         ✓ 1 phone                    │
   │ ✓ 2 addresses     ✓ 1 address                  │
   │                                                 │
   │ Result: Entity B will have 5 emails,           │
   │         2 phones, 3 addresses                   │
   │                                                 │
   │ Reason (required):                              │
   │ [Text area]                                     │
   │ 0/500 characters                                │
   │                                                 │
   │                  [Cancel] [Merge Entities →]   │
   └─────────────────────────────────────────────────┘
   ```

3. **User Interaction**
   ```
   Expandable Sections:
   - Click section header to expand/collapse
   - View detailed data comparison
   - Smooth transition (300ms)

   Reason Input:
   - Type reason (min 10 chars)
   - Character counter updates live
   - Button enabled when valid

   Validation:
   - Reason length: 10-500 characters
   - No empty/whitespace-only input
   - Real-time validation feedback
   ```

4. **Merge Confirmation**
   ```
   User Action: Click "Merge Entities" button

   System Response:
   - Show inline confirmation:
     ┌───────────────────────────────────────────┐
     │ ⚠️ Are you sure?                          │
     │ This will permanently merge John Doe      │
     │ into John Smith. This cannot be undone.   │
     │                                           │
     │ [Cancel] [Yes, Merge Entities]            │
     └───────────────────────────────────────────┘
   ```

5. **Execute Merge**
   ```
   API Request:
   POST /api/entities/merge
   {
     "source_entity_id": "ent_abc123",
     "target_entity_id": "ent_def456",
     "reason": "Same person confirmed by email and phone",
     "user_id": "user_12345"
   }

   Progress Indicator:
   ┌─────────────────────────────────────┐
   │ ⏳ Merging entities...              │
   │ [████████████████░░░░] 80%         │
   │                                     │
   │ Transferring data...                │
   └─────────────────────────────────────┘

   Steps:
   1. Validate entities exist
   2. Transfer all data items
   3. Update references
   4. Mark source entity as deleted
   5. Create audit log entry
   6. Return result
   ```

6. **Success Response**
   ```
   Response:
   {
     "success": true,
     "merged_entity_id": "ent_def456",
     "deleted_entity_id": "ent_abc123",
     "data_transferred": {
       "emails": 3,
       "phones": 1,
       "addresses": 2
     },
     "timestamp": "2026-01-09T10:35:00Z"
   }

   System Actions:
   - Close modal (fade out)
   - Redirect: /entities/ent_def456
   - Show success banner:
     ┌───────────────────────────────────────────┐
     │ ✓ Successfully merged entities            │
     │ John Doe has been merged into John Smith  │
     │ [View Audit Log]                     [✕]  │
     └───────────────────────────────────────────┘

   - Remove suggestion from list
   - Update entity profile
   - Log to audit trail
   ```

**State Machine:**

```
IDLE → MODAL_OPENING → MODAL_OPEN
                          ↓
       REVIEW_DATA ← ─────┘
          ↓
       ENTERING_REASON
          ↓
       READY_TO_MERGE
          ↓
       CONFIRMING
          ↓
       MERGING
          ↓
       ├─→ SUCCESS → REDIRECTING
       └─→ ERROR → REVIEW_DATA
```

**Error Scenarios:**

1. **Entity Not Found**
   ```
   Error:
   ┌─────────────────────────────────────┐
   │ ✕ Merge Failed                      │
   │                                     │
   │ One of the entities no longer       │
   │ exists. It may have been deleted.   │
   │                                     │
   │ [Close] [Refresh Page]              │
   └─────────────────────────────────────┘
   ```

2. **Permission Denied**
   ```
   Error:
   ┌─────────────────────────────────────┐
   │ ✕ Permission Denied                 │
   │                                     │
   │ You don't have permission to merge  │
   │ entities. Contact your admin.       │
   │                                     │
   │ [Close]                             │
   └─────────────────────────────────────┘
   ```

3. **Network Error**
   ```
   Error:
   ┌─────────────────────────────────────┐
   │ ✕ Network Error                     │
   │                                     │
   │ Failed to merge entities.           │
   │ Check your connection and retry.    │
   │                                     │
   │ [Cancel] [Retry]                    │
   └─────────────────────────────────────┘
   ```

---

### Flow 4: Dismiss Suggestion

**User Goal:** Hide a suggestion without taking action

**Prerequisites:**
- Suggestion is visible
- User has permission to dismiss

**Flow Diagram:**

```
Start
  │
  ├─→ User clicks "Dismiss" button
  │     │
  │     ├─→ (Optional) Show reason picker
  │     │   ├─→ "Not a match"
  │     │   ├─→ "Already handled"
  │     │   ├─→ "Incorrect data"
  │     │   └─→ "Other..."
  │     │
  │     ├─→ Update UI immediately
  │     │   ├─→ Fade out card
  │     │   ├─→ Slide up remaining cards
  │     │   └─→ Update count badge
  │     │
  │     ├─→ Send dismiss request
  │     │   └─→ POST /api/suggestions/dismiss
  │     │
  │     └─→ Handle response
  │           │
  │           ├─→ SUCCESS
  │           │   ├─→ Move to "Dismissed" section
  │           │   ├─→ Show toast with undo
  │           │   └─→ Enable undo (10 seconds)
  │           │
  │           └─→ ERROR
  │               ├─→ Restore suggestion
  │               └─→ Show error message
  │
  └─→ End
```

**Detailed Steps:**

1. **User Dismisses Suggestion**
   ```
   User Action: Click "Dismiss" button

   System Response:
   - Animate card fade out (200ms)
   - Slide up remaining cards (300ms, staggered)
   - Update count badge: (5) → (4)
   - Update filter counts: HIGH (2) → HIGH (1)
   ```

2. **Optional: Reason Picker**
   ```
   Quick Action Menu:
   ┌─────────────────────────────────────┐
   │ Why dismiss this suggestion?        │
   │                                     │
   │ ⚪ Not a match                      │
   │ ⚪ Already handled elsewhere        │
   │ ⚪ Incorrect or outdated data       │
   │ ⚪ Low confidence, not useful       │
   │ ⚪ Other (provide feedback)         │
   │                                     │
   │ [Cancel] [Dismiss]                  │
   └─────────────────────────────────────┘

   - Click reason to select
   - "Other" opens text input
   - Optional feedback improves algorithm
   ```

3. **API Request**
   ```
   POST /api/suggestions/sug_abc123/dismiss
   {
     "reason": "not_a_match",
     "feedback": "Email domains are different",
     "user_id": "user_12345"
   }

   Response:
   {
     "success": true,
     "dismissed_at": "2026-01-09T10:40:00Z",
     "suggestion_id": "sug_abc123"
   }
   ```

4. **Success Response**
   ```
   Toast Notification:
   ┌─────────────────────────────────────┐
   │ ℹ️ Suggestion dismissed              │
   │ [Undo]                         [✕]  │
   └─────────────────────────────────────┘

   Auto-dismiss: 10 seconds

   Dismissed Section:
   - Move to collapsed "Dismissed" section
   - Show with reduced opacity
   - Allow permanent removal
   ```

5. **Undo Action**
   ```
   User Action: Click "Undo" within 10 seconds

   System Response:
   - POST /api/suggestions/sug_abc123/restore
   - Animate card back in (slide down + fade)
   - Update count badge: (4) → (5)
   - Show confirmation: "Suggestion restored"
   - Position at original location
   ```

**State Machine:**

```
VISIBLE → DISMISSING → DISMISSED → [UNDO] → VISIBLE
                          ↓
                    PERMANENTLY_DISMISSED
```

**Visual States:**

```
DISMISSING:
┌─────────────────────────────────────┐
│ 🟢 HIGH (0.95)          [⏳ ...]   │
│ (fading out, opacity: 0.3)          │
└─────────────────────────────────────┘

DISMISSED:
Moved to collapsed section:
┌─────────────────────────────────────┐
│ [▼ Show Dismissed (3)]              │
└─────────────────────────────────────┘

EXPANDED:
┌─────────────────────────────────────┐
│ [▲ Hide Dismissed (3)]              │
│                                     │
│ 🟢 Email match (dismissed 2m ago)  │
│    [Restore] [Delete Forever]       │
│                                     │
│ 🟡 Similar name (dismissed 5m ago) │
│    [Restore] [Delete Forever]       │
└─────────────────────────────────────┘
```

---

### Flow 5: Undo Action

**User Goal:** Reverse a recently completed action

**Supported Actions:**
- Link entities
- Dismiss suggestion
- (Future: Merge entities with admin override)

**Flow Diagram:**

```
Start
  │
  ├─→ User completes action
  │     │
  │     ├─→ Show success toast with "Undo"
  │     │   └─→ Start 5-second timer
  │     │
  │     ├─→ User clicks "Undo"
  │     │   ├─→ Cancel timer
  │     │   ├─→ Reverse action
  │     │   └─→ Update UI
  │     │
  │     └─→ Timer expires
  │           └─→ Action becomes permanent
  │
  └─→ End
```

**Detailed Steps:**

1. **Action Completed**
   ```
   Example: Link Entities

   Toast:
   ┌─────────────────────────────────────┐
   │ ✓ Successfully linked entities      │
   │ [Undo] ⏱️ 5s                   [✕]  │
   └─────────────────────────────────────┘

   Countdown:
   5s → 4s → 3s → 2s → 1s → Gone
   ```

2. **User Clicks Undo**
   ```
   User Action: Click "Undo" within 5 seconds

   System Response:
   - Cancel action timer
   - Update toast:
     ┌───────────────────────────────────┐
     │ ⏳ Undoing action...              │
     └───────────────────────────────────┘

   - Send API request:
     DELETE /api/entity-links/link_xyz789

   - Reverse UI changes:
     • Restore suggestion card
     • Update count badge
     • Re-enable all actions
   ```

3. **Undo Success**
   ```
   System Response:
   - Update toast:
     ┌───────────────────────────────────┐
     │ ✓ Action undone                   │
     └───────────────────────────────────┘

   - Animate suggestion back in
   - Restore to original position
   - Smooth transition (300ms)
   ```

4. **Undo Error**
   ```
   Error Scenarios:

   1. Network Error:
   ┌─────────────────────────────────────┐
   │ ✕ Failed to undo                    │
   │ Network error. [Retry]         [✕]  │
   └─────────────────────────────────────┘

   2. Action Already Permanent:
   ┌─────────────────────────────────────┐
   │ ⚠️ Cannot undo                       │
   │ Action is already permanent.   [✕]  │
   └─────────────────────────────────────┘

   3. State Changed:
   ┌─────────────────────────────────────┐
   │ ⚠️ Cannot undo                       │
   │ Entity has been modified.      [✕]  │
   └─────────────────────────────────────┘
   ```

**State Machine:**

```
ACTION_COMPLETED → UNDO_AVAILABLE (5s timer)
                       ↓
   ├─→ UNDOING → UNDONE
   └─→ TIMER_EXPIRED → PERMANENT
```

**Multiple Undo Queue:**

```
When multiple actions are performed:

Queue (newest first):
1. Link entities (John → Jane) - 3s remaining
2. Dismiss suggestion (Email match) - 7s remaining
3. Link entities (Doc → Project) - 10s remaining

Each action has independent timer.
User can undo any action in the queue.
```

---

## Edge Cases

### Edge Case 1: Concurrent Modifications

**Scenario:** Two users modify the same entity simultaneously

**Example:**
```
Time: 10:00:00
User A: Views suggestions for Entity X
User B: Views suggestions for Entity X

Time: 10:00:30
User A: Clicks "Link Entities" (suggestion 1)
User B: Clicks "Merge Duplicates" (suggestion 2)

Time: 10:00:31
Both requests arrive at server
```

**Resolution:**

1. **Optimistic Locking**
   ```
   Request includes version/timestamp:
   {
     "entity_id": "ent_abc123",
     "version": 42,
     "last_modified": "2026-01-09T10:00:00Z"
   }

   Server checks:
   - If version matches: Process request
   - If version mismatch: Return conflict error
   ```

2. **Conflict Response**
   ```
   HTTP 409 Conflict
   {
     "error": "entity_modified",
     "message": "Entity was modified by another user",
     "current_version": 43,
     "modified_by": "user_67890",
     "modified_at": "2026-01-09T10:00:30Z"
   }

   UI Response:
   ┌─────────────────────────────────────┐
   │ ⚠️ Entity Modified                   │
   │                                     │
   │ Another user modified this entity   │
   │ while you were working.             │
   │                                     │
   │ [Refresh & Retry] [Cancel]          │
   └─────────────────────────────────────┘
   ```

3. **User Options**
   ```
   Option 1: Refresh & Retry
   - Fetch latest entity data
   - Re-display suggestions
   - User can retry action

   Option 2: Cancel
   - Discard current action
   - Return to entity view
   ```

---

### Edge Case 2: Network Interruption

**Scenario:** Network connection lost during action

**Example:**
```
User clicks "Link Entities"
→ Request sent
→ Network drops
→ No response received
```

**Resolution:**

1. **Timeout Detection**
   ```
   Request timeout: 30 seconds

   After 30s without response:
   ┌─────────────────────────────────────┐
   │ ⚠️ Connection Timeout                │
   │                                     │
   │ Request is taking longer than       │
   │ expected. Check your connection.    │
   │                                     │
   │ [Keep Waiting] [Retry] [Cancel]     │
   └─────────────────────────────────────┘
   ```

2. **Retry Strategy**
   ```
   Exponential backoff:
   - Attempt 1: Immediate
   - Attempt 2: 1 second
   - Attempt 3: 2 seconds
   - Attempt 4: 4 seconds
   - Attempt 5: 8 seconds

   Max attempts: 5

   If all fail:
   ┌─────────────────────────────────────┐
   │ ✕ Connection Failed                 │
   │                                     │
   │ Unable to complete action.          │
   │ Please check your internet          │
   │ connection and try again.           │
   │                                     │
   │ [Retry] [Cancel]                    │
   └─────────────────────────────────────┘
   ```

3. **State Recovery**
   ```
   On reconnect:
   - Check if action was completed
   - GET /api/entity-links?entity_id=xxx&created_after=timestamp

   If completed:
   - Update UI to reflect success
   - Show toast: "Action completed successfully"

   If not completed:
   - Restore original state
   - Allow user to retry
   ```

---

### Edge Case 3: Stale Data

**Scenario:** Suggestion based on outdated data

**Example:**
```
1. System generates suggestion (Entity A → Entity B)
2. User navigates away
3. Entity B is deleted by another user
4. User returns and tries to link entities
5. Entity B no longer exists
```

**Resolution:**

1. **Pre-Action Validation**
   ```
   Before executing action:
   GET /api/entities/ent_def456/exists

   If not exists:
   ┌─────────────────────────────────────┐
   │ ⚠️ Entity No Longer Exists           │
   │                                     │
   │ The target entity was deleted.      │
   │ This suggestion is no longer valid. │
   │                                     │
   │ [Remove Suggestion] [Refresh List]  │
   └─────────────────────────────────────┘
   ```

2. **Automatic Cleanup**
   ```
   System actions:
   - Remove invalid suggestion from list
   - Update count badge
   - Log stale suggestion event
   - Improve suggestion freshness algorithm
   ```

3. **Prevention**
   ```
   WebSocket updates:
   - Subscribe to entity deletion events
   - Automatically remove suggestions when target is deleted
   - Show real-time notification:
     "1 suggestion removed (entity deleted)"
   ```

---

### Edge Case 4: Mass Actions

**Scenario:** User performs many actions quickly

**Example:**
```
User clicks:
1. Link entities (suggestion 1)
2. Dismiss (suggestion 2)
3. Link entities (suggestion 3)
4. Link entities (suggestion 4)
5. Dismiss (suggestion 5)

All within 2 seconds
```

**Resolution:**

1. **Request Queuing**
   ```
   Sequential processing:
   - Queue all requests
   - Process one at a time
   - Show combined progress:
     ┌───────────────────────────────────┐
     │ Processing 5 actions...           │
     │ [████████████░░░░] 3/5           │
     └───────────────────────────────────┘
   ```

2. **Batch API**
   ```
   POST /api/suggestions/batch
   {
     "actions": [
       { "type": "link", "suggestion_id": "sug_1" },
       { "type": "dismiss", "suggestion_id": "sug_2" },
       { "type": "link", "suggestion_id": "sug_3" }
     ]
   }

   Response:
   {
     "results": [
       { "suggestion_id": "sug_1", "status": "success" },
       { "suggestion_id": "sug_2", "status": "success" },
       { "suggestion_id": "sug_3", "status": "error", "message": "..." }
     ]
   }
   ```

3. **Summary Display**
   ```
   After all actions complete:
   ┌─────────────────────────────────────┐
   │ ✓ Actions Complete                  │
   │                                     │
   │ • 3 entities linked                 │
   │ • 2 suggestions dismissed           │
   │ • 0 errors                          │
   │                                     │
   │ [View Details] [✕]                  │
   └─────────────────────────────────────┘
   ```

---

## Error Handling

### Error Categories

1. **Client Errors (4xx)**
2. **Server Errors (5xx)**
3. **Network Errors**
4. **Validation Errors**

---

### 1. Client Errors (4xx)

#### 400 Bad Request

```
Cause: Invalid request data

Response:
{
  "error": "bad_request",
  "message": "Invalid entity ID format",
  "details": {
    "field": "entity_id",
    "value": "invalid_id",
    "expected": "ent_[a-z0-9]{6}"
  }
}

UI:
┌─────────────────────────────────────┐
│ ✕ Invalid Request                   │
│                                     │
│ The entity ID format is invalid.    │
│ Please refresh and try again.       │
│                                     │
│ [Refresh Page] [✕]                  │
└─────────────────────────────────────┘
```

#### 401 Unauthorized

```
Cause: User not authenticated

Response:
{
  "error": "unauthorized",
  "message": "Authentication required"
}

UI:
┌─────────────────────────────────────┐
│ 🔒 Authentication Required           │
│                                     │
│ Your session has expired.           │
│ Please log in again.                │
│                                     │
│ [Log In] [✕]                        │
└─────────────────────────────────────┘

Action: Redirect to login page
```

#### 403 Forbidden

```
Cause: User lacks permission

Response:
{
  "error": "forbidden",
  "message": "Insufficient permissions to merge entities",
  "required_permission": "entities:merge"
}

UI:
┌─────────────────────────────────────┐
│ 🚫 Permission Denied                │
│                                     │
│ You don't have permission to        │
│ merge entities. Contact your admin. │
│                                     │
│ [Contact Admin] [✕]                 │
└─────────────────────────────────────┘
```

#### 404 Not Found

```
Cause: Entity does not exist

Response:
{
  "error": "not_found",
  "message": "Entity not found",
  "entity_id": "ent_abc123"
}

UI:
┌─────────────────────────────────────┐
│ 🔍 Entity Not Found                 │
│                                     │
│ The entity you're looking for       │
│ doesn't exist or was deleted.       │
│                                     │
│ [Go Back] [Home]                    │
└─────────────────────────────────────┘
```

#### 409 Conflict

```
Cause: Concurrent modification

Response:
{
  "error": "conflict",
  "message": "Entity was modified by another user",
  "current_version": 43,
  "your_version": 42
}

UI:
┌─────────────────────────────────────┐
│ ⚠️ Conflict Detected                 │
│                                     │
│ Another user modified this entity.  │
│ Refresh to see the latest version.  │
│                                     │
│ [Refresh] [✕]                       │
└─────────────────────────────────────┘
```

#### 429 Too Many Requests

```
Cause: Rate limit exceeded

Response:
{
  "error": "rate_limit_exceeded",
  "message": "Too many requests",
  "retry_after": 60
}

UI:
┌─────────────────────────────────────┐
│ ⏱️ Rate Limit Exceeded              │
│                                     │
│ You've made too many requests.      │
│ Please wait 60 seconds and retry.   │
│                                     │
│ Retry available in: 00:60           │
│                                     │
│ [✕]                                 │
└─────────────────────────────────────┘

Auto-retry after countdown
```

---

### 2. Server Errors (5xx)

#### 500 Internal Server Error

```
Cause: Unexpected server error

Response:
{
  "error": "internal_server_error",
  "message": "An unexpected error occurred",
  "error_id": "err_xyz789"
}

UI:
┌─────────────────────────────────────┐
│ ✕ Server Error                      │
│                                     │
│ Something went wrong on our end.    │
│ Our team has been notified.         │
│                                     │
│ Error ID: err_xyz789                │
│                                     │
│ [Retry] [Contact Support]           │
└─────────────────────────────────────┘
```

#### 503 Service Unavailable

```
Cause: Service temporarily down

Response:
{
  "error": "service_unavailable",
  "message": "Service temporarily unavailable",
  "retry_after": 30
}

UI:
┌─────────────────────────────────────┐
│ 🔧 Service Unavailable              │
│                                     │
│ The service is temporarily          │
│ unavailable. We'll retry shortly.   │
│                                     │
│ Retrying in: 00:30                  │
│                                     │
│ [Cancel]                            │
└─────────────────────────────────────┘

Auto-retry with exponential backoff
```

---

### 3. Network Errors

```
Types:
- Connection timeout
- Network unreachable
- DNS resolution failed
- SSL/TLS error

UI (Generic):
┌─────────────────────────────────────┐
│ 📡 Connection Error                 │
│                                     │
│ Unable to connect to the server.    │
│ Check your internet connection.     │
│                                     │
│ [Retry] [Cancel]                    │
└─────────────────────────────────────┘

Detection:
- Monitor online/offline events
- Show banner when offline:
  ┌───────────────────────────────────┐
  │ ⚠️ You're offline. Changes won't   │
  │   be saved until reconnected. [✕]  │
  └───────────────────────────────────┘
```

---

### 4. Validation Errors

```
Client-side validation:

1. Empty Required Field:
┌─────────────────────────────────────┐
│ Reason *                            │
│ [                                 ] │
│ ⚠️ This field is required            │
└─────────────────────────────────────┘

2. Invalid Format:
┌─────────────────────────────────────┐
│ Email                               │
│ [invalid-email                    ] │
│ ⚠️ Please enter a valid email        │
└─────────────────────────────────────┘

3. Length Constraints:
┌─────────────────────────────────────┐
│ Reason (min 10 characters) *        │
│ [Short                            ] │
│ ⚠️ Must be at least 10 characters    │
└─────────────────────────────────────┘

Prevent submission until valid.
```

---

## State Management

### Global State

```javascript
// Redux/Zustand store structure

{
  suggestions: {
    items: [
      {
        id: 'sug_abc123',
        confidence: 0.95,
        level: 'high',
        matchType: 'email',
        sourceEntity: { ... },
        targetEntity: { ... },
        explanation: { ... },
        status: 'active' | 'dismissed' | 'linked' | 'merged'
      }
    ],
    filters: {
      high: true,
      medium: true,
      low: false
    },
    loading: false,
    error: null
  },

  ui: {
    expandedSuggestions: ['sug_abc123'],
    modalOpen: false,
    modalData: null,
    toasts: []
  },

  undo: {
    queue: [
      {
        id: 'undo_1',
        action: 'link_entities',
        data: { ... },
        expiresAt: 1704798300000,
        expired: false
      }
    ]
  }
}
```

### State Actions

```javascript
// Action creators

// Load suggestions
function loadSuggestions(entityId) {
  return async (dispatch) => {
    dispatch({ type: 'SUGGESTIONS_LOADING' });

    try {
      const response = await api.getSuggestions(entityId);
      dispatch({
        type: 'SUGGESTIONS_LOADED',
        payload: response.data
      });
    } catch (error) {
      dispatch({
        type: 'SUGGESTIONS_ERROR',
        payload: error.message
      });
    }
  };
}

// Link entities
function linkEntities(suggestionId) {
  return async (dispatch) => {
    // Optimistic update
    dispatch({
      type: 'SUGGESTION_STATUS_CHANGED',
      payload: { id: suggestionId, status: 'linking' }
    });

    try {
      const response = await api.linkEntities(suggestionId);

      dispatch({
        type: 'ENTITIES_LINKED',
        payload: { id: suggestionId, data: response.data }
      });

      // Add to undo queue
      dispatch({
        type: 'UNDO_ADDED',
        payload: {
          action: 'link_entities',
          data: response.data,
          expiresIn: 5000
        }
      });

      // Show toast
      dispatch({
        type: 'TOAST_SHOW',
        payload: {
          message: 'Successfully linked entities',
          type: 'success',
          action: 'undo'
        }
      });

    } catch (error) {
      // Rollback optimistic update
      dispatch({
        type: 'SUGGESTION_STATUS_CHANGED',
        payload: { id: suggestionId, status: 'active' }
      });

      dispatch({
        type: 'TOAST_SHOW',
        payload: {
          message: 'Failed to link entities',
          type: 'error'
        }
      });
    }
  };
}

// Undo action
function undoAction(undoId) {
  return async (dispatch, getState) => {
    const undoItem = getState().undo.queue.find(item => item.id === undoId);

    if (!undoItem || undoItem.expired) {
      dispatch({
        type: 'TOAST_SHOW',
        payload: {
          message: 'Cannot undo: action expired',
          type: 'error'
        }
      });
      return;
    }

    try {
      await api.undo(undoItem.action, undoItem.data);

      // Reverse the action
      switch (undoItem.action) {
        case 'link_entities':
          dispatch({
            type: 'ENTITIES_UNLINKED',
            payload: undoItem.data
          });
          break;
        // ... other actions
      }

      // Remove from undo queue
      dispatch({
        type: 'UNDO_REMOVED',
        payload: undoId
      });

      dispatch({
        type: 'TOAST_SHOW',
        payload: {
          message: 'Action undone',
          type: 'success'
        }
      });

    } catch (error) {
      dispatch({
        type: 'TOAST_SHOW',
        payload: {
          message: 'Failed to undo action',
          type: 'error'
        }
      });
    }
  };
}
```

### WebSocket Integration

```javascript
// Real-time updates via WebSocket

const ws = new WebSocket('ws://localhost:8000/suggestions/stream');

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);

  switch (message.type) {
    case 'new_suggestion':
      store.dispatch({
        type: 'SUGGESTION_ADDED',
        payload: message.data
      });

      store.dispatch({
        type: 'TOAST_SHOW',
        payload: {
          message: 'New suggestion available',
          type: 'info'
        }
      });
      break;

    case 'suggestion_updated':
      store.dispatch({
        type: 'SUGGESTION_UPDATED',
        payload: message.data
      });
      break;

    case 'entity_deleted':
      // Remove suggestions for deleted entity
      store.dispatch({
        type: 'SUGGESTIONS_REMOVED_BY_ENTITY',
        payload: message.entity_id
      });
      break;
  }
};

ws.onerror = (error) => {
  store.dispatch({
    type: 'WEBSOCKET_ERROR',
    payload: error
  });
};

ws.onclose = () => {
  // Attempt reconnect
  setTimeout(() => {
    connectWebSocket();
  }, 5000);
};
```

---

## Keyboard Shortcuts

### Global Shortcuts

```
Shortcut Key Actions:

G → S: Go to Suggestions page
?: Show keyboard shortcuts help
/: Focus search bar
ESC: Close modal/dismiss toast
```

### Suggestion-Specific Shortcuts

```
When focus is on a suggestion card:

Enter: Expand/collapse explanation
L: Link entities
D: Dismiss suggestion
M: Open merge modal
→: Next suggestion
←: Previous suggestion
```

### Modal Shortcuts

```
When merge modal is open:

Tab: Navigate fields
Shift+Tab: Navigate backwards
Enter: Submit (if valid)
ESC: Close modal
```

### Accessibility

```
Screen reader announcements:

- "Suggestion card, high confidence, 0.95"
- "Email match, john.doe@example.com found in John Smith"
- "Link entities button"
- "Dismiss button"
- "Explanation, collapsed, press Enter to expand"
```

---

## Analytics & Tracking

### Events to Track

```javascript
// Track user interactions

analytics.track('suggestion_viewed', {
  suggestion_id: 'sug_abc123',
  confidence_level: 'high',
  confidence_score: 0.95,
  match_type: 'email',
  user_id: 'user_12345'
});

analytics.track('suggestion_action', {
  suggestion_id: 'sug_abc123',
  action: 'link_entities',
  time_to_action: 12.5, // seconds
  user_id: 'user_12345'
});

analytics.track('suggestion_dismissed', {
  suggestion_id: 'sug_abc123',
  reason: 'not_a_match',
  feedback: 'Email domains are different',
  user_id: 'user_12345'
});

analytics.track('merge_completed', {
  source_entity: 'ent_abc123',
  target_entity: 'ent_def456',
  data_transferred: {
    emails: 3,
    phones: 1,
    addresses: 2
  },
  duration: 3.2, // seconds
  user_id: 'user_12345'
});

analytics.track('undo_action', {
  action_type: 'link_entities',
  undo_after: 3.8, // seconds
  user_id: 'user_12345'
});
```

### Performance Metrics

```javascript
// Track performance

performance.measure('suggestion_card_render');
performance.measure('modal_open_time');
performance.measure('api_response_time');

// Send to analytics
analytics.track('performance', {
  metric: 'suggestion_card_render',
  duration: 45, // ms
  timestamp: Date.now()
});
```

---

## Version History

| Version | Date       | Changes                     |
|---------|------------|-----------------------------|
| 1.0     | 2026-01-09 | Initial interaction flows   |

---

## Next Steps

1. **Implement Core Flows**
   - Build React/Vue components
   - Connect to API endpoints
   - Add state management

2. **Add Advanced Features**
   - Keyboard shortcuts
   - Batch operations
   - Real-time updates

3. **User Testing**
   - Conduct usability tests
   - Gather feedback
   - Iterate on flows

4. **Performance Optimization**
   - Implement virtual scrolling
   - Add code splitting
   - Optimize animations

5. **Accessibility Audit**
   - Screen reader testing
   - Keyboard navigation testing
   - Color contrast verification
