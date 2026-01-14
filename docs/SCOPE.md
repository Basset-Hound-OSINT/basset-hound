# basset-hound Scope Definition

**Version:** 2.0 (Post-Phase 41 Clarification)
**Date:** 2026-01-09
**Status:** Active

---

## Purpose

basset-hound is an **intelligence storage and management system** for OSINT investigations. It provides the **data backbone** for intelligence work - structured storage, relationship mapping, investigation tracking, and basic data matching through a Neo4j graph database and MCP server interface.

**Core Mission**: Store and manage intelligence in highly configurable ways, enabling AI agents and investigators to organize, query, and retrieve collected information.

**What basset-hound IS:**
- ✅ **Storage backbone** - Entities, relationships, evidence, provenance
- ✅ **Data organization** - Projects, investigations, timelines
- ✅ **Basic data matching** - Suggest potential matches with confidence scores
- ✅ **Graph database** - Relationship queries and path finding
- ✅ **MCP server** - API for AI agents and external tools

**What basset-hound is NOT:**
- ❌ **Intelligence analysis platform** - No ML, pattern detection, or predictive analytics
- ❌ **OSINT automation** - No web scraping or social media enumeration
- ❌ **Verification service** - Use basset-verify for identifier validation
- ❌ **Browser automation** - Use basset-hound-browser for evidence capture

basset-hound focuses on **data management**, not data analysis or collection.

---

## In Scope

### ✅ Intelligence Storage

**Entity Management**:
- ✅ Create, read, update, delete entities
- ✅ Flexible JSON schema with entity types
- ✅ Entity attribute storage (names, identifiers, profile data)
- ✅ Entity metadata (created_at, updated_at, confidence scores)
- ✅ Custom entity type definitions via schema configuration

**Entity Types**:
- ✅ **person** - Individual person
- ✅ **organization** - Company, corporation, business
- ✅ **government** - Government entity, agency, department
- ✅ **group** - Social group, religious organization, informal group
- ✅ **sock_puppet** - Fake identity for undercover investigations (law enforcement use)
- ✅ **location** - Physical location, address
- ✅ **unknown** - Entity type not yet determined
- ✅ **custom** - User-defined entity types

**Dynamic Entity Types (Phase 48 - PLANNED)**:
- ⏳ **platform** - Social media, marketplace, forum, or any online platform (e.g., Facebook, LinkedIn, eBay)

**NOT Entities (Dependent Data - Phase 48)**:
- ❌ **account** - Cannot exist without a Platform; modeled as HAS_ACCOUNT_ON relationship with properties
- ❌ **content** - Cannot exist without a Platform and Author; modeled as relationship properties or nested data

**Dynamic Relationship Types (Phase 48 - PLANNED)**:
- ⏳ **HAS_ACCOUNT_ON** - Edge linking Person/SockPuppet → Platform with properties (username, profile_url, password_ref, etc.)
- ⏳ **OWNS** - Edge linking Person/Org → Org/Platform/Location (ownership)
- ⏳ **CONTROLS** - Edge linking Person/Org → SockPuppet (operator relationship)

**Important**: Sock puppet entities are NOT real people - they are fictitious identities created by investigators for online investigations. They store profile data and credential references, but basset-hound does NOT generate or create sock puppet data.

**What Makes Something an Entity (Ontological Independence Test)**:

An **entity** in basset-hound is something that can **exist and be clearly defined without requiring a relationship to another entity**. An entity is where the "pipeline of influence" stops - it can stand alone.

> **The Primary Test**: "Can this thing exist and be clearly defined WITHOUT requiring ANY relationship to another entity?"

For the formal test framework with decision matrix and examples, see: [Ontological Independence Test](findings/ONTOLOGICAL-INDEPENDENCE-TEST-2026-01-14.md)

| Entity | Why It's an Entity |
|--------|-------------------|
| **Person** | Exists regardless of accounts, employers, or relationships |
| **Organization** | Exists even if no one works there and it owns nothing |
| **Platform** | "A platform can simply just be a platform" - exists without owners or users |
| **Location** | An address exists even if no one lives there |
| **Group** | Can exist with 0 members - "there can be 0 people in a group if all the people left" |
| **Government** | A government entity/agency exists independently of personnel or controlled organizations |
| **Sock Puppet** | A fictitious identity exists as a defined persona even without active accounts |

| NOT an Entity | Why NOT |
|---------------|---------|
| **Account** | Cannot exist without a Platform to host it (ontologically dependent) |
| **Content** | Cannot be defined without knowing which Platform hosts it (ontologically dependent) |

**Three Distinct Data Concepts**:

