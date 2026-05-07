"""
Pytest fixtures for Basset Hound API tests.
"""

import os
import pytest
from typing import Generator, AsyncGenerator
from unittest.mock import MagicMock, AsyncMock, patch

# Set test environment
os.environ["TESTING"] = "true"
os.environ["NEO4J_URI"] = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
os.environ["NEO4J_USER"] = os.environ.get("NEO4J_USER", "neo4j")
os.environ["NEO4J_PASSWORD"] = os.environ.get("NEO4J_PASSWORD", "testpassword")
os.environ["SECRET_KEY"] = os.environ.get("SECRET_KEY", "test-secret-key-for-testing-only")
os.environ["REDIS_URL"] = os.environ.get("REDIS_URL", "redis://localhost:6379")
os.environ["API_URL"] = os.environ.get("API_URL", "http://localhost:8000")


@pytest.fixture
def mock_neo4j_handler():
    """Create a mock Neo4j handler for testing."""
    handler = MagicMock()

    # Mock project methods
    handler.get_all_projects.return_value = [
        {
            "id": "test-project-id",
            "name": "Test Project",
            "safe_name": "test_project",
            "created_at": "2024-01-15T10:30:00"
        }
    ]

    handler.get_project.return_value = {
        "id": "test-project-id",
        "name": "Test Project",
        "safe_name": "test_project",
        "created_at": "2024-01-15T10:30:00",
        "people": []
    }

    handler.create_project.return_value = {
        "id": "new-project-id",
        "name": "New Project",
        "safe_name": "new_project",
        "created_at": "2024-01-15T10:30:00"
    }

    handler.delete_project.return_value = True

    # Mock person methods
    handler.get_all_people.return_value = [
        {
            "id": "test-person-id",
            "created_at": "2024-01-15T10:30:00",
            "profile": {
                "core": {
                    "name": [{"first_name": "John", "last_name": "Doe"}]
                }
            }
        }
    ]

    handler.get_person.return_value = {
        "id": "test-person-id",
        "created_at": "2024-01-15T10:30:00",
        "profile": {
            "core": {
                "name": [{"first_name": "John", "last_name": "Doe"}],
                "email": ["john@example.com"]
            },
            "Tagged People": {
                "tagged_people": [],
                "transitive_relationships": []
            }
        }
    }

    handler.create_person.return_value = {
        "id": "new-person-id",
        "created_at": "2024-01-15T10:30:00",
        "profile": {}
    }

    handler.update_person.return_value = {
        "id": "test-person-id",
        "created_at": "2024-01-15T10:30:00",
        "profile": {"updated": True}
    }

    handler.delete_person.return_value = True

    # Mock file methods
    handler.get_file.return_value = {
        "id": "test-file-id",
        "name": "test.txt",
        "path": "test-file-id_test.txt"
    }

    handler.delete_file.return_value = True

    # Mock report methods
    handler.add_report_to_person.return_value = None
    handler.remove_report_from_person.return_value = None

    # Mock schema methods
    handler.setup_schema_from_config.return_value = None

    return handler


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    return {
        "sections": [
            {
                "id": "core",
                "name": "Personal Information",
                "fields": [
                    {"id": "name", "type": "string", "multiple": True},
                    {"id": "email", "type": "email", "multiple": True}
                ]
            },
            {
                "id": "social",
                "name": "Social Media",
                "fields": [
                    {"id": "twitter", "type": "string"},
                    {"id": "linkedin", "type": "url"}
                ]
            }
        ]
    }


@pytest.fixture
def sample_project():
    """Sample project data for testing."""
    return {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "name": "Test Project",
        "safe_name": "test_project",
        "created_at": "2024-01-15T10:30:00"
    }


@pytest.fixture
def sample_entity():
    """Sample entity data for testing."""
    return {
        "id": "550e8400-e29b-41d4-a716-446655440001",
        "created_at": "2024-01-15T10:30:00",
        "profile": {
            "core": {
                "name": [{"first_name": "John", "last_name": "Doe"}],
                "email": ["john.doe@example.com"]
            },
            "social": {
                "twitter": "@johndoe",
                "linkedin": "https://linkedin.com/in/johndoe"
            }
        }
    }


@pytest.fixture
def sample_report():
    """Sample report data for testing."""
    return {
        "name": "sherlock_20240115_abc12345.md",
        "path": "sherlock_20240115_abc12345.md",
        "tool": "sherlock",
        "created_at": "2024-01-15T10:30:00",
        "id": "abc12345"
    }


# Deployment test fixtures

@pytest.fixture
def api_base_url():
    """Get the API base URL for deployment tests."""
    return os.environ.get("API_URL", "http://localhost:8000")


@pytest.fixture
def neo4j_config():
    """Get Neo4j configuration for deployment tests."""
    return {
        "uri": os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        "user": os.environ.get("NEO4J_USER", "neo4j"),
        "password": os.environ.get("NEO4J_PASSWORD", "testpassword"),
    }


@pytest.fixture
def redis_config():
    """Get Redis configuration for deployment tests."""
    return {
        "url": os.environ.get("REDIS_URL", "redis://localhost:6379"),
        "host": os.environ.get("REDIS_HOST", "localhost"),
        "port": int(os.environ.get("REDIS_PORT", "6379")),
    }


@pytest.fixture
def deployment_environment():
    """Check if deployment environment is available."""
    return {
        "api_running": _check_api_running(),
        "neo4j_running": _check_neo4j_running(),
        "redis_running": _check_redis_running(),
    }


def _check_api_running() -> bool:
    """Check if the API is running."""
    try:
        import httpx
        api_url = os.environ.get("API_URL", "http://localhost:8000")
        client = httpx.Client(timeout=2.0)
        response = client.get(f"{api_url}/health")
        client.close()
        return response.status_code == 200
    except Exception:
        return False


def _check_neo4j_running() -> bool:
    """Check if Neo4j is running."""
    try:
        from neo4j import GraphDatabase
        neo4j_uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
        neo4j_user = os.environ.get("NEO4J_USER", "neo4j")
        neo4j_password = os.environ.get("NEO4J_PASSWORD", "testpassword")
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        driver.verify_connectivity()
        driver.close()
        return True
    except Exception:
        return False


def _check_redis_running() -> bool:
    """Check if Redis is running."""
    try:
        import redis
        redis_host = os.environ.get("REDIS_HOST", "localhost")
        redis_port = int(os.environ.get("REDIS_PORT", "6379"))
        r = redis.Redis(host=redis_host, port=redis_port)
        r.ping()
        return True
    except Exception:
        return False


# Markers for deployment tests

def pytest_configure(config):
    """Register custom markers for deployment tests."""
    config.addinivalue_line(
        "markers", "deployment: mark test as a deployment test (requires running services)"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
