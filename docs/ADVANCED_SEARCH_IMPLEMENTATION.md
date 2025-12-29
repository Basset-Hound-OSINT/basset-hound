# Advanced Boolean Search Implementation

## Overview

This document describes the implementation of advanced boolean search operators for the Basset Hound OSINT platform. The enhancement adds powerful query capabilities including boolean operators, wildcards, field-specific searches, and phrase matching.

## Features Implemented

### 1. Query Parser (`AdvancedQueryParser`)

Location: `/home/devel/basset-hound/api/services/search_service.py`

The query parser tokenizes and validates advanced search queries, supporting:

- **Boolean Operators**: AND, OR, NOT
- **Field-Specific Search**: `field:value` syntax
- **Phrase Search**: `"exact phrase"` with quotes
- **Wildcards**: `*` (multiple chars), `?` (single char)
- **Grouping**: Parentheses for complex logic
- **Operator Precedence**: NOT > AND > OR

#### Key Classes

```python
class QueryToken:
    """Represents a parsed token in the query."""
    type: str        # 'field', 'phrase', 'word', 'operator', 'group'
    value: str       # The token value
    field: Optional[str]  # Field name for field:value syntax
    negated: bool    # Whether NOT was applied

class ParsedQuery:
    """Result of parsing an advanced query."""
    tokens: List[QueryToken]
    field_conditions: Dict[str, List[str]]
    has_wildcards: bool
    error: Optional[str]
```

### 2. Enhanced Search Service

The `SearchService` class now includes:

#### New Methods

- **`parse_advanced_query(query_string: str) -> ParsedQuery`**
  - Public method to parse and validate queries
  - Returns ParsedQuery with tokens or error

- **`_advanced_search(query, search_text) -> Tuple[List[SearchResult], int]`**
  - Executes advanced boolean search
  - Calls query parser and evaluator

- **`_execute_boolean_query(query, parsed) -> List[SearchResult]`**
  - Iterates through entities and evaluates query
  - Returns matching results

- **`_evaluate_query(tokens, profile, highlight) -> Tuple[bool, float, dict, list]`**
  - Evaluates query tokens against entity profile
  - Handles operator precedence and grouping
  - Returns match status, score, highlights, and matched fields

- **`_evaluate_term(token, profile, highlight) -> Tuple[bool, float, dict, list]`**
  - Evaluates a single search term
  - Handles field-specific and global searches
  - Supports negation

- **`_match_value(value, search_text, exact_phrase, highlight) -> Dict`**
  - Matches search term against value
  - Supports wildcards and exact phrases
  - Returns match status, score, and highlights

- **`_wildcard_to_regex(pattern: str) -> str`**
  - Converts wildcard pattern to regex
  - Handles `*` and `?` wildcards

- **`_get_field_value(profile, field_path) -> Optional[Any]`**
  - Extracts field value using dot notation
  - Supports nested field access

### 3. Enhanced Search Router

Location: `/home/devel/basset-hound/api/routers/search.py`

#### New Endpoints

##### GET `/api/v1/search/syntax-help`
Returns comprehensive documentation for advanced search syntax.

**Response:**
```json
{
  "syntax": {
    "operators": {
      "AND": "Both conditions must match",
      "OR": "At least one condition must match",
      "NOT": "Negates the following condition"
    },
    "wildcards": {
      "*": "Matches any number of characters",
      "?": "Matches exactly one character"
    },
    "field_search": "field:value",
    "phrase_search": "\"exact phrase\"",
    "grouping": "(query1 OR query2) AND query3"
  },
  "examples": [...]
}
```

##### GET `/api/v1/projects/{project_id}/search/advanced`
Executes advanced boolean search within a project.

**Parameters:**
- `q` (required): Advanced query string
- `limit` (optional): Max results (1-100, default 20)
- `offset` (optional): Pagination offset
- `highlight` (optional): Generate highlights (default true)

**Example:**
```
GET /api/v1/projects/my-project/search/advanced?q=email:john* AND NOT status:archived
```

#### Enhanced Models

```python
class SyntaxHelpResponse(BaseModel):
    """Response model for syntax help."""
    syntax: dict[str, Any]
    examples: list[dict[str, str]]
    operators: list[dict[str, str]]
    wildcards: list[dict[str, str]]
```

### 4. Backward Compatibility

The implementation maintains full backward compatibility:

- Simple string searches still work with `advanced=False`
- Existing endpoints unchanged
- Default behavior is non-advanced search

To use advanced search, set `advanced=True` in `SearchQuery` or use the `/advanced` endpoint.

