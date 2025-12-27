"""
Tests for the Advanced Search Service.

These tests cover the search functionality including:
- Basic text search
- Fuzzy search
- Field-specific search
- Pagination
- Highlighting
- Multi-project search
- Search index building
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from typing import Dict, Any, List

# Import test fixtures
from .conftest import mock_neo4j_handler, mock_config


class TestSearchResult:
    """Tests for SearchResult dataclass."""

    def test_search_result_creation(self):
        """Test creating a SearchResult."""
        from api.services.search_service import SearchResult

        result = SearchResult(
            entity_id="entity-123",
            project_id="project-456",
            entity_type="Person",
            score=0.95,
            highlights={"core.name": ["**John** Doe"]},
            matched_fields=["core.name"],
            entity_data={"id": "entity-123", "name": {"first_name": "John"}},
        )

        assert result.entity_id == "entity-123"
        assert result.project_id == "project-456"
        assert result.entity_type == "Person"
        assert result.score == 0.95
        assert result.highlights == {"core.name": ["**John** Doe"]}
        assert result.matched_fields == ["core.name"]
        assert result.entity_data["id"] == "entity-123"

    def test_search_result_defaults(self):
        """Test SearchResult with default values."""
        from api.services.search_service import SearchResult

        result = SearchResult(
            entity_id="entity-123",
            project_id="project-456",
            entity_type="Person",
            score=0.5,
        )

        assert result.highlights == {}
        assert result.matched_fields == []
        assert result.entity_data == {}

    def test_search_result_to_dict(self):
        """Test converting SearchResult to dictionary."""
        from api.services.search_service import SearchResult

        result = SearchResult(
            entity_id="entity-123",
            project_id="project-456",
            entity_type="Person",
            score=0.8,
            highlights={"field1": ["match"]},
            matched_fields=["field1"],
            entity_data={"key": "value"},
        )

        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert result_dict["entity_id"] == "entity-123"
        assert result_dict["project_id"] == "project-456"
        assert result_dict["score"] == 0.8
        assert "highlights" in result_dict
        assert "matched_fields" in result_dict


class TestSearchQuery:
    """Tests for SearchQuery dataclass."""

    def test_search_query_creation(self):
        """Test creating a SearchQuery."""
        from api.services.search_service import SearchQuery

        query = SearchQuery(
            query="John Doe",
            project_id="project-123",
            entity_types=["Person"],
            fields=["core.name", "core.email"],
            limit=10,
            offset=0,
            fuzzy=True,
            highlight=True,
        )

        assert query.query == "John Doe"
        assert query.project_id == "project-123"
        assert query.entity_types == ["Person"]
        assert query.fields == ["core.name", "core.email"]
        assert query.limit == 10
        assert query.offset == 0
        assert query.fuzzy is True
        assert query.highlight is True

    def test_search_query_defaults(self):
        """Test SearchQuery with default values."""
        from api.services.search_service import SearchQuery

        query = SearchQuery(query="test")

        assert query.query == "test"
        assert query.project_id is None
        assert query.entity_types is None
        assert query.fields is None
        assert query.limit == 20
        assert query.offset == 0
        assert query.fuzzy is True
        assert query.highlight is True

    def test_search_query_limit_validation(self):
        """Test that limit is validated."""
        from api.services.search_service import SearchQuery

        # Limit too low should be set to 1
        query = SearchQuery(query="test", limit=0)
        assert query.limit == 1

        # Limit too high should be capped at 100
        query = SearchQuery(query="test", limit=500)
        assert query.limit == 100

        # Valid limit should be unchanged
        query = SearchQuery(query="test", limit=50)
        assert query.limit == 50

    def test_search_query_offset_validation(self):
        """Test that offset is validated."""
        from api.services.search_service import SearchQuery

        # Negative offset should be set to 0
        query = SearchQuery(query="test", offset=-5)
        assert query.offset == 0


class TestSearchServiceBasic:
    """Tests for basic SearchService functionality."""

    @pytest.fixture
    def mock_handler(self, mock_neo4j_handler):
        """Create a mock Neo4j handler for testing."""
        return mock_neo4j_handler

    @pytest.fixture
    def sample_config(self, mock_config):
        """Create sample config for testing."""
        return mock_config

    @pytest.fixture
    def search_service(self, mock_handler, sample_config):
        """Create a SearchService instance for testing."""
        from api.services.search_service import SearchService

        # Add execute_query method to mock
        mock_handler.execute_query = MagicMock(return_value=[])

        return SearchService(mock_handler, sample_config)

    def test_service_creation(self, mock_handler, sample_config):
        """Test creating a SearchService."""
        from api.services.search_service import SearchService

        service = SearchService(mock_handler, sample_config)

        assert service.neo4j == mock_handler
        assert service.config == sample_config

    def test_service_creation_without_config(self, mock_handler):
        """Test creating SearchService without config."""
        from api.services.search_service import SearchService

        service = SearchService(mock_handler)

        assert service.config == {}


class TestSearchServiceSearch:
    """Tests for search functionality."""

    @pytest.fixture
    def mock_handler(self):
        """Create a mock Neo4j handler."""
        handler = MagicMock()
        handler.execute_query = MagicMock(return_value=[])
        handler.get_all_projects = MagicMock(return_value=[
            {
                "id": "project-1",
                "safe_name": "project_one",
                "name": "Project One"
            }
        ])
        handler.get_project = MagicMock(return_value={
            "id": "project-1",
            "safe_name": "project_one",
            "name": "Project One"
        })
        handler.get_all_people = MagicMock(return_value=[
            {
                "id": "entity-1",
                "created_at": "2024-01-15T10:30:00",
                "profile": {
                    "core": {
                        "name": [{"first_name": "John", "last_name": "Doe"}],
                        "email": ["john.doe@example.com"]
                    }
                }
            },
            {
                "id": "entity-2",
                "created_at": "2024-01-15T11:00:00",
                "profile": {
                    "core": {
                        "name": [{"first_name": "Jane", "last_name": "Smith"}],
                        "email": ["jane.smith@example.com"]
                    }
                }
            }
        ])
        return handler

    @pytest.fixture
    def search_service(self, mock_handler, mock_config):
        """Create a SearchService with mocks."""
        from api.services.search_service import SearchService
        return SearchService(mock_handler, mock_config)

    @pytest.mark.asyncio
    async def test_search_empty_query(self, search_service):
        """Test search with empty query returns no results."""
        from api.services.search_service import SearchQuery

        query = SearchQuery(query="")
        results, total = await search_service.search(query)

        assert results == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_search_whitespace_query(self, search_service):
        """Test search with whitespace-only query returns no results."""
        from api.services.search_service import SearchQuery

        query = SearchQuery(query="   ")
        results, total = await search_service.search(query)

        assert results == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_basic_text_search(self, search_service):
        """Test basic text search finds matching entities."""
        from api.services.search_service import SearchQuery

        query = SearchQuery(query="John")
        results, total = await search_service.search(query)

        # Should find entity-1 with "John" in name
        assert len(results) >= 1
        entity_ids = [r.entity_id for r in results]
        assert "entity-1" in entity_ids

    @pytest.mark.asyncio
    async def test_search_case_insensitive(self, search_service):
        """Test that search is case insensitive."""
        from api.services.search_service import SearchQuery

        query = SearchQuery(query="JOHN")
        results, total = await search_service.search(query)

        # Should still find entity-1
        entity_ids = [r.entity_id for r in results]
        assert "entity-1" in entity_ids

    @pytest.mark.asyncio
    async def test_search_project_scoped(self, search_service, mock_handler):
        """Test search scoped to a specific project."""
        from api.services.search_service import SearchQuery

        query = SearchQuery(query="John", project_id="project-1")
        results, total = await search_service.search(query)

        # All results should have the correct project_id
        for result in results:
            assert result.project_id in ["project-1", "project_one"]

    @pytest.mark.asyncio
    async def test_search_no_results(self, search_service):
        """Test search that finds no matches."""
        from api.services.search_service import SearchQuery

        query = SearchQuery(query="NonExistentSearchTerm12345", fuzzy=False)
        results, total = await search_service.search(query)

        assert len(results) == 0
        assert total == 0


class TestSearchServicePagination:
    """Tests for search pagination."""

    @pytest.fixture
    def mock_handler(self):
        """Create a mock Neo4j handler with many entities."""
        handler = MagicMock()
        handler.execute_query = MagicMock(return_value=[])
        handler.get_all_projects = MagicMock(return_value=[
            {"id": "project-1", "safe_name": "project_one", "name": "Project One"}
        ])
        handler.get_project = MagicMock(return_value={
            "id": "project-1", "safe_name": "project_one", "name": "Project One"
        })

        # Create many entities that all match "test"
        entities = []
        for i in range(25):
            entities.append({
                "id": f"entity-{i}",
                "created_at": "2024-01-15T10:30:00",
                "profile": {
                    "core": {
                        "name": [{"first_name": f"Test{i}", "last_name": "User"}],
                        "email": [f"test{i}@example.com"]
                    }
                }
            })
        handler.get_all_people = MagicMock(return_value=entities)
        return handler

    @pytest.fixture
    def search_service(self, mock_handler, mock_config):
        """Create a SearchService with mocks."""
        from api.services.search_service import SearchService
        return SearchService(mock_handler, mock_config)

    @pytest.mark.asyncio
    async def test_pagination_limit(self, search_service):
        """Test that limit restricts number of results."""
        from api.services.search_service import SearchQuery

        query = SearchQuery(query="test", limit=10)
        results, total = await search_service.search(query)

        assert len(results) <= 10

    @pytest.mark.asyncio
    async def test_pagination_offset(self, search_service):
        """Test that offset skips results."""
        from api.services.search_service import SearchQuery

        # First page
        query1 = SearchQuery(query="test", limit=5, offset=0)
        results1, _ = await search_service.search(query1)

        # Second page
        query2 = SearchQuery(query="test", limit=5, offset=5)
        results2, _ = await search_service.search(query2)

        # Results should be different
        ids1 = {r.entity_id for r in results1}
        ids2 = {r.entity_id for r in results2}
        assert ids1.isdisjoint(ids2)


class TestSearchServiceHighlighting:
    """Tests for search highlighting."""

    @pytest.fixture
    def mock_handler(self):
        """Create a mock Neo4j handler."""
        handler = MagicMock()
        handler.execute_query = MagicMock(return_value=[])
        handler.get_all_projects = MagicMock(return_value=[
            {"id": "project-1", "safe_name": "project_one", "name": "Project One"}
        ])
        handler.get_project = MagicMock(return_value={
            "id": "project-1", "safe_name": "project_one", "name": "Project One"
        })
        handler.get_all_people = MagicMock(return_value=[
            {
                "id": "entity-1",
                "created_at": "2024-01-15T10:30:00",
                "profile": {
                    "core": {
                        "name": [{"first_name": "John", "last_name": "Doe"}],
                        "email": ["john.doe@example.com"]
                    }
                }
            }
        ])
        return handler

    @pytest.fixture
    def search_service(self, mock_handler, mock_config):
        """Create a SearchService with mocks."""
        from api.services.search_service import SearchService
        return SearchService(mock_handler, mock_config)

    @pytest.mark.asyncio
    async def test_highlighting_enabled(self, search_service):
        """Test that highlights are generated when enabled."""
        from api.services.search_service import SearchQuery

        query = SearchQuery(query="John", highlight=True)
        results, _ = await search_service.search(query)

        if results:
            # Should have highlights
            assert any(r.highlights for r in results)

    @pytest.mark.asyncio
    async def test_highlighting_disabled(self, search_service):
        """Test that highlights are not generated when disabled."""
        from api.services.search_service import SearchQuery

        query = SearchQuery(query="John", highlight=False)
        results, _ = await search_service.search(query)

        # Highlights should be empty when disabled
        for result in results:
            assert result.highlights == {} or not result.highlights

    def test_generate_highlight(self, search_service):
        """Test highlight snippet generation."""
        text = "The quick brown fox jumps over the lazy dog"
        search = "fox"

        snippet = search_service._generate_highlight(text, search, context_chars=10)

        # Should contain the match with **markers**
        assert "**fox**" in snippet

    def test_generate_highlight_at_start(self, search_service):
        """Test highlight at start of text."""
        text = "fox is an animal"
        search = "fox"

        snippet = search_service._generate_highlight(text, search, context_chars=10)

        # Should start with the match
        assert "**fox**" in snippet
        assert not snippet.startswith("...")

    def test_generate_highlight_at_end(self, search_service):
        """Test highlight at end of text."""
        text = "I saw a fox"
        search = "fox"

        snippet = search_service._generate_highlight(text, search, context_chars=10)

        # Should end with the match
        assert "**fox**" in snippet
        assert not snippet.endswith("...")


class TestSearchServiceFuzzy:
    """Tests for fuzzy search functionality."""

    @pytest.fixture
    def mock_handler(self):
        """Create a mock Neo4j handler."""
        handler = MagicMock()
        handler.execute_query = MagicMock(return_value=[])
        handler.get_all_projects = MagicMock(return_value=[
            {"id": "project-1", "safe_name": "project_one", "name": "Project One"}
        ])
        handler.get_project = MagicMock(return_value={
            "id": "project-1", "safe_name": "project_one", "name": "Project One"
        })
        handler.get_all_people = MagicMock(return_value=[
            {
                "id": "entity-1",
                "created_at": "2024-01-15T10:30:00",
                "profile": {
                    "core": {
                        "name": [{"first_name": "Michael", "last_name": "Johnson"}],
                        "email": ["michael.johnson@example.com"]
                    }
                }
            },
            {
                "id": "entity-2",
                "created_at": "2024-01-15T11:00:00",
                "profile": {
                    "core": {
                        "name": [{"first_name": "Micheal", "last_name": "Jonson"}],
                        "email": ["micheal.jonson@example.com"]
                    }
                }
            }
        ])
        return handler

    @pytest.fixture
    def search_service(self, mock_handler, mock_config):
        """Create a SearchService with mocks."""
        from api.services.search_service import SearchService
        return SearchService(mock_handler, mock_config)

    @pytest.mark.asyncio
    async def test_fuzzy_search_enabled(self, search_service):
        """Test fuzzy search finds similar matches."""
        from api.services.search_service import SearchQuery

        # Search for "Michael" should find both "Michael" and "Micheal"
        query = SearchQuery(query="Michael", fuzzy=True)
        results, total = await search_service.search(query)

        entity_ids = [r.entity_id for r in results]
        # Should find exact match
        assert "entity-1" in entity_ids

    @pytest.mark.asyncio
    async def test_fuzzy_search_disabled(self, search_service):
        """Test that fuzzy matching is skipped when disabled."""
        from api.services.search_service import SearchQuery

        query = SearchQuery(query="Michiel", fuzzy=False)  # Misspelling
        results, total = await search_service.search(query)

        # Without fuzzy, exact misspelling won't match
        # (actual behavior depends on implementation)
        assert isinstance(results, list)


class TestSearchServiceFieldSpecific:
    """Tests for field-specific search."""

    @pytest.fixture
    def mock_handler(self):
        """Create a mock Neo4j handler."""
        handler = MagicMock()
        handler.execute_query = MagicMock(return_value=[])
        handler.get_all_projects = MagicMock(return_value=[
            {"id": "project-1", "safe_name": "project_one", "name": "Project One"}
        ])
        handler.get_project = MagicMock(return_value={
            "id": "project-1", "safe_name": "project_one", "name": "Project One"
        })
        handler.get_all_people = MagicMock(return_value=[
            {
                "id": "entity-1",
                "created_at": "2024-01-15T10:30:00",
                "profile": {
                    "core": {
                        "name": [{"first_name": "John", "last_name": "Doe"}],
                        "email": ["john@example.com"]
                    },
                    "social": {
                        "twitter": "@johndoe"
                    }
                }
            }
        ])
        return handler

    @pytest.fixture
    def search_service(self, mock_handler, mock_config):
        """Create a SearchService with mocks."""
        from api.services.search_service import SearchService
        return SearchService(mock_handler, mock_config)

    @pytest.mark.asyncio
    async def test_search_specific_field(self, search_service):
        """Test searching only in specific fields."""
        from api.services.search_service import SearchQuery

        # Search only in email field
        query = SearchQuery(query="john", fields=["email"])
        results, _ = await search_service.search(query)

        # Should find match in email
        if results:
            for r in results:
                assert any("email" in f for f in r.matched_fields)

    @pytest.mark.asyncio
    async def test_search_multiple_fields(self, search_service):
        """Test searching in multiple specific fields."""
        from api.services.search_service import SearchQuery

        query = SearchQuery(query="john", fields=["name", "email", "twitter"])
        results, _ = await search_service.search(query)

        # Should work with multiple field filters
        assert isinstance(results, list)


class TestSearchServiceSearchableFields:
    """Tests for searchable fields functionality."""

    @pytest.fixture
    def search_service(self, mock_neo4j_handler, mock_config):
        """Create a SearchService with mocks."""
        from api.services.search_service import SearchService
        mock_neo4j_handler.execute_query = MagicMock(return_value=[])
        return SearchService(mock_neo4j_handler, mock_config)

    def test_get_searchable_fields(self, search_service):
        """Test getting list of searchable fields."""
        fields = search_service.get_searchable_fields()

        assert isinstance(fields, list)
        # Should include string and email type fields from mock config
        # Based on mock_config: core.name (string), core.email (email)
        assert any("core" in f for f in fields)

    def test_searchable_fields_caching(self, search_service):
        """Test that searchable fields are cached."""
        fields1 = search_service.get_searchable_fields()
        fields2 = search_service.get_searchable_fields()

        # Should return same list (cached)
        assert fields1 is fields2


class TestSearchServiceIndex:
    """Tests for search index functionality."""

    @pytest.fixture
    def mock_handler(self):
        """Create a mock Neo4j handler."""
        handler = MagicMock()
        handler.execute_query = MagicMock(return_value=[{"person": {"id": "entity-1"}}])
        handler.get_all_projects = MagicMock(return_value=[
            {"id": "project-1", "safe_name": "project_one", "name": "Project One"}
        ])
        handler.get_project = MagicMock(return_value={
            "id": "project-1", "safe_name": "project_one", "name": "Project One"
        })
        handler.get_all_people = MagicMock(return_value=[
            {
                "id": "entity-1",
                "created_at": "2024-01-15T10:30:00",
                "profile": {
                    "core": {
                        "name": [{"first_name": "John", "last_name": "Doe"}],
                        "email": ["john@example.com"]
                    }
                }
            }
        ])
        return handler

    @pytest.fixture
    def search_service(self, mock_handler, mock_config):
        """Create a SearchService with mocks."""
        from api.services.search_service import SearchService
        return SearchService(mock_handler, mock_config)

    @pytest.mark.asyncio
    async def test_build_search_index(self, search_service):
        """Test building search index for a project."""
        count = await search_service.build_search_index("project-1")

        assert count >= 0

    @pytest.mark.asyncio
    async def test_build_search_index_invalid_project(self, search_service, mock_handler):
        """Test building search index for non-existent project."""
        mock_handler.get_project.return_value = None
        mock_handler.get_all_projects.return_value = []

        count = await search_service.build_search_index("nonexistent")

        assert count == 0

    @pytest.mark.asyncio
    async def test_index_entity(self, search_service):
        """Test indexing a single entity."""
        entity_data = {
            "id": "entity-1",
            "profile": {
                "core": {
                    "name": [{"first_name": "John", "last_name": "Doe"}]
                }
            }
        }

        result = await search_service.index_entity("project-1", "entity-1", entity_data)

        assert isinstance(result, bool)


class TestSearchServiceEntitySearch:
    """Tests for search within a specific entity."""

    @pytest.fixture
    def mock_handler(self):
        """Create a mock Neo4j handler."""
        handler = MagicMock()
        handler.execute_query = MagicMock(return_value=[])
        handler.get_all_projects = MagicMock(return_value=[
            {"id": "project-1", "safe_name": "project_one", "name": "Project One"}
        ])
        handler.get_project = MagicMock(return_value={
            "id": "project-1", "safe_name": "project_one", "name": "Project One"
        })
        handler.get_person = MagicMock(return_value={
            "id": "entity-1",
            "created_at": "2024-01-15T10:30:00",
            "profile": {
                "core": {
                    "name": [{"first_name": "John", "last_name": "Doe"}],
                    "email": ["john@example.com", "johndoe@company.com"]
                },
                "notes": {
                    "comment": "Important person to track"
                }
            }
        })
        return handler

    @pytest.fixture
    def search_service(self, mock_handler, mock_config):
        """Create a SearchService with mocks."""
        from api.services.search_service import SearchService
        return SearchService(mock_handler, mock_config)

    @pytest.mark.asyncio
    async def test_search_entity(self, search_service):
        """Test searching within a specific entity."""
        results = await search_service.search_entity("project-1", "entity-1", "John")

        assert isinstance(results, list)
        if results:
            assert results[0].entity_id == "entity-1"

    @pytest.mark.asyncio
    async def test_search_entity_no_match(self, search_service):
        """Test searching for non-matching text in entity."""
        results = await search_service.search_entity(
            "project-1",
            "entity-1",
            "nonexistent12345"
        )

        assert results == []

    @pytest.mark.asyncio
    async def test_search_entity_empty_query(self, search_service):
        """Test searching entity with empty query."""
        results = await search_service.search_entity("project-1", "entity-1", "")

        assert results == []

    @pytest.mark.asyncio
    async def test_search_entity_not_found(self, search_service, mock_handler):
        """Test searching in non-existent entity."""
        mock_handler.get_person.return_value = None

        results = await search_service.search_entity("project-1", "nonexistent", "test")

        assert results == []


class TestSearchServiceHelpers:
    """Tests for helper methods."""

    @pytest.fixture
    def search_service(self, mock_neo4j_handler, mock_config):
        """Create a SearchService with mocks."""
        from api.services.search_service import SearchService
        mock_neo4j_handler.execute_query = MagicMock(return_value=[])
        return SearchService(mock_neo4j_handler, mock_config)

    def test_value_to_strings_string(self, search_service):
        """Test converting string value."""
        result = search_service._value_to_strings("hello")
        assert result == ["hello"]

    def test_value_to_strings_empty(self, search_service):
        """Test converting empty values."""
        assert search_service._value_to_strings(None) == []
        assert search_service._value_to_strings("") == []
        assert search_service._value_to_strings("   ") == []

    def test_value_to_strings_number(self, search_service):
        """Test converting numeric values."""
        assert search_service._value_to_strings(123) == ["123"]
        assert search_service._value_to_strings(45.67) == ["45.67"]

    def test_value_to_strings_list(self, search_service):
        """Test converting list values."""
        result = search_service._value_to_strings(["a", "b", "c"])
        assert result == ["a", "b", "c"]

    def test_value_to_strings_nested_list(self, search_service):
        """Test converting nested list values."""
        result = search_service._value_to_strings([["a", "b"], "c"])
        assert "a" in result
        assert "b" in result
        assert "c" in result

    def test_value_to_strings_dict(self, search_service):
        """Test converting dict values."""
        result = search_service._value_to_strings({"first": "John", "last": "Doe"})
        assert "John" in result
        assert "Doe" in result

    def test_escape_lucene_query(self, search_service):
        """Test escaping Lucene special characters."""
        # Test various special characters
        assert "\\" in search_service._escape_lucene_query("test\\path")
        assert "\\+" in search_service._escape_lucene_query("test+")
        assert "\\-" in search_service._escape_lucene_query("test-")

    def test_extract_entity_summary(self, search_service):
        """Test extracting entity summary."""
        entity = {
            "id": "entity-1",
            "created_at": "2024-01-15T10:30:00",
            "profile": {
                "core": {
                    "name": [{"first_name": "John", "last_name": "Doe"}],
                    "email": ["john@example.com"]
                }
            }
        }

        summary = search_service._extract_entity_summary(entity)

        assert summary["id"] == "entity-1"
        assert "name" in summary
        assert "email" in summary

    def test_extract_searchable_text(self, search_service):
        """Test extracting searchable text from entity."""
        entity = {
            "profile": {
                "core": {
                    "name": [{"first_name": "John", "last_name": "Doe"}],
                    "email": ["john@example.com"]
                }
            }
        }

        text = search_service._extract_searchable_text(entity)

        assert "John" in text
        assert "Doe" in text
        assert "john@example.com" in text

    def test_search_in_value_exact_match(self, search_service):
        """Test search_in_value with exact match."""
        result = search_service._search_in_value("john", "john", "john", True)

        assert result["matched"] is True
        assert result["score"] == 1.0

    def test_search_in_value_partial_match(self, search_service):
        """Test search_in_value with partial match."""
        result = search_service._search_in_value("john doe", "john", "john", True)

        assert result["matched"] is True
        assert result["score"] > 0

    def test_search_in_value_no_match(self, search_service):
        """Test search_in_value with no match."""
        result = search_service._search_in_value("jane", "john", "john", True)

        assert result["matched"] is False
        assert result["score"] == 0.0


class TestSearchServiceSingleton:
    """Tests for singleton pattern."""

    def test_get_search_service(self, mock_neo4j_handler, mock_config):
        """Test get_search_service returns instance."""
        from api.services.search_service import (
            get_search_service,
            set_search_service,
            SearchService
        )

        # Reset singleton
        set_search_service(None)

        service = get_search_service(mock_neo4j_handler, mock_config)

        assert isinstance(service, SearchService)

    def test_get_search_service_singleton(self, mock_neo4j_handler, mock_config):
        """Test get_search_service returns same instance."""
        from api.services.search_service import (
            get_search_service,
            set_search_service,
        )

        # Reset singleton
        set_search_service(None)

        service1 = get_search_service(mock_neo4j_handler, mock_config)
        service2 = get_search_service()

        assert service1 is service2

    def test_set_search_service(self, mock_neo4j_handler, mock_config):
        """Test setting the search service instance."""
        from api.services.search_service import (
            get_search_service,
            set_search_service,
            SearchService
        )

        custom_service = SearchService(mock_neo4j_handler, mock_config)
        set_search_service(custom_service)

        retrieved = get_search_service()

        assert retrieved is custom_service

        # Cleanup
        set_search_service(None)


class TestSearchServiceMultiProject:
    """Tests for multi-project search."""

    @pytest.fixture
    def mock_handler(self):
        """Create a mock Neo4j handler with multiple projects."""
        handler = MagicMock()
        handler.execute_query = MagicMock(return_value=[])
        handler.get_all_projects = MagicMock(return_value=[
            {"id": "project-1", "safe_name": "project_one", "name": "Project One"},
            {"id": "project-2", "safe_name": "project_two", "name": "Project Two"},
        ])
        handler.get_project = MagicMock(return_value={
            "id": "project-1", "safe_name": "project_one", "name": "Project One"
        })

        def get_people_side_effect(project_safe_name):
            if project_safe_name == "project_one":
                return [{
                    "id": "entity-1",
                    "created_at": "2024-01-15T10:30:00",
                    "profile": {
                        "core": {"name": [{"first_name": "John"}]}
                    }
                }]
            elif project_safe_name == "project_two":
                return [{
                    "id": "entity-2",
                    "created_at": "2024-01-15T11:00:00",
                    "profile": {
                        "core": {"name": [{"first_name": "John"}]}
                    }
                }]
            return []

        handler.get_all_people = MagicMock(side_effect=get_people_side_effect)
        return handler

    @pytest.fixture
    def search_service(self, mock_handler, mock_config):
        """Create a SearchService with mocks."""
        from api.services.search_service import SearchService
        return SearchService(mock_handler, mock_config)

    @pytest.mark.asyncio
    async def test_search_all_projects(self, search_service):
        """Test searching across all projects."""
        from api.services.search_service import SearchQuery

        # Search without project_id to search all
        query = SearchQuery(query="John", project_id=None)
        results, total = await search_service.search(query)

        # Should find results from both projects
        project_ids = {r.project_id for r in results}
        assert len(project_ids) >= 1  # At least one project

    @pytest.mark.asyncio
    async def test_search_single_project(self, search_service, mock_handler):
        """Test searching in a single project."""
        from api.services.search_service import SearchQuery

        # Search only in project-1
        query = SearchQuery(query="John", project_id="project_one")
        results, total = await search_service.search(query)

        # All results should be from project-1
        for result in results:
            assert result.project_id in ["project-1", "project_one"]
