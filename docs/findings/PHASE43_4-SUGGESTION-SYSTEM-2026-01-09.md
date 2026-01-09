# Phase 43.4: Suggestion System Implementation

**Date**: 2026-01-09
**Phase**: 43.4 - Smart Suggestions & Data Matching System
**Status**: ✅ Complete

## Overview

Implemented the on-demand suggestion computation system that shows "Suggested Tags" on entity profiles. This system helps human operators identify potential relationships between entities and link orphan data based on matching data items.

## Components Implemented

### 1. Core Service: `api/services/suggestion_service.py`

**Key Features**:
- **On-demand computation only**: No automatic suggestions or auto-linking
- **Confidence-based ranking**: HIGH (0.9-1.0), MEDIUM (0.7-0.89), LOW (0.5-0.69)
- **Entity suggestions**: Find matching DataItems from other entities
- **Orphan suggestions**: Find entities that match orphan data
- **Dismissed suggestions**: Track manually dismissed suggestions

**Main Classes**:

1. **SuggestionMatch**: Represents a single match
   - data_id, data_type, data_value
   - match_type (exact_hash, exact_string, partial_string)
   - confidence_score (0.5-1.0)
   - matched_entity_id, matched_entity_name
   - matched_orphan_id (for orphan matches)

2. **ConfidenceGroup**: Groups matches by confidence level
   - confidence: HIGH, MEDIUM, or LOW
   - matches: List of SuggestionMatch objects

3. **SuggestionService**: Main service class
   - `get_entity_suggestions()`: Get suggestions for an entity
   - `get_orphan_suggestions()`: Get entity suggestions for orphan data
   - `dismiss_suggestion()`: Mark a suggestion as dismissed
   - `get_dismissed_suggestions_list()`: Get all dismissed suggestions

**Integration Points**:
- Uses `MatchingEngine` from Phase 43.3 for finding matches
- Uses `DataService` from Phase 43.1 for data retrieval
- Uses `Neo4jService` for database operations

### 2. MCP Tools: `basset_mcp/tools/suggestions.py`

**Tools Implemented**:

1. **get_entity_suggestions**
   - Get on-demand suggestions for an entity
   - Parameters: project_id, entity_id, include_partial, min_confidence
   - Returns: Suggestions grouped by confidence level
   - Use case: Finding related entities based on shared data

2. **get_orphan_suggestions**
   - Get entity suggestions for orphan data
   - Parameters: project_id, orphan_id, include_partial, min_confidence
   - Returns: Entity suggestions for linking orphan
   - Use case: Linking orphan data to existing entities

3. **dismiss_suggestion**
   - Mark a suggestion as dismissed
   - Parameters: project_id, entity_id, data_id
   - Creates DISMISSED_SUGGESTION relationship
   - Use case: Filtering out irrelevant suggestions
   - **Note**: Enhanced version in Phase 43.5 (linking.py) includes reason tracking

4. **get_dismissed_suggestions**
   - List all dismissed suggestions for an entity
   - Parameters: project_id, entity_id
   - Returns: List of dismissed suggestions with timestamps
   - Use case: Reviewing dismissed suggestions

5. **undismiss_suggestion**
   - Remove a dismissed suggestion
   - Parameters: project_id, entity_id, data_id
   - Removes DISMISSED_SUGGESTION relationship
   - Use case: Re-enabling a previously dismissed suggestion

### 3. Comprehensive Tests: `tests/test_suggestion_system.py`

**Test Coverage**:

1. **Unit Tests**:
   - SuggestionMatch creation and serialization
   - ConfidenceGroup creation and serialization
   - Confidence classification (HIGH/MEDIUM/LOW)
   - Confidence grouping logic
   - Entity name retrieval
   - Dismissed suggestions tracking

2. **Integration Tests**:
   - Entity suggestion generation
   - Orphan suggestion generation
   - Self-match filtering
   - Dismissed suggestion filtering
   - End-to-end confidence grouping

3. **Performance Tests**:
   - Handles 100+ entities in <1s
   - Efficient matching and grouping
   - Memory-efficient processing

4. **Edge Cases**:
   - Empty data handling
   - Non-existent entities/orphans
   - Invalid IDs
   - Single confidence level grouping

## Confidence Scoring System

### Confidence Levels

