# Architecture Integration: Three-Project System

## Overview

This document describes the architecture of the basset-hound ecosystem, consisting of three distinct projects working together to provide comprehensive intelligence management and analysis capabilities.

## System Architecture

### The Three Projects

```
┌─────────────────────────────────────────────────────────────────┐
│                   Intelligence Ecosystem                        │
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌────────────────┐ │
│  │ basset-hound    │  │ basset-verify   │  │ intelligence-  │ │
│  │                 │  │                 │  │ analysis       │ │
│  │ Storage &       │  │ Verification    │  │                │ │
│  │ Management      │  │ Service         │  │ (Future)       │ │
│  └─────────────────┘  └─────────────────┘  └────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Project 1: basset-hound (Intelligence Storage & Management)

### Purpose
Data backbone for intelligence operations. The single source of truth for all entity data, relationships, and evidence.

### Core Responsibilities
- **Entity Management**: Store and manage entities (people, organizations, addresses, etc.)
- **Relationship Management**: Track connections between entities with typed relationships
- **Identifier Storage**: Store and index identifiers (email, phone, crypto addresses, etc.)
- **Basic Data Matching**: Fuzzy string comparison for duplicate detection
- **Confidence Scoring**: Provide confidence scores for suggested matches
- **CRUD Operations**: Full create, read, update, delete functionality
- **Search & Filtering**: Query entities by type, properties, relationships
- **Evidence Storage**: Store supporting documents, screenshots, metadata
- **Project Management**: Organize investigations into discrete projects
- **MCP Server**: Expose functionality via Model Context Protocol

### Technology Stack
- **Database**: Neo4j (graph database)
- **Backend**: FastAPI (Python)
- **API Layer**: MCP Server
- **Frontend**: React (planned)

### What basset-hound Does NOT Do
- No machine learning or AI analysis
- No predictive analytics
- No pattern detection algorithms
- No risk scoring or threat assessment
- No automatic data collection or OSINT
- No complex behavioral analysis
- No report generation or analytical insights

### Key Design Principle
basset-hound is deliberately simple and focused. It's a robust storage layer, not an analytical engine.

## Project 2: basset-verify (Identifier Verification)

### Purpose
Dedicated microservice for validating identifiers through technical checks and network-level verification.

### Core Responsibilities
- **Email Verification**: Format validation, MX record checks, SMTP validation
- **Phone Verification**: Format validation, carrier lookup, number type detection
- **Crypto Address Verification**: Format validation, checksum validation, network checks
- **Network-Level Validation**: DNS checks, API calls to validation services
- **Manual Verification**: User-initiated verification workflows
- **Verification History**: Track verification attempts and results

### Technology Stack
- **Backend**: FastAPI (Python)
- **API Layer**: MCP Server
- **Validation Libraries**: email-validator, phonenumbers, web3

### What basset-verify Does NOT Do
- No automatic/background verification
- No OSINT collection
- No social media scraping
- No data analysis
- No entity storage (delegates to basset-hound)

### Integration with basset-hound
```python
# User triggers verification in basset-hound
# basset-hound calls basset-verify MCP server
verification_result = await verify_mcp.call("verify_email", {
    "email": "user@example.com"
})