| Concept | Definition | Example |
|---------|------------|---------|
| **Ontologically Independent Entity** | Can exist and be defined without ANY relationship to another entity | Person, Platform, Location |
| **Ontologically Dependent Data** | *Inherently* cannot exist without another entity | Account (needs Platform), Content (needs Platform + Author) |
| **Orphan Data** | *Temporarily* unlinked data waiting to be attached to an entity | Scraped profile before entity linkage |

**Key Distinction**: Ontological dependence is an *inherent property* - an Account is ALWAYS dependent on a Platform (part of its definition). Orphan data is a *temporary state* - the data COULD be linked to an existing entity type, we just haven't made the connection yet.

**Dynamic Entity Architecture Philosophy (Phase 48)**:

basset-hound is evolving from hardcoded data schemas to a **dynamic, entity-driven architecture**:

1. **Platforms as Entities**: Instead of hardcoding 70+ social media platforms in YAML, platforms become first-class entities with configurable field schemas. Human operators add platforms as needed.

2. **Accounts as Relationships**: An account is the HAS_ACCOUNT_ON relationship between a Person and a Platform, with properties (username, profile_url, password_ref, etc.). Accounts are NOT entities because they cannot exist without a Platform.

3. **Platform-Specific Fields**: Each Platform entity defines its own field schema (username, profile_url, headline for LinkedIn, etc.), eliminating duplicate field definitions.

4. **On-Demand Configuration**: Human operators create "Other Platform" entities when they encounter new platforms, rather than waiting for config updates.

**Relationship Management**:
- ✅ Link entities with typed relationships (KNOWS, WORKS_FOR, LOCATED_IN, etc.)
- ✅ Relationship properties (since, until, confidence, strength)
- ✅ Bidirectional relationship queries
- ✅ Transitive relationship discovery (friends-of-friends)
- ✅ Path finding between entities

**Identifiers**:
- ✅ Store email, phone, crypto addresses, domains, IPs, URLs, usernames
- ✅ Link identifiers to entities
- ✅ Handle unlinked identifiers as "orphan data"
- ✅ Batch import of identifiers
- ✅ Identifier deduplication

### ✅ Investigation Management

**Investigations**:
- ✅ Create and manage investigation cases
- ✅ Investigation lifecycle (open, active, suspended, closed, archived)
- ✅ Investigation priorities (low, medium, high, critical)
- ✅ Investigation types (fraud, counter_intel, due_diligence, threat_actor, etc.)
- ✅ Investigation subjects (target, suspect, witness, associate, victim)

**Tasks & Activity Logging**:
- ✅ Create investigation tasks with status tracking
- ✅ Log investigation activity with timestamps
- ✅ Activity types (evidence_collected, interview_conducted, lead_discovered, etc.)
- ✅ Activity search and filtering

**Timeline & Progress**:
- ✅ Investigation timeline generation
- ✅ Progress tracking (entities added, relationships discovered, evidence collected)
- ✅ Investigation context for AI agents

### ✅ Sock Puppet Management

**What are Sock Puppets?**
Sock puppets are fictitious online personas used by law enforcement and OSINT investigators for undercover investigations. They are NOT real people - they are entities created to collect information without revealing the investigator's identity.

**Sock Puppet Identities (Storage Only)**:
- ✅ **Store** sock puppet profiles created by investigators
- ✅ Store alias names, backstory, target platforms
- ✅ Link sock puppets to investigations
- ✅ Platform-specific profile data (LinkedIn, Twitter, forums)
- ✅ Sock puppet activity logging (which sock puppet was used where)
- ❌ **DO NOT** generate sock puppet data (names, emails, passwords, etc.)
- ❌ **DO NOT** create fake identities automatically

**Credentials Reference (NOT Password Management)**:
- ✅ Store **references** to credentials (e.g., "stored in 1Password as 'puppet_linkedin_001'")
- ✅ Track credential rotation dates
- ✅ Store credential metadata (created_at, last_used, platforms)
- ❌ **DO NOT** store actual passwords or credentials in basset-hound
- ❌ **DO NOT** generate passwords
- ❌ **DO NOT** act as a password manager (use 1Password, Bitwarden, KeePass)

**Browser Integration**:
- ✅ Provide sock puppet profile data for form autofill (via MCP tools)
- ✅ Track sock puppet usage across investigations
- ✅ Allow investigators to select which sock puppet to use for login
- ❌ **DO NOT** automatically log in (human must review and click submit)

**Philosophy**: basset-hound is a **storage system** for sock puppet profiles created elsewhere. Investigators create fake identities using external tools or manual methods, then store the profile data in basset-hound for easy access during investigations.

### ✅ Orphan Data Management

**Important Distinction**: Orphan data is NOT the same as ontologically dependent data.

