# Smart Suggestions API Reference

**Phase 43: Smart Suggestions & Data Matching System**

Complete API reference for all Smart Suggestions endpoints, MCP tools, and services.

## Table of Contents

- [MCP Tools](#mcp-tools)
  - [Data Management](#data-management-tools)
  - [File Hashing](#file-hashing-tools)
  - [Matching Engine](#matching-engine-tools-future)
- [Services](#services)
  - [DataService](#dataservice)
  - [FileHashService](#filehashservice)
  - [MatchingEngine](#matchingengine)
- [Models](#models)
  - [DataItem](#dataitem)
  - [MatchResult](#matchresult)
- [REST API Endpoints (Future)](#rest-api-endpoints-future)

---

## MCP Tools

### Data Management Tools

#### create_data_item

Create a new DataItem in a project.

**Parameters:**
- `project_id` (str): Project ID or safe_name
- `data_type` (str): Type of data (email, phone, image, document, etc.)
- `value` (Any): The actual data value or file path
- `entity_id` (Optional[str]): Entity ID to link to
- `orphan_id` (Optional[str]): Orphan ID to link to
- `metadata` (Optional[Dict]): Metadata dictionary (source, confidence, etc.)

**Returns:**
```python
{
    "id": "data_abc123",
    "type": "email",
    "value": "test@example.com",
    "normalized_value": "test@example.com",
    "entity_id": "entity-123",
    "orphan_id": null,
    "created_at": "2026-01-09T10:00:00",
    "metadata": {"source": "Investigation #42"}
}
```

**Example:**
```python
result = create_data_item(
    project_id="my_investigation",
    data_type="email",
    value="suspect@example.com",
    entity_id="entity-123",
    metadata={"source": "Email intercept", "confidence": "high"}
)
```

---

#### get_data_item

Get a DataItem by ID.

**Parameters:**
- `project_id` (str): Project ID or safe_name
- `data_id` (str): DataItem ID (format: data_abc123)

**Returns:**
```python
{
    "id": "data_abc123",
    "type": "email",
    "value": "test@example.com",
    "normalized_value": "test@example.com",
    "entity_id": "entity-123",
    "created_at": "2026-01-09T10:00:00",
    "metadata": {}
}
```

**Errors:**
- `{"error": "Project not found: project_id"}`
- `{"error": "DataItem not found: data_id"}`

---

#### list_entity_data

List all DataItems linked to an entity.

**Parameters:**
- `project_id` (str): Project ID or safe_name
- `entity_id` (str): Entity (Person) ID
- `data_type` (Optional[str]): Filter by data type

**Returns:**
```python
{
    "data_items": [
        {
            "id": "data_abc123",
            "type": "email",
            "value": "test@example.com",
            ...
        },
        {
            "id": "data_def456",
            "type": "phone",
            "value": "+15551234567",
            ...
        }
    ],
    "count": 2,
    "entity_id": "entity-123"
}
```

**Example:**
```python
# Get all data for entity
all_data = list_entity_data(
    project_id="my_investigation",
    entity_id="entity-123"
)

# Get only emails
emails = list_entity_data(
    project_id="my_investigation",
    entity_id="entity-123",
    data_type="email"
)
```

---

#### delete_data_item

Delete a DataItem by ID.

**Parameters:**
- `project_id` (str): Project ID or safe_name
- `data_id` (str): DataItem ID to delete

**Returns:**
```python
{
    "success": True,
    "data_id": "data_abc123"
}
```

**Errors:**
- `{"error": "DataItem not found: data_id"}`

---

#### link_data_to_entity

Link a DataItem to an entity.

Creates a HAS_DATA relationship between entity and data item.

**Parameters:**
- `project_id` (str): Project ID or safe_name
- `data_id` (str): DataItem ID
- `entity_id` (str): Entity (Person) ID

**Returns:**
```python
{
    "success": True,
    "data_id": "data_abc123",
    "entity_id": "entity-123"
}
```

**Errors:**
- `{"error": "Failed to link data item ... to entity ..."}`

---

#### unlink_data_from_entity

Unlink a DataItem from its entity.

Removes HAS_DATA relationship and clears entity_id.

**Parameters:**
- `project_id` (str): Project ID or safe_name
- `data_id` (str): DataItem ID

**Returns:**
```python
{
    "success": True,
    "data_id": "data_abc123"
}
```

---

#### find_similar_data

Find DataItems with similar values.

Uses normalized value comparison for duplicate detection.

**Parameters:**
- `project_id` (str): Project ID or safe_name
- `value` (Any): Value to search for
- `data_type` (str): Type of data (email, phone, etc.)
- `exclude_id` (Optional[str]): DataItem ID to exclude from results

**Returns:**
```python
{
    "similar_items": [
        {
            "id": "data_def456",
            "type": "email",
            "value": "test@example.com",
            "normalized_value": "test@example.com",
            "entity_id": "entity-456"
        }
    ],
    "count": 1,
    "search_value": "Test@Example.COM",
    "normalized_value": "test@example.com",
    "data_type": "email"
}
```

**Example:**
```python
# Find entities with same email
similar = find_similar_data(
    project_id="my_investigation",
    value="Test@Example.COM",  # Case-insensitive
    data_type="email"
)
# Returns entities with "test@example.com"
```

---

#### find_duplicate_files

Find DataItems with the same file hash.

Computes SHA-256 hash and searches for duplicates.

**Parameters:**
- `project_id` (str): Project ID or safe_name
- `file_path` (str): Path to file to check

**Returns:**
```python
{
    "duplicates": [
        {
            "id": "data_abc123",
            "type": "file",
            "value": "evidence.jpg",
            "hash": "abc123...",
            "entity_id": "entity-123"
        }
    ],
    "count": 1,
    "file_path": "/path/to/file.jpg",
    "file_hash": "abc123..."
}
```

---

### File Hashing Tools

#### compute_file_hash

Compute SHA-256 hash for a file.

**Parameters:**
- `project_id` (str): Project ID or safe_name
- `file_path` (str): Path to file (relative to project or absolute)

**Returns:**
```python
{
    "success": True,
    "hash": "a1b2c3d4e5f6...",  # 64 hex characters
    "file_path": "entity-123/files/evidence.jpg",
    "size": 52481,
    "algorithm": "sha256"
}
```

**Errors:**
- `{"error": "File not found: file_path"}`
- `{"error": "Failed to compute hash: ..."}`

**Example:**
```python
result = compute_file_hash(
    project_id="my_investigation",
    file_path="entity-123/files/evidence.jpg"
)
# Returns: {"hash": "abc123...", "size": 52481, ...}
```

---

#### verify_file_integrity

Verify a file matches an expected hash.

**Parameters:**
- `project_id` (str): Project ID or safe_name
- `file_path` (str): Path to file
- `expected_hash` (str): Expected SHA-256 hash (64 hex chars)

**Returns:**
```python
{
    "success": True,
    "valid": True,
    "actual_hash": "abc123...",
    "expected_hash": "abc123...",
    "file_path": "evidence.jpg",
    "status": "VERIFIED"
}
```

**Status Values:**
- `VERIFIED`: Hash matches
- `MISMATCH`: Hash does not match

**Example:**
```python
result = verify_file_integrity(
    project_id="my_investigation",
    file_path="evidence.jpg",
    expected_hash="abc123..."
)

if result["valid"]:
    print("File integrity verified!")
else:
    print("WARNING: File has been modified!")
```

---

#### find_duplicates_by_hash

Find all files with the same hash.

Searches entities and orphan data for matching hashes.

**Parameters:**
- `project_id` (str): Project ID or safe_name
- `file_hash` (str): SHA-256 hash (64 hex chars)

**Returns:**
```python
{
    "success": True,
    "hash": "abc123...",
    "total_matches": 3,
    "entity_matches": [
        {
            "type": "entity",
            "entity_id": "entity-123",
            "field_path": "evidence.photo1",
            "hash": "abc123..."
        },
        {
            "type": "entity",
            "entity_id": "entity-456",
            "field_path": "evidence.image",
            "hash": "abc123..."
        }
    ],
    "orphan_matches": [
        {
            "type": "orphan",
            "orphan_id": "orphan-789",
            "identifier_type": "file",
            "hash": "abc123..."
        }
    ],
    "suggestions": [
        "Same file appears in 2 entities and 1 orphan data",
        "Consider linking orphan-789 to an existing entity",
        "Entities with this file: entity-123, entity-456"
    ]
}
```

**Example:**
```python
# Find where screenshot.png appears
result = find_duplicates_by_hash(
    project_id="my_investigation",
    file_hash="abc123..."
)

for match in result["entity_matches"]:
    print(f"Found in entity: {match['entity_id']}")

for suggestion in result["suggestions"]:
    print(f"Suggestion: {suggestion}")
```

---

#### find_data_by_hash

Alias for `find_duplicates_by_hash`.

---

### Matching Engine Tools (Future)

#### find_matches

Find potential matches for a value.

**Parameters:**
- `value` (str): Value to search for
- `field_type` (str): Type of field (email, phone, name, address, etc.)
- `include_partial` (bool, default=False): Include fuzzy matches
- `confidence_threshold` (float, default=0.5): Minimum confidence (0.0-1.0)

**Returns:**
```python
{
    "matches": [
        {
            "entity_id": "entity-123",
            "field_type": "core.email",
            "field_value": "test@example.com",
            "confidence": 0.95,
            "match_type": "exact_string"
        },
        {
            "entity_id": "entity-456",
            "field_type": "core.email",
            "field_value": "test@example.net",
            "confidence": 0.75,
            "match_type": "partial_string"
        }
    ],
    "count": 2,
    "search_value": "test@example.com"
}
```

---

## Services

### DataService

Async service for DataItem CRUD operations.

#### Constructor

```python
from api.services.data_service import DataService
from api.services.neo4j_service import AsyncNeo4jService

async with AsyncNeo4jService() as neo4j:
    service = DataService(neo4j)
```

#### Methods

##### async create_data_item(data_item: DataItem) -> DataItem

Create a DataItem in Neo4j.

```python
from api.models.data_item import DataItem
from datetime import datetime

data_item = DataItem(
    id=DataItem.generate_id(),
    type="email",
    value="test@example.com",
    normalized_value="test@example.com",
    entity_id="entity-123",
    created_at=datetime.now()
)

created = await service.create_data_item(data_item)
```

---

##### async get_data_item(data_id: str) -> Optional[DataItem]

Get DataItem by ID.

```python
item = await service.get_data_item("data_abc123")
if item:
    print(f"Found: {item.value}")
else:
    print("Not found")
```

---

##### async list_data_items(entity_id: str = None, orphan_id: str = None, data_type: str = None) -> List[DataItem]

List DataItems with optional filtering.

```python
# All data for entity
all_data = await service.list_data_items(entity_id="entity-123")

# Only emails
emails = await service.list_data_items(
    entity_id="entity-123",
    data_type="email"
)

# All orphan data
orphans = await service.list_data_items(orphan_id="orphan-456")
```

---

##### async delete_data_item(data_id: str) -> bool

Delete DataItem by ID.

```python
deleted = await service.delete_data_item("data_abc123")
if deleted:
    print("Deleted successfully")
```

---

##### async link_data_to_entity(data_id: str, entity_id: str) -> bool

Link DataItem to entity.

```python
linked = await service.link_data_to_entity("data_abc123", "entity-123")
```

---

##### async unlink_data_from_entity(data_id: str) -> bool

Unlink DataItem from entity.

```python
unlinked = await service.unlink_data_from_entity("data_abc123")
```

---

##### async find_similar_data(normalized_value: str, data_type: str, exclude_id: str = None) -> List[DataItem]

Find DataItems with similar normalized values.

```python
similar = await service.find_similar_data(
    normalized_value="test@example.com",
    data_type="email",
    exclude_id="data_abc123"  # Don't include this one
)
```

---

##### async find_by_hash(file_hash: str) -> List[DataItem]

Find DataItems with matching file hash.

```python
duplicates = await service.find_by_hash("abc123...")
```

---

### FileHashService

Synchronous service for file hashing operations.

#### Constructor

```python
from api.services.file_hash_service import FileHashService

service = FileHashService()
```

#### Methods

##### compute_hash(file_path: str) -> str

Compute SHA-256 hash of file.

```python
file_hash = service.compute_hash("/path/to/file.jpg")
# Returns: "abc123..." (64 hex characters)
```

**Raises:**
- `FileNotFoundError`: File does not exist
- `IOError`: Error reading file

---

##### compute_hash_with_metadata(file_path: str) -> Dict

Compute hash with file metadata.

```python
metadata = service.compute_hash_with_metadata("/path/to/file.jpg")
# Returns:
# {
#     "hash": "abc123...",
#     "size": 52481,
#     "filename": "file.jpg",
#     "algorithm": "sha256"
# }
```

---

##### compute_hash_from_bytes(data: bytes) -> str

Compute hash from byte data.

```python
data = b"Hello, World!"
file_hash = service.compute_hash_from_bytes(data)
```

---

##### verify_hash(file_path: str, expected_hash: str) -> bool

Verify file matches expected hash.

```python
is_valid = service.verify_hash("/path/to/file.jpg", "abc123...")
if is_valid:
    print("File integrity verified")
else:
    print("WARNING: File has been modified!")
```

**Raises:**
- `ValueError`: Invalid hash format
- `FileNotFoundError`: File does not exist

---

### MatchingEngine

Async service for finding data matches.

#### Constructor

```python
from api.services.matching_engine import MatchingEngine

async with MatchingEngine() as engine:
    matches = await engine.find_exact_string_matches("test@example.com", "email")
```

#### Methods

##### async find_exact_hash_matches(hash_value: str) -> List[MatchResult]

Find exact matches by file hash.

**Confidence**: 1.0 (100%)

```python
matches = await engine.find_exact_hash_matches("abc123...")

for match in matches:
    print(f"Entity: {match.entity_id}")
    print(f"Field: {match.field_type}")
    print(f"Value: {match.field_value}")
```

---

##### async find_exact_string_matches(value: str, field_type: str) -> List[MatchResult]

Find exact matches by normalized string.

**Confidence**: 0.95 (95%)

```python
matches = await engine.find_exact_string_matches(
    "Test@Example.COM",  # Case-insensitive
    "email"
)
```

**Supported field_type values:**
- `email`
- `phone`
- `username`
- `crypto_address`
- `url`
- `ip_address`

---

##### async find_partial_matches(value: str, field_type: str, threshold: float = 0.7) -> List[MatchResult]

Find partial (fuzzy) matches.

**Confidence**: 0.5-0.9 (based on similarity)

```python
matches = await engine.find_partial_matches(
    "John Doe",
    "name",
    threshold=0.7  # 70% similarity minimum
)

for match in matches:
    print(f"Match: {match.field_value}")
    # Note: Confidence calculated separately in find_all_matches
```

**Algorithms used:**
- Names: Jaro-Winkler
- Addresses: Token Set Ratio
- General: Levenshtein

---

##### async find_all_matches(value: str, field_type: str, include_partial: bool = False, partial_threshold: float = 0.7) -> List[Tuple[MatchResult, float, str]]

Combined matching using all strategies.

**Returns**: List of (MatchResult, confidence, match_type) tuples

```python
matches = await engine.find_all_matches(
    "test@example.com",
    "email",
    include_partial=True,
    partial_threshold=0.7
)

for match, confidence, match_type in matches:
    print(f"Entity: {match.entity_id}")
    print(f"Confidence: {confidence:.2f}")
    print(f"Type: {match_type}")
    # match_type: "exact_hash", "exact_string", or "partial_string"
```

---

## Models

### DataItem

Model representing a discrete piece of data.

#### Fields

```python
class DataItem:
    id: str                    # Format: data_abc123
    type: str                  # email, phone, image, etc.
    value: Any                 # Actual data value
    normalized_value: str      # Normalized for matching
    entity_id: Optional[str]   # Linked entity
    orphan_id: Optional[str]   # Linked orphan
    created_at: datetime       # Creation timestamp
    updated_at: Optional[datetime]
    metadata: Dict[str, Any]   # Additional metadata
```

#### Methods

##### static generate_id() -> str

Generate unique DataItem ID.

```python
data_id = DataItem.generate_id()
# Returns: "data_abc12345"
```

---

##### static normalize_value(value: Any, data_type: str) -> str

Normalize value for matching.

```python
# Email normalization
normalized = DataItem.normalize_value("User@EXAMPLE.COM", "email")
# Returns: "user@example.com"

# Phone normalization
normalized = DataItem.normalize_value("+1 (555) 123-4567", "phone")
# Returns: "15551234567"
```

---

##### to_dict() -> Dict

Convert to dictionary.

```python
item = DataItem(id="data_abc123", type="email", value="test@example.com", ...)
data = item.to_dict()
# Returns:
# {
#     "id": "data_abc123",
#     "type": "email",
#     "value": "test@example.com",
#     ...
# }
```

---

### MatchResult

Model representing a match result.

#### Fields

```python
class MatchResult:
    entity_id: Optional[str]   # Matched entity ID
    orphan_id: Optional[str]   # Matched orphan ID
    field_type: str            # Field that matched (e.g., "core.email")
    field_value: Any           # Value that matched
    data_id: Optional[str]     # DataItem ID if applicable
```

#### Methods

##### to_dict() -> Dict

Convert to dictionary.

```python
match = MatchResult(
    entity_id="entity-123",
    field_type="core.email",
    field_value="test@example.com"
)
data = match.to_dict()
```

---

## REST API Endpoints (Future)

### Suggestions

#### GET /api/v1/suggestions/entity/{entity_id}

Get all suggestions for an entity.

**Query Parameters:**
- `min_confidence` (float, default=0.5): Minimum confidence threshold
- `max_results` (int, default=20): Maximum suggestions to return
- `include_dismissed` (bool, default=false): Include dismissed suggestions

**Response:**
```json
{
    "entity_id": "entity-123",
    "suggestions": [
        {
            "suggested_entity_id": "entity-456",
            "confidence": 0.95,
            "match_type": "exact_string",
            "field": "email",
            "value": "test@example.com",
            "created_at": "2026-01-09T10:00:00"
        }
    ],
    "count": 1
}
```

---

#### GET /api/v1/suggestions/orphan/{orphan_id}

Get entity suggestions for orphan data.

**Response:**
```json
{
    "orphan_id": "orphan-123",
    "suggestions": [
        {
            "entity_id": "entity-456",
            "confidence": 0.95,
            "match_type": "exact_string",
            "field": "phone"
        }
    ],
    "count": 1
}
```

---

#### POST /api/v1/suggestions/find-matches

Find matches for arbitrary value.

**Request Body:**
```json
{
    "value": "test@example.com",
    "field_type": "email",
    "options": {
        "include_partial": true,
        "confidence_threshold": 0.7
    }
}
```

**Response:**
```json
{
    "matches": [
        {
            "entity_id": "entity-123",
            "confidence": 0.95,
            "match_type": "exact_string",
            "field_value": "test@example.com"
        }
    ],
    "count": 1
}
```

---

#### POST /api/v1/suggestions/{suggestion_id}/dismiss

Dismiss a suggestion.

**Response:**
```json
{
    "success": true,
    "suggestion_id": "suggestion-123",
    "dismissed": true
}
```

---

#### POST /api/v1/suggestions/{suggestion_id}/link

Accept suggestion and link entities.

**Response:**
```json
{
    "success": true,
    "entity_id": "entity-123",
    "linked_entity_id": "entity-456",
    "relationship_created": true
}
```

---

#### POST /api/v1/suggestions/batch

Generate suggestions for multiple entities.

**Request Body:**
```json
{
    "entity_ids": ["entity-123", "entity-456", "entity-789"],
    "min_confidence": 0.7
}
```

**Response:**
```json
{
    "results": [
        {
            "entity_id": "entity-123",
            "suggestions": [...],
            "count": 2
        },
        {
            "entity_id": "entity-456",
            "suggestions": [...],
            "count": 1
        }
    ],
    "total_suggestions": 3
}
```

---

## Error Responses

All API endpoints follow consistent error response format:

```json
{
    "error": "Error message",
    "code": "ERROR_CODE",
    "details": {
        "field": "Additional context"
    }
}
```

### Common Error Codes

- `PROJECT_NOT_FOUND`: Project does not exist
- `DATA_NOT_FOUND`: DataItem not found
- `ENTITY_NOT_FOUND`: Entity not found
- `ORPHAN_NOT_FOUND`: Orphan data not found
- `INVALID_HASH`: Invalid hash format
- `FILE_NOT_FOUND`: File does not exist
- `VALIDATION_ERROR`: Invalid input parameters
- `NEO4J_ERROR`: Database operation failed

---

## Examples

### Complete Workflow Example

```python
import asyncio
from api.services.data_service import DataService
from api.services.matching_engine import MatchingEngine
from api.services.neo4j_service import AsyncNeo4jService
from api.models.data_item import DataItem
from datetime import datetime

async def complete_workflow():
    async with AsyncNeo4jService() as neo4j:
        # Initialize services
        data_service = DataService(neo4j)
        matching_engine = MatchingEngine()
        matching_engine.neo4j = neo4j

        # 1. Create data item
        item = DataItem(
            id=DataItem.generate_id(),
            type="email",
            value="suspect@example.com",
            normalized_value="suspect@example.com",
            entity_id="entity-123",
            created_at=datetime.now()
        )
        created = await data_service.create_data_item(item)
        print(f"Created: {created.id}")

        # 2. Find similar data
        similar = await data_service.find_similar_data(
            normalized_value="suspect@example.com",
            data_type="email"
        )
        print(f"Found {len(similar)} similar items")

        # 3. Find exact matches
        matches = await matching_engine.find_exact_string_matches(
            "suspect@example.com",
            "email"
        )
        print(f"Found {len(matches)} exact matches")

        # 4. Find all matches (combined)
        all_matches = await matching_engine.find_all_matches(
            "suspect@example.com",
            "email",
            include_partial=True
        )

        for match, confidence, match_type in all_matches:
            print(f"Match: {match.entity_id}")
            print(f"Confidence: {confidence:.2f}")
            print(f"Type: {match_type}")

asyncio.run(complete_workflow())
```

---

**Version**: 1.0
**Last Updated**: 2026-01-09
**Phase**: 43.6 - Integration Testing and Documentation
