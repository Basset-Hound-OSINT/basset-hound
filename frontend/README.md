# basset-hound Frontend

React components for the basset-hound Smart Suggestions System.

## Overview

This package provides production-ready React components for displaying and managing entity match suggestions. It integrates with the basset-hound REST API and WebSocket endpoints.

## Installation

```bash
cd frontend
npm install
```

## Development

```bash
# Start development server
npm run dev

# Run tests
npm run test

# Run tests with UI
npm run test:ui

# Build for production
npm run build

# Run Storybook
npm run storybook
```

## Components

### SuggestionBadge

Displays a confidence level badge with color coding and accessibility features.

```tsx
import { SuggestionBadge } from '@/components';

<SuggestionBadge
  level="high"
  score={0.95}
  variant="badge"  // 'badge' | 'pill' | 'compact'
  showScore={true}
  showIcon={true}
/>
```

### SuggestionCard

Displays a single suggestion with expandable details and action buttons.

```tsx
import { SuggestionCard } from '@/components';

<SuggestionCard
  suggestion={suggestion}
  onDismiss={(suggestion, reason) => handleDismiss(suggestion, reason)}
  onLink={(suggestion) => handleLink(suggestion)}
  onMerge={(suggestion) => handleMerge(suggestion)}
  onViewProfile={(suggestion) => handleViewProfile(suggestion)}
/>
```

### SuggestionPanel

Container component that displays all suggestions for an entity with real-time updates.

```tsx
import { SuggestionPanel } from '@/components';

<SuggestionPanel
  projectId="proj_123"
  entityId="ent_abc"
  onViewEntity={(entityId) => navigateTo(entityId)}
/>
```

## Hooks

### useWebSocket

Manages WebSocket connection for real-time suggestion updates.

```tsx
import { useWebSocket } from '@/hooks';

const { state, subscribeToEntity, unsubscribeFromEntity } = useWebSocket({
  projectId: 'proj_123',
  onEvent: (event) => console.log('Event:', event),
});
```

## State Management

Uses Zustand for lightweight state management.

```tsx
import { useSuggestionsStore } from '@/store';

const suggestions = useSuggestionsStore((s) => s.suggestions[entityId]);
const fetchSuggestions = useSuggestionsStore((s) => s.fetchSuggestions);

useEffect(() => {
  fetchSuggestions(projectId, entityId);
}, []);
```

## API Integration

The components integrate with these basset-hound endpoints:

- `GET /api/v1/projects/{project}/entities/{entity}/suggestions` - Fetch suggestions
- `POST /api/v1/projects/{project}/entities/{entity}/suggestions/compute` - Compute fresh suggestions
- `POST /api/v1/projects/{project}/linking/dismiss` - Dismiss a suggestion
- `POST /api/v1/projects/{project}/linking/relationship` - Create relationship
- `POST /api/v1/projects/{project}/linking/merge` - Merge entities
- `WS /api/v1/ws/suggestions/{project}` - Real-time updates

## Color System

Based on UI-COMPONENTS-SPECIFICATION.md:

| Level | Color | Badge |
|-------|-------|-------|
| High (0.9-1.0) | Green (#10B981) | 🟢 |
| Medium (0.7-0.89) | Amber (#F59E0B) | 🟡 |
| Low (0.5-0.69) | Red (#EF4444) | 🔴 |

## Accessibility

- Color-blind friendly patterns (icons in addition to colors)
- ARIA labels for screen readers
- Keyboard navigation support
- WCAG 2.1 AA compliant contrast ratios

## Building for Integration

To build components for embedding in existing pages:

```bash
npm run build
```

Output goes to `../static/js/components/` as:
- `basset-hound-ui.es.js` (ES module)
- `basset-hound-ui.umd.js` (UMD bundle)

## Usage in Existing Pages

```html
<!-- Load React (if not already loaded) -->
<script src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
<script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>

<!-- Load basset-hound UI -->
<script src="/static/js/components/basset-hound-ui.umd.js"></script>

<div id="suggestions-container"></div>

<script>
  const { SuggestionPanel } = BassetHoundUI;
  const root = ReactDOM.createRoot(document.getElementById('suggestions-container'));
  root.render(
    React.createElement(SuggestionPanel, {
      projectId: 'proj_123',
      entityId: 'ent_abc',
    })
  );
</script>
```

## Testing

```bash
# Run all tests
npm run test

# Run with coverage
npm run test:coverage

# Watch mode
npm run test -- --watch
```

## License

MIT - Part of the basset-hound project.