## Query Syntax Examples

### Basic Field Search
```
email:john@example.com
```
Finds entities with exact email match.

### AND Operator
```
name:John AND email:*@gmail.com
```
Finds entities named John with Gmail addresses.

### OR Operator
```
phone:555* OR phone:777*
```
Finds entities with phone numbers starting with 555 or 777.

### NOT Operator
```
tag:customer AND NOT status:inactive
```
Finds active customers (excludes inactive).

### Phrase Search
```
"John Smith"
```
Finds exact phrase "John Smith" across all fields.

### Field-Specific Phrase
```
name:"John Doe"
```
Finds exact phrase in name field only.

### Wildcards
```
email:*@company.com     # Matches any email at company.com
name:J?hn               # Matches John, Jahn, etc.
```

### Complex Grouping
```
(tag:suspect OR tag:person_of_interest) AND NOT status:cleared
```
Finds suspects or persons of interest who are not cleared.

### Nested Groups
```
(email:*@gmail.com OR email:*@yahoo.com) AND (status:active OR status:pending)
```
Finds Gmail/Yahoo users who are active or pending.

### Multi-Criteria Search
```
(name:"John Doe" OR name:"Jane Doe") AND city:Boston
```
Finds specific people in Boston.

## Testing

### Test Suite

Location: `/home/devel/basset-hound/tests/test_advanced_search.py`

The comprehensive test suite includes:

#### Parser Tests
- Simple word parsing
- Field-specific search
- Phrase search
- Operators (AND, OR, NOT)
- Wildcards (* and ?)
- Grouping with parentheses
- Complex nested queries
- Error handling (empty queries, unclosed quotes)

#### Search Service Tests
- Field-specific searches
- Boolean operators (AND, OR, NOT)
- Wildcard matching
- Phrase searches
- Complex grouping
- Highlighting in advanced search
- Backward compatibility

#### Wildcard Matching Tests
- Star (*) wildcard conversion to regex
- Question mark (?) wildcard conversion
- Combined wildcard patterns
- Matching with wildcards

#### Field Extraction Tests
- Simple field values
- Nested field access
- Nonexistent fields
- Empty profiles

#### Edge Cases
- Empty queries
- Operator-only queries
- Unbalanced parentheses
- Special characters
- Invalid field names
- Global searches

#### Integration Tests
- Complete investigation workflows
- Exclusion searches
- Multi-criteria searches
- Phone number searches with wildcards

#### Performance Tests
- Complex query parsing
- Many OR conditions
- Deeply nested queries

### Demo Script

Location: `/home/devel/basset-hound/test_advanced_search_demo.py`

Run the demo to see the parser and matching in action:

```bash
python test_advanced_search_demo.py
```

The demo tests:
- Query parsing with various inputs
- Wildcard to regex conversion
- Field value extraction
- Value matching with wildcards

## Implementation Details

### Operator Precedence

The query evaluator respects standard boolean operator precedence:

1. **NOT** (highest precedence)
2. **AND**
3. **OR** (lowest precedence)

Example:
```
A OR B AND NOT C
```
Evaluates as:
```
A OR (B AND (NOT C))
```

### Query Evaluation Algorithm

1. **Parse Query**: Tokenize query string into tokens
2. **Extract Field Conditions**: Build map of field-specific searches
3. **For Each Entity**:
   - Evaluate tokens recursively
   - Handle grouping with parentheses
   - Process operators in precedence order
   - Calculate relevance score
   - Generate highlights if requested
4. **Sort by Score**: Return results sorted by relevance
5. **Apply Pagination**: Return requested page of results

### Wildcard Matching

Wildcards are converted to regex patterns:

- `*` becomes `.*` (zero or more characters)
- `?` becomes `.` (exactly one character)
- Special regex characters are escaped
- Pattern is anchored with `^` and `$`

Examples:
```
john*         -> ^john.*$
*@gmail.com   -> ^.*@gmail\.com$
j?hn          -> ^j.hn$
```

### Field Path Resolution

Field values are accessed using dot notation:

```python
profile = {
    "core": {
        "name": "John Doe",
        "contact": {
            "email": "john@example.com"
        }
    }
}

# Accessing fields
"core.name"           -> "John Doe"
"core.contact.email"  -> "john@example.com"
"core.missing"        -> None
```

## API Usage Examples

### Python Client

