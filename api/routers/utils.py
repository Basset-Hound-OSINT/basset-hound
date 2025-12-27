"""
Utility API endpoints for Basset Hound.

Provides utility functions like cryptocurrency address detection,
data validation, and schema introspection.
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from api.utils.crypto_detector import (
    CryptoAddressDetector,
    CryptoDetectionResult,
    detect_crypto_address,
    detect_all_crypto_addresses,
)


router = APIRouter(prefix="/utils", tags=["Utilities"])


# =============================================================================
# Pydantic Models
# =============================================================================


class CryptoDetectionRequest(BaseModel):
    """Request model for crypto address detection."""

    address: str = Field(..., description="The cryptocurrency address to analyze")
    chain_hint: Optional[str] = Field(
        None,
        description="Optional chain hint for EVM addresses (e.g., 'ETH', 'BNB', 'MATIC')",
    )


class CryptoDetectionResponse(BaseModel):
    """Response model for crypto address detection."""

    address: str
    detected: bool
    coin_name: Optional[str] = None
    coin_ticker: Optional[str] = None
    network: Optional[str] = None
    address_type: Optional[str] = None
    confidence: float = 0.0
    explorer_url: Optional[str] = None


class CryptoMultiDetectionResponse(BaseModel):
    """Response model for detecting all possible cryptocurrencies."""

    address: str
    matches: List[CryptoDetectionResponse]
    best_match: Optional[CryptoDetectionResponse] = None


class SupportedCryptocurrency(BaseModel):
    """Model for supported cryptocurrency info."""

    coin_name: str
    coin_ticker: str


class SupportedCryptocurrenciesResponse(BaseModel):
    """Response model for listing supported cryptocurrencies."""

    count: int
    cryptocurrencies: List[SupportedCryptocurrency]


class BatchDetectionRequest(BaseModel):
    """Request model for batch crypto detection."""

    addresses: List[str] = Field(
        ...,
        description="List of cryptocurrency addresses to analyze",
        max_length=100,
    )


class BatchDetectionResponse(BaseModel):
    """Response model for batch crypto detection."""

    count: int
    results: List[CryptoDetectionResponse]


# =============================================================================
# API Endpoints
# =============================================================================


@router.post(
    "/detect-crypto",
    response_model=CryptoDetectionResponse,
    summary="Detect cryptocurrency type from address",
    description="""
Automatically detect the cryptocurrency type from a wallet address.

Supports 20+ major cryptocurrencies including:
- Bitcoin (BTC) - Legacy, SegWit, Bech32, Taproot
- Ethereum (ETH) and EVM-compatible chains
- Litecoin (LTC)
- Dogecoin (DOGE)
- Ripple/XRP
- Cardano (ADA)
- Solana (SOL)
- Monero (XMR)
- Tron (TRX)
- And many more...

The response includes:
- Detected coin name and ticker
- Network (mainnet/testnet)
- Address type (e.g., P2PKH, SegWit, etc.)
- Confidence score (0.0 to 1.0)
- Block explorer URL for verification
""",
)
async def detect_crypto(request: CryptoDetectionRequest) -> CryptoDetectionResponse:
    """Detect cryptocurrency type from a wallet address."""
    if not request.address or not request.address.strip():
        raise HTTPException(status_code=400, detail="Address cannot be empty")

    detector = CryptoAddressDetector()

    # If chain hint provided for EVM address, use specific detection
    if request.chain_hint:
        result = detector.detect_evm(request.address, request.chain_hint)
    else:
        result = detector.detect(request.address)

    return CryptoDetectionResponse(
        address=result.address,
        detected=result.detected,
        coin_name=result.coin_name,
        coin_ticker=result.coin_ticker,
        network=result.network,
        address_type=result.address_type,
        confidence=result.confidence,
        explorer_url=result.explorer_url,
    )


@router.get(
    "/detect-crypto/{address}",
    response_model=CryptoDetectionResponse,
    summary="Detect cryptocurrency type from address (GET)",
    description="Same as POST /detect-crypto but using GET with path parameter.",
)
async def detect_crypto_get(
    address: str,
    chain_hint: Optional[str] = Query(None, description="Optional chain hint for EVM addresses"),
) -> CryptoDetectionResponse:
    """Detect cryptocurrency type from a wallet address (GET method)."""
    request = CryptoDetectionRequest(address=address, chain_hint=chain_hint)
    return await detect_crypto(request)


@router.post(
    "/detect-crypto/all",
    response_model=CryptoMultiDetectionResponse,
    summary="Get all possible cryptocurrency matches",
    description="""
