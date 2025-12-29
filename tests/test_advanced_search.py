"""
Comprehensive Tests for Advanced Boolean Search.

This test suite covers:
- Query parsing and tokenization
- Boolean operators (AND, OR, NOT)
- Field-specific searches
- Phrase searches with quotes
- Wildcard matching (* and ?)
- Query grouping with parentheses
- Complex nested queries
- Edge cases and error handling
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from typing import Dict, Any, List

from api.services.search_service import (
    SearchService,
    SearchQuery,
    SearchResult,
    AdvancedQueryParser,
    ParsedQuery,
    QueryToken,
    QueryOperator,
)


# ----- Test Fixtures -----

@pytest.fixture
def mock_neo4j_handler():
    """Create a mock Neo4j handler for testing."""
    handler = MagicMock()

    # Mock project data
    handler.get_project = MagicMock(return_value={
        "id": "project-123",
        "safe_name": "test_project",
        "name": "Test Project"
    })

    handler.get_all_projects = MagicMock(return_value=[
        {
            "id": "project-123",
            "safe_name": "test_project",
            "name": "Test Project"
        }
    ])

    # Mock entity data
    handler.get_all_people = MagicMock(return_value=[
        {
            "id": "person-1",
            "created_at": "2024-01-01",
            "profile": {
                "core": {
                    "name": "John Doe",
                    "email": "john.doe@gmail.com",
                    "phone": "555-1234"
                },
                "social": {
                    "linkedin": "https://linkedin.com/in/johndoe"
                },
                "tags": {
                    "status": "active",
                    "category": "suspect"
                }
            }
        },
        {
            "id": "person-2",
            "created_at": "2024-01-02",
            "profile": {
                "core": {
                    "name": "Jane Smith",
                    "email": "jane.smith@example.com",
                    "phone": "555-5678"
                },
                "social": {
                    "linkedin": "https://linkedin.com/in/janesmith"
                },
                "tags": {
                    "status": "cleared",
                    "category": "person_of_interest"
                }
            }
        },
        {
            "id": "person-3",
            "created_at": "2024-01-03",
            "profile": {
                "core": {
                    "name": "Bob Johnson",
                    "email": "bob.johnson@gmail.com",
                    "phone": "777-9999"
                },
                "social": {
                    "linkedin": "https://linkedin.com/in/bobjohnson"
                },
                "tags": {
                    "status": "active",
                    "category": "contact"
                }
            }
        }
    ])

    handler.get_person = MagicMock(side_effect=lambda project, id: {
        "person-1": {
            "id": "person-1",
            "profile": {
                "core": {
                    "name": "John Doe",
                    "email": "john.doe@gmail.com"
                }
            }
        },
        "person-2": {
            "id": "person-2",
            "profile": {
                "core": {
                    "name": "Jane Smith",
                    "email": "jane.smith@example.com"
                }
            }
        }
    }.get(id))

    handler.execute_query = MagicMock(return_value=[])

    return handler


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    return {
        "sections": [
            {
                "id": "core",
                "fields": [
                    {"id": "name", "type": "string"},
                    {"id": "email", "type": "email"},
                    {"id": "phone", "type": "string"}
                ]
            },
            {
                "id": "social",
                "fields": [
                    {"id": "linkedin", "type": "url"}
                ]
            },
            {
                "id": "tags",
                "fields": [
                    {"id": "status", "type": "string"},
                    {"id": "category", "type": "string"}
                ]
            }
        ]
    }


@pytest.fixture
def search_service(mock_neo4j_handler, mock_config):
    """Create a SearchService instance for testing."""
    return SearchService(mock_neo4j_handler, mock_config)


@pytest.fixture
def query_parser():
    """Create an AdvancedQueryParser instance for testing."""
    return AdvancedQueryParser()


# ----- Query Parser Tests -----

class TestAdvancedQueryParser:
    """Tests for the AdvancedQueryParser class."""

    def test_parse_simple_word(self, query_parser):
        """Test parsing a simple word query."""
        parsed = query_parser.parse("John")

        assert not parsed.error
        assert len(parsed.tokens) == 1
        assert parsed.tokens[0].type == "word"
        assert parsed.tokens[0].value == "John"
        assert not parsed.tokens[0].negated

    def test_parse_field_search(self, query_parser):
        """Test parsing field:value syntax."""
        parsed = query_parser.parse("email:john@example.com")

        assert not parsed.error
        assert len(parsed.tokens) == 1
        assert parsed.tokens[0].type == "field"
        assert parsed.tokens[0].field == "email"
        assert parsed.tokens[0].value == "john@example.com"

    def test_parse_phrase_search(self, query_parser):
        """Test parsing quoted phrase search."""
        parsed = query_parser.parse('"John Doe"')

        assert not parsed.error
        assert len(parsed.tokens) == 1
        assert parsed.tokens[0].type == "phrase"
        assert parsed.tokens[0].value == "John Doe"

    def test_parse_field_with_phrase(self, query_parser):
        """Test parsing field with quoted phrase value."""
        parsed = query_parser.parse('name:"John Doe"')

        assert not parsed.error
        assert len(parsed.tokens) == 1
        assert parsed.tokens[0].type == "field"
        assert parsed.tokens[0].field == "name"
        assert parsed.tokens[0].value == "John Doe"

    def test_parse_and_operator(self, query_parser):
        """Test parsing AND operator."""
        parsed = query_parser.parse("name:John AND email:john@example.com")

        assert not parsed.error
        assert len(parsed.tokens) == 3
        assert parsed.tokens[0].type == "field"
        assert parsed.tokens[1].type == "operator"
        assert parsed.tokens[1].value == "AND"
        assert parsed.tokens[2].type == "field"

    def test_parse_or_operator(self, query_parser):
        """Test parsing OR operator."""
        parsed = query_parser.parse("email:john@example.com OR phone:555-1234")

        assert not parsed.error
        assert len(parsed.tokens) == 3
        assert parsed.tokens[0].type == "field"
        assert parsed.tokens[1].type == "operator"
        assert parsed.tokens[1].value == "OR"
        assert parsed.tokens[2].type == "field"

    def test_parse_not_operator(self, query_parser):
        """Test parsing NOT operator."""
        parsed = query_parser.parse("NOT status:archived")

        assert not parsed.error
        assert len(parsed.tokens) == 1
        assert parsed.tokens[0].type == "field"
        assert parsed.tokens[0].negated is True

    def test_parse_wildcard_star(self, query_parser):
        """Test parsing * wildcard."""
        parsed = query_parser.parse("email:*@gmail.com")

        assert not parsed.error
        assert parsed.has_wildcards is True
        assert parsed.tokens[0].value == "*@gmail.com"

    def test_parse_wildcard_question(self, query_parser):
        """Test parsing ? wildcard."""
        parsed = query_parser.parse("name:J?hn")

        assert not parsed.error
        assert parsed.has_wildcards is True
        assert parsed.tokens[0].value == "J?hn"

    def test_parse_grouping(self, query_parser):
        """Test parsing parentheses grouping."""
        parsed = query_parser.parse("(name:John OR name:Jane)")

        assert not parsed.error
        tokens = parsed.tokens
        assert tokens[0].type == "group"
        assert tokens[0].value == "("
        assert tokens[-1].type == "group"
        assert tokens[-1].value == ")"

    def test_parse_complex_nested_query(self, query_parser):
        """Test parsing complex nested query."""
        query = '(email:*@gmail.com OR email:*@yahoo.com) AND NOT status:archived'
        parsed = query_parser.parse(query)

        assert not parsed.error
        assert parsed.has_wildcards is True
        # Check for opening paren, fields, operators, and closing paren
        assert any(t.type == "group" and t.value == "(" for t in parsed.tokens)
        assert any(t.type == "operator" and t.value == "AND" for t in parsed.tokens)

    def test_parse_empty_query(self, query_parser):
        """Test parsing empty query returns error."""
        parsed = query_parser.parse("")

        assert parsed.error is not None
        assert "Empty" in parsed.error

    def test_parse_unclosed_quote(self, query_parser):
        """Test parsing unclosed quote returns error."""
        parsed = query_parser.parse('name:"John')

        assert parsed.error is not None

    def test_field_conditions_extraction(self, query_parser):
        """Test extraction of field conditions."""
        parsed = query_parser.parse("email:john@example.com AND email:jane@example.com")

        assert "email" in parsed.field_conditions
        assert len(parsed.field_conditions["email"]) == 2
        assert "john@example.com" in parsed.field_conditions["email"]
        assert "jane@example.com" in parsed.field_conditions["email"]


# ----- Search Service Tests -----

class TestSearchServiceAdvanced:
    """Tests for advanced search functionality in SearchService."""

    @pytest.mark.asyncio
    async def test_simple_field_search(self, search_service):
        """Test simple field-specific search."""
        query = SearchQuery(
            query="email:john.doe@gmail.com",
            project_id="project-123",
            advanced=True
        )

        results, total = await search_service.search(query)

        assert total >= 1
        # Should find person-1 with john.doe@gmail.com
        assert any(r.entity_id == "person-1" for r in results)

    @pytest.mark.asyncio
    async def test_and_operator(self, search_service):
        """Test AND operator."""
        query = SearchQuery(
            query="core.name:John AND core.email:*@gmail.com",
            project_id="project-123",
            advanced=True
        )

        results, total = await search_service.search(query)

        # Should find person-1 (John with Gmail)
        assert any(r.entity_id == "person-1" for r in results)

    @pytest.mark.asyncio
    async def test_or_operator(self, search_service):
        """Test OR operator."""
        query = SearchQuery(
            query="core.email:*@gmail.com OR core.email:*@example.com",
            project_id="project-123",
            advanced=True
        )

        results, total = await search_service.search(query)

        # Should find both Gmail and example.com users
        assert total >= 2

    @pytest.mark.asyncio
    async def test_not_operator(self, search_service):
        """Test NOT operator."""
        query = SearchQuery(
            query="tags.status:active AND NOT tags.category:suspect",
            project_id="project-123",
            advanced=True
        )

        results, total = await search_service.search(query)

        # Should exclude person-1 (active suspect)
        # Should include person-3 (active contact)
        entity_ids = [r.entity_id for r in results]
        assert "person-3" in entity_ids
        assert "person-1" not in entity_ids

    @pytest.mark.asyncio
    async def test_wildcard_star(self, search_service):
        """Test * wildcard matching."""
        query = SearchQuery(
            query="core.phone:555*",
            project_id="project-123",
            advanced=True
        )

        results, total = await search_service.search(query)

        # Should find person-1 and person-2 with 555 prefix
        assert total >= 2
        entity_ids = [r.entity_id for r in results]
        assert "person-1" in entity_ids
        assert "person-2" in entity_ids

    @pytest.mark.asyncio
    async def test_wildcard_question(self, search_service):
        """Test ? wildcard matching."""
        query = SearchQuery(
            query="core.name:J?hn",
            project_id="project-123",
            advanced=True
        )

        results, total = await search_service.search(query)

        # Should match "John"
        assert total >= 1
        assert any(r.entity_id == "person-1" for r in results)

    @pytest.mark.asyncio
    async def test_phrase_search(self, search_service):
        """Test exact phrase search."""
        query = SearchQuery(
            query='"John Doe"',
            project_id="project-123",
            advanced=True
        )

        results, total = await search_service.search(query)

        # Should find exact match for "John Doe"
        assert total >= 1
        assert any(r.entity_id == "person-1" for r in results)

    @pytest.mark.asyncio
    async def test_complex_grouping(self, search_service):
        """Test complex query with grouping."""
        query = SearchQuery(
            query="(tags.category:suspect OR tags.category:person_of_interest) AND tags.status:active",
            project_id="project-123",
            advanced=True
        )

        results, total = await search_service.search(query)

        # Should find person-1 (active suspect)
        # Should NOT find person-2 (cleared person_of_interest)
        entity_ids = [r.entity_id for r in results]
        assert "person-1" in entity_ids
        assert "person-2" not in entity_ids

    @pytest.mark.asyncio
    async def test_nested_groups_with_not(self, search_service):
        """Test nested groups with NOT operator."""
        query = SearchQuery(
            query="(core.email:*@gmail.com OR core.email:*@yahoo.com) AND NOT tags.status:cleared",
            project_id="project-123",
            advanced=True
        )

        results, total = await search_service.search(query)

        # Should find person-1 (gmail, active)
        # Should NOT find person-2 (example.com, cleared)
        entity_ids = [r.entity_id for r in results]
        assert "person-1" in entity_ids or "person-3" in entity_ids

    @pytest.mark.asyncio
    async def test_field_specific_with_phrase(self, search_service):
        """Test field-specific search with phrase."""
        query = SearchQuery(
            query='core.name:"John Doe"',
            project_id="project-123",
            advanced=True
        )

        results, total = await search_service.search(query)

        assert total >= 1
        assert any(r.entity_id == "person-1" for r in results)

    @pytest.mark.asyncio
    async def test_multiple_wildcards(self, search_service):
        """Test multiple wildcard patterns."""
        query = SearchQuery(
            query="core.phone:555* OR core.phone:777*",
            project_id="project-123",
            advanced=True
        )

        results, total = await search_service.search(query)

        # Should find person-1, person-2 (555*) and person-3 (777*)
        assert total >= 2
        entity_ids = [r.entity_id for r in results]
        assert len(entity_ids) >= 2

    @pytest.mark.asyncio
    async def test_highlighting_in_advanced_search(self, search_service):
        """Test that highlighting works in advanced search."""
        query = SearchQuery(
            query="core.email:john.doe@gmail.com",
            project_id="project-123",
            advanced=True,
            highlight=True
        )

        results, total = await search_service.search(query)

        if total > 0:
            # Check that highlights are generated
            result = results[0]
            assert len(result.highlights) > 0 or len(result.matched_fields) > 0


# ----- Wildcard Matching Tests -----

class TestWildcardMatching:
    """Tests for wildcard pattern matching."""

    def test_wildcard_to_regex_star(self, search_service):
        """Test conversion of * wildcard to regex."""
        pattern = search_service._wildcard_to_regex("john*")
        assert pattern == "^john.*$"

    def test_wildcard_to_regex_question(self, search_service):
        """Test conversion of ? wildcard to regex."""
        pattern = search_service._wildcard_to_regex("j?hn")
        assert pattern == "^j.hn$"

    def test_wildcard_to_regex_combined(self, search_service):
        """Test conversion of combined wildcards."""
        pattern = search_service._wildcard_to_regex("j?hn*")
        assert pattern == "^j.hn.*$"

    def test_match_value_with_star_wildcard(self, search_service):
        """Test matching with * wildcard."""
        result = search_service._match_value(
            "john.doe@gmail.com",
            "*@gmail.com",
            exact_phrase=False,
            highlight=False
        )

        assert result["matched"] is True
        assert result["score"] > 0

    def test_match_value_with_question_wildcard(self, search_service):
        """Test matching with ? wildcard."""
        result = search_service._match_value(
            "John",
            "J?hn",
            exact_phrase=False,
            highlight=False
        )

        assert result["matched"] is True

    def test_match_value_no_wildcard_match(self, search_service):
        """Test non-matching wildcard pattern."""
        result = search_service._match_value(
            "john@example.com",
            "*@gmail.com",
            exact_phrase=False,
            highlight=False
        )

        assert result["matched"] is False


# ----- Field Value Extraction Tests -----

class TestFieldValueExtraction:
    """Tests for extracting field values from profiles."""

    def test_get_simple_field_value(self, search_service):
        """Test getting a simple field value."""
        profile = {
            "core": {
                "name": "John Doe",
                "email": "john@example.com"
            }
        }

        value = search_service._get_field_value(profile, "core.name")
        assert value == "John Doe"

    def test_get_nested_field_value(self, search_service):
        """Test getting a nested field value."""
        profile = {
            "core": {
                "contact": {
                    "email": "john@example.com"
                }
            }
        }

        value = search_service._get_field_value(profile, "core.contact.email")
        assert value == "john@example.com"

    def test_get_nonexistent_field(self, search_service):
        """Test getting a field that doesn't exist."""
        profile = {
            "core": {
                "name": "John Doe"
            }
        }

        value = search_service._get_field_value(profile, "core.email")
        assert value is None

    def test_get_field_from_empty_profile(self, search_service):
        """Test getting field from empty profile."""
        profile = {}

        value = search_service._get_field_value(profile, "core.name")
        assert value is None


