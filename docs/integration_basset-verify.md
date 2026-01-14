# basset-hound ↔ basset-verify Integration

**Status**: ✅ COMPLETE
**Last Updated**: 2026-01-14
**Integration Type**: Service Client (basset-hound calls basset-verify)

---

## Overview

basset-hound integrates with basset-verify for identifier verification. This is an **optional** integration - basset-hound functions fully without basset-verify (graceful degradation).

### Integration Direction

```
┌─────────────────┐         HTTP/REST          ┌─────────────────┐
│  basset-hound   │  ──────────────────────►   │  basset-verify  │
│  (Primary)      │         Port 8001          │  (Secondary)    │
│  Port 8000      │  ◄──────────────────────   │                 │
└─────────────────┘      JSON Responses        └─────────────────┘
```

---

## Scope

### In Scope

| Feature | Status | Description |
|---------|--------|-------------|
| Email verification | ✅ Complete | Forward to basset-verify |
| Phone verification | ✅ Complete | Forward to basset-verify |
| Crypto verification | ✅ Complete | Forward to basset-verify |
| Domain verification | ✅ Complete | Forward to basset-verify |
| IP verification | ✅ Complete | Forward to basset-verify |
| URL verification | ✅ Complete | Forward to basset-verify |
| Username verification | ✅ Complete | Forward to basset-verify |
| Batch verification | ✅ Complete | Forward to basset-verify |
| Health check | ✅ Complete | Check basset-verify availability |
| Graceful degradation | ✅ Complete | Return `verification_unavailable` when down |

### Out of Scope

- Automatic verification (user must click "Verify")
- Storing verification results in basset-hound (caller's responsibility)
- Caching verification results (future enhancement)

---

## Implementation

### Client Location

```
basset-hound/
├── api/
│   ├── clients/
│   │   ├── __init__.py
│   │   └── basset_verify_client.py    # ✅ Implemented
│   └── routers/
│       └── integrations.py             # ✅ Implemented
└── tests/
    └── integration/
        └── test_basset_verify_integration.py  # ✅ 43 tests
```

### Client Features

- Async HTTP client using `httpx`
- Configurable base URL (default: `http://localhost:8001`)
- Configurable timeout (default: 10 seconds)
- Graceful degradation when service unavailable
- Context manager support for connection pooling

### API Endpoints Added

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/integrations/basset-verify/status` | GET | Health check |
| `/api/v1/integrations/verify/email` | POST | Email verification |
| `/api/v1/integrations/verify/phone` | POST | Phone verification |
| `/api/v1/integrations/verify/crypto` | POST | Crypto verification |
| `/api/v1/integrations/verify` | POST | Generic verification |
| `/api/v1/integrations/verify/batch` | POST | Batch verification |
| `/api/v1/integrations/basset-verify/types` | GET | Supported types |
| `/api/v1/integrations/basset-verify/crypto/supported` | GET | Supported cryptos |
| `/api/v1/integrations/basset-verify/crypto/matches/{address}` | GET | Crypto matches |

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BASSET_VERIFY_URL` | `http://localhost:8001` | basset-verify base URL |
| `BASSET_VERIFY_TIMEOUT` | `10` | Request timeout (seconds) |

### Code Configuration

```python
from api.clients import BassetVerifyClient

# Default configuration
client = BassetVerifyClient()

# Custom configuration
client = BassetVerifyClient(
    base_url="http://basset-verify:8001",
    timeout=30.0
)
```

---

## Graceful Degradation

When basset-verify is unavailable, the client returns:

```python
VerificationResult(
    identifier_type="email",
    identifier_value="user@example.com",
    is_valid=None,  # Unknown
    confidence=0.0,
    status="verification_unavailable",
    level="none",
    warnings=["Verification service unavailable"],
    allows_override=True,
    override_hint="Service unavailable - manual verification recommended"
)
```

This allows the UI to show "Verification unavailable - verify manually" rather than failing.

---

## Testing

### Test File

`tests/integration/test_basset_verify_integration.py` - 43 tests

### Test Categories

| Category | Tests | Description |
|----------|-------|-------------|
| Connection | 3 | Health check, availability |
| Email | 5 | Valid/invalid email verification |
| Phone | 4 | Valid/invalid phone verification |
| Crypto | 4 | Valid/invalid crypto verification |
| Graceful Degradation | 8 | All types when service down |
| Batch | 3 | Batch verification |
| Client Lifecycle | 4 | Context manager, connection pooling |
| Error Handling | 6 | Timeouts, HTTP errors |
| Types Endpoint | 6 | Metadata endpoints |

### Running Tests

```bash
# All integration tests
pytest tests/integration/test_basset_verify_integration.py -v

# Just graceful degradation tests
pytest tests/integration/test_basset_verify_integration.py -v -k "degradation"
```

---

## Usage Examples

### Basic Verification

```python
from api.clients import get_basset_verify_client

async def verify_email(email: str):
    async with get_basset_verify_client() as client:
        result = await client.verify_email(email)
        if result.status == "verification_unavailable":
            return "Service unavailable - verify manually"
        return f"Valid: {result.is_valid}, Confidence: {result.confidence}"
```

### Batch Verification

```python
async def verify_batch(identifiers: list):
    async with get_basset_verify_client() as client:
        results = await client.batch_verify(identifiers)
        return results
```

### Health Check

```python
async def check_basset_verify():
    async with get_basset_verify_client() as client:
        return await client.health_check()
```

---

## Findings

Integration findings documented in:
- `docs/findings/basset-verify-integration/`
- `docs/findings/BASSET-VERIFY-INTEGRATION-2026-01-13.md`

---

## Suggestions for basset-verify

Suggestions for basset-verify improvements are tracked in:
- `~/basset-verify/docs/suggestions_basset-hound/`

---

## Completion Checklist

- [x] Client implemented (`api/clients/basset_verify_client.py`)
- [x] Router implemented (`api/routers/integrations.py`)
- [x] Tests implemented (43 tests)
- [x] Graceful degradation working
- [x] Documentation complete
- [x] Health check working
- [ ] Caching layer (future enhancement)
- [ ] Retry with backoff (future enhancement)