Get all possible cryptocurrency matches for an address.

Some addresses (particularly 0x addresses) could belong to multiple
EVM-compatible chains. This endpoint returns all possible matches
sorted by confidence score.
""",
)
async def detect_crypto_all(request: CryptoDetectionRequest) -> CryptoMultiDetectionResponse:
    """Get all possible cryptocurrency matches for an address."""
    if not request.address or not request.address.strip():
        raise HTTPException(status_code=400, detail="Address cannot be empty")

    results = detect_all_crypto_addresses(request.address)

    matches = [
        CryptoDetectionResponse(
            address=r.address,
            detected=r.detected,
            coin_name=r.coin_name,
            coin_ticker=r.coin_ticker,
            network=r.network,
            address_type=r.address_type,
            confidence=r.confidence,
            explorer_url=r.explorer_url,
        )
        for r in results
    ]

    best_match = matches[0] if matches else None

    return CryptoMultiDetectionResponse(
        address=request.address,
        matches=matches,
        best_match=best_match,
    )


@router.post(
    "/detect-crypto/batch",
    response_model=BatchDetectionResponse,
    summary="Batch detect cryptocurrency types",
    description="Detect cryptocurrency types for multiple addresses at once (max 100).",
)
async def detect_crypto_batch(request: BatchDetectionRequest) -> BatchDetectionResponse:
    """Batch detect cryptocurrency types for multiple addresses."""
    if not request.addresses:
        raise HTTPException(status_code=400, detail="Addresses list cannot be empty")

    if len(request.addresses) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 addresses per request")

    results = []
    for address in request.addresses:
        result = detect_crypto_address(address)
        results.append(
            CryptoDetectionResponse(
                address=result.address,
                detected=result.detected,
                coin_name=result.coin_name,
                coin_ticker=result.coin_ticker,
                network=result.network,
                address_type=result.address_type,
                confidence=result.confidence,
                explorer_url=result.explorer_url,
            )
        )

    return BatchDetectionResponse(
        count=len(results),
        results=results,
    )


@router.get(
    "/crypto/supported",
    response_model=SupportedCryptocurrenciesResponse,
    summary="List supported cryptocurrencies",
    description="Get a list of all cryptocurrencies supported by the detection system.",
)
async def list_supported_cryptocurrencies() -> SupportedCryptocurrenciesResponse:
    """List all supported cryptocurrencies."""
    detector = CryptoAddressDetector()
    cryptos = detector.get_supported_cryptocurrencies()

    return SupportedCryptocurrenciesResponse(
        count=len(cryptos),
        cryptocurrencies=[
            SupportedCryptocurrency(
                coin_name=c["coin_name"],
                coin_ticker=c["coin_ticker"],
            )
            for c in cryptos
        ],
    )


@router.get(
    "/crypto/validate/{address}",
    response_model=CryptoDetectionResponse,
    summary="Validate cryptocurrency address format",
    description="Validate if a string is a valid cryptocurrency address format.",
)
async def validate_crypto_address(address: str) -> CryptoDetectionResponse:
    """Validate if a string is a valid cryptocurrency address."""
    result = detect_crypto_address(address)

    return CryptoDetectionResponse(
        address=result.address,
        detected=result.detected,
        coin_name=result.coin_name,
        coin_ticker=result.coin_ticker,
        network=result.network,
        address_type=result.address_type,
        confidence=result.confidence,
        explorer_url=result.explorer_url,
    )
