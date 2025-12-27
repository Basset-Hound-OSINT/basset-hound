# Repository Analysis: Detailed Findings

## 1. basset-hound

### Technology Stack
- **Backend**: Flask 3.1.0 (Python)
- **Database**: Neo4j 5.13.0 (graph database via Docker)
- **Frontend**: Bootstrap 5.3.0, Cytoscape.js, modular ES6 JavaScript
- **Configuration**: YAML-based dynamic schema

### Architecture
```
basset-hound/
├── app.py                 # Main Flask app, project management
├── neo4j_handler.py       # Database abstraction (26KB, core CRUD)
├── profiles.py            # Person/profile blueprint (24.5KB)
├── reports.py             # Report management blueprint
├── config_loader.py       # YAML configuration utilities
├── data_config.yaml       # Dynamic schema definition
├── docker-compose.yml     # Neo4j container orchestration
├── static/js/             # 11 modular JavaScript files (~150KB)
│   ├── dashboard.js       # App initialization
│   ├── api.js             # Fetch wrapper functions
│   ├── ui-form-handlers.js    # Dynamic form creation
│   ├── ui-person-details.js   # Profile rendering
│   ├── tag-handler.js     # Relationship tagging
│   ├── report-handler.js  # Markdown report generation
│   └── file_explorer.js   # File browser
└── templates/             # Jinja2 templates
```

### Database Schema (Neo4j Graph)
```
Project
  ├─ HAS_PERSON → Person
  │   ├─ HAS_FIELD_VALUE → FieldValue
  │   ├─ HAS_FILE → File
  │   └─ HAS_REPORT → Report
  └─ HAS_SECTION → Section
      └─ HAS_FIELD → Field
          └─ HAS_COMPONENT → Component
```

### Key Features
1. **Dynamic Schema**: Profiles defined via YAML, supports multiple field types
2. **Relationship Tracking**: Direct + transitive relationship calculation
3. **File Management**: Organized file storage per person/project
4. **Report Generation**: Markdown reports with full profile data
5. **Graph Visualization**: Cytoscape.js ready (skeleton implemented)

### API Endpoints (Integration Points)
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/add_person` | POST | Create entity |
| `/get_people` | GET | List all entities |
| `/get_person/<id>` | GET | Fetch entity details |
| `/update_person/<id>` | POST | Update entity data |
| `/tag_person/<id>` | POST | Create relationships |
| `/person/<id>/reports` | POST | Create OSINT report |
| `/person/<id>/upload` | POST | Upload files |
| `/download_project` | GET | Export project JSON |

### Current Limitations
- No browser automation or web scraping
- Manual data entry only
- No API authentication
- No scheduled tasks
- Limited search (basic text only)

---

## 2. osint-resources

### Technology Stack
- **Format**: mdbook (Rust-based book generator)
- **Content**: Markdown files organized by category
- **Size**: ~14,778 lines across 60+ markdown files

### Structure
```
osint-resources/
├── book.toml              # mdbook configuration
├── src/
│   ├── SUMMARY.md         # Table of contents (149 lines)
│   ├── README.md          # Introduction
│   ├── template.md        # Tool documentation template (YAML)
│   ├── identifiers/       # Names, emails, usernames, phones
│   ├── discovery/         # Search engines, maps, scrapers
│   ├── social/            # Platform-specific tools (15 files)
│   ├── files/             # Document, image, video analysis
│   ├── records/           # Public/government records
│   ├── breaches/          # Data breach sources
│   ├── specialized/       # Dark web, mobile, IoT
│   ├── offsec/            # Offensive security tools
│   ├── sock_puppets/      # Identity management
│   └── management/        # Methodology, reporting
├── references/            # Additional resource files
└── scripts/               # Link extraction utilities
```

### Tool Categories Documented
1. **Data Types & Identifiers**: Names, emails, usernames, phones, vehicles
2. **Discovery Tools**: Search engines, custom searches, maps
3. **Social Networks**: Facebook, Twitter, LinkedIn, Discord, etc.
4. **File Analysis**: Documents, images, video, audio, forensics
5. **Public Records**: Real estate, government, business, court
6. **Financial**: Crypto, stock market, investing tools
7. **Breach Intelligence**: Data breaches, password lookups
8. **Specialized**: Tor/dark web, cloud/CDN, mobile, IoT
9. **Offensive Security**: IP, DNS, web vulns, WiFi, Bluetooth
10. **Sock Puppets**: Fake identity management

### Tool Documentation Template
```yaml
tool_info:
  name: chiasmodon
  type: serverside | web
  git_url: https://github.com/...
  usage_url: https://...
  tool_cmd:
    sudo: false
    cmd: chiasmodon_cli.py ${DOMAIN} -ot ${PROFILE}/logs/...
    target_info: firstname, lastname
    target_info_opt: phonenumber, email
  fields:  # For web tools
    'input#AccountCheck_Account': 'test@example.com'
