# Phase 43.5: Linking Actions - Implementation Report

**Date:** 2026-01-09
**Phase:** 43.5 (Smart Suggestions - Linking Actions)
**Status:** ✅ Complete

---

## Executive Summary

Phase 43.5 implements a comprehensive linking action system that enables users to act on smart suggestions with proper audit trails and human accountability. This system provides five core operations:

1. **Link DataItems** - Connect duplicate or related data
2. **Merge Entities** - Combine duplicate entity profiles
3. **Create Relationships** - Establish connections from suggestions
4. **Link Orphans** - Convert orphan data to entity data
5. **Dismiss Suggestions** - Track rejected suggestions

All operations require explicit user intent (reason parameter) and create detailed audit trails for compliance and accountability.

---

## Implementation Details

### 1. Core Service: `api/services/linking_service.py`

Created `LinkingService` class with five main operations and comprehensive audit trail support.

#### Key Features:

- **Reason Required**: All operations require a human-readable reason parameter
- **Audit Trail**: Every action creates a `LinkingAction` node in Neo4j
- **Reversibility Warnings**: Entity merges are marked as irreversible
- **Bidirectional Relationships**: Symmetric relationships create inverse links
- **Profile Merging**: Intelligent merging of entity profiles (lists combined, duplicates removed)

#### Operations:

##### 1. Link Data Items
```python
async def link_data_items(
    data_id_1: str,
    data_id_2: str,
    reason: str,
    confidence: float = 0.8,
    created_by: str = "system",
) -> Dict
```

**Purpose**: Link two DataItems with LINKED_TO relationship
**Use Case**: Same email/phone/image appearing in different contexts
**Neo4j Relationship**: Creates bidirectional `(DataItem)-[:LINKED_TO]->(DataItem)`

**Properties**:
- `reason`: Human explanation
- `confidence`: 0.0-1.0 score
- `created_at`: Timestamp
- `created_by`: User/system identifier
- `action_id`: Unique action ID for audit

##### 2. Merge Entities
```python
async def merge_entities(
    entity_id_1: str,
    entity_id_2: str,
    keep_entity_id: str,
    reason: str,
    created_by: str = "system",
) -> Dict
```

**Purpose**: Merge duplicate entities (IRREVERSIBLE)
**Use Case**: Same person with multiple profiles
**Operations**:
1. Move all DataItems from discarded entity to kept entity
2. Merge profile data (intelligent list combination)
3. Move all relationships to kept entity
4. Mark discarded entity with `merged_into` property

**Profile Merging Logic**:
- Keep entity values take precedence
- Lists are combined and deduplicated
- Nested dicts merged recursively
- New sections/fields from discard entity added

##### 3. Create Relationship from Suggestion
```python
async def create_relationship_from_suggestion(
    entity_id_1: str,
    entity_id_2: str,
    relationship_type: str,
    reason: str,
    confidence: Optional[str] = None,
    created_by: str = "system",
) -> Dict
```

**Purpose**: Create relationship when entities are related but NOT duplicates
**Use Case**: Shared address → FAMILY, NEIGHBOR, or WORKS_WITH
**Neo4j Relationship**: Creates `(Person)-[:TAGGED]->(Person)` with properties

**Relationship Types** (from `api/models/relationship.py`):
- Generic: RELATED_TO, KNOWS
- Professional: WORKS_WITH, COLLEAGUE, BUSINESS_PARTNER
- Family: FAMILY, MARRIED_TO, PARENT_OF, SIBLING_OF
- Social: FRIEND, ACQUAINTANCE, NEIGHBOR
- Investigative: ASSOCIATED_WITH, SUSPECTED_ASSOCIATE, ALIAS_OF

**Symmetric Handling**: Automatically creates inverse for symmetric types (WORKS_WITH, MARRIED_TO, etc.)

##### 4. Link Orphan to Entity
```python
async def link_orphan_to_entity(
    orphan_id: str,
    entity_id: str,
    reason: str,
    created_by: str = "system",
) -> Dict
```

**Purpose**: Convert orphan data to entity data
**Use Case**: Orphan email matches entity email
**Operations**:
1. Move all DataItems from orphan to entity
2. Update DataItem `entity_id` and clear `orphan_id`
3. Mark orphan as `resolved=true` with resolution details

##### 5. Dismiss Suggestion
```python
async def dismiss_suggestion(
    entity_id: str,
    data_id: str,
    reason: str,
    created_by: str = "system",
) -> Dict
```

**Purpose**: Track rejected suggestions to prevent reappearance
**Use Case**: User explicitly rejects a false match
**Neo4j Relationship**: Creates `(Entity)-[:DISMISSED_SUGGESTION]->(DataItem)`