1. **HIGH (0.9-1.0)**:
   - Exact hash matches (1.0)
   - Exact string matches after normalization (0.95)
   - Very high similarity fuzzy matches (>0.9)
   - **Use case**: Strong evidence of relationship

2. **MEDIUM (0.7-0.89)**:
   - High similarity fuzzy matches
   - Name variations with similar spelling
   - Address variations with common tokens
   - **Use case**: Probable relationship requiring verification

3. **LOW (0.5-0.69)**:
   - Lower similarity matches
   - Partial address matches
   - Similar but not identical names
   - **Use case**: Possible relationship worth investigating

### Confidence Classification Logic

```python
def _classify_confidence(score: float) -> ConfidenceLevel:
    if score >= 0.9:
        return ConfidenceLevel.HIGH
    elif score >= 0.7:
        return ConfidenceLevel.MEDIUM
    else:
        return ConfidenceLevel.LOW
```

## Result Format

### Entity Suggestions

```json
{
    "entity_id": "ent_abc123",
    "suggestions": [
        {
            "confidence": "HIGH",
            "matches": [
                {
                    "data_id": "data_xyz789",
                    "data_type": "email",
                    "data_value": "test@example.com",
                    "match_type": "exact_hash",
                    "confidence_score": 1.0,
                    "matched_entity_id": "ent_def456",
                    "matched_entity_name": "John Doe"
                }
            ]
        },
        {
            "confidence": "MEDIUM",
            "matches": [...]
        },
        {
            "confidence": "LOW",
            "matches": [...]
        }
    ],
    "dismissed_count": 3
}
```

### Orphan Suggestions

```json
{
    "orphan_id": "orphan_xyz789",
    "suggestions": [
        {
            "confidence": "HIGH",
            "matches": [
                {
                    "data_id": "data_abc123",
                    "data_type": "email",
                    "data_value": "test@example.com",
                    "match_type": "exact_string",
                    "confidence_score": 0.95,
                    "matched_entity_id": "ent_def456",
                    "matched_entity_name": "John Doe"
                }
            ]
        }
    ]
}
```

## Key Design Principles

### 1. On-Demand Only
- No automatic suggestion computation
- No background processing
- Suggestions computed when explicitly requested
- Human operator controls when to see suggestions

### 2. Read-Only Suggestions
- Suggestions do not modify data
- No automatic linking
- Human operator must explicitly act on suggestions
- Dismissed suggestions tracked separately

### 3. Performance-Conscious
- Efficient matching using MatchingEngine
- Deduplication of repeated matches
- Grouped results for easy consumption
- Handles 100+ entities in <1s

### 4. Human-in-the-Loop
- Suggestions can be dismissed
- Dismissed suggestions not shown again
- Can review dismissed suggestions
- Can undismiss if needed

## Use Cases

### 1. Finding Related Entities
**Scenario**: Entity "John Smith" has email "john@example.com"
**Suggestion**: Entity "J. Smith" also has "john@example.com"
**Action**: Human operator reviews and decides if they are the same person

### 2. Detecting Potential Duplicates
**Scenario**: Two entities share multiple data items
**Suggestion**: HIGH confidence match on email, phone, address
**Action**: Human operator merges or tags as related

### 3. Linking Orphan Data
**Scenario**: Orphan email "test@example.com" exists
**Suggestion**: Entity "Test User" has matching email
**Action**: Human operator links orphan to entity

### 4. Address Variations
**Scenario**: Entity has "123 Main Street, Apt 4B"
**Suggestion**: MEDIUM confidence match with "123 Main St #4B"
**Action**: Human operator verifies it's the same address

### 5. Name Variations
**Scenario**: Entity "José García"
**Suggestion**: LOW confidence match with "Jose Garcia"
**Action**: Human operator verifies diacritics difference

## Integration with Existing Systems

### Phase 43.1: Data ID System
- Uses DataItem model with unique IDs
- Retrieves data items via DataService
- Tracks entity_id and orphan_id relationships

### Phase 43.3: Matching Engine
- Uses MatchingEngine for finding matches
- Leverages exact hash, exact string, and partial matching
- Benefits from confidence scoring system

