"""
Tests for project API endpoints.
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


class TestProjectEndpoints:
    """Tests for project CRUD endpoints."""

    def test_list_projects(self, mock_neo4j_handler):
        """Test listing all projects."""
        client = get_test_client(mock_neo4j_handler)

        response = client.get("/api/v1/projects/")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["name"] == "Test Project"

    def test_create_project(self, mock_neo4j_handler):
        """Test creating a new project."""
        client = get_test_client(mock_neo4j_handler)

        response = client.post(
            "/api/v1/projects/",
            json={"name": "New Project"}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Project"
        assert "id" in data

    def test_create_project_empty_name(self, mock_neo4j_handler):
        """Test creating a project with empty name fails."""
        client = get_test_client(mock_neo4j_handler)

        response = client.post(
            "/api/v1/projects/",
            json={"name": ""}
        )

        assert response.status_code == 422

    def test_get_project(self, mock_neo4j_handler):
        """Test getting a specific project."""
        client = get_test_client(mock_neo4j_handler)

        response = client.get("/api/v1/projects/test_project")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Project"
        assert data["safe_name"] == "test_project"

    def test_get_project_not_found(self, mock_neo4j_handler):
        """Test getting a non-existent project."""
        mock_neo4j_handler.get_project.return_value = None
        client = get_test_client(mock_neo4j_handler)

        response = client.get("/api/v1/projects/nonexistent")

        assert response.status_code == 404

    def test_delete_project(self, mock_neo4j_handler):
        """Test deleting a project."""
        client = get_test_client(mock_neo4j_handler)

        response = client.delete("/api/v1/projects/test_project")

        assert response.status_code == 204

    def test_delete_project_not_found(self, mock_neo4j_handler):
        """Test deleting a non-existent project."""
        mock_neo4j_handler.delete_project.return_value = False
        client = get_test_client(mock_neo4j_handler)

        response = client.delete("/api/v1/projects/nonexistent")

        assert response.status_code == 404

    def test_set_current_project(self, mock_neo4j_handler):
        """Test setting the current project."""
        client = get_test_client(mock_neo4j_handler)

        response = client.post(
            "/api/v1/projects/current",
            json={"safe_name": "test_project"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "project_id" in data

    def test_download_project(self, mock_neo4j_handler):
        """Test downloading a project as JSON."""
        client = get_test_client(mock_neo4j_handler)

        response = client.get("/api/v1/projects/test_project/download")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
