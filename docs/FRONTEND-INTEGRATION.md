# Basset Hound - Frontend Integration Guide

**Version**: 2.0.0  
**Last Updated**: 2026-05-19  
**Purpose**: Code examples and patterns for integrating with Basset Hound API from frontend

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Authentication & Requests](#authentication--requests)
3. [Entity Management](#entity-management)
4. [Search & Discovery](#search--discovery)
5. [Relationships](#relationships)
6. [Suggestions & ML Features](#suggestions--ml-features)
7. [Real-Time Updates (WebSocket)](#real-time-updates-websocket)
8. [Data Export](#data-export)
9. [Error Handling](#error-handling)
10. [Code Examples](#code-examples)

---

## Getting Started

### Base Configuration

**JavaScript/TypeScript**:
```javascript
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8080/api/v1';
const API_TIMEOUT = 30000; // 30 seconds

// Helper for API calls
async function apiCall(endpoint, options = {}) {
  const { method = 'GET', body = null, headers = {} } = options;
  
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...headers,
    },
    body: body ? JSON.stringify(body) : null,
    timeout: API_TIMEOUT,
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error?.message || 'API request failed');
  }

  return response.json();
}
```

**React Hook Example**:
```javascript
import { useCallback, useState, useEffect } from 'react';

export function useApi(url, options = {}) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetch = async () => {
      try {
        setLoading(true);
        const result = await apiCall(url, options);
        setData(result.data);
        setError(null);
      } catch (err) {
        setError(err.message);
        setData(null);
      } finally {
        setLoading(false);
      }
    };

    fetch();
  }, [url, options]);

  return { data, loading, error };
}
```

---

## Authentication & Requests

### Development Mode (No Auth)

Default mode - no authentication required:

```javascript
// Simple GET request
const projects = await apiCall('/projects');

// With query parameters
const filtered = await apiCall('/projects?limit=10&offset=0');
```

### Production Mode (JWT)

When authentication is enabled:

```javascript
// Get JWT token
async function login(username, password) {
  const response = await fetch(`${API_BASE_URL}/auth/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  
  const { access_token } = await response.json();
  localStorage.setItem('auth_token', access_token);
  return access_token;
}

// Include token in all requests
async function apiCall(endpoint, options = {}) {
  const token = localStorage.getItem('auth_token');
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  // ... rest of apiCall implementation
}
```

---

## Entity Management

### Create Entity

```javascript
async function createEntity(projectId, entityData) {
  const response = await apiCall(`/projects/${projectId}/entities`, {
    method: 'POST',
    body: {
      entity_type: 'PERSON', // PERSON, ORGANIZATION, PLATFORM, LOCATION, GROUP, GOVERNMENT, SOCK_PUPPET
      data: {
        name: entityData.name,
        description: entityData.description || '',
        email: entityData.email || null,
        phone: entityData.phone || null,
        // ... other fields based on entity_type
      },
      tags: entityData.tags || [],
      confidence: entityData.confidence || 'high',
    },
  });
  
  return response.data;
}

// Usage
const newEntity = await createEntity('proj_123', {
  name: 'John Doe',
  email: 'john@example.com',
  tags: ['suspect', 'investigate'],
});
```

### Get Entity Details

```javascript
async function getEntity(projectId, entityId) {
  const response = await apiCall(
    `/projects/${projectId}/entities/${entityId}`
  );
  
  return {
    entity: response.data.entity,
    relationships: response.data.relationships,
    orphanData: response.data.orphan_data,
    metadata: response.data.metadata,
  };
}

// Usage with React
function EntityProfile({ projectId, entityId }) {
  const { data, loading, error } = useApi(
    `/projects/${projectId}/entities/${entityId}`
  );

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div>
      <h1>{data?.entity.name}</h1>
      <p>{data?.entity.description}</p>
      <RelationshipsList relationships={data?.relationships} />
    </div>
  );
}
```

### Update Entity

```javascript
async function updateEntity(projectId, entityId, updates) {
  const response = await apiCall(
    `/projects/${projectId}/entities/${entityId}`,
    {
      method: 'PUT',
      body: {
        data: updates,
        tags: updates.tags || [],
      },
    }
  );
  
  return response.data;
}

// Usage
await updateEntity('proj_123', 'ent_abc', {
  name: 'John Doe (Updated)',
  email: 'newemail@example.com',
  tags: ['suspect', 'investigate', 'high-priority'],
});
```

### List Entities

```javascript
async function listEntities(projectId, options = {}) {
  const params = new URLSearchParams({
    limit: options.limit || 20,
    offset: options.offset || 0,
    entity_type: options.entityType || '',
    tag: options.tags?.join(',') || '',
    sort: options.sort || '-created_at', // Negative = descending
  });

  const response = await apiCall(
    `/projects/${projectId}/entities?${params}`
  );

  return {
    entities: response.data,
    pagination: response.meta.pagination,
    links: response.links, // HATEOAS links
  };
}

// React Pagination Component
function EntityList({ projectId }) {
  const [page, setPage] = useState(0);
  const { data, loading } = useApi(
    `/projects/${projectId}/entities?offset=${page * 20}&limit=20`
  );

  return (
    <div>
      {data?.map(entity => <EntityCard key={entity.id} entity={entity} />)}
      <button onClick={() => setPage(page + 1)}>Next</button>
    </div>
  );
}
```

---

## Search & Discovery

### Basic Search

```javascript
async function search(projectId, query) {
  const params = new URLSearchParams({
    q: query,
    limit: 20,
  });

  const response = await apiCall(
    `/projects/${projectId}/search/simple?${params}`
  );

  return response.data; // Array of matching entities
}

// Usage
const results = await search('proj_123', 'john@example.com');
```

### Advanced Search (Boolean)

```javascript
async function advancedSearch(projectId, query) {
  // Boolean operators: AND, OR, NOT
  // Field-specific: email:john@example.com
  // Phrase search: "exact phrase"
  // Wildcards: john* or john?
  
  const params = new URLSearchParams({
    query: query,
    limit: 50,
  });

  const response = await apiCall(
    `/projects/${projectId}/search/advanced?${params}`
  );

  return {
    results: response.data,
    totalCount: response.meta.total_count,
  };
}

// Examples
await advancedSearch('proj_123', 'email:*@gmail.com AND tag:suspect');
await advancedSearch('proj_123', '"John Doe" OR "john doe"');
await advancedSearch('proj_123', 'email:* AND NOT status:cleared');
```

### Faceted Search

```javascript
async function facetedSearch(projectId, criteria) {
  const response = await apiCall(
    `/projects/${projectId}/search/faceted`,
    {
      method: 'POST',
      body: {
        facets: {
          entity_type: criteria.entityTypes || [],
          tags: criteria.tags || [],
          confidence: criteria.confidence || [],
          created_date_range: criteria.dateRange || null,
        },
        limit: 50,
      },
    }
  );

  return {
    results: response.data.results,
    facets: response.data.facets, // Updated facet counts
  };
}

// React Component
function SearchFilters() {
  const [entityTypes, setEntityTypes] = useState([]);
  const [tags, setTags] = useState([]);

  const handleSearch = async () => {
    const results = await facetedSearch('proj_123', {
      entityTypes,
      tags,
    });
    // Use results...
  };

  return (
    <div>
      <FilterCheckbox
        label="Entity Type: Person"
        onChange={(checked) => 
          setEntityTypes(checked 
            ? [...entityTypes, 'PERSON'] 
            : entityTypes.filter(t => t !== 'PERSON')
          )
        }
      />
      {/* More filters */}
      <button onClick={handleSearch}>Search</button>
    </div>
  );
}
```

### Autocomplete

```javascript
async function getAutocomplete(projectId, prefix) {
  const params = new URLSearchParams({
    prefix: prefix,
    limit: 10,
  });

  const response = await apiCall(
    `/projects/${projectId}/search/autocomplete?${params}`
  );

  return response.data; // Array of suggestions
}

// React Autocomplete Component
function SearchInput() {
  const [input, setInput] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const [selectedSuggestion, setSelectedSuggestion] = useState(null);

  useEffect(() => {
    if (input.length < 2) {
      setSuggestions([]);
      return;
    }

    const timer = setTimeout(async () => {
      const results = await getAutocomplete('proj_123', input);
      setSuggestions(results);
    }, 300); // Debounce

    return () => clearTimeout(timer);
  }, [input]);

  return (
    <div className="autocomplete">
      <input
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder="Search entities..."
      />
      {suggestions.length > 0 && (
        <ul className="suggestions">
          {suggestions.map((suggestion) => (
            <li
              key={suggestion.id}
              onClick={() => {
                setSelectedSuggestion(suggestion);
                setInput('');
                setSuggestions([]);
              }}
            >
              {suggestion.name}
              <span className="type">{suggestion.entity_type}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

---

## Relationships

### Create Relationship

```javascript
async function createRelationship(projectId, relationship) {
  const response = await apiCall(
    `/projects/${projectId}/relationships`,
    {
      method: 'POST',
      body: {
        source_entity_id: relationship.sourceId,
        target_entity_id: relationship.targetId,
        relationship_type: relationship.type, // WORKS_WITH, KNOWS, FAMILY, OWNS, etc.
        properties: {
          started_date: relationship.startDate || null,
          ended_date: relationship.endDate || null,
          confidence: relationship.confidence || 'high',
          notes: relationship.notes || '',
        },
        bidirectional: relationship.bidirectional || false,
      },
    }
  );

  return response.data;
}

// Usage
await createRelationship('proj_123', {
  sourceId: 'ent_abc',
  targetId: 'ent_def',
  type: 'KNOWS',
  confidence: 'high',
  notes: 'Met at conference 2024',
});
```

### Get Relationships

```javascript
async function getRelationships(projectId, entityId) {
  const response = await apiCall(
    `/projects/${projectId}/entities/${entityId}/relationships`
  );

  return response.data; // Array of relationships
}

// React Component
function RelationshipsList({ projectId, entityId }) {
  const { data: relationships, loading } = useApi(
    `/projects/${projectId}/entities/${entityId}/relationships`
  );

  if (loading) return <div>Loading relationships...</div>;

  return (
    <div className="relationships">
      {relationships?.map((rel) => (
        <div key={rel.id} className="relationship-card">
          <div className="relationship-type">{rel.relationship_type}</div>
          <div className="target-entity">{rel.target_entity.name}</div>
          {rel.properties?.notes && <p>{rel.properties.notes}</p>}
        </div>
      ))}
    </div>
  );
}
```

### Delete Relationship

```javascript
async function deleteRelationship(projectId, relationshipId) {
  await apiCall(
    `/projects/${projectId}/relationships/${relationshipId}`,
    { method: 'DELETE' }
  );
}
```

---

## Suggestions & ML Features

### Get Suggestions for Entity

```javascript
async function getEntitySuggestions(projectId, entityId) {
  const response = await apiCall(
    `/projects/${projectId}/entities/${entityId}/suggestions`
  );

  return response.data; // Array of suggestions with confidence scores
}

// React Component showing ML suggestions
function SuggestionsPanel({ projectId, entityId }) {
  const { data: suggestions } = useApi(
    `/projects/${projectId}/entities/${entityId}/suggestions`
  );

  const handleAccept = async (suggestion) => {
    await apiCall(
      `/projects/${projectId}/suggestions/${suggestion.id}/accept`,
      { method: 'POST' }
    );
    // Refresh UI
  };

  const handleDismiss = async (suggestion) => {
    await apiCall(
      `/projects/${projectId}/suggestions/${suggestion.id}/dismiss`,
      { method: 'POST' }
    );
  };

  return (
    <div className="suggestions-panel">
      <h3>ML Suggestions</h3>
      {suggestions?.map((suggestion) => (
        <div key={suggestion.id} className="suggestion-card">
          <div className="confidence-score">
            {Math.round(suggestion.confidence * 100)}%
          </div>
          <div className="suggestion-text">{suggestion.description}</div>
          <button onClick={() => handleAccept(suggestion)}>Accept</button>
          <button onClick={() => handleDismiss(suggestion)}>Dismiss</button>
        </div>
      ))}
    </div>
  );
}
```

### Link Orphan Data

```javascript
async function linkOrphanData(projectId, orphanId, entityId) {
  const response = await apiCall(
    `/projects/${projectId}/orphan-data/${orphanId}/link/${entityId}`,
    { method: 'POST' }
  );

  return response.data;
}

// Usage
await linkOrphanData('proj_123', 'orphan_xyz', 'ent_abc');
```

---

## Real-Time Updates (WebSocket)

### Suggestions WebSocket

```javascript
class SuggestionsWebSocket {
  constructor(projectId, onMessage, onError) {
    this.projectId = projectId;
    this.onMessage = onMessage;
    this.onError = onError;
    this.ws = null;
  }

  connect() {
    const wsUrl = process.env.REACT_APP_WS_URL || 'ws://localhost:8080';
    this.ws = new WebSocket(`${wsUrl}/ws/suggestions/${this.projectId}`);

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.onMessage(data);
    };

    this.ws.onerror = (error) => {
      this.onError(error);
      // Attempt reconnect
      setTimeout(() => this.connect(), 5000);
    };
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

// React Hook for WebSocket
export function useSuggestionsWebSocket(projectId) {
  const [suggestions, setSuggestions] = useState([]);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const ws = new SuggestionsWebSocket(
      projectId,
      (data) => {
        switch (data.event_type) {
          case 'suggestion_generated':
            setSuggestions((prev) => [
              ...prev,
              ...data.suggestions,
            ]);
            setConnected(true);
            break;
          case 'entity_merged':
            // Refresh entity view
            break;
        }
      },
      (error) => {
        console.error('WebSocket error:', error);
        setConnected(false);
      }
    );

    ws.connect();
    return () => ws.disconnect();
  }, [projectId]);

  return { suggestions, connected };
}
```

### Activity Feed WebSocket

```javascript
function ActivityFeed({ projectId }) {
  const [activities, setActivities] = useState([]);

  useEffect(() => {
    const wsUrl = process.env.REACT_APP_WS_URL || 'ws://localhost:8080';
    const ws = new WebSocket(`${wsUrl}/ws/projects/${projectId}`);

    ws.onmessage = (event) => {
      const activity = JSON.parse(event.data);
      setActivities((prev) => [activity, ...prev.slice(0, 49)]);
    };

    return () => ws.close();
  }, [projectId]);

  return (
    <div className="activity-feed">
      {activities.map((activity, index) => (
        <div key={index} className="activity-item">
          <time>{new Date(activity.timestamp).toLocaleString()}</time>
          <span className="activity-type">{activity.activity_type}</span>
          <span className="activity-description">{activity.description}</span>
        </div>
      ))}
    </div>
  );
}
```

---

## Data Export

### Export Graph

```javascript
async function exportGraph(projectId, format = 'json') {
  // Formats: json, csv, graphml, geojson, pdf
  
  const response = await fetch(
    `${API_BASE_URL}/projects/${projectId}/export/graph?format=${format}`,
    {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
      },
    }
  );

  const blob = await response.blob();
  downloadFile(blob, `export.${getFileExtension(format)}`);
}

function downloadFile(blob, filename) {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
}

function getFileExtension(format) {
  const extensions = {
    json: 'json',
    csv: 'csv',
    graphml: 'graphml',
    geojson: 'geojson',
    pdf: 'pdf',
  };
  return extensions[format] || format;
}

// React Export Component
function ExportButton({ projectId }) {
  const [format, setFormat] = useState('json');
  const [exporting, setExporting] = useState(false);

  const handleExport = async () => {
    setExporting(true);
    try {
      await exportGraph(projectId, format);
    } catch (error) {
      console.error('Export failed:', error);
      alert('Export failed: ' + error.message);
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="export-section">
      <select value={format} onChange={(e) => setFormat(e.target.value)}>
        <option value="json">JSON</option>
        <option value="csv">CSV</option>
        <option value="graphml">GraphML</option>
        <option value="geojson">GeoJSON</option>
        <option value="pdf">PDF Report</option>
      </select>
      <button onClick={handleExport} disabled={exporting}>
        {exporting ? 'Exporting...' : 'Export'}
      </button>
    </div>
  );
}
```

---

## Error Handling

### API Error Handler

```javascript
class APIError extends Error {
  constructor(code, message, details = {}) {
    super(message);
    this.code = code;
    this.details = details;
  }
}

async function apiCall(endpoint, options = {}) {
  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      // ... request options
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new APIError(
        errorData.error?.code || 'UNKNOWN_ERROR',
        errorData.error?.message || response.statusText,
        errorData.error?.details
      );
    }

    return response.json();
  } catch (error) {
    if (error instanceof APIError) {
      throw error;
    }
    throw new APIError('NETWORK_ERROR', error.message);
  }
}

// Usage with error handling
async function loadEntity(projectId, entityId) {
  try {
    return await apiCall(`/projects/${projectId}/entities/${entityId}`);
  } catch (error) {
    if (error.code === 'ENTITY_NOT_FOUND') {
      console.error('Entity does not exist');
      return null;
    } else if (error.code === 'PERMISSION_DENIED') {
      console.error('Access denied to this entity');
      return null;
    } else if (error.code === 'NETWORK_ERROR') {
      console.error('Network error:', error.message);
      // Retry logic here
    }
    throw error;
  }
}

// React Error Boundary
class APIErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-container">
          <h2>Error Loading Data</h2>
          <p>{this.state.error.message}</p>
          <button onClick={() => window.location.reload()}>
            Retry
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
```

---

## Code Examples

### Complete Entity Management Component

```javascript
import React, { useState } from 'react';
import { useApi } from './hooks';

export function EntityManager({ projectId }) {
  const [selectedEntity, setSelectedEntity] = useState(null);
  const { data: entities } = useApi(`/projects/${projectId}/entities`);
  const { data: currentEntity } = useApi(
    selectedEntity 
      ? `/projects/${projectId}/entities/${selectedEntity.id}`
      : null
  );

  return (
    <div className="entity-manager">
      <div className="entities-list">
        <h2>Entities</h2>
        {entities?.map((entity) => (
          <div
            key={entity.id}
            className={`entity-card ${selectedEntity?.id === entity.id ? 'active' : ''}`}
            onClick={() => setSelectedEntity(entity)}
          >
            <h3>{entity.name}</h3>
            <span className="type">{entity.entity_type}</span>
          </div>
        ))}
      </div>

      {currentEntity && (
        <div className="entity-details">
          <h2>{currentEntity.entity.name}</h2>
          <p>{currentEntity.entity.description}</p>
          
          <h3>Relationships</h3>
          <RelationshipsList relationships={currentEntity.relationships} />
          
          <h3>ML Suggestions</h3>
          <SuggestionsPanel 
            projectId={projectId} 
            entityId={selectedEntity.id}
          />
        </div>
      )}
    </div>
  );
}
```

---

## Performance Tips

1. **Use pagination**: Always use limit/offset parameters
2. **Cache responses**: Store fetched data in state/Redux
3. **Debounce search**: Add 300ms delay to search input
4. **WebSocket batching**: Batch WebSocket messages
5. **Lazy load**: Load relationship details on demand
6. **Memoize components**: Use React.memo for list items

---

## Testing

```javascript
// Jest + React Testing Library example
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { EntityManager } from './EntityManager';

jest.mock('./hooks', () => ({
  useApi: jest.fn(),
}));

describe('EntityManager', () => {
  it('loads and displays entities', async () => {
    useApi.mockReturnValue({
      data: [{ id: 'ent_1', name: 'John Doe', entity_type: 'PERSON' }],
      loading: false,
    });

    render(<EntityManager projectId="proj_123" />);
    
    await waitFor(() => {
      expect(screen.getByText('John Doe')).toBeInTheDocument();
    });
  });
});
```

---

## API Response Structure

All API responses follow this format:

```javascript
{
  "status": "success",
  "data": { /* actual data */ },
  "meta": {
    "timestamp": "2026-05-19T12:00:00Z",
    "version": "2.0.0",
    "request_id": "req_abc123"
  },
  "links": {
    "self": "/api/v1/...",
    "next": "/api/v1/...?page=2",
    "prev": "/api/v1/...?page=1"
  }
}
```

For errors:

```javascript
{
  "status": "error",
  "error": {
    "code": "ENTITY_NOT_FOUND",
    "message": "Entity not found",
    "details": { /* error details */ }
  },
  "meta": { /* same as above */ }
}
```

---

## See Also

- [API_REFERENCE.md](./API_REFERENCE.md) - Complete endpoint documentation
- [ARCHITECTURE.md](./ARCHITECTURE.md) - System architecture overview
- [WebSocket Events](./API_REFERENCE.md#websocket-endpoints) - Real-time events

---

Created for Basset Hound Phase 8 | Last Updated: 2026-05-19