### Integration with Phase 43.5: Linking Actions
- ✅ Phase 43.5 has been implemented in `basset_mcp/tools/linking.py`
- ✅ Provides `dismiss_suggestion` with reason tracking (supersedes basic dismiss in this phase)
- ✅ Provides `link_entities`, `merge_entities`, and `link_orphan` actions
- Suggestions from this phase inform the linking actions
- Human operators can act on suggestions through Phase 43.5 tools

## Neo4j Graph Structure

### New Relationships

1. **DISMISSED_SUGGESTION**
   ```cypher
   (Person)-[:DISMISSED_SUGGESTION {dismissed_at: datetime()}]->(DataItem)
   ```
   - Tracks manually dismissed suggestions
   - Prevents re-showing dismissed matches
   - Allows reviewing dismissed history

### Queries

1. **Get Dismissed Suggestions**:
   ```cypher
   MATCH (p:Person {id: $entity_id})-[:DISMISSED_SUGGESTION]->(d:DataItem)
   RETURN d.id as data_id
   ```

2. **Dismiss Suggestion**:
   ```cypher
   MATCH (p:Person {id: $entity_id})
   MATCH (d:DataItem {id: $data_id})
   MERGE (p)-[r:DISMISSED_SUGGESTION {dismissed_at: datetime()}]->(d)
   ```

3. **Undismiss Suggestion**:
   ```cypher
   MATCH (p:Person {id: $entity_id})-[r:DISMISSED_SUGGESTION]->(d:DataItem {id: $data_id})
   DELETE r
   ```

## Performance Characteristics

### Benchmarks

1. **Entity Suggestions**:
   - 100 matches processed in <1s
   - Efficient deduplication
   - Minimal memory overhead

2. **Orphan Suggestions**:
   - Fast entity lookup
   - Filtered by entity type
   - No orphan-to-orphan suggestions

3. **Confidence Grouping**:
   - O(n) complexity
   - In-memory grouping
   - Sorted by confidence level

### Optimization Strategies

1. **Deduplication**:
   - Track seen data_ids to avoid duplicates
   - Skip self-matches early
   - Filter dismissed suggestions upfront

2. **Lazy Loading**:
   - Entity names fetched only when needed
   - Batch queries where possible
   - Async operations for parallelism

3. **Result Limiting**:
   - MatchingEngine limits to 100 results
   - Confidence threshold filters results
   - Grouped results reduce payload size

## Testing Strategy

### Unit Tests
- ✅ SuggestionMatch creation and serialization
- ✅ ConfidenceGroup creation and serialization
- ✅ Confidence classification logic
- ✅ Confidence grouping algorithm
- ✅ Entity name retrieval
- ✅ Dismissed suggestions tracking

### Integration Tests
- ✅ Entity suggestion generation end-to-end
- ✅ Orphan suggestion generation end-to-end
- ✅ Self-match filtering
- ✅ Dismissed suggestion filtering
- ✅ Confidence grouping with real data

### Performance Tests
- ✅ 100+ entity processing in <1s
- ✅ Memory efficiency validation
- ✅ Query performance benchmarks

### Edge Case Tests
- ✅ Empty data handling
- ✅ Non-existent entities/orphans
- ✅ Invalid ID handling
- ✅ Single confidence level results

## Example Workflows

### Workflow 1: Review Entity Suggestions

```python
# Get suggestions for an entity
suggestions = get_entity_suggestions(
    project_id="proj_abc",
    entity_id="ent_123",
    include_partial=True,
    min_confidence=0.5
)

# Review HIGH confidence matches
for match in suggestions["suggestions"][0]["matches"]:
    print(f"Match: {match['data_value']}")
    print(f"Entity: {match['matched_entity_name']}")
    print(f"Confidence: {match['confidence_score']}")

# Dismiss irrelevant suggestion
dismiss_suggestion(
    project_id="proj_abc",
    entity_id="ent_123",
    data_id="data_xyz"
)
```

### Workflow 2: Link Orphan Data

```python
# Get suggestions for orphan
suggestions = get_orphan_suggestions(
    project_id="proj_abc",
    orphan_id="orphan_789",
    include_partial=False,  # Only exact matches
    min_confidence=0.9
)

# Review HIGH confidence entity matches
for match in suggestions["suggestions"][0]["matches"]:
    print(f"Entity: {match['matched_entity_name']}")
    print(f"Match type: {match['match_type']}")

# Human operator decides to link (Phase 43.5)
```

