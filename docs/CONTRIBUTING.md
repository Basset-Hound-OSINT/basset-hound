# Contributing to Basset Hound

**Version**: 2.0.0  
**Last Updated**: 2026-05-07

Thank you for your interest in contributing to Basset Hound! This document provides guidelines for contributing code, documentation, and bug reports.

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Setup](#development-setup)
4. [Code Style](#code-style)
5. [Git Workflow](#git-workflow)
6. [Testing](#testing)
7. [Documentation](#documentation)
8. [Pull Request Process](#pull-request-process)
9. [Commit Message Guidelines](#commit-message-guidelines)
10. [Reporting Bugs](#reporting-bugs)
11. [Suggesting Features](#suggesting-features)

---

## Code of Conduct

By participating in this project, you agree to:

- Be respectful and inclusive
- Provide constructive feedback
- Accept criticism gracefully
- Focus on the code, not the person
- Help create a welcoming environment

---

## Getting Started

### Prerequisites

- Python 3.12+
- Docker & Docker Compose
- Git
- Text editor (VS Code, PyCharm, etc.)

### Fork & Clone

```bash
# 1. Fork on GitHub
# https://github.com/yourusername/basset-hound/fork

# 2. Clone your fork
git clone https://github.com/YOUR_USERNAME/basset-hound.git
cd basset-hound

# 3. Add upstream remote
git remote add upstream https://github.com/yourusername/basset-hound.git

# 4. Verify remotes
git remote -v
# origin   https://github.com/YOUR_USERNAME/basset-hound.git (fetch)
# origin   https://github.com/YOUR_USERNAME/basset-hound.git (push)
# upstream https://github.com/yourusername/basset-hound.git (fetch)
```

---

## Development Setup

### 1. Create Development Environment

```bash
# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt  # If available
# Otherwise: pip install pytest pytest-asyncio pytest-cov ruff mypy
```

### 2. Start Services

```bash
# Start Docker services
docker compose up -d

# Wait for services to be healthy
docker compose ps

# Check health
curl http://localhost:8080/health
```

### 3. Run Tests

```bash
# All tests
python -m pytest tests/ -v

# With coverage
python -m pytest tests/ --cov=api --cov-report=html
```

### 4. Start Development Server

```bash
# Run FastAPI server
python main.py

# Or with auto-reload
pip install watchfiles  # For auto-reload
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Code Style

### Python Style Guide (PEP 8)

```python
# Good
def create_entity(project_id: str, entity_data: dict) -> Entity:
    """Create a new entity in the project.
    
    Args:
        project_id: The project ID
        entity_data: Entity attributes
        
    Returns:
        Created entity with ID
        
    Raises:
        ValueError: If project not found
    """
    if not project_id:
        raise ValueError("project_id required")
    
    entity = Entity(id=generate_id(), **entity_data)
    return entity

# Bad
def create_entity(project_id,entity_data):
    e=Entity(id=generate_id(),**entity_data)
    return e
```

### Naming Conventions

```python
# Classes: PascalCase
class EntityService:
    pass

# Functions/methods: snake_case
def get_entity_by_id(entity_id: str) -> Entity:
    pass

# Constants: UPPER_SNAKE_CASE
MAX_ENTITIES = 1000000
DEFAULT_TIMEOUT = 30

# Private methods: _leading_underscore
def _validate_entity(entity: Entity) -> bool:
    pass

# Protected methods: _leading_underscore
def _calculate_confidence(data: dict) -> float:
    pass
```

### Type Hints (Required)

```python
# All functions must have type hints
from typing import Optional, List, Dict, Tuple

def search_entities(
    project_id: str,
    query: str,
    limit: int = 20,
    offset: int = 0
) -> Tuple[List[Entity], int]:
    """Search entities in project.
    
    Returns:
        Tuple of (entities, total_count)
    """
    pass
```

### Docstring Style (Google Format)

```python
def calculate_similarity(text1: str, text2: str) -> float:
    """Calculate string similarity using Levenshtein distance.
    
    Uses the FuzzyWuzzy library for case-insensitive matching.
    
    Args:
        text1: First string to compare
        text2: Second string to compare
        
    Returns:
        Similarity score between 0.0 and 1.0
        
    Raises:
        ValueError: If either string is empty
        TypeError: If inputs are not strings
        
    Examples:
        >>> calculate_similarity("John Doe", "John D.")
        0.89
    """
    if not text1 or not text2:
        raise ValueError("Strings cannot be empty")
    
    if not isinstance(text1, str) or not isinstance(text2, str):
        raise TypeError("Inputs must be strings")
    
    # Implementation
    return score
```

### Code Quality Tools

**Ruff (Linting & Formatting)**

```bash
# Check code
ruff check api/ tests/

# Fix issues automatically
ruff check api/ --fix

# Format code
ruff format api/ tests/
```

**MyPy (Type Checking)**

```bash
# Check types
mypy api/ --ignore-missing-imports

# Strict mode
mypy api/ --strict
```

**Configuration** (pyproject.toml)

```toml
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
extend-select = ["E", "F", "I", "N"]

[tool.mypy]
python_version = "3.12"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false  # Too strict for now
```

---

## Git Workflow

### Creating a Feature Branch

```bash
# 1. Update main branch
git checkout main
git pull upstream main

# 2. Create feature branch
git checkout -b feature/entity-search
# Or bugfix:
git checkout -b bugfix/cache-ttl-issue
# Or docs:
git checkout -b docs/api-reference

# 3. Push to your fork
git push origin feature/entity-search
```

### Commit Workflow

```bash
# 1. Make changes
# Edit files...

# 2. Check changes
git status
git diff

# 3. Stage changes
git add api/services/entity_service.py
git add tests/test_entity_service.py

# 4. Commit with good message
git commit -m "feat: implement fuzzy matching for entity search

- Add FuzzyWuzzy for string similarity
- Support partial name matches
- Include confidence scoring
- Add tests with 95%+ coverage

Resolves #123"

# 5. Push to fork
git push origin feature/entity-search
```

### Branch Naming Conventions

```
feature/description      # New features
bugfix/description       # Bug fixes
docs/description         # Documentation only
refactor/description     # Code refactoring
test/description         # Tests only
perf/description         # Performance improvements
security/description     # Security fixes
chore/description        # Maintenance tasks
```

---

## Testing

### Test Structure

```python
# tests/test_entity_service.py

import pytest
from api.services.entity_service import EntityService
from api.models import Entity

class TestEntityService:
    """Test suite for EntityService."""
    
    @pytest.fixture
    def service(self):
        """Create service instance."""
        return EntityService()
    
    @pytest.fixture
    def sample_entity(self):
        """Create sample entity for testing."""
        return {
            "name": "Test Entity",
            "type": "PERSON",
            "attributes": {"email": "test@example.com"}
        }
    
    def test_create_entity(self, service, sample_entity):
        """Test entity creation."""
        entity = service.create_entity("proj_123", sample_entity)
        
        assert entity.id is not None
        assert entity.name == "Test Entity"
        assert entity.type == "PERSON"
    
    def test_create_entity_missing_name(self, service):
        """Test entity creation with missing name."""
        with pytest.raises(ValueError, match="name required"):
            service.create_entity("proj_123", {"type": "PERSON"})
    
    @pytest.mark.asyncio
    async def test_create_entity_async(self, service, sample_entity):
        """Test async entity creation."""
        entity = await service.create_entity_async("proj_123", sample_entity)
        assert entity.id is not None
```

### Test Coverage

- **Minimum**: 80% code coverage
- **Target**: 95%+ for critical paths
- **Coverage Report**: `pytest --cov=api --cov-report=html`

### Running Tests

```bash
# All tests
python -m pytest tests/ -v

# Specific test file
python -m pytest tests/test_entity_service.py -v

# Specific test class
python -m pytest tests/test_entity_service.py::TestEntityService -v

# Specific test method
python -m pytest tests/test_entity_service.py::TestEntityService::test_create_entity -v

# With coverage
python -m pytest tests/ --cov=api --cov-report=html --cov-report=term

# Parallel execution (faster)
pip install pytest-xdist
python -m pytest tests/ -n auto

# Watch mode (auto-rerun on changes)
pip install pytest-watch
ptw tests/
```

### Mock & Fixtures

```python
import pytest
from unittest.mock import Mock, patch, AsyncMock

@pytest.fixture
def mock_neo4j():
    """Mock Neo4j handler."""
    with patch('api.services.entity_service.neo4j_handler') as mock:
        mock.create_entity.return_value = {"id": "ent_123"}
        yield mock

def test_create_entity_calls_neo4j(service, mock_neo4j):
    """Test that service calls Neo4j."""
    service.create_entity("proj_123", {"name": "Test"})
    
    mock_neo4j.create_entity.assert_called_once()
    call_args = mock_neo4j.create_entity.call_args
    assert call_args[0][0] == "proj_123"
```

---

## Documentation

### README Updates

When adding features, update README.md:
- Add to feature matrix table
- Update API endpoints list
- Include example usage
- Link to detailed docs

### API Documentation

For new endpoints:
1. Add comprehensive docstring to router function
2. Update `docs/API_REFERENCE.md`
3. Include example request/response
4. Document error codes
5. Add parameters table

```python
@router.post(
    "/projects/{project_id}/entities",
    response_model=EntityResponse,
    status_code=201,
    tags=["entities"],
    summary="Create new entity",
    responses={
        201: {"description": "Entity created successfully"},
        400: {"description": "Invalid entity data"},
        404: {"description": "Project not found"},
    }
)
async def create_entity(
    project_id: str,
    entity: EntityCreate,
    request: Request
) -> EntityResponse:
    """Create a new entity in the project.
    
    This endpoint creates a new entity with the specified attributes.
    
    Args:
        project_id: The project ID (path parameter)
        entity: Entity creation data (request body)
        request: The HTTP request object
        
    Returns:
        Created entity with generated ID
        
    Raises:
        HTTPException(404): Project not found
        HTTPException(400): Invalid entity data
    """
    # Implementation
    pass
```

### Architecture Documentation

For significant changes:
1. Update `docs/ARCHITECTURE.md`
2. Include diagrams (ASCII or Mermaid)
3. Document data flow
4. Update component diagrams
5. Explain integration points

### Changelog

Maintain `CHANGELOG.md`:

```markdown
## [2.1.0] - 2026-05-15

### Added
- New fuzzy matching algorithm for entity search
- WebSocket support for real-time notifications
- Prometheus metrics for performance monitoring

### Changed
- Improved search query parsing
- Optimized Neo4j query performance
- Updated documentation with examples

### Fixed
- Cache invalidation bug in entity updates
- WebSocket connection timeout issue
- Incorrect relationship count calculation

### Security
- Added input validation for all endpoints
- Implemented rate limiting (100 req/min)
- Added CORS origin whitelist
```

---

## Pull Request Process

### Before Creating PR

1. **Create feature branch** (see Git Workflow)
2. **Make changes** with good commit messages
3. **Run tests**: `pytest tests/ -v`
4. **Check code quality**: `ruff check`, `mypy api/`
5. **Update documentation** if needed
6. **Update CHANGELOG.md**
7. **Push to fork**: `git push origin feature/...`

### Creating Pull Request

1. **Open PR** on GitHub
2. **Fill in PR template** (see below)
3. **Link to issues**: Use `Fixes #123` or `Closes #456`
4. **Request reviewers** (1-2 core maintainers)
5. **Allow auto-merge** if all checks pass

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] New feature
- [ ] Bug fix
- [ ] Documentation
- [ ] Performance improvement
- [ ] Breaking change

## Related Issues
Fixes #123

## Changes Made
- Change 1
- Change 2
- Change 3

## Testing
- [ ] Added tests
- [ ] All tests pass: `pytest tests/ -v`
- [ ] Coverage maintained: `pytest --cov=api`
- [ ] Manual testing completed

## Code Quality
- [ ] Ruff check passes: `ruff check api/`
- [ ] MyPy check passes: `mypy api/`
- [ ] Type hints added
- [ ] Docstrings included

## Documentation
- [ ] README updated
- [ ] API reference updated (if API change)
- [ ] Changelog updated
- [ ] Architecture docs updated (if needed)

## Breaking Changes
- [ ] Yes, breaking change
  - Description:

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex logic
- [ ] No new warnings generated
- [ ] Tests added/updated
- [ ] Documentation updated
```

### Review Process

1. **Automated Checks**
   - Tests pass
   - Code coverage maintained
   - Linting passes
   - Type checking passes

2. **Code Review**
   - Code quality and style
   - Architecture and design
   - Test coverage
   - Documentation completeness

3. **Approval & Merge**
   - At least 1 approval required
   - All checks must pass
   - Main branch must be current
   - Squash commits on merge (optional)

---

## Commit Message Guidelines

### Format

```
type(scope): subject

body (optional)

footer (optional)
```

### Type

```
feat      Feature implementation
fix       Bug fix
docs      Documentation only
style     Code style changes (formatting, semicolons, etc.)
refactor  Code refactoring
perf      Performance improvement
test      Test additions/changes
chore     Build, dependencies, tooling
ci        CI/CD configuration
```

### Scope

```
entities          Entity management
relationships     Relationship handling
search            Search functionality
suggestions       Suggestion engine
reports           Report generation
integrations      External service integrations
api               API endpoints
database          Database/Neo4j
cache             Redis caching
monitoring        Prometheus/Grafana
```

### Examples

```
feat(entities): add entity type validation

- Validate entity type against allowed types
- Return 400 Bad Request for invalid types
- Add tests for type validation

Resolves #45

feat(search): implement fuzzy matching for entity names

Implement FuzzyWuzzy-based fuzzy matching for entity search,
allowing users to find entities with partially correct names.

- Add fuzzy_threshold parameter (default 0.8)
- Support partial name matches
- Include confidence scoring in results
- Add 10 new test cases

Fixes #123
Relates to #456

fix(api): correct relationship count in entity response

The entity response was returning incorrect relationship counts
when relationships were deleted but not properly cleaned up.

- Fix relationship count calculation
- Add cleanup for orphaned relationships
- Add integration test for deletion flow

Closes #789

docs(readme): add feature matrix table

Update README with comprehensive feature matrix showing all
implemented features across all phases.

Relates to #234
```

---

## Reporting Bugs

### Bug Report Template

Use the GitHub issue template:

```markdown
## Bug Description
Clear description of the bug

## Expected Behavior
What should happen

## Actual Behavior
What actually happens

## Reproduction Steps
1. Step 1
2. Step 2
3. Step 3

## Error Message/Logs
```
Error: ...
```

## Environment
- OS: [e.g., Ubuntu 22.04]
- Python: [e.g., 3.12.0]
- Basset Version: [e.g., 2.0.0]
- Docker: [e.g., 24.0.0]

## Screenshots (if applicable)
[Screenshots or gifs]

## Possible Solution (optional)
[Suggestions for fix]
```

### Bug Severity Levels

- **Critical**: System down, data loss, security breach
- **High**: Major feature broken, significant impact
- **Medium**: Feature partially broken, workaround exists
- **Low**: Minor issue, cosmetic, edge case

---

## Suggesting Features

### Feature Request Template

```markdown
## Problem Statement
Describe the problem this solves

## Proposed Solution
Describe the desired feature

## Alternative Solutions
Other approaches considered

## Use Cases
Who benefits and how

## Additional Context
Screenshots, links, references, etc.
```

### Feature Discussion

1. **Open GitHub Discussion** before starting work
2. **Describe feature** and its benefits
3. **Wait for feedback** from maintainers
4. **Design discussion** on API and architecture
5. **Get approval** before implementing

---

## Development Tips

### Environment Variables

```bash
# Create .env for development
cat > .env.local <<EOF
DEBUG=true
LOG_LEVEL=DEBUG
NEO4J_PASSWORD=neo4jbasset
PROMETHEUS_ENABLED=true
EOF
```

### Useful Commands

```bash
# Database shell
docker exec -it neo4j_osint_db cypher-shell -u neo4j -p neo4jbasset

# View logs
docker compose logs -f basset_api

# Reset database
docker compose down -v
docker compose up -d neo4j

# Run linter
ruff check api/ --fix

# Type check
mypy api/ --ignore-missing-imports

# Run specific test
python -m pytest tests/test_file.py::TestClass::test_method -vv

# Measure code coverage
coverage run -m pytest tests/
coverage report
coverage html  # Opens htmlcov/index.html
```

### Debugging

```python
# Add debugging to code
import logging

logger = logging.getLogger(__name__)

# Debug log
logger.debug("Entity created", extra={"entity_id": entity.id})

# Or use print for quick debugging
print(f"DEBUG: entity={entity.id}, name={entity.name}")
```

---

## Questions?

- **Documentation**: See [docs/](../docs/) directory
- **API Questions**: Check [docs/API_REFERENCE.md](../docs/API_REFERENCE.md)
- **Architecture**: See [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md)
- **Issues**: Open GitHub issue with question label
- **Discussions**: Use GitHub Discussions tab

---

**Thank you for contributing!**

Last Updated: 2026-05-07