**Properties**:
- `reason`: Why suggestion was dismissed
- `dismissed_at`: Timestamp
- `dismissed_by`: User identifier
- `action_id`: For audit trail

---

### 2. MCP Tools: `basset_mcp/tools/linking.py`

Created 6 MCP tools for agent and API access to linking operations.

#### Tools Implemented:

1. **`link_data_items(project_id, data_id_1, data_id_2, reason, confidence)`**
   - Link two DataItems together
   - Returns: success, action_id, linked_data_items, reason, confidence

2. **`merge_entities(project_id, entity_id_1, entity_id_2, keep_entity_id, reason)`**
   - Merge duplicate entities (IRREVERSIBLE)
   - Returns: success, action_id, kept_entity_id, merged_entity_id, data_items_moved, relationships_moved
   - Includes warning about irreversibility

3. **`create_relationship_from_match(project_id, entity_id_1, entity_id_2, relationship_type, reason, confidence)`**
   - Create relationship from suggestion
   - Returns: success, action_id, source_entity_id, target_entity_id, relationship_type, is_symmetric

4. **`link_orphan_to_entity(project_id, orphan_id, entity_id, reason)`**
   - Link orphan to entity
   - Returns: success, action_id, orphan_id, entity_id, data_items_moved

5. **`dismiss_suggestion(project_id, entity_id, data_id, reason)`**
   - Dismiss a suggestion
   - Returns: success, action_id, entity_id, data_id, dismissed_at

6. **`get_linking_history(project_id, entity_id, action_type, limit)`**
   - Retrieve audit trail
   - Returns: actions, count, filtered_by

#### Tool Features:

- **Comprehensive Documentation**: Each tool has detailed docstrings with examples
- **Error Handling**: Validates inputs and returns clear error messages
- **Async Execution**: All tools use asyncio.run() for Neo4j operations
- **Project Context**: All tools require project_id for proper isolation

---

### 3. Neo4j Relationships Created

#### New Relationship Types:

1. **`(DataItem)-[:LINKED_TO]->(DataItem)`**
   - Bidirectional linking of data items
   - Properties: reason, confidence, created_at, created_by, action_id

2. **`(Entity)-[:DISMISSED_SUGGESTION]->(DataItem)`**
   - Track dismissed suggestions
   - Properties: reason, dismissed_at, dismissed_by, action_id

3. **`(Person)-[:TAGGED]->(Person)` (Enhanced)**
   - Now includes properties from linking actions
   - Properties: relationship_type, confidence, reason, source, created_at, created_by, action_id

#### New Node Type:

**`LinkingAction`** - Audit trail node
- Properties: action_id, action_type, created_at, created_by, reason, details (JSON), confidence

---

### 4. Audit Trail System

Every linking action creates a comprehensive audit trail:

#### Audit Trail Components:

1. **Action ID**: Unique identifier in format `{type}_action_{timestamp}`
2. **Action Type**: link_data_items, merge_entities, create_relationship, link_orphan_to_entity, dismiss_suggestion
3. **Created By**: User or system identifier
4. **Reason**: Human-readable explanation (REQUIRED)
5. **Details**: JSON object with action-specific data
6. **Confidence**: Confidence score for the action

#### Audit Trail Query:

```python
async def get_linking_history(
    entity_id: Optional[str] = None,
    action_type: Optional[str] = None,
    limit: int = 100,
) -> List[Dict]
```

**Use Cases**:
- Review recent linking decisions
- Audit entity merge history
- Track who made what decisions
- Prepare for potential rollback operations

---

### 5. Safety Requirements Implemented

✅ **Reason Required**: All operations require non-empty reason parameter
✅ **No Automatic Linking**: All actions require explicit user intent
✅ **Irreversible Warning**: Entity merges include warning in response
✅ **Dismissed Tracking**: DISMISSED_SUGGESTION prevents suggestion reappearance
✅ **Audit Trail**: Complete accountability chain for all actions
✅ **Validation**: All inputs validated before operations
✅ **Entity Verification**: Confirms entities/data exist before operations

---

### 6. Integration Points

#### With Phase 43.1 (Data ID System):
- Uses `DataService` for DataItem operations
- Leverages DataItem IDs for linking
- Updates entity_id/orphan_id properties on DataItems

#### With Phase 43.4 (Suggestions - To Be Implemented):
- Linking actions respond to suggestions
- Dismissed suggestions tracked to filter future results
- Confidence scores from suggestions passed to linking actions

#### With Existing Systems:
- Uses `RelationshipType` enum from `api/models/relationship.py`
- Uses `ConfidenceLevel` enum for relationship confidence
- Integrates with existing Neo4j entity and relationship structures

---

## Testing

### Test Coverage: `tests/test_linking_actions.py`

Created comprehensive test suite with 20+ test cases:

#### Test Classes:

