# MCP Server Enhancement - Phase 40.5 Implementation

**Date:** 2026-01-08
**Phase:** 40.5 (Remaining MCP Tools)
**Status:** Completed

---

## Executive Summary

This document captures the implementation of Phase 40.5 MCP server enhancements, including sock puppet identity management and identifier verification tools. These tools complete the MCP server's capability to support full OSINT investigation workflows.

---

## 1. Sock Puppet Identity Management Tools

### Purpose

Sock puppets are specialized entity types for managing undercover/research identities in OSINT investigations. They are used by law enforcement, security researchers, and corporate investigators to:

- Observe targets on social platforms without detection
- Maintain separation between investigator identity and research activity
- Track the provenance of information gathered under cover
- Maintain audit trails for legal proceedings

### Key Design Decisions

**Storage Philosophy:** The sock puppet tools store **metadata and references only**, not actual credentials. Passwords, 2FA seeds, and recovery codes should be stored in external password managers (KeePass, HashiCorp Vault, etc.) with only reference strings stored in basset-hound.

**Entity Type:** Sock puppets are implemented as PERSON entities with a special `_sock_puppet` section in the profile, allowing them to inherit all standard person fields while adding operational metadata.

### Tools Implemented (15 total)

| Tool | Description |
|------|-------------|
| `create_sock_puppet` | Create new sock puppet identity |
| `get_sock_puppet` | Retrieve sock puppet by ID |
| `list_sock_puppets` | List with filtering (status, handler, purpose) |
| `activate_sock_puppet` | Set status to active for operational use |
| `deactivate_sock_puppet` | Set status to dormant |
| `burn_sock_puppet` | Mark as compromised (permanent) |
| `retire_sock_puppet` | Voluntarily decommission |
| `add_platform_account` | Add social media account to puppet |
| `update_platform_account` | Update account metadata |
| `record_puppet_activity` | Log activity for audit trail |
| `assign_handler` | Assign/change handler |
| `get_puppet_activity_log` | Get audit log with filtering |
| `assess_puppet_risk` | Automated risk assessment |

### Data Model

```python
_sock_puppet: {
    is_sock_puppet: True,
    alias_name: "Cover Identity Name",
    backstory: "Detailed cover story",
    birth_date: "1985-03-15",
    nationality: "US",
    occupation: "IT Consultant",
    location: {"city": "Seattle", "country": "US"},

    # Operational
    handler_id: "entity-uuid",
    operation_id: "investigation-uuid",
    purpose: "research",  # passive_surveillance, active_engagement, infiltration
    status: "active",     # planning, active, dormant, burned, retired
    risk_level: "low",    # low, medium, high, critical

    # Lifecycle
    created_date: "2026-01-08T10:00:00",
    activated_date: "2026-01-08T12:00:00",
    burn_date: "2026-07-08",  # Scheduled retirement
    burned_date: null,         # When compromised
    retirement_reason: null,
    last_activity: "2026-01-08T15:30:00",

    # Platform accounts
    platform_accounts: [
        {
            id: "uuid",
            platform: "linkedin",
            username: "cover-identity",
            email: "cover@protonmail.com",
            credential_vault_ref: "keepass://sock_puppets/cover",
            account_status: "active",
            last_login: "2026-01-08T14:00:00"
        }
    ],

    # Audit trail
    activity_log: [
        {timestamp: "...", action: "login", platform: "linkedin", details: {...}}
    ]
}
```

### Risk Assessment Algorithm

The `assess_puppet_risk` tool evaluates:

1. **Account Age vs Activity** - Flags accounts used too quickly after creation
2. **Burn Date Proximity** - Warns when retirement date is approaching
3. **Platform Account Status** - Flags suspended/banned accounts
4. **Missing Credential References** - Warns about accounts without vault refs

Risk scores: 0-14 (low), 15-29 (medium), 30-49 (high), 50+ (critical)

---

## 2. Verification Tools

### Purpose

Expose basset-hound's existing verification service infrastructure via MCP, allowing AI agents to validate identifiers during investigation workflows.

### Tools Implemented (12 total)

| Tool | Description |
|------|-------------|
| `get_verification_types` | List supported types and levels |
| `verify_identifier` | Generic verification routing |
| `verify_email` | Email validation + disposable detection |
| `verify_phone` | Phone validation + carrier detection |
| `verify_domain` | Domain validation + DNS resolution |
| `verify_ip` | IP validation + range detection |
| `verify_url` | URL parsing and validation |
| `verify_username` | Username format validation |
| `verify_crypto` | Cryptocurrency address detection |
| `get_all_crypto_matches` | All possible crypto matches |
| `batch_verify` | Batch verification (up to 100 items) |
| `get_supported_cryptocurrencies` | List 30+ supported coins |

### Verification Capabilities

**Email:**
- RFC 5322 format validation
- Disposable domain detection (500+ domains)
- Typo detection for common domains
- MX record verification (network level)

**Phone:**
- E.164 format validation
- Country/region detection
- Number type (mobile, landline, VOIP, toll-free)
- Carrier detection