# basset-hound stores verification result
await basset_mcp.call("update_identifier", {
    "identifier_id": "id_123",
    "verification_status": verification_result["status"],
    "verification_timestamp": verification_result["timestamp"]
})
```

## Project 3: intelligence-analysis (Future - Intelligence Analysis)

### Purpose
Advanced analytical capabilities using AI, machine learning, and specialized algorithms to generate intelligence insights.

### Core Responsibilities
- **OSINT Analysis**: AI agents perform open-source intelligence collection and analysis
- **Pattern Detection**: Identify communication patterns, behavioral patterns, network clusters
- **Correlation Analysis**: Find connections between seemingly unrelated entities
- **Behavioral Analysis**: Analyze entity behaviors over time
- **Risk Scoring**: Calculate risk levels based on multiple factors
- **Threat Assessment**: Evaluate potential threats and vulnerabilities
- **Predictive Analytics**: Forecast likely future actions or events
- **Anomaly Detection**: Identify unusual patterns or outliers
- **Machine Learning Models**: Train and deploy ML models for classification, clustering
- **Natural Language Processing**: Extract insights from text data
- **Report Generation**: Create analytical reports, visualizations, summaries
- **Trend Analysis**: Identify trends across entities and time periods

### Planned Technology Stack
- **Language**: Python
- **ML Frameworks**: scikit-learn, TensorFlow/PyTorch
- **LLM Integration**: OpenAI API, Anthropic API, local models
- **NLP**: spaCy, NLTK, transformers
- **Data Analysis**: pandas, numpy
- **Visualization**: matplotlib, plotly
- **Graph Analytics**: NetworkX
- **MCP Client**: Integrates with basset-hound MCP server

### What intelligence-analysis Does NOT Do
- No data storage (delegates to basset-hound)
- No entity CRUD operations
- No relationship management
- No project management
- No user authentication (relies on basset-hound)

### Key Design Principle
intelligence-analysis is compute-intensive and specialized. It reads from basset-hound, performs complex analysis, and writes results back.

## Data Flow Architecture

### Complete System Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                      AI Agent (palletai)                        │
│  - Human-directed OSINT collection                              │
│  - Social media research                                        │
│  - Web scraping                                                 │
│  - Document analysis                                            │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ Stores raw collected data
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                        basset-hound                             │
│  - Stores entities (people, organizations, etc.)                │
│  - Stores relationships (knows, works_for, etc.)                │
│  - Stores identifiers (email, phone, crypto)                    │
│  - Basic fuzzy matching for duplicates                          │
│  - Suggests possible matches with confidence scores             │
│  - Stores evidence (documents, screenshots)                     │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ Reads entity/relationship data
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                  intelligence-analysis (future)                 │
│  - AI agent analyzes entity relationships                       │
│  - Detects communication patterns                               │
│  - Identifies network clusters                                  │
│  - Calculates risk scores                                       │
│  - Generates predictive insights                                │
│  - Creates analytical reports                                   │
│  - Produces visualizations                                      │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ Stores analytical reports
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                        basset-hound                             │
│  - Stores reports as entities (type: "report")                  │
│  - Links reports to analyzed entities                           │
│  - Human analyst reviews reports in UI                          │
│  - Analyst makes decisions based on analysis                    │
│  - Analyst updates entities with new findings                   │
└─────────────────────────────────────────────────────────────────┘
                             │
                             │ Human decisions trigger
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                  intelligence-analysis (future)                 │
│  - New analysis based on human feedback                         │
│  - Refined models based on human decisions                      │
│  - Iterative improvement cycle                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Verification Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                      Human Analyst                              │
│  - Reviews entity identifier                                    │
│  - Clicks "Verify" button in UI                                 │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ Triggers verification
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                        basset-hound                             │
│  - Receives verification request                                │
│  - Calls basset-verify MCP server                               │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ MCP call: verify_email/phone/crypto
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                       basset-verify                             │
│  - Validates format                                             │
│  - Checks MX records (email)                                    │
│  - Validates checksum (crypto)                                  │
│  - Performs network-level checks                                │
│  - Returns verification result                                  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ Returns result
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                        basset-hound                             │
│  - Stores verification result                                   │
│  - Updates identifier status                                    │
│  - Displays result to human                                     │
└─────────────────────────────────────────────────────────────────┘
```

## Integration Patterns

### Pattern 1: Analysis Agent Reads Entity Data

The intelligence-analysis project needs to read data from basset-hound to perform analysis.

```python
# intelligence-analysis/agents/pattern_detector.py
from basset_hound_client import BassetHoundMCP

async def analyze_entity_patterns(entity_id: str):
    """
    Analyze patterns for a specific entity by reading
    all related data from basset-hound.
    """
    # Initialize MCP client
    mcp = BassetHoundMCP()

    # Read entity data
    entity_data = await mcp.call("get_entity", {
        "entity_id": entity_id
    })

    # Get all relationships
    relationships = await mcp.call("get_entity_relationships", {
        "entity_id": entity_id
    })

    # Get related entities for context
    related_entities = []
    for rel in relationships:
        related_id = rel["target_id"] if rel["source_id"] == entity_id else rel["source_id"]
        related_entity = await mcp.call("get_entity", {
            "entity_id": related_id
        })
        related_entities.append(related_entity)

    # Perform pattern analysis (ML algorithms, graph analysis, etc.)
    patterns = detect_communication_patterns(entity_data, relationships, related_entities)
    clusters = identify_network_clusters(relationships)
    anomalies = detect_anomalies(entity_data, relationships)

    # Return analysis result
    return {
        "entity_id": entity_id,
        "patterns": patterns,
        "clusters": clusters,
        "anomalies": anomalies,
        "analysis_timestamp": datetime.now().isoformat()
    }
```

