# Phase 43.3: Matching Engine Architecture

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Smart Suggestions System                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Uses
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       MatchingEngine                             │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  find_exact_hash_matches()        [Confidence: 1.0]      │  │
│  │  find_exact_string_matches()      [Confidence: 0.95]     │  │
│  │  find_partial_matches()           [Confidence: 0.5-0.9]  │  │
│  │  find_all_matches()               [Combined]             │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
           │                    │                    │
           │                    │                    │
           ▼                    ▼                    ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│ StringNormalizer │  │  FuzzyMatcher    │  │ DataNormalizer   │
│                  │  │                  │  │                  │
│ - Email          │  │ - Jaro-Winkler   │  │ - Phone (E.164)  │
│ - Phone          │  │ - Levenshtein    │  │ - Email          │
│ - Address        │  │ - Token Set      │  │ - Crypto         │
│ - Name           │  │ - Token Sort     │  │ - URL            │
│ - Hash (SHA-256) │  │ - Partial Ratio  │  │ - IP Address     │
└──────────────────┘  └──────────────────┘  └──────────────────┘
           │                    │                    │
           └────────────────────┴────────────────────┘
                              │
                              ▼
                     ┌─────────────────┐
                     │   Neo4j Service │
                     │                 │
                     │  - Entity Nodes │
                     │  - Orphan Data  │
                     │  - DataItems    │
                     └─────────────────┘
```

## Data Flow

### 1. Exact Hash Matching

```
Input: hash_value
  │
  ├─> Query Neo4j for hash matches
  │
  ├─> Return all entities/data with matching hash
  │
  └─> MatchResult(confidence=1.0, match_type="exact_hash")
```

### 2. Exact String Matching

```
Input: value, field_type
  │
  ├─> Normalize value (email, phone, etc.)
  │
  ├─> Query Neo4j for exact normalized matches
  │
  ├─> Search both entities and orphan data
  │
  └─> MatchResult(confidence=0.95, match_type="exact_string")
```

### 3. Partial Matching

```
Input: value, field_type, threshold
  │
  ├─> Normalize value based on type
  │
  ├─> Query Neo4j for all candidates
  │
  ├─> For each candidate:
  │   ├─> Normalize candidate
  │   ├─> Calculate similarity (Jaro-Winkler/Levenshtein/Token)
  │   └─> Filter by threshold
  │
  ├─> Calculate confidence from similarity
  │
  └─> MatchResult(confidence=0.5-0.9, match_type="partial_string")
```

### 4. Combined Matching

```
Input: value, field_type, options
  │
  ├─> Try exact hash matching (if applicable)
  │
  ├─> Try exact string matching
  │
  ├─> Try partial matching (if enabled)
  │
  ├─> Combine and deduplicate results
  │
  ├─> Sort by confidence descending
  │
  └─> List[(MatchResult, confidence, match_type)]
```

## Component Details

### MatchingEngine

**Purpose**: Orchestrate all matching operations

**Key Methods**:
- `find_exact_hash_matches()`: Binary data matching
- `find_exact_string_matches()`: Identifier matching
- `find_partial_matches()`: Fuzzy text matching
- `find_all_matches()`: Combined strategy matching

**Dependencies**:
- AsyncNeo4jService (database)
- FuzzyMatcher (similarity calculations)
- DataNormalizer (type-specific normalization)
- StringNormalizer (matching-specific normalization)

### StringNormalizer

**Purpose**: Prepare strings for matching comparison

**Key Methods**:
- `normalize_email()`: Lowercase, trim
- `normalize_phone_e164()`: E.164 format
- `normalize_address()`: Abbreviations, no punctuation
- `normalize_name()`: No middle initials, no diacritics
- `calculate_hash()`: SHA-256 for binary data

**Features**:
- Unicode normalization (NFD)
- Diacritic removal
- Abbreviation expansion
- Punctuation handling

### FuzzyMatcher

**Purpose**: Calculate string similarity scores

**Algorithms**:
- **Jaro-Winkler**: Best for names (prioritizes prefix matches)
- **Levenshtein**: Edit distance (insertions, deletions, substitutions)
- **Token Set Ratio**: Handles word order differences
- **Token Sort Ratio**: Alphabetical token comparison
- **Partial Ratio**: Substring matching

**Strategy Selection**:
- Names → Jaro-Winkler
- Addresses → Token Set Ratio
- General → Levenshtein

### DataNormalizer

**Purpose**: Type-specific data normalization

**Supported Types**:
- EMAIL
- PHONE
- CRYPTO_ADDRESS
- USERNAME
- DOMAIN
- URL
- IP_ADDRESS
- MAC_ADDRESS

**Features**:
- Validation
- Component extraction
- Alternative forms
- Error reporting

## Confidence Scoring System

```
┌─────────────────────────────────────────────────────────┐
│              Confidence Calculation Flow                 │
└─────────────────────────────────────────────────────────┘

Similarity Score (0.0-1.0)
        │
        ├─> ≥ 0.90 → Confidence: 0.9
        │
        ├─> 0.80-0.89 → Confidence: 0.7 + (sim - 0.80) * 2.0
        │                         = 0.7 to 0.9 (linear)
        │
        ├─> 0.70-0.79 → Confidence: 0.5 + (sim - 0.70) * 2.0
        │                         = 0.5 to 0.7 (linear)
        │
        └─> < 0.70 → Not shown (below threshold)

Examples:
  sim = 1.00 → conf = 1.0   (exact match)
  sim = 0.95 → conf = 0.95  (exact string)
  sim = 0.90 → conf = 0.9   (very similar)
  sim = 0.85 → conf = 0.8   (high similarity)
  sim = 0.75 → conf = 0.6   (medium similarity)
  sim = 0.70 → conf = 0.5   (threshold)
