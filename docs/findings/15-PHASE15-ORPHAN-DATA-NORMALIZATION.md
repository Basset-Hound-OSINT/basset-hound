# Phase 15: Orphan Data Management & Data Normalization

**Date:** 2025-12-29
**Status:** COMPLETED

## Overview

Phase 15 implements two major features for the Basset Hound OSINT platform:

1. **Orphan Data Management** - A complete system for managing unlinked identifiers (emails, phones, crypto addresses, etc.) that haven't been tied to entities yet.

2. **Data Normalization Service** - Standardizes data formats before storage to make searching consistent and reliable across the platform.

## Key Concepts

### Orphan Data

Orphan data represents identifiers discovered during OSINT investigations that don't yet have an associated entity. This is critical because:

- Data is often collected before relationships are established
- Multiple sources may reference the same identifier
- Investigators need to stage data before making entity connections

### Bidirectional Data Flow

A key innovation in this phase is the **bidirectional data flow** between entities and orphan data:

- **Link to Entity**: Move orphan data into an entity's profile
- **Detach from Entity**: Remove data from an entity and convert it back to orphan status

This enables "soft delete" - data is never truly lost, just moved between states.

## Implementation Details

### 1. Orphan Data Models (`api/models/orphan.py`)

**IdentifierType Enum:**
- EMAIL, PHONE, CRYPTO_ADDRESS, USERNAME, IP_ADDRESS
- DOMAIN, URL, SOCIAL_MEDIA, LICENSE_PLATE, PASSPORT
- SSN, ACCOUNT_NUMBER, MAC_ADDRESS, IMEI, OTHER

**Pydantic Models:**
- `OrphanDataCreate` - Create new orphan records
- `OrphanDataUpdate` - Partial update support
- `OrphanDataResponse` - API response model
- `OrphanDataList` - Paginated list response
- `OrphanLinkRequest/Response` - Link orphan to entity
- `DetachRequest/Response` - Detach data from entity to orphan

### 2. Orphan Service (`api/services/orphan_service.py`)

**CRUD Operations:**
- `create_orphan()` - Create with auto-generated ID
- `get_orphan()` - Retrieve by ID
- `list_orphans()` - List with filtering (type, tags, date, linked status)
- `update_orphan()` - Partial updates
- `delete_orphan()` - Permanent deletion

**Auto-Linking:**
- `suggest_entity_matches()` - Find entities that match orphan identifiers
- Scoring algorithm: exact match (10.0), fuzzy high (9.0), fuzzy medium (7.0)
- Threshold for suggestions: score >= 7.0

**Linking Operations:**
- `link_to_entity()` - Connect orphan to entity, optionally merge data
- `detach_from_entity()` - Remove value from entity, create orphan

**Bulk Operations:**
- `import_orphans_bulk()` - Batch import with duplicate detection
- `find_duplicates()` - Identify duplicate identifiers

**Field Mappings:**
```python
IDENTIFIER_FIELD_MAP = {
    EMAIL: ["core.email", "contact.email", "online.email"],
    PHONE: ["core.phone", "contact.phone"],
    USERNAME: ["online.username", "social.username"],
    CRYPTO_ADDRESS: ["financial.crypto_address", "blockchain.address"],
    IP_ADDRESS: ["technical.ip_address", "network.ip"],
    ...
}

FIELD_PATH_TO_IDENTIFIER_TYPE = {
    "core.email": IdentifierType.EMAIL,
    "core.phone": IdentifierType.PHONE,
    ...
}
```

### 3. Data Normalization Service (`api/services/normalizer.py`)

**NormalizedResult Dataclass:**
```python
@dataclass
class NormalizedResult:
    original: str           # Original input
    normalized: str         # Standardized format
    is_valid: bool          # Validation passed
    components: dict        # Extracted parts
    alternative_forms: list # Other searchable forms
    errors: list            # Validation errors
```

**Normalization Methods:**

| Method | Input | Output | Components |
|--------|-------|--------|------------|
| `normalize_phone()` | `(555) 123-4567` | `5551234567` | country_code, local_number |
| `normalize_email()` | `User@EXAMPLE.COM` | `user@example.com` | user, domain, tag |
| `normalize_username()` | `@JohnDoe` | `johndoe` | original_had_at |
| `normalize_domain()` | `https://WWW.Example.COM/` | `example.com` | tld, subdomain |
| `normalize_url()` | `HTTP://...` | `http://...` | scheme, domain, path |
| `normalize_ip()` | `192.168.001.001` | `192.168.1.1` | version, octets |
| `normalize_crypto()` | `0x...` | `0x...` | crypto_type, crypto_name |
| `normalize_mac_address()` | `00-1A-2B-...` | `00:1a:2b:...` | oui, nic |