### Pattern 2: Analysis Agent Generates and Stores Report

After performing analysis, intelligence-analysis stores the report in basset-hound.

```python
# intelligence-analysis/agents/report_generator.py
from basset_hound_client import BassetHoundMCP

async def generate_threat_assessment(entity_id: str, project_id: str):
    """
    Generate a threat assessment report and store it in basset-hound.
    """
    mcp = BassetHoundMCP()

    # Perform comprehensive analysis
    patterns = await analyze_entity_patterns(entity_id)
    risk_score = await calculate_risk_score(entity_id)
    predictions = await generate_predictions(entity_id)

    # Generate analytical report
    report = {
        "type": "threat_assessment",
        "analyzed_entity_id": entity_id,
        "risk_level": "HIGH" if risk_score > 0.7 else "MEDIUM" if risk_score > 0.4 else "LOW",
        "risk_score": risk_score,
        "patterns_detected": patterns["patterns"],
        "network_clusters": patterns["clusters"],
        "anomalies": patterns["anomalies"],
        "predictions": predictions,
        "recommendations": generate_recommendations(risk_score, patterns),
        "analysis_method": "ML-based pattern detection with graph analytics",
        "confidence": 0.85,
        "generated_at": datetime.now().isoformat(),
        "generated_by": "intelligence-analysis v1.0"
    }

    # Store report as an entity in basset-hound
    report_entity = await mcp.call("create_entity", {
        "project_id": project_id,
        "type": "report",
        "profile": {
            "name": f"Threat Assessment: {entity_id}",
            "report_type": "threat_assessment",
            "content": report
        }
    })

    # Link report to analyzed entity
    await mcp.call("create_relationship", {
        "project_id": project_id,
        "source_id": report_entity["id"],
        "target_id": entity_id,
        "type": "ANALYZES",
        "properties": {
            "analysis_date": datetime.now().isoformat(),
            "report_version": "1.0"
        }
    })

    return report_entity
```

### Pattern 3: Human Reviews Analysis in basset-hound UI

Users interact with analysis results through the basset-hound interface.

```python
# basset-hound/frontend/components/EntityView.jsx
function EntityView({ entityId }) {
    const [entity, setEntity] = useState(null);
    const [reports, setReports] = useState([]);

    useEffect(() => {
        // Load entity data
        loadEntity(entityId);

        // Load linked analytical reports
        loadAnalyticalReports(entityId);
    }, [entityId]);

    async function loadAnalyticalReports(entityId) {
        // Query for reports that analyze this entity
        const relationships = await bassetAPI.getRelationships({
            target_id: entityId,
            type: "ANALYZES"
        });

        // Load each report entity
        const reportPromises = relationships.map(rel =>
            bassetAPI.getEntity(rel.source_id)
        );
        const reports = await Promise.all(reportPromises);

        setReports(reports.filter(r => r.type === "report"));
    }

    return (
        <div className="entity-view">
            <EntityDetails entity={entity} />

            {reports.length > 0 && (
                <div className="analytical-reports">
                    <h3>Intelligence Analysis</h3>
                    {reports.map(report => (
                        <ReportCard
                            key={report.id}
                            report={report}
                            onViewDetails={() => viewReportDetails(report)}
                        />
                    ))}
                </div>
            )}
        </div>
    );
}
```

### Pattern 4: Continuous Analysis Loop

intelligence-analysis can monitor entities and trigger analysis when conditions are met.

```python
# intelligence-analysis/agents/continuous_monitor.py
from basset_hound_client import BassetHoundMCP
import asyncio

async def continuous_monitoring_loop(project_id: str):
    """
    Continuously monitor entities and trigger analysis
    when significant changes are detected.
    """
    mcp = BassetHoundMCP()

    while True:
        # Get entities that need analysis
        entities = await mcp.call("search_entities", {
            "project_id": project_id,
            "filter": {
                "needs_analysis": True
            }
        })

        for entity in entities:
            # Check if entity has changed significantly since last analysis
            last_analysis = await get_last_analysis_date(entity["id"])
            if should_analyze(entity, last_analysis):
                # Trigger analysis
                await generate_threat_assessment(entity["id"], project_id)

                # Mark entity as analyzed
                await mcp.call("update_entity", {
                    "entity_id": entity["id"],
                    "profile": {
                        "last_analyzed": datetime.now().isoformat(),
                        "needs_analysis": False
                    }
                })

        # Wait before next iteration
        await asyncio.sleep(3600)  # Check every hour
```

