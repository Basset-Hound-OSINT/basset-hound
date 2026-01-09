# Intelligence Analysis Integration

**Version:** 1.0
**Date:** 2026-01-09
**Status:** Future Architecture Proposal

---

## Overview

This document describes the future **intelligence-analysis** project and how it will integrate with **basset-hound** to provide advanced analytical capabilities while maintaining clear separation of concerns.

**Key Principle:** basset-hound is the **storage backbone**, intelligence-analysis is the **analytical brain**.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Intelligence Analysis                     │
│                     (Future Project)                         │
│  ┌────────────┐  ┌────────────┐  ┌────────────────────────┐ │
│  │ AI Agents  │  │ ML Models  │  │ Pattern Detection      │ │
│  │            │  │            │  │ - Behavioral analysis  │ │
│  │ - Entity   │  │ - Entity   │  │ - Anomaly detection   │ │
│  │   resolver │  │   resolution│  │ - Network analysis    │ │
│  │ - Pattern  │  │ - Risk     │  │ - Predictive analytics│ │
│  │   hunter   │  │   scoring  │  │ - Threat scoring      │ │
│  │ - Report   │  │ - Sentiment│  │                       │ │
│  │   generator│  │   analysis │  │                       │ │
│  └────────────┘  └────────────┘  └────────────────────────┘ │
│                          │                                   │
│                          ▼                                   │
│                  ┌───────────────┐                           │
│                  │ Analysis API  │                           │
│                  └───────────────┘                           │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          │ Read/Write via MCP + REST API
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                      basset-hound                            │
│                   (Storage Backbone)                         │
│  ┌────────────┐  ┌────────────┐  ┌────────────────────────┐ │
│  │ Entities   │  │ Relations  │  │ Evidence               │ │
│  │            │  │            │  │                        │ │
│  │ - Profiles │  │ - Graph    │  │ - Screenshots          │ │
│  │ - IDs      │  │ - Props    │  │ - Page archives        │ │
│  │ - Metadata │  │ - Strength │  │ - Network HAR          │ │
│  │            │  │            │  │ - DOM snapshots        │ │
│  └────────────┘  └────────────┘  └────────────────────────┘ │
│                                                               │
│  ┌────────────┐  ┌────────────┐  ┌────────────────────────┐ │
│  │ Reports    │  │ Orphan     │  │ Investigations         │ │
│  │ (generated │  │ Data       │  │                        │ │
│  │  by intel- │  │            │  │ - Cases                │ │
│  │  analysis) │  │ - Unlinked │  │ - Tasks                │ │
│  │            │  │   IDs      │  │ - Timeline             │ │
│  │            │  │            │  │                        │ │
│  └────────────┘  └────────────┘  └────────────────────────┘ │
│                                                               │
│                    Neo4j Graph Database                       │
└───────────────────────────────────────────────────────────────┘
```

---

## Separation of Concerns

### basset-hound (Storage & Management)

**Role:** Data backbone for intelligence operations

**Responsibilities:**
- ✅ Store entities, relationships, evidence, and provenance
- ✅ Organize data by projects and investigations
- ✅ Provide MCP tools and REST API for data access
- ✅ Basic data matching with confidence scores (hash comparison, fuzzy matching)
- ✅ Human-in-the-loop suggestions ("these might be related")
- ✅ Graph queries (shortest path, centrality, clustering)
- ✅ Full-text search and filtering
- ✅ Data import/export in various formats
- ✅ Audit trail and provenance tracking

**NOT Responsible For:**
- ❌ Machine learning or AI model training
- ❌ Advanced pattern detection
- ❌ Behavioral analysis
- ❌ Predictive analytics
- ❌ Anomaly detection
- ❌ Threat scoring algorithms

### intelligence-analysis (Analysis & Insights)

**Role:** Analytical brain for intelligence operations

**Responsibilities:**
- ✅ Machine learning for entity resolution
- ✅ Pattern detection across entities and relationships
- ✅ Behavioral analysis and profiling
- ✅ Predictive analytics (threat likelihood, risk scoring)
- ✅ Anomaly detection (unusual patterns, outliers)
- ✅ Network analysis (community detection with ML, influence scoring)
- ✅ Natural language processing (sentiment analysis, topic modeling)
- ✅ Image recognition (facial detection, object recognition)
- ✅ Geospatial analysis (geocoding, route planning, proximity analysis)
- ✅ Generate analytical reports with insights and recommendations
- ✅ Automated investigation workflow suggestions

**NOT Responsible For:**
- ❌ Long-term data storage (uses basset-hound for persistence)
- ❌ Evidence collection (uses basset-hound-browser)
- ❌ Identifier verification (uses basset-verify)

---

## Integration Patterns

### 1. Data Access (intelligence-analysis → basset-hound)

**intelligence-analysis reads from basset-hound via:**

**MCP Tools (Primary):**
```python
# AI agents use basset-hound MCP tools
from mcp import ClientSession