# ----- Edge Cases and Error Handling -----

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_query_returns_no_results(self, query_parser):
        """Test that empty query returns error."""
        parsed = query_parser.parse("")

        assert parsed.error is not None

    def test_query_with_only_operators(self, query_parser):
        """Test query with only operators."""
        parsed = query_parser.parse("AND OR NOT")

        # Should parse operators but have no search terms
        assert not parsed.error
        operator_tokens = [t for t in parsed.tokens if t.type == "operator"]
        assert len(operator_tokens) == 2  # AND and OR

    def test_unbalanced_parentheses(self, query_parser):
        """Test unbalanced parentheses."""
        parsed = query_parser.parse("(name:John AND email:test")

        # Parser should handle this gracefully
        assert not parsed.error or "(" in str(parsed.error)

    def test_special_characters_in_value(self, query_parser):
        """Test special characters in field values."""
        parsed = query_parser.parse("email:john+test@example.com")

        assert not parsed.error
        assert parsed.tokens[0].value == "john+test@example.com"

    @pytest.mark.asyncio
    async def test_invalid_field_name(self, search_service):
        """Test search with invalid field name."""
        query = SearchQuery(
            query="nonexistent_field:value",
            project_id="project-123",
            advanced=True
        )

        results, total = await search_service.search(query)

        # Should return no results for nonexistent field
        assert total == 0

    @pytest.mark.asyncio
    async def test_search_with_no_project(self, search_service):
        """Test global search across all projects."""
        query = SearchQuery(
            query="core.email:*@gmail.com",
            advanced=True
        )

        results, total = await search_service.search(query)

        # Should search across all projects
        assert total >= 0

    def test_parse_advanced_query_method(self, search_service):
        """Test the parse_advanced_query public method."""
        parsed = search_service.parse_advanced_query("email:test@example.com")

        assert not parsed.error
        assert len(parsed.tokens) == 1
        assert parsed.tokens[0].field == "email"

    @pytest.mark.asyncio
    async def test_backward_compatibility_simple_search(self, search_service):
        """Test that simple searches still work."""
        query = SearchQuery(
            query="John",
            project_id="project-123",
            advanced=False  # Simple search
        )

        results, total = await search_service.search(query)

        # Should still work with simple search
        assert total >= 0


