# Implementation Roadmap

## Overview

This document provides a detailed implementation roadmap for integrating the four repositories into a cohesive OSINT and cybersecurity automation platform.

## Phase 1: Foundation (Priority: Critical)

### 1.1 basset-hound API Enhancements

**Goal**: Make basset-hound accessible to external tools and agents.

**Tasks**:
| Task | Description | Effort |
|------|-------------|--------|
| Add REST API documentation | OpenAPI/Swagger spec | Low |
| Implement search endpoint | Full-text search across entities | Medium |
| Add API authentication | JWT or API key auth | Medium |
| Create bulk import/export | JSON/CSV entity import | Medium |
| Add webhook support | Notify on entity changes | Low |

**Files to Create/Modify**:
- `basset-hound/api_routes.py` - New Flask blueprint for clean API
- `basset-hound/auth.py` - Authentication middleware
- `basset-hound/static/swagger.yaml` - API documentation

**Acceptance Criteria**:
- [ ] All CRUD operations accessible via REST API
- [ ] API authentication working
- [ ] Swagger documentation available at `/api/docs`

### 1.2 osint-resources Knowledge Base Ingestion

**Goal**: Make OSINT tool documentation queryable by AI agents.

**Tasks**:
| Task | Description | Effort |
|------|-------------|--------|
| Create ingestion script | Parse markdown → structured JSON | Medium |
| Define tool schema | Standardize tool_info YAML format | Low |
| Set up palletAI KB config | Add to repository_kbs.yaml | Low |
| Test RAG queries | Verify relevant results returned | Medium |

**Files to Create/Modify**:
- `osint-resources/scripts/export_to_json.py` - Export structured tool data
- `palletAI/agent_manager/repository_kbs.yaml` - Add osint-resources entry
- `osint-resources/src/template.md` - Finalize schema

**Acceptance Criteria**:
- [ ] All tools indexed in palletAI vector database
- [ ] Query "tools for email investigation" returns relevant results
- [ ] Tool metadata (type, cmd, target_info) extracted

### 1.3 Create basset-hound MCP Server

**Goal**: Enable palletAI agents to interact with basset-hound.

**Tasks**:
| Task | Description | Effort |
|------|-------------|--------|
| Create MCP server structure | FastMCP setup | Low |
| Implement entity tools | create, read, update, delete | Medium |
| Implement relationship tools | tag, get_related, graph | Medium |
| Implement report tools | create_report, upload_file | Medium |
| Add to palletAI tool executor | Register new MCP server | Low |

**Files to Create**:
- `palletAI/agent_manager/mcp_servers/basset_hound/server.py`
- `palletAI/agent_manager/mcp_servers/basset_hound/__init__.py`

**Acceptance Criteria**:
- [ ] Agent can create entity in basset-hound
- [ ] Agent can update entity fields
- [ ] Agent can create relationships between entities
- [ ] Agent can generate reports

---

## Phase 2: Browser Automation (Priority: Critical)

### 2.1 Rebuild autofill-extension Core ✅ COMPLETED

**Goal**: Create bi-directional communication with palletAI.

**Tasks**:
| Task | Description | Effort | Status |
|------|-------------|--------|--------|
| WebSocket client in background.js | Connect to palletAI | Medium | ✅ Done |
| Command router | Handle navigate, click, fill, etc. | High | ✅ Done |
| Response handler | Send results back to agent | Medium | ✅ Done |
| Connection management | Reconnection, status tracking | Medium | ✅ Done |

**Files Created**:
- `basset-hound-autofill-extension/background.js` - WebSocket client with command handlers
- `basset-hound-autofill-extension/manifest.json` - Chrome MV3 manifest
- `basset-hound-autofill-extension/popup.html` - Extension popup UI
- `basset-hound-autofill-extension/popup.js` - Popup functionality
- `basset-hound-autofill-extension/utils/logger.js` - Structured logging utility

**Implementation Details**:
- WebSocket connects to `ws://localhost:8765/browser`
- Exponential backoff reconnection (1s to 30s, max 10 attempts)
- Heartbeat mechanism for connection health
- Task queue tracking for pending commands
- Commands: navigate, fill_form, click, get_content, screenshot, wait_for_element, get_page_state, execute_script

**Acceptance Criteria**:
- [x] Extension connects to palletAI WebSocket server
- [x] Commands received and executed
- [x] Results returned to agent

