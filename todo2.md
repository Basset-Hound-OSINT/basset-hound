I have this repository and then the following external repositories that are meant to be independent projects but they're primarily built to extend to this existing project I just think everything all three repositories are large projects in of themselves that can stand alone and I simply want to make them integrate together but also be independent of each other.

~/autofill-extension
~/basset-hound-browser

and then the current local repository

~/basset-hound

Autofill extension auto search for data fields to allow users to click a button “ingest”

For information like crypto, email, phones, need to make sure data is plausible and ideally verify if exists. If not plausible then don’t allow ingest, but also want humans to be able to select html elements and auto copy content and take screenshots of pages.

For verify, need to find either algorithms or blockchain api for verifying wallet address, then need some probe or something or a Whois to see if domain exists and if email route exists for emails.


Basset hound keep track of where data comes from, either human operator entry or website, if website then have url and date

Autofill extension get full url and date for ingesting data


Somehow integrate into basset hound browser


OSINT agent use basset hound browser to perform automated investigations





Please take the ideas I just listed and do some sort of code review for every single repository and then add good updates or make sure these ideas are reflected in the road map.Md files for every single repository you may find the road map dot MD files and each repositories in the docs folder or something else but please do that comprehensive code review and figure out how I can integrate all these changes and make them all work together. Does this make sense? Feel free to spawn multiple agents as needed and let me know what you find you may need to also do web research so please document your findings into respective repositories where your research findings for various projects affect them differently. Effectively do research for all three repositories simultaneously but record your findings as they pertain to each project into the findings folder inside of the docs folder forever repository and then please also update every projects road map.Md to kind of help me understand how it would be implementing all these ideas or if there's better ideas please let me know. Feel free to call multiple agents as needed
Show less
I'll help you perform a comprehensive code review of all three repositories, research integration strategies, and update the roadmaps. Let me start by exploring all three codebases simultaneously.
Task:Explore basset-hound repository
IN
Thoroughly explore the ~/basset-hound repository. I need a comprehensive code review including:
1. Overall architecture and structure
2. Key features and functionality
3. Database schema and data models
4. API endpoints and interfaces
5. Current integration points or extensibility
6. Find and read the docs/ROADMAP.md or any roadmap file
7. Identify any existing docs folder structure
8. Technology stack used
9. Current state of completion
10. Any existing integration mechanisms

Please be very thorough - read key files, understand the data flow, and document everything you find.
Task:Explore autofill-extension repo
IN
Thoroughly explore the ~/autofill-extension repository. I need a comprehensive code review including:
1. Overall architecture and structure
2. Key features and functionality - especially around data field detection and ingestion
3. How it detects and parses data fields (crypto addresses, emails, phones)
4. Current validation/verification mechanisms
5. Screenshot and element selection capabilities
6. Find and read any docs/ROADMAP.md or roadmap file
7. Identify the docs folder structure
8. Technology stack (browser extension APIs used)
9. Current state of completion
10. Any existing integration mechanisms with external systems
11. How it captures URLs and dates

Please be very thorough - read key files, understand the data flow, and document everything you find.
Task:Explore basset-hound-browser
IN
Thoroughly explore the ~/basset-hound-browser repository. I need a comprehensive code review including:
1. Overall architecture and structure
2. Key features and functionality
3. Browser capabilities (is it Electron, custom browser, etc?)
4. How it integrates with other tools/extensions
5. OSINT agent capabilities if any
6. Automation features
7. Find and read any docs/ROADMAP.md or roadmap file
8. Identify the docs folder structure
9. Technology stack used
10. Current state of completion
11. Extension/plugin system if any
12. API or IPC mechanisms for external communication

Please be very thorough - read key files, understand the data flow, and document everything you find.
Task:Research data verification APIs
IN
Research and document findings about verification methods for OSINT data validation:

1. **Cryptocurrency Address Validation:**
   - Algorithms for validating Bitcoin, Ethereum, and other major crypto addresses (checksum validation)
   - Free/open APIs for checking if addresses exist on blockchain (have transactions)
   - Libraries available for address validation in JavaScript/TypeScript

2. **Email Verification:**
   - MX record lookup methods
   - SMTP verification techniques (without sending emails)
   - Email format validation regex patterns
   - Free APIs or libraries for email verification
   - Rate limiting considerations

3. **Phone Number Verification:**
   - libphonenumber and similar libraries
   - Format validation by country
   - Carrier lookup APIs
   - Plausibility checks

4. **Domain/WHOIS Verification:**
   - WHOIS lookup APIs and libraries
   - DNS verification methods
   - Domain existence checks

Please provide practical implementation recommendations with specific library names, API endpoints, and code examples where helpful. Focus on methods that can work client-side in a browser extension AND server-side for more thorough verification.
I've launched 4 agents in parallel to explore all three repositories and research verification APIs. Let me wait for their results to complete.
Update Todos

Explore and review basset-hound repository

Explore and review autofill-extension repository

Explore and review basset-hound-browser repository

Research data verification APIs and methods

Document research findings in each repository's docs folder

Update ROADMAP.md for basset-hound

Update ROADMAP.md for autofill-extension

Update ROADMAP.md for basset-hound-browser

Create integration architecture document
Good, the agents are making progress. Let me check on their status.
TaskOutput task: "a6311ae"
OUT
<retrieval_status>timeout</retrieval_status>

<task_id>a6311ae</task_id>

<task_type>local_agent</task_type>

<status>running</status>

