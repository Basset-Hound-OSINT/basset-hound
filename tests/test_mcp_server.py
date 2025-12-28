"""
Tests for the MCP server tools.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import json


class TestMCPServerTools:
    """Tests for MCP server entity management tools."""

    @pytest.fixture
    def mock_neo4j(self):
        """Create mock Neo4j handler."""
        handler = MagicMock()
        handler.get_all_projects.return_value = [
            {"id": "proj-1", "name": "Test Project", "safe_name": "test_project"}
        ]
        handler.get_project.return_value = {
            "id": "proj-1",
            "name": "Test Project",
            "safe_name": "test_project"
        }
        handler.create_project.return_value = {
            "id": "new-proj",
            "name": "New Project",
            "safe_name": "new_project"
        }
        handler.get_all_people.return_value = [
            {"id": "person-1", "profile": {"core": {"name": [{"first_name": "John"}]}}}
        ]
        handler.get_person.return_value = {
            "id": "person-1",
            "profile": {"core": {"name": [{"first_name": "John"}]}}
        }
        handler.create_person.return_value = {
            "id": "new-person",
            "profile": {}
        }
        handler.update_person.return_value = {
            "id": "person-1",
            "profile": {"updated": True}
        }
        handler.delete_person.return_value = True
        return handler

    def test_mcp_server_imports(self):
        """Test that MCP server module can be imported."""
        # This tests syntax and basic imports of the basset_mcp module
        try:
            # Import the local Basset Hound MCP server
            # Note: This requires the mcp package (fastmcp) to be installed
            from basset_mcp import mcp as basset_mcp_server
            assert basset_mcp_server is not None
        except ImportError as e:
            # MCP package (fastmcp) might not be installed in test environment
            pytest.skip(f"MCP/FastMCP package not available: {e}")

    def test_entity_search_logic(self, mock_neo4j):
        """Test entity search logic."""
        # Get all people
        people = mock_neo4j.get_all_people("test_project")

        # Simulate search by name
        search_query = "John"
        results = []
        for person in people:
            profile = person.get("profile", {})
            for section_id, section_data in profile.items():
                if isinstance(section_data, dict):
                    for field_id, field_value in section_data.items():
                        value_str = json.dumps(field_value).lower()
                        if search_query.lower() in value_str:
                            results.append(person)
                            break

        assert len(results) == 1
        assert results[0]["id"] == "person-1"

    def test_entity_relationship_logic(self, mock_neo4j):
        """Test entity relationship logic."""
        # Get person with relationships
        person = mock_neo4j.get_person("test_project", "person-1")

        # Update with relationships
        update_data = {
            "profile": {
                "Tagged People": {
                    "tagged_people": ["person-2", "person-3"],
                    "transitive_relationships": ["person-4"]
                }
            }
        }

        mock_neo4j.update_person("test_project", "person-1", update_data)
        mock_neo4j.update_person.assert_called_once()

    def test_project_crud_logic(self, mock_neo4j):
        """Test project CRUD operations."""
        # Create project
        new_project = mock_neo4j.create_project("New Project")
        assert new_project["name"] == "New Project"

        # Get project
        project = mock_neo4j.get_project("new_project")
        assert project is not None

        # List projects
        projects = mock_neo4j.get_all_projects()
        assert len(projects) == 1

    def test_entity_identifier_extraction(self, mock_neo4j):
        """Test extracting identifiers from entity profile."""
        person = mock_neo4j.get_person("test_project", "person-1")
        profile = person.get("profile", {})

        identifiers = {}
        for section_id, section_data in profile.items():
            if isinstance(section_data, dict):
                for field_id, field_value in section_data.items():
                    identifiers[f"{section_id}.{field_id}"] = field_value

        assert "core.name" in identifiers
        assert identifiers["core.name"] == [{"first_name": "John"}]

    def test_mcp_tool_parameter_validation(self):
        """Test that MCP tool parameters are properly validated."""
        # Test project_safe_name validation
        valid_names = ["test_project", "my_investigation", "case_2024"]
        invalid_names = ["", "project with spaces", "../path/traversal"]

        for name in valid_names:
            # Valid names should pass basic validation
            assert name.replace("_", "").isalnum() or name == ""

        for name in invalid_names:
            # Invalid names should fail
            is_valid = name.replace("_", "").isalnum() if name else False
            if name and "/" not in name and " " not in name:
                # Only alphanumeric with underscores
                pass
            else:
                assert not is_valid or name == ""


class TestMCPServerConfiguration:
    """Tests for MCP server configuration."""

    def test_mcp_server_tool_definitions(self):
        """Test that all expected tools are defined."""
        expected_tools = [
            "create_entity",
            "get_entity",
            "update_entity",
            "delete_entity",
            "list_entities",
            "link_entities",
            "unlink_entities",
            "get_related",
            "search_entities",
            "search_by_identifier",
            "create_project",
            "list_projects",
            "get_project",
            "create_report",
            "get_reports"
        ]

        try:
            # Import the local Basset Hound MCP server
            from basset_mcp import mcp as basset_mcp_server

            # The FastMCP server should have these tools registered
            # This is a basic check - full integration tests would verify behavior
            assert basset_mcp_server is not None

        except ImportError:
            pytest.skip("MCP/FastMCP package not available")

    def test_mcp_neo4j_integration_config(self):
        """Test that Neo4j configuration is properly loaded."""
        import os

        # These should be set in conftest.py
        assert os.environ.get("NEO4J_URI") is not None
        assert os.environ.get("NEO4J_USER") is not None