### 2.2 Enhanced Content Script ✅ COMPLETED

**Goal**: Comprehensive DOM interaction capabilities.

**Tasks**:
| Task | Description | Effort | Status |
|------|-------------|--------|--------|
| Form detection | Auto-discover form fields | High | ✅ Done |
| Element interaction | Click, scroll, wait | Medium | ✅ Done |
| Content extraction | Get text, HTML, attributes | Low | ✅ Done |
| Page state capture | Forms, links, buttons | Medium | ✅ Done |
| Screenshot capability | Tab capture API | Low | ✅ Done |

**Files Created**:
- `basset-hound-autofill-extension/content.js` - DOM interaction with comprehensive error handling

**Implementation Details**:
- Multi-strategy element finding (CSS, ID, name, placeholder, aria-label, text content)
- Human-like typing simulation with random delays (30-100ms per character)
- MutationObserver-based element waiting with timeout
- Comprehensive page state extraction (forms, fields, links, buttons)
- Error boundaries around all DOM operations

**Acceptance Criteria**:
- [x] Agent can fill any form field
- [x] Agent can click any element
- [x] Agent can extract page content
- [x] Screenshots captured on demand

### 2.2.1 Structured Logging ✅ COMPLETED (NEW)

**Goal**: Comprehensive logging for debugging and monitoring.

**Implementation**:
- Log levels: DEBUG, INFO, WARN, ERROR
- Timestamps and component tracking
- Optional Chrome storage persistence
- Child logger support for isolated contexts

### 2.2.2 Error Handling Improvements ✅ COMPLETED (NEW)

**Goal**: Robust error handling throughout the extension.

**Implementation**:
- Try-catch blocks around all async operations
- Graceful degradation on failures
- Detailed error messages with stack traces
- Connection state recovery mechanisms

### 2.3 palletAI Browser Bridge

**Goal**: Server-side WebSocket endpoint for browser control.

**Tasks**:
| Task | Description | Effort |
|------|-------------|--------|
| WebSocket server | Accept extension connection | Medium |
| Command queue | Queue and track pending commands | Medium |
| Timeout handling | Fail gracefully on timeout | Low |
| Status endpoint | Check if browser connected | Low |

**Files to Create**:
- `palletAI/agent_manager/src/api/routes/browser_bridge.py`

**Acceptance Criteria**:
- [ ] Extension connects successfully
- [ ] Commands sent and responses received
- [ ] Timeouts handled properly

### 2.4 Browser MCP Tools

**Goal**: Make browser automation available to agents.

**Tasks**:
| Task | Description | Effort |
|------|-------------|--------|
| Implement browser_navigate | URL navigation with wait | Low |
| Implement browser_fill_form | Field filling | Low |
| Implement browser_click | Element clicking | Low |
| Implement browser_get_content | Content extraction | Low |
| Implement browser_screenshot | Screenshot capture | Low |
| Implement browser_get_page_state | Page analysis | Medium |

**Files to Create**:
- `palletAI/agent_manager/mcp_servers/browser/server.py`

**Acceptance Criteria**:
- [ ] All browser tools accessible to agents
- [ ] HaveIBeenPwned workflow automated
- [ ] Screenshots saved to workspace

### 2.5 Electron Browser Application ✅ COMPLETED (NEW)

**Goal**: Custom Electron-based browser with WebSocket control and bot detection evasion.

**Tasks**:
| Task | Description | Effort | Status |
|------|-------------|--------|--------|
| Electron main process | BrowserWindow with anti-fingerprinting | High | ✅ Done |
| WebSocket server | Accept automation commands | Medium | ✅ Done |
| IPC bridge | Secure context bridge | Medium | ✅ Done |
| Bot detection evasion | Fingerprint spoofing | High | ✅ Done |
| Human behavior simulation | Typing, mouse, scroll | High | ✅ Done |

**Files Created**:
- `basset-hound-browser/package.json` - Electron dependencies and build config
- `basset-hound-browser/main.js` - Main process with IPC handlers
- `basset-hound-browser/preload.js` - Secure IPC bridge
- `basset-hound-browser/websocket/server.js` - WebSocket server (11 commands)
- `basset-hound-browser/evasion/fingerprint.js` - Anti-fingerprinting module
- `basset-hound-browser/evasion/humanize.js` - Human behavior simulation
- `basset-hound-browser/renderer/index.html` - Browser UI
- `basset-hound-browser/renderer/renderer.js` - Renderer process