| Concept | Definition | In basset-hound |
|---------|------------|-----------------|
| **Orphan Data** | Data that *temporarily* lacks a link but COULD be linked to an existing entity type | OrphanData node (temporary storage) |
| **Ontologically Dependent Data** | Data that *inherently* cannot exist without another entity (part of its definition) | Relationship properties, NOT nodes |

**Key insight**: Orphan data is a *temporary state* - the data is waiting to be linked. Ontological dependence is an *inherent property* - an Account can NEVER exist without a Platform.

**Unlinked Identifiers**:
- ✅ Store identifiers not yet linked to entities ("orphan data")
- ✅ Batch import of orphan identifiers
- ✅ Link orphan data to entities when matches found
- ✅ Orphan data search and filtering
- ✅ Automatic linking suggestions based on similarity

**Use Case**: Collect email addresses from web pages → store as orphans → link to entities later

**Note**: Once orphan data is linked to an entity, it becomes properties ON that entity - it was never an entity itself, just data waiting to find its home.

### ✅ Provenance Tracking

**Data Sources**:
- ✅ Record data provenance (where information came from)
- ✅ Chain of custody for evidence
- ✅ Source reliability ratings
- ✅ Collection method tracking (web_scraping, public_record, social_media, etc.)

**Audit Trail**:
- ✅ Track who added/modified data
- ✅ Timestamp all changes
- ✅ Source attribution for every data point

### ✅ Evidence Storage

**Evidence Capture**:
- ✅ Store evidence submitted by basset-hound-browser
- ✅ Evidence types (screenshot, page_archive, network_har, dom_snapshot, etc.)
- ✅ SHA-256 hashing for integrity verification
- ✅ Chain of custody tracking
- ✅ Evidence metadata (URL, title, viewport, timestamp)

**Evidence Management**:
- ✅ Retrieve evidence by ID
- ✅ List evidence for investigation
- ✅ Verify evidence integrity (SHA-256 match)
- ✅ Link evidence to entities and investigations

### ✅ Basic Graph Queries

**Relationship Queries (NOT Analysis)**:
- ✅ Find paths between entities (shortest path, all paths)
- ✅ Degree centrality (count connections, who is most connected?)
- ✅ Community detection (basic clustering of related entities)
- ✅ Relationship strength scoring (based on edge properties)
- ✅ Neighborhood exploration (N-hop queries)
- ✅ Export graph for visualization (Gephi, Cytoscape)

**Important**: These are basic graph database queries, NOT advanced analysis:
- ❌ NO machine learning for community detection
- ❌ NO predictive link analysis
- ❌ NO behavioral pattern detection
- ❌ NO anomaly detection in networks
- ❌ NO graph embeddings or neural networks

**Data Export**:
- ✅ Export graph in standard formats (JSON, GraphML)
- ✅ Generate entity type schemas for UI rendering
- ✅ Subgraph extraction (entities within N hops)

### ✅ Search & Query

**Full-Text Search**:
- ✅ Search entities by name, identifier, attribute
- ✅ Search investigations by title, description
- ✅ Search orphan data by identifier value

**Structured Queries**:
- ✅ Filter entities by type, attribute, date range
- ✅ Filter relationships by type, strength, date range
- ✅ Cypher query support for advanced users

### ✅ Reports & Data Export

**IMPORTANT DISTINCTION**: basset-hound provides **data presentation** features, NOT intelligence analysis. Reports are generated from templates using stored data - no new insights are created.

**Template-Based Report Generation**:
- ✅ Entity profile reports (with relationships and activity)
- ✅ Investigation summary reports
- ✅ Relationship network reports
- ✅ Timeline reports
- ✅ Activity aggregation reports
- ❌ **NO** predictive analytics reports
- ❌ **NO** risk assessment reports
- ❌ **NO** behavioral analysis reports

**Philosophy**: Reports show "here's your data in a useful format," NOT "here's what your data means."

### ✅ Reporting

**Export & Programmatic Reporting**:
- ✅ Export of relationship data and entity profiles
- ✅ Programmatic report generation from graph data
- ✅ Bulk export features for external analysis tools

**NOT in Scope for Reporting**:
- ❌ AI-generated narrative reports (use external LLM tools)
- ❌ Data generation (basset-hound is storage, not generation)
- ❌ Automated insights or analysis summaries

**Future Enhancements**:
- ⏳ Report templates (BLUF format, executive summary, etc.)
- ⏳ Customizable report layouts
- ⏳ Scheduled report generation

**Data Visualization & Export**:
- ✅ Export relationship graphs as images (PNG, SVG)
- ✅ Export timelines as visualizations
- ✅ Graph rendering with layout algorithms (for display, not analysis)
- ✅ Node sizing based on connection count (for visualization)
- ✅ Bulk export features (ZIP files, JSON archives)
- ✅ API export endpoints for external tools

