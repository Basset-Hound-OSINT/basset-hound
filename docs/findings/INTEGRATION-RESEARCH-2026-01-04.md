# Integration Research Findings - Basset Hound

**Date:** January 4, 2026
**Purpose:** Document integration strategies for the Basset Hound ecosystem

---

## Overview

This document outlines research findings for integrating three independent OSINT projects:
1. **basset-hound** - Entity relationship engine (graph database backend)
2. **autofill-extension** - Chrome browser automation extension
3. **basset-hound-browser** - Electron-based automation browser

---

## Integration Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                        OSINT INVESTIGATION ECOSYSTEM                         │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌─────────────────────┐     ┌─────────────────────┐                       │
│   │  autofill-extension │     │ basset-hound-browser│                       │
│   │    (Chrome MV3)     │     │     (Electron)       │                       │
│   │                     │     │                      │                       │
│   │  - Data field       │     │  - Automated browsing│                       │
│   │    detection        │     │  - Bot evasion       │                       │
│   │  - Ingest button    │     │  - Screenshots       │                       │
│   │  - Screenshots      │     │  - Tor integration   │                       │
│   │  - Element selection│     │  - Session recording │                       │
│   └──────────┬──────────┘     └───────────┬─────────┘                       │
│              │                             │                                 │
│              │      WebSocket/API          │                                 │
│              │                             │                                 │
│              └──────────────┬──────────────┘                                 │
│                             │                                                │
│                             ▼                                                │
│              ┌─────────────────────────────┐                                │
│              │       basset-hound          │                                │
│              │    (Entity Relationship     │                                │
│              │         Engine)             │                                │
│              │                             │                                │
│              │  - Store orphan data        │                                │
│              │  - Track data provenance    │                                │
│              │  - Verify identifiers       │                                │
│              │  - Auto-link entities       │                                │
│              │  - Graph analysis           │                                │
│              └─────────────────────────────┘                                │
│                             │                                                │
│                             │ MCP/API                                        │
│                             ▼                                                │
│              ┌─────────────────────────────┐                                │
│              │       OSINT Agent           │                                │
│              │   (palletAI or LLM-based)   │                                │
│              │                             │                                │
│              │  - Automated investigations │                                │
│              │  - Pattern discovery        │                                │
│              │  - Report generation        │                                │
│              └─────────────────────────────┘                                │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Key Integration Requirements from User

### 1. Data Provenance Tracking

**Requirement:** Track where data comes from - human operator entry OR website (URL + date)

**Implementation in basset-hound:**
- Already supports `source` metadata on orphan data
- Enhance to include structured provenance:

```python
# Proposed DataProvenance model
class DataProvenance(BaseModel):
    source_type: Literal["human_entry", "website", "api", "import"]
    source_url: Optional[str] = None
    source_date: datetime
    captured_by: Literal["autofill-extension", "basset-hound-browser", "api", "manual"]
    confidence: float = 1.0  # How confident are we in this data
    verification_status: Literal["unverified", "format_valid", "verified", "failed"]
```

**Files to modify:**
- `/api/models/orphan.py` - Add provenance fields
- `/api/services/orphan_service.py` - Track provenance on create
- `/api/routers/orphan.py` - Accept provenance in API

### 2. Data Verification Service

**Requirement:** Verify plausibility of crypto addresses, emails, phones, domains

**Research Findings:**

#### Cryptocurrency Address Validation
- **Client-side:** Use `wallet-address-validator` (supports 100+ coins)
- **Server-side:** Use blockchain APIs (Blockstream, Etherscan, Mempool.space)
- **Current state:** basset-hound has `crypto_detector.py` with 30+ coin detection
- **Enhancement needed:** Add existence verification via blockchain APIs

```python
# Proposed VerificationService
class VerificationService:
    async def verify_crypto(self, address: str) -> VerificationResult:
        """Verify crypto address format AND check blockchain existence."""
        pass

    async def verify_email(self, email: str) -> VerificationResult:
        """Validate format, check MX records, optionally SMTP verify."""
        pass

    async def verify_phone(self, phone: str) -> VerificationResult:
        """Parse with libphonenumber, validate format by country."""
        pass

    async def verify_domain(self, domain: str) -> VerificationResult:
        """Check DNS records, WHOIS/RDAP lookup."""
        pass
```

#### Email Verification
- **Format validation:** RFC 5322 regex
- **MX record lookup:** `dns.resolver` in Python
- **SMTP verification:** Available but rate-limited
- **Libraries:** `email-validator`, `dnspython`

