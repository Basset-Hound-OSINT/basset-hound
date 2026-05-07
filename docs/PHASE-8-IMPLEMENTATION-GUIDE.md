# Phase 8 Implementation Guide
**Version**: 1.0.0  
**Date**: 2026-05-07  
**Status**: Production Ready

---

## Table of Contents

1. [Overview](#overview)
2. [Feature Flags](#feature-flags)
3. [Performance Tuning](#performance-tuning)
4. [ML Analytics Setup](#ml-analytics-setup)
5. [Real-Time Collaboration Setup](#real-time-collaboration-setup)
6. [Custom Plugins Development](#custom-plugins-development)
7. [Export Configuration](#export-configuration)
8. [Usage Examples](#usage-examples)
9. [Troubleshooting](#troubleshooting)

---

## Overview

Phase 8 introduces 8 major feature streams with **50+ new endpoints**. This guide provides:
- How to enable/disable features via flags
- Performance tuning recommendations
- Setup instructions for ML, real-time, and plugins
- Code examples for integration

---

## Feature Flags

### Environment Variables Configuration

Create `.env` or set environment variables:

```bash
# Performance Optimization (Streams 1-4)
CACHE_ENABLED=true                    # Enable Redis caching (default: true)
REDIS_URL=redis://localhost:6379/0    # Redis connection
CACHE_TTL_DEFAULT=300                 # Default TTL (seconds)
CACHE_TTL_QUERY=60                    # Query cache TTL
CACHE_HIT_RATE_TARGET=40              # Target hit rate (%)

# Search Optimization
SEARCH_FULL_TEXT_ENABLED=true         # Enable full-text search
SEARCH_FACETS_ENABLED=true            # Enable faceted search
SEARCH_AUTOCOMPLETE_ENABLED=true      # Enable autocomplete
AUTOCOMPLETE_MAX_RESULTS=20           # Max suggestions

# ML Analytics (Stream 5)
ENABLE_ML_ANALYTICS=true              # Enable/disable ML features
ML_MODEL_PATH=/opt/basset-hound/models/
ML_DUPLICATE_THRESHOLD=0.75           # Duplicate match threshold (0-1)
ML_LINK_PREDICTION_TOP_K=10           # Top K link predictions
ML_COMMUNITY_MIN_SIZE=3               # Min entities in community
ENABLE_ANOMALY_DETECTION=true         # Enable anomaly alerts

# Real-Time Collaboration (Stream 6)
ENABLE_COLLABORATION=true             # Enable real-time sync
WEBSOCKET_ENABLED=true                # Enable WebSocket
ACTIVITY_FEED_ENABLED=true            # Enable activity feed
PRESENCE_INDICATORS_ENABLED=true      # Show active users
MAX_CONCURRENT_CONNECTIONS=500        # Max WebSocket connections
ACTIVITY_ARCHIVE_MINUTES=5            # Archive old activity

# Plugins (Stream 7)
ENABLE_PLUGINS=true                   # Enable plugin system
PLUGIN_SANDBOX_ENABLED=true           # Isolate plugins via iframe
PLUGIN_MAX_SIZE_MB=5                  # Max plugin file size
BUILTIN_PLUGINS=sankey,timeline,heatmap,network-stats

# Export (Stream 8)
ENABLE_EXPORT=true                    # Enable data export
EXPORT_FORMATS=graphml,csv,json,geojson,pdf,database
EXPORT_MAX_SIZE_MB=100                # Max export file size
EXPORT_TIMEOUT_SECONDS=300            # Export job timeout
```

### Toggling Features

```python
# In application code
from config import settings

if settings.ENABLE_ML_ANALYTICS:
    # Use ML features
    from api.services.ml_analytics_service import MLAnalyticsService

if settings.ENABLE_COLLABORATION:
    # Use collaboration features
    from api.services.collaboration_service import CollaborationService

if settings.ENABLE_PLUGINS:
    # Enable plugin system
    from api.services.plugin_service import PluginService
```

### Per-Project Feature Control

```python
# Enable features for specific projects only
class ProjectConfig:
    id: str
    features: {
        "ml_analytics": True,
        "collaboration": True,
        "plugins": True,
        "exports": ["csv", "json", "pdf"]
    }

# Usage
if project.features.get("ml_analytics"):
    # Run ML analytics for this project
```

---

## Performance Tuning

### Query Optimization Tuning

```python
# neo4j_handler.py or neo4j_service.py
from api.services.neo4j_service import Neo4jService

# Configure batch sizes
NEO4J_BATCH_SIZE = 100  # Batch size for UNWIND operations
NEO4J_QUERY_TIMEOUT = 30000  # Query timeout (ms)

# Enable query profiling
NEO4J_ENABLE_PROFILING = True
NEO4J_SLOW_QUERY_THRESHOLD = 100  # Log queries >100ms
```

### Cache Tuning

```bash
# Redis memory optimization
redis-cli CONFIG SET maxmemory 256mb
redis-cli CONFIG SET maxmemory-policy allkeys-lru

# Clear cache if needed
curl -X POST http://localhost:8080/api/v1/cache/clear

# Monitor cache hit rate
curl http://localhost:8080/api/v1/cache/hit-rate
```

### Frontend Bundle Optimization

```bash
# Rebuild frontend with optimizations
cd frontend/
npm run build:prod  # Production build with code splitting
npm run analyze     # Analyze bundle size

# Check sizes
npm run webpack-bundle-analyzer

# Expected sizes after optimization:
# main.js:    ~150KB (was 300KB)
# vendor.js:  ~140KB (was 200KB)
# Total:      ~290KB (was 500KB)
```

### Database Indexing

```cypher
# Verify indexes are created
CALL db.indexes() YIELD name, properties, state
RETURN name, properties, state;

# Analyze index usage
CALL db.index.relationship.stats('HAS_RELATIONSHIP')
YIELD name, type, percentage
RETURN name, type, percentage;

# Force index rebuild if needed
DROP INDEX index_name;
CREATE INDEX index_name ON (...);
```

### Monitoring

```bash
# Check system metrics
curl http://localhost:8080/api/v1/metrics/performance

# Response includes:
{
  "cpu_usage": 25.5,
  "memory_usage_mb": 450,
  "open_connections": 45,
  "requests_per_second": 150,
  "avg_response_time_ms": 45,
  "cache_hit_rate": 0.62
}
```

---

## ML Analytics Setup

### Enabling ML Analytics

```bash
# 1. Set environment variable
export ENABLE_ML_ANALYTICS=true
export ML_MODEL_PATH=/opt/basset-hound/models/

# 2. Download/train models
python scripts/setup_ml_models.py

# 3. Verify installation
curl http://localhost:8080/api/v1/ml/models/status
```

### Using Duplicate Detection

```python
# Find duplicates for an entity
import requests

response = requests.get(
    'http://localhost:8080/api/v1/ml/duplicates',
    params={
        'entity_id': 'ent_123',
        'confidence_threshold': 0.75,
        'limit': 10
    }
)

# Response
{
  "entity_id": "ent_123",
  "duplicates": [
    {
      "id": "ent_456",
      "name": "John Smith",
      "similarity": 0.92,
      "reason": "Same email domain and name similarity"
    },
    {
      "id": "ent_789",
      "name": "Jon Smith",
      "similarity": 0.87,
      "reason": "Similar name pattern"
    }
  ]
}

# Merge duplicates
merge_response = requests.post(
    'http://localhost:8080/api/v1/ml/duplicates/merge',
    json={
        'source_id': 'ent_456',
        'target_id': 'ent_123',
        'strategy': 'keep_both'  # or 'merge_fields'
    }
)
```

### Using Link Prediction

```python
# Predict likely relationships
response = requests.get(
    'http://localhost:8080/api/v1/ml/link-prediction',
    params={
        'entity_id': 'ent_123',
        'relationship_type': 'KNOWS',  # Optional filter
        'top_k': 10
    }
)

# Response
{
  "entity_id": "ent_123",
  "predictions": [
    {
      "target_id": "ent_456",
      "target_name": "Jane Doe",
      "confidence": 0.85,
      "reason": "Shared 3 mutual contacts",
      "common_neighbors": ["ent_111", "ent_222", "ent_333"]
    },
    {
      "target_id": "ent_789",
      "target_name": "Bob Johnson",
      "confidence": 0.72,
      "reason": "Similar company associations"
    }
  ]
}

# Accept prediction
accept_response = requests.post(
    'http://localhost:8080/api/v1/ml/link-prediction/accept',
    json={
        'source_id': 'ent_123',
        'target_id': 'ent_456',
        'relationship_type': 'KNOWS',
        'confidence': 0.85
    }
)
```

### Using Community Detection

```python
# Detect communities/clusters
response = requests.get(
    'http://localhost:8080/api/v1/ml/communities',
    params={
        'project_id': 'proj_123',
        'algorithm': 'louvain',  # louvain or connected_components
        'min_size': 3
    }
)

# Response
{
  "communities": [
    {
      "id": "community_1",
      "name": "High-Value Network",
      "size": 45,
      "modularity": 0.68,
      "entities": ["ent_123", "ent_456", ...],
      "description": "Tightly connected group with 156 internal edges"
    },
    {
      "id": "community_2",
      "name": "Secondary Network",
      "size": 23,
      "modularity": 0.62,
      "entities": ["ent_789", ...],
      "description": "Separate cluster with 52 internal edges"
    }
  ],
  "statistics": {
    "total_communities": 5,
    "avg_community_size": 18,
    "modularity_score": 0.65
  }
}
```

### Detecting Anomalies

```python
# Detect anomalous entities
response = requests.get(
    'http://localhost:8080/api/v1/ml/anomalies',
    params={
        'project_id': 'proj_123',
        'anomaly_threshold': 0.7,
        'anomaly_types': ['rapid_updates', 'sparse_data', 'unusual_pattern']
    }
)

# Response
{
  "anomalies": [
    {
      "entity_id": "ent_123",
      "anomaly_type": "rapid_updates",
      "anomaly_score": 0.92,
      "description": "Entity updated 50 times in 1 hour",
      "severity": "high",
      "recommendation": "Review recent changes"
    },
    {
      "entity_id": "ent_456",
      "anomaly_type": "sparse_data",
      "anomaly_score": 0.65,
      "description": "Only 2 fields populated out of 15",
      "severity": "medium",
      "recommendation": "Complete entity profile"
    }
  ]
}
```

---

## Real-Time Collaboration Setup

### Enabling WebSocket Connection

```javascript
// In frontend JavaScript
const collaborationManager = new CollaborationManager({
    project_id: 'proj_123',
    ws_url: 'ws://localhost:8080/ws/sync',
    auto_reconnect: true,
    reconnect_attempts: 5,
    reconnect_interval: 3000
});

// Connect to project
collaborationManager.connect();

// Listen to changes
collaborationManager.on('entity_updated', (event) => {
    console.log('Entity updated:', event.entity_id, event.changes);
    // Refresh UI
});

collaborationManager.on('presence_changed', (event) => {
    console.log('User status:', event.user_id, event.status);
    // Update presence indicators
});
```

### Activity Feed Usage

```javascript
// Get activity feed
const activityFeed = await fetch(
    'http://localhost:8080/api/v1/collaboration/activity?project_id=proj_123'
).then(r => r.json());

// Display activity
activityFeed.activities.forEach(activity => {
    console.log(`${activity.user_name} ${activity.action} ${activity.entity_type}`);
    // 2 minutes ago: John created Person "Jane Doe"
});

// Filter activity
const filtered = await fetch(
    'http://localhost:8080/api/v1/collaboration/activity?' +
    'project_id=proj_123&' +
    'action=created&' +
    'entity_type=Person&' +
    'hours=24'
).then(r => r.json());
```

### Handling Merge Conflicts

```javascript
// Listen for conflicts
collaborationManager.on('merge_conflict', async (conflict) => {
    console.log('Conflict detected:', conflict);
    
    // Show conflict dialog to user
    const resolution = await showMergeDialog(conflict);
    
    // Send resolution to server
    await fetch('http://localhost:8080/api/v1/collaboration/conflicts/resolve', {
        method: 'POST',
        body: JSON.stringify({
            conflict_id: conflict.id,
            resolution: resolution  // 'keep_local', 'keep_remote', or 'merge'
        })
    });
});
```

### Presence Indicators

```javascript
// Show active users
const presence = await fetch(
    'http://localhost:8080/api/v1/collaboration/presence?project_id=proj_123'
).then(r => r.json());

presence.active_users.forEach(user => {
    // Show user indicator in UI
    console.log(`${user.name} is online (viewing: ${user.viewing_entity})`);
});

// Listen for presence updates
collaborationManager.on('user_joined', (user) => {
    console.log(`${user.name} joined the project`);
});

collaborationManager.on('user_left', (user) => {
    console.log(`${user.name} left the project`);
});
```

---

## Custom Plugins Development

### Plugin Structure

```json
{
  "id": "plugin_my_visualization",
  "name": "My Visualization",
  "version": "1.0.0",
  "author": "Your Name",
  "description": "A custom visualization plugin",
  "interface": {
    "inputs": [
      {
        "name": "start_date",
        "type": "date",
        "required": true
      },
      {
        "name": "entity_types",
        "type": "array",
        "options": ["Person", "Organization", "Location"]
      }
    ],
    "outputs": [
      {
        "name": "visualization_html",
        "type": "html"
      }
    ],
    "api_calls": [
      "GET /api/v1/entities",
      "GET /api/v1/relationships"
    ]
  },
  "sandbox": true,
  "min_entities": 10,
  "max_entities": 10000
}
```

### Developing a Plugin

```javascript
// static/plugins/my-visualization/index.js

class MyVisualizationPlugin {
    constructor(config) {
        this.config = config;
        this.container = config.container;
        this.api = config.api;  // API client
    }

    async init(inputs) {
        // inputs = { start_date, entity_types }
        const entities = await this.api.get('/api/v1/entities', {
            types: inputs.entity_types.join(','),
            created_after: inputs.start_date
        });

        const relationships = await this.api.get('/api/v1/relationships', {
            between_entities: entities.map(e => e.id)
        });

        return { entities, relationships };
    }

    render(data) {
        // Create visualization
        const html = this.createVisualization(data);
        this.container.innerHTML = html;
    }

    createVisualization(data) {
        // Your visualization logic
        // Return HTML or render using D3/Canvas/etc.
        return `<div>Visualization here</div>`;
    }

    onExport() {
        // Return exportable format
        return {
            format: 'svg',
            data: this.container.innerHTML
        };
    }
}

// Export for plugin loader
window.PluginClass = MyVisualizationPlugin;
```

### Installing a Plugin

```bash
# Option 1: Upload via API
curl -X POST http://localhost:8080/api/v1/plugins/upload \
  -F "file=@my-plugin.zip" \
  -F "metadata=manifest.json"

# Option 2: Upload via UI
# Dashboard > Plugins > Upload > Select ZIP file

# Option 3: Copy to plugins directory
cp -r my-plugin/ /opt/basset-hound/static/plugins/

# Verify installation
curl http://localhost:8080/api/v1/plugins/
```

### Using a Plugin

```javascript
// Load plugin
const pluginManager = new PluginManager();
const plugin = await pluginManager.load('my_visualization');

// Configure and render
const visualization = await plugin.render({
    start_date: '2026-01-01',
    entity_types: ['Person', 'Organization']
});

// Display in page
document.getElementById('visualization-container').appendChild(visualization);
```

### Built-in Plugins Usage

**Sankey Diagram**:
```javascript
const sankey = await pluginManager.load('sankey');
const output = await sankey.render({
    entity_type_filter: 'Person',
    time_window: '30d',
    group_by: 'creation_date'
});
```

**Timeline Visualization**:
```javascript
const timeline = await pluginManager.load('timeline');
const output = await timeline.render({
    start_date: '2026-01-01',
    end_date: '2026-05-07',
    granularity: 'daily',
    entity_types: ['Person', 'Organization']
});
```

**Heat Map**:
```javascript
const heatmap = await pluginManager.load('heatmap');
const output = await heatmap.render({
    time_window: '24h',
    granularity: 'hourly',
    metric: 'update_frequency'
});
```

---

## Export Configuration

### Using Export API

```bash
# GraphML Export
curl -X POST http://localhost:8080/api/v1/projects/proj_123/export/graphml \
  -H "Content-Type: application/json" \
  -d '{
    "entity_types": ["Person", "Organization"],
    "tags": ["VIP", "Target"],
    "include_properties": true
  }' \
  -o export.graphml

# CSV Export
curl -X POST http://localhost:8080/api/v1/projects/proj_123/export/csv \
  -H "Content-Type: application/json" \
  -d '{
    "filters": {
      "created_after": "2026-01-01",
      "entity_types": ["Person"]
    },
    "fields": ["id", "name", "email", "phone"],
    "page": 1,
    "limit": 1000
  }' \
  -o entities.csv

# JSON Export (structured)
curl -X POST http://localhost:8080/api/v1/projects/proj_123/export/json \
  -H "Content-Type: application/json" \
  -d '{
    "include_entities": true,
    "include_relationships": true,
    "include_metadata": true
  }' \
  -o graph.json

# GeoJSON Export (for mapping)
curl -X POST http://localhost:8080/api/v1/projects/proj_123/export/geojson \
  -d '{"entity_type": "Location"}' \
  -o locations.geojson

# PDF Report Export
curl -X POST http://localhost:8080/api/v1/projects/proj_123/export/pdf \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Investigation Report",
    "include_charts": true,
    "include_timeline": true,
    "include_communities": true
  }' \
  -o report.pdf

# Full Database Dump
curl -X POST http://localhost:8080/api/v1/projects/proj_123/export/database \
  -H "Content-Type: application/json" \
  -d '{
    "encrypt": true,
    "password": "secure_password",
    "compression": "gzip"
  }' \
  -o dump.tar.gz.enc
```

### Export in Code

```python
import requests
from datetime import datetime, timedelta

# Setup
base_url = "http://localhost:8080/api/v1"
project_id = "proj_123"

# Export entities as CSV
response = requests.post(
    f"{base_url}/projects/{project_id}/export/csv",
    json={
        "filters": {
            "entity_types": ["Person"],
            "created_after": (datetime.now() - timedelta(days=30)).isoformat()
        }
    },
    stream=True
)

with open("entities.csv", "wb") as f:
    for chunk in response.iter_content(chunk_size=8192):
        f.write(chunk)

# Export as JSON
response = requests.post(
    f"{base_url}/projects/{project_id}/export/json",
    json={
        "include_entities": True,
        "include_relationships": True
    },
    stream=True
)

with open("graph.json", "wb") as f:
    for chunk in response.iter_content():
        f.write(chunk)
```

---

## Usage Examples

### Example 1: Finding Duplicate Entities with ML

```python
# Find and merge duplicates automatically
from api.services.ml_analytics_service import MLAnalyticsService

ml_service = MLAnalyticsService()

# Find duplicates in project
duplicates = await ml_service.find_duplicates(
    project_id="proj_123",
    confidence_threshold=0.80,
    entity_type="Person"
)

# Auto-merge if confident
for source, targets in duplicates.items():
    for target in targets:
        if target['similarity'] > 0.90:
            await ml_service.merge_entities(
                source_id=source,
                target_id=target['id'],
                confidence=target['similarity']
            )
```

### Example 2: Real-Time Collaboration with Conflict Resolution

```javascript
// Multi-user project with automatic conflict handling
const collaboration = new CollaborationManager({
    project_id: 'proj_123',
    auto_merge: true  // Automatically merge non-conflicting changes
});

collaboration.on('conflict', (conflict) => {
    // Only show conflicts that can't be auto-merged
    console.log('Manual resolution needed:', conflict);
    
    // Merge strategy options
    const options = [
        { label: 'Keep Mine', value: 'local' },
        { label: 'Keep Theirs', value: 'remote' },
        { label: 'Merge Fields', value: 'merge' }
    ];
});

// Auto-archive old activity
setInterval(() => {
    fetch('http://localhost:8080/api/v1/collaboration/activity/archive', {
        method: 'POST',
        body: JSON.stringify({
            project_id: 'proj_123',
            older_than_minutes: 5
        })
    });
}, 5 * 60 * 1000);
```

### Example 3: Performance Monitoring

```python
import asyncio
from api.middleware.metrics import get_metrics

async def monitor_performance():
    while True:
        metrics = get_metrics()
        
        # Check critical thresholds
        if metrics['cache_hit_rate'] < 0.40:
            print("⚠️ Cache hit rate low:", metrics['cache_hit_rate'])
            # Warm cache
            await warm_cache()
        
        if metrics['query_latency_p99'] > 100:
            print("⚠️ Query latency high:", metrics['query_latency_p99'], "ms")
            # Alert or trigger optimization
        
        await asyncio.sleep(60)

asyncio.run(monitor_performance())
```

---

## Troubleshooting

### Issue: Cache Hit Rate Low

**Symptom**: Cache hit rate <30%

**Solutions**:
```bash
# Check cache configuration
curl http://localhost:8080/api/v1/cache/stats

# Warm cache with common queries
curl -X POST http://localhost:8080/api/v1/cache/warm

# Increase TTL
# Set in .env: CACHE_TTL_QUERY=120

# Check Redis connection
redis-cli ping
# Expected: PONG
```

### Issue: ML Analytics Slow

**Symptom**: ML endpoints taking >1s

**Solutions**:
```bash
# Check model loading
curl http://localhost:8080/api/v1/ml/models/status

# Reduce batch size
export ML_INFERENCE_BATCH_SIZE=50

# Pre-load models on startup
python scripts/preload_models.py

# Monitor GPU usage (if available)
nvidia-smi
```

### Issue: WebSocket Connection Failed

**Symptom**: Real-time collaboration not working

**Solutions**:
```bash
# Check WebSocket service
curl -i -N -H "Connection: Upgrade" \
  -H "Upgrade: websocket" \
  http://localhost:8080/ws/sync/proj_123

# Verify ENABLE_COLLABORATION=true in .env

# Check for firewall issues
telnet localhost 8080

# Increase connection limits
ulimit -n 65536
```

### Issue: Export Timeout

**Symptom**: Large exports timing out

**Solutions**:
```bash
# Increase export timeout
export EXPORT_TIMEOUT_SECONDS=600  # 10 minutes

# Export in smaller chunks
curl -X POST http://localhost:8080/api/v1/projects/proj_123/export/csv \
  -d '{
    "page": 1,
    "limit": 50000
  }'

# Monitor export jobs
curl http://localhost:8080/api/v1/exports/jobs
```

### Issue: Plugin Sandbox Issues

**Symptom**: Plugins not loading or crashing

**Solutions**:
```bash
# Check plugin manifest
cat static/plugins/my-plugin/manifest.json

# Verify plugin size
du -h static/plugins/my-plugin/

# Check console for errors
curl http://localhost:8080/api/v1/plugins/my-plugin/logs

# Disable sandbox temporarily for debugging
export PLUGIN_SANDBOX_ENABLED=false
```

---

## Quick Reference

### Common Commands

```bash
# Enable all Phase 8 features
export ENABLE_ML_ANALYTICS=true
export ENABLE_COLLABORATION=true
export ENABLE_PLUGINS=true
export ENABLE_EXPORT=true

# Check cache performance
curl http://localhost:8080/api/v1/metrics/performance

# List available plugins
curl http://localhost:8080/api/v1/plugins

# View database statistics
curl http://localhost:8080/api/v1/metrics/database

# Export all data as JSON
curl -X POST http://localhost:8080/api/v1/projects/proj_123/export/json \
  -d '{}' > full_export.json
```

### Feature Compatibility Matrix

| Feature | Minimum Requirements | Recommended |
|---------|---------------------|-------------|
| ML Analytics | 2GB RAM, 1 hour training | 8GB RAM, GPU |
| Collaboration | WebSocket support, Redis | Redis Cluster |
| Plugins | 100MB disk space | 500MB disk space |
| Export | API access, 2GB disk | Async job queue |

---

## Next Steps

1. **Enable desired features** via environment variables
2. **Test each feature** with provided examples
3. **Monitor performance** using metrics endpoints
4. **Customize configurations** based on your needs
5. **Integrate with workflows** as needed

For detailed technical information, see the [Phase 8 Summary](./archive/PHASE-8-SUMMARY-2026-05-07.md) and individual stream documents in the `docs/findings/` directory.

---

**Document Version**: 1.0.0  
**Last Updated**: 2026-05-07  
**Status**: Production Ready