**Export Formats**:
- ✅ JSON (machine-readable)
- ✅ Markdown (human-readable)
- ✅ GraphML (graph export for Gephi, Cytoscape)
- ✅ CSV (tabular data)
- ✅ Images (PNG, SVG for visualizations)
- ✅ Future: PDF, HTML

**What This IS:**
```python
# ✅ EXAMPLE: Template-based report
def generate_entity_report(entity_id):
    """Generate report from template with entity data."""
    entity = get_entity(entity_id)
    relationships = get_relationships(entity_id)
    evidence = get_evidence(entity_id)

    # Fill template with stored data (NO NEW INSIGHTS)
    return render_template("entity_report.html",
                          entity=entity,
                          relationships=relationships,
                          evidence=evidence)
```

**What This is NOT:**
```python
# ❌ EXAMPLE: Predictive analysis
def generate_risk_report(entity_id):
    """Generate risk assessment report."""
    history = get_activity_history(entity_id)
    # ML model generates NEW INSIGHT (risk score)
    risk_score = ml_model.predict(history)
    # This creates new analytical data - OUT OF SCOPE
    return {"risk_score": risk_score}
```

### ✅ Projects

**Project Management**:
- ✅ Create projects as data isolation boundaries
- ✅ All entities belong to a project
- ✅ Project-level permissions (future)
- ✅ Project metadata (name, description, created_at)

### ✅ MCP Server

**AI Agent Interface**:
- ✅ 100 MCP tools for entity/relationship/investigation management
- ✅ FastMCP server on port 8000
- ✅ Tool discovery and documentation
- ✅ Async/await support for long-running operations

### ✅ Browser Integration

**Autofill Data**:
- ✅ Provide entity data in flattened format for form filling
- ✅ Suggest form field mappings to entity paths
- ✅ Provide sock puppet profile data for autofill

**Browser Session Tracking**:
- ✅ Register browser sessions
- ✅ Track session activity (pages visited, evidence captured)
- ✅ End sessions with summary

### ✅ Smart Suggestions & Data Matching (Phase 43 - COMPLETE)

**This is DATA MATCHING, NOT intelligence analysis.**

basset-hound suggests potential matches based on comparing data values (hashes, strings, fuzzy matching). This is fundamentally different from machine learning or advanced analysis.

**Data-Level Identity**:
- ✅ Every piece of data gets unique ID (data_abc123)
- ✅ Hash-based file identification (SHA-256)
- ✅ Images, documents, evidence files tracked independently
- ✅ Data can exist without being linked to entities

**Basic Data Matching (NOT ML)**:
- ✅ Exact hash matching (images, documents) - 1.0 confidence
- ✅ Exact string matching (email, phone, crypto) - 0.95 confidence
- ✅ Fuzzy matching (Jaro-Winkler, Levenshtein) - 0.3-0.9 confidence
- ✅ Partial matching (names, addresses) - 0.3-0.9 confidence
- ✅ Cross-entity duplicate detection
- ✅ Orphan data to entity matching

**What this is NOT:**
- ❌ NOT machine learning - just string/hash comparison algorithms
- ❌ NOT pattern detection - just data similarity scoring
- ❌ NOT predictive - just matching existing data
- ❌ NOT behavioral analysis - just comparing field values

**Suggestion System (Human-in-the-Loop)**:
- ✅ Show "Suggested Tags" section on entity profiles
- ✅ Suggest potential matches with confidence scores
- ✅ Human operator reviews and decides (view, link, dismiss)
- ✅ No automatic linking - always require human verification
- ✅ Dismissed suggestions hidden permanently
- ✅ Audit trail for all linking decisions

**Use Cases**:
- Same image appears in two entities → suggest possible duplicate (hash match)
- Same email in entity and orphan data → suggest linking (exact string match)
- Partial address match → suggest but flag as low confidence (fuzzy match)
- Same document hash → highlight potential relationship (hash match)
- Similar names with typos → suggest potential match (Levenshtein distance)

**Philosophy**: Assist human operators with data matching suggestions using simple algorithms (hash comparison, string similarity, fuzzy matching). This is NOT intelligence analysis - it's basic data comparison with confidence scoring. The human operator always makes the final decision.

---

## Scope Boundary: Data Management vs Analysis

### Core Philosophy

basset-hound is a **DATA STORAGE AND MANAGEMENT** system, NOT a data acquisition or intelligence analysis platform.

