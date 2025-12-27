"""
Tests for auto-linking service.

These tests cover the Phase 3 auto-linking features:
- Identifier extraction from entities
- Matching entities by shared identifiers
- Link suggestions (duplicates vs. related entities)
- Entity merging
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


class TestAutoLinkerService:
    """Tests for the AutoLinker service class."""

    @pytest.fixture
    def auto_linker(self, mock_neo4j_handler):
        """Create an AutoLinker instance with mock handler."""
        from api.services.auto_linker import AutoLinker
        linker = AutoLinker(mock_neo4j_handler)
        return linker

    @pytest.fixture
    def sample_entities(self):
        """Sample entities for testing."""
        return [
            {
                "id": "entity-1",
                "profile": {
                    "core": {
                        "name": [{"first_name": "John", "last_name": "Doe"}],
                        "email": ["john.doe@example.com", "jdoe@work.com"]
                    },
                    "social_major": {
                        "twitter": [{"handle": "@johndoe"}],
                        "instagram": [{"username": "johndoe123"}]
                    }
                }
            },
            {
                "id": "entity-2",
                "profile": {
                    "core": {
                        "name": [{"first_name": "John", "middle_name": "D", "last_name": "Doe"}],
                        "email": ["john.doe@example.com"]  # Same email as entity-1
                    },
                    "social_major": {
                        "twitter": [{"handle": "@john_d"}]  # Different Twitter
                    }
                }
            },
            {
                "id": "entity-3",
                "profile": {
                    "core": {
                        "name": [{"first_name": "Jane", "last_name": "Smith"}],
                        "email": ["jane.smith@example.com"]
                    },
                    "social_major": {
                        "twitter": [{"handle": "@janesmith"}]
                    }
                }
            },
            {
                "id": "entity-4",
                "profile": {
                    "core": {
                        "name": [{"first_name": "Bob", "last_name": "Wilson"}],
                        "email": ["bob@example.com"]
                    },
                    "social_major": {
                        "instagram": [{"username": "johndoe123"}]  # Same Instagram as entity-1
                    }
                }
            }
        ]

    def test_identifier_weights(self, auto_linker):
        """Test that identifier weights are properly defined."""
        weights = auto_linker.IDENTIFIER_WEIGHTS

        # High-value identifiers
        assert weights["email"] >= 2.0
        assert weights["phone"] >= 2.0
        assert weights["crypto_address"] >= 3.0

        # Social identifiers
        assert weights["twitter.handle"] >= 1.5
        assert weights["github.username"] >= 2.0

        # Default weight
        assert weights["default"] == 1.0

    def test_confidence_thresholds(self, auto_linker):
        """Test confidence threshold values."""
        assert auto_linker.DUPLICATE_THRESHOLD > auto_linker.LINK_THRESHOLD
        assert auto_linker.LINK_THRESHOLD > 0

    def test_normalize_email(self, auto_linker):
        """Test email normalization."""
        assert auto_linker._normalize_value("John.Doe@Example.COM", "email") == "john.doe@example.com"
        assert auto_linker._normalize_value("  test@test.com  ", "email") == "test@test.com"

    def test_normalize_phone(self, auto_linker):
        """Test phone number normalization."""
        assert auto_linker._normalize_value("+1 (555) 123-4567", "phone") == "+15551234567"
        assert auto_linker._normalize_value("555.123.4567", "phone") == "5551234567"

    def test_normalize_empty_values(self, auto_linker):
        """Test normalization of empty values."""
        assert auto_linker._normalize_value(None, "string") is None
        assert auto_linker._normalize_value("", "string") is None
        assert auto_linker._normalize_value("   ", "string") is None

    def test_extract_identifiers(self, auto_linker, sample_entities):
        """Test identifier extraction from entity profiles."""
        # Mock the config loading with identifier paths
        auto_linker.identifier_paths = [
            {"path": "core.email", "section_id": "core", "field_id": "email",
             "component_id": None, "field_type": "email", "multiple": True},
            {"path": "social_major.twitter.handle", "section_id": "social_major",
             "field_id": "twitter", "component_id": "handle", "field_type": "string", "multiple": True},
            {"path": "social_major.instagram.username", "section_id": "social_major",
             "field_id": "instagram", "component_id": "username", "field_type": "string", "multiple": True}
        ]

        identifiers = auto_linker._extract_identifiers(sample_entities[0])

        assert "core.email" in identifiers
        assert len(identifiers["core.email"]) == 2
        assert "john.doe@example.com" in identifiers["core.email"]

    def test_get_identifier_weight(self, auto_linker):
        """Test identifier weight lookup."""
        # Exact match
        assert auto_linker._get_identifier_weight("email") == auto_linker.IDENTIFIER_WEIGHTS["email"]

        # Partial match
        assert auto_linker._get_identifier_weight("social_major.twitter.handle") >= 1.5

        # Contains email
        assert auto_linker._get_identifier_weight("core.email") == auto_linker.IDENTIFIER_WEIGHTS["email"]

        # Unknown identifier
        assert auto_linker._get_identifier_weight("unknown.field") == auto_linker.IDENTIFIER_WEIGHTS["default"]

    def test_get_entity_display_name(self, auto_linker, sample_entities):
        """Test entity display name extraction."""
        name = auto_linker._get_entity_display_name(sample_entities[0])
        assert "John" in name
        assert "Doe" in name

    def test_get_entity_display_name_fallback(self, auto_linker):
        """Test display name fallback to entity ID."""
        entity = {"id": "abc12345", "profile": {}}
        name = auto_linker._get_entity_display_name(entity)
        assert "abc12345"[:8] in name

    def test_find_matching_entities(self, auto_linker, sample_entities, mock_neo4j_handler):
        """Test finding matching entities."""
        mock_neo4j_handler.get_person.return_value = sample_entities[0]
        mock_neo4j_handler.get_all_people.return_value = sample_entities

        # Mock identifier paths
        auto_linker.identifier_paths = [
            {"path": "core.email", "section_id": "core", "field_id": "email",
             "component_id": None, "field_type": "email", "multiple": True}
        ]

        suggestions = auto_linker.find_matching_entities("test_project", "entity-1", min_confidence=0)

        # entity-2 has matching email
        matching_ids = [s.target_entity_id for s in suggestions]
        assert "entity-2" in matching_ids

    def test_suggest_links(self, auto_linker, sample_entities, mock_neo4j_handler):
        """Test link suggestions categorization."""
        mock_neo4j_handler.get_person.return_value = sample_entities[0]
        mock_neo4j_handler.get_all_people.return_value = sample_entities

        auto_linker.identifier_paths = [
            {"path": "core.email", "section_id": "core", "field_id": "email",
             "component_id": None, "field_type": "email", "multiple": True}
        ]

        result = auto_linker.suggest_links("test_project", "entity-1")

        assert "entity_id" in result
        assert "potential_duplicates" in result
        assert "suggested_links" in result
        assert "total_suggestions" in result

    def test_auto_link_all(self, auto_linker, sample_entities, mock_neo4j_handler):
        """Test scanning all entities for matches."""
        mock_neo4j_handler.get_all_people.return_value = sample_entities

        auto_linker.identifier_paths = [
            {"path": "core.email", "section_id": "core", "field_id": "email",
             "component_id": None, "field_type": "email", "multiple": True}
        ]

        result = auto_linker.auto_link_all("test_project", create_links=False)

        assert "entities_scanned" in result
        assert result["entities_scanned"] == len(sample_entities)
        assert "potential_duplicates" in result
        assert "suggested_links" in result
        assert "scanned_at" in result

    def test_merge_entities(self, auto_linker, mock_neo4j_handler):
        """Test entity merging."""
        primary = {
            "id": "primary-id",
            "profile": {
                "core": {
                    "name": [{"first_name": "John", "last_name": "Doe"}],
                    "email": ["john@primary.com"]
                }
            }
        }
        secondary = {
            "id": "secondary-id",
            "profile": {
                "core": {
                    "name": [{"first_name": "John", "middle_name": "M", "last_name": "Doe"}],
                    "email": ["john@secondary.com"],
                    "phone": [{"number": "555-1234"}]  # New field
                }
            }
        }

        mock_neo4j_handler.get_person.side_effect = lambda p, eid: \
            primary if eid == "primary-id" else secondary if eid == "secondary-id" else None
        mock_neo4j_handler.update_person.return_value = {"id": "primary-id", "profile": {}}
        mock_neo4j_handler.delete_person.return_value = True

        result = auto_linker.merge_entities(
            "test_project",
            "primary-id",
            "secondary-id",
            delete_secondary=True
        )

        assert result["success"] is True
        assert result["primary_entity_id"] == "primary-id"
        assert result["secondary_entity_id"] == "secondary-id"

    def test_merge_profiles(self, auto_linker):
        """Test profile merging logic."""
        primary = {
            "core": {
                "name": [{"first_name": "John"}],
                "email": ["john@example.com"]
            }
        }
        secondary = {
            "core": {
                "name": [{"first_name": "John", "last_name": "Doe"}],
                "phone": [{"number": "555-1234"}]
            },
            "social": {
                "twitter": "@johndoe"
            }
        }

        merged = auto_linker._merge_profiles(primary, secondary)

        # Primary takes precedence for existing fields
        assert "core" in merged
        assert "social" in merged  # Added from secondary

    def test_merge_values_lists(self, auto_linker):
        """Test value merging for lists."""
        primary = ["a", "b", "c"]
        secondary = ["b", "c", "d", "e"]

        result = auto_linker._merge_values(primary, secondary)

        # Should combine unique values
        assert len(result) == 5
        assert set(result) == {"a", "b", "c", "d", "e"}

    def test_merge_values_dicts(self, auto_linker):
        """Test value merging for dictionaries."""
        primary = {"key1": "value1", "key2": "value2"}
        secondary = {"key2": "other", "key3": "value3"}

        result = auto_linker._merge_values(primary, secondary)

        # Primary takes precedence
        assert result["key1"] == "value1"
        assert result["key2"] == "value2"  # Primary wins
        assert result["key3"] == "value3"  # Added from secondary

    def test_merge_values_empty(self, auto_linker):
        """Test value merging with empty values."""
        assert auto_linker._merge_values(None, "value") == "value"
        assert auto_linker._merge_values("value", None) == "value"
        assert auto_linker._merge_values("", "value") == "value"
        assert auto_linker._merge_values([], ["a", "b"]) == ["a", "b"]

    def test_get_identifier_fields(self, auto_linker):
        """Test getting identifier field definitions."""
        auto_linker.identifier_paths = [
            {"path": "core.email", "section_id": "core"},
            {"path": "social.twitter", "section_id": "social"}
        ]

        fields = auto_linker.get_identifier_fields()

        assert len(fields) == 2
        assert fields[0]["path"] == "core.email"


class TestLinkSuggestionModel:
    """Tests for LinkSuggestion dataclass."""

    def test_link_suggestion_creation(self):
        """Test creating a LinkSuggestion."""
        from api.services.auto_linker import LinkSuggestion, IdentifierMatch

        matches = [
            IdentifierMatch(
                identifier_type="email",
                path="core.email",
                value="test@example.com",
                weight=3.0
            )
        ]

        suggestion = LinkSuggestion(
            source_entity_id="entity-1",
            target_entity_id="entity-2",
            target_entity_name="John Doe",
            matching_identifiers=matches,
            confidence_score=3.0,
            suggested_relationship_type="POTENTIAL_DUPLICATE"
        )

        assert suggestion.source_entity_id == "entity-1"
        assert suggestion.confidence_score == 3.0
        assert len(suggestion.matching_identifiers) == 1

    def test_link_suggestion_to_dict(self):
        """Test converting LinkSuggestion to dictionary."""
        from api.services.auto_linker import LinkSuggestion, IdentifierMatch

        matches = [
            IdentifierMatch(
                identifier_type="email",
                path="core.email",
                value="test@example.com",
                weight=3.0
            )
        ]

        suggestion = LinkSuggestion(
            source_entity_id="entity-1",
            target_entity_id="entity-2",
            target_entity_name="John Doe",
            matching_identifiers=matches,
            confidence_score=3.0,
            suggested_relationship_type="SHARED_IDENTIFIER"
        )

        result = suggestion.to_dict()

        assert isinstance(result, dict)
        assert result["source_entity_id"] == "entity-1"
        assert result["target_entity_id"] == "entity-2"
        assert len(result["matching_identifiers"]) == 1
        assert result["matching_identifiers"][0]["value"] == "test@example.com"


class TestAutoLinkerEndpoints:
    """Tests for auto-linker API endpoints."""

    @pytest.fixture
    def mock_handler_with_auto_linker(self, mock_neo4j_handler):
        """Extend mock handler for auto-linker tests."""
        mock_neo4j_handler.get_all_people.return_value = [
            {
                "id": "entity-1",
                "profile": {
                    "core": {
                        "name": [{"first_name": "John", "last_name": "Doe"}],
                        "email": ["john@example.com"]
                    }
                }
            },
            {
                "id": "entity-2",
                "profile": {
                    "core": {
                        "name": [{"first_name": "John", "last_name": "Doe"}],
                        "email": ["john@example.com"]  # Same email
                    }
                }
            }
        ]
        return mock_neo4j_handler

    def test_get_link_suggestions(self, mock_handler_with_auto_linker):
        """Test getting link suggestions for an entity."""
        client = get_test_client(mock_handler_with_auto_linker)

        response = client.get(
            "/api/v1/projects/test_project/auto-link/entities/entity-1/suggested-links"
        )

        assert response.status_code == 200
        data = response.json()
        assert "entity_id" in data
        assert "potential_duplicates" in data
        assert "suggested_links" in data

    def test_scan_project_for_links(self, mock_handler_with_auto_linker):
        """Test scanning entire project for link suggestions."""
        client = get_test_client(mock_handler_with_auto_linker)

        response = client.post(
            "/api/v1/projects/test_project/auto-link/scan"
        )

        assert response.status_code == 200
        data = response.json()
        assert "entities_scanned" in data
        assert "potential_duplicates" in data
        assert "suggested_links" in data

    def test_get_identifier_fields_endpoint(self, mock_handler_with_auto_linker):
        """Test getting configured identifier fields."""
        client = get_test_client(mock_handler_with_auto_linker)

        response = client.get(
            "/api/v1/projects/test_project/auto-link/identifier-fields"
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_merge_entities_endpoint(self, mock_handler_with_auto_linker):
        """Test entity merge endpoint."""
        mock_handler_with_auto_linker.update_person.return_value = {
            "id": "entity-1",
            "profile": {}
        }
        mock_handler_with_auto_linker.delete_person.return_value = True

        client = get_test_client(mock_handler_with_auto_linker)

        response = client.post(
            "/api/v1/projects/test_project/auto-link/merge",
            json={
                "primary_entity_id": "entity-1",
                "secondary_entity_id": "entity-2",
                "delete_secondary": True
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True or "error" not in data


class TestIdentifierMatchDataclass:
    """Tests for IdentifierMatch dataclass."""

    def test_identifier_match_creation(self):
        """Test creating an IdentifierMatch."""
        from api.services.auto_linker import IdentifierMatch

        match = IdentifierMatch(
            identifier_type="email",
            path="core.email",
            value="test@example.com",
            weight=3.0
        )

        assert match.identifier_type == "email"
        assert match.path == "core.email"
        assert match.value == "test@example.com"
        assert match.weight == 3.0

    def test_identifier_match_default_weight(self):
        """Test default weight for IdentifierMatch."""
        from api.services.auto_linker import IdentifierMatch

        match = IdentifierMatch(
            identifier_type="unknown",
            path="section.field",
            value="value"
        )

        assert match.weight == 1.0


class TestAutoLinkerSingleton:
    """Tests for AutoLinker singleton pattern."""

    def test_get_auto_linker_singleton(self, mock_neo4j_handler):
        """Test get_auto_linker returns same instance."""
        from api.services.auto_linker import get_auto_linker, _auto_linker_instance

        # Reset singleton
        import api.services.auto_linker as module
        module._auto_linker_instance = None

        linker1 = get_auto_linker(mock_neo4j_handler)
        linker2 = get_auto_linker()

        assert linker1 is linker2

    def test_get_auto_linker_updates_handler(self, mock_neo4j_handler):
        """Test that passing a new handler updates the singleton."""
        from api.services.auto_linker import get_auto_linker

        import api.services.auto_linker as module
        module._auto_linker_instance = None

        linker = get_auto_linker(mock_neo4j_handler)
        assert linker.neo4j_handler is mock_neo4j_handler

        new_handler = MagicMock()
        linker = get_auto_linker(new_handler)
        assert linker.neo4j_handler is new_handler
