"""
Tests for entity API endpoints.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


def get_test_client(mock_handler):
    """Create a test client with mocked dependencies."""
    from api.main import app
    from api.dependencies import get_neo4j_handler

    app.dependency_overrides[get_neo4j_handler] = lambda: mock_handler
    return TestClient(app)


class TestEntityEndpoints:
    """Tests for entity CRUD endpoints."""

    def test_list_entities(self, mock_neo4j_handler):
        """Test listing all entities in a project."""
        client = get_test_client(mock_neo4j_handler)

        response = client.get("/api/v1/projects/test_project/entities/")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1

    def test_list_entities_project_not_found(self, mock_neo4j_handler):
        """Test listing entities for non-existent project."""
        mock_neo4j_handler.get_project.return_value = None
        client = get_test_client(mock_neo4j_handler)

        response = client.get("/api/v1/projects/nonexistent/entities/")

        assert response.status_code == 404

    def test_create_entity(self, mock_neo4j_handler):
        """Test creating a new entity."""
        client = get_test_client(mock_neo4j_handler)

        response = client.post(
            "/api/v1/projects/test_project/entities/",
            json={
                "profile": {
                    "core": {
                        "name": [{"first_name": "Jane", "last_name": "Smith"}]
                    }
                }
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert "id" in data

    def test_create_entity_empty_profile(self, mock_neo4j_handler):
        """Test creating an entity with empty profile."""
        client = get_test_client(mock_neo4j_handler)

        response = client.post(
            "/api/v1/projects/test_project/entities/",
            json={"profile": {}}
        )

        assert response.status_code == 201

    def test_get_entity(self, mock_neo4j_handler):
        """Test getting a specific entity."""
        client = get_test_client(mock_neo4j_handler)

        response = client.get("/api/v1/projects/test_project/entities/test-person-id")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test-person-id"
        assert "profile" in data

    def test_get_entity_not_found(self, mock_neo4j_handler):
        """Test getting a non-existent entity."""
        mock_neo4j_handler.get_person.return_value = None
        client = get_test_client(mock_neo4j_handler)

        response = client.get("/api/v1/projects/test_project/entities/nonexistent")

        assert response.status_code == 404

    def test_update_entity(self, mock_neo4j_handler):
        """Test updating an entity."""
        client = get_test_client(mock_neo4j_handler)

        response = client.put(
            "/api/v1/projects/test_project/entities/test-person-id",
            json={
                "profile": {
                    "core": {
                        "email": ["updated@example.com"]
                    }
                }
            }
        )

        assert response.status_code == 200

    def test_delete_entity(self, mock_neo4j_handler):
        """Test deleting an entity."""
        client = get_test_client(mock_neo4j_handler)

        response = client.delete("/api/v1/projects/test_project/entities/test-person-id")

        assert response.status_code == 204

    def test_delete_entity_not_found(self, mock_neo4j_handler):
        """Test deleting a non-existent entity."""
        mock_neo4j_handler.delete_person.return_value = False
        client = get_test_client(mock_neo4j_handler)

        response = client.delete("/api/v1/projects/test_project/entities/nonexistent")

        assert response.status_code == 404


class TestRelationshipEndpoints:
    """Tests for relationship/tagging endpoints."""

    def test_get_relationships(self, mock_neo4j_handler):
        """Test getting entity relationships."""
        client = get_test_client(mock_neo4j_handler)

        response = client.get(
            "/api/v1/projects/test_project/entities/test-person-id/relationships/"
        )

        assert response.status_code == 200
        data = response.json()
        assert "tagged_people" in data
        assert "transitive_relationships" in data

    def test_update_relationships(self, mock_neo4j_handler):
        """Test updating entity relationships."""
        client = get_test_client(mock_neo4j_handler)

        response = client.put(
            "/api/v1/projects/test_project/entities/test-person-id/relationships/",
            json={
                "tagged_ids": ["other-person-id"],
                "transitive_relationships": []
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_tag_entity(self, mock_neo4j_handler):
        """Test tagging another entity."""
        client = get_test_client(mock_neo4j_handler)

        response = client.post(
            "/api/v1/projects/test_project/entities/test-person-id/relationships/tag/other-person-id"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_untag_entity(self, mock_neo4j_handler):
        """Test removing a tag from entity."""
        client = get_test_client(mock_neo4j_handler)

        response = client.delete(
            "/api/v1/projects/test_project/entities/test-person-id/relationships/tag/other-person-id"
        )

        assert response.status_code == 200