<output>
[Tool: Bash] {"command":"find /home/devel/basset-hound -type f -name \"*.md\" | head -20","description":"Find markdown documentation files"}
[Tool: Bash] {"command":"ls -la /home/devel/basset-hound/","description":"List root directory contents"}
[Tool: Bash] {"command":"find /home/devel/basset-hound -maxdepth 3 -type d | sort","description":"Show directory structure"}
[Tool: Bash] {"command":"find /home/devel/basset-hound -maxdepth 3 -type d | sort","description":"Show directory structure"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/README.md"}
[Tool: Bash] {"command":"find /home/devel/basset-hound -type f \\( -name \"*ROADMAP*\" -o -name \"*roadmap*\" -o -name \"*PLAN*\" -o -name \"*plan*\" \\)","description":"Search for roadmap or plan files"}
[Tool: Bash] {"command":"ls -la /home/devel/basset-hound/docs/","description":"List documentation directory"}
[Tool: Bash] {"command":"ls -la /home/devel/basset-hound/docs/","description":"List documentation directory"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/docs/ROADMAP.md"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/app.py"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/main.py"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/main.py"}
[Tool: Bash] {"command":"find /home/devel/basset-hound/api -type f -name \"*.py\" | head -30","description":"List Python files in API directory"}
[Tool: Bash] {"command":"wc -l /home/devel/basset-hound/neo4j_handler.py /home/devel/basset-hound/api/main.py /home/devel/basset-hound/app.py","description":"Count lines in key files"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/requirements.txt"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/requirements.txt"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/api/main.py"}
[Tool: Bash] {"command":"ls -la /home/devel/basset-hound/api/routers/","description":"List API routers"}
[Tool: Bash] {"command":"ls -la /home/devel/basset-hound/api/models/","description":"List API models"}
[Tool: Bash] {"command":"ls -la /home/devel/basset-hound/api/models/","description":"List API models"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/neo4j_handler.py","limit":150}
[Tool: Bash] {"command":"head -100 /home/devel/basset-hound/data_config.yaml","description":"Show data configuration schema"}
[Tool: Bash] {"command":"head -100 /home/devel/basset-hound/data_config.yaml","description":"Show data configuration schema"}
[Tool: Bash] {"command":"find /home/devel/basset-hound/api/services -name \"*.py\" | sort | xargs wc -l | tail -1","description":"Count total lines in services"}
[Tool: Bash] {"command":"ls -lh /home/devel/basset-hound/basset_mcp/","description":"Check MCP directory"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/docker-compose.yml"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/docker-compose.yml"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/basset_mcp/server.py","limit":200}
[Tool: Bash] {"command":"grep -r \"def \" /home/devel/basset-hound/api/routers/__init__.py | head -20","description":"Check API router structure"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/api/routers/__init__.py"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/api/routers/__init__.py"}
[Tool: Bash] {"command":"find /home/devel/basset-hound/tests -name \"test_*.py\" | wc -l","description":"Count test files"}
[Tool: Bash] {"command":"ls -1 /home/devel/basset-hound/docs/findings/ | head -15","description":"List phase documentation"}
[Tool: Bash] {"command":"head -100 /home/devel/basset-hound/install.sh","description":"Check installation script"}
[Tool: Bash] {"command":"head -100 /home/devel/basset-hound/install.sh","description":"Check installation script"}
[Tool: Bash] {"command":"head -200 /home/devel/basset-hound/docs/00-EXECUTIVE-SUMMARY.md","description":"Executive summary documentation"}
</output>
TaskOutput task: "a31c290"
OUT
<retrieval_status>timeout</retrieval_status>

<task_id>a31c290</task_id>

<task_type>local_agent</task_type>

<status>running</status>

<output>
[Tool: Bash] {"command":"find /home/devel -type d -name \"*autofill*\" 2>/dev/null | head -20","description":"Find autofill-extension directory"}
[Tool: Bash] {"command":"find /home/devel -type d -name \"*autofill*\" 2>/dev/null | head -20","description":"Find autofill-extension directory"}
[Tool: Glob] {"path":"/home/devel","pattern":"*autofill*"}
[Tool: Glob] {"path":"/home/devel","pattern":"*autofill*"}
[Tool: Read] {"file_path":"/home/devel/autofill-extension"}
[Tool: Read] {"file_path":"/home/devel/autofill-extension"}
[Tool: Bash] {"command":"ls -la /home/devel/ | head -20","description":"List home directory contents"}
[Tool: Bash] {"command":"ls -la /home/devel/ | head -20","description":"List home directory contents"}
[Tool: Bash] {"command":"ls -la","description":"List current directory contents"}
[Tool: Bash] {"command":"ls -la","description":"List current directory contents"}
[Tool: Bash] {"command":"ls -la /home/devel/autofill-extension 2>&1 | head -30","description":"List autofill-extension directory"}
[Tool: Bash] {"command":"ls -la /home/devel/autofill-extension 2>&1 | head -30","description":"List autofill-extension directory"}
[Tool: Glob] {"pattern":"**/extension/**"}
[Tool: Glob] {"pattern":"**/extension/**"}
[Tool: Read] {"file_path":"/home/devel"}
[Tool: Read] {"file_path":"/home/devel"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/README.md"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/README.md"}
[Tool: Bash] {"command":"pwd","description":"Show current working directory"}
[Tool: Bash] {"command":"pwd","description":"Show current working directory"}
[Tool: Bash] {"command":"ls -la /home/devel/","description":"List contents of /home/devel directory"}
[Tool: Bash] {"command":"ls -la /home/devel/","description":"List contents of /home/devel directory"}
[Tool: Glob] {"path":"/home/devel","pattern":"*"}
[Tool: Glob] {"path":"/home/devel","pattern":"*"}
[Tool: Read] {"file_path":"/home/devel/autofill-extension/README.md"}
[Tool: Read] {"file_path":"/home/devel/autofill-extension/README.md"}
[Tool: Read] {"file_path":"/home/devel/autofill_extension/README.md"}
[Tool: Read] {"file_path":"/home/devel/autofill_extension/README.md"}
[Tool: Read] {"file_path":"/home/devel/.autofill-extension/README.md"}
[Tool: Read] {"file_path":"/home/devel/.autofill-extension/README.md"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/docs/ROADMAP.md"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/docs/ROADMAP.md"}
[Tool: Grep] {"pattern":"autofill|auto.fill|field.detect|screenshot|element.select","path":"/home/devel/basset-hound","type":"py"}
[Tool: Grep] {"pattern":"autofill|auto.fill|field.detect|screenshot|element.select","path":"/home/devel/basset-hound","type":"py"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/docs"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/docs"}
[Tool: Glob] {"path":"/home/devel/basset-hound/docs","pattern":"*"}
[Tool: Glob] {"path":"/home/devel/basset-hound/docs","pattern":"*"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/docs/03-BROWSER-AUTOMATION-STRATEGY.md"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/docs/03-BROWSER-AUTOMATION-STRATEGY.md"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/docs/04-PENTESTING-INTEGRATION.md"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/docs/04-PENTESTING-INTEGRATION.md"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/docs/02-INTEGRATION-ARCHITECTURE.md","limit":150}
[Tool: Read] {"file_path":"/home/devel/basset-hound/docs/02-INTEGRATION-ARCHITECTURE.md","limit":150}
[Tool: Read] {"file_path":"/home/devel/basset-hound/api/utils/crypto_detector.py","limit":100}
[Tool: Read] {"file_path":"/home/devel/basset-hound/api/utils/crypto_detector.py","limit":100}
[Tool: Read] {"file_path":"/home/devel/basset-hound/api/services/orphan_service.py","limit":150}
[Tool: Read] {"file_path":"/home/devel/basset-hound/api/services/orphan_service.py","limit":150}
[Tool: Read] {"file_path":"/home/devel/basset-hound/api/services/normalizer.py","limit":120}
[Tool: Read] {"file_path":"/home/devel/basset-hound/api/services/normalizer.py","limit":120}
[Tool: Read] {"file_path":"/home/devel/basset-hound/api/services/data_import.py","limit":150}
[Tool: Read] {"file_path":"/home/devel/basset-hound/api/services/data_import.py","limit":150}
[Tool: Read] {"file_path":"/home/devel/basset-hound/api/main.py","limit":150}
[Tool: Read] {"file_path":"/home/devel/basset-hound/api/main.py","limit":150}
[Tool: Read] {"file_path":"/home/devel/basset-hound/api/services/graph_visualization.py","limit":100}
[Tool: Read] {"file_path":"/home/devel/basset-hound/api/services/graph_visualization.py","limit":100}
[Tool: Grep] {"pattern":"screenshot|capture|element.select|dom.interact","path":"/home/devel/basset-hound","type":"js","head_limit":20}
[Tool: Grep] {"pattern":"screenshot|capture|element.select|dom.interact","path":"/home/devel/basset-hound","type":"js","head_limit":20}
[Tool: Read] {"file_path":"/home/devel/basset-hound/api/services/data_import.py","offset":300,"limit":100}
[Tool: Read] {"file_path":"/home/devel/basset-hound/api/services/data_import.py","offset":300,"limit":100}
[Tool: Read] {"file_path":"/home/devel/basset-hound/data_config.yaml","limit":80}
</output>
TaskOutput task: "a3f57eb"
OUT
<retrieval_status>success</retrieval_status>

<task_id>a3f57eb</task_id>

<task_type>local_agent</task_type>

<status>completed</status>

<output>
[Tool: Bash] {"command":"find /home/devel/basset-hound -type f -name \"*.md\" | head -20","description":"Find markdown files in the repository"}
[Tool: Bash] {"command":"ls -la /home/devel/basset-hound/","description":"List root directory contents"}
[Tool: Bash] {"command":"find /home/devel/basset-hound -maxdepth 2 -type d | sort","description":"Find directory structure up to 2 levels deep"}
[Tool: Bash] {"command":"find /home/devel/basset-hound -maxdepth 2 -type d | sort","description":"Find directory structure up to 2 levels deep"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/README.md"}
[Tool: Bash] {"command":"ls -la /home/devel/basset-hound/docs/","description":"List documentation directory"}
[Tool: Bash] {"command":"ls -la /home/devel/basset-hound/api/","description":"List API directory structure"}
[Tool: Bash] {"command":"ls -la /home/devel/basset-hound/api/","description":"List API directory structure"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/docs/ROADMAP.md","limit":200}
[Tool: Read] {"file_path":"/home/devel/basset-hound/requirements.txt"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/main.py"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/app.py"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/app.py"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/api/main.py"}
[Tool: Bash] {"command":"ls -la /home/devel/basset-hound/api/routers/","description":"List API routers"}
[Tool: Bash] {"command":"ls -la /home/devel/basset-hound/api/services/","description":"List API services"}
[Tool: Bash] {"command":"ls -la /home/devel/basset-hound/basset_mcp/","description":"List MCP module"}
[Tool: Bash] {"command":"ls -la /home/devel/basset-hound/basset_mcp/","description":"List MCP module"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/basset_mcp/server.py","limit":200}
[Tool: Read] {"file_path":"/home/devel/basset-hound/neo4j_handler.py","limit":200}
[Tool: Bash] {"command":"ls -la /home/devel/basset-hound/api/routers/","description":"List API routers"}
[Tool: Bash] {"command":"ls -la /home/devel/basset-hound/api/routers/","description":"List API routers"}
[Tool: Bash] {"command":"find /home/devel/basset-hound/api/routers -type f -name \"*.py\" | xargs ls -lh","description":"List all router files"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/api/routers/__init__.py"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/api/config.py"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/api/config.py"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/docs/00-EXECUTIVE-SUMMARY.md"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/docs/01-REPOSITORY-ANALYSIS.md","limit":150}
[Tool: Read] {"file_path":"/home/devel/basset-hound/docs/01-REPOSITORY-ANALYSIS.md","limit":150}
[Tool: Read] {"file_path":"/home/devel/basset-hound/docker-compose.yml"}
[Tool: Bash] {"command":"find /home/devel/basset-hound/static -type f | head -20","description":"List static files"}
[Tool: Bash] {"command":"find /home/devel/basset-hound/templates -type f","description":"List template files"}
[Tool: Bash] {"command":"find /home/devel/basset-hound/templates -type f","description":"List template files"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/.env"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/Dockerfile"}
[Tool: Bash] {"command":"wc -l /home/devel/basset-hound/*.py /home/devel/basset-hound/api/services/*.py 2>/dev/null | tail -1","description":"Count lines of Python code"}
[Tool: Bash] {"command":"wc -l /home/devel/basset-hound/*.py /home/devel/basset-hound/api/services/*.py 2>/dev/null | tail -1","description":"Count lines of Python code"}
[Tool: Grep] {"pattern":"^def |^class |^async def","path":"/home/devel/basset-hound/api/routers","output_mode":"files_with_matches"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/api/models"}
[Tool: Bash] {"command":"ls -lh /home/devel/basset-hound/api/models/","description":"List model files"}
[Tool: Bash] {"command":"ls -lh /home/devel/basset-hound/api/models/","description":"List model files"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/api/models/entity.py"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/api/routers/orphan.py","limit":150}
[Tool: Bash] {"command":"head -100 /home/devel/basset-hound/api/routers/projects.py","description":"Read project router"}
[Tool: Bash] {"command":"head -100 /home/devel/basset-hound/api/routers/projects.py","description":"Read project router"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/docs/02-INTEGRATION-ARCHITECTURE.md","limit":100}
[Tool: Read] {"file_path":"/home/devel/basset-hound/docs/ROADMAP.md","limit":100,"offset":200}
[Tool: Bash] {"command":"grep -r \"TODO\\|FIXME\\|XXX\" /home/devel/basset-hound/*.py | head -20","description":"Find TODOs in codebase"}
[Tool: Bash] {"command":"grep -r \"TODO\\|FIXME\\|XXX\" /home/devel/basset-hound/*.py | head -20","description":"Find TODOs in codebase"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/todo.md","limit":300}
[Tool: Read] {"file_path":"/home/devel/basset-hound/todo.md","limit":300}

--- RESULT ---
Excellent! Now I have gathered comprehensive information. Let me create a detailed code review document based on all the information collected.

## Comprehensive Code Review: Basset Hound OSINT Platform

---

### 1. OVERALL ARCHITECTURE AND STRUCTURE

**Type:** API-First OSINT Investigation Platform (NOT a Browser)

**Basset Hound is NOT an Electron app, custom browser, or web browser.** It is a **graph-based entity relationship management engine** designed to backend OSINT investigations. The architecture consists of:

#### Core Architecture:
```
┌─────────────────────────────────────────────────────────────┐
│                      Basset Hound                            │
├─────────────────────────────────────────────────────────────┤
│  FastAPI (REST API)  │  Flask (Web UI)  │  MCP Server       │
├─────────────────────────────────────────────────────────────┤
│                     Services Layer                           │
│  • Entity Management    • Orphan Data    • Graph Analysis   │
│  • Auto-Linking         • Search         • Timeline         │
│  • Bulk Operations      • Reports        • Cache            │
├─────────────────────────────────────────────────────────────┤
│                     Neo4j Graph Database                     │
│  Entities (Person, Org, Device, etc.) + Relationships        │
└─────────────────────────────────────────────────────────────┘
```

#### Directory Structure:
```
basset-hound/
├── api/                           # FastAPI application (primary)
│   ├── main.py                   # FastAPI app factory with lifespan
│   ├── config.py                 # Settings with Pydantic
│   ├── dependencies.py           # Dependency injection
│   ├── auth/                     # Authentication modules
│   ├── models/                   # Pydantic data models (13 files)
│   │   ├── entity.py             # Entity/Person models
│   │   ├── orphan.py             # Orphan data models
│   │   ├── relationship.py       # Relationship models
│   │   └── ...
│   ├── routers/                  # API endpoints (40 routers)
│   │   ├── projects.py           # Project CRUD
│   │   ├── entities.py           # Entity CRUD
│   │   ├── orphan.py             # Orphan data management
│   │   ├── search.py             # Full-text search
│   │   ├── graph.py              # Graph visualization
│   │   ├── analysis.py           # Graph analysis (paths, clustering)
│   │   ├── relationships.py      # Relationship management
│   │   ├── auto_linker.py        # Automatic entity linking
│   │   ├── import_data.py        # OSINT tool data import
│   │   ├── export.py             # Report export (PDF, HTML, Markdown)
│   │   ├── webhooks.py           # Webhook integrations
│   │   ├── saved_search.py       # Saved search configurations
│   │   ├── graph_analytics.py    # Advanced analytics
│   │   ├── data_quality.py       # Data quality scoring
│   │   ├── deduplication.py      # Duplicate detection
│   │   └── ... (37 more routers)
│   ├── services/                 # Business logic (40+ services)
│   │   ├── neo4j_service.py      # Neo4j wrapper
│   │   ├── orphan_service.py     # Orphan data logic
│   │   ├── search_service.py     # Full-text search impl
│   │   ├── graph_visualization.py # Graph formatting
│   │   ├── deduplication.py      # Duplicate logic
│   │   ├── auto_linker.py        # Entity linking logic
│   │   ├── ml_analytics.py       # ML-based suggestions
│   │   ├── normalizer_v2.py      # Conservative data normalization
│   │   ├── graph_analytics.py    # Community detection, influence
│   │   ├── timeline_service.py   # Temporal tracking
│   │   ├── webhook_service.py    # Webhook execution
│   │   └── ... (30+ more services)
│   └── tasks/                    # Celery background jobs
├── basset_mcp/                   # MCP server for AI integration
│   └── server.py                 # FastMCP implementation (56KB)
├── app.py                        # Legacy Flask app (for backwards compat)
├── neo4j_handler.py              # Neo4j connection & schema (100KB)
├── profiles.py                   # Legacy profile blueprint
├── reports.py                    # Legacy reports blueprint
├── config_loader.py              # YAML schema loader
├── docker-compose.yml            # Neo4j + Redis + Celery setup
├── Dockerfile                    # Multi-stage production build
├── main.py                       # Entry point (starts FastAPI + MCP)
├── requirements.txt              # Dependencies
├── data_config.yaml              # Dynamic schema definition (~71KB)
├── static/                       # Frontend assets
│   ├── js/                       # 13 JavaScript modules
│   │   ├── api.js               # Fetch wrapper
│   │   ├── dashboard.js         # App initialization
│   │   ├── ui-form-handlers.js  # Dynamic forms
│   │   ├── ui-person-details.js # Profile rendering
│   │   ├── tag-handler.js       # Relationships
│   │   ├── report-handler.js    # Report generation
│   │   └── ...
│   ├── css/                      # Bootstrap + custom CSS
│   └── imgs/                     # Logos and assets
├── templates/                    # Jinja2 HTML templates
│   ├── dashboard.html            # Main UI
│   ├── index.html               # Landing page
│   └── ...
├── docs/                         # Comprehensive documentation
│   ├── ROADMAP.md               # Development roadmap (86KB)
│   ├── 00-EXECUTIVE-SUMMARY.md  # Integration analysis
│   ├── 01-REPOSITORY-ANALYSIS.md # Detailed findings
│   ├── 02-INTEGRATION-ARCHITECTURE.md
│   ├── 03-BROWSER-AUTOMATION-STRATEGY.md
│   ├── ADVANCED_SEARCH_IMPLEMENTATION.md
│   ├── GRAPH_VISUALIZATION_API.md
│   └── findings/                 # Phase-specific documentation
├── tests/                        # Pytest test suite
└── projects/                     # Project file storage

```

---

### 2. KEY FEATURES AND FUNCTIONALITY

#### Core OSINT Capabilities:

| Feature | Implementation | Status |
|---------|-----------------|--------|
| **Entity Management** | Full CRUD with dynamic profiles | ✅ Complete |
| **Orphan Data Management** | Store unlinked identifiers (emails, phones, crypto) | ✅ Complete |
| **Graph Relationships** | 26+ relationship types, bidirectional, transitive | ✅ Complete |
| **Full-Text Search** | Boolean operators, field-specific, fuzzy matching | ✅ Complete |
| **Graph Visualization** | D3.js, vis.js, Cytoscape.js formats | ✅ Complete |
| **Auto-Linking** | Fuzzy matching with entity suggestion | ✅ Complete |
| **Deduplication** | Duplicate detection and resolution | ✅ Complete |
| **Data Quality** | Entity scoring and ambiguity flagging | ✅ Complete |
| **Timeline Analysis** | Temporal tracking of entity/relationship changes | ✅ Complete |
| **Graph Analytics** | Community detection, centrality, influence | ✅ Complete |
| **ML Analytics** | Query suggestions, TF-IDF, similarity scoring | ✅ Complete |
| **Cross-Project Linking** | Entity linking across investigations | ✅ Complete |
| **Report Generation** | Markdown, HTML, PDF export | ✅ Complete |
| **Webhook Integrations** | External notifications | ✅ Complete |
| **Saved Searches** | Reusable query configurations | ✅ Complete |
| **Import/Export** | JSON, CSV, JSONL, Maltego, SpiderFoot, Shodan, HIBP | ✅ Complete |
| **Data Normalization** | Conservative v2 with ambiguity detection | ✅ Complete |
| **Template Management** | Custom report templates | ✅ Complete |
| **Marketplace** | Community template sharing | ✅ Complete |
| **Scheduled Reports** | Periodic report generation | ✅ Complete |
| **Caching Layer** | Redis + in-memory cache | ✅ Complete |
| **Job Runner** | Background async task execution | ✅ Complete |
| **Audit Logging** | Change tracking for debugging | ✅ Complete |

#### Identifier Types Supported:
- EMAIL, PHONE, USERNAME, URL, IP_ADDRESS, CRYPTO_ADDRESS, MAC_ADDRESS, DOMAIN, CREDIT_CARD, SSN, PASSPORT, DRIVER_LICENSE, BANK_ACCOUNT, IMEI, IMSI, ICCID, CUSTOM

#### Entity Types:
- Person, Organization, Device, Location, Event, Document, Cryptocurrency Wallet, IP Address, Domain, and custom types

#### Data Import Sources:
- Maltego, SpiderFoot, TheHarvester, Shodan, HIBP (Have I Been Pwned), Custom CSV/JSON

---

### 3. BROWSER CAPABILITIES

**ANSWER: Basset Hound is NOT a Browser.** 

Basset Hound does **NOT**:
- Render web pages
- Execute JavaScript in a browser context
- Perform automated web scraping
- Handle authentication flows
- Bypass bot detection

Instead, Basset Hound:
- **Stores OSINT data** - Entities, relationships, evidence
- **Analyzes relationships** - Graph algorithms for pattern discovery
- **Manages investigations** - Projects, timelines, reports
- **Integrates with tools** - Via REST API and MCP protocol
- **Serves as a backend** - For AI agents, extensions, and other tools

**Integration with Browsers:**
- Designed to be called by browser extensions (e.g., `autofill-extension`)
- Can receive data from browser tools via webhooks
- Stores evidence (screenshots, HTML, etc.) uploaded from browser

---

### 4. INTEGRATION WITH OTHER TOOLS/EXTENSIONS

#### **MCP (Model Context Protocol) Integration:**
- **Server Location:** `/home/devel/basset-hound/basset_mcp/server.py` (56KB)
- **Protocol:** FastMCP-based (FastAPI for MCP)
- **Tool Categories:**
  - Schema introspection (`get_schema`, `get_sections`, `get_identifiers`)
  - Project management (`create_project`, `list_projects`, `delete_project`)
  - Entity operations (`create_entity`, `get_entity`, `update_entity`, `delete_entity`)
  - Orphan data (`create_orphan`, `link_orphan`, `get_suggestions`)
  - Search (`search_entities`, `search_orphans`)
  - Relationships (`link_entities`, `get_related`)
  - Reports (`generate_report`, `export_report`)
  - Graph analysis (`path_finding`, `centrality`)
  - Data import (`import_entities_batch`)
  - Configuration management

#### **REST API Integration:**
- **Base URL:** `http://localhost:8000`
- **OpenAPI Docs:** `/docs` (auto-generated Swagger UI)
- **ReDoc:** `/redoc`
- **40+ API Routers** providing 100+ endpoints

#### **Webhook Support:**
- POST to external services on entity/relationship changes
- Retry logic with exponential backoff
- Webhook templates for common platforms

#### **Authentication:**
- Optional JWT-based auth (currently disabled in development)
- API key support planned
- CORS middleware for cross-origin requests

#### **Known Integrations:**
- **palletAI** - Agent orchestration system (separate repo)
- **osint-resources** - Knowledge base (separate repo, 14,000+ lines)
- **autofill-extension** - Browser automation prototype (separate repo)
- Custom Python scripts via REST API
- LLM agents via MCP protocol

---

### 5. OSINT AGENT CAPABILITIES

Basset Hound provides these capabilities for OSINT agents:

#### **Entity-Focused Workflow:**
1. **Create Project** - Start new investigation
2. **Store Orphan Data** - Capture fragments without assignment
3. **Search & Link** - Find matches, merge data
4. **Track Relationships** - Build connection graphs
5. **Generate Reports** - Export findings

#### **MCP Tools for AI Agents:**

```python
# Schema Discovery
get_schema()                          # Full schema
get_sections()                        # Section definitions
get_identifiers()                     # Identifier fields

# Entity Management
create_entity(project, profile)       # Create entity
get_entity(project, entity_id)        # Fetch entity
update_entity(project, entity_id, profile)
delete_entity(project, entity_id)
list_entities(project)                # All entities

# Orphan Data (Key for "Collect Now, Connect Later")
create_orphan(project, identifier_type, value, metadata)
get_orphan_suggestions(project, orphan_id)  # Get entity matches
link_orphan(project, orphan_id, entity_id)  # Merge into entity
search_orphans(project, query)

# Relationships
link_entities(project, source_id, target_id, type)
get_related_entities(project, entity_id, depth=2)
get_transitive_relationships(project, entity_id)

# Search
search_entities(project, query)       # Full-text search
search_by_identifier(project, type, value)

# Reports
generate_report(project, entity_id)   # Markdown report
export_report(project, format="pdf")  # Multi-format export

# Graph Analysis
find_paths(project, source_id, target_id)
centrality_analysis(project)          # Node importance
community_detection(project)          # Clustering

# Data Management
import_entities_batch(project, data)  # Bulk import
export_entities(project, format)      # Bulk export
```

#### **OSINT Data Flow:**
1. **Discovery Phase:** Agent finds identifiers → Store as orphan data
2. **Connection Phase:** Agent matches patterns → Link orphans to entities
3. **Analysis Phase:** Agent queries relationships → Find patterns/clusters
4. **Reporting Phase:** Agent exports findings → Generate reports

---

### 6. AUTOMATION FEATURES

#### **Built-In Automation:**

| Feature | Implementation | Status |
|---------|-----------------|--------|
| **Auto-Linking** | Fuzzy matching engine with configurable thresholds | ✅ |
| **Auto-Deduplication** | Duplicate detection across entities | ✅ |
| **Background Jobs** | Celery + Redis for async tasks | ✅ |
| **Scheduled Reports** | Celery Beat for periodic execution | ✅ |
| **Data Normalization** | Conservative v2 with hint support | ✅ |
| **Change Tracking** | Audit log of all modifications | ✅ |
| **Bulk Operations** | Batch import/export/update | ✅ |
| **Data Quality Scoring** | Automatic scoring of entity data | ✅ |
| **ML Suggestions** | Query suggestions based on history | ✅ |
| **Cache Management** | Redis-backed caching with TTLs | ✅ |

#### **Job Runner Service:**
- Executes background tasks
- Memory-limited (configurable job/result limits)
- Support for async/await patterns
- Job status tracking

#### **Scheduler Service:**
- Periodic task execution
- Cron-like scheduling
- Report generation
- Cleanup tasks

#### **Celery Integration:**
- Distributed task queue
- Worker processes for concurrent execution
- Beat for scheduled tasks
- Redis backend for task state

---

### 7. DOCUMENTATION

#### **Main Documentation:**
- **README.md** - Quick start and overview
- **ROADMAP.md** - 86KB comprehensive development roadmap
- **docs/00-EXECUTIVE-SUMMARY.md** - Integration analysis
- **docs/01-REPOSITORY-ANALYSIS.md** - Detailed tech findings
- **docs/02-INTEGRATION-ARCHITECTURE.md** - System architecture
- **docs/03-BROWSER-AUTOMATION-STRATEGY.md** - Browser extension plans
- **docs/04-PENTESTING-INTEGRATION.md** - Security testing integration
- **docs/05-IMPLEMENTATION-ROADMAP.md** - Detailed implementation plan
- **docs/ADVANCED_SEARCH_IMPLEMENTATION.md** - Search feature details
- **docs/GRAPH_VISUALIZATION_API.md** - Graph visualization specs
- **docs/SEARCH_SYNTAX_QUICK_REFERENCE.md** - Search query syntax

#### **Phase Documentation (findings/ folder):**
Detailed findings for 25+ phases of development:
- Phase 4-7: Implementation foundations
- Phase 9-10: Advanced features
- Phase 11: Production hardening
- Phase 12: Performance & scalability
- Phase 14: Enterprise features
- Phase 15: Orphan data normalization
- Phase 17-18: Frontend & analytics
- Phase 19: Deployment infrastructure
- Phase 22-23: API endpoints & saved searches
- Phase 24-25: Webhooks & deduplication

---

### 8. TECHNOLOGY STACK

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| **Backend** | FastAPI | 0.115+ | REST API (primary) |
| **Backend** | Flask | 3.1.0 | Web UI (legacy, maintained) |
| **Web Server** | Uvicorn | 0.32+ | ASGI server |
| **Database** | Neo4j | 5.28 | Graph database |
| **Cache** | Redis | 7 | Caching & task queue |
| **Task Queue** | Celery | Latest | Background jobs |
| **Python Version** | Python | 3.12+ | Runtime |
| **Data Validation** | Pydantic | 2.10+ | Type safety |
| **ORM/Driver** | neo4j-driver | 5.28.1 | Neo4j connection |
| **AI Protocol** | FastMCP | 1.0+ | LLM integration |
| **Search** | Neo4j FTS | Built-in | Full-text search |
| **Frontend** | Vanilla JS | ES6 | Dynamic UI |
| **Frontend** | Bootstrap | 5.3 | Styling |
| **Frontend** | Cytoscape.js | Latest | Graph visualization |
| **Frontend** | D3.js | Latest | Data viz |
| **Frontend** | vis.js | Latest | Network graphs |
| **Config** | YAML | 6.0.2 | Schema definition |
| **Deployment** | Docker | Latest | Containerization |
| **Testing** | Pytest | 8.3+ | Unit tests |

#### **Key Dependencies:**
- `python-jose[cryptography]` - JWT tokens
- `passlib[bcrypt]` - Password hashing
- `markdown` - Report generation
- `aiofiles` - Async file operations
- `python-magic` - File type detection
- `httpx` - HTTP client
- `rapidfuzz` - Fuzzy matching
- `pydantic-settings` - Configuration management

---

### 9. CURRENT STATE OF COMPLETION

#### **Production-Ready Components:**
- ✅ **FastAPI Migration** - Complete with 40+ routers
- ✅ **Database** - Neo4j with schema, constraints, indexes
- ✅ **Core CRUD** - Projects, entities, relationships, files
- ✅ **Search** - Full-text search with Boolean operators
- ✅ **Graph Analysis** - Path finding, centrality, clustering
- ✅ **Orphan Data** - Store-now-link-later workflow
- ✅ **Auto-Linking** - Fuzzy matching with scoring
- ✅ **MCP Server** - FastMCP-based AI integration
- ✅ **Web UI** - Dashboard with dynamic forms
- ✅ **REST API** - OpenAPI documentation
- ✅ **Data Import** - Multiple OSINT tool formats
- ✅ **Report Export** - PDF, HTML, Markdown
- ✅ **Caching** - Redis + in-memory
- ✅ **Job Queue** - Celery with Beat scheduler
- ✅ **Data Quality** - Normalization, deduplication, scoring
- ✅ **Timeline Analysis** - Temporal tracking
- ✅ **Webhooks** - External integrations

#### **Advanced Features (Completed):**
- ✅ **Graph Analytics** - Community detection, influence propagation
- ✅ **ML Analytics** - Query suggestions, TF-IDF, co-occurrence
- ✅ **Cross-Project Linking** - Entity deduplication across projects
- ✅ **Saved Searches** - Reusable query configurations
- ✅ **Template System** - Custom report templates
- ✅ **Marketplace** - Template sharing platform
- ✅ **Data Normalization v2** - Conservative with ambiguity detection
- ✅ **Change Audit Log** - Full change tracking

#### **In Development / Recent:**
- 🔄 **Phase 26** - Conservative data normalization with hint support
- 🔄 **Documentation** - Comprehensive phase documentation
- 🔄 **Testing** - Test suite expansion

#### **Not Implemented:**
- ❌ **Browser Automation** - Not in scope (separate tool)
- ❌ **Multi-User** - Single-user trusted environment
- ❌ **Enterprise Auth** - OAuth2, SAML (planned but disabled)
- ❌ **UI-First Focus** - API-first design priority

---

### 10. EXTENSION/PLUGIN SYSTEM

**Basset Hound uses a declarative extension model via `data_config.yaml`:**

#### **Configuration-Driven Schema:**
Users can add custom entity types, fields, and sections **without code changes**:

```yaml
sections:
  - id: custom_section
    name: My Custom Data
    icon: fa-cog
    sensitive: false
    fields:
      - id: custom_field
        type: string                      # Supports 20+ field types
        label: Custom Field
        identifier: true                  # Use for matching
        searchable: true                  # Include in full-text search
        pattern: "^[A-Z]{3}\\d{3}$"      # Validation regex
        required: false
        multiple: true                    # Allow multiple values
        components:                       # Nested structure support
          - id: subfield
            type: string

field_types:
  string: { html_input: text }
  email: { html_input: email }
  phone: { html_input: tel }
  date: { html_input: date }
  url: { html_input: url }
  select: { html_input: select, options: [...] }
  component: { html_input: fieldset }
  # ... 14+ more field types
```

#### **Frontend Component Generation:**
The UI automatically generates forms based on schema without hardcoding.

#### **MCP Tool Introspection:**
Agents can discover available schema:
```python
get_schema()      # Full schema
get_sections()    # Sections with fields
get_identifiers() # Identifier fields
```

#### **No Plugin System:**
Basset Hound doesn't use plugins. Instead:
- **Custom Fields** → Add to `data_config.yaml`
- **Custom Integration** → Call REST API or MCP tools
- **Custom Logic** → Subclass services or write Python scripts

---

### 11. API/IPC MECHANISMS FOR EXTERNAL COMMUNICATION

#### **1. REST API (Primary)**
- **Base URL:** `http://localhost:8000/api/v1`
- **Authentication:** Optional JWT (currently disabled)
- **CORS:** Enabled (configurable)
- **Documentation:** Auto-generated at `/docs` (Swagger) and `/redoc` (ReDoc)

#### **2. MCP Protocol (Secondary)**
- **Type:** Stdio-based Model Context Protocol
- **Location:** Subprocess launched by `main.py`
- **Port:** stdio pipes (no network port)
- **Tools:** 15+ tools for entity management, search, graph analysis
- **Clients:** LLMs and AI agents

#### **3. WebSocket (Real-Time)**
- **Endpoint:** `/ws` (documented in websocket router)
- **Use Cases:** Real-time notifications, live data updates
- **Implementation:** `websocket_service.py`

#### **4. Webhooks (Outbound)**
- **Use Case:** Notify external systems of changes
- **Implementation:** `webhook_service.py`
- **Features:**
  - Event filtering (entity.created, entity.updated, relationship.added)
  - Retry logic with exponential backoff
  - Custom headers and payload templates

#### **5. File System (Event-Based)**
- **Projects Directory:** `./projects/{project_id}/`
- **File Storage:** Per-entity file uploads
- **Reports:** Markdown reports exported to files

#### **6. Background Jobs (Celery)**
- **Broker:** Redis
- **Task Queue:** Async job execution
- **Use Cases:** Bulk import/export, scheduled reports, background analysis
- **Endpoints:** `/api/v1/jobs/` for job management

#### **API Endpoint Categories:**

| Category | Routers | Endpoints |
|----------|---------|-----------|
| Projects | projects | Create, read, update, delete, list |
| Entities | entities | CRUD for people/persons |
| Orphans | orphan | Store, link, deduplicate orphan data |
| Relationships | relationships | Create/delete/list entity relationships |
| Search | search | Full-text search, fuzzy matching |
| Graph | graph | Visualization formats (D3, vis.js, Cytoscape) |
| Analysis | analysis | Path finding, centrality, clustering |
| Auto-Link | auto_linker | Automatic entity linking |
| Import | import_data | OSINT tool data import |
| Export | export | Report generation & export |
| Files | files | File upload/download |
| Reports | reports | Report CRUD and generation |
| Timeline | timeline | Temporal tracking and visualization |
| Webhooks | webhooks | Webhook management |
| Saved Searches | saved_search | Save/load search configurations |
| Graph Analytics | graph_analytics | Community detection, influence |
| Data Quality | data_quality | Quality scoring, ambiguity detection |
| Deduplication | deduplication | Duplicate detection & merging |
| Cross-Project | cross_project | Entity linking across projects |
| Jobs | jobs | Background task management |
| Config | config | Schema & configuration endpoints |
| And 20+ more... | ... | ... |

---

### 12. CODE QUALITY & ARCHITECTURE OBSERVATIONS

#### **Strengths:**
- ✅ **Well-Organized Structure** - Clear separation of concerns (routers, services, models)
- ✅ **Type Safety** - Comprehensive Pydantic models for all data
- ✅ **Documentation** - Extensive docs with phase-based development tracking
- ✅ **Modern Stack** - FastAPI, async/await, Neo4j graph database
- ✅ **Scalability** - Redis caching, Celery jobs, connection pooling
- ✅ **Configuration-Driven** - YAML schema without code changes
- ✅ **API First** - OpenAPI documentation, REST + MCP protocols
- ✅ **Conservative Data Handling** - v2 normalizer preserves raw data
- ✅ **Graph Database** - Neo4j for powerful relationship queries
- ✅ **Integration Ready** - MCP, webhooks, multiple export formats

#### **Areas for Improvement:**
- ⚠️ **Legacy Flask Code** - Parallel Flask app may create confusion; consider removing
- ⚠️ **Service Layer Size** - Some services are quite large (>40KB); consider breaking down
- ⚠️ **Documentation Density** - Excellent docs, but scattered across many files
- ⚠️ **Error Handling** - Could be more consistent across services
- ⚠️ **Testing Coverage** - Basic test suite; needs expansion for critical paths
- ⚠️ **Performance Indexes** - Could add more composite indexes for common queries
- ⚠️ **Rate Limiting** - No API rate limiting implemented (important for production)
- ⚠️ **Input Validation** - Could add stricter validation for all inputs

#### **Technical Debt:**
- Multiple normalizer versions (v1 and v2) - v1 still exists
- Legacy `app.py` Flask code duplicates FastAPI logic
- Some routers combine routing with business logic
- Constants scattered (country codes, crypto patterns, etc.)

---

### 13. CURRENT DEVELOPMENT PHASE

**Currently in: Phase 26 - Conservative Data Normalization**

The system is tracking:
- Raw data preservation
- Ambiguity detection
- Hint-based disambiguation
- International support (phones, dates, currency)
- Integration with data quality service

Recent work shows focus on:
1. Making data normalization more robust
2. Handling international formats correctly
3. Flagging ambiguous data for human review
4. Adding contextual hints for resolution

---

### 14. DEPLOYMENT & INFRASTRUCTURE

#### **Docker-Based Deployment:**
- **Multi-stage build** - Optimized production image
- **Containers:**
  - Neo4j 5.28 (Graph database)
  - Redis 7 (Cache & task broker)
  - basset_api (FastAPI + MCP on port 8000)
  - celery_worker (Background job processing)
  - celery_beat (Scheduled tasks)

#### **Environment Configuration:**
- Neo4j credentials configurable via env
- FastAPI host/port configurable
- Redis URL configurable
- Cache TTLs configurable
- Memory limits for various services configurable

#### **Health Checks:**
- HTTP health check endpoint at `/health`
- Neo4j health check in docker-compose
- Redis health check in docker-compose
- Liveness/readiness for Kubernetes

---

### 15. SECURITY CONSIDERATIONS

#### **Current State:**
- ✅ No hardcoded credentials (uses environment variables)
- ✅ Non-root container user
- ✅ CORS headers configurable
- ✅ Optional JWT authentication framework
- ❌ Authentication currently disabled (development mode)
- ❌ No rate limiting
- ❌ No input sanitization for Neo4j queries (parameterized queries used, but worth auditing)

#### **Recommendations:**
1. Enable authentication for production
2. Add rate limiting middleware
3. Implement API key rotation
4. Add query parameter validation
5. Consider request signing for webhook callbacks
6. Audit all Neo4j query parameters

---

## SUMMARY

**Basset Hound** is a **mature, production-ready OSINT entity relationship management platform** built on modern Python technology. It's **NOT a browser** but rather a sophisticated graph database backend designed to:

1. **Store fragmented OSINT data** before knowing relationships
2. **Discover connections** through graph analysis and fuzzy matching
3. **Serve as an API** for AI agents, extensions, and other tools
4. **Generate reports** and export findings in multiple formats

The codebase demonstrates:
- Strong architecture with clear separation of concerns
- Comprehensive feature set (26+ OSINT capabilities)
- Active development (Phase 26 in progress)
- Excellent documentation
- Production-ready deployment setup

The platform is ideal for:
- OSINT investigations with relationship discovery
- Threat intelligence collection and analysis
- Data breach correlation
- Social network analysis
- Integration with AI agents via MCP
- Extension development (browser, CLI, etc.)

**Total Codebase:** ~100,000+ lines of Python code across services, routers, and utilities, with comprehensive documentation covering 25+ development phases.
</output>
TaskOutput task: "a6f0bd3"
OUT
<retrieval_status>timeout</retrieval_status>

<task_id>a6f0bd3</task_id>

<task_type>local_agent</task_type>

<status>running</status>

<output>
[Tool: WebSearch] {"query":"Bitcoin Ethereum address validation checksum algorithm JavaScript library 2025"}
[Tool: WebSearch] {"query":"email verification MX record SMTP validation JavaScript library 2025"}
[Tool: WebSearch] {"query":"libphonenumber JavaScript phone number validation library 2025"}
[Tool: WebSearch] {"query":"WHOIS lookup API free domain verification JavaScript 2025"}
[Tool: WebSearch] {"query":"WHOIS lookup API free domain verification JavaScript 2025"}
[Tool: Glob] {"pattern":"**/*.{ts,js,md}","path":"/home/devel/basset-hound"}
[Tool: Glob] {"pattern":"**/*.{ts,js,md}","path":"/home/devel/basset-hound"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/docs/findings/04-CRYPTO-DETECTION.md"}
[Tool: Glob] {"pattern":"**/*valid*.{ts,js,py}","path":"/home/devel/basset-hound"}
[Tool: Glob] {"pattern":"**/*verif*.{ts,js,py}","path":"/home/devel/basset-hound"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/api/utils/crypto_detector.py"}
[Tool: Glob] {"pattern":"**/*.py","path":"/home/devel/basset-hound"}
[Tool: Grep] {"pattern":"email.*valid|phone.*valid|domain.*valid|whois|MX.*record","-i":true,"path":"/home/devel/basset-hound","output_mode":"files_with_matches"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/docs/ROADMAP.md"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/docs/ROADMAP.md"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/api/services/normalizer.py"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/todo.md"}
</output>
I have results from the basset-hound-browser exploration. Let me wait for the remaining agents to complete and check on their status.
TaskOutput task: "a6311ae"
OUT
<retrieval_status>success</retrieval_status>

<task_id>a6311ae</task_id>

<task_type>local_agent</task_type>

<status>completed</status>

<output>
[Tool: Bash] {"command":"find /home/devel/basset-hound -type f -name \"*.md\" | head -20","description":"Find markdown documentation files"}
[Tool: Bash] {"command":"ls -la /home/devel/basset-hound/","description":"List root directory contents"}
[Tool: Bash] {"command":"find /home/devel/basset-hound -maxdepth 3 -type d | sort","description":"Show directory structure"}
[Tool: Bash] {"command":"find /home/devel/basset-hound -maxdepth 3 -type d | sort","description":"Show directory structure"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/README.md"}
[Tool: Bash] {"command":"find /home/devel/basset-hound -type f \\( -name \"*ROADMAP*\" -o -name \"*roadmap*\" -o -name \"*PLAN*\" -o -name \"*plan*\" \\)","description":"Search for roadmap or plan files"}
[Tool: Bash] {"command":"ls -la /home/devel/basset-hound/docs/","description":"List documentation directory"}
[Tool: Bash] {"command":"ls -la /home/devel/basset-hound/docs/","description":"List documentation directory"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/docs/ROADMAP.md"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/app.py"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/main.py"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/main.py"}
[Tool: Bash] {"command":"find /home/devel/basset-hound/api -type f -name \"*.py\" | head -30","description":"List Python files in API directory"}
[Tool: Bash] {"command":"wc -l /home/devel/basset-hound/neo4j_handler.py /home/devel/basset-hound/api/main.py /home/devel/basset-hound/app.py","description":"Count lines in key files"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/requirements.txt"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/requirements.txt"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/api/main.py"}
[Tool: Bash] {"command":"ls -la /home/devel/basset-hound/api/routers/","description":"List API routers"}
[Tool: Bash] {"command":"ls -la /home/devel/basset-hound/api/models/","description":"List API models"}
[Tool: Bash] {"command":"ls -la /home/devel/basset-hound/api/models/","description":"List API models"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/neo4j_handler.py","limit":150}
[Tool: Bash] {"command":"head -100 /home/devel/basset-hound/data_config.yaml","description":"Show data configuration schema"}
[Tool: Bash] {"command":"head -100 /home/devel/basset-hound/data_config.yaml","description":"Show data configuration schema"}
[Tool: Bash] {"command":"find /home/devel/basset-hound/api/services -name \"*.py\" | sort | xargs wc -l | tail -1","description":"Count total lines in services"}
[Tool: Bash] {"command":"ls -lh /home/devel/basset-hound/basset_mcp/","description":"Check MCP directory"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/docker-compose.yml"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/docker-compose.yml"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/basset_mcp/server.py","limit":200}
[Tool: Bash] {"command":"grep -r \"def \" /home/devel/basset-hound/api/routers/__init__.py | head -20","description":"Check API router structure"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/api/routers/__init__.py"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/api/routers/__init__.py"}
[Tool: Bash] {"command":"find /home/devel/basset-hound/tests -name \"test_*.py\" | wc -l","description":"Count test files"}
[Tool: Bash] {"command":"ls -1 /home/devel/basset-hound/docs/findings/ | head -15","description":"List phase documentation"}
[Tool: Bash] {"command":"head -100 /home/devel/basset-hound/install.sh","description":"Check installation script"}
[Tool: Bash] {"command":"head -100 /home/devel/basset-hound/install.sh","description":"Check installation script"}
[Tool: Bash] {"command":"head -200 /home/devel/basset-hound/docs/00-EXECUTIVE-SUMMARY.md","description":"Executive summary documentation"}
[Tool: Bash] {"command":"head -200 /home/devel/basset-hound/docs/00-EXECUTIVE-SUMMARY.md","description":"Executive summary documentation"}

--- RESULT ---
Perfect! Now I have comprehensive information. Let me compile the complete report:

---

# COMPREHENSIVE CODE REVIEW: BASSET HOUND REPOSITORY

## EXECUTIVE SUMMARY

**Basset Hound** is a sophisticated, production-ready **FastAPI-based entity relationship engine** for OSINT investigations. It's evolved significantly from its Flask foundation and now features:

- **150+ REST API endpoints** across 42+ routers
- **46K+ lines of service code** implementing 25+ distinct features
- **1600+ test cases** with comprehensive coverage
- **MCP server integration** for AI assistant compatibility
- **Neo4j graph database** with advanced relationship analysis
- **25 completed development phases** with full documentation

### Current Completion Status
- **Architecture:** 100% - Fully migrated to FastAPI
- **Core Features:** 100% - Entity management, relationships, projects
- **Advanced Features:** 85%+ - Graph analytics, webhooks, data quality, deduplication
- **Testing:** 1600+ tests passing
- **Documentation:** Extensive (25+ phase documents)

---

## 1. OVERALL ARCHITECTURE & STRUCTURE

### High-Level Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    Basset Hound                          │
├──────────────────────────────────────────────────────────┤
│  FastAPI (8000)  │  Flask (5000)  │  MCP Server (stdio) │
├──────────────────────────────────────────────────────────┤
│                  Service Layer (46K+ lines)              │
│  Entities │ Relationships │ Analysis │ Search │ Import   │
│  Crypto   │ Timeline      │ Quality  │ Jobs   │ Export   │
├──────────────────────────────────────────────────────────┤
│           Neo4j 5.28 + GDS (Graph Database)             │
│           Redis 7 (Cache/Task Queue/Sessions)           │
│           Celery (Background Jobs)                      │
└──────────────────────────────────────────────────────────┘
```

### Directory Structure

```
basset-hound/
├── api/                          # FastAPI Application (primary)
│   ├── main.py                  # FastAPI entry point
│   ├── config.py                # Pydantic settings
│   ├── dependencies.py          # DI system
│   ├── routers/                 # 42 route modules (>800KB)
│   │   ├── entities.py          # Entity CRUD
│   │   ├── relationships.py     # Relationship management
│   │   ├── analysis.py          # Graph analysis (paths, centrality)
│   │   ├── graph_analytics.py   # Advanced analytics (1700+ lines)
│   │   ├── visualization.py     # Graph visualization
│   │   ├── search.py            # Full-text search
│   │   ├── timeline.py          # Timeline tracking
│   │   ├── webhooks.py          # Event webhooks
│   │   ├── data_quality.py      # Quality assessment
│   │   ├── deduplication.py     # Duplicate detection
│   │   ├── saved_search.py      # Saved queries
│   │   ├── jobs.py              # Background jobs (1300+ lines)
│   │   ├── ml_analytics.py      # ML suggestions (1200+ lines)
│   │   └── [37 more routers]
│   ├── services/                # Business Logic (46K+ lines)
│   │   ├── neo4j_service.py     # Async Neo4j
│   │   ├── search_service.py    # Full-text search
│   │   ├── cache_service.py     # Dual Redis/Memory cache
│   │   ├── community_detection.py  # Louvain algorithm
│   │   ├── influence_service.py # PageRank, influence spread
│   │   ├── auto_linker.py       # Auto-duplicate linking
│   │   ├── timeline_service.py  # Event tracking
│   │   ├── webhook_service.py   # Webhook delivery
│   │   └── [20+ more services]
│   ├── models/                  # Pydantic Models
│   │   ├── entity.py            # Entity schemas
│   │   ├── relationship.py      # Relationship enums/models
│   │   ├── entity_types.py      # 6 entity types + configs
│   │   ├── orphan.py            # Orphan data models
│   │   └── [8 more model files]
│   ├── auth/                    # Authentication
│   │   ├── jwt.py               # JWT tokens
│   │   ├── api_key.py           # API key management
│   │   └── dependencies.py      # Auth dependencies
│   └── utils/                   # Utilities
│       └── crypto_detector.py   # 20+ crypto detection
├── mcp/                         # MCP Server (FastMCP)
│   └── server.py                # 1400+ lines, 50+ tools
├── basset_mcp/                  # Legacy MCP (56KB)
│   └── server.py                # Deprecated version
├── neo4j_handler.py             # Core Neo4j operations (2500+ lines)
├── config_loader.py             # YAML schema loader
├── data_config.yaml             # Entity schema (70+ social networks)
├── app.py                       # Flask application (legacy, maintained)
├── main.py                      # Unified entry point
├── docker-compose.yml           # Full stack (Neo4j + Redis + Celery)
├── Dockerfile                   # Multi-stage build
├── install.sh                   # Ubuntu 22.04 native install (24KB)
├── requirements.txt             # 47 dependencies
├── tests/                       # 43 test files
│   ├── test_api_*.py           # API endpoint tests
│   ├── test_crypto_*.py        # Crypto detection tests
│   ├── test_graph_*.py         # Graph analysis tests
│   ├── test_phase*.py          # Phase-specific tests
│   └── test_*.py               # 1600+ total tests
├── docs/                        # Documentation
│   ├── ROADMAP.md              # 2150+ line roadmap
│   ├── README.md               # Component specs
│   └── findings/               # 25 phase documents
├── templates/                  # Jinja2 templates
├── static/                     # Frontend assets
│   ├── css/
│   ├── js/
│   └── imgs/
└── data/                       # Data directory
```

### Technology Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| **API Framework** | FastAPI | 0.115+ | REST API, async, auto-docs |
| **Database** | Neo4j | 5.28+ | Graph relationships |
| **Cache/Queue** | Redis | 7+ | Caching, Celery broker |
| **Task Worker** | Celery | Latest | Background jobs |
| **Legacy Web** | Flask | 3.1.0 | Maintained for compatibility |
| **Data Validation** | Pydantic | 2.10+ | Type safety, validation |
| **Auth** | python-jose + bcrypt | Latest | JWT + password hashing |
| **Async HTTP** | httpx | 0.27+ | Async HTTP client |
| **Graph Algorithms** | Neo4j GDS | 5.28+ | Community detection, PageRank |
| **Fuzzy Matching** | rapidfuzz | 3.0+ | String similarity |

---

## 2. KEY FEATURES & FUNCTIONALITY

### Core Features (Fully Implemented)

#### 2.1 Project Management
- **Multi-project support** - Isolated workspaces for different investigations
- **Project CRUD** - Create, list, get, update, delete projects
- **Safe naming** - Automatic slug generation for project names
- **Storage isolation** - Per-project file and data directories

#### 2.2 Entity Management (6 Types)
**Supported Entity Types:**
1. **Person** - Individuals with 70+ social networks, 35 sections
2. **Organization** - Companies, groups, agencies with structure
3. **Device** - Phones, computers, IoT with technical specs
4. **Location** - Addresses, venues, regions with coordinates
5. **Event** - Incidents, meetings, transactions with timing
6. **Document** - Files, reports, evidence with metadata

**Entity Features:**
- Dynamic field system based on `data_config.yaml`
- 70+ social networks (LinkedIn, Twitter, Telegram, Discord, GitHub, etc.)
- Custom field types (string, email, phone, date, file, select, component)
- Bulk import/export (JSON, CSV, JSONL)
- Field-level validation
- Profile photo support

#### 2.3 Relationship Management
**26 Relationship Types:**
- Professional: WORKS_WITH, BUSINESS_PARTNER, REPORTS_TO, MANAGES, COLLEAGUE, CLIENT
- Family: MARRIED_TO, PARENT_OF, CHILD_OF, SIBLING_OF
- Social: FRIEND, ACQUAINTANCE, NEIGHBOR, KNOWS
- Organizational: MEMBER_OF, AFFILIATED_WITH
- Investigative: ALIAS_OF, ASSOCIATED_WITH, SUSPECTED_ASSOCIATE
- Cross-type: EMPLOYED_BY, FOUNDED, OWNS_DEVICE, USES, LIVES_AT, etc.

**Relationship Features:**
- Directional relationships (asymmetric & symmetric)
- Relationship properties (confidence, source, notes, timestamp)
- Auto-creation of inverse relationships
- Transitive relationship detection
- Relationship statistics and counts

#### 2.4 Orphan Data Management
**Identifier Types:** (15 total)
- EMAIL, PHONE, CRYPTO_ADDRESS, USERNAME, IP_ADDRESS
- DOMAIN, URL, SOCIAL_MEDIA, LICENSE_PLATE, PASSPORT
- SSN, ACCOUNT_NUMBER, MAC_ADDRESS, IMEI, OTHER

**Orphan Features:**
- Store unlinked identifiers before entity assignment
- Auto-suggest matches to existing entities
- One-click linking to merge orphan → entity
- Bidirectional: detach entity data → orphan
- Data provenance tracking (source, confidence, timestamp)
- Bulk orphan import

#### 2.5 Advanced Search
**Search Capabilities:**
- **Full-text search** - Neo4j Lucene-based indexing
- **Boolean operators** - AND, OR, NOT
- **Field-specific** - `email:john@example.com`
- **Phrase search** - "exact match"
- **Wildcards** - `name:John*`, `phone:555?`
- **Fuzzy matching** - Typo tolerance
- **Multi-project** - Scope search to single or all projects
- **Pagination** - Limit/offset support
- **Search analytics** - Track query history, suggestions, zero-result detection

#### 2.6 Graph Analysis
**Path Finding:**
- Shortest path between two entities
- All paths with depth limits
- Relationship type filtering

**Clustering & Community Detection:**
- Connected component analysis
- Louvain algorithm (Neo4j GDS)
- Label propagation
- Cluster hierarchies

**Centrality Analysis:**
- Degree centrality (in/out)
- Betweenness centrality
- PageRank (influence scoring)
- Eigenvector centrality
- Closeness centrality

**Similarity & Pattern Detection:**
- Jaccard similarity (shared neighbors)
- Cosine similarity
- Common neighbors
- SimRank (recursive similarity)
- Temporal pattern detection

**Neighborhood Analysis:**
- N-hop ego networks
- Entity clustering
- Sub-graph extraction
- Influence propagation

#### 2.7 Timeline & Activity Tracking
**Event Types:** (15+)
- CREATED, UPDATED, DELETED, MERGED, TAGGED, FILE_ADDED
- RELATIONSHIP_ADDED, RELATIONSHIP_UPDATED, RELATIONSHIP_DELETED
- IMPORTED, EXPORTED, LINKED, DETACHED

**Timeline Features:**
- Auto-tracking with UUIDs and timestamps
- Filter by date range, event type, actor (deprecated)
- Entity-level timelines
- Relationship history between two entities
- Activity heatmaps (hourly, daily, weekly, monthly)
- Entity evolution tracking
- Temporal snapshots (graph state at point in time)
- Time period comparison

#### 2.8 Cryptocurrency Intelligence
**Supported Cryptocurrencies:** (30+)
- Bitcoin (P2PKH, P2SH, Bech32, Taproot)
- Ethereum, Litecoin, Ripple, Monero, Dogecoin
- Solana, Cardano, Polkadot, Cosmos, Stellar
- EVM chains: BSC, Polygon, Arbitrum, Avalanche, Optimism
- Layer 2 solutions and many others

**Crypto Features:**
- Auto-detection from address format
- Type classification (addresses, explorers)
- Confidence scoring
- Block explorer URLs
- Batch address lookup
- FontAwesome icons
- Address validation and normalization

#### 2.9 Data Quality & Deduplication
**Data Quality Dimensions:** (6)
- Completeness - % fields filled
- Freshness - age of last update
- Accuracy - based on source reliability
- Consistency - value format/validity
- Uniqueness - duplicate detection
- Validity - regex/format matching

**Quality Features:**
- 11 data sources with reliability ratings (manual_entry: 0.9, Shodan: 0.85, etc.)
- Letter grades (A-F) based on weighted scores
- Field-level quality recommendations
- Project quality reports
- Quality comparison between entities

**Deduplication Features:**
- 7 match types (exact, fuzzy, phonetic, normalized, token_set, case_insensitive, partial)
- 7 merge strategies (keep_primary, keep_newest, keep_longest, etc.)
- Preview before merge with conflict detection
- Merge history and undo support
- Project-wide duplicate scanning
- Duplicate reports

#### 2.10 Auto-Linking & Entity Resolution
**Matching Mechanisms:**
- Email exact matching (weight 3.0)
- Phone normalized matching (weight 2.5)
- Crypto address matching (weight 3.5)
- Social media handles (weight 2.0)
- Username exact/fuzzy matching
- Fuzzy name matching (Levenshtein, Jaro-Winkler, token ratios, phonetic)

**Auto-Linker Features:**
- Duplicate detection threshold (≥5.0)
- Link suggestion threshold (≥2.0)
- Project-wide duplicate scan
- Entity merge with profile consolidation
- Fuzzy threshold configuration
- Identifier-only searches

#### 2.11 Cross-Project Linking
**Features:**
- Link entities across different projects
- 6 link types: SAME_PERSON, RELATED, ALIAS, ASSOCIATE, FAMILY, ORGANIZATION
- Confidence scoring (0.0-1.0)
- Bidirectional Neo4j relationships
- Metadata support
- Auto-match finding

#### 2.12 Data Import & Export
**Import Sources:** (7 connectors)
- Maltego CSV exports with entity type mapping
- SpiderFoot JSON scan results
- TheHarvester email/domain discovery
- Shodan host/service data
- HIBP breach data
- Generic CSV (configurable mapping)
- Generic JSON (flexible import)

**Import Features:**
- Auto type detection (10+ identifier types)
- Dry-run validation mode
- Success/error/warning tracking
- Entity + orphan creation
- Relationship preservation

**Export Formats:** (5)
- JSON (full entity/relationship graph)
- CSV (configured field export)
- JSONL (JSON Lines for streaming)
- GraphML (XML-based)
- Graph formats (D3, Cytoscape, DOT, etc.)

#### 2.13 Visualization & Analytics
**Graph Visualization:**
- 5 layout algorithms (force-directed, hierarchical, circular, radial, grid)
- 4 export formats (D3.js, Cytoscape.js, GraphML, DOT)
- Graph metrics (degree, betweenness, node degrees)
- Real-time updates via WebSocket

**Timeline Visualization:**
- Entity event timeline
- Relationship history timeline
- Activity heatmaps
- Temporal snapshots
- Entity evolution tracking
- Period comparison

#### 2.14 Report Generation
**Report Formats:** (3)
- PDF (via WeasyPrint, optional)
- HTML (modern template)
- Markdown (portable)

**Report Features:**
- Custom templates (5 types: ENTITY, PROJECT, GRAPH, TIMELINE, CUSTOM)
- Template marketplace (publish, search, download, rate)
- Report scheduling (ONCE, HOURLY, DAILY, WEEKLY, MONTHLY, CRON)
- Report storage with version history
- Report diffing (unified diff)
- Report deduplication

#### 2.15 Search Capabilities
**Saved Searches:**
- Save search configurations with name, description
- 3 scopes: GLOBAL, PROJECT, USER
- 6 categories: GENERAL, INVESTIGATION, MONITORING, COMPLIANCE, RISK, CUSTOM
- Tag-based organization
- Favorites, recent, and popular searches
- Clone searches for modifications
- Execution tracking with parameters

---

## 3. DATABASE SCHEMA & DATA MODELS

### Neo4j Graph Model

**Node Types:**
```
(Project)           - Investigation projects
  ├─ properties: id, name, safe_name, created_at, description
  
(Entity)            - Persons, Organizations, Devices, etc.
  ├─ properties: id, entity_type, profile (JSON), tags, created_at, updated_at
  
(OrphanData)        - Unlinked identifiers
  ├─ properties: id, identifier_type, identifier_value, linked, metadata, created_at
  
(File)              - Attached documents/media
  ├─ properties: id, filename, path, mime_type, size, created_at
  
(Timeline)          - Event records
  ├─ properties: id, event_type, timestamp, actor_id, changes
  
(Section)           - Schema sections (from config)
  ├─ properties: id, label, icon, description
  
(Field)             - Schema fields
  ├─ properties: id, section_id, label, type, multiple
  
(Configuration)     - Root config node
  ├─ properties: id, updated_at
```

**Relationship Types:**
```
(Project) -[CONTAINS]-> (Entity)
(Entity) -[HAS_FILE]-> (File)
(Entity) -[TAGGED]-> (Entity)          [26 types: WORKS_WITH, KNOWS, FAMILY, etc.]
(Entity) -[LINKED_TO]-> (Entity)       [Cross-project: SAME_PERSON, ALIAS, etc.]
(Entity) -[HAS_ORPHAN]-> (OrphanData)
(Entity) -[RECORDED_EVENT]-> (Timeline)
(Project) -[HAS_TIMELINE]-> (Timeline)
(Configuration) -[HAS_SECTION]-> (Section)
(Section) -[HAS_FIELD]-> (Field)
```

**Indexes:**
```
UNIQUE CONSTRAINTS:
- Project.safe_name
- Person.id
- File.id
- OrphanData.id

INDEXES:
- Project.name, created_at
- Person.created_at, profile
- Section.id
- Field.id
- OrphanData (identifier_type, identifier_value, linked, created_at)
- FieldValue (section_id, field_id)
- OrphanData (identifier_type, linked) - composite
- HAS_FILE (section_id, field_id)
- TAGGED (relationship_type)
```

### Pydantic Models (API Layer)

**Core Models:**
- `ProjectBase`, `ProjectCreate`, `ProjectResponse` - Project CRUD
- `EntityBase`, `EntityCreate`, `EntityUpdate`, `EntityResponse` - Entity CRUD
- `RelationshipCreate`, `RelationshipUpdate`, `RelationshipResponse` - Relationship ops
- `OrphanDataCreate`, `OrphanDataResponse`, `OrphanDataLink` - Orphan data
- `FileUpload`, `FileResponse` - File management
- `TimelineEvent`, `TimelineResponse` - Event tracking

**Enum Models:**
- `EntityType` (6 types: Person, Organization, Device, Location, Event, Document)
- `RelationshipType` (26 types)
- `OrphanIdentifierType` (15 types)
- `EventType` (15+ event types)
- `JobStatus`, `JobPriority` - Background jobs
- `MatchType`, `MergeStrategy` - Deduplication

**Complex Models:**
- `GraphAnalysisResult` - Path, cluster, centrality results
- `SearchResult` - Query results with highlighting
- `ImportResult` - Batch import status
- `ReportTemplate`, `ReportSchedule` - Report config
- `DataQualityScore` - Quality metrics
- `WebhookConfig`, `WebhookDelivery` - Webhook tracking

---

## 4. API ENDPOINTS & INTERFACES

### API Organization (150+ Endpoints)

#### Core Projects (12 endpoints)
```
POST   /api/v1/projects                  - Create project
GET    /api/v1/projects                  - List all projects
GET    /api/v1/projects/{safe_name}      - Get project details
PATCH  /api/v1/projects/{safe_name}      - Update project
DELETE /api/v1/projects/{safe_name}      - Delete project
GET    /api/v1/projects/{safe_name}/stats - Project statistics
```

#### Entities (25+ endpoints)
```
POST   /api/v1/projects/{p}/entities             - Create entity
GET    /api/v1/projects/{p}/entities             - List entities
GET    /api/v1/projects/{p}/entities/{id}        - Get entity
PUT    /api/v1/projects/{p}/entities/{id}        - Update entity
DELETE /api/v1/projects/{p}/entities/{id}        - Delete entity
GET    /api/v1/projects/{p}/entities/type/{type} - By entity type
GET    /api/v1/projects/{p}/entities/{id}/files  - List entity files
POST   /api/v1/projects/{p}/entities/{id}/tags   - Add tags
GET    /api/v1/projects/{p}/entities/{id}/timeline - Entity timeline
```

#### Relationships (20+ endpoints)
```
GET    /api/v1/projects/{p}/relationships/       - List all
GET    /api/v1/projects/{p}/relationships/stats  - Statistics
POST   /api/v1/entities/{id}/relationships/tag/{target_id} - Create
PATCH  /api/v1/entities/{id}/relationships/tag/{target_id} - Update
DELETE /api/v1/entities/{id}/relationships/tag/{target_id} - Delete
GET    /api/v1/entities/{id}/relationships/types - Available types
```

#### Orphan Data (15+ endpoints)
```
POST   /api/v1/projects/{p}/orphans              - Create orphan
GET    /api/v1/projects/{p}/orphans              - List/search orphans
GET    /api/v1/projects/{p}/orphans/{id}         - Get orphan
PUT    /api/v1/projects/{p}/orphans/{id}         - Update
DELETE /api/v1/projects/{p}/orphans/{id}         - Delete
GET    /api/v1/projects/{p}/orphans/{id}/suggestions - Match suggestions
POST   /api/v1/projects/{p}/orphans/{id}/link    - Link to entity
POST   /api/v1/projects/{p}/orphans/detach       - Detach from entity
POST   /api/v1/projects/{p}/orphans/batch        - Bulk import
GET    /api/v1/projects/{p}/orphans/duplicates   - Find duplicates
```

#### Graph Analysis (18+ endpoints)
```
GET    /api/v1/analysis/{p}/path/{id1}/{id2}           - Shortest path
GET    /api/v1/analysis/{p}/paths/{id1}/{id2}          - All paths
GET    /api/v1/analysis/{p}/centrality/{id}            - Centrality score
GET    /api/v1/analysis/{p}/most-connected            - Top entities
GET    /api/v1/analysis/{p}/neighborhood/{id}          - N-hop ego net
GET    /api/v1/analysis/{p}/clusters                  - Find clusters
GET    /api/v1/analysis/{p}/similarity/{id1}/{id2}    - Similarity score
```

#### Advanced Graph Analytics (25+ endpoints)
```
POST   /api/v1/graph-analytics/{p}/communities         - Detect communities
POST   /api/v1/graph-analytics/{p}/influence-scores    - PageRank
POST   /api/v1/graph-analytics/{p}/similarity-matrix   - All similarities
POST   /api/v1/graph-analytics/{p}/temporal-patterns   - Pattern detection
GET    /api/v1/graph-analytics/{p}/influence/{id}      - Entity influence
GET    /api/v1/graph-analytics/{p}/anomalies           - Anomaly detection
```

#### Search (12+ endpoints)
```
GET    /api/v1/search                        - Global search
GET    /api/v1/projects/{p}/search           - Project search
GET    /api/v1/search/fields                 - Searchable fields
POST   /api/v1/projects/{p}/search/reindex   - Rebuild index
POST   /api/v1/analytics/search               - Record search event
GET    /api/v1/analytics/top-queries         - Popular queries
GET    /api/v1/analytics/zero-results        - Failed queries
```

#### Saved Searches (17 endpoints)
```
POST   /api/v1/saved-searches                     - Create
GET    /api/v1/saved-searches                     - List
GET    /api/v1/saved-searches/{id}                - Get
PUT    /api/v1/saved-searches/{id}                - Update
DELETE /api/v1/saved-searches/{id}                - Delete
POST   /api/v1/saved-searches/{id}/execute        - Execute
POST   /api/v1/saved-searches/{id}/duplicate      - Clone
POST   /api/v1/saved-searches/{id}/toggle-favorite - Favorite
GET    /api/v1/saved-searches/favorites           - List favorites
GET    /api/v1/saved-searches/recent              - Recent
GET    /api/v1/saved-searches/popular             - Most used
```

#### Timeline (10+ endpoints)
```
GET    /api/v1/projects/{p}/timeline                   - Project timeline
GET    /api/v1/projects/{p}/entities/{id}/timeline     - Entity timeline
GET    /api/v1/projects/{p}/relationships/{id1}/{id2}/history - Relationship history
GET    /api/v1/projects/{p}/entities/{id}/activity     - Activity stats
POST   /api/v1/projects/{p}/entities/{id}/timeline     - Record event
```

#### Timeline Visualization (6 endpoints)
```
GET    /api/v1/timeline-viz/{p}/entity/{id}              - Entity timeline viz
GET    /api/v1/timeline-viz/{p}/relationship/{id1}/{id2} - Relationship viz
GET    /api/v1/timeline-viz/{p}/activity                 - Activity heatmap
GET    /api/v1/timeline-viz/{p}/snapshot                 - Temporal snapshot
GET    /api/v1/timeline-viz/{p}/entity/{id}/evolution    - Evolution history
POST   /api/v1/timeline-viz/{p}/compare                  - Compare periods
```

#### Cryptocurrency (8 endpoints)
```
GET    /api/v1/crypto/ticker/{address}        - Lookup address
POST   /api/v1/crypto/ticker/batch            - Batch lookup
GET    /api/v1/crypto/currencies              - Supported currencies
GET    /api/v1/crypto/explorer-url/{address}  - Generate explorer URL
```

#### Data Import (15+ endpoints)
```
POST   /api/v1/projects/{p}/import/maltego            - Maltego
POST   /api/v1/projects/{p}/import/spiderfoot         - SpiderFoot
POST   /api/v1/projects/{p}/import/theharvester       - TheHarvester
POST   /api/v1/projects/{p}/import/shodan             - Shodan
POST   /api/v1/projects/{p}/import/hibp               - HIBP
POST   /api/v1/projects/{p}/import/csv                - CSV
POST   /api/v1/projects/{p}/import/json               - JSON
GET    /api/v1/import/formats                        - List formats
POST   /api/v1/import/validate                       - Validate data
```

#### Data Export (15+ endpoints)
```
POST   /api/v1/projects/{p}/llm-export/entity/{id}              - Entity
POST   /api/v1/projects/{p}/llm-export/summary                  - Summary
POST   /api/v1/projects/{p}/llm-export/entity/{id}/context      - With context
POST   /api/v1/projects/{p}/llm-export/investigation-brief      - Investigation
POST   /api/v1/llm-export/estimate-tokens                       - Token estimate
GET    /api/v1/llm-export/formats                              - List formats
POST   /api/v1/graph-format/convert                             - Convert graphs
POST   /api/v1/graph-format/detect                              - Detect format
GET    /api/v1/graph-format/formats                             - List formats
```

#### Webhooks (15 endpoints)
```
POST   /api/v1/webhooks                     - Create webhook
GET    /api/v1/webhooks                     - List
GET    /api/v1/webhooks/{id}                - Get specific
PUT    /api/v1/webhooks/{id}                - Update
DELETE /api/v1/webhooks/{id}                - Delete
POST   /api/v1/webhooks/{id}/test           - Test event
GET    /api/v1/webhooks/{id}/deliveries     - Delivery history
POST   /api/v1/webhooks/deliveries/{id}/retry - Retry delivery
GET    /api/v1/webhooks/events              - Available event types
GET    /api/v1/webhooks/stats               - Statistics
```

#### Jobs & Background Processing (12 endpoints)
```
POST   /api/v1/jobs                         - Enqueue job
GET    /api/v1/jobs                         - List jobs
GET    /api/v1/jobs/{id}                    - Get job
DELETE /api/v1/jobs/{id}                    - Cancel job
GET    /api/v1/jobs/stats                   - Statistics
POST   /api/v1/jobs/worker/start            - Start worker
POST   /api/v1/jobs/worker/stop             - Stop worker
GET    /api/v1/jobs/worker/status           - Worker status
```

#### Report Management (15+ endpoints)
```
POST   /api/v1/projects/{p}/schedules               - Create schedule
GET    /api/v1/projects/{p}/schedules               - List
PATCH  /api/v1/schedules/{id}                       - Update
DELETE /api/v1/schedules/{id}                       - Delete
POST   /api/v1/schedules/{id}/run                   - Trigger
POST   /api/v1/reports                              - Store report
GET    /api/v1/reports/{id}/versions                - List versions
GET    /api/v1/reports/{id}/diff                    - Compare versions
POST   /api/v1/reports/{id}/cleanup                 - Cleanup old
```

#### Templates & Marketplace (20+ endpoints)
```
POST   /api/v1/templates                           - Create template
GET    /api/v1/templates                           - List
GET    /api/v1/templates/{id}                      - Get
PUT    /api/v1/templates/{id}                      - Update
DELETE /api/v1/templates/{id}                      - Delete
POST   /api/v1/templates/{id}/render               - Render
POST   /api/v1/templates/{id}/preview              - Preview
POST   /api/v1/marketplace/templates                - Publish
GET    /api/v1/marketplace/templates                - Search
POST   /api/v1/marketplace/templates/{id}/download - Download
POST   /api/v1/marketplace/templates/{id}/reviews  - Review
GET    /api/v1/marketplace/popular                 - Popular
GET    /api/v1/marketplace/top-rated               - Top rated
```

#### Data Quality & Deduplication (20+ endpoints)
```
POST   /api/v1/data-quality/score                  - Score entity
POST   /api/v1/data-quality/score/batch            - Batch score
GET    /api/v1/data-quality/config                 - Configuration
GET    /api/v1/data-quality/sources                - Source reliability
POST   /api/v1/data-quality/compare                - Compare entities
GET    /api/v1/data-quality/stats                  - Statistics
POST   /api/v1/deduplication/find                  - Find duplicates
POST   /api/v1/deduplication/find-all              - Find all
POST   /api/v1/deduplication/merge                 - Execute merge
POST   /api/v1/deduplication/undo/{id}             - Undo merge
GET    /api/v1/deduplication/history               - Merge history
```

#### ML Analytics (8 endpoints)
```
POST   /api/v1/ml/record-query                     - Record query
GET    /api/v1/ml/suggest                          - Get suggestions
GET    /api/v1/ml/patterns                         - Detect patterns
GET    /api/v1/ml/entity-insights/{id}             - Entity insights
GET    /api/v1/ml/predict-zero-results             - Predict failures
```

#### WebSocket (1 endpoint)
```
WS     /api/v1/ws                                  - Real-time notifications
```

#### Health & Info (4 endpoints)
```
GET    /health                                     - Health check
GET    /                                           - Root info
GET    /api/info                                   - API info
GET    /docs                                       - OpenAPI docs
```

### Authentication
- **No authentication required** - Local-first, single-user design
- **Optional JWT/API key** - Available for future multi-user support
- **Development mode** - Defaults to auth disabled

---

## 5. CURRENT INTEGRATION POINTS & EXTENSIBILITY

### 5.1 MCP Server Integration

**Basset Hound MCP Server** (`mcp/server.py` - 1400+ lines)

Provides 50+ tools for AI assistants:

**Schema Tools (Dynamic):**
- `get_schema()` - Complete data_config.yaml
- `get_sections()` - Section summaries
- `get_identifiers()` - Identifier fields
- `get_field_info()` - Field details
- `validate_profile_data()` - Validate entity data
- `reload_schema()` - Hot-reload config

**Project Tools:**
- `create_project()` - New investigation
- `list_projects()` - All projects
- `get_project()` - Project details
- `get_project_stats()` - Statistics

**Entity Tools:**
- `create_entity()` - New entity
- `get_entity()` - Get by ID
- `update_entity()` - Update profile
- `delete_entity()` - Delete entity
- `list_entities()` - List all
- `list_entities_by_type()` - By entity type
- `find_similar_entities()` - Fuzzy matching

**Relationship Tools:**
- `link_entities()` - Create relationship
- `unlink_entities()` - Remove relationship
- `get_related_entities()` - Get connections
- `get_relationship_types()` - Available types

**Search Tools:**
- `search_entities()` - Full-text search
- `search_by_identifier()` - Exact identifier lookup
- `advanced_search()` - Boolean search

**Orphan Data Tools:**
- `create_orphan()` - New orphan data
- `get_orphan_suggestions()` - Match suggestions
- `link_orphan_to_entity()` - Link operation
- `find_orphan_duplicates()` - Duplicate detection

**Report Tools:**
- `generate_report()` - Create report
- `get_reports()` - List reports
- `create_schedule()` - Schedule report

**Analysis Tools:**
- `find_shortest_path()` - Path finding
- `analyze_centrality()` - Centrality score
- `detect_clusters()` - Community detection
- `find_similar_entities()` - Similarity

### 5.2 REST API Integration

**OpenAPI/Swagger Documentation:**
- Auto-generated at `/docs` and `/redoc`
- Full endpoint documentation
- Example requests/responses
- Schema definitions

**Client SDK Generation:**
- Auto-generateable from OpenAPI spec
- Python, JavaScript, TypeScript, Go, etc.

**Webhook Integration:**
- 20+ event types
- HMAC-SHA256 signature verification
- Retry logic with exponential backoff
- Delivery tracking and history

### 5.3 Data Format Integration

**Import Formats:**
- Maltego CSV exports
- SpiderFoot JSON
- TheHarvester JSON
- Shodan JSON
- HIBP breach data
- Generic CSV (configurable)
- Generic JSON

**Export Formats:**
- JSON (entities + relationships)
- CSV (field-specific)
- JSONL (streaming)
- GraphML (for network tools)
- D3.js JSON
- Cytoscape.js JSON
- DOT (Graphviz)
- Pajek format

### 5.4 External System Integration

**Supported Integrations:**
- **Neo4j GDS** - Community detection, PageRank, similarity
- **Redis** - Caching, session management, Celery broker
- **Celery** - Background job processing
- **External Webhooks** - OSINT tool notifications
- **HTTP APIs** - For OSINT data collection

### 5.5 Extensibility Mechanisms

#### Configuration-Driven Schema
The `data_config.yaml` system allows:
```yaml
sections:
  - id: custom_section
    name: Custom Data
    fields:
      - id: custom_field
        type: string                    # string, email, phone, date, file, etc.
        label: Custom Field
        searchable: true                # Include in full-text index
        identifier: true                # Use for entity matching
        multiple: true                  # Allow multiple values
```

**No code changes needed** - Just edit YAML and reload.

#### Custom Service Layer
Add new services in `api/services/`:
```python
# api/services/my_analyzer.py
class MyAnalyzer:
    def analyze(self, entity_id, project):
        # Custom logic here
        return results
```

Register in router:
```python
# api/routers/my_analyzer.py
from api.services.my_analyzer import MyAnalyzer

@router.get("/my-analysis/{id}")
def analyze_entity(id: str, project: str):
    analyzer = MyAnalyzer()
    return analyzer.analyze(id, project)
```

#### Custom Routers
Add new endpoints:
```python
# api/routers/my_feature.py
router = APIRouter(prefix="/my-feature")

@router.post("/{project}/action")
def my_action(project: str, data: MyModel):
    # Custom endpoint logic
    pass
```

#### Neo4j Query Customization
Extend `neo4j_handler.py`:
```python
def my_custom_query(self, project_safe_name, param):
    with self.driver.session() as session:
        result = session.run("""
            MATCH (p:Project {safe_name: $safe_name})
            // Custom Cypher here
        """, safe_name=project_safe_name, param=param)
        return result.data()
```

#### MCP Tool Addition
Add new tools to `mcp/server.py`:
```python
@mcp.tool()
def my_mcp_tool(entity_id: str, project_id: str) -> dict:
    """Custom MCP tool for AI assistants."""
    # Tool implementation
    return {"result": "data"}
```

---

## 6. ROADMAP & DOCUMENTATION

### Phase Completion Summary (25 Phases)

| Phase | Title | Status | Tests |
|-------|-------|--------|-------|
| 1 | Core Modernization | 100% | 200+ |
| 2 | MCP Server Integration | 100% | 150+ |
| 2.5 | Intelligent Data Processing | 100% | 85+ |
| 3 | Advanced Relationships | 100% | 212 |
| 4 | Performance & Scalability | 100% | 346 |
| 5 | Multi-Entity Type Support | 100% | 48 |
| 6 | Cross-Project & Fuzzy Matching | 100% | 439 |
| 7 | Timeline, Auto-Linker Fuzzy, Bulk | 100% | 562 |
| 8 | Crypto Ticker, Search, Reports | 100% | 737 |
| 9 | Real-Time & Automation | 100% | 1039 |
| 10 | Background Processing | 100% | 1581 |
| 11 | Production Hardening | 100% | 1595 |
| 12 | Performance & Scalability | 100% | 1628 |
| 13 | Infrastructure | 100% | 1628 |
| 14 | Local-First Simplification | 100% | 1692 |
| 15 | Orphan Data Management | 100% | 1750+ |
| 16 | Visualization & Data Import | 100% | 1850+ |
| 17 | Frontend Integration & UI | 100% | 1900+ |
| 18 | Advanced Graph Analytics | 100% | 1950+ |
| 19 | Deployment & Infrastructure | 100% | 2000+ |
| 20 | Query & Performance Optimization | 100% | 2050+ |
| 21 | Import/Export Flexibility | 100% | 2100+ |
| 22 | API Endpoints for Phase 21 | 100% | 2150+ |
| 23 | Saved Search Configurations | 100% | 2200+ |
| 24 | Webhook Integrations | 100% | 2280+ |
| 25 | Deduplication & Data Quality | 100% | 2350+ |

### Documentation Structure

**Found in `/home/devel/basset-hound/docs/`:**

1. **ROADMAP.md** (2150+ lines) - Comprehensive development plan with phases
2. **README.md** - Component specifications
3. **ADVANCED_SEARCH_IMPLEMENTATION.md** - Search system details
4. **GRAPH_VISUALIZATION_API.md** - Graph API documentation
5. **SEARCH_SYNTAX_QUICK_REFERENCE.md** - Query syntax guide
6. **Phase Findings (25 documents):**
   - 00-EXECUTIVE-SUMMARY.md
   - 01-REPOSITORY-ANALYSIS.md through 25-PHASE25-DEDUPLICATION-DATA-QUALITY.md

Each phase document includes:
- Completed tasks with status
- Files created/modified
- Test coverage
- API endpoints added
- Known issues or improvements

---

## 7. TECHNOLOGY STACK DETAILS

### Backend Framework
- **FastAPI 0.115+** - Modern async Python web framework
- **Uvicorn 0.32+** - ASGI server
- **Pydantic 2.10+** - Data validation (v2 with ConfigDict)
- **Python 3.12+** - Language version

### Database
- **Neo4j 5.28** - Graph database
- **Neo4j GDS** - Graph algorithms (community detection, PageRank, similarity)
- **Neo4j Cypher** - Query language

### Caching & Queuing
- **Redis 7** - Caching, session storage, Celery broker
- **Python-RQ / ARQ** - Alternative job queues (optional)
- **Celery** - Distributed task processing

### Authentication
- **python-jose** - JWT token generation/validation
- **Passlib[bcrypt]** - Password hashing
- **python-multipart** - Form data parsing

### Data Processing
- **Pydantic** - Type validation
- **PyYAML** - Configuration files
- **python-dotenv** - Environment variables
- **rapidfuzz** - Fuzzy string matching
- **python-magic** - File type detection

### AI/ML Integration
- **MCP** - Model Context Protocol for AI assistants
- **scikit-learn** (implicit) - TF-IDF, clustering
- **Custom ML** - Query suggestions, pattern detection

### HTTP & Communication
- **httpx** - Async HTTP client
- **WebSockets** - Real-time connections
- **CORS middleware** - Cross-origin requests

### Development & Testing
- **pytest** - Testing framework
- **pytest-asyncio** - Async test support
- **pytest-cov** - Code coverage
- **ruff** - Code linting
- **mypy** - Type checking

### File & Document Processing
- **aiofiles** - Async file operations
- **Markdown** - Markdown to HTML
- **WeasyPrint** (optional) - PDF generation

### Infrastructure
- **Docker** - Containerization
- **docker-compose** - Multi-container orchestration
- **Bash scripts** - Installation automation

---

## 8. CURRENT STATE OF COMPLETION

### What's Fully Complete

✅ **Core Architecture**
- FastAPI migration from Flask (100%)
- Neo4j integration with proper constraints/indexes
- Async service layer
- MCP server with 50+ tools

✅ **Entity Management**
- 6 entity types (Person, Org, Device, Location, Event, Document)
- Dynamic schema system (data_config.yaml)
- 70+ social networks
- Full CRUD operations

✅ **Relationships**
- 26 relationship types with properties
- Bidirectional creation
- Transitive detection
- Statistics and counting

✅ **Graph Analysis**
- Path finding (shortest, all paths)
- Centrality analysis (degree, betweenness, PageRank)
- Community detection (Louvain, Label Propagation)
- Similarity scoring (Jaccard, Cosine, SimRank)
- Cluster detection

✅ **Search & Query**
- Full-text search with fuzzy
- Field-specific queries
- Boolean operators
- Saved searches
- Search analytics

✅ **Data Import/Export**
- 7 import sources (Maltego, SpiderFoot, etc.)
- 5 export formats
- Validation and dry-run
- Graph format converters

✅ **Advanced Features**
- Orphan data management
- Timeline tracking
- Cryptocurrency detection (30+ coins)
- Webhook integration (20+ events)
- Data quality scoring
- Duplicate detection & merging
- Cross-project linking
- Report scheduling
- Template marketplace
- ML-powered suggestions

✅ **Infrastructure**
- Docker Compose full stack
- Native Ubuntu 22.04 install script
- Redis caching
- Celery background jobs
- Neo4j GDS guarantee

✅ **Testing**
- 1600+ comprehensive tests
- 85%+ code coverage
- Phase-specific tests
- Integration tests

### What's In Development/Needs Work

⚠️ **Optional/Lower Priority**
- PDF report generation (WeasyPrint - optional dependency)
- Plugin architecture
- Advanced caching strategies beyond Redis/in-memory
- Multi-tenant support (explicitly not implemented)
- Frontend UI (Flask legacy UI maintained, no modern React/Vue app)
- Kubernetes deployment manifests

⚠️ **Known Limitations**
- Single-user design (by intention)
- No built-in multi-tenancy
- Legacy Flask app still present (for backwards compatibility)
- Some router consolidation needed (analytics, schedule have v2 versions)
- frontend_components.py not fully integrated with modern frontend

### Test Coverage Status

```
Total Tests: 1600+ (as of Phase 25)
Coverage: 85%+
Test Types:
  - Unit tests: 600+
  - Integration tests: 500+
  - Phase-specific: 500+
  - API endpoint tests: 400+

Test Categories:
  ✅ Neo4j handler operations
  ✅ Pydantic models
  ✅ API endpoints
  ✅ Services (all 30+)
  ✅ Graph analysis algorithms
  ✅ Fuzzy matching
  ✅ Crypto detection
  ✅ Data quality
  ✅ Deduplication
  ✅ Timeline tracking
  ✅ MCP tools
```

---

## 9. DATA FLOW & INTEGRATION MECHANISMS

### Data Flow Architecture

```
External Tools             API Client
  ├─ Maltego               ├─ MCP Client
  ├─ SpiderFoot            ├─ REST Client
  ├─ Shodan                ├─ Browser (WebSocket)
  └─ HIBP                  └─ CLI Script
        │                         │
        └─────────────┬───────────┘
                      │
              ┌───────▼────────┐
              │  FastAPI (8000) │
              │   42 Routers    │
              │  150+ Endpoints │
              └────────┬────────┘
                      │
        ┌─────────────┼─────────────┬─────────────┐
        │             │             │             │
   ┌────▼─────┐  ┌────▼─────┐  ┌──▼───────┐  ┌──▼──────┐
   │ Neo4j    │  │  Redis   │  │ Celery  │  │ MCP    │
   │ Graph DB │  │  Cache   │  │ Workers │  │ Tools  │
   │          │  │          │  │         │  │        │
   └──────────┘  └──────────┘  └─────────┘  └────────┘
        │
   ┌────▼──────────────────┐
   │  Projects/Entities    │
   │  Relationships        │
   │  Timeline Events      │
   │  Orphan Data          │
   └───────────────────────┘
```

### Integration Points

#### 1. **Inbound Integration** (External Data → Basset Hound)

**REST API**
```bash
curl -X POST http://localhost:8000/api/v1/projects/my-project/entities \
  -H "Content-Type: application/json" \
  -d '{
    "entity_type": "Person",
    "profile": {
      "core": {"name": {"first_name": "John"}}
    }
  }'
```

**MCP Tools**
```python
from mcp import MCPClient

client = MCPClient("localhost:8000")
client.create_entity(
    project_id="my-project",
    entity_type="Person",
    profile={"core": {"name": {"first_name": "John"}}}
)
```

**Webhooks (Inbound)**
```json
{
  "event": "entity.created",
  "entity_id": "123",
  "entity_type": "Person",
  "timestamp": "2024-12-29T10:00:00Z"
}
```

#### 2. **Outbound Integration** (Basset Hound → External Systems)

**Webhooks (Outbound)**
```python
# When entity is created, notify external system
{
  "url": "https://external-system.com/webhook",
  "events": ["entity.created", "relationship.added"],
  "signature": "HMAC-SHA256(...)",
  "delivery_status": "SUCCESS"
}
```

**Report Export**
```bash
# Export entity for LLM context
curl -X POST http://localhost:8000/api/v1/projects/my-project/llm-export/entity/123 \
  -d '{"format": "markdown"}'
```

**Job Queue**
```python
# Background task processing
{
  "job_type": "REPORT",
  "status": "PENDING",
  "priority": "HIGH",
  "created_at": "2024-12-29T10:00:00Z",
  "result": null
}
```

#### 3. **Real-Time Integration** (WebSocket)

**Subscribe to Project Updates**
```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/ws');
ws.send(JSON.stringify({
  action: 'subscribe',
  project: 'my-project'
}));

ws.onmessage = (event) => {
  const notification = JSON.parse(event.data);
  console.log('Entity created:', notification);
};
```

**Notification Types:**
- ENTITY_CREATED, ENTITY_UPDATED, ENTITY_DELETED
- RELATIONSHIP_ADDED, RELATIONSHIP_UPDATED, RELATIONSHIP_DELETED
- SEARCH_EXECUTED, REPORT_GENERATED
- IMPORT_STARTED, IMPORT_COMPLETED
- GRAPH_CLUSTER_DETECTED, GRAPH_EDGE_ADDED
- ENTITY_MERGED, ENTITY_DEDUPED

#### 4. **Graph Algorithms Integration**

**Neo4j GDS Algorithms**
```cypher
-- Community Detection (Louvain)
CALL gds.louvain.stream('myGraph')
YIELD nodeId, communityId
RETURN nodeId, communityId

-- PageRank (Influence Scoring)
CALL gds.pageRank.stream('myGraph')
YIELD nodeId, score
RETURN nodeId, score

-- Similarity (Cosine, Jaccard)
CALL gds.similarity.cosine.stream('myGraph')
YIELD node1, node2, similarity
RETURN node1, node2, similarity
```

**Python API**
```python
from api.services.community_detection import CommunityDetectionService

service = CommunityDetectionService(neo4j_handler)
communities = service.detect_louvain(project_safe_name)
```

#### 5. **Import/Export Pipeline**

**Maltego CSV → Basset Hound**
```
CSV File (Maltego export)
  ↓ (parse CSV)
Map columns to entity fields
  ↓ (type detection)
Auto-detect identifiers (email, phone, etc.)
  ↓ (validation)
Dry-run check
  ↓ (create entities)
Neo4j transaction
  ↓ (timeline event)
Record IMPORTED event
```

**Basset Hound → LLM Context**
```
Entity Profile (JSON)
  ↓ (select format: markdown/json/yaml)
Add relationships
  ↓ (serialize)
Estimate tokens
  ↓ (intelligent truncation)
Return LLM-ready context
```

---

## 10. EXISTING INTEGRATION MECHANISMS

### 10.1 Configuration-Based Extensibility

**Dynamic Schema System**
```yaml
# data_config.yaml
sections:
  - id: blockchain
    name: Blockchain & Crypto
    fields:
      - id: bitcoin_address
        type: string
        identifier: true        # Auto-detect and match
        searchable: true        # Full-text index
      - id: ethereum_address
        type: string
        identifier: true
```

**MCP Auto-Introspection**
- MCP tools automatically expose schema structure
- Fields marked `identifier: true` are used for auto-linking
- `searchable: true` fields are indexed

### 10.2 Service-Based Architecture

**Pluggable Services** (`api/services/`)
- Each service is independent module
- Can be imported and extended
- Standard interface patterns

**Example: Adding Custom Analysis**
```python
# api/services/my_custom_analysis.py
from api.services.neo4j_service import Neo4jService

class MyAnalysis(Neo4jService):
    def analyze(self, project, entity_id):
        # Custom Neo4j queries
        pass

# api/routers/my_analysis.py
from api.services.my_custom_analysis import MyAnalysis

@router.get("/my-analysis/{id}")
async def run_analysis(project: str, id: str):
    service = MyAnalysis(neo4j_handler)
    return await service.analyze(project, id)
```

### 10.3 MCP Tool Registry

**Dynamic Tool Generation**
- 50+ tools automatically exposed to AI assistants
- Tools introspect data_config.yaml
- New entity types automatically available

**Tool Categories:**
- Schema (get_schema, get_sections, validate_profile_data)
- Projects (create, list, get)
- Entities (create, get, update, delete, list)
- Relationships (link, unlink, get_related)
- Search (search_entities, search_by_identifier)
- Reports (generate, get, schedule)
- Analysis (path_finding, centrality, clustering)

### 10.4 Webhook Event System

**20+ Event Types:**
```python
ENTITY_CREATED, ENTITY_UPDATED, ENTITY_DELETED
RELATIONSHIP_CREATED, RELATIONSHIP_UPDATED, RELATIONSHIP_DELETED
SEARCH_EXECUTED, SAVED_SEARCH_EXECUTED
REPORT_GENERATED, REPORT_SCHEDULED
IMPORT_STARTED, IMPORT_COMPLETED, IMPORT_FAILED
EXPORT_STARTED, EXPORT_COMPLETED
PROJECT_CREATED, PROJECT_DELETED
ORPHAN_CREATED, ORPHAN_LINKED
HEALTH_CHECK, RATE_LIMIT_EXCEEDED
```

**Webhook Delivery:**
- HMAC-SHA256 signature verification
- Retry logic (exponential backoff)
- Delivery tracking
- Event filtering by type

### 10.5 Cache & Performance Integration

**Dual Backend Cache**
```python
# Tries Redis first, falls back to in-memory
cache = CacheService(redis_url="redis://localhost:6379")

# Tag-based invalidation
cache.set("entity:123", entity_data, tags=["project:proj1", "entity:123"])
cache.invalidate_by_tag("project:proj1")  # Clear all project entities
```

**Query Result Caching**
- Automatic caching by query hash
- Configurable per-query-type TTLs
- Context-aware invalidation

### 10.6 Background Job System

**Job Types:**
```python
JOB_TYPE_REPORT = "REPORT"           # Generate report
JOB_TYPE_EXPORT = "EXPORT"           # Export data
JOB_TYPE_BULK_IMPORT = "BULK_IMPORT" # Import entities
JOB_TYPE_CUSTOM = "CUSTOM"           # Custom job
```

**Job Execution:**
```python
# Enqueue job
job = job_runner.enqueue(
    job_type="REPORT",
    project_id="my-project",
    priority="HIGH",
    payload={"template": "default"}
)

# Check status
status = job_runner.get_job_status(job.id)

# Get result
result = job_runner.get_job_result(job.id)
```

---

## 11. KNOWN ISSUES & RECOMMENDATIONS

### Current Issues (Low Severity)

1. **Router Consolidation** - Some routers have v2 versions (analytics_v2, scheduler)
   - **Impact:** Mild duplication, non-critical
   - **Recommendation:** Consolidate into single version (v2 is primary)

2. **Legacy Flask App** - Still present for backwards compatibility
   - **Impact:** Duplication, increased complexity
   - **Recommendation:** Keep for transition period, eventually deprecate

3. **Frontend Components** - Not integrated with modern frontend
   - **Impact:** API exists but not consumed
   - **Recommendation:** Build React/Vue UI using component specs

4. **Optional Dependencies** - WeasyPrint for PDF is optional
   - **Impact:** PDF export not available without install
   - **Recommendation:** Document dependency, consider making required

### Recommendations for Enhancement

1. **Build Modern Frontend**
   - React/Vue application
   - Consume REST API and WebSocket
   - Use component specs from `frontend_components.py`

2. **Implement Plugin System**
   - Dynamic loader for custom services
   - Plugin marketplace
   - Security sandboxing for plugins

3. **Advanced Caching**
   - Redis pub/sub for cache invalidation
   - Cache warming strategies
   - Distributed cache coordination

4. **Multi-Instance Support**
   - Stateless API design (already done)
   - Load balancer ready
   - Distributed Neo4j setup (GDS enterprise)

5. **Enhanced Security**
   - Rate limiting per IP/API key
   - API key scoping (read-only, project-specific)
   - Data encryption at rest
   - Audit logging enhancements

6. **Performance Tuning**
   - Query optimization profiling
   - Batch operation improvements
   - Connection pooling optimization
   - Index tuning for large datasets

---

## CONCLUSION

Basset Hound is a **mature, production-ready OSINT entity relationship platform** with:

- **Comprehensive feature set** covering entity management, graph analysis, search, import/export, and automation
- **Solid architecture** with proper separation of concerns, async/await patterns, and MCP integration
- **Extensive testing** (1600+ tests) and documentation (25+ phase docs)
- **Active development** with 25 completed phases showing continuous improvement
- **Clean code** with proper Pydantic models, type hints, and error handling
- **Multiple integration points** (REST API, MCP, Webhooks, WebSocket)
- **Production-ready deployment** (Docker, native install, Redis, Celery)

The codebase is **well-organized**, **well-documented**, and **ready for both standalone use and integration** into larger systems like AI agent platforms or OSINT automation frameworks.

---

**Repository Location:** `/home/devel/basset-hound/`
**Total Code:** 46K+ lines in services, 2500+ lines in Neo4j handler, 150+ API endpoints
**Test Coverage:** 1600+ tests, 85%+ coverage
**Documentation:** 25 phase documents, comprehensive README, ROADMAP
**Status:** Production Ready (Phase 25 Complete)
</output>
TaskOutput task: "a31c290"
OUT
<retrieval_status>success</retrieval_status>

<task_id>a31c290</task_id>

<task_type>local_agent</task_type>

<status>completed</status>

<output>
[Tool: Bash] {"command":"find /home/devel -type d -name \"*autofill*\" 2>/dev/null | head -20","description":"Find autofill-extension directory"}
[Tool: Bash] {"command":"find /home/devel -type d -name \"*autofill*\" 2>/dev/null | head -20","description":"Find autofill-extension directory"}
[Tool: Glob] {"path":"/home/devel","pattern":"*autofill*"}
[Tool: Glob] {"path":"/home/devel","pattern":"*autofill*"}
[Tool: Read] {"file_path":"/home/devel/autofill-extension"}
[Tool: Read] {"file_path":"/home/devel/autofill-extension"}
[Tool: Bash] {"command":"ls -la /home/devel/ | head -20","description":"List home directory contents"}
[Tool: Bash] {"command":"ls -la /home/devel/ | head -20","description":"List home directory contents"}
[Tool: Bash] {"command":"ls -la","description":"List current directory contents"}
[Tool: Bash] {"command":"ls -la","description":"List current directory contents"}
[Tool: Bash] {"command":"ls -la /home/devel/autofill-extension 2>&1 | head -30","description":"List autofill-extension directory"}
[Tool: Bash] {"command":"ls -la /home/devel/autofill-extension 2>&1 | head -30","description":"List autofill-extension directory"}
[Tool: Glob] {"pattern":"**/extension/**"}
[Tool: Glob] {"pattern":"**/extension/**"}
[Tool: Read] {"file_path":"/home/devel"}
[Tool: Read] {"file_path":"/home/devel"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/README.md"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/README.md"}
[Tool: Bash] {"command":"pwd","description":"Show current working directory"}
[Tool: Bash] {"command":"pwd","description":"Show current working directory"}
[Tool: Bash] {"command":"ls -la /home/devel/","description":"List contents of /home/devel directory"}
[Tool: Bash] {"command":"ls -la /home/devel/","description":"List contents of /home/devel directory"}
[Tool: Glob] {"path":"/home/devel","pattern":"*"}
[Tool: Glob] {"path":"/home/devel","pattern":"*"}
[Tool: Read] {"file_path":"/home/devel/autofill-extension/README.md"}
[Tool: Read] {"file_path":"/home/devel/autofill-extension/README.md"}
[Tool: Read] {"file_path":"/home/devel/autofill_extension/README.md"}
[Tool: Read] {"file_path":"/home/devel/autofill_extension/README.md"}
[Tool: Read] {"file_path":"/home/devel/.autofill-extension/README.md"}
[Tool: Read] {"file_path":"/home/devel/.autofill-extension/README.md"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/docs/ROADMAP.md"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/docs/ROADMAP.md"}
[Tool: Grep] {"pattern":"autofill|auto.fill|field.detect|screenshot|element.select","path":"/home/devel/basset-hound","type":"py"}
[Tool: Grep] {"pattern":"autofill|auto.fill|field.detect|screenshot|element.select","path":"/home/devel/basset-hound","type":"py"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/docs"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/docs"}
[Tool: Glob] {"path":"/home/devel/basset-hound/docs","pattern":"*"}
[Tool: Glob] {"path":"/home/devel/basset-hound/docs","pattern":"*"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/docs/03-BROWSER-AUTOMATION-STRATEGY.md"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/docs/03-BROWSER-AUTOMATION-STRATEGY.md"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/docs/04-PENTESTING-INTEGRATION.md"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/docs/04-PENTESTING-INTEGRATION.md"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/docs/02-INTEGRATION-ARCHITECTURE.md","limit":150}
[Tool: Read] {"file_path":"/home/devel/basset-hound/docs/02-INTEGRATION-ARCHITECTURE.md","limit":150}
[Tool: Read] {"file_path":"/home/devel/basset-hound/api/utils/crypto_detector.py","limit":100}
[Tool: Read] {"file_path":"/home/devel/basset-hound/api/utils/crypto_detector.py","limit":100}
[Tool: Read] {"file_path":"/home/devel/basset-hound/api/services/orphan_service.py","limit":150}
[Tool: Read] {"file_path":"/home/devel/basset-hound/api/services/orphan_service.py","limit":150}
[Tool: Read] {"file_path":"/home/devel/basset-hound/api/services/normalizer.py","limit":120}
[Tool: Read] {"file_path":"/home/devel/basset-hound/api/services/normalizer.py","limit":120}
[Tool: Read] {"file_path":"/home/devel/basset-hound/api/services/data_import.py","limit":150}
[Tool: Read] {"file_path":"/home/devel/basset-hound/api/services/data_import.py","limit":150}
[Tool: Read] {"file_path":"/home/devel/basset-hound/api/main.py","limit":150}
[Tool: Read] {"file_path":"/home/devel/basset-hound/api/main.py","limit":150}
[Tool: Read] {"file_path":"/home/devel/basset-hound/api/services/graph_visualization.py","limit":100}
[Tool: Read] {"file_path":"/home/devel/basset-hound/api/services/graph_visualization.py","limit":100}
[Tool: Grep] {"pattern":"screenshot|capture|element.select|dom.interact","path":"/home/devel/basset-hound","type":"js","head_limit":20}
[Tool: Grep] {"pattern":"screenshot|capture|element.select|dom.interact","path":"/home/devel/basset-hound","type":"js","head_limit":20}
[Tool: Read] {"file_path":"/home/devel/basset-hound/api/services/data_import.py","offset":300,"limit":100}
[Tool: Read] {"file_path":"/home/devel/basset-hound/api/services/data_import.py","offset":300,"limit":100}
[Tool: Read] {"file_path":"/home/devel/basset-hound/data_config.yaml","limit":80}
[Tool: Read] {"file_path":"/home/devel/basset-hound/data_config.yaml","limit":80}

--- RESULT ---
Excellent! Now I have comprehensive information. Let me create the code review document. Since I cannot write files, I'll provide the comprehensive findings directly:

---

# COMPREHENSIVE CODE REVIEW: Basset Hound OSINT Entity Relationship Engine

## CRITICAL CLARIFICATION
**The user requested exploration of "~/autofill-extension" repository, which is referenced in basset-hound documentation but does NOT exist as a separate repository in the file system.** However, extensive PLANNING and ARCHITECTURAL DOCUMENTATION for browser automation and autofill functionality exists in `/home/devel/basset-hound/docs/03-BROWSER-AUTOMATION-STRATEGY.md`. This review covers the complete Basset Hound architecture with all its data field detection, ingestion, and processing capabilities.

---

## EXECUTIVE SUMMARY

**Basset Hound** is a lightweight, API-first entity relationship engine for OSINT investigations, built on:
- **FastAPI** (modern async Python framework)
- **Neo4j 5.28** (graph database for relationships)
- **Redis** (optional caching layer)
- **MCP (Model Context Protocol)** for AI integration
- **Pydantic v2** (data validation)

**Completion Status:** Production-ready with 25+ completed phases, 1,800+ test cases passing.

**Core Value:** "Store now, connect later" - Capture unlinked data immediately, discover relationships as investigation progresses.

---

## ARCHITECTURE OVERVIEW

### 1. OVERALL ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────┐
│                      Basset Hound                            │
├─────────────────────────────────────────────────────────────┤
│  FastAPI (8000)  │  MCP Server  │  Celery Workers           │
├─────────────────────────────────────────────────────────────┤
│                     Services Layer                           │
│  • Entity Management    • Orphan Data    • Graph Analysis   │
│  • Auto-Linking         • Search         • Timeline         │
│  • Bulk Operations      • Reports        • Cache            │
├─────────────────────────────────────────────────────────────┤
│                     Neo4j 5.28 + GDS                         │
│  Entities + Relationships + Indexes + Full-text Search      │
└─────────────────────────────────────────────────────────────┘
```

### 2. KEY COMPONENTS

**Entry Points:**
- `/api/main.py` - FastAPI application (async)
- `/main.py` - Unified entry (FastAPI + MCP server)
- `/app.py` - Legacy Flask UI (deprecated)
- `/mcp/server.py` - MCP server for AI tool integration

**Core Layers:**
- `/api/routers/` - REST API endpoints (26 routers, 150+ endpoints)
- `/api/services/` - Business logic (25+ services)
- `/api/models/` - Pydantic v2 data models (strict validation)
- `/neo4j_handler.py` - Database abstraction (1400+ lines)

---

## DETAILED FEATURE ANALYSIS

### 1. DATA FIELD DETECTION & INGESTION

#### A. Identifier Type Detection System

**Supported Identifier Types (15 types):**
```python
EMAIL, PHONE, CRYPTO_ADDRESS, USERNAME, IP_ADDRESS,
DOMAIN, URL, SOCIAL_MEDIA, LICENSE_PLATE, PASSPORT,
SSN, ACCOUNT_NUMBER, MAC_ADDRESS, IMEI, OTHER
```

**Location:** `/api/models/orphan.py` - `IdentifierType` enum

**Detection Flow:**
1. User submits raw data (email, phone, crypto address, etc.)
2. System auto-detects identifier type using pattern matching
3. Data normalized to standard format
4. Stored as orphan data (unlinked state)
5. Auto-linked to entities when connections discovered

#### B. Crypto Address Detection Engine

**File:** `/api/services/crypto_detector.py` (40+ patterns)

**Supported Cryptocurrencies (30+):**
- **Bitcoin Family:** BTC (P2PKH, P2SH, Bech32, Taproot, Testnet)
- **Ethereum:** ETH (EVM addresses)
- **EVM Chains:** BNB, MATIC, AVAX, ARB (using EVM pattern)
- **Altcoins:** LTC, DOGE, BCH, XRP, ADA, SOL, ATOM, DOT, TRX, XMR, ZEC, DASH
- **Cardano:** ADA (Byron, Shelley)
- **Algorand, Near, Harmony, Flow, Tezos**

**Detection Algorithm:**
```python
CryptoDetectionResult:
  - address: str
  - detected: bool
  - coin_name: str (e.g., "Bitcoin")
  - coin_ticker: str (e.g., "BTC")
  - network: str (e.g., "mainnet", "testnet")
  - address_type: str (e.g., "Bech32 (Native SegWit)")
  - confidence: float (0.0-1.0)
  - explorer_url: str (auto-generated blockchain explorer link)
```

**API Endpoints:**
```
POST /api/v1/crypto/ticker/{address}         - Single detection
POST /api/v1/crypto/ticker/batch              - Batch detection (100 max)
GET /api/v1/crypto/currencies                 - List 30+ supported cryptocurrencies
GET /api/v1/crypto/explorer-url/{address}    - Generate explorer URL
```

#### C. Data Normalization Service

**File:** `/api/services/normalizer.py` (600+ lines)

**Normalizes 8 Identifier Types:**

1. **Phone Numbers**
   - Input: `(555) 123-4567`, `+1-555-123-4567`
   - Normalized: `5551234567`, `+15551234567`
   - Components extracted: `country_code`, `local_number`, `has_country_code`

2. **Email Addresses**
   - Input: `User@EXAMPLE.COM`, `service+support@gmail.com`
   - Normalized: `user@example.com`
   - Plus-addressing: Stores both normalized and base email
   - Components: `user`, `domain`, `tag` (if plus-addressing)

3. **Usernames**
   - Input: `@JohnDoe`, `JOHNNY123`
   - Normalized: `johndoe`, `johnny123`
   - Removes leading @, lowercases

4. **Domains**
   - Input: `https://WWW.Example.COM/`
   - Normalized: `example.com`
   - Removes protocol, www, trailing slashes

5. **URLs**
   - Input: `HTTP://WWW.Example.COM/Path/Page`
   - Normalized: `http://example.com/Path/Page`
   - Lowercases domain, preserves path case
   - Extracts: `scheme`, `domain`, `path`, `query`, `fragment`

6. **IP Addresses (IPv4 & IPv6)**
   - Input: `192.168.001.001`
   - Normalized: `192.168.1.1` (removes leading zeros)
   - IPv6: `::1` → `0000:0000:0000:0000:0000:0000:0000:0001`

7. **Cryptocurrency Addresses**
   - Trims whitespace, preserves case (checksum-sensitive)
   - Auto-detects coin type (integrated with crypto_detector.py)

8. **MAC Addresses**
   - Input: `00-1A-2B-3C-4D-5E`, `00:1a:2b:3c:4d:5e`
   - Normalized: `00:1a:2b:3c:4d:5e` (colon-separated lowercase)

**Result Structure:**
```python
NormalizedResult:
  - original: str
  - normalized: str
  - is_valid: bool
  - components: Dict[str, Any]
  - alternative_forms: List[str]
  - errors: List[str]
```

#### D. Orphan Data Management System

**File:** `/api/services/orphan_service.py` (600+ lines)

**Core Concept:** Unlinked identifiers (emails, phones, crypto, etc.) that haven't been assigned to entities yet.

**CRUD Operations:**
- `create_orphan()` - Create new orphan record
- `get_orphan()` - Retrieve by ID
- `update_orphan()` - Modify metadata
- `delete_orphan()` - Remove record
- `list_orphans()` - List with filtering/pagination

**Search Features:**
- Full-text search on identifier values and metadata
- Filter by identifier_type, linked status, date range
- Pagination support
- Tag-based filtering

**Auto-Linking Features:**
```python
SCORE_EXACT_MATCH = 10.0         # Exact identifier match
SCORE_FUZZY_HIGH = 9.0            # High fuzzy name match
SCORE_FUZZY_MEDIUM = 7.0          # Medium fuzzy match
SCORE_FUZZY_LOW = 5.0             # Low fuzzy match
SCORE_CONTEXT_HIGH = 3.0          # High context match
SUGGESTION_THRESHOLD = 7.0         # Minimum for suggestions
```

**Identifier Field Mapping:**
```python
EMAIL → ["core.email", "contact.email", "online.email"]
PHONE → ["core.phone", "contact.phone"]
USERNAME → ["online.username", "social.username"]
CRYPTO_ADDRESS → ["financial.crypto_address", "blockchain.address"]
IP_ADDRESS → ["technical.ip_address", "network.ip"]
DOMAIN → ["online.domain", "website.domain"]
URL → ["online.url", "social.profile_url"]
MAC_ADDRESS → ["technical.mac_address", "network.mac"]
IMEI → ["device.imei", "technical.imei"]
```

**Bidirectional Data Flow:**
- **Link to Entity:** Move orphan data into entity profile
- **Detach from Entity:** Convert entity field back to orphan status
- Data never truly deleted - soft delete through state changes

**API Endpoints (10+ endpoints):**
```
POST /projects/{id}/orphans                 - Create
GET /projects/{id}/orphans                  - List with search
GET /projects/{id}/orphans/{orphan_id}      - Get specific
PUT /projects/{id}/orphans/{orphan_id}      - Update
DELETE /projects/{id}/orphans/{orphan_id}   - Delete
GET /projects/{id}/orphans/{id}/suggestions - Entity match suggestions
POST /projects/{id}/orphans/{id}/link       - Link to entity
POST /projects/{id}/orphans/detach          - Detach from entity
POST /projects/{id}/orphans/batch           - Bulk import
GET /projects/{id}/orphans/duplicates       - Find duplicates
```

#### E. Data Import Connectors (7 Tools)

**File:** `/api/services/data_import.py` (2000+ lines)

**Supported OSINT Tools:**

1. **Maltego** - CSV entity exports
   - Maps entity types and relationships
   - Preserves connection data

2. **SpiderFoot** - JSON scan results
   - 20+ data type mappings
   - Module attribution
   - Automatic type detection

3. **TheHarvester** - Email/domain/IP discovery
   - JSON format parsing
   - Multi-type result handling

4. **Shodan** - Host/service data
   - JSON host exports
   - Service and banner information
   - Port mappings

5. **Have I Been Pwned (HIBP)** - Breach data
   - JSON breach imports
   - Credential handling

6. **Generic CSV** - Configurable mapping
   - User-defined column mapping
   - Flexible type detection

7. **Generic JSON** - Flexible schema
   - Handles arbitrary JSON structures
   - Auto field detection

**Import Features:**
- **Type Detection:** Auto-detects emails, phones, IPs, domains, URLs, usernames, crypto, MAC
- **Validation:** Pre-import validation with detailed error reporting
- **Dry-Run Mode:** Validate without creating records
- **Error Handling:** Tracks success/error/warning per record
- **Batch Processing:** Efficient bulk creation with Neo4j UNWIND

**ImportResult Statistics:**
```python
ImportResult:
  - total_records: int
  - entities_created: int
  - orphans_created: int
  - relationships_created: int
  - skipped: int
  - errors: List[ImportError]
  - warnings: List[ImportWarning]
  - entity_ids: List[str]
  - orphan_ids: List[str]
  - source_tool: str
  - import_timestamp: datetime
```

---

### 2. VALIDATION & VERIFICATION MECHANISMS

#### A. Data Quality Service

**File:** `/api/services/data_quality.py` (900+ lines)

**6 Quality Dimensions:**

1. **Completeness** - Percentage of fields populated (0-100%)
2. **Freshness** - Time since last update (days)
3. **Accuracy** - Confidence based on source reliability (0-1.0)
4. **Consistency** - Cross-field validation and conflicts
5. **Uniqueness** - Duplicate field value detection
6. **Validity** - Format and constraint validation

**Source Reliability Ratings (11+ sources):**
```python
manual_entry: 0.90          # User manually entered
maltego: 0.85               # Maltego tool discovery
shodan: 0.85                # Shodan host data
spiderfoot: 0.80            # SpiderFoot reconnaissance
hibp: 0.95                  # Have I Been Pwned breaches
api_query: 0.75             # External API result
web_scrape: 0.70            # Web scraping result
social_profile: 0.65        # Social media profile
community_report: 0.60      # Community-reported data
user_generated: 0.50        # User input (unverified)
system_generated: 0.80      # Auto-generated (algorithmic)
```

**Quality Scoring:**
- Weighted combination of 6 dimensions
- Letter grades: A (90+), B (80-89), C (70-79), D (60-69), F (<60)
- Field-level recommendations for improvement
- Project-wide quality reports with grade distribution

**API Endpoints:**
```
POST /data-quality/score                    - Score single entity
POST /data-quality/score/batch              - Score multiple
GET /data-quality/config                    - Get config
PUT /data-quality/config                    - Update config
GET /data-quality/sources                   - List sources
PUT /data-quality/sources/{source}          - Update reliability
POST /data-quality/compare                  - Compare entities
GET /data-quality/stats                     - Service statistics
POST /data-quality/clear-cache              - Clear cache
GET /projects/{project}/data-quality/report - Project report
```

#### B. Deduplication Service

**File:** `/api/services/deduplication.py` (900+ lines)

**7 Match Types:**
1. **Exact** - Byte-for-byte identical
2. **Case Insensitive** - Differs only in case
3. **Fuzzy** - Levenshtein similarity > threshold
4. **Phonetic** - Sounds-alike matching (Soundex-like)
5. **Normalized** - Match after normalization
6. **Partial** - Substring match
7. **Token Set** - Word-based set matching

**7 Merge Strategies:**
1. **Keep Primary** - Keep primary entity, discard duplicate
2. **Keep Duplicate** - Keep duplicate, merge into it
3. **Keep Newest** - Keep entity with most recent update
4. **Keep Oldest** - Keep entity with earliest creation
5. **Keep Longest** - Keep entity with most data
6. **Keep All** - Merge all fields (manual conflicts)
7. **Manual** - Mark for manual review

**Deduplication Features:**
- Levenshtein similarity scoring for fuzzy matches
- Phonetic matching with algorithm
- Merge preview with conflict detection
- Merge history and undo support
- Project-wide duplicate reports

**API Endpoints:**
```
POST /deduplication/find                    - Find duplicates for entity
POST /deduplication/find-all                - Find all project duplicates
POST /deduplication/preview                 - Preview merge
POST /deduplication/merge                   - Execute merge
POST /deduplication/undo/{merge_id}         - Undo merge
GET /deduplication/history                  - Get merge history
GET /deduplication/config                   - Get config
PUT /deduplication/config                   - Update config
GET /deduplication/stats                    - Service statistics
POST /deduplication/clear-cache             - Clear cache
GET /projects/{project}/deduplication/report - Project dedup report
```

#### C. Auto-Linking Service

**File:** `/api/services/auto_linker.py` (600+ lines)

**Matching Algorithm:**
- Identifier weights: Email (3.0), Phone (2.5), Crypto (3.5), Handles (2.0)
- Duplicate threshold: Score ≥5.0
- Link threshold: Score ≥2.0
- Fuzzy + identifier matching integration

**Features:**
- Project-wide duplicate scanning
- Entity-specific duplicate finding
- Suggested link discovery
- Merge support with profile consolidation
- Identifier field mapping

**API Endpoints:**
```
GET /auto-link/duplicates                           - Project duplicates
GET /auto-link/entities/{id}/duplicates             - Entity duplicates
GET /auto-link/entities/{id}/suggested-links        - Link suggestions
GET /projects/{project}/auto-link/entities/{id}/fuzzy-matches - Fuzzy matches
GET /projects/{project}/auto-link/fuzzy-config      - Fuzzy config
POST /auto-link/scan                                - Full scan
POST /auto-link/merge                               - Merge entities
GET /auto-link/identifier-fields                    - List identifier fields
```

---

### 3. SCREENSHOT & ELEMENT SELECTION CAPABILITIES

#### A. Browser Automation Strategy (Planned)

**Documentation File:** `/docs/03-BROWSER-AUTOMATION-STRATEGY.md` (730+ lines)

**Proposed Chrome Extension (MV3) Architecture:**

**Components:**
1. **Background Service Worker** (`background.js`)
   - WebSocket connection to basset-hound
   - Command routing and dispatch
   - State management

2. **Content Script** (`content.js`)
   - DOM interaction and element selection
   - Form analysis and filling
   - Page state extraction
   - Screenshot capture
   - Element waiting logic

3. **Popup UI** (optional)
   - Connection status display
   - Task queue management
   - Manual controls

**Command Types (12 commands):**
```javascript
navigate(url, wait_for)              - Navigate to URL
fill_form(fields, submit)            - Fill form fields
click(selector, wait_after)          - Click element
get_content(selector)                - Extract element content
screenshot()                         - Capture page screenshot
wait_for_element(selector, timeout)  - Wait for element
get_page_state()                     - Extract form/button state
execute_script(script)               - Execute custom JavaScript
hover(selector)                      - Hover over element
scroll(x, y)                         - Scroll page
get_cookies()                        - Extract cookies
set_cookie(name, value, domain)      - Set cookie
```

**Page State Extraction:**
```javascript
get_page_state() returns:
{
  url: string,
  title: string,
  forms: [
    {
      id: string,
      name: string,
      action: string,
      method: string,
      fields: [
        {
          selector: string,
          type: string,
          name: string,
          id: string,
          label: string,
          required: boolean,
          value: string,
          options: [{value, text}]
        }
      ]
    }
  ],
  links: [{text, href}],
  buttons: [{selector, text}]
}
```

**Element Selection Methods:**
1. **ID-based:** `#element_id`
2. **Name-based:** `[name="field_name"]`
3. **CSS path:** `div.container > form > input[type="email"]`
4. **Aria-label:** `[aria-label*="search"]`
5. **Placeholder:** `[placeholder*="keyword"]`
6. **Label association:** Via `<label for="id">`

**Smart Label Detection:**
```javascript
function findLabel(element) {
  // 1. Check label with 'for' attribute
  if (element.id) {
    const label = document.querySelector(`label[for="${element.id}"]`);
    if (label) return label.innerText.trim();
  }
  
  // 2. Check wrapping label
  const parentLabel = element.closest('label');
  if (parentLabel) return parentLabel.innerText.trim();
  
  // 3. Check aria-label
  if (element.getAttribute('aria-label')) {
    return element.getAttribute('aria-label');
  }
  
  // 4. Check placeholder
  if (element.placeholder) return element.placeholder;
}
```

**Security Considerations:**
- Local-only WebSocket (localhost only)
- Command validation before execution
- Timeout protection (configurable per command)
- User notification when automation active
- Manual pause/stop capability
- Password masking in page state
- No credential logging

#### B. Screenshot Capabilities

**Current Implementation:**

1. **Chrome Extension Screenshot** (from browser automation doc)
   ```javascript
   chrome.tabs.captureVisibleTab(null, { format: 'png' }, (dataUrl) => {
     // Returns base64-encoded PNG
   })
   ```

2. **Server-Side Screenshot** (planned)
   - Capture via automation or headless browser
   - Store as file attachment
   - Link to entity records
   - Evidence collection

#### C. URL & Date Capture

**URL Capture Methods:**

1. **From Page State Extraction**
   - `window.location.href` - Current page URL
   - All links extracted from page
   - Stored in graph relationships

2. **From Data Import**
   - Maltego exports contain URLs
   - SpiderFoot results include source URLs
   - Normalized and stored

3. **From Orphan Data**
   - URL identifier type with normalization
   - Domain extraction from URLs
   - Validation and format standardization

**Date Capture Methods:**

1. **From Config Schema**
   - `date` field type in `/data_config.yaml`
   - Date of birth, event dates
   - Extracted from web scraping

2. **Auto-Generated**
   - Created timestamp on entity creation
   - Updated timestamp on modification
   - Import timestamps on data ingestion

3. **From Data Import**
   - Event dates from historical records
   - Timestamps from breach data (HIBP)
   - Discovery dates from SpiderFoot

4. **Timeline Service**
   - Track all entity changes over time
   - Event timestamps (CREATED, UPDATED, LINKED, etc.)
   - Period-based analysis

---

### 4. TECHNOLOGY STACK

#### Core Technologies

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Framework** | FastAPI | 0.115+ | Async REST API, auto-docs |
| **Database** | Neo4j | 5.28+ | Graph relationships, full-text search |
| **Graph Analytics** | Neo4j GDS | Included | Community detection, centrality |
| **Caching** | Redis | 7.0 (optional) | Query caching, job queue |
| **Task Queue** | Celery | 5.3+ | Background jobs, scheduling |
| **Server** | Uvicorn | 0.32+ | ASGI HTTP server |
| **Validation** | Pydantic | 2.10+ | Strict data models |
| **Authentication** | JWT + API Keys | Custom | Auth layer |
| **ORM** | Neo4j Python Driver | 5.10+ | Database abstraction |
| **Web Framework (Legacy)** | Flask | 3.1 | Deprecated UI |
| **Async Client** | httpx | 0.27+ | Async HTTP requests |
| **File Upload** | aiofiles | 24.1+ | Async file operations |
| **Templating** | Jinja2 | 3.0+ | Report templates |
| **MCP Support** | FastMCP | 1.0+ | AI tool integration |

#### Browser Extension Stack (Proposed)

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Extension Format** | Chrome MV3 | Manifest V3 support |
| **Background Script** | Service Worker | Message routing, WebSocket |
| **Content Script** | Vanilla JS | DOM interaction |
| **Communication** | WebSocket | Real-time bidirectional |
| **Serialization** | JSON | Command/response format |
| **Storage** | chrome.storage | Extension state persistence |

#### Python Packages (Key Dependencies)

```
fastapi>=0.115.0              # REST API framework
uvicorn[standard]>=0.32.0     # ASGI server
pydantic>=2.10.0              # Data validation
python-jose[cryptography]     # JWT handling
passlib[bcrypt]               # Password hashing
neo4j>=5.10.0                 # Database driver
redis>=5.0.0                  # Cache (optional)
celery>=5.3.0                 # Task queue
aiofiles>=24.1.0              # Async files
httpx>=0.27.0                 # Async HTTP
rapidfuzz>=3.0.0              # Fuzzy matching
markdown>=3.0.0               # Markdown to HTML
python-multipart>=0.0.12      # Form parsing
croniter>=1.0.0               # Cron scheduling
mcp>=1.0.0                    # Model Context Protocol
```

---

### 5. CURRENT STATE OF COMPLETION

#### Phase Completion Summary (25 Phases Completed)

| Phase | Title | Status | Completion Date |
|-------|-------|--------|-----------------|
| 1 | FastAPI Migration | ✅ | 2025-12-27 |
| 2 | MCP Server Integration | ✅ | 2025-12-27 |
| 2.5 | Crypto Detection | ✅ | 2025-12-27 |
| 3 | Advanced Relationships | ✅ | 2025-12-27 |
| 4 | Performance & Caching | ✅ | 2025-12-27 |
| 5 | Multi-Entity Types | ✅ | 2025-12-27 |
| 6 | Cross-Project Linking | ✅ | 2025-12-27 |
| 7 | Timeline & Bulk Ops | ✅ | 2025-12-27 |
| 8 | Crypto Ticker & Search | ✅ | 2025-12-27 |
| 9 | Real-Time & Automation | ✅ | 2025-12-27 |
| 10 | Background Processing | ✅ | 2025-12-27 |
| 11 | Production Hardening | ✅ | 2025-12-27 |
| 12 | Query Optimization | ✅ | 2025-12-28 |
| 13 | Infrastructure (Docker/K8s) | ✅ | 2025-12-28 |
| 14 | Local-First Simplification | ✅ | 2025-12-28 |
| 15 | Orphan Data Management | ✅ | 2025-12-29 |
| 16 | Visualization & Data Import | ✅ | 2025-12-29 |
| 17 | Frontend Integration | ✅ | 2025-12-29 |
| 18 | Advanced Graph Analytics | ✅ | 2025-12-29 |
| 19 | Deployment & Infrastructure | ✅ | 2025-12-29 |
| 20 | Query & Performance Optimization | ✅ | 2025-12-29 |
| 21 | Import/Export Flexibility | ✅ | 2025-12-29 |
| 22 | API Endpoints (Phase 21) | ✅ | 2025-12-29 |
| 23 | Saved Search Configurations | ✅ | 2025-12-29 |
| 24 | Webhook Integrations | ✅ | 2025-12-29 |
| 25 | Entity Deduplication & Data Quality | ✅ | 2025-12-29 |

**Test Coverage:** 1,800+ tests passing

#### API Endpoint Count
- **26 Routers** across multiple modules
- **150+ REST Endpoints** covering all operations
- **Full OpenAPI documentation** at `/docs`

#### Database Features
- **26 Relationship Types** (WORKS_WITH, KNOWS, FAMILY, etc.)
- **6 Entity Types** (Person, Organization, Device, Location, Event, Document)
- **15 Identifier Types** (EMAIL, PHONE, CRYPTO, etc.)
- **50+ Data Fields** in configuration schema
- **Full-text search** with Neo4j Lucene indexing
- **Graph analysis** (path finding, clustering, centrality)

---

### 6. EXISTING INTEGRATION MECHANISMS

#### A. External Systems Integration

1. **OSINT Tool Imports (7 tools)**
   - Maltego, SpiderFoot, TheHarvester, Shodan, HIBP, Generic CSV, Generic JSON

2. **Browser Automation** (Planned)
   - Chrome Extension MV3 for interactive web scraping
   - WebSocket communication with backend

3. **MCP Server** (FastMCP)
   - 15+ tools for AI integration
   - Entity CRUD, relationships, search, reports

4. **REST API**
   - Full-featured HTTP API for external tools
   - OAuth2 ready (JWT + API keys)
   - CORS support

5. **Webhooks** (24+ event types)
   - Event-driven integration
   - HMAC signature verification
   - Retry logic with exponential backoff
   - 10 req/sec outbound rate limiting

6. **Export Capabilities**
   - LLM Export (Markdown, JSON, YAML, Plain Text, XML)
   - Graph formats (GraphML, GEXF, D3, Cytoscape, DOT, Pajek)
   - CSV/JSON bulk export

#### B. Search & Query Features

**Full-Text Search:**
- Neo4j Lucene-based indexing
- Fuzzy matching with typo tolerance
- Result highlighting with `**matched text**` snippets
- Field-specific search (`email:john@example.com`)
- Multi-project search

**Saved Searches:**
- Save search configurations with parameters
- Categorization (GENERAL, INVESTIGATION, MONITORING, etc.)
- Tag-based organization
- Execution tracking (popularity, recency)
- Public/private scopes

**Advanced Search API:**
```
GET /api/v1/search?query=email:*@gmail.com&limit=50
GET /api/v1/projects/{project}/search?query=...
GET /api/v1/saved-searches?category=INVESTIGATION
```

#### C. Real-Time Features

**WebSocket Notifications:**
- Connection management with heartbeat
- Project-scoped subscriptions
- 10+ notification types:
  - Entity CRUD events
  - Relationship changes
  - Search executed
  - Report generation
  - Bulk import progress
  - System health

**API Endpoint:**
```
WS /api/v1/ws - WebSocket connection
GET /api/v1/ws/stats - Connection statistics
```

#### D. Scheduling & Automation

**Report Scheduling:**
- Frequencies: ONCE, HOURLY, DAILY, WEEKLY, MONTHLY
- Custom cron expressions
- Timezone awareness
- Manual trigger capability

**Background Jobs:**
- Job types: REPORT, EXPORT, BULK_IMPORT, CUSTOM
- Priority levels: CRITICAL, HIGH, NORMAL, LOW
- Status tracking: PENDING, RUNNING, COMPLETED, FAILED
- Retry logic with exponential backoff

---

### 7. DATA FLOW ARCHITECTURE

#### Complete Ingestion Flow

```
External Data Source (CSV, JSON, Browser)
        ↓
[Import Service] - Parse & normalize
        ↓
[Data Normalizer] - Standardize formats
        ↓
[Type Detection] - Identify identifier types
        ↓
[Validation] - Quality checks
        ↓
[Crypto Detector] - Detect coins if applicable
        ↓
[Auto-Linker] - Find potential matches
        ↓
[Neo4j Storage] - Create orphans or entities
        ↓
[Cache Invalidation] - Update cache
        ↓
[Webhooks] - Notify subscribers
```

#### Orphan Data to Entity Linking

```
Orphan Data (unlinked identifier)
        ↓
[Auto-Linker] - Score potential entity matches
        ↓
[Fuzzy Matcher] - Apply fuzzy matching
        ↓
[Suggest Matches] - Present options to user
        ↓
[User Selection] - Choose target entity
        ↓
[Link Operation] - Move to entity profile
        ↓
[Neo4j Relationship] - LINKED_TO relationship
        ↓
[Deduplication Check] - Identify duplicates
        ↓
[Merge Option] - Combine if same person
```

---

## KEY INSIGHTS & ANALYSIS

### 1. Strengths

✅ **Excellent Data Detection & Normalization**
- Comprehensive identifier type support (15 types)
- Robust normalization for 8+ data formats
- Smart email handling (plus-addressing)
- 30+ cryptocurrency patterns

✅ **Flexible Data Ingestion**
- 7 OSINT tool connectors with extensible base class
- Orphan data management for unlinked identifiers
- Bulk import with validation and error tracking
- Dry-run mode for testing

✅ **Production-Ready Quality**
- 1,800+ passing tests
- Comprehensive error handling
- Thread-safe services with RLock
- Comprehensive logging

✅ **Rich Graph Capabilities**
- 26 relationship types with properties
- Path finding and clustering
- Centrality analysis
- 6 entity types for flexible modeling

✅ **Modern Architecture**
- FastAPI async/await throughout
- Pydantic v2 strict validation
- Neo4j graph database
- MCP integration for AI tools

### 2. Design Considerations

⚠️ **Browser Automation Status**
- Planned but NOT YET IMPLEMENTED
- Comprehensive architecture designed in docs
- Chrome MV3 extension structure defined
- WebSocket communication protocol specified
- Currently requires manual integration

⚠️ **Performance Optimizations**
- Query caching with configurable TTLs
- Batch operations reduce N+1 queries
- Index optimization for composite keys
- Redis optional (in-memory fallback available)

⚠️ **Local-First Approach**
- NO API rate limiting (scales with hardware)
- Single-user design (no multi-user auth)
- Orphan rate limiting for outbound webhooks only
- Designed for local security researcher use

### 3. Missing or Incomplete Features

❌ **Browser Automation NOT IMPLEMENTED**
- Extension code only exists in documentation
- No actual Chrome extension files in repo
- Manual implementation required

⚠️ **UI/Frontend**
- Legacy Flask UI (deprecated)
- API-first design (no modern SPA included)
- Frontend components API defined but not implemented

⚠️ **Advanced Features Partially Complete**
- Some ML analytics features sketched
- Template marketplace defined but basic
- Some reporting features have mock implementations

---

## FILE STRUCTURE

```
basset-hound/
├── api/                              # FastAPI application
│   ├── __init__.py
│   ├── main.py                      # FastAPI entry point
│   ├── config.py                    # Configuration (Pydantic Settings)
│   ├── dependencies.py              # Dependency injection
│   ├── auth/
│   │   ├── jwt.py                  # JWT utilities
│   │   ├── api_key.py              # API key management
│   │   └── dependencies.py         # Auth dependencies
│   ├── models/
│   │   ├── entity_types.py         # EntityType enum (6 types)
│   │   ├── relationship.py         # RelationshipType enum (26 types)
│   │   ├── orphan.py               # Orphan data models (15 identifier types)
│   │   ├── visualization.py        # Graph visualization models
│   │   ├── data_import.py          # Import result models
│   │   ├── entity_type_ui.py       # UI configuration models
│   │   └── *.py                    # Other Pydantic models
│   ├── services/
│   │   ├── neo4j_service.py        # Async Neo4j operations
│   │   ├── orphan_service.py       # Orphan CRUD & auto-linking
│   │   ├── normalizer.py           # Data normalization (8 types)
│   │   ├── crypto_detector.py      # Crypto detection (30+ coins)
│   │   ├── data_import.py          # Import connectors (7 tools)
│   │   ├── auto_linker.py          # Entity auto-linking
│   │   ├── fuzzy_matcher.py        # Fuzzy matching with rapidfuzz
│   │   ├── graph_visualization.py  # Layout + export (5 algorithms)
│   │   ├── data_quality.py         # Quality scoring (6 dimensions)
│   │   ├── deduplication.py        # Duplicate detection (7 strategies)
│   │   ├── cache_service.py        # Redis/in-memory caching
│   │   ├── timeline_service.py     # Timeline tracking
│   │   ├── webhook_service.py      # Webhook management
│   │   ├── search_service.py       # Full-text search
│   │   ├── saved_search.py         # Search configuration
│   │   ├── report_storage.py       # Report versioning
│   │   ├── job_runner.py           # Background jobs (Celery)
│   │   ├── template_service.py     # Custom templates
│   │   └── *.py                    # 20+ other services
│   ├── routers/
│   │   ├── projects.py             # Project CRUD
│   │   ├── entities.py             # Entity management
│   │   ├── relationships.py        # Relationship management
│   │   ├── orphan.py               # Orphan data API
│   │   ├── analysis.py             # Graph analysis
│   │   ├── search.py               # Search endpoints
│   │   ├── visualization.py        # Graph visualization
│   │   ├── import_data.py          # Data import
│   │   ├── crypto.py               # Crypto ticker
│   │   ├── webhooks.py             # Webhook management
│   │   ├── timeline.py             # Timeline API
│   │   ├── saved_search.py         # Saved search API
│   │   ├── deduplication.py        # Dedup API
│   │   ├── data_quality.py         # Quality API
│   │   └── *.py                    # 12+ other routers
│   └── utils/
│       └── crypto_detector.py      # Crypto patterns
│
├── mcp/                             # MCP Server
│   ├── __init__.py
│   └── server.py                   # FastMCP with 15 tools
│
├── neo4j_handler.py                 # Database abstraction (1400+ lines)
├── config_loader.py                 # YAML config loader
├── main.py                          # Unified entry point (FastAPI + MCP)
├── app.py                           # Legacy Flask UI (deprecated)
│
├── docs/                            # Documentation
│   ├── ROADMAP.md                  # Detailed roadmap (2000+ lines)
│   ├── README.md                    # User guide
│   ├── 03-BROWSER-AUTOMATION-STRATEGY.md  # Browser extension design
│   ├── 04-PENTESTING-INTEGRATION.md       # Pentest workflows
│   ├── findings/
│   │   ├── 01-FASTAPI-MIGRATION.md
│   │   ├── 02-MCP-SERVER.md
│   │   ├── 04-CRYPTO-DETECTION.md
│   │   ├── 15-PHASE15-ORPHAN-DATA-NORMALIZATION.md
│   │   ├── 16-PHASE16-ENHANCED-VISUALIZATION-DATA-IMPORT.md
│   │   ├── 17-PHASE17-FRONTEND-INTEGRATION-UI-ENHANCEMENTS.md
│   │   ├── 18-PHASE18-ADVANCED-GRAPH-ANALYTICS.md
│   │   ├── 19-PHASE19-DEPLOYMENT-INFRASTRUCTURE.md
│   │   ├── 20-PHASE20-QUERY-PERFORMANCE-OPTIMIZATION.md
│   │   ├── 21-PHASE21-IMPORT-EXPORT-FLEXIBILITY.md
│   │   ├── 22-PHASE22-API-ENDPOINTS-PHASE21-SERVICES.md
│   │   ├── 23-PHASE23-SAVED-SEARCH-CONFIGURATIONS.md
│   │   ├── 24-PHASE24-WEBHOOK-INTEGRATIONS.md
│   │   └── 25-PHASE25-DEDUPLICATION-DATA-QUALITY.md
│
├── tests/                           # 1,800+ tests
│   ├── test_orphan_service.py
│   ├── test_normalizer.py
│   ├── test_crypto_detector.py
│   ├── test_data_import.py
│   ├── test_fuzzy_matcher.py
│   ├── test_auto_linker.py
│   ├── test_deduplication_quality.py
│   └── test_*.py                   # 50+ test files
│
├── data_config.yaml                 # Schema (70+ fields, 35+ sections)
├── docker-compose.yml               # Full stack (Neo4j + Redis + Celery)
├── Dockerfile                       # Multi-stage build
├── install.sh                       # Ubuntu 22.04 native install
├── requirements.txt                 # Python dependencies
└── README.md                        # Project overview
```

---

## DEPLOYMENT OPTIONS

### 1. Docker (Recommended)

**Stack includes:**
- Neo4j 5.28 + Graph Data Science plugin
- Redis 7.0 with persistence
- FastAPI application (port 8000)
- Celery worker + scheduler
- Health checks and dependency management

**Start:**
```bash
docker-compose up -d
# FastAPI: http://localhost:8000
# OpenAPI: http://localhost:8000/docs
# Neo4j Browser: http://localhost:7474
# Redis: localhost:6379
```

### 2. Native Ubuntu 22.04

**Install script:** `/install.sh` (24KB)

Installs:
- Python 3.12
- Neo4j 5.x with GDS plugin
- Redis 7.0
- Creates venv with all dependencies
- Systemd service files (optional)

**Start:**
```bash
python main.py
# Runs FastAPI + MCP server concurrently
```

---

## CRITICAL GAPS & RECOMMENDATIONS

### 🔴 Critical Gaps

1. **Browser Automation Not Implemented**
   - Only documented in `/docs/03-BROWSER-AUTOMATION-STRATEGY.md`
   - No actual Chrome extension code
   - Recommendation: Implement extension from documented spec

2. **Frontend UI Missing**
   - Legacy Flask deprecated
   - No modern SPA included
   - Recommendation: Build React/Vue app using provided API

3. **Documentation Examples**
   - Some documentation shows pseudocode
   - Template marketplace is skeletal
   - Recommendation: Implement missing features from Phase docs

### 🟡 Important Considerations

1. **Single-User Local Design**
   - No multi-user authentication (by design)
   - Good for security researchers
   - Not suitable for team collaboration without modifications

2. **Hardware Scaling**
   - "No artificial limits" philosophy
   - Performance depends on:
     - CPU cores
     - RAM (entity caching)
     - Neo4j database size
     - Disk I/O

3. **Graph Database Learning**
   - Neo4j Cypher queries for advanced use
   - GDS plugin for graph algorithms
   - Requires understanding of property graphs

---

## CODE QUALITY OBSERVATIONS

| Aspect | Rating | Notes |
|--------|--------|-------|
| **Error Handling** | A+ | Comprehensive try/except, logging throughout |
| **Testing** | A+ | 1,800+ tests, good coverage of services |
| **Code Organization** | A | Clean separation of concerns, routers/services/models |
| **Documentation** | A | Excellent inline docs and phase documentation |
| **Security** | A | JWT + API keys, CORS, input validation |
| **Performance** | A- | Query optimization done, caching available |
| **Type Safety** | A | Pydantic v2, full type hints |
| **API Design** | A | REST conventions, OpenAPI docs, versioning |
| **Data Validation** | A+ | Strict Pydantic models, normalization |

---

## CONCLUSION

Basset Hound is a **production-ready, comprehensive OSINT platform** with:

✅ **Excellent data field detection** (15+ identifier types)  
✅ **Robust normalization** (8+ data formats)  
✅ **7 OSINT tool import connectors**  
✅ **Advanced graph analysis** (26 relationship types)  
✅ **6 entity types** for flexible modeling  
✅ **150+ REST API endpoints**  
✅ **1,800+ passing tests**  
✅ **MCP integration** for AI tools  
✅ **Comprehensive documentation** (25 phases)  

❌ **Browser automation NOT YET implemented**  
❌ **Frontend UI not included**  
❌ **Some advanced features are skeletal**  

**Status:** Suitable for production use as an OSINT data backend. Browser automation requires additional implementation from documented specifications.

---

This comprehensive code review covers all 25 implemented phases, technical stack, data flow, validation mechanisms, and architectural details of the Basset Hound OSINT platform.
</output>
TaskOutput task: "a6f0bd3"
OUT
<retrieval_status>success</retrieval_status>

<task_id>a6f0bd3</task_id>

<task_type>local_agent</task_type>

<status>completed</status>

<output>
[Tool: WebSearch] {"query":"Bitcoin Ethereum address validation checksum algorithm JavaScript library 2025"}
[Tool: WebSearch] {"query":"email verification MX record SMTP validation JavaScript library 2025"}
[Tool: WebSearch] {"query":"libphonenumber JavaScript phone number validation library 2025"}
[Tool: WebSearch] {"query":"WHOIS lookup API free domain verification JavaScript 2025"}
[Tool: WebSearch] {"query":"WHOIS lookup API free domain verification JavaScript 2025"}
[Tool: Glob] {"pattern":"**/*.{ts,js,md}","path":"/home/devel/basset-hound"}
[Tool: Glob] {"pattern":"**/*.{ts,js,md}","path":"/home/devel/basset-hound"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/docs/findings/04-CRYPTO-DETECTION.md"}
[Tool: Glob] {"pattern":"**/*valid*.{ts,js,py}","path":"/home/devel/basset-hound"}
[Tool: Glob] {"pattern":"**/*verif*.{ts,js,py}","path":"/home/devel/basset-hound"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/api/utils/crypto_detector.py"}
[Tool: Glob] {"pattern":"**/*.py","path":"/home/devel/basset-hound"}
[Tool: Grep] {"pattern":"email.*valid|phone.*valid|domain.*valid|whois|MX.*record","-i":true,"path":"/home/devel/basset-hound","output_mode":"files_with_matches"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/docs/ROADMAP.md"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/docs/ROADMAP.md"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/api/services/normalizer.py"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/todo.md"}
[Tool: Read] {"file_path":"/home/devel/basset-hound/todo.md"}

--- RESULT ---
Now I have a comprehensive understanding of the existing codebase. Let me compile a thorough research document on verification methods for OSINT data validation based on my knowledge and the context of this project.

---

# OSINT Data Verification Methods Research

## Executive Summary

This document provides practical implementation recommendations for verifying OSINT data types including cryptocurrency addresses, emails, phone numbers, and domains. Recommendations cover both **client-side** (browser extension) and **server-side** verification approaches.

---

## 1. Cryptocurrency Address Validation

### 1.1 Address Format Validation (Checksum Algorithms)

#### Bitcoin Address Validation

**Legacy (P2PKH/P2SH) Addresses** - Use Base58Check encoding with double SHA-256 checksum:

```javascript
// JavaScript/TypeScript implementation
const bs58 = require('bs58');
const { sha256 } = require('@noble/hashes/sha256');

function validateBitcoinLegacy(address) {
  try {
    // P2PKH starts with '1', P2SH starts with '3'
    if (!/^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$/.test(address)) {
      return false;
    }
    
    const decoded = bs58.decode(address);
    if (decoded.length !== 25) return false;
    
    // Last 4 bytes are checksum
    const payload = decoded.slice(0, -4);
    const checksum = decoded.slice(-4);
    
    // Double SHA-256
    const hash1 = sha256(payload);
    const hash2 = sha256(hash1);
    
    // Compare first 4 bytes of double hash with checksum
    return hash2.slice(0, 4).every((byte, i) => byte === checksum[i]);
  } catch {
    return false;
  }
}
```

**Bech32 (SegWit) Addresses** - Use BIP-173 Bech32 encoding:

```javascript
const { bech32, bech32m } = require('bech32');

function validateBitcoinBech32(address) {
  try {
    // bc1q... for SegWit v0, bc1p... for Taproot
    if (address.startsWith('bc1q')) {
      const decoded = bech32.decode(address);
      return decoded.prefix === 'bc' && decoded.words.length >= 1;
    } else if (address.startsWith('bc1p')) {
      // Taproot uses bech32m
      const decoded = bech32m.decode(address);
      return decoded.prefix === 'bc' && decoded.words.length >= 1;
    }
    return false;
  } catch {
    return false;
  }
}
```

#### Ethereum Address Validation (EIP-55 Checksum)

```javascript
const { keccak256 } = require('@noble/hashes/sha3');

function validateEthereumAddress(address) {
  // Basic format check
  if (!/^0x[a-fA-F0-9]{40}$/.test(address)) {
    return { valid: false, checksumValid: false };
  }
  
  // All lowercase or all uppercase is valid (no checksum)
  const isLower = address === address.toLowerCase();
  const isUpper = address.slice(2) === address.slice(2).toUpperCase();
  
  if (isLower || isUpper) {
    return { valid: true, checksumValid: null }; // No checksum to verify
  }
  
  // EIP-55 checksum validation
  const addressLower = address.slice(2).toLowerCase();
  const hash = Buffer.from(keccak256(addressLower)).toString('hex');
  
  for (let i = 0; i < 40; i++) {
    const char = addressLower[i];
    if (/[a-f]/.test(char)) {
      const shouldBeUpper = parseInt(hash[i], 16) >= 8;
      const isUpper = address[i + 2] === char.toUpperCase();
      if (shouldBeUpper !== isUpper) {
        return { valid: true, checksumValid: false };
      }
    }
  }
  
  return { valid: true, checksumValid: true };
}
```

#### Multi-Chain Address Libraries

| Library | Languages | Chains Supported | Client-Side |
|---------|-----------|------------------|-------------|
| **bitcoinjs-lib** | JS/TS | BTC, LTC | Yes |
| **ethers.js** | JS/TS | ETH, EVM chains | Yes |
| **@solana/web3.js** | JS/TS | Solana | Yes |
| **cardano-serialization-lib** | JS/TS/Rust | Cardano | Yes (WASM) |
| **coinstring** | JS | Multi-coin Base58Check | Yes |
| **wallet-address-validator** | JS | 100+ coins | Yes |

**Recommended: `wallet-address-validator`**

```javascript
const WAValidator = require('wallet-address-validator');

// Validate Bitcoin address
WAValidator.validate('1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2', 'BTC'); // true

// Validate Ethereum address
WAValidator.validate('0x742d35Cc6634C0532925a3b844Bc454e4438f44e', 'ETH'); // true

// Validate Litecoin address
WAValidator.validate('LQL9pVH1LsMfKwt82Y2wGhNGkrjF8vwUst', 'LTC'); // true
```

### 1.2 Blockchain Existence Verification APIs

These APIs check if an address has on-chain activity (transactions):

#### Free/Open APIs

| Service | Chains | Rate Limits | Auth Required |
|---------|--------|-------------|---------------|
| **Blockstream.info** | BTC | 10 req/sec | No |
| **Blockchain.com** | BTC, ETH | 10K/day | Optional |
| **Etherscan** | ETH, EVM | 5/sec (free) | Yes (free tier) |
| **Blockcypher** | BTC, LTC, DOGE, ETH | 200/hour (free) | Optional |
| **Mempool.space** | BTC | Generous | No |
| **Solscan** | SOL | Rate limited | No |

**Example: Check Bitcoin Address Activity**

```javascript
// Server-side (Node.js) - avoids CORS
async function checkBitcoinAddressActivity(address) {
  // Using Mempool.space (no auth, generous limits)
  const response = await fetch(
    `https://mempool.space/api/address/${address}`
  );
  
  if (!response.ok) {
    if (response.status === 400) {
      return { exists: false, error: 'Invalid address format' };
    }
    throw new Error(`API error: ${response.status}`);
  }
  
  const data = await response.json();
  
  return {
    exists: true,
    funded_txo_count: data.chain_stats.funded_txo_count,
    spent_txo_count: data.chain_stats.spent_txo_count,
    tx_count: data.chain_stats.tx_count,
    balance_sat: data.chain_stats.funded_txo_sum - data.chain_stats.spent_txo_sum
  };
}
```

**Example: Check Ethereum Address Activity**

```javascript
// Using Etherscan (requires free API key)
async function checkEthereumAddressActivity(address, apiKey) {
  const response = await fetch(
    `https://api.etherscan.io/api?module=account&action=txlist&address=${address}&startblock=0&endblock=99999999&page=1&offset=1&sort=asc&apikey=${apiKey}`
  );
  
  const data = await response.json();
  
  if (data.status === '1') {
    return { exists: true, hasTransactions: true };
  } else if (data.message === 'No transactions found') {
    return { exists: true, hasTransactions: false };
  } else {
    return { exists: false, error: data.message };
  }
}
```

### 1.3 Recommended Approach for Basset Hound

**Client-Side (Browser Extension):**
- Use `wallet-address-validator` for format/checksum validation
- Cache validation results locally
- No API calls needed for basic validation

**Server-Side (Thorough Verification):**
- Format validation first (fast, no API)
- Optional blockchain lookup via Blockcypher/Etherscan
- Rate limit API calls, cache results in Redis/memory

---

## 2. Email Verification

### 2.1 Email Format Validation (Regex)

```javascript
// RFC 5322 compliant (simplified for practical use)
const EMAIL_REGEX = /^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$/;

function isValidEmailFormat(email) {
  if (!email || email.length > 254) return false;
  return EMAIL_REGEX.test(email);
}

// More strict validation
function isValidEmailStrict(email) {
  if (!email) return false;
  
  const parts = email.split('@');
  if (parts.length !== 2) return false;
  
  const [local, domain] = parts;
  
  // Local part max 64 chars
  if (local.length > 64) return false;
  
  // Domain must have at least one dot
  if (!domain.includes('.')) return false;
  
  // TLD must be at least 2 chars
  const tld = domain.split('.').pop();
  if (tld.length < 2) return false;
  
  return EMAIL_REGEX.test(email);
}
```

### 2.2 MX Record Lookup

MX (Mail Exchange) records indicate if a domain can receive email.

**Server-Side Only (DNS lookups cannot be done client-side)**

```javascript
// Node.js
const dns = require('dns').promises;

async function checkMXRecords(domain) {
  try {
    const records = await dns.resolveMx(domain);
    
    if (records && records.length > 0) {
      // Sort by priority (lower is higher priority)
      records.sort((a, b) => a.priority - b.priority);
      
      return {
        hasMX: true,
        records: records.map(r => ({
          exchange: r.exchange,
          priority: r.priority
        }))
      };
    }
    
    return { hasMX: false, records: [] };
  } catch (error) {
    if (error.code === 'ENOTFOUND' || error.code === 'ENODATA') {
      return { hasMX: false, records: [], error: 'Domain not found' };
    }
    throw error;
  }
}

// Usage
const result = await checkMXRecords('gmail.com');
// { hasMX: true, records: [{ exchange: 'gmail-smtp-in.l.google.com', priority: 5 }, ...] }
```

**Python Alternative:**

```python
import dns.resolver

def check_mx_records(domain):
    try:
        records = dns.resolver.resolve(domain, 'MX')
        return {
            'has_mx': True,
            'records': [
                {'exchange': str(r.exchange), 'priority': r.preference}
                for r in sorted(records, key=lambda x: x.preference)
            ]
        }
    except dns.resolver.NXDOMAIN:
        return {'has_mx': False, 'error': 'Domain not found'}
    except dns.resolver.NoAnswer:
        return {'has_mx': False, 'error': 'No MX records'}
```

### 2.3 SMTP Verification (Without Sending Email)

SMTP verification checks if a mailbox exists by connecting to the mail server and initiating (but not completing) a delivery.

**IMPORTANT: Use with extreme caution - many servers rate limit or block this.**

```javascript
// Node.js - Using 'email-verify' package
const verifier = require('email-verify');

function verifyEmailSMTP(email) {
  return new Promise((resolve, reject) => {
    verifier.verify(email, {
      port: 25,
      sender: 'verify@yourdomain.com', // Use your actual domain
      timeout: 10000,
      fqdn: 'yourdomain.com'
    }, (err, info) => {
      if (err) {
        resolve({ valid: false, error: err.message });
      } else {
        resolve({
          valid: info.success,
          code: info.code,
          banner: info.banner
        });
      }
    });
  });
}
```

**Python Alternative:**

```python
import smtplib
import dns.resolver

def verify_email_smtp(email, sender='verify@example.com'):
    domain = email.split('@')[1]
    
    try:
        # Get MX records
        mx_records = dns.resolver.resolve(domain, 'MX')
        mx_host = str(sorted(mx_records, key=lambda x: x.preference)[0].exchange)
    except:
        return {'valid': False, 'error': 'No MX records'}
    
    try:
        # Connect to SMTP server
        server = smtplib.SMTP(timeout=10)
        server.connect(mx_host)
        server.helo('verify.example.com')
        server.mail(sender)
        code, message = server.rcpt(email)
        server.quit()
        
        # 250 = success, 550 = mailbox doesn't exist
        return {
            'valid': code == 250,
            'code': code,
            'message': message.decode()
        }
    except Exception as e:
        return {'valid': None, 'error': str(e)}
```

### 2.4 Email Verification Libraries and APIs

| Library/Service | Type | Features | Cost |
|-----------------|------|----------|------|
| **email-validator** (npm) | Client/Server | Format validation, disposable detection | Free |
| **email-verify** (npm) | Server | MX + SMTP verification | Free |
| **validator.js** | Client/Server | Format validation | Free |
| **Hunter.io** | API | Full verification, deliverability | Freemium |
| **ZeroBounce** | API | Full verification, abuse detection | Paid |
| **NeverBounce** | API | Real-time verification | Paid |
| **Mailgun** | API | Verification as part of email service | Paid |

**Recommended Free Approach:**

```javascript
const validator = require('validator');
const dns = require('dns').promises;

async function validateEmail(email) {
  const result = {
    email,
    formatValid: false,
    domainValid: false,
    mxExists: false,
    isDisposable: false,
    score: 0
  };
  
  // 1. Format validation
  result.formatValid = validator.isEmail(email);
  if (!result.formatValid) return result;
  result.score += 25;
  
  const domain = email.split('@')[1];
  
  // 2. Domain exists (A or AAAA record)
  try {
    await dns.resolve(domain);
    result.domainValid = true;
    result.score += 25;
  } catch {
    return result;
  }
  
  // 3. MX record check
  try {
    const mx = await dns.resolveMx(domain);
    result.mxExists = mx.length > 0;
    if (result.mxExists) result.score += 40;
  } catch {
    // Domain exists but no MX - might still work via A record
  }
  
  // 4. Disposable email detection (basic list)
  const disposableDomains = [
    'tempmail.com', 'guerrillamail.com', '10minutemail.com',
    'mailinator.com', 'throwaway.email', 'temp-mail.org'
  ];
  result.isDisposable = disposableDomains.some(d => domain.endsWith(d));
  if (!result.isDisposable) result.score += 10;
  
  return result;
}
```

### 2.5 Rate Limiting Considerations

- **MX Lookups**: Generally safe, 100+ per second typical
- **SMTP Verification**: Limit to 1-2 per second per target domain
- **API Services**: Follow their documented limits (typically 10-100/second on paid plans)

**Best Practice for OSINT:**
1. Cache MX records (TTL-based, usually 1 hour minimum)
2. Never send actual emails for verification
3. Accept that some addresses cannot be verified without delivery
4. Mark unverifiable as "unknown" not "invalid"

---

## 3. Phone Number Verification

### 3.1 libphonenumber and Alternatives

**Google's libphonenumber** is the gold standard for phone number parsing and validation.

| Library | Language | Size | Client-Side |
|---------|----------|------|-------------|
| **libphonenumber-js** | JS/TS | ~300KB | Yes (tree-shakeable) |
| **awesome-phonenumber** | JS/TS | ~300KB | Yes |
| **phonenumbers** | Python | ~1MB | N/A |
| **phone** (npm) | JS/TS | Small | Yes (basic) |

**Recommended: `libphonenumber-js`**

```javascript
import {
  parsePhoneNumber,
  isValidPhoneNumber,
  isPossiblePhoneNumber,
  getCountryCallingCode,
  getExampleNumber
} from 'libphonenumber-js';

// Parse a phone number
function validatePhoneNumber(input, defaultCountry = null) {
  try {
    // Try to parse
    const parsed = parsePhoneNumber(input, defaultCountry);
    
    return {
      valid: parsed.isValid(),
      possible: parsed.isPossible(),
      country: parsed.country,
      countryCallingCode: parsed.countryCallingCode,
      nationalNumber: parsed.nationalNumber,
      type: parsed.getType(), // MOBILE, FIXED_LINE, etc.
      formatted: {
        international: parsed.formatInternational(),
        national: parsed.formatNational(),
        e164: parsed.format('E.164'),
        rfc3966: parsed.format('RFC3966')
      }
    };
  } catch (error) {
    return {
      valid: false,
      possible: false,
      error: error.message
    };
  }
}

// Examples
validatePhoneNumber('+1 (555) 123-4567');
// { valid: false, possible: true, country: 'US', ... }
// (555 is not a valid US area code)

validatePhoneNumber('+1 (212) 555-1234');
// { valid: true, country: 'US', type: 'FIXED_LINE_OR_MOBILE', ... }

validatePhoneNumber('07911 123456', 'GB');
// { valid: true, country: 'GB', type: 'MOBILE', ... }
```

**Python Example:**

```python
import phonenumbers
from phonenumbers import carrier, geocoder, timezone

def validate_phone_number(input_str, default_region=None):
    try:
        parsed = phonenumbers.parse(input_str, default_region)
        
        return {
            'valid': phonenumbers.is_valid_number(parsed),
            'possible': phonenumbers.is_possible_number(parsed),
            'country_code': parsed.country_code,
            'national_number': parsed.national_number,
            'type': phonenumbers.number_type(parsed),
            'carrier': carrier.name_for_number(parsed, 'en'),
            'location': geocoder.description_for_number(parsed, 'en'),
            'timezones': timezone.time_zones_for_number(parsed),
            'formatted': {
                'international': phonenumbers.format_number(
                    parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL
                ),
                'national': phonenumbers.format_number(
                    parsed, phonenumbers.PhoneNumberFormat.NATIONAL
                ),
                'e164': phonenumbers.format_number(
                    parsed, phonenumbers.PhoneNumberFormat.E164
                )
            }
        }
    except phonenumbers.NumberParseException as e:
        return {'valid': False, 'error': str(e)}
```

### 3.2 Format Validation by Country

libphonenumber handles country-specific formats automatically. Key considerations:

| Country | Format Example | Length | Notes |
|---------|---------------|--------|-------|
| US/CA | +1 (212) 555-1234 | 10 digits | Area code required |
| UK | +44 7911 123456 | 10-11 digits | Mobile starts with 7 |
| Germany | +49 30 12345678 | 10-12 digits | Variable length |
| Japan | +81 3-1234-5678 | 10 digits | Area codes 1-5 digits |
| China | +86 138 1234 5678 | 11 digits | Mobile starts with 1 |
| India | +91 98765 43210 | 10 digits | Mobile starts with 6-9 |

### 3.3 Carrier Lookup APIs

| Service | Features | Free Tier | Notes |
|---------|----------|-----------|-------|
| **Twilio Lookup** | Carrier, type, caller ID | 100 free | Excellent accuracy |
| **NumVerify** | Carrier, type, location | 100/month | International |
| **Plivo** | Carrier, type | Pay per lookup | Good API |
| **Telnyx** | Carrier, CNAM | No free tier | US-focused |
| **Abstract API** | Carrier, type, format | 100/month | Simple API |

**Example: Twilio Lookup**

```javascript
// Server-side only (requires auth)
const twilio = require('twilio')(accountSid, authToken);

async function lookupCarrier(phoneNumber) {
  try {
    const lookup = await twilio.lookups.v2
      .phoneNumbers(phoneNumber)
      .fetch({ fields: 'line_type_intelligence' });
    
    return {
      valid: lookup.valid,
      callingCountryCode: lookup.callingCountryCode,
      countryCode: lookup.countryCode,
      nationalFormat: lookup.nationalFormat,
      lineType: lookup.lineTypeIntelligence?.type, // mobile, landline, voip
      carrier: lookup.lineTypeIntelligence?.carrier_name
    };
  } catch (error) {
    return { valid: false, error: error.message };
  }
}
```

### 3.4 Plausibility Checks

```javascript
function phoneNumberPlausibilityChecks(parsed) {
  const checks = {
    hasCountryCode: !!parsed.countryCallingCode,
    lengthValid: parsed.nationalNumber?.length >= 4,
    notAllSameDigit: !/^(\d)\1+$/.test(parsed.nationalNumber),
    notSequential: !isSequential(parsed.nationalNumber),
    typeKnown: parsed.type !== 'UNKNOWN'
  };
  
  const score = Object.values(checks).filter(Boolean).length;
  
  return {
    checks,
    score,
    maxScore: Object.keys(checks).length,
    plausible: score >= 4
  };
}

function isSequential(str) {
  const ascending = '0123456789';
  const descending = '9876543210';
  return ascending.includes(str) || descending.includes(str);
}
```

---

## 4. Domain/WHOIS Verification

### 4.1 WHOIS Lookup APIs and Libraries

| Service/Library | Type | Features | Cost |
|-----------------|------|----------|------|
| **whois** (npm) | Library | Basic WHOIS | Free |
| **whois-json** (npm) | Library | Parsed JSON output | Free |
| **python-whois** | Library | Good parsing | Free |
| **WhoisXML API** | API | Comprehensive, parsed | Freemium |
| **DomainTools** | API | Historical WHOIS | Paid |
| **RDAP** | Protocol | Standard, replacing WHOIS | Free |

**RDAP (Registration Data Access Protocol)** is the modern replacement for WHOIS with structured JSON responses.

```javascript
// RDAP lookup (no library needed)
async function rdapLookup(domain) {
  // IANA bootstrap to find correct RDAP server
  const bootstrapUrl = `https://rdap.org/domain/${domain}`;
  
  try {
    const response = await fetch(bootstrapUrl);
    if (!response.ok) {
      if (response.status === 404) {
        return { found: false, error: 'Domain not found' };
      }
      throw new Error(`RDAP error: ${response.status}`);
    }
    
    const data = await response.json();
    
    return {
      found: true,
      name: data.ldhName,
      status: data.status,
      registrar: data.entities?.find(e => 
        e.roles?.includes('registrar')
      )?.vcardArray?.[1]?.find(v => v[0] === 'fn')?.[3],
      nameservers: data.nameservers?.map(ns => ns.ldhName),
      created: data.events?.find(e => e.eventAction === 'registration')?.eventDate,
      expires: data.events?.find(e => e.eventAction === 'expiration')?.eventDate,
      updated: data.events?.find(e => e.eventAction === 'last changed')?.eventDate
    };
  } catch (error) {
    return { found: false, error: error.message };
  }
}
```

**Node.js WHOIS Library:**

```javascript
const whois = require('whois-json');

async function whoisLookup(domain) {
  try {
    const result = await whois(domain);
    
    return {
      found: true,
      domain: result.domainName,
      registrar: result.registrar,
      created: result.createdDate || result.creationDate,
      expires: result.expirationDate || result.registryExpiryDate,
      updated: result.updatedDate,
      nameservers: result.nameServer,
      status: result.domainStatus,
      dnssec: result.dnssec
    };
  } catch (error) {
    return { found: false, error: error.message };
  }
}
```

### 4.2 DNS Verification Methods

```javascript
const dns = require('dns').promises;

async function verifyDomain(domain) {
  const result = {
    domain,
    exists: false,
    hasA: false,
    hasAAAA: false,
    hasMX: false,
    hasNS: false,
    hasTXT: false,
    records: {}
  };
  
  // Check A records (IPv4)
  try {
    result.records.A = await dns.resolve4(domain);
    result.hasA = true;
    result.exists = true;
  } catch {}
  
  // Check AAAA records (IPv6)
  try {
    result.records.AAAA = await dns.resolve6(domain);
    result.hasAAAA = true;
    result.exists = true;
  } catch {}
  
  // Check MX records
  try {
    result.records.MX = await dns.resolveMx(domain);
    result.hasMX = true;
    result.exists = true;
  } catch {}
  
  // Check NS records
  try {
    result.records.NS = await dns.resolveNs(domain);
    result.hasNS = true;
    result.exists = true;
  } catch {}
  
  // Check TXT records (useful for SPF, DKIM, DMARC)
  try {
    result.records.TXT = await dns.resolveTxt(domain);
    result.hasTXT = true;
  } catch {}
  
  return result;
}
```

### 4.3 Domain Existence and Age Checks

```javascript
async function domainExistenceCheck(domain) {
  const result = {
    domain,
    exists: false,
    registerable: false,
    age: null,
    trustSignals: []
  };
  
  // 1. DNS check
  const dnsResult = await verifyDomain(domain);
  result.exists = dnsResult.exists;
  
  // 2. WHOIS/RDAP for age
  const whoisResult = await rdapLookup(domain);
  if (whoisResult.found) {
    result.exists = true;
    result.registerable = false;
    
    if (whoisResult.created) {
      const created = new Date(whoisResult.created);
      const ageMs = Date.now() - created.getTime();
      result.age = {
        days: Math.floor(ageMs / (1000 * 60 * 60 * 24)),
        created: whoisResult.created,
        expires: whoisResult.expires
      };
      
      // Trust signal: older domains more trustworthy
      if (result.age.days > 365) {
        result.trustSignals.push('Domain older than 1 year');
      }
      if (result.age.days > 1825) { // 5 years
        result.trustSignals.push('Domain older than 5 years');
      }
    }
    
    // Trust signal: has nameservers
    if (whoisResult.nameservers?.length > 0) {
      result.trustSignals.push('Has configured nameservers');
    }
  } else {
    result.registerable = true; // Domain might be available
  }
  
  // 3. Additional trust signals from DNS
  if (dnsResult.hasMX) {
    result.trustSignals.push('Has mail servers configured');
  }
  if (dnsResult.records.TXT?.some(t => t.join('').includes('v=spf'))) {
    result.trustSignals.push('Has SPF record');
  }
  
  return result;
}
```

---

## 5. Implementation Recommendations for Basset Hound

### 5.1 Client-Side (Browser Extension) Strategy

**What CAN be done client-side:**
- Regex format validation (all types)
- Cryptocurrency checksum validation
- Phone number parsing (libphonenumber-js)
- Email format validation

**What CANNOT be done client-side:**
- DNS/MX lookups (browser security)
- WHOIS/RDAP queries (CORS restrictions)
- SMTP verification (no raw socket access)
- Most blockchain API calls (CORS)

### 5.2 Recommended Architecture

```
Browser Extension                     Server (FastAPI)
      |                                     |
      v                                     v
[Format Validation]               [Deep Verification]
- Regex patterns                  - MX record lookup
- Checksum validation             - SMTP verification
- libphonenumber parsing          - WHOIS/RDAP lookup
- Local cache                     - Blockchain API calls
      |                           - Carrier lookup
      |                                     |
      +-----------> API Call --------------->
      <----------- Verification Result ------+
```

### 5.3 Suggested New Verification Service

```python
# api/services/verification_service.py (proposed)

from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, Dict, Any
import dns.resolver
import asyncio

class VerificationLevel(Enum):
    FORMAT_ONLY = "format"        # Regex/checksum only
    DNS_VERIFIED = "dns"          # MX/A record verified
    SMTP_VERIFIED = "smtp"        # SMTP check passed
    BLOCKCHAIN_VERIFIED = "chain" # On-chain activity found
    CARRIER_VERIFIED = "carrier"  # Carrier lookup successful

@dataclass
class VerificationResult:
    identifier: str
    identifier_type: str
    is_valid: bool
    verification_level: VerificationLevel
    confidence: float  # 0.0 to 1.0
    details: Dict[str, Any]
    errors: List[str]
    
class VerificationService:
    """
    Multi-level verification service for OSINT identifiers.
    """
    
    async def verify_email(
        self, 
        email: str, 
        level: VerificationLevel = VerificationLevel.DNS_VERIFIED
    ) -> VerificationResult:
        """Verify email with configurable depth."""
        # Implementation here
        pass
    
    async def verify_phone(
        self,
        phone: str,
        country_hint: Optional[str] = None,
        level: VerificationLevel = VerificationLevel.FORMAT_ONLY
    ) -> VerificationResult:
        """Verify phone number with optional carrier lookup."""
        pass
    
    async def verify_crypto(
        self,
        address: str,
        level: VerificationLevel = VerificationLevel.FORMAT_ONLY
    ) -> VerificationResult:
        """Verify crypto address with optional blockchain check."""
        pass
    
    async def verify_domain(
        self,
        domain: str,
        level: VerificationLevel = VerificationLevel.DNS_VERIFIED
    ) -> VerificationResult:
        """Verify domain existence and configuration."""
        pass
```

### 5.4 Recommended Dependencies

**JavaScript/TypeScript (Browser Extension):**
```json
{
  "dependencies": {
    "libphonenumber-js": "^1.10.0",
    "wallet-address-validator": "^0.2.4",
    "validator": "^13.9.0"
  }
}
```

**Python (Server-Side):**
```
phonenumbers>=8.13.0
dnspython>=2.4.0
whois>=0.9.0
aiohttp>=3.8.0  # For async API calls
```

---

## 6. Summary Table

| Data Type | Client-Side Validation | Server-Side Verification | Recommended Library |
|-----------|----------------------|-------------------------|---------------------|
| **Crypto Address** | Checksum validation | Blockchain API lookup | `wallet-address-validator` |
| **Email** | Format regex | MX + optional SMTP | `validator` + `dns.resolve` |
| **Phone** | libphonenumber parsing | Carrier lookup API | `libphonenumber-js` |
| **Domain** | Format check | DNS + WHOIS/RDAP | `dns` + `rdap.org` |

---

## Files Referenced

The existing Basset Hound codebase already has strong foundations for this work:

- `/home/devel/basset-hound/api/utils/crypto_detector.py` - Crypto address detection (20+ coins)
- `/home/devel/basset-hound/api/services/normalizer.py` - Data normalization service (v1)
- `/home/devel/basset-hound/api/services/normalizer_v2.py` - Conservative normalization with ambiguity detection
- `/home/devel/basset-hound/docs/findings/04-CRYPTO-DETECTION.md` - Crypto detection documentation

The verification methods documented here would complement the existing normalization and detection capabilities, adding a layer of external verification for higher confidence in OSINT data quality.
</output>
Excellent! Now I have comprehensive results from all agents. Let me update the todos and then proceed to document findings and update roadmaps.
Update Todos

Explore and review basset-hound repository

Explore and review autofill-extension repository

Explore and review basset-hound-browser repository

Research data verification APIs and methods

Document research findings in each repository's docs folder

Update ROADMAP.md for basset-hound

Update ROADMAP.md for autofill-extension

Update ROADMAP.md for basset-hound-browser

Create integration architecture document
Now let me check if the other repositories actually exist in the filesystem before creating documentation.
Bash Check which repositories exist
IN
ls -la /home/devel/ | grep -E "autofill|basset"

OUT
drwxr-xr-x 12 devel devel  4096 Jan  4 19:21 autofill-extension
drwxr-xr-x 10 devel devel  4096 Jan  4 19:20 basset-hound
drwxr-xr-x 40 devel devel  4096 Jan  4 19:21 basset-hound-browser
All three repositories exist. Let me explore the other two repositories now since my agents had trouble finding them.
Bash List autofill-extension contents
IN
ls -la /home/devel/autofill-extension/

OUT
total 716
drwxr-xr-x 12 devel devel   4096 Jan  4 19:21 .
drwxr-x--- 23 devel devel   4096 Jan  4 19:39 ..
drwxr-xr-x  8 devel devel   4096 Jan  4 19:21 .git
-rw-r--r--  1 devel devel    353 Jan  4 19:21 .gitignore
-rw-r--r--  1 devel devel  10351 Jan  4 19:21 DEVTOOLS-GUIDE.md
-rw-r--r--  1 devel devel   9831 Jan  4 19:21 DEVTOOLS-INSTALLATION.md
-rw-r--r--  1 devel devel   5175 Jan  4 19:21 DEVTOOLS-QUICKSTART.md
-rw-r--r--  1 devel devel  16911 Jan  4 19:21 DEVTOOLS-SUMMARY.txt
-rw-r--r--  1 devel devel  12075 Jan  4 19:21 SESSION_COMPLETE_DEC29.md
-rw-r--r--  1 devel devel 243933 Jan  4 19:21 background.js
-rw-r--r--  1 devel devel 247786 Jan  4 19:21 content.js
drwxr-xr-x  2 devel devel   4096 Jan  4 19:21 data
-rw-r--r--  1 devel devel  22800 Jan  4 19:21 devtools-panel.css
-rw-r--r--  1 devel devel  18251 Jan  4 19:21 devtools-panel.html
-rw-r--r--  1 devel devel  29810 Jan  4 19:21 devtools-panel.js
-rw-r--r--  1 devel devel    173 Jan  4 19:21 devtools.html
-rw-r--r--  1 devel devel   1822 Jan  4 19:21 devtools.js
drwxr-xr-x  3 devel devel   4096 Jan  4 19:21 docs
drwxr-xr-x  2 devel devel   4096 Jan  4 19:21 examples
drwxr-xr-x  2 devel devel   4096 Jan  4 19:21 icons
-rw-r--r--  1 devel devel   1964 Jan  4 19:21 manifest.json
drwxr-xr-x  2 devel devel   4096 Jan  4 19:21 mcp-server
-rw-r--r--  1 devel devel   2470 Jan  4 19:21 package.json
-rw-r--r--  1 devel devel   7349 Jan  4 19:21 popup.html
-rw-r--r--  1 devel devel  11898 Jan  4 19:21 popup.js
drwxr-xr-x  2 devel devel   4096 Jan  4 19:21 server
drwxr-xr-x  8 devel devel   4096 Jan  4 19:21 tests
-rw-r--r--  1 devel devel   3540 Jan  4 19:21 todo.md
drwxr-xr-x  2 devel devel   4096 Jan  4 19:21 tools
drwxr-xr-x  7 devel devel   4096 Jan  4 19:21 utils
Bash List basset-hound-browser contents
IN
ls -la /home/devel/basset-hound-browser/

OUT
total 368
drwxr-xr-x 40 devel devel  4096 Jan  4 19:21 .
drwxr-x--- 23 devel devel  4096 Jan  4 19:39 ..
-rw-r--r--  1 devel devel   811 Jan  4 19:21 .dockerignore
drwxr-xr-x  8 devel devel  4096 Jan  4 19:21 .git
-rw-r--r--  1 devel devel   612 Jan  4 19:21 .gitignore
-rw-r--r--  1 devel devel  2755 Jan  4 19:21 Dockerfile
-rw-r--r--  1 devel devel 32223 Jan  4 19:21 README.md
drwxr-xr-x  2 devel devel  4096 Jan  4 19:21 assets
drwxr-xr-x  2 devel devel  4096 Jan  4 19:21 automation
drwxr-xr-x  2 devel devel  4096 Jan  4 19:21 blocking
drwxr-xr-x  5 devel devel  4096 Jan  4 19:21 clients
drwxr-xr-x  2 devel devel  4096 Jan  4 19:21 config
-rw-r--r--  1 devel devel 13987 Jan  4 19:21 config.example.yaml
drwxr-xr-x  2 devel devel  4096 Jan  4 19:21 cookies
drwxr-xr-x  2 devel devel  4096 Jan  4 19:21 devtools
-rw-r--r--  1 devel devel  1661 Jan  4 19:21 docker-compose.yml
drwxr-xr-x  9 devel devel  4096 Jan  4 19:21 docs
drwxr-xr-x  2 devel devel  4096 Jan  4 19:21 downloads
drwxr-xr-x  2 devel devel  4096 Jan  4 19:21 evasion
drwxr-xr-x  2 devel devel  4096 Jan  4 19:21 extraction
drwxr-xr-x  2 devel devel  4096 Jan  4 19:21 geolocation
drwxr-xr-x  2 devel devel  4096 Jan  4 19:21 headers
drwxr-xr-x  2 devel devel  4096 Jan  4 19:21 headless
drwxr-xr-x  2 devel devel  4096 Jan  4 19:21 history
drwxr-xr-x  2 devel devel  4096 Jan  4 19:21 input
drwxr-xr-x  2 devel devel  4096 Jan  4 19:21 inspector
drwxr-xr-x  2 devel devel  4096 Jan  4 19:21 logging
-rw-r--r--  1 devel devel 88486 Jan  4 19:21 main.js
drwxr-xr-x  2 devel devel  4096 Jan  4 19:21 network
drwxr-xr-x  2 devel devel  4096 Jan  4 19:21 network-analysis
-rw-r--r--  1 devel devel  7724 Jan  4 19:21 package.json
drwxr-xr-x  3 devel devel  4096 Jan  4 19:21 plugins
-rw-r--r--  1 devel devel 42253 Jan  4 19:21 preload.js
drwxr-xr-x  2 devel devel  4096 Jan  4 19:21 profiles
drwxr-xr-x  2 devel devel  4096 Jan  4 19:21 proxy
drwxr-xr-x  2 devel devel  4096 Jan  4 19:21 recording
drwxr-xr-x  2 devel devel  4096 Jan  4 19:21 recordings
drwxr-xr-x  2 devel devel  4096 Jan  4 19:21 renderer
drwxr-xr-x  2 devel devel  4096 Jan  4 19:21 screenshots
drwxr-xr-x  3 devel devel  4096 Jan  4 19:21 scripts
drwxr-xr-x  2 devel devel  4096 Jan  4 19:21 sessions
drwxr-xr-x  2 devel devel  4096 Jan  4 19:21 storage
drwxr-xr-x  2 devel devel  4096 Jan  4 19:21 tabs
drwxr-xr-x  2 devel devel  4096 Jan  4 19:21 technology
drwxr-xr-x  9 devel devel  4096 Jan  4 19:21 tests
-rw-r--r--  1 devel devel  4057 Jan  4 19:21 todo.md
drwxr-xr-x  2 devel devel  4096 Jan  4 19:21 updater
drwxr-xr-x  2 devel devel  4096 Jan  4 19:21 utils
drwxr-xr-x  3 devel devel  4096 Jan  4 19:21 websocket
drwxr-xr-x  2 devel devel  4096 Jan  4 19:21 windows
All three repositories exist and are substantial. Let me now read their existing roadmaps and docs to understand their current state.
Globpattern: "**/*ROADMAP*"
Found 1 file
Globpattern: "**/*ROADMAP*"
Found 1 file
Bash Check autofill docs folder
IN
ls -la /home/devel/autofill-extension/docs/

OUT
total 412
drwxr-xr-x  3 devel devel  4096 Jan  4 19:21 .
drwxr-xr-x 12 devel devel  4096 Jan  4 19:21 ..
-rw-r--r--  1 devel devel 15591 Jan  4 19:21 API.md
-rw-r--r--  1 devel devel 15001 Jan  4 19:21 API_REFERENCE.md
-rw-r--r--  1 devel devel 14070 Jan  4 19:21 ARCHITECTURE.md
-rw-r--r--  1 devel devel 17276 Jan  4 19:21 CHROME-EXTENSION-DEBUGGING.md
-rw-r--r--  1 devel devel 28242 Jan  4 19:21 CONTENT_EXTRACTION_GUIDE.md
-rw-r--r--  1 devel devel 11828 Jan  4 19:21 DEVELOPMENT.md
-rw-r--r--  1 devel devel  9914 Jan  4 19:21 DEVELOPMENT_WORKFLOW.md
-rw-r--r--  1 devel devel 15906 Jan  4 19:21 EXAMPLES.md
-rw-r--r--  1 devel devel 10196 Jan  4 19:21 FEATURE_SUMMARY.md
-rw-r--r--  1 devel devel 13121 Jan  4 19:21 FORM_AUTOMATION_API.md
-rw-r--r--  1 devel devel 14138 Jan  4 19:21 GETTING_STARTED.md
-rw-r--r--  1 devel devel 17821 Jan  4 19:21 INDEX.md
-rw-r--r--  1 devel devel  2846 Jan  4 19:21 INTEGRATION.md
-rw-r--r--  1 devel devel 17047 Jan  4 19:21 NETWORK-MONITORING.md
-rw-r--r--  1 devel devel 15903 Jan  4 19:21 NETWORK_EXPORT_GUIDE.md
-rw-r--r--  1 devel devel  4337 Jan  4 19:21 QUICK_REFERENCE.md
-rw-r--r--  1 devel devel 15257 Jan  4 19:21 README.md
-rw-r--r--  1 devel devel  5749 Jan  4 19:21 README_DOCS.md
-rw-r--r--  1 devel devel 34538 Jan  4 19:21 ROADMAP.md
-rw-r--r--  1 devel devel  2081 Jan  4 19:21 RSYNC.md
-rw-r--r--  1 devel devel 23320 Jan  4 19:21 TESTING.md
-rw-r--r--  1 devel devel 23103 Jan  4 19:21 automated-testing.md
-rw-r--r--  1 devel devel 20551 Jan  4 19:21 chrome-extension-cross-communication.md
-rw-r--r--  1 devel devel    71 Jan  4 19:21 connections.md
drwxr-xr-x  2 devel devel  4096 Jan  4 19:21 findings
-rwxr-xr-x  1 devel devel  1578 Jan  4 19:21 quick-test.sh
-rwxr-xr-x  1 devel devel  5080 Jan  4 19:21 setup-testing.sh
Bash Check browser docs folder
IN
ls -la /home/devel/basset-hound-browser/docs/

OUT
total 128
drwxr-xr-x  9 devel devel  4096 Jan  4 19:21 .
drwxr-xr-x 40 devel devel  4096 Jan  4 19:21 ..
-rw-r--r--  1 devel devel 17635 Jan  4 19:21 DEVELOPMENT-STATUS.md
-rw-r--r--  1 devel devel  7138 Jan  4 19:21 README.md
-rw-r--r--  1 devel devel 43748 Jan  4 19:21 ROADMAP.md
-rw-r--r--  1 devel devel 10033 Jan  4 19:21 SSL-CERTIFICATES.md
-rw-r--r--  1 devel devel  5960 Jan  4 19:21 SYSTEM-TOR-INSTALLATION.md
drwxr-xr-x  2 devel devel  4096 Jan  4 19:21 api
drwxr-xr-x  2 devel devel  4096 Jan  4 19:21 core
drwxr-xr-x  2 devel devel  4096 Jan  4 19:21 deployment
drwxr-xr-x  2 devel devel  4096 Jan  4 19:21 features
drwxr-xr-x  2 devel devel  4096 Jan  4 19:21 findings
drwxr-xr-x  2 devel devel  4096 Jan  4 19:21 integration
drwxr-xr-x  2 devel devel  4096 Jan  4 19:21 testing
All three repositories have ROADMAP.md files and docs/findings folders. Let me read their current roadmaps and key files to understand the current state better.
Read ROADMAP.md
Read ROADMAP.md
Read todo.md
Read todo.md
Now I have a comprehensive understanding of all three repositories. Let me also read the basset-hound ROADMAP.md to get the full picture.
Read ROADMAP.md
Now I have a comprehensive understanding of all three repositories. Let me create the findings documents and update the roadmaps. I'll start by creating the research findings for each repository.
Update Todos

Explore and review basset-hound repository

Explore and review autofill-extension repository

Explore and review basset-hound-browser repository

Research data verification APIs and methods

Document research findings in each repository's docs folder

Update ROADMAP.md for basset-hound

Update ROADMAP.md for autofill-extension

Update ROADMAP.md for basset-hound-browser

Create integration architecture document
Let me create the research findings documents for each repository and then update the roadmaps. I'll create comprehensive documentation that captures your ideas and how they integrate.
Write INTEGRATION-RESEARCH-2026-01-04.md
371 lines
# Integration Research Findings - Basset Hound

**Date:** January 4, 2026
**Purpose:** Document integration strategies for the Basset Hound ecosystem

---

## Overview

This document outlines research findings for integrating three independent OSINT projects:
1. **basset-hound** - Entity relationship engine (graph database backend)
2. **autofill-extension** - Chrome browser automation extension
3. **basset-hound-browser** - Electron-based automation browser

---

## Integration Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                        OSINT INVESTIGATION ECOSYSTEM                         │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌─────────────────────┐     ┌─────────────────────┐                       │
│   │  autofill-extension │     │ basset-hound-browser│                       │
│   │    (Chrome MV3)     │     │     (Electron)       │                       │
│   │                     │     │                      │                       │
│   │  - Data field       │     │  - Automated browsing│                       │
│   │    detection        │     │  - Bot evasion       │                       │
│   │  - Ingest button    │     │  - Screenshots       │                       │
│   │  - Screenshots      │     │  - Tor integration   │                       │
│   │  - Element selection│     │  - Session recording │                       │
│   └──────────┬──────────┘     └───────────┬─────────┘                       │
│              │                             │                                 │
│              │      WebSocket/API          │                                 │
│              │                             │                                 │
│              └──────────────┬──────────────┘                                 │
│                             │                                                │
│                             ▼                                                │
│              ┌─────────────────────────────┐                                │
│              │       basset-hound          │                                │
│              │    (Entity Relationship     │                                │
│              │         Engine)             │                                │
│              │                             │                                │
│              │  - Store orphan data        │                                │
│              │  - Track data provenance    │                                │
│              │  - Verify identifiers       │                                │
│              │  - Auto-link entities       │                                │
│              │  - Graph analysis           │                                │
│              └─────────────────────────────┘                                │
│                             │                                                │
│                             │ MCP/API                                        │
│                             ▼                                                │
│              ┌─────────────────────────────┐                                │
│              │       OSINT Agent           │                                │
│              │   (palletAI or LLM-based)   │                                │
│              │                             │                                │
│              │  - Automated investigations │                                │
│              │  - Pattern discovery        │                                │
│              │  - Report generation        │                                │
│              └─────────────────────────────┘                                │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Key Integration Requirements from User

### 1. Data Provenance Tracking

**Requirement:** Track where data comes from - human operator entry OR website (URL + date)

**Implementation in basset-hound:**
- Already supports `source` metadata on orphan data
- Enhance to include structured provenance:

```python
# Proposed DataProvenance model
class DataProvenance(BaseModel):
    source_type: Literal["human_entry", "website", "api", "import"]
    source_url: Optional[str] = None
    source_date: datetime
    captured_by: Literal["autofill-extension", "basset-hound-browser", "api", "manual"]
    confidence: float = 1.0  # How confident are we in this data
    verification_status: Literal["unverified", "format_valid", "verified", "failed"]
```

**Files to modify:**
- `/api/models/orphan.py` - Add provenance fields
- `/api/services/orphan_service.py` - Track provenance on create
- `/api/routers/orphan.py` - Accept provenance in API

### 2. Data Verification Service

**Requirement:** Verify plausibility of crypto addresses, emails, phones, domains

**Research Findings:**

#### Cryptocurrency Address Validation
- **Client-side:** Use `wallet-address-validator` (supports 100+ coins)
- **Server-side:** Use blockchain APIs (Blockstream, Etherscan, Mempool.space)
- **Current state:** basset-hound has `crypto_detector.py` with 30+ coin detection
- **Enhancement needed:** Add existence verification via blockchain APIs

```python
# Proposed VerificationService
class VerificationService:
    async def verify_crypto(self, address: str) -> VerificationResult:
        """Verify crypto address format AND check blockchain existence."""
        pass

    async def verify_email(self, email: str) -> VerificationResult:
        """Validate format, check MX records, optionally SMTP verify."""
        pass

    async def verify_phone(self, phone: str) -> VerificationResult:
        """Parse with libphonenumber, validate format by country."""
        pass

    async def verify_domain(self, domain: str) -> VerificationResult:
        """Check DNS records, WHOIS/RDAP lookup."""
        pass
```

#### Email Verification
- **Format validation:** RFC 5322 regex
- **MX record lookup:** `dns.resolver` in Python
- **SMTP verification:** Available but rate-limited
- **Libraries:** `email-validator`, `dnspython`

#### Phone Verification
- **Primary library:** `phonenumbers` (Python port of Google's libphonenumber)
- **Features:** Format validation, country detection, carrier lookup
- **Plausibility checks:** Not all same digit, not sequential

#### Domain/WHOIS Verification
- **RDAP (modern):** `rdap.org` - structured JSON responses
- **WHOIS (legacy):** `python-whois` library
- **DNS checks:** A, AAAA, MX, NS, TXT records

### 3. Autofill Extension Ingestion

**Requirement:**
- Auto-detect data fields on web pages
- "Ingest" button to send data to basset-hound
- Capture full URL and date
- Allow manual element selection and screenshot

**Current state in autofill-extension:**
- Already has data normalization (`utils/data-pipeline/normalizer.js`)
- Already has basset-hound sync (`utils/data-pipeline/basset-hound-sync.js`)
- Has entity manager (`utils/data-pipeline/entity-manager.js`)
- Has screenshot capabilities

**Enhancement needed:**
- Add data provenance capture (URL, timestamp)
- Add verification before ingest
- Integrate with basset-hound verification API

### 4. basset-hound-browser Integration

**Requirement:**
- OSINT agent uses basset-hound-browser for automated investigations
- Results stored in basset-hound

**Current state:**
- basset-hound-browser has WebSocket API (port 8765)
- Has technology detection, content extraction, network analysis
- Has Python/Node.js client libraries

**Integration pattern:**
```python
# OSINT Agent workflow
async def investigate(target: str):
    # 1. Use basset-hound-browser for automated browsing
    browser = BassetHoundBrowser()
    await browser.navigate(target)
    page_state = await browser.get_page_state()

    # 2. Extract identifiers
    emails = extract_emails(page_state)
    phones = extract_phones(page_state)

    # 3. Store in basset-hound as orphan data
    for email in emails:
        basset.create_orphan(
            identifier_type="EMAIL",
            value=email,
            provenance={
                "source_type": "website",
                "source_url": target,
                "source_date": datetime.now(),
                "captured_by": "basset-hound-browser"
            }
        )
```

---

## Data Verification Implementation Plan

### Phase 1: Format Validation (Client-side compatible)

```python
# api/services/verification/format_validators.py

def validate_email_format(email: str) -> bool:
    """RFC 5322 compliant email validation."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_phone_format(phone: str, country_hint: str = None) -> dict:
    """Parse and validate phone number format."""
    import phonenumbers
    try:
        parsed = phonenumbers.parse(phone, country_hint)
        return {
            "valid": phonenumbers.is_valid_number(parsed),
            "possible": phonenumbers.is_possible_number(parsed),
            "country": phonenumbers.region_code_for_number(parsed),
            "formatted": phonenumbers.format_number(
                parsed, phonenumbers.PhoneNumberFormat.E164
            )
        }
    except:
        return {"valid": False}

def validate_crypto_format(address: str) -> dict:
    """Checksum validation for crypto addresses."""
    # Use existing crypto_detector.py
    from api.utils.crypto_detector import detect_cryptocurrency
    return detect_cryptocurrency(address)
```

### Phase 2: DNS/Network Verification (Server-side)

```python
# api/services/verification/network_validators.py

import dns.resolver

async def verify_email_domain(email: str) -> dict:
    """Check if email domain has MX records."""
    domain = email.split('@')[1]
    try:
        mx_records = dns.resolver.resolve(domain, 'MX')
        return {
            "has_mx": True,
            "mx_count": len(mx_records),
            "primary_mx": str(sorted(mx_records, key=lambda x: x.preference)[0].exchange)
        }
    except:
        return {"has_mx": False}

async def verify_domain_exists(domain: str) -> dict:
    """Check if domain has DNS records."""
    result = {"exists": False, "has_a": False, "has_mx": False}
    try:
        dns.resolver.resolve(domain, 'A')
        result["exists"] = True
        result["has_a"] = True
    except:
        pass
    try:
        dns.resolver.resolve(domain, 'MX')
        result["has_mx"] = True
    except:
        pass
    return result
```

### Phase 3: Blockchain/External API Verification

```python
# api/services/verification/blockchain_validators.py

import httpx

async def verify_bitcoin_address(address: str) -> dict:
    """Check if Bitcoin address has blockchain activity."""
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                f"https://mempool.space/api/address/{address}",
                timeout=10.0
            )
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "exists": True,
                    "tx_count": data["chain_stats"]["tx_count"],
                    "balance_sat": data["chain_stats"]["funded_txo_sum"] -
                                   data["chain_stats"]["spent_txo_sum"]
                }
        except:
            pass
    return {"exists": False}
```

---

## API Endpoint Design

### New Verification Endpoints

```
POST /api/v1/verify/email
POST /api/v1/verify/phone
POST /api/v1/verify/crypto
POST /api/v1/verify/domain
POST /api/v1/verify/batch   # Multiple items at once
```

### Enhanced Orphan Endpoints

```
POST /api/v1/projects/{project}/orphans
  - Now accepts `provenance` object
  - Auto-verifies on creation (optional)
  - Blocks ingestion if verification fails (configurable)
```

---

## Dependencies to Add

**Python (basset-hound):**
```
phonenumbers>=8.13.0       # Phone number parsing
dnspython>=2.4.0           # DNS lookups
httpx>=0.27.0              # Async HTTP for blockchain APIs
python-whois>=0.9.0        # WHOIS lookups (optional)
```

**JavaScript (autofill-extension):**
```json
{
  "libphonenumber-js": "^1.10.0",
  "wallet-address-validator": "^0.2.4",
  "validator": "^13.9.0"
}
```

---

## Security Considerations

1. **Rate Limiting:** External API calls should be rate-limited
2. **Caching:** Cache verification results to avoid repeated lookups
3. **Privacy:** SMTP verification may reveal investigation intent
4. **WHOIS Privacy:** Many domains have privacy protection
5. **Blockchain APIs:** Use multiple providers for redundancy

---

## Recommended Implementation Order

1. **Add DataProvenance model to basset-hound** (Quick win)
2. **Add format validators** (No external dependencies)
3. **Add MX/DNS verification** (Reliable, server-side)
4. **Add blockchain verification** (External APIs, rate-limited)
5. **Update autofill-extension to send provenance** (Integration)
6. **OSINT agent integration** (Uses all above)

---

## Next Steps

See updated ROADMAP.md for implementation phases.
Write INTEGRATION-RESEARCH-2026-01-04.md
497 lines
# Integration Research Findings - Autofill Extension

**Date:** January 4, 2026
**Purpose:** Document integration strategies and enhancement requirements

---

## Overview

This document outlines research findings for enhancing the autofill-extension to integrate with the Basset Hound ecosystem for OSINT investigations.

---

## Current State Analysis

### Existing Capabilities (v2.15.0)

The autofill-extension is already a feature-rich browser automation tool with:

| Category | Features |
|----------|----------|
| **Data Pipeline** | Normalization, entity management, deduplication |
| **basset-hound Sync** | Entity sync with offline queue, conflict resolution |
| **Content Extraction** | Tables, links, images, structured data |
| **Form Automation** | Field detection, human-like typing, CAPTCHA detection |
| **OSINT Handlers** | HIBP, Shodan, Wayback, WHOIS, Hunter, Social Media |
| **MCP Server** | 76+ browser automation tools for AI agents |
| **DevTools Panel** | 6-tab professional UI |

### Key Files for Integration

```
utils/data-pipeline/
├── normalizer.js           # Data normalization (dates, names, addresses, phones, emails)
├── entity-manager.js       # Entity creation, relationships, export
├── basset-hound-sync.js    # Backend sync with offline queue
└── (new) provenance.js     # Data provenance tracking (TO BE CREATED)

utils/osint-handlers/
├── haveibeenpwned.js       # Email/password breach check
├── shodan.js               # IP/device search
├── wayback.js              # Historical snapshots
├── whois.js                # Domain/IP registration
├── hunter.js               # Email finder
├── social-media.js         # Profile lookup
└── (new) verifier.js       # Data verification (TO BE CREATED)
```

---

## Enhancement Requirements

### 1. Data Field Auto-Detection for Ingestion

**Current:** Form field detection exists for form filling
**Needed:** Detect data fields for OSINT ingestion

```javascript
// utils/data-pipeline/field-detector.js (TO BE CREATED)

const OSINT_PATTERNS = {
  email: /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g,
  phone: /(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}/g,
  crypto_btc: /\b(bc1|[13])[a-zA-HJ-NP-Z0-9]{25,39}\b/g,
  crypto_eth: /\b0x[a-fA-F0-9]{40}\b/g,
  ip_v4: /\b(?:\d{1,3}\.){3}\d{1,3}\b/g,
  domain: /(?:https?:\/\/)?(?:www\.)?([a-zA-Z0-9-]+\.[a-zA-Z]{2,})/g,
  username: /@[a-zA-Z0-9_]{3,30}/g,
  ssn: /\b\d{3}-\d{2}-\d{4}\b/g,
  cc_masked: /\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b/g
};

class OSINTFieldDetector {
  detectAll(text) {
    const findings = [];
    for (const [type, pattern] of Object.entries(OSINT_PATTERNS)) {
      const matches = text.matchAll(pattern);
      for (const match of matches) {
        findings.push({
          type,
          value: match[0],
          position: match.index,
          context: text.slice(Math.max(0, match.index - 50), match.index + match[0].length + 50)
        });
      }
    }
    return findings;
  }

  highlightOnPage() {
    // Highlight detected fields with visual indicators
  }
}
```

### 2. "Ingest" Button Functionality

**Implementation:**

```javascript
// content.js additions

function createIngestButton(detectedData) {
  const button = document.createElement('button');
  button.id = 'basset-ingest-btn';
  button.innerHTML = `
    <img src="${chrome.runtime.getURL('icons/basset-16.png')}" />
    Ingest (${detectedData.length} items)
  `;
  button.onclick = () => showIngestPanel(detectedData);
  document.body.appendChild(button);
}

function showIngestPanel(detectedData) {
  // Modal showing detected data
  // Checkboxes to select what to ingest
  // Verification status for each item
  // "Ingest Selected" button
}

async function ingestSelectedData(selectedItems) {
  const provenance = {
    source_type: 'website',
    source_url: window.location.href,
    source_date: new Date().toISOString(),
    captured_by: 'autofill-extension'
  };

  for (const item of selectedItems) {
    // Verify first
    const verification = await verifyData(item.type, item.value);

    if (!verification.plausible && !item.forceIngest) {
      item.status = 'blocked';
      continue;
    }

    // Send to basset-hound
    await bassetHoundSync.createOrphan({
      identifier_type: mapToIdentifierType(item.type),
      identifier_value: item.value,
      metadata: {
        context: item.context,
        verification: verification
      },
      provenance
    });

    item.status = 'ingested';
  }
}
```

### 3. Data Verification Before Ingestion

**Client-side verification (in extension):**

```javascript
// utils/data-pipeline/verifier.js (TO BE CREATED)

import validator from 'validator';
import { parsePhoneNumber, isValidPhoneNumber } from 'libphonenumber-js';
import WAValidator from 'wallet-address-validator';

class DataVerifier {
  async verifyEmail(email) {
    return {
      plausible: validator.isEmail(email),
      format_valid: true,
      disposable: this.isDisposableEmail(email),
      // Note: MX check requires server-side
      needs_server_verification: true
    };
  }

  async verifyPhone(phone, countryHint = null) {
    try {
      const parsed = parsePhoneNumber(phone, countryHint);
      return {
        plausible: parsed.isPossible(),
        valid: parsed.isValid(),
        country: parsed.country,
        type: parsed.getType(),
        formatted: parsed.format('E.164')
      };
    } catch {
      return { plausible: false, valid: false };
    }
  }

  async verifyCrypto(address) {
    // Try multiple coin types
    const coins = ['BTC', 'ETH', 'LTC', 'XRP', 'DOGE'];
    for (const coin of coins) {
      if (WAValidator.validate(address, coin)) {
        return {
          plausible: true,
          coin,
          checksum_valid: true,
          // Note: Blockchain existence check requires server-side
          needs_server_verification: true
        };
      }
    }
    return { plausible: false };
  }

  isDisposableEmail(email) {
    const disposableDomains = [
      'tempmail.com', 'guerrillamail.com', '10minutemail.com',
      'mailinator.com', 'throwaway.email', 'temp-mail.org'
      // ... extend with full list
    ];
    const domain = email.split('@')[1]?.toLowerCase();
    return disposableDomains.some(d => domain?.endsWith(d));
  }
}
```

### 4. Manual Element Selection and Screenshot

**Element picker mode:**

```javascript
// content.js additions

class ElementPicker {
  constructor() {
    this.active = false;
    this.selectedElements = [];
  }

  enable() {
    this.active = true;
    document.body.style.cursor = 'crosshair';

    document.addEventListener('mouseover', this.highlightElement);
    document.addEventListener('click', this.selectElement);
    document.addEventListener('keydown', this.handleKeydown);
  }

  highlightElement = (e) => {
    if (!this.active) return;
    // Add highlight overlay
    const overlay = document.getElementById('basset-picker-overlay') ||
                    this.createOverlay();
    const rect = e.target.getBoundingClientRect();
    overlay.style.cssText = `
      position: fixed;
      top: ${rect.top}px;
      left: ${rect.left}px;
      width: ${rect.width}px;
      height: ${rect.height}px;
      background: rgba(0, 123, 255, 0.3);
      border: 2px solid #007bff;
      pointer-events: none;
      z-index: 999999;
    `;
  }

  selectElement = (e) => {
    if (!this.active) return;
    e.preventDefault();

    const element = e.target;
    this.selectedElements.push({
      tag: element.tagName,
      text: element.innerText,
      html: element.innerHTML,
      selector: this.generateSelector(element),
      rect: element.getBoundingClientRect()
    });

    // Visual feedback
    element.style.outline = '3px solid #28a745';
  }

  async captureScreenshot() {
    // Use chrome.tabs.captureVisibleTab
    return new Promise((resolve) => {
      chrome.runtime.sendMessage(
        { type: 'capture_screenshot' },
        (response) => resolve(response.dataUrl)
      );
    });
  }

  generateSelector(element) {
    // Generate unique CSS selector
    if (element.id) return `#${element.id}`;
    // ... fallback to path-based selector
  }
}
```

### 5. URL and Date Capture

**Automatic provenance capture:**

```javascript
// utils/data-pipeline/provenance.js (TO BE CREATED)

class ProvenanceCapture {
  capture() {
    return {
      source_type: 'website',
      source_url: window.location.href,
      source_date: new Date().toISOString(),
      captured_by: 'autofill-extension',
      page_title: document.title,
      page_domain: window.location.hostname,
      capture_timestamp: Date.now(),
      user_agent: navigator.userAgent,
      // Additional context
      meta: {
        canonical_url: this.getCanonicalUrl(),
        last_modified: this.getLastModified(),
        page_language: document.documentElement.lang
      }
    };
  }

  getCanonicalUrl() {
    const canonical = document.querySelector('link[rel="canonical"]');
    return canonical?.href || null;
  }

  getLastModified() {
    // Try to get page modification date
    const modified = document.querySelector('meta[property="article:modified_time"]');
    return modified?.content || null;
  }
}
```

---

## Integration with basset-hound

### Enhanced basset-hound-sync.js

```javascript
// utils/data-pipeline/basset-hound-sync.js enhancements

class BassetHoundSync {
  // ... existing code ...

  async createOrphanWithProvenance(data) {
    const payload = {
      identifier_type: data.identifier_type,
      identifier_value: data.identifier_value,
      metadata: data.metadata || {},
      provenance: data.provenance  // NEW: Include provenance
    };

    // Optionally verify before sending
    if (this.config.verifyBeforeSync) {
      const verification = await this.verifier.verify(
        data.identifier_type,
        data.identifier_value
      );

      if (!verification.plausible) {
        throw new Error(`Data not plausible: ${verification.reason}`);
      }

      payload.metadata.verification = verification;
    }

    return this.sendToBackend('POST', '/orphans', payload);
  }

  async createEntityWithSource(entityData, sourceUrl) {
    const provenance = {
      source_type: 'website',
      source_url: sourceUrl,
      source_date: new Date().toISOString(),
      captured_by: 'autofill-extension'
    };

    return this.sendToBackend('POST', '/entities', {
      ...entityData,
      provenance
    });
  }
}
```

---

## UI Enhancements

### DevTools Panel Additions

Add new tab: **"Ingest"**

```html
<!-- devtools-panel.html additions -->
<div id="tab-ingest" class="tab-content">
  <div class="section">
    <h3>Detected Data</h3>
    <div id="detected-data-list">
      <!-- Auto-populated with detected items -->
    </div>
  </div>

  <div class="section">
    <h3>Selected Elements</h3>
    <button id="enable-picker">Enable Element Picker</button>
    <div id="selected-elements-list"></div>
  </div>

  <div class="section">
    <h3>Verification Status</h3>
    <div id="verification-status"></div>
  </div>

  <div class="actions">
    <button id="verify-all">Verify All</button>
    <button id="ingest-selected" class="primary">Ingest Selected</button>
  </div>
</div>
```

### Popup UI Additions

```html
<!-- popup.html additions -->
<div class="quick-actions">
  <button id="quick-scan">Scan Page</button>
  <button id="quick-ingest">Quick Ingest</button>
  <button id="screenshot">Screenshot</button>
</div>

<div id="scan-results">
  <div class="result-count">
    <span id="email-count">0</span> emails,
    <span id="phone-count">0</span> phones,
    <span id="crypto-count">0</span> crypto
  </div>
</div>
```

---

## Dependencies to Add

```json
{
  "dependencies": {
    "libphonenumber-js": "^1.10.0",
    "wallet-address-validator": "^0.2.4",
    "validator": "^13.9.0"
  }
}
```

Note: For Chrome MV3 extensions, these need to be bundled (e.g., with webpack or rollup).

---

## New Files to Create

1. `utils/data-pipeline/field-detector.js` - OSINT field detection
2. `utils/data-pipeline/verifier.js` - Data verification
3. `utils/data-pipeline/provenance.js` - Provenance capture
4. `utils/ui/ingest-panel.js` - Ingest modal UI
5. `utils/ui/element-picker.js` - Element selection mode

---

## Integration Testing Checklist

- [ ] Field detection finds emails, phones, crypto on test pages
- [ ] Verification correctly validates/rejects test data
- [ ] Provenance captures full URL and timestamp
- [ ] basset-hound receives data with provenance
- [ ] Element picker captures selected elements
- [ ] Screenshot functionality works
- [ ] Offline queue handles disconnection
- [ ] MCP tools expose ingestion capabilities

---

## Security Considerations

1. **Data Privacy:** Selected data may contain PII - handle carefully
2. **Screenshot Consent:** Users should confirm before capturing
3. **Verification APIs:** Don't leak investigation targets
4. **Storage:** Sensitive data should be encrypted in offline queue

---

## Next Steps

See updated ROADMAP.md for implementation phases.
Please also make sure to make the MCP server for this project located in bassett MCP folder more modular or split it into multiple files as needed. Otherwise I really want to get to testing this app and please move all scripts into the tests folder To help kind of clean up this repository Otherwise please deploy this app and show me where I can access it in my browser to check to make sure that the Profile handling is good all the fea.... up the pages from a profile and show A map of connections with nodes and edges from the perspective of the current profile that I'm not. That's another thing I want to mention is that when we view the map of all the nodes and connections I want the center of it to be the current profile that we are looking at does this make sense? Or is this already implemented Otherwise please continue with what you're doing. Please make sure the road map reflects these ideas
I see you've also requested additional tasks. Let me continue creating the findings documents and then address your additional requests. Let me create the basset-hound-browser findings document first.
Write INTEGRATION-RESEARCH-2026-01-04.md
528 lines
# Integration Research Findings - Basset Hound Browser

**Date:** January 4, 2026
**Purpose:** Document integration strategies for OSINT agent automation

---

## Overview

Basset Hound Browser is an Electron-based automation browser designed for OSINT investigations. This document outlines how it integrates with the broader ecosystem for AI-driven automated investigations.

---

## Current State Analysis

### Existing Capabilities (v8.2.4)

| Category | Features |
|----------|----------|
| **Core Automation** | Navigation, form filling, clicking, scrolling, screenshots |
| **Bot Evasion** | Fingerprint spoofing, human-like typing, mouse simulation |
| **Proxy Support** | HTTP/HTTPS, SOCKS4/5, Tor integration, proxy rotation |
| **Content Extraction** | Technology detection, metadata, links, forms, images |
| **Network Analysis** | HAR export, request capture, security headers |
| **Session Management** | Recording, replay, profiles, cookies |
| **Client Libraries** | Python, Node.js, CLI tool |
| **Tor Integration** | Embedded Tor, circuit management, exit node selection |

### Architecture

```
External Client (OSINT Agent)
         |
         | WebSocket (ws://localhost:8765)
         v
+-------------------+
|   MAIN PROCESS    |  <-- main.js
|  - WebSocket srv  |
|  - IPC handlers   |
|  - Evasion config |
+-------------------+
         |
         | IPC
         v
+-------------------+
|   PRELOAD SCRIPT  |  <-- preload.js
|  - Context bridge |
+-------------------+
         |
         v
+-------------------+
|    RENDERER       |  <-- renderer/
|  - Webview ctrl   |
+-------------------+
```

---

## Integration with OSINT Agent

### Recommended Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        OSINT AGENT                               │
│  (palletAI, Claude with MCP, custom Python/Node.js script)       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐    ┌──────────────────┐                  │
│  │  Task Planner     │    │  Data Processor  │                  │
│  │  - Investigation  │    │  - Extract data  │                  │
│  │    goals          │    │  - Normalize     │                  │
│  │  - Step planning  │    │  - Deduplicate   │                  │
│  └────────┬─────────┘    └────────┬─────────┘                  │
│           │                       │                              │
│           ▼                       ▼                              │
│  ┌────────────────────────────────────────────┐                 │
│  │           Browser Controller                │                 │
│  │  - WebSocket client to basset-hound-browser│                 │
│  │  - Command execution                        │                 │
│  │  - Screenshot capture                       │                 │
│  │  - Page state extraction                    │                 │
│  └────────────────────────────────────────────┘                 │
│                          │                                       │
└──────────────────────────┼───────────────────────────────────────┘
                           │ WebSocket
                           ▼
              ┌─────────────────────────────┐
              │   basset-hound-browser      │
              │   (Electron automation)     │
              │                             │
              │   - Execute navigation      │
              │   - Fill forms              │
              │   - Bypass bot detection    │
              │   - Capture content         │
              └──────────────┬──────────────┘
                             │
                             │ Extracted Data
                             ▼
              ┌─────────────────────────────┐
              │       basset-hound          │
              │   (Entity Storage)          │
              │                             │
              │   - Store orphan data       │
              │   - Track relationships     │
              │   - Verify identifiers      │
              └─────────────────────────────┘
```

---

## OSINT Agent Workflow Example

### Python Implementation

```python
# osint_agent.py

import asyncio
import json
from datetime import datetime
from basset_hound_browser import BassetHoundBrowser
from basset_hound_client import BassetHoundClient

class OSINTAgent:
    def __init__(self, project_name: str):
        self.browser = BassetHoundBrowser()
        self.basset = BassetHoundClient(project=project_name)

    async def investigate_target(self, target_url: str):
        """Run automated investigation on a target URL."""

        # 1. Navigate to target
        await self.browser.navigate(target_url)
        await self.browser.wait_for_load()

        # 2. Capture page state
        page_state = await self.browser.get_page_state()
        screenshot = await self.browser.screenshot()

        # 3. Detect technologies
        tech_stack = await self.browser.detect_technologies()

        # 4. Extract content
        extracted = await self.browser.extract_all()

        # 5. Process extracted data
        findings = self.process_extraction(extracted, target_url)

        # 6. Store in basset-hound
        await self.store_findings(findings, target_url)

        return {
            "url": target_url,
            "technologies": tech_stack,
            "findings_count": len(findings),
            "screenshot": screenshot
        }

    def process_extraction(self, extracted: dict, source_url: str):
        """Process extracted content for OSINT data."""
        findings = []

        # Extract emails
        for email in extracted.get("emails", []):
            findings.append({
                "type": "EMAIL",
                "value": email,
                "source_url": source_url
            })

        # Extract links for further investigation
        for link in extracted.get("links", []):
            if self.is_interesting_link(link):
                findings.append({
                    "type": "URL",
                    "value": link["href"],
                    "source_url": source_url,
                    "context": link.get("text", "")
                })

        # Extract from structured data (JSON-LD, etc.)
        for schema in extracted.get("structured_data", []):
            if schema.get("@type") == "Person":
                findings.extend(self.extract_person_data(schema, source_url))

        return findings

    async def store_findings(self, findings: list, source_url: str):
        """Store findings in basset-hound with provenance."""
        provenance = {
            "source_type": "website",
            "source_url": source_url,
            "source_date": datetime.now().isoformat(),
            "captured_by": "basset-hound-browser"
        }

        for finding in findings:
            await self.basset.create_orphan(
                identifier_type=finding["type"],
                value=finding["value"],
                metadata={
                    "context": finding.get("context", ""),
                    "verification": await self.verify(finding)
                },
                provenance=provenance
            )

    async def verify(self, finding: dict):
        """Verify finding before storage."""
        # Call basset-hound verification API
        return await self.basset.verify(
            identifier_type=finding["type"],
            value=finding["value"]
        )

# Usage
async def main():
    agent = OSINTAgent("my-investigation")

    targets = [
        "https://example.com/about",
        "https://example.org/team"
    ]

    for target in targets:
        result = await agent.investigate_target(target)
        print(f"Investigated {target}: {result['findings_count']} findings")

asyncio.run(main())
```

### Node.js Implementation

```javascript
// osint-agent.js

const { BassetHoundBrowser } = require('basset-hound-client');
const BassetHound = require('basset-hound-client');

class OSINTAgent {
  constructor(projectName) {
    this.browser = new BassetHoundBrowser();
    this.basset = new BassetHound({ project: projectName });
  }

  async investigateTarget(targetUrl) {
    await this.browser.connect();

    try {
      // Navigate and extract
      await this.browser.navigate(targetUrl);
      const pageState = await this.browser.getPageState();
      const screenshot = await this.browser.screenshot();
      const extracted = await this.browser.extractAll();

      // Process and store
      const findings = this.processExtraction(extracted, targetUrl);
      await this.storeFindings(findings, targetUrl);

      return {
        url: targetUrl,
        findingsCount: findings.length,
        screenshot
      };
    } finally {
      await this.browser.disconnect();
    }
  }

  async storeFindings(findings, sourceUrl) {
    const provenance = {
      source_type: 'website',
      source_url: sourceUrl,
      source_date: new Date().toISOString(),
      captured_by: 'basset-hound-browser'
    };

    for (const finding of findings) {
      await this.basset.createOrphan({
        identifier_type: finding.type,
        identifier_value: finding.value,
        metadata: { context: finding.context },
        provenance
      });
    }
  }
}

module.exports = { OSINTAgent };
```

---

## New WebSocket Commands for OSINT

### Proposed Additions

| Command | Description | Parameters |
|---------|-------------|------------|
| `extract_osint_data` | Extract all OSINT-relevant data | `types[]` (email, phone, crypto, etc.) |
| `verify_data` | Verify extracted data | `type`, `value` |
| `store_to_basset` | Direct storage to basset-hound | `orphan_data`, `provenance` |
| `investigate_links` | Follow and investigate linked pages | `depth`, `patterns[]` |
| `capture_evidence` | Screenshot + HTML + metadata | `format` |

### Implementation

```javascript
// websocket/commands/osint-commands.js (TO BE CREATED)

const osintCommands = {
  extract_osint_data: async (params, webContents) => {
    const types = params.types || ['email', 'phone', 'crypto'];

    const extracted = await webContents.executeJavaScript(`
      (function() {
        const patterns = {
          email: /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}/g,
          phone: /(?:\\+?1[-.]?)?\\(?[0-9]{3}\\)?[-.]?[0-9]{3}[-.]?[0-9]{4}/g,
          crypto_btc: /\\b(bc1|[13])[a-zA-HJ-NP-Z0-9]{25,39}\\b/g,
          crypto_eth: /\\b0x[a-fA-F0-9]{40}\\b/g
        };

        const text = document.body.innerText;
        const results = {};

        for (const [type, pattern] of Object.entries(patterns)) {
          results[type] = [...new Set(text.match(pattern) || [])];
        }

        return results;
      })()
    `);

    return { success: true, data: extracted };
  },

  capture_evidence: async (params, win) => {
    const webContents = win.webContents;

    // Capture screenshot
    const image = await webContents.capturePage();
    const screenshot = image.toDataURL();

    // Capture HTML
    const html = await webContents.executeJavaScript('document.documentElement.outerHTML');

    // Capture metadata
    const metadata = await webContents.executeJavaScript(`
      ({
        url: window.location.href,
        title: document.title,
        timestamp: new Date().toISOString(),
        meta: Array.from(document.querySelectorAll('meta')).map(m => ({
          name: m.name || m.getAttribute('property'),
          content: m.content
        }))
      })
    `);

    return {
      success: true,
      data: {
        screenshot,
        html,
        metadata
      }
    };
  }
};

module.exports = osintCommands;
```

---

## Tor Integration for Anonymous Investigation

### Usage Pattern

```python
# Anonymous investigation with Tor
async def anonymous_investigation(target: str):
    browser = BassetHoundBrowser()

    # Start embedded Tor
    await browser.tor_start()
    await browser.tor_set_exit_country('DE')  # Use German exit

    # Verify Tor is working
    tor_status = await browser.tor_check_connection()
    print(f"Using Tor exit IP: {tor_status['exit_ip']}")

    # Navigate through Tor
    await browser.navigate(target)

    # Extract data
    data = await browser.extract_osint_data()

    # Rotate circuit for next target
    await browser.tor_rebuild_circuit()

    return data
```

---

## basset-hound-browser Client Library Enhancements

### Python Client Updates

```python
# clients/python/basset_hound_browser/osint.py (TO BE CREATED)

class OSINTMixin:
    """OSINT-specific methods for BassetHoundBrowser client."""

    async def extract_osint_data(self, types=None):
        """Extract OSINT-relevant data from current page."""
        return await self.send_command('extract_osint_data', {
            'types': types or ['email', 'phone', 'crypto', 'domain']
        })

    async def capture_evidence(self):
        """Capture screenshot, HTML, and metadata as evidence."""
        return await self.send_command('capture_evidence', {})

    async def investigate_page(self):
        """Full investigation of current page."""
        page_state = await self.get_page_state()
        technologies = await self.detect_technologies()
        osint_data = await self.extract_osint_data()
        evidence = await self.capture_evidence()

        return {
            'page_state': page_state,
            'technologies': technologies,
            'osint_data': osint_data,
            'evidence': evidence
        }
```

---

## Integration Test Suite

### Test Scenarios

```javascript
// tests/integration/osint-workflow.test.js (TO BE CREATED)

describe('OSINT Workflow Integration', () => {
  let browser;

  beforeAll(async () => {
    browser = new BassetHoundBrowser();
    await browser.connect();
  });

  afterAll(async () => {
    await browser.disconnect();
  });

  test('should extract emails from page', async () => {
    await browser.navigate('https://example.com/contact');
    const data = await browser.extractOsintData(['email']);
    expect(data.email).toBeInstanceOf(Array);
  });

  test('should capture evidence bundle', async () => {
    await browser.navigate('https://example.com');
    const evidence = await browser.captureEvidence();
    expect(evidence.screenshot).toBeDefined();
    expect(evidence.html).toBeDefined();
    expect(evidence.metadata.url).toBe('https://example.com/');
  });

  test('should use Tor for anonymous browsing', async () => {
    await browser.torStart();
    const status = await browser.torCheckConnection();
    expect(status.is_tor).toBe(true);
    expect(status.exit_ip).toBeDefined();
    await browser.torStop();
  });
});
```

---

## File Structure Updates

```
basset-hound-browser/
├── websocket/
│   └── commands/
│       ├── osint-commands.js       # NEW: OSINT extraction commands
│       └── evidence-commands.js    # NEW: Evidence capture commands
├── clients/
│   ├── python/
│   │   └── basset_hound_browser/
│   │       ├── client.py
│   │       └── osint.py            # NEW: OSINT mixin
│   └── nodejs/
│       └── osint.js                # NEW: OSINT mixin
├── tests/
│   └── integration/
│       └── osint-workflow.test.js  # NEW: OSINT tests
└── docs/
    └── OSINT-INTEGRATION.md        # NEW: Integration guide
```

---

## Security Considerations

1. **Tor Usage:** Respect exit node bandwidth, don't abuse
2. **Rate Limiting:** Implement delays between requests
3. **Target Ethics:** Only investigate legitimate targets
4. **Data Handling:** Encrypt sensitive data at rest
5. **Evidence Chain:** Maintain provenance for legal validity

---

## Next Steps

See updated ROADMAP.md for implementation phases.
Now let me update the todos and create an integration architecture document, then update all the roadmaps.
Update Todos

Explore and review basset-hound repository

Explore and review autofill-extension repository

Explore and review basset-hound-browser repository

Research data verification APIs and methods

Document research findings in each repository's docs folder

Update ROADMAP.md for basset-hound

Update ROADMAP.md for autofill-extension

Update ROADMAP.md for basset-hound-browser

Create integration architecture document

Make MCP server more modular (split files)

Move scripts to tests folder

Deploy basset-hound app for testing

Ensure graph visualization centers on current profile
Now let me read the current ROADMAP.md for basset-hound to see how to best update it.
Read ROADMAP.md (lines 2001-2200)
Read ROADMAP.md (lines 2141-2240)
Now I'll update the basset-hound ROADMAP with the new integration phases.
Edit ROADMAP.md
Added 101 lines
Now let me update the autofill-extension ROADMAP.
Read ROADMAP.md (lines 841-890)
Edit ROADMAP.md
Added 90 lines
Now let me update the basset-hound-browser ROADMAP.
Read ROADMAP.md (lines 891-920)
Edit ROADMAP.md
Added 50 lines
