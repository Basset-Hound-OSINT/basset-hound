"""
Tests for named relationship types and relationship management.

These tests cover the Phase 3 relationship features:
- Named relationship types (WORKS_WITH, KNOWS, FAMILY, etc.)
- Relationship properties (confidence, source, notes)
- Bidirectional relationships
- Relationship CRUD operations
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


class TestRelationshipTypes:
    """Tests for the RelationshipType enum and utility functions."""

    def test_relationship_type_enum_values(self):
        """Test that all expected relationship types exist."""
        from api.models.relationship import RelationshipType

        expected_types = [
            "RELATED_TO", "KNOWS", "WORKS_WITH", "BUSINESS_PARTNER",
            "REPORTS_TO", "MANAGES", "COLLEAGUE", "CLIENT", "EMPLOYER", "EMPLOYEE",
            "FAMILY", "MARRIED_TO", "PARENT_OF", "CHILD_OF", "SIBLING_OF", "SPOUSE",
            "FRIEND", "ACQUAINTANCE", "NEIGHBOR",
            "MEMBER_OF", "AFFILIATED_WITH",
            "ASSOCIATED_WITH", "SUSPECTED_ASSOCIATE", "ALIAS_OF",
            "COMMUNICATES_WITH", "CONTACTED"
        ]

        for rel_type in expected_types:
            assert hasattr(RelationshipType, rel_type)
            assert RelationshipType[rel_type].value == rel_type

    def test_get_inverse_relationship(self):
        """Test inverse relationship lookups."""
        from api.models.relationship import RelationshipType

        # Test asymmetric relationships
        assert RelationshipType.get_inverse(RelationshipType.PARENT_OF) == RelationshipType.CHILD_OF
        assert RelationshipType.get_inverse(RelationshipType.CHILD_OF) == RelationshipType.PARENT_OF
        assert RelationshipType.get_inverse(RelationshipType.MANAGES) == RelationshipType.REPORTS_TO
        assert RelationshipType.get_inverse(RelationshipType.REPORTS_TO) == RelationshipType.MANAGES
        assert RelationshipType.get_inverse(RelationshipType.EMPLOYER) == RelationshipType.EMPLOYEE
        assert RelationshipType.get_inverse(RelationshipType.EMPLOYEE) == RelationshipType.EMPLOYER

        # Symmetric relationships should return None
        assert RelationshipType.get_inverse(RelationshipType.WORKS_WITH) is None
        assert RelationshipType.get_inverse(RelationshipType.FRIEND) is None

    def test_is_symmetric_relationship(self):
        """Test symmetric relationship detection."""
        from api.models.relationship import RelationshipType

        # Symmetric relationships
        assert RelationshipType.is_symmetric(RelationshipType.RELATED_TO) is True
        assert RelationshipType.is_symmetric(RelationshipType.KNOWS) is True
        assert RelationshipType.is_symmetric(RelationshipType.WORKS_WITH) is True
        assert RelationshipType.is_symmetric(RelationshipType.BUSINESS_PARTNER) is True
        assert RelationshipType.is_symmetric(RelationshipType.COLLEAGUE) is True
        assert RelationshipType.is_symmetric(RelationshipType.MARRIED_TO) is True
        assert RelationshipType.is_symmetric(RelationshipType.SIBLING_OF) is True
        assert RelationshipType.is_symmetric(RelationshipType.FRIEND) is True

        # Asymmetric relationships
        assert RelationshipType.is_symmetric(RelationshipType.PARENT_OF) is False
        assert RelationshipType.is_symmetric(RelationshipType.CHILD_OF) is False
        assert RelationshipType.is_symmetric(RelationshipType.MANAGES) is False
        assert RelationshipType.is_symmetric(RelationshipType.REPORTS_TO) is False
        assert RelationshipType.is_symmetric(RelationshipType.EMPLOYER) is False
        assert RelationshipType.is_symmetric(RelationshipType.EMPLOYEE) is False

    def test_get_all_relationship_types(self):
        """Test getting all relationship type values."""
        from api.models.relationship import get_all_relationship_types

        all_types = get_all_relationship_types()
        assert isinstance(all_types, list)
        assert len(all_types) > 20  # We have many types defined
        assert "RELATED_TO" in all_types
        assert "WORKS_WITH" in all_types
        assert "FAMILY" in all_types

    def test_get_relationship_type_categories(self):
        """Test relationship type categorization."""
        from api.models.relationship import get_relationship_type_categories

        categories = get_relationship_type_categories()
        assert isinstance(categories, dict)

        # Check expected categories
        assert "generic" in categories
        assert "professional" in categories
        assert "family" in categories
        assert "social" in categories
        assert "organizational" in categories
        assert "investigative" in categories
        assert "communication" in categories

        # Check some values
        assert "RELATED_TO" in categories["generic"]
        assert "WORKS_WITH" in categories["professional"]
        assert "FAMILY" in categories["family"]
        assert "FRIEND" in categories["social"]


class TestConfidenceLevel:
    """Tests for confidence level enum."""

    def test_confidence_level_values(self):
        """Test that all confidence levels exist."""
        from api.models.relationship import ConfidenceLevel

        expected_levels = ["confirmed", "high", "medium", "low", "unverified"]

        for level in expected_levels:
            # Check the enum has a member with this value
            assert any(cl.value == level for cl in ConfidenceLevel)


class TestRelationshipModels:
    """Tests for relationship Pydantic models."""

    def test_relationship_properties_model(self):
        """Test RelationshipProperties model creation."""
        from api.models.relationship import RelationshipProperties, RelationshipType, ConfidenceLevel
        from datetime import datetime

        props = RelationshipProperties(
            relationship_type=RelationshipType.WORKS_WITH,
            confidence=ConfidenceLevel.HIGH,
            source="LinkedIn",
            notes="Same company",
            is_active=True
        )

        assert props.relationship_type == RelationshipType.WORKS_WITH
        assert props.confidence == ConfidenceLevel.HIGH
        assert props.source == "LinkedIn"
        assert props.notes == "Same company"
        assert props.is_active is True

    def test_relationship_create_model(self):
        """Test RelationshipCreate model validation."""
        from api.models.relationship import RelationshipCreate, RelationshipType

        data = RelationshipCreate(
            tagged_ids=["uuid-1", "uuid-2"],
            transitive_relationships=["uuid-3"],
            relationship_types={"uuid-1": RelationshipType.WORKS_WITH}
        )

        assert len(data.tagged_ids) == 2
        assert len(data.transitive_relationships) == 1
        assert data.relationship_types["uuid-1"] == RelationshipType.WORKS_WITH

    def test_relationship_create_unique_ids(self):
        """Test that duplicate IDs are rejected."""
        from api.models.relationship import RelationshipCreate
        import pydantic

        with pytest.raises(pydantic.ValidationError):
            RelationshipCreate(
                tagged_ids=["uuid-1", "uuid-1"],  # Duplicate
                transitive_relationships=[]
            )

    def test_named_relationship_create_model(self):
        """Test NamedRelationshipCreate model."""
        from api.models.relationship import NamedRelationshipCreate, RelationshipType, ConfidenceLevel

        data = NamedRelationshipCreate(
            relationship_type=RelationshipType.FRIEND,
            confidence=ConfidenceLevel.HIGH,
            source="Facebook",
            notes="Known friends",
            bidirectional=True
        )

        assert data.relationship_type == RelationshipType.FRIEND
        assert data.confidence == ConfidenceLevel.HIGH
        assert data.bidirectional is True

    def test_relationship_info_model(self):
        """Test RelationshipInfo model."""
        from api.models.relationship import RelationshipInfo, RelationshipType, ConfidenceLevel

        info = RelationshipInfo(
            source_id="uuid-1",
            target_id="uuid-2",
            relationship_type=RelationshipType.FAMILY,
            confidence=ConfidenceLevel.CONFIRMED,
            is_transitive=False
        )

        assert info.source_id == "uuid-1"
        assert info.target_id == "uuid-2"
        assert info.relationship_type == RelationshipType.FAMILY

    def test_relationship_response_model(self):
        """Test RelationshipResponse model."""
        from api.models.relationship import RelationshipResponse

        response = RelationshipResponse(
            entity_id="uuid-1",
            tagged_ids=["uuid-2", "uuid-3"],
            transitive_relationships=["uuid-4"],
            relationship_types={"uuid-2": "WORKS_WITH", "uuid-3": "FRIEND"}
        )

        assert response.entity_id == "uuid-1"
        assert len(response.tagged_ids) == 2
        assert len(response.transitive_relationships) == 1


class TestRelationshipEndpoints:
    """Tests for relationship API endpoints."""

    @pytest.fixture
    def mock_handler_with_relationships(self, mock_neo4j_handler):
        """Extend mock handler with relationship methods."""
        mock_neo4j_handler.create_relationship.return_value = {
            "source_id": "entity-1",
            "target_id": "entity-2",
            "relationship_type": "WORKS_WITH",
            "properties": {"timestamp": "2024-01-15T10:30:00"}
        }

        mock_neo4j_handler.get_relationship.return_value = {
            "source_id": "entity-1",
            "target_id": "entity-2",
            "relationship_type": "WORKS_WITH",
            "properties": {"confidence": "high"}
        }

        mock_neo4j_handler.update_relationship.return_value = {
            "source_id": "entity-1",
            "target_id": "entity-2",
            "relationship_type": "FRIEND",
            "properties": {"confidence": "confirmed"}
        }

        mock_neo4j_handler.delete_relationship.return_value = True

        mock_neo4j_handler.create_bidirectional_relationship.return_value = {
            "forward": {"source_id": "entity-1", "target_id": "entity-2"},
            "reverse": {"source_id": "entity-2", "target_id": "entity-1"}
        }

        mock_neo4j_handler.get_all_relationships.return_value = [
            {
                "source_id": "entity-1",
                "target_id": "entity-2",
                "relationship_type": "WORKS_WITH",
                "properties": {},
                "is_transitive": False
            }
        ]

        mock_neo4j_handler.get_relationship_type_counts.return_value = {
            "WORKS_WITH": 5,
            "FRIEND": 3,
            "FAMILY": 2
        }

        return mock_neo4j_handler

    def test_get_relationship_types(self, mock_handler_with_relationships):
        """Test getting available relationship types."""
        client = get_test_client(mock_handler_with_relationships)

        response = client.get(
            "/api/v1/projects/test_project/entities/entity-1/relationships/types"
        )

        assert response.status_code == 200
        data = response.json()
        assert "types" in data
        assert "categories" in data
        assert "WORKS_WITH" in data["types"]

    def test_tag_entity_with_type(self, mock_handler_with_relationships):
        """Test tagging an entity with a specific relationship type."""
        client = get_test_client(mock_handler_with_relationships)

        response = client.post(
            "/api/v1/projects/test_project/entities/entity-1/relationships/tag/entity-2",
            params={
                "relationship_type": "WORKS_WITH",
                "confidence": "high",
                "source": "LinkedIn"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_tag_entity_bidirectional(self, mock_handler_with_relationships):
        """Test creating a bidirectional relationship."""
        client = get_test_client(mock_handler_with_relationships)

        response = client.post(
            "/api/v1/projects/test_project/entities/entity-1/relationships/tag/entity-2",
            params={
                "relationship_type": "FRIEND",
                "bidirectional": True
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_update_relationship_type(self, mock_handler_with_relationships):
        """Test updating a relationship type."""
        client = get_test_client(mock_handler_with_relationships)

        response = client.patch(
            "/api/v1/projects/test_project/entities/entity-1/relationships/tag/entity-2",
            params={
                "relationship_type": "FRIEND",
                "confidence": "confirmed"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_get_relationship_details(self, mock_handler_with_relationships):
        """Test getting specific relationship details."""
        client = get_test_client(mock_handler_with_relationships)

        response = client.get(
            "/api/v1/projects/test_project/entities/entity-1/relationships/tag/entity-2"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["source_id"] == "entity-1"
        assert data["target_id"] == "entity-2"

    def test_get_all_project_relationships(self, mock_handler_with_relationships):
        """Test getting all relationships in a project."""
        client = get_test_client(mock_handler_with_relationships)

        response = client.get(
            "/api/v1/projects/test_project/relationships/"
        )

        assert response.status_code == 200
        data = response.json()
        assert "relationships" in data
        assert "count" in data

    def test_get_relationship_stats(self, mock_handler_with_relationships):
        """Test getting relationship statistics."""
        client = get_test_client(mock_handler_with_relationships)

        response = client.get(
            "/api/v1/projects/test_project/relationships/stats"
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_relationships" in data
        assert "relationship_type_counts" in data

    def test_untag_entity_bidirectional(self, mock_handler_with_relationships):
        """Test removing a bidirectional relationship."""
        client = get_test_client(mock_handler_with_relationships)

        response = client.delete(
            "/api/v1/projects/test_project/entities/entity-1/relationships/tag/entity-2",
            params={"bidirectional": True}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestRelationshipValidation:
    """Tests for relationship data validation."""

    def test_invalid_relationship_type_rejected(self):
        """Test that invalid relationship types are rejected."""
        from api.models.relationship import NamedRelationshipCreate
        import pydantic

        with pytest.raises(pydantic.ValidationError):
            NamedRelationshipCreate(
                relationship_type="INVALID_TYPE",  # Not a valid enum value
                bidirectional=False
            )

    def test_invalid_confidence_rejected(self):
        """Test that invalid confidence levels are rejected."""
        from api.models.relationship import NamedRelationshipCreate, RelationshipType
        import pydantic

        with pytest.raises(pydantic.ValidationError):
            NamedRelationshipCreate(
                relationship_type=RelationshipType.FRIEND,
                confidence="super_high",  # Not a valid level
                bidirectional=False
            )

    def test_source_field_max_length(self):
        """Test source field max length validation."""
        from api.models.relationship import RelationshipProperties, RelationshipType
        import pydantic

        # Should raise error for too long source
        with pytest.raises(pydantic.ValidationError):
            RelationshipProperties(
                relationship_type=RelationshipType.WORKS_WITH,
                source="x" * 501  # Exceeds 500 char limit
            )

    def test_notes_field_max_length(self):
        """Test notes field max length validation."""
        from api.models.relationship import RelationshipProperties, RelationshipType
        import pydantic

        # Should raise error for too long notes
        with pytest.raises(pydantic.ValidationError):
            RelationshipProperties(
                relationship_type=RelationshipType.WORKS_WITH,
                notes="x" * 2001  # Exceeds 2000 char limit
            )
