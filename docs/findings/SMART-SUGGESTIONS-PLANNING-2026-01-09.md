# Smart Suggestions & Data Matching System - Planning Document

**Date:** 2026-01-09
**Phase:** 43 (Smart Suggestions)
**Status:** Planning

---

## Executive Summary

This document outlines a new intelligent suggestion system for basset-hound that helps human operators identify potential matches, duplicates, and related data across entities and orphan data.

**Core Principle**: Suggest possible matches based on data analysis (hashes, exact matches, partial matches), but **always require human verification** before linking.

---

## 1. Feature Overview

### Problem Statement

Currently, human operators must manually search for related entities. This new system will:
- **Suggest** entities that might be related based on shared data
- **Detect** potential duplicates using hash-based matching
- **Highlight** orphan data that matches entity data
- **Assist** with deduplication while preventing false positives

### Key Insight

> "Some entities may share data in common but not be the same entity. Example: Two people at '123 Main St' but in different states → suggest but don't auto-link."

---

## 2. Use Cases

### Use Case 1: Image Hash Matching

**Scenario**: Investigator uploads profile photo for Entity A.

**System Behavior**:
1. Compute SHA-256 hash of image
2. Check if hash exists elsewhere in database
3. If match found → Show suggestion: "This image matches Entity B (ID: ent_456)"
4. Human operator reviews and decides:
   - "Link as same person" → Merge entities
   - "Same image, different people" → Ignore suggestion
   - "Evidence of connection" → Create relationship (KNOWS, ASSOCIATE_OF)

### Use Case 2: Shared Email Address

**Scenario**: Entity A has email "support@company.com", Entity B also has "support@company.com"

**System Behavior**:
1. Detect exact email match
2. Show suggestion: "Email 'support@company.com' also found in Entity B"
3. Human operator decides:
   - "Same person" → Merge
   - "Shared corporate email" → Ignore
   - "Works for same company" → Create WORKS_FOR relationship

### Use Case 3: Partial Address Match

**Scenario**:
- Entity A: "123 Main St, Seattle, WA"
- Entity B: "123 Main St, Portland, OR"

**System Behavior**:
1. Detect partial match on street address
2. Show suggestion: "Address '123 Main St' matches Entity B (different city)"
3. Confidence: LOW (0.3) - different cities
4. Human operator: "Not the same person" → Dismiss suggestion

### Use Case 4: Orphan Data Matching

**Scenario**: Orphan email "john@example.com" exists. Entity A is created with same email.

**System Behavior**:
1. Detect exact match between entity data and orphan data
2. Show suggestion: "Orphan data (ID: orphan_789) has matching email"
3. Human operator:
   - "Link orphan to this entity" → Convert orphan to entity data
   - "Same value, different context" → Keep separate

### Use Case 5: Document Hash Matching

**Scenario**: Evidence document uploaded for Investigation A also appears in Investigation B.

**System Behavior**:
1. Compute file hash (SHA-256)
2. Detect match in different investigation
3. Show suggestion: "Document hash matches evidence in Investigation B"
4. Human operator verifies: "Same leaked document used by both targets"

---

## 3. Data Types for Matching

### 3.1 Hash-Based Matching (Exact)

**File/Image Hashing**:
- ✅ Images (JPEG, PNG, GIF, WebP)
- ✅ Documents (PDF, DOCX, TXT)
- ✅ Evidence files (screenshots, archives)
- ✅ Use SHA-256 for all files

**Confidence**: 1.0 (exact match)

### 3.2 Exact String Matching

**Identifiers**:
- ✅ Email addresses
- ✅ Phone numbers (normalized to E.164)
- ✅ Cryptocurrency addresses
- ✅ URLs (normalized)
- ✅ Social media handles
- ✅ IP addresses

**Confidence**: 0.95 (exact match, case-insensitive)

### 3.3 Partial/Fuzzy Matching

**Names**:
- ✅ Full name matches: "John Doe" = "John Doe"
- ✅ Partial name matches: "John Doe" ≈ "John D." (0.7 confidence)
- ✅ Name variations: "Robert" ≈ "Bob" (nickname detection)

