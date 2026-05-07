# Basset Hound Plugin System

Directory structure for built-in and community plugins for Basset Hound.

## Built-in Plugins

### 1. Sankey Diagram (`sankey/`)

**ID**: `sankey-diagram`  
**Type**: Visualization  
**Version**: 1.0.0

Visualizes entity flow and relationships using Sankey diagrams. Perfect for understanding how entities are connected and how information flows through your network.

**Files**:
- `manifest.json` - Plugin metadata
- `plugin.js` - Implementation

**Usage**:
```javascript
const result = await pluginManager.executePlugin('sankey-diagram', {
    nodes: [...],
    edges: [...]
}, {
    width: 800,
    height: 600,
    colors: ['#FF6B6B', '#4ECDC4', '#45B7D1']
});
```

### 2. Timeline Visualization (`timeline/`)

**ID**: `timeline-visualization`  
**Type**: Visualization  
**Version**: 1.0.0

Displays entities and their relationships across time, helping you understand the sequence and timing of events in your investigation.

**Features**:
- Temporal event visualization
- Multiple event types (creation, update, relationship)
- Linear time scale with date labels
- Interactive event markers

**Usage**:
```javascript
const result = await pluginManager.executePlugin('timeline-visualization', {
    nodes: [...],  // Must include created_at, updated_at
    edges: [...]
});
```

### 3. Heat Map (`heatmap/`)

**ID**: `heatmap-visualization`  
**Type**: Visualization  
**Version**: 1.0.0

Visualizes entity activity and connection density using color-coded heat maps. Identify hotspots and high-activity areas in your investigation.

**Metrics**:
- Activity level (in_degree + out_degree + weight)
- Hotspot detection (top 20%)
- Viridis color scheme (purple to yellow)

**Usage**:
```javascript
const result = await pluginManager.executePlugin('heatmap-visualization', {
    nodes: [...],
    edges: [...]
}, {
    cellSize: 20,
    showValues: true
});
```

### 4. Network Statistics Dashboard (`network-stats/`)

**ID**: `network-statistics`  
**Type**: Analysis  
**Version**: 1.0.0

Comprehensive network metrics and graph-theoretic analysis including degree centrality, clustering, density, and component analysis.

**Metrics Computed**:
- Node/edge counts
- Network density
- Degree statistics (min, max, average)
- Clustering coefficient
- Connected components
- Entity type distribution
- Top connected nodes

**Usage**:
```javascript
const result = await pluginManager.executePlugin('network-statistics', {
    nodes: [...],
    edges: [...]
});
```

## Plugin Development

### Creating a Plugin

1. **Create plugin directory**:
```bash
mkdir -p static/plugins/my-plugin
```

2. **Create manifest.json**:
```json
{
  "id": "my-plugin",
  "name": "My Plugin",
  "description": "Description of what it does",
  "author": "Your Name",
  "version": "1.0.0",
  "type": "visualization",
  "entry_point": "plugin.js",
  "tags": ["tag1", "tag2"],
  "permissions": ["read:entities", "read:relationships", "read:graph"]
}
```

3. **Create plugin.js**:
```javascript
class MyPlugin extends PluginAPIBridge {
    async execute(graphData, options = {}) {
        try {
            const { nodes, edges } = graphData;
            
            // Your plugin logic here
            const result = this.analyze(nodes, edges);
            const html = this.render(result);
            
            return {
                status: 'success',
                data: {
                    html,
                    metrics: result.metrics
                }
            };
        } catch (error) {
            return {
                status: 'error',
                error: error.message
            };
        }
    }
    
    analyze(nodes, edges) {
        // Analysis logic
        return { /* results */ };
    }
    
    render(data) {
        // Generate HTML/SVG
        return '<svg>...</svg>';
    }
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = MyPlugin;
}
```

4. **Register plugin**:
```javascript
const manifest = require('./manifest.json');
const code = require('fs').readFileSync('./plugin.js', 'utf8');

await pluginManager.registerPlugin(manifest, code, 'your-user-id');
```

### Plugin API

Inside your plugin, you have access to these methods:

```javascript
// Data Access
async queryGraph(query, params)      // Neo4j query
async getEntities(filter)            // Get entities
async getRelationships(filter)       // Get relationships

// Caching
getCached(key)                       // Get cached value
setCached(key, value, ttl)          // Set cached value

// Events
emit(event, data)                    // Emit event
on(event, listener)                  // Listen to event

// Logging
log(level, message, data)            // Log message
```

### Plugin Permissions

Available permissions (declare in manifest):
- `read:entities` - Read entity data
- `read:relationships` - Read relationship data
- `read:graph` - Read full graph
- `read:analytics` - Read analytics data
- `write:entities` - Create/modify entities
- `write:relationships` - Create/modify relationships
- `execute:custom_query` - Execute custom Cypher queries

### Plugin Guidelines

