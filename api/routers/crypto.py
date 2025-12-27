"""
Cryptocurrency Ticker API endpoints for Basset Hound.

Provides REST API endpoints for cryptocurrency address analysis and
ticker information retrieval.
"""

from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, ConfigDict

from api.services.crypto_ticker_service import (
    CryptoTickerInfo,
    CryptoTickerService,
    get_crypto_ticker_service,
)


router = APIRouter(prefix="/crypto", tags=["Cryptocurrency"])


# =============================================================================
# Pydantic Models
# =============================================================================


class CryptoTickerResponse(BaseModel):
    """Response model for cryptocurrency ticker information."""

    model_config = ConfigDict(from_attributes=True)

    address: str = Field(..., description="The cryptocurrency wallet address")
    currency: str = Field(..., description="Currency ticker symbol (BTC, ETH, etc.)")
    network: str = Field(..., description="Network type (mainnet, testnet, etc.)")
    ticker_symbol: str = Field(..., description="Trading ticker symbol")
    display_name: str = Field(
        ..., description="Human-readable currency name (Bitcoin, Ethereum, etc.)"
    )
    icon_class: str = Field(
        ..., description="FontAwesome icon class for frontend display"
    )
    explorer_url: Optional[str] = Field(
        None, description="Link to block explorer for the address"
    )
    is_valid: bool = Field(..., description="Whether the address is valid")
    address_type: Optional[str] = Field(
        None, description="Type of address (P2PKH, Bech32, EVM, etc.)"
    )
    confidence: float = Field(
        ..., description="Detection confidence score (0.0 to 1.0)"
    )


class TickerNotFoundResponse(BaseModel):
    """Response when address is not recognized."""

    address: str
    detected: bool = False
    message: str = "Address not recognized as a valid cryptocurrency address"


class BatchTickerRequest(BaseModel):
    """Request model for batch ticker lookup."""

    addresses: List[str] = Field(
        ...,
        description="List of cryptocurrency addresses to analyze",
        min_length=1,
        max_length=100,
    )


class BatchTickerResponse(BaseModel):
    """Response model for batch ticker lookup."""

    count: int = Field(..., description="Number of addresses processed")
    found: int = Field(..., description="Number of addresses successfully identified")
    results: Dict[str, CryptoTickerResponse] = Field(
        ..., description="Mapping of addresses to their ticker info"
    )
    not_found: List[str] = Field(
        ..., description="Addresses that could not be identified"
    )


class SupportedCurrencyInfo(BaseModel):
    """Information about a supported cryptocurrency."""

    ticker_symbol: str = Field(..., description="Currency ticker symbol")
    display_name: str = Field(..., description="Human-readable currency name")
    icon_class: str = Field(..., description="FontAwesome icon class")
    has_explorer: bool = Field(
        ..., description="Whether a block explorer is configured"
    )


class SupportedCurrenciesResponse(BaseModel):
    """Response model for listing supported currencies."""

    count: int = Field(..., description="Total number of supported currencies")
    currencies: List[SupportedCurrencyInfo] = Field(
        ..., description="List of supported currencies with metadata"
    )


class ExplorerUrlRequest(BaseModel):
    """Request model for generating explorer URL."""

    address: str = Field(..., description="The cryptocurrency wallet address")
    currency: str = Field(..., description="Currency ticker symbol (BTC, ETH, etc.)")
    network: str = Field(
        "mainnet", description="Network type (mainnet, testnet, etc.)"
    )


class ExplorerUrlResponse(BaseModel):
    """Response model for explorer URL."""

    address: str
    currency: str
    network: str
    explorer_url: Optional[str] = Field(
        None, description="Block explorer URL, or null if not available"
    )


# =============================================================================
# Helper Functions
# =============================================================================


def _ticker_info_to_response(info: CryptoTickerInfo) -> CryptoTickerResponse:
    """Convert CryptoTickerInfo to response model."""
    return CryptoTickerResponse(
        address=info.address,
        currency=info.currency,
        network=info.network,
        ticker_symbol=info.ticker_symbol,
        display_name=info.display_name,
        icon_class=info.icon_class,
        explorer_url=info.explorer_url,
        is_valid=info.is_valid,
        address_type=info.address_type,
        confidence=info.confidence,
    )


# =============================================================================
# API Endpoints
# =============================================================================