**Addresses**:
- ✅ Exact address: "123 Main St, Seattle, WA 98101"
- ✅ Partial match: "123 Main St" (different cities → 0.3 confidence)
- ✅ Normalized comparison (remove punctuation, case-insensitive)

**Confidence**: 0.3-0.9 (depending on match quality)

---

## 4. Architecture Design

### 4.1 Data ID System

**Every piece of data gets an ID**:

```python
class DataItem:
    """Base class for all data items in basset-hound."""
    id: str                    # data_abc123
    type: DataType             # image, document, email, phone, etc.
    value: Any                 # Actual data or file path
    hash: Optional[str]        # SHA-256 hash (for files)
    normalized_value: str      # Normalized for comparison
    entity_id: Optional[str]   # If linked to entity
    created_at: datetime
    metadata: dict

# Examples:
DataItem(id="data_001", type="email", value="john@example.com", entity_id="ent_123")
DataItem(id="data_002", type="image", value="/path/to/image.jpg", hash="abc123...", entity_id="ent_456")
DataItem(id="data_003", type="phone", value="+14155551234", entity_id="ent_123")
```

### 4.2 Suggestion System

**Suggestions are NOT stored permanently**:
- Computed on-demand when viewing entity profile
- Cached for performance (5-minute TTL)
- Human operator can dismiss suggestions (stored in user preferences)

```python
class Suggestion:
    """A suggested match between two data items."""
    id: str                      # suggestion_xyz
    source_data_id: str          # data_001
    target_data_id: str          # data_002
    match_type: MatchType        # exact_hash, exact_string, partial_string
    confidence: float            # 0.0 - 1.0
    reason: str                  # "Email address matches"
    created_at: datetime
    dismissed_by: Optional[str]  # User ID if dismissed

    # Context
    source_entity_id: Optional[str]
    target_entity_id: Optional[str]
    source_orphan_id: Optional[str]
    target_orphan_id: Optional[str]
```

### 4.3 Neo4j Schema

**New Node Types**:
```cypher
(:DataItem {
    id: string,
    type: string,              // email, phone, image, document, etc.
    value: string,             // Actual value or file path
    hash: string,              // SHA-256 (for files)
    normalized_value: string,  // For comparison
    created_at: datetime
})

(:DataItem)-[:BELONGS_TO]->(:Entity)
(:DataItem)-[:BELONGS_TO]->(:OrphanIdentifier)
(:DataItem)-[:MATCHES {confidence: float, match_type: string}]->(:DataItem)  // Suggested match
```

**Example Graph**:
```
(:Entity {id: "ent_123", name: "John Doe"})
  ↓ [:HAS_DATA]
(:DataItem {id: "data_001", type: "email", value: "john@example.com", hash: null})
  ↓ [:MATCHES {confidence: 1.0, match_type: "exact_string"}]
(:DataItem {id: "data_002", type: "email", value: "john@example.com", hash: null})
  ↓ [:BELONGS_TO]
(:OrphanIdentifier {id: "orphan_789"})
```

### 4.4 Matching Engine

```python
class MatchingEngine:
    """Find matches between data items."""

    async def find_matches(self, data_item: DataItem) -> List[Suggestion]:
        """Find all potential matches for a data item."""
        suggestions = []

        # 1. Hash-based matching (exact)
        if data_item.hash:
            hash_matches = await self.find_hash_matches(data_item.hash)
            for match in hash_matches:
                suggestions.append(Suggestion(
                    source_data_id=data_item.id,
                    target_data_id=match.id,
                    match_type=MatchType.EXACT_HASH,
                    confidence=1.0,
                    reason=f"{data_item.type.capitalize()} hash matches"
                ))

        # 2. Exact string matching
        if data_item.type in ["email", "phone", "crypto_address", "url"]:
            exact_matches = await self.find_exact_matches(
                data_item.normalized_value,
                data_item.type
            )
            for match in exact_matches:
                suggestions.append(Suggestion(
                    source_data_id=data_item.id,
                    target_data_id=match.id,
                    match_type=MatchType.EXACT_STRING,
                    confidence=0.95,
                    reason=f"{data_item.type.capitalize()} matches exactly"
                ))

        # 3. Partial matching (names, addresses)
        if data_item.type in ["name", "address"]:
            partial_matches = await self.find_partial_matches(
                data_item.normalized_value,
                data_item.type
            )
            for match, similarity in partial_matches:
                if similarity >= 0.7:  # Threshold
                    suggestions.append(Suggestion(
                        source_data_id=data_item.id,
                        target_data_id=match.id,
                        match_type=MatchType.PARTIAL_STRING,
                        confidence=similarity,
                        reason=f"{data_item.type.capitalize()} partially matches ({similarity:.0%})"
                    ))

        return suggestions
```

