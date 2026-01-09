# UI Components Specification
## Smart Suggestions System

**Version:** 1.0
**Date:** 2026-01-09
**Status:** Draft
**Based on:** 2026 UX Research and Best Practices

---

## Table of Contents

1. [Design Principles](#design-principles)
2. [Color System](#color-system)
3. [Component Library](#component-library)
4. [Accessibility](#accessibility)
5. [Responsive Design](#responsive-design)
6. [Performance Targets](#performance-targets)

---

## Design Principles

### Core Principles (2026 UX Standards)

1. **AI-Driven Personalization**
   - Context-aware suggestions based on user behavior
   - Adaptive UI that learns from user interactions
   - Progressive disclosure of complex information

2. **Explainable AI**
   - Clear reasoning for every suggestion
   - Transparent confidence scoring
   - User-friendly explanations of algorithm decisions

3. **Layered Communication**
   - Primary: Color-coded badges (visual)
   - Secondary: Confidence labels (textual)
   - Tertiary: Detailed tooltips (on-demand)

4. **Predictive & Responsive**
   - Instant fuzzy matching as user types
   - Real-time updates via WebSocket
   - Optimistic UI with rollback capability

5. **Visual Clarity**
   - High contrast for readability
   - Consistent spacing and alignment
   - Progressive enhancement for complexity

---

## Color System

### Confidence Level Colors

```
HIGH CONFIDENCE (0.9 - 1.0)
├─ Primary: #10B981 (Green-500)
├─ Hover: #059669 (Green-600)
├─ Background: #D1FAE5 (Green-100)
├─ Border: #6EE7B7 (Green-300)
└─ Badge: 🟢

MEDIUM CONFIDENCE (0.7 - 0.89)
├─ Primary: #F59E0B (Amber-500)
├─ Hover: #D97706 (Amber-600)
├─ Background: #FEF3C7 (Amber-100)
├─ Border: #FCD34D (Amber-300)
└─ Badge: 🟡

LOW CONFIDENCE (0.5 - 0.69)
├─ Primary: #EF4444 (Red-500)
├─ Hover: #DC2626 (Red-600)
├─ Background: #FEE2E2 (Red-100)
├─ Border: #FCA5A5 (Red-300)
└─ Badge: 🔴
```

### Accessibility Colors (Color Blind Friendly)

In addition to colors, we use patterns:

- **HIGH**: Solid fill + checkmark icon ✓
- **MEDIUM**: Diagonal stripes + warning icon ⚠
- **LOW**: Dotted pattern + info icon ℹ️

### Semantic Colors

```
Success: #10B981 (Green-500)
Warning: #F59E0B (Amber-500)
Error: #EF4444 (Red-500)
Info: #3B82F6 (Blue-500)
Neutral: #6B7280 (Gray-500)
```

---

## Component Library

### Component 1: Suggestion Card

#### Visual Design

```
┌─────────────────────────────────────────────────────────────────┐
│ 🟢 HIGH CONFIDENCE (0.95)                    [Dismiss ✕]       │
│────────────────────────────────────────────────────────────────│
│                                                                 │
│ Email Match: john.doe@example.com                              │
│ ↓                                                               │
│ Found in: John Smith (ent_def456)                              │
│                                                                 │
│ ───────────────────────────────────────────────────────────────│
│ ℹ️ Why this match? [Expand ▼]                                  │
│────────────────────────────────────────────────────────────────│
│                                                                 │
│ [View Profile] [Link Entities] [Merge Duplicates]              │
└─────────────────────────────────────────────────────────────────┘

EXPANDED STATE:
┌─────────────────────────────────────────────────────────────────┐
│ 🟢 HIGH CONFIDENCE (0.95)                    [Dismiss ✕]       │
│────────────────────────────────────────────────────────────────│
│                                                                 │
│ Email Match: john.doe@example.com                              │
│ ↓                                                               │
│ Found in: John Smith (ent_def456)                              │
│                                                                 │
│ ───────────────────────────────────────────────────────────────│
│ ℹ️ Why this match? [Collapse ▲]                                │
│                                                                 │
│ Match Factors:                                                  │
│ ✓ Exact email address match         (Weight: 0.4, Score: 1.0) │
│ ✓ Normalized format comparison       (Weight: 0.3, Score: 0.95)│
│ ✓ Domain verification                (Weight: 0.2, Score: 1.0) │
│ ✓ Historical context                 (Weight: 0.1, Score: 0.85)│
│                                                                 │
│ Total Score: 0.95 (weighted average)                           │
│                                                                 │
│ Last Updated: 2 minutes ago                                     │
│────────────────────────────────────────────────────────────────│
│                                                                 │
│ [View Profile] [Link Entities] [Merge Duplicates]              │
└─────────────────────────────────────────────────────────────────┘
```

#### HTML/CSS Structure

```html
<div class="suggestion-card" data-confidence="high" data-score="0.95">
  <!-- Header -->
  <div class="card-header">
    <div class="confidence-badge">
      <span class="badge-icon" aria-hidden="true">🟢</span>
      <span class="badge-label">HIGH CONFIDENCE</span>
      <span class="badge-score">(0.95)</span>
    </div>
    <button class="dismiss-btn" aria-label="Dismiss suggestion">
      Dismiss <span aria-hidden="true">✕</span>
    </button>
  </div>

  <!-- Content -->
  <div class="card-content">
    <div class="match-info">
      <p class="match-type">Email Match: <strong>john.doe@example.com</strong></p>
      <div class="match-arrow" aria-hidden="true">↓</div>
      <p class="match-target">
        Found in: <a href="/entities/ent_def456">John Smith</a>
        <span class="entity-id">(ent_def456)</span>
      </p>
    </div>

    <!-- Expandable Explanation -->
    <details class="explanation-section">
      <summary class="explanation-toggle">
        <span class="icon" aria-hidden="true">ℹ️</span>
        Why this match?
        <span class="expand-icon" aria-hidden="true">▼</span>
      </summary>
      <div class="explanation-content">
        <h4>Match Factors:</h4>
        <ul class="factor-list">
          <li class="factor-item">
            <span class="check-icon" aria-hidden="true">✓</span>
            <span class="factor-name">Exact email address match</span>
            <span class="factor-details">(Weight: 0.4, Score: 1.0)</span>
          </li>
          <!-- More factors... -->
        </ul>
        <p class="total-score">Total Score: 0.95 (weighted average)</p>
        <p class="last-updated">Last Updated: 2 minutes ago</p>
      </div>
    </details>
  </div>

  <!-- Actions -->
  <div class="card-actions">
    <button class="btn btn-secondary">View Profile</button>
    <button class="btn btn-primary">Link Entities</button>
    <button class="btn btn-warning">Merge Duplicates</button>
  </div>
</div>
```

#### CSS Specifications

```css
.suggestion-card {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  padding: 16px;
  margin-bottom: 16px;
  transition: box-shadow 0.2s ease;
}

.suggestion-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.suggestion-card[data-confidence="high"] {
  border-left: 4px solid #10B981;
}

.suggestion-card[data-confidence="medium"] {
  border-left: 4px solid #F59E0B;
}

.suggestion-card[data-confidence="low"] {
  border-left: 4px solid #EF4444;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid #E5E7EB;
}

.confidence-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: 14px;
}

.badge-icon {
  font-size: 16px;
}

.badge-score {
  color: #6B7280;
  font-weight: 400;
}

.dismiss-btn {
  background: transparent;
  border: 1px solid #D1D5DB;
  border-radius: 4px;
  padding: 4px 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.dismiss-btn:hover {
  background: #F3F4F6;
  border-color: #9CA3AF;
}

.dismiss-btn:focus {
  outline: 2px solid #3B82F6;
  outline-offset: 2px;
}

.match-info {
  margin: 16px 0;
  padding: 12px;
  background: #F9FAFB;
  border-radius: 6px;
}

.match-arrow {
  text-align: center;
  color: #6B7280;
  margin: 8px 0;
  font-size: 20px;
}

.explanation-section {
  margin: 16px 0;
  border-top: 1px solid #E5E7EB;
  padding-top: 12px;
}

.explanation-toggle {
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
  list-style: none;
}

.explanation-toggle::-webkit-details-marker {
  display: none;
}

.explanation-content {
  margin-top: 12px;
  padding-left: 28px;
}

.factor-list {
  list-style: none;
  padding: 0;
  margin: 8px 0;
}

.factor-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 8px 0;
  font-size: 14px;
}

.factor-details {
  color: #6B7280;
  font-size: 12px;
  margin-left: auto;
}

.card-actions {
  display: flex;
  gap: 8px;
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid #E5E7EB;
}

.btn {
  padding: 8px 16px;
  border-radius: 6px;
  border: 1px solid transparent;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.2s ease;
}

.btn-primary {
  background: #3B82F6;
  color: white;
}

.btn-primary:hover {
  background: #2563EB;
}

.btn-secondary {
  background: white;
  border-color: #D1D5DB;
  color: #374151;
}

.btn-secondary:hover {
  background: #F3F4F6;
}

.btn-warning {
  background: #FEF3C7;
  border-color: #FCD34D;
  color: #92400E;
}

.btn-warning:hover {
  background: #FDE68A;
}
```

#### Interaction States

1. **Default State**
   - Card visible with collapsed explanation
   - All actions enabled

2. **Hover State**
   - Elevated shadow
   - Dismiss button highlighted

3. **Expanded State**
   - Explanation section visible
   - Arrow icon rotated 180°

4. **Dismissed State**
   - Slide out animation (300ms)
   - Fade opacity to 0
   - Remove from DOM after animation

5. **Loading State**
   - Skeleton placeholder
   - Pulsing animation

---

### Component 2: Suggested Tags Section

#### Visual Design

```
┌─────────────────────────────────────────────────────────────────┐
│ Suggested Tags (5)                                   [Settings] │
│                                                                 │
│ Filter by confidence:                                           │
│ [🟢 HIGH (2)] [🟡 MEDIUM (2)] [🔴 LOW (1)]                     │
│                                                                 │
│─────────────────────────────────────────────────────────────────│
│ HIGH CONFIDENCE                                                 │
│─────────────────────────────────────────────────────────────────│
│                                                                 │
│ 🟢 Exact email match                                           │
│    john.doe@example.com → John Smith (ent_def456)              │
│    Score: 0.95 • 2 minutes ago                                 │
│    [Link] [Dismiss]                                            │
│                                                                 │
│ 🟢 Same document hash                                          │
│    report.pdf (SHA-256: 7f8a9b2c...) → Project Alpha           │
│    Score: 0.92 • 5 minutes ago                                 │
│    [Link] [Dismiss]                                            │
│                                                                 │
│─────────────────────────────────────────────────────────────────│
│ MEDIUM CONFIDENCE                                               │
│─────────────────────────────────────────────────────────────────│
│                                                                 │
│ 🟡 Similar name                                                │
│    "J. Doe" matches "John Doe" (fuzzy: 0.85)                   │
│    Score: 0.85 • 10 minutes ago                                │
│    [Link] [Dismiss]                                            │
│                                                                 │
│ 🟡 Phone number partial match                                  │
│    +1-555-0123 similar to +1-555-0100 (edit distance: 2)       │
│    Score: 0.78 • 15 minutes ago                                │
│    [Link] [Dismiss]                                            │
│                                                                 │
│─────────────────────────────────────────────────────────────────│
│ LOW CONFIDENCE                                                  │
│─────────────────────────────────────────────────────────────────│
│                                                                 │
│ 🔴 Possible duplicate                                          │
│    Similar creation time and location metadata                 │
│    Score: 0.62 • 20 minutes ago                                │
│    [Link] [Dismiss]                                            │
│                                                                 │
│─────────────────────────────────────────────────────────────────│
│                                                                 │
│ [▼ Show Dismissed (3)]                                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

COLLAPSED FILTER:
┌─────────────────────────────────────────────────────────────────┐
│ Suggested Tags (5)                                   [Settings] │
│                                                                 │
│ Filter by confidence:                                           │
│ [🟢 HIGH (2)] [🟡 MEDIUM (0)] [🔴 LOW (0)]                     │
│                                                                 │
│─────────────────────────────────────────────────────────────────│
│ HIGH CONFIDENCE                                                 │
│─────────────────────────────────────────────────────────────────│
│ (Only HIGH confidence suggestions shown)                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### HTML Structure

```html
<div class="suggestions-panel">
  <!-- Header -->
  <div class="panel-header">
    <h2 class="panel-title">
      Suggested Tags <span class="count-badge">(5)</span>
    </h2>
    <button class="settings-btn" aria-label="Suggestion settings">
      <span aria-hidden="true">⚙️</span> Settings
    </button>
  </div>

  <!-- Filters -->
  <div class="confidence-filters">
    <p class="filter-label">Filter by confidence:</p>
    <div class="filter-buttons" role="group" aria-label="Confidence level filters">
      <button
        class="filter-btn active"
        data-level="high"
        aria-pressed="true"
      >
        <span class="badge-icon" aria-hidden="true">🟢</span>
        HIGH <span class="filter-count">(2)</span>
      </button>
      <button
        class="filter-btn active"
        data-level="medium"
        aria-pressed="true"
      >
        <span class="badge-icon" aria-hidden="true">🟡</span>
        MEDIUM <span class="filter-count">(2)</span>
      </button>
      <button
        class="filter-btn active"
        data-level="low"
        aria-pressed="true"
      >
        <span class="badge-icon" aria-hidden="true">🔴</span>
        LOW <span class="filter-count">(1)</span>
      </button>
    </div>
  </div>

  <!-- Suggestions List -->
  <div class="suggestions-list">
    <!-- High Confidence Section -->
    <section class="confidence-section" data-level="high">
      <h3 class="section-header">HIGH CONFIDENCE</h3>

      <article class="suggestion-item">
        <div class="suggestion-header">
          <span class="badge-icon" aria-hidden="true">🟢</span>
          <h4 class="suggestion-title">Exact email match</h4>
        </div>
        <div class="suggestion-content">
          <p class="match-details">
            <span class="source">john.doe@example.com</span>
            <span class="arrow" aria-hidden="true">→</span>
            <span class="target">John Smith (ent_def456)</span>
          </p>
          <div class="suggestion-meta">
            <span class="score">Score: 0.95</span>
            <span class="separator">•</span>
            <time datetime="2026-01-09T10:30:00">2 minutes ago</time>
          </div>
        </div>
        <div class="suggestion-actions">
          <button class="btn btn-sm btn-primary">Link</button>
          <button class="btn btn-sm btn-ghost">Dismiss</button>
        </div>
      </article>

      <!-- More suggestions... -->
    </section>

    <!-- Medium Confidence Section -->
    <section class="confidence-section" data-level="medium">
      <!-- Similar structure... -->
    </section>

    <!-- Low Confidence Section -->
    <section class="confidence-section" data-level="low">
      <!-- Similar structure... -->
    </section>
  </div>

  <!-- Dismissed Items -->
  <details class="dismissed-section">
    <summary class="dismissed-toggle">
      <span class="expand-icon" aria-hidden="true">▼</span>
      Show Dismissed (3)
    </summary>
    <div class="dismissed-list">
      <!-- Dismissed suggestions... -->
    </div>
  </details>
</div>
```

#### CSS Specifications

```css
.suggestions-panel {
  background: white;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  padding: 20px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.panel-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
}

.count-badge {
  color: #6B7280;
  font-weight: 400;
  font-size: 16px;
}

.settings-btn {
  background: transparent;
  border: 1px solid #D1D5DB;
  border-radius: 4px;
  padding: 6px 12px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
}

.confidence-filters {
  margin-bottom: 20px;
}

.filter-label {
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 8px;
  color: #374151;
}

.filter-buttons {
  display: flex;
  gap: 8px;
}

.filter-btn {
  padding: 8px 16px;
  border: 2px solid #E5E7EB;
  border-radius: 6px;
  background: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 500;
  transition: all 0.2s ease;
}

.filter-btn:hover {
  background: #F9FAFB;
}

.filter-btn.active[data-level="high"] {
  border-color: #10B981;
  background: #D1FAE5;
  color: #065F46;
}

.filter-btn.active[data-level="medium"] {
  border-color: #F59E0B;
  background: #FEF3C7;
  color: #92400E;
}

.filter-btn.active[data-level="low"] {
  border-color: #EF4444;
  background: #FEE2E2;
  color: #991B1B;
}

.filter-btn[aria-pressed="false"] {
  opacity: 0.5;
}

.filter-count {
  font-size: 12px;
  opacity: 0.8;
}

.suggestions-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.confidence-section {
  border-top: 2px solid #E5E7EB;
  padding-top: 16px;
}

.section-header {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: #6B7280;
  margin: 0 0 12px 0;
}

.suggestion-item {
  border: 1px solid #E5E7EB;
  border-radius: 6px;
  padding: 12px;
  margin-bottom: 12px;
  transition: all 0.2s ease;
}

.suggestion-item:hover {
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
}

.suggestion-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.suggestion-title {
  font-size: 15px;
  font-weight: 600;
  margin: 0;
}

.match-details {
  font-size: 14px;
  margin: 8px 0;
  color: #374151;
}

.source {
  font-family: 'Monaco', 'Courier New', monospace;
  background: #F3F4F6;
  padding: 2px 6px;
  border-radius: 3px;
}

.arrow {
  margin: 0 8px;
  color: #9CA3AF;
}

.target {
  font-weight: 500;
}

.suggestion-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #6B7280;
  margin-top: 6px;
}

.score {
  font-weight: 500;
}

.separator {
  opacity: 0.5;
}

.suggestion-actions {
  display: flex;
  gap: 6px;
  margin-top: 10px;
}

.btn-sm {
  padding: 4px 12px;
  font-size: 13px;
}

.btn-ghost {
  background: transparent;
  border-color: #D1D5DB;
  color: #6B7280;
}

.btn-ghost:hover {
  background: #F3F4F6;
}

.dismissed-section {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px dashed #D1D5DB;
}

.dismissed-toggle {
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  color: #6B7280;
  font-weight: 500;
  list-style: none;
}

.dismissed-toggle::-webkit-details-marker {
  display: none;
}

.dismissed-list {
  margin-top: 12px;
  opacity: 0.7;
}
```

#### Real-time Updates

```javascript
// WebSocket connection for real-time updates
const ws = new WebSocket('ws://localhost:8000/suggestions/stream');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  switch (data.type) {
    case 'new_suggestion':
      addSuggestion(data.suggestion);
      showToast('New suggestion available', 'info');
      break;

    case 'suggestion_updated':
      updateSuggestion(data.suggestionId, data.updates);
      break;

    case 'suggestion_dismissed':
      removeSuggestion(data.suggestionId);
      break;
  }
};

function addSuggestion(suggestion) {
  // Animate in new suggestion
  const element = createSuggestionElement(suggestion);
  element.style.opacity = '0';
  element.style.transform = 'translateY(-10px)';

  container.prepend(element);

  // Trigger reflow
  element.offsetHeight;

  // Animate
  element.style.transition = 'all 0.3s ease';
  element.style.opacity = '1';
  element.style.transform = 'translateY(0)';
}
```

---

### Component 3: Merge Preview Modal

#### Visual Design

```
┌─────────────────────────────────────────────────────────────────┐
│ Merge Entities                                        [Close ✕] │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ ⚠️ Warning: This action cannot be undone                        │
│                                                                 │
│ ┌─────────────────────────┐  ┌─────────────────────────┐       │
│ │ Entity A (Discard)      │  │ Entity B (Keep)         │       │
│ │─────────────────────────│  │─────────────────────────│       │
│ │ John Doe                │  │ John Smith              │       │
│ │ ent_abc123              │  │ ent_def456              │       │
│ │                         │  │                         │       │
│ │ Created: 2025-12-01     │  │ Created: 2025-11-15     │       │
│ │ Updated: 2026-01-05     │  │ Updated: 2026-01-09     │       │
│ └─────────────────────────┘  └─────────────────────────┘       │
│                                                                 │
│ Data to merge:                                                  │
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ Emails                                                      ││
│ │ ✓ 3 from Entity A         ✓ 2 from Entity B               ││
│ │                                                             ││
│ │ Entity A:                 Entity B:                         ││
│ │ • john.doe@example.com    • john.smith@example.com         ││
│ │ • jdoe@work.com           • j.smith@work.com               ││
│ │ • john@personal.net                                         ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ Phone Numbers                                               ││
│ │ ✓ 1 from Entity A         ✓ 1 from Entity B               ││
│ │                                                             ││
│ │ Entity A:                 Entity B:                         ││
│ │ • +1-555-0123             • +1-555-0100                    ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ Addresses                                                   ││
│ │ ✓ 2 from Entity A         ✓ 1 from Entity B               ││
│ │                                                             ││
│ │ Entity A:                 Entity B:                         ││
│ │ • 123 Main St, NY         • 456 Oak Ave, CA                ││
│ │ • 789 Elm St, TX                                            ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ ───────────────────────────────────────────────────────────────│
│                                                                 │
│ Result Preview:                                                 │
│ Entity B will contain:                                          │
│ • 5 unique emails (1 duplicate removed)                        │
│ • 2 phone numbers                                              │
│ • 3 addresses                                                  │
│                                                                 │
│ Entity A will be marked as deleted and redirected to Entity B  │
│                                                                 │
│ ───────────────────────────────────────────────────────────────│
│                                                                 │
│ Reason (required):                                              │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ Same person confirmed by email and phone verification.      ││
│ │                                                              ││
│ │                                                              ││
│ └─────────────────────────────────────────────────────────────┘│
│ 0/500 characters                                                │
│                                                                 │
│                                                                 │
│                               [Cancel] [Merge Entities →]      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### HTML Structure

```html
<div class="modal-overlay" role="dialog" aria-modal="true" aria-labelledby="modal-title">
  <div class="modal-container">
    <!-- Header -->
    <div class="modal-header">
      <h2 id="modal-title" class="modal-title">Merge Entities</h2>
      <button class="close-btn" aria-label="Close modal">
        <span aria-hidden="true">✕</span>
      </button>
    </div>

    <!-- Content -->
    <div class="modal-content">
      <!-- Warning -->
      <div class="alert alert-warning" role="alert">
        <span class="alert-icon" aria-hidden="true">⚠️</span>
        <strong>Warning:</strong> This action cannot be undone
      </div>

      <!-- Entity Comparison -->
      <div class="entity-comparison">
        <div class="entity-card discard">
          <div class="entity-label">Entity A (Discard)</div>
          <h3 class="entity-name">John Doe</h3>
          <p class="entity-id">ent_abc123</p>
          <div class="entity-meta">
            <p>Created: <time datetime="2025-12-01">2025-12-01</time></p>
            <p>Updated: <time datetime="2026-01-05">2026-01-05</time></p>
          </div>
        </div>

        <div class="merge-arrow" aria-hidden="true">→</div>

        <div class="entity-card keep">
          <div class="entity-label">Entity B (Keep)</div>
          <h3 class="entity-name">John Smith</h3>
          <p class="entity-id">ent_def456</p>
          <div class="entity-meta">
            <p>Created: <time datetime="2025-11-15">2025-11-15</time></p>
            <p>Updated: <time datetime="2026-01-09">2026-01-09</time></p>
          </div>
        </div>
      </div>

      <!-- Data Preview -->
      <div class="data-preview">
        <h3 class="preview-title">Data to merge:</h3>

        <!-- Emails -->
        <details class="data-section" open>
          <summary class="data-section-header">
            <span class="section-icon" aria-hidden="true">📧</span>
            <span class="section-title">Emails</span>
            <span class="section-count">
              <span class="check-icon" aria-hidden="true">✓</span>
              3 from Entity A
              <span class="separator">•</span>
              2 from Entity B
            </span>
          </summary>
          <div class="data-section-content">
            <div class="data-columns">
              <div class="data-column">
                <h4>Entity A:</h4>
                <ul>
                  <li>john.doe@example.com</li>
                  <li>jdoe@work.com</li>
                  <li>john@personal.net</li>
                </ul>
              </div>
              <div class="data-column">
                <h4>Entity B:</h4>
                <ul>
                  <li>john.smith@example.com</li>
                  <li>j.smith@work.com</li>
                </ul>
              </div>
            </div>
          </div>
        </details>

        <!-- Phone Numbers -->
        <details class="data-section">
          <summary class="data-section-header">
            <span class="section-icon" aria-hidden="true">📱</span>
            <span class="section-title">Phone Numbers</span>
            <span class="section-count">
              <span class="check-icon" aria-hidden="true">✓</span>
              1 from Entity A
              <span class="separator">•</span>
              1 from Entity B
            </span>
          </summary>
          <div class="data-section-content">
            <div class="data-columns">
              <div class="data-column">
                <h4>Entity A:</h4>
                <ul>
                  <li>+1-555-0123</li>
                </ul>
              </div>
              <div class="data-column">
                <h4>Entity B:</h4>
                <ul>
                  <li>+1-555-0100</li>
                </ul>
              </div>
            </div>
          </div>
        </details>

        <!-- Addresses -->
        <details class="data-section">
          <summary class="data-section-header">
            <span class="section-icon" aria-hidden="true">📍</span>
            <span class="section-title">Addresses</span>
            <span class="section-count">
              <span class="check-icon" aria-hidden="true">✓</span>
              2 from Entity A
              <span class="separator">•</span>
              1 from Entity B
            </span>
          </summary>
          <div class="data-section-content">
            <div class="data-columns">
              <div class="data-column">
                <h4>Entity A:</h4>
                <ul>
                  <li>123 Main St, NY</li>
                  <li>789 Elm St, TX</li>
                </ul>
              </div>
              <div class="data-column">
                <h4>Entity B:</h4>
                <ul>
                  <li>456 Oak Ave, CA</li>
                </ul>
              </div>
            </div>
          </div>
        </details>
      </div>

      <!-- Result Preview -->
      <div class="result-preview">
        <h3 class="preview-title">Result Preview:</h3>
        <div class="result-summary">
          <p><strong>Entity B will contain:</strong></p>
          <ul>
            <li>5 unique emails <span class="note">(1 duplicate removed)</span></li>
            <li>2 phone numbers</li>
            <li>3 addresses</li>
          </ul>
          <p class="redirect-note">
            Entity A will be marked as deleted and redirected to Entity B
          </p>
        </div>
      </div>

      <!-- Reason Input -->
      <div class="reason-section">
        <label for="merge-reason" class="reason-label">
          Reason <span class="required-mark">*</span>
        </label>
        <textarea
          id="merge-reason"
          class="reason-input"
          rows="3"
          maxlength="500"
          required
          placeholder="Explain why these entities should be merged..."
        ></textarea>
        <p class="char-count" aria-live="polite">
          <span id="char-count">0</span>/500 characters
        </p>
      </div>
    </div>

    <!-- Footer -->
    <div class="modal-footer">
      <button class="btn btn-secondary" id="cancel-btn">Cancel</button>
      <button class="btn btn-danger" id="merge-btn" disabled>
        Merge Entities <span aria-hidden="true">→</span>
      </button>
    </div>
  </div>
</div>
```

#### CSS Specifications

```css
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.modal-container {
  background: white;
  border-radius: 12px;
  max-width: 800px;
  width: 90%;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1),
              0 10px 10px -5px rgba(0, 0, 0, 0.04);
  animation: slideUp 0.3s ease;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid #E5E7EB;
}

.modal-title {
  font-size: 20px;
  font-weight: 600;
  margin: 0;
}

.close-btn {
  background: transparent;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #6B7280;
  padding: 4px;
  line-height: 1;
}

.close-btn:hover {
  color: #374151;
}

.modal-content {
  padding: 24px;
  overflow-y: auto;
  flex: 1;
}

.alert {
  padding: 12px 16px;
  border-radius: 6px;
  margin-bottom: 20px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.alert-warning {
  background: #FEF3C7;
  border: 1px solid #FCD34D;
  color: #92400E;
}

.alert-icon {
  font-size: 20px;
}

.entity-comparison {
  display: flex;
  gap: 16px;
  align-items: center;
  margin-bottom: 24px;
}

.entity-card {
  flex: 1;
  padding: 16px;
  border: 2px solid #E5E7EB;
  border-radius: 8px;
  background: #F9FAFB;
}

.entity-card.discard {
  border-color: #FCA5A5;
  background: #FEE2E2;
}

.entity-card.keep {
  border-color: #6EE7B7;
  background: #D1FAE5;
}

.entity-label {
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #6B7280;
  margin-bottom: 8px;
}

.entity-name {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 4px 0;
}

.entity-id {
  font-family: 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  color: #6B7280;
  margin: 0 0 12px 0;
}

.entity-meta {
  font-size: 12px;
  color: #6B7280;
}

.entity-meta p {
  margin: 4px 0;
}

.merge-arrow {
  font-size: 32px;
  color: #9CA3AF;
  flex-shrink: 0;
}

.data-preview {
  margin-bottom: 24px;
}

.preview-title {
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 16px 0;
}

.data-section {
  border: 1px solid #E5E7EB;
  border-radius: 6px;
  margin-bottom: 12px;
}

.data-section-header {
  padding: 12px 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 12px;
  background: #F9FAFB;
  list-style: none;
  user-select: none;
}

.data-section-header::-webkit-details-marker {
  display: none;
}

.data-section-header:hover {
  background: #F3F4F6;
}

.section-icon {
  font-size: 20px;
}

.section-title {
  font-weight: 500;
  flex: 1;
}

.section-count {
  font-size: 13px;
  color: #6B7280;
}

.data-section-content {
  padding: 16px;
  border-top: 1px solid #E5E7EB;
}

.data-columns {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

.data-column h4 {
  font-size: 14px;
  font-weight: 600;
  margin: 0 0 8px 0;
  color: #374151;
}

.data-column ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.data-column li {
  font-size: 14px;
  padding: 4px 0;
  color: #6B7280;
}

.result-preview {
  background: #EFF6FF;
  border: 1px solid #BFDBFE;
  border-radius: 6px;
  padding: 16px;
  margin-bottom: 24px;
}

.result-summary {
  font-size: 14px;
}

.result-summary ul {
  margin: 8px 0;
  padding-left: 20px;
}

.result-summary li {
  margin: 4px 0;
}

.note {
  color: #6B7280;
  font-size: 13px;
}

.redirect-note {
  margin-top: 12px;
  font-style: italic;
  color: #6B7280;
}

.reason-section {
  margin-bottom: 0;
}

.reason-label {
  display: block;
  font-weight: 500;
  margin-bottom: 8px;
}

.required-mark {
  color: #EF4444;
}

.reason-input {
  width: 100%;
  padding: 12px;
  border: 1px solid #D1D5DB;
  border-radius: 6px;
  font-family: inherit;
  font-size: 14px;
  resize: vertical;
  transition: border-color 0.2s ease;
}

.reason-input:focus {
  outline: none;
  border-color: #3B82F6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.char-count {
  font-size: 12px;
  color: #6B7280;
  text-align: right;
  margin-top: 4px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 20px 24px;
  border-top: 1px solid #E5E7EB;
}

.btn-danger {
  background: #EF4444;
  color: white;
}

.btn-danger:hover:not(:disabled) {
  background: #DC2626;
}

.btn-danger:disabled {
  background: #FCA5A5;
  cursor: not-allowed;
  opacity: 0.5;
}
```

---

### Component 4: Confidence Visualization

#### Visual Design

```
Progress Bar:
┌──────────────────────────────────────────────┐
│ HIGH CONFIDENCE                              │
│ [████████████████████████░░░░░░] 0.95       │
└──────────────────────────────────────────────┘

┌──────────────────────────────────────────────┐
│ MEDIUM CONFIDENCE                            │
│ [███████████████░░░░░░░░░░░░░] 0.75         │
└──────────────────────────────────────────────┘

┌──────────────────────────────────────────────┐
│ LOW CONFIDENCE                               │
│ [████████░░░░░░░░░░░░░░░░░░░░] 0.55         │
└──────────────────────────────────────────────┘

Radial Gauge (Alternative):
     0.95
    ┌────┐
    │████│
    │████│ HIGH
    │████│
    └────┘

Tooltip on Hover:
┌────────────────────────────────────┐
│ Confidence Score: 0.95             │
│                                    │
│ Factors:                           │
│ • Email match: 1.0 (40%)           │
│ • Format: 0.95 (30%)               │
│ • Domain: 1.0 (20%)                │
│ • History: 0.85 (10%)              │
│                                    │
│ Weighted Average: 0.95             │
└────────────────────────────────────┘
```

#### HTML Structure

```html
<div class="confidence-widget">
  <div class="confidence-header">
    <span class="confidence-level">HIGH CONFIDENCE</span>
    <span class="confidence-score">0.95</span>
  </div>

  <div class="progress-bar" role="progressbar" aria-valuenow="95" aria-valuemin="0" aria-valuemax="100">
    <div class="progress-fill" style="width: 95%" data-level="high"></div>
  </div>

  <button class="info-trigger" aria-label="View confidence details">
    <span aria-hidden="true">ℹ️</span>
  </button>

  <!-- Tooltip (shown on hover/focus) -->
  <div class="confidence-tooltip" role="tooltip" hidden>
    <h4>Confidence Score: 0.95</h4>
    <ul class="factor-breakdown">
      <li>
        <span class="factor-name">Email match:</span>
        <span class="factor-score">1.0</span>
        <span class="factor-weight">(40%)</span>
      </li>
      <li>
        <span class="factor-name">Format:</span>
        <span class="factor-score">0.95</span>
        <span class="factor-weight">(30%)</span>
      </li>
      <li>
        <span class="factor-name">Domain:</span>
        <span class="factor-score">1.0</span>
        <span class="factor-weight">(20%)</span>
      </li>
      <li>
        <span class="factor-name">History:</span>
        <span class="factor-score">0.85</span>
        <span class="factor-weight">(10%)</span>
      </li>
    </ul>
    <p class="weighted-avg">Weighted Average: 0.95</p>
  </div>
</div>
```

#### CSS Specifications

```css
.confidence-widget {
  position: relative;
  display: inline-block;
}

.confidence-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.confidence-level {
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.confidence-score {
  font-size: 14px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.progress-bar {
  width: 200px;
  height: 8px;
  background: #E5E7EB;
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  transition: width 0.3s ease;
  border-radius: 4px;
}

.progress-fill[data-level="high"] {
  background: linear-gradient(90deg, #10B981 0%, #059669 100%);
}

.progress-fill[data-level="medium"] {
  background: linear-gradient(90deg, #F59E0B 0%, #D97706 100%);
}

.progress-fill[data-level="low"] {
  background: linear-gradient(90deg, #EF4444 0%, #DC2626 100%);
}

.info-trigger {
  position: absolute;
  top: 0;
  right: -24px;
  background: transparent;
  border: none;
  cursor: pointer;
  font-size: 16px;
  padding: 0;
}

.confidence-tooltip {
  position: absolute;
  top: 100%;
  left: 0;
  margin-top: 8px;
  background: #1F2937;
  color: white;
  padding: 12px;
  border-radius: 6px;
  width: 250px;
  font-size: 13px;
  z-index: 10;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.confidence-tooltip::before {
  content: '';
  position: absolute;
  top: -6px;
  left: 20px;
  width: 0;
  height: 0;
  border-left: 6px solid transparent;
  border-right: 6px solid transparent;
  border-bottom: 6px solid #1F2937;
}

.confidence-tooltip h4 {
  margin: 0 0 8px 0;
  font-size: 14px;
  font-weight: 600;
}

.factor-breakdown {
  list-style: none;
  padding: 0;
  margin: 8px 0;
}

.factor-breakdown li {
  display: flex;
  justify-content: space-between;
  margin: 4px 0;
}

.factor-name {
  flex: 1;
}

.factor-score {
  font-weight: 600;
  margin: 0 8px;
}

.factor-weight {
  color: #9CA3AF;
  font-size: 12px;
}

.weighted-avg {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid #374151;
  font-weight: 600;
  font-size: 14px;
}
```

---

### Component 5: Loading States

#### Visual Design

```
Initial Loading (Skeleton):
┌─────────────────────────────────────────────────────┐
│ ⏳ Finding matches...                               │
│                                                     │
│ [████████████████░░░░░░░░░░] 65%                   │
│                                                     │
│ Analyzing 127 entities, 834 data items...          │
│                                                     │
│ ┌─────────────────────────────────────────────────┐│
│ │ ░░░░░░░░░░░░░░░░░░░░░░░░░░░                     ││
│ │ ░░░░░░░░░░░░░░░░░░░░░░░░░░░                     ││
│ │ ░░░░░░░░░░░░░░░                                  ││
│ └─────────────────────────────────────────────────┘│
│                                                     │
│ ┌─────────────────────────────────────────────────┐│
│ │ ░░░░░░░░░░░░░░░░░░░░░░░░░░░                     ││
│ │ ░░░░░░░░░░░░░░░░░░░░░░░░░░░                     ││
│ │ ░░░░░░░░░░░░░░░                                  ││
│ └─────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────┘

Card Loading (Shimmer):
┌─────────────────────────────────────────────────────┐
│ ░░░░░░░░░░░░░░░░░░░░                   [░░░░░░░]   │
│────────────────────────────────────────────────────│
│                                                     │
│ ░░░░░░░░░: ░░░░░░░░░░░░░░░░░░░░░░░                 │
│ ↓                                                   │
│ ░░░░░░ ░░: ░░░░░░░░░░░░ (░░░░░░░░░░)               │
│                                                     │
└─────────────────────────────────────────────────────┘

Action Loading (Spinner):
┌─────────────────────────────────────────────────────┐
│ [⟳ Linking...] [Dismiss]                           │
└─────────────────────────────────────────────────────┘

Success State:
┌─────────────────────────────────────────────────────┐
│ ✓ Successfully linked entities                      │
│ [Undo]                                              │
└─────────────────────────────────────────────────────┘
```

#### HTML Structure

```html
<!-- Initial Loading -->
<div class="loading-container">
  <div class="loading-header">
    <span class="loading-icon" aria-hidden="true">⏳</span>
    <h3 class="loading-title">Finding matches...</h3>
  </div>

  <div class="progress-bar" role="progressbar" aria-valuenow="65" aria-valuemin="0" aria-valuemax="100">
    <div class="progress-fill" style="width: 65%"></div>
  </div>

  <p class="loading-status" aria-live="polite">
    Analyzing 127 entities, 834 data items...
  </p>

  <div class="skeleton-cards">
    <div class="skeleton-card">
      <div class="skeleton-line skeleton-header"></div>
      <div class="skeleton-line skeleton-content"></div>
      <div class="skeleton-line skeleton-short"></div>
    </div>
    <div class="skeleton-card">
      <div class="skeleton-line skeleton-header"></div>
      <div class="skeleton-line skeleton-content"></div>
      <div class="skeleton-line skeleton-short"></div>
    </div>
  </div>
</div>

<!-- Card Loading -->
<div class="suggestion-card loading">
  <div class="card-header">
    <div class="skeleton-line skeleton-badge"></div>
    <div class="skeleton-line skeleton-btn"></div>
  </div>
  <div class="card-content">
    <div class="skeleton-line skeleton-content"></div>
    <div class="skeleton-line skeleton-short"></div>
  </div>
</div>

<!-- Button Loading -->
<button class="btn btn-primary loading" disabled>
  <span class="spinner" aria-hidden="true"></span>
  <span class="btn-text">Linking...</span>
</button>

<!-- Success Toast -->
<div class="toast toast-success" role="status" aria-live="polite">
  <span class="toast-icon" aria-hidden="true">✓</span>
  <span class="toast-message">Successfully linked entities</span>
  <button class="toast-action">Undo</button>
  <button class="toast-close" aria-label="Close notification">✕</button>
</div>
```

#### CSS Specifications

```css
.loading-container {
  padding: 24px;
  text-align: center;
}

.loading-header {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-bottom: 16px;
}

.loading-icon {
  font-size: 24px;
  animation: spin 2s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.loading-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
}

.progress-bar {
  width: 100%;
  height: 8px;
  background: #E5E7EB;
  border-radius: 4px;
  overflow: hidden;
  margin: 16px 0;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #3B82F6 0%, #2563EB 100%);
  border-radius: 4px;
  transition: width 0.3s ease;
  animation: shimmer 1.5s infinite;
}

@keyframes shimmer {
  0% {
    background-position: -200px 0;
  }
  100% {
    background-position: 200px 0;
  }
}

.loading-status {
  color: #6B7280;
  font-size: 14px;
  margin: 8px 0 24px 0;
}

.skeleton-cards {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.skeleton-card {
  background: white;
  border-radius: 8px;
  padding: 16px;
  border: 1px solid #E5E7EB;
}

.skeleton-line {
  background: linear-gradient(
    90deg,
    #F3F4F6 25%,
    #E5E7EB 50%,
    #F3F4F6 75%
  );
  background-size: 200% 100%;
  animation: loading-shimmer 1.5s infinite;
  border-radius: 4px;
  margin: 8px 0;
}

@keyframes loading-shimmer {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}

.skeleton-header {
  height: 20px;
  width: 60%;
}

.skeleton-content {
  height: 16px;
  width: 100%;
}

.skeleton-short {
  height: 16px;
  width: 40%;
}

.skeleton-badge {
  height: 24px;
  width: 150px;
}

.skeleton-btn {
  height: 32px;
  width: 80px;
}

.btn.loading {
  position: relative;
  cursor: wait;
  opacity: 0.7;
}

.spinner {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid currentColor;
  border-right-color: transparent;
  border-radius: 50%;
  animation: spinner-rotate 0.6s linear infinite;
  margin-right: 8px;
}

@keyframes spinner-rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.toast {
  position: fixed;
  bottom: 24px;
  right: 24px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1),
              0 4px 6px -2px rgba(0, 0, 0, 0.05);
  padding: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 300px;
  animation: toast-slide-in 0.3s ease;
  z-index: 1000;
}

@keyframes toast-slide-in {
  from {
    transform: translateX(400px);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

.toast-success {
  border-left: 4px solid #10B981;
}

.toast-error {
  border-left: 4px solid #EF4444;
}

.toast-icon {
  font-size: 20px;
  flex-shrink: 0;
}

.toast-message {
  flex: 1;
  font-size: 14px;
  font-weight: 500;
}

.toast-action {
  background: transparent;
  border: 1px solid #D1D5DB;
  border-radius: 4px;
  padding: 4px 12px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  transition: all 0.2s ease;
}

.toast-action:hover {
  background: #F3F4F6;
}

.toast-close {
  background: transparent;
  border: none;
  cursor: pointer;
  color: #6B7280;
  font-size: 18px;
  padding: 0;
  line-height: 1;
}
```

---

## Accessibility

### WCAG 2.1 AA Compliance

#### 1. Color Contrast

All text must meet WCAG AA standards:
- Normal text: 4.5:1 contrast ratio
- Large text (18pt+): 3:1 contrast ratio
- UI components: 3:1 contrast ratio

**Tested Combinations:**
```
✓ Green-500 (#10B981) on White: 3.8:1 (Large text only)
✓ Green-600 (#059669) on White: 5.2:1 (Pass)
✓ Amber-500 (#F59E0B) on Black: 5.1:1 (Pass)
✓ Red-500 (#EF4444) on White: 3.9:1 (Large text only)
✓ Gray-700 (#374151) on White: 10.8:1 (Pass)
```

#### 2. Keyboard Navigation

All interactive elements must be keyboard accessible:

```
Tab Order:
1. Dismiss button
2. View Profile button
3. Link Entities button
4. Merge Duplicates button
5. Explanation toggle
6. Next suggestion card...

Shortcuts:
- Tab: Move to next element
- Shift+Tab: Move to previous element
- Enter/Space: Activate button or toggle
- Escape: Close modal or dismiss suggestion
- Arrow keys: Navigate within filter buttons
```

#### 3. Focus Indicators

```css
:focus {
  outline: 2px solid #3B82F6;
  outline-offset: 2px;
}

:focus:not(:focus-visible) {
  outline: none;
}

:focus-visible {
  outline: 2px solid #3B82F6;
  outline-offset: 2px;
}
```

#### 4. Screen Reader Support

**ARIA Labels:**
```html
<button aria-label="Dismiss suggestion">Dismiss</button>
<div role="progressbar" aria-valuenow="95" aria-valuemin="0" aria-valuemax="100"></div>
<div role="alert" aria-live="polite">Successfully linked entities</div>
<button aria-pressed="true">HIGH (2)</button>
```

**Semantic HTML:**
- Use `<button>` for actions
- Use `<a>` for navigation
- Use `<details>`/`<summary>` for expandable content
- Use `<time>` for timestamps
- Use proper heading hierarchy (`<h2>`, `<h3>`, etc.)

#### 5. Color Blind Friendly

In addition to colors, use multiple indicators:

**High Confidence:**
- Green color
- Solid badge icon (🟢)
- Checkmark icon (✓)
- "HIGH" text label

**Medium Confidence:**
- Yellow/amber color
- Warning badge (🟡)
- Warning icon (⚠)
- "MEDIUM" text label

**Low Confidence:**
- Red color
- Alert badge (🔴)
- Info icon (ℹ️)
- "LOW" text label

---

## Responsive Design

### Breakpoints

```css
/* Mobile First Approach */

/* Small devices (phones) */
@media (max-width: 640px) {
  /* Mobile styles */
}

/* Medium devices (tablets) */
@media (min-width: 641px) and (max-width: 1024px) {
  /* Tablet styles */
}

/* Large devices (desktops) */
@media (min-width: 1025px) {
  /* Desktop styles */
}
```

### Desktop Layout (1025px+)

```
┌────────────────────────────────────────────────────┐
│ Header                                             │
├────────┬───────────────────────────────────────────┤
│        │                                           │
│ Side   │  Main Content                            │
│ bar    │                                           │
│        │  Suggestions List                         │
│ Nav    │  ┌─────────────────────────────┐         │
│        │  │ Suggestion Card             │         │
│ Filters│  └─────────────────────────────┘         │
│        │  ┌─────────────────────────────┐         │
│        │  │ Suggestion Card             │         │
│        │  └─────────────────────────────┘         │
│        │                                           │
└────────┴───────────────────────────────────────────┘

Sidebar: 240px fixed
Main: flex-1 (remaining space)
```

### Tablet Layout (641px - 1024px)

```
┌────────────────────────────────────────────────────┐
│ Header                              [☰ Menu]       │
├────────────────────────────────────────────────────┤
│                                                    │
│  Main Content (Full Width)                        │
│                                                    │
│  Filters (Horizontal)                              │
│  [🟢 HIGH] [🟡 MEDIUM] [🔴 LOW]                   │
│                                                    │
│  Suggestions List                                  │
│  ┌──────────────────────────────────────────────┐ │
│  │ Suggestion Card (Compressed)                 │ │
│  └──────────────────────────────────────────────┘ │
│                                                    │
└────────────────────────────────────────────────────┘

Sidebar: Collapsible overlay
Filters: Horizontal scroll if needed
```

### Mobile Layout (<640px)

```
┌──────────────────────────┐
│ Header          [☰ Menu] │
├──────────────────────────┤
│                          │
│  Main Content            │
│                          │
│  [Filter: All ▾]         │
│                          │
│  Suggestions (Stacked)   │
│  ┌────────────────────┐  │
│  │ Compact Card       │  │
│  │ ✓ HIGH • 0.95      │  │
│  │ Email Match        │  │
│  │ [Link] [Dismiss]   │  │
│  └────────────────────┘  │
│                          │
│  ┌────────────────────┐  │
│  │ Compact Card       │  │
│  └────────────────────┘  │
│                          │
│ [+ Show More]            │
│                          │
└──────────────────────────┘

Bottom Sheet for Details:
┌──────────────────────────┐
│ ════ (drag handle)       │
│                          │
│ Suggestion Details       │
│ ...                      │
└──────────────────────────┘
```

### Responsive CSS

```css
/* Mobile Styles */
.suggestion-card {
  padding: 12px;
  margin-bottom: 12px;
}

.card-actions {
  flex-direction: column;
}

.btn {
  width: 100%;
}

/* Tablet Styles */
@media (min-width: 641px) {
  .suggestion-card {
    padding: 16px;
  }

  .card-actions {
    flex-direction: row;
  }

  .btn {
    width: auto;
  }

  .entity-comparison {
    flex-direction: column;
  }
}

/* Desktop Styles */
@media (min-width: 1025px) {
  .suggestions-panel {
    display: grid;
    grid-template-columns: 240px 1fr;
    gap: 24px;
  }

  .entity-comparison {
    flex-direction: row;
  }

  .modal-container {
    max-width: 800px;
  }
}
```

---

## Performance Targets

### Critical Metrics

1. **First Paint**
   - Target: <100ms
   - Strategy: Inline critical CSS, defer non-critical JS

2. **Suggestion Card Render**
   - Target: <50ms per card
   - Strategy: Virtual scrolling for >20 cards

3. **Animation Frame Rate**
   - Target: 60fps (16.67ms per frame)
   - Strategy: Use CSS transforms, avoid layout thrashing

4. **Optimistic UI Updates**
   - Target: <10ms for local state update
   - Strategy: Update UI immediately, sync with server in background

### Implementation Strategies

#### 1. Virtual Scrolling

```javascript
// Use virtual scrolling for large lists
import { VirtualScroller } from 'virtual-scroller';

const scroller = new VirtualScroller({
  container: '.suggestions-list',
  itemHeight: 120,
  bufferSize: 5,
  renderItem: (suggestion) => renderSuggestionCard(suggestion)
});
```

#### 2. Code Splitting

```javascript
// Lazy load modal components
const MergeModal = lazy(() => import('./components/MergeModal'));

// Load on demand
<Suspense fallback={<LoadingSpinner />}>
  {showModal && <MergeModal />}
</Suspense>
```

#### 3. Optimistic Updates

```javascript
async function linkEntities(suggestionId) {
  // 1. Update UI immediately
  updateSuggestionState(suggestionId, { status: 'linking' });

  try {
    // 2. Send request to server
    const result = await api.linkEntities(suggestionId);

    // 3. Update with server response
    updateSuggestionState(suggestionId, { status: 'linked', ...result });

    // 4. Show success toast
    showToast('Successfully linked entities', 'success');
  } catch (error) {
    // 5. Rollback on error
    updateSuggestionState(suggestionId, { status: 'error' });
    showToast('Failed to link entities', 'error');
  }
}
```

#### 4. Debouncing & Throttling

```javascript
// Debounce search input
const debouncedSearch = debounce((query) => {
  fetchSuggestions(query);
}, 300);

// Throttle scroll events
const throttledScroll = throttle(() => {
  updateVisibleCards();
}, 100);
```

#### 5. Web Workers

```javascript
// Offload heavy computations to Web Worker
const worker = new Worker('suggestion-matcher.worker.js');

worker.postMessage({ entities, dataItems });

worker.onmessage = (event) => {
  const matches = event.data;
  renderSuggestions(matches);
};
```

### Performance Budget

```
Initial Load:
- HTML: <10KB (gzipped)
- CSS: <50KB (gzipped)
- JS (critical): <100KB (gzipped)
- JS (total): <300KB (gzipped)

Runtime:
- Memory: <50MB for 1000 suggestions
- CPU: <5% idle, <30% active
- Network: WebSocket reconnect <1s
```

### Monitoring

```javascript
// Performance monitoring
const observer = new PerformanceObserver((list) => {
  for (const entry of list.getEntries()) {
    console.log(`${entry.name}: ${entry.duration}ms`);

    // Send to analytics
    analytics.track('performance', {
      metric: entry.name,
      duration: entry.duration,
      timestamp: Date.now()
    });
  }
});

observer.observe({ entryTypes: ['measure', 'navigation'] });

// Mark custom metrics
performance.mark('suggestions-start');
renderSuggestions();
performance.mark('suggestions-end');
performance.measure('suggestions-render', 'suggestions-start', 'suggestions-end');
```

---

## Implementation Checklist

### Phase 1: Core Components
- [ ] Implement Suggestion Card component
- [ ] Add confidence badge system
- [ ] Create expandable explanation section
- [ ] Add action buttons with loading states

### Phase 2: List & Filters
- [ ] Build Suggested Tags Section
- [ ] Implement confidence filters
- [ ] Add real-time WebSocket updates
- [ ] Create smooth animations

### Phase 3: Modals & Overlays
- [ ] Create Merge Preview Modal
- [ ] Implement entity comparison view
- [ ] Add data preview sections
- [ ] Build reason input with validation

### Phase 4: Visualizations
- [ ] Design confidence progress bars
- [ ] Add tooltip with factor breakdown
- [ ] Implement color gradients
- [ ] Create alternative visualizations

### Phase 5: Loading States
- [ ] Build skeleton loaders
- [ ] Add shimmer animations
- [ ] Create button spinners
- [ ] Implement toast notifications

### Phase 6: Accessibility
- [ ] Ensure WCAG 2.1 AA compliance
- [ ] Test keyboard navigation
- [ ] Add ARIA labels
- [ ] Verify screen reader support

### Phase 7: Responsive Design
- [ ] Implement mobile layout
- [ ] Create tablet layout
- [ ] Optimize desktop layout
- [ ] Test across devices

### Phase 8: Performance
- [ ] Add virtual scrolling
- [ ] Implement code splitting
- [ ] Optimize animations
- [ ] Monitor performance metrics

---

## Design Tokens

### Spacing Scale

```css
:root {
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --space-10: 40px;
  --space-12: 48px;
  --space-16: 64px;
}
```

### Typography Scale

```css
:root {
  --text-xs: 12px;
  --text-sm: 13px;
  --text-base: 14px;
  --text-lg: 16px;
  --text-xl: 18px;
  --text-2xl: 20px;
  --text-3xl: 24px;

  --font-normal: 400;
  --font-medium: 500;
  --font-semibold: 600;
  --font-bold: 700;

  --line-tight: 1.25;
  --line-normal: 1.5;
  --line-relaxed: 1.75;
}
```

### Shadow Scale

```css
:root {
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
  --shadow-md: 0 2px 8px rgba(0, 0, 0, 0.1);
  --shadow-lg: 0 4px 12px rgba(0, 0, 0, 0.15);
  --shadow-xl: 0 10px 25px rgba(0, 0, 0, 0.2);
}
```

### Border Radius

```css
:root {
  --radius-sm: 4px;
  --radius-md: 6px;
  --radius-lg: 8px;
  --radius-xl: 12px;
  --radius-full: 9999px;
}
```

### Transitions

```css
:root {
  --transition-fast: 0.15s ease;
  --transition-base: 0.2s ease;
  --transition-slow: 0.3s ease;
}
```

---

## Component Library Integration

These components are designed to integrate with popular frameworks:

- **React**: Use hooks for state management
- **Vue**: Use Composition API
- **Svelte**: Use reactive declarations
- **Vanilla JS**: Use Web Components

Example React component:

```jsx
import React, { useState, useEffect } from 'react';
import './SuggestionCard.css';

export function SuggestionCard({ suggestion, onLink, onDismiss }) {
  const [expanded, setExpanded] = useState(false);
  const [loading, setLoading] = useState(false);

  const confidenceLevel =
    suggestion.score >= 0.9 ? 'high' :
    suggestion.score >= 0.7 ? 'medium' : 'low';

  const handleLink = async () => {
    setLoading(true);
    try {
      await onLink(suggestion.id);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={`suggestion-card ${confidenceLevel}`}>
      {/* Component implementation */}
    </div>
  );
}
```

---

## Version History

| Version | Date       | Changes                          |
|---------|------------|----------------------------------|
| 1.0     | 2026-01-09 | Initial specification            |

---

## References

- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [Material Design 3](https://m3.material.io/)
- [Apple Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines/)
- [Web.dev Performance](https://web.dev/performance/)
- [Color Blind Accessibility](https://www.color-blindness.com/)
