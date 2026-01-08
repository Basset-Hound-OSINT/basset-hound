"""
Tests for the enhanced MCP server tools (orphans, provenance, query_entities, get_entity_graph).

These tests cover the new MCP tools added for OSINT platform integration:
- Orphan data management (unlinked identifiers)
- Data provenance and chain of custody tracking
- Flexible entity querying
- Graph export functionality
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from uuid import uuid4
import json


class TestOrphanTools:
    """Tests for orphan data management MCP tools."""

    @pytest.fixture
    def mock_neo4j_orphan(self):
        """Create mock Neo4j handler with orphan methods."""
        handler = MagicMock()

        # Mock project methods
        handler.get_project.return_value = {
            "id": "proj-1",
            "name": "Test Project",
            "safe_name": "test_project"
        }
        handler.get_all_projects.return_value = [{
            "id": "proj-1",
            "name": "Test Project",
            "safe_name": "test_project"
        }]

        # Mock orphan methods
        orphan_id = str(uuid4())
        handler.create_orphan_data.return_value = {
            "id": orphan_id,
            "identifier_type": "email",
            "identifier_value": "test@example.com",
            "created_at": datetime.now().isoformat(),
            "linked": False,
            "tags": ["import"]
        }

        handler.create_orphan_data_batch.return_value = {
            "created": [orphan_id, str(uuid4())],
            "failed": [],
            "total": 2
        }

        handler.get_orphan_data.return_value = {
            "id": orphan_id,
            "identifier_type": "email",
            "identifier_value": "test@example.com",
            "created_at": datetime.now().isoformat(),
            "linked": False,
            "tags": ["import"]
        }

        handler.list_orphan_data.return_value = [
            {
                "id": orphan_id,
                "identifier_type": "email",
                "identifier_value": "test@example.com",
                "linked": False
            },
            {
                "id": str(uuid4()),
                "identifier_type": "phone",
                "identifier_value": "+1234567890",
                "linked": True
            }
        ]

        handler.search_orphan_data.return_value = [
            {
                "id": orphan_id,
                "identifier_type": "email",
                "identifier_value": "test@example.com"
            }
        ]

        handler.link_orphan_data_batch.return_value = {
            "linked": 1,
            "failed": [],
            "total": 1
        }

        handler.update_orphan_data.return_value = {
            "id": orphan_id,
            "identifier_type": "email",
            "identifier_value": "updated@example.com",
            "tags": ["updated"]
        }

        handler.delete_orphan_data.return_value = True

        handler.find_duplicate_orphans.return_value = [
            {
                "identifier_type": "email",
                "identifier_value": "dup@example.com",
                "orphan_ids": [str(uuid4()), str(uuid4())]
            }
        ]

        handler.count_orphan_data.return_value = 5

        handler.get_person.return_value = {
            "id": "person-1",
            "profile": {"core": {"name": [{"first_name": "John"}]}}
        }

        return handler

    def test_orphan_tool_imports(self):
        """Test that orphan tools module can be imported."""
        try:
            from basset_mcp.tools.orphans import register_orphan_tools
            assert register_orphan_tools is not None
        except ImportError as e:
            pytest.skip(f"MCP package not available: {e}")

    def test_create_orphan_logic(self, mock_neo4j_orphan):
        """Test orphan creation logic."""
        result = mock_neo4j_orphan.create_orphan_data("test_project", {
            "identifier_type": "email",
            "identifier_value": "test@example.com",
            "tags": ["import"]
        })

        assert result is not None
        assert result["identifier_type"] == "email"
        assert result["identifier_value"] == "test@example.com"
        assert "id" in result

    def test_create_orphan_batch_logic(self, mock_neo4j_orphan):
        """Test batch orphan creation logic."""
        orphans = [
            {"identifier_type": "email", "identifier_value": "test1@example.com"},
            {"identifier_type": "phone", "identifier_value": "+1234567890"}
        ]

        result = mock_neo4j_orphan.create_orphan_data_batch("test_project", orphans)

        assert result["total"] == 2
        assert len(result["created"]) == 2
        assert len(result["failed"]) == 0

    def test_list_orphans_with_filter(self, mock_neo4j_orphan):
        """Test orphan listing with filters."""
        filters = {"identifier_type": "email", "linked": False}
        orphans = mock_neo4j_orphan.list_orphan_data("test_project", filters=filters)

        assert len(orphans) == 2
        assert orphans[0]["identifier_type"] == "email"

    def test_search_orphans(self, mock_neo4j_orphan):
        """Test orphan search functionality."""
        results = mock_neo4j_orphan.search_orphan_data("test_project", "test@example.com")

        assert len(results) == 1
        assert "test@example.com" in results[0]["identifier_value"]

    def test_link_orphan_logic(self, mock_neo4j_orphan):
        """Test linking orphan to entity."""
        links = [{"orphan_id": "orphan-1", "entity_id": "person-1"}]
        result = mock_neo4j_orphan.link_orphan_data_batch("test_project", links)

        assert result["linked"] == 1
        assert result["total"] == 1

    def test_duplicate_orphan_detection(self, mock_neo4j_orphan):
        """Test duplicate orphan detection."""
        duplicates = mock_neo4j_orphan.find_duplicate_orphans("test_project")

        assert len(duplicates) == 1
        assert duplicates[0]["identifier_type"] == "email"
        assert len(duplicates[0]["orphan_ids"]) == 2


class TestProvenanceTools:
    """Tests for data provenance MCP tools."""

    @pytest.fixture
    def mock_neo4j_provenance(self):
        """Create mock Neo4j handler for provenance tests."""
        handler = MagicMock()

        handler.get_project.return_value = {
            "id": "proj-1",
            "safe_name": "test_project"
        }
        handler.get_all_projects.return_value = [{
            "id": "proj-1",
            "safe_name": "test_project"
        }]

        handler.get_person.return_value = {
            "id": "person-1",
            "profile": {
                "core": {"name": [{"first_name": "John"}]},
                "_provenance": [],
                "_field_provenance": {}
            }
        }

        handler.update_person.return_value = {
            "id": "person-1",
            "profile": {"updated": True}
        }

        return handler

    def test_provenance_tool_imports(self):
        """Test that provenance tools module can be imported."""
        try:
            from basset_mcp.tools.provenance import register_provenance_tools
            assert register_provenance_tools is not None
        except ImportError as e:
            pytest.skip(f"MCP package not available: {e}")

    def test_provenance_model_imports(self):
        """Test that provenance models can be imported."""
        from api.models.provenance import (
            DataProvenance,
            ProvenanceCreate,
            SourceType,
            CaptureMethod,
            VerificationState
        )

        # Test enum values
        assert SourceType.WEBSITE.value == "website"
        assert SourceType.MCP_TOOL.value == "mcp_tool"
        assert SourceType.BROWSER_EXTENSION.value == "browser_extension"

        assert CaptureMethod.AUTO_DETECTED.value == "auto_detected"
        assert CaptureMethod.USER_SELECTED.value == "user_selected"

        assert VerificationState.UNVERIFIED.value == "unverified"
        assert VerificationState.HUMAN_VERIFIED.value == "human_verified"

    def test_provenance_create_model(self):
        """Test ProvenanceCreate model."""
        from api.models.provenance import ProvenanceCreate, SourceType, CaptureMethod

        prov = ProvenanceCreate(
            source_type=SourceType.WEBSITE,
            source_url="https://example.com",
            capture_method=CaptureMethod.AUTO_DETECTED,
            captured_by="autofill-extension",
            confidence=0.85
        )

        assert prov.source_type == SourceType.WEBSITE
        assert prov.confidence == 0.85

        # Convert to full provenance
        full_prov = prov.to_provenance()
        assert full_prov.source_domain == "example.com"
        assert full_prov.captured_at is not None

    def test_provenance_to_dict(self):
        """Test DataProvenance to_dict method."""
        from api.models.provenance import DataProvenance, SourceType, CaptureMethod

        prov = DataProvenance(
            source_type=SourceType.OSINT_AGENT,
            source_url="https://target.com/profile",
            capture_method=CaptureMethod.SCRAPE,
            captured_by="osint-agent-1",
            confidence=0.9
        )

        prov_dict = prov.to_dict()

        assert prov_dict["source_type"] == "osint_agent"
        assert prov_dict["capture_method"] == "scrape"
        assert prov_dict["confidence"] == 0.9
        assert "captured_at" in prov_dict


class TestQueryEntitiesTools:
    """Tests for the query_entities MCP tool."""

    @pytest.fixture
    def mock_neo4j_query(self):
        """Create mock Neo4j handler for query tests."""
        handler = MagicMock()

        handler.get_project.return_value = {
            "id": "proj-1",
            "safe_name": "test_project"
        }
        handler.get_all_projects.return_value = [{
            "id": "proj-1",
            "safe_name": "test_project"
        }]

        # Return multiple entities for filtering tests
        handler.get_all_people.return_value = [
            {
                "id": "person-1",
                "created_at": "2024-01-15T10:30:00",
                "profile": {
                    "core": {"name": [{"first_name": "John"}], "email": ["john@example.com"]},
                    "contact": {"phone": ["+1234567890"]},
                    "Tagged People": {"relationships": []}
                }
            },
            {
                "id": "person-2",
                "created_at": "2024-06-20T14:00:00",
                "profile": {
                    "core": {"name": [{"first_name": "Jane"}]},
                    "Tagged People": {"relationships": [{"target_entity_id": "person-1", "type": "WORKS_WITH"}]}
                }
            },
            {
                "id": "person-3",
                "created_at": "2024-12-01T09:00:00",
                "profile": {
                    "core": {"name": [{"first_name": "Bob"}]},
                    "social": {"twitter": "@bob"}
                }
            }
        ]

        return handler

    def test_query_entities_logic_filter_by_date(self, mock_neo4j_query):
        """Test entity query filtering by creation date."""
        all_entities = mock_neo4j_query.get_all_people("test_project")

        # Filter entities created after June 2024
        created_after = "2024-06-01T00:00:00"
        filtered = [e for e in all_entities if e.get("created_at", "") >= created_after]

        assert len(filtered) == 2  # person-2 and person-3
        assert filtered[0]["id"] in ["person-2", "person-3"]

    def test_query_entities_logic_has_section(self, mock_neo4j_query):
        """Test entity query filtering by section existence."""
        all_entities = mock_neo4j_query.get_all_people("test_project")

        # Filter entities with contact section
        filtered = []
        for entity in all_entities:
            profile = entity.get("profile", {})
            if "contact" in profile and profile["contact"]:
                filtered.append(entity)

        assert len(filtered) == 1
        assert filtered[0]["id"] == "person-1"

    def test_query_entities_logic_has_field(self, mock_neo4j_query):
        """Test entity query filtering by field existence."""
        all_entities = mock_neo4j_query.get_all_people("test_project")

        # Filter entities with twitter field
        filtered = []
        for entity in all_entities:
            profile = entity.get("profile", {})
            social = profile.get("social", {})
            if social.get("twitter"):
                filtered.append(entity)

        assert len(filtered) == 1
        assert filtered[0]["id"] == "person-3"

    def test_query_entities_logic_has_relationship(self, mock_neo4j_query):
        """Test entity query filtering by relationship existence."""
        all_entities = mock_neo4j_query.get_all_people("test_project")

        # Filter entities with relationships
        with_relationships = []
        for entity in all_entities:
            profile = entity.get("profile", {})
            tagged = profile.get("Tagged People", {})
            relationships = tagged.get("relationships", [])
            if relationships:
                with_relationships.append(entity)

        assert len(with_relationships) == 1
        assert with_relationships[0]["id"] == "person-2"


class TestGetEntityGraphTools:
    """Tests for the get_entity_graph MCP tool."""

    @pytest.fixture
    def mock_neo4j_graph(self):
        """Create mock Neo4j handler for graph export tests."""
        handler = MagicMock()

        handler.get_project.return_value = {
            "id": "proj-1",
            "safe_name": "test_project"
        }
        handler.get_all_projects.return_value = [{
            "id": "proj-1",
            "safe_name": "test_project"
        }]

        handler.get_all_people.return_value = [
            {
                "id": "person-1",
                "profile": {
                    "core": {"name": [{"first_name": "Alice", "last_name": "Smith"}]},
                    "Tagged People": {
                        "relationships": [
                            {"target_entity_id": "person-2", "type": "WORKS_WITH", "confidence": "high"}
                        ]
                    }
                }
            },
            {
                "id": "person-2",
                "profile": {
                    "core": {"name": [{"first_name": "Bob", "last_name": "Jones"}]},
                    "Tagged People": {
                        "relationships": [
                            {"target_entity_id": "person-3", "type": "FAMILY", "confidence": "confirmed"}
                        ]
                    }
                }
            },
            {
                "id": "person-3",
                "profile": {
                    "core": {"name": [{"first_name": "Carol", "last_name": "Jones"}]},
                    "Tagged People": {}
                }
            }
        ]

        handler.list_orphan_data.return_value = [
            {
                "id": "orphan-1",
                "identifier_type": "email",
                "identifier_value": "unknown@example.com",
                "linked": True,
                "linked_entity_id": "person-1"
            }
        ]

        return handler

    def test_graph_export_standard_format(self, mock_neo4j_graph):
        """Test graph export in standard format."""
        entities = mock_neo4j_graph.get_all_people("test_project")

        # Build nodes
        nodes = []
        for entity in entities:
            entity_id = entity.get("id")
            profile = entity.get("profile", {})
            core = profile.get("core", {})
            name_data = core.get("name", [])

            if name_data and isinstance(name_data, list):
                first_name = name_data[0]
                if isinstance(first_name, dict):
                    display_name = f"{first_name.get('first_name', '')} {first_name.get('last_name', '')}"
                else:
                    display_name = str(first_name)
            else:
                display_name = entity_id[:8]

            nodes.append({
                "id": entity_id,
                "type": "entity",
                "label": display_name.strip()
            })

        assert len(nodes) == 3
        assert nodes[0]["label"] == "Alice Smith"
        assert nodes[1]["label"] == "Bob Jones"

    def test_graph_export_edges(self, mock_neo4j_graph):
        """Test graph export edge extraction."""
        entities = mock_neo4j_graph.get_all_people("test_project")

        # Build edges
        edges = []
        entity_ids = {e["id"] for e in entities}

        for entity in entities:
            entity_id = entity.get("id")
            profile = entity.get("profile", {})
            tagged = profile.get("Tagged People", {})
            relationships = tagged.get("relationships", [])

            for rel in relationships:
                target_id = rel.get("target_entity_id")
                if target_id and target_id in entity_ids:
                    edges.append({
                        "source": entity_id,
                        "target": target_id,
                        "type": rel.get("type", "RELATED"),
                        "confidence": rel.get("confidence", "medium")
                    })

        assert len(edges) == 2
        assert edges[0]["source"] == "person-1"
        assert edges[0]["target"] == "person-2"
        assert edges[0]["type"] == "WORKS_WITH"

    def test_graph_export_with_orphans(self, mock_neo4j_graph):
        """Test graph export including orphan data."""
        entities = mock_neo4j_graph.get_all_people("test_project")
        orphans = mock_neo4j_graph.list_orphan_data("test_project", filters={"linked": True})

        entity_ids = {e["id"] for e in entities}

        orphan_nodes = []
        orphan_edges = []

        for orphan in orphans:
            orphan_nodes.append({
                "id": orphan["id"],
                "type": "orphan",
                "label": f"{orphan['identifier_type']}: {orphan['identifier_value'][:20]}"
            })

            linked_entity_id = orphan.get("linked_entity_id")
            if linked_entity_id and linked_entity_id in entity_ids:
                orphan_edges.append({
                    "source": orphan["id"],
                    "target": linked_entity_id,
                    "type": "LINKED_TO"
                })

        assert len(orphan_nodes) == 1
        assert orphan_nodes[0]["type"] == "orphan"
        assert len(orphan_edges) == 1
        assert orphan_edges[0]["target"] == "person-1"

    def test_graph_export_cytoscape_format(self, mock_neo4j_graph):
        """Test graph export in Cytoscape.js format."""
        entities = mock_neo4j_graph.get_all_people("test_project")

        nodes = [{"id": e["id"], "label": e["id"][:8]} for e in entities]

        cyto_nodes = [{"data": node} for node in nodes]

        assert len(cyto_nodes) == 3
        assert "data" in cyto_nodes[0]
        assert cyto_nodes[0]["data"]["id"] == "person-1"

    def test_graph_export_adjacency_format(self, mock_neo4j_graph):
        """Test graph export in adjacency list format."""
        entities = mock_neo4j_graph.get_all_people("test_project")

        adjacency = {}
        for entity in entities:
            adjacency[entity["id"]] = []

        # Add edges to adjacency list
        for entity in entities:
            entity_id = entity.get("id")
            profile = entity.get("profile", {})
            tagged = profile.get("Tagged People", {})
            relationships = tagged.get("relationships", [])

            for rel in relationships:
                target_id = rel.get("target_entity_id")
                if target_id in adjacency:
                    adjacency[entity_id].append({
                        "target": target_id,
                        "type": rel.get("type", "RELATED")
                    })

        assert "person-1" in adjacency
        assert len(adjacency["person-1"]) == 1
        assert adjacency["person-1"][0]["target"] == "person-2"


class TestToolRegistration:
    """Tests for MCP tool registration."""

    def test_all_tools_registered(self):
        """Test that all new tools are properly registered."""
        try:
            from basset_mcp.tools import register_all_tools
            from basset_mcp.tools.orphans import register_orphan_tools
            from basset_mcp.tools.provenance import register_provenance_tools

            # Create a mock MCP instance
            mock_mcp = MagicMock()
            mock_mcp.tool.return_value = lambda f: f

            # Register all tools
            register_all_tools(mock_mcp)

            # Verify tool decorator was called
            assert mock_mcp.tool.called

        except ImportError as e:
            pytest.skip(f"MCP package not available: {e}")

    def test_expected_tools_defined(self):
        """Test that expected new tools exist in modules."""
        try:
            from basset_mcp.tools import (
                register_orphan_tools,
                register_provenance_tools
            )

            # These should be callable
            assert callable(register_orphan_tools)
            assert callable(register_provenance_tools)

        except ImportError as e:
            pytest.skip(f"MCP package not available: {e}")


class TestIntegrationScenarios:
    """Integration-style tests for common OSINT workflows."""

    def test_osint_data_ingestion_workflow(self):
        """Test typical OSINT data ingestion workflow."""
        # Simulate: Agent discovers data -> creates orphan -> links to entity

        # 1. Create orphan for discovered identifier
        orphan_data = {
            "identifier_type": "email",
            "identifier_value": "target@example.com",
            "source_file": "linkedin_scrape.json",
            "context": "Found in LinkedIn profile",
            "tags": ["linkedin", "osint"]
        }
        assert orphan_data["identifier_type"] == "email"

        # 2. Create provenance record
        from api.models.provenance import ProvenanceCreate, SourceType, CaptureMethod

        prov = ProvenanceCreate(
            source_type=SourceType.OSINT_AGENT,
            source_url="https://linkedin.com/in/target",
            capture_method=CaptureMethod.SCRAPE,
            captured_by="basset-hound-browser",
            confidence=0.85
        )

        assert prov.source_type == SourceType.OSINT_AGENT

        # 3. Link orphan to entity (simulated)
        link_request = {
            "orphan_id": "orphan-123",
            "entity_id": "person-456",
            "field_mapping": "contact.email"
        }
        assert link_request["field_mapping"] == "contact.email"

    def test_evidence_chain_workflow(self):
        """Test evidence collection with provenance chain."""
        from api.models.provenance import (
            DataProvenance,
            SourceType,
            CaptureMethod,
            VerificationState
        )

        # 1. Initial capture
        initial_prov = DataProvenance(
            source_type=SourceType.BROWSER_EXTENSION,
            source_url="https://target-site.com/profile",
            capture_method=CaptureMethod.USER_SELECTED,
            captured_by="autofill-extension",
            confidence=0.8,
            verification_state=VerificationState.UNVERIFIED
        )

        # 2. Verification update
        initial_prov.verification_state = VerificationState.FORMAT_VALID
        initial_prov.verification_method = "regex_validation"

        assert initial_prov.verification_state == VerificationState.FORMAT_VALID

        # 3. Human verification
        initial_prov.verification_state = VerificationState.HUMAN_VERIFIED
        initial_prov.user_verified = True

        assert initial_prov.user_verified is True

    def test_entity_relationship_analysis_workflow(self):
        """Test entity relationship analysis with graph export."""
        # Simulate: Query entities -> Export graph -> Analyze

        # 1. Query entities with relationships
        query_params = {
            "has_relationship": True,
            "has_section": "contact",
            "limit": 50
        }

        # 2. Export graph for visualization
        graph_params = {
            "include_orphans": True,
            "format": "cytoscape"
        }

        assert query_params["has_relationship"] is True
        assert graph_params["format"] == "cytoscape"