async with ClientSession(basset_hound_url) as session:
    # Get all entities for analysis
    entities = await session.call_tool("list_entities", {
        "project_id": "proj_123",
        "limit": 1000
    })

    # Get relationship graph
    relationships = await session.call_tool("get_entity_relationships", {
        "project_id": "proj_123",
        "entity_id": "ent_456"
    })
```

**REST API (Alternative):**
```python
# Direct API calls for bulk operations
import httpx

async with httpx.AsyncClient() as client:
    # Export entire project for analysis
    response = await client.get(
        "http://localhost:8000/api/v1/projects/proj_123/bulk/export",
        params={"include_relationships": True}
    )
    project_data = response.json()
```

### 2. Results Storage (intelligence-analysis → basset-hound)

**intelligence-analysis writes results back to basset-hound:**

**Analytical Reports:**
```python
# Store generated report in basset-hound
report = await session.call_tool("create_report", {
    "project_id": "proj_123",
    "report_type": "intelligence_analysis",
    "title": "Entity Resolution Analysis",
    "format": "markdown",
    "content": analysis_results,
    "metadata": {
        "analysis_type": "entity_resolution",
        "model_version": "1.2.3",
        "confidence": 0.87,
        "generated_by": "intelligence-analysis",
        "timestamp": "2026-01-09T10:30:00Z"
    }
})
```

**Suggested Relationships:**
```python
# AI agent suggests new relationship based on analysis
suggestion = await session.call_tool("link_entities", {
    "project_id": "proj_123",
    "source_id": "ent_123",
    "target_id": "ent_456",
    "relationship_type": "ASSOCIATED_WITH",
    "properties": {
        "confidence": 0.75,
        "source": "ml_analysis",
        "reason": "Similar behavior patterns detected",
        "suggested": True,  # Flag for human review
        "analysis_id": "analysis_789"
    }
})
```

**Annotations and Tags:**
```python
# Add ML-generated tags to entities
await session.call_tool("update_entity", {
    "project_id": "proj_123",
    "entity_id": "ent_123",
    "tags": ["high_risk", "anomaly_detected", "requires_review"],
    "metadata": {
        "risk_score": 0.82,
        "threat_level": "medium",
        "last_analyzed": "2026-01-09T10:30:00Z"
    }
})
```

### 3. Bidirectional Workflow

**Complete investigation workflow:**

```
1. Investigator collects data
   ↓
2. basset-hound-browser captures evidence
   ↓
3. basset-hound stores entities, relationships, evidence
   ↓
4. intelligence-analysis reads project data via MCP
   ↓
5. AI agents perform analysis:
   - Entity resolution (find duplicates with ML)
   - Pattern detection (behavioral clusters)
   - Risk scoring (threat assessment)
   - Network analysis (influence mapping)
   ↓
6. intelligence-analysis writes results to basset-hound:
   - Analytical reports linked to entities
   - Suggested relationships (flagged for human review)
   - Tags and annotations (risk scores, threat levels)
   ↓