**WebSocket Commands Implemented**:
1. `navigate` - URL navigation with wait options
2. `click` - Element clicking with selectors
3. `fill` - Form field filling
4. `get_content` - Content extraction (text/HTML)
5. `screenshot` - Page capture
6. `get_page_state` - Full page analysis
7. `execute_script` - Custom JS execution
8. `wait_for_element` - Element waiting with timeout
9. `scroll` - Page scrolling
10. `get_cookies` - Cookie retrieval
11. `set_cookies` - Cookie setting

**Bot Detection Evasion Features**:
- Navigator property spoofing (webdriver, plugins, languages)
- WebGL fingerprint randomization
- Canvas fingerprint noise injection
- Audio context modification
- Timezone and screen dimension spoofing
- Realistic user agent rotation
- Chrome runtime environment simulation

**Human Behavior Simulation**:
- Typing with realistic delays and occasional mistakes
- Mouse movement using Bezier curves
- Natural scroll patterns with momentum
- Random micro-delays between actions

**Acceptance Criteria**:
- [x] Electron browser with URL navigation
- [x] WebSocket server accepting commands
- [x] Bot detection evasion active
- [x] Human-like behavior simulation

### 2.6 Advanced Browser Features ✅ COMPLETED (NEW)

**Goal**: Full-featured browser automation with profile and session management.

**Tasks**:
| Task | Description | Effort | Status |
|------|-------------|--------|--------|
| Tab Management | Multiple tabs, switching, closing | Medium | ✅ Done |
| Profile/Identity Management | Browser profiles, fingerprint profiles | High | ✅ Done |
| Cookie Import/Export | JSON/file import/export | Medium | ✅ Done |
| Download Management | Track, pause, resume, cancel | Medium | ✅ Done |
| DevTools Access | Console, network, elements | High | ✅ Done |
| Network Throttling | Bandwidth limiting, latency | Medium | ✅ Done |
| Geolocation Spoofing | GPS/timezone override | Medium | ✅ Done |
| Local Storage Manager | View, edit, export/import | Medium | ✅ Done |
| Header Modification | Request/response headers | Medium | ✅ Done |
| Page History Tracking | Record, export, search | Medium | ✅ Done |
| Ad/Tracker Blocking | EasyList integration, custom filters | High | ✅ Done |
| Page Automation Scripts | Storage, execution, scheduling | High | ✅ Done |
| DOM Inspector | Element inspection, selector generation | Medium | ✅ Done |

**Files Created**:
- `basset-hound-browser/tabs/manager.js` - Multi-tab support
- `basset-hound-browser/profiles/manager.js` - Profile management
- `basset-hound-browser/profiles/storage.js` - Profile persistence
- `basset-hound-browser/cookies/manager.js` - Cookie import/export
- `basset-hound-browser/downloads/manager.js` - Download control
- `basset-hound-browser/devtools/manager.js` - DevTools access
- `basset-hound-browser/devtools/console.js` - Console logging
- `basset-hound-browser/network/throttling.js` - Network throttling
- `basset-hound-browser/geolocation/manager.js` - GPS spoofing
- `basset-hound-browser/geolocation/presets.js` - Location presets
- `basset-hound-browser/storage/manager.js` - Storage management
- `basset-hound-browser/headers/manager.js` - Header modification
- `basset-hound-browser/headers/profiles.js` - Header profiles
- `basset-hound-browser/history/manager.js` - History tracking
- `basset-hound-browser/history/storage.js` - History persistence
- `basset-hound-browser/blocking/manager.js` - Ad/tracker blocking
- `basset-hound-browser/blocking/filters.js` - Filter management
- `basset-hound-browser/automation/runner.js` - Script execution
- `basset-hound-browser/automation/scripts.js` - Script management
- `basset-hound-browser/automation/storage.js` - Script storage
- `basset-hound-browser/inspector/manager.js` - DOM inspection
- `basset-hound-browser/inspector/highlighter.js` - Element highlighting
- `basset-hound-browser/inspector/selector-generator.js` - CSS selector generation

**Acceptance Criteria**:
- [x] Multiple browser tabs supported
- [x] Profile switching working
- [x] Cookie import/export functional
- [x] Network throttling active
- [x] Geolocation spoofing working
- [x] Ad/tracker blocking enabled
- [x] Automation scripts executing

