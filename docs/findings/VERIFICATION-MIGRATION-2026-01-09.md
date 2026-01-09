# Verification System Migration - Phase 42

**Date:** 2026-01-09
**Phase:** 42 (Scope Clarification & Verification Migration)
**Status:** In Progress

---

## Executive Summary

This document captures the migration of the verification system from basset-hound to the new basset-verify microservice. This scope clarification ensures basset-hound remains focused on **intelligence management only**, while basset-verify handles all identifier verification.

**Key Changes:**
- Created new `~/basset-verify` repository
- Defined clear scope boundaries for both projects
- 12 MCP tools will migrate from basset-hound to basset-verify
- basset-hound tool count: 112 → 100 tools
- basset-verify tool count: 0 → 12 tools

---

## 1. Motivation

### User Feedback (2026-01-09)

> "I would like to clarify that this project should not perform any other features other than Intelligence management... i would want to make a different project... i made a new git repository ~/basset-verify that i want to migrate all information Verification to"

### Key Points:

1. **basset-hound Scope**: Intelligence management ONLY
   - Store entities, relationships, investigations
   - Provide MCP server for AI agents
   - Generate reports
   - NO OSINT automation
   - NO fingerprinting/analysis beyond intelligence storage

2. **Verification Should Be Separate**:
   - Create standalone basset-verify microservice
   - Verification is optional dependency
   - Graceful degradation if basset-verify is down
   - Manual verification only (user clicks "Verify" button)

3. **Why Manual Verification?**:
   - Automatic verification can alert threat actors
   - Threat actors monitor traffic patterns
   - .onion addresses should not be auto-verified (Tor monitoring)
   - User discretion required for sensitive targets

---

## 2. Architecture Change

### Before Migration

```
┌──────────────────────────────────────────┐
│           basset-hound                   │
│                                          │
│  - Intelligence Management               │
│  - Investigation Tracking                │
│  - Entity/Relationship Storage           │
│  - Verification Tools (12 MCP tools)  ← REMOVE
│  - Sock Puppet Management                │
│  - Evidence Storage                      │
│  - Orphan Data Management                │
│                                          │
│  Total: 112 MCP tools                    │
└──────────────────────────────────────────┘
```

### After Migration

```
┌──────────────────────────────────────────┐
│           basset-hound                   │
│     (Intelligence Management)            │
│                                          │
│  - Entity/Relationship Storage           │
│  - Investigation Tracking                │
│  - Sock Puppet Management                │
│  - Evidence Storage                      │
│  - Orphan Data Management                │
│  - Provenance Tracking                   │
│  - Graph Analysis                        │
│  - Reports Generation                    │
│                                          │
│  Total: 100 MCP tools                    │
└─────────────────┬────────────────────────┘
                  │ Optional
                  │ User clicks "Verify"
                  ▼
┌──────────────────────────────────────────┐
│          basset-verify                   │
│    (Verification Microservice)           │
│                                          │
│  - Email Verification                    │
│  - Phone Verification                    │
│  - Crypto Address Detection (30+)       │
│  - Domain Verification                   │
│  - IP Verification                       │
│  - URL Verification                      │
│  - Username Verification                 │
│  - Batch Verification                    │
│                                          │
│  Total: 12 MCP tools                     │
└──────────────────────────────────────────┘
```

---

## 3. Scope Clarification

### basset-hound Scope (INTELLIGENCE MANAGEMENT)

#### ✅ In Scope:
- Entity CRUD operations
- Relationship management
- Investigation lifecycle
- Sock puppet management (metadata only, not credentials)
- Evidence storage (from basset-hound-browser)
- Orphan data management
- Provenance tracking
- Graph analysis & visualization
- Report generation
- MCP server for AI agents

#### ❌ Out of Scope:
- Identifier verification → basset-verify
- OSINT automation → palletai agents
- Browser automation → basset-hound-browser
- Credential management → 1Password, Bitwarden, etc.
- Active reconnaissance → external tools
- Real-time monitoring → external tools

### basset-verify Scope (VERIFICATION ONLY)

#### ✅ In Scope:
- Format validation (email, phone, crypto, domain, IP, URL, username)
- Network verification (MX/DNS lookups)
- Cryptocurrency detection (30+ currencies)
- Batch verification
- Graceful degradation
- Manual verification only

#### ❌ Out of Scope:
- Intelligence storage → basset-hound
- Entity management → basset-hound
- OSINT automation → palletai
- Browser automation → basset-hound-browser
- Automatic verification (security risk)

---

## 4. Tools to Migrate

### From basset-hound (Phase 40.5) → To basset-verify

