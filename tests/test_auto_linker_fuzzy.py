"""
Tests for auto-linker fuzzy matching integration.

These tests cover the Phase 5+ fuzzy matching features:
- Finding fuzzy matches by name similarity
- Combined identifier + fuzzy matching
- Threshold configuration
- Edge cases and error handling
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


class TestFuzzyMatchConfig:
    """Tests for FuzzyMatchConfig dataclass."""

    def test_default_config(self):
        """Test default fuzzy match configuration."""
        from api.services.auto_linker import FuzzyMatchConfig

        config = FuzzyMatchConfig()

        assert config.fuzzy_matching_enabled is True
        assert config.fuzzy_threshold == 0.85
        assert config.fuzzy_fields == ["core.name", "core.alias"]

    def test_custom_config(self):
        """Test custom fuzzy match configuration."""
        from api.services.auto_linker import FuzzyMatchConfig

        config = FuzzyMatchConfig(
            fuzzy_matching_enabled=False,
            fuzzy_threshold=0.90,
            fuzzy_fields=["core.name", "social.twitter.handle"]
        )

        assert config.fuzzy_matching_enabled is False
        assert config.fuzzy_threshold == 0.90
        assert "social.twitter.handle" in config.fuzzy_fields


class TestAutoLinkerFuzzyIntegration:
    """Tests for AutoLinker fuzzy matching integration."""

    @pytest.fixture
    def mock_fuzzy_matcher(self):
        """Create a mock FuzzyMatcher."""
        matcher = MagicMock()
        matcher.calculate_similarity.return_value = 0.92
        matcher.phonetic_match.return_value = (False, 0.0)
        matcher.normalize_name.side_effect = lambda x: x.lower().strip()
        return matcher

    @pytest.fixture
    def sample_entities_fuzzy(self):
        """Sample entities for fuzzy matching tests."""
        return [
            {
                "id": "entity-1",
                "profile": {
                    "core": {
                        "name": [{"first_name": "John", "last_name": "Doe"}],
                        "alias": ["JohnD", "johndoe"]
                    }
                }
            },
            {
                "id": "entity-2",
                "profile": {
                    "core": {
                        "name": [{"first_name": "Jon", "last_name": "Doe"}],  # Similar name
                        "alias": ["JonD"]
                    }
                }
            },
            {
                "id": "entity-3",
                "profile": {
                    "core": {
                        "name": [{"first_name": "Jane", "last_name": "Smith"}],
                        "alias": ["janesmith"]
                    }
                }
            },
            {
                "id": "entity-4",
                "profile": {
                    "core": {
                        "name": [{"first_name": "John", "middle_name": "M", "last_name": "Doe"}],
                        "alias": ["john.doe"]
                    }
                }
            },
            {
                "id": "entity-5",
                "profile": {
                    "core": {
                        "name": [{"first_name": "Johan", "last_name": "Doe"}],  # Phonetic similar
                        "alias": []
                    }
                }
            }
        ]

    def test_is_fuzzy_matching_available(self, mock_neo4j_handler):
        """Test fuzzy matching availability check."""
        from api.services.auto_linker import AutoLinker, FuzzyMatchConfig, FUZZY_MATCHING_AVAILABLE

        config = FuzzyMatchConfig(fuzzy_matching_enabled=True)
        linker = AutoLinker(mock_neo4j_handler, fuzzy_config=config)

        # If rapidfuzz is installed, it should be available
        if FUZZY_MATCHING_AVAILABLE:
            assert linker.is_fuzzy_matching_available() is True
        else:
            assert linker.is_fuzzy_matching_available() is False

    def test_is_fuzzy_matching_disabled(self, mock_neo4j_handler):
        """Test fuzzy matching when disabled."""
        from api.services.auto_linker import AutoLinker, FuzzyMatchConfig

        config = FuzzyMatchConfig(fuzzy_matching_enabled=False)
        linker = AutoLinker(mock_neo4j_handler, fuzzy_config=config)

        # Should be unavailable when disabled
        assert linker.is_fuzzy_matching_available() is False

    def test_extract_field_values_name(self, mock_neo4j_handler, sample_entities_fuzzy):
        """Test extracting name field values."""
        from api.services.auto_linker import AutoLinker

        linker = AutoLinker(mock_neo4j_handler)
        entity = sample_entities_fuzzy[0]

        values = linker._extract_field_values(entity, "core.name")

        assert len(values) == 1
        assert "John" in values[0]
        assert "Doe" in values[0]

    def test_extract_field_values_with_middle_name(self, mock_neo4j_handler, sample_entities_fuzzy):
        """Test extracting name with middle name."""
        from api.services.auto_linker import AutoLinker

        linker = AutoLinker(mock_neo4j_handler)
        entity = sample_entities_fuzzy[3]  # entity-4 has middle name

        values = linker._extract_field_values(entity, "core.name")

        assert len(values) == 1
        assert "John" in values[0]
        assert "M" in values[0]
        assert "Doe" in values[0]

    def test_extract_field_values_alias(self, mock_neo4j_handler, sample_entities_fuzzy):
        """Test extracting alias field values."""
        from api.services.auto_linker import AutoLinker

        linker = AutoLinker(mock_neo4j_handler)
        entity = sample_entities_fuzzy[0]

        values = linker._extract_field_values(entity, "core.alias")

        assert len(values) == 2
        assert "JohnD" in values
        assert "johndoe" in values

    def test_extract_field_values_empty(self, mock_neo4j_handler):
        """Test extracting from empty profile."""
        from api.services.auto_linker import AutoLinker

        linker = AutoLinker(mock_neo4j_handler)
        entity = {"id": "empty", "profile": {}}

        values = linker._extract_field_values(entity, "core.name")

        assert values == []

    def test_extract_field_values_missing_field(self, mock_neo4j_handler, sample_entities_fuzzy):
        """Test extracting non-existent field."""
        from api.services.auto_linker import AutoLinker

        linker = AutoLinker(mock_neo4j_handler)
        entity = sample_entities_fuzzy[0]

        values = linker._extract_field_values(entity, "nonexistent.field")

        assert values == []

    @pytest.mark.skipif(
        not pytest.importorskip("rapidfuzz", reason="rapidfuzz not installed"),
        reason="rapidfuzz not installed"
    )
    def test_find_fuzzy_matches_similar_names(self, mock_neo4j_handler, sample_entities_fuzzy):
        """Test finding fuzzy matches for similar names."""
        from api.services.auto_linker import AutoLinker, FuzzyMatchConfig

        mock_neo4j_handler.get_person.return_value = sample_entities_fuzzy[0]
        mock_neo4j_handler.get_all_people.return_value = sample_entities_fuzzy

        config = FuzzyMatchConfig(
            fuzzy_matching_enabled=True,
            fuzzy_threshold=0.80,
            fuzzy_fields=["core.name"]
        )
        linker = AutoLinker(mock_neo4j_handler, fuzzy_config=config)

        if not linker.is_fuzzy_matching_available():
            pytest.skip("Fuzzy matching not available")

        suggestions = linker.find_fuzzy_matches(
            "test_project",
            "entity-1",
            threshold=0.80
        )

        # Should find similar names (Jon Doe, John M Doe, Johan Doe)
        assert len(suggestions) > 0

        # Check that similar entities are found
        target_ids = [s.target_entity_id for s in suggestions]
        assert "entity-2" in target_ids or "entity-4" in target_ids

    @pytest.mark.skipif(
        not pytest.importorskip("rapidfuzz", reason="rapidfuzz not installed"),
        reason="rapidfuzz not installed"
    )
    def test_find_fuzzy_matches_threshold(self, mock_neo4j_handler, sample_entities_fuzzy):
        """Test threshold configuration for fuzzy matches."""
        from api.services.auto_linker import AutoLinker, FuzzyMatchConfig

        mock_neo4j_handler.get_person.return_value = sample_entities_fuzzy[0]
        mock_neo4j_handler.get_all_people.return_value = sample_entities_fuzzy

        config = FuzzyMatchConfig(fuzzy_matching_enabled=True, fuzzy_threshold=0.95)
        linker = AutoLinker(mock_neo4j_handler, fuzzy_config=config)

        if not linker.is_fuzzy_matching_available():
            pytest.skip("Fuzzy matching not available")

        # High threshold should find fewer matches
        high_threshold_suggestions = linker.find_fuzzy_matches(
            "test_project", "entity-1", threshold=0.99
        )

        low_threshold_suggestions = linker.find_fuzzy_matches(
            "test_project", "entity-1", threshold=0.50
        )

        # Lower threshold should generally find more matches
        assert len(low_threshold_suggestions) >= len(high_threshold_suggestions)

    @pytest.mark.skipif(
        not pytest.importorskip("rapidfuzz", reason="rapidfuzz not installed"),
        reason="rapidfuzz not installed"
    )
    def test_find_fuzzy_matches_custom_fields(self, mock_neo4j_handler, sample_entities_fuzzy):
        """Test fuzzy matching with custom fields."""
        from api.services.auto_linker import AutoLinker, FuzzyMatchConfig

        mock_neo4j_handler.get_person.return_value = sample_entities_fuzzy[0]
        mock_neo4j_handler.get_all_people.return_value = sample_entities_fuzzy

        config = FuzzyMatchConfig(fuzzy_matching_enabled=True)
        linker = AutoLinker(mock_neo4j_handler, fuzzy_config=config)

        if not linker.is_fuzzy_matching_available():
            pytest.skip("Fuzzy matching not available")

        # Match only on alias
        suggestions = linker.find_fuzzy_matches(
            "test_project",
            "entity-1",
            fields=["core.alias"],
            threshold=0.70
        )

        # All matches should be from alias field
        for suggestion in suggestions:
            if suggestion.fuzzy_matches:
                for match in suggestion.fuzzy_matches:
                    assert match["field_path"] == "core.alias"

    def test_find_fuzzy_matches_no_database(self, mock_neo4j_handler):
        """Test fuzzy matching without database handler."""
        from api.services.auto_linker import AutoLinker

        linker = AutoLinker(neo4j_handler=None)
        suggestions = linker.find_fuzzy_matches("test_project", "entity-1")

        assert suggestions == []

    def test_find_fuzzy_matches_entity_not_found(self, mock_neo4j_handler):
        """Test fuzzy matching when entity not found."""
        from api.services.auto_linker import AutoLinker

        mock_neo4j_handler.get_person.return_value = None
        linker = AutoLinker(mock_neo4j_handler)

        suggestions = linker.find_fuzzy_matches("test_project", "nonexistent")

        assert suggestions == []

    @pytest.mark.skipif(
        not pytest.importorskip("rapidfuzz", reason="rapidfuzz not installed"),
        reason="rapidfuzz not installed"
    )
    def test_find_combined_matches(self, mock_neo4j_handler, sample_entities_fuzzy):
        """Test combined identifier and fuzzy matching."""
        from api.services.auto_linker import AutoLinker, FuzzyMatchConfig

        # Entity with both identifier and name match
        entities = sample_entities_fuzzy.copy()
        entities[1]["profile"]["core"]["email"] = ["john.doe@example.com"]
        entities[0]["profile"]["core"]["email"] = ["john.doe@example.com"]

        mock_neo4j_handler.get_person.return_value = entities[0]
        mock_neo4j_handler.get_all_people.return_value = entities

        config = FuzzyMatchConfig(fuzzy_matching_enabled=True, fuzzy_threshold=0.80)
        linker = AutoLinker(mock_neo4j_handler, fuzzy_config=config)

        # Set up identifier paths for email
        linker.identifier_paths = [
            {
                "path": "core.email",
                "section_id": "core",
                "field_id": "email",
                "component_id": None,
                "field_type": "email",
                "multiple": True
            }
        ]

        if not linker.is_fuzzy_matching_available():
            pytest.skip("Fuzzy matching not available")

        suggestions = linker.find_combined_matches(
            "test_project",
            "entity-1",
            min_confidence=0.5
        )

        # Should find matches from both identifier and fuzzy matching
        assert len(suggestions) > 0

    @pytest.mark.skipif(
        not pytest.importorskip("rapidfuzz", reason="rapidfuzz not installed"),
        reason="rapidfuzz not installed"
    )
    def test_fuzzy_match_confidence_score(self, mock_neo4j_handler, sample_entities_fuzzy):
        """Test confidence score calculation for fuzzy matches."""
        from api.services.auto_linker import AutoLinker, FuzzyMatchConfig

        mock_neo4j_handler.get_person.return_value = sample_entities_fuzzy[0]
        mock_neo4j_handler.get_all_people.return_value = sample_entities_fuzzy

        config = FuzzyMatchConfig(fuzzy_matching_enabled=True, fuzzy_threshold=0.50)
        linker = AutoLinker(mock_neo4j_handler, fuzzy_config=config)

        if not linker.is_fuzzy_matching_available():
            pytest.skip("Fuzzy matching not available")

        suggestions = linker.find_fuzzy_matches("test_project", "entity-1", threshold=0.50)

        for suggestion in suggestions:
            # Confidence should be between 0 and 1
            assert 0 <= suggestion.confidence_score <= 1.0

            # Should have appropriate relationship type
            assert suggestion.suggested_relationship_type in [
                "POTENTIAL_DUPLICATE", "SIMILAR_NAME", "POSSIBLE_MATCH"
            ]

    @pytest.mark.skipif(
        not pytest.importorskip("rapidfuzz", reason="rapidfuzz not installed"),
        reason="rapidfuzz not installed"
    )
    def test_fuzzy_match_includes_details(self, mock_neo4j_handler, sample_entities_fuzzy):
        """Test that fuzzy matches include detailed match information."""
        from api.services.auto_linker import AutoLinker, FuzzyMatchConfig

        mock_neo4j_handler.get_person.return_value = sample_entities_fuzzy[0]
        mock_neo4j_handler.get_all_people.return_value = sample_entities_fuzzy

        config = FuzzyMatchConfig(fuzzy_matching_enabled=True, fuzzy_threshold=0.70)
        linker = AutoLinker(mock_neo4j_handler, fuzzy_config=config)

        if not linker.is_fuzzy_matching_available():
            pytest.skip("Fuzzy matching not available")

        suggestions = linker.find_fuzzy_matches("test_project", "entity-1", threshold=0.70)

        for suggestion in suggestions:
            assert suggestion.fuzzy_matches is not None

            for match in suggestion.fuzzy_matches:
                assert "field_path" in match
                assert "source_value" in match
                assert "target_value" in match
                assert "similarity" in match
                assert "match_type" in match
                assert match["match_type"] in ["exact", "fuzzy", "phonetic"]


class TestFuzzyMatchEndpoints:
    """Tests for fuzzy matching API endpoints."""

    @pytest.fixture
    def mock_handler_with_fuzzy(self, mock_neo4j_handler):
        """Extend mock handler for fuzzy matching tests."""
        mock_neo4j_handler.get_all_people.return_value = [
            {
                "id": "entity-1",
                "profile": {
                    "core": {
                        "name": [{"first_name": "John", "last_name": "Doe"}],
                        "alias": ["johndoe"]
                    }
                }
            },
            {
                "id": "entity-2",
                "profile": {
                    "core": {
                        "name": [{"first_name": "Jon", "last_name": "Doe"}],
                        "alias": ["jondoe"]
                    }
                }
            }
        ]
        return mock_neo4j_handler

    def test_get_fuzzy_matches_endpoint(self, mock_handler_with_fuzzy):
        """Test getting fuzzy matches for an entity."""
        client = get_test_client(mock_handler_with_fuzzy)

        response = client.get(
            "/api/v1/projects/test_project/auto-link/entities/entity-1/fuzzy-matches"
        )

        assert response.status_code == 200
        data = response.json()

        assert "entity_id" in data
        assert data["entity_id"] == "entity-1"
        assert "project_id" in data
        assert "fuzzy_matching_enabled" in data
        assert "threshold" in data
        assert "fields" in data
        assert "matches" in data
        assert "count" in data

    def test_get_fuzzy_matches_with_threshold(self, mock_handler_with_fuzzy):
        """Test fuzzy matches with custom threshold."""
        client = get_test_client(mock_handler_with_fuzzy)

        response = client.get(
            "/api/v1/projects/test_project/auto-link/entities/entity-1/fuzzy-matches",
            params={"threshold": 0.90}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["threshold"] == 0.90

    def test_get_fuzzy_matches_with_fields(self, mock_handler_with_fuzzy):
        """Test fuzzy matches with custom fields."""
        client = get_test_client(mock_handler_with_fuzzy)

        response = client.get(
            "/api/v1/projects/test_project/auto-link/entities/entity-1/fuzzy-matches",
            params={"fields": "core.name,core.alias"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "core.name" in data["fields"]
        assert "core.alias" in data["fields"]

    def test_get_fuzzy_matches_entity_not_found(self, mock_handler_with_fuzzy):
        """Test fuzzy matches for non-existent entity."""
        mock_handler_with_fuzzy.get_person.return_value = None

        client = get_test_client(mock_handler_with_fuzzy)

        response = client.get(
            "/api/v1/projects/test_project/auto-link/entities/nonexistent/fuzzy-matches"
        )

        assert response.status_code == 404

    def test_get_fuzzy_config_endpoint(self, mock_handler_with_fuzzy):
        """Test getting fuzzy matching configuration."""
        client = get_test_client(mock_handler_with_fuzzy)

        response = client.get(
            "/api/v1/projects/test_project/auto-link/fuzzy-config"
        )

        assert response.status_code == 200
        data = response.json()

        assert "fuzzy_matching_available" in data
        assert "fuzzy_matching_enabled" in data
        assert "fuzzy_threshold" in data
        assert "fuzzy_fields" in data

    def test_get_fuzzy_config_project_not_found(self, mock_handler_with_fuzzy):
        """Test fuzzy config for non-existent project."""
        mock_handler_with_fuzzy.get_project.return_value = None

        client = get_test_client(mock_handler_with_fuzzy)

        response = client.get(
            "/api/v1/projects/nonexistent/auto-link/fuzzy-config"
        )

        assert response.status_code == 404


class TestLinkSuggestionWithFuzzy:
    """Tests for LinkSuggestion with fuzzy matches."""

    def test_link_suggestion_with_fuzzy_matches(self):
        """Test LinkSuggestion includes fuzzy matches."""
        from api.services.auto_linker import LinkSuggestion

        fuzzy_matches = [
            {
                "field_path": "core.name",
                "source_value": "John Doe",
                "target_value": "Jon Doe",
                "similarity": 0.92,
                "match_type": "fuzzy"
            }
        ]

        suggestion = LinkSuggestion(
            source_entity_id="entity-1",
            target_entity_id="entity-2",
            target_entity_name="Jon Doe",
            matching_identifiers=[],
            confidence_score=0.92,
            suggested_relationship_type="SIMILAR_NAME",
            fuzzy_matches=fuzzy_matches
        )

        assert suggestion.fuzzy_matches == fuzzy_matches

    def test_link_suggestion_to_dict_with_fuzzy(self):
        """Test LinkSuggestion.to_dict includes fuzzy matches."""
        from api.services.auto_linker import LinkSuggestion

        fuzzy_matches = [
            {
                "field_path": "core.name",
                "source_value": "John Doe",
                "target_value": "Jon Doe",
                "similarity": 0.92,
                "match_type": "fuzzy"
            }
        ]

        suggestion = LinkSuggestion(
            source_entity_id="entity-1",
            target_entity_id="entity-2",
            target_entity_name="Jon Doe",
            matching_identifiers=[],
            confidence_score=0.92,
            suggested_relationship_type="SIMILAR_NAME",
            fuzzy_matches=fuzzy_matches
        )

        result = suggestion.to_dict()

        assert "fuzzy_matches" in result
        assert len(result["fuzzy_matches"]) == 1
        assert result["fuzzy_matches"][0]["similarity"] == 0.92

    def test_link_suggestion_to_dict_without_fuzzy(self):
        """Test LinkSuggestion.to_dict without fuzzy matches."""
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

        # Should not include fuzzy_matches key when None
        assert "fuzzy_matches" not in result


class TestEdgeCases:
    """Edge case tests for fuzzy matching."""

    def test_empty_entity_list(self, mock_neo4j_handler):
        """Test fuzzy matching with empty entity list."""
        from api.services.auto_linker import AutoLinker

        mock_neo4j_handler.get_person.return_value = {
            "id": "entity-1",
            "profile": {"core": {"name": [{"first_name": "John", "last_name": "Doe"}]}}
        }
        mock_neo4j_handler.get_all_people.return_value = []

        linker = AutoLinker(mock_neo4j_handler)
        suggestions = linker.find_fuzzy_matches("test_project", "entity-1")

        assert suggestions == []

    def test_single_entity(self, mock_neo4j_handler):
        """Test fuzzy matching with only one entity."""
        from api.services.auto_linker import AutoLinker

        entity = {
            "id": "entity-1",
            "profile": {"core": {"name": [{"first_name": "John", "last_name": "Doe"}]}}
        }

        mock_neo4j_handler.get_person.return_value = entity
        mock_neo4j_handler.get_all_people.return_value = [entity]

        linker = AutoLinker(mock_neo4j_handler)
        suggestions = linker.find_fuzzy_matches("test_project", "entity-1")

        # Should not match itself
        assert suggestions == []

    def test_entity_with_no_matchable_fields(self, mock_neo4j_handler):
        """Test entity with no fields to match on."""
        from api.services.auto_linker import AutoLinker, FuzzyMatchConfig

        entity = {
            "id": "entity-1",
            "profile": {"other_section": {"data": "value"}}
        }

        mock_neo4j_handler.get_person.return_value = entity
        mock_neo4j_handler.get_all_people.return_value = [entity]

        config = FuzzyMatchConfig(fuzzy_fields=["core.name", "core.alias"])
        linker = AutoLinker(mock_neo4j_handler, fuzzy_config=config)

        suggestions = linker.find_fuzzy_matches("test_project", "entity-1")

        assert suggestions == []

    def test_unicode_names(self, mock_neo4j_handler):
        """Test fuzzy matching with unicode names."""
        from api.services.auto_linker import AutoLinker, FuzzyMatchConfig, FUZZY_MATCHING_AVAILABLE

        if not FUZZY_MATCHING_AVAILABLE:
            pytest.skip("Fuzzy matching not available")

        entities = [
            {
                "id": "entity-1",
                "profile": {"core": {"name": [{"first_name": "Jose", "last_name": "Garcia"}]}}
            },
            {
                "id": "entity-2",
                "profile": {"core": {"name": [{"first_name": "Jose", "last_name": "Garcia"}]}}
            }
        ]

        mock_neo4j_handler.get_person.return_value = entities[0]
        mock_neo4j_handler.get_all_people.return_value = entities

        config = FuzzyMatchConfig(fuzzy_matching_enabled=True, fuzzy_threshold=0.70)
        linker = AutoLinker(mock_neo4j_handler, fuzzy_config=config)

        suggestions = linker.find_fuzzy_matches("test_project", "entity-1", threshold=0.70)

        # Should find exact match
        assert len(suggestions) >= 1

    def test_very_short_names(self, mock_neo4j_handler):
        """Test fuzzy matching with very short names."""
        from api.services.auto_linker import AutoLinker, FuzzyMatchConfig, FUZZY_MATCHING_AVAILABLE

        if not FUZZY_MATCHING_AVAILABLE:
            pytest.skip("Fuzzy matching not available")

        entities = [
            {
                "id": "entity-1",
                "profile": {"core": {"name": [{"first_name": "Jo", "last_name": "Do"}]}}
            },
            {
                "id": "entity-2",
                "profile": {"core": {"name": [{"first_name": "Jo", "last_name": "Da"}]}}
            }
        ]

        mock_neo4j_handler.get_person.return_value = entities[0]
        mock_neo4j_handler.get_all_people.return_value = entities

        config = FuzzyMatchConfig(fuzzy_matching_enabled=True, fuzzy_threshold=0.50)
        linker = AutoLinker(mock_neo4j_handler, fuzzy_config=config)

        # Should handle short names without error
        suggestions = linker.find_fuzzy_matches("test_project", "entity-1", threshold=0.50)
        assert isinstance(suggestions, list)

    def test_empty_name_fields(self, mock_neo4j_handler):
        """Test handling of empty name fields."""
        from api.services.auto_linker import AutoLinker

        entities = [
            {
                "id": "entity-1",
                "profile": {"core": {"name": [{"first_name": "", "last_name": ""}]}}
            },
            {
                "id": "entity-2",
                "profile": {"core": {"name": []}}
            }
        ]

        mock_neo4j_handler.get_person.return_value = entities[0]
        mock_neo4j_handler.get_all_people.return_value = entities

        linker = AutoLinker(mock_neo4j_handler)

        # Should handle empty names without error
        suggestions = linker.find_fuzzy_matches("test_project", "entity-1")
        assert isinstance(suggestions, list)
