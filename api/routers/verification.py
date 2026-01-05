"""
Data Verification API endpoints for Basset Hound.

Provides REST API endpoints for verifying identifier data before
ingestion. Supports format validation, network verification, and
external API verification for emails, phones, domains, IPs, URLs,
crypto addresses, and usernames.

These endpoints are designed to be called by:
- The browser extension (autofill-extension) before data ingestion
- The basset-hound-browser agent for automated verification
- MCP tools for AI-assisted OSINT investigations
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, ConfigDict

from api.models.orphan import IdentifierType
from api.services.verification_service import (
    VerificationLevel,
    VerificationResult,
    VerificationService,
    VerificationStatus,
    get_verification_service,
)


router = APIRouter(prefix="/verify", tags=["Verification"])


# =============================================================================
# Request/Response Models
# =============================================================================


class VerifyRequest(BaseModel):
    """Request model for single identifier verification."""

    value: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="The identifier value to verify",
    )
    identifier_type: str = Field(
        ...,
        description="Type of identifier (email, phone, domain, ip_address, url, crypto_address, username)",
    )
    level: Optional[str] = Field(
        default="format",
        description="Verification level: 'format' (syntax only), 'network' (DNS/MX), 'external' (API verification)",
    )


class VerifyResponse(BaseModel):
    """Response model for verification results."""

    model_config = ConfigDict(from_attributes=True)

    identifier_type: str = Field(..., description="Type of identifier verified")
    identifier_value: str = Field(..., description="The value that was verified")
    status: str = Field(
        ...,
        description="Verification status: valid, invalid, plausible, unverifiable, error",
    )
    verification_level: str = Field(
        ..., description="Level of verification performed"
    )
    is_valid: bool = Field(..., description="Whether the identifier is valid")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score (0.0 to 1.0)"
    )
    details: dict = Field(default_factory=dict, description="Additional verification details")
    warnings: List[str] = Field(default_factory=list, description="Warning messages")
    errors: List[str] = Field(default_factory=list, description="Error messages")
    verified_at: str = Field(..., description="ISO timestamp of verification")
    # User override advisory fields
    allows_override: bool = Field(
        default=True,
        description="Whether user can override this verification result"
    )
    override_hint: Optional[str] = Field(
        default=None,
        description="Hint explaining when override might be appropriate"
    )


class BatchVerifyRequest(BaseModel):
    """Request model for batch verification."""

    items: List[VerifyRequest] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="List of identifiers to verify (max 100)",
    )


class BatchVerifyResponse(BaseModel):
    """Response model for batch verification."""

    count: int = Field(..., description="Total number of items verified")
    valid_count: int = Field(..., description="Number of valid identifiers")
    invalid_count: int = Field(..., description="Number of invalid identifiers")
    results: List[VerifyResponse] = Field(..., description="Verification results")


class SupportedTypesResponse(BaseModel):
    """Response model for supported verification types."""

    types: List[str] = Field(..., description="List of supported identifier types")
    levels: List[str] = Field(..., description="List of supported verification levels")


# =============================================================================
# Helper Functions
# =============================================================================


def _result_to_response(result: VerificationResult) -> VerifyResponse:
    """Convert a VerificationResult to a VerifyResponse."""
    return VerifyResponse(
        identifier_type=result.identifier_type,
        identifier_value=result.identifier_value,
        status=result.status.value,
        verification_level=result.verification_level.value,
        is_valid=result.is_valid,
        confidence=result.confidence,
        details=result.details,
        warnings=result.warnings,
        errors=result.errors,
        verified_at=result.verified_at.isoformat(),
        allows_override=result.allows_override,
        override_hint=result.override_hint,
    )


def _parse_level(level_str: Optional[str]) -> VerificationLevel:
    """Parse verification level string to enum."""
    if not level_str:
        return VerificationLevel.FORMAT

    level_map = {
        "none": VerificationLevel.NONE,
        "format": VerificationLevel.FORMAT,
        "network": VerificationLevel.NETWORK,
        "external": VerificationLevel.EXTERNAL_API,
    }
    return level_map.get(level_str.lower(), VerificationLevel.FORMAT)


# =============================================================================
# Endpoints
# =============================================================================


@router.get(
    "/types",
    response_model=SupportedTypesResponse,
    summary="List supported verification types",
    description="Returns the list of supported identifier types and verification levels.",
)
async def get_supported_types() -> SupportedTypesResponse:
    """Get list of supported identifier types and verification levels."""
    return SupportedTypesResponse(
        types=[t.value for t in IdentifierType],
        levels=[l.value for l in VerificationLevel],
    )


@router.post(
    "",
    response_model=VerifyResponse,
    summary="Verify a single identifier",
    description="Verifies a single identifier value and returns validation results.",
)
async def verify_identifier(request: VerifyRequest) -> VerifyResponse:
    """
    Verify a single identifier.

    Performs format validation and optionally network/external verification
    based on the requested level.

    Returns verification status, confidence score, and detailed results.
    """
    service = get_verification_service()
    level = _parse_level(request.level)

    result = await service.verify(
        request.value,
        request.identifier_type,
        level,
    )

    return _result_to_response(result)


@router.post(
    "/batch",
    response_model=BatchVerifyResponse,
    summary="Verify multiple identifiers",
    description="Verifies up to 100 identifiers in a single request.",
)
async def batch_verify(request: BatchVerifyRequest) -> BatchVerifyResponse:
    """
    Verify multiple identifiers in batch.

    Efficiently processes up to 100 identifiers in parallel.
    Returns aggregated results with counts.
    """
    service = get_verification_service()

    items = [
        {"value": item.value, "type": item.identifier_type}
        for item in request.items
    ]

    # Use the first item's level or default
    level = _parse_level(request.items[0].level if request.items else None)

    results = await service.batch_verify(items, level)

    responses = [_result_to_response(r) for r in results]
    valid_count = sum(1 for r in results if r.is_valid)

    return BatchVerifyResponse(
        count=len(results),
        valid_count=valid_count,
        invalid_count=len(results) - valid_count,
        results=responses,
    )


@router.post(
    "/email",
    response_model=VerifyResponse,
    summary="Verify email address",
    description="Specialized endpoint for email verification with MX lookup support.",
)
async def verify_email(
    email: str,
    level: Optional[str] = "format",
) -> VerifyResponse:
    """
    Verify an email address.

    Performs:
    - Format validation (RFC 5322)
    - Disposable domain detection
    - Typo detection
    - MX record lookup (if level=network or level=external)

    Args:
        email: Email address to verify.
        level: Verification level (format, network, external).

    Returns:
        Verification result with confidence and details.
    """
    service = get_verification_service()
    result = await service.verify_email(email, _parse_level(level))
    return _result_to_response(result)


@router.post(
    "/phone",
    response_model=VerifyResponse,
    summary="Verify phone number",
    description="Specialized endpoint for phone number verification.",
)
async def verify_phone(
    phone: str,
    level: Optional[str] = "format",
) -> VerifyResponse:
    """
    Verify a phone number.

    Performs:
    - E.164 format validation
    - Country code extraction
    - Digit count validation

    Args:
        phone: Phone number to verify.
        level: Verification level.

    Returns:
        Verification result with confidence and details.
    """
    service = get_verification_service()
    result = await service.verify_phone(phone, _parse_level(level))
    return _result_to_response(result)


@router.post(
    "/domain",
    response_model=VerifyResponse,
    summary="Verify domain name",
    description="Specialized endpoint for domain verification with DNS lookup.",
)
async def verify_domain(
    domain: str,
    level: Optional[str] = "format",
) -> VerifyResponse:
    """
    Verify a domain name.

    Performs:
    - Domain format validation
    - TLD extraction
    - DNS resolution (if level=network or level=external)

    Args:
        domain: Domain name to verify.
        level: Verification level.

    Returns:
        Verification result with confidence and details.
    """
    service = get_verification_service()
    result = await service.verify_domain(domain, _parse_level(level))
    return _result_to_response(result)


@router.post(
    "/ip",
    response_model=VerifyResponse,
    summary="Verify IP address",
    description="Specialized endpoint for IP address verification.",
)
async def verify_ip(ip: str) -> VerifyResponse:
    """
    Verify an IP address.

    Performs:
    - IPv4/IPv6 format validation
    - Private/loopback/reserved range detection

    Args:
        ip: IP address to verify.

    Returns:
        Verification result with confidence and details.
    """
    service = get_verification_service()
    result = await service.verify_ip(ip)
    return _result_to_response(result)


@router.post(
    "/url",
    response_model=VerifyResponse,
    summary="Verify URL",
    description="Specialized endpoint for URL verification.",
)
async def verify_url(url: str) -> VerifyResponse:
    """
    Verify a URL.

    Performs:
    - URL format validation
    - Scheme/domain/path extraction

    Args:
        url: URL to verify.

    Returns:
        Verification result with confidence and details.
    """
    service = get_verification_service()
    result = await service.verify_url(url)
    return _result_to_response(result)


@router.post(
    "/crypto",
    response_model=VerifyResponse,
    summary="Verify cryptocurrency address",
    description="Specialized endpoint for crypto address verification with coin detection.",
)
async def verify_crypto(address: str) -> VerifyResponse:
    """
    Verify a cryptocurrency address.

    Performs:
    - Pattern matching for 20+ cryptocurrencies
    - Coin type detection (BTC, ETH, LTC, etc.)
    - Network detection (mainnet/testnet)
    - Block explorer URL generation

    Args:
        address: Cryptocurrency address to verify.

    Returns:
        Verification result with coin details and explorer URL.
    """
    service = get_verification_service()
    result = await service.verify_crypto(address)
    return _result_to_response(result)


@router.post(
    "/username",
    response_model=VerifyResponse,
    summary="Verify username/handle",
    description="Specialized endpoint for username verification.",
)
async def verify_username(username: str) -> VerifyResponse:
    """
    Verify a username or social media handle.

    Performs:
    - Username format validation
    - @ prefix handling

    Args:
        username: Username to verify.

    Returns:
        Verification result with confidence.
    """
    service = get_verification_service()
    result = await service.verify_username(username)
    return _result_to_response(result)
