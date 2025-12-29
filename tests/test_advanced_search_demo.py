#!/usr/bin/env python3
"""
Demo script to test advanced search functionality.

This script demonstrates the key features of the advanced boolean search:
- Query parsing
- Boolean operators
- Wildcards
- Field-specific search
"""

from api.services.search_service import (
    AdvancedQueryParser,
    SearchService,
    SearchQuery,
)
from unittest.mock import MagicMock


def test_query_parser():
    """Test the query parser with various inputs."""
    parser = AdvancedQueryParser()

    print("=" * 70)
    print("ADVANCED SEARCH QUERY PARSER TESTS")
    print("=" * 70)

    test_queries = [
        "email:john@example.com",
        "name:John AND email:*@gmail.com",
        '(tag:suspect OR tag:person_of_interest) AND NOT status:cleared',
        '"John Smith"',
        "phone:555* OR phone:777*",
        "name:J?hn",
        '(email:*@gmail.com OR email:*@yahoo.com) AND NOT archived:true',
        'name:"John Doe" AND city:Boston',
    ]

    for i, query in enumerate(test_queries, 1):
        print(f"\n{i}. Query: {query}")
        parsed = parser.parse(query)

        if parsed.error:
            print(f"   ERROR: {parsed.error}")
        else:
            print(f"   Tokens: {len(parsed.tokens)}")
            print(f"   Has wildcards: {parsed.has_wildcards}")
            if parsed.field_conditions:
                print(f"   Field conditions: {list(parsed.field_conditions.keys())}")

            # Show token details
            for j, token in enumerate(parsed.tokens[:5], 1):  # Show first 5 tokens
                print(f"   Token {j}: type={token.type}, value={token.value[:20]}...", end="")
                if token.field:
                    print(f", field={token.field}", end="")
                if token.negated:
                    print(", negated=True", end="")
                print()

    print("\n" + "=" * 70)


def test_wildcard_conversion():
    """Test wildcard to regex conversion."""
    # Create a mock Neo4j handler
    mock_neo4j = MagicMock()
    mock_neo4j.get_all_projects.return_value = []
    mock_neo4j.execute_query.return_value = []

    service = SearchService(mock_neo4j, {})

    print("\nWILDCARD TO REGEX CONVERSION")
    print("=" * 70)

    test_patterns = [
        "john*",
        "*@gmail.com",
        "j?hn",
        "555*",
        "test*@*.com",
        "a?b*c",
    ]

    for pattern in test_patterns:
        regex = service._wildcard_to_regex(pattern)
        print(f"Pattern: {pattern:20} -> Regex: {regex}")

    print("=" * 70)


def test_field_extraction():
    """Test field value extraction."""
    mock_neo4j = MagicMock()
    mock_neo4j.get_all_projects.return_value = []

    service = SearchService(mock_neo4j, {})

    print("\nFIELD VALUE EXTRACTION")
    print("=" * 70)

    profile = {
        "core": {
            "name": "John Doe",
            "email": "john@example.com",
            "contact": {
                "phone": "555-1234"
            }
        },
        "social": {
            "linkedin": "https://linkedin.com/in/johndoe"
        }
    }

    test_paths = [
        "core.name",
        "core.email",
        "core.contact.phone",
        "social.linkedin",
        "core.nonexistent",
        "invalid.path.here",
    ]

    for path in test_paths:
        value = service._get_field_value(profile, path)
        print(f"Path: {path:25} -> Value: {value}")

    print("=" * 70)


def test_match_value():
    """Test value matching with wildcards."""
    mock_neo4j = MagicMock()
    service = SearchService(mock_neo4j, {})

    print("\nVALUE MATCHING WITH WILDCARDS")
    print("=" * 70)

    test_cases = [
        ("john.doe@gmail.com", "*@gmail.com", False),
        ("John", "J?hn", False),
        ("John Doe", '"John Doe"', True),
        ("555-1234", "555*", False),
        ("test@example.com", "*@*.com", False),
        ("John", "john", False),  # Case insensitive
    ]

    for value, pattern, exact in test_cases:
        result = service._match_value(value, pattern, exact, highlight=False)
        matched = "MATCH" if result["matched"] else "NO MATCH"
        score = result.get("score", 0.0)
        print(f"Value: {value:25} Pattern: {pattern:20} -> {matched} (score: {score:.2f})")

    print("=" * 70)


def main():
    """Run all demo tests."""
    print("\n")
    print("*" * 70)
    print("BASSET HOUND ADVANCED SEARCH - DEMONSTRATION")
    print("*" * 70)
    print()

    test_query_parser()
    test_wildcard_conversion()
    test_field_extraction()
    test_match_value()

    print("\n" + "*" * 70)
    print("DEMONSTRATION COMPLETE")
    print("*" * 70)
    print()


if __name__ == "__main__":
    main()
