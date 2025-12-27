"""
Pytest fixtures for Basset Hound API tests.
"""

import os
import pytest
from typing import Generator, AsyncGenerator
from unittest.mock import MagicMock, AsyncMock, patch

# Set test environment
os.environ["TESTING"] = "true"
os.environ["NEO4J_URI"] = "bolt://localhost:7687"
os.environ["NEO4J_USER"] = "neo4j"
os.environ["NEO4J_PASSWORD"] = "testpassword"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"


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