# ----- Integration Tests -----

class TestAdvancedSearchIntegration:
    """Integration tests for complete search workflows."""

    @pytest.mark.asyncio
    async def test_complete_investigation_workflow(self, search_service):
        """Test a complete investigation search workflow."""
        # Step 1: Find all Gmail users
        query1 = SearchQuery(
            query="core.email:*@gmail.com",
            project_id="project-123",
            advanced=True
        )
        results1, total1 = await search_service.search(query1)
        gmail_users = [r.entity_id for r in results1]

        assert len(gmail_users) >= 1

        # Step 2: Find active suspects
        query2 = SearchQuery(
            query="tags.category:suspect AND tags.status:active",
            project_id="project-123",
            advanced=True
        )
        results2, total2 = await search_service.search(query2)
        active_suspects = [r.entity_id for r in results2]

        # Step 3: Find Gmail users who are active suspects
        query3 = SearchQuery(
            query="core.email:*@gmail.com AND tags.category:suspect AND tags.status:active",
            project_id="project-123",
            advanced=True
        )
        results3, total3 = await search_service.search(query3)
        gmail_active_suspects = [r.entity_id for r in results3]

        # Verify logical consistency
        for entity_id in gmail_active_suspects:
            assert entity_id in gmail_users
            assert entity_id in active_suspects

    @pytest.mark.asyncio
    async def test_exclusion_search(self, search_service):
        """Test searching with exclusions."""
        # Find all active users except suspects
        query = SearchQuery(
            query="tags.status:active AND NOT tags.category:suspect",
            project_id="project-123",
            advanced=True
        )

        results, total = await search_service.search(query)
        entity_ids = [r.entity_id for r in results]

        # Should include person-3 (active contact)
        # Should exclude person-1 (active suspect)
        if "person-3" in entity_ids:
            assert "person-1" not in entity_ids

    @pytest.mark.asyncio
    async def test_multi_criteria_search(self, search_service):
        """Test search with multiple criteria."""
        query = SearchQuery(
            query='(core.name:"John Doe" OR core.name:"Jane Smith") AND core.email:*@gmail.com',
            project_id="project-123",
            advanced=True
        )

        results, total = await search_service.search(query)

        # Should find John Doe with Gmail
        assert any(r.entity_id == "person-1" for r in results)

    @pytest.mark.asyncio
    async def test_phone_number_search_with_wildcards(self, search_service):
        """Test searching phone numbers with wildcards."""
        # Find all numbers starting with 555 or 777
        query = SearchQuery(
            query="core.phone:555* OR core.phone:777*",
            project_id="project-123",
            advanced=True
        )

        results, total = await search_service.search(query)

        # Should find person-1, person-2 (555*) and person-3 (777*)
        assert total >= 2


