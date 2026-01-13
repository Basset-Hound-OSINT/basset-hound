"""
Integration tests for basset-hound <-> basset-verify communication.

These tests verify the integration between basset-hound and the basset-verify
microservice for identifier verification.

Tests are designed to:
1. Run successfully when basset-verify is available (full integration)
2. Skip gracefully when basset-verify is not running
3. Verify graceful degradation behavior

To run these tests:
    # Start basset-verify first (optional - tests will skip if unavailable)
    cd ~/basset-verify && python -m basset_verify.server

    # Run integration tests
    pytest tests/integration/test_basset_verify_integration.py -v
"""

import os
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock

import httpx

# Add project root to path for imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api.clients.basset_verify_client import (
    BassetVerifyClient,
    VerificationResult,
    VerificationLevel,
    IdentifierType,
    VerificationStatus,
    BatchVerificationResult,
    ServiceStatus,
    get_basset_verify_client,
    close_basset_verify_client,
)


# Configuration
BASSET_VERIFY_URL = os.environ.get("BASSET_VERIFY_URL", "http://localhost:8001")
INTEGRATION_TIMEOUT = 5.0  # seconds


# Configure pytest-asyncio for all tests
pytestmark = pytest.mark.asyncio


# Fixtures

@pytest.fixture
def client() -> BassetVerifyClient:
    """Create a basset-verify client for testing (sync fixture, async usage)."""
    return BassetVerifyClient(
        base_url=BASSET_VERIFY_URL,
        timeout=INTEGRATION_TIMEOUT,
    )


@pytest.fixture
def mock_client() -> BassetVerifyClient:
    """Create a mock client for unit testing without network."""
    return BassetVerifyClient(base_url="http://mock:8001", timeout=1.0)


# ==============================================================================
# Test 1: Health Check / Connection Test
# ==============================================================================

class TestHealthCheck:
    """Test connection to basset-verify service."""

    async def test_health_check_when_available(self, client: BassetVerifyClient):
        """Test health check returns correct status when service is available."""
        status = await client.health_check()

        if status.available:
            assert status.status == "healthy"
            assert status.version is not None
            assert status.error_message is None
        else:
            # Service not available - graceful degradation
            assert status.status in ["unreachable", "timeout", "error"]
            assert status.error_message is not None

        # Cleanup
        await client.close()

    async def test_health_check_graceful_failure(self):
        """Test health check returns graceful failure when service is down."""
        # Use a port that's definitely not running basset-verify
        client = BassetVerifyClient(
            base_url="http://localhost:59999",
            timeout=1.0,
        )
        try:
            status = await client.health_check()

            assert status.available is False
            assert status.status in ["unreachable", "timeout", "error"]
            assert status.error_message is not None
        finally:
            await client.close()

    async def test_health_check_timeout(self):
        """Test health check handles timeout gracefully."""
        # Very short timeout to force timeout
        client = BassetVerifyClient(
            base_url=BASSET_VERIFY_URL,
            timeout=0.001,
        )
        try:
            status = await client.health_check()

            # Should handle timeout gracefully
            assert isinstance(status, ServiceStatus)
            if not status.available:
                assert status.error_message is not None
        finally:
            await client.close()


# ==============================================================================
# Test 2: Email Verification
# ==============================================================================

