# Cletus Integration - News Aggregation Data Source

**Date**: 2026-02-10
**Integration Version**: 1.0 (Stream 9)
**Status**: IMPLEMENTED (2026-05-06)

## Overview

[Cletus](~/cletus/) is a news aggregation platform that scrapes 272 sources across 12 categories, generates LLM-based intelligence reports, and tracks evolving events across report cycles. Basset Hound can consume Cletus's event timeline data to build relationship graphs between news events, entities, and categories.

**Cletus provides**: Raw aggregated news data, LLM-extracted events, keyword-based timeline matching
**Basset Hound provides**: Deep relationship analysis, entity resolution, graph visualization, path finding

## Why Integrate

Cletus tracks 70+ event timelines across 10 news categories with keyword-based matching (Jaccard similarity). However, it deliberately does NOT:
- Establish authoritative entity relationships
- Perform deep graph analysis or clustering
- Provide 3D relationship visualization
- Resolve entity identity across events

These are exactly Basset Hound's strengths. By consuming Cletus's event timeline data, Basset Hound can:
1. Build a graph of how news events relate to each other
2. Link events to entities (people, organizations, governments)
3. Discover non-obvious connections across categories
4. Provide 3D graph visualization of the news landscape

## Cletus API Endpoints (Data Sources)

Cletus runs on `http://localhost:9000`. All data is available via REST API.

### Event Timelines (Primary Integration Point)
```
GET /api/events/                    # List all event timelines (filter by status, category, severity)
GET /api/events/{id}                # Get timeline with all entries
GET /api/events/stats               # Summary statistics
GET /api/events/search?q=           # Search by title/summary
```

**EventTimeline fields**: id, title, summary, category, event_type, severity, keywords (JSON array), status (active/dormant/closed), first_seen, last_updated, entry_count, report_count, article_count

**EventTimelineEntry fields**: id, event_id, report_id, summary, key_developments (JSON array), sources_mentioned (JSON array), sentiment_shift, significance, article_ids (JSON array), observed_at

### Reports
```
GET /api/reports/sessions           # List report sessions
GET /api/reports/{id}               # Get full report (markdown content)
GET /api/export/reports/{id}/json   # Export report as structured JSON
```

### Articles
```
GET /api/export/articles/json       # Export articles (filter by category, session, limit)
GET /api/export/articles/csv        # CSV export
```

### Feeds
```
GET /api/export/feed/rss            # RSS feed of reports
GET /api/export/feed/atom           # Atom feed of reports
```

## Proposed Integration Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        Cletus (Port 9000)                      │
│              News Aggregation + Event Timelines                │
│                                                                │
│  272 sources → Articles → Reports → Event Timelines           │
│                                                                │
│  REST API: /api/events/, /api/reports/, /api/export/          │
└─────────────────────────┬────────────────────────────────────┘
                          │ HTTP/REST
                          │ Pull-based (Basset Hound polls Cletus)
                          ▼
┌──────────────────────────────────────────────────────────────┐
│                    Basset Hound (Port 8000)                    │
│              Entity Relationship Engine (Neo4j)                │
│                                                                │
│  1. Fetch event timelines from Cletus API                     │
│  2. Create entities for events, categories, sources           │
│  3. Establish relationships:                                   │
│     - EVENT -[SHARES_KEYWORDS]-> EVENT                        │
│     - EVENT -[IN_CATEGORY]-> CATEGORY                         │
│     - EVENT -[MENTIONED_IN]-> REPORT                          │
│     - EVENT -[TEMPORAL_PROXIMITY]-> EVENT                     │
│     - EVENT -[INVOLVES]-> PERSON/ORGANIZATION                 │
│  4. Provide graph visualization + path analysis               │
└──────────────────────────────────────────────────────────────┘
```

## Suggested Entity Mappings

| Cletus Concept | Basset Hound Entity Type | Notes |
|---|---|---|
| EventTimeline | Custom: "NewsEvent" | title, summary, severity, keywords |
| News Category | Custom: "NewsCategory" | 12 categories |
| Source | Organization | News source as entity |
| Person mentioned | Person | Extracted from event key_developments |
| Organization mentioned | Organization | Extracted from event sources_mentioned |

## Suggested Relationship Types

| Relationship | From → To | Source |
|---|---|---|
| SHARES_KEYWORDS | NewsEvent → NewsEvent | Jaccard similarity on keywords |
| IN_CATEGORY | NewsEvent → NewsCategory | EventTimeline.category |
| TEMPORAL_PROXIMITY | NewsEvent → NewsEvent | Events within same time window |
| MENTIONED_IN | NewsEvent → Report | EventTimelineEntry.report_id |
| INVOLVES | NewsEvent → Person/Org | Extracted from key_developments text |
| CROSS_CATEGORY | NewsEvent → NewsEvent | Same event mentioned in different categories |

## Implementation Suggestions

### Phase 1: Data Ingestion
- Create a Basset Hound connector/plugin that polls Cletus `/api/events/` periodically
- Map event timelines to Neo4j nodes with all metadata
- Establish SHARES_KEYWORDS edges using the existing keyword overlap

### Phase 2: Entity Extraction
- Use Basset Hound's entity resolution on event timeline summaries and key_developments
- Link events to people, organizations, governments mentioned
- This is where Basset Hound adds value beyond what Cletus can do alone

### Phase 3: Graph Visualization
- 3D visualization of the news event graph
- Path finding: "How is this Cyber event connected to this Legal event?"
- Clustering: group tightly connected events
- Temporal animation: watch the graph evolve over time

## Open Questions
1. Should Basset Hound create a dedicated "Cletus connector" or use the generic MCP/API pattern?
2. How often should Basset Hound poll Cletus? (After each report generation? Daily?)
3. Should Cletus expose a webhook/notification when new events are created, or is polling sufficient?
4. What Basset Hound entity types best map to news events? (Existing types, or new custom types?)

## Implementation Details (Stream 9)

### Client: `api/clients/cletus_client.py`

Async HTTP client for Cletus API with methods:

```python
class CletusClient:
    async def health_check() -> bool
    async def list_events(category, status, severity) -> List[Dict]
    async def get_event(event_id) -> Dict
    async def get_event_stats() -> Dict
    async def search_events(query) -> List[Dict]
    async def list_reports() -> List[Dict]
    async def get_report(report_id) -> str
    async def export_articles_json(category, limit) -> List[Dict]