```

### Integration Value
- **Knowledge Base**: 1000s of tools with URLs and categories
- **Automation Metadata**: Template includes CLI commands and web form selectors
- **RAG Source**: Can be chunked and embedded for agent queries

---

## 3. palletAI

### Technology Stack
- **Backend**: FastAPI (async Python)
- **Database**: PostgreSQL + pgvector (vector embeddings)
- **LLM**: Ollama (local inference, multi-GPU support)
- **Protocol**: FastMCP (Model Context Protocol)
- **Queue**: Redis + Celery (async tasks)

### Architecture
```
palletAI/
└── agent_manager/
    ├── main.py                    # Entry point
    ├── src/
    │   ├── api/
    │   │   ├── main.py            # FastAPI app
    │   │   └── routes/
    │   │       ├── agents.py      # Agent CRUD, coworker spawning
    │   │       ├── tasks.py       # Task management
    │   │       ├── websocket.py   # Real-time streaming
    │   │       └── system_tools.py
    │   ├── core/
    │   │   ├── agent.py           # Agent class
    │   │   ├── agent_executor.py  # DAG execution engine
    │   │   ├── tool_executor.py   # MCP tool runner
    │   │   ├── rag_engine.py      # Three-tier RAG system
    │   │   ├── task_dag.py        # Task dependency graph
    │   │   ├── kb_manager.py      # Knowledge base manager
    │   │   ├── llm_router.py      # Model selection
    │   │   └── prompt_manager.py  # Prompt composition
    │   ├── models/
    │   │   ├── database.py        # SQLAlchemy models
    │   │   └── schemas.py         # Pydantic schemas
    │   └── services/
    │       └── multi_agent_coordinator.py
    ├── mcp_servers/
    │   └── system_tools/
    │       └── server.py          # MCP tool implementations
    ├── agent_prompts/             # Personality markdown files
    │   ├── base_knowledge_aware.md
    │   ├── research_assistant.md
    │   ├── code_assistant.md
    │   └── bug_bounty_agent.md
    └── repository_kbs.yaml        # Knowledge base sources
```

### Key Features

#### 1. Agent System
- **Agent Types**: Defined by personality markdown files
- **Lifecycle**: INITIALIZING → IDLE → EXECUTING → COMPLETED/FAILED
- **Workspaces**: Isolated directories per agent

#### 2. Coworker Spawning
```python
POST /api/agents/{agent_id}/spawn-coworker
{
  "coworker_name": "research_agent_1",
  "coworker_type": "research_assistant",  # Optional
  "task_description": "Find all social media profiles for target",
  "share_workspace": true,
  "auto_select_type": true,  # AI picks personality
  "strict_scope": true
}
```

#### 3. Scope Constraints
```python
CoworkerScopeConstraints:
  - allowed_actions: ["read_file", "web_search"]
  - forbidden_actions: ["execute_command"]
  - max_files_to_create: 10
  - max_execution_time_minutes: 30
  - can_spawn_coworkers: false
  - required_result_format: "json"
```

#### 4. Three-Tier RAG System
```
Domain KB (Methodology)
├─ Best practices for agent type
├─ Domain-specific how-to guides

Tool KB (Capabilities)
├─ Tool documentation
├─ Command reference

Instance KB (Session-Specific)
├─ Chat history
├─ Agent-specific learnings
```

#### 5. MCP Tools Available
- Workspace: `list_workspace`, `read_file`, `write_file`, `search_workspace`
- Memory: `remember`, `recall`, `forget`
- Messaging: `send_message`, `check_inbox`
- Web: `web_search`, `fetch_url`, `search_code`
- Code: `validate_code`, `run_tests`
- System: `execute_command`

### Extension Points
1. Add new MCP tools in `mcp_servers/system_tools/server.py`
2. Create new personalities in `agent_prompts/`
3. Configure knowledge sources in `repository_kbs.yaml`

---

## 4. autofill-extension

### Technology Stack
- **Type**: Chrome Extension (Manifest V3)
- **Languages**: JavaScript, HTML
- **Backend**: Flask test server (Python)
- **Config**: YAML-based field mappings

### Current Structure
```
autofill-extension/
├── manifest.json          # MV3 configuration
├── background.js          # Service worker (4 lines)
├── content.js             # Form filler (16 lines)
├── popup.js               # UI logic (34 lines)
├── popup.html             # Popup interface
├── utils.js               # Utilities (11 lines)
├── js-yaml.min.js         # YAML parser
└── flask_test_app/
    ├── app.py             # Config server
    └── configs/           # YAML field mappings
```

### Current Capabilities
- Fill text input fields with CSS selector matching
- Load configurations from Flask server
- Display available fields in popup
- Manual trigger via popup button
- Event dispatching for form handlers

### Missing Features (Critical)
1. **Dynamic Form Detection**: Only works with pre-configured selectors
2. **Element Interaction**: No dropdown, checkbox, file upload support
3. **Navigation**: Cannot navigate between pages
4. **AI Control**: No bi-directional agent communication
5. **Error Handling**: No retry logic or feedback
6. **Authentication**: No session management

### Required Enhancements
```
Agent Communication Protocol:
  - navigate(url)
  - fillForm(selectors, values)
  - clickElement(selector)
  - getText(selector)
  - getFormState()
  - submitForm(selector)
  - waitForElement(selector, timeout)
  - screenshot()
```