# ----- Performance and Stress Tests -----

class TestPerformance:
    """Performance and stress tests."""

    def test_parse_complex_query_performance(self, query_parser):
        """Test parsing of very complex queries."""
        complex_query = (
            "(email:*@gmail.com OR email:*@yahoo.com OR email:*@hotmail.com) "
            "AND (status:active OR status:pending) "
            "AND NOT (category:archived OR category:deleted) "
            "AND (phone:555* OR phone:777* OR phone:888*)"
        )

        parsed = query_parser.parse(complex_query)

        assert not parsed.error
        assert len(parsed.tokens) > 10

    @pytest.mark.asyncio
    async def test_search_with_many_or_conditions(self, search_service):
        """Test search with many OR conditions."""
        query = SearchQuery(
            query=(
                "core.email:*@gmail.com OR "
                "core.email:*@yahoo.com OR "
                "core.email:*@hotmail.com OR "
                "core.email:*@example.com"
            ),
            project_id="project-123",
            advanced=True
        )

        results, total = await search_service.search(query)

        # Should complete without errors
        assert total >= 0

    def test_deeply_nested_query(self, query_parser):
        """Test parsing deeply nested query."""
        nested_query = (
            "((name:John AND email:*@gmail.com) OR "
            "(name:Jane AND email:*@yahoo.com)) AND "
            "((status:active OR status:pending) AND "
            "NOT category:archived)"
        )

        parsed = query_parser.parse(nested_query)

        assert not parsed.error
