# Cletus Integration - News Aggregation Data Source

**Date**: 2026-02-10
**Integration Version**: Proposed (not yet implemented)
**Status**: PLANNING

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

## Notes
- Cletus is designed as an information aggregation platform, NOT an information management platform
- Comprehensive relationship management is explicitly out of Cletus's scope
- The integration is one-directional: Basset Hound consumes from Cletus, not vice versa
- Cletus will have its own lightweight timeline visualization (D3.js/vis.js) for the frontend, separate from Basset Hound's deep graph analysis
