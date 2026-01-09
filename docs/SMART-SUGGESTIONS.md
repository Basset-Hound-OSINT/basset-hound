# Smart Suggestions User Guide

**Phase 43: Smart Suggestions & Data Matching System**

## Overview

Smart Suggestions is an intelligent data matching system that helps you discover relationships between entities and deduplicate information in your OSINT investigations. The system automatically suggests when:

- Two entities share the same email, phone, or other identifiers
- Orphan data matches existing entities
- The same file appears in multiple locations
- Similar addresses, names, or usernames might indicate related entities

## Key Features

### 1. Automatic Match Detection

The system continuously analyzes your data and identifies potential matches using three strategies:

- **Exact Hash Matching** (100% confidence): Identical files, images, documents
- **Exact String Matching** (95% confidence): Identical emails, phones, crypto addresses
- **Partial Matching** (50-90% confidence): Similar names, addresses, usernames

### 2. Confidence Scoring

Each suggestion includes a confidence score to help you prioritize:

| Confidence | Range | Description | Action |
|------------|-------|-------------|--------|
| **HIGH** | 0.9-1.0 | Almost certainly the same | Review and link |
| **MEDIUM** | 0.7-0.89 | Likely related | Investigate |
| **LOW** | 0.5-0.69 | Possibly related | Consider reviewing |

### 3. Smart Deduplication

When you find duplicate entities:

1. View suggestions showing matching data
2. Review the confidence scores
3. Link or merge entities
4. All data moves automatically to the correct entity
5. No information is lost

### 4. Orphan Data Linking

Orphan data (identifiers without an entity) automatically suggests potential matches:

- Email in orphan data → Suggests entities with same email
- Phone number → Suggests entities with that phone
- File hash → Suggests entities with same file

## Quick Start

### Step 1: Enable Smart Suggestions

Smart Suggestions work automatically in the background. No configuration needed!

### Step 2: View Suggestions

On any entity profile page, scroll to the **"Suggested Matches"** section to see:

```
Suggested Matches (3)

HIGH CONFIDENCE (95%)
┌─────────────────────────────────────────────────────┐
│ Person: John Smith (entity-456)                     │
│ Match: Email "john.doe@example.com"                 │
│ Reason: Exact match                                 │
│ [Link Entities] [Dismiss]                           │
└─────────────────────────────────────────────────────┘

MEDIUM CONFIDENCE (75%)
┌─────────────────────────────────────────────────────┐
│ Person: Jonathan Doe (entity-789)                   │
│ Match: Address "123 Main St, Springfield, IL"       │
│ Reason: Similar address (different city)            │
│ [Link Entities] [Dismiss]                           │
└─────────────────────────────────────────────────────┘
```

### Step 3: Take Action

For each suggestion, you can:

