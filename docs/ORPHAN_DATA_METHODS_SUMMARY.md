# Orphan Data Methods Implementation Summary

## Overview
Added comprehensive orphan data management methods to the `Neo4jHandler` class in `/home/devel/basset-hound/neo4j_handler.py`.

## Methods Implemented

### 1. `create_orphan_data(project_id, orphan_data)`
Creates a new `:OrphanData` node linked to a project via `:HAS_ORPHAN` relationship.

**Features:**
- Auto-generates UUID if not provided
- Stores all standard fields: identifier_type, identifier_value, source_file, source_location, context, notes
- Handles tags as a list (supports ANY match in queries)
- Serializes metadata dict to JSON
- Sets created_at and updated_at timestamps
- Returns the created orphan node with parsed metadata

**Cypher Pattern:**
```cypher
MATCH (project:Project {safe_name: $project_id})
CREATE (orphan:OrphanData)
SET orphan = $props
CREATE (project)-[:HAS_ORPHAN]->(orphan)
RETURN orphan
```

### 2. `get_orphan_data(project_id, orphan_id)`
Retrieves a single orphan data node by ID with linked entity information.

**Features:**
- Returns orphan node properties as dict
- Includes linked_entity_ids if the orphan has `:LINKED_TO` relationships
- Parses metadata JSON back to dict

**Cypher Pattern:**
```cypher
MATCH (project:Project {safe_name: $project_id})-[:HAS_ORPHAN]->(orphan:OrphanData {id: $orphan_id})
OPTIONAL MATCH (orphan)-[:LINKED_TO]->(entity:Person)
RETURN orphan, collect(entity.id) as linked_entity_ids
```

### 3. `list_orphan_data(project_id, filters, limit, offset)`
Lists orphan data with flexible filtering and pagination.

**Supported Filters:**
- `identifier_type`: Exact match on identifier type
- `tags`: List of tags (ANY tag must match)
- `linked`: Boolean filter for linked status
- `date_from`: Filter created_at >= date_from
- `date_to`: Filter created_at <= date_to

**Features:**
- Dynamic WHERE clause construction
- Database-level pagination with SKIP/LIMIT
- Returns list of orphan dicts with parsed metadata

**Example:**
```python
orphans = handler.list_orphan_data(
    "my_project",
    filters={"identifier_type": "email", "linked": False},
    limit=50,
    offset=0
)
```

### 4. `update_orphan_data(project_id, orphan_id, updates)`
Updates orphan node properties using Cypher's `SET +=` operator.

**Features:**
- Automatically sets updated_at timestamp
- Handles metadata dict serialization
- Returns updated node with parsed metadata

**Cypher Pattern:**
```cypher
MATCH (project:Project {safe_name: $project_id})-[:HAS_ORPHAN]->(orphan:OrphanData {id: $orphan_id})
SET orphan += $updates
RETURN orphan
```

### 5. `delete_orphan_data(project_id, orphan_id)`
Deletes an orphan node and all its relationships.

**Features:**
- Uses DETACH DELETE to remove all relationships
- Returns True if deleted, False otherwise

**Cypher Pattern:**
```cypher
MATCH (project:Project {safe_name: $project_id})-[:HAS_ORPHAN]->(orphan:OrphanData {id: $orphan_id})
DETACH DELETE orphan
RETURN count(orphan) as deleted_count
```

### 6. `search_orphan_data(project_id, query, limit)`
Full-text search across orphan data fields.

**Searchable Fields:**
- identifier_value
- source_file
- context
- notes

**Features:**
- Case-insensitive CONTAINS matching
- Searches across multiple fields with OR
- Returns up to limit results ordered by created_at DESC

**Cypher Pattern:**
```cypher
MATCH (project:Project {safe_name: $project_id})-[:HAS_ORPHAN]->(orphan:OrphanData)
WHERE toLower(orphan.identifier_value) CONTAINS toLower($query)
   OR toLower(orphan.source_file) CONTAINS toLower($query)
   OR toLower(orphan.context) CONTAINS toLower($query)
   OR toLower(orphan.notes) CONTAINS toLower($query)
RETURN orphan
ORDER BY orphan.created_at DESC
LIMIT $limit
```

### 7. `find_duplicate_orphans(project_id)`
Identifies duplicate orphan records based on identifier_value.

**Features:**
- Groups orphans by identifier_value
- Returns only groups with 2+ members
- Ordered by group size (most duplicates first)
- Includes full orphan data for each duplicate