#### Phone Verification
- **Primary library:** `phonenumbers` (Python port of Google's libphonenumber)
- **Features:** Format validation, country detection, carrier lookup
- **Plausibility checks:** Not all same digit, not sequential

#### Domain/WHOIS Verification
- **RDAP (modern):** `rdap.org` - structured JSON responses
- **WHOIS (legacy):** `python-whois` library
- **DNS checks:** A, AAAA, MX, NS, TXT records

### 3. Autofill Extension Ingestion

**Requirement:**
- Auto-detect data fields on web pages
- "Ingest" button to send data to basset-hound
- Capture full URL and date
- Allow manual element selection and screenshot

**Current state in autofill-extension:**
- Already has data normalization (`utils/data-pipeline/normalizer.js`)
- Already has basset-hound sync (`utils/data-pipeline/basset-hound-sync.js`)
- Has entity manager (`utils/data-pipeline/entity-manager.js`)
- Has screenshot capabilities

**Enhancement needed:**
- Add data provenance capture (URL, timestamp)
- Add verification before ingest
- Integrate with basset-hound verification API

### 4. basset-hound-browser Integration

**Requirement:**
- OSINT agent uses basset-hound-browser for automated investigations
- Results stored in basset-hound

**Current state:**
- basset-hound-browser has WebSocket API (port 8765)
- Has technology detection, content extraction, network analysis
- Has Python/Node.js client libraries

**Integration pattern:**
```python
# OSINT Agent workflow
async def investigate(target: str):
    # 1. Use basset-hound-browser for automated browsing
    browser = BassetHoundBrowser()
    await browser.navigate(target)
    page_state = await browser.get_page_state()

    # 2. Extract identifiers
    emails = extract_emails(page_state)
    phones = extract_phones(page_state)

    # 3. Store in basset-hound as orphan data
    for email in emails:
        basset.create_orphan(
            identifier_type="EMAIL",
            value=email,
            provenance={
                "source_type": "website",
                "source_url": target,
                "source_date": datetime.now(),
                "captured_by": "basset-hound-browser"
            }
        )
```

---

## Data Verification Implementation Plan

### Phase 1: Format Validation (Client-side compatible)

```python
# api/services/verification/format_validators.py

def validate_email_format(email: str) -> bool:
    """RFC 5322 compliant email validation."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_phone_format(phone: str, country_hint: str = None) -> dict:
    """Parse and validate phone number format."""
    import phonenumbers
    try:
        parsed = phonenumbers.parse(phone, country_hint)
        return {
            "valid": phonenumbers.is_valid_number(parsed),
            "possible": phonenumbers.is_possible_number(parsed),
            "country": phonenumbers.region_code_for_number(parsed),
            "formatted": phonenumbers.format_number(
                parsed, phonenumbers.PhoneNumberFormat.E164
            )
        }
    except:
        return {"valid": False}

def validate_crypto_format(address: str) -> dict:
    """Checksum validation for crypto addresses."""
    # Use existing crypto_detector.py
    from api.utils.crypto_detector import detect_cryptocurrency
    return detect_cryptocurrency(address)
```

### Phase 2: DNS/Network Verification (Server-side)

```python
# api/services/verification/network_validators.py

import dns.resolver

async def verify_email_domain(email: str) -> dict:
    """Check if email domain has MX records."""
    domain = email.split('@')[1]
    try:
        mx_records = dns.resolver.resolve(domain, 'MX')
        return {
            "has_mx": True,
            "mx_count": len(mx_records),
            "primary_mx": str(sorted(mx_records, key=lambda x: x.preference)[0].exchange)
        }
    except:
        return {"has_mx": False}

async def verify_domain_exists(domain: str) -> dict:
    """Check if domain has DNS records."""
    result = {"exists": False, "has_a": False, "has_mx": False}
    try:
        dns.resolver.resolve(domain, 'A')
        result["exists"] = True
        result["has_a"] = True
    except:
        pass
    try:
        dns.resolver.resolve(domain, 'MX')
        result["has_mx"] = True
    except:
        pass
    return result
```

### Phase 3: Blockchain/External API Verification

```python
# api/services/verification/blockchain_validators.py

import httpx

async def verify_bitcoin_address(address: str) -> dict:
    """Check if Bitcoin address has blockchain activity."""
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                f"https://mempool.space/api/address/{address}",
                timeout=10.0
            )
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "exists": True,
                    "tx_count": data["chain_stats"]["tx_count"],
                    "balance_sat": data["chain_stats"]["funded_txo_sum"] -
                                   data["chain_stats"]["spent_txo_sum"]
                }
        except:
            pass
    return {"exists": False}
```

---

## API Endpoint Design

### New Verification Endpoints

```
POST /api/v1/verify/email
POST /api/v1/verify/phone
POST /api/v1/verify/crypto
POST /api/v1/verify/domain
POST /api/v1/verify/batch   # Multiple items at once
```

### Enhanced Orphan Endpoints

```
POST /api/v1/projects/{project}/orphans
  - Now accepts `provenance` object
  - Auto-verifies on creation (optional)
  - Blocks ingestion if verification fails (configurable)
```

---

## Dependencies to Add

**Python (basset-hound):**
```
phonenumbers>=8.13.0       # Phone number parsing
dnspython>=2.4.0           # DNS lookups
httpx>=0.27.0              # Async HTTP for blockchain APIs
python-whois>=0.9.0        # WHOIS lookups (optional)
```

**JavaScript (autofill-extension):**
```json
{
  "libphonenumber-js": "^1.10.0",
  "wallet-address-validator": "^0.2.4",
  "validator": "^13.9.0"
}
```

---

## Security Considerations

1. **Rate Limiting:** External API calls should be rate-limited
2. **Caching:** Cache verification results to avoid repeated lookups
3. **Privacy:** SMTP verification may reveal investigation intent
4. **WHOIS Privacy:** Many domains have privacy protection
5. **Blockchain APIs:** Use multiple providers for redundancy

---

## Recommended Implementation Order

1. **Add DataProvenance model to basset-hound** (Quick win)
2. **Add format validators** (No external dependencies)
3. **Add MX/DNS verification** (Reliable, server-side)
4. **Add blockchain verification** (External APIs, rate-limited)
5. **Update autofill-extension to send provenance** (Integration)
6. **OSINT agent integration** (Uses all above)

---

## Next Steps

See updated ROADMAP.md for implementation phases.