---

## 5. MCP Tools (New)

### Phase 43: Smart Suggestions (8 new tools)

| Tool | Description |
|------|-------------|
| `compute_file_hash` | Compute SHA-256 hash for uploaded file |
| `find_data_matches` | Find all matches for a data item |
| `get_entity_suggestions` | Get all suggestions for an entity profile |
| `dismiss_suggestion` | Dismiss a suggestion (user says "not related") |
| `accept_suggestion_merge` | Accept suggestion and merge entities |
| `accept_suggestion_link` | Accept suggestion and create relationship |
| `link_orphan_to_entity` | Link orphan data to entity based on suggestion |
| `list_dismissed_suggestions` | Show user's dismissed suggestions |

**Total Tool Count**: 100 → 108 tools (+8)

---

## 6. UI/UX Flow

### Entity Profile Page

```
┌─────────────────────────────────────────────────────┐
│ Entity: John Doe (ent_123)                         │
├─────────────────────────────────────────────────────┤
│ Email: john@example.com                            │
│ Phone: +14155551234                                │
│ Address: 123 Main St, Seattle, WA                  │
│ Profile Photo: [image.jpg] ✓ SHA-256: abc123...   │
├─────────────────────────────────────────────────────┤
│ Relationships:                                      │
│ - KNOWS: Jane Doe (ent_456)                        │
├─────────────────────────────────────────────────────┤
│ 💡 Suggested Tags (3)                              │
│                                                     │
│ 1. High Confidence (95%)                           │
│    Email "john@example.com" matches:               │
│    - Entity: John D. (ent_789) [View] [Link] [Dismiss] │
│    - Orphan: orphan_456 [View] [Link] [Dismiss]   │
│                                                     │
│ 2. Medium Confidence (70%)                         │
│    Name "John Doe" similar to:                     │
│    - Entity: Jon Doe (ent_234) [View] [Link] [Dismiss] │
│                                                     │
│ 3. Low Confidence (30%)                            │
│    Address "123 Main St" matches:                  │
│    - Entity: Alice Smith (ent_999) - Portland, OR │
│      [View] [Link] [Dismiss]                       │
│                                                     │
│ [Show Dismissed Suggestions (2)]                   │
└─────────────────────────────────────────────────────┘
```

### Actions:

**[View]**: Opens entity ent_789 in new tab for comparison

**[Link]**: Shows dialog:
```
How should these be linked?
○ Merge entities (same person)
○ Create relationship: [KNOWS ▼]
○ Link orphan data to this entity
[Cancel] [Confirm]
```

**[Dismiss]**: Hides suggestion permanently for this user

---

## 7. Implementation Phases

### Phase 43.1: Data ID System (Week 1)

**Tasks**:
- [ ] Create `DataItem` model
- [ ] Create `(:DataItem)` node type in Neo4j
- [ ] Migrate existing entity attributes to DataItem nodes
- [ ] Generate IDs for all data: `data_abc123`
- [ ] Add `[:HAS_DATA]` relationships

**Deliverables**:
- Entity attributes become DataItem nodes
- Every piece of data has a unique ID
- Migration script for existing data

### Phase 43.2: Hash Computation (Week 2)

**Tasks**:
- [ ] Create `FileHashService` class
- [ ] Compute SHA-256 for uploaded images/documents
- [ ] Store hashes in DataItem.hash field
- [ ] Create `compute_file_hash` MCP tool
- [ ] Add hash verification for evidence integrity

