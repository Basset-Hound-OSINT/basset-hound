# Basset-Verify Integration

**Date**: 2026-01-13
**Status**: Implemented
**Author**: Claude Code

## Overview

This document describes the integration between basset-hound and basset-verify microservice for identifier verification. The integration enables basset-hound to validate identifiers (emails, phones, crypto addresses, etc.) through the basset-verify service while maintaining graceful degradation when the service is unavailable.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      basset-hound                                │
│                 (Intelligence Storage Layer)                     │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  FastAPI Application                       │  │
│  │                                                            │  │
│  │  ┌─────────────────────────────────────────────────────┐ │  │
│  │  │        /api/v1/integrations/* Endpoints             │ │  │
│  │  │                                                      │ │  │
│  │  │  GET  /basset-verify/status                         │ │  │
│  │  │  POST /verify/email                                  │ │  │
│  │  │  POST /verify/phone                                  │ │  │
│  │  │  POST /verify/crypto                                 │ │  │
│  │  │  POST /verify                                        │ │  │
│  │  │  POST /verify/batch                                  │ │  │
│  │  │  GET  /basset-verify/types                          │ │  │
│  │  │  GET  /basset-verify/crypto/supported               │ │  │
│  │  │  GET  /basset-verify/crypto/matches/{address}       │ │  │
│  │  └─────────────────────────────────────────────────────┘ │  │
│  │                          │                                 │  │
│  │                          ▼                                 │  │
│  │  ┌─────────────────────────────────────────────────────┐ │  │
│  │  │          BassetVerifyClient                          │ │  │
│  │  │          (api/clients/basset_verify_client.py)       │ │  │
│  │  │                                                      │ │  │
│  │  │  - Async HTTP client (httpx)                        │ │  │
│  │  │  - Configurable base URL                            │ │  │
│  │  │  - Timeout handling                                  │ │  │
│  │  │  - Graceful degradation                             │ │  │
│  │  │  - Connection pooling                               │ │  │
│  │  └─────────────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                               │
                               │ HTTP/REST
                               │ Default: http://localhost:8001
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      basset-verify                               │
│               (Identifier Verification Service)                  │
│                                                                  │
│  Endpoints Used:                                                 │
│  - GET  /health          Health check                           │
│  - POST /verify          Generic verification                   │
│  - POST /verify/email    Email verification                     │
│  - POST /verify/phone    Phone verification                     │
│  - POST /verify/crypto   Crypto address verification            │
│  - POST /verify/domain   Domain verification                    │
│  - POST /verify/ip       IP address verification                │
│  - POST /verify/url      URL verification                       │
│  - POST /verify/username Username verification                  │
│  - POST /verify/batch    Batch verification                     │
│  - GET  /types           Supported verification types           │
│  - GET  /crypto/supported Supported cryptocurrencies            │
│  - GET  /crypto/matches/{addr} All crypto matches               │
└─────────────────────────────────────────────────────────────────┘
```

## Components Created

### 1. BassetVerifyClient (`api/clients/basset_verify_client.py`)

Async HTTP client for communicating with basset-verify.

**Features**:
- Async context manager support
- Configurable base URL (default: `http://localhost:8001`)
- Configurable timeout (default: 10 seconds)
- Graceful degradation when service unavailable
- Connection pooling via httpx
- Type-safe with dataclasses and enums

**Key Classes**:
```python
class VerificationLevel(str, Enum):
    FORMAT = "format"
    NETWORK = "network"
    EXTERNAL_API = "external_api"

class IdentifierType(str, Enum):
    EMAIL = "email"
    PHONE = "phone"
    CRYPTO_ADDRESS = "crypto_address"
    DOMAIN = "domain"
    IP_ADDRESS = "ip_address"
    URL = "url"
    USERNAME = "username"

@dataclass
class VerificationResult:
    identifier_type: str
    identifier_value: str
    status: str
    verification_level: str
    is_valid: Optional[bool]
    confidence: float
    details: dict[str, Any]
    warnings: list[str]
    errors: list[str]
    verified_at: Optional[datetime]
    allows_override: bool
    override_hint: Optional[str]
```

**Usage Example**:
```python
from api.clients import BassetVerifyClient

async with BassetVerifyClient() as client:
    # Check service health
    status = await client.health_check()

    if status.available:
        # Verify email
        result = await client.verify_email("test@example.com")
        print(f"Valid: {result.is_valid}, Confidence: {result.confidence}")
    else:
        print(f"Service unavailable: {status.error_message}")
```

### 2. Integrations Router (`api/routers/integrations.py`)

FastAPI router providing REST endpoints for basset-verify integration.

**Endpoints**:

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/integrations/basset-verify/status` | Check basset-verify service health |
| POST | `/api/v1/integrations/verify/email` | Verify email address |
| POST | `/api/v1/integrations/verify/phone` | Verify phone number |
| POST | `/api/v1/integrations/verify/crypto` | Verify cryptocurrency address |
| POST | `/api/v1/integrations/verify` | Verify any identifier type |
| POST | `/api/v1/integrations/verify/batch` | Batch verify multiple identifiers |
| GET | `/api/v1/integrations/basset-verify/types` | Get supported verification types |
| GET | `/api/v1/integrations/basset-verify/crypto/supported` | Get supported cryptocurrencies |
| GET | `/api/v1/integrations/basset-verify/crypto/matches/{address}` | Get all crypto matches |

### 3. Integration Tests (`tests/integration/test_basset_verify_integration.py`)

Comprehensive test suite for the integration.

**Test Categories**:
1. **Health Check Tests** - Connection and availability testing
2. **Email Verification Tests** - Email format and MX lookup
3. **Phone Verification Tests** - International phone parsing
4. **Crypto Verification Tests** - Bitcoin, Ethereum, and other currencies
5. **Graceful Degradation Tests** - Behavior when service unavailable
6. **Batch Verification Tests** - Multiple identifier verification
7. **Result Storage Tests** - Serialization and deserialization

## Error Handling Strategy

### Graceful Degradation

When basset-verify is unavailable, the client returns a special "unavailable" result:

```python
{
    "identifier_type": "email",
    "identifier_value": "test@example.com",
    "status": "verification_unavailable",
    "verification_level": "none",
    "is_valid": null,
    "confidence": 0.0,
    "details": {},
    "warnings": ["basset-verify service is unavailable"],
    "errors": [],
    "verified_at": "2026-01-13T12:00:00Z",
    "allows_override": true,
    "override_hint": "Verification service unavailable. Manual verification recommended."
}
```

### Error Types Handled

| Error Type | Handling |
|------------|----------|
| `httpx.ConnectError` | Return unavailable result with error message |
| `httpx.TimeoutException` | Return unavailable result with timeout message |
| `httpx.HTTPStatusError` | Return error result with HTTP status code |
| General exceptions | Return error result with exception message |

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BASSET_VERIFY_URL` | `http://localhost:8001` | Base URL for basset-verify service |
| `BASSET_VERIFY_TIMEOUT` | `10.0` | Request timeout in seconds |

### Client Configuration

```python
# Custom configuration
client = BassetVerifyClient(
    base_url="http://custom-host:8001",
    timeout=30.0,
    max_retries=5,
)
```

## API Request/Response Examples

### Email Verification

**Request**:
```bash
curl -X POST http://localhost:8000/api/v1/integrations/verify/email \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "level": "format"}'
```

**Response (success)**:
```json
{
    "identifier_type": "email",
    "identifier_value": "test@example.com",
    "status": "plausible",
    "verification_level": "format",
    "is_valid": true,
    "confidence": 0.7,
    "details": {
        "local_part": "test",
        "domain": "example.com",
        "has_plus_addressing": false,
        "is_disposable": false
    },
    "warnings": [],
    "errors": [],
    "verified_at": "2026-01-13T12:00:00Z",
    "allows_override": true,
    "override_hint": null
}
```

**Response (service unavailable)**:
```json
{
    "identifier_type": "email",
    "identifier_value": "test@example.com",
    "status": "verification_unavailable",
    "verification_level": "none",
    "is_valid": null,
    "confidence": 0.0,
    "details": {},
    "warnings": ["Service unavailable: Connection refused"],
    "errors": [],
    "verified_at": "2026-01-13T12:00:00Z",
    "allows_override": true,
    "override_hint": "Verification service unavailable. Manual verification recommended."
}
```

### Batch Verification

**Request**:
```bash
curl -X POST http://localhost:8000/api/v1/integrations/verify/batch \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
        {"value": "test@example.com", "type": "email"},
        {"value": "+1234567890", "type": "phone"},
        {"value": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", "type": "crypto_address"}
    ],
    "level": "format"
}'
```

**Response**:
```json
{
    "results": [
        {"identifier_type": "email", "status": "plausible", ...},
        {"identifier_type": "phone", "status": "valid", ...},
        {"identifier_type": "crypto_address", "status": "valid", ...}
    ],
    "count": 3,
    "success": true,
    "error_message": null
}
```

## Test Results

### Running Tests

```bash
# Run all integration tests
cd ~/basset-hound
pytest tests/integration/test_basset_verify_integration.py -v

# Run with basset-verify (start service first)
cd ~/basset-verify && python -m basset_verify.server &
pytest tests/integration/test_basset_verify_integration.py -v

# Run specific test categories
pytest tests/integration/test_basset_verify_integration.py -v -k "TestHealthCheck"
pytest tests/integration/test_basset_verify_integration.py -v -k "TestGracefulDegradation"
```

### Test Coverage

| Test Class | Tests | Purpose |
|------------|-------|---------|
| `TestHealthCheck` | 3 | Connection and health check |
| `TestEmailVerification` | 4 | Email verification scenarios |
| `TestPhoneVerification` | 4 | Phone verification scenarios |
| `TestCryptoVerification` | 6 | Crypto address verification |
| `TestGracefulDegradation` | 3 | Service unavailability handling |
| `TestBatchVerification` | 4 | Batch verification |
| `TestVerificationResultStorage` | 3 | Result serialization |
| `TestGenericVerify` | 3 | Generic verify method |
| `TestAdditionalVerificationTypes` | 6 | Domain, IP, URL, username |
| `TestClientLifecycle` | 3 | Client resource management |
| `TestErrorHandling` | 3 | Error handling scenarios |
| `TestVerificationTypesEndpoint` | 1 | Metadata endpoint |

## Security Considerations

1. **No Credential Storage**: The client does not store or log sensitive credentials
2. **Timeout Protection**: Configurable timeouts prevent hanging requests
3. **Rate Limiting**: basset-verify enforces rate limits (100 req/min per IP)
4. **Input Validation**: Request validation via Pydantic models
5. **Error Sanitization**: Error messages do not expose internal details

## Future Enhancements

1. **Caching**: Add caching layer for repeated verification requests
2. **Circuit Breaker**: Implement circuit breaker pattern for better resilience
3. **Metrics**: Add Prometheus metrics for monitoring
4. **Retry Policy**: Configurable retry with exponential backoff
5. **Connection Pool**: Tune connection pool settings for high traffic

## Files Created/Modified

### New Files
- `api/clients/__init__.py` - Client module exports
- `api/clients/basset_verify_client.py` - Main client implementation
- `api/routers/integrations.py` - Integration endpoints
- `tests/integration/test_basset_verify_integration.py` - Integration tests
- `docs/findings/BASSET-VERIFY-INTEGRATION-2026-01-13.md` - This document

### Modified Files
- `api/routers/__init__.py` - Added integrations_router import and registration

## Related Documentation

- [basset-verify README](~/basset-verify/README.md) - basset-verify service documentation
- [basset-verify API](~/basset-verify/docs/API.md) - Full API reference
- [Integration Guide](~/basset-verify/docs/INTEGRATION.md) - Integration patterns