## Use Cases

### Use Case 1: Communication Pattern Detection

**Scenario**: Analyst wants to understand communication patterns between entities.

**Flow**:

1. **Data Collection (palletai)**
   - Human analyst uses AI agent to collect data on Entity A and Entity B
   - palletai stores entities and relationships in basset-hound

2. **Pattern Detection (intelligence-analysis)**
   - Analyst triggers pattern analysis for Entity A
   - intelligence-analysis reads all relationships for Entity A
   - ML algorithm detects frequent communication with Entity B
   - Identifies communication frequency, timing patterns, channels used
   - Generates "Communication Pattern Report"

3. **Report Storage (basset-hound)**
   - intelligence-analysis stores report as entity in basset-hound
   - Links report to Entity A and Entity B with ANALYZES relationship
   - Stores confidence score, timestamps, analysis methods

4. **Human Review (basset-hound UI)**
   - Analyst views Entity A in basset-hound UI
   - UI displays linked "Communication Pattern Report"
   - Analyst reviews patterns, decides relationship is significant
   - Analyst updates Entity A profile with new insights
   - Analyst creates additional relationships based on findings

**Code Example**:

```python
# intelligence-analysis detects pattern
pattern_report = {
    "type": "communication_pattern",
    "entities": ["ent_123", "ent_456"],
    "pattern": "frequent_communication",
    "frequency": "5-10 interactions per week",
    "channels": ["email", "messaging_app"],
    "timing_pattern": "primarily weekday evenings",
    "duration": "6 months",
    "confidence": 0.92
}

# Store in basset-hound
report_id = await store_analysis_report(pattern_report)
```

### Use Case 2: Risk Assessment

**Scenario**: Analyst needs to prioritize investigations based on threat level.

**Flow**:

1. **Data Accumulation (basset-hound)**
   - Over time, many entities and relationships are stored
   - Each entity has identifiers, connections, evidence

2. **Risk Analysis (intelligence-analysis)**
   - Analyst triggers batch risk assessment
   - intelligence-analysis analyzes each entity:
     - Number and type of connections
     - Identifiers (crypto addresses, offshore accounts, etc.)
     - Relationship to known high-risk entities
     - Behavioral patterns
     - Historical actions
   - ML model calculates risk score (0.0 - 1.0)
   - Classifies as LOW, MEDIUM, HIGH, CRITICAL

3. **Report Generation (intelligence-analysis)**
   - Generates "Risk Assessment Report" for each entity
   - Includes risk factors, contributing elements, recommendations
   - Stores reports in basset-hound

4. **Prioritization (basset-hound UI)**
   - Analyst views dashboard sorted by risk score
   - High-risk entities appear at top
   - Analyst focuses investigation resources on highest risks
   - Analyst drills down into risk factors for each entity

**Code Example**:

```python
# intelligence-analysis calculates risk
risk_factors = {
    "connection_to_known_threats": 0.8,
    "suspicious_financial_activity": 0.6,
    "use_of_anonymization_tools": 0.7,
    "geographic_risk_indicators": 0.4,
    "behavioral_anomalies": 0.5
}

risk_score = calculate_weighted_risk(risk_factors)  # 0.62

risk_report = {
    "type": "risk_assessment",
    "entity_id": "ent_789",
    "risk_level": "HIGH",
    "risk_score": 0.62,
    "risk_factors": risk_factors,
    "recommendations": [
        "Immediate investigation recommended",
        "Monitor financial transactions",
        "Review all known associates"
    ]
}
```

### Use Case 3: Predictive Analysis

**Scenario**: Analyst wants to anticipate future actions or events.

**Flow**:

1. **Historical Data (basset-hound)**
   - basset-hound contains historical entity behaviors
   - Relationships show how entities evolved over time
   - Evidence provides context for past actions