**Deliverables**:
- All uploaded files have SHA-256 hashes
- Hash-based duplicate detection

### Phase 43.3: Matching Engine (Week 2-3)

**Tasks**:
- [ ] Create `MatchingEngine` class
- [ ] Implement exact hash matching
- [ ] Implement exact string matching (email, phone, crypto)
- [ ] Implement partial string matching (names, addresses)
- [ ] Create `find_data_matches` MCP tool
- [ ] Performance optimization (indexes on normalized_value, hash)

**Deliverables**:
- Matching engine finds duplicates/similar data
- Confidence scoring (0.0 - 1.0)

### Phase 43.4: Suggestion System (Week 3-4)

**Tasks**:
- [ ] Create `Suggestion` model
- [ ] Create `get_entity_suggestions` MCP tool
- [ ] Implement suggestion caching (5-minute TTL)
- [ ] Create `dismiss_suggestion` MCP tool
- [ ] Store dismissed suggestions in user preferences
- [ ] Create `list_dismissed_suggestions` MCP tool

**Deliverables**:
- Entity profiles show suggested tags
- Users can dismiss irrelevant suggestions
- Suggestions computed on-demand

### Phase 43.5: Linking Actions (Week 4)

**Tasks**:
- [ ] Create `accept_suggestion_merge` MCP tool (merge entities)
- [ ] Create `accept_suggestion_link` MCP tool (create relationship)
- [ ] Create `link_orphan_to_entity` MCP tool
- [ ] Add audit logging for all linking actions
- [ ] Prevent accidental merges (confirmation required)

**Deliverables**:
- Human operators can act on suggestions
- All actions are reversible (audit trail)

### Phase 43.6: Testing & Documentation (Week 5)

**Tasks**:
- [ ] Unit tests for MatchingEngine
- [ ] Integration tests for suggestion flow
- [ ] Performance tests (10,000+ entities)
- [ ] Documentation for new MCP tools
- [ ] Update SCOPE.md and ROADMAP.md

**Deliverables**:
- >90% test coverage
- Complete documentation
- Performance benchmarks

---

## 8. Example Scenarios

### Scenario 1: Image Upload

```python
# User uploads profile photo for Entity A
image_path = "/uploads/profile_photo.jpg"

# 1. Compute hash
hash_service = FileHashService()
sha256 = hash_service.compute_hash(image_path)  # "abc123def456..."

# 2. Create DataItem
data_item = DataItem(
    id="data_001",
    type="image",
    value=image_path,
    hash=sha256,
    entity_id="ent_123"
)
await data_service.create_data_item(data_item)

# 3. Find matches
matching_engine = MatchingEngine()
suggestions = await matching_engine.find_matches(data_item)

# Results:
# Suggestion(
#     source_data_id="data_001",
#     target_data_id="data_456",  # Entity B's profile photo
#     match_type=MatchType.EXACT_HASH,
#     confidence=1.0,
#     reason="Image hash matches"
# )
```

### Scenario 2: Email Match

```python
# Entity A has email "john@example.com"
data_item = DataItem(
    id="data_002",
    type="email",
    value="john@example.com",
    normalized_value="john@example.com",
    entity_id="ent_123"
)

# Find matches
suggestions = await matching_engine.find_matches(data_item)

# Results:
# - Suggestion for Entity B (has same email)
# - Suggestion for Orphan orphan_789 (has same email)
```

### Scenario 3: Partial Address Match

```python
# Entity A: "123 Main St, Seattle, WA"
# Entity B: "123 Main St, Portland, OR"

data_item_a = DataItem(
    id="data_003",
    type="address",
    value="123 Main St, Seattle, WA",
    normalized_value="123mainst",  # Normalized for comparison
    entity_id="ent_123"
)

suggestions = await matching_engine.find_matches(data_item_a)

# Results:
# Suggestion(
#     target_data_id="data_456",  # Entity B's address
#     match_type=MatchType.PARTIAL_STRING,
#     confidence=0.3,  # LOW - different cities
#     reason="Address partially matches (different city)"
# )
```