7. Investigator reviews AI suggestions in basset-hound UI
   ↓
8. Human operator approves/rejects AI suggestions
   ↓
9. Approved suggestions become permanent relationships
```

---

## Use Cases

### Use Case 1: ML-Based Entity Resolution

**Problem:** Multiple entities might represent the same person, but fuzzy matching isn't enough.

**Solution:**

1. **basset-hound** stores entities with basic data matching:
   - John Smith (john@example.com)
   - J. Smith (jsmith@company.com)
   - Jonathan Smith (johnsmith@gmail.com)
   - Basic fuzzy matching suggests possible duplicates (0.6-0.7 confidence)

2. **intelligence-analysis** performs ML-based resolution:
   - Trains on investigator's past merge decisions
   - Analyzes behavior patterns (same locations, timestamps, social circles)
   - Uses graph embeddings to find hidden connections
   - Generates high-confidence suggestions (0.85-0.95 confidence)

3. **Result:** AI suggests merging entities with detailed reasoning:
   ```markdown
   **Suggested Merge:** ent_123 + ent_456 + ent_789

   **Confidence:** 0.91

   **Reasoning:**
   - All three entities visited same locations within 1 hour
   - Email domains resolve to same organization
   - Social network overlap: 15 mutual connections
   - Writing style analysis: 0.89 similarity
   - IP address clustering: Same /24 subnet

   **Recommendation:** High confidence - likely same person
   ```

### Use Case 2: Behavioral Pattern Detection

**Problem:** Identify entities with suspicious behavior patterns.

**Solution:**

1. **basset-hound** stores entity activity:
   - Login timestamps
   - Location changes
   - Transaction history
   - Communication patterns

2. **intelligence-analysis** detects anomalies:
   - Time series analysis for unusual activity spikes
   - Geospatial analysis for impossible travel
   - Network analysis for suspicious new connections
   - Sentiment analysis for communication tone changes

3. **Result:** AI generates alert report stored in basset-hound:
   ```markdown
   **Anomaly Alert:** Entity ent_123

   **Risk Score:** 0.78 (High)

   **Anomalies Detected:**
   1. Impossible travel: NYC → Tokyo in 2 hours
   2. Activity spike: 300% increase in communications
   3. New connections: 15 suspicious accounts in 24 hours
   4. Sentiment shift: Neutral → Aggressive (0.82 confidence)

   **Recommended Actions:**
   - Flag for immediate investigation
   - Review all new relationships
   - Cross-reference with threat intelligence
   ```

### Use Case 3: Network Influence Analysis

**Problem:** Identify key players in a network.

**Solution:**

1. **basset-hound** stores relationship graph:
   - Entities and typed relationships
   - Relationship properties (strength, confidence)
   - Basic centrality metrics (degree count)

2. **intelligence-analysis** performs advanced network analysis:
   - PageRank for influence scoring
   - Community detection with Louvain algorithm
   - Betweenness centrality (bridge nodes)
   - Temporal network analysis (how influence changes over time)

3. **Result:** AI generates influence report:
   ```markdown
   **Network Influence Analysis**

   **Top 5 Influencers:**
   1. ent_456 - PageRank: 0.42, Betweenness: 0.38
      - Role: Network hub, connects 3 communities
      - Influence trend: +25% over last 30 days

   2. ent_789 - PageRank: 0.35, Betweenness: 0.15
      - Role: Information broker
      - Influence trend: Stable

   **Communities Detected:** 4 distinct clusters
   - Community A: Financial sector (12 entities)
   - Community B: Social activists (8 entities)
   - Community C: Tech industry (15 entities)
   - Community D: Mixed/unknown (5 entities)

   **Bridge Nodes:** ent_456, ent_234 (connect communities)
   ```

### Use Case 4: Predictive Threat Scoring

**Problem:** Assess which entities pose the highest risk.

**Solution:**

1. **basset-hound** stores entity data and evidence:
   - Profile information
   - Communication history
   - Associated evidence (screenshots, documents)
   - Investigation notes

2. **intelligence-analysis** trains threat scoring model:
   - Features: Entity attributes, relationship patterns, behavior metrics
   - Training data: Past investigations with known outcomes
   - Model: Gradient boosting classifier with SHAP explainability

3. **Result:** AI assigns threat scores with explanations:
   ```markdown
   **Threat Score:** 0.87 (High Risk)

   **Contributing Factors:**
   - Association with known threat actors (+0.35)
   - Recent activity in sanctioned regions (+0.25)
   - Communication pattern anomalies (+0.15)
   - Use of encryption tools (+0.12)

   **Model Confidence:** 0.82

   **Recommended Action:** Priority investigation
   ```

---

## Technical Architecture

### intelligence-analysis Tech Stack

**Core Technologies:**
- **Python 3.11+** - Primary language
- **FastAPI** - REST API for analysis services
- **FastMCP** - MCP client for basset-hound integration
- **scikit-learn** - Traditional ML algorithms
- **TensorFlow/PyTorch** - Deep learning models
- **NetworkX** - Graph analysis algorithms
- **spaCy/NLTK** - Natural language processing
- **GeoPandas** - Geospatial analysis
- **Redis** - Caching for analysis results
- **PostgreSQL** - Metadata storage (model versions, training history)

**Project Structure:**
```
intelligence-analysis/
├── agents/                    # AI agents
│   ├── entity_resolver.py     # ML-based entity resolution
│   ├── pattern_hunter.py      # Pattern detection
│   ├── report_generator.py    # Analytical report generation
│   └── threat_scorer.py       # Risk assessment
├── models/                    # ML models
│   ├── entity_resolution/
│   │   ├── model.pkl
│   │   ├── vectorizer.pkl
│   │   └── config.yaml
│   ├── threat_scoring/
│   └── sentiment_analysis/
├── analysis/                  # Analysis services
│   ├── behavioral.py          # Behavioral analysis
│   ├── network.py             # Network analysis
│   ├── geospatial.py          # Geospatial analysis
│   └── nlp.py                 # Text analysis
├── integrations/              # External system integrations
│   ├── basset_hound.py        # basset-hound MCP client
│   ├── basset_verify.py       # basset-verify client
│   └── threat_intel.py        # Threat intelligence feeds
├── api/                       # REST API
│   ├── routers/
│   │   ├── analysis.py
│   │   ├── reports.py
│   │   └── models.py
│   └── main.py
├── training/                  # Model training scripts
│   ├── train_entity_resolution.py
│   ├── train_threat_scorer.py
│   └── evaluate_models.py
├── tests/
├── docs/
└── requirements.txt
```

### Deployment Architecture

**Development:**
```yaml
# docker-compose.yml
services:
  basset-hound:
    image: basset-hound:latest
    ports:
      - "8000:8000"
    environment:
      - NEO4J_URI=bolt://neo4j:7687

  neo4j:
    image: neo4j:5.28.1
    ports:
      - "7474:7474"
      - "7687:7687"

  intelligence-analysis:
    image: intelligence-analysis:latest
    ports:
      - "8001:8001"
    environment:
      - BASSET_HOUND_URL=http://basset-hound:8000
      - REDIS_URL=redis://redis:6379
    depends_on:
      - basset-hound
      - redis

  redis:
    image: redis:7
    ports:
      - "6379:6379"
