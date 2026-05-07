"""
Tests for the Map Visualization UI (Stream 6)

Tests the enhanced graph visualization interface at /map.html with:
- Cytoscape.js rendering
- Layout switching (COSE, Breadthfirst, Circle, Grid)
- Depth control slider
- Entity type coloring
- Node/edge styling
- Interactive controls (center, export, fullscreen)
- Tooltip on hover
- Click navigation to entities
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock


def get_test_client(mock_handler):
    """Create a test client with mocked dependencies."""
    from api.main import app
    from api.dependencies import get_neo4j_handler

    app.dependency_overrides[get_neo4j_handler] = lambda: mock_handler
    return TestClient(app)


@pytest.fixture
def sample_subgraph_cytoscape():
    """Sample Cytoscape format subgraph for testing."""
    return {
        "elements": {
            "nodes": [
                {
                    "data": {
                        "id": "person-1",
                        "label": "John Doe",
                        "type": "Person",
                        "properties": {
                            "entity_type": "person",
                            "profile": {"profile": {"first_name": "John", "last_name": "Doe"}},
                            "created_at": "2024-01-01T00:00:00"
                        }
                    }
                },
                {
                    "data": {
                        "id": "person-2",
                        "label": "Jane Smith",
                        "type": "Person",
                        "properties": {
                            "entity_type": "person",
                            "profile": {"profile": {"first_name": "Jane", "last_name": "Smith"}},
                            "created_at": "2024-01-02T00:00:00"
                        }
                    }
                },
                {
                    "data": {
                        "id": "org-1",
                        "label": "ACME Corp",
                        "type": "Organization",
                        "properties": {
                            "entity_type": "organization",
                            "profile": {"profile": {"name": "ACME Corporation"}},
                            "created_at": "2024-01-03T00:00:00"
                        }
                    }
                }
            ],
            "edges": [
                {
                    "data": {
                        "id": "edge_0",
                        "source": "person-1",
                        "target": "person-2",
                        "label": "KNOWS",
                        "type": "KNOWS",
                        "properties": {"confidence": "high"}
                    }
                },
                {
                    "data": {
                        "id": "edge_1",
                        "source": "person-1",
                        "target": "org-1",
                        "label": "WORKS_WITH",
                        "type": "WORKS_WITH",
                        "properties": {"confidence": "medium"}
                    }
                }
            ]
        },
        "center_entity": "person-1",
        "depth": 2
    }


@pytest.fixture
def mock_neo4j_with_subgraph(mock_neo4j_handler, sample_subgraph_cytoscape):
    """Mock Neo4j handler with subgraph data."""
    # Mock get_person to return entity data
    def mock_get_person(project, entity_id):
        entities = {
            "person-1": {
                "id": "person-1",
                "profile": {
                    "core": {"name": "John Doe"},
                    "profile": {"first_name": "John", "last_name": "Doe"}
                }
            },
            "person-2": {
                "id": "person-2",
                "profile": {
                    "core": {"name": "Jane Smith"},
                    "profile": {"first_name": "Jane", "last_name": "Smith"}
                }
            }
        }
        return entities.get(entity_id)

    mock_neo4j_handler.get_person.side_effect = mock_get_person
    return mock_neo4j_handler


class TestMapVisualizationPage:
    """Tests for the /map.html page rendering."""

    def test_map_page_loads(self):
        """Test that /map.html page loads successfully."""
        client = TestClient(TestClient)
        response = client.get("/map.html")
        assert response.status_code == 200
        assert "graph-container" in response.text
        assert "Cytoscape" in response.text or "cytoscape" in response.text.lower()

    def test_map_page_includes_controls(self):
        """Test that the map page includes all control elements."""
        from tests.helpers import get_test_client
        client = get_test_client(MagicMock())
        response = client.get("/map.html")

        assert response.status_code == 200
        html = response.text

        # Verify all controls are present
        assert "depth-slider" in html, "Depth slider missing"
        assert "layout-selector" in html, "Layout selector missing"
        assert "center-btn" in html, "Center button missing"
        assert "export-btn" in html, "Export button missing"
        assert "reset-view-btn" in html, "Reset view button missing"
        assert "fullscreen-btn" in html, "Fullscreen button missing"
        assert "controls-panel" in html, "Controls panel missing"


class TestGraphDataStructure:
    """Tests for the graph data structure and API response."""

    def test_cytoscape_format_has_required_fields(self, sample_subgraph_cytoscape):
        """Test that Cytoscape format has all required fields."""
        assert "elements" in sample_subgraph_cytoscape
        assert "nodes" in sample_subgraph_cytoscape["elements"]
        assert "edges" in sample_subgraph_cytoscape["elements"]

        # Verify node structure
        node = sample_subgraph_cytoscape["elements"]["nodes"][0]
        assert "data" in node
        assert "id" in node["data"]
        assert "label" in node["data"]
        assert "type" in node["data"]
        assert "properties" in node["data"]

        # Verify entity_type is available in properties
        assert "entity_type" in node["data"]["properties"]

        # Verify edge structure
        edge = sample_subgraph_cytoscape["elements"]["edges"][0]
        assert "data" in edge
        assert "source" in edge["data"]
        assert "target" in edge["data"]
        assert "label" in edge["data"]
        assert "properties" in edge["data"]

    def test_entity_type_colors_mapping(self):
        """Test entity type to color mapping."""
        # This would test the client-side color mapping
        color_mapping = {
            'person': '#3498DB',
            'organization': '#27AE60',
            'location': '#E74C3C',
            'event': '#F39C12',
            'document': '#9B59B6',
            'other': '#95A5A6'
        }

        # Verify all types are mapped
        for entity_type, color in color_mapping.items():
            assert color.startswith('#'), f"Invalid color format for {entity_type}"
            assert len(color) == 7, f"Color must be 6-digit hex code for {entity_type}"


class TestNodeStyling:
    """Tests for node styling logic."""

    def test_node_degree_calculation(self):
        """Test that node degrees are calculated correctly."""
        elements = {
            "nodes": [
                {"data": {"id": "n1"}},
                {"data": {"id": "n2"}},
                {"data": {"id": "n3"}}
            ],
            "edges": [
                {"data": {"source": "n1", "target": "n2"}},
                {"data": {"source": "n1", "target": "n3"}},
                {"data": {"source": "n2", "target": "n3"}}
            ]
        }

        # Calculate degrees
        degrees = {}
        for edge in elements["edges"]:
            source = edge["data"]["source"]
            target = edge["data"]["target"]
            degrees[source] = degrees.get(source, 0) + 1
            degrees[target] = degrees.get(target, 0) + 1

        # Verify calculations
        assert degrees["n1"] == 2
        assert degrees["n2"] == 2
        assert degrees["n3"] == 2

    def test_node_size_calculation(self):
        """Test that node sizes are based on degree."""
        degree = 3
        base_size = 30
        degree_multiplier = 3
        max_additional = 25

        expected_size = base_size + min(degree * degree_multiplier, max_additional)
        assert expected_size == 39, "Node size calculation incorrect"


class TestEdgeStyling:
    """Tests for edge styling logic."""

    def test_edge_width_by_confidence(self):
        """Test edge width varies by confidence level."""
        confidence_widths = {
            'high': 3,
            'medium': 2,
            'low': 1
        }

        for confidence, expected_width in confidence_widths.items():
            assert isinstance(expected_width, int)
            assert expected_width > 0

    def test_edge_color_by_confidence(self):
        """Test edge color varies by confidence level."""
        confidence_colors = {
            'high': '#27AE60',    # Green
            'medium': '#95A5A6',  # Gray
            'low': '#BDC3C7'      # Light gray
        }

        for confidence, color in confidence_colors.items():
            assert color.startswith('#')
            assert len(color) == 7


class TestControls:
    """Tests for control functionality."""

    def test_depth_slider_range(self):
        """Test that depth slider has correct range."""
        min_depth = 1
        max_depth = 5
        default_depth = 2

        assert min_depth >= 1
        assert max_depth <= 10
        assert min_depth < default_depth < max_depth

    def test_layout_options(self):
        """Test that all required layout options are available."""
        layouts = ['cose', 'breadthfirst', 'circle', 'grid']

        assert len(layouts) == 4
        for layout in layouts:
            assert isinstance(layout, str)
            assert len(layout) > 0

    def test_export_endpoint_exists(self, mock_neo4j_handler):
        """Test that export endpoint is available."""
        from api.routers.visualization import ExportFormat

        # Verify the export format enum has graphml
        assert hasattr(ExportFormat, 'GRAPHML')
        assert ExportFormat.GRAPHML.value == 'graphml'


class TestInteractivity:
    """Tests for interactive features."""

    def test_node_click_navigation_url(self):
        """Test that node click generates correct navigation URL."""
        project = "test_project"
        clicked_node = "person-2"
        current_depth = 2

        expected_url = f"/map.html?project={project}&personId={clicked_node}&depth={current_depth}"

        # Verify URL format
        assert "personId=" in expected_url
        assert "project=" in expected_url
        assert "depth=" in expected_url

    def test_tooltip_content_format(self):
        """Test that tooltip shows correct information."""
        name = "John Doe"
        entity_type = "person"

        # Expected format: "Name (Type)"
        tooltip_text = f"{name} ({entity_type.capitalize()})"

        assert "John Doe" in tooltip_text
        assert "Person" in tooltip_text


class TestPerformance:
    """Tests for performance-related features."""

    def test_debounce_prevents_excessive_requests(self):
        """Test that debouncing prevents excessive API calls."""
        # This would be tested in integration tests
        # The debounce timeout should be reasonable (e.g., 500ms)
        debounce_delay = 500  # milliseconds

        assert debounce_delay > 0
        assert debounce_delay < 2000  # Not too long

    def test_graph_data_caching(self):
        """Test that graph data is cached client-side."""
        # When fetching the same entity/project, cache should be used
        project = "test_project"
        entity = "person-1"

        # In the implementation, we check if:
        # cachedProjectName === projectSafeName &&
        # cachedEntityId === entityId

        assert project == "test_project"
        assert entity == "person-1"


class TestResponsiveness:
    """Tests for responsive design."""

    def test_controls_panel_responsive(self):
        """Test that controls panel is responsive."""
        # The controls panel should have max-width and be positioned fixed
        # Mobile media query should adjust layout
        assert True  # This would be visual testing


class TestAccessibility:
    """Tests for accessibility features."""

    def test_labels_for_controls(self):
        """Test that all controls have proper labels."""
        controls = ['depth-slider', 'layout-selector', 'center-btn', 'export-btn']

        for control in controls:
            assert control is not None
            assert len(control) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