| # | Tool Name | Description |
|---|-----------|-------------|
| 1 | `get_verification_types` | List available identifier types and verification levels |
| 2 | `verify_identifier` | Generic verification (routes to specialized verifier) |
| 3 | `verify_email` | Email format + MX/DNS |
| 4 | `verify_phone` | Phone parsing with libphonenumber |
| 5 | `verify_domain` | Domain format + DNS resolution |
| 6 | `verify_ip` | IPv4/IPv6 validation |
| 7 | `verify_url` | URL parsing and validation |
| 8 | `verify_username` | Username format validation |
| 9 | `verify_crypto` | Cryptocurrency address detection |
| 10 | `get_all_crypto_matches` | All possible crypto matches for ambiguous addresses |
| 11 | `batch_verify` | Verify up to 100 identifiers |
| 12 | `get_supported_cryptocurrencies` | List 30+ supported currencies |

**Total**: 12 tools

---

## 5. Files to Migrate

### Source Files (basset-hound)

```
basset-hound/
├── api/
│   ├── services/
│   │   └── verification_service.py     → basset-verify/basset_verify/services/verification_service.py
│   └── utils/
│       └── crypto_detector.py          → basset-verify/basset_verify/services/crypto_detector.py
├── basset_mcp/
│   └── tools/
│       └── verification.py             → basset-verify/basset_verify/mcp/tools.py
└── tests/
    └── test_verification_service.py    → basset-verify/tests/test_verification_service.py
```

### Target Structure (basset-verify)

```
basset-verify/
├── basset_verify/
│   ├── __init__.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── verification_service.py     # From basset-hound
│   │   └── crypto_detector.py          # From basset-hound
│   ├── api/
│   │   ├── __init__.py
│   │   └── server.py                   # NEW - FastAPI server
│   └── mcp/
│       ├── __init__.py
│       └── tools.py                    # From basset-hound (adapted)
├── tests/
│   ├── __init__.py
│   ├── test_verification_service.py    # From basset-hound
│   └── test_mcp_tools.py               # NEW
├── docs/
│   ├── SCOPE.md                        # CREATED
│   ├── ROADMAP.md                      # CREATED
│   └── findings/
├── config.yaml                         # NEW
├── requirements.txt                    # NEW
├── requirements-dev.txt                # NEW
├── Dockerfile                          # NEW
├── docker-compose.yaml                 # NEW
└── README.md                           # CREATED
```

---

## 6. Code Changes Required

### 6.1 basset-verify Setup

**Phase 1 Tasks**:
1. Create package structure: `basset_verify/`
2. Migrate `VerificationService` class
3. Migrate `CryptoAddressDetector` class
4. Update imports (remove basset-hound dependencies)
5. Create standalone `requirements.txt`
6. Migrate tests and update paths
7. Ensure all tests pass independently

### 6.2 basset-hound Refactoring

**Phase 7 Tasks**:
1. Remove `basset_mcp/tools/verification.py`
2. Create `BassetVerifyClient` for optional integration
3. Add graceful degradation:
```python
try:
    result = await basset_verify_client.verify_email(email)
except (ConnectionError, TimeoutError):
    return {"status": "verification_unavailable"}
```
4. Update tool registration (remove 12 verification tools)
5. Update tool count: 112 → 100
6. Update documentation

### 6.3 Graceful Degradation Example

```python
# In basset-hound: basset_mcp/tools/entities.py

from typing import Optional
import httpx

class BassetVerifyClient:
    """Optional client for basset-verify microservice."""

    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=5.0)
        self.available = None  # Cache availability check

    async def is_available(self) -> bool:
        """Check if basset-verify is available."""
        if self.available is not None:
            return self.available

        try:
            response = await self.client.get(f"{self.base_url}/health")
            self.available = response.status_code == 200
            return self.available
        except:
            self.available = False
            return False

    async def verify_email(self, email: str, level: str = "format") -> dict:
        """Verify email with graceful degradation."""
        if not await self.is_available():
            return {
                "status": "verification_unavailable",
                "message": "basset-verify service is unavailable",
                "is_valid": None,
                "confidence": 0.0
            }

        try:
            response = await self.client.post(
                f"{self.base_url}/verify",
                json={"value": email, "type": "email", "level": level}
            )
            return response.json()
        except Exception as e:
            return {
                "status": "verification_error",
                "message": f"Error calling basset-verify: {str(e)}",
                "is_valid": None,
                "confidence": 0.0
            }

# In MCP tool
@mcp.tool()
async def verify_entity_identifier(
    project_id: str,
    entity_id: str,
    identifier_type: str,
    identifier_value: str,
    level: str = "format"
) -> dict:
    """
    Verify an entity's identifier via basset-verify (optional).

    If basset-verify is unavailable, returns 'verification_unavailable' status.
    """
    verify_client = BassetVerifyClient()

    result = await verify_client.verify_email(identifier_value, level)

    # Store result in entity metadata (even if unavailable)
    # ... entity update code ...

    return result
```