@router.get(
    "/ticker/{address}",
    response_model=CryptoTickerResponse,
    responses={
        200: {"description": "Ticker information retrieved successfully"},
        404: {
            "description": "Address not recognized",
            "model": TickerNotFoundResponse,
        },
    },
    summary="Get ticker info for single address",
    description="""
Get comprehensive cryptocurrency ticker information for a wallet address.

Returns:
- Currency type (BTC, ETH, LTC, etc.)
- Human-readable display name
- Network information (mainnet/testnet)
- Address type (P2PKH, Bech32, EVM, etc.)
- Block explorer URL
- Frontend display icon class
- Detection confidence score

Supports 30+ cryptocurrencies including Bitcoin, Ethereum, Litecoin,
Dogecoin, XRP, Cardano, Solana, and many EVM-compatible chains.
""",
)
async def get_ticker_info(address: str) -> CryptoTickerResponse:
    """Get ticker information for a single cryptocurrency address."""
    if not address or not address.strip():
        raise HTTPException(status_code=400, detail="Address cannot be empty")

    service = get_crypto_ticker_service()
    info = service.get_ticker_info(address)

    if not info:
        raise HTTPException(
            status_code=404,
            detail={
                "address": address,
                "detected": False,
                "message": "Address not recognized as a valid cryptocurrency address",
            },
        )

    return _ticker_info_to_response(info)


@router.post(
    "/ticker/batch",
    response_model=BatchTickerResponse,
    summary="Get ticker info for multiple addresses",
    description="""
Get cryptocurrency ticker information for multiple addresses at once.

Accepts up to 100 addresses per request. Returns a dictionary mapping
each recognized address to its ticker information, plus a list of
addresses that could not be identified.

Useful for bulk analysis of wallet addresses in investigations.
""",
)
async def get_ticker_info_batch(request: BatchTickerRequest) -> BatchTickerResponse:
    """Get ticker information for multiple cryptocurrency addresses."""
    if not request.addresses:
        raise HTTPException(status_code=400, detail="Addresses list cannot be empty")

    if len(request.addresses) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 addresses per request")

    service = get_crypto_ticker_service()
    results = service.get_ticker_info_batch(request.addresses)

    # Build response
    found_results: Dict[str, CryptoTickerResponse] = {}
    not_found: List[str] = []

    for address in request.addresses:
        address = address.strip() if address else ""
        if not address:
            continue

        if address in results:
            found_results[address] = _ticker_info_to_response(results[address])
        else:
            not_found.append(address)

    return BatchTickerResponse(
        count=len(request.addresses),
        found=len(found_results),
        results=found_results,
        not_found=not_found,
    )


@router.get(
    "/currencies",
    response_model=SupportedCurrenciesResponse,
    summary="List supported cryptocurrencies",
    description="""
Get a list of all cryptocurrencies supported by the ticker service.

Returns metadata for each currency including:
- Ticker symbol
- Display name
- Icon class for frontend
- Whether a block explorer is available
""",
)
async def list_supported_currencies() -> SupportedCurrenciesResponse:
    """List all supported cryptocurrencies with metadata."""
    service = get_crypto_ticker_service()
    currencies = service.get_supported_currencies()

    return SupportedCurrenciesResponse(
        count=len(currencies),
        currencies=[
            SupportedCurrencyInfo(
                ticker_symbol=c["ticker_symbol"],
                display_name=c["display_name"],
                icon_class=c["icon_class"],
                has_explorer=c["has_explorer"],
            )
            for c in currencies
        ],
    )


@router.post(
    "/explorer-url",
    response_model=ExplorerUrlResponse,
    summary="Generate block explorer URL",
    description="""
Generate a block explorer URL for a given address and currency.

Useful when you already know the currency type and want to generate
an explorer link without running full address detection.
""",
)
async def generate_explorer_url(request: ExplorerUrlRequest) -> ExplorerUrlResponse:
    """Generate a block explorer URL for an address."""
    if not request.address or not request.address.strip():
        raise HTTPException(status_code=400, detail="Address cannot be empty")

    if not request.currency or not request.currency.strip():
        raise HTTPException(status_code=400, detail="Currency cannot be empty")

    service = get_crypto_ticker_service()
    explorer_url = service.format_explorer_url(
        request.address.strip(),
        request.currency.strip(),
        request.network or "mainnet",
    )

    return ExplorerUrlResponse(
        address=request.address.strip(),
        currency=request.currency.strip().upper(),
        network=request.network or "mainnet",
        explorer_url=explorer_url if explorer_url else None,
    )


@router.get(
    "/explorer-url/{address}",
    response_model=ExplorerUrlResponse,
    summary="Generate block explorer URL (GET)",
    description="""
Generate a block explorer URL for an address with auto-detection.

First detects the cryptocurrency type, then generates the appropriate
block explorer URL. If detection fails, returns null for explorer_url.
""",
)
async def get_explorer_url(
    address: str,
    network: str = Query("mainnet", description="Network type"),
) -> ExplorerUrlResponse:
    """Generate a block explorer URL with auto-detection."""
    if not address or not address.strip():
        raise HTTPException(status_code=400, detail="Address cannot be empty")

    service = get_crypto_ticker_service()
    info = service.get_ticker_info(address)

    if not info:
        return ExplorerUrlResponse(
            address=address.strip(),
            currency="UNKNOWN",
            network=network,
            explorer_url=None,
        )

    return ExplorerUrlResponse(
        address=info.address,
        currency=info.currency,
        network=info.network,
        explorer_url=info.explorer_url,
    )