**The Three-Tier Model:**
```
┌─────────────────────────────────────────────────────────────────────┐
│  DATA ACQUISITION (OUT OF SCOPE)                                    │
│  - Web scraping, social media enumeration                           │
│  - OSINT automation, browser automation                             │
│  - → Use palletai, basset-hound-browser                             │
├─────────────────────────────────────────────────────────────────────┤
│  DATA MANAGEMENT (basset-hound - THIS PROJECT)                      │
│  - Storage: Entities, relationships, evidence, provenance           │
│  - Organization: Projects, investigations, timelines                │
│  - Matching: Hash/string comparison, fuzzy matching, suggestions    │
│  - Graph Analytics: Neo4j-native algorithms (OPTIONAL, TOGGLEABLE)  │
├─────────────────────────────────────────────────────────────────────┤
│  INTELLIGENCE ANALYSIS (OUT OF SCOPE)                               │
│  - ML models, predictive analytics, behavioral profiling            │
│  - Risk scoring, threat assessment, anomaly detection               │
│  - → Use future intelligence-analysis project                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

### ✅ IN SCOPE: Neo4j-Native Graph Analytics (Optional, Toggleable)

**Key Principle:** Features that run natively in Neo4j (no external ML libraries) ARE in scope, but should be:
- **Optional** - Can be disabled for resource-constrained environments
- **Background-friendly** - Can run asynchronously without blocking
- **Scalable** - Work on both laptops and industrial deployments

**Neo4j Graph Data Science (GDS) Features:**

| Feature | Type | Description | Resource Impact |
|---------|------|-------------|-----------------|
| **Path Finding** | Core | Shortest path, all paths between entities | Low |
| **Connected Components** | Core | Find isolated subgraphs | Low |
| **Degree Centrality** | Optional | Count connections per entity | Low |
| **PageRank** | Optional | Identify influential entities | Medium |
| **Community Detection** | Optional | Louvain/Label Propagation clustering | Medium-High |
| **Betweenness Centrality** | Optional | Find bridge/broker entities | High |
| **Similarity Metrics** | Optional | Jaccard, Cosine, Node Similarity | Medium |

**Implementation Requirements:**
```yaml
# Feature flags in config
graph_analytics:
  enabled: true              # Master toggle
  background_processing: true # Run expensive queries async
  features:
    path_finding: true       # Always on (core feature)
    connected_components: true
    degree_centrality: true
    pagerank: false          # Disabled by default
    community_detection: false
    betweenness_centrality: false
```

**Why Neo4j-Native Analytics are IN SCOPE:**
- These algorithms run **inside Neo4j** - no external dependencies
- They're mathematical/deterministic, not machine learning
- They answer "what exists in my data" not "what does it mean"
- Neo4j GDS is already a dependency for graph operations
- Results are facts about the graph, not predictions

---

### ❌ OUT OF SCOPE: ML Training and Intelligence Analysis

**Critical Clarification: basset-hound is NOT an ML framework.**

basset-hound is a **data storage and relationship management** system. It does NOT:
- Train machine learning models
- Require ML model weights or training data
- Include any ML training infrastructure
- Provide model inference pipelines

**ML Training Integration Pattern (for external projects):**

If you need ML capabilities, use basset-hound as a **data source** for your ML training project:

```
┌─────────────────────────────────────────────────────────────────────┐
│  YOUR ML TRAINING PROJECT (External)                                │
│  - Your ML framework (PyTorch, TensorFlow, scikit-learn)           │
│  - Your training pipeline                                           │
│  - Your model weights and checkpoints                               │
│                                                                     │
│  ┌─────────────────┐     ┌─────────────────┐                       │
│  │ Training Script │────>│ basset-hound    │  (read-only API)      │
│  │                 │<────│ REST API        │                       │
│  └─────────────────┘     └─────────────────┘                       │
│         │                                                           │
│         v                                                           │
│  ┌─────────────────┐                                               │
│  │ Trained Model   │  ← Your project owns the model                │
│  └─────────────────┘                                               │
└─────────────────────────────────────────────────────────────────────┘
```

**Example: Using basset-hound data for ML training (external project):**
```python
# In your ML training project (NOT in basset-hound)
import requests
from your_ml_framework import Model, train

# Fetch training data from basset-hound API
response = requests.get("http://basset-hound/api/v1/entities?project=investigation_1")
entities = response.json()

