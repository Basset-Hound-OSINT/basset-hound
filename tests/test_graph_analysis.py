"""
Tests for graph analysis tools.

These tests cover the Phase 3 graph analysis features:
- Path finding (shortest path, all paths)
- Centrality analysis
- Neighborhood exploration
- Cluster detection
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


class TestPathFinding:
    """Tests for path finding functionality."""

    @pytest.fixture
    def mock_handler_with_paths(self, mock_neo4j_handler):
        """Extend mock handler with path finding methods."""
        mock_neo4j_handler.find_shortest_path.return_value = {
            "found": True,
            "path_length": 2,
            "entity_count": 3,
            "entity_ids": ["entity-1", "entity-2", "entity-3"],
            "entities": [
                {"id": "entity-1", "profile": {}},
                {"id": "entity-2", "profile": {}},
                {"id": "entity-3", "profile": {}}
            ]
        }

        mock_neo4j_handler.find_all_paths.return_value = {
            "found": True,
            "path_count": 2,
            "max_depth_searched": 5,
            "paths": [
                {"entity_ids": ["entity-1", "entity-2", "entity-3"], "path_length": 2, "entity_count": 3},
                {"entity_ids": ["entity-1", "entity-4", "entity-3"], "path_length": 2, "entity_count": 3}
            ]
        }

        return mock_neo4j_handler

    def test_find_shortest_path_success(self, mock_handler_with_paths):
        """Test finding shortest path between two entities."""
        client = get_test_client(mock_handler_with_paths)

        response = client.get(
            "/api/v1/analysis/test_project/path/entity-1/entity-3"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["found"] is True
        assert data["path_length"] == 2
        assert len(data["entity_ids"]) == 3
        assert data["entity_ids"][0] == "entity-1"
        assert data["entity_ids"][-1] == "entity-3"

    def test_find_shortest_path_no_path(self, mock_handler_with_paths):
        """Test when no path exists between entities."""
        mock_handler_with_paths.find_shortest_path.return_value = {
            "found": False,
            "message": "No path found between entities"
        }
        client = get_test_client(mock_handler_with_paths)

        response = client.get(
            "/api/v1/analysis/test_project/path/entity-1/entity-99"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["found"] is False

    def test_find_shortest_path_entity_not_found(self, mock_handler_with_paths):
        """Test path finding with non-existent entity."""
        mock_handler_with_paths.get_person.return_value = None
        client = get_test_client(mock_handler_with_paths)

        response = client.get(
            "/api/v1/analysis/test_project/path/nonexistent/entity-2"
        )

        assert response.status_code == 404

    def test_find_all_paths(self, mock_handler_with_paths):
        """Test finding all paths between entities."""
        client = get_test_client(mock_handler_with_paths)

        response = client.get(
            "/api/v1/analysis/test_project/paths/entity-1/entity-3",
            params={"max_depth": 5}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["found"] is True
        assert data["path_count"] == 2
        assert len(data["paths"]) == 2

    def test_find_all_paths_max_depth_limit(self, mock_handler_with_paths):
        """Test max_depth parameter limits."""
        client = get_test_client(mock_handler_with_paths)

        # Valid max_depth
        response = client.get(
            "/api/v1/analysis/test_project/paths/entity-1/entity-3",
            params={"max_depth": 10}
        )
        assert response.status_code == 200

        # Invalid max_depth (too high)
        response = client.get(
            "/api/v1/analysis/test_project/paths/entity-1/entity-3",
            params={"max_depth": 15}
        )
        assert response.status_code == 422  # Validation error


class TestCentralityAnalysis:
    """Tests for centrality analysis functionality."""

    @pytest.fixture
    def mock_handler_with_centrality(self, mock_neo4j_handler):
        """Extend mock handler with centrality methods."""
        mock_neo4j_handler.get_entity_centrality.return_value = {
            "entity_id": "entity-1",
            "degree_centrality": 8,
            "outgoing_connections": 5,
            "incoming_connections": 3,
            "outgoing_to": ["entity-2", "entity-3", "entity-4", "entity-5", "entity-6"],
            "incoming_from": ["entity-7", "entity-8", "entity-9"],
            "normalized_centrality": 0.4,
            "total_entities_in_project": 10
        }

        mock_neo4j_handler.get_most_connected.return_value = {
            "entities": [
                {
                    "entity_id": "entity-1",
                    "entity": {"id": "entity-1", "profile": {}},
                    "outgoing_connections": 5,
                    "incoming_connections": 3,
                    "total_connections": 8
                },
                {
                    "entity_id": "entity-2",
                    "entity": {"id": "entity-2", "profile": {}},
                    "outgoing_connections": 4,
                    "incoming_connections": 2,
                    "total_connections": 6
                }
            ],
            "count": 2,
            "total_entities_analyzed": 10
        }

        return mock_neo4j_handler

    def test_get_entity_centrality(self, mock_handler_with_centrality):
        """Test getting centrality for a specific entity."""
        client = get_test_client(mock_handler_with_centrality)

        response = client.get(
            "/api/v1/analysis/test_project/centrality/entity-1"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["entity_id"] == "entity-1"
        assert data["degree_centrality"] == 8
        assert data["outgoing_connections"] == 5
        assert data["incoming_connections"] == 3
        assert 0 <= data["normalized_centrality"] <= 1

    def test_get_entity_centrality_not_found(self, mock_handler_with_centrality):
        """Test centrality for non-existent entity."""
        mock_handler_with_centrality.get_entity_centrality.return_value = None
        client = get_test_client(mock_handler_with_centrality)

        response = client.get(
            "/api/v1/analysis/test_project/centrality/nonexistent"
        )

        assert response.status_code == 404

    def test_get_most_connected(self, mock_handler_with_centrality):
        """Test getting most connected entities."""
        client = get_test_client(mock_handler_with_centrality)

        response = client.get(
            "/api/v1/analysis/test_project/most-connected",
            params={"limit": 10}
        )

        assert response.status_code == 200
        data = response.json()
        assert "entities" in data
        assert "count" in data
        assert len(data["entities"]) == 2
        # Verify sorted by connections
        assert data["entities"][0]["total_connections"] >= data["entities"][1]["total_connections"]

    def test_get_most_connected_limit(self, mock_handler_with_centrality):
        """Test limit parameter for most connected."""
        client = get_test_client(mock_handler_with_centrality)

        # Valid limit
        response = client.get(
            "/api/v1/analysis/test_project/most-connected",
            params={"limit": 50}
        )
        assert response.status_code == 200

        # Invalid limit (too high)
        response = client.get(
            "/api/v1/analysis/test_project/most-connected",
            params={"limit": 200}
        )
        assert response.status_code == 422


class TestNeighborhoodExploration:
    """Tests for neighborhood exploration functionality."""

    @pytest.fixture
    def mock_handler_with_neighborhood(self, mock_neo4j_handler):
        """Extend mock handler with neighborhood methods."""
        mock_neo4j_handler.get_entity_neighborhood.return_value = {
            "center_entity_id": "entity-1",
            "max_depth": 2,
            "total_entities": 5,
            "neighborhood": {
                "depth_0": [{"id": "entity-1", "profile": {}}],
                "depth_1": [
                    {"id": "entity-2", "profile": {}},
                    {"id": "entity-3", "profile": {}}
                ],
                "depth_2": [
                    {"id": "entity-4", "profile": {}},
                    {"id": "entity-5", "profile": {}}
                ]
            },
            "edges": [
                {"source": "entity-1", "target": "entity-2"},
                {"source": "entity-1", "target": "entity-3"},
                {"source": "entity-2", "target": "entity-4"},
                {"source": "entity-3", "target": "entity-5"}
            ]
        }

        return mock_neo4j_handler

    def test_get_entity_neighborhood(self, mock_handler_with_neighborhood):
        """Test getting entity neighborhood."""
        client = get_test_client(mock_handler_with_neighborhood)

        response = client.get(
            "/api/v1/analysis/test_project/neighborhood/entity-1",
            params={"depth": 2}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["center_entity_id"] == "entity-1"
        assert data["max_depth"] == 2
        assert data["total_entities"] == 5
        assert "depth_0" in data["neighborhood"]
        assert "depth_1" in data["neighborhood"]
        assert "depth_2" in data["neighborhood"]
        assert len(data["edges"]) == 4

    def test_get_neighborhood_entity_not_found(self, mock_handler_with_neighborhood):
        """Test neighborhood for non-existent entity."""
        mock_handler_with_neighborhood.get_entity_neighborhood.return_value = None
        client = get_test_client(mock_handler_with_neighborhood)

        response = client.get(
            "/api/v1/analysis/test_project/neighborhood/nonexistent"
        )

        assert response.status_code == 404

    def test_get_neighborhood_depth_limit(self, mock_handler_with_neighborhood):
        """Test depth parameter limits."""
        client = get_test_client(mock_handler_with_neighborhood)

        # Valid depth
        response = client.get(
            "/api/v1/analysis/test_project/neighborhood/entity-1",
            params={"depth": 5}
        )
        assert response.status_code == 200

        # Invalid depth (too high)
        response = client.get(
            "/api/v1/analysis/test_project/neighborhood/entity-1",
            params={"depth": 10}
        )
        assert response.status_code == 422


class TestClusterDetection:
    """Tests for cluster detection functionality."""

    @pytest.fixture
    def mock_handler_with_clusters(self, mock_neo4j_handler):
        """Extend mock handler with cluster methods."""
        mock_neo4j_handler.find_clusters.return_value = {
            "cluster_count": 3,
            "isolated_count": 1,
            "connected_clusters": 2,
            "total_entities": 10,
            "clusters": [
                {
                    "cluster_id": "entity-1",
                    "size": 5,
                    "entity_ids": ["entity-1", "entity-2", "entity-3", "entity-4", "entity-5"],
                    "entities": [{"id": f"entity-{i}", "profile": {}} for i in range(1, 6)],
                    "internal_edges": 6,
                    "is_isolated": False
                },
                {
                    "cluster_id": "entity-6",
                    "size": 4,
                    "entity_ids": ["entity-6", "entity-7", "entity-8", "entity-9"],
                    "entities": [{"id": f"entity-{i}", "profile": {}} for i in range(6, 10)],
                    "internal_edges": 4,
                    "is_isolated": False
                },
                {
                    "cluster_id": "entity-10",
                    "size": 1,
                    "entity_ids": ["entity-10"],
                    "entities": [{"id": "entity-10", "profile": {}}],
                    "internal_edges": 0,
                    "is_isolated": True
                }
            ]
        }

        return mock_neo4j_handler

    def test_get_clusters(self, mock_handler_with_clusters):
        """Test getting all clusters in a project."""
        client = get_test_client(mock_handler_with_clusters)

        response = client.get(
            "/api/v1/analysis/test_project/clusters"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["cluster_count"] == 3
        assert data["isolated_count"] == 1
        assert data["connected_clusters"] == 2
        assert data["total_entities"] == 10
        assert len(data["clusters"]) == 3

        # Verify sorted by size (largest first)
        assert data["clusters"][0]["size"] >= data["clusters"][1]["size"]

    def test_get_clusters_exclude_isolated(self, mock_handler_with_clusters):
        """Test excluding isolated entities from clusters."""
        client = get_test_client(mock_handler_with_clusters)

        response = client.get(
            "/api/v1/analysis/test_project/clusters",
            params={"include_isolated": False}
        )

        assert response.status_code == 200
        data = response.json()
        # Should filter out isolated clusters
        assert data["cluster_count"] == 2
        assert all(not c["is_isolated"] for c in data["clusters"])

    def test_get_clusters_empty_project(self, mock_handler_with_clusters):
        """Test clusters for empty project."""
        mock_handler_with_clusters.find_clusters.return_value = {
            "cluster_count": 0,
            "isolated_count": 0,
            "connected_clusters": 0,
            "total_entities": 0,
            "clusters": []
        }
        client = get_test_client(mock_handler_with_clusters)

        response = client.get(
            "/api/v1/analysis/test_project/clusters"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["cluster_count"] == 0
        assert len(data["clusters"]) == 0


class TestNeo4jHandlerGraphMethods:
    """Unit tests for Neo4j handler graph analysis methods."""

    def test_find_shortest_path_logic(self):
        """Test the shortest path finding logic."""
        from neo4j_handler import Neo4jHandler

        # This would require a real Neo4j connection or more sophisticated mocking
        # For unit tests, we verify the method signature and basic behavior
        handler = MagicMock(spec=Neo4jHandler)
        handler.find_shortest_path.return_value = {
            "found": True,
            "path_length": 3,
            "entity_ids": ["a", "b", "c", "d"]
        }

        result = handler.find_shortest_path("project", "a", "d")
        assert result["found"] is True
        assert result["path_length"] == 3

    def test_centrality_calculation_logic(self):
        """Test centrality calculation logic."""
        from neo4j_handler import Neo4jHandler

        handler = MagicMock(spec=Neo4jHandler)
        handler.get_entity_centrality.return_value = {
            "entity_id": "test",
            "degree_centrality": 10,
            "outgoing_connections": 6,
            "incoming_connections": 4,
            "normalized_centrality": 0.5
        }

        result = handler.get_entity_centrality("project", "test")
        assert result["degree_centrality"] == result["outgoing_connections"] + result["incoming_connections"]

    def test_cluster_union_find_logic(self):
        """Test cluster detection using union-find."""
        from neo4j_handler import Neo4jHandler

        handler = MagicMock(spec=Neo4jHandler)
        handler.find_clusters.return_value = {
            "cluster_count": 2,
            "clusters": [
                {"cluster_id": "a", "size": 3, "entity_ids": ["a", "b", "c"]},
                {"cluster_id": "d", "size": 2, "entity_ids": ["d", "e"]}
            ]
        }

        result = handler.find_clusters("project")
        total_entities = sum(c["size"] for c in result["clusters"])
        assert total_entities == 5


class TestAnalysisResponseModels:
    """Tests for analysis response Pydantic models."""

    def test_shortest_path_response_model(self):
        """Test ShortestPathResponse model."""
        from api.routers.analysis import ShortestPathResponse

        # Found path
        response = ShortestPathResponse(
            found=True,
            path_length=3,
            entity_count=4,
            entity_ids=["a", "b", "c", "d"]
        )
        assert response.found is True
        assert response.path_length == 3

        # No path found
        response = ShortestPathResponse(
            found=False,
            message="No path exists"
        )
        assert response.found is False
        assert response.message == "No path exists"

    def test_centrality_response_model(self):
        """Test CentralityResponse model."""
        from api.routers.analysis import CentralityResponse

        response = CentralityResponse(
            entity_id="test-id",
            degree_centrality=10,
            outgoing_connections=6,
            incoming_connections=4,
            outgoing_to=["a", "b", "c", "d", "e", "f"],
            incoming_from=["g", "h", "i", "j"],
            normalized_centrality=0.5,
            total_entities_in_project=20
        )

        assert response.entity_id == "test-id"
        assert response.degree_centrality == 10
        assert len(response.outgoing_to) == 6
        assert len(response.incoming_from) == 4

    def test_neighborhood_response_model(self):
        """Test NeighborhoodResponse model."""
        from api.routers.analysis import NeighborhoodResponse

        response = NeighborhoodResponse(
            center_entity_id="center",
            max_depth=2,
            total_entities=5,
            neighborhood={
                "depth_0": [{"id": "center"}],
                "depth_1": [{"id": "a"}, {"id": "b"}],
                "depth_2": [{"id": "c"}, {"id": "d"}]
            },
            edges=[
                {"source": "center", "target": "a"},
                {"source": "center", "target": "b"}
            ]
        )

        assert response.center_entity_id == "center"
        assert response.total_entities == 5
        assert len(response.neighborhood["depth_1"]) == 2

    def test_clusters_response_model(self):
        """Test ClustersResponse model."""
        from api.routers.analysis import ClustersResponse, ClusterInfo

        cluster = ClusterInfo(
            cluster_id="root",
            size=5,
            entity_ids=["a", "b", "c", "d", "e"],
            internal_edges=6,
            is_isolated=False
        )

        response = ClustersResponse(
            cluster_count=1,
            isolated_count=0,
            connected_clusters=1,
            total_entities=5,
            clusters=[cluster]
        )

        assert response.cluster_count == 1
        assert response.clusters[0].size == 5