1. **Link Entities**: Create a relationship (TAGGED) between the entities
2. **Merge Entities**: Combine two entities into one (moves all data)
3. **Dismiss**: Mark as "not related" (won't show again)

### Step 4: Review Orphan Suggestions

On the Orphan Data page, view suggestions for each orphan:

```
Orphan: unknown-phone@investigation
Value: +1-555-123-4567

Suggested Entities (2)

HIGH CONFIDENCE (95%)
┌─────────────────────────────────────────────────────┐
│ Person: Alice Johnson (entity-123)                  │
│ Match: Phone "+15551234567"                         │
│ [Link to Entity] [Dismiss]                          │
└─────────────────────────────────────────────────────┘
```

## Use Cases

### Use Case 1: Finding Duplicate Entities

**Scenario**: You have two entities for the same person created at different times.

**How Smart Suggestions Helps**:

1. System detects they share the same email address
2. Shows HIGH confidence (95%) suggestion
3. You review both profiles
4. Click "Merge Entities"
5. All data from both entities is combined
6. Duplicate entity is removed

**Example**:

```
Entity A: John Doe
- Email: john.doe@example.com
- Phone: +1-555-1234
- Files: photo1.jpg, document1.pdf

Entity B: J. Doe
- Email: john.doe@example.com
- Address: 123 Main St
- Files: photo2.jpg

After Merge → Combined Entity:
- Name: John Doe
- Email: john.doe@example.com
- Phone: +1-555-1234
- Address: 123 Main St
- Files: photo1.jpg, document1.pdf, photo2.jpg
```

### Use Case 2: Linking Orphan Data

**Scenario**: You captured an email address during investigation but didn't know who it belonged to.

**How Smart Suggestions Helps**:

1. System searches for entities with this email
2. Finds 1 match with HIGH confidence
3. Shows suggestion to link orphan to entity
4. You click "Link to Entity"
5. Email is now part of that entity's profile

**Example**:

```
Orphan Data: suspect-email
- Type: email
- Value: suspect@darknet.onion
- Source: Investigation #42

Suggestion: Link to Entity "Alice Johnson"
- Confidence: 95% (exact match)
- Reason: Alice Johnson has email "suspect@darknet.onion"

After Linking:
- Orphan data is marked as "linked"
- Email appears in Alice Johnson's profile
- Source attribution preserved
```

### Use Case 3: Detecting Duplicate Files

**Scenario**: The same screenshot appears attached to multiple entities.

**How Smart Suggestions Helps**:

1. System computes SHA-256 hash of uploaded file
2. Searches database for matching hash
3. Finds same file in 2 other entities
4. Suggests these entities might be related

**Example**:

```
Uploading: evidence-screenshot.png

DUPLICATE DETECTED!

This file already exists in:
1. Entity: Bob Smith (entity-789)
   - File: screenshot-2026-01-01.png
   - Hash: abc123...

2. Orphan Data: orphan-456
   - File: evidence.png
   - Hash: abc123...

Suggestions:
- These entities might be the same person
- Consider linking or merging entities
```

### Use Case 4: Finding Related Addresses

**Scenario**: Two entities have similar addresses but in different cities.

**How Smart Suggestions Helps**:

1. System uses fuzzy matching on addresses
2. Finds "123 Main St, Springfield, IL" vs "123 Main St, Springfield, MA"
3. Shows MEDIUM confidence (70%) suggestion
4. You investigate and determine they're different people
5. Click "Dismiss" to hide suggestion

**Example**:

```
Entity: John Doe
- Address: 123 Main St, Springfield, IL

MEDIUM CONFIDENCE Suggestion (70%)
- Entity: Jane Doe (entity-456)
- Address: 123 Main St, Springfield, MA
- Reason: Similar address (different state)

Options:
[Link] - These are related
[Dismiss] - These are NOT related
```

## Advanced Features

### Hash-Based File Matching

Every file uploaded to Basset Hound is automatically hashed with SHA-256. This enables:

1. **Duplicate Detection**: Same file uploaded multiple times
2. **Integrity Verification**: Ensure files haven't been tampered with
3. **Cross-Entity Linking**: Find when same evidence appears in multiple entities

**Supported File Types**:
- Images: JPG, PNG, GIF, BMP
- Documents: PDF, DOCX, TXT
- Archives: ZIP, TAR, GZ
- Any binary file

**Example**: Verify File Integrity

```bash
# Using MCP Tools
compute_file_hash(project_id="my_investigation", file_path="evidence.jpg")
# Returns: {"hash": "abc123...", "size": 52481, "algorithm": "sha256"}

verify_file_integrity(
    project_id="my_investigation",
    file_path="evidence.jpg",
    expected_hash="abc123..."
)
# Returns: {"valid": true, "status": "VERIFIED"}
```

### Data ID System

Every piece of data in Basset Hound gets a unique ID in format `data_abc123`:

**Benefits**:
- Track individual data items across entities
- See when same email/phone appears in multiple places
- Preserve data when moving between entities
- Maintain audit trail of data changes

**Example**: Query Data by ID

```bash
# Get specific data item
get_data_item(project_id="my_investigation", data_id="data_abc123")

# Find all entities with this data
find_data_references(data_id="data_abc123")
```

### String Normalization

The system normalizes data for accurate matching:

| Data Type | Normalization | Example |
|-----------|---------------|---------|
| **Email** | Lowercase, trim | `User@EXAMPLE.COM` → `user@example.com` |
| **Phone** | E.164 format | `(555) 123-4567` → `+15551234567` |
| **Address** | Lowercase, abbreviations | `123 Main Street, Apt 4B` → `123 main st apt 4b` |
| **Name** | Remove middle initial, diacritics | `José García` → `jose garcia` |
| **Hash** | SHA-256 hex | Binary data → `abc123...` (64 chars) |

### Confidence Calculation

The system uses multiple algorithms to calculate confidence:

**Exact Hash Match** (1.0 confidence):
```
Binary comparison: hash1 == hash2
→ Confidence: 1.0 (100%)
```

**Exact String Match** (0.95 confidence):
```
Normalized comparison: normalize(str1) == normalize(str2)
→ Confidence: 0.95 (95%)
```

**Partial Match** (0.5-0.9 confidence):
```
Fuzzy matching algorithms:
1. Jaro-Winkler (names): similarity × 0.9
2. Token Set Ratio (addresses): similarity × 0.85
3. Levenshtein (general): similarity × 0.8

Formula:
if similarity >= 0.90: confidence = 0.9
if similarity >= 0.80: confidence = 0.7 + (similarity - 0.80) × 2.0
if similarity >= 0.70: confidence = 0.5 + (similarity - 0.70) × 2.0
else: not shown (below threshold)
```

## Best Practices

### 1. Review HIGH Confidence Suggestions First

Start with suggestions above 90% confidence - these are usually duplicates or exact matches.

### 2. Investigate MEDIUM Confidence Suggestions

For 70-89% confidence, investigate manually:
- Compare entity profiles side-by-side
- Check sources and dates
- Look for other corroborating data

### 3. Dismiss Irrelevant Suggestions

Don't ignore suggestions - dismiss them:
- Keeps your suggestion list clean
- System learns not to show again
- Helps other team members

### 4. Use File Hashing for Evidence

Always use the hash verification features:
- Verify evidence integrity before analysis
- Track chain of custody
- Detect file tampering

### 5. Link Before Merging

When unsure, use "Link" instead of "Merge":
- Linking creates a relationship (reversible)
- Merging combines entities (permanent)
- You can always merge later

## Troubleshooting

### Why don't I see suggestions?

**Possible Reasons**:

1. **No matching data**: Your entities don't share common identifiers
2. **Below threshold**: Similarity below 50% (not shown)
3. **Already dismissed**: You dismissed these suggestions before
4. **Different projects**: Suggestions are per-project

**Solution**: Check data normalization and similarity thresholds.

### Why are some suggestions wrong?

**Possible Reasons**:

1. **Common values**: Multiple people with same name/location
2. **Partial matches**: Similar but different data
3. **Data quality**: Incomplete or inconsistent data

**Solution**: Use confidence scores and manual verification.

### How do I undo a merge?

**Current Status**: Merging is permanent (by design)

**Workaround**:
1. Keep backups of projects before major operations
2. Use Export feature before merging
3. Use "Link" instead of "Merge" when uncertain

### Performance is slow

**Possible Reasons**:

1. **Large dataset**: >10,000 entities
2. **No indexes**: Neo4j indexes not created
3. **Partial matching**: Fuzzy matching is expensive

**Solution**:
1. Create Neo4j indexes (see Admin Guide)
2. Disable partial matching for faster suggestions
3. Use exact matching only for large datasets

## MCP Tools Reference

Smart Suggestions provides these MCP tools for automation:

### Data Management

```python
# Create data item
create_data_item(
    project_id="my_investigation",
    data_type="email",
    value="test@example.com",
    entity_id="entity-123"  # Optional
)

# Find similar data
find_similar_data(
    project_id="my_investigation",
    value="test@example.com",
    data_type="email"
)

# Find duplicate files
find_duplicate_files(
    project_id="my_investigation",
    file_path="evidence.jpg"
)
```

### File Hashing

```python
# Compute file hash
compute_file_hash(
    project_id="my_investigation",
    file_path="entity-123/files/evidence.jpg"
)

# Verify integrity
verify_file_integrity(
    project_id="my_investigation",
    file_path="evidence.jpg",
    expected_hash="abc123..."
)

# Find duplicates by hash
find_duplicates_by_hash(
    project_id="my_investigation",
    file_hash="abc123..."
)
```

### Matching Engine (Future)

```python
# Find matches for value
find_matches(
    value="john.doe@example.com",
    field_type="email",
    include_partial=True,
    confidence_threshold=0.7
)

# Get suggestions for entity
get_entity_suggestions(
    entity_id="entity-123",
    min_confidence=0.5
)

# Dismiss suggestion
dismiss_suggestion(
    entity_id="entity-123",
    suggested_entity_id="entity-456"
)
```

## API Endpoints (Future)

REST API endpoints for Smart Suggestions:

```
GET  /api/v1/suggestions/entity/{entity_id}
     - Get all suggestions for an entity
     - Query params: min_confidence, max_results

GET  /api/v1/suggestions/orphan/{orphan_id}
     - Get entity suggestions for orphan data

POST /api/v1/suggestions/find-matches
     - Find matches for arbitrary value
     - Body: {value, field_type, options}

POST /api/v1/suggestions/{suggestion_id}/dismiss
     - Dismiss a suggestion

POST /api/v1/suggestions/{suggestion_id}/link
     - Accept suggestion and link entities

POST /api/v1/suggestions/batch
     - Generate suggestions for multiple entities
     - Body: {entity_ids: [...]}
```

## Configuration

### Adjust Confidence Thresholds

Edit your project configuration to adjust thresholds:

```yaml
# config/suggestions.yaml
smart_suggestions:
  enabled: true

  # Minimum confidence to show suggestion
  min_confidence: 0.5  # 50%

  # Enable partial (fuzzy) matching
  partial_matching: true

  # Partial matching threshold
  partial_threshold: 0.7  # 70% similarity

  # Maximum suggestions per entity
  max_suggestions: 20

  # Show dismissed suggestions
  show_dismissed: false
```

### Performance Tuning

For large datasets (>10,000 entities):

```yaml
smart_suggestions:
  # Disable partial matching for speed
  partial_matching: false

  # Only show high-confidence matches
  min_confidence: 0.9

  # Limit suggestions per entity
  max_suggestions: 5

  # Use indexed fields only
  indexed_fields_only: true
```

## Examples

### Example 1: Complete Workflow

```bash
# 1. Create project
create_project(name="Investigation Alpha", safe_name="investigation_alpha")

# 2. Add entities
create_entity(project_id="investigation_alpha", name="John Doe")
# Returns: entity-001

create_entity(project_id="investigation_alpha", name="J. Doe")
# Returns: entity-002

# 3. Add email to both entities
add_data(entity_id="entity-001", type="email", value="john.doe@example.com")
add_data(entity_id="entity-002", type="email", value="john.doe@example.com")

# 4. Check suggestions
get_entity_suggestions(entity_id="entity-001")
# Returns:
# {
#   "suggestions": [{
#     "entity_id": "entity-002",
#     "confidence": 0.95,
#     "match_type": "exact_string",
#     "field": "email",
#     "value": "john.doe@example.com"
#   }]
# }

# 5. Merge entities
merge_entities(source="entity-002", target="entity-001")
# All data from entity-002 moved to entity-001
# entity-002 deleted
```

### Example 2: File Deduplication

```bash
# Upload file to entity A
upload_file(entity_id="entity-001", file_path="/tmp/evidence.jpg")
# System computes hash: abc123...

# Upload same file to entity B
upload_file(entity_id="entity-002", file_path="/tmp/evidence-copy.jpg")
# System detects duplicate hash: abc123...

# Get duplicate suggestions
find_duplicates_by_hash(
    project_id="investigation_alpha",
    file_hash="abc123..."
)
# Returns:
# {
#   "duplicates": [
#     {"entity_id": "entity-001", "file_path": "evidence.jpg"},
#     {"entity_id": "entity-002", "file_path": "evidence-copy.jpg"}
#   ],
#   "suggestions": [
#     "Consider if entity-001 and entity-002 are the same person"
#   ]
# }
```

### Example 3: Orphan Data Linking

```bash
# Create orphan data
create_orphan_data(
    project_id="investigation_alpha",
    identifier_type="phone",
    identifier_value="+1-555-123-4567",
    source="Phone records from Investigation #42"
)
# Returns: orphan-001

# Add same phone to existing entity
add_data(
    entity_id="entity-001",
    type="phone",
    value="+15551234567"
)

# Get suggestions for orphan
get_orphan_suggestions(orphan_id="orphan-001")
# Returns:
# {
#   "suggestions": [{
#     "entity_id": "entity-001",
#     "confidence": 0.95,
#     "match_type": "exact_string",
#     "field": "phone"
#   }]
# }

# Link orphan to entity
link_orphan_to_entity(orphan_id="orphan-001", entity_id="entity-001")
# Phone data added to entity-001 profile
# Orphan marked as "linked"
```

## FAQ

**Q: Are suggestions generated in real-time?**

A: Yes! Suggestions are generated on-demand when you view an entity or orphan data page.

**Q: Can I disable Smart Suggestions?**

A: Yes, set `smart_suggestions.enabled = false` in your project configuration.

**Q: Do suggestions work across projects?**

A: No, suggestions are project-scoped. Each project has independent suggestions.

**Q: How are dismissed suggestions stored?**

A: In Neo4j as a property on the entity: `dismissed_suggestions = ['entity-456', ...]`

**Q: Can I suggest custom matching rules?**

A: Not yet. Custom matching rules are planned for a future release.

**Q: Does this work with the MCP server?**

A: Yes! All Smart Suggestions features are available via MCP tools for AI agent integration.

## Support

For issues or questions:

1. Check this documentation
2. Review the API reference (`docs/API-SUGGESTIONS.md`)
3. Check GitHub issues
4. Contact: [Your contact info]

## Related Documentation

- [API Reference](API-SUGGESTIONS.md) - Complete API documentation
- [Matching Engine Architecture](findings/PHASE43_3-ARCHITECTURE.md) - Technical details
- [Data ID System](findings/PHASE43_1-DATA-ID-SYSTEM-2026-01-09.md) - Data model
- [File Hashing](findings/PHASE43_2-FILE-HASHING-2026-01-09.md) - Hash system

---

**Version**: 1.0
**Last Updated**: 2026-01-09
**Phase**: 43.6 - Integration Testing and Documentation
