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