class TestEmailVerification:
    """Test email verification via basset-verify."""

    async def test_verify_valid_email_format(self, client: BassetVerifyClient):
        """Test verifying a valid email address format."""
        try:
            result = await client.verify_email(
                "test@example.com",
                level=VerificationLevel.FORMAT,
            )

            assert isinstance(result, VerificationResult)
            assert result.identifier_type == "email"
            assert result.identifier_value == "test@example.com"

            if result.status != VerificationStatus.UNAVAILABLE.value:
                # Service available - check full result
                assert result.verification_level == "format"
                assert result.is_valid is not None
                assert 0.0 <= result.confidence <= 1.0
            else:
                # Graceful degradation
                assert result.is_valid is None
                assert result.confidence == 0.0
        finally:
            await client.close()

    async def test_verify_invalid_email_format(self, client: BassetVerifyClient):
        """Test verifying an invalid email address format."""
        try:
            result = await client.verify_email(
                "not-an-email",
                level=VerificationLevel.FORMAT,
            )

            assert isinstance(result, VerificationResult)
            assert result.identifier_value == "not-an-email"

            if result.status != VerificationStatus.UNAVAILABLE.value:
                assert result.is_valid is False or result.status == "invalid"
        finally:
            await client.close()

    async def test_verify_email_with_network_level(self, client: BassetVerifyClient):
        """Test email verification with network (MX) lookup."""
        try:
            result = await client.verify_email(
                "test@google.com",
                level=VerificationLevel.NETWORK,
            )

            assert isinstance(result, VerificationResult)
            if result.status != VerificationStatus.UNAVAILABLE.value:
                assert result.verification_level == "network"
        finally:
            await client.close()

    async def test_verify_email_graceful_degradation(self):
        """Test email verification returns graceful result when service is down."""
        client = BassetVerifyClient(
            base_url="http://localhost:59999",
            timeout=1.0,
        )
        try:
            result = await client.verify_email("test@example.com")

            assert result.status == VerificationStatus.UNAVAILABLE.value
            assert result.is_valid is None
            assert result.confidence == 0.0
            assert result.allows_override is True
            assert len(result.warnings) > 0
        finally:
            await client.close()


# ==============================================================================
# Test 3: Phone Verification
# ==============================================================================

class TestPhoneVerification:
    """Test phone verification via basset-verify."""

    async def test_verify_valid_phone_us(self, client: BassetVerifyClient):
        """Test verifying a valid US phone number."""
        try:
            result = await client.verify_phone(
                "+1 555 123 4567",
                level=VerificationLevel.FORMAT,
                default_region="US",
            )

            assert isinstance(result, VerificationResult)
            assert result.identifier_type == "phone"

            if result.status != VerificationStatus.UNAVAILABLE.value:
                assert result.verification_level == "format"
        finally:
            await client.close()

    async def test_verify_valid_phone_international(self, client: BassetVerifyClient):
        """Test verifying an international phone number."""
        try:
            result = await client.verify_phone(
                "+44 20 7946 0958",  # UK number
                level=VerificationLevel.FORMAT,
            )

            assert isinstance(result, VerificationResult)
            if result.status != VerificationStatus.UNAVAILABLE.value:
                assert "details" in dir(result) or hasattr(result, "details")
        finally:
            await client.close()

    async def test_verify_invalid_phone(self, client: BassetVerifyClient):
        """Test verifying an invalid phone number."""
        try:
            result = await client.verify_phone(
                "12345",
                level=VerificationLevel.FORMAT,
            )

            assert isinstance(result, VerificationResult)
            # Invalid numbers should still return a result
        finally:
            await client.close()

    async def test_verify_phone_graceful_degradation(self):
        """Test phone verification graceful degradation."""
        client = BassetVerifyClient(
            base_url="http://localhost:59999",
            timeout=1.0,
        )
        try:
            result = await client.verify_phone("+1 555 123 4567")

            assert result.status == VerificationStatus.UNAVAILABLE.value
            assert result.is_valid is None
        finally:
            await client.close()


# ==============================================================================
# Test 4: Crypto Address Verification
# ==============================================================================