### 2.7 Enhanced Extension Features ✅ COMPLETED (NEW)

**Goal**: Advanced extension capabilities for comprehensive automation.

**Tasks**:
| Task | Description | Effort | Status |
|------|-------------|--------|--------|
| Cookie Management | Get/set cookies via API | Medium | ✅ Done |
| Storage Management | localStorage/sessionStorage | Medium | ✅ Done |
| Network Monitoring | Request/response capture, HAR export | High | ✅ Done |
| Request Interception | Header modification, URL blocking | High | ✅ Done |

**Files Created/Modified**:
- `basset-hound-autofill-extension/utils/network-monitor.js` - Network traffic monitoring
- `basset-hound-autofill-extension/utils/request-interceptor.js` - Request interception

---

## Phase 3: Agent Development (Priority: High)

### 3.1 OSINT Agent Personalities

**Goal**: Create specialized agents for OSINT workflows.

**Personalities to Create**:
| Agent | Purpose | Primary Tools |
|-------|---------|---------------|
| email_investigator | Email-based OSINT | browser, web_search, basset_hound |
| username_hunter | Username enumeration | browser, execute_command |
| domain_analyst | Domain reconnaissance | nmap, web_search, basset_hound |
| social_media_researcher | Social platform OSINT | browser, basset_hound |

**Files to Create**:
- `palletAI/agent_manager/agent_prompts/email_investigator.md`
- `palletAI/agent_manager/agent_prompts/username_hunter.md`
- `palletAI/agent_manager/agent_prompts/domain_analyst.md`
- `palletAI/agent_manager/agent_prompts/social_media_researcher.md`

### 3.2 Pentesting Agent Personalities

**Personalities to Create**:
| Agent | Purpose | Primary Tools |
|-------|---------|---------------|
| recon_agent | Network reconnaissance | nmap, masscan, basset_hound |
| vuln_scanner | Vulnerability assessment | nuclei, nikto, basset_hound |
| web_tester | Web application testing | browser, sqlmap, ffuf |
| exploit_researcher | Exploit finding | searchsploit, web_search |

**Files to Create**:
- `palletAI/agent_manager/agent_prompts/recon_agent.md`
- `palletAI/agent_manager/agent_prompts/vuln_scanner.md`
- `palletAI/agent_manager/agent_prompts/web_tester.md`
- `palletAI/agent_manager/agent_prompts/exploit_researcher.md`

### 3.3 Pentesting MCP Tools

**Goal**: Add security testing tools to palletAI.

**Tools to Implement**:
| Tool | Function | Binary |
|------|----------|--------|
| nmap_scan | Port/service scanning | nmap |
| nuclei_scan | Template-based vuln scan | nuclei |
| directory_bruteforce | Directory enumeration | ffuf |
| nikto_scan | Web server scanning | nikto |
| sqlmap_test | SQL injection testing | sqlmap |
| check_exploit_db | Exploit search | searchsploit |

**Files to Create**:
- `palletAI/agent_manager/mcp_servers/pentest_tools/server.py`

---

## Phase 4: Integration & Workflows (Priority: Medium)

### 4.1 Multi-Agent Workflows

**Goal**: Enable complex multi-step investigations.

**Workflows to Implement**:
| Workflow | Description | Agents Involved |
|----------|-------------|-----------------|
| Full Email Investigation | Email → Social → Breaches | email_investigator, social_researcher |
| Network Assessment | Recon → Vuln Scan → Report | recon_agent, vuln_scanner |
| Bug Bounty Recon | Subdomains → Tech Stack → Vulns | domain_analyst, web_tester |

**Implementation Approach**:
1. Create orchestrator agents that spawn coworkers
2. Use Task DAG for dependency management
3. Aggregate results in basset-hound

### 4.2 Report Generation

**Goal**: Automated report creation from agent findings.

**Tasks**:
| Task | Description | Effort |
|------|-------------|--------|
| Template system | Markdown templates for reports | Medium |
| Evidence inclusion | Embed screenshots and files | Medium |
| Entity cross-referencing | Link to basset-hound entities | Low |
| Export formats | PDF, DOCX, HTML | Medium |

### 4.3 osint-resources Tool Automation

**Goal**: Use tool documentation to guide automation.

