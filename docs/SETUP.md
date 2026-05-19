# Basset Hound - Local Development Setup Guide

**Version**: 2.0.0  
**Last Updated**: 2026-05-19  
**Purpose**: Quick setup for developers working on Basset Hound locally

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start (Docker)](#quick-start-docker)
3. [Manual Setup (Development)](#manual-setup-development)
4. [IDE Configuration](#ide-configuration)
5. [Environment Variables](#environment-variables)
6. [Database Initialization](#database-initialization)
7. [Running Tests](#running-tests)
8. [Troubleshooting](#troubleshooting)
9. [Next Steps](#next-steps)

---

## Prerequisites

### System Requirements

**Minimum**:
- CPU: 2 cores
- Memory: 4GB RAM
- Disk: 20GB available
- OS: Ubuntu 20.04+, macOS 12+, or Windows 10+ with WSL2

**Recommended for Development**:
- CPU: 4+ cores
- Memory: 8GB+ RAM
- Disk: 50GB SSD
- OS: Ubuntu 22.04 LTS or macOS 13+

### Required Software

**macOS**:
```bash
# Install Homebrew first
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install dependencies
brew install docker docker-compose python@3.12 git node curl
```

**Ubuntu/Debian**:
```bash
sudo apt-get update && sudo apt-get install -y \
  docker.io \
  docker-compose \
  python3.12 \
  python3.12-venv \
  git \
  curl \
  nodejs \
  npm
```

**Windows (WSL2)**:
```powershell
# Install WSL2
wsl --install

# In WSL2 terminal, run Ubuntu instructions above
```

### Verify Installations

```bash
docker --version        # Should be 24.0+
docker-compose --version  # Should be 2.20+
python3.12 --version    # Should be 3.12+
node --version          # Should be 18.0+
git --version           # Any recent version
```

---

## Quick Start (Docker)

### Fastest Setup (< 5 minutes)

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/basset-hound.git
cd basset-hound

# 2. Copy environment template
cp .env.example .env

# 3. Start all services
docker-compose up --build -d

# 4. Wait for services to be healthy
sleep 10
docker-compose ps

# 5. Initialize database
docker-compose exec basset_api python scripts/init_db.py

# 6. Verify installation
curl http://localhost:8080/health
```

### Access the Application

| Service | URL | User | Password |
|---------|-----|------|----------|
| **Dashboard** | http://localhost:8080/ | N/A | N/A |
| **API Docs** | http://localhost:8080/docs | N/A | N/A |
| **Neo4j** | http://localhost:7474 | neo4j | neo4jbasset |
| **Grafana** | http://localhost:3000 | admin | admin |
| **Prometheus** | http://localhost:9090 | N/A | N/A |

### Common Docker Commands

```bash
# View logs
docker-compose logs -f basset_api

# Restart a service
docker-compose restart basset_api

# Stop all services
docker-compose down

# Clean up (remove volumes)
docker-compose down -v

# Run a command in a container
docker-compose exec basset_api python -m pytest tests/

# View service status
docker-compose ps
```

---

## Manual Setup (Development)

### For developers making frequent changes to Python code

```bash
# 1. Clone repository
git clone https://github.com/yourusername/basset-hound.git
cd basset-hound

# 2. Create Python virtual environment
python3.12 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Additional dev tools

# 4. Start Neo4j and Redis (Docker only)
docker-compose up -d neo4j redis

# 5. Create .env file
cp .env.example .env

# 6. Edit .env with correct paths
# NEO4J_URI=bolt://localhost:7687
# NEO4J_USER=neo4j
# NEO4J_PASSWORD=neo4jbasset
# REDIS_URL=redis://localhost:6379/0

# 7. Initialize database
python scripts/init_db.py

# 8. Start Basset Hound API
python main.py
```

**Expected Output**:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

Access API at `http://localhost:8000/docs`

### Frontend Development

For developing React/Vue components:

```bash
# Install Node dependencies
cd frontend && npm install

# Start development server
npm run dev

# Or watch mode for building with FastAPI
npm run watch
```

---

## IDE Configuration

### VS Code

**Recommended Extensions**:
```
Python
Pylance
Ruff (Python linter)
JSON
YAML
REST Client
Docker
SQLTools
```

**settings.json**:
```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.formatting.provider": "none",
  "[python]": {
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.fixAll.ruff": true
    }
  },
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests"]
}
```

**launch.json** (for debugging):
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": ["main:app", "--reload"],
      "jinja": true,
      "console": "integratedTerminal",
      "python": "${command:python.interpreterPath}"
    }
  ]
}
```

### PyCharm

1. **Set Python Interpreter**: Preferences → Python Interpreter → Add local interpreter → venv
2. **Enable pytest**: Preferences → Tools → Python Integrated Tools → Testing → pytest
3. **Code Style**: Preferences → Editor → Code Style → Set to PEP 8
4. **Run Configuration**: Edit → Add Configuration → Python → Module name: uvicorn, Parameters: main:app --reload

### Vim/Neovim

Use the setup in `.nvim/init.lua` (if provided) or install:
- vim-python-pep8-indent
- coc-python
- ALE (Asynchronous Lint Engine)

---

## Environment Variables

### Development (.env file)

```bash
# FastAPI Settings
DEBUG=true
ENVIRONMENT=development
API_HOST=0.0.0.0
API_PORT=8000
SECRET_KEY=dev-secret-key-change-in-production

# Database
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=neo4jbasset
NEO4J_ENCRYPTED=false

# Cache
REDIS_URL=redis://localhost:6379/0
CACHE_ENABLED=true
CACHE_TTL_DEFAULT=300

# Phase 8 Features
ENABLE_ML_ANALYTICS=true
ENABLE_COLLABORATION=true
ENABLE_PLUGINS=true
ENABLE_EXPORT=true
ENABLE_CACHE_MANAGEMENT=true

# Logging
LOG_LEVEL=DEBUG
LOG_FORMAT=json
```

### Production (.env.production file)

```bash
# FastAPI Settings
DEBUG=false
ENVIRONMENT=production
API_HOST=0.0.0.0
API_PORT=8000
SECRET_KEY=your-secure-random-key-here

# Database (Production)
NEO4J_URI=bolt://neo4j-server:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-secure-password-here
NEO4J_ENCRYPTED=true

# Cache (Production)
REDIS_URL=redis://:your-password@redis-server:6379/0
CACHE_ENABLED=true
CACHE_TTL_DEFAULT=600

# Phase 8 Features (Tune for production)
ENABLE_ML_ANALYTICS=true
ENABLE_COLLABORATION=true
ENABLE_PLUGINS=true
ENABLE_EXPORT=true
ML_DUPLICATE_THRESHOLD=0.75
MAX_CONCURRENT_CONNECTIONS=500

# Logging (Production)
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### Environment Variable Reference

| Variable | Default | Purpose |
|----------|---------|---------|
| DEBUG | false | Enable debug mode and detailed logging |
| ENVIRONMENT | production | Deployment environment (development/staging/production) |
| API_PORT | 8000 | Port for FastAPI server |
| NEO4J_URI | bolt://localhost:7687 | Neo4j database URI |
| REDIS_URL | redis://localhost:6379/0 | Redis connection string |
| CACHE_ENABLED | true | Enable caching layer |
| ENABLE_ML_ANALYTICS | true | Enable ML features |
| ENABLE_COLLABORATION | true | Enable real-time features |

---

## Database Initialization

### First-Time Setup

```bash
# Using Docker Compose
docker-compose exec basset_api python scripts/init_db.py

# Manual setup
# 1. Connect to Neo4j
docker-compose exec neo4j cypher-shell -u neo4j -p neo4jbasset

# 2. Run initialization
python scripts/init_db.py
```

### Create Sample Data

```bash
# Load sample project
docker-compose exec basset_api python scripts/load_samples.py

# View in Neo4j Browser
# http://localhost:7474
# Credentials: neo4j / neo4jbasset
```

### Reset Database

```bash
# ⚠️ WARNING: Deletes all data
docker-compose exec neo4j cypher-shell -u neo4j -p neo4jbasset "MATCH (n) DETACH DELETE n"

# Reinitialize
docker-compose exec basset_api python scripts/init_db.py
```

---

## Running Tests

### Quick Test Run

```bash
# All tests (< 2 minutes)
python -m pytest tests/ -v

# Specific test file
python -m pytest tests/test_entities.py -v

# Specific test function
python -m pytest tests/test_entities.py::test_create_entity -v
```

### Test Coverage

```bash
# Generate coverage report
python -m pytest tests/ --cov=api --cov-report=html

# View report
open htmlcov/index.html  # macOS
firefox htmlcov/index.html  # Linux
```

### Test Categories

```bash
# Unit tests only
python -m pytest tests/ -m unit -v

# Integration tests only
python -m pytest tests/ -m integration -v

# Slow tests (>1s)
python -m pytest tests/ -m slow -v

# Skip slow tests
python -m pytest tests/ -m "not slow" -v
```

### Continuous Testing

```bash
# Auto-run tests on file changes (requires pytest-watch)
pip install pytest-watch
ptw tests/

# Or use file watcher
while inotifywait -r tests/ api/; do python -m pytest tests/ -q; done
```

---

## Troubleshooting

### Docker Issues

**Ports Already in Use**:
```bash
# Find process using port 8080
lsof -i :8080

# Kill process
kill -9 <PID>

# Or change port in docker-compose.yml
```

**Services Not Starting**:
```bash
# Check logs
docker-compose logs

# Restart from scratch
docker-compose down -v
docker-compose up --build -d
```

**Database Connection Failed**:
```bash
# Check Neo4j is healthy
docker-compose exec neo4j cypher-shell -u neo4j -p neo4jbasset "RETURN 1"

# Check credentials in .env
# Default: neo4j / neo4jbasset
```

### Python Issues

**Module Not Found**:
```bash
# Verify venv is activated
which python  # Should show path to venv

# Reinstall dependencies
pip install -r requirements.txt
```

**Import Errors**:
```bash
# Verify Python version
python --version  # Must be 3.12+

# Clear cache
find . -type d -name __pycache__ -exec rm -r {} +
pip cache purge
```

### Port Conflicts

**Services on Different Ports**:
```bash
# Change in .env or docker-compose.yml
API_PORT=8001
GRAFANA_PORT=3001
PROMETHEUS_PORT=9001
NEO4J_PORT=7688
```

### Database Issues

**High Memory Usage**:
```bash
# Check Neo4j memory
docker stats neo4j

# Reduce in docker-compose.yml
environment:
  - NEO4J_HEAP_MEMORY=512M
```

**Slow Queries**:
```bash
# Enable query logging
docker-compose exec neo4j cypher-shell -u neo4j -p neo4jbasset \
  "CALL dbms.setConfig('server.logs.query.enabled', 'true')"

# View query log
docker-compose exec neo4j tail -f logs/query.log
```

---

## Development Workflow

### Feature Development

```bash
# 1. Create feature branch
git checkout -b feature/my-feature

# 2. Make changes and test locally
python -m pytest tests/test_my_feature.py -v

# 3. Run linter and formatter
ruff check api/ --fix
mypy api/ --ignore-missing-imports

# 4. Commit changes
git add .
git commit -m "feat: Add my feature"

# 5. Push and create pull request
git push origin feature/my-feature
```

### Bug Fixing

```bash
# 1. Create issue branch
git checkout -b fix/issue-123

# 2. Write test that reproduces bug
python -m pytest tests/test_bug_fix.py::test_bug -v

# 3. Fix code until test passes
# ... edit code ...
python -m pytest tests/test_bug_fix.py::test_bug -v

# 4. Run full test suite
python -m pytest tests/ -v

# 5. Commit with issue reference
git commit -m "fix: Resolve issue #123 - bug description"

# 6. Push and create pull request
```

### Code Review Checklist

Before pushing code:
- [ ] All tests pass: `python -m pytest tests/ -v`
- [ ] Code formatted: `ruff check api/ --fix`
- [ ] Type hints valid: `mypy api/ --ignore-missing-imports`
- [ ] Documentation updated for API changes
- [ ] CHANGELOG.md updated
- [ ] No debug print statements
- [ ] No hardcoded secrets or credentials

---

## Next Steps

1. **Explore the Codebase**:
   - Read `docs/ARCHITECTURE.md` for system overview
   - Check `api/routers/` for endpoint structure
   - Review `api/services/` for business logic

2. **Run Examples**:
   - Check `tests/` for usage examples
   - Try API endpoints: `http://localhost:8000/docs`
   - Create test project and entities

3. **Make Your First Change**:
   - Create small feature or fix bug
   - Follow development workflow above
   - Submit pull request

4. **Read Phase 8 Documentation**:
   - Review `docs/PHASE-8-IMPLEMENTATION-GUIDE.md`
   - Check relevant stream document in `docs/findings/`
   - Understand performance optimizations

5. **Join Development**:
   - Check issues with `help wanted` label
   - Read `docs/CONTRIBUTING.md` for guidelines
   - Ask questions in discussions

---

## Additional Resources

- **API Documentation**: `http://localhost:8000/docs` (interactive)
- **Architecture Guide**: `docs/ARCHITECTURE.md`
- **Deployment Guide**: `docs/DEPLOYMENT.md`
- **Contributing Guide**: `docs/CONTRIBUTING.md`
- **Neo4j Documentation**: https://neo4j.com/docs/
- **FastAPI Documentation**: https://fastapi.tiangolo.com/

---

## Getting Help

### Debug Locally

```bash
# Enable debug logging
export DEBUG=true
python main.py

# Check individual services
curl http://localhost:8000/health
curl http://localhost:9090/api/v1/query?query=up

# View database directly
docker-compose exec neo4j cypher-shell -u neo4j -p neo4jbasset
```

### Check Documentation

1. Read relevant section in this file
2. Check `docs/TROUBLESHOOTING.md` (when available)
3. Search `docs/` for related topics
4. Check test files for usage examples

### Ask for Help

- Open issue on GitHub
- Check existing issues/discussions
- Contact maintainers via email

---

**Happy coding! 🎉**

Created for Basset Hound Phase 8 | Last Updated: 2026-05-19