```

Features:
- Connection pooling via httpx.AsyncClient
- Automatic reconnection with timeout handling
- Graceful degradation on connection failure
- Context manager for lifecycle management

### Service: `api/services/cletus_ingestion.py`

Maps Cletus events to basset-hound entities:

```python
class CletusIngestionService:
    async def ingest_all_events() -> Dict[str, Any]
    async def ingest_event(client, event) -> str
    async def ingest_event_by_id(event_id) -> str
```

Entity Creation Strategy:
- **NewsEvent**: Created as Person entity with "News Event Details" profile section
  - Stores: title, summary, category, severity, status, keywords, timestamps
  - Includes cletus_event_id for deduplication
- **Category**: Created as Person entity (type="news_category")
- **Organization**: Created as Person entity (type="organization")

Relationship Types:
- `IN_CATEGORY`: Event → Category
- `INVOLVES`: Event → Organization (from sources_mentioned)
- `SHARES_KEYWORDS`: Event → Event (bidirectional keyword overlap)

### Router: `api/routers/cletus_integration.py`

REST endpoints:

```
GET /api/v1/cletus/status              # Check Cletus health
GET /api/v1/cletus/stats               # Get event statistics
GET /api/v1/cletus/events              # List events with filters
GET /api/v1/cletus/events/search?q=    # Search events
GET /api/v1/cletus/events/{event_id}   # Get event details
POST /api/v1/cletus/ingest             # Ingest all events
POST /api/v1/cletus/ingest/{event_id}  # Ingest specific event
```

Query Parameters:
- `project_safe_name` (required for ingest endpoints): Target project
- `category` (optional): Filter by news category
- `status` (optional): Filter by status (active, dormant, closed)
- `severity` (optional): Filter by severity level
- `q` (required for search): Search query

Response Examples:

Health Check:
```json
{
  "status": "available",
  "message": "Cletus is healthy and responding"
}
```

Ingestion Results:
```json
{
  "success": true,
  "message": "Successfully ingested 42/45 events",
  "total": 45,
  "created": 42,
  "errors": [
    "Event evt_123: Missing required fields",
    "Event evt_456: Organization creation failed"
  ]
}
```

### Configuration

Environment variable `CLETUS_BASE_URL` (default: http://localhost:9000):

```env
CLETUS_BASE_URL=http://localhost:9000
```

### Testing

Integration tests in `tests/integration/test_cletus_integration.py`:
- Client initialization and configuration
- Health checks and connectivity
- Mock event ingestion
- Entity and relationship creation
- Organization extraction
- Category handling

Run with:
```bash
pytest tests/integration/test_cletus_integration.py -v
```

## Notes
- Cletus is designed as an information aggregation platform, NOT an information management platform
- Comprehensive relationship management is explicitly out of Cletus's scope
- The integration is one-directional: Basset Hound consumes from Cletus, not vice versa
- Cletus will have its own lightweight timeline visualization (D3.js/vis.js) for the frontend, separate from Basset Hound's deep graph analysis

## Future Enhancements

Phase 9.1: Advanced Entity Extraction
- NER-based extraction of people/entities from key_developments text
- Linking extracted entities to existing project entities
- Confidence scoring for mentions

Phase 9.2: Temporal Analysis
- Track entity connections over time as new events emerge
- Detect temporal patterns (sudden spikes, correlations)
- Timeline visualization of event evolution

Phase 9.3: Webhook Support
- Cletus → Basset Hound webhooks for real-time ingestion
- Event stream processing with configurable debouncing
- Automatic background ingestion of new events