```

**Production:**
- basset-hound: Lightweight, runs on investigator's laptop
- intelligence-analysis: Cloud-based for GPU acceleration and model training
- Communication: Encrypted HTTPS + VPN tunnel
- Data flow: basset-hound → intelligence-analysis → basset-hound (results)

---

## API Design

### intelligence-analysis REST API

**Endpoint Examples:**

```python
# POST /api/v1/analyze/entity-resolution
{
  "project_id": "proj_123",
  "entity_ids": ["ent_123", "ent_456", "ent_789"],
  "confidence_threshold": 0.8
}

# Response
{
  "analysis_id": "analysis_001",
  "suggestions": [
    {
      "entities": ["ent_123", "ent_456"],
      "confidence": 0.91,
      "reasoning": "Same locations, email domain match, network overlap",
      "action": "merge"
    }
  ],
  "report_url": "http://basset-hound:8000/reports/rep_001"
}

# POST /api/v1/analyze/behavioral-patterns
{
  "project_id": "proj_123",
  "entity_id": "ent_123",
  "analysis_type": "anomaly_detection",
  "time_range": "30d"
}

# Response
{
  "analysis_id": "analysis_002",
  "risk_score": 0.78,
  "anomalies": [
    {
      "type": "impossible_travel",
      "confidence": 0.95,
      "description": "NYC → Tokyo in 2 hours"
    }
  ],
  "report_url": "http://basset-hound:8000/reports/rep_002"
}

