#!/usr/bin/env python3
"""
Manual test script for graph visualization API.

This script can be used to manually test the graph service and router
without running the full test suite.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from unittest.mock import MagicMock


def test_graph_service():
    """Test the graph service directly."""
    print("Testing GraphService...")

    from api.services.graph_service import GraphService

    # Create mock Neo4j handler
    mock_neo4j = MagicMock()

    # Mock session and query results
    mock_session = MagicMock()
    mock_neo4j.driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
    mock_neo4j.driver.session.return_value.__exit__ = MagicMock(return_value=None)

    # Mock entity data
    mock_records = [
        MagicMock(
            __getitem__=lambda self, key: {
                "id": "entity-1",
                "profile": {
                    "profile": {"first_name": "John", "last_name": "Doe"},
                    "Tagged People": {
                        "tagged_people": ["entity-2"],
                        "relationship_types": {"entity-2": "WORKS_WITH"}
                    }
                },
                "created_at": "2024-01-01"
            }[key]
        ),
        MagicMock(
            __getitem__=lambda self, key: {
                "id": "entity-2",
                "profile": {
                    "profile": {"first_name": "Jane", "last_name": "Smith"},
                    "Tagged People": {}
                },
                "created_at": "2024-01-02"
            }[key]
        )
    ]

    mock_session.run.return_value = mock_records

    # Create service instance
    service = GraphService(mock_neo4j)

    # Test display name extraction
    print("  Testing display name extraction...")
    profile = {"profile": {"first_name": "John", "last_name": "Doe"}}
    name = service._extract_display_name(profile, "entity-1")
    assert name == "John Doe", f"Expected 'John Doe', got '{name}'"
    print(f"    ✓ Display name: {name}")

    # Test format conversions
    print("  Testing format conversions...")
    sample_graph = {
        "nodes": [
            {
                "id": "entity-1",
                "label": "John Doe",
                "type": "Person",
                "properties": {}
            }
        ],
        "edges": [
            {
                "source": "entity-1",
                "target": "entity-2",
                "type": "WORKS_WITH",
                "properties": {}
            }
        ]
    }

    # Test D3 format
    d3_data = service.format_for_d3(sample_graph)
    assert "nodes" in d3_data and "links" in d3_data
    print("    ✓ D3 format conversion")

    # Test vis.js format
    vis_data = service.format_for_vis(sample_graph)
    assert "nodes" in vis_data and "edges" in vis_data
    assert "from" in vis_data["edges"][0]
    print("    ✓ vis.js format conversion")

    # Test Cytoscape format
    cyto_data = service.format_for_cytoscape(sample_graph)
    assert "elements" in cyto_data
    print("    ✓ Cytoscape format conversion")

    print("✓ GraphService tests passed!\n")


def test_router_imports():
    """Test that router imports work correctly."""
    print("Testing router imports...")

    try:
        from api.routers.graph import router
        print("  ✓ Router imported successfully")

        # Check router attributes
        assert router.prefix == "/projects/{project_safe_name}/graph"
        print("  ✓ Router prefix correct")

        assert "graph" in router.tags
        print("  ✓ Router tags correct")

        print("✓ Router import tests passed!\n")

    except Exception as e:
        print(f"✗ Router import failed: {e}\n")
        raise


def test_format_examples():
    """Test format conversion with example data."""
    print("Testing format conversions with examples...")

    from api.services.graph_service import GraphService

    mock_neo4j = MagicMock()
    service = GraphService(mock_neo4j)

    sample_data = {
        "nodes": [
            {
                "id": "e1",
                "label": "Alice",
                "type": "Person",
                "properties": {"age": 30}
            },
            {
                "id": "e2",
                "label": "Bob",
                "type": "Person",
                "properties": {"age": 25}
            }
        ],
        "edges": [
            {
                "source": "e1",
                "target": "e2",
                "type": "FRIEND",
                "properties": {"since": "2020"}
            }
        ]
    }

    print("\n  Raw format:")
    print(f"    Nodes: {len(sample_data['nodes'])}")
    print(f"    Edges: {len(sample_data['edges'])}")

    print("\n  D3.js format:")
    d3 = service.format_for_d3(sample_data)
    print(f"    Nodes: {len(d3['nodes'])}")
    print(f"    Links: {len(d3['links'])}")
    print(f"    Sample link: {d3['links'][0]}")

    print("\n  vis.js format:")
    vis = service.format_for_vis(sample_data)
    print(f"    Nodes: {len(vis['nodes'])}")
    print(f"    Edges: {len(vis['edges'])}")
    print(f"    Sample edge: {vis['edges'][0]}")

    print("\n  Cytoscape format:")
    cyto = service.format_for_cytoscape(sample_data)
    print(f"    Nodes: {len(cyto['elements']['nodes'])}")
    print(f"    Edges: {len(cyto['elements']['edges'])}")
    print(f"    Sample node: {cyto['elements']['nodes'][0]}")

    print("\n✓ Format conversion examples completed!\n")


if __name__ == "__main__":
    print("=" * 60)
    print("Graph Visualization API - Manual Tests")
    print("=" * 60 + "\n")

    try:
        test_graph_service()
        test_router_imports()
        test_format_examples()

        print("=" * 60)
        print("All manual tests passed!")
        print("=" * 60)

    except Exception as e:
        print("\n" + "=" * 60)
        print(f"Tests failed with error: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        sys.exit(1)