**Tasks**:
| Task | Description | Effort |
|------|-------------|--------|
| Parse tool_info YAML | Extract cmd, fields, target_info | Medium |
| Generate browser configs | Create field mappings for web tools | High |
| CLI tool wrapper | Auto-generate tool execution commands | Medium |

---

## Phase 5: Advanced Features (Priority: Low)

### 5.1 Graph Visualization

**Goal**: Visualize entity relationships in basset-hound.

**Tasks**:
- Implement Cytoscape.js graph view
- Add force-directed layout
- Enable click-through to entity details
- Support filtering by relationship type

### 5.2 Scheduled Tasks

**Goal**: Run automated reconnaissance on schedule.

**Tasks**:
- Add Celery beat scheduler to palletAI
- Create scheduling API
- Implement notification on findings

### 5.3 Tor Integration

**Goal**: Enable dark web research capabilities.

**Tasks**:
- Add Tor proxy configuration
- Create onion-aware browser tools
- Implement .onion enumeration

### 5.4 API Credential Management

**Goal**: Secure storage of service API keys.

**Tasks**:
- Create credential vault in palletAI
- Implement secure injection into tools
- Add rotation and expiry tracking

---

## Technical Dependencies

### Required Installations

**basset-hound**:
```bash
# Already installed
pip install flask neo4j pyyaml
```

**palletAI**:
```bash
# Core
pip install fastapi uvicorn sqlalchemy asyncpg
pip install sentence-transformers pgvector

# Tools
pip install httpx aiofiles
```

**basset-hound-autofill-extension** ✅:
```bash
# No build required - Chrome extension loads directly
# For development/testing:
npm install --save-dev web-ext
```

**basset-hound-browser** ✅:
```bash
cd basset-hound-browser
npm install
npm start  # Development mode
npm run build  # Package for distribution
```

**System Tools (for pentesting)**:
```bash
# Debian/Ubuntu
sudo apt install nmap nikto sqlmap

# Go tools
go install github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest
go install github.com/ffuf/ffuf@latest
go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
```

### Environment Variables

```bash
# palletAI
DATABASE_URL=postgresql://user:pass@localhost/palletai
OLLAMA_HOST=http://localhost:11434
REDIS_URL=redis://localhost:6379

# basset-hound
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# Browser Bridge
BROWSER_WS_PORT=8765
```

---

## Success Metrics

### Phase 1 Completion
- [ ] basset-hound API responding
- [ ] osint-resources indexed in palletAI
- [ ] MCP tools creating entities

### Phase 2 Completion
- [x] Browser extension connected (basset-hound-autofill-extension)
- [x] Form filling automated (content.js with human-like typing)
- [x] Screenshots captured (Tab capture API)
- [x] Electron browser with WebSocket control (basset-hound-browser)
- [x] Bot detection evasion implemented
- [x] Human behavior simulation active

### Phase 3 Completion
- [ ] OSINT agent running investigations
- [ ] Results stored in basset-hound
- [ ] Reports generated

### Phase 4 Completion
- [ ] Multi-agent workflows executing
- [ ] Network assessments running
- [ ] Tool documentation driving automation

### Phase 5 Completion
- [ ] Graph visualization working
- [ ] Scheduled scans running
- [ ] Dark web research enabled

---

## Risk Mitigation

| Risk | Mitigation | Status |
|------|------------|--------|
| Browser extension breaks with Chrome updates | Use stable MV3 APIs, test on beta channel | ✅ Using MV3 |
| Bot detection on OSINT sites | Use human-in-the-loop, rate limiting | ✅ Evasion implemented |
| Security vulnerabilities in automation | Sandboxing, scope constraints, audit logging | Ongoing |
| Neo4j performance at scale | Index optimization, query profiling | Pending |
| LLM hallucination in agent responses | Validation steps, tool result verification | Pending |

**Bot Detection Mitigations Implemented**:
- Navigator.webdriver property spoofed
- Canvas/WebGL fingerprint randomization
- Human-like typing, mouse movement, scrolling
- Realistic user agents and viewport sizes
- Chrome runtime environment simulation

---

## Maintenance Plan

### Weekly
- Review agent execution logs
- Update blocked/broken tool URLs
- Monitor database performance

### Monthly
- Update osint-resources knowledge base
- Review and update agent personalities
- Security audit of new code

### Quarterly
- Major dependency updates
- Performance optimization review
- Feature prioritization for next quarter