# POST /api/v1/analyze/network-influence
{
  "project_id": "proj_123",
  "algorithm": "pagerank",
  "min_connections": 3
}

# Response
{
  "analysis_id": "analysis_003",
  "top_influencers": [
    {
      "entity_id": "ent_456",
      "pagerank": 0.42,
      "betweenness": 0.38,
      "role": "Network hub"
    }
  ],
  "communities": [
    {
      "id": "community_A",
      "size": 12,
      "label": "Financial sector"
    }
  ],
  "report_url": "http://basset-hound:8000/reports/rep_003"
}
```

---

## Data Flow Examples

### Example 1: AI-Assisted Investigation

```
1. Investigator creates project in basset-hound
   → POST /api/v1/projects {name: "Operation Phoenix"}

2. Investigator adds entities manually
   → POST /api/v1/entities (10 entities created)

3. basset-hound suggests basic matches (fuzzy matching)
   → GET /api/v1/entities/ent_123/suggestions
   → Response: 3 potential duplicates (0.6-0.7 confidence)

4. Investigator requests AI analysis
   → POST intelligence-analysis:8001/api/v1/analyze/entity-resolution
   → {project_id: "proj_123", confidence_threshold: 0.8}

5. intelligence-analysis:
   a. Reads project data from basset-hound via MCP
      → list_entities(project_id="proj_123")
   b. Performs ML-based entity resolution
      → Uses trained model + graph embeddings
   c. Writes report to basset-hound
      → create_report(title="Entity Resolution Analysis")
   d. Tags entities with risk scores
      → update_entity(tags=["high_confidence_duplicate"])

6. Investigator reviews AI suggestions in basset-hound UI
   → GET /api/v1/reports/rep_001
   → Shows: 2 high-confidence merges (0.85, 0.91)

7. Investigator approves merge
   → POST /api/v1/entities/merge
   → {source: "ent_123", target: "ent_456"}

8. basset-hound records decision for future ML training
   → Audit log: {"action": "merge_approved", "suggested_by": "ml_analysis"}
```

### Example 2: Continuous Monitoring

```
1. intelligence-analysis runs scheduled analysis (daily)
   → Cron job: analyze_behavioral_patterns()

2. For each project in basset-hound:
   a. Read entities created/updated in last 24h
      → list_entities(updated_since="2026-01-08T00:00:00Z")
   b. Perform anomaly detection
      → Check for unusual patterns
   c. Generate alerts for high-risk anomalies
      → create_report(report_type="anomaly_alert")
   d. Tag entities with risk scores
      → update_entity(metadata={risk_score: 0.78})

3. Investigator logs into basset-hound
   → Dashboard shows: "2 new alerts from AI analysis"

4. Investigator reviews alerts
   → GET /api/v1/reports?type=anomaly_alert&status=new