# Your training logic
model = Model()
train(model, entities)  # Your responsibility
model.save("my_trained_model.pt")  # Your project owns this
```

**What basset-hound does NOT do:**

| Category | Examples | Why Out of Scope |
|----------|----------|------------------|
| **ML Training** | Model training, fine-tuning, transfer learning | basset-hound is storage, not a training framework |
| **Model Inference** | Running predictions, classification | Use external inference services |
| **Model Storage** | Saving model weights, checkpoints | Use MLflow, Weights & Biases, or filesystem |
| **Training Data Management** | Dataset versioning, splits, augmentation | Use DVC, Hugging Face Datasets, or similar |
| **Predictive Analytics** | Forecasting, probability prediction | Generates insights, not data management |
| **Behavioral Analysis** | Profiling, pattern detection, anomaly scoring | Interpretive, not factual |
| **NLP/Image/Audio** | Sentiment, facial recognition, voice ID | External models, significant compute |

**Archived Services (for future intelligence-analysis project):**
- `ml_analytics_service.py` - TF-IDF query suggestions, search patterns
- `temporal_patterns.py` - Burst detection, trend analysis
- `influence_service.py` - Influence propagation simulation
- See `/archive/out-of-scope-ml/` for migration notes

**Suggested Integration: basset-hound + ML Project**

If ML training IS required for your workflow:
1. Create a separate `intelligence-analysis` project
2. Use basset-hound REST API to fetch training data
3. Train models in your ML project
4. Optionally store analysis results back to basset-hound via API

---

### Clear Examples

**IN SCOPE (Data Management + Neo4j Analytics):**
```python
# ✅ "Which entities have the most connections?" (Degree Centrality)
result = neo4j.run("MATCH (e:Person)-[r]-() RETURN e, count(r) ORDER BY count(r) DESC")

# ✅ "Find communities of connected entities" (Neo4j GDS Louvain)
CALL gds.louvain.stream('myGraph') YIELD nodeId, communityId

# ✅ "What's the shortest path between Entity A and Entity B?"
MATCH path = shortestPath((a:Person)-[*]-(b:Person))

# ✅ "These two entities share the same email - suggest a link"
# (Hash/string comparison with confidence score)
```

**OUT OF SCOPE (Intelligence Analysis):**
```python
# ❌ "Predict which entities are likely to be connected in the future"
model.predict_link(entity_a, entity_b)  # ML prediction

# ❌ "This entity's behavior is anomalous based on historical patterns"
anomaly_score = ml_model.detect_anomaly(entity)  # Behavioral profiling

# ❌ "Generate a risk score for this entity"
risk = threat_model.score(entity)  # Subjective assessment

# ❌ "What topics are trending in the investigation?"
trends = nlp_model.extract_trends(text_corpus)  # NLP analysis
```

---

### Hardware Scalability

basset-hound is designed to work on:

| Environment | Configuration | Features Available |
|-------------|--------------|-------------------|
| **Laptop** (8GB RAM) | `graph_analytics.enabled: false` | Storage, matching, basic queries |
| **Workstation** (32GB) | Default config | All core + optional analytics |
| **Server** (64GB+) | Full config, workers | All features, background processing |
| **Industrial** (Cluster) | Neo4j cluster | All features, horizontal scaling |

**Resource Management:**
- Expensive queries run in background workers (Celery/ARQ)
- Results cached to avoid recomputation
- Feature flags disable heavy operations on limited hardware
- API rate limiting prevents resource exhaustion

---

### Integration Architecture

**basset-hound Integrations:**

1. **basset-verify** (existing):
   - Identifier validation (email, phone, crypto)
   - basset-hound calls on-demand (optional)

2. **basset-hound-browser** (existing):
   - Evidence capture, session tracking
   - Browser → basset-hound data flow

3. **intelligence-analysis** (future, OUT OF SCOPE):
   - ML-based analysis, predictions, insights
   - Consumes data FROM basset-hound
   - Stores results BACK to basset-hound
   - Separate deployment, separate resources

---

### ❌ OSINT Automation

- ❌ Web scraping (use palletai agents + basset-hound-browser)
- ❌ Social media enumeration (use palletai agents)
- ❌ Username checking across platforms (use palletai agents)
- ❌ Automated data collection (use palletai agents)
- ❌ Scheduled scraping jobs (use palletai agents)

**Reason**: basset-hound is **intelligence management**, not OSINT automation. AI agents (palletai) perform tool automation and data collection. basset-hound stores the results.

### ❌ Identifier Verification

- ❌ Email verification (use basset-verify)
- ❌ Phone verification (use basset-verify)
- ❌ Crypto address detection (use basset-verify)
- ❌ Domain DNS lookups (use basset-verify)
- ❌ IP geolocation (use basset-verify - future)

**Reason**: Verification is a separate concern. basset-verify is a standalone microservice that basset-hound calls **optionally** when user clicks "Verify" button. basset-hound must work even if basset-verify is down (graceful degradation).

### ❌ Browser Automation

- ❌ Page navigation (use basset-hound-browser)
- ❌ Evidence capture (use basset-hound-browser)
- ❌ Form filling (use basset-hound-browser)
- ❌ Screenshot capture (use basset-hound-browser)
- ❌ Session management (use basset-hound-browser)
- ❌ Tor integration (use basset-hound-browser)

**Reason**: basset-hound-browser handles browser automation. basset-hound stores evidence submitted by the browser.

### ❌ AI Agent Orchestration

- ❌ Agent spawning (use palletai)
- ❌ Task planning (use palletai)
- ❌ Multi-agent coordination (use palletai)
- ❌ Tool automation (use palletai)
- ❌ Workflow execution (use palletai)

**Reason**: palletai handles AI agent orchestration. basset-hound provides the MCP server for agents to interact with.

### ❌ Real-Time Monitoring

- ❌ Social media monitoring
- ❌ Alert generation
- ❌ Notification systems
- ❌ Threat intelligence feeds

**Reason**: basset-hound is for **investigation management**, not real-time monitoring.

### ❌ Active Reconnaissance

- ❌ Port scanning
- ❌ Service fingerprinting
- ❌ Banner grabbing
- ❌ Vulnerability scanning
- ❌ Password cracking
- ❌ Exploit execution

**Reason**: basset-hound manages **collected intelligence**, it does not perform active reconnaissance.

### ❌ Credential Management

- ❌ Password storage (use 1Password, Bitwarden, KeePass)
- ❌ Credential encryption (use external vault)
- ❌ Credential rotation automation (use external vault)

**Reason**: Sock puppets store **references** to credentials ("stored in 1Password as 'puppet_001'"), not actual passwords. Specialized tools handle credential management better than basset-hound.

### ❌ Data Generation

**basset-hound is a STORAGE system, NOT a data generator**:

- ❌ Generate sock puppet identities (names, emails, addresses, etc.)
- ❌ Generate fake data for investigations
- ❌ Generate passwords or credentials
- ❌ Generate social media profiles
- ❌ Generate backstories automatically
- ❌ AI-generated entity attributes

**Exception**: Report Generation ONLY
- ✅ Generate reports from stored data (investigation summaries, timelines, etc.)
- ✅ Users can choose to store generated reports back in the system

**Reason**: basset-hound stores and manages intelligence collected by investigators. External tools or human operators create/collect data, then store it in basset-hound. This prevents scope creep and maintains focus on intelligence management.

**Data Flow**:
```
External Tool/Human → Creates sock puppet identity
          ↓
   Investigator → Stores profile in basset-hound
          ↓
   basset-hound → Stores and relates data
          ↓
   Browser Extension → Uses stored data for autofill