**Crypto (30+ currencies):**
- Bitcoin (P2PKH, P2SH, Bech32, Taproot)
- Ethereum and 10+ EVM chains
- Litecoin, Dogecoin, Monero, Solana, Cardano
- Checksum validation (Base58Check, Bech32, EIP-55)
- Block explorer URL generation

**IP:**
- IPv4/IPv6 format validation
- Private range detection (RFC 1918)
- Loopback, link-local, reserved range detection

---

## 3. Entity Type Visualization

### Intent

Enable visual distinction of entity types in graph visualizations, similar to BloodHound's approach:

- Different node colors per entity type
- Entity type labels displayed as grayed text
- Quick visual reference for investigators

### Proposed Visual Schema

| Entity Type | Color | Icon | Use Case |
|-------------|-------|------|----------|
| PERSON | `#4A90D9` (blue) | user | Standard individuals |
| SOCK_PUPPET | `#9B59B6` (purple) | user-secret | Undercover identities |
| COMPANY | `#27AE60` (green) | building | Corporations |
| ORGANIZATION | `#E67E22` (orange) | sitemap | Groups, NGOs |

### Type Detection Logic

```python
def get_entity_type(entity):
    profile = entity.get("profile", {})

    # Check for sock puppet marker
    if profile.get("_sock_puppet", {}).get("is_sock_puppet"):
        return "SOCK_PUPPET"

    # Future: Check for company/organization markers
    # if profile.get("_entity_type") == "company":
    #     return "COMPANY"

    return "PERSON"
```

---

## 4. Updated Tool Count

| Module | Tool Count | Status |
|--------|-----------|--------|
| schema | 6 | Existing |
| entities | 6 | Enhanced (+query_entities) |
| relationships | 7 | Existing |
| search | 2 | Existing |
| projects | 3 | Existing |
| reports | 2 | Existing |
| analysis | 5 | Enhanced (+get_entity_graph) |
| auto_linking | 4 | Existing |
| **orphans** | **11** | Phase 40 |
| **provenance** | **8** | Phase 40 |
| **sock_puppets** | **15** | **Phase 40.5** |
| **verification** | **12** | **Phase 40.5** |
| **TOTAL** | **81** | +27 new tools |

---

## 5. Test Coverage

Created test suite: `tests/test_mcp_sock_puppets_verification.py`

**Test Classes:**
- `TestSockPuppetTools` - 8 tests for sock puppet management
- `TestVerificationTools` - 12 tests for identifier verification
- `TestEntityTypeVisualization` - 2 tests for graph visualization
- `TestIntegrationScenarios` - 3 tests for OSINT workflows

**Results:** 27 passed, 1 skipped (IPv6 not fully supported)

---

## 6. Files Changed

### New Files
- `basset_mcp/tools/sock_puppets.py` - Sock puppet management (15 tools)
- `basset_mcp/tools/verification.py` - Verification tools (12 tools)
- `tests/test_mcp_sock_puppets_verification.py` - Test suite
- `docs/findings/MCP-PHASE40.5-2026-01-08.md` - This document

### Modified Files
- `basset_mcp/tools/__init__.py` - Register new modules

---

## 7. Integration Notes

### For Law Enforcement Use

Sock puppets support:
- Case number association (`operation_id`)
- Handler assignment for accountability
- Full activity logging for court proceedings
- Risk assessment for operational security

### For AI Agents (palletai)

Agents can now:
1. Create and manage investigation identities
2. Verify discovered identifiers in real-time
3. Track which sock puppet collected which data (via provenance)
4. Assess operational risk before engaging targets

### Example Agent Workflow

```python
# 1. Verify discovered email
result = await mcp_client.call("verify_email", {
    "email": "target@example.com",
    "level": "network"  # Check MX records
})

if result["is_valid"]:
    # 2. Record as orphan data
    await mcp_client.call("create_orphan", {
        "project_id": "inv-001",
        "identifier_type": "email",
        "identifier_value": "target@example.com"
    })

# 3. Log observation using sock puppet
await mcp_client.call("record_puppet_activity", {
    "project_id": "inv-001",
    "puppet_id": "puppet-001",
    "platform": "linkedin",
    "activity_type": "profile_view",
    "details": {"target_profile": "linkedin.com/in/target"}
})
```

---

## 8. Future Considerations

### BloodHound-Style Visualization

The user expressed interest in graph visualization similar to BloodHound. Key features to consider:

1. **Node Styling:**
   - Entity type determines color and icon
   - Size based on connection count (centrality)
   - Glow/highlight for selected nodes

2. **Edge Styling:**
   - Relationship type determines line style
   - Confidence level affects opacity
   - Direction arrows for non-bidirectional relationships

3. **Layout:**
   - Force-directed for natural clustering
   - Hierarchical for investigation flow
   - Radial for ego-network views

### Next Phases

- **Phase 41:** Browser Integration APIs (autofill-extension, basset-hound-browser)
- **Phase 42:** Investigation management tools (workflow, milestones)
- **Phase 43:** Evidence collection with WARC archiving
