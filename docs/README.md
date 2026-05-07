# Basset Hound Integration Documentation

## Overview

This documentation describes the architecture and integration strategy for connecting four repositories into a unified OSINT and cybersecurity automation platform:

| Repository | Purpose |
|------------|---------|
| **basset-hound** | Entity and relationship management, OSINT profile storage |
| **osint-resources** | Knowledge base of OSINT tools (~14,000+ lines) |
| **palletAI** | AI agent orchestration and tool execution |
| **autofill-extension** | Browser automation via Chrome extension |

## Documentation Index

### Phase 8 Implementation (Latest - 2026-05-07)

**[PHASE-8-IMPLEMENTATION-GUIDE.md](./PHASE-8-IMPLEMENTATION-GUIDE.md)** - Quick start for Phase 8 features
- How to enable/disable features with flags
- Performance tuning recommendations
- ML analytics setup and usage examples
- Real-time collaboration guide
- Custom plugin development
- Export configuration and examples

**[archive/PHASE-8-SUMMARY-2026-05-07.md](./archive/PHASE-8-SUMMARY-2026-05-07.md)** - Comprehensive Phase 8 overview (68 KB)
- 8 parallel workstreams summary
- 50+ new API endpoints
- Performance improvements (5-10x)
- Feature details for each stream
- Files created/modified
- Deployment checklist

**[findings/PERFORMANCE-REPORT-2026-05-07.md](./findings/PERFORMANCE-REPORT-2026-05-07.md)** - Detailed performance metrics
- Baseline vs. optimized metrics
- Per-component analysis
- Scaling capacity estimates
- Bottleneck analysis
- Monitoring recommendations

**Phase 8 Technical Details** (stream-specific findings):
- [Stream 1: Query Optimization](./findings/QUERY-OPTIMIZATION-2026-05-07.md) - 90% query reduction
- [Stream 2: Caching Strategy](./findings/CACHING-STRATEGY-2026-05-07.md) - 60%+ hit rate
- [Stream 3: Bundle Optimization](./findings/BUNDLE-OPTIMIZATION-2026-05-07.md) - 42% bundle reduction
- [Stream 4: Search Optimization](./findings/SEARCH-OPTIMIZATION-2026-05-07.md) - Full-text + faceted search
- [Stream 5: ML Analytics](./findings/ML-ANALYTICS-IMPLEMENTATION-2026-05-07.md) - Duplicate detection, link prediction
- [Stream 6: Collaboration](./findings/COLLABORATION-ARCHITECTURE-2026-05-07.md) - Real-time sync, activity feeds
- [Stream 7: Plugins](./findings/PLUGIN-SYSTEM-DESIGN-2026-05-07.md) - Custom visualizations
- [Stream 8: Export](./findings/EXPORT-FORMATS-2026-05-07.md) - GraphML, CSV, JSON, GeoJSON, PDF

### Core Documentation

### [00-EXECUTIVE-SUMMARY.md](./00-EXECUTIVE-SUMMARY.md)
High-level overview, key findings, and priority roadmap. Start here for a quick understanding of the integration strategy.

### [01-REPOSITORY-ANALYSIS.md](./01-REPOSITORY-ANALYSIS.md)
Detailed analysis of each repository including:
- Technology stacks
- Current features and capabilities
- API endpoints and integration points
- Limitations and gaps

### [02-INTEGRATION-ARCHITECTURE.md](./02-INTEGRATION-ARCHITECTURE.md)
System architecture design including:
- Component diagrams
- Data flow patterns
- MCP tool implementations
- Example code for basset-hound and browser integration

### [03-BROWSER-AUTOMATION-STRATEGY.md](./03-BROWSER-AUTOMATION-STRATEGY.md)
Comprehensive plan for rebuilding the Chrome extension:
- Architecture design
- WebSocket communication protocol
- Content script implementation
- palletAI bridge server

### [04-PENTESTING-INTEGRATION.md](./04-PENTESTING-INTEGRATION.md)
Extending the platform for penetration testing:
- Entity model extensions
- Pentesting agent personalities
- Security tool MCP implementations
- Bug bounty workflows

### [05-IMPLEMENTATION-ROADMAP.md](./05-IMPLEMENTATION-ROADMAP.md)
Phased implementation plan:
- Phase 1: Foundation (basset-hound API, osint-resources ingestion)
- Phase 2: Browser Automation (extension rebuild)
- Phase 3: Agent Development (OSINT and pentesting personalities)
- Phase 4: Integration & Workflows
- Phase 5: Advanced Features

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.10+
- Node.js 18+
- Chrome browser
- Ollama (for local LLM inference)

### Repository Setup

```bash
# Clone all repositories
cd ~
git clone <basset-hound-url>
git clone <osint-resources-url>
git clone <palletAI-url>
git clone <autofill-extension-url>

# Start basset-hound
cd ~/basset-hound
docker-compose up -d
pip install -r requirements.txt
python app.py

# Start palletAI
cd ~/palletAI/agent_manager
pip install -r requirements.txt
python main.py

# Load extension in Chrome
# 1. Go to chrome://extensions
# 2. Enable Developer mode
# 3. Load unpacked: ~/autofill-extension
```

## Architecture Overview

```
┌────────────────────────────────────────────────────────────────┐
│                         User Interface                          │
│  basset-hound UI │ palletAI CLI │ Chrome Extension Popup       │
└────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌────────────────────────────────────────────────────────────────┐
│                    palletAI Agent Manager                       │
│  Agent Executor │ Multi-Agent Coordinator │ Task DAG Engine    │
│                              │                                  │
│                    MCP Tool Executor                            │
└────────────────────────────────────────────────────────────────┘
         │                     │                     │
         ▼                     ▼                     ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ basset-hound │    │ Browser      │    │ System       │
│ MCP Tools    │    │ MCP Tools    │    │ Tools        │
└──────────────┘    └──────────────┘    └──────────────┘
         │                     │                     │
         ▼                     ▼                     ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ Neo4j        │    │ Chrome       │    │ CLI Tools    │
│ Graph DB     │    │ Extension    │    │ nmap, etc.   │
└──────────────┘    └──────────────┘    └──────────────┘
```

## Key Integration Points

### 1. palletAI → basset-hound
MCP tools that allow agents to create entities, relationships, and reports.

### 2. palletAI → Browser Extension
WebSocket bridge for browser automation commands.

### 3. osint-resources → palletAI
Knowledge base ingestion for RAG queries about OSINT tools.

### 4. All → basset-hound
Central storage for investigation findings and relationships.

## Development Priorities

1. **Critical**: Browser extension WebSocket communication
2. **High**: basset-hound MCP tools
3. **High**: osint-resources KB ingestion
4. **Medium**: OSINT agent personalities
5. **Medium**: Pentesting tools integration
6. **Low**: Advanced visualization and scheduling

## Contributing

When extending this platform:

1. Follow existing patterns in each repository
2. Add new MCP tools to appropriate server files
3. Document new agent personalities thoroughly
4. Update osint-resources with new tool documentation
5. Store all findings in basset-hound for relationship tracking

## Security Considerations

- All browser automation is local-only (localhost WebSocket)
- API authentication required for production deployment
- Agent scope constraints prevent unauthorized actions
- Sensitive credentials never logged or exposed
- All pentesting requires explicit authorization