1. **Input Data Format**:
```json
{
  "nodes": [
    {
      "id": "node-id",
      "name": "Node Name",
      "type": "Person",
      "created_at": "2026-05-07T00:00:00Z",
      "updated_at": "2026-05-07T00:00:00Z",
      "...": "other properties"
    }
  ],
  "edges": [
    {
      "id": "edge-id",
      "source": "node-id-1",
      "target": "node-id-2",
      "type": "knows",
      "weight": 1,
      "created_at": "2026-05-07T00:00:00Z"
    }
  ]
}
```

2. **Output Format**:
```json
{
  "status": "success",
  "data": {
    "html": "<svg>...</svg>",
    "metrics": { /* computed metrics */ }
  }
}
```

3. **Error Handling**:
```json
{
  "status": "error",
  "error": "Error message describing what went wrong"
}
```

### Best Practices

1. **Validate Input**:
```javascript
if (!nodes || !edges) {
    return {
        status: 'error',
        error: 'Missing required data: nodes and edges'
    };
}
```

2. **Handle Edge Cases**:
```javascript
const nodeCount = nodes.length || 0;
const edges = edges || [];
if (nodeCount === 0) {
    return {
        status: 'error',
        error: 'No entities to visualize'
    };
}
```

3. **Use Caching**:
```javascript
const cachedResult = this.getCached('analysis-key');
if (cachedResult) {
    return cachedResult;
}
const result = performExpensiveAnalysis();
this.setCached('analysis-key', result, 5 * 60 * 1000);
return result;
```

4. **Responsive Design**:
```javascript
// Support custom dimensions
const width = options.width || 800;
const height = options.height || 600;
const responsive = options.responsive !== false;
```

5. **Performance**:
- Handle large datasets (1000+ nodes/edges)
- Limit visualization to top N items
- Cache intermediate results
- Use efficient algorithms

### Testing Your Plugin

```javascript
const pluginManager = new PluginManager();
const result = await pluginManager.registerPlugin(manifest, code, 'test-user');
console.log('Plugin registered:', result.id);

const graphData = {
    nodes: [/* test data */],
    edges: [/* test data */]
};

const result = await pluginManager.executePlugin(result.id, graphData);
console.log('Execution result:', result);
```

## Publishing to Marketplace

1. **Register your plugin**:
```bash
curl -X POST /api/v1/plugins/register?user_id=your-user-id \
  -H "Content-Type: application/json" \
  -d '{
    "manifest": {...},
    "code": "..."
  }'
```

2. **Share with community**:
- Update plugin status to "published"
- Submit to marketplace
- Collect reviews and ratings

3. **Versioning**:
- Follow semantic versioning (x.y.z)
- Document changelog
- Plan for compatibility

## Plugin Examples

### Example 1: Simple Statistics Plugin

```javascript
class StatisticsPlugin extends PluginAPIBridge {
    async execute(graphData, options = {}) {
        const { nodes, edges } = graphData;
        
        const stats = {
            nodeCount: nodes.length,
            edgeCount: edges.length,
            density: edges.length / (nodes.length * (nodes.length - 1) / 2),
            avgDegree: (2 * edges.length) / nodes.length
        };
        
        const html = this.generateStatsCard(stats);
        
        return {
            status: 'success',
            data: {
                html,
                metrics: stats
            }
        };
    }
    
    generateStatsCard(stats) {
        return `
            <div style="padding: 20px; background: #f5f5f5;">
                <h3>Network Statistics</h3>
                <p>Nodes: ${stats.nodeCount}</p>
                <p>Edges: ${stats.edgeCount}</p>
                <p>Density: ${stats.density.toFixed(3)}</p>
                <p>Avg Degree: ${stats.avgDegree.toFixed(2)}</p>
            </div>
        `;
    }
}
```

### Example 2: Filtering Plugin

```javascript
class FilteredVisualizationPlugin extends PluginAPIBridge {
    async execute(graphData, options = {}) {
        const { nodes, edges } = graphData;
        const filterType = options.filterType;
        
        // Filter nodes by type
        const filteredNodes = nodes.filter(n => n.type === filterType);
        const filteredNodeIds = new Set(filteredNodes.map(n => n.id));
        
        // Filter edges
        const filteredEdges = edges.filter(e => 
            filteredNodeIds.has(e.source) && filteredNodeIds.has(e.target)
        );
        
        // Generate visualization
        const html = this.renderGraph(filteredNodes, filteredEdges);
        
        return {
            status: 'success',
            data: {
                html,
                nodeCount: filteredNodes.length,
                edgeCount: filteredEdges.length
            }
        };
    }
}
```

## Troubleshooting

### Plugin Not Loading
- Check manifest.json syntax
- Verify entry_point file exists
- Ensure plugin ID is unique

### Execution Timeout
- Optimize data processing
- Limit dataset size
- Use caching for repeated queries

### Sandbox Errors
- Ensure plugin uses proper API methods
- Don't try to access window or parent
- Use postMessage for communication

### Performance Issues
- Profile with browser DevTools
- Reduce DOM operations
- Cache computed results

## Support

For issues and feature requests:
- GitHub Issues: https://github.com/basset-hound/basset-hound/issues
- Documentation: https://basset-hound.dev/docs/plugins
- Community: https://basset-hound.dev/community

## License

Built-in plugins are MIT licensed. Community plugins follow their own licenses.