5. Investigator takes action based on AI recommendations
```

---

## Migration Path

### Phase 1: Proof of Concept (4 weeks)

**Goal:** Validate architecture with simple ML model

**Deliverables:**
1. Create intelligence-analysis repository
2. Implement basic entity resolution agent
3. Integrate with basset-hound via MCP
4. Train simple model on sample dataset
5. Generate first AI report stored in basset-hound

**Success Criteria:**
- AI agent can read entities from basset-hound
- Model suggests entity merges with >80% accuracy
- Reports are stored and viewable in basset-hound

### Phase 2: Core Agents (8 weeks)

**Goal:** Implement primary AI agents

**Deliverables:**
1. Entity resolver (ML-based duplicate detection)
2. Pattern hunter (behavioral pattern detection)
3. Threat scorer (risk assessment model)
4. Report generator (automated analytical reports)

**Success Criteria:**
- All agents integrated with basset-hound
- Models achieve >85% accuracy on test datasets
- Human-in-the-loop workflow functional

### Phase 3: Advanced Analysis (12 weeks)

**Goal:** Add sophisticated analytical capabilities

**Deliverables:**
1. Network analysis (PageRank, community detection)
2. Geospatial analysis (geocoding, proximity)
3. NLP analysis (sentiment, topic modeling)
4. Image analysis (facial recognition, object detection)

**Success Criteria:**
- Full suite of analytical capabilities
- Performance: <5s for most analyses
- Integration tests passing

### Phase 4: Production Deployment (4 weeks)

**Goal:** Production-ready deployment

**Deliverables:**
1. Docker compose setup
2. Cloud deployment (AWS/GCP)
3. Model versioning and registry
4. Monitoring and alerting
5. User documentation

**Success Criteria:**
- 99.9% uptime
- <1s API response times
- Complete documentation

---

## Success Metrics

### Technical Metrics

| Metric | Target |
|--------|--------|
| **Entity Resolution Accuracy** | >85% precision, >80% recall |
| **Anomaly Detection Accuracy** | <5% false positive rate |
| **Threat Scoring Accuracy** | >80% on validation dataset |
| **API Response Time** | <5s for complex analyses |
| **Model Inference Time** | <1s for entity resolution |
| **Uptime** | 99.9% availability |

### Business Metrics

| Metric | Target |
|--------|--------|
| **Time Saved** | 50% reduction in manual entity resolution |
| **Investigation Quality** | 30% increase in discovered relationships |
| **Alert Accuracy** | >70% of alerts actionable |
| **Investigator Satisfaction** | >80% find AI suggestions helpful |

---

## Security Considerations

### Data Privacy

- **Sensitive Data:** intelligence-analysis processes highly sensitive investigation data
- **Encryption:** All communication basset-hound ↔ intelligence-analysis uses TLS 1.3
- **Data Retention:** Analysis results stored in basset-hound, not intelligence-analysis
- **Model Privacy:** Models trained on aggregated data, never on individual cases
- **Access Control:** intelligence-analysis requires API key from basset-hound

### Deployment Security

- **Separation:** basset-hound (local) + intelligence-analysis (cloud) = air gap
- **VPN Tunnel:** Encrypted tunnel for cloud communication
- **No Direct Access:** intelligence-analysis cannot write arbitrary data to basset-hound
- **Audit Logging:** All AI actions logged in basset-hound audit trail

---

## Conclusion

The separation of **basset-hound** (storage) and **intelligence-analysis** (analysis) provides:

✅ **Clear Separation of Concerns** - Each project focused on what it does best
✅ **Lightweight Storage** - basset-hound stays simple and reliable
✅ **Advanced Analysis** - intelligence-analysis uses ML without constraints
✅ **Flexible Deployment** - Storage local, analysis in cloud
✅ **Investigator Choice** - Use basset-hound standalone or with AI augmentation
✅ **Maintainability** - Independent release cycles, easier testing
✅ **Scalability** - Scale storage and analysis independently

**Next Steps:**
1. Finalize basset-hound Phase 44-46 (REST API, WebSocket, UI)
2. Create intelligence-analysis repository
3. Build Phase 1 proof of concept
4. Validate architecture with real investigation data

---

**Document Version:** 1.0
**Last Updated:** 2026-01-09
**Author:** basset-hound team
**Status:** Proposed Architecture