**Plus-Addressing Support:**
For emails like `service+support@gmail.com`:
- Normalized: `service+support@gmail.com`
- Alternative form: `service@gmail.com` (base email for searching)
- Components: `user=service`, `tag=support`, `domain=gmail.com`

### 4. REST API Endpoints (`api/routers/orphan.py`)

**CRUD Endpoints:**
- `POST /projects/{id}/orphans` - Create orphan
- `GET /projects/{id}/orphans` - List with filters
- `GET /projects/{id}/orphans/{id}` - Get by ID
- `PUT /projects/{id}/orphans/{id}` - Update
- `DELETE /projects/{id}/orphans/{id}` - Delete

**Linking Endpoints:**
- `GET /projects/{id}/orphans/{id}/suggestions` - Entity match suggestions
- `POST /projects/{id}/orphans/{id}/link` - Link to entity
- `POST /projects/{id}/orphans/detach` - Detach from entity (NEW)

**Utility Endpoints:**
- `POST /projects/{id}/orphans/batch` - Bulk import
- `GET /projects/{id}/orphans/duplicates` - Find duplicates
- `GET /orphans/types` - List identifier types

## Detach Operation Details

The detach operation is the key innovation enabling bidirectional data flow:

```python
request = DetachRequest(
    entity_id="entity-123",
    field_path="core.email",
    field_value="old@example.com",
    reason="Email belongs to different person",
    keep_in_entity=False  # True to copy instead of move
)

response = service.detach_from_entity(project_id, request)
# Returns:
# - success: True
# - orphan_id: "orphan-xxx" (newly created)
# - removed_from_entity: True
# - message: "Data successfully detached..."
```

**Provenance Metadata:**
When data is detached, the orphan record includes:
- `detached_from_entity`: Original entity ID
- `detached_from_field`: Field path (e.g., "core.email")
- `detached_at`: Timestamp
- `detach_reason`: User-provided reason
- `original_entity_name`: Name from entity preview

## Testing

**Normalizer Tests (`tests/test_normalizer.py`):**
- Phone normalization (with/without country codes)
- Email normalization (case, plus-addressing)
- Username normalization (@ removal, lowercase)
- Domain normalization (protocol, www removal)
- URL normalization (domain lowercase, path preserved)
- IP normalization (IPv4 leading zeros, IPv6 expansion)
- Crypto address detection
- MAC address formatting

**Test Execution:**
```bash
python3 -m pytest tests/test_normalizer.py -v
```

## Files Created/Modified

**New Files:**
```
api/services/normalizer.py          # DataNormalizer service
tests/test_normalizer.py            # Normalizer tests
docs/findings/15-PHASE15-*.md       # This document
```

**Modified Files:**
```
api/models/orphan.py                # Added DetachRequest, DetachResponse
api/services/orphan_service.py      # Added detach_from_entity(), mappings
api/routers/orphan.py               # Added /detach endpoint, link implementation
docs/ROADMAP.md                     # Updated with Phase 15 details
```

## Usage Examples

### Creating Orphan Data
```python
orphan = OrphanDataCreate(
    identifier_type=IdentifierType.EMAIL,
    identifier_value="john@example.com",
    source="Data breach 2024",
    notes="Found in leaked database",
    tags=["breach", "unverified"],
    confidence_score=0.6
)
result = service.create_orphan("project-123", orphan)
```

### Linking Orphan to Entity
```python
result = service.link_to_entity(
    project_id="project-123",
    orphan_id="orphan-456",
    entity_id="entity-789",
    merge=True,   # Add value to entity profile
    delete=False  # Keep orphan record
)
```

### Detaching Data from Entity
```python
request = DetachRequest(
    entity_id="entity-789",
    field_path="core.email",
    field_value="john@example.com",
    reason="Belongs to different person"
)
result = service.detach_from_entity("project-123", request)
```

### Normalizing Data
```python
normalizer = DataNormalizer()

# Phone
result = normalizer.normalize_phone("+1 (555) 123-4567")
print(result.normalized)  # "+15551234567"
print(result.components)  # {"country_code": "1", ...}

# Email with plus-addressing
result = normalizer.normalize_email("User+Tag@EXAMPLE.COM")
print(result.normalized)      # "user+tag@example.com"
print(result.alternative_forms)  # ["user@example.com"]
```

## Future Enhancements

1. **Auto-normalize on input** - Integrate normalizer into create/update flows
2. **Batch normalization** - Normalize existing data in database
3. **Custom normalization rules** - User-defined patterns per project
4. **Similarity search** - Find similar identifiers using normalized forms
5. **Duplicate prevention** - Check for duplicates using normalized values

## Conclusion

Phase 15 establishes a robust foundation for managing unlinked identifiers in OSINT investigations. The bidirectional data flow ensures data is never lost, while normalization makes searching consistent across varied input formats.