```python
from api.services.search_service import SearchService, SearchQuery

# Create service
service = SearchService(neo4j_handler, config)

# Simple search
query = SearchQuery(
    query="John Doe",
    project_id="my-project"
)
results, total = await service.search(query)

# Advanced search
query = SearchQuery(
    query='email:*@gmail.com AND NOT status:archived',
    project_id="my-project",
    advanced=True
)
results, total = await service.search(query)

# Parse query to validate
parsed = service.parse_advanced_query('name:John AND email:test@example.com')
if parsed.error:
    print(f"Invalid query: {parsed.error}")
```

### HTTP API

```bash
# Get syntax help
curl http://localhost:8000/api/v1/search/syntax-help

# Simple search
curl "http://localhost:8000/api/v1/projects/my-project/search?q=John+Doe"

# Advanced search
curl "http://localhost:8000/api/v1/projects/my-project/search/advanced?q=email:john*+AND+NOT+status:archived"

# Get searchable fields
curl http://localhost:8000/api/v1/search/fields
```

## Performance Considerations

### Query Complexity

- **Simple queries**: O(n) where n is number of entities
- **Complex queries**: O(n × m) where m is query complexity
- **Wildcard matching**: Uses regex, slightly slower than exact match
- **Grouping**: Recursive evaluation, additional overhead

### Optimization Tips

1. **Use field-specific searches** when possible (faster than global search)
2. **Place restrictive conditions first** in AND queries
3. **Avoid excessive wildcards** (e.g., `*test*`)
4. **Use exact matches** when possible
5. **Limit result sets** with appropriate limits

### Indexing

The implementation supports Neo4j full-text indexes:

```bash
# Reindex a project
curl -X POST http://localhost:8000/api/v1/projects/my-project/search/reindex
```

## Error Handling

### Query Syntax Errors

Invalid queries return helpful error messages:

```json
{
  "detail": "Invalid query syntax: Unclosed quote at position 15"
}
```

Common errors:
- Unclosed quotes
- Unbalanced parentheses
- Empty queries
- Invalid field names (no error, just no results)

### Service Errors

Search failures return 500 errors with details:

```json
{
  "detail": "Search failed: Database connection error"
}
```

## Future Enhancements

Potential improvements for future versions:

1. **Fuzzy matching in advanced search**: Currently disabled for advanced queries
2. **Field type awareness**: Type-specific matching (date ranges, numeric comparisons)
3. **Query optimization**: Reorder query terms for optimal performance
4. **Query caching**: Cache parsed queries for repeated searches
5. **Proximity search**: Find terms within N words of each other
6. **Regular expression support**: Full regex in addition to wildcards
7. **Saved queries**: Save and reuse complex queries
8. **Query builder UI**: Visual query builder for complex searches

## Migration Guide

### Upgrading from Simple Search

Before:
```python
query = SearchQuery(query="john@gmail.com")
results, total = await service.search(query)
```

After (using advanced search):
```python
query = SearchQuery(
    query="email:john@gmail.com",
    advanced=True
)
results, total = await service.search(query)
```

### No Breaking Changes

All existing code continues to work. Advanced search is opt-in via:
- `advanced=True` parameter in `SearchQuery`
- `/advanced` endpoint in the API

## Troubleshooting

### Query Not Matching Expected Results

1. Check field names: Use `/api/v1/search/fields` to list searchable fields
2. Verify syntax: Use `/api/v1/search/syntax-help` for examples
3. Test simpler queries: Break down complex queries
4. Check case sensitivity: Searches are case-insensitive
5. Verify wildcards: Ensure wildcards are in correct positions

### Performance Issues

1. Simplify query: Remove unnecessary operators
2. Use field-specific searches: More efficient than global
3. Add indexes: Reindex project if needed
4. Limit results: Use appropriate limit parameter
5. Check entity count: Large numbers of entities slow searches

## Support

For issues or questions:
1. Check test suite examples in `tests/test_advanced_search.py`
2. Run demo script: `python test_advanced_search_demo.py`
3. Review syntax help: `/api/v1/search/syntax-help`
4. Check logs for detailed error messages

## Summary

The advanced search implementation provides powerful, flexible search capabilities while maintaining backward compatibility. The query parser, search evaluator, and API endpoints work together to enable complex investigations with boolean logic, wildcards, and field-specific searches.

**Files Modified:**
- `/home/devel/basset-hound/api/services/search_service.py` (enhanced)
- `/home/devel/basset-hound/api/routers/search.py` (enhanced)

**Files Added:**
- `/home/devel/basset-hound/tests/test_advanced_search.py` (comprehensive tests)
- `/home/devel/basset-hound/test_advanced_search_demo.py` (demo script)
- `/home/devel/basset-hound/ADVANCED_SEARCH_IMPLEMENTATION.md` (this document)