1. **TestLinkDataItems** (4 tests)
   - Success case with audit trail
   - Validation: requires reason
   - Validation: data items must exist
   - Validation: prevents self-linking

2. **TestMergeEntities** (5 tests)
   - Success case with data/relationship moves
   - Validation: requires reason
   - Validation: keep_entity_id must be valid
   - Validation: entities must exist
   - Profile merging logic verification

3. **TestCreateRelationshipFromSuggestion** (4 tests)
   - Success case with relationship properties
   - Symmetric relationships create inverse
   - Validation: requires reason
   - Validation: relationship type must be valid

4. **TestLinkOrphanToEntity** (3 tests)
   - Success case with data moves
   - Validation: requires reason
   - Validation: orphan/entity must exist

5. **TestDismissSuggestion** (3 tests)
   - Success case with dismissal tracking
   - Validation: requires reason
   - Validation: entity/data must exist

6. **TestAuditTrail** (3 tests)
   - Audit trail creation
   - History retrieval
   - Filtered history queries

7. **TestHelperMethods** (2 tests)
   - List merging with deduplication
   - List merging with dict objects

8. **TestLinkingAction** (1 test)
   - LinkingAction model serialization

#### Test Technologies:
- pytest with asyncio support
- unittest.mock for Neo4j mocking
- AsyncMock for async operations
- Comprehensive edge case coverage

---

## Usage Examples

### Example 1: Link Duplicate Data Items

```python
from api.services.linking_service import LinkingService
from api.services.neo4j_service import AsyncNeo4jService

async with AsyncNeo4jService() as neo4j:
    service = LinkingService(neo4j)

    result = await service.link_data_items(
        data_id_1="data_abc123",
        data_id_2="data_xyz789",
        reason="Same email address found in different data sources",
        confidence=0.95,
        created_by="analyst_john"
    )

    print(f"Linked data items: {result['action_id']}")
```

### Example 2: Merge Duplicate Entities

```python
result = await service.merge_entities(
    entity_id_1="ent_abc123",
    entity_id_2="ent_xyz789",
    keep_entity_id="ent_abc123",
    reason="Confirmed duplicate: same person with matching email, phone, and social media profiles",
    created_by="analyst_john"
)

print(f"Merged {result['data_items_moved']} data items")
print(f"Merged {result['relationships_moved']} relationships")
```

### Example 3: Create Relationship from Suggestion

```python
result = await service.create_relationship_from_suggestion(
    entity_id_1="ent_abc123",
    entity_id_2="ent_xyz789",
    relationship_type="WORKS_WITH",
    confidence="high",
    reason="Both listed as employees at Acme Corp on LinkedIn",
    created_by="analyst_john"
)

if result["is_symmetric"]:
    print("Created bidirectional relationship")
```

### Example 4: Link Orphan to Entity

```python
result = await service.link_orphan_to_entity(
    orphan_id="orphan_abc123",
    entity_id="ent_xyz789",
    reason="Orphan email matches entity primary email exactly",
    created_by="analyst_john"
)

print(f"Moved {result['data_items_moved']} data items from orphan to entity")
```

### Example 5: Dismiss False Suggestion

```python
result = await service.dismiss_suggestion(
    entity_id="ent_abc123",
    data_id="data_xyz789",
    reason="Same name but different person - verified via date of birth mismatch",
    created_by="analyst_john"
)

print(f"Dismissed suggestion at {result['dismissed_at']}")
```

### Example 6: MCP Tool Usage

```python
# Via MCP server
from basset_mcp.tools.linking import link_data_items

result = link_data_items(
    project_id="my_project",
    data_id_1="data_abc123",
    data_id_2="data_xyz789",
    reason="Duplicate image detected via hash matching",
    confidence=1.0
)

if result["success"]:
    print(f"Action ID: {result['action_id']}")
```

---

## Benefits

### For Human Operators:

1. **Clear Decision Making**: Reason parameter forces explicit justification
2. **Audit Trail**: Complete history of who did what and why
3. **Reversibility Awareness**: Clear warnings about irreversible operations
4. **Flexible Actions**: Multiple ways to act on suggestions (link, merge, relate, dismiss)

### For AI Agents:

1. **MCP Tool Access**: All operations available via MCP server
2. **Error Handling**: Clear error messages for invalid operations
3. **Audit Participation**: Agent actions tracked with "mcp_user" identifier
4. **Documentation**: Comprehensive tool descriptions and examples

### For Compliance:

1. **Accountability**: Every action tracked with reason and user
2. **Traceability**: Audit trail enables investigation of decisions
3. **Reversibility**: Audit data can support rollback operations
4. **Evidence**: Reasons provide justification for investigative decisions

### For System Architecture:

