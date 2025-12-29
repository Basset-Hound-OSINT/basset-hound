"""
Tests for graph visualization API endpoints.

This module tests the graph visualization endpoints that provide graph data
in various formats (D3.js, vis.js, Cytoscape, raw) for frontend visualization.
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


@pytest.fixture
def sample_graph_data():
    """Sample graph data for testing."""
    return {
        "nodes": [
            {
                "id": "entity-1",
                "label": "John Doe",
                "type": "Person",
                "properties": {
                    "profile": {
                        "profile": {
                            "first_name": "John",
                            "last_name": "Doe"
                        }
                    },
                    "created_at": "2024-01-01T00:00:00"
                }
            },
            {
                "id": "entity-2",
                "label": "Jane Smith",
                "type": "Person",
                "properties": {
                    "profile": {
                        "profile": {
                            "first_name": "Jane",
                            "last_name": "Smith"
                        }
                    },
                    "created_at": "2024-01-02T00:00:00"
                }
            },
            {
                "id": "entity-3",
                "label": "Bob Johnson",
                "type": "Person",
                "properties": {
                    "profile": {
                        "profile": {
                            "first_name": "Bob",
                            "last_name": "Johnson"
                        }
                    },
                    "created_at": "2024-01-03T00:00:00"
                }
            }
        ],
        "edges": [
            {
                "source": "entity-1",
                "target": "entity-2",
                "type": "WORKS_WITH",
                "properties": {
                    "confidence": "high",
                    "source": "LinkedIn"
                }
            },
            {
                "source": "entity-2",
                "target": "entity-3",
                "type": "FRIEND",
                "properties": {
                    "confidence": "medium"
                }
            }
        ]
    }


@pytest.fixture
def mock_neo4j_with_graph(mock_neo4j_handler, sample_graph_data):
    """Mock Neo4j handler with graph data."""
    # Mock driver session
    mock_session = MagicMock()
    mock_neo4j_handler.driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
    mock_neo4j_handler.driver.session.return_value.__exit__ = MagicMock(return_value=None)

    # Mock query results for entities
    mock_records = [
        {
            "id": "entity-1",
            "profile": {
                "profile": {"first_name": "John", "last_name": "Doe"},
                "Tagged People": {
                    "tagged_people": ["entity-2"],
                    "relationship_types": {"entity-2": "WORKS_WITH"},
                    "relationship_properties": {
                        "entity-2": {"confidence": "high", "source": "LinkedIn"}
                    }
                }
            },
            "created_at": "2024-01-01T00:00:00"
        },
        {
            "id": "entity-2",
            "profile": {
                "profile": {"first_name": "Jane", "last_name": "Smith"},
                "Tagged People": {
                    "tagged_people": ["entity-3"],
                    "relationship_types": {"entity-3": "FRIEND"},
                    "relationship_properties": {
                        "entity-3": {"confidence": "medium"}
                    }
                }
            },
            "created_at": "2024-01-02T00:00:00"
        },
        {
            "id": "entity-3",
            "profile": {
                "profile": {"first_name": "Bob", "last_name": "Johnson"},
                "Tagged People": {}
            },
            "created_at": "2024-01-03T00:00:00"
        }
    ]

    mock_session.run.return_value = mock_records

    # Mock get_person for entity lookup
    def mock_get_person(project, entity_id):
        for record in mock_records:
            if record["id"] == entity_id:
                return record
        return None

    mock_neo4j_handler.get_person.side_effect = mock_get_person

    # Mock get_clusters for cluster queries
    mock_neo4j_handler.get_clusters.return_value = {
        "cluster_count": 1,
        "clusters": [
            {
                "cluster_id": "entity-1",
                "size": 3,
                "entity_ids": ["entity-1", "entity-2", "entity-3"],
                "entities": mock_records,
                "internal_edges": 2,
                "is_isolated": False
            }
        ]
    }

    return mock_neo4j_handler


class TestProjectGraph:
    """Tests for full project graph endpoint."""

    def test_get_project_graph_raw(self, mock_neo4j_with_graph):
        """Test getting project graph in raw format."""
        client = get_test_client(mock_neo4j_with_graph)

        response = client.get("/api/v1/projects/test_project/graph")

        assert response.status_code == 200
        data = response.json()

        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) == 3
        assert len(data["edges"]) == 2

        # Verify node structure
        node = data["nodes"][0]
        assert "id" in node
        assert "label" in node
        assert "type" in node
        assert "properties" in node

        # Verify edge structure
        edge = data["edges"][0]
        assert "source" in edge
        assert "target" in edge
        assert "type" in edge
        assert "properties" in edge

    def test_get_project_graph_d3(self, mock_neo4j_with_graph):
        """Test getting project graph in D3.js format."""
        client = get_test_client(mock_neo4j_with_graph)

        response = client.get("/api/v1/projects/test_project/graph?format=d3")

        assert response.status_code == 200
        data = response.json()

        # D3 format uses 'links' instead of 'edges'
        assert "nodes" in data
        assert "links" in data
        assert len(data["nodes"]) == 3
        assert len(data["links"]) == 2

        # Verify link structure
        link = data["links"][0]
        assert "source" in link
        assert "target" in link
        assert "type" in link

    def test_get_project_graph_vis(self, mock_neo4j_with_graph):
        """Test getting project graph in vis.js format."""
        client = get_test_client(mock_neo4j_with_graph)

        response = client.get("/api/v1/projects/test_project/graph?format=vis")

        assert response.status_code == 200
        data = response.json()

        assert "nodes" in data
        assert "edges" in data

        # vis.js specific fields
        node = data["nodes"][0]
        assert "id" in node
        assert "label" in node
        assert "group" in node
        assert "title" in node

        edge = data["edges"][0]
        assert "from" in edge
        assert "to" in edge
        assert "arrows" in edge
        assert edge["arrows"] == "to"

    def test_get_project_graph_cytoscape(self, mock_neo4j_with_graph):
        """Test getting project graph in Cytoscape.js format."""
        client = get_test_client(mock_neo4j_with_graph)

        response = client.get("/api/v1/projects/test_project/graph?format=cytoscape")

        assert response.status_code == 200
        data = response.json()

        assert "elements" in data
        assert "nodes" in data["elements"]
        assert "edges" in data["elements"]

        # Cytoscape format has nested data objects
        node = data["elements"]["nodes"][0]
        assert "data" in node
        assert "id" in node["data"]
        assert "label" in node["data"]

        edge = data["elements"]["edges"][0]
        assert "data" in edge
        assert "source" in edge["data"]
        assert "target" in edge["data"]

    def test_get_project_graph_exclude_orphans(self, mock_neo4j_with_graph):
        """Test excluding orphan nodes from graph."""
        client = get_test_client(mock_neo4j_with_graph)

        response = client.get(
            "/api/v1/projects/test_project/graph?include_orphans=false"
        )

        assert response.status_code == 200
        data = response.json()

        # All nodes in our test data have connections, so count should be same
        assert len(data["nodes"]) == 3


class TestEntitySubgraph:
    """Tests for entity-centered subgraph endpoint."""

    def test_get_entity_subgraph_raw(self, mock_neo4j_with_graph):
        """Test getting entity subgraph in raw format."""
        client = get_test_client(mock_neo4j_with_graph)

        response = client.get(
            "/api/v1/projects/test_project/graph/entity/entity-1"
        )

        assert response.status_code == 200
        data = response.json()

        assert "nodes" in data
        assert "edges" in data
        assert "center_entity" in data
        assert "depth" in data

        assert data["center_entity"] == "entity-1"
        assert data["depth"] == 2

        # Should include at least the center entity
        node_ids = [n["id"] for n in data["nodes"]]
        assert "entity-1" in node_ids

    def test_get_entity_subgraph_with_depth(self, mock_neo4j_with_graph):
        """Test getting entity subgraph with specific depth."""
        client = get_test_client(mock_neo4j_with_graph)

        response = client.get(
            "/api/v1/projects/test_project/graph/entity/entity-1?depth=1"
        )

        assert response.status_code == 200
        data = response.json()

        assert data["depth"] == 1
        assert "nodes" in data
        assert "edges" in data

    def test_get_entity_subgraph_d3(self, mock_neo4j_with_graph):
        """Test getting entity subgraph in D3 format."""
        client = get_test_client(mock_neo4j_with_graph)

        response = client.get(
            "/api/v1/projects/test_project/graph/entity/entity-1?format=d3"
        )

        assert response.status_code == 200
        data = response.json()

        assert "nodes" in data
        assert "links" in data
        assert "center_entity" in data
        assert data["center_entity"] == "entity-1"

    def test_get_entity_subgraph_not_found(self, mock_neo4j_with_graph):
        """Test getting subgraph for non-existent entity."""
        client = get_test_client(mock_neo4j_with_graph)

        response = client.get(
            "/api/v1/projects/test_project/graph/entity/nonexistent"
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_entity_subgraph_depth_validation(self, mock_neo4j_with_graph):
        """Test depth parameter validation."""
        client = get_test_client(mock_neo4j_with_graph)

        # Depth too high
        response = client.get(
            "/api/v1/projects/test_project/graph/entity/entity-1?depth=20"
        )
        assert response.status_code == 422  # Validation error

        # Depth too low
        response = client.get(
            "/api/v1/projects/test_project/graph/entity/entity-1?depth=0"
        )
        assert response.status_code == 422  # Validation error


class TestClusterGraph:
    """Tests for cluster graph endpoint."""

    def test_get_cluster_graph_raw(self, mock_neo4j_with_graph):
        """Test getting cluster graph in raw format."""
        client = get_test_client(mock_neo4j_with_graph)

        response = client.get(
            "/api/v1/projects/test_project/graph/cluster/entity-1"
        )

        assert response.status_code == 200
        data = response.json()

        assert "nodes" in data
        assert "edges" in data
        assert "cluster_id" in data
        assert "cluster_size" in data
        assert "is_isolated" in data

        assert data["cluster_id"] == "entity-1"
        assert data["cluster_size"] == 3
        assert data["is_isolated"] is False

    def test_get_cluster_graph_d3(self, mock_neo4j_with_graph):
        """Test getting cluster graph in D3 format."""
        client = get_test_client(mock_neo4j_with_graph)

        response = client.get(
            "/api/v1/projects/test_project/graph/cluster/entity-1?format=d3"
        )

        assert response.status_code == 200
        data = response.json()

        assert "nodes" in data
        assert "links" in data
        assert "cluster_id" in data
        assert data["cluster_id"] == "entity-1"

    def test_get_cluster_graph_vis(self, mock_neo4j_with_graph):
        """Test getting cluster graph in vis.js format."""
        client = get_test_client(mock_neo4j_with_graph)

        response = client.get(
            "/api/v1/projects/test_project/graph/cluster/entity-1?format=vis"
        )

        assert response.status_code == 200
        data = response.json()

        assert "nodes" in data
        assert "edges" in data
        assert "cluster_id" in data

        # Check vis.js specific format
        if len(data["edges"]) > 0:
            assert "from" in data["edges"][0]
            assert "to" in data["edges"][0]

    def test_get_cluster_graph_cytoscape(self, mock_neo4j_with_graph):
        """Test getting cluster graph in Cytoscape format."""
        client = get_test_client(mock_neo4j_with_graph)

        response = client.get(
            "/api/v1/projects/test_project/graph/cluster/entity-1?format=cytoscape"
        )

        assert response.status_code == 200
        data = response.json()

        assert "elements" in data
        assert "cluster_id" in data

    def test_get_cluster_graph_not_found(self, mock_neo4j_with_graph):
        """Test getting graph for non-existent cluster."""
        # Mock clusters to return empty
        mock_neo4j_with_graph.get_clusters.return_value = {
            "cluster_count": 0,
            "clusters": []
        }

        client = get_test_client(mock_neo4j_with_graph)

        response = client.get(
            "/api/v1/projects/test_project/graph/cluster/nonexistent"
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestGraphService:
    """Tests for the GraphService class."""

    def test_extract_display_name_from_profile(self):
        """Test display name extraction from various profile formats."""
        from api.services.graph_service import GraphService

        mock_neo4j = MagicMock()
        service = GraphService(mock_neo4j)

        # Test with first_name and last_name
        profile = {"profile": {"first_name": "John", "last_name": "Doe"}}
        name = service._extract_display_name(profile, "entity-1")
        assert name == "John Doe"

        # Test with only first_name
        profile = {"profile": {"first_name": "John"}}
        name = service._extract_display_name(profile, "entity-1")
        assert name == "John"

        # Test with full_name
        profile = {"profile": {"full_name": "John Doe"}}
        name = service._extract_display_name(profile, "entity-1")
        assert name == "John Doe"

        # Test with username
        profile = {"social": {"username": "johndoe"}}
        name = service._extract_display_name(profile, "entity-1")
        assert name == "@johndoe"

        # Test with email
        profile = {"contact": {"email": "john@example.com"}}
        name = service._extract_display_name(profile, "entity-1")
        assert name == "john"

        # Test fallback to entity ID
        profile = {}
        name = service._extract_display_name(profile, "entity-123456789")
        assert "Entity" in name
        assert "entity-12" in name

    def test_format_conversions(self, sample_graph_data):
        """Test format conversion methods."""
        from api.services.graph_service import GraphService

        mock_neo4j = MagicMock()
        service = GraphService(mock_neo4j)

        # Test D3 format
        d3_data = service.format_for_d3(sample_graph_data)
        assert "nodes" in d3_data
        assert "links" in d3_data
        assert len(d3_data["nodes"]) == 3
        assert len(d3_data["links"]) == 2

        # Test vis.js format
        vis_data = service.format_for_vis(sample_graph_data)
        assert "nodes" in vis_data
        assert "edges" in vis_data
        assert "group" in vis_data["nodes"][0]
        assert "from" in vis_data["edges"][0]
        assert "to" in vis_data["edges"][0]

        # Test Cytoscape format
        cyto_data = service.format_for_cytoscape(sample_graph_data)
        assert "elements" in cyto_data
        assert "nodes" in cyto_data["elements"]
        assert "edges" in cyto_data["elements"]
        assert "data" in cyto_data["elements"]["nodes"][0]

    def test_metadata_preservation(self, sample_graph_data):
        """Test that metadata is preserved in format conversions."""
        from api.services.graph_service import GraphService

        mock_neo4j = MagicMock()
        service = GraphService(mock_neo4j)

        # Add metadata to graph data
        graph_with_meta = {
            **sample_graph_data,
            "center_entity": "entity-1",
            "depth": 2,
            "cluster_id": "cluster-1"
        }

        # Test D3 format preserves metadata
        d3_data = service.format_for_d3(graph_with_meta)
        assert d3_data["center_entity"] == "entity-1"
        assert d3_data["depth"] == 2
        assert d3_data["cluster_id"] == "cluster-1"

        # Test vis.js format preserves metadata
        vis_data = service.format_for_vis(graph_with_meta)
        assert vis_data["center_entity"] == "entity-1"

        # Test Cytoscape format preserves metadata
        cyto_data = service.format_for_cytoscape(graph_with_meta)
        assert cyto_data["center_entity"] == "entity-1"


class TestErrorHandling:
    """Tests for error handling in graph endpoints."""

    def test_graph_service_error(self, mock_neo4j_handler):
        """Test handling of service errors."""
        # Mock session to raise an exception
        mock_neo4j_handler.driver.session.side_effect = Exception("Database error")

        client = get_test_client(mock_neo4j_handler)

        response = client.get("/api/v1/projects/test_project/graph")

        assert response.status_code == 500
        assert "error" in response.json()["detail"].lower()

    def test_invalid_format_parameter(self, mock_neo4j_with_graph):
        """Test handling of invalid format parameter."""
        client = get_test_client(mock_neo4j_with_graph)

        response = client.get(
            "/api/v1/projects/test_project/graph?format=invalid"
        )

        # FastAPI should return 422 for invalid enum value
        assert response.status_code == 422