```

---

## Integration Architecture

### basset-hound ↔ basset-verify

**basset-hound calls basset-verify**:
- When user clicks "Verify" button on entity page
- For manual verification of specific identifiers
- For batch verification of orphan data (user-initiated)

**basset-hound stores results**:
- Verification status (verified, unverified, invalid)
- Confidence score (0.0 - 1.0)
- Verification timestamp
- Verification level (format, network)

**Graceful degradation**:
```python
try:
    result = await basset_verify_client.verify_email(email)
except ConnectionError:
    return {"status": "verification_unavailable"}
```

### basset-hound ↔ basset-hound-browser

**basset-hound-browser submits evidence**:
- Screenshots, page archives, network HAR, DOM snapshots
- SHA-256 hashes for integrity verification
- Metadata (URL, title, viewport, timestamp)

**basset-hound provides context**:
- Investigation details for browser decisions
- Sock puppet profiles for form autofill
- Known entities to highlight on page

**basset-hound tracks sessions**:
- Register browser sessions
- Track activity counters
- End sessions with summary

### basset-hound ↔ palletai

**AI agents use basset-hound**:
- Store collected intelligence via MCP tools
- Query entities and relationships
- Create investigation tasks
- Log activity

**basset-hound provides**:
- 100 MCP tools for intelligence management
- Investigation context for decision-making
- Entity/relationship graph for analysis

**AI agents perform automation**:
- Web scraping (palletai agents)
- Social media enumeration (palletai agents)
- Data collection (palletai agents)
- Tool orchestration (palletai agents)

### basset-hound ↔ autofill-extension

**Extension requests autofill data**:
- Flattened entity data for form filling
- Sock puppet profile data
- Form field mapping suggestions

**Extension submits collected data**:
- Identifiers extracted from forms
- Evidence captured from pages (via basset-hound-browser)

---

## Data Model

### Core Entities

**Entity Node**:
```cypher
(:Entity {
    id: string,
    project_id: string,
    entity_type: string,  // person, organization, location, etc.
    name: string,
    attributes: json,
    confidence: float,
    created_at: datetime,
    updated_at: datetime
})
```

**Relationship**:
```cypher
(:Entity)-[:RELATIONSHIP_TYPE {
    since: date,
    until: date,
    strength: float,
    confidence: float,
    properties: json
}]->(:Entity)
```

**Orphan Data**:
```cypher
(:OrphanIdentifier {
    id: string,
    project_id: string,
    identifier_type: string,
    identifier_value: string,
    source: string,
    collected_at: datetime
})
```

**Investigation**:
```cypher
(:Investigation {
    id: string,
    project_id: string,
    title: string,
    investigation_type: string,
    status: string,
    priority: string,
    opened_at: datetime,
    closed_at: datetime
})
```

**Sock Puppet**:
```cypher
(:SockPuppet {
    id: string,
    project_id: string,
    alias_name: string,
    entity_id: string,  // Link to entity
    platforms: json,
    credentials_ref: string,  // Reference to external vault
    created_at: datetime
})
```

---

## Technology Stack

### Core
- **Language**: Python 3.11+
- **Database**: Neo4j 5.x (graph database)
- **API**: FastAPI (REST API)
- **MCP**: FastMCP (Model Context Protocol server)

### Libraries
- py2neo (Neo4j driver)
- pydantic (data validation)
- httpx (async HTTP client for basset-verify integration)

### Deployment
- Docker container
- Docker Compose with Neo4j
- Optional Kubernetes deployment

---

## Performance Requirements

- **Entity creation**: < 100ms
- **Relationship queries**: < 500ms (with proper indexing)
- **Full-text search**: < 1s
- **Graph analysis**: < 5s for subgraphs up to 1000 nodes
- **Concurrent requests**: 100+ requests/second
- **Database size**: Support 100,000+ entities

---

## Security Requirements

- ✅ No plaintext password storage
- ✅ No automatic verification (prevents alerting threat actors)
- ✅ Project-level data isolation
- ✅ Audit logging for all data changes
- ✅ Chain of custody for evidence
- ✅ SHA-256 integrity verification
- ✅ TLS/HTTPS for all external connections

---

## Testing Requirements

- ✅ Unit tests for all MCP tools (>90% coverage)
- ✅ Integration tests with Neo4j
- ✅ API endpoint tests
- ✅ Graph query tests
- ✅ Evidence integrity tests
- ✅ Graceful degradation tests (when basset-verify is down)

---

## Documentation Requirements

- ✅ README with installation instructions
- ✅ SCOPE.md (this document)
- ✅ ROADMAP.md with development phases
- ✅ MCP tool documentation (auto-generated)
- ✅ Integration guides for external tools
- ✅ Schema configuration guide
- ✅ Findings documents for each phase

---

## Versioning & Stability

### API Stability Promise

basset-hound follows semantic versioning (MAJOR.MINOR.PATCH):

- **MAJOR**: Breaking schema or API changes
- **MINOR**: New MCP tools, backward compatible
- **PATCH**: Bug fixes

### Schema Migration

- Schema changes must be backward compatible
- Migration scripts provided for breaking changes
- Neo4j constraints and indexes maintained

---

## Success Criteria

basset-hound is successful if:

1. ✅ Intelligence is stored in a flexible, queryable structure
2. ✅ AI agents can easily interact via MCP tools
3. ✅ Investigators can manage investigations effectively
4. ✅ Relationships are discoverable and analyzable
5. ✅ Evidence has verified chain of custody
6. ✅ Sock puppets enable undercover investigations
7. ✅ System degrades gracefully when dependencies fail
8. ✅ No automatic operations alert threat actors

---

## Non-Goals

- **Not an OSINT automation platform** (use palletai)
- **Not a verification service** (use basset-verify)
- **Not a browser automation tool** (use basset-hound-browser)
- **Not a threat intelligence platform**
- **Not a real-time monitoring system**
- **Not a credential manager** (use 1Password, etc.)
- **Not a social media scraper**
- **Not an active reconnaissance tool**

basset-hound does **one thing well**: manage intelligence in highly configurable ways.

---

## Feature Removal (Post-Phase 41 Clarification)

The following features were **removed from basset-hound scope** and migrated to appropriate repositories:

### Migrated to basset-verify
- ❌ `verify_identifier` tool → basset-verify
- ❌ `verify_email` tool → basset-verify
- ❌ `verify_phone` tool → basset-verify
- ❌ `verify_crypto` tool → basset-verify
- ❌ `verify_domain` tool → basset-verify
- ❌ `verify_ip` tool → basset-verify
- ❌ `verify_url` tool → basset-verify
- ❌ `verify_username` tool → basset-verify
- ❌ `batch_verify` tool → basset-verify
- ❌ `get_supported_cryptocurrencies` tool → basset-verify
- ❌ `get_all_crypto_matches` tool → basset-verify
- ❌ `get_verification_types` tool → basset-verify

**Total tools removed**: 12 (Phase 40.5)
**New tool count**: 112 → 100 tools

---

## Review Schedule

This scope document should be reviewed:

- **Quarterly**: Ensure scope remains focused on intelligence management
- **Before major releases**: Confirm no scope creep
- **When adding new features**: Verify alignment with core mission

**Last Review**: 2026-01-09 (Post-Phase 41 Clarification)
**Next Review**: 2026-04-09