**Cypher Pattern:**
```cypher
MATCH (project:Project {safe_name: $project_id})-[:HAS_ORPHAN]->(orphan:OrphanData)
WHERE orphan.identifier_value IS NOT NULL AND orphan.identifier_value <> ''
WITH orphan.identifier_value as identifier_value, collect(orphan) as orphans
WHERE size(orphans) > 1
RETURN identifier_value, orphans
ORDER BY size(orphans) DESC
```

### 8. `link_orphan_to_entity(orphan_id, entity_id)`
Creates a `:LINKED_TO` relationship between an orphan and a Person entity.

**Features:**
- Verifies both nodes exist before creating relationship
- Uses MERGE to prevent duplicate relationships
- Sets created_at timestamp on relationship
- Updates orphan's linked status to true
- Returns relationship information

**Cypher Pattern:**
```cypher
MATCH (orphan:OrphanData {id: $orphan_id})
MATCH (entity:Person {id: $entity_id})
MERGE (orphan)-[r:LINKED_TO]->(entity)
ON CREATE SET r.created_at = $timestamp
SET orphan.linked = true,
    orphan.updated_at = $timestamp
RETURN orphan, entity, r
```

### 9. `count_orphan_data(project_id, filters)`
Counts orphan data with the same filter support as list_orphan_data.

**Features:**
- Supports all the same filters as list_orphan_data
- Efficient count-only query
- Returns integer count

## Database Schema Updates

### Constraints and Indexes Added
Updated `ensure_constraints()` method with:

```python
"CREATE CONSTRAINT IF NOT EXISTS FOR (o:OrphanData) REQUIRE o.id IS UNIQUE",
"CREATE INDEX IF NOT EXISTS FOR (o:OrphanData) ON (o.identifier_type)",
"CREATE INDEX IF NOT EXISTS FOR (o:OrphanData) ON (o.identifier_value)",
"CREATE INDEX IF NOT EXISTS FOR (o:OrphanData) ON (o.linked)",
"CREATE INDEX IF NOT EXISTS FOR (o:OrphanData) ON (o.created_at)",
```

### Node Structure
```
:OrphanData {
  id: string (UUID, unique)
  identifier_type: string
  identifier_value: string
  source_file: string
  source_location: string
  context: string
  notes: string
  tags: [string]
  linked: boolean
  created_at: ISO datetime string
  updated_at: ISO datetime string
  metadata: JSON string (optional)
}
```

### Relationships
- `(Project)-[:HAS_ORPHAN]->(OrphanData)` - Links orphan to project
- `(OrphanData)-[:LINKED_TO]->(Person)` - Links orphan to matched entity

## Design Patterns Used

1. **Consistent with Existing Code**: Follows the same patterns as Person/File methods
2. **Clean Data Helper**: Uses `self.clean_data()` for Neo4j compatibility
3. **JSON Serialization**: Metadata and tags handled properly for Neo4j storage
4. **Batch Operations Ready**: Query patterns support UNWIND for future batch methods
5. **Filter Building**: Dynamic WHERE clause construction for flexible queries
6. **Pagination**: Database-level SKIP/LIMIT for efficient large datasets
7. **Error Handling**: Returns None on failures, verifies node existence
8. **Timestamp Management**: Automatic created_at/updated_at tracking

## Test Coverage

Created comprehensive test script at `/home/devel/basset-hound/test_orphan_methods.py` that validates:
- Creating orphan data
- Retrieving by ID
- Listing with pagination
- Filtering by type, tags, and linked status
- Counting with filters
- Updating properties
- Searching text fields
- Finding duplicates
- Linking to entities
- Deleting orphans

## Usage Example

```python
from neo4j_handler import Neo4jHandler

handler = Neo4jHandler()

# Create orphan data
orphan = handler.create_orphan_data("my_project", {
    "identifier_type": "email",
    "identifier_value": "unknown@example.com",
    "source_file": "import.csv",
    "source_location": "row 42",
    "tags": ["import", "needs_review"],
    "metadata": {"confidence": 0.85}
})

# List unlinked orphans
unlinked = handler.list_orphan_data(
    "my_project",
    filters={"linked": False},
    limit=100
)

# Search for orphans
results = handler.search_orphan_data("my_project", "example.com")

# Find duplicates
duplicates = handler.find_duplicate_orphans("my_project")

# Link to entity
handler.link_orphan_to_entity(orphan["id"], person_id)

# Count orphans by type
email_count = handler.count_orphan_data(
    "my_project",
    filters={"identifier_type": "email"}
)

handler.close()
```

## File Locations
- Implementation: `/home/devel/basset-hound/neo4j_handler.py` (lines 1946-2362)
- Test Script: `/home/devel/basset-hound/test_orphan_methods.py`
- Documentation: `/home/devel/basset-hound/ORPHAN_DATA_METHODS_SUMMARY.md`