---

## 7. Manual Verification Flow

### User Workflow

```
1. User views entity in basset-hound UI
   └─ Entity shows email: "target@example.com"
   └─ Status: "unverified" (gray badge)

2. User clicks "Verify" button next to identifier

3. basset-hound calls basset-verify API
   └─ POST http://localhost:8001/verify
   └─ {value: "target@example.com", type: "email", level: "network"}

4. basset-verify performs validation
   └─ Format check ✓
   └─ MX record lookup ✓
   └─ Disposable domain check ✓

5. Result returned to basset-hound
   └─ {is_valid: true, confidence: 0.95, details: {...}}

6. basset-hound stores result in entity metadata

7. UI updates status badge
   └─ "Verified ✓" (green badge)
   └─ Confidence: 95%
   └─ Last verified: 2026-01-09 12:00:00
```

### .onion Address Special Handling

```
1. Entity has identifier: "http://example.onion"

2. basset-hound detects .onion domain
   └─ Shows "Tor Hidden Service" badge
   └─ Status: "unverified"
   └─ Warning: "Manual verification recommended"

3. User clicks "Verify" button

4. basset-verify returns format validation only
   └─ {is_valid: true, confidence: 0.5}
   └─ {status: "requires_manual_verification"}
   └─ {message: "Use basset-hound-browser with Tor to verify"}

5. User can choose to verify via basset-hound-browser
   └─ basset-hound-browser navigates with Tor
   └─ Captures screenshot as evidence
   └─ Submits to basset-hound
```

---

## 8. Tool Count Changes

### basset-hound Tool Count

| Module | Before Migration | After Migration | Change |
|--------|-----------------|-----------------|--------|
| schema | 6 | 6 | 0 |
| entities | 6 | 6 | 0 |
| relationships | 7 | 7 | 0 |
| search | 2 | 2 | 0 |
| projects | 3 | 3 | 0 |
| reports | 2 | 2 | 0 |
| analysis | 6 | 6 | 0 |
| auto_linking | 4 | 4 | 0 |
| orphans | 11 | 11 | 0 |
| provenance | 8 | 8 | 0 |
| sock_puppets | 15 | 15 | 0 |
| **verification** | **12** | **0** | **-12** |
| investigations | 17 | 17 | 0 |
| browser_integration | 13 | 13 | 0 |
| **TOTAL** | **112** | **100** | **-12** |

### basset-verify Tool Count

| Module | Tool Count |
|--------|-----------|
| verification | 12 |
| **TOTAL** | **12** |

---

## 9. Integration Testing Plan

### Test Scenarios

#### Scenario 1: basset-verify Available
```
1. Start basset-verify on port 8001
2. Start basset-hound on port 8000
3. Create entity with email identifier
4. Call verify_entity_identifier MCP tool
5. Verify result includes is_valid, confidence, details
6. Verify entity metadata updated with verification result
```

#### Scenario 2: basset-verify Unavailable
```
1. Stop basset-verify
2. Start basset-hound on port 8000
3. Create entity with email identifier
4. Call verify_entity_identifier MCP tool
5. Verify result: {status: "verification_unavailable"}
6. Verify basset-hound continues to function
7. Verify entity still created successfully
```

#### Scenario 3: basset-verify Timeout
```
1. Start basset-verify with slow network verification
2. Start basset-hound on port 8000
3. Call verify_entity_identifier with level="network"
4. Verify 5-second timeout triggers
5. Verify graceful degradation returns format validation only
```

#### Scenario 4: .onion Address
```
1. Create entity with .onion URL
2. Call verify_entity_identifier
3. Verify result: {status: "requires_manual_verification"}
4. Verify warning message about Tor
```

---

## 10. Migration Timeline

### Phase 42: Verification Migration (Current Phase)

**Week 1 (2026-01-09 to 2026-01-13)**:
- [x] Create basset-verify repository structure
- [x] Create SCOPE.md for both projects
- [x] Create basset-verify README
- [x] Create basset-verify ROADMAP
- [ ] Migrate verification code (Phase 1)
- [ ] Migrate tests
- [ ] Ensure tests pass independently

**Week 2 (2026-01-13 to 2026-01-20)**:
- [ ] Create REST API (Phase 2)
- [ ] Create MCP Server (Phase 3)
- [ ] Enhance crypto detection (Phase 4)
- [ ] Add network verification (Phase 5)

**Week 3 (2026-01-20 to 2026-01-27)**:
- [ ] Docker deployment (Phase 6)
- [ ] basset-hound integration (Phase 7)
- [ ] Testing & documentation (Phase 8)
- [ ] Update basset-hound roadmap