class TestCryptoVerification:
    """Test cryptocurrency address verification via basset-verify."""

    # Test addresses (do not use in production - these are well-known)
    BITCOIN_ADDRESS = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"  # Satoshi's genesis block
    ETHEREUM_ADDRESS = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"

    async def test_verify_bitcoin_address(self, client: BassetVerifyClient):
        """Test verifying a Bitcoin address."""
        try:
            result = await client.verify_crypto(
                self.BITCOIN_ADDRESS,
                validate_checksum=True,
            )

            assert isinstance(result, VerificationResult)
            assert result.identifier_type == "crypto_address"

            if result.status != VerificationStatus.UNAVAILABLE.value:
                assert result.is_valid is not None
                # Check for crypto-specific details
                if result.details:
                    assert "coin_ticker" in result.details or "currency" in result.details or "detected_coins" in result.details
        finally:
            await client.close()

    async def test_verify_ethereum_address(self, client: BassetVerifyClient):
        """Test verifying an Ethereum address."""
        try:
            result = await client.verify_crypto(
                self.ETHEREUM_ADDRESS,
                validate_checksum=True,
            )

            assert isinstance(result, VerificationResult)
            if result.status != VerificationStatus.UNAVAILABLE.value:
                assert result.is_valid is not None
        finally:
            await client.close()

    async def test_verify_invalid_crypto_address(self, client: BassetVerifyClient):
        """Test verifying an invalid crypto address."""
        try:
            result = await client.verify_crypto(
                "not-a-crypto-address",
                validate_checksum=True,
            )

            assert isinstance(result, VerificationResult)
            if result.status != VerificationStatus.UNAVAILABLE.value:
                # Invalid addresses should return invalid or low confidence
                assert result.is_valid is False or result.confidence < 0.5
        finally:
            await client.close()

    async def test_get_crypto_matches(self, client: BassetVerifyClient):
        """Test getting all possible crypto matches for an address."""
        try:
            result = await client.get_crypto_matches(self.ETHEREUM_ADDRESS)

            assert isinstance(result, dict)
            assert "address" in result
            assert "matches" in result
            assert "count" in result

            if "error" not in result:
                # EVM address should match multiple chains
                assert result["count"] >= 0
        finally:
            await client.close()

    async def test_get_supported_cryptocurrencies(self, client: BassetVerifyClient):
        """Test getting list of supported cryptocurrencies."""
        try:
            result = await client.get_supported_cryptocurrencies()

            assert isinstance(result, dict)
            assert "cryptocurrencies" in result
            assert "count" in result

            if "error" not in result:
                assert result["count"] > 0
        finally:
            await client.close()

    async def test_crypto_graceful_degradation(self):
        """Test crypto verification graceful degradation."""
        client = BassetVerifyClient(
            base_url="http://localhost:59999",
            timeout=1.0,
        )
        try:
            result = await client.verify_crypto(self.BITCOIN_ADDRESS)

            assert result.status == VerificationStatus.UNAVAILABLE.value
            assert result.is_valid is None
        finally:
            await client.close()


# ==============================================================================
# Test 5: Graceful Degradation (Comprehensive)
# ==============================================================================

class TestGracefulDegradation:
    """Test graceful degradation when basset-verify is unavailable."""

    async def test_all_verification_methods_degrade_gracefully(self):
        """Test that all verification methods handle service unavailability."""
        client = BassetVerifyClient(
            base_url="http://localhost:59999",
            timeout=1.0,
        )
        try:
            # Test each verification method
            test_cases = [
                ("email", await client.verify_email("test@example.com")),
                ("phone", await client.verify_phone("+1234567890")),
                ("crypto", await client.verify_crypto("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa")),
                ("domain", await client.verify_domain("example.com")),
                ("ip", await client.verify_ip("8.8.8.8")),
                ("url", await client.verify_url("https://example.com")),
                ("username", await client.verify_username("@testuser")),
            ]

            for name, result in test_cases:
                assert result.status == VerificationStatus.UNAVAILABLE.value, \
                    f"{name} verification should degrade gracefully"
                assert result.is_valid is None, \
                    f"{name} verification should have None is_valid"
                assert result.confidence == 0.0, \
                    f"{name} verification should have 0.0 confidence"
                assert result.allows_override is True, \
                    f"{name} verification should allow override"
        finally:
            await client.close()

    async def test_batch_verify_degrades_gracefully(self):
        """Test batch verification graceful degradation."""
        client = BassetVerifyClient(
            base_url="http://localhost:59999",
            timeout=1.0,
        )
        try:
            items = [
                {"value": "test@example.com", "type": "email"},
                {"value": "+1234567890", "type": "phone"},
            ]

            result = await client.batch_verify(items)

            assert isinstance(result, BatchVerificationResult)
            assert result.success is False
            assert result.error_message is not None
            assert len(result.results) == len(items)

            for r in result.results:
                assert r.status == VerificationStatus.UNAVAILABLE.value
        finally:
            await client.close()

    async def test_metadata_endpoints_degrade_gracefully(self):
        """Test metadata endpoints graceful degradation."""
        client = BassetVerifyClient(
            base_url="http://localhost:59999",
            timeout=1.0,
        )
        try:
            # Test verification types
            types_result = await client.get_verification_types()
            assert "error" in types_result
            assert types_result["identifier_types"] == []

            # Test supported cryptocurrencies
            crypto_result = await client.get_supported_cryptocurrencies()
            assert "error" in crypto_result
            assert crypto_result["cryptocurrencies"] == []
        finally:
            await client.close()


