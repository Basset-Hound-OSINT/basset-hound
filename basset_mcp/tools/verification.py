"""
Verification tools for MCP.

Provides tools for validating and verifying identifiers (email, phone, crypto,
domain, IP, URL, username) via MCP. Exposes the existing verification service
infrastructure to AI agents.

These tools are stateless validation utilities - they don't store results
but return verification status for use in workflows.
"""

import sys
import os

# Add parent paths for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from api.services.verification_service import (
    VerificationService,
    VerificationLevel,
    VerificationResult,
    VerificationStatus,
)
from api.utils.crypto_detector import CryptoAddressDetector


def register_verification_tools(mcp):
    """Register verification tools with the MCP server."""

    # Initialize services (singleton pattern)
    _verification_service = None
    _crypto_detector = None

    def get_verification_service():
        nonlocal _verification_service
        if _verification_service is None:
            _verification_service = VerificationService()
        return _verification_service

    def get_crypto_detector():
        nonlocal _crypto_detector
        if _crypto_detector is None:
            _crypto_detector = CryptoAddressDetector()
        return _crypto_detector

    def _result_to_dict(result: VerificationResult) -> dict:
        """Convert VerificationResult to dictionary."""
        return {
            "identifier_type": result.identifier_type,
            "identifier_value": result.identifier_value,
            "status": result.status.value if isinstance(result.status, VerificationStatus) else result.status,
            "verification_level": result.verification_level.value if isinstance(result.verification_level, VerificationLevel) else result.verification_level,
            "is_valid": result.is_valid,
            "confidence": result.confidence,
            "details": result.details,
            "warnings": result.warnings,
            "errors": result.errors,
            "verified_at": result.verified_at.isoformat() if result.verified_at else None,
            "allows_override": result.allows_override,
            "override_hint": result.override_hint
        }

    @mcp.tool()
    def get_verification_types() -> dict:
        """
        Get available identifier types and verification levels.

        Returns:
            Dictionary with supported types and levels
        """
        return {
            "identifier_types": [
                "email", "phone", "crypto_address", "domain",
                "ip_address", "url", "username"
            ],
            "verification_levels": [
                {"value": "none", "description": "No verification"},
                {"value": "format", "description": "Syntax/format validation only"},
                {"value": "network", "description": "DNS/MX/network verification"},
                {"value": "external_api", "description": "External API verification (future)"}
            ]
        }

    @mcp.tool()
    async def verify_identifier(
        value: str,
        identifier_type: str,
        level: str = "format"
    ) -> dict:
        """
        Verify any identifier type.

        Generic verification that routes to the appropriate specialized verifier.

        Args:
            value: The identifier value to verify
            identifier_type: Type of identifier (email, phone, crypto_address, domain, ip_address, url, username)
            level: Verification level (none, format, network)

        Returns:
            Verification result with status, confidence, and details
        """
        service = get_verification_service()

        try:
            level_enum = VerificationLevel(level)
        except ValueError:
            return {"error": f"Invalid verification level: {level}"}

        try:
            result = await service.verify(value, identifier_type, level_enum)
            return _result_to_dict(result)
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    async def verify_email(
        email: str,
        level: str = "format"
    ) -> dict:
        """
        Verify an email address.

        Checks format, detects disposable domains, validates MX records.

        Args:
            email: Email address to verify
            level: Verification level (format or network for MX lookup)

        Returns:
            Verification result with:
            - is_valid: Whether email passes validation
            - confidence: 0.0-1.0 confidence score
            - details: local_part, domain, has_plus_addressing, is_disposable
            - warnings: Disposable domain warnings, typo suggestions
        """
        service = get_verification_service()

        try:
            level_enum = VerificationLevel(level)
        except ValueError:
            return {"error": f"Invalid verification level: {level}"}

        result = await service.verify_email(email, level_enum)
        return _result_to_dict(result)

    @mcp.tool()
    async def verify_phone(
        phone: str,
        level: str = "format",
        default_region: str = "US"
    ) -> dict:
        """
        Verify a phone number.

        Uses Google's libphonenumber for validation and metadata extraction.

        Args:
            phone: Phone number to verify (any format)
            level: Verification level
            default_region: Default country code if not specified (default: US)

        Returns:
            Verification result with:
            - is_valid: Whether phone passes validation
            - confidence: 0.0-1.0 confidence score
            - details: e164_format, international_format, national_format,
                      country_code, region, location, carrier, number_type
        """
        service = get_verification_service()

        try:
            level_enum = VerificationLevel(level)
        except ValueError:
            return {"error": f"Invalid verification level: {level}"}

        result = await service.verify_phone(phone, level_enum, default_region)
        return _result_to_dict(result)

    @mcp.tool()
    async def verify_domain(
        domain: str,
        level: str = "format"
    ) -> dict:
        """
        Verify a domain name.

        Validates format and optionally resolves DNS.

        Args:
            domain: Domain name to verify
            level: Verification level (format or network for DNS)

        Returns:
            Verification result with:
            - is_valid: Whether domain is valid
            - confidence: 0.0-1.0 confidence score
            - details: domain, tld, ip_addresses (if network level)
        """
        service = get_verification_service()

        try:
            level_enum = VerificationLevel(level)
        except ValueError:
            return {"error": f"Invalid verification level: {level}"}

        result = await service.verify_domain(domain, level_enum)
        return _result_to_dict(result)

    @mcp.tool()
    async def verify_ip(ip: str) -> dict:
        """
        Verify an IP address.

        Validates format and detects IP type (IPv4/IPv6, public/private/loopback).

        Args:
            ip: IP address to verify

        Returns:
            Verification result with:
            - is_valid: Whether IP is valid
            - details: version (4 or 6), is_private, is_loopback, is_link_local
            - warnings: Advisory for special IP ranges
        """
        service = get_verification_service()
        result = await service.verify_ip(ip)
        return _result_to_dict(result)

    @mcp.tool()
    async def verify_url(url: str) -> dict:
        """
        Verify a URL.

        Validates URL format and extracts components.

        Args:
            url: URL to verify

        Returns:
            Verification result with:
            - is_valid: Whether URL is valid
            - details: scheme, domain, path, has_query, has_fragment
        """
        service = get_verification_service()
        result = await service.verify_url(url)
        return _result_to_dict(result)

    @mcp.tool()
    async def verify_username(username: str) -> dict:
        """
        Verify a username format.

        Validates common username patterns.

        Args:
            username: Username to verify (with or without @ prefix)

        Returns:
            Verification result with validity and format details
        """
        service = get_verification_service()
        result = await service.verify_username(username)
        return _result_to_dict(result)

    @mcp.tool()
    def verify_crypto(
        address: str,
        validate_checksum: bool = True
    ) -> dict:
        """
        Detect and verify a cryptocurrency address.

        Identifies cryptocurrency type from address format and validates checksum.
        Supports 30+ cryptocurrencies including Bitcoin, Ethereum, Litecoin,
        Dogecoin, Monero, Solana, Cardano, and more.

        Args:
            address: Cryptocurrency address to verify
            validate_checksum: Whether to validate checksum (default: True)

        Returns:
            Detection result with:
            - detected: Whether a crypto address was detected
            - currency: Detected cryptocurrency (btc, eth, ltc, etc.)
            - currency_name: Human-readable name
            - address_type: Specific format (p2pkh, bech32, evm, etc.)
            - confidence: 0.0-1.0 confidence score
            - checksum_valid: Whether checksum is valid (if applicable)
            - explorer_url: Link to block explorer for this address
        """
        detector = get_crypto_detector()
        result = detector.detect(address, validate_checksum)

        return {
            "address": address,
            "detected": result.detected,
            "currency": result.coin_ticker.lower() if result.coin_ticker else None,
            "currency_name": result.coin_name,
            "address_type": result.address_type,
            "confidence": result.confidence,
            "checksum_valid": result.checksum_valid,
            "network": result.network,
            "explorer_url": result.explorer_url
        }

    @mcp.tool()
    def get_all_crypto_matches(address: str) -> dict:
        """
        Get all possible cryptocurrency matches for an address.

        Some address formats (like 0x...) can match multiple chains.
        This returns all possibilities with confidence scores.

        Args:
            address: Cryptocurrency address to check

        Returns:
            List of all possible matches with confidence scores
        """
        detector = get_crypto_detector()
        matches = detector.detect_all_possible(address)

        return {
            "address": address,
            "match_count": len(matches),
            "matches": [
                {
                    "currency": m.coin_ticker.lower() if m.coin_ticker else None,
                    "currency_name": m.coin_name,
                    "address_type": m.address_type,
                    "confidence": m.confidence,
                    "checksum_valid": m.checksum_valid,
                    "explorer_url": m.explorer_url
                }
                for m in matches
            ]
        }

    @mcp.tool()
    async def batch_verify(items: list, level: str = "format") -> dict:
        """
        Verify multiple identifiers in batch.

        More efficient than calling verify_identifier multiple times.

        Args:
            items: List of dicts with 'value' and 'type' keys
                   e.g., [{"value": "test@example.com", "type": "email"}]
            level: Verification level to apply to all items

        Returns:
            List of verification results
        """
        service = get_verification_service()

        if not items:
            return {"results": [], "count": 0}

        if len(items) > 100:
            return {"error": "Maximum 100 items per batch"}

        try:
            level_enum = VerificationLevel(level)
        except ValueError:
            return {"error": f"Invalid verification level: {level}"}

        # Convert to service format
        service_items = []
        for item in items:
            if not isinstance(item, dict) or "value" not in item or "type" not in item:
                continue
            service_items.append({
                "value": item["value"],
                "type": item["type"]
            })

        results = await service.batch_verify(service_items, level_enum)

        return {
            "count": len(results),
            "results": [_result_to_dict(r) for r in results]
        }

    @mcp.tool()
    def get_supported_cryptocurrencies() -> dict:
        """
        Get list of all supported cryptocurrencies for detection.

        Returns:
            Dictionary with all supported currencies, their symbols, and address formats
        """
        return {
            "count": 30,
            "currencies": [
                {"symbol": "btc", "name": "Bitcoin", "formats": ["p2pkh", "p2sh", "bech32", "bech32m"]},
                {"symbol": "eth", "name": "Ethereum", "formats": ["evm"]},
                {"symbol": "ltc", "name": "Litecoin", "formats": ["legacy", "p2sh", "bech32"]},
                {"symbol": "doge", "name": "Dogecoin", "formats": ["standard"]},
                {"symbol": "bch", "name": "Bitcoin Cash", "formats": ["legacy", "cashaddr"]},
                {"symbol": "xrp", "name": "Ripple", "formats": ["classic", "x-address"]},
                {"symbol": "ada", "name": "Cardano", "formats": ["shelley", "byron"]},
                {"symbol": "sol", "name": "Solana", "formats": ["standard"]},
                {"symbol": "dot", "name": "Polkadot", "formats": ["standard"]},
                {"symbol": "atom", "name": "Cosmos", "formats": ["bech32"]},
                {"symbol": "trx", "name": "Tron", "formats": ["standard"]},
                {"symbol": "xlm", "name": "Stellar", "formats": ["standard"]},
                {"symbol": "xmr", "name": "Monero", "formats": ["standard", "subaddress"]},
                {"symbol": "avax", "name": "Avalanche", "formats": ["x-chain", "p-chain", "c-chain"]},
                {"symbol": "zec", "name": "Zcash", "formats": ["transparent", "shielded"]},
                {"symbol": "dash", "name": "Dash", "formats": ["standard"]},
                {"symbol": "eos", "name": "EOS", "formats": ["account"]},
                {"symbol": "neo", "name": "NEO", "formats": ["standard"]},
                {"symbol": "near", "name": "NEAR Protocol", "formats": ["account", "implicit"]},
                {"symbol": "algo", "name": "Algorand", "formats": ["standard"]},
                {"symbol": "xtz", "name": "Tezos", "formats": ["tz1", "tz2", "tz3", "kt1"]},
                {"symbol": "hbar", "name": "Hedera", "formats": ["account"]},
                {"symbol": "fil", "name": "Filecoin", "formats": ["f1", "f2", "f3"]},
                {"symbol": "apt", "name": "Aptos", "formats": ["standard"]},
                {"symbol": "sui", "name": "Sui", "formats": ["standard"]},
                {"symbol": "bnb", "name": "BNB Chain", "formats": ["evm"]},
                {"symbol": "matic", "name": "Polygon", "formats": ["evm"]},
                {"symbol": "arb", "name": "Arbitrum", "formats": ["evm"]},
                {"symbol": "op", "name": "Optimism", "formats": ["evm"]},
                {"symbol": "base", "name": "Base", "formats": ["evm"]}
            ],
            "evm_compatible": [
                "eth", "bnb", "matic", "arb", "op", "ftm", "celo", "cro", "gnosis", "base"
            ]
        }
