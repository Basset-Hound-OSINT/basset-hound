# Graph Visualization API

This document describes the Graph Visualization API endpoints for the Basset Hound OSINT tool.

## Overview

The Graph Visualization API provides endpoints to retrieve graph data in formats suitable for popular frontend visualization libraries:
- **D3.js** - Force-directed graphs and custom visualizations
- **vis.js** - Interactive network graphs
- **Cytoscape.js** - Advanced graph analysis and visualization
- **Raw** - Custom format with full Neo4j properties

## Architecture

### Components

1. **GraphService** (`api/services/graph_service.py`)
   - Core service for graph data retrieval and transformation
   - Handles data fetching from Neo4j
   - Provides format conversion methods

2. **Graph Router** (`api/routers/graph.py`)
   - REST API endpoints
   - Request validation and error handling
   - Format selection via query parameters

3. **Tests** (`tests/test_graph_visualization.py`)
   - Comprehensive test coverage
   - Mock Neo4j handlers
   - Format validation tests

## API Endpoints

### 1. Get Full Project Graph

```
GET /api/v1/projects/{project_safe_name}/graph
```

Retrieves the complete graph for a project.

**Query Parameters:**
- `format` (optional): Output format - `d3`, `vis`, `cytoscape`, or `raw` (default: `raw`)
- `include_orphans` (optional): Include entities with no relationships (default: `true`)

**Response (Raw format):**
```json
{
  "nodes": [
    {
      "id": "entity-uuid",
      "label": "John Doe",
      "type": "Person",
      "properties": {
        "profile": {...},
        "created_at": "2024-01-01T00:00:00"
      }
    }
  ],
  "edges": [
    {
      "source": "entity-uuid-1",
      "target": "entity-uuid-2",
      "type": "WORKS_WITH",
      "properties": {
        "confidence": "high",
        "source": "LinkedIn"
      }
    }
  ]
}
```

**Examples:**
```bash
# Get raw format
curl http://localhost:8000/api/v1/projects/my_project/graph

# Get D3.js format
curl http://localhost:8000/api/v1/projects/my_project/graph?format=d3

# Get vis.js format without orphans
curl http://localhost:8000/api/v1/projects/my_project/graph?format=vis&include_orphans=false
```

### 2. Get Entity-Centered Subgraph

```
GET /api/v1/projects/{project_safe_name}/graph/entity/{entity_id}
```

Retrieves a subgraph centered around a specific entity with N-hop depth.

**Path Parameters:**
- `project_safe_name`: The project's safe name
- `entity_id`: The entity UUID to center the subgraph around

**Query Parameters:**
- `format` (optional): Output format - `d3`, `vis`, `cytoscape`, or `raw` (default: `raw`)
- `depth` (optional): Number of relationship hops to include, 1-10 (default: `2`)
- `include_orphans` (optional): Include entities with no relationships (default: `false`)

**Response:**
```json
{
  "nodes": [...],
  "edges": [...],
  "center_entity": "entity-uuid",
  "depth": 2
}
```

**Examples:**
```bash
# Get 2-hop subgraph around entity
curl http://localhost:8000/api/v1/projects/my_project/graph/entity/550e8400-e29b-41d4-a716-446655440000

# Get 1-hop subgraph in D3 format
curl http://localhost:8000/api/v1/projects/my_project/graph/entity/550e8400-e29b-41d4-a716-446655440000?depth=1&format=d3

# Get 3-hop subgraph in Cytoscape format
curl http://localhost:8000/api/v1/projects/my_project/graph/entity/550e8400-e29b-41d4-a716-446655440000?depth=3&format=cytoscape
```

### 3. Get Cluster Graph

```
GET /api/v1/projects/{project_safe_name}/graph/cluster/{cluster_id}
```

Retrieves the graph for a specific cluster detected by the cluster analysis.

**Path Parameters:**
- `project_safe_name`: The project's safe name
- `cluster_id`: The cluster root entity UUID

**Query Parameters:**
- `format` (optional): Output format - `d3`, `vis`, `cytoscape`, or `raw` (default: `raw`)

**Response:**
```json
{
  "nodes": [...],
  "edges": [...],
  "cluster_id": "entity-uuid",
  "cluster_size": 5,
  "is_isolated": false
}
```

**Examples:**
```bash
# Get cluster graph
curl http://localhost:8000/api/v1/projects/my_project/graph/cluster/550e8400-e29b-41d4-a716-446655440000

# Get cluster in vis.js format
curl http://localhost:8000/api/v1/projects/my_project/graph/cluster/550e8400-e29b-41d4-a716-446655440000?format=vis
```

## Data Formats

### Raw Format

The default format with complete Neo4j properties.

```json
{
  "nodes": [
    {
      "id": "string",
      "label": "string",
      "type": "string",
      "properties": {}
    }
  ],
  "edges": [
    {
      "source": "string",
      "target": "string",
      "type": "string",
      "properties": {}
    }
  ]
}
```

### D3.js Format

Optimized for D3.js force-directed graphs. Uses `links` instead of `edges`.

```json
{
  "nodes": [
    {
      "id": "string",
      "label": "string",
      "type": "string",
      "properties": {}
    }
  ],
  "links": [
    {
      "source": "string",
      "target": "string",
      "type": "string",
      "properties": {}
    }
  ]
}
```

**Usage in D3.js:**
```javascript
d3.json('/api/v1/projects/my_project/graph?format=d3')
  .then(data => {
    const simulation = d3.forceSimulation(data.nodes)
      .force("link", d3.forceLink(data.links).id(d => d.id))
      .force("charge", d3.forceManyBody())
      .force("center", d3.forceCenter(width / 2, height / 2));
  });
```