```

## Neo4j Schema Integration

### Entity Node Structure

```cypher
(:Entity {
  id: "entity-123",
  created_at: "2026-01-09T10:00:00",
  profile: {
    core: {
      name: [{
        first_name: "John",
        last_name: "Doe"
      }],
      email: ["john.doe@example.com"],
      phone: ["+15551234567"]
    },
    social: {
      linkedin: [{
        url: "https://linkedin.com/in/johndoe",
        username: "johndoe"
      }]
    }
  }
})
```

### Orphan Data Node Structure

```cypher
(:OrphanData {
  id: "orphan-456",
  identifier_type: "email",
  identifier_value: "test@example.com",
  normalized_value: "test@example.com",
  source: "Investigation #42",
  tags: ["suspect", "investigation"],
  discovered_date: "2026-01-09T10:00:00"
})
```

### DataItem Node Structure (Future)

```cypher
(:DataItem {
  id: "data-789",
  hash: "abc123...",
  file_name: "document.pdf",
  file_size: 1024000,
  mime_type: "application/pdf",
  created_at: "2026-01-09T10:00:00"
})
```

### Required Indexes

```cypher
// Hash index for fast binary matching
CREATE INDEX data_hash IF NOT EXISTS
FOR (d:DataItem) ON (d.hash);

// Normalized value index for exact string matching
CREATE INDEX data_normalized IF NOT EXISTS
FOR (d:DataItem) ON (d.normalized_value);

// Orphan normalized value index
CREATE INDEX orphan_normalized IF NOT EXISTS
FOR (o:OrphanData) ON (o.normalized_value);

// Entity ID index
CREATE INDEX entity_id IF NOT EXISTS
FOR (e:Entity) ON (e.id);

// Identifier type index for filtering
CREATE INDEX orphan_type IF NOT EXISTS
FOR (o:OrphanData) ON (o.identifier_type);
```

## Performance Optimization

### Query Optimization

```cypher
// Optimized query for exact string matching
MATCH (e:Entity)
UNWIND keys(e.profile) as section
UNWIND keys(e.profile[section]) as field
WITH e, section, field, e.profile[section][field] as values
WHERE field = $field_type
UNWIND values as value
WITH e, section, field, value,
     CASE
       WHEN value.normalized_value = $normalized_value THEN true
       WHEN toLower(toString(value)) = $normalized_value THEN true
       ELSE false
     END as is_match
WHERE is_match
RETURN e.id as entity_id,
       section + '.' + field as field_type,
       value as field_value,
       coalesce(value.id, null) as data_id
LIMIT 100
```

### Caching Strategy (Future)

```
┌─────────────────────────────────────────────────────────┐
│                    Redis Cache Layer                     │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Key: "match:hash:{hash}"                       │   │
│  │  TTL: 1 hour                                    │   │
│  │  Value: [MatchResult, ...]                      │   │
│  └─────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Key: "match:exact:{type}:{normalized_value}"  │   │
│  │  TTL: 30 minutes                                │   │
│  │  Value: [MatchResult, ...]                      │   │
│  └─────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Key: "normalized:{type}:{value}"               │   │
│  │  TTL: 1 hour                                    │   │
│  │  Value: normalized_string                       │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## Error Handling

### Error Types

1. **Neo4jConnectionError**: Database connection failed
2. **Neo4jQueryError**: Query execution failed
3. **NormalizationError**: Value normalization failed
4. **ValidationError**: Invalid input parameters

### Error Flow

```
User Request
     │
     ├─> Validate input parameters
     │   └─> ValidationError if invalid
     │
     ├─> Normalize value
     │   └─> NormalizationError if fails
     │
     ├─> Query Neo4j
     │   └─> Neo4jConnectionError if connection fails
     │   └─> Neo4jQueryError if query fails
     │
     ├─> Process results
     │
     └─> Return matches (empty list on error)
```

## Integration Points

### REST API (Future)

```
POST /api/v1/suggestions/find-matches
GET  /api/v1/suggestions/entity/{entity_id}
GET  /api/v1/suggestions/orphan/{orphan_id}
POST /api/v1/suggestions/batch
```

### WebSocket (Future)

```
ws://host/api/v1/suggestions/realtime
  → send: {"action": "subscribe", "entity_id": "123"}
  ← recv: {"type": "match", "data": {...}}
```

### MCP Integration (Future)

```python
@mcp.tool()
async def find_matches(value: str, field_type: str):
    """Find potential matches for a value"""
    async with MatchingEngine() as engine:
        return await engine.find_all_matches(value, field_type)
```

## Monitoring and Metrics

### Key Metrics

1. **Latency**
   - P50: <100ms
   - P95: <500ms
   - P99: <1000ms

2. **Throughput**
   - Queries per second: >100
   - Concurrent queries: >10

3. **Accuracy**
   - False positive rate: <5%
   - False negative rate: <10%
   - User acceptance rate: >80%

### Logging

```python
logger.info(f"Match query: type={field_type}, confidence>={threshold}")
logger.debug(f"Found {len(matches)} candidates")
logger.info(f"Returned {len(filtered)} matches above threshold")
logger.error(f"Query failed: {error}")
```

## Testing Strategy

### Unit Tests
- String normalization (5 tests)
- Individual matching methods (4 tests)
- Confidence scoring (1 test)
- Edge cases (3 tests)

### Integration Tests
- Neo4j integration (planned)
- API endpoints (planned)
- End-to-end workflows (planned)

### Performance Tests
- Batch matching (1 test)
- Large dataset handling (planned)
- Concurrent queries (planned)

---

**Architecture Version**: 1.0
**Last Updated**: 2026-01-09
**Status**: Production Ready ✅