---

## 9. Performance Considerations

### Indexes Required

```cypher
// Neo4j indexes for fast matching
CREATE INDEX data_hash FOR (d:DataItem) ON (d.hash);
CREATE INDEX data_normalized FOR (d:DataItem) ON (d.normalized_value);
CREATE INDEX data_type FOR (d:DataItem) ON (d.type);
CREATE CONSTRAINT data_id FOR (d:DataItem) REQUIRE d.id IS UNIQUE;
```

### Caching Strategy

- **Suggestion Cache**: 5-minute TTL per entity
- **Hash Lookup**: Permanent (hashes don't change)
- **Dismissed Suggestions**: Permanent (user preference)

### Query Optimization

- Limit partial matching to threshold >= 0.7
- Batch process suggestions (10 entities at a time)
- Async/await throughout

---

## 10. Success Criteria

Phase 43 is successful if:

1. ✅ Every piece of data has a unique ID (data_xxx)
2. ✅ All uploaded files have SHA-256 hashes
3. ✅ Matching engine finds exact hash matches (1.0 confidence)
4. ✅ Matching engine finds exact string matches (0.95 confidence)
5. ✅ Matching engine finds partial name/address matches (0.3-0.9 confidence)
6. ✅ Entity profiles show suggested tags
7. ✅ Human operators can view, link, or dismiss suggestions
8. ✅ Dismissed suggestions are hidden
9. ✅ All linking actions are logged (audit trail)
10. ✅ Performance: <500ms to compute suggestions for entity with 100 data items

---

## 11. Future Enhancements (Backlog)

### Advanced Matching
- [ ] Fuzzy string matching (Levenshtein distance)
- [ ] Nickname detection ("Robert" → "Bob")
- [ ] Company name variations ("Inc" vs "Incorporated")
- [ ] Date range overlap (employment dates)

### Machine Learning
- [ ] Learn from user's accept/dismiss patterns
- [ ] Adjust confidence scores based on user feedback
- [ ] Anomaly detection (unusual patterns)

### Bulk Operations
- [ ] Bulk dismiss all low-confidence suggestions
- [ ] Bulk merge obvious duplicates (with confirmation)
- [ ] Deduplication wizard

---

## 12. Integration with Existing Features

### Auto-Linking (Phase 40)
- Auto-linking creates suggestions, not automatic links
- User confirms all links

### Orphan Data (Phase 40)
- Orphan data that matches entity data → suggestion
- User decides to link or keep separate

### Verification (basset-verify)
- Verified identifiers have higher confidence in matching
- Unverified data can still generate suggestions

---

## 13. User Workflow

```
1. Investigator creates Entity A with email "john@example.com"
   └─ System computes suggestions

2. Entity profile shows:
   "💡 Email matches Entity B (ent_456) - Confidence: 95%"

3. Investigator clicks [View]
   └─ Opens Entity B in new tab

4. Investigator compares profiles:
   - Entity A: John Doe, Seattle, WA, Software Engineer
   - Entity B: John Doe, Portland, OR, Graphic Designer

5. Investigator decision:
   - Different people (same name, different cities)
   - Clicks [Dismiss]

6. Suggestion is hidden permanently for this user

7. Later, Entity C has same email "john@example.com"
   └─ System shows suggestion again (new context)

8. Investigator reviews Entity C:
   - Same person as Entity A (same email, same employer)
   - Clicks [Link] → "Merge entities"

9. Entities A and C are merged with audit log
```

---

## 14. Summary

This smart suggestion system:

✅ **Helps** human operators find related data
✅ **Suggests** potential matches based on hashes and values
✅ **Requires** human verification (no auto-linking)
✅ **Prevents** false positives (low confidence suggestions can be dismissed)
✅ **Assists** with deduplication without forcing it
✅ **Tracks** all decisions (audit trail)

**Status**: Ready for implementation in Phase 43

**Next Steps**:
1. Update SCOPE.md with data matching features
2. Add Phase 43 to ROADMAP.md
3. Begin Phase 43.1 (Data ID System)