2. **Prediction (intelligence-analysis)**
   - Analyst requests predictive analysis for Entity C
   - intelligence-analysis analyzes historical patterns
   - ML model trained on similar entities
   - Generates predictions:
     - "Likely to establish new relationship with Entity D (70% confidence)"
     - "May relocate to Country X within 3 months (60% confidence)"
     - "Probable increase in financial activity (75% confidence)"

3. **Report Storage (basset-hound)**
   - Stores "Predictive Analysis Report"
   - Links to Entity C
   - Includes confidence levels, timeframes, reasoning

4. **Investigation Guidance (Human)**
   - Analyst uses predictions to guide investigation
   - Sets up monitoring for predicted activities
   - Allocates resources proactively
   - Validates predictions over time

5. **Model Refinement (intelligence-analysis)**
   - As predictions prove true/false, models are refined
   - Human feedback improves future predictions
   - Continuous learning loop

**Code Example**:

```python
# intelligence-analysis generates predictions
predictions = [
    {
        "prediction": "New relationship with Entity D",
        "confidence": 0.70,
        "timeframe": "within 30 days",
        "reasoning": "Historical pattern shows Entity C forms new relationships after similar events",
        "indicators_to_monitor": ["communication with Entity D", "shared locations"]
    },
    {
        "prediction": "Relocation to Country X",
        "confidence": 0.60,
        "timeframe": "within 90 days",
        "reasoning": "Entity C has shown increased interest in Country X (5 searches, 2 property inquiries)",
        "indicators_to_monitor": ["visa applications", "property purchases", "job searches"]
    }
]

predictive_report = {
    "type": "predictive_analysis",
    "entity_id": "ent_999",
    "predictions": predictions,
    "model_version": "v2.3",
    "training_data_size": 1500
}
```

### Use Case 4: Network Cluster Identification

**Scenario**: Analyst discovers a new entity and wants to understand what network they belong to.

**Flow**:

1. **Entity Discovery (palletai)**
   - New Entity E is added to basset-hound
   - Has relationships to Entity F and Entity G

2. **Cluster Analysis (intelligence-analysis)**
   - Analyst triggers network analysis
   - intelligence-analysis performs graph analysis:
     - Identifies all entities connected to Entity E
     - Analyzes relationship strength, frequency, type
     - Detects tightly-connected clusters
     - Identifies cluster characteristics
   - Discovers Entity E belongs to a 15-member cluster
   - Cluster characteristics: Financial services industry, Country Y based

3. **Cluster Report (basset-hound)**
   - Stores "Network Cluster Report"
   - Links to all cluster members
   - Visualizations available for human review

4. **Investigation Strategy (Human)**
   - Analyst sees Entity E is part of larger network
   - Adjusts investigation scope to include cluster
   - Prioritizes understanding cluster structure
   - Identifies key nodes in cluster

**Code Example**:

```python
# intelligence-analysis performs cluster detection
import networkx as nx

# Build graph from basset-hound data
graph = build_entity_graph(project_id)

# Detect clusters using community detection
clusters = nx.community.louvain_communities(graph)

# Analyze Entity E's cluster
entity_cluster = find_cluster_for_entity("ent_e", clusters)

cluster_report = {
    "type": "network_cluster",
    "focal_entity": "ent_e",
    "cluster_members": [member.id for member in entity_cluster],
    "cluster_size": len(entity_cluster),
    "cluster_density": nx.density(graph.subgraph(entity_cluster)),
    "key_nodes": identify_key_nodes(graph, entity_cluster),
    "cluster_characteristics": {
        "industry": "financial_services",
        "geography": "Country Y",
        "activity_level": "high"
    }
}
```

## Separation of Concerns

### Feature Responsibility Matrix