---

## 11. Documentation Updates Required

### basset-hound Updates

- [ ] Update README to clarify scope (intelligence management only)
- [ ] Update ROADMAP.md to remove verification features
- [ ] Update SCOPE.md (created in Phase 42)
- [ ] Update MCP tool count: 112 → 100
- [ ] Create BASSET-VERIFY-INTEGRATION.md guide
- [ ] Update Phase 40.5 findings to note migration

### basset-verify Updates

- [x] Create README
- [x] Create SCOPE.md
- [x] Create ROADMAP.md
- [ ] Create API reference documentation
- [ ] Create MCP tool documentation
- [ ] Create integration examples

---

## 12. Benefits of Separation

### 1. Clear Separation of Concerns
- basset-hound: Intelligence management
- basset-verify: Identifier verification
- Each service has a single, focused responsibility

### 2. Optional Dependency
- basset-hound works even if basset-verify is down
- Graceful degradation prevents service outages
- Users can choose whether to deploy basset-verify

### 3. Security
- Manual verification only (user discretion)
- No automatic traffic that could alert threat actors
- .onion addresses not automatically queried

### 4. Scalability
- basset-verify can scale independently
- High-volume verification doesn't impact intelligence storage
- Can deploy multiple basset-verify instances

### 5. Reusability
- Other tools can use basset-verify independently
- Not tied to basset-hound's architecture
- Standalone microservice with clear API

### 6. Maintenance
- Easier to maintain focused codebases
- Verification logic separate from graph database logic
- Testing is simpler (unit vs integration)

---

## 13. Risks & Mitigation

### Risk 1: Service Dependency

**Risk**: basset-hound depends on basset-verify for verification

**Mitigation**:
- Graceful degradation (basset-hound works without basset-verify)
- Clear "verification unavailable" messaging
- Entities can exist without verification

### Risk 2: Migration Complexity

**Risk**: Code migration may introduce bugs

**Mitigation**:
- Comprehensive test coverage (>90%)
- Test both services independently
- Test integration scenarios
- Gradual rollout

### Risk 3: User Confusion

**Risk**: Users may not understand two separate services

**Mitigation**:
- Clear documentation (SCOPE.md, README)
- Architecture diagrams
- Integration guides
- Docker Compose for easy deployment

### Risk 4: Performance

**Risk**: Network calls to basset-verify may be slow

**Mitigation**:
- 5-second timeout
- Connection pooling
- Result caching in basset-hound
- Async/await throughout

---

## 14. Success Criteria

Phase 42 is successful if:

1. ✅ basset-verify repository created with clear scope
2. [ ] All 12 verification tools work in basset-verify independently
3. [ ] basset-hound gracefully degrades when basset-verify is down
4. [ ] All tests pass (>90% coverage)
5. [ ] Docker deployment works for both services
6. [ ] Integration testing passes all scenarios
7. [ ] Tool count updated: basset-hound 112 → 100, basset-verify 0 → 12
8. [ ] Documentation complete and clear
9. [ ] Manual verification flow works end-to-end
10. [ ] .onion addresses handled correctly (no automatic verification)

---

## 15. Related Documents

- [basset-hound SCOPE.md](/home/devel/basset-hound/docs/SCOPE.md) - Intelligence management scope
- [basset-verify SCOPE.md](/home/devel/basset-verify/docs/SCOPE.md) - Verification scope
- [basset-verify README.md](/home/devel/basset-verify/README.md) - Project overview
- [basset-verify ROADMAP.md](/home/devel/basset-verify/docs/ROADMAP.md) - Development plan
- [Phase 40.5 Findings](/home/devel/basset-hound/docs/findings/MCP-PHASE40_5-2026-01-07.md) - Original verification implementation

---

## 16. Next Steps

1. **Complete Phase 1 (Code Migration)**:
   - Migrate verification_service.py
   - Migrate crypto_detector.py
   - Update imports and paths
   - Migrate tests
   - Ensure tests pass

2. **Phase 2 (REST API)**:
   - Create FastAPI server
   - Implement verification endpoints
   - Add rate limiting

3. **Phase 3 (MCP Server)**:
   - Create FastMCP server
   - Implement 12 MCP tools
   - Add tool documentation

4. **Phase 7 (basset-hound Integration)**:
   - Create BassetVerifyClient
   - Remove verification tools from basset-hound
   - Implement graceful degradation
   - Update tool count

5. **Testing & Documentation**:
   - End-to-end testing
   - Update all documentation
   - Create integration guides

---

**Status:** Phase 42 in progress - Repository structure created, scope defined, roadmap developed
**Next Milestone:** Complete Phase 1 (Code Migration) by 2026-01-10