### vis.js Format

Optimized for vis.js network graphs. Uses `from`/`to` for edges and includes tooltips.

```json
{
  "nodes": [
    {
      "id": "string",
      "label": "string",
      "group": "string",
      "title": "string (HTML tooltip)",
      "value": 1
    }
  ],
  "edges": [
    {
      "id": 0,
      "from": "string",
      "to": "string",
      "label": "string",
      "arrows": "to",
      "title": "string"
    }
  ]
}
```

**Usage in vis.js:**
```javascript
fetch('/api/v1/projects/my_project/graph?format=vis')
  .then(response => response.json())
  .then(data => {
    const container = document.getElementById('network');
    const network = new vis.Network(container, data, options);
  });
```

### Cytoscape Format

Optimized for Cytoscape.js. Uses nested `elements` structure.

```json
{
  "elements": {
    "nodes": [
      {
        "data": {
          "id": "string",
          "label": "string",
          "type": "string",
          "properties": {}
        }
      }
    ],
    "edges": [
      {
        "data": {
          "id": "string",
          "source": "string",
          "target": "string",
          "label": "string",
          "type": "string",
          "properties": {}
        }
      }
    ]
  }
}
```

**Usage in Cytoscape.js:**
```javascript
fetch('/api/v1/projects/my_project/graph?format=cytoscape')
  .then(response => response.json())
  .then(data => {
    const cy = cytoscape({
      container: document.getElementById('cy'),
      elements: data.elements,
      style: [...]
    });
  });
```

## Display Name Extraction

The service automatically extracts display names from entity profiles using this priority:

1. `first_name` + `last_name` from profile section
2. `full_name` from profile section
3. `name` from profile section
4. `@username` from any section
5. Email username (before @) from any section
6. Fallback to shortened entity UUID

## Error Handling

### 404 Not Found
- Entity not found in project
- Cluster not found in project
- Project not found

```json
{
  "detail": "Entity entity-uuid not found in project my_project"
}
```

### 422 Validation Error
- Invalid format parameter
- Depth parameter out of range (must be 1-10)

```json
{
  "detail": [
    {
      "loc": ["query", "depth"],
      "msg": "ensure this value is less than or equal to 10",
      "type": "value_error.number.not_le"
    }
  ]
}
```

### 500 Internal Server Error
- Database connection issues
- Query execution errors

```json
{
  "detail": "Error retrieving project graph: Database connection failed"
}
```

## Performance Considerations

### Large Graphs

For projects with many entities (>1000), consider:
1. Use `include_orphans=false` to reduce node count
2. Use entity subgraphs instead of full project graph
3. Use cluster graphs to focus on specific communities

### Caching

The API does not currently implement caching. For production use, consider:
- HTTP caching headers
- Redis caching layer
- Client-side caching

### Query Optimization

The service uses optimized Neo4j queries:
- Single query for all entities
- In-memory relationship processing
- BFS for subgraph traversal

## Testing

Run the test suite:

```bash
# Run all graph visualization tests
pytest tests/test_graph_visualization.py -v

# Run specific test class
pytest tests/test_graph_visualization.py::TestProjectGraph -v

# Run with coverage
pytest tests/test_graph_visualization.py --cov=api.services.graph_service --cov=api.routers.graph
```

Manual testing script:

```bash
python test_graph_manual.py
```

## Integration Examples

### React with D3.js

```javascript
import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';

function GraphVisualization({ projectName }) {
  const svgRef = useRef();

  useEffect(() => {
    fetch(`/api/v1/projects/${projectName}/graph?format=d3`)
      .then(res => res.json())
      .then(data => {
        const svg = d3.select(svgRef.current);
        // Render graph...
      });
  }, [projectName]);

  return <svg ref={svgRef} width={800} height={600} />;
}
```

### Vue with vis.js

```javascript
<template>
  <div ref="network" style="width: 100%; height: 600px;"></div>
</template>

<script>
import { Network } from 'vis-network';

export default {
  props: ['projectName'],
  mounted() {
    fetch(`/api/v1/projects/${this.projectName}/graph?format=vis`)
      .then(res => res.json())
      .then(data => {
        new Network(this.$refs.network, data, {});
      });
  }
}
</script>
```

### Angular with Cytoscape

```typescript
import { Component, OnInit } from '@angular/core';
import cytoscape from 'cytoscape';

@Component({
  selector: 'app-graph',
  template: '<div id="cy" style="width: 100%; height: 600px;"></div>'
})
export class GraphComponent implements OnInit {
  ngOnInit() {
    fetch('/api/v1/projects/my_project/graph?format=cytoscape')
      .then(res => res.json())
      .then(data => {
        cytoscape({
          container: document.getElementById('cy'),
          elements: data.elements
        });
      });
  }
}
```

## Future Enhancements

Potential improvements:
- [ ] GraphQL support for flexible queries
- [ ] Streaming API for very large graphs
- [ ] WebSocket support for real-time updates
- [ ] Additional formats (Gephi, GraphML)
- [ ] Graph statistics in response
- [ ] Filtering by relationship type
- [ ] Time-based graph slicing
- [ ] Export to image formats (PNG, SVG)

## See Also

- [Graph Analysis API](api/routers/analysis.py) - Path finding, centrality, clustering
- [Neo4j Handler](neo4j_handler.py) - Database operations
- [Entity API](api/routers/entities.py) - Entity management
- [Relationship API](api/routers/relationships.py) - Relationship management