| Feature | basset-hound | basset-verify | intelligence-analysis |
|---------|--------------|---------------|----------------------|
| **Data Storage** |
| Store entities | ✅ | ❌ | ❌ |
| Store relationships | ✅ | ❌ | ❌ |
| Store identifiers | ✅ | ❌ | ❌ |
| Store evidence | ✅ | ❌ | ❌ |
| Store reports | ✅ | ❌ | ❌ |
| **Data Management** |
| CRUD operations | ✅ | ❌ | ❌ |
| Project management | ✅ | ❌ | ❌ |
| Search and filtering | ✅ | ❌ | ❌ |
| **Basic Analysis** |
| Fuzzy string matching | ✅ | ❌ | ❌ |
| Duplicate detection | ✅ | ❌ | ❌ |
| Confidence scoring | ✅ | ❌ | ❌ |
| **Verification** |
| Email verification | ❌ | ✅ | ❌ |
| Phone verification | ❌ | ✅ | ❌ |
| Crypto address verification | ❌ | ✅ | ❌ |
| Network-level checks | ❌ | ✅ | ❌ |
| **Advanced Analysis** |
| Machine learning | ❌ | ❌ | ✅ |
| Pattern detection | ❌ | ❌ | ✅ |
| Risk assessment | ❌ | ❌ | ✅ |
| Predictive analytics | ❌ | ❌ | ✅ |
| Network analysis | ❌ | ❌ | ✅ |
| Behavioral analysis | ❌ | ❌ | ✅ |
| Anomaly detection | ❌ | ❌ | ✅ |
| Report generation | ❌ | ❌ | ✅ |
| **Interface** |
| Web UI | ✅ | ❌ | ❌ |
| REST API | ✅ | ✅ | ❌ |
| MCP Server | ✅ | ✅ | ❌ |
| MCP Client | ❌ | ❌ | ✅ |

### Design Boundaries

#### basset-hound Boundaries

**What it IS:**
- A graph database for intelligence data
- A storage and retrieval system
- A project management tool
- A basic duplicate detection system
- A user interface for data interaction

**What it is NOT:**
- An analysis engine
- A machine learning platform
- An OSINT collection tool
- A prediction system
- A reporting/analytics platform

**Rule of Thumb**: If it requires complex algorithms, ML models, or heavy computation, it belongs in intelligence-analysis.

#### basset-verify Boundaries

**What it IS:**
- A validation service for identifiers
- A network-level verification tool
- A format checker

**What it is NOT:**
- A data storage system
- An OSINT collection tool
- An analysis engine
- A social media scraper

**Rule of Thumb**: If it's about validating an identifier's format or existence (not analyzing its significance), it belongs in basset-verify.

#### intelligence-analysis Boundaries

**What it IS:**
- An analytical engine
- A machine learning platform
- A pattern detection system
- A prediction generator
- A report generator

**What it is NOT:**
- A data storage system
- A user interface
- A CRUD API
- A project management tool

**Rule of Thumb**: If it's about deriving insights from data (not storing data), it belongs in intelligence-analysis.

## Benefits of Separation

### 1. Clear Boundaries
- Each project has a well-defined purpose
- No confusion about where features belong
- Easy to understand system architecture
- Simpler onboarding for new developers

### 2. Easier Maintenance
- Changes to analysis algorithms don't affect storage
- Database schema changes don't affect analysis
- Can fix bugs in one project without touching others
- Smaller, more focused codebases

### 3. Independent Scaling
- **basset-hound**: Scale for data volume and query load
- **intelligence-analysis**: Scale for computational workload
- Different hardware requirements (storage vs. compute)
- Different deployment strategies

**Example Scaling Scenario**:
```
basset-hound:
- Deployed on database-optimized instances
- 500GB Neo4j database
- Moderate CPU requirements
- 3 replicas for high availability

intelligence-analysis:
- Deployed on GPU-enabled instances for ML
- High CPU and memory requirements
- 10 worker nodes for parallel analysis
- Auto-scaling based on analysis queue depth
```

### 4. Technology Independence
- **basset-hound**: Can optimize for Neo4j and graph queries
- **intelligence-analysis**: Can use any ML framework (TensorFlow, PyTorch, scikit-learn)
- basset-verify: Can use specialized validation libraries
- Each project uses best tools for its purpose

### 5. Development Velocity
- Different teams can work on each project
- Teams can deploy independently
- No merge conflicts between storage and analysis code
- Faster iteration on analytical algorithms

### 6. Testing Isolation
- Test storage separately from analysis
- Mock basset-hound for intelligence-analysis tests
- Simpler unit tests (smaller surface area)
- Integration tests only test interfaces

### 7. Security Boundaries
- Different access controls for each project
- intelligence-analysis can be more restricted
- Easier to audit and secure
- Clear data flow boundaries

### 8. Cost Optimization
- Pay for storage in basset-hound
- Pay for compute in intelligence-analysis
- Can turn off analysis when not needed
- Storage runs 24/7, analysis runs on-demand

## Future Expansion

### Adding New Analysis Capabilities

When intelligence-analysis needs new capabilities:

1. **Add new analysis module** (in intelligence-analysis)
   ```python
   # intelligence-analysis/modules/sentiment_analysis.py
   async def analyze_sentiment(entity_id: str):
       # Read text data from basset-hound
       # Perform sentiment analysis
       # Generate report
       # Store in basset-hound
   ```

2. **No changes needed in basset-hound**
   - Still just stores reports as entities
   - Same MCP interface works

3. **UI updates in basset-hound** (optional)
   - Add button to trigger new analysis
   - Display new report type

### Adding New Data Types

When basset-hound needs new entity types:

1. **Add entity type** (in basset-hound)
   ```python
   # New entity type: "financial_transaction"
   # Just add to allowed types
   ```

2. **intelligence-analysis automatically works**
   - Reads new entity type via MCP
   - Can analyze new data
   - No code changes needed

### Adding New Verification Types

When new identifier types need verification:

1. **Add verification method** (in basset-verify)
   ```python
   # basset-verify/verifiers/username_verifier.py
   async def verify_username(username: str, platform: str):
       # Check if username exists on platform
       # Return verification result
   ```

2. **Expose via MCP** (in basset-verify)
   ```python
   @mcp.tool()
   async def verify_username(username: str, platform: str):
       return await username_verifier.verify(username, platform)
   ```

3. **Call from basset-hound**
   ```python
   # basset-hound calls new verification
   result = await verify_mcp.call("verify_username", {
       "username": "johndoe",
       "platform": "twitter"
   })
   ```

## Integration Checklist

When building intelligence-analysis, ensure:

- [ ] Uses basset-hound MCP client for ALL data access
- [ ] Never directly accesses basset-hound database
- [ ] Stores all reports in basset-hound (not local files)
- [ ] Links reports to entities with ANALYZES relationship
- [ ] Includes confidence scores in all analyses
- [ ] Provides clear reasoning for all conclusions
- [ ] Uses consistent report format
- [ ] Handles basset-hound API errors gracefully
- [ ] Respects project boundaries (only analyze entities in authorized projects)
- [ ] Logs all analysis activities
- [ ] Provides progress updates for long-running analyses
- [ ] Can be deployed independently of basset-hound
- [ ] Has own test suite that mocks basset-hound
- [ ] Documents all analysis methods and algorithms

## MCP Interface Contract

### basset-hound MCP Tools (that intelligence-analysis will use)

```python
# Read operations
get_entity(entity_id: str) -> Entity
get_entity_relationships(entity_id: str, type: Optional[str]) -> List[Relationship]
search_entities(project_id: str, query: dict) -> List[Entity]
get_project(project_id: str) -> Project

# Write operations
create_entity(project_id: str, type: str, profile: dict) -> Entity
update_entity(entity_id: str, profile: dict) -> Entity
create_relationship(project_id: str, source_id: str, target_id: str, type: str, properties: dict) -> Relationship

# Evidence operations
add_evidence(entity_id: str, evidence_type: str, content: Any) -> Evidence
```

### basset-verify MCP Tools

```python
# Verification operations
verify_email(email: str) -> VerificationResult
verify_phone(phone: str) -> VerificationResult
verify_crypto_address(address: str, chain: str) -> VerificationResult
```

### Expected Report Format

intelligence-analysis should store reports in this format:

```python
{
    "type": "report",
    "profile": {
        "name": "Report Title",
        "report_type": "threat_assessment|pattern_analysis|predictive_analysis|risk_assessment",
        "content": {
            "analyzed_entity_id": "ent_123",
            "analysis_type": "...",
            "findings": [...],
            "confidence": 0.0-1.0,
            "reasoning": "...",
            "recommendations": [...],
            "generated_at": "ISO 8601 timestamp",
            "generated_by": "intelligence-analysis v1.0",
            "model_version": "..."
        }
    }
}
```

## Conclusion

This three-project architecture provides:
- **Separation of concerns**: Each project has a clear, focused purpose
- **Scalability**: Projects can scale independently based on their needs
- **Maintainability**: Smaller, focused codebases are easier to maintain
- **Flexibility**: Can evolve each project independently
- **Clarity**: Clear boundaries prevent confusion and technical debt

basset-hound remains focused on being an excellent storage and management system for intelligence data, while intelligence-analysis (when built) will provide sophisticated analytical capabilities that enhance the value of that stored data.

The key principle: **basset-hound stores, intelligence-analysis thinks**.
