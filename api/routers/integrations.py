"""
API Router for external service integrations.

Provides endpoints for checking status and interacting with external
microservices in the basset ecosystem, including basset-verify.
"""

import logging
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from api.clients.basset_verify_client import (
    BassetVerifyClient,
    get_basset_verify_client,
    VerificationResult,
    VerificationLevel,
    IdentifierType,
)

logger = logging.getLogger("basset_hound.integrations")


# =============================================================================
# Pydantic Models
# =============================================================================

class ServiceStatusResponse(BaseModel):
    """Response model for service status check."""
    service: str = Field(..., description="Service name")
    available: bool = Field(..., description="Whether the service is reachable")
    status: str = Field(..., description="Service status")
    version: Optional[str] = Field(None, description="Service version if available")
    timestamp: Optional[datetime] = Field(None, description="Status check timestamp")
    error_message: Optional[str] = Field(None, description="Error message if unavailable")


class VerifyEmailRequest(BaseModel):
    """Request model for email verification."""
    email: str = Field(..., description="Email address to verify", min_length=1)
    level: str = Field(
        default="format",
        description="Verification level (format, network)",
        pattern="^(format|network)$"
    )


class VerifyPhoneRequest(BaseModel):
    """Request model for phone verification."""
    phone: str = Field(..., description="Phone number to verify", min_length=1)
    level: str = Field(default="format", description="Verification level")
    default_region: str = Field(default="US", description="Default region code")


class VerifyCryptoRequest(BaseModel):
    """Request model for crypto address verification."""
    address: str = Field(..., description="Cryptocurrency address to verify")
    validate_checksum: bool = Field(default=True, description="Validate checksum")


class VerifyGenericRequest(BaseModel):
    """Request model for generic verification."""
    value: str = Field(..., description="Value to verify", min_length=1)
    type: str = Field(
        ...,
        description="Identifier type",
        pattern="^(email|phone|crypto_address|domain|ip_address|url|username)$"
    )
    level: str = Field(default="format", description="Verification level")


class BatchVerifyRequest(BaseModel):
    """Request model for batch verification."""
    items: list[dict[str, str]] = Field(
        ...,
        description="List of items with 'value' and 'type' keys",
        min_length=1,
    )
    level: str = Field(default="format", description="Verification level for all items")


class VerificationResponse(BaseModel):
    """Response model for verification results."""
    identifier_type: str
    identifier_value: str
    status: str
    verification_level: str
    is_valid: Optional[bool]
    confidence: float
    details: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    verified_at: Optional[datetime] = None
    allows_override: bool = True
    override_hint: Optional[str] = None


class BatchVerificationResponse(BaseModel):
    """Response model for batch verification."""
    results: list[VerificationResponse]
    count: int
    success: bool
    error_message: Optional[str] = None


# =============================================================================
# Router
# =============================================================================

router = APIRouter(prefix="/integrations", tags=["Integrations"])


def get_client() -> BassetVerifyClient:
    """Dependency to get basset-verify client."""
    return get_basset_verify_client()


# =============================================================================
# basset-verify Integration Endpoints
# =============================================================================

@router.get(
    "/basset-verify/status",
    response_model=ServiceStatusResponse,
    summary="Check basset-verify service status",
    description="Check if the basset-verify microservice is available and healthy.",
)
async def check_basset_verify_status(
    client: BassetVerifyClient = Depends(get_client),
) -> ServiceStatusResponse:
    """
    Check the health status of basset-verify service.

    Returns:
        ServiceStatusResponse with availability and version information
    """
    status = await client.health_check()

    return ServiceStatusResponse(
        service="basset-verify",
        available=status.available,
        status=status.status,
        version=status.version,
        timestamp=status.timestamp or datetime.utcnow(),
        error_message=status.error_message,
    )


@router.post(
    "/verify/email",
    response_model=VerificationResponse,
    summary="Verify email address via basset-verify",
    description="Forward email verification request to basset-verify microservice.",
)
async def verify_email(
    request: VerifyEmailRequest,
    client: BassetVerifyClient = Depends(get_client),
) -> VerificationResponse:
    """
    Verify an email address through basset-verify.

    This endpoint forwards the request to basset-verify and returns
    the verification result. If basset-verify is unavailable, returns
    a graceful degradation response.

    Args:
        request: Email verification request

    Returns:
        VerificationResponse with verification results
    """
    try:
        level = VerificationLevel(request.level)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid verification level: {request.level}"
        )

    result = await client.verify_email(request.email, level=level)

    return VerificationResponse(
        identifier_type=result.identifier_type,
        identifier_value=result.identifier_value,
        status=result.status,
        verification_level=result.verification_level,
        is_valid=result.is_valid,
        confidence=result.confidence,
        details=result.details,
        warnings=result.warnings,
        errors=result.errors,
        verified_at=result.verified_at,
        allows_override=result.allows_override,
        override_hint=result.override_hint,
    )


@router.post(
    "/verify/phone",
    response_model=VerificationResponse,
    summary="Verify phone number via basset-verify",
    description="Forward phone verification request to basset-verify microservice.",
)
async def verify_phone(
    request: VerifyPhoneRequest,
    client: BassetVerifyClient = Depends(get_client),
) -> VerificationResponse:
    """
    Verify a phone number through basset-verify.

    Args:
        request: Phone verification request

    Returns:
        VerificationResponse with verification results
    """
    try:
        level = VerificationLevel(request.level)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid verification level: {request.level}"
        )

    result = await client.verify_phone(
        request.phone,
        level=level,
        default_region=request.default_region,
    )

    return VerificationResponse(
        identifier_type=result.identifier_type,
        identifier_value=result.identifier_value,
        status=result.status,
        verification_level=result.verification_level,
        is_valid=result.is_valid,
        confidence=result.confidence,
        details=result.details,
        warnings=result.warnings,
        errors=result.errors,
        verified_at=result.verified_at,
        allows_override=result.allows_override,
        override_hint=result.override_hint,
    )