1. **Modularity**: Service pattern separates business logic from API/MCP
2. **Testability**: Comprehensive test coverage with mocked dependencies
3. **Extensibility**: Easy to add new linking action types
4. **Integration**: Clean integration points with Phase 43.1 and future 43.4

---

## Database Schema Changes

### New Node Labels:

```cypher
(:LinkingAction {
    action_id: String,
    action_type: String,
    created_at: DateTime,
    created_by: String,
    reason: String,
    details: String,  // JSON
    confidence: Float
})
```

### New Relationships:

```cypher
// Data item linking
(DataItem)-[:LINKED_TO {
    reason: String,
    confidence: Float,
    created_at: DateTime,
    created_by: String,
    action_id: String
}]->(DataItem)

// Suggestion dismissal
(Person)-[:DISMISSED_SUGGESTION {
    reason: String,
    dismissed_at: DateTime,
    dismissed_by: String,
    action_id: String
}]->(DataItem)
```

### Enhanced Relationships:

```cypher
// Enhanced TAGGED relationships
(Person)-[:TAGGED {
    relationship_type: String,
    confidence: String,
    reason: String,
    source: String,
    created_at: DateTime,
    created_by: String,
    action_id: String
}]->(Person)
```

### Entity Merge Markers:

```cypher
(:Person {
    merged_into: String,      // ID of entity merged into
    merged_at: DateTime,
    merge_reason: String,
    merge_action_id: String
})
```

---

## Performance Considerations

### Optimizations:

1. **Batch Operations**: Entity merge moves all data in single transaction
2. **Index Usage**: Uses entity/data ID indices for lookups
3. **Async Operations**: All Neo4j operations use async/await
4. **Lazy Loading**: Only loads data when needed

### Scalability:

1. **Transaction Scope**: Each operation is a single transaction
2. **Query Efficiency**: Uses MATCH → SET → MERGE pattern for updates
3. **Audit Storage**: Audit nodes separate from operational data
4. **History Limits**: get_linking_history has configurable limit

---

## Future Enhancements

### Phase 43.6 Possibilities:

1. **Undo Operations**: Use audit trail to reverse linking actions
2. **Bulk Operations**: Link multiple data items in single transaction
3. **Conflict Resolution**: Handle conflicting merge decisions
4. **Confidence Tracking**: Track confidence score changes over time
5. **Suggestion Feedback**: Use dismissals to improve suggestion quality

### Integration Opportunities:

1. **Browser Extension**: Trigger linking actions from browser UI
2. **Reports**: Include linking history in investigation reports
3. **Analytics**: Track most common dismissal reasons
4. **Notifications**: Alert on high-confidence suggestions

---

## Files Created

1. **`/home/devel/basset-hound/api/services/linking_service.py`** (1,100+ lines)
   - LinkingService class with 5 core operations
   - LinkingAction model for audit trail
   - Helper methods for profile merging and list deduplication

2. **`/home/devel/basset-hound/basset_mcp/tools/linking.py`** (500+ lines)
   - 6 MCP tools for linking actions
   - Comprehensive documentation and examples
   - Error handling and validation

3. **`/home/devel/basset-hound/tests/test_linking_actions.py`** (700+ lines)
   - 20+ test cases
   - 8 test classes covering all operations
   - Mock-based testing for Neo4j operations

4. **`/home/devel/basset-hound/docs/findings/PHASE43_5-LINKING-ACTIONS-2026-01-09.md`** (This document)
   - Comprehensive implementation report
   - Usage examples and integration guide

### Files Modified:

1. **`/home/devel/basset-hound/basset_mcp/tools/__init__.py`**
   - Added linking tools registration
   - Updated module documentation

---

## Conclusion

Phase 43.5 successfully implements a comprehensive linking action system with:

✅ **5 Core Operations**: Link data, merge entities, create relationships, link orphans, dismiss suggestions
✅ **Human Accountability**: Required reason parameters for all actions
✅ **Audit Trail**: Complete tracking of all linking decisions
✅ **MCP Integration**: 6 tools for AI agent access
✅ **Safety Features**: Validation, warnings, and dismissal tracking
✅ **Test Coverage**: 20+ comprehensive test cases
✅ **Documentation**: Detailed usage examples and integration guide

The system provides the foundation for Phase 43.4 (Suggestion Service) to present suggestions, and Phase 43.5 enables users to act on those suggestions with proper accountability and audit trails.

### Next Steps:

1. Implement Phase 43.4 (Suggestion Service) to generate suggestions
2. Create UI components for viewing and acting on suggestions
3. Add undo functionality using audit trail
4. Integrate with browser extension for inline suggestions

---

**Implementation Quality**: Production Ready
**Test Coverage**: Comprehensive
**Documentation**: Complete
**Integration**: Ready for Phase 43.4