### Workflow 3: Audit Dismissed Suggestions

```python
# Get dismissed suggestions
dismissed = get_dismissed_suggestions(
    project_id="proj_abc",
    entity_id="ent_123"
)

# Review dismissed items
for item in dismissed["dismissed_suggestions"]:
    print(f"Data: {item['data_value']}")
    print(f"Dismissed: {item['dismissed_at']}")

# Undismiss if needed
undismiss_suggestion(
    project_id="proj_abc",
    entity_id="ent_123",
    data_id="data_xyz"
)
```

## Security Considerations

1. **No Automatic Actions**:
   - Suggestions never modify data
   - Human operator must explicitly act
   - Prevents accidental data merging

2. **Project Isolation**:
   - Suggestions scoped to project
   - No cross-project suggestions
   - Project ID validated

3. **Permission Model**:
   - Read-only for suggestions
   - Dismiss action requires entity access
   - Linking requires explicit permission (Phase 43.5)

## Future Enhancements

### Phase 43.5: Linking Actions
- Act on suggestions to link entities
- Merge duplicate entities
- Link orphan data to entities
- Create relationships based on suggestions

### Potential Improvements
1. **Suggestion Ranking**:
   - Machine learning-based scoring
   - Historical acceptance rate
   - Context-aware relevance

2. **Batch Suggestions**:
   - Get suggestions for multiple entities
   - Parallel processing
   - Cached results

3. **Suggestion Explanations**:
   - Why this suggestion was made
   - Which data items matched
   - Similarity breakdown

4. **Negative Suggestions**:
   - Track "not related" decisions
   - Learn from dismissals
   - Improve future suggestions

## Lessons Learned

### What Worked Well
1. **Confidence Grouping**: Makes it easy for human operators to prioritize HIGH confidence matches
2. **Dismissed Tracking**: Prevents suggestion fatigue by hiding irrelevant matches
3. **On-Demand Only**: Keeps system simple and performant
4. **Integration**: Leverages existing MatchingEngine and DataService

### Challenges
1. **Entity Name Lookup**: Requires additional query for each match
2. **Deduplication**: Need to track seen IDs to avoid duplicate suggestions
3. **Orphan vs Entity**: Different data structures require separate logic

### Solutions
1. **Async Operations**: Use async/await for parallel queries
2. **In-Memory Tracking**: Use sets for efficient deduplication
3. **Unified Interface**: SuggestionMatch works for both entities and orphans

## Conclusion

Phase 43.4 successfully implements the on-demand suggestion computation system that empowers human operators to discover relationships between entities and link orphan data. The system is:

- ✅ **Read-only**: No automatic actions
- ✅ **Performance-conscious**: Handles 100+ entities in <1s
- ✅ **Human-in-the-loop**: Dismissed suggestions tracked
- ✅ **Confidence-based**: HIGH/MEDIUM/LOW grouping
- ✅ **Well-tested**: Comprehensive unit and integration tests
- ✅ **Well-integrated**: Uses MatchingEngine and DataService

The suggestion system provides the intelligence layer for Phase 43.5 (Linking Actions) while maintaining the principle of human operator control over all data relationships.

## Files Created

1. **Service Layer**:
   - `/home/devel/basset-hound/api/services/suggestion_service.py` (575 lines)

2. **MCP Tools**:
   - `/home/devel/basset-hound/basset_mcp/tools/suggestions.py` (341 lines)

3. **Tests**:
   - `/home/devel/basset-hound/tests/test_suggestion_system.py` (752 lines)

4. **Documentation**:
   - `/home/devel/basset-hound/docs/findings/PHASE43_4-SUGGESTION-SYSTEM-2026-01-09.md` (this file)

## Next Steps

1. ~~**Phase 43.5**: Implement linking actions to act on suggestions~~ ✅ **Complete** (see `basset_mcp/tools/linking.py`)
2. **UI Integration**: Add "Suggested Tags" section to entity profiles
3. **Performance Optimization**: Cache entity names and suggestions
4. **User Testing**: Gather feedback from human operators
5. **Tool Consolidation**: Consider deprecating basic `dismiss_suggestion` in favor of Phase 43.5 version