@router.post(
    "/verify/crypto",
    response_model=VerificationResponse,
    summary="Verify cryptocurrency address via basset-verify",
    description="Forward crypto verification request to basset-verify microservice.",
)
async def verify_crypto(
    request: VerifyCryptoRequest,
    client: BassetVerifyClient = Depends(get_client),
) -> VerificationResponse:
    """
    Verify a cryptocurrency address through basset-verify.

    Args:
        request: Crypto verification request

    Returns:
        VerificationResponse with verification results
    """
    result = await client.verify_crypto(
        request.address,
        validate_checksum=request.validate_checksum,
    )

    return VerificationResponse(
        identifier_type=result.identifier_type,
        identifier_value=result.identifier_value,
        status=result.status,
        verification_level=result.verification_level,
        is_valid=result.is_valid,
        confidence=result.confidence,
        details=result.details,
        warnings=result.warnings,
        errors=result.errors,
        verified_at=result.verified_at,
        allows_override=result.allows_override,
        override_hint=result.override_hint,
    )


@router.post(
    "/verify",
    response_model=VerificationResponse,
    summary="Verify any identifier via basset-verify",
    description="Forward generic verification request to basset-verify microservice.",
)
async def verify_generic(
    request: VerifyGenericRequest,
    client: BassetVerifyClient = Depends(get_client),
) -> VerificationResponse:
    """
    Verify any identifier type through basset-verify.

    Args:
        request: Generic verification request with value, type, and level

    Returns:
        VerificationResponse with verification results
    """
    try:
        identifier_type = IdentifierType(request.type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid identifier type: {request.type}"
        )

    try:
        level = VerificationLevel(request.level)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid verification level: {request.level}"
        )

    result = await client.verify(
        value=request.value,
        identifier_type=identifier_type,
        level=level,
    )

    return VerificationResponse(
        identifier_type=result.identifier_type,
        identifier_value=result.identifier_value,
        status=result.status,
        verification_level=result.verification_level,
        is_valid=result.is_valid,
        confidence=result.confidence,
        details=result.details,
        warnings=result.warnings,
        errors=result.errors,
        verified_at=result.verified_at,
        allows_override=result.allows_override,
        override_hint=result.override_hint,
    )


@router.post(
    "/verify/batch",
    response_model=BatchVerificationResponse,
    summary="Batch verify identifiers via basset-verify",
    description="Forward batch verification request to basset-verify microservice.",
)
async def verify_batch(
    request: BatchVerifyRequest,
    client: BassetVerifyClient = Depends(get_client),
) -> BatchVerificationResponse:
    """
    Verify multiple identifiers in batch through basset-verify.

    Args:
        request: Batch verification request with items list

    Returns:
        BatchVerificationResponse with all verification results
    """
    if len(request.items) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Batch size cannot exceed 100 items"
        )

    try:
        level = VerificationLevel(request.level)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid verification level: {request.level}"
        )

    result = await client.batch_verify(request.items, level=level)

    return BatchVerificationResponse(
        results=[
            VerificationResponse(
                identifier_type=r.identifier_type,
                identifier_value=r.identifier_value,
                status=r.status,
                verification_level=r.verification_level,
                is_valid=r.is_valid,
                confidence=r.confidence,
                details=r.details,
                warnings=r.warnings,
                errors=r.errors,
                verified_at=r.verified_at,
                allows_override=r.allows_override,
                override_hint=r.override_hint,
            )
            for r in result.results
        ],
        count=result.count,
        success=result.success,
        error_message=result.error_message,
    )


@router.get(
    "/basset-verify/types",
    summary="Get supported verification types",
    description="Get list of supported identifier types and verification levels from basset-verify.",
)
async def get_verification_types(
    client: BassetVerifyClient = Depends(get_client),
) -> dict[str, Any]:
    """
    Get supported identifier types and verification levels.

    Returns:
        Dict with identifier_types and verification_levels lists
    """
    return await client.get_verification_types()


@router.get(
    "/basset-verify/crypto/supported",
    summary="Get supported cryptocurrencies",
    description="Get list of supported cryptocurrencies from basset-verify.",
)
async def get_supported_cryptocurrencies(
    client: BassetVerifyClient = Depends(get_client),
) -> dict[str, Any]:
    """
    Get list of supported cryptocurrencies.

    Returns:
        Dict with cryptocurrencies list and count
    """
    return await client.get_supported_cryptocurrencies()


@router.get(
    "/basset-verify/crypto/matches/{address}",
    summary="Get all crypto matches for address",
    description="Get all possible cryptocurrency matches for an address from basset-verify.",
)
async def get_crypto_matches(
    address: str,
    client: BassetVerifyClient = Depends(get_client),
) -> dict[str, Any]:
    """
    Get all possible cryptocurrency matches for an address.

    Some addresses (like 0x...) could belong to multiple EVM chains.

    Args:
        address: Cryptocurrency address to analyze

    Returns:
        Dict with address, matches list, and count
    """
    return await client.get_crypto_matches(address)