# ==============================================================================
# Test 6: Batch Verification
# ==============================================================================

class TestBatchVerification:
    """Test batch verification via basset-verify."""

    async def test_batch_verify_multiple_types(self, client: BassetVerifyClient):
        """Test batch verification with multiple identifier types."""
        try:
            items = [
                {"value": "test@example.com", "type": "email"},
                {"value": "+1234567890", "type": "phone"},
                {"value": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", "type": "crypto_address"},
                {"value": "example.com", "type": "domain"},
            ]

            result = await client.batch_verify(items, level=VerificationLevel.FORMAT)

            assert isinstance(result, BatchVerificationResult)

            if result.success:
                assert result.count == len(items)
                assert len(result.results) == len(items)

                for r in result.results:
                    assert isinstance(r, VerificationResult)
            else:
                # Service unavailable
                assert result.error_message is not None
        finally:
            await client.close()

    async def test_batch_verify_exceeds_limit(self, client: BassetVerifyClient):
        """Test batch verification rejects too many items."""
        try:
            items = [{"value": f"test{i}@example.com", "type": "email"} for i in range(101)]

            result = await client.batch_verify(items)

            assert result.success is False
            assert "exceed" in result.error_message.lower()
        finally:
            await client.close()

    async def test_batch_verify_empty_list(self, client: BassetVerifyClient):
        """Test batch verification with empty list."""
        try:
            # Empty list should be handled by the API
            # The client might accept it but the API should reject
            items = []

            result = await client.batch_verify(items)

            # Either an error or empty results
            assert isinstance(result, BatchVerificationResult)
        finally:
            await client.close()

    async def test_batch_verify_single_item(self, client: BassetVerifyClient):
        """Test batch verification with single item."""
        try:
            items = [{"value": "test@example.com", "type": "email"}]

            result = await client.batch_verify(items)

            if result.success:
                assert result.count == 1
                assert len(result.results) == 1
        finally:
            await client.close()


# ==============================================================================
# Test 7: Verification Result Storage Integration
# ==============================================================================

class TestVerificationResultStorage:
    """Test verification result storage in basset-hound."""

    async def test_verification_result_serialization(self, client: BassetVerifyClient):
        """Test that verification results can be serialized for storage."""
        try:
            result = await client.verify_email("test@example.com")

            # Convert to dict for storage
            result_dict = {
                "identifier_type": result.identifier_type,
                "identifier_value": result.identifier_value,
                "status": result.status,
                "verification_level": result.verification_level,
                "is_valid": result.is_valid,
                "confidence": result.confidence,
                "details": result.details,
                "warnings": result.warnings,
                "errors": result.errors,
                "verified_at": result.verified_at.isoformat() if result.verified_at else None,
                "allows_override": result.allows_override,
                "override_hint": result.override_hint,
            }

            # Verify all fields are serializable
            import json
            json_str = json.dumps(result_dict)
            assert json_str is not None

            # Verify round-trip
            parsed = json.loads(json_str)
            assert parsed["identifier_type"] == result.identifier_type
            assert parsed["identifier_value"] == result.identifier_value
        finally:
            await client.close()

    async def test_verification_result_from_response(self):
        """Test creating VerificationResult from API response data."""
        response_data = {
            "identifier_type": "email",
            "identifier_value": "test@example.com",
            "status": "plausible",
            "verification_level": "format",
            "is_valid": True,
            "confidence": 0.7,
            "details": {"local_part": "test", "domain": "example.com"},
            "warnings": [],
            "errors": [],
            "verified_at": "2026-01-13T12:00:00Z",
            "allows_override": True,
            "override_hint": None,
        }

        result = VerificationResult.from_response(response_data)

        assert result.identifier_type == "email"
        assert result.identifier_value == "test@example.com"
        assert result.status == "plausible"
        assert result.is_valid is True
        assert result.confidence == 0.7
        assert result.details["local_part"] == "test"

    async def test_unavailable_result_factory(self):
        """Test creating unavailable results for graceful degradation."""
        result = VerificationResult.unavailable(
            identifier_type="email",
            identifier_value="test@example.com",
            message="Custom unavailable message",
        )

        assert result.status == VerificationStatus.UNAVAILABLE.value
        assert result.is_valid is None
        assert result.confidence == 0.0
        assert result.allows_override is True
        assert "Custom unavailable message" in result.warnings


# ==============================================================================
# Test: Generic Verify Method
# ==============================================================================

class TestGenericVerify:
    """Test the generic verify method."""

    async def test_verify_with_enum_types(self, client: BassetVerifyClient):
        """Test verify method with enum types."""
        try:
            result = await client.verify(
                value="test@example.com",
                identifier_type=IdentifierType.EMAIL,
                level=VerificationLevel.FORMAT,
            )

            assert isinstance(result, VerificationResult)
            assert result.identifier_type == "email"
        finally:
            await client.close()

    async def test_verify_with_string_types(self, client: BassetVerifyClient):
        """Test verify method with string types."""
        try:
            result = await client.verify(
                value="test@example.com",
                identifier_type="email",
                level="format",
            )

            assert isinstance(result, VerificationResult)
            assert result.identifier_type == "email"
        finally:
            await client.close()

    async def test_verify_all_identifier_types(self, client: BassetVerifyClient):
        """Test verify method with all identifier types."""
        try:
            test_cases = [
                ("email", "test@example.com"),
                ("phone", "+1234567890"),
                ("crypto_address", "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"),
                ("domain", "example.com"),
                ("ip_address", "8.8.8.8"),
                ("url", "https://example.com"),
                ("username", "@testuser"),
            ]

            for id_type, value in test_cases:
                result = await client.verify(value=value, identifier_type=id_type)
                assert isinstance(result, VerificationResult), f"Failed for {id_type}"
                assert result.identifier_type == id_type, f"Type mismatch for {id_type}"
        finally:
            await client.close()


# ==============================================================================
# Test: Additional Verification Types
# ==============================================================================

class TestAdditionalVerificationTypes:
    """Test domain, IP, URL, and username verification."""

    async def test_verify_domain(self, client: BassetVerifyClient):
        """Test domain verification."""
        try:
            result = await client.verify_domain("example.com")

            assert isinstance(result, VerificationResult)
            assert result.identifier_type == "domain"
        finally:
            await client.close()

    async def test_verify_domain_network_level(self, client: BassetVerifyClient):
        """Test domain verification with DNS lookup."""
        try:
            result = await client.verify_domain(
                "google.com",
                level=VerificationLevel.NETWORK,
            )

            assert isinstance(result, VerificationResult)
            if result.status != VerificationStatus.UNAVAILABLE.value:
                assert result.verification_level == "network"
        finally:
            await client.close()

    async def test_verify_ip_v4(self, client: BassetVerifyClient):
        """Test IPv4 address verification."""
        try:
            result = await client.verify_ip("8.8.8.8")

            assert isinstance(result, VerificationResult)
            assert result.identifier_type == "ip_address"
        finally:
            await client.close()

    async def test_verify_ip_v6(self, client: BassetVerifyClient):
        """Test IPv6 address verification."""
        try:
            result = await client.verify_ip("2001:4860:4860::8888")

            assert isinstance(result, VerificationResult)
            assert result.identifier_type == "ip_address"
        finally:
            await client.close()

    async def test_verify_url(self, client: BassetVerifyClient):
        """Test URL verification."""
        try:
            result = await client.verify_url("https://example.com/path?query=value")

            assert isinstance(result, VerificationResult)
            assert result.identifier_type == "url"
        finally:
            await client.close()

    async def test_verify_username(self, client: BassetVerifyClient):
        """Test username verification."""
        try:
            result = await client.verify_username("@johndoe")

            assert isinstance(result, VerificationResult)
            assert result.identifier_type == "username"
        finally:
            await client.close()


# ==============================================================================
# Test: Client Lifecycle
# ==============================================================================

class TestClientLifecycle:
    """Test client lifecycle and resource management."""

    async def test_context_manager(self):
        """Test client as async context manager."""
        async with BassetVerifyClient(base_url=BASSET_VERIFY_URL) as client:
            assert client._client is not None
            status = await client.health_check()
            assert isinstance(status, ServiceStatus)

        # After context exit, client should be closed
        assert client._client is None

    async def test_explicit_close(self):
        """Test explicit client close."""
        client = BassetVerifyClient(base_url=BASSET_VERIFY_URL)

        # Make a request to initialize client
        await client.health_check()
        assert client._client is not None

        # Close explicitly
        await client.close()
        assert client._client is None

    async def test_global_client_singleton(self):
        """Test global client singleton pattern."""
        # Get client twice
        client1 = get_basset_verify_client()
        client2 = get_basset_verify_client()

        assert client1 is client2

        # Cleanup
        await close_basset_verify_client()


# ==============================================================================
# Test: Error Handling
# ==============================================================================

class TestErrorHandling:
    """Test error handling in various scenarios."""

    async def test_http_error_handling(self):
        """Test handling of HTTP errors."""
        client = BassetVerifyClient(base_url="http://mock:8001", timeout=1.0)

        # Create a mock httpx client
        mock_http_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error",
            request=MagicMock(),
            response=mock_response,
        )
        mock_http_client.post = AsyncMock(return_value=mock_response)

        # Inject the mock client
        client._client = mock_http_client

        result = await client.verify_email("test@example.com")

        assert result.status == "error"
        assert len(result.errors) > 0

    async def test_connection_error_handling(self):
        """Test handling of connection errors."""
        client = BassetVerifyClient(base_url="http://mock:8001", timeout=1.0)

        # Create a mock httpx client that raises ConnectError
        mock_http_client = MagicMock()
        mock_http_client.post = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        # Inject the mock client
        client._client = mock_http_client

        result = await client.verify_email("test@example.com")

        assert result.status == VerificationStatus.UNAVAILABLE.value
        assert result.is_valid is None

    async def test_timeout_error_handling(self):
        """Test handling of timeout errors."""
        client = BassetVerifyClient(base_url="http://mock:8001", timeout=1.0)

        # Create a mock httpx client that raises TimeoutException
        mock_http_client = MagicMock()
        mock_http_client.post = AsyncMock(
            side_effect=httpx.TimeoutException("Request timeout")
        )

        # Inject the mock client
        client._client = mock_http_client

        result = await client.verify_email("test@example.com")

        assert result.status == VerificationStatus.UNAVAILABLE.value
        assert result.is_valid is None


# ==============================================================================
# Test: Verification Types Endpoint
# ==============================================================================

class TestVerificationTypesEndpoint:
    """Test the verification types metadata endpoint."""

    async def test_get_verification_types(self, client: BassetVerifyClient):
        """Test getting supported verification types."""
        try:
            result = await client.get_verification_types()

            assert isinstance(result, dict)
            assert "identifier_types" in result
            assert "verification_levels" in result

            if "error" not in result:
                # Check expected types
                expected_types = ["email", "phone", "crypto_address", "domain"]
                for expected in expected_types:
                    assert expected in result["identifier_types"]

                # Check expected levels
                expected_levels = ["format", "network"]
                for expected in expected_levels:
                    assert expected in result["verification_levels"]
        finally:
            await client.close()
